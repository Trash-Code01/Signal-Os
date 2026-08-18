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
            
        url = "https://api.dataforseo.com/v3/serp/google/maps/task_post"
        
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        # Maps query payload
        payload = [{
            "keyword": f"{industry} in {location}",
            "location_name": location,
            "language_name": "English",
            "depth": 100 # Adjust depth depending on target_quantity
        }]
        
        raw_businesses = []
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Post Task
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        tasks = data.get("tasks", [])
                        if not tasks:
                            return []
                            
                        task_id = tasks[0].get("id")
                        if not task_id:
                            return []
                            
                        # 2. Get Task Results
                        result_url = f"https://api.dataforseo.com/v3/serp/google/maps/task_get/advanced/{task_id}"
                        
                        # In reality, this requires polling or webhooks. 
                        # Using a simple short poll loop for MVP
                        for attempt in range(5):
                            await asyncio.sleep(5) # Wait before polling
                            async with session.get(result_url, headers=headers) as res_response:
                                if res_response.status == 200:
                                    res_data = await res_response.json()
                                    res_tasks = res_data.get("tasks", [])
                                    if res_tasks and res_tasks[0].get("status_code") == 20000:
                                        # Task is complete
                                        items = res_tasks[0].get("result", [{}])[0].get("items", [])
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
                                        break
                                        
        except Exception as e:
            print(f"DataForSEO error: {e}")
            
        return raw_businesses
