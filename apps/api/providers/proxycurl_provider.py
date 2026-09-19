from core.runtime import IS_STAGING
import os
import aiohttp
from typing import List, Dict, Any
from core.provider_health import report_provider_state

class ProxycurlProvider:
    def __init__(self):
        self.api_key = "" if IS_STAGING else os.environ.get('PROXYCURL_API_KEY', '').strip()
        self.base_url = "https://nubela.co/api/v1/company/details"

    async def get_executives(self, domain: str) -> List[Dict[str, Any]]:
        if not self.api_key or not domain:
            if not self.api_key:
                report_provider_state("proxycurl", "not_configured", "PROXYCURL_API_KEY is missing.")
            return []
            
        contacts = []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"website": domain}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        report_provider_state("proxycurl", "active", "Decision-maker search completed.", resp.status)
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
                    else:
                        response_text = (await resp.text())[:180]
                        state = "cooldown" if resp.status == 429 else "exhausted" if resp.status in (402, 403) else "invalid_key" if resp.status == 401 else "unavailable"
                        report_provider_state("proxycurl", state, f"Decision-maker search failed ({resp.status}): {response_text}", resp.status)
        except Exception as e:
            print(f"Proxycurl error for {domain}: {e}")
            report_provider_state("proxycurl", "unavailable", "Proxycurl could not be reached.")
            
        return contacts
