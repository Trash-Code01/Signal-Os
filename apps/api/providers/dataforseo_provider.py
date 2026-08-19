import os
import aiohttp
import asyncio
import base64
from typing import List, Dict, Any
from core.providers import BusinessDiscoveryProvider

class DataForSEOProvider(BusinessDiscoveryProvider):
    def __init__(self):
        self.username = os.environ.get("DATAFORSEO_USERNAME")
        self.password = os.environ.get("DATAFORSEO_PASSWORD")
        # In a real implementation, you would set up the HTTP client here.

    async def discover(self, query: str, location: str, industry: str) -> List[Dict[str, Any]]:
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
        
        # Maps query payload
        payload = [{
            "keyword": f"{industry} in {location}",
            "language_code": "en",
            "location_code": 2840,
            "depth": 100 # Adjust depth depending on target_quantity
        }]
        
        raw_businesses = []
        try:
            async with aiohttp.ClientSession() as session:
                # Use Live API for immediate response (blocks until done)
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    if response.status == 200:
                        tasks = data.get("tasks", [])
                        if not tasks:
                            print("DataForSEO: No tasks in response")
                            return []
                            
                        status_code = tasks[0].get("status_code")
                        if status_code == 20000:
                            items = tasks[0].get("result", [{}])[0].get("items", [])
                        else:
                            print(f"DataForSEO task error {status_code}: {tasks[0].get('status_message')}")
                            return []
                    else:
                        print(f"DataForSEO error {response.status}: {data}")
                        return []
                        
                for item in items:
                    raw_businesses.append({
                        "name": item.get("title"),
                        "domain": item.get("domain"), # Important for dedupe
                        "phone": item.get("phone"),
                        "address": item.get("address"),
                        "city": item.get("city"),
                        "state": item.get("state"),
                        "country": item.get("country_code"),
                        "place_id": item.get("place_id"),
                        "source_metadata": {"source": "dataforseo_maps", "rank_group": item.get("rank_group")}
                    })
                                        
        except Exception as e:
            print(f"DataForSEO error: {e}")
            
        return raw_businesses
