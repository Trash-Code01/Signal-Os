import os
import aiohttp
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, nullslast
from typing import List, Dict, Any, Optional

from core.models import ProviderAccount
from core.providers import EmailProvider


class ApolloProviderPool:
    """Manages rotation, limits, and cooldowns for Apollo.io API keys."""

    def __init__(self, db: Session):
        self.db = db

    def _get_active_account(self) -> Optional[ProviderAccount]:
        """Find an active account under limits and not in cooldown, using LRU round-robin."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.provider_name == "apollo",
                ProviderAccount.status == "active",
                ProviderAccount.usage_today < func.coalesce(ProviderAccount.limit_per_day, 50),
                (ProviderAccount.cooldown_until == None) | (ProviderAccount.cooldown_until < now),
            )
            .order_by(nullslast(ProviderAccount.last_request_at.asc()), ProviderAccount.id.asc())
            .first()
        )

    def _mark_cooldown(self, account: ProviderAccount, minutes: int = 60):
        account.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        account.status = "cooldown"
        self.db.commit()

    def _mark_exhausted(self, account: ProviderAccount):
        account.status = "exhausted"
        self.db.commit()

    def _increment_usage(self, account: ProviderAccount):
        account.usage_today = (account.usage_today or 0) + 1
        account.last_request_at = datetime.now(timezone.utc)
        self.db.commit()


class ApolloProvider(EmailProvider):
    """
    Apollo.io enrichment provider.

    Strategy (industry-standard, free-plan compatible):
    ─────────────────────────────────────────────────────
    1.  Targeted owner lookup — when a named owner (first + last name) is already
        known (found via Serper), we search Apollo by name + domain.
        Endpoint: POST /api/v1/people/search  ← free plan compatible
        This costs ~1 credit vs 5+ for a domain-only scan.

    2.  Domain-only fallback — when no named owner is known, search by domain
        for C-suite/owner titles.
        Same endpoint: POST /api/v1/people/search

    403 handling — IMPORTANT:
    A 403 from Apollo on the free plan means "this feature is not available on
    your plan", NOT that the API key is invalid.  We must NOT mark the key as
    exhausted — all three keys share the same plan restriction.  We simply return
    an empty list and move on.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.base_url = "https://api.apollo.io/api/v1"
        self.db = db_session
        self.pool = ApolloProviderPool(self.db) if self.db else None

    async def _get_api_key(self) -> tuple[Optional[str], Optional[ProviderAccount]]:
        """Get API key from pool (LRU rotation) or env fallback."""
        if self.pool:
            account = self.pool._get_active_account()
            if account:
                return account.api_key_ref, account
        env_key = os.environ.get("APOLLO_API_KEY", "").strip()
        return (env_key or None, None)

    @classmethod
    def _contact_from_person(cls, person: Dict[str, Any]) -> Dict[str, Any]:
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
            "mobile": person.get("mobile_phone") or first_phone.get("sanitized_number"),
            "linkedin_url": person.get("linkedin_url"),
            "contact_type": "professional",
            "verification_status": "verified" if person.get("email_status") == "verified" else "unknown",
            "confidence": 0.95,
            "source": "apollo",
        }

    @classmethod
    def _contacts_from_people(cls, people: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        contacts: List[Dict[str, Any]] = []
        seen: set = set()
        for person in people:
            raw = person.get("person") if isinstance(person.get("person"), dict) else person
            base = cls._contact_from_person(raw)
            emails = []
            primary = (raw.get("email") or "").strip().lower()
            if primary:
                emails.append((primary, "professional"))
            for pe in raw.get("personal_emails") or []:
                e = (pe or "").strip().lower()
                if e:
                    emails.append((e, "personal"))
            if not emails:
                key = (base.get("first_name"), base.get("last_name"), base.get("linkedin_url"))
                if key not in seen:
                    seen.add(key)
                    contacts.append(base)
                continue
            for email, ctype in emails:
                key = (email, base.get("first_name"), base.get("last_name"))
                if key not in seen:
                    seen.add(key)
                    c = dict(base)
                    c["email"] = email
                    c["contact_type"] = ctype
                    contacts.append(c)
        return contacts

    async def _do_search(
        self,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        api_key: str,
        account: Optional[ProviderAccount],
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute a /people/search call. None means retry with another account."""
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
            "X-Api-Key": api_key,
        }
        try:
            async with session.post(
                f"{self.base_url}/people/search",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if self.pool and account:
                        self.pool._increment_usage(account)
                    return data.get("people", [])[:5]

                elif response.status == 429:
                    print("ApolloProvider: Rate limited (429). Entering 60-min cooldown.")
                    if self.pool and account:
                        self.pool._mark_cooldown(account, minutes=60)
                    return None

                elif response.status in (401,):
                    # Genuine auth failure — key is bad, mark exhausted
                    details = (await response.text())[:200]
                    print(f"ApolloProvider: Auth error 401. Key invalid. {details}")
                    if self.pool and account:
                        self.pool._mark_exhausted(account)
                    return None

                elif response.status == 403:
                    # Plan restriction — NOT a key error. All keys share the same plan.
                    # Do NOT mark exhausted. Just skip gracefully.
                    details = (await response.text())[:200]
                    print(f"ApolloProvider: 403 plan restriction (not an auth failure). {details}")
                    return []

                else:
                    details = (await response.text())[:200]
                    print(f"ApolloProvider: Unexpected {response.status}. {details}")
                    return []

        except Exception as exc:
            print(f"ApolloProvider: Request error — {exc}")
            return []

    async def find_email_by_name(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> List[Dict[str, Any]]:
        """
        TARGETED lookup: search for a specific named person at a domain.
        Uses ~1 Apollo credit. Preferred path when Serper found the owner name.
        """
        api_key, account = await self._get_api_key()
        if not api_key:
            return []

        payload = {
            "q_organization_domains": [domain],
            "q_keywords": f"{first_name} {last_name}",
            "per_page": 3,
        }
        async with aiohttp.ClientSession() as session:
            for _ in range(3):
                people = await self._do_search(session, payload, api_key, account)
                if people is not None:
                    return self._contacts_from_people(people)
                api_key, account = await self._get_api_key()
                if not api_key:
                    return []
        return []

    async def find_emails(
        self,
        domain: str,
        name: Optional[str] = None,
        business_id: Optional[int] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Domain-level enrichment fallback (no named owner known).
        Searches for C-suite / owner titles at the domain.
        """
        payload: Dict[str, Any] = {
            "q_organization_domains": [domain],
            "person_titles": ["owner", "founder", "ceo", "president", "managing director", "principal"],
            "person_seniorities": ["c_suite", "owner", "founder"],
            "per_page": 5,
        }
        if name:
            payload["q_keywords"] = name

        # If caller already has a name, use the targeted path
        if first_name and last_name:
            return await self.find_email_by_name(first_name, last_name, domain)

        async with aiohttp.ClientSession() as session:
            for _ in range(3):
                api_key, account = await self._get_api_key()
                if not api_key:
                    print("ApolloProvider: No API key configured. Skipping enrichment.")
                    return []
                people = await self._do_search(session, payload, api_key, account)
                if people is not None:
                    return self._contacts_from_people(people)
        return []
