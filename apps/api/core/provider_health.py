"""Small, failure-tolerant provider health registry for the operator UI."""

from __future__ import annotations

from typing import Optional

from .database import SessionLocal
from .models import ProviderHealth


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
