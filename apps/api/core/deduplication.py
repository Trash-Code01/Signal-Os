"""Deterministic, provider-agnostic business deduplication."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _normalise_domain(value: Any) -> str:
    raw = _normalise_text(value)
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return parsed.netloc.removeprefix("www.").rstrip(".")


def _normalise_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    # A leading US country code should not make the same local number unique.
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def _identity_keys(business: Dict[str, Any]) -> Iterable[str]:
    """Build stable identities, preferring independently verifiable facts."""
    domain = _normalise_domain(business.get("website_url") or business.get("domain"))
    phone = _normalise_phone(business.get("primary_phone") or business.get("phone"))
    name = _normalise_text(business.get("name"))
    location = "|".join(filter(None, (
        _normalise_text(business.get("address")),
        _normalise_text(business.get("city")),
        _normalise_text(business.get("state_province")),
        _normalise_text(business.get("country")),
    )))
    if domain:
        yield f"domain:{domain}"
    if len(phone) >= 7:
        yield f"phone:{phone}"
    # A name alone is too weak; combine it with a discovered location.
    if name and location:
        yield f"name_location:{name}|{location}"


class DeduplicationEngine:
    """Remove duplicate businesses returned by one discovery run.

    Persistent deduplication is handled by the worker's database lookup before
    insert. This class intentionally handles only the provider batch and has
    no database dependency, making it deterministic and easy to test.
    """

    def deduplicate(self, raw_businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique_businesses: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for business in raw_businesses:
            keys = list(_identity_keys(business))
            if keys and any(key in seen for key in keys):
                continue
            unique_businesses.append(business)
            seen.update(keys)

        return unique_businesses


def find_existing_business(db: Any, business_data: Dict[str, Any], owner_id: Optional[int] = None) -> Optional[Any]:
    """Locate an existing business record matching any stable identity tier.
    
    Tiers checked in order of reliability:
    1. Google Place ID / CID
    2. Normalized Web Domain
    3. Normalized Primary Phone Number
    4. Normalized Business Name + City
    """
    from sqlalchemy import func
    from core.models import Business

    query = db.query(Business).filter(Business.deleted_at.is_(None))
    if owner_id is not None:
        query = query.filter(Business.owner_id == owner_id)

    # 1. Google Place ID
    place_id = str(business_data.get("google_place_id") or "").strip()
    if place_id:
        match = query.filter(Business.google_place_id == place_id).first()
        if match:
            return match

    # 2. Normalized Domain
    raw_url = business_data.get("website_url") or business_data.get("website_domain") or business_data.get("domain")
    domain = _normalise_domain(raw_url)
    if domain:
        match = query.filter(Business.website_domain == domain).first()
        if match:
            return match
        # Check against website_url if website_domain was not indexed or null
        match = query.filter(func.lower(Business.website_url).ilike(f"%{domain}%")).first()
        if match:
            return match

    # 3. Normalized Phone
    raw_phone = business_data.get("primary_phone") or business_data.get("phone")
    phone_digits = _normalise_phone(raw_phone)
    if len(phone_digits) >= 7:
        # Check direct match on primary_phone first
        if raw_phone:
            match = query.filter(Business.primary_phone == str(raw_phone).strip()).first()
            if match:
                return match
        # Match across formatted phone strings (e.g. "+1 214-555-4321" vs "(214) 555-4321")
        last4 = phone_digits[-4:]
        candidates = query.filter(Business.primary_phone.isnot(None), Business.primary_phone.ilike(f"%{last4}%")).all()
        target_last7 = phone_digits[-7:]
        for cand in candidates:
            if not cand.primary_phone:
                continue
            cand_digits = _normalise_phone(cand.primary_phone)
            # Match if full normalized digits match or last 7 digits match (local number equivalence)
            if cand_digits == phone_digits or (len(cand_digits) >= 7 and cand_digits[-7:] == target_last7):
                return cand

    # 4. Normalized Name + City
    name_clean = _normalise_text(business_data.get("name"))
    city_clean = _normalise_text(business_data.get("city"))
    if name_clean and city_clean:
        match = query.filter(
            func.lower(Business.normalized_name) == name_clean,
            func.lower(Business.city) == city_clean
        ).first()
        if match:
            return match
        match = query.filter(
            func.lower(Business.name) == name_clean,
            func.lower(Business.city) == city_clean
        ).first()
        if match:
            return match

    return None
