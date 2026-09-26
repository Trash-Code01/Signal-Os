from datetime import datetime, timezone
import re
from core.models import (
    Business,
    BusinessSource,
    Campaign,
    CRMLead,
    DecisionMaker,
    JobRun,
    CampaignLocation,
    Opportunity,
    Score,
    Website,
    WebsiteAudit,
    CRMActivity,
)


def sanitize_legacy_mock_data(engine) -> int:
    """Make older staging fixtures unmistakably synthetic and remove fake contacts."""
    from core.database import SessionLocal

    db = SessionLocal(bind=engine)
    db.info["system_access"] = True
    try:
        mock_ids = [
            row[0]
            for row in db.query(BusinessSource.business_id)
            .filter(BusinessSource.source.in_(("mock", "fixture")))
            .distinct()
            .all()
        ]
        if not mock_ids:
            return 0

        businesses = db.query(Business).filter(Business.id.in_(mock_ids)).all()
        campaign_ids = {business.campaign_id for business in businesses if business.campaign_id}
        locations = {
            location.campaign_id: location
            for location in db.query(CampaignLocation)
            .filter(CampaignLocation.campaign_id.in_(campaign_ids))
            .order_by(CampaignLocation.id.asc())
            .all()
        }

        db.query(DecisionMaker).filter(DecisionMaker.business_id.in_(mock_ids)).delete(synchronize_session=False)
        for business in businesses:
            location = locations.get(business.campaign_id)
            clean_slug = re.sub(r"[^a-z0-9]+", "-", (business.name or "business").lower()).strip("-")
            domain = f"{clean_slug}-{business.id}.test.invalid"
            business.website_url = f"https://{domain}"
            business.website_domain = domain
            business.primary_phone = None
            business.address = "Synthetic staging fixture"
            if location:
                business.city = location.city
                business.state_province = location.region_state or None
                business.country = location.country

            for website in db.query(Website).filter(Website.business_id == business.id).all():
                website.url = business.website_url
                website.is_live = False
                website.has_ssl = None
                website.cms = None
                audit = db.query(WebsiteAudit).filter(WebsiteAudit.website_id == website.id).first()
                if audit:
                    audit.mobile_responsive = None
                    audit.mobile_ux_score = None
                    audit.desktop_ux_score = None
                    audit.accessibility_score = None
                    audit.contact_form = None
                    audit.quote_form = None
                    audit.phone_cta = None

            for score in db.query(Score).filter(Score.business_id == business.id).all():
                score.commercial_score = 0
                score.data_confidence = 0
                score.grade = "U"
            for opportunity in db.query(Opportunity).filter(Opportunity.business_id == business.id).all():
                opportunity.primary_problem = "Synthetic staging fixture; live website research was not run"
                opportunity.problems = ["Live discovery and crawling are disabled in staging"]
                opportunity.recommended_offer = "Run this campaign in production to collect research-backed leads"
                opportunity.outreach_angle = None
                opportunity.ai_reasoning = "This record exists only to test workflow behavior."
                opportunity.confidence = "low"

        for campaign in db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).all():
            campaign.settings = {**(campaign.settings or {}), "data_mode": "synthetic"}

        db.commit()
        return len(businesses)
    finally:
        db.close()


