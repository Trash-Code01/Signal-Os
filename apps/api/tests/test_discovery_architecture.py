import asyncio
import os
from unittest.mock import AsyncMock

os.environ['ENVIRONMENT'] = 'staging'
os.environ['DISCOVERY_MODE'] = 'mock'

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import main
import worker
from core.database import Base, SessionLocal
from core.discovery import no_website_score
from core.deduplication import DeduplicationEngine, find_existing_business
from core.models import Business, BusinessSource, Campaign, CampaignLocation, CRMLead, IndustryConfig, Score, User, WebsiteEvidence
from providers.multichannel_discovery import MultiChannelDiscoveryProvider, parse_candidate
from providers.serper_discovery_provider import SerperDiscoveryProvider


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def create_session():
        session = SessionLocal(bind=engine)
        session.info['system_access'] = True
        return session
    with create_session() as db:
        db.add(User(id=1, email='test@example.com', role='admin'))
        db.commit()
    monkeypatch.setattr(worker, 'SessionLocal', create_session)
    monkeypatch.setattr(worker, 'IS_STAGING', False)
    monkeypatch.setattr(worker, 'lookup_optional_contacts', AsyncMock(return_value=[]))
    yield create_session
    engine.dispose()


def campaign(db, target=1, threshold=60, website_filter='all'):
    industry = IndustryConfig(name='Roofing', owner_id=1)
    db.add(industry); db.flush()
    record = Campaign(name='Discovery test', industry_id=industry.id, target_quantity=target, min_quality_score=threshold,
                      owner_id=1, settings={'website_filter': website_filter})
    db.add(record); db.flush()
    db.add(CampaignLocation(campaign_id=record.id, city='Austin', country='USA', owner_id=1))
    db.commit()
    return record.id


def test_campaign_options_reject_invalid_channels_and_preserve_zero_score():
    payload = dict(name='Campaign', country='USA', cities=['Austin', 'Austin'], industry='roofing', target_quantity=10, min_quality_score=0)
    parsed = main.CampaignCreateRequest(**payload, discovery_channels=['facebook', 'facebook'], website_filter='no_website')
    assert parsed.discovery_channels == ['facebook']
    assert parsed.cities == ['Austin']
    assert parsed.min_quality_score == 0
    for channels in ([], ['invented']):
        with pytest.raises(ValidationError):
            main.CampaignCreateRequest(**payload, discovery_channels=channels)


def test_missing_live_key_never_returns_mock(monkeypatch):
    monkeypatch.delenv('SERPER_API_KEY', raising=False)
    monkeypatch.setattr('providers.serper_discovery_provider.report_provider_state', lambda *args: None)
    with pytest.raises(RuntimeError, match='requires SERPER_API_KEY'):
        asyncio.run(SerperDiscoveryProvider().discover('roofing', 'Austin, USA', 'roofing', 2))


def test_social_candidates_require_location_and_profile_source():
    item = {'title': 'Oak Roofing | Facebook', 'snippet': 'Roofing in Austin. Call: +1 512 555 0199', 'link': 'https://facebook.com/oakroofing'}
    parsed = parse_candidate(item, 'facebook', 'Austin', None, 'USA')
    assert parsed['website_url'] is None
    assert parsed['website_status'] == 'unknown'
    assert parsed['primary_phone']
    assert parse_candidate(item, 'facebook', 'Dallas', None, 'USA') is None
    assert parse_candidate({**item, 'link': 'https://facebook.com/oak/posts/123'}, 'facebook', 'Austin', None, 'USA') is None
    assert parse_candidate({**item, 'link': 'https://notfacebook.com/oak'}, 'facebook', 'Austin', None, 'USA') is None


def test_lookup_failure_is_unknown_not_no_website():
    class Response:
        status = 429
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    class Session:
        def post(self, *args, **kwargs): return Response()
    business = {'name': 'Oak', 'city': 'Austin'}
    assert asyncio.run(SerperDiscoveryProvider()._fetch_website(Session(), business)) is None
    assert business['website_status'] == 'unknown'


def test_selected_channels_only_and_partial_failure(monkeypatch):
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')
    provider = MultiChannelDiscoveryProvider(['facebook', 'instagram'])
    calls = []
    async def search(channel, *args):
        calls.append(channel)
        if channel == 'instagram': raise RuntimeError('Rate limited')
        return [{'name': 'Oak', 'city': 'Austin', 'country': 'USA', 'source_metadata': {'channel': channel}}]
    monkeypatch.setattr(provider, '_search_channel', search)
    results = asyncio.run(provider.discover('roofing', 'Austin, USA', 'roofing', 10))
    assert calls == ['facebook', 'instagram']
    assert len(results) == 1
    assert provider.channel_errors == {'Austin, USA: instagram': 'Rate limited'}


def test_cross_channel_deduplication_retains_sources_and_website():
    records = [dict(name='Oak', city='Austin', country='USA', address='1 Street', website_status='no_website', source_metadata={'channel':'google_maps'}, source_url='https://google.com/maps/1'),
               dict(name='Oak', city='Austin', country='USA', website_url='https://oak.example', source_metadata={'channel':'google_search'}, source_url='https://oak.example')]
    merged = DeduplicationEngine().deduplicate(records)
    assert len(merged) == 1
    assert len(merged[0]['sources']) == 2
    assert merged[0]['website_status'] == 'has_website'


