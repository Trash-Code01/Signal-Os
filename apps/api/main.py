from fastapi import FastAPI, Depends, HTTPException, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
from worker import enrich_lead_contacts_task, process_campaign_task
from core.database import get_db, engine
from core.models import *
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
import csv
import io
import json
import os
import re
from auth import router as auth_router

app = FastAPI(title="Devacia Lead Intelligence OS", version="1.0.0")

app.include_router(auth_router)

@app.get("/api/debug-discovery")
def debug_discovery():
    import asyncio
    import os
    from providers.serper_discovery_provider import SerperDiscoveryProvider
    try:
        key = os.environ.get('SERPER_API_KEY', 'MISSING')
        provider = SerperDiscoveryProvider()
        res = asyncio.run(provider.discover('roofing', 'Dallas', 'roofing', 5))
        return {'key_length': len(key) if key != 'MISSING' else 0, 'result_count': len(res), 'sample': res[:1] if res else []}
    except Exception as e:
        return {'error': str(e)}
@app.get("/api/health")
def health_check():
    """Lightweight keepalive endpoint — no DB query, returns instantly."""
    return {"status": "ok"}


@app.post("/api/setup-admin")
def setup_admin(db: Session = Depends(get_db)):
    """Creates the admin user only if NO users exist. Safe bootstrap endpoint."""
    from core.models import User
    from core.auth import get_password_hash
    user_count = db.query(User).count()
    if user_count > 0:
        return {"status": "exists", "message": f"Database already has {user_count} user(s). No action taken."}
    admin = User(email="admin@devacia.com", hashed_password=get_password_hash("admin123"))
    db.add(admin)
    db.commit()
    return {"status": "ok", "message": "Admin user created: admin@devacia.com / admin123"}

MIGRATE_TABLES = {"campaigns", "businesses", "scores", "opportunities", "crm_leads"}

