import os
import aiohttp
import urllib.parse
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
        
        if not account:
            api_key = os.environ.get("APOLLO_API_KEY", "FUc0sLL0bqT181HhTUm0WQ").strip()
            if api_key:
                account = ProviderAccount(
                    provider_name="apollo",
                    api_key_ref=api_key,
                    status="active",
                    usage_today=0,
                    limit_per_day=50
                )
                self.db.add(account)
                self.db.commit()
                self.db.refresh(account)
                
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
        self.base_url = "https://api.apollo.io/api/v1"
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
        return os.environ.get("APOLLO_API_KEY", "FUc0sLL0bqT181HhTUm0WQ"), None

    @staticmethod
    def _contact_from_person(person: Dict[str, Any]) -> Dict[str, Any]:
        """Map returned Apollo facts to the CRM contact shape."""
        if isinstance(person.get("person"), dict):
            person = person["person"]
        phone_numbers = person.get("phone_numbers") or []
        if isinstance(phone_numbers, dict):
            phone_numbers = [phone_numbers]
        first_phone = phone_numbers[0] if phone_numbers else {}
        if isinstance(first_phone, str):
            first_phone = {"raw_number": first_phone}
        personal_emails = person.get("personal_emails") or []
        return {
            "email": person.get("email") or (personal_emails[0] if personal_emails else None),
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "title": person.get("title") or person.get("headline"),
            "phone": person.get("phone") or first_phone.get("sanitized_number") or first_phone.get("raw_number"),
            "mobile": person.get("mobile_phone") or first_phone.get("sanitized_number") or first_phone.get("raw_number"),
            "linkedin_url": person.get("linkedin_url"),
            "contact_type": "professional",
            "verification_status": "verified" if person.get("email_status") == "verified" else "unknown",
            "confidence": 0.95,
            "source": "apollo",
        }

    async def _handle_error(self, response: aiohttp.ClientResponse, account: Optional[ProviderAccount]) -> List[Dict[str, Any]]:
        details = (await response.text())[:300]
        if response.status == 429:
            print("ApolloProvider: Rate Limit Hit (429). Initiating cooldown.")
            if self.pool and account:
                self.pool._mark_cooldown(account, minutes=60)
        elif response.status in (401, 403):
            print(f"ApolloProvider: Auth or API-scope error {response.status}. {details}")
            if self.pool and account:
                account.status = "exhausted"
                self.db.commit()
        else:
            print(f"Apollo API error: {response.status} {details}")
        return []

    async def find_emails(self, domain: str, name: Optional[str] = None, business_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Find decision-maker contacts via Apollo.

        Strategy:
        1. Try the free-plan endpoint (/mixed_people/search, POST JSON).
           Returns name, title, email (if plan reveals it), LinkedIn URL.
        2. If the account has Bulk People Enrichment scope, follow up with
           /people/bulk_match to get richer email/phone data.
        Both calls fall back gracefully on 403 (plan restriction).
        """
        api_key, account = await self._get_api_key()

        if not api_key:
            print("ApolloProvider: No API key configured. Skipping enrichment.")
            return []

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
            "X-Api-Key": api_key,
        }

        payload: Dict[str, Any] = {
            "q_organization_domains": [domain],
            "person_titles": ["owner", "founder", "ceo", "president", "managing director"],
            "person_seniorities": ["c_suite", "owner"],
            "per_page": 5,
        }
        if name:
            payload["q_keywords"] = name

        try:
            async with aiohttp.ClientSession() as session:
                # ── Step 1: People Search (free plan) ─────────────────────
                async with session.post(
                    f"{self.base_url}/mixed_people/search",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 403:
                        details = (await response.text())[:400]
                        print(f"ApolloProvider: Search 403 — key lacks scope or is invalid. {details}")
                        return []
                    if response.status != 200:
                        return await self._handle_error(response, account)

                    data = await response.json()
                    people = data.get("people", [])[:5]

                if not people:
                    return []

                # If the search already returned emails (some plans do), use them.
                has_emails = any(p.get("email") for p in people)

                if has_emails:
                    if self.pool and account:
                        self.pool._increment_usage(account)
                    return [self._contact_from_person(p) for p in people]

                # ── Step 2: Bulk Enrichment (paid plan, optional) ──────────
                # Try to enrich via bulk_match to get work emails.  If the plan
                # doesn't include this endpoint we fall back to whatever the
                # search gave us (name + title + LinkedIn).
                person_ids = [p.get("id") for p in people if p.get("id")]
                if not person_ids:
                    return [self._contact_from_person(p) for p in people]

                enrich_payload = {
                    "details": [{"id": pid} for pid in person_ids],
                    "reveal_personal_emails": os.environ.get("APOLLO_REVEAL_PERSONAL_EMAILS", "false").lower() == "true",
                }
                async with session.post(
                    f"{self.base_url}/people/bulk_match",
                    headers=headers,
                    json=enrich_payload,
                ) as enrich_resp:
                    if enrich_resp.status == 403:
                        # Paid scope not available — use search-only results
                        print("ApolloProvider: Bulk enrichment 403 (paid scope). Using search-only results (name/title/LinkedIn).")
                        if self.pool and account:
                            self.pool._increment_usage(account)
                        return [self._contact_from_person(p) for p in people]
                    if enrich_resp.status != 200:
                        await self._handle_error(enrich_resp, account)
                        # Still return whatever the search gave us
                        return [self._contact_from_person(p) for p in people]

                    enrich_data = await enrich_resp.json()
                    matches = enrich_data.get("matches") or enrich_data.get("people") or []
                    if self.pool and account:
                        self.pool._increment_usage(account)
                    return [self._contact_from_person(m) for m in matches] if matches else [self._contact_from_person(p) for p in people]

        except Exception as exc:
            print(f"ApolloProvider: Unexpected error — {exc}")
            return []
