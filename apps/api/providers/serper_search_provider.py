import os
import re
from typing import Any, Dict, List, Optional

import aiohttp


class SerperSearchProvider:
    """Public Google-result fallback for decision-maker discovery.

    It returns only names and roles explicitly present in a result title or
    snippet. Contact details are deliberately never guessed from a name.
    """

    base_url = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.environ.get("SERPER_API_KEY", "").strip()

    async def search_decision_makers(self, business_name: str, city: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.api_key or not business_name:
            return []

        location = (city or "").strip()
        queries = [
            f'"{business_name}" "{location}" (owner OR founder OR CEO OR president)',
            f'site:linkedin.com/in "{business_name}" (owner OR founder OR CEO OR president)',
        ]
        contacts: List[Dict[str, Any]] = []
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for query in queries:
                try:
                    async with session.post(self.base_url, json={"q": query, "num": 10}) as response:
                        if response.status != 200:
                            details = (await response.text())[:300]
                            print(f"SerperSearchProvider error {response.status}: {details}")
                            continue
                        payload = await response.json()
                except Exception as exc:
                    print(f"SerperSearchProvider request failed: {exc}")
                    continue
                for result in payload.get("organic") or []:
                    contact = self._extract_person(
                        result.get("title") or "",
                        result.get("snippet") or "",
                        result.get("link") or "",
                    )
                    if contact:
                        contacts.append(contact)
        return self._dedupe(contacts)

    @staticmethod
    def _extract_person(title: str, snippet: str, url: str) -> Optional[Dict[str, Any]]:
        leadership = r"Owner|Co[- ]?Owner|Founder|Co[- ]?Founder|CEO|Chief Executive(?: Officer)?|President|Principal|Partner|Managing Director|Director|General Manager"
        name = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'.-]+(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'.-]+){1,3}"
        text = f"{title}\n{snippet}"
        patterns = [
            (rf"(?P<name>{name})\s*(?:,|\||—|–|-)\s*(?P<title>{leadership})\b", False),
            (rf"\b(?P<title>{leadership})\s*[:—–-]\s*(?P<name>{name})", False),
            (rf"\bfounded\s+by\s+(?P<name>{name})\b", True),
            (rf"\b(?P<name>{name})\s+founded\b", True),
        ]
        for pattern, founder_pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            full_name = re.sub(r"\s+", " ", match.group("name").strip(" \t\n,|:-"))
            parts = full_name.split()
            if len(parts) < 2:
                continue
            role = "Founder" if founder_pattern else re.sub(r"\s+", " ", match.group("title").strip())
            return {
                "first_name": parts[0],
                "last_name": " ".join(parts[1:]),
                "title": role,
                "linkedin_url": url if "linkedin.com/in/" in url.lower() else None,
                "contact_type": "professional",
                "verification_status": "unknown",
                "confidence": 0.82,
                "source": "serper_google_search",
                "source_url": url,
            }
        return None

    @staticmethod
    def _dedupe(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[str, Dict[str, Any]] = {}
        for contact in contacts:
            key = f"{contact['first_name'].lower()} {contact['last_name'].lower()}|{contact['title'].lower()}"
            if key not in unique or (contact.get("linkedin_url") and not unique[key].get("linkedin_url")):
                unique[key] = contact
        return list(unique.values())
