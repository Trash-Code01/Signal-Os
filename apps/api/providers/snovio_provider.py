import os
import aiohttp
from typing import List, Dict, Any, Optional
from core.providers import EmailProvider

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
                    return self._token
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
        return contacts