def run_mock_campaign(db, campaign):
    """Create unmistakable synthetic fixtures without invented contact facts."""
    started_at = datetime.now(timezone.utc)
    location = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == campaign.id).first()
    target_count = min(max(campaign.target_quantity or 1, 1), 500)
    existing_count = db.query(Business.id).filter(Business.campaign_id == campaign.id).count()
    count = max(0, target_count - existing_count)

    if count == 0:
        campaign.status = "completed"
        db.commit()
        return {
            "status": "completed",
            "mode": "mock",
            "discovered": existing_count,
            "qualified": existing_count,
        }

    ind_name = (campaign.industry.name if campaign.industry else "Roofing").strip()
    city = location.city if location and location.city else "Synthetic test city"
    state = location.region_state if location else None
    country = location.country if location and location.country else "Synthetic test country"

    from core.deduplication import find_existing_business

    prefixes = [
        "Apex", "Summit", "Vanguard", "Lone Star", "Pinnacle", "Heritage",
        "NextGen", "Paramount", "TrueNorth", "Metro", "Sterling", "BlueSky",
        "Optima", "Prime", "Integrity", "Titan", "Zenith", "Horizon",
        "Ascent", "Frontier", "Benchmark", "Endeavor", "Keystone", "Noble",
        "Valor", "Beacon", "Crestview", "Radiant", "Elevate", "Velocity",
        "Signature", "Ironclad", "Atlas", "Oasis", "Liberty", "Evergreen"
    ]
    modifiers = [
        "", "Commercial ", "Premier ", "Elite ", "Pro ", "Advanced ",
        "Precision ", "Master ", "Dynamic ", "Direct ", "Select "
    ]
    suffixes = [
        "Solutions", "Group", "Pros", "Services", "Co", "Works",
        "Experts", "Specialists", "Contractors", "Partners", "Enterprises"
    ]

    # Offset candidate generation by existing business count in database to guarantee novel leads
    base_offset = db.query(Business.id).count() + (campaign.id * 17)
    created_count = 0
    candidate_attempt = 0

    while created_count < count and candidate_attempt < 10000:
        candidate_attempt += 1
        seq = base_offset + candidate_attempt

        p_idx = seq % len(prefixes)
        m_idx = (seq // len(prefixes)) % len(modifiers)
        s_idx = (seq // (len(prefixes) * len(modifiers))) % len(suffixes)

        prefix = prefixes[p_idx]
        modifier = modifiers[m_idx]
        suffix = suffixes[s_idx]

        biz_name = f"{prefix} {modifier}{ind_name.title()} {suffix}".replace("  ", " ").strip()
        clean_slug = re.sub(r"[^a-z0-9]+", "-", biz_name.lower()).strip("-")
        website_domain = f"{clean_slug}-{seq}.test.invalid"
        website_url = f"https://{website_domain}"

        # Check if this candidate already exists in the CRM or database
        duplicate = find_existing_business(db, {
            "google_place_id": None,
            "website_url": website_url,
            "name": biz_name,
            "city": city,
        })
        if duplicate:
            continue

        created_count += 1
        number = created_count

        business = Business(
            campaign_id=campaign.id,
            name=biz_name,
            normalized_name=biz_name.lower(),
            industry=ind_name,
            country=country,
            state_province=state,
            city=city,
            address="Synthetic staging fixture",
            primary_phone=None,
            website_url=website_url,
            website_domain=website_domain,
            status="qualified",
            rating=4.8,
            review_count=35 + number * 7,
        )
        db.add(business)
        db.flush()

        db.add(BusinessSource(business_id=business.id, source="mock", source_url=None))

        # Add Website and Audit
        website = Website(
            business_id=business.id,
            url=business.website_url,
            is_live=False,
            has_ssl=None,
            cms=None,
        )
        db.add(website)
        db.flush()

        db.add(WebsiteAudit(
            website_id=website.id,
            mobile_responsive=None,
            mobile_ux_score=None,
            desktop_ux_score=None,
            accessibility_score=None,
            contact_form=None,
            quote_form=None,
            phone_cta=None,
        ))

        # Add Opportunity & AI Diagnosis
        opportunity = Opportunity(
            business_id=business.id,
            primary_problem="Synthetic staging fixture; live website research was not run",
            problems=["Live discovery and crawling are disabled in staging"],
            recommended_offer="Run this campaign in production to collect research-backed leads",
            ticket_low=None,
            ticket_high=None,
            outreach_angle=None,
            ai_reasoning="This record exists only to test campaign counts, isolation, and workflow behavior.",
            confidence="low",
        )
        db.add(opportunity)

        # Add Score
        score = Score(
            business_id=business.id,
            commercial_score=0,
            grade="U",
            data_confidence=0,
            business_fit=0,
            digital_gap=0,
            offer_fit=0,
            buying_intent=0,
        )
        db.add(score)

        # Add CRM Lead
        db.add(CRMLead(business_id=business.id, stage="qualified", source="campaign"))

        db.add(CRMActivity(
            business_id=business.id,
            activity_type="qualified",
            body="Synthetic staging fixture. No business, website, email, phone, or person was scraped.",
            created_by="Lead Intelligence",
        ))

    total_count = existing_count + created_count
    campaign.status = "completed" if total_count >= target_count else "completed_partial"
    db.add(JobRun(
        campaign_id=campaign.id,
        stage="lead_intelligence",
        status=campaign.status,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        metrics={"mode": "mock", "discovered": total_count, "qualified": total_count, "paid_requests": 0},
    ))
    db.commit()
    return {"status": campaign.status, "mode": "mock", "discovered": total_count, "qualified": total_count}
