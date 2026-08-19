import os
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import ProviderAccount
from core.providers import EmailProvider

class ApolloProviderPool:
    """Manages rotation, limits, and cooldowns for Apollo.io API keys."""
    
    def __init__(self, db: Session):
        self.db = db
        
    def _get_active_account(self) -> Optional[ProviderAccount]:
        """Find an active account under limits and not in cooldown."""
        now = datetime.now(timezone.utc)
        
        # Simple reset of usage_today if it's a new day (for MVP we'll just check if last_request was yesterday)
        # In a real app this would be a cron job
        
        account = self.db.query(ProviderAccount).filter(
            ProviderAccount.provider_name == "apollo",
            ProviderAccount.status == "active",
            ProviderAccount.usage_today < ProviderAccount.limit_per_day
        ).filter(
            (ProviderAccount.cooldown_until == None) | (ProviderAccount.cooldown_until < now)
        ).first()
        
        return account

    def _mark_cooldown(self, account: ProviderAccount, minutes: int = 60):
        account.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        account.status = "cooldown"
        self.db.commit()
        
    def _increment_usage(self, account: ProviderAccount):
        account.usage_today = (account.usage_today or 0) + 1
        account.last_request_at = datetime.now(timezone.utc)
        self.db.commit()


class ApolloProvider(EmailProvider):
    def __init__(self, db_session: Optional[Session] = None):
        self.base_url = "https://api.apollo.io/v1"
        self.db = db_session
        self.pool = ApolloProviderPool(self.db) if self.db else None

    async def _get_api_key(self) -> tuple[Optional[str], Optional[ProviderAccount]]:
        """Get key from pool or fallback to environment."""
        if self.pool:
            account = self.pool._get_active_account()
            if account and account.api_key_ref:
                # In production, api_key_ref might be an AWS Secret ARN or the actual key.
                # For this MVP, we treat it as the raw key or env var name
                key = os.environ.get(account.api_key_ref, account.api_key_ref)
                return key, account
                
        # Fallback
        return os.environ.get("APOLLO_API_KEY"), None

    async def find_emails(self, domain: str, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Deep decision-maker enrichment and phone/contact data for high-value prospects."""
        api_key, account = await self._get_api_key()
        
        if not api_key:
            print("ApolloProvider: No valid API key available (keys exhausted or not configured). Skipping enrichment.")
            return []
            
        url = f"{self.base_url}/mixed_people/search"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        payload = {
            "q_organization_domains": [domain],
            "person_titles": ["owner", "founder", "ceo", "president"]
        }
        
        if name:
            payload["q_keywords"] = name
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    
                    if response.status == 200:
                        if self.pool and account:
                            self.pool._increment_usage(account)
                            
                        data = await response.json()
                        contacts = []
                        for person in data.get("people", []):
                            phone_numbers = person.get("phone_numbers") or []
                            first_phone = phone_numbers[0] if phone_numbers else {}
                            contacts.append({
                                "email": person.get("email"),
                                "first_name": person.get("first_name"),
                                "last_name": person.get("last_name"),
                                "title": person.get("title"),
                                "phone": person.get("phone") or first_phone.get("sanitized_number") or first_phone.get("raw_number"),
                                "linkedin_url": person.get("linkedin_url"),
                                "contact_type": "professional",
                                "verification_status": "verified" if person.get("email_status") == "verified" else "unknown",
                                "confidence": 0.95,
                                "source": "apollo"
                            })
                        return contacts
                        
                    elif response.status == 429: # Rate Limited
                        print("ApolloProvider: Rate Limit Hit (429). Initiating cooldown.")
                        if self.pool and account:
                            self.pool._mark_cooldown(account, minutes=60)
                        return []
                        
                    elif response.status == 401 or response.status == 403: # Auth error
                        print(f"ApolloProvider: Auth error {response.status}. Key might be invalid or expired.")
                        if self.pool and account:
                            account.status = "exhausted"
                            self.db.commit()
                        return []
                        
                    else:
                        details = (await response.text())[:300]
                        print(f"Apollo API error: {response.status} {details}")
                        return []
                        
        except Exception as e:
            print(f"Error calling Apollo API: {e}")
            return []
