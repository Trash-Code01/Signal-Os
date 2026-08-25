import os
import aiohttp
from typing import List, Dict, Any, Optional
from core.providers import BusinessDiscoveryProvider

class SerperDiscoveryProvider(BusinessDiscoveryProvider):
    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY", "9da0ce52b3729b7d9c1cd60fd3ab5ab20da47eab").strip()

    async def discover(self, query: str, location: str, industry: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        print(f"Serper discovering: {query} in {location} for {industry}")
        
        if not self.api_key:
            print("Serper API key missing. Returning empty list.")
            return []
            
        url = "https://google.serper.dev/places"
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        search_query = f"{query or industry} in {location}"
        
        raw_businesses = []
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                payload = {
                    "q": search_query,
                    "num": min(limit or 100, 100) # Serper allows up to 100 places per request
                }
                
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    
                    if response.status != 200:
                        print(f"Serper error {response.status}: {data}")
                        return []
                        
                    places = data.get("places", [])
                    
                    for place in places:
                        # Extract location parts safely
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
                                    
                        raw_businesses.append({
                            "name": place.get("title"),
                            "website_url": place.get("website"),
                            "primary_phone": place.get("phoneNumber"),
                            "address": address_str,
                            "city": city,
                            "state_province": state,
                            "country": "US", # Assuming US for Dallas D2C, can be derived
                            "postal_code": zip_code,
                            "latitude": place.get("latitude"),
                            "longitude": place.get("longitude"),
                            "google_place_id": place.get("cid"),
                            "rating": place.get("rating"),
                            "review_count": place.get("ratingCount"),
                            "source_url": f"https://www.google.com/maps/place/?q=place_id:{place.get('cid')}",
                            "source_metadata": {"source": "serper_places", "rank_group": place.get("position")}
                        })
                                        
        except Exception as e:
            print(f"Serper discovery error: {e}")
            
        return raw_businesses
