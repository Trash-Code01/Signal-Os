from core.runtime import IS_STAGING
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from core.provider_health import report_provider_state

class SerperSearchProvider:
    """Public Google-result fallback for decision-maker discovery."""

    base_url = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = "" if IS_STAGING else os.environ.get("SERPER_API_KEY", "").strip()

    async def search_decision_makers(self, business_name: str, city: Optional[str] = None, official_domain: Optional[str] = None, include_email: bool = False, include_phone: bool = False) -> List[Dict[str, Any]]:
        if not self.api_key or not business_name:
            if not self.api_key:
                report_provider_state("serper", "not_configured", "SERPER_API_KEY is missing.")
            return []

        location = (city or "").strip()
        queries = []
        if official_domain:
            queries.append(f'site:{official_domain} (owner OR founder OR CEO OR president)')
        
        queries.extend([
            f'"{business_name}" "{location}" (owner OR founder OR CEO OR president)',
            f'site:linkedin.com/in "{business_name}" (owner OR founder OR CEO OR president)',
        ])
        
        if include_email or include_phone:
            fields = " ".join(field for enabled, field in [(include_email, "email"), (include_phone, "direct phone mobile")] if enabled)
            queries = [f'"{business_name}" "{location}" (owner OR founder OR CEO) ({fields})']
        contacts: List[Dict[str, Any]] = []
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for query in queries:
                try:
                    async with session.post(self.base_url, json={"q": query, "num": 10}) as response:
                        if response.status != 200:
                            state = "cooldown" if response.status == 429 else "exhausted" if response.status in (402, 403) else "invalid_key" if response.status == 401 else "unavailable"
                            report_provider_state("serper", state, f"Public decision-maker search failed ({response.status}).", response.status)
                            continue
                        payload = await response.json()
                        report_provider_state("serper", "active", "Public decision-maker search completed.", response.status)
                except Exception:
                    continue
                for result in payload.get("organic") or []:
                    contact = self._extract_person(
                        result.get("title") or "",
                        result.get("snippet") or "",
                        result.get("link") or "",
                        business_name,
                        location,
                        official_domain
                    )
                    if contact:
                        # Only attach details explicitly present in the same source snippet.
                        snippet = result.get("snippet") or ""
                        if include_email:
                            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", snippet)
                            contact["email"] = emails[0].lower() if emails else None
                        if include_phone:
                            phone = re.search(r"(?:direct(?:\s+phone)?|mobile|cell)\s*[:=]?\s*(\+?[\d(][\d\s().-]{7,}\d)", snippet, re.I)
                            candidate = phone.group(1).strip() if phone else None
                            digits = re.sub(r"\D", "", candidate or "")
                            contact["phone"] = candidate if 8 <= len(digits) <= 15 else None
                        contacts.append(contact)
                        
        deduped = self._dedupe(contacts)
        # Keep the full verified result set so the dossier can show every
        # owner/decision maker and their role, not just the first match.
        return deduped[:5]

    @staticmethod
    def _is_valid_person_name(first_name: str, last_name: str, business_name: str) -> bool:
        full_name = f"{first_name} {last_name}".lower()
        stopwords = {"operated", "since", "details", "company", "roofing", "service", "contact", "about", "home", "llc", "inc", "ltd", "team", "menu", "restaurant", "bar"}
        if any(word in full_name.split() for word in stopwords):
            return False
            
        biz_tokens = set(business_name.lower().split())
        if all(token in biz_tokens for token in full_name.split()):
            return False
            
        if not (2 <= len(full_name.split()) <= 4):
            return False
            
        return True

    @staticmethod
    def _verify_business_binding(title: str, snippet: str, url: str, business_name: str, city: str, official_domain: Optional[str]) -> bool:
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        biz_lower = business_name.lower().replace("llc", "").replace("inc", "").strip()
        city_lower = (city or "").lower().strip()
        
        if official_domain:
            try:
                parsed_url = urlparse(url)
                if parsed_url.hostname and (parsed_url.hostname.lower() == official_domain.lower() or parsed_url.hostname.lower().endswith("." + official_domain.lower())):
                    return True
            except Exception:
                pass
                
        if "linkedin.com/in/" in url.lower():
            if biz_lower in title_lower or biz_lower in snippet_lower:
                return True
                
        if biz_lower in title_lower or biz_lower in snippet_lower:
            if city_lower and (city_lower in title_lower or city_lower in snippet_lower):
                return True
            if not city_lower:
                return True
                
        return False

    def _extract_person(self, title: str, snippet: str, url: str, business_name: str, city: str, official_domain: Optional[str]) -> Optional[Dict[str, Any]]:
        if not self._verify_business_binding(title, snippet, url, business_name, city, official_domain):
            return None
            
        if "linkedin.com/in/" in url.lower():
            clean_title = re.sub(r" \| LinkedIn", "", title)
            parts = re.split(r"\s+[-|]\s+", clean_title)
            if len(parts) >= 1:
                name_parts = parts[0].strip().split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = " ".join(name_parts[1:])
                    role = parts[1].strip() if len(parts) >= 2 else "Professional"
                    role = role.split(" at ")[0].strip()
                    
                    if self._is_valid_person_name(first_name, last_name, business_name):
                        return {
                            "first_name": first_name.title(),
                            "last_name": last_name.title(),
                            "title": role.title(),
                            "linkedin_url": url,
                            "contact_type": "professional",
                            "verification_status": "needs_review",
                            "confidence": 0.75,
                            "source": "serper_public_evidence",
                            "source_url": url,
                        }

        leadership = r"Owner|Co[- ]?Owner|Founder|Co[- ]?Founder|CEO|Chief Executive(?: Officer)?|President|Principal|Partner|Managing Director|Director|General Manager"
        name = r"[A-Z][A-Za-zA-Z\.\-\']+(?:\s+[A-Z][A-Za-zA-Z\.\-\']+){1,3}"
        text = f"{title}\n{snippet}"
        patterns = [
            (rf"(?P<name>{name})\s*(?:,|\||\-)\s*(?P<title>{leadership})\b", False),
            (rf"\b(?P<title>{leadership})\s*[:\-]\s*(?P<name>{name})", False),
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
            
            first_name = parts[0]
            last_name = " ".join(parts[1:])
            
            if self._is_valid_person_name(first_name, last_name, business_name):
                return {
                    "first_name": first_name.title(),
                    "last_name": last_name.title(),
                    "title": role.title(),
                    "linkedin_url": None,
                    "contact_type": "professional",
                    "verification_status": "needs_review",
                    "confidence": 0.70,
                    "source": "serper_public_evidence",
                    "source_url": url,
                }
        return None

    @staticmethod
    def _dedupe(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[str, Dict[str, Any]] = {}
        for contact in contacts:
            key = f"{contact['first_name'].lower()} {contact['last_name'].lower()}"
            if key not in unique or (contact.get("linkedin_url") and not unique[key].get("linkedin_url")):
                unique[key] = contact
        return sorted(list(unique.values()), key=lambda x: x.get("confidence", 0), reverse=True)
