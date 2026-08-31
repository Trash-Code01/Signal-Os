import os
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from core.providers import BusinessDiscoveryProvider

# Domains that are NEVER a valid local business website — always skip these
JUNK_WEBSITE_DOMAINS = {
    "wikipedia.org", "yelp.com", "facebook.com", "tripadvisor.com", "instagram.com",
    "linkedin.com", "google.com", "doordash.com", "ubereats.com", "grubhub.com",
    "yellowpages.com", "angi.com", "houzz.com", "thumbtack.com", "homeadvisor.com",
    "opentable.com", "zillow.com", "realtor.com", "chamberofcommerce.com", "manta.com",
    "bizapedia.com", "zoominfo.com", "dnb.com", "glassdoor.com", "indeed.com",
    "trustpilot.com", "foursquare.com", "alignable.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "mapquest.com", "bbb.org", "fmcsa.dot.gov",
    "serviceagent.ai",
}


def _is_junk_website(url) -> bool:
    """Return True if the URL is a directory, social, Wikipedia, or chain HQ page."""
    if not url:
        return False
    url_lower = url.lower()
    for domain in JUNK_WEBSITE_DOMAINS:
        if domain in url_lower:
            return True
    return False


class SerperDiscoveryProvider(BusinessDiscoveryProvider):
    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY", "").strip()

    def _is_directory_or_social(self, link: str) -> bool:
        return _is_junk_website(link)

    def _is_official_business_website(self, result: dict, business_name: str) -> bool:
        link = result.get("link", "").lower()
        if not link or self._is_directory_or_social(link):
            return False
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        name_lower = business_name.lower().replace("llc", "").replace("inc", "").strip()
        stopwords = {"the", "a", "an", "and", "of", "inc", "llc", "co", "company"}
        name_parts = [p for p in name_lower.split() if p not in stopwords]
        if not name_parts:
            return False
        primary_name = name_parts[0]
        if primary_name in title or primary_name in snippet or primary_name in link:
            return True
        return False

    async def _fetch_website(self, session: aiohttp.ClientSession, business: dict):
        """Fallback to Serper organic search to find the website if Google Maps did not provide one."""
        query = f"{business.get('name', '')} {business.get('address', '')} official website"
        payload = {"q": query, "num": 5}
        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            async with session.post("https://google.serper.dev/search", headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    for res in data.get("organic", []):
                        if self._is_official_business_website(res, business.get("name", "")):
                            return res.get("link")
        except Exception as e:
            print(f"Error fetching website for {business.get('name')}: {e}")
        return None

    def _infer_country(self, location: str) -> str:
        """Infer country label from the location string passed to discover()."""
        loc_lower = location.lower()
        if "australia" in loc_lower:
            return "Australia"
        if "united kingdom" in loc_lower or " uk" in loc_lower:
            return "UK"
        if "canada" in loc_lower:
            return "Canada"
        if "india" in loc_lower:
            return "India"
        if "new zealand" in loc_lower:
            return "New Zealand"
        return "USA"

    async def discover(self, query: str, location: str, industry: str, limit=None) -> List[Dict[str, Any]]:
        print(f"Serper discovering: {query} in {location} for {industry}")

        if not self.api_key:
            print("Serper API key missing. Returning empty list.")
            return []

        # Infer the country from the location string so businesses are tagged correctly
        inferred_country = self._infer_country(location)

        url = "https://google.serper.dev/places"
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        search_query = f"{query or industry} in {location}"

        raw_businesses = []
        places = []
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                payload = {
                    "q": search_query,
                    "num": min(limit or 100, 100)
                }

                for attempt in range(2):
                    async with session.post(url, json=payload) as response:
                        data = await response.json()

                        if response.status != 200:
                            print(f"Serper error {response.status}: {data}")
                            return []

                        places = data.get("places", [])
                        if places:
                            break

                        if attempt == 0:
                            print(f"Serper returned 0 places for '{search_query}'. Retrying in 2s...")
                            await asyncio.sleep(2)

                for place in places:
                    address_str = place.get("address", "")
                    city, state, zip_code = None, None, None
                    if address_str and "," in address_str:
                        parts = address_str.split(",")
                        if len(parts) >= 2:
                            city = parts[-2].strip()
                            state_zip = parts[-1].strip().split(" ")
                            if len(state_zip) >= 2:
                                state = state_zip[0]
                                zip_code = state_zip[1]

                    website = place.get("website")
                    # Clear out junk websites — Wikipedia, chain HQ pages, social media
                    if _is_junk_website(website):
                        website = None

                    raw_businesses.append({
                        "name": place.get("title"),
                        "website_url": website,
                        "primary_phone": place.get("phoneNumber"),
                        "address": address_str,
                        "city": city,
                        "state_province": state,
                        "country": inferred_country,   # FIXED: was hardcoded to "US"
                        "postal_code": zip_code,
                        "latitude": place.get("latitude"),
                        "longitude": place.get("longitude"),
                        "google_place_id": place.get("cid"),
                        "rating": place.get("rating"),
                        "review_count": place.get("ratingCount"),
                        "source_url": f"https://www.google.com/maps/place/?q=place_id:{place.get('cid')}",
                        "source_metadata": {"source": "serper_places", "rank_group": place.get("position")}
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
                    for idx, website in zip(missing_indices, results):
                        raw_businesses[idx]["website_url"] = website

        except Exception as e:
            print(f"Serper discovery error: {e}")

        return raw_businesses
