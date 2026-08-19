import asyncio
import math
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from celery import Celery
from sqlalchemy import or_

from core.database import SessionLocal
from core.deduplication import DeduplicationEngine
from core.models import (
    AIAnalysis,
    Business,
    BusinessSource,
    Campaign,
    CampaignLocation,
    CRMActivity,
    CRMLead,
    DecisionMaker,
    IndustryConfig,
    JobRun,
    Opportunity,
    Score,
    Website,
    WebsiteAudit,
    WebsiteEvidence,
    WebsitePage,
    WebsiteScreenshot,
    WebsiteTechnology,
)
from engines.scoring import ScoringEngine
from engines.website_intelligence import WebsiteIntelligenceEngine
from providers.apollo_provider import ApolloProvider
from providers.discovery_factory import get_discovery_provider
from providers.gemini_provider import GeminiProvider
from providers.hunter_provider import HunterProvider


redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("devacia_worker", broker=redis_url, backend=redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def _location_label(location: CampaignLocation) -> str:
    return ", ".join(
        part.strip()
        for part in [location.city, location.region_state, location.country]
        if part and part.strip()
    )


def _domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc.lower().removeprefix("www.") or None


def _page_type(url: str) -> str:
    value = (url or "").lower()
    if "contact" in value:
        return "contact"
    if any(term in value for term in ("book", "quote", "estimate", "schedule")):
        return "booking"
    if "service" in value:
        return "services"
    if "about" in value:
        return "about"
    return "homepage"


def _existing_business(db, data: Dict[str, Any]) -> Optional[Business]:
    place_id = data.get("google_place_id")
    if place_id:
        match = db.query(Business).filter(Business.google_place_id == place_id).first()
        if match:
            return match
    website = data.get("website_url")
    if website:
        match = db.query(Business).filter(Business.website_url == website).first()
        if match:
            return match
    name = data.get("name")
    city = data.get("city")
    if name:
        return db.query(Business).filter(Business.name == name, Business.city == city).first()
    return None


def _save_contact(db, business_id: int, data: Dict[str, Any]) -> bool:
    """Save only usable, provider-sourced contact facts and avoid duplicates."""
    email = (data.get("email") or "").strip().lower() or None
    phone = (data.get("phone") or data.get("mobile") or "").strip() or None
    if not email and not phone:
        return False

    duplicate_query = db.query(DecisionMaker).filter(DecisionMaker.business_id == business_id)
    if email:
        duplicate_query = duplicate_query.filter(DecisionMaker.email == email)
    elif phone:
        duplicate_query = duplicate_query.filter(or_(DecisionMaker.phone == phone, DecisionMaker.mobile == phone))
    if duplicate_query.first():
        return False

    db.add(DecisionMaker(
        business_id=business_id,
        first_name=data.get("first_name") or None,
        last_name=data.get("last_name") or None,
        title=data.get("title") or None,
        email=email,
        phone=phone,
        mobile=(data.get("mobile") or "").strip() or None,
        linkedin_url=data.get("linkedin_url") or None,
        contact_type=data.get("contact_type") or "professional",
        verification_status=data.get("verification_status") or "unknown",
        confidence=data.get("confidence"),
        source=data.get("source") or "unknown",
    ))
    return True


def _has_actionable_contact(db, business: Business) -> bool:
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == business.id).all()
    has_email = any(contact.email for contact in contacts)
    has_phone = bool(business.primary_phone) or any(contact.phone or contact.mobile for contact in contacts)
    return has_email and has_phone