def test_no_website_score_needs_evidence_and_does_not_invent_intent():
    strong = no_website_score(phone=True, contact=True, reviews=90, rating=4.8, checked=True)
    weak = no_website_score(phone=False, contact=False, reviews=0, rating=0, checked=False)
    assert strong['commercial_score'] > weak['commercial_score']
    assert strong['commercial_score'] < 100
    assert strong['buying_intent'] == weak['buying_intent'] == 0


def test_bridge_candidates_merge_all_duplicate_groups():
    records = [dict(name='Oak', website_url='https://oak.example'),
               dict(name='Oak LLC', primary_phone='+1 512 555 0199'),
               dict(name='Oak Roof', website_url='https://oak.example', primary_phone='+1 512 555 0199')]
    assert len(DeduplicationEngine().deduplicate(records)) == 1


@pytest.mark.parametrize('checked,threshold,expected', [(True, 90, 'below_quality_threshold'), (True, 0, 'qualified'), (False, 0, 'needs_research')])
def test_no_website_qualification_respects_threshold(factory, checked, threshold, expected):
    with factory() as db:
        cid = campaign(db, threshold=threshold)
        business = Business(name='Oak', campaign_id=cid, owner_id=1, primary_phone='+1 512 555 0199')
        db.add(business); db.flush()
        if checked:
            db.add(WebsiteEvidence(business_id=business.id, evidence_type='website_presence', observed_value='no_website', owner_id=1))
        db.commit()
        worker._qualify_no_website_business(db, business)
        assert business.status == expected
        assert db.query(Score).filter_by(business_id=business.id).one().commercial_score < 100


def test_crm_rank_filters_sources_and_listing_phone(factory):
    with factory() as db:
        for name, score, site, channel in [('Low', 55, None, 'facebook'), ('Best', 95, None, 'google_maps'), ('Website', 80, 'https://site.example', 'google_search')]:
            business = Business(name=name, owner_id=1, website_url=site, primary_phone='+1 512 555 0199', country='USA')
            db.add(business); db.flush()
            db.add_all([CRMLead(business_id=business.id, owner_id=1), Score(business_id=business.id, commercial_score=score, owner_id=1), BusinessSource(business_id=business.id, source=channel, owner_id=1)])
            if not site: db.add(WebsiteEvidence(business_id=business.id, evidence_type='website_presence', observed_value='no_website', owner_id=1))
        db.commit()
        result = main._get_crm_leads(db, website_filter='no_website', has_contact=True, page_size=1)
        assert result['total'] == 2
        assert result['leads'][0]['name'] == 'Best'
        assert result['leads'][0]['website_status'] == 'no_website'
        assert main._get_crm_leads(db, channel='facebook')['total'] == 1
        assert main._get_crm_leads(db, has_contact=False)['total'] == 0


def test_dedupe_does_not_confuse_domain_substrings_or_phone_suffixes(factory):
    with factory() as db:
        db.add(Business(name='Other', owner_id=1, website_url='https://notacme.com', primary_phone='+1 212 555 0199'))
        db.commit()
        assert find_existing_business(db, {'website_url':'https://acme.com'}) is None
        assert find_existing_business(db, {'primary_phone':'+1 512 555 0199'}) is None


def test_worker_preserves_website_score_and_resume_target(factory, monkeypatch):
    with factory() as db: cid = campaign(db, threshold=0)
    provider = type('Provider', (), {'discover': AsyncMock(return_value=[{'name':'Oak', 'website_url':'https://oak.example', 'primary_phone':'+1 512 555 0199', 'city':'Austin', 'country':'USA'}])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    audit = {'is_live':True, 'pages_checked':['https://oak.example'], 'evidence':[], 'emails':[], 'mobile_responsive':False, 'booking_detected':False}
    monkeypatch.setattr(worker.WebsiteIntelligenceEngine, 'audit_website', AsyncMock(return_value=audit))
    monkeypatch.setattr(worker.GroqProvider, 'analyze', AsyncMock(return_value=None))
    result = worker.process_campaign_task(cid)
    assert result['status'] == 'completed', result
    with factory() as db:
        assert db.query(Score).count() == 1
        assert db.query(Score).one().commercial_score > 0
    result = worker.process_campaign_task(cid)
    assert result['qualified'] == 1
    assert provider.discover.await_count == 1


def test_resume_can_add_candidates_when_pending_pool_exceeds_fetch_budget(factory, monkeypatch):
    with factory() as db:
        cid = campaign(db, target=26, threshold=0)
        for index in range(25):
            business = Business(name=f'Reserve {index}', campaign_id=cid, owner_id=1, status='researching', primary_phone=f'+1 512 555 {index:04d}')
            db.add(business); db.flush()
            db.add(WebsiteEvidence(business_id=business.id, owner_id=1, evidence_type='website_presence', observed_value='no_website'))
        db.commit()
    provider = type('Provider', (), {'discover': AsyncMock(return_value=[{'name':'New candidate', 'primary_phone':'+1 512 555 9999', 'city':'Austin', 'country':'USA', 'website_status':'no_website'}])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    result = worker.process_campaign_task(cid)
    assert result['qualified'] == 26, result
