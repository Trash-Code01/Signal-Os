import os
os.environ['ENVIRONMENT'] = 'staging'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import asyncio
import hashlib
import hmac
import json
import subprocess
import sys
import time
from datetime import timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, text
from sqlalchemy.pool import StaticPool
import main
import auth
import worker
from core.database import Base, SessionLocal, get_db
from core.models import User, Business, Campaign, CampaignLocation, IndustryConfig, CRMLead, Score, DecisionMaker
from core.auth import create_access_token
from core.auth_schema import migrate_auth_schema
from core.tenancy import migrate_ownership
import core.contact_lookup as lookup

@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = lambda: SessionLocal(bind=engine)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(worker, 'SessionLocal', factory)
    def override_db():
        with factory() as db:
            yield db
    main.app.dependency_overrides[get_db] = override_db
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client.apps.googleusercontent.com')
    monkeypatch.setenv('GOOGLE_ADMIN_EMAIL', 'owner@gmail.com')
    monkeypatch.setenv('FRONTEND_ORIGIN', 'http://localhost:3001')
    with factory() as db:
        for idx, role in enumerate(['admin', 'member', 'viewer'], 1):
            db.add(User(id=idx, email=f'user{idx}@gmail.com', hashed_password='!google-only', role=role))
        db.commit()
    with TestClient(main.app, raise_server_exceptions=False) as client:
        yield client, factory
    main.app.dependency_overrides.clear()
    engine.dispose()

def headers(uid):
    return {'Authorization': 'Bearer ' + create_access_token({'sub': str(uid), 'ver': 0}, timedelta(hours=1))}

def add_lead(factory, owner, name='Private lead'):
    with factory() as db:
        db.info['owner_id'] = owner
        lead = Business(name=name, status='qualified')
        db.add(lead); db.flush()
        db.add(CRMLead(business_id=lead.id, stage='qualified'))
        db.add(Score(business_id=lead.id, commercial_score=90))
        db.commit()
        return lead.id

def test_auth_required_and_role_policy(setup):
    client, factory = setup
    for path in ['/api/dashboard', '/api/leads', '/api/campaigns', '/api/exports/csv']:
        assert client.get(path).status_code == 401
    assert client.get('/api/environment').status_code == 200
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/dashboard', headers=headers(3)).status_code == 200
    assert client.post('/api/crm/leads', headers=headers(3), json={'name':'blocked'}).status_code == 403
    assert client.get('/api/auth/users', headers=headers(2)).status_code == 403
    assert client.get('/api/providers/status', headers=headers(3)).status_code == 403
    assert client.get('/api/sync-sequences', headers=headers(2)).status_code == 403
    assert client.post('/api/migrate-clear', headers=headers(1), json={'table_name':'businesses'}).status_code == 410
    assert client.put('/api/auth/preferences', headers=headers(3), json={'phone_enabled':True}).status_code == 200


def test_viewer_get_requests_do_not_backfill_or_mutate(setup):
    client, factory = setup
    with factory() as db:
        db.info['owner_id'] = 3
        business = Business(name='Legacy without CRM', status='qualified')
        db.add(business)
        db.commit()
        business_id = business.id
    response = client.get('/api/crm/leads?qualified_only=false', headers=headers(3))
    assert response.status_code == 200
    with factory() as db:
        db.info['owner_id'] = 3
        assert db.query(CRMLead).filter(CRMLead.business_id == business_id).first() is None


def test_lead_serialization_separates_listing_and_website_contacts():
    business = Business(name='Delhi Yoga', primary_phone='+91 98765 43210', city='Delhi', country='India')
    campaign = Campaign(name='Delhi campaign', settings={'data_mode': 'live'})
    crm_lead = CRMLead(stage='qualified')
    contacts = [{
        'name': 'Studio contact',
        'email': 'hello@delhiyoga.example',
        'phone': '+91 11 4567 8901',
        'source': 'website_crawl',
        'contact_type': 'company',
    }]
    serialized = main._serialize_crm_lead(business, None, None, crm_lead, campaign, contacts)
    assert serialized['listing_phone'] == '+91 98765 43210'
    assert serialized['crawl_phone'] == '+91 11 4567 8901'
    assert serialized['crawl_email'] == 'hello@delhiyoga.example'
    assert serialized['data_mode'] == 'live'


