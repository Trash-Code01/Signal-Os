import asyncio
from unittest.mock import AsyncMock

import worker
import main
from core.models import Business, Campaign, CampaignLocation, WebsiteEvidence
from providers.multichannel_discovery import MultiChannelDiscoveryProvider
from providers.serper_discovery_provider import SerperDiscoveryProvider
from test_discovery_architecture import factory, campaign


def candidate(index, **changes):
    return dict(name=f'Business {index}', google_place_id=str(index), city='Austin', country='USA',
                website_status='no_website', primary_phone=f'+1 512 555 {index:04d}',
                review_count=100, rating=4.8, **changes)


def test_refills_filtered_pages_until_ten_qualified_without_crawling(factory, monkeypatch):
    with factory() as db:
        cid = campaign(db, target=10, threshold=80, website_filter='no_website')
    provider = type('Provider', (), {'discover': AsyncMock(side_effect=[
        [dict(candidate(1), website_url='https://example.com')],
        [dict(candidate(2), primary_phone=None)],
        [candidate(i) for i in range(10, 25)],
    ])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    crawl = AsyncMock(side_effect=AssertionError('No-website campaign must not crawl'))
    monkeypatch.setattr(worker.WebsiteIntelligenceEngine, 'audit_website', crawl)
    result = worker.process_campaign_task(cid)
    assert result['qualified'] == 10, result
    assert result['discovery_rounds'] == 3
    assert result['stop_reason'] == 'target_reached'
    assert provider.discover.await_count == 3
    crawl.assert_not_called()
    with factory() as db:
        assert db.query(Business).filter(Business.status == 'qualified').count() == 10
        assert db.query(Business).filter(Business.status == 'below_quality_threshold').count() == 1


def test_pending_below_threshold_pool_does_not_block_new_discovery(factory, monkeypatch):
    with factory() as db:
        cid = campaign(db, target=1, threshold=80, website_filter='no_website')
        business = Business(name='Weak candidate', campaign_id=cid, owner_id=1, status='below_quality_threshold')
        db.add(business); db.flush()
        db.add(WebsiteEvidence(business_id=business.id, owner_id=1, evidence_type='website_presence', observed_value='no_website'))
        db.commit()
    provider = type('Provider', (), {'discover': AsyncMock(return_value=[candidate(11)])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    result = worker.process_campaign_task(cid)
    assert result['qualified'] == 1, result
    assert result['discovery_rounds'] == 2
    provider.discover.assert_awaited_once()


def test_repeated_candidates_stop_honestly_and_monitor_accounts_for_shortfall(factory, monkeypatch):
    with factory() as db:
        cid = campaign(db, target=10, threshold=80, website_filter='no_website')
    provider = type('Provider', (), {'discover': AsyncMock(return_value=[dict(candidate(1), primary_phone=None)])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    result = worker.process_campaign_task(cid)
    assert result['status'] == 'completed_partial'
    assert result['qualified'] == 0
    assert result['stop_reason'] == 'search_exhausted'
    assert provider.discover.await_count == 2
    with factory() as db:
        status = main.get_campaign_status(cid, db)
        assert status['stats']['needs_review'] == 1
        assert status['stages'][1]['status'] == 'partial'
        assert 'exhausted' in status['summary']


def test_page_progress_persists_and_resume_uses_next_page(factory, monkeypatch):
    class Provider:
        def __init__(self): self.discovery_state = {}
        @property
        def has_more_results(self): return False
        async def discover(self, **kwargs):
            page = self.discovery_state.get('google_maps|roofing|Austin', {}).get('next_page', 1)
            self.discovery_state['google_maps|roofing|Austin'] = {'next_page': page + 1}
            return [dict(candidate(page), primary_phone=None if page == 1 else '+1 512 555 0199')]
    monkeypatch.setattr(worker, 'get_discovery_provider', Provider)
    with factory() as db: cid = campaign(db, target=1, threshold=80, website_filter='no_website')
    assert worker.process_campaign_task(cid)['qualified'] == 0
    with factory() as db:
        assert db.get(Campaign, cid).settings['discovery_state']['google_maps|roofing|Austin']['next_page'] == 2
    assert worker.process_campaign_task(cid)['qualified'] == 1


def test_selected_channels_receive_full_pages_without_discarding_candidates(monkeypatch):
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')
    provider = MultiChannelDiscoveryProvider(['google_maps', 'facebook'])
    calls = []
    async def maps(self, query, location, industry, limit, page_state):
        calls.append(limit)
        return [candidate(i) for i in range(10)]
    async def search(channel, query, location, limit):
        calls.append(limit)
        return [candidate(i) for i in range(10, 20)]
    monkeypatch.setattr(SerperDiscoveryProvider, 'discover', maps)
    monkeypatch.setattr(provider, '_search_channel', search)
    results = asyncio.run(provider.discover('roofing', 'Austin, USA', 'roofing', 4))
    assert calls == [10, 10]
    assert len(results) == 20


def test_maps_fetches_fresh_pages_after_first_batch(monkeypatch):
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')
    monkeypatch.setattr('providers.serper_discovery_provider.report_provider_state', lambda *args: None)
    pages = []
    class Response:
        status = 200
        def __init__(self, page): self.page = page
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def json(self):
            return {'ll': '@30.27,-97.74,14z', 'places': [{'title': f'Business {self.page}', 'cid': str(self.page), 'website': 'https://example.com'}]}
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def post(self, url, json):
            assert url == 'https://google.serper.dev/maps'
            if json['page'] > 1:
                assert json['ll'] == '@30.27,-97.74,14z'
            pages.append(json['page']); return Response(json['page'])
    monkeypatch.setattr('providers.serper_discovery_provider.aiohttp.ClientSession', lambda **kwargs: Session())
    provider, state = SerperDiscoveryProvider(), {}
    first = asyncio.run(provider.discover('roofing', 'Austin, USA', 'roofing', 1, state))
    second = asyncio.run(provider.discover('roofing', 'Austin, USA', 'roofing', 1, state))
    assert pages == [1, 2]
    assert first[0]['google_place_id'] != second[0]['google_place_id']


def test_search_budget_bounds_unproductive_searches(factory, monkeypatch):
    class Provider:
        has_more_results = True
        async def discover(self, **kwargs):
            return [dict(candidate(i), website_url='https://example.com') for i in range(25)]
    monkeypatch.setattr(worker, 'get_discovery_provider', Provider)
    with factory() as db: cid = campaign(db, target=10, website_filter='no_website')
    result = worker.process_campaign_task(cid)
    assert result['status'] == 'completed_partial'
    assert result['stop_reason'] == 'search_budget_reached'
    assert result['discovery_rounds'] == 50
    assert result['qualified'] == 0


def test_full_page_from_first_city_does_not_starve_other_locations(factory, monkeypatch):
    with factory() as db:
        cid = campaign(db, target=1, website_filter='no_website')
        db.add(CampaignLocation(campaign_id=cid, city='Dallas', country='USA', owner_id=1))
        db.commit()
    provider = type('Provider', (), {'discover': AsyncMock(side_effect=[
        [dict(candidate(i), website_url='https://example.com') for i in range(30)],
        [dict(candidate(100), city='Dallas')],
    ])})()
    monkeypatch.setattr(worker, 'get_discovery_provider', lambda: provider)
    result = worker.process_campaign_task(cid)
    assert result['qualified'] == 1
    assert [call.kwargs['location'] for call in provider.discover.await_args_list] == ['Austin, USA', 'Dallas, USA']


def test_exhausted_query_refines_same_industry_and_city(monkeypatch):
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')
    provider = MultiChannelDiscoveryProvider(['google_maps'])
    provider.discovery_state = {'google_maps|restaurant|Austin, USA': {
        'exhausted': True, 'next_page': 11, 'll': 'old-location', 'seen': ['old-id'],
    }}
    calls = []
    async def maps(self, query, location, industry, limit, page_state):
        calls.append((query, location, industry, dict(page_state)))
        return []
    monkeypatch.setattr(SerperDiscoveryProvider, 'discover', maps)
    assert provider.has_more_results
    asyncio.run(provider.discover('restaurant', 'Austin, USA', 'restaurant', 10))
    assert calls == [('local restaurant', 'Austin, USA', 'restaurant', {'query_variant': 1})]
    provider.discovery_state['google_maps|restaurant|Austin, USA'].update(exhausted=True, provider_error=True)
    assert not provider.has_more_results
