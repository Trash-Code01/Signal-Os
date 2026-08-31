import os
import aiohttp
from typing import List, Dict, Any

class ProxycurlProvider:
    def __init__(self):
        self.api_key = os.environ.get('PROXYCURL_API_KEY', 'bbb15a7be7504d4ca3fd3a0c8836a3ce')
        self.base_url = "https://nubela.co/api/v1/company/details"

    async def get_executives(self, domain: str) -> List[Dict[str, Any]]:
        if not self.api_key or not domain:
            return []
            
        contacts = []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"website": domain}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        executives = data.get("executives") or []
                        for exec in executives:
                            name = exec.get("name", "")
                            parts = name.split(" ")
                            first_name = parts[0]
                            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                            
                            contacts.append({
                                "first_name": first_name,
                                "last_name": last_name,
                                "title": exec.get("title", ""),
                                "linkedin_url": exec.get("person_profile_url", ""),
                                "source": "proxycurl",
                                "confidence": 0.9
                            })
        except Exception as e:
            print(f"Proxycurl error for {domain}: {e}")
            
        return contacts