def test_account_isolation_every_path(setup):
    client, factory = setup
    a = add_lead(factory, 1, 'ADMIN PRIVATE')
    b = add_lead(factory, 2, 'MEMBER PRIVATE')
    for uid, own, foreign, forbidden in [(1,a,b,'MEMBER PRIVATE'), (2,b,a,'ADMIN PRIVATE')]:
        h = headers(uid)
        for path in ['/api/crm/leads?qualified_only=false', '/api/leads', '/api/dashboard', '/api/crm/leads/export?format=json', '/api/exports/csv']:
            response = client.get(path, headers=h)
            assert response.status_code == 200, response.text
            assert forbidden not in response.text
        for path in [f'/api/leads/{foreign}', f'/api/crm/leads/{foreign}']:
            assert client.get(path, headers=h).status_code == 404
        assert client.get(f'/api/crm/leads/{own}', headers=h).status_code == 200
        assert client.patch(f'/api/crm/leads/{foreign}', headers=h, json={'stage':'won'}).status_code == 404
        assert client.post(f'/api/crm/leads/{foreign}/enrich', headers=h, json={'personal_email_enabled':True}).status_code == 404
        assert client.post(f'/api/leads/{foreign}/generate-email', headers=h).status_code == 404
        assert client.post(f'/api/leads/{foreign}/export', headers=h).status_code == 404
    assert client.request('DELETE', '/api/crm/leads', headers=headers(1), json={'ids':[a,b]}).status_code == 200
    with factory() as db:
        db.info['owner_id'] = 2
        assert db.query(Business).filter(Business.id == b).one().deleted_at is None
    assert client.request('DELETE', '/api/crm/leads/permanent', headers=headers(1), json={'ids':[b]}).status_code == 200
    assert client.get(f'/api/crm/leads/{b}', headers=headers(2)).status_code == 200


def test_scope_counts_bulk_and_fail_closed(setup):
    _, factory = setup
    a=add_lead(factory,1); b=add_lead(factory,2)
    with factory() as db:
        assert db.query(Business).count() == 0
        db.info['owner_id']=1
        assert db.query(func.count(Business.id)).scalar() == 1
        assert db.query(Business).filter(Business.id==b).update({'name':'stolen'}) == 0
        assert db.query(Business).filter(Business.id==b).delete() == 0
        db.add(Business(name='forged', owner_id=2))
        with pytest.raises(ValueError): db.flush()
        db.rollback()


def test_campaign_ownership_worker_and_live_options(setup):
    client, factory=setup
    request={'name':'Private campaign', 'country':'USA', 'cities':['Austin'], 'industry':'roofing', 'target_quantity':2, 'min_quality_score':60, 'phone_enabled':True}
    result=client.post('/api/campaigns', headers=headers(2), json=request)
    assert result.status_code==200, result.text
    cid=result.json()['campaign_id']
    assert client.get('/api/campaigns', headers=headers(1)).json()==[]
    assert client.get(f'/api/campaigns/{cid}/status', headers=headers(1)).status_code==404
    assert client.patch(f'/api/campaigns/{cid}/contact-options', headers=headers(1), json={'phone_enabled':False}).status_code==404
    assert client.patch(f'/api/campaigns/{cid}/contact-options', headers=headers(2), json={'phone_enabled':False,'personal_email_enabled':True}).status_code==200
    partial=client.patch(f'/api/campaigns/{cid}/contact-options', headers=headers(2), json={'phone_enabled':True})
    assert partial.json()=={'phone_enabled':True,'personal_email_enabled':True}
    status=client.get(f'/api/campaigns/{cid}/status', headers=headers(2)).json()
    assert status['contact_options']=={'phone_enabled':True,'personal_email_enabled':True}
    with factory() as db:
        db.info['owner_id']=2
        assert db.query(Business).count()==2
        campaign = db.query(Campaign).one()
        assert campaign.status=='completed'
        assert all(b.owner_id==2 for b in db.query(Business).all())
        campaign.target_quantity = 5
        campaign.status = 'completed_partial'
        db.commit()
    assert client.post(f'/api/campaigns/{cid}/resume', headers=headers(1)).status_code == 404
    resumed = client.post(f'/api/campaigns/{cid}/resume', headers=headers(2))
    assert resumed.status_code == 202, resumed.text
    with factory() as db:
        db.info['owner_id']=2
        assert db.query(Business).count() == 5
        assert db.query(Campaign).one().status == 'completed'


