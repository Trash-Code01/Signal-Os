"""Small, failure-tolerant provider health registry for the operator UI."""

from __future__ import annotations

from typing import Optional

from .database import SessionLocal
from .models import ProviderHealth


def provider_failure(http_status: int, body: object = None) -> tuple[str, str]:
    """Translate upstream failures without echoing provider response secrets."""
    text = str(body or '').lower()
    if http_status == 402 or any(term in text for term in ('not enough credits', 'insufficient credits', 'ran out of credits', 'quota exceeded', 'insufficient_quota')):
        return 'exhausted', 'Provider credits exhausted. Replenish the account and retry.'
    if http_status == 429:
        return 'cooldown', 'Provider rate limit reached. Retry after the cooldown.'
    if http_status in (401, 403):
        return 'invalid_key', 'Provider rejected the credentials or account permissions.'
    return 'unavailable', f'Provider request failed (HTTP {http_status}).'


def report_provider_state(
    provider_name: str,
    state: str,
    message: Optional[str] = None,
    http_status: Optional[int] = None,
) -> None:
    """Persist a provider state without ever persisting a secret.

    Enrichment must continue even when telemetry storage is unavailable, so
    this deliberately swallows database failures after rolling back.
    """
    db = None
    try:
        db = SessionLocal()
        record = (
            db.query(ProviderHealth)
            .filter(ProviderHealth.provider_name == provider_name)
            .first()
        )
        if not record:
            record = ProviderHealth(provider_name=provider_name)
            db.add(record)
        record.state = state
        record.message = (message or "").strip()[:500] or None
        record.last_http_status = http_status
        db.commit()
    except Exception:
        if db:
            db.rollback()
    finally:
        if db:
            db.close()
