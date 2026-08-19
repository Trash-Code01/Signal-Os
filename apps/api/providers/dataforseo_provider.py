import os
import aiohttp
import asyncio
import base64
from typing import List, Dict, Any, Optional
from core.providers import BusinessDiscoveryProvider

class DataForSEOProvider(BusinessDiscoveryProvider):
    def __init__(self):
        self.username = os.environ.get("DATAFORSEO_USERNAME")
        self.password = os.environ.get("DATAFORSEO_PASSWORD")

    @staticmethod
    def _country_code(location: str) -> str:
        country = (location.rsplit(",", 1)[-1] if "," in location else location).strip().lower()
        aliases = {
            "usa": "us",
            "u.s.a.": "us",
            "united states": "us",
            "uk": "gb",
            "u.k.": "gb",
            "united kingdom": "gb",
        }
        return aliases.get(country, country[:2])

    @staticmethod
    def _normalise_location(value: str) -> str:
        return "".join((value or "").lower().replace("usa", "united states").split())

    async def _resolve_location_code(self, session: aiohttp.ClientSession, location: str) -> Optional[int]:
        """Resolve the campaign's exact city into DataForSEO's supported code.

        The location-list endpoint is free. Using an explicit code prevents a
        search from silently falling back to a country-wide result.
        """
        country_code = self._country_code(location)
        url = f"https://api.dataforseo.com/v3/serp/google/locations/{country_code}"
        try:
            async with session.get(url) as response:
                data = await response.json()
            task = (data.get("tasks") or [{}])[0]
            if task.get("status_code") != 20000:
                print(f"DataForSEO location lookup failed: {task.get('status_message')}")
                return None
            locations = task.get("result") or []
            expected = self._normalise_location(location)
            exact = next(
                (item for item in locations if self._normalise_location(item.get("location_name", "")) == expected),
                None,
            )
            if exact:
                return exact.get("location_code")

            parts = [part.strip().lower() for part in location.split(",") if part.strip()]
            city = parts[0] if parts else ""
            region = parts[1] if len(parts) > 2 else ""
            candidates = [
                item for item in locations
                if city and item.get("location_type") in {"City", "DMA Region"}
                and item.get("location_name", "").lower().startswith(f"{city},")
            ]
            if region:
                candidates = [item for item in candidates if f",{region}," in item.get("location_name", "").lower()]
            return candidates[0].get("location_code") if candidates else None
        except Exception as exc:
            print(f"DataForSEO location lookup error: {exc}")
            return None

    async def discover(self, query: str, location: str, industry: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Discover businesses using DataForSEO Google Maps API."""
        print(f"DataForSEO discovering: {query} in {location} for {industry}")
        
        if not self.username or not self.password:
            print("DataForSEO credentials missing. Returning empty list.")
            return []
            
        url = "https://api.dataforseo.com/v3/serp/google/maps/live/advanced"
        
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        depth = min(max(limit or 100, 1), 100)
        raw_businesses = []
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                location_code = await self._resolve_location_code(session, location)
                if not location_code:
                    print(f"DataForSEO: No exact supported location for {location!r}; discovery skipped.")
                    return []

                payload = [{
                    "keyword": query or industry,
                    "language_code": "en",
                    "location_code": location_code,
                    "depth": depth,
                }]
                # Use Live API for immediate response (blocks until done)
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    if response.status == 200:
                        tasks = data.get("tasks", [])
                        if not tasks:
                            print("DataForSEO: No tasks in response")
                            return []
                            
                        status_code = tasks[0].get("status_code")
                        if status_code == 20000:
                            result = tasks[0].get("result", [{}])[0]
                            items = result.get("items", [])
                            source_url = result.get("check_url")
                        else:
                            print(f"DataForSEO task error {status_code}: {tasks[0].get('status_message')}")
                            return []
                    else:
                        print(f"DataForSEO error {response.status}: {data}")
                        return []
                        
                for item in items[:depth]:
                    address_info = item.get("address_info") or {}
                    rating = item.get("rating") or {}
                    raw_businesses.append({
                        "name": item.get("title"),
                        "website_url": item.get("url") or (f"https://{item.get('domain')}" if item.get("domain") else None),
                        "primary_phone": item.get("phone"),
                        "address": item.get("address") or address_info.get("address"),
                        "city": item.get("city") or address_info.get("city"),
                        "state_province": item.get("state") or address_info.get("state"),
                        "country": item.get("country_code") or address_info.get("country_code"),
                        "postal_code": item.get("zip") or address_info.get("zip"),
                        "latitude": item.get("latitude"),
                        "longitude": item.get("longitude"),
                        "google_place_id": item.get("place_id") or item.get("cid"),
                        "rating": rating.get("value") if isinstance(rating, dict) else None,
                        "review_count": rating.get("votes_count") if isinstance(rating, dict) else None,
                        "source_url": source_url,
                        "source_metadata": {"source": "dataforseo_maps", "rank_group": item.get("rank_group")}
                    })
                                        
        except Exception as e:
            print(f"DataForSEO error: {e}")
            
        return raw_businesses