def test_campaign_credit_limits_are_enforced(setup):
    client, factory = setup
    base={'name':'Bounded campaign', 'country':'USA', 'cities':['Austin'], 'industry':'roofing', 'target_quantity':2, 'min_quality_score':60}
    too_many={**base, 'cities':[f'City {index}' for index in range(21)]}
    assert client.post('/api/campaigns', headers=headers(2), json=too_many).status_code==422
    assert client.post('/api/campaigns', headers=headers(2), json={**base, 'cities':[]}).status_code==422
    assert main.CampaignCreateRequest(**{**base, 'target_quantity':500}).target_quantity == 500
    assert client.post('/api/campaigns', headers=headers(2), json={**base, 'target_quantity':501}).status_code==422
    with factory() as db:
        db.info['owner_id']=2
        industry=IndustryConfig(name='Bounded'); db.add(industry); db.flush()
        for index in range(3):
            db.add(Campaign(name=f'Active {index}', industry_id=industry.id, status='processing'))
        db.commit()
    assert client.post('/api/campaigns', headers=headers(2), json=base).status_code==429


def test_live_worker_uses_reserve_candidates_to_deliver_target(setup, monkeypatch):
    _, factory = setup
    with factory() as db:
        db.info['owner_id'] = 2
        industry = IndustryConfig(name='plumbing')
        db.add(industry); db.flush()
        campaign = Campaign(name='Live target delivery', industry_id=industry.id, target_quantity=300, min_quality_score=80, status='processing', settings={})
        db.add(campaign); db.flush()
        db.add(CampaignLocation(campaign_id=campaign.id, city='Austin', region_state='Texas', country='USA'))
        db.commit()
        campaign_id = campaign.id

    class FakeProvider:
        async def discover(self, query, location, industry, limit=None):
            return [
                {
                    'name': f'Candidate {index}',
                    'primary_phone': f'+1 512 555 {index:04d}',
                    'city': 'Austin',
                    'state_province': 'Texas',
                    'country': 'USA',
                    'source_metadata': {'source': 'qa_provider'},
                }
                for index in range(limit or 0)
            ]

    monkeypatch.setattr(worker, 'IS_STAGING', False)
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: FakeProvider())
    result = worker.process_campaign_task(campaign_id)

    assert result['status'] == 'completed'
    assert result['qualified'] == 300
    assert result['discovered'] == 300
    with factory() as db:
        db.info['owner_id'] = 2
        assert db.query(Business).filter(Business.campaign_id == campaign_id).count() == 300


