"""HTTP-level regression coverage for complete CRM and campaign workflows."""
import json
import asyncio
from unittest.mock import AsyncMock
import worker
import core.contact_lookup as lookup
import main
from core.models import AIAnalysis, Business, BusinessSource, Campaign, Opportunity, ProviderHealth
from core.provider_health import provider_failure
from providers.groq_provider import GroqProvider
from test_accounts_and_contact_options import setup, headers


def test_crm_lifecycle_import_exports_and_bulk_selection(setup):
    client, factory = setup
    auth = headers(1)
    response = client.post('/api/crm/leads', headers=auth, json={
        'name':'QA Oak Roofing', 'city':'Austin', 'country':'USA', 'primary_phone':'+1 512 555 0199',
        'commercial_score':85, 'owner_name':'Sales', 'contact_email':'qa@oak.example',
    })
    assert response.status_code == 200, response.text
    lead_id = response.json()['lead_id']
    assert client.patch(f'/api/crm/leads/{lead_id}', headers=auth, json={'owner_name':None, 'tags':['priority'], 'stage':'contacted'}).status_code == 200
    result = client.patch('/api/crm/actions/bulk', headers=auth, json={'lead_ids':[lead_id,lead_id], 'stage':'qualified'})
    assert result.status_code == 200, result.text
    assert result.json()['updated'] == 1
    assert client.patch('/api/crm/actions/bulk', headers=auth, json={'lead_ids':[], 'stage':'new'}).status_code == 400
    assert client.post(f'/api/crm/leads/{lead_id}/activities', headers=auth, json={'body':'QA follow-up'}).status_code == 200
    assert client.post(f'/api/crm/leads/{lead_id}/activities', headers=auth, json={'body':' '}).status_code == 400
    for path in ('/api/leads', '/api/dashboard', f'/api/crm/leads/{lead_id}', f'/api/leads/{lead_id}'):
        result = client.get(path, headers=auth)
        assert result.status_code == 200, (path, result.text)
    assert client.post(f'/api/leads/{lead_id}/export', headers=auth).status_code == 200
    for format in ('csv','tsv','json'):
        result = client.get(f'/api/crm/leads/export?format={format}&ids={lead_id}', headers=auth)
        assert result.status_code == 200 and 'QA Oak Roofing' in result.text
    assert client.get('/api/crm/leads/export?format=pdf', headers=auth).status_code == 400
    for filename, content in [('test.csv','name,city,country\nQA Elm,Austin,USA'),('test.json',json.dumps([{'name':'QA Pine','city':'Austin','country':'USA'}]))]:
        result = client.post('/api/crm/leads/import', headers=auth, files={'file':(filename,content.encode())})
        assert result.status_code == 200 and result.json()['added'] == 1, result.text
    assert client.request('DELETE','/api/crm/leads',headers=auth,json={'ids':[lead_id]}).status_code == 200
    assert client.get('/api/crm/leads?status=trash',headers=auth).json()['total'] == 1
    assert client.post('/api/crm/leads/recover',headers=auth,json={'ids':[lead_id]}).status_code == 200
    assert client.get('/api/crm/leads?status=trash',headers=auth).json()['total'] == 0
    assert client.request('DELETE','/api/crm/leads/permanent',headers=auth,json={'ids':[lead_id]}).status_code == 200
    assert client.get(f'/api/crm/leads/{lead_id}',headers=auth).status_code == 404


