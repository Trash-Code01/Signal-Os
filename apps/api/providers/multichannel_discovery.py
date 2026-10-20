"""Discover public business pages through selectable search channels.

Social channels use indexed public results, never private platform data.
Candidates retain source URLs and require location evidence in the result.
"""
import asyncio
import math
import re
from urllib.parse import urlsplit

import aiohttp
from core.discovery import CHANNELS, candidate_priority
from core.provider_health import report_provider_state, provider_failure
from core.deduplication import DeduplicationEngine
from core.lead_quality import clean_website_url, clean_phone_for_country
from .serper_discovery_provider import SerperDiscoveryProvider, _parse_target_location

CHANNEL_QUERIES = {
    'google_search': '',
    'directories': '(site:yelp.com/biz OR site:yellowpages.com OR site:justdial.com OR site:bbb.org)',
    'facebook': 'site:facebook.com',
    'instagram': 'site:instagram.com',
    'linkedin': 'site:linkedin.com/company',
}
CHANNEL_HOSTS = {
    'directories': ('yelp.com', 'yellowpages.com', 'justdial.com', 'bbb.org'),
    'facebook': ('facebook.com',), 'instagram': ('instagram.com',), 'linkedin': ('linkedin.com',),
}
QUERY_PREFIXES = ('', 'local ', 'small ', 'independent ')


def parse_candidate(result, channel, city, state, country):
    link = str(result.get('link') or '')
    parsed = urlsplit(link)
    host = (parsed.hostname or '').lower().removeprefix('www.')
    if parsed.scheme not in ('https', 'http') or not host:
        return None
    hosts = CHANNEL_HOSTS.get(channel)
    if hosts and not any(host == h or host.endswith('.' + h) for h in hosts):
        return None
    title, snippet = str(result.get('title') or ''), str(result.get('snippet') or '')
    # Never infer the result's city merely from the query.
    if not re.search(r'(?<!\w)' + re.escape(city) + r'(?!\w)', title + ' ' + snippet, re.I):
        return None
    path = parsed.path.lower()
    if any(segment in path for segment in ('/posts/', '/reel/', '/reels/', '/p/', '/groups/', '/search', '/in/')):
        return None
    if channel == 'linkedin' and not path.startswith('/company/'):
        return None
    name = re.split(r'\s+[|–—-]\s+|\s*\|\s*', title)[0].strip()
    name = re.sub(r'\s*\(@[^)]+\).*$', '', name).strip()
    if len(name) < 3 or re.search(r'\b(top\s+\d+|best\s+\d+|near me|directory|list of)\b', name, re.I):
        return None
    website = clean_website_url(link) if channel == 'google_search' else None
    if channel == 'google_search' and not website:
        return None
    phone_match = re.search(r'(?:phone|tel|call|contact)\s*:?\s*(\+?[\d(][\d ().-]{7,}\d)', snippet, re.I)
    return dict(name=name[:255], website_url=website,
                website_status='has_website' if website else 'unknown',
                primary_phone=clean_phone_for_country(phone_match.group(1) if phone_match else None, country),
                city=city, state_province=state, country=country, source_url=link,
                source_metadata={'source': channel, 'channel': channel})


