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

    async def _search_channel(self, channel, query, location, limit):
        city, state, country = _parse_target_location(location)
        if not city or not country:
            raise ValueError('City and country are required.')
        results, seen = [], set()
        async with aiohttp.ClientSession(headers={'X-API-KEY': self.api_key}, timeout=aiohttp.ClientTimeout(total=30)) as session:
            for page in range(1, min(20, math.ceil(limit / 10)) + 1):
                async with session.post('https://google.serper.dev/search', json={
                    'q': f'{query} in {location} {CHANNEL_QUERIES[channel]}', 'num': 10, 'page': page,
                }) as response:
                    if response.status != 200:
                        raise RuntimeError(f'{channel} search failed ({response.status})')
                    payload = await response.json()
                organic = payload.get('organic') or []
                fresh = [r for r in organic if r.get('link') not in seen]
                if not fresh:
                    break
                seen.update(r.get('link') for r in fresh)
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
        return results[:limit]

    async def discover(self, query, location, industry, limit=None):
        if not self.api_key:
            raise RuntimeError('Live discovery requires SERPER_API_KEY. No sample leads were created.')
        # A fresh semaphore belongs to each event loop (worker uses asyncio.run).
        self.lookup_semaphore = asyncio.Semaphore(5)
        limit = max(1, limit or 100)
        per_channel = max(1, math.ceil(limit / len(self.channels)))
        maps_discover = super().discover
        calls = [maps_discover(query, location, industry, per_channel) if c == 'google_maps'
                 else self._search_channel(c, query, location, per_channel) for c in self.channels]
        batches = await asyncio.gather(*calls, return_exceptions=True)
        candidates, successes = [], 0
        for channel, batch in zip(self.channels, batches):
            if isinstance(batch, Exception):
                self.channel_errors[f'{location}: {channel}'] = str(batch)
            else:
                successes += 1
                candidates.extend(batch)
        if not successes:
            raise RuntimeError('All selected discovery channels failed. Check provider configuration and retry.')
        return sorted(DeduplicationEngine().deduplicate(candidates), key=candidate_priority, reverse=True)[:limit]
