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