@app.post("/api/migrate-clear")
def migrate_clear(payload: dict, db: Session = Depends(get_db)):
    """Truncates a table with CASCADE."""
    from sqlalchemy import text as sa_text
    table_name = payload.get("table_name")
    if table_name not in MIGRATE_TABLES:
        return {"status": "error", "message": f"Table {table_name} not allowed"}
    try:
        db.execute(sa_text(f"TRUNCATE TABLE {table_name} CASCADE"))
        db.commit()
        return {"status": "ok", "message": f"Truncated {table_name}"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/api/migrate-disable-fk")
def migrate_disable_fk(db: Session = Depends(get_db)):
    """Drops ALL FK constraints on all migration tables so data can be inserted in any order."""
    from sqlalchemy import text as sa_text
    dropped = []
    try:
        # Find all FK constraints on our migration tables
        result = db.execute(sa_text("""
            SELECT tc.table_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name IN ('campaigns','businesses','scores','opportunities','crm_leads')
        """))
        constraints = result.fetchall()
        for table_name, constraint_name in constraints:
            db.execute(sa_text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{constraint_name}"'))
            dropped.append(f"{table_name}.{constraint_name}")
        db.commit()
        return {"status": "ok", "dropped": dropped}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@app.post("/api/migrate-upload")
def migrate_upload(payload: dict, db: Session = Depends(get_db)):
    """Inserts a batch of records into a table. Call migrate-disable-fk first."""
    try:
        from core.models import Base
        table_name = payload.get("table_name")
        records = payload.get("records", [])
        if not records:
            return {"status": "ok", "inserted": 0}

        model_class = next((c for c in Base.registry.mappers if c.class_.__tablename__ == table_name), None)
        if not model_class:
            return {"status": "error", "message": f"Table {table_name} not found"}

        cls = model_class.class_
        for record in records:
            db.merge(cls(**record))
        db.commit()
        return {"status": "ok", "inserted": len(records)}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}


@app.on_event("startup")
def ensure_crm_workspace_schema() -> None:
    """Create only the new CRM tables for deployments with legacy Alembic history."""
    CRMLead.__table__.create(bind=engine, checkfirst=True)
    CRMActivity.__table__.create(bind=engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaigns_deleted_at ON campaigns (deleted_at)"))
        conn.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_businesses_deleted_at ON businesses (deleted_at)"))
        conn.execute(text("ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_crm_leads_deleted_at ON crm_leads (deleted_at)"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _apollo_webhook_people(payload: object) -> List[dict]:
    """Accept the documented Apollo webhook variants without trusting invented data."""
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("matches") or payload.get("people") or payload.get("data") or []
    if isinstance(candidates, dict):
        candidates = candidates.get("matches") or candidates.get("people") or [candidates]
    if not isinstance(candidates, list):
        candidates = []
    people: List[dict] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        person = candidate.get("person") if isinstance(candidate.get("person"), dict) else candidate
        if any(person.get(field) for field in ("email", "phone_numbers", "phone", "mobile_phone", "first_name", "last_name")):
            people.append(person)
    return people


@app.post("/api/webhooks/apollo")
async def receive_apollo_webhook(
    request: Request,
    business_id: int = Query(..., gt=0),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Persist asynchronous Apollo phone/waterfall enrichment for one business."""
    expected_token = os.environ.get("APOLLO_WEBHOOK_SECRET", "").strip()
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid Apollo webhook token")
    if not db.query(Business.id).filter(Business.id == business_id).first():
        raise HTTPException(status_code=404, detail="Business not found")

    payload = await request.json()
    saved = 0
    for person in _apollo_webhook_people(payload):
        phones = person.get("phone_numbers") or []
        if isinstance(phones, dict):
            phones = [phones]
        first_phone = phones[0] if phones else {}
        if isinstance(first_phone, str):
            first_phone = {"raw_number": first_phone}
        email = (person.get("email") or "").strip().lower() or None
        phone = person.get("phone") or person.get("mobile_phone") or first_phone.get("sanitized_number") or first_phone.get("raw_number")
        if not email and not phone:
            continue
        contact = (
            db.query(DecisionMaker)
            .filter(DecisionMaker.business_id == business_id)
            .filter(DecisionMaker.email == email if email else DecisionMaker.phone == phone)
            .first()
        )
        if not contact:
            contact = DecisionMaker(business_id=business_id, source="apollo", contact_type="professional")
            db.add(contact)
            saved += 1
        contact.first_name = person.get("first_name") or contact.first_name
        contact.last_name = person.get("last_name") or contact.last_name
        contact.title = person.get("title") or contact.title
        contact.email = email or contact.email
        contact.phone = phone or contact.phone
        contact.mobile = person.get("mobile_phone") or contact.mobile
        contact.linkedin_url = person.get("linkedin_url") or contact.linkedin_url
        contact.verification_status = "verified" if person.get("email_status") == "verified" else (contact.verification_status or "unknown")
        contact.confidence = max(contact.confidence or 0, 0.95)
    db.commit()
    return {"status": "ok", "contacts_saved": saved}

@app.get("/api/campaigns/{campaign_id}/status")
def get_campaign_status(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    total_target = campaign.target_quantity
    active_business = db.query(Business).filter(
        Business.campaign_id == campaign_id,
        Business.deleted_at.is_(None),
    )
    discovered = active_business.count()
    websites = (
        db.query(Website)
        .join(Business)
        .filter(Business.campaign_id == campaign_id, Business.deleted_at.is_(None))
        .count()
    )
    opportunities = (
        db.query(Opportunity)
        .join(Business)
        .filter(Business.campaign_id == campaign_id, Business.deleted_at.is_(None))
        .count()
    )
    enriched = (
        db.query(DecisionMaker)
        .join(Business)
        .filter(Business.campaign_id == campaign_id, Business.deleted_at.is_(None))
        .count()
    )
    qualified = active_business.filter(Business.status == "qualified").count()
    needs_review = active_business.filter(Business.status.in_([
        "needs_review", "needs_official_website", "needs_research", "needs_contact_enrichment"
    ])).count()
    rejected = active_business.filter(Business.status.like("rejected%")).count()
    terminal_statuses = {"completed", "completed_partial", "needs_review", "failed"}
    is_terminal = campaign.status in terminal_statuses
    is_running = campaign.status == "processing"

    # Stage statuses are independent; each reflects its own data only.
    # discovery: done if any businesses were found
    discovery_status = (
        "done" if discovered > 0
        else "running" if is_running
        else "pending"
    )

    # crawler: done if all discovered businesses have a Website record or were skipped (no website / unreachable)
    skipped_crawl = active_business.filter(
        Business.status.in_(["needs_official_website", "rejected_no_website", "rejected_unreachable"])
    ).count()
    businesses_needing_crawl = max(0, discovered - skipped_crawl)
    crawler_status = (
        "done" if is_terminal and discovered > 0
        else "done" if discovered > 0 and websites >= businesses_needing_crawl and businesses_needing_crawl > 0
        else "running" if discovered > 0 and is_running and websites < discovered
        else "pending"
    )

    # ai_sdr: done if terminal (AI ran; some may have passed, some failed with needs_research)
    # running if crawler is done and campaign is still processing
    ai_status = (
        "done" if is_terminal and websites > 0
        else "running" if websites > 0 and is_running
        else "pending"
    )

    # enrichment: done if terminal; running if opportunities exist and still processing
    enrichment_status = (
        "done" if is_terminal and (enriched > 0 or opportunities > 0)
        else "running" if opportunities > 0 and is_running
        else "pending"
    )

    stages = [
        {"key": "discovery",   "label": "Business Discovery & Deduplication", "status": discovery_status,   "count": discovered,   "total": total_target},
        {"key": "crawler",     "label": "Website Crawl & UX Audit",           "status": crawler_status,     "count": websites,     "total": discovered},
        {"key": "ai_sdr",      "label": "AI SDR Analysis & Scoring",          "status": ai_status,          "count": opportunities,"total": websites},
        {"key": "enrichment",  "label": "Contact Enrichment",                 "status": enrichment_status,  "count": enriched,     "total": opportunities},
    ]
    
    return {
        "status": campaign.status,
        "terminal": is_terminal,
        "campaign_id": campaign.id,
        "name": campaign.name,
        "stats": {
            "discovered": discovered,
            "qualified": qualified,
            "opportunities": opportunities,
            "enriched": enriched,
            "needs_review": needs_review,
            "rejected": rejected,
            "target": total_target,
        },
        "summary": f"{qualified} qualified / {total_target} target, {needs_review} need review, {rejected} rejected.",
        "stages": stages
    }


class CampaignCreateRequest(BaseModel):

    name: str
    country: str
    state_province: Optional[str] = None
    cities: List[str]
    industry: str
    target_quantity: int
    min_quality_score: int
@app.get("/api/sync-sequences")
def sync_sequences(db: Session = Depends(get_db)):
    from sqlalchemy import text
    tables = [
        "industry_configs", "campaigns", "campaign_locations", 
        "provider_accounts", "job_runs", "businesses", 
        "business_sources", "decision_makers", "scores", 
        "opportunities", "crm_leads", "crm_activities"
    ]
    for table in tables:
        try:
            db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table};"))
        except Exception as e:
            print(f"Failed on {table}: {e}")
    db.commit()
    return {"status": "synced"}


@app.post("/api/campaigns")

def create_and_start_campaign(req: CampaignCreateRequest, db: Session = Depends(get_db)):
    try:
        # Create industry config if it doesn't exist
        industry = db.query(IndustryConfig).filter(IndustryConfig.name == req.industry).first()
        if not industry:
            industry = IndustryConfig(name=req.industry)
            db.add(industry)
            db.commit()
            db.refresh(industry)
    
        # Create campaign
        campaign = Campaign(
            name=req.name,
            industry_id=industry.id,
            target_quantity=req.target_quantity,
            min_quality_score=req.min_quality_score,
            status="processing"
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
    
        # Add locations
        from core.models import CampaignLocation
        for city in req.cities:
            loc = CampaignLocation(
                campaign_id=campaign.id,
                country=req.country,
                region_state=req.state_province,
                city=city
            )
            db.add(loc)
        db.commit()
    
        # Trigger worker
        from worker import process_campaign_task
        task = process_campaign_task.apply_async(args=[campaign.id], queue='devacia_queue')
        return {"status": "accepted", "campaign_id": campaign.id, "task_id": task.id}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=error_details)

CRM_STAGES = ("new", "reviewing", "contacted", "qualified", "needs_review", "proposal", "won", "lost", "archived")


class CRMLeadUpdate(BaseModel):
    stage: Optional[str] = None
    owner_name: Optional[str] = None
    tags: Optional[List[str]] = None
    next_follow_up_at: Optional[datetime] = None


class CRMLeadBulkUpdate(BaseModel):
    lead_ids: List[int]
    stage: str


class CRMActivityCreate(BaseModel):
    body: str


class CRMLeadCreate(BaseModel):
    name: str
    website_url: Optional[str] = None
    primary_phone: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    stage: str = "new"
    owner_name: Optional[str] = None
    tags: List[str] = []
    commercial_score: Optional[int] = None
    primary_problem: Optional[str] = None
    recommended_offer: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_title: Optional[str] = None


def _normalise_stage(stage: Optional[str]) -> str:
    value = (stage or "new").strip().lower().replace(" ", "_")
    aliases = {"raw": "new", "processing": "reviewing", "contact": "contacted", "closed_won": "won", "closed_lost": "lost", "needs_research": "needs_review", "needs_official_website": "needs_review", "needs_contact_enrichment": "needs_review", "researching": "needs_review"}
    value = aliases.get(value, value)
    return value if value in CRM_STAGES else "new"


def _normalise_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    return list(dict.fromkeys(tag.strip() for tag in tags if tag and tag.strip()))[:12]


def _format_contact(contact: DecisionMaker) -> dict:
    name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    return {
        "id": contact.id,
        "name": name or contact.email or "Unknown contact",
        "email": contact.email,
        "phone": contact.phone or contact.mobile,
        "title": contact.title,
        "verification_status": contact.verification_status,
        "linkedin_url": contact.linkedin_url,
        "contact_type": contact.contact_type,
        "source": contact.source,
        "source_url": contact.source_url,
        "confidence": contact.confidence,
    }


def _ensure_crm_records(db: Session) -> None:
    """Backfill CRM state for campaign leads created before the CRM existed."""
    missing_businesses = (
        db.query(Business.id, Business.status)
        .outerjoin(CRMLead, CRMLead.business_id == Business.id)
        .outerjoin(Campaign, Campaign.id == Business.campaign_id)
        .filter(CRMLead.id.is_(None))
        .filter(Business.deleted_at.is_(None))
        .filter(or_(Campaign.id.is_(None), Campaign.deleted_at.is_(None)))
        .filter(Business.status.in_([
            "qualified", "needs_review", "needs_official_website", "needs_research", "needs_contact_enrichment"
        ]))
        .all()
    )
    if missing_businesses:
        for b_id, b_status in missing_businesses:
            stage = "qualified" if b_status == "qualified" else "needs_review"
            db.add(CRMLead(business_id=b_id, stage=stage, source="campaign"))
        db.commit()


def _contacts_by_business(db: Session, business_ids: List[int]) -> dict:
    grouped = {business_id: [] for business_id in business_ids}
    if not business_ids:
        return grouped
    for contact in db.query(DecisionMaker).filter(DecisionMaker.business_id.in_(business_ids)).all():
        grouped.setdefault(contact.business_id, []).append(_format_contact(contact))
    for business_id, contacts in grouped.items():
        # Prefer a named decision maker, then a professional contact, then a
        # public website inbox. The dossier must not call a generic inbox "Owner".
        contacts.sort(key=lambda contact: (
            contact.get("contact_type") == "company",
            contact.get("name", "").lower().endswith("contact"),
            not bool(contact.get("email")),
        ))
    return grouped


def _display_opportunity_text(value: Optional[str]) -> Optional[str]:
    """Avoid presenting provider failures or placeholder values as lead intelligence."""
    text = _clean_text(value)
    placeholders = {
        "none", "n/a", "null", "good fit", "standard booking system",
        "pitch standard booking system", "no booking system found",
    }
    if not text or text.lower() in placeholders or text.startswith("Error:"):
        return None
    return text


def _clean_text(value) -> str:
    """Clean old mojibake and unsafe display text before it reaches the UI."""
    text_value = "" if value is None else str(value)
    replacements = {
        "\u00c3\u00a2\u00c2\u0080\u00c2\u0093": "-",
        "\u00c3\u00a2\u00c2\u0080\u00c2\u0094": "-",
        "\u00c3\u00a2\u00c2\u0080\u00c2\u00a2": " | ",
        "\u00c3\u00a2\u00c2\u0080\u00c2\u0099": "'",
        "\u00c3\u00a2\u00c2\u0080\u00c2\u009c": '"',
        "\u00c3\u00a2\u00c2\u0080\u00c2\u009d": '"',
        "\u00e2\u0080\u0093": "-",
        "\u00e2\u0080\u0094": "-",
        "\u00e2\u0080\u00a2": " | ",
        "\u00e2\u0080\u0099": "'",
        "\u00c3\u0082\u00c2": "",
        "\u00c2": "",
    }
    for bad, good in replacements.items():
        text_value = text_value.replace(bad, good)
    return text_value.strip()


def _ticket_range(opportunity: Optional[Opportunity]) -> Optional[str]:
    if not opportunity or (opportunity.ticket_low is None and opportunity.ticket_high is None):
        return None
    if opportunity.ticket_low is not None and opportunity.ticket_high is not None:
        return f"${opportunity.ticket_low:,}-${opportunity.ticket_high:,}"
    value = opportunity.ticket_low if opportunity.ticket_low is not None else opportunity.ticket_high
    return f"${value:,}"


def _dossier_priority(score: Optional[Score]) -> str:
    value = score.commercial_score if score else None
    if value is not None and value >= 80:
        return "high"
    if value is not None and value >= 65:
        return "medium"
    return "normal"


def _dossier_audit_metrics(website: Optional[Website], audit: Optional[WebsiteAudit]) -> dict:
    """Provide stable display metrics, using stored values first and audit signals as a fallback."""
    if not website or website.is_live is not True or not audit:
        return {"mobile": None, "desktop": None, "ux": None, "conversion": None}

    mobile = audit.mobile_ux_score
    if mobile is None and audit.mobile_responsive is not None:
        mobile = 80 if audit.mobile_responsive else 35

    desktop = audit.desktop_ux_score
    if desktop is None:
        desktop = 50 if audit.horizontal_overflow else 70

    ux = audit.accessibility_score
    if ux is None and mobile is not None and desktop is not None:
        ux = round((mobile + desktop) / 2)

    conversion = None
    conversion_signals = [audit.contact_form, audit.quote_form, audit.phone_cta, audit.booking_detected, audit.sticky_cta]
    if any(signal is not None for signal in conversion_signals):
        conversion = round(sum(1 for signal in conversion_signals if signal is True) / len(conversion_signals) * 100)

    return {"mobile": mobile, "desktop": desktop, "ux": ux, "conversion": conversion}


def _dossier_page_labels(pages: List[WebsitePage], screenshot_count: int, evidence_count: int) -> List[str]:
    labels = []
    for index, page in enumerate(pages):
        url = (page.url or "").lower()
        label = "Homepage" if index == 0 else None
        if "service" in url:
            label = "Services"
        elif "contact" in url:
            label = "Contact"
        elif any(term in url for term in ("book", "quote", "estimate")):
            label = "Booking"
        elif "about" in url:
            label = "About"
        if label and label not in labels:
            labels.append(label)
    if screenshot_count:
        labels.append("Screenshots")
    if pages:
        labels.append("Crawl data")
    if evidence_count:
        labels.append("Audit findings")
    return labels


def _serialize_crm_lead(
    business: Business,
    opportunity: Optional[Opportunity],
    score: Optional[Score],
    crm_lead: CRMLead,
    campaign: Optional[Campaign],
    contacts: List[dict],
) -> dict:
    industry = business.industry or (campaign.industry.name if campaign and campaign.industry else "Uncategorized")
    location = ", ".join(part for part in [business.city, business.state_province, business.country] if part)
    return {
        "id": business.id,
        "name": business.name,
        "website_url": business.website_url,
        "phone": business.primary_phone,
        "industry": industry,
        "city": business.city,
        "state_province": business.state_province,
        "country": business.country,
        "location": location or "Location not set",
        "stage": _normalise_stage(crm_lead.stage),
        "owner_name": crm_lead.owner_name,
        "tags": _normalise_tags(crm_lead.tags),
        "source": crm_lead.source,
        "campaign_id": campaign.id if campaign else None,
        "campaign_name": campaign.name if campaign else "Imported / manual",
        "commercial_score": score.commercial_score if score else None,
        "data_confidence": score.data_confidence if score else None,
        "grade": score.grade if score else None,
        "primary_problem": _display_opportunity_text(opportunity.primary_problem) if opportunity else None,
        "recommended_offer": _display_opportunity_text(opportunity.recommended_offer) if opportunity else None,
        "outreach_angle": _display_opportunity_text(opportunity.outreach_angle) if opportunity else None,
        "next_follow_up_at": crm_lead.next_follow_up_at.isoformat() if crm_lead.next_follow_up_at else None,
        "last_activity_at": crm_lead.last_activity_at.isoformat() if crm_lead.last_activity_at else None,
        "created_at": business.created_at.isoformat() if business.created_at else None,
        "contacts": contacts,
        "contact_count": len(contacts),
    }


def _get_crm_leads(
    db: Session,
    q: str = "",
    status: str = "active",
    stage: Optional[str] = None,
    grade: Optional[str] = None,
    campaign_id: Optional[int] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    has_contact: Optional[bool] = None,
    min_score: Optional[int] = None,
    qualified_only: bool = False,
    ids: Optional[List[int]] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    _ensure_crm_records(db)
    query = (
        db.query(Business, Opportunity, Score, CRMLead, Campaign)
        .outerjoin(Opportunity, Opportunity.business_id == Business.id)
        .outerjoin(Score, Score.business_id == Business.id)
        .join(CRMLead, CRMLead.business_id == Business.id)
        .outerjoin(Campaign, Campaign.id == Business.campaign_id)
    )

    deleted_filter = or_(
        CRMLead.deleted_at.is_not(None),
        Business.deleted_at.is_not(None),
        Campaign.deleted_at.is_not(None),
    )
    if status == "trash":
        query = query.filter(deleted_filter)
    else:
        query = query.filter(CRMLead.deleted_at.is_(None), Business.deleted_at.is_(None))
        query = query.filter(or_(Campaign.id.is_(None), Campaign.deleted_at.is_(None)))

    if q.strip():
        search = f"%{q.strip()}%"
        query = query.filter(or_(Business.name.ilike(search), Business.website_url.ilike(search), Business.city.ilike(search)))
    if stage and stage != "all":
        query = query.filter(CRMLead.stage == _normalise_stage(stage))
    if grade and grade != "all":
        query = query.filter(Score.grade == grade.upper())
    if campaign_id:
        query = query.filter(Business.campaign_id == campaign_id)
    if industry and industry != "all":
        query = query.filter(Business.industry == industry)
    if country and country != "all":
        query = query.filter(Business.country == country)
    if min_score is not None:
        query = query.filter(func.coalesce(Score.commercial_score, 0) >= min_score)
    if qualified_only:
        # Campaign leads must pass the worker's complete research gate. Manual
        # and imported leads remain visible because the user supplied them.
        query = query.filter(or_(Business.status == "qualified", CRMLead.source.in_(("manual", "import"))))
    if ids:
        query = query.filter(Business.id.in_(ids))
    if has_contact is True:
        query = query.filter(Business.id.in_(db.query(DecisionMaker.business_id).distinct()))
    if has_contact is False:
        query = query.filter(~Business.id.in_(db.query(DecisionMaker.business_id).distinct()))

    total = query.count()
    rows = (
        query.order_by(func.coalesce(CRMLead.updated_at, CRMLead.created_at, Business.created_at).desc(), Business.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    contacts = _contacts_by_business(db, [business.id for business, *_ in rows])
    leads = [
        _serialize_crm_lead(business, opportunity, score, crm_lead, campaign, contacts.get(business.id, []))
        for business, opportunity, score, crm_lead, campaign in rows
    ]
    return {"leads": leads, "total": total, "page": page, "page_size": page_size}


@app.get("/api/crm/leads")
def list_crm_leads(
    q: str = "",
    status: str = "active",
    stage: Optional[str] = None,
    grade: Optional[str] = None,
    campaign_id: Optional[int] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    has_contact: Optional[bool] = None,
    min_score: Optional[int] = None,
    qualified_only: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)

    # Default: show only qualified leads. When user filters by stage, disable qualified gate.
    if qualified_only is None:
        qualified_only = (stage is None) or (stage == "qualified")

    data = _get_crm_leads(
        db, q=q, status=status, stage=stage, grade=grade,
        campaign_id=campaign_id, industry=industry, country=country,
        has_contact=has_contact, min_score=min_score,
        qualified_only=qualified_only, page=page, page_size=page_size,
    )
    campaigns = [
        {"id": c.id, "name": c.name}
        for c in db.query(Campaign).filter(Campaign.deleted_at.is_(None)).order_by(Campaign.created_at.desc()).all()
    ]
    visible_industries = [
        row[0]
        for row in (
            db.query(Business.industry)
            .join(CRMLead, CRMLead.business_id == Business.id)
            .filter(Business.industry.isnot(None))
            .filter(Business.deleted_at.is_(None), CRMLead.deleted_at.is_(None))
            .distinct()
            .all()
        )
        if row[0]
    ]
    data["facets"] = {"campaigns": campaigns, "industries": sorted(visible_industries)}
    return data



@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    """Backward-compatible route for the leads view and existing integrations."""
    return _get_crm_leads(db, qualified_only=True, page_size=200)


def _get_crm_lead_or_404(lead_id: int, db: Session) -> tuple[Business, CRMLead]:
    business = db.query(Business).filter(Business.id == lead_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Lead not found")
    _ensure_crm_records(db)
    crm_lead = db.query(CRMLead).filter(CRMLead.business_id == lead_id).first()
    if not crm_lead:
        raise HTTPException(status_code=404, detail="CRM record not found")
    return business, crm_lead


@app.patch("/api/crm/leads/{lead_id}")
def update_crm_lead(lead_id: int, payload: CRMLeadUpdate, db: Session = Depends(get_db)):
    business, crm_lead = _get_crm_lead_or_404(lead_id, db)
    if "stage" in payload.model_fields_set and payload.stage is not None:
        crm_lead.stage = _normalise_stage(payload.stage)
    if "owner_name" in payload.model_fields_set:
        crm_lead.owner_name = payload.owner_name.strip() or None
    if "tags" in payload.model_fields_set:
        crm_lead.tags = _normalise_tags(payload.tags)
    if "next_follow_up_at" in payload.model_fields_set:
        crm_lead.next_follow_up_at = payload.next_follow_up_at
    crm_lead.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "updated", "lead_id": lead_id}


@app.patch("/api/crm/actions/bulk")
def bulk_update_crm_leads(payload: CRMLeadBulkUpdate, db: Session = Depends(get_db)):
    lead_ids = list(dict.fromkeys(payload.lead_ids))
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Select at least one lead")
    stage = _normalise_stage(payload.stage)
    _ensure_crm_records(db)
    records = db.query(CRMLead).filter(CRMLead.business_id.in_(lead_ids)).all()
    for record in records:
        record.stage = stage
        record.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "updated", "updated": len(records), "stage": stage}


@app.post("/api/crm/leads/{lead_id}/activities")
def create_crm_activity(lead_id: int, payload: CRMActivityCreate, db: Session = Depends(get_db)):
    _, crm_lead = _get_crm_lead_or_404(lead_id, db)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="A note cannot be empty")
    activity = CRMActivity(business_id=lead_id, activity_type="note", body=body, created_by="Workspace")
    crm_lead.last_activity_at = datetime.now(timezone.utc)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return {
        "id": activity.id,
        "type": activity.activity_type,
        "body": activity.body,
        "created_by": activity.created_by,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


def _split_contact_name(name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    parts = (name or "").strip().split(maxsplit=1)
    return (parts[0], parts[1] if len(parts) > 1 else None) if parts else (None, None)


def _find_duplicate_business(db: Session, name: str, website_url: Optional[str], city: Optional[str]) -> Optional[Business]:
    if website_url:
        duplicate = db.query(Business).filter(func.lower(Business.website_url) == website_url.lower()).first()
        if duplicate:
            return duplicate
    return db.query(Business).filter(Business.name == name, Business.city == city).first()


def _create_crm_lead(payload: CRMLeadCreate, db: Session, source: str, activity_body: str) -> tuple[Business, bool]:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Company name is required")
    duplicate = _find_duplicate_business(db, name, payload.website_url, payload.city)
    if duplicate:
        return duplicate, False

    stage = _normalise_stage(payload.stage)
    business = Business(
        name=name,
        industry=payload.industry.strip() if payload.industry else None,
        country=payload.country.strip() if payload.country else None,
        state_province=payload.state_province.strip() if payload.state_province else None,
        city=payload.city.strip() if payload.city else None,
        primary_phone=payload.primary_phone.strip() if payload.primary_phone else None,
        website_url=payload.website_url.strip() if payload.website_url else None,
        status=stage,
    )
    db.add(business)
    db.flush()

    if payload.primary_problem or payload.recommended_offer:
        db.add(Opportunity(
            business_id=business.id,
            primary_problem=payload.primary_problem or "Imported CRM lead",
            recommended_offer=payload.recommended_offer,
            outreach_angle="Imported into the Devacia CRM",
            confidence="imported",
        ))
    if payload.commercial_score is not None:
        score = max(0, min(payload.commercial_score, 100))
        grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C"
        db.add(Score(business_id=business.id, commercial_score=score, data_confidence=50, grade=grade))
    if payload.contact_name or payload.contact_email or payload.contact_phone:
        first_name, last_name = _split_contact_name(payload.contact_name)
        db.add(DecisionMaker(
            business_id=business.id,
            first_name=first_name,
            last_name=last_name,
            title=payload.contact_title,
            email=payload.contact_email,
            phone=payload.contact_phone,
            source=source,
            verification_status="unknown",
        ))
    db.add(CRMLead(
        business_id=business.id,
        stage=stage,
        owner_name=payload.owner_name.strip() if payload.owner_name else None,
        tags=_normalise_tags(payload.tags),
        source=source,
        last_activity_at=datetime.now(timezone.utc),
    ))
    db.add(CRMActivity(business_id=business.id, activity_type="created", body=activity_body, created_by="Workspace"))
    db.commit()
    db.refresh(business)
    return business, True


@app.post("/api/crm/leads")
def create_crm_lead(payload: CRMLeadCreate, db: Session = Depends(get_db)):
    business, created = _create_crm_lead(payload, db, "manual", "Added manually to the CRM")
    if not created:
        raise HTTPException(status_code=409, detail=f"{business.name} is already in the CRM")
    return {"status": "created", "lead_id": business.id}


def _normalise_import_row(row: dict) -> dict:
    return {re.sub(r"[^a-z0-9]+", "_", (key or "").strip().lower()).strip("_"): value for key, value in row.items()}


def _import_value(row: dict, *aliases: str) -> Optional[str]:
    for alias in aliases:
        value = row.get(alias)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _parse_tags(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return _normalise_tags(re.split(r"[,;|]", value))


@app.post("/api/crm/leads/import")
async def import_crm_leads(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "leads.csv"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    if extension not in {"csv", "tsv", "txt", "json"}:
        raise HTTPException(status_code=400, detail="Use a CSV, TSV, or JSON file. Export from Excel or Google Sheets as CSV first.")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Import files must be 5 MB or smaller")

    try:
        text = raw.decode("utf-8-sig")
        if extension == "json":
            imported_rows = json.loads(text)
            if not isinstance(imported_rows, list):
                raise ValueError("JSON must contain an array of lead objects")
        else:
            delimiter = "\t" if extension == "tsv" else ","
            if extension == "txt":
                delimiter = "\t" if "\t" in text.partition("\n")[0] else ","
            imported_rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, csv.Error) as exc:
        raise HTTPException(status_code=400, detail=f"Could not read import file: {exc}") from exc

    added = 0
    skipped = 0
    errors = []
    for index, original_row in enumerate(imported_rows, start=2):
        row = _normalise_import_row(original_row)
        name = _import_value(row, "name", "company", "company_name", "business_name")
        if not name:
            skipped += 1
            errors.append(f"Row {index}: company name is missing")
            continue
        score_value = _import_value(row, "commercial_score", "score")
        try:
            score = int(float(score_value)) if score_value else None
        except ValueError:
            score = None
        try:
            _, created = _create_crm_lead(CRMLeadCreate(
                name=name,
                website_url=_import_value(row, "website_url", "website", "domain"),
                primary_phone=_import_value(row, "primary_phone", "phone", "company_phone"),
                city=_import_value(row, "city"),
                state_province=_import_value(row, "state_province", "state", "province", "region"),
                country=_import_value(row, "country"),
                industry=_import_value(row, "industry"),
                stage=_import_value(row, "stage", "status") or "new",
                owner_name=_import_value(row, "owner", "owner_name"),
                tags=_parse_tags(_import_value(row, "tags", "tag")),
                commercial_score=score,
                primary_problem=_import_value(row, "primary_problem", "problem", "opportunity"),
                recommended_offer=_import_value(row, "recommended_offer", "offer"),
                contact_name=_import_value(row, "contact_name", "contact", "decision_maker"),
                contact_email=_import_value(row, "contact_email", "email"),
                contact_phone=_import_value(row, "contact_phone", "contact_number"),
                contact_title=_import_value(row, "contact_title", "title"),
            ), db, "import", f"Imported from {filename}")
            added += int(created)
            skipped += int(not created)
        except Exception as exc:
            db.rollback()
            skipped += 1
            errors.append(f"Row {index}: {str(exc)}")
    return {"status": "completed", "added": added, "skipped": skipped, "errors": errors[:10]}


def _safe_export_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _crm_export_rows(leads: List[dict]) -> tuple[List[str], List[List[str]]]:
    header = [
        "Company", "Website", "Stage", "Score", "Grade", "Industry", "Location",
        "Owner", "Tags", "Campaign", "Primary problem", "Recommended offer",
        "Primary contact", "Primary contact title", "Primary contact email", "Primary contact phone",
        "All emails", "Website emails", "Apollo emails", "All phones", "LinkedIn profiles",
        "Next follow-up"
    ]
    rows = []
    for lead in leads:
        contact = lead["contacts"][0] if lead["contacts"] else {}
        contacts = lead.get("contacts") or []
        all_emails = sorted({c.get("email") for c in contacts if c.get("email")})
        website_emails = sorted({
            c.get("email") for c in contacts
            if c.get("email") and "website" in (c.get("source") or "").lower()
        })
        apollo_emails = sorted({
            c.get("email") for c in contacts
            if c.get("email") and "apollo" in (c.get("source") or "").lower()
        })
        all_phones = sorted({c.get("phone") for c in contacts if c.get("phone")})
        linkedin_profiles = sorted({c.get("linkedin_url") for c in contacts if c.get("linkedin_url")})
        rows.append([_safe_export_cell(value) for value in [
            lead["name"], lead["website_url"], lead["stage"], lead["commercial_score"], lead["grade"],
            lead["industry"], lead["location"], lead["owner_name"], ", ".join(lead["tags"]),
            lead["campaign_name"], lead["primary_problem"], lead["recommended_offer"],
            contact.get("name"), contact.get("title"), contact.get("email"), contact.get("phone"),
            "; ".join(all_emails), "; ".join(website_emails), "; ".join(apollo_emails),
            "; ".join(all_phones), "; ".join(linkedin_profiles), lead["next_follow_up_at"],
        ]])
    return header, rows


@app.get("/api/crm/leads/export")
def export_crm_leads(
    format: str = "csv",
    ids: List[int] = Query(default=[]),
    db: Session = Depends(get_db),
):
    export_format = format.lower()
    if export_format not in {"csv", "tsv", "json"}:
        raise HTTPException(status_code=400, detail="Supported formats: csv, tsv, json")
    data = _get_crm_leads(db, ids=ids or None, qualified_only=True, page_size=5000)
    if export_format == "json":
        content = json.dumps(data["leads"], indent=2)
        return StreamingResponse(io.StringIO(content), media_type="application/json", headers={"Content-Disposition": "attachment; filename=devacia-leads.json"})
    output = io.StringIO()
    header, rows = _crm_export_rows(data["leads"])
    delimiter = "\t" if export_format == "tsv" else ","
    csv.writer(output, delimiter=delimiter).writerows([header, *rows])
    extension = "tsv" if export_format == "tsv" else "csv"
    media_type = "text/tab-separated-values" if export_format == "tsv" else "text/csv"
    return StreamingResponse(output, media_type=media_type, headers={"Content-Disposition": f"attachment; filename=devacia-leads.{extension}"})

@app.get("/api/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch aggregated stats for the dashboard."""
    total_campaigns = db.query(Campaign).count()
    total_businesses = db.query(Business).count()
    total_opportunities = db.query(Opportunity).count()
    
    # Calculate average score (approximate)
    scores = db.query(Score.commercial_score).all()
    avg_score = sum([s[0] for s in scores]) / len(scores) if scores else 0
    
    a_plus = len([s for s in scores if s[0] >= 90])
    
    recent_campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).limit(5).all()
    
    formatted_recent = []
    from core.models import CampaignLocation
    for c in recent_campaigns:
        loc = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == c.id).first()
        formatted_recent.append({
            "id": c.id, 
            "name": c.name, 
            "status": c.status, 
            "target": c.target_quantity, 
            "progress": min(c.target_quantity, total_opportunities), 
            "country": loc.country if loc else "USA", 
            "city": loc.city if loc else "Dallas", 
            "industry": c.industry.name if c.industry else ""
        })
        
    # Generate 7-day trailing chart data (mocked for visual shape but dynamically scaled)
    # In a real scenario, this groups opportunities by created_at.
    import datetime
    chart_data = []
    for i in range(7):
        day = (datetime.datetime.now() - datetime.timedelta(days=6 - i)).strftime("%a")[0]
        # mock variation based on total_opportunities
        val = total_opportunities + (i * 10) + (10 if i % 2 == 0 else 0)
        chart_data.append({"day": day, "value": val})
        
    # Fetch top priority opportunities (top 3 by score)
    top_scores = db.query(Score).order_by(Score.commercial_score.desc()).limit(3).all()
    priority_ops = []
    for s in top_scores:
        b = db.query(Business).filter(Business.id == s.business_id).first()
        if b:
            priority_ops.append({
                "id": b.id,
                "name": b.name,
                "city": b.city or "Unknown",
                "state": b.state_province or "Unknown",
                "industry": b.industry or "Unknown",
                "score": s.commercial_score,
                "recommended_offer": "Custom Offer"
            })
            
    return {
        "stats": {
            "campaigns": total_campaigns,
            "raw_leads": total_businesses,
            "qualified_opportunities": total_opportunities,
            "average_score": int(avg_score),
            "a_plus_leads": a_plus
        },
        "recent_campaigns": formatted_recent,
        "chart_data": chart_data,
        "priority_opportunities": priority_ops
    }

@app.get("/api/campaigns")
def get_all_campaigns(status: str = "active", db: Session = Depends(get_db)):
    """Fetch all campaigns with their locations, filtered by active or trash."""
    query = db.query(Campaign)
    if status == "trash":
        query = query.filter(Campaign.deleted_at.is_not(None))
    else:
        query = query.filter(Campaign.deleted_at.is_(None))

    campaigns = query.order_by(Campaign.created_at.desc()).all()
    from core.models import CampaignLocation
    result = []
    for c in campaigns:
        loc = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == c.id).first()
        result.append({
            "id": c.id, 
            "name": c.name, 
            "status": c.status, 
            "target": c.target_quantity, 
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "country": loc.country if loc else "USA", 
            "city": loc.city if loc else "Dallas", 
            "industry": c.industry.name if c.industry else ""
        })
    return result

@app.get("/api/crm/leads/{lead_id}")
@app.get("/api/leads/{lead_id}")
def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    """Fetch full dossier for a specific lead."""
    business, crm_lead = _get_crm_lead_or_404(lead_id, db)

    opp = db.query(Opportunity).filter(Opportunity.business_id == lead_id).first()
    score = db.query(Score).filter(Score.business_id == lead_id).first()
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == lead_id).all()
    evidence = db.query(WebsiteEvidence).filter(WebsiteEvidence.business_id == lead_id).all()
    website = db.query(Website).filter(Website.business_id == lead_id).first()
    audit = db.query(WebsiteAudit).filter(WebsiteAudit.website_id == website.id).first() if website else None
    technologies = db.query(WebsiteTechnology).filter(WebsiteTechnology.website_id == website.id).all() if website else []
    pages = db.query(WebsitePage).filter(WebsitePage.website_id == website.id).order_by(WebsitePage.id.asc()).all() if website else []
    screenshots = (
        db.query(WebsiteScreenshot)
        .join(WebsitePage, WebsiteScreenshot.website_page_id == WebsitePage.id)
        .filter(WebsitePage.website_id == website.id)
        .order_by(WebsiteScreenshot.id.asc())
        .all()
        if website else []
    )
    pages_checked = len(pages)
    screenshot_count = len(screenshots)
    social_profiles = db.query(SocialProfile).filter(SocialProfile.business_id == lead_id).all()

    from core.models import AIAnalysis
    ai_record = db.query(AIAnalysis).filter(AIAnalysis.opportunity_id == opp.id).first() if opp else None

    activities = db.query(CRMActivity).filter(CRMActivity.business_id == lead_id).order_by(CRMActivity.created_at.desc()).limit(30).all()
    campaign = db.query(Campaign).filter(Campaign.id == business.campaign_id).first() if business.campaign_id else None
    audit_metrics = _dossier_audit_metrics(website, audit)
    digital_gaps = []
    if website and website.is_live is True and audit:
        if audit.booking_detected is False:
            digital_gaps.append("No booking")
        if audit.quote_form is False:
            digital_gaps.append("No dedicated quote funnel")
        if audit.mobile_responsive is False or audit.phone_cta is False:
            digital_gaps.append("Weak mobile CTA")
        if audit.contact_form is False and audit.quote_form is False:
            digital_gaps.append("No lead qualification")
    evidence_summary = _dossier_page_labels(pages, screenshot_count, len(evidence))
    primary_contact = _contacts_by_business(db, [lead_id]).get(lead_id, [])
    dossier_contact = primary_contact[0] if primary_contact else None
    company_email = next(
        (contact.get("email") for contact in primary_contact if contact.get("contact_type") == "company" and contact.get("email")),
        None,
    )
    lead = _serialize_crm_lead(
        business,
        opp,
        score,
        crm_lead,
        campaign,
        primary_contact,
    )
    lead.update({
        "ticket_range": _ticket_range(opp),
        "opportunity": {
            "ticket_low": opp.ticket_low if opp else None,
            "ticket_high": opp.ticket_high if opp else None,
            "problems": opp.problems if opp and opp.problems else [],
            "confidence": opp.confidence if opp else None,
        },
        "ai_reasoning": _display_opportunity_text(opp.ai_reasoning) if opp else None,
        "ai_transparency": ai_record.parsed_output if ai_record else None,
        "audit": {
            "mobile_responsive": audit.mobile_responsive if audit else None,
            "horizontal_overflow": audit.horizontal_overflow if audit else None,
            "performance_score": audit.performance_score if audit else None,
            "seo_score": audit.seo_score if audit else None,
            "desktop_ux_score": audit.desktop_ux_score if audit else None,
            "mobile_ux_score": audit.mobile_ux_score if audit else None,
            "accessibility_score": audit.accessibility_score if audit else None,
            "phone_cta": audit.phone_cta if audit else None,
            "contact_form": audit.contact_form if audit else None,
            "quote_form": audit.quote_form if audit else None,
            "live_chat": audit.live_chat if audit else None,
            "sticky_cta": audit.sticky_cta if audit else None,
            "ecommerce_detected": audit.ecommerce_detected if audit else None,
            "booking_detected": audit.booking_detected if audit else None,
        },
        "website": {
            "url": website.url if website else business.website_url,
            "is_live": website.is_live if website else None,
            "has_ssl": website.has_ssl if website else None,
            "cms": website.cms if website else None,
            "framework": website.framework if website else None,
            "technology_stack": list(dict.fromkeys(
                [technology.technology for technology in technologies if technology.technology]
                + [value for value in [website.cms if website else None, website.framework if website else None] if value]
            )),
            "pages_checked": pages_checked,
            "screenshot_count": screenshot_count,
            "pages": [{
                "id": page.id,
                "url": page.url,
                "page_type": page.page_type,
                "title": page.title,
                "status_code": page.status_code,
                "crawled_at": page.crawled_at.isoformat() if page.crawled_at else None,
            } for page in pages],
            "technologies": [{
                "name": technology.technology,
                "category": technology.category,
                "confidence": technology.confidence,
            } for technology in technologies],
            "screenshots": [{
                "id": screenshot.id,
                "viewport": screenshot.viewport_type,
                "asset_path": screenshot.s3_key_or_path,
                "captured_at": screenshot.captured_at.isoformat() if screenshot.captured_at else None,
            } for screenshot in screenshots],
        },
        "dossier": {
            "priority": _dossier_priority(score),
            "metrics": audit_metrics,
            "digital_gaps": digital_gaps,
            "audit_available": bool(website and website.is_live is True and audit),
            "why_contact": _display_opportunity_text(opp.ai_reasoning) if opp else None,
            "evidence_labels": evidence_summary,
            "evidence_summary": " | ".join(evidence_summary) if evidence_summary else None,
            "owner": {
                "name": dossier_contact.get("name") if dossier_contact else ("Business contact" if business.primary_phone else None),
                "role": dossier_contact.get("title") if dossier_contact else "Company phone",
                "email": dossier_contact.get("email") if dossier_contact else None,
                "phone": (dossier_contact.get("phone") if dossier_contact else None) or business.primary_phone,
                "linkedin_url": dossier_contact.get("linkedin_url") if dossier_contact else None,
                "contact_type": dossier_contact.get("contact_type") if dossier_contact else None,
                "verification_status": dossier_contact.get("verification_status") if dossier_contact else None,
                "email_verified": bool(dossier_contact and dossier_contact.get("email") and dossier_contact.get("verification_status") == "verified"),
                "has_phone": bool((dossier_contact and dossier_contact.get("phone")) or business.primary_phone),
                "has_linkedin": bool(dossier_contact and dossier_contact.get("linkedin_url")),
            },
        },
        "crm": {
            "stage": _normalise_stage(crm_lead.stage),
            "owner_name": crm_lead.owner_name,
            "tags": _normalise_tags(crm_lead.tags),
            "source": crm_lead.source,
            "next_follow_up_at": crm_lead.next_follow_up_at.isoformat() if crm_lead.next_follow_up_at else None,
        },
        "evidence": [{"source": e.evidence_type, "text": e.finding, "confidence": e.confidence} for e in evidence],
        "business_detail": {
            "address": business.address,
            "postal_code": business.postal_code,
            "latitude": business.latitude,
            "longitude": business.longitude,
            "rating": business.rating,
            "review_count": business.review_count,
            "company_email": company_email,
            "google_place_id": business.google_place_id,
        },
        "social_profiles": [{
            "platform": profile.platform,
            "url": profile.profile_url,
            "followers": profile.followers,
        } for profile in social_profiles],
        "activities": [{
            "id": activity.id,
            "type": activity.activity_type,
            "body": activity.body,
            "created_by": activity.created_by,
            "created_at": activity.created_at.isoformat() if activity.created_at else None,
        } for activity in activities],
    })
    return lead


@app.post("/api/crm/leads/{lead_id}/enrich")
def enrich_crm_lead_contacts(lead_id: int, db: Session = Depends(get_db)):
    """Queue a safe refresh of Apollo decision-maker and public social data."""
    _get_crm_lead_or_404(lead_id, db)
    task = enrich_lead_contacts_task.apply_async(args=[lead_id], queue='devacia_queue')
    return {"status": "queued", "task_id": task.id, "message": "Apollo decision-maker enrichment has started."}

@app.post("/api/leads/{lead_id}/export")
def export_single_lead(lead_id: int, db: Session = Depends(get_db)):
    """Compatibility endpoint: prepare a browser download for a single lead."""
    _get_crm_lead_or_404(lead_id, db)
    return {"status": "ready", "download_url": f"/api/crm/leads/export?ids={lead_id}"}

@app.get("/api/exports/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    """Legacy CSV route kept for bookmarked exports."""
    return export_crm_leads(format="csv", ids=[], db=db)

# ==========================================
# TRASH BIN BULK ACTIONS
# ==========================================
from pydantic import BaseModel
from typing import List

class BulkActionRequest(BaseModel):
    ids: List[int]


def _hard_delete_businesses(db: Session, business_ids: List[int]) -> int:
    """Delete businesses and dependent CRM/intelligence records in FK-safe order."""
    business_ids = list(dict.fromkeys(int(business_id) for business_id in business_ids if business_id))
    if not business_ids:
        return 0

    website_ids = [
        website_id for (website_id,) in
        db.query(Website.id).filter(Website.business_id.in_(business_ids)).all()
    ]
    if website_ids:
        page_ids = [
            page_id for (page_id,) in
            db.query(WebsitePage.id).filter(WebsitePage.website_id.in_(website_ids)).all()
        ]
        db.query(WebsiteEvidence).filter(WebsiteEvidence.business_id.in_(business_ids)).delete(synchronize_session=False)
        if page_ids:
            db.query(WebsiteScreenshot).filter(WebsiteScreenshot.website_page_id.in_(page_ids)).delete(synchronize_session=False)
        db.query(WebsiteAudit).filter(WebsiteAudit.website_id.in_(website_ids)).delete(synchronize_session=False)
        db.query(WebsiteTechnology).filter(WebsiteTechnology.website_id.in_(website_ids)).delete(synchronize_session=False)
        db.query(WebsitePage).filter(WebsitePage.website_id.in_(website_ids)).delete(synchronize_session=False)
        db.query(Website).filter(Website.id.in_(website_ids)).delete(synchronize_session=False)
    else:
        db.query(WebsiteEvidence).filter(WebsiteEvidence.business_id.in_(business_ids)).delete(synchronize_session=False)

    db.query(AIAnalysis).filter(AIAnalysis.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(Opportunity).filter(Opportunity.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(Score).filter(Score.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(DecisionMaker).filter(DecisionMaker.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(SocialProfile).filter(SocialProfile.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(BusinessSource).filter(BusinessSource.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(CRMActivity).filter(CRMActivity.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(CRMNote).filter(CRMNote.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.query(CRMLead).filter(CRMLead.business_id.in_(business_ids)).delete(synchronize_session=False)
    deleted = db.query(Business).filter(Business.id.in_(business_ids)).delete(synchronize_session=False)
    return deleted

@app.delete('/api/campaigns')
def bulk_delete_campaigns(payload: BulkActionRequest, db: Session = Depends(get_db)):
    now = func.now()
    db.query(Campaign).filter(Campaign.id.in_(payload.ids)).update({Campaign.deleted_at: now}, synchronize_session=False)
    businesses = db.query(Business).filter(Business.campaign_id.in_(payload.ids)).all()
    b_ids = [b.id for b in businesses]
    if b_ids:
        db.query(Business).filter(Business.id.in_(b_ids)).update({Business.deleted_at: now}, synchronize_session=False)
        db.query(CRMLead).filter(CRMLead.business_id.in_(b_ids)).update({CRMLead.deleted_at: now}, synchronize_session=False)
    db.commit()
    return {'status': 'success'}

@app.post('/api/campaigns/recover')
def bulk_recover_campaigns(payload: BulkActionRequest, db: Session = Depends(get_db)):
    db.query(Campaign).filter(Campaign.id.in_(payload.ids)).update({Campaign.deleted_at: None}, synchronize_session=False)
    businesses = db.query(Business).filter(Business.campaign_id.in_(payload.ids)).all()
    b_ids = [b.id for b in businesses]
    if b_ids:
        db.query(Business).filter(Business.id.in_(b_ids)).update({Business.deleted_at: None}, synchronize_session=False)
        db.query(CRMLead).filter(CRMLead.business_id.in_(b_ids)).update({CRMLead.deleted_at: None}, synchronize_session=False)
    db.commit()
    return {'status': 'success'}

@app.delete('/api/campaigns/permanent')
def bulk_hard_delete_campaigns(payload: BulkActionRequest, db: Session = Depends(get_db)):
    campaign_ids = list(dict.fromkeys(payload.ids))
    business_ids = [
        business_id for (business_id,) in
        db.query(Business.id).filter(Business.campaign_id.in_(campaign_ids)).all()
    ]
    _hard_delete_businesses(db, business_ids)
    db.query(CampaignLocation).filter(CampaignLocation.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(JobRun).filter(JobRun.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).delete(synchronize_session=False)
    db.commit()
    return {'status': 'success'}

@app.delete('/api/crm/leads')
def bulk_delete_leads(payload: BulkActionRequest, db: Session = Depends(get_db)):
    now = func.now()
    db.query(CRMLead).filter(CRMLead.business_id.in_(payload.ids)).update({CRMLead.deleted_at: now}, synchronize_session=False)
    db.query(Business).filter(Business.id.in_(payload.ids)).update({Business.deleted_at: now}, synchronize_session=False)
    db.commit()
    return {'status': 'success'}

@app.post('/api/crm/leads/recover')
def bulk_recover_leads(payload: BulkActionRequest, db: Session = Depends(get_db)):
    db.query(CRMLead).filter(CRMLead.business_id.in_(payload.ids)).update({CRMLead.deleted_at: None}, synchronize_session=False)
    db.query(Business).filter(Business.id.in_(payload.ids)).update({Business.deleted_at: None}, synchronize_session=False)
    db.commit()
    return {'status': 'success'}

@app.delete('/api/crm/leads/permanent')
def bulk_hard_delete_leads(payload: BulkActionRequest, db: Session = Depends(get_db)):
    deleted = _hard_delete_businesses(db, payload.ids)
    db.commit()
    return {'status': 'success', 'deleted': deleted}

from pydantic import BaseModel
class EmailGenerateResponse(BaseModel):
    email_body: str
    source: str = "ai"


def _lead_email_context(db: Session, biz: Business, opp: Optional[Opportunity]) -> str:
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == biz.id).all()
    website = db.query(Website).filter(Website.business_id == biz.id).first()
    audit = db.query(WebsiteAudit).filter(WebsiteAudit.website_id == website.id).first() if website else None
    evidence = db.query(WebsiteEvidence).filter(WebsiteEvidence.business_id == biz.id).limit(8).all()
    social_profiles = db.query(SocialProfile).filter(SocialProfile.business_id == biz.id).all()

    named_contacts = [
        f"{' '.join(part for part in [c.first_name, c.last_name] if part)} ({c.title or 'decision maker'})"
        for c in contacts
        if c.first_name or c.last_name
    ]
    emails = sorted({c.email for c in contacts if c.email})
    phones = sorted({(c.phone or c.mobile) for c in contacts if c.phone or c.mobile})
    gaps = []
    if audit:
        if audit.booking_detected is False:
            gaps.append("no online booking")
        if audit.quote_form is False:
            gaps.append("no quote/estimate funnel")
        if audit.contact_form is False:
            gaps.append("no lead form")
        if audit.phone_cta is False:
            gaps.append("weak phone call-to-action")

    lines = [
        f"Business Name: {_clean_text(biz.name)}",
        f"Industry: {_clean_text(biz.industry)}",
        f"Location: {_clean_text(', '.join(part for part in [biz.city, biz.state_province, biz.country] if part))}",
        f"Website: {_clean_text(biz.website_url or 'No official website found')}",
        f"Google Rating: {_clean_text(biz.rating)}/5 ({_clean_text(biz.review_count)} reviews)",
        f"Known Contacts: {_clean_text('; '.join(named_contacts) or 'No named decision maker found')}",
        f"Known Emails: {_clean_text('; '.join(emails) or 'No email found')}",
        f"Known Phones: {_clean_text('; '.join(phones) or biz.primary_phone or 'No phone found')}",
        f"Social Profiles: {_clean_text('; '.join(p.profile_url for p in social_profiles if p.profile_url) or 'None found')}",
        f"Observed Digital Gaps: {_clean_text('; '.join(gaps) or 'No confirmed digital gap')}",
    ]
    if opp:
        lines.extend([
            f"Primary Problem: {_clean_text(opp.primary_problem)}",
            f"Recommended Devacia Offer: {_clean_text(opp.recommended_offer)}",
            f"Estimated Project Value: {_ticket_range(opp) or 'Pending'}",
            f"Existing Outreach Angle: {_clean_text(opp.outreach_angle)}",
            f"AI Reasoning: {_clean_text(opp.ai_reasoning)}",
        ])
    if evidence:
        lines.append("Evidence Snippets:")
        lines.extend(f"- {_clean_text(item.finding)}" for item in evidence if item.finding)
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def _fallback_personalized_email(biz: Business, opp: Optional[Opportunity]) -> str:
    business_name = _clean_text(biz.name) or "your business"
    first_problem = _clean_text(opp.primary_problem if opp else "") or "a few conversion gaps on your website"
    offer = _clean_text(opp.recommended_offer if opp else "") or "a cleaner lead-capture system"
    location = _clean_text(", ".join(part for part in [biz.city, biz.country] if part))
    subject = f"Subject: Quick idea for {business_name}"
    intro_location = f" in {location}" if location else ""
    return (
        f"{subject}\n\n"
        f"Hi,\n\n"
        f"I was reviewing {business_name}{intro_location} and noticed {first_problem}. "
        f"Devacia can help with {offer}, so visitors have a clearer path to contact, book, or request a quote.\n\n"
        f"Would a quick 15-minute call this week make sense?\n\n"
        f"Laraib | Devacia"
    )

@app.post("/api/leads/{lead_id}/generate-email", response_model=EmailGenerateResponse)
def generate_lead_email(lead_id: int, db: Session = Depends(get_db)):
    biz, crm = _get_crm_lead_or_404(lead_id, db)
    opp = db.query(Opportunity).filter(Opportunity.business_id == biz.id).first()
    context = _lead_email_context(db, biz, opp)
    
    system_prompt = """You are an elite Sales Development Representative (SDR) writing for Devacia, a web development and digital marketing agency.

Your task: Write a SHORT, high-converting cold outreach email.

Rules:
1. Address the decision maker by first name if known, otherwise use a natural greeting.
2. Reference their SPECIFIC business and location (show you did your homework).
3. Mention one specific digital gap or opportunity you spotted (e.g., no website, no booking system, slow mobile).
4. Offer a single clear value proposition from Devacia.
5. Include a low-friction CTA (e.g., "Would a 15-minute call this week work?").
6. Keep it under 150 words. No fluff. No generic phrases.
7. Format: Subject line first, then the email body. No placeholders like [Your Name].
8. Sign off as: Laraib | Devacia"""

    user_prompt = f"Write a cold outreach email using this intelligence:\n\n{context}"
    email_text = ""
    source = "fallback"

    try:
        from providers.groq_provider import GroqProvider
        import groq as groq_sdk

        groq_provider = GroqProvider()
        if groq_provider.api_key:
            sync_client = groq_sdk.Groq(api_key=groq_provider.api_key)
            completion = sync_client.chat.completions.create(
                model=groq_provider.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            email_text = completion.choices[0].message.content or ""
            source = "groq"
    except Exception as exc:
        print(f"Email generation AI failed for lead {lead_id}: {str(exc)[:200]}")

    # Strip <think> blocks (including unclosed ones if truncated)
    email_text = re.sub(r"<think>.*?(?:</think>|$)", "", email_text, flags=re.DOTALL).strip()
    email_text = _clean_text(email_text)
    if not email_text:
        email_text = _fallback_personalized_email(biz, opp)

    db.add(CRMActivity(
        business_id=biz.id,
        activity_type="generated_email",
        body=email_text,
        created_by="Lead Intelligence",
    ))
    crm.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    return EmailGenerateResponse(email_body=email_text, source=source)