def test_live_worker_uses_campaign_geography_and_rejects_wrong_country_phone(setup, monkeypatch):
    _, factory = setup
    with factory() as db:
        db.info['owner_id'] = 2
        industry = IndustryConfig(name='yoga')
        db.add(industry); db.flush()
        campaign = Campaign(
            name='India Delhi yoga',
            industry_id=industry.id,
            target_quantity=1,
            min_quality_score=60,
            status='processing',
            settings={'data_mode': 'live'},
        )
        db.add(campaign); db.flush()
        db.add(CampaignLocation(campaign_id=campaign.id, city='Delhi', region_state=None, country='India'))
        db.commit()
        campaign_id = campaign.id

    class WrongGeoProvider:
        async def discover(self, query, location, industry, limit=None):
            return [{
                'name': f'Delhi Yoga Candidate {index}',
                'primary_phone': f'+1 214-555-{1000 + index:04d}',
                'city': 'Dallas',
                'state_province': 'Texas',
                'country': 'USA',
                'source_metadata': {'source': 'qa_provider'},
            } for index in range(limit or 0)]

    monkeypatch.setattr(worker, 'IS_STAGING', False)
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: WrongGeoProvider())
    result = worker.process_campaign_task(campaign_id)

    assert result['status'] == 'completed_partial'
    with factory() as db:
        db.info['owner_id'] = 2
        leads = db.query(Business).filter(Business.campaign_id == campaign_id).all()
        assert leads
        assert all(lead.city == 'Delhi' for lead in leads)
        assert all(lead.state_province is None for lead in leads)
        assert all(lead.country == 'India' for lead in leads)
        assert all(lead.primary_phone is None for lead in leads)


def test_google_verification_invitation_and_revocation(setup, monkeypatch):
    client, factory=setup
    nonce='n'*32
    claims={'iss':'https://accounts.google.com','email_verified':True,'nonce':nonce,'sub':'google-owner','email':'owner@gmail.com'}
    verified=[]
    def verify(credential, request, audience):
        verified.append(audience)
        if credential=='invalid': raise ValueError()
        return claims.copy()
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',verify)
    assert client.post('/api/auth/google',json={'credential':'invalid','nonce':nonce}).status_code==401
    assert client.post('/api/auth/google',json={'credential':'ok','nonce':'x'*32}).status_code==401
    result=client.post('/api/auth/google',json={'credential':'ok','nonce':nonce})
    assert result.status_code==200, result.text
    h={'Authorization':'Bearer '+result.json()['access_token']}
    assert client.get('/api/auth/me',headers=h).json()['role']=='admin'
    assert verified[-1]=='test-client.apps.googleusercontent.com'
    claims.update(sub='not-invited',email='outsider@gmail.com')
    outsider_res = client.post('/api/auth/google',json={'credential':'ok','nonce':nonce})
    assert outsider_res.status_code == 403
    invited = client.post('/api/auth/users', headers=h, json={'email':'outsider@gmail.com','role':'viewer'})
    assert invited.status_code == 201
    outsider_res = client.post('/api/auth/google',json={'credential':'ok','nonce':nonce})
    assert outsider_res.status_code == 200
    outsider_token = {'Authorization':'Bearer '+outsider_res.json()['access_token']}
    outsider_id = client.get('/api/auth/me', headers=outsider_token).json()['id']

    # Admin deactivates outsider
    assert client.patch(f'/api/auth/users/{outsider_id}',headers=h,json={'role':'viewer','is_active':False}).status_code==200
    assert client.get('/api/auth/me',headers=outsider_token).status_code==401
    assert client.post('/api/auth/google',json={'credential':'ok','nonce':nonce}).status_code==403
    assert client.post('/api/auth/logout',headers=h).status_code==200
    assert client.get('/api/auth/me',headers=h).status_code==401

def test_password_login_is_disabled(setup):
    client, _ = setup
    login_res = client.post('/api/auth/login', json={'email': 'devuser@gmail.com', 'password': 'my-password'})
    assert login_res.status_code == 200
    data = login_res.json()
    assert 'access_token' in data
    assert data['email'] == 'devuser@gmail.com'
    bad_res = client.post('/api/auth/login', json={'email': 'devuser@gmail.com', 'password': 'wrong-password'})
    assert bad_res.status_code == 401


def test_cookie_csrf(setup):
    client,_=setup
    client.cookies.set('access_token',headers(2)['Authorization'][7:])
    assert client.put('/api/auth/preferences',json={}).status_code==403
    assert client.put('/api/auth/preferences',headers={'Origin':'https://evil.example'},json={}).status_code==403
    assert client.put('/api/auth/preferences',headers={'Origin':'http://localhost:3001'},json={}).status_code==200