def test_campaign_generation_status_resume_and_recovery(setup):
    client, _ = setup
    auth = headers(1)
    response = client.post('/api/campaigns', headers=auth, json={
        'name':'QA synthetic workflow','country':'USA','cities':['Austin'],'industry':'roofing',
        'target_quantity':2,'min_quality_score':60,'website_filter':'no_website','discovery_channels':['google_maps','facebook'],
    })
    assert response.status_code == 200, response.text
    cid = response.json()['campaign_id']
    status = client.get(f'/api/campaigns/{cid}/status',headers=auth)
    assert status.status_code == 200 and status.json()['status'] == 'completed'
    assert status.json()['website_filter'] == 'no_website'
    assert [stage['key'] for stage in status.json()['stages']] == ['discovery', 'enrichment', 'ai_sdr']
    assert status.json()['stages'][-1]['label'] == 'No-Website Opportunity Scoring'
    leads = client.get(f'/api/crm/leads?campaign_id={cid}&website_filter=no_website',headers=auth).json()['leads']
    assert len(leads) == 2 and all(lead['data_mode']=='synthetic' for lead in leads)
    assert client.patch(f'/api/campaigns/{cid}/contact-options',headers=auth,json={'phone_enabled':True}).status_code == 200
    assert client.post(f'/api/campaigns/{cid}/resume',headers=auth).json()['remaining'] == 0
    assert client.get('/api/campaigns',headers=auth).status_code == 200
    assert client.request('DELETE','/api/campaigns',headers=auth,json={'ids':[cid]}).status_code == 200
    assert client.get('/api/crm/leads?status=trash',headers=auth).json()['total'] == 2
    assert client.post('/api/campaigns/recover',headers=auth,json={'ids':[cid]}).status_code == 200
    assert client.request('DELETE','/api/campaigns/permanent',headers=auth,json={'ids':[cid]}).status_code == 200
    assert client.get(f'/api/campaigns/{cid}/status',headers=auth).status_code == 404


def test_provider_status_distinguishes_configuration_credit_failure_and_live_mode(setup, monkeypatch):
    client, factory = setup
    monkeypatch.setenv('DISCOVERY_MODE','live')
    monkeypatch.setenv('SERPER_API_KEY','test-key')
    with factory() as db:
        db.add(ProviderHealth(provider_name='serper',state='exhausted',message='Replenish credits',last_http_status=400))
        db.commit()
    result = client.get('/api/providers/status',headers=headers(1))
    assert result.status_code == 200
    providers = result.json()['providers']
    serper = next(p for p in providers if p['id']=='serper')
    assert serper['state'] == 'exhausted' and serper['action_required']
    assert provider_failure(400, {'message':'Not enough credits'})[0] == 'exhausted'
    assert provider_failure(400, {'errors':[{'user_id':'Sorry, you ran out of credits, please order more credits'}]})[0] == 'exhausted'
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    assert GroqProvider().api_key == 'test-key'
    monkeypatch.setenv('DISCOVERY_MODE','mock')
    assert GroqProvider().api_key == ''


def test_invalid_json_import_rows_are_client_errors(setup):
    client, _ = setup
    response = client.post('/api/crm/leads/import',headers=headers(1),files={'file':('bad.json',b'[null, "bad"]')})
    assert response.status_code == 400, response.text


def test_listing_phone_and_sources_survive_api_csv_export(setup):
    client, factory = setup
    auth=headers(1)
    result=client.post('/api/crm/leads',headers=auth,json={'name':'Phone only','primary_phone':'+1 512 555 0188'})
    lead_id=result.json()['lead_id']
    with factory() as db:
        db.info['owner_id']=1
        db.add(BusinessSource(business_id=lead_id,source='facebook',source_url='https://facebook.com/phone-only'))
        db.commit()
    response=client.get(f'/api/crm/leads/export?ids={lead_id}',headers=auth)
    assert response.status_code==200
    assert '+1 512 555 0188' in response.text
    assert 'facebook: https://facebook.com/phone-only' in response.text


