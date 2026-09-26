from core.runtime import IS_STAGING
from core.contact_lookup import lookup_optional_contacts
from core.tenancy import load_owned_job
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
from core.lead_quality import clean_phone_for_country, clean_website_url
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
    SocialProfile,
    Website,
    WebsiteAudit,
    WebsiteEvidence,
    WebsitePage,
    WebsiteScreenshot,
    WebsiteTechnology,
)
from engines.scoring import ScoringEngine
from engines.website_intelligence import WebsiteIntelligenceEngine
from providers.discovery_factory import get_discovery_provider
from providers.groq_provider import GroqProvider


redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("devacia_worker", broker="memory://" if IS_STAGING else redis_url, backend="cache+memory://" if IS_STAGING else redis_url)
if IS_STAGING:
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def _location_label(location: CampaignLocation) -> str:
    """Build a clean location string for discovery queries.
    
    For non-US/Canada countries, state/province is omitted to avoid polluting
    the query (e.g. a state left over from a previous USA campaign).
    """
    country = (location.country or "").strip()
    city = (location.city or "").strip()
    state = (location.region_state or "").strip()
    
    # Only include state for countries where it disambiguates (USA, Canada)
    include_state = bool(state) and country in {"USA", "Canada", "US"}
    
    parts = [p for p in [city, state if include_state else None, country] if p]
    return ", ".join(parts)


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



def _set_business_status(db, business, status: str):
    business.status = status
    db.info["system_access"] = True
    try:
        crm = db.query(CRMLead).filter(CRMLead.business_id == business.id).first()
        if not crm:
            crm = CRMLead(business_id=business.id, source="campaign", owner_id=business.owner_id)
            db.add(crm)
        elif business.owner_id is not None and crm.owner_id != business.owner_id:
            crm.owner_id = business.owner_id
        if status == "qualified":
            crm.stage = "qualified"
        elif status in ["needs_research", "needs_official_website", "needs_contact_enrichment", "researching"]:
            crm.stage = "needs_review"
        elif status in ["rejected_unreachable", "below_quality_threshold"]:
            crm.stage = "archived"
        db.flush()
    finally:
        db.info.pop("system_access", None)


def _existing_business(db, data: Dict[str, Any]) -> Optional[Business]:
    from core.deduplication import find_existing_business
    return find_existing_business(db, data)


def _save_contact(db, business_id: int, data: Dict[str, Any]) -> bool:
    """Save contact facts. Allows named leaders without email/phone. Merges duplicates."""
    email = (data.get("email") or "").strip().lower() or None
    phone = (data.get("phone") or data.get("mobile") or "").strip() or None
    linkedin_url = (data.get("linkedin_url") or "").strip() or None
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    title = (data.get("title") or "").strip()
    
    # Must have either email, phone, or a valid name
    if not email and not phone and not (first_name and last_name):
        return False
        
    full_name = f"{first_name} {last_name}".strip().lower()

    # Find duplicate candidates
    existing_contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == business_id).all()
    match = None
    
    # 1. Match by email
    if not match and email:
        match = next((c for c in existing_contacts if c.email and c.email.lower() == email), None)
        
    # 2. Match by LinkedIn
    if not match and linkedin_url:
        match = next((c for c in existing_contacts if c.linkedin_url and c.linkedin_url == linkedin_url), None)
        
    # 3. Match by name and title (if it's a named professional)
    if not match and first_name and last_name:
        for c in existing_contacts:
            if not c.first_name or not c.last_name:
                continue
            c_name = f"{c.first_name} {c.last_name}".strip().lower()
            if c_name == full_name and (not email or not c.email or c.email.lower() == email):
                # If titles exist, maybe verify they are somewhat similar or just trust the name match
                match = c
                break
                
    # 4. Match by direct phone. Do not collapse separate inboxes merely
    # because they share the same company phone number.
    if not match and phone and not (first_name and last_name):
        match = next((
            c for c in existing_contacts
            if ((c.phone and c.phone == phone) or (c.mobile and c.mobile == phone))
            and (not email or not c.email or c.email.lower() == email)
        ), None)
        
    source = data.get("source") or "unknown"
    source_url = data.get("source_url") or None
    
    if match:
        # Merge new info into the existing record
        updated = False
        if email and not match.email:
            match.email = email
            updated = True
        if phone and not match.phone:
            match.phone = phone
            updated = True
        if linkedin_url and not match.linkedin_url:
            match.linkedin_url = linkedin_url
            updated = True
        if first_name and not match.first_name:
            match.first_name = first_name
            match.last_name = last_name
            updated = True
        if title and not match.title:
            match.title = title
            updated = True
        if source_url and not match.source_url:
            match.source_url = source_url
            updated = True
            
        if updated:
            db.commit()
            return True
        return False

    db.add(DecisionMaker(
        business_id=business_id,
        first_name=first_name or None,
        last_name=last_name or None,
        title=title or None,
        email=email,
        phone=phone,
        mobile=(data.get("mobile") or "").strip() or None,
        linkedin_url=linkedin_url,
        contact_type=data.get("contact_type") or "professional",
        verification_status=data.get("verification_status") or "unknown",
        confidence=data.get("confidence"),
        source=source,
        source_url=source_url,
    ))
    db.commit()
    return True