class MultiChannelDiscoveryProvider(SerperDiscoveryProvider):
    def __init__(self, channels):
        super().__init__()
        self.channels = list(dict.fromkeys(channels))
        if not self.channels or any(c not in CHANNELS for c in self.channels):
            raise ValueError('Select at least one supported discovery channel.')
        self.channel_errors = {}
        self.discovery_state = {}

    def _page_state(self, channel, query, location):
        return self.discovery_state.setdefault(f'{channel}|{query}|{location}', {})

    def _prepare_page_state(self, channel, query, location):
        state = self._page_state(channel, query, location)
        page_limit = 50 if channel == 'google_maps' else 20
        variant = state.get('query_variant', 0)
        if (state.get('exhausted') or state.get('next_page', 1) > page_limit) and not state.get('provider_error'):
            if variant + 1 < len(QUERY_PREFIXES):
                # Refine the same industry in the same city after exhausting
                # a query; never broaden the campaign's geography or filters.
                state.clear()
                state['query_variant'] = variant + 1
        return state

    @property
    def has_more_results(self):
        return any(not state.get('provider_error') and (
                   state.get('query_variant', 0) + 1 < len(QUERY_PREFIXES) or
                   (not state.get('exhausted') and state.get('next_page', 1) <=
                   (50 if key.startswith('google_maps|') else 20)))
                   for key, state in self.discovery_state.items())

    async def _search_channel(self, channel, query, location, limit):
        city, state, country = _parse_target_location(location)
        if not city or not country:
            raise ValueError('City and country are required.')
        page_state = self._prepare_page_state(channel, query, location)
        search_query = QUERY_PREFIXES[page_state.get('query_variant', 0)] + query
        start_page = int(page_state.get('next_page', 1))
        if page_state.get('exhausted') or start_page > 20:
            return []
        results, seen = [], set(page_state.get('seen', []))
        async with aiohttp.ClientSession(headers={'X-API-KEY': self.api_key}, timeout=aiohttp.ClientTimeout(total=30)) as session:
            for page in range(start_page, min(21, start_page + math.ceil(limit / 10))):
                async with session.post('https://google.serper.dev/search', json={
                    'q': f'{search_query} in {location} {CHANNEL_QUERIES[channel]}', 'num': 10, 'page': page,
                }) as response:
                    if response.status != 200:
                        state, message = provider_failure(response.status, await response.text())
                        report_provider_state('serper', state, message, response.status)
                        raise RuntimeError(f'{channel}: {message}')
                    payload = await response.json()
                    report_provider_state('serper', 'active', 'Public business search completed.', response.status)
                organic = payload.get('organic') or []
                fresh = [r for r in organic if r.get('link') not in seen]
                page_state['next_page'] = page + 1
                if not fresh:
                    page_state['exhausted'] = True
                    break
                seen.update(r.get('link') for r in fresh)
                page_state['seen'] = list(seen)
                for item in fresh:
                    candidate = parse_candidate(item, channel, city, state, country)
                    if candidate and channel == 'google_search' and not self._is_official_business_website(item, candidate['name']):
                        continue
                    if candidate:
                        results.append(candidate)
                if len(results) >= limit:
                    break
            missing = [b for b in results if not b['website_url']]
            websites = await asyncio.gather(*(self._fetch_website(session, b) for b in missing))
            for business, website in zip(missing, websites):
                business['website_url'] = clean_website_url(website)
        return results

    async def discover(self, query, location, industry, limit=None):
        if not self.api_key:
            try:
                from .dataforseo_provider import DataForSEOProvider
                df = DataForSEOProvider()
                if df.username and df.password:
                    print("SERPER_API_KEY missing in multichannel. Falling back to DataForSEO provider.")
                    return await df.discover(query, location, industry, limit)
            except Exception as df_err:
                print(f"DataForSEO fallback error: {df_err}")
            raise RuntimeError('Live discovery requires SERPER_API_KEY. No sample leads were created.')
        # A fresh semaphore belongs to each event loop (worker uses asyncio.run).
        self.lookup_semaphore = asyncio.Semaphore(5)
        limit = max(1, limit or 100)
        # A selected channel gets at least one complete page. Filtering and
        # deduplication happen later; raw candidates are not the lead target.
        per_channel = max(10, math.ceil(limit / len(self.channels)))
        maps_discover = super().discover
        calls = []
        for channel in self.channels:
            if channel == 'google_maps':
                state = self._prepare_page_state(channel, query, location)
                search_query = QUERY_PREFIXES[state.get('query_variant', 0)] + query
                calls.append(maps_discover(search_query, location, industry, per_channel, page_state=state))
            else:
                calls.append(self._search_channel(channel, query, location, per_channel))
        batches = await asyncio.gather(*calls, return_exceptions=True)
        candidates, successes = [], 0
        for channel, batch in zip(self.channels, batches):
            if isinstance(batch, Exception):
                self.channel_errors[f'{location}: {channel}'] = str(batch)
                self._page_state(channel, query, location).update(exhausted=True, provider_error=True)
            else:
                successes += 1
                candidates.extend(batch)
        if not successes:
            reasons = '; '.join(dict.fromkeys(str(batch) for batch in batches if isinstance(batch, Exception)))
            try:
                from .dataforseo_provider import DataForSEOProvider
                df = DataForSEOProvider()
                if df.username and df.password:
                    print(f"[MultiChannelDiscovery] All channels failed ({reasons}). Falling back to DataForSEO provider.")
                    fallback_candidates = await df.discover(query, location, industry, limit)
                    if fallback_candidates:
                        return sorted(DeduplicationEngine().deduplicate(fallback_candidates), key=candidate_priority, reverse=True)
            except Exception as df_err:
                print(f"DataForSEO fallback error in multichannel: {df_err}")
            raise RuntimeError(f'All selected discovery channels failed. {reasons}')
        return sorted(DeduplicationEngine().deduplicate(candidates), key=candidate_priority, reverse=True)