def test_dashboard_uses_real_qualified_counts_per_campaign_and_excludes_trash(setup):
    client, factory = setup
    auth = headers(1)
    empty = client.get('/api/dashboard',headers=auth).json()
    assert all(day['value'] == 0 for day in empty['chart_data'])
    with factory() as db:
        db.info['owner_id']=1
        first=Campaign(name='Delivered',target_quantity=10)
        second=Campaign(name='Empty',target_quantity=10)
        db.add_all([first,second]); db.flush()
        qualified=Business(name='Qualified',campaign_id=first.id,status='qualified')
        unqualified=Business(name='Needs review',campaign_id=second.id,status='needs_research')
        db.add_all([qualified,unqualified]); db.flush()
        db.add_all([Opportunity(business_id=qualified.id),Opportunity(business_id=unqualified.id)])
        db.commit()
        lead_id=qualified.id
    result=client.get('/api/dashboard',headers=auth).json()
    assert result['stats']['qualified_opportunities']==1
    assert sum(day['value'] for day in result['chart_data'])==1
    assert {c['name']:c['progress'] for c in result['recent_campaigns']}=={'Delivered':1,'Empty':0}
    assert client.request('DELETE','/api/crm/leads',headers=auth,json={'ids':[lead_id]}).status_code==200
    result=client.get('/api/dashboard',headers=auth).json()
    assert result['stats']['qualified_opportunities']==0
    assert sum(day['value'] for day in result['chart_data'])==0


def test_optional_contact_outages_preserve_other_results(monkeypatch):
    monkeypatch.setenv('DISCOVERY_MODE','live')
    monkeypatch.setattr(lookup,'report_provider_state',lambda *args: None)
    monkeypatch.setattr(lookup.SnovioProvider,'find_emails',AsyncMock(side_effect=TimeoutError()))
    search=AsyncMock(return_value=[{'email':'public@example.com','phone':'unexpected'}])
    monkeypatch.setattr(lookup.SerperSearchProvider,'search_decision_makers',search)
    business=Business(name='QA',website_url='https://example.com')
    contacts=asyncio.run(lookup.lookup_optional_contacts(business,True,False))
    assert contacts==[{'email':'public@example.com','phone':None,'mobile':None}]
    monkeypatch.setattr(lookup.SnovioProvider,'find_emails',AsyncMock(return_value=[{'email':'retained@example.com'}]))
    search.side_effect=TimeoutError()
    assert asyncio.run(lookup.lookup_optional_contacts(business,True,True))==[{'email':'retained@example.com'}]


def test_failed_live_campaign_exposes_credit_failure_without_fake_leads(setup,monkeypatch):
    client,_=setup
    monkeypatch.setenv('DISCOVERY_MODE','live')
    class EmptyCreditsProvider:
        channel_errors={'Austin: google_maps':'Provider credits exhausted.'}
        async def discover(self,**kwargs):
            raise RuntimeError('Provider credits exhausted. Replenish the account and retry.')
    monkeypatch.setattr(worker,'get_discovery_provider',lambda *args: EmptyCreditsProvider())
    def dispatch(task,cid):
        task(cid)
        return type('Task',(),{'id':'qa'})()
    monkeypatch.setattr(main,'_dispatch_task',dispatch)
    result=client.post('/api/campaigns',headers=headers(1),json={'name':'Credit failure','country':'USA','cities':['Austin'],'industry':'roofing','target_quantity':1,'min_quality_score':60,'discovery_channels':['google_maps']})
    assert result.status_code==200,result.text
    cid=result.json()['campaign_id']
    status=client.get(f'/api/campaigns/{cid}/status',headers=headers(1)).json()
    assert status['status']=='failed'
    assert 'credits exhausted' in status['summary']
    assert status['channel_errors']
    assert status['stats']['discovered']==0
    assert status['stages'][0]['status']=='failed'


def test_status_update_keeps_pending_ai_analysis_visible_to_its_owner(setup):
    client,factory=setup
    with factory() as db:
        db.info['owner_id']=1
        business=Business(name='Research owner',status='researching')
        db.add(business); db.flush()
        opportunity=Opportunity(business_id=business.id)
        db.add(opportunity); db.flush()
        analysis=AIAnalysis(business_id=business.id,opportunity_id=opportunity.id,parsed_output={'confidence':'high'})
        db.add(analysis)
        worker._set_business_status(db,business,'qualified')
        db.commit()
        assert analysis.owner_id==1
        bid=business.id
    result=client.get(f'/api/leads/{bid}',headers=headers(1))
    assert result.status_code==200,result.text
    assert result.json()['ai_transparency']=={'confidence':'high'}
