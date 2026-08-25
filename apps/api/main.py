from fastapi import FastAPI, Depends, HTTPException, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
  
@app.post("/api/migrate-upload")
def migrate_upload(payload: dict, db: Session = Depends(get_db)):
    """Accepts a JSON payload of tables and records and inserts them."""
    try:
        from core.models import Base
        table_name = payload.get("table_name")
        records = payload.get("records", [])
        if not records:
            return {"status": "ok", "message": "No records"}
            
        # Find the model class
        model_class = next((c for c in Base.registry.mappers if c.class_.__tablename__ == table_name), None)
        if not model_class:
            return {"status": "error", "message": f"Table {table_name} not found"}
            
        cls = model_class.class_
        for record in records:
            # Create instance and merge
            instance = cls(**record)
            db.merge(instance)
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
    discovered = db.query(Business).filter(Business.campaign_id == campaign_id).count()
    websites = db.query(Website).join(Business).filter(Business.campaign_id == campaign_id).count()
    opportunities = db.query(Opportunity).join(Business).filter(Business.campaign_id == campaign_id).count()
    enriched = db.query(DecisionMaker).join(Business).filter(Business.campaign_id == campaign_id).count()
    
    # Determine which stage we are actively on
    discovery_status = "done" if discovered > 0 and websites > 0 else ("running" if campaign.status == "processing" else "pending")
    crawler_status = "done" if websites >= discovered and discovered > 0 and opportunities > 0 else ("running" if discovered > 0 and websites < discovered else "pending")
    ai_status = "done" if opportunities >= discovered and discovered > 0 else ("running" if websites > 0 and opportunities < websites else "pending")
    enrichment_status = "done" if campaign.status == "completed" else ("running" if opportunities > 0 and campaign.status == "processing" else "pending")
    
    if campaign.status == "completed":
        discovery_status = crawler_status = ai_status = enrichment_status = "done"

    stages = [
        {"key": "discovery", "label": "Business Discovery & Deduplication", "status": discovery_status, "count": discovered, "total": total_target},
        {"key": "crawler", "label": "Playwright Crawler & UX Audit", "status": crawler_status, "count": websites, "total": discovered},
        {"key": "ai_sdr", "label": "AI SDR Analysis & Scoring", "status": ai_status, "count": opportunities, "total": websites},
        {"key": "enrichment", "label": "Apollo & Hunter Enrichment", "status": enrichment_status, "count": enriched, "total": opportunities},
    ]
    
    return {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "stats": {
            "discovered": discovered,
            "qualified": opportunities,
            "enriched": enriched
        },
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

@app.post("/api/campaigns")
def create_and_start_campaign(req: CampaignCreateRequest, db: Session = Depends(get_db)):
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
    task = process_campaign_task.delay(campaign.id)
    return {"status": "accepted", "campaign_id": campaign.id, "task_id": task.id}

CRM_STAGES = ("new", "reviewing", "contacted", "qualified", "proposal", "won", "lost", "archived")


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
    aliases = {"raw": "new", "processing": "reviewing", "contact": "contacted", "closed_won": "won", "closed_lost": "lost"}
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
    missing_business_ids = [
        business_id
        for (business_id,) in (
            db.query(Business.id)
            .outerjoin(CRMLead, CRMLead.business_id == Business.id)
            .filter(CRMLead.id.is_(None))
            .filter(Business.status == "qualified")
            .all()
        )
    ]
    if missing_business_ids:
        db.add_all(
            CRMLead(business_id=business_id, stage="new", source="campaign")
            for business_id in missing_business_ids
        )
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
    text = (value or "").strip()
    placeholders = {
        "none", "n/a", "null", "good fit", "standard booking system",
        "pitch standard booking system", "no booking system found",
    }
    if not text or text.lower() in placeholders or text.startswith("Error:"):
        return None
    return text


def _ticket_range(opportunity: Optional[Opportunity]) -> Optional[str]:
    if not opportunity or (opportunity.ticket_low is None and opportunity.ticket_high is None):
        return None
    if opportunity.ticket_low is not None and opportunity.ticket_high is not None:
        return f"${opportunity.ticket_low:,}–${opportunity.ticket_high:,}"
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
    stage: Optional[str] = None,
    grade: Optional[str] = None,
    campaign_id: Optional[int] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    has_contact: Optional[bool] = None,
    min_score: Optional[int] = None,
    qualified_only: bool = False,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    data = _get_crm_leads(
        db,
        q=q,
        stage=stage,
        grade=grade,
        campaign_id=campaign_id,
        industry=industry,
        country=country,
        has_contact=has_contact,
        min_score=min_score,
        qualified_only=qualified_only,
        page=page,
        page_size=page_size,
    )
    campaigns = [
        {"id": campaign.id, "name": campaign.name}
        for campaign in db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    ]
    # Only surface facet values for leads that are actually visible in the CRM
    # (qualified campaign leads + all manual/import leads)
    from sqlalchemy import or_ as _or
    visible_industries = [
        row[0]
        for row in (
            db.query(Business.industry)
            .join(CRMLead, CRMLead.business_id == Business.id)
            .filter(Business.industry.isnot(None))
            .filter(_or(Business.status == "qualified", CRMLead.source.in_(("manual", "import"))))
            .distinct()
            .all()
        )
    ]
    visible_countries = [
        row[0]
        for row in (
            db.query(Business.country)
            .join(CRMLead, CRMLead.business_id == Business.id)
            .filter(Business.country.isnot(None))
            .filter(_or(Business.status == "qualified", CRMLead.source.in_(("manual", "import"))))
            .distinct()
            .all()
        )
    ]
    data["facets"] = {
        "campaigns": campaigns,
        "stages": list(CRM_STAGES),
        "industries": sorted(set(visible_industries)),
        "countries": sorted(set(visible_countries))
    }
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
    if crm_lead.source == "campaign" and business.status != "qualified":
        raise HTTPException(status_code=404, detail="This campaign record has not passed qualification")
    return business, crm_lead


@app.patch("/api/crm/leads/{lead_id}")
def update_crm_lead(lead_id: int, payload: CRMLeadUpdate, db: Session = Depends(get_db)):
    business, crm_lead = _get_crm_lead_or_404(lead_id, db)
    if "stage" in payload.model_fields_set and payload.stage is not None:
        crm_lead.stage = _normalise_stage(payload.stage)
        business.status = crm_lead.stage
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
    db.query(Business).filter(Business.id.in_(lead_ids)).update({Business.status: stage}, synchronize_session=False)
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
    header = ["Company", "Website", "Stage", "Score", "Grade", "Industry", "Location", "Owner", "Tags", "Campaign", "Primary problem", "Recommended offer", "Contact", "Contact email", "Contact phone", "Next follow-up"]
    rows = []
    for lead in leads:
        contact = lead["contacts"][0] if lead["contacts"] else {}
        rows.append([_safe_export_cell(value) for value in [
            lead["name"], lead["website_url"], lead["stage"], lead["commercial_score"], lead["grade"], lead["industry"], lead["location"], lead["owner_name"], ", ".join(lead["tags"]), lead["campaign_name"], lead["primary_problem"], lead["recommended_offer"], contact.get("name"), contact.get("email"), contact.get("phone"), lead["next_follow_up_at"],
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
def get_all_campaigns(db: Session = Depends(get_db)):
    """Fetch all campaigns with their locations."""
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
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
            "evidence_summary": " • ".join(evidence_summary) if evidence_summary else None,
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
    task = enrich_lead_contacts_task.delay(lead_id)
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