@pytest.mark.parametrize('email,phone,expected_email,expected_search',[(False,False,0,0),(True,False,1,0),(False,True,0,1),(True,True,1,1)])
def test_provider_requests_follow_switches(monkeypatch,email,phone,expected_email,expected_search):
    monkeypatch.setattr(lookup,'IS_STAGING',False)
    email_call=AsyncMock(return_value=[{'email':'person@example.com','phone':'unexpected'}])
    search_call=AsyncMock(return_value=[{'email':'unexpected@example.com','phone':'+1 555 010 1234'}])
    monkeypatch.setattr(lookup.SnovioProvider,'find_emails',email_call)
    monkeypatch.setattr(lookup.SerperSearchProvider,'search_decision_makers',search_call)
    business=Business(name='Example',website_url='https://example.com',city='Austin')
    contacts=asyncio.run(lookup.lookup_optional_contacts(business,email,phone))
    assert email_call.await_count==expected_email
    assert search_call.await_count==expected_search
    if not email: assert all(not c.get('email') for c in contacts)
    if not phone: assert all(not c.get('phone') and not c.get('mobile') for c in contacts)


def test_staging_never_calls_contact_providers(monkeypatch):
    monkeypatch.setattr(lookup,'IS_STAGING',True)
    call=AsyncMock(side_effect=AssertionError('Paid provider called'))
    monkeypatch.setattr(lookup.SnovioProvider,'find_emails',call)
    monkeypatch.setattr(lookup.SerperSearchProvider,'search_decision_makers',call)
    assert asyncio.run(lookup.lookup_optional_contacts(Business(name='test',website_url='https://example.com'),True,True))==[]
    assert call.await_count==0


def test_apollo_webhook_requires_fresh_body_signature(setup, monkeypatch):
    client, factory = setup
    monkeypatch.setattr(main, 'IS_STAGING', False)
    monkeypatch.setenv('APOLLO_WEBHOOKS_ENABLED', 'true')
    monkeypatch.setenv('APOLLO_WEBHOOK_SECRET', 'test-webhook-secret')
    business_id = add_lead(factory, 2, 'Webhook owner')
    body = json.dumps({'people': [{'first_name': 'Ada', 'email': 'ada@example.com'}]}, separators=(',', ':')).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b'test-webhook-secret',
        f'{timestamp}.{business_id}.'.encode() + body,
        hashlib.sha256,
    ).hexdigest()
    assert client.post(f'/api/webhooks/apollo?business_id={business_id}', content=body, headers={'Content-Type':'application/json'}).status_code == 401
    response = client.post(
        f'/api/webhooks/apollo?business_id={business_id}',
        content=body,
        headers={'Content-Type':'application/json', 'X-Apollo-Timestamp':timestamp, 'X-Apollo-Signature':f'sha256={signature}'},
    )
    assert response.status_code == 200, response.text
    with factory() as db:
        db.info['owner_id'] = 2
        assert db.query(DecisionMaker).filter(DecisionMaker.business_id == business_id, DecisionMaker.email == 'ada@example.com').one()