def _persist_website_research(db, business: Business, audit: Dict[str, Any]) -> tuple[Website, List[Dict[str, Any]]]:
    """Persist a traceable crawl. A business is never qualified merely by this step."""
    technologies = audit.get("technology_stack") or []
    cms = next((item for item in technologies if item.lower() in {"wordpress", "wix", "squarespace", "shopify"}), None)
    website = Website(
        business_id=business.id,
        url=business.website_url if business.website_url.startswith("http") else f"https://{business.website_url}",
        is_live=audit.get("is_live") is True,
        has_ssl=audit.get("has_ssl") is True,
        cms=cms,
    )
    db.add(website)
    db.flush()

    db.add(WebsiteAudit(
        website_id=website.id,
        mobile_responsive=audit.get("mobile_responsive"),
        mobile_ux_score=80 if audit.get("mobile_responsive") is True else 35 if audit.get("mobile_responsive") is False else None,
        desktop_ux_score=70 if audit.get("is_live") is True else None,
        accessibility_score=75 if audit.get("mobile_responsive") is True else 53 if audit.get("mobile_responsive") is False else None,
        phone_cta=audit.get("phone_cta"),
        contact_form=audit.get("contact_form"),
        quote_form=audit.get("quote_form"),
        live_chat=audit.get("live_chat"),
        sticky_cta=audit.get("sticky_cta"),
        booking_detected=audit.get("booking_detected"),
        ecommerce_detected=audit.get("ecommerce_detected"),
    ))
    db.add_all(
        WebsiteTechnology(website_id=website.id, technology=item, category="detected", confidence=1.0)
        for item in technologies
    )

    page_map: Dict[str, int] = {}
    for page_url in audit.get("pages_checked") or []:
        page = WebsitePage(website_id=website.id, url=page_url, page_type=_page_type(page_url), status_code=200)
        db.add(page)
        db.flush()
        page_map[page_url] = page.id

    screenshot_id = None
    pages_checked = audit.get("pages_checked") or []
    if audit.get("desktop_screenshot_base64") and pages_checked:
        screenshot = WebsiteScreenshot(
            website_page_id=page_map.get(pages_checked[0]),
            viewport_type="desktop",
            s3_key_or_path="captured_in_worker",
        )
        db.add(screenshot)
        db.flush()
        screenshot_id = screenshot.id

    evidence_records: List[Dict[str, Any]] = []
    for evidence in audit.get("evidence") or []:
        page_url = evidence.get("page_url")
        finding = evidence.get("evidence_text") or ""
        if not finding:
            continue
        db.add(WebsiteEvidence(
            business_id=business.id,
            evidence_type=evidence.get("source_type") or "website_crawl",
            finding=finding,
            confidence=evidence.get("confidence") or 0.75,
            source_page_id=page_map.get(page_url) if page_url else None,
        ))
        evidence_records.append({
            "type": evidence.get("source_type") or "website_crawl",
            "finding": finding,
            "confidence": evidence.get("confidence") or 0.75,
            "source_url": page_url,
        })
    if screenshot_id:
        db.add(WebsiteEvidence(
            business_id=business.id,
            evidence_type="playwright_screenshot",
            finding="Desktop screenshot captured during the audit.",
            confidence=1.0,
            screenshot_id=screenshot_id,
        ))
    db.flush()
    return website, evidence_records


