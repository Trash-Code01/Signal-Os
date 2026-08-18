import os
import aiohttp
from typing import List, Dict, Any, Optional
from core.providers import EmailProvider

class ApolloProvider(EmailProvider):
    def __init__(self):
        self.api_key = os.environ.get("APOLLO_API_KEY")
        self.base_url = "https://api.apollo.io/v1"

    async def find_emails(self, domain: str, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Deep decision-maker enrichment and phone/contact data for high-value prospects."""
        if not self.api_key:
            print("Apollo API key not configured. Skipping enrichment.")
            return []
            
        url = f"{self.base_url}/mixed_people/search"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }
        
        payload = {
            "api_key": self.api_key,
            "q_organization_domains": domain,
            "person_titles": ["owner", "founder", "ceo", "president"]
        }
        
        if name:
            payload["q_keywords"] = name
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        contacts = []
                        for person in data.get("people", []):
                            contacts.append({
                                "email": person.get("email"),
                                "first_name": person.get("first_name"),
                                "last_name": person.get("last_name"),
                                "title": person.get("title"),
                                "phone": person.get("phone"), # or sanitized phone number
                                "confidence": 0.95, # Apollo is generally high confidence when email is present
                                "source": "apollo"
                            })
                        return contacts
                    else:
                        print(f"Apollo API error: {response.status}")
                        return []
        except Exception as e:
            print(f"Error calling Apollo API: {e}")
            return []
