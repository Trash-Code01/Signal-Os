import os
import aiohttp
from typing import List, Dict, Any, Optional
from core.providers import EmailProvider
from core.provider_health import report_provider_state

class SnovioProvider(EmailProvider):
    def __init__(self, db_session=None):
        self.client_id = os.environ.get('SNOVIO_CLIENT_ID', '').strip()
        self.client_secret = os.environ.get('SNOVIO_CLIENT_SECRET', '').strip()
        self.base_url = "https://api.snov.io"
        self._token = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        if not self.client_id or not self.client_secret:
            print("SnovioProvider: credentials are not configured. Skipping enrichment.")
            report_provider_state("snovio", "not_configured", "SNOVIO_CLIENT_ID or SNOVIO_CLIENT_SECRET is missing.")
            return None
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            async with session.post(f"{self.base_url}/v1/oauth/access_token", data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self._token = token_data.get("access_token")
                    report_provider_state("snovio", "active", "Credentials accepted.", resp.status)
                    return self._token
                response_text = (await resp.text())[:180]
                state = "invalid_key" if resp.status in (400, 401) else "cooldown" if resp.status == 429 else "exhausted" if resp.status in (402, 403) else "unavailable"
                report_provider_state("snovio", state, f"Token request failed ({resp.status}): {response_text}", resp.status)
        return None

    async def find_emails(self, domain: str, name: Optional[str] = None) -> List[Dict[str, Any]]:
        token = await self._get_token()
        if not token:
            return []
            
        contacts = []
        async with aiohttp.ClientSession() as session:
            # Domain search
            url = f"{self.base_url}/v2/domain-emails-with-info"
            params = {
                "access_token": token,
                "domain": domain,
                "type": "personal", # get personal emails if possible, or all
                "limit": 5
            }
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    report_provider_state("snovio", "active", "Domain email search completed.", resp.status)
                    data = await resp.json()
                    for p in data.get("emails", []):
                        contacts.append({
                            "first_name": p.get("firstName"),
                            "last_name": p.get("lastName"),
                            "email": p.get("email"),
                            "title": p.get("position"),
                            "linkedin_url": p.get("sourcePage"),
                            "phone": None,
                            "mobile": None,
                            "contact_type": "professional",
                            "source": "snovio"
                        })
                else:
                    response_text = (await resp.text())[:180]
                    state = "cooldown" if resp.status == 429 else "exhausted" if resp.status in (402, 403) else "invalid_key" if resp.status == 401 else "unavailable"
                    report_provider_state("snovio", state, f"Domain email search failed ({resp.status}): {response_text}", resp.status)
        return contacts