def _contact_source_url(audit: Dict[str, Any]) -> Optional[str]:
    pages = audit.get("pages_checked") or []
    if not pages:
        return None
    prioritized_terms = ("contact", "about", "team", "staff", "leadership")
    return next((url for url in pages if any(term in (url or "").lower() for term in prioritized_terms)), pages[0])


def _save_public_website_contacts(db, business: Business, audit: Dict[str, Any]) -> int:
    """Persist every public email/phone found by the website crawler."""
    source_url = _contact_source_url(audit)
    public_emails = sorted({email.lower().strip() for email in audit.get("emails") or [] if email})
    public_phones = sorted({phone.strip() for phone in audit.get("phones") or [] if phone})

    if not business.primary_phone and public_phones:
        business.primary_phone = public_phones[0]

    saved = 0
    shared_phone = business.primary_phone or (public_phones[0] if public_phones else None)
    for email in public_emails:
        saved += int(_save_contact(db, business.id, {
            "email": email,
            "phone": shared_phone,
            "title": "Website email",
            "contact_type": "company",
            "verification_status": "unknown",
            "confidence": 1.0,
            "source": "website_crawl",
            "source_url": source_url,
        }))

    if not public_emails:
        for phone_value in public_phones:
            saved += int(_save_contact(db, business.id, {
                "phone": phone_value,
                "title": "Website phone",
                "contact_type": "company",
                "verification_status": "unknown",
                "confidence": 1.0,
                "source": "website_crawl",
                "source_url": source_url,
            }))

    db.flush()
    return saved