@celery_app.task
def process_campaign_task(campaign_id: int):
    """Run live discovery and admit only research-backed, contactable leads into the CRM."""
    db = SessionLocal()
    job: Optional[JobRun] = None
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "reason": "Campaign not found"}

        job = JobRun(campaign_id=campaign_id, stage="lead_intelligence", status="running", metrics={})
        db.add(job)
        db.commit()
        db.refresh(job)

        config = db.query(IndustryConfig).filter(IndustryConfig.id == campaign.industry_id).first()
        industry_config = getattr(config, "settings", None) or getattr(config, "signals", None) or {}
        industry_name = campaign.industry.name if campaign.industry else "Local business"
        quality_threshold = max(0, min(int(campaign.min_quality_score or 80), 100))
        target_quantity = max(1, int(campaign.target_quantity or 1))
        locations = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == campaign_id).all()
        if not locations:
            locations = [CampaignLocation(city="Dallas", region_state="Texas", country="USA")]

        resumable_statuses = ("researching", "needs_research", "needs_contact_enrichment", "below_quality_threshold")
        test_business_ids = db.query(BusinessSource.business_id).filter(BusinessSource.source.in_(("mock", "fixture")))
        resumable_businesses = (
            db.query(Business)
            .filter(Business.campaign_id == campaign_id, Business.status.in_(resumable_statuses))
            .filter(~Business.id.in_(test_business_ids))
            .all()
        )
        provider = get_discovery_provider()
        discovery_needed = max(0, target_quantity - len(resumable_businesses))
        per_location_limit = max(1, math.ceil(discovery_needed / len(locations))) if discovery_needed else 0
        raw_businesses: List[Dict[str, Any]] = []
        for location in locations:
            if not discovery_needed:
                break
            remaining = target_quantity - len(raw_businesses)
            if remaining <= 0:
                break
            raw_businesses.extend(asyncio.run(provider.discover(
                query=f"{industry_name} contractors",
                location=_location_label(location),
                industry=industry_name,
                limit=min(per_location_limit, remaining),
            )))

        dedupe = DeduplicationEngine(db_session=db)
        unique_businesses = dedupe.deduplicate(raw_businesses)[:discovery_needed]
        saved_businesses: List[Business] = list(resumable_businesses)
        for raw in unique_businesses:
            if not raw.get("name"):
                continue
            existing = _existing_business(db, raw)
            if existing:
                # Existing candidates are loaded above. Test records are never
                # eligible to re-enter the live pipeline.
                continue
            business = Business(
                campaign_id=campaign_id,
                name=raw["name"].strip(),
                normalized_name=raw["name"].strip().lower(),
                industry=industry_name,
                country=raw.get("country"),
                state_province=raw.get("state_province"),
                city=raw.get("city"),
                postal_code=raw.get("postal_code"),
                address=raw.get("address"),
                latitude=raw.get("latitude"),
                longitude=raw.get("longitude"),
                primary_phone=raw.get("primary_phone"),
                website_url=raw.get("website_url"),
                google_place_id=str(raw.get("google_place_id")) if raw.get("google_place_id") else None,
                rating=raw.get("rating"),
                review_count=raw.get("review_count"),
                status="researching",
            )
            db.add(business)
            db.flush()
            source = raw.get("source_metadata") or {}
            db.add(BusinessSource(
                business_id=business.id,
                source=source.get("source") or "unknown",
                source_id=business.google_place_id,
                source_url=raw.get("source_url"),
            ))
            saved_businesses.append(business)
        db.commit()

        crawler = WebsiteIntelligenceEngine()
        scorer = ScoringEngine(industry_config)
        gemini = GeminiProvider()
        hunter = HunterProvider()
        apollo = ApolloProvider(db_session=db)
        qualified_count = 0
        audited_count = 0
        enriched_count = 0

        for business in saved_businesses:
            if not business.website_url:
                business.status = "rejected_no_website"
                db.commit()
                continue

            audit = asyncio.run(crawler.audit_website(business.website_url))
            _, evidence = _persist_website_research(db, business, audit)
            audited_count += 1
            if not audit.get("is_live"):
                business.status = "rejected_unreachable"
                db.commit()
                continue

            public_emails = sorted({email.lower().strip() for email in audit.get("emails") or [] if email})
            public_phones = sorted({phone.strip() for phone in audit.get("phones") or [] if phone})
            if not business.primary_phone and public_phones:
                business.primary_phone = public_phones[0]
            for email in public_emails:
                _save_contact(db, business.id, {
                    "email": email,
                    "phone": business.primary_phone,
                    "title": "Website email",
                    "contact_type": "company",
                    "verification_status": "unknown",
                    "confidence": 1.0,
                    "source": "website_crawl",
                })

            score_result = scorer.calculate_score({
                "primary_phone": business.primary_phone,
                "website_url": business.website_url,
                "website_email": public_emails[0] if public_emails else None,
                "review_count": business.review_count,
            }, audit)
            score = db.query(Score).filter(Score.business_id == business.id).order_by(Score.id.desc()).first()
            if not score:
                score = Score(business_id=business.id)
                db.add(score)
            score.commercial_score = score_result["commercial_score"]
            score.data_confidence = score_result["data_confidence"]
            score.grade = score_result["grade"]
            score.business_fit = score_result["business_fit"]
            score.digital_gap = score_result["digital_gap"]
            score.offer_fit = score_result["offer_fit"]
            score.buying_intent = score_result["buying_intent"]
            score.contactability = score_result["contactability"]
            score.score_version = "v2-research-gated"
            db.commit()

            if score.commercial_score < quality_threshold:
                business.status = "below_quality_threshold"
                db.commit()
                continue

            domain = _domain(business.website_url)
            if domain:
                provider_contacts = asyncio.run(hunter.find_emails(domain=domain))
                # Hunter can return general inboxes. Use Apollo to seek a real
                # owner/founder when no named professional contact was found.
                if not any(item.get("first_name") or item.get("last_name") for item in provider_contacts):
                    provider_contacts.extend(asyncio.run(apollo.find_emails(domain=domain, name=business.name)))
                for contact in provider_contacts:
                    enriched_count += int(_save_contact(db, business.id, contact))
                db.commit()

            diagnosis = asyncio.run(gemini.analyze(evidence, industry_config))
            if not diagnosis or diagnosis.get("confidence") not in {"high", "medium"}:
                business.status = "needs_research"
                db.commit()
                continue

            if not _has_actionable_contact(db, business):
                business.status = "needs_contact_enrichment"
                db.commit()
                continue

            opportunity = Opportunity(
                business_id=business.id,
                primary_problem=diagnosis["primary_problem"],
                problems=diagnosis["problems"],
                recommended_offer=diagnosis["recommended_offer"],
                ticket_low=diagnosis["ticket_low"],
                ticket_high=diagnosis["ticket_high"],
                outreach_angle=diagnosis["outreach_angle"],
                ai_reasoning=diagnosis["ai_reasoning"],
                confidence=diagnosis["confidence"],
            )
            db.add(opportunity)
            db.flush()
            db.add(AIAnalysis(
                business_id=business.id,
                opportunity_id=opportunity.id,
                model_name=gemini.model_name,
                prompt_template="research_gated_website_evidence",
                parsed_output=diagnosis,
            ))
            business.status = "qualified"
            crm_lead = db.query(CRMLead).filter(CRMLead.business_id == business.id).first()
            if not crm_lead:
                db.add(CRMLead(business_id=business.id, stage="qualified", source="campaign"))
            db.add(CRMActivity(
                business_id=business.id,
                activity_type="qualified",
                body="Qualified from live discovery, website research, AI analysis, and contact enrichment.",
                created_by="Lead Intelligence",
            ))
            db.commit()
            qualified_count += 1

        campaign.status = "completed"
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.metrics = {
            "discovered": len(raw_businesses),
            "deduplicated": len(unique_businesses),
            "saved": len(saved_businesses),
            "audited": audited_count,
            "enriched_contacts": enriched_count,
            "qualified": qualified_count,
        }
        db.commit()
        return {"status": "success", **job.metrics}
    except Exception as exc:
        print(f"Campaign {campaign_id} failed: {exc}")
        db.rollback()
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = "failed"
        if job:
            current_job = db.query(JobRun).filter(JobRun.id == job.id).first()
            if current_job:
                current_job.status = "failed"
                current_job.completed_at = datetime.now(timezone.utc)
                current_job.error_message = str(exc)[:2000]
        db.commit()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