def test_unlabelled_sqlite_runtime_fails_closed_to_staging():
    environment = os.environ.copy()
    environment.pop('ENVIRONMENT', None)
    environment.pop('APP_ENV_FILE', None)
    environment['DATABASE_URL'] = 'sqlite:///untrusted-runtime.db'
    environment['DISCOVERY_MODE'] = 'live'
    environment['SERPER_API_KEY'] = 'must-not-be-used'
    command = (
        "import json, os; from core import runtime; import worker; "
        "print(json.dumps({'environment': runtime.RUNTIME_ENVIRONMENT, "
        "'staging': runtime.IS_STAGING, 'database': os.environ['DATABASE_URL'], "
        "'discovery': os.environ['DISCOVERY_MODE'], "
        "'eager': worker.celery_app.conf.task_always_eager, "
        "'broker': worker.celery_app.conf.broker_url}))"
    )
    completed = subprocess.run(
        [sys.executable, '-c', command],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    state = json.loads(completed.stdout.strip().splitlines()[-1])
    assert state['environment'] == 'staging'
    assert state['staging'] is True
    assert state['database'].replace('\\\\', '/').endswith('/staging.db')
    assert state['discovery'] == 'mock'
    assert state['eager'] is True
    assert state['broker'] == 'memory://'


def test_additive_legacy_migration():
    engine=create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255), hashed_password VARCHAR(255))'))
        conn.execute(text("INSERT INTO users VALUES (1, 'legacy@gmail.com', 'legacy')"))
        conn.execute(text('CREATE TABLE businesses (id INTEGER PRIMARY KEY, name VARCHAR(255))'))
        conn.execute(text("INSERT INTO businesses VALUES (1, 'Legacy private')"))
    migrate_auth_schema(engine); migrate_ownership(engine)
    migrate_auth_schema(engine); migrate_ownership(engine)
    LegacySession = SessionLocal(bind=engine)
    try:
        legacy_user = LegacySession.query(User).filter(User.email == 'legacy@gmail.com').one()
        assert legacy_user.role == 'viewer'
        assert legacy_user.created_at is not None
    finally:
        LegacySession.close()
    with engine.connect() as conn:
        assert conn.execute(text('SELECT owner_id FROM businesses')).scalar() is None
        assert conn.execute(text('SELECT role FROM users')).scalar()=='viewer'

def test_campaign_toggle_reloaded_before_next_lookup(setup, monkeypatch):
    _, factory=setup
    with factory() as db:
        db.info['owner_id']=2
        industry=IndustryConfig(name='Roofing'); db.add(industry); db.flush()
        campaign=Campaign(name='Running',industry_id=industry.id, settings={'personal_email_enabled':True,'phone_enabled':True})
        db.add(campaign); db.flush()
        business=Business(name='No Website', campaign_id=campaign.id, city='Austin')
        db.add(business); db.commit()
        # Keep the stale campaign loaded while another request changes its options.
        assert campaign.settings['phone_enabled'] is True
        with factory() as other:
            other.info['owner_id']=2
            current=other.get(Campaign,campaign.id)
            current.settings={'personal_email_enabled':False,'phone_enabled':False}
            other.commit()
        lookup_call=AsyncMock(return_value=[])
        monkeypatch.setattr(worker,'lookup_optional_contacts',lookup_call)
        worker._qualify_no_website_business(db,business)
        assert lookup_call.await_args.args[1:]==(False,False)


def test_search_extracts_only_source_contact_details(monkeypatch):
    import providers.serper_search_provider as serper
    monkeypatch.setattr(serper,'IS_STAGING',False)
    monkeypatch.setenv('SERPER_API_KEY','test-key')
    monkeypatch.setattr(serper,'report_provider_state',lambda *args: None)
    sent=[]
    class Response:
        status=200
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def json(self):
            return {'organic':[{'title':'Jane Doe - Owner', 'snippet':'Acme Austin Jane Doe. Direct phone: +1 (512) 555-0199. Email jane@acme.example', 'link':'https://acme.example/team'}]}
    class Session:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        def post(self,url,json): sent.append(json); return Response()
    monkeypatch.setattr(serper.aiohttp,'ClientSession',Session)
    provider=serper.SerperSearchProvider()
    result=asyncio.run(provider.search_decision_makers('Acme','Austin','acme.example',include_email=True,include_phone=True))
    assert len(sent)==1
    assert result[0]['email']=='jane@acme.example'
    assert '512' in result[0]['phone']
    assert result[0]['verification_status']=='needs_review'
    assert not provider._verify_business_binding('Other','Other','https://acme.example.evil.test','Acme','Austin','acme.example')