def _has_actionable_contact(db, business: Business) -> bool:
    """A lead is actionable if we have an email OR a phone number — not both required."""
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == business.id).all()
    has_email = any(contact.email for contact in contacts)
    has_phone = bool(business.primary_phone) or any(contact.phone or contact.mobile for contact in contacts)
    return has_email or has_phone


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
    _save_social_profiles(db, business, audit.get("social_profiles") or [])

    page_map: Dict[str, int] = {}
    page_details = {
        (detail.get("url") or "").rstrip("/"): detail
        for detail in audit.get("page_details") or []
        if detail.get("url")
    }
    for page_url in audit.get("pages_checked") or []:
        detail = page_details.get(page_url.rstrip("/"), {})
        page = WebsitePage(
            website_id=website.id,
            url=page_url,
            page_type=detail.get("page_type") or _page_type(page_url),
            title=detail.get("title"),
            status_code=detail.get("status_code") or 200,
        )
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
        page_url = evidence.get("url")
        finding = evidence.get("content") or evidence.get("context") or ""
        if not finding:
            continue
        db.add(WebsiteEvidence(
            business_id=business.id,
            evidence_type=evidence.get("type") or "website_crawl",
            finding=finding,
            confidence=evidence.get("confidence") or 0.75,
            source_page_id=page_map.get(page_url) if page_url else None,
        ))
        evidence_records.append({
            "type": evidence.get("type") or "website_crawl",
            "finding": finding,
            "confidence": evidence.get("confidence") or 0.75,
            "source_url": page_url,
        })
        
    if not evidence_records:
        evidence_records.append({
            "type": "website_crawl",
            "finding": "Website is live and functional. Standard forms and CTAs appear to be present. Needs deeper analysis of messaging or performance.",
            "confidence": 1.0,
            "source_url": business.website_url,
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


def _save_social_profiles(db, business: Business, profiles: List[Dict[str, Any]]) -> int:
    """Persist public company social links without duplicating prior crawls."""
    existing_social_urls = {
        profile.profile_url
        for profile in db.query(SocialProfile).filter(SocialProfile.business_id == business.id).all()
    }
    saved = 0
    for profile in profiles:
        url = (profile.get("url") or "").strip()
        platform = (profile.get("platform") or "").strip().lower()
        if not url or not platform or url in existing_social_urls:
            continue
        db.add(SocialProfile(business_id=business.id, platform=platform, profile_url=url))
        existing_social_urls.add(url)
        saved += 1
    return saved


def _qualify_no_website_business(db, business: Business) -> int:
    """Qualify a business with no usable website and still research its people.

    A missing website is itself a high-signal prospect.  It must not cause the
    contact-enrichment workflow to stop: public search can still identify
    owners, titles, LinkedIn profiles, and a callable business number.
    """
    db.query(AIAnalysis).filter(AIAnalysis.business_id == business.id).delete()
    db.query(Opportunity).filter(Opportunity.business_id == business.id).delete()
    db.query(Score).filter(Score.business_id == business.id).delete()

    opportunity = Opportunity(
        business_id=business.id,
        primary_problem="No official website or usable digital home was found",
        problems=[
            "No official website was found during business discovery",
            "Potential customers have no owned web destination to learn, enquire, or book",
        ],
        recommended_offer="Launch-ready website and local lead-capture setup",
        ticket_low=2000,
        ticket_high=5000,
        outreach_angle=(
            f"{business.name} appears to have no official website, so local customers may be "
            "forced to rely on third-party listings instead of a direct path to call or enquire."
        ),
        ai_reasoning="Qualified from discovery evidence: no official website was found. Public contact research continues independently.",
        confidence="high",
    )
    db.add(opportunity)
    db.flush()
    db.add(Score(
        business_id=business.id,
        commercial_score=100,
        data_confidence=80,
        grade="A+",
        business_fit=100,
        digital_gap=100,
        offer_fit=100,
        buying_intent=80,
        contactability=50 if business.primary_phone else 20,
        score_version="v2-no-website",
    ))
    db.add(AIAnalysis(
        business_id=business.id,
        opportunity_id=opportunity.id,
        model_name="deterministic_rule",
        prompt_template="no_website_rule_with_public_contact_research",
        parsed_output={"confidence": "high", "primary_problem": "No official website found"},
    ))
    campaign = db.get(Campaign, business.campaign_id) if business.campaign_id else None
    if campaign:
        db.refresh(campaign)
    options = (campaign.settings or {}) if campaign else {}
    public_contacts = asyncio.run(lookup_optional_contacts(business, options.get("personal_email_enabled", False), options.get("phone_enabled", False)))
    saved_contacts = 0
    for contact in public_contacts:
        contact["source"] = contact.get("source") or "google_search_fallback"
        saved_contacts += int(_save_contact(db, business.id, contact))

    has_contact = (saved_contacts > 0) or bool(business.primary_phone) or _has_actionable_contact(db, business)
    final_status = "qualified" if has_contact else "needs_contact_enrichment"
    _set_business_status(db, business, final_status)

    db.add(CRMActivity(
        business_id=business.id,
        activity_type=final_status,
        body=(
            "Qualified as a no-website opportunity. Public contact research found "
            f"{saved_contacts} new decision-maker record(s); the business phone remains available as a fallback."
            if has_contact else
            "No official website and no callable contact found. Routed to needs review."
        ),
        created_by="Lead Intelligence",
    ))
    db.commit()
    return saved_contacts


@celery_app.task
def enrich_lead_contacts_task(business_id: int, personal_email_enabled: bool = False, phone_enabled: bool = False):
    is_live = os.getenv("DISCOVERY_MODE", "").strip().lower() == "live"
    if IS_STAGING and not is_live:
        return {"status": "completed", "contacts_added": 0, "mode": "mock"}
    db = SessionLocal()
    try:
        business = load_owned_job(db, Business, business_id)
        if not business:
            return {"status": "skipped", "reason": "Lead not found"}

        # No-website leads still deserve owner/decision-maker research.  The
        # prior implementation returned early here, leaving the highest-value
        # web-design prospects with no follow-up intelligence.
        if not business.website_url:
            contacts = asyncio.run(lookup_optional_contacts(business, personal_email_enabled, phone_enabled))
            saved = sum(int(_save_contact(db, business.id, contact)) for contact in contacts)
            db.add(CRMActivity(
                business_id=business.id,
                activity_type="enrichment",
                body=(
                    "No website is attached to this business, so contact research used public business and "
                    f"leadership results instead. {saved} new decision-maker record(s) were added."
                ),
                created_by="Lead Intelligence",
            ))
            db.commit()
            return {"status": "completed", "contacts_added": saved, "mode": "no_website_public_research"}
        
        try:
            audit = asyncio.run(asyncio.wait_for(WebsiteIntelligenceEngine().audit_website(business.website_url), timeout=240.0))
        except Exception as e:
            print(f"Crawler timeout/error on refresh for {business.website_url}: {e}")
            audit = {"social_profiles": [], "public_people": []}

        social_count = _save_social_profiles(db, business, audit.get("social_profiles") or [])
        website_contact_count = _save_public_website_contacts(db, business, audit)

        # 1. Save public people found on the website
        public_people = audit.get("public_people") or []
        website_contact_count += sum(int(_save_contact(db, business.id, person)) for person in public_people)

        optional_contacts = asyncio.run(lookup_optional_contacts(business, personal_email_enabled, phone_enabled))
        serper_count = sum(int(_save_contact(db, business.id, contact)) for contact in optional_contacts)

        total_contacts = website_contact_count + serper_count
        db.add(CRMActivity(
            business_id=business.id,
            activity_type="enrichment",
            body=f"Contact research completed: {total_contacts} contacts found ({website_contact_count} from website, {serper_count} from optional lookups) and {social_count} social profiles added.",
            created_by="Lead Intelligence",
        ))
        db.commit()
        return {"status": "completed", "contacts_added": total_contacts, "social_profiles_added": social_count}
    except Exception as exc:
        db.rollback()
        print(f"Lead enrichment {business_id} failed: {exc}")
        return {"status": "failed"}
    finally:
        db.close()


def _fallback_sdr_diagnosis(business: Business, audit: Dict[str, Any], evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> Dict[str, Any]:
    problems = []
    if audit and not audit.get("mobile_responsive", True):
        problems.append("Website layout is not optimized for mobile visitors")
    if audit and not audit.get("booking_detected", True):
        problems.append("No instant online booking or scheduling system detected")
    if audit and not audit.get("quote_form", True) and not audit.get("contact_form", True):
        problems.append("No frictionless lead capture or quick quote funnel on the homepage")
    if audit and not audit.get("phone_cta", True):
        problems.append("Missing prominent click-to-call CTA for mobile users")
    if not problems:
        problems = [
            "Digital conversion funnel has friction points that cause visitor drop-off",
            "Outdated web architecture lacks automated lead capture mechanisms"
        ]

    primary_problem = problems[0]
    recommended_offer = "Custom High-Converting Web Application & Booking Funnel"
    ticket_low = 2500
    ticket_high = 6000
    biz_name = business.name or "your business"
    outreach_angle = f"Noticed {biz_name}'s website is missing a streamlined digital booking funnel, losing potential customers to competitors."
    ai_reasoning = f"Automated SDR rule-based analysis: detected key conversion barriers ({', '.join(problems[:2])}). Devacia's high-converting web applications directly address these gaps."

    return {
        "primary_problem": primary_problem,
        "problems": problems,
        "recommended_offer": recommended_offer,
        "ticket_low": ticket_low,
        "ticket_high": ticket_high,
        "outreach_angle": outreach_angle,
        "ai_reasoning": ai_reasoning,
        "confidence": "medium",
        "evidence_types_used": [e.get("evidence_type", "website_audit") for e in evidence] if evidence else ["website_audit"]
    }


@celery_app.task
def process_campaign_task(campaign_id: int):
    """Run live discovery and admit only research-backed, contactable leads into the CRM."""
    db = SessionLocal()
    job: Optional[JobRun] = None
    try:
        campaign = load_owned_job(db, Campaign, campaign_id)
        if not campaign:
            return {"status": "failed", "reason": "Campaign not found"}

        if IS_STAGING and os.getenv("DISCOVERY_MODE", "").strip().lower() != "live":
            from core.staging_jobs import run_mock_campaign
            return run_mock_campaign(db, campaign)

        job = JobRun(campaign_id=campaign_id, stage="lead_intelligence", status="running", metrics={})
        db.add(job)
        db.commit()
        db.refresh(job)

        config = db.query(IndustryConfig).filter(IndustryConfig.id == campaign.industry_id).first()
        industry_config = getattr(config, "settings", None) or getattr(config, "signals", None) or {}
        industry_raw = campaign.industry.name if campaign.industry else "Local business"
        # Map internal industry values to search-friendly Google Maps terms
        industry_map = {
            # Frontend industry values
            "roofing": "roofing contractor",
            "hvac": "HVAC company",
            "cleaning": "cleaning service company",
            "restaurant": "restaurant",
            "clinic": "medical clinic",
            "real_estate": "real estate agency",
            "d2c": "ecommerce store",
            "wedding": "wedding photographer",
            # Extended industry values
            "architecture": "architecture firm",
            "architect": "architecture firm",
            "agriculture": "agricultural business",
            "farming": "farm supply company",
            "construction": "construction company",
            "plumbing": "plumbing contractor",
            "electrical": "electrical contractor",
            "landscaping": "landscaping company",
            "law": "law firm",
            "legal": "law firm",
            "accounting": "accounting firm",
            "dental": "dental clinic",
            "dentist": "dentist",
            "gym": "fitness gym",
            "fitness": "fitness center",
            "salon": "hair salon",
            "spa": "day spa",
            "hotel": "hotel",
            "logistics": "logistics company",
            "trucking": "trucking company",
            "auto": "auto repair shop",
            "car": "car dealership",
            "insurance": "insurance agency",
            "marketing": "marketing agency",
            "software": "software company",
            "tech": "technology company",
            "printing": "printing company",
            "photography": "photography studio",
            "catering": "catering company",
            "bakery": "bakery",
            "flooring": "flooring company",
            "painting": "painting contractor",
            "pest": "pest control company",
            "security": "security company",
            "solar": "solar energy company",
            "staffing": "staffing agency",
            "travel": "travel agency",
            "tutoring": "tutoring center",
            "childcare": "daycare center",
        }
        search_term = industry_map.get(industry_raw.lower(), industry_raw.replace("_", " "))
        industry_name = search_term
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
        # Oversample candidate pool up to twice the remaining target (bounded at 1,000)
        fetch_limit = min(1000, max(discovery_needed * 2, 20)) if discovery_needed else 0
        per_location_limit = max(1, math.ceil(fetch_limit / len(locations))) if fetch_limit else 0
        raw_businesses: List[Dict[str, Any]] = []
        for location in locations:
            if not discovery_needed:
                break
            remaining = fetch_limit - len(raw_businesses)
            if remaining <= 0:
                break
            batch = asyncio.run(provider.discover(
                query=industry_name,
                location=_location_label(location),
                industry=industry_name,
                limit=min(per_location_limit, remaining),
            ))
            for item in batch:
                item["_campaign_location"] = location
            raw_businesses.extend(batch)

        dedupe = DeduplicationEngine()
        unique_businesses = dedupe.deduplicate(raw_businesses)
        saved_businesses: List[Business] = list(resumable_businesses)
        for raw in unique_businesses:
            if len(saved_businesses) >= fetch_limit:
                break
            if not raw.get("name"):
                continue
            existing = _existing_business(db, raw)
            if existing:
                if existing.campaign_id == campaign_id:
                    if existing not in saved_businesses:
                        saved_businesses.append(existing)
                    continue
                # Never re-appropriate or repeat an already discovered lead in a new campaign
                print(f"Skipping previously gathered lead '{raw.get('name')}' (already in Campaign {existing.campaign_id}) to prevent duplicates.")
                continue
            loc = raw.get("_campaign_location") or (locations[0] if locations else None)
            loc_country = loc.country if loc and loc.country else raw.get("country")
            loc_state = loc.region_state if loc else raw.get("state_province")
            loc_city = loc.city if loc and loc.city else raw.get("city")
            primary_phone = clean_phone_for_country(raw.get("primary_phone"), loc_country)
            business = Business(
                campaign_id=campaign_id,
                name=raw["name"].strip(),
                normalized_name=raw["name"].strip().lower(),
                industry=industry_name,
                country=loc_country,
                state_province=loc_state,
                city=loc_city,
                postal_code=raw.get("postal_code"),
                address=raw.get("address"),
                latitude=raw.get("latitude"),
                longitude=raw.get("longitude"),
                primary_phone=primary_phone,
                website_url=clean_website_url(raw.get("website_url")),
                website_domain=_domain(clean_website_url(raw.get("website_url"))),
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
        ai_sdr = GroqProvider()
        qualified_count = 0
        audited_count = 0
        enriched_count = 0

        for business in saved_businesses:
            if qualified_count >= target_quantity:
                break
            if not business.website_url:
                enriched_count += _qualify_no_website_business(db, business)
                if business.status == "qualified":
                    qualified_count += 1
                continue

            try:
                # Guard: if the URL is a directory/Wikipedia/chain HQ, treat as no-website
                from providers.serper_discovery_provider import _is_junk_website
                if _is_junk_website(business.website_url):
                    print(f"Skipping junk website for {business.name}: {business.website_url}")
                    business.website_url = None
                    # A directory/social link is not an official site. Process
                    # it as a no-website lead in this same run instead of
                    # re-queuing it and silently losing the contact work.
                    enriched_count += _qualify_no_website_business(db, business)
                    if business.status == "qualified":
                        qualified_count += 1
                    continue

                audit = asyncio.run(asyncio.wait_for(crawler.audit_website(business.website_url), timeout=240.0))
            except Exception as e:
                print(f"Crawler timeout/error for {business.website_url}: {e}")
                _set_business_status(db, business, "rejected_unreachable")
                db.commit()
                continue

            _, evidence = _persist_website_research(db, business, audit)
            audited_count += 1
            if not audit.get("is_live"):
                _set_business_status(db, business, "rejected_unreachable")
                db.commit()
                continue

            final_url = next(iter(audit.get("pages_checked") or []), None)
            if final_url:
                cleaned_final = clean_website_url(final_url)
                if cleaned_final and (not business.website_url or _domain(cleaned_final) != _domain(business.website_url)):
                    business.website_url = cleaned_final
                    business.website_domain = _domain(cleaned_final)
                    db.commit()

            public_emails = sorted({email.lower().strip() for email in audit.get("emails") or [] if email})
            _save_public_website_contacts(db, business, audit)

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
                _set_business_status(db, business, "below_quality_threshold")
                db.commit()
                continue

            # 1. Save public people found on the website
            public_people = audit.get("public_people") or []
            for person in public_people:
                _save_contact(db, business.id, person)

            db.refresh(campaign)
            options = campaign.settings or {}
            provider_contacts: List[Dict[str, Any]] = []
            provider_contacts.extend(asyncio.run(lookup_optional_contacts(
                business, options.get("personal_email_enabled", False), options.get("phone_enabled", False)
            )))
            for contact in provider_contacts:
                enriched_count += int(_save_contact(db, business.id, contact))
            db.commit()


            diagnosis = asyncio.run(ai_sdr.analyze(evidence, industry_config))
            if not diagnosis:
                print(f"ai_sdr.analyze returned None for {business.name}; applying fallback SDR diagnosis.")
                diagnosis = _fallback_sdr_diagnosis(business, audit, evidence, industry_config)

            # Always save AI output, even if confidence is low. 
            # We will just mark low confidence as "needs_research" after saving.
            is_low_confidence = diagnosis.get("confidence") not in {"high", "medium"}

            # Clean up old records before creating new ones on a re-run
            db.query(AIAnalysis).filter(AIAnalysis.business_id == business.id).delete()
            db.query(Opportunity).filter(Opportunity.business_id == business.id).delete()
            db.query(Score).filter(Score.business_id == business.id).delete()
            
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
                model_name=ai_sdr.model_name,
                prompt_template="research_gated_website_evidence",
                parsed_output=diagnosis,
            ))
            # Determine final status incorporating confidence and contact gate
            has_contact = _has_actionable_contact(db, business) or bool(business.primary_phone)
            
            if is_low_confidence:
                final_status = "needs_research"
                stage = "needs_review"
                activity_body = "AI Analysis saved, but low confidence. Needs human review."
            elif not has_contact:
                final_status = "needs_contact_enrichment"
                stage = "needs_review"
                activity_body = "AI Analysis saved, but no actionable contact (email/phone) was found."
            else:
                final_status = "qualified"
                stage = "qualified"
                activity_body = "Qualified from live discovery, website research, AI analysis, and contact enrichment."

            _set_business_status(db, business, final_status)
            
            db.add(CRMActivity(

                business_id=business.id,
                activity_type=stage,
                body=activity_body,
                created_by="Lead Intelligence",
            ))
            db.commit()
            if final_status == "qualified":
                qualified_count += 1

        # Remove unused reserve candidates still in researching state
        unreached_businesses = (
            db.query(Business)
            .filter(Business.campaign_id == campaign_id, Business.status == "researching")
            .all()
        )
        for u in unreached_businesses:
            db.query(BusinessSource).filter(BusinessSource.business_id == u.id).delete()
            db.delete(u)
        db.commit()

        total_qualified = (
            db.query(Business)
            .filter(Business.campaign_id == campaign_id, Business.status == "qualified")
            .count()
        )
        total_delivered = (
            db.query(Business)
            .filter(Business.campaign_id == campaign_id)
            .count()
        )
        campaign.status = "completed" if total_qualified >= target_quantity else "completed_partial"
        job.status = campaign.status
        job.completed_at = datetime.now(timezone.utc)
        job.metrics = {
            "discovered": total_delivered,
            "deduplicated": len(unique_businesses),
            "saved": total_delivered,
            "audited": audited_count,
            "enriched_contacts": enriched_count,
            "qualified": total_qualified,
        }
        db.commit()
        return {"status": campaign.status, **job.metrics}
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
