import os
import aiohttp
import asyncio
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from core.providers import BusinessDiscoveryProvider
from core.provider_health import report_provider_state, provider_failure
from core.lead_quality import canonical_country, clean_phone_for_country, clean_website_url, JUNK_WEBSITE_DOMAINS

def _is_junk_website(url) -> bool:
    """Return True if the URL is a directory, social, Wikipedia, or chain HQ page."""
    if not url:
        return False
    parsed = urllib.parse.urlsplit(url if "://" in url else f"https://{url}")
    hostname = (parsed.hostname or "").rstrip(".").lower()
    for domain in JUNK_WEBSITE_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return True
    return False


def _parse_target_location(location: str) -> tuple[Optional[str], Optional[str], str]:
    """Parse the campaign location label, not a locale-specific street address."""
    parts = [part.strip() for part in (location or "").split(",") if part.strip()]
    if not parts:
        return None, None, ""
    country = canonical_country(parts[-1])
    if country in {"USA", "Canada"} and len(parts) >= 3:
        return ", ".join(parts[:-2]), parts[-2], country
    return ", ".join(parts[:-1]) or None, None, country


class SerperDiscoveryProvider(BusinessDiscoveryProvider):
    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY", "").strip()
        self.lookup_semaphore = asyncio.Semaphore(5)

    def _is_directory_or_social(self, link: str) -> bool:
        return _is_junk_website(link)

    def _is_official_business_website(self, result: dict, business_name: str) -> bool:
        link = result.get("link", "").strip()
        if not link or self._is_directory_or_social(link):
            return False
        hostname = (
            urllib.parse.urlsplit(link if "://" in link else f"https://{link}").hostname or ""
        ).lower().removeprefix("www.")
        compact_host = re.sub(r"[^a-z0-9]", "", hostname.split(".")[0])
        normalized_name = re.sub(r"[^a-z0-9]+", " ", business_name.lower()).strip()
        compact_name = normalized_name.replace(" ", "")
        all_tokens = [token for token in normalized_name.split() if len(token) >= 3]
        generic = {
            "the", "and", "company", "services", "solutions", "group", "studio",
            "centre", "center", "clinic", "official", "private", "limited", "ltd",
            "llc", "inc", "pvt", "yoga", "fitness", "premier", "elite", "apex",
        }
        distinctive_tokens = [token for token in all_tokens if token not in generic]
        if not all_tokens:
            return False
        title = re.sub(r"[^a-z0-9]+", " ", (result.get("title") or "").lower())
        snippet = re.sub(r"[^a-z0-9]+", " ", (result.get("snippet") or "").lower())
        result_text = f" {title} {snippet} "

        if len(compact_name) >= 5 and compact_name in compact_host:
            return True
        if distinctive_tokens and any(token in compact_host for token in distinctive_tokens):
            return any(token in result_text for token in distinctive_tokens)
        matched = sum(token in result_text for token in all_tokens)
        required = 1 if len(all_tokens) == 1 else 2
        return matched >= required and any(token in compact_host for token in all_tokens)

    async def _fetch_website(self, session: aiohttp.ClientSession, business: dict):
        """Fallback to Serper organic search to find the website if Google Maps did not provide one."""
        business['website_status'] = 'unknown'
        if not self.api_key:
            return None
        query = f"{business.get('name', '')} {business.get('address') or business.get('city', '')} official website"
        payload = {"q": query, "num": 5}
        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            async with self.lookup_semaphore, session.post("https://google.serper.dev/search", headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    for res in data.get("organic", []):
                        if self._is_official_business_website(res, business.get("name", "")):
                            business['website_status'] = 'has_website'
                            return res.get("link")
                    business['website_status'] = 'no_website'
        except Exception as e:
            print(f"Error fetching website for {business.get('name')}: {e}")
        return None

    async def discover(self, query: str, location: str, industry: str, limit=None, page_state=None) -> List[Dict[str, Any]]:
        print(f"Serper discovering: {query} in {location} for {industry}")

        if not self.api_key:
            try:
                from .dataforseo_provider import DataForSEOProvider
                df = DataForSEOProvider()
                if df.username and df.password:
                    print("SERPER_API_KEY missing. Falling back to DataForSEO provider.")
                    return await df.discover(query, location, industry, limit)
            except Exception as df_err:
                print(f"DataForSEO fallback error: {df_err}")
            report_provider_state("serper", "not_configured", "SERPER_API_KEY is missing.")
            raise RuntimeError("Live discovery requires SERPER_API_KEY. No sample leads were created.")

        target_city, target_state, target_country = _parse_target_location(location)
        if not target_city or not target_country:
            report_provider_state("serper", "invalid_request", "Campaign city and country are required.")
            return []

        # Maps includes public listing phones and full addresses; Places can
        # omit these fields and leave no-website candidates uncontactable.
        url = "https://google.serper.dev/maps"
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        search_query = f"{query or industry} in {location}"

        raw_businesses = []
        places = []
        target_limit = max(1, limit or 100)
        # Larger campaigns need more than the first ten result pages. Stop at
        # 50 pages, the requested quantity, or the first empty/repeated page.
        max_pages = min(50, (target_limit + 19) // 20)
        page_state = page_state if page_state is not None else {}
        seen_cids = set(page_state.get('seen', []))
        start_page = int(page_state.get('next_page', 1))
        if page_state.get('exhausted') or start_page > 50:
            return []

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
                for page in range(start_page, min(51, start_page + max_pages)):
                    if len(places) >= target_limit:
                        break
                    payload = {
                        "q": search_query,
                        "page": page,
                    }
                    if page_state.get('ll'):
                        payload['ll'] = page_state['ll']
                    data = None
                    for attempt in range(2):
                        async with session.post(url, json=payload) as response:
                            data = await response.json()

                            if response.status != 200:
                                state, message = provider_failure(response.status, data)
                                report_provider_state("serper", state, message, response.status)
                                if not places:
                                    try:
                                        from .dataforseo_provider import DataForSEOProvider
                                        df = DataForSEOProvider()
                                        if df.username and df.password:
                                            print(f"[Discovery] Serper returned {response.status} ({message}). Falling back to DataForSEO provider.")
                                            return await df.discover(query, location, industry, limit)
                                    except Exception as df_err:
                                        print(f"DataForSEO fallback error: {df_err}")
                                    raise RuntimeError(message)
                                break

                            page_places = data.get("places", [])
                            if data.get('ll'):
                                # Maps requires this location token on page 2+.
                                page_state['ll'] = data['ll']
                            if page_places:
                                report_provider_state("serper", "active", "Business discovery in progress.", response.status)
                                break

                            if attempt == 0:
                                await asyncio.sleep(1)

                    page_places = (data or {}).get("places", []) if data else []
                    if not page_places:
                        page_state['exhausted'] = True
                        break

                    new_added = 0
                    for p in page_places:
                        cid = p.get("cid") or p.get("placeId") or p.get("title")
                        if cid and cid in seen_cids:
                            continue
                        if cid:
                            seen_cids.add(cid)
                        places.append(p)
                        new_added += 1
                    page_state['next_page'] = page + 1
                    page_state['seen'] = list(seen_cids)
                    if new_added == 0:
                        page_state['exhausted'] = True
                        break

                for place in places:
                    address_str = place.get("address", "")
                    # Keep the existing CID identity stable across the endpoint
                    # change, so resumes do not import the same listing twice.
                    place_identifier = place.get("cid") or place.get("placeId")
                    source_url = place.get("link") or (
                        f"https://www.google.com/maps?cid={place.get('cid')}" if place.get("cid") else None
                    )
                    zip_code = None
                    if target_country == "India":
                        pin_match = re.search(r"\b[1-9]\d{5}\b", address_str)
                        zip_code = pin_match.group(0) if pin_match else None
                    elif target_country in {"USA", "Canada"}:
                        postal_match = re.search(r"\b\d{5}(?:-\d{4})?\b", address_str)
                        zip_code = postal_match.group(0) if postal_match else None

                    website = clean_website_url(place.get("website"))

                    raw_businesses.append({
                        "name": place.get("title"),
                        "website_url": website,
                        "website_status": "has_website" if website else "unknown",
                        "primary_phone": clean_phone_for_country(place.get("phoneNumber"), target_country),
                        "address": address_str,
                        "city": target_city,
                        "state_province": target_state,
                        "country": target_country,
                        "postal_code": zip_code,
                        "latitude": place.get("latitude"),
                        "longitude": place.get("longitude"),
                        "google_place_id": place_identifier,
                        "rating": place.get("rating"),
                        "review_count": place.get("ratingCount"),
                        "source_url": source_url,
                        "source_metadata": {
                            "source": "serper_maps",
                            "channel": "google_maps",
                            "rank_group": place.get("position"),
                            "website_source": "google_business_profile" if website else None,
                        }
                    })

                # Fallback website fetching for businesses with no website
                tasks = []
                missing_indices = []
                for i, b in enumerate(raw_businesses):
                    if not b.get("website_url"):
                        tasks.append(self._fetch_website(session, b))
                        missing_indices.append(i)

                if tasks:
                    print(f"Fetching missing websites for {len(tasks)} businesses...")
                    results = await asyncio.gather(*tasks)
                    for idx, fetched_website in zip(missing_indices, results):
                        cleaned = clean_website_url(fetched_website)
                        raw_businesses[idx]["website_url"] = cleaned
                        if cleaned:
                            raw_businesses[idx]["source_metadata"]["website_source"] = "verified_organic_match"

        except Exception as e:
            print(f"Serper discovery error: {e}")
            if not raw_businesses:
                try:
                    from .dataforseo_provider import DataForSEOProvider
                    df = DataForSEOProvider()
                    if df.username and df.password:
                        print(f"[Discovery] Serper failed ({e}). Falling back to DataForSEO provider.")
                        return await df.discover(query, location, industry, limit)
                except Exception as df_err:
                    print(f"DataForSEO fallback error: {df_err}")
                raise RuntimeError(f"Google Maps discovery unavailable: {e}") from e

        return raw_businesses
