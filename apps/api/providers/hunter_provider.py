import os
import aiohttp
from typing import List, Dict, Any, Optional
from core.providers import EmailProvider

from datetime import datetime, timedelta, timezone

class HunterProvider(EmailProvider):
    _cooldown_until: Optional[datetime] = None

    def __init__(self):
        self.api_key = os.environ.get("HUNTER_API_KEY", "")
        self.base_url = "https://api.hunter.io/v2"

    def _is_in_cooldown(self) -> bool:
        """Return True if Hunter is currently rate-limited and should not be called."""
        return bool(
            HunterProvider._cooldown_until
            and datetime.now(timezone.utc) < HunterProvider._cooldown_until
        )

    async def find_emails(self, domain: str, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find emails for a domain using Hunter.io Domain Search API."""
        if not self.api_key:
            print("Hunter API key not configured. Skipping enrichment.")
            return []
            
        if HunterProvider._cooldown_until and datetime.now(timezone.utc) < HunterProvider._cooldown_until:
            print("Hunter API is in cooldown period due to 429. Skipping enrichment.")
            return []
            
        url = f"{self.base_url}/domain-search"
        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": 5
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        emails = []
                        for email_data in data.get("data", {}).get("emails", []):
                            verification = email_data.get("verification") or {}
                            verification_status = "verified" if verification.get("status") == "valid" else "unknown"
                            emails.append({
                                "email": email_data.get("value"),
                                "first_name": email_data.get("first_name"),
                                "last_name": email_data.get("last_name"),
                                "title": email_data.get("position"),
                                "phone": email_data.get("phone_number"),
                                "linkedin_url": email_data.get("linkedin"),
                                "contact_type": "professional" if (email_data.get("first_name") or email_data.get("last_name")) else "company",
                                "verification_status": verification_status,
                                "confidence": email_data.get("confidence", 0) / 100.0,
                                "source": "hunter"
                            })
                        return emails
                    else:
                        print(f"Hunter API error: {response.status}")
                        if response.status == 429:
                            HunterProvider._cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=60)
                            print("Hunter API rate limited. Entering 60 minute cooldown.")
                        return []
        except Exception as e:
            print(f"Error calling Hunter API: {e}")
            return []
