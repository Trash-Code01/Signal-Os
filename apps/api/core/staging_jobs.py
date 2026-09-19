from datetime import datetime, timezone
import re
from core.models import (
    Business,
    BusinessSource,
    CRMLead,
    JobRun,
    CampaignLocation,
    Opportunity,
    Score,
    Website,
    WebsiteAudit,
    DecisionMaker,
    CRMActivity,
)


def run_mock_campaign(db, campaign):
    """Deterministic fixtures with realistic website crawl data and optional personal enrichment."""
    if db.query(Business.id).filter(Business.campaign_id == campaign.id).first():
        return {"status": "completed", "mode": "mock"}

    location = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == campaign.id).first()
    count = min(max(campaign.target_quantity or 1, 1), 20)

    settings = campaign.settings or {}
    personal_email_enabled = bool(settings.get("personal_email_enabled", False))
    phone_enabled = bool(settings.get("phone_enabled", False))

    ind_name = campaign.industry.name if campaign.industry else "Roofing"
    city = location.city if location and location.city else "Dallas"
    state = location.region_state if location and location.region_state else "Texas"
    country = location.country if location and location.country else "USA"

    sample_names = [
        f"Apex {ind_name.title()} Solutions",
        f"Summit Commercial {ind_name.title()}",
        f"Vanguard {ind_name.title()} Group",
        f"Lone Star {ind_name.title()} Pros",
        f"Pinnacle {ind_name.title()} & Services",
        f"Heritage {ind_name.title()} Co",
        f"NextGen {ind_name.title()} Works",
        f"Paramount {ind_name.title()} Experts",
        f"TrueNorth {ind_name.title()} Specialists",
        f"Metro {ind_name.title()} Contractors",
    ]

    first_names = ["David", "Michael", "Sarah", "James", "Elena", "Robert", "Jennifer", "Thomas", "Lisa", "William"]
    last_names = ["Miller", "Sterling", "Davis", "Vance", "Harrison", "Carter", "Brooks", "Mitchell", "Morgan", "Price"]

    for number in range(1, count + 1):
        biz_name = sample_names[(number - 1) % len(sample_names)]
        if number > len(sample_names):
            biz_name = f"{biz_name} #{number}"

        slug = re.sub(r"[^a-z0-9]+", "", biz_name.lower())
        crawl_email = f"contact@{slug}.com"
        crawl_phone = f"+1 214-555-01{number:02d}"

        business = Business(
            campaign_id=campaign.id,
            name=biz_name,
            normalized_name=biz_name.lower(),
            industry=ind_name,
            country=country,
            state_province=state,
            city=city,
            address=f"{100 + number * 14} Commercial Blvd, Suite {number}",
            primary_phone=crawl_phone,
            website_url=f"https://{slug}.com",
            website_domain=f"{slug}.com",
            status="qualified",
            rating=4.8,
            review_count=35 + number * 7,
        )
        db.add(business)
        db.flush()

        db.add(BusinessSource(business_id=business.id, source="mock", source_url=f"https://maps.google.com/?q={slug}"))

        # Add Website and Audit
        website = Website(
            business_id=business.id,
            url=business.website_url,
            is_live=True,
            has_ssl=True,
            cms="WordPress",
        )
        db.add(website)
        db.flush()

        db.add(WebsiteAudit(
            website_id=website.id,
            mobile_responsive=True,
            mobile_ux_score=88,
            desktop_ux_score=92,
            accessibility_score=90,
            contact_form=True,
            quote_form=True,
            phone_cta=True,
        ))

        # Add Opportunity & AI Diagnosis
        opportunity = Opportunity(
            business_id=business.id,
            primary_problem="Website lacks automated quote estimation and click-to-call CTA",
            problems=["Missing instant quote calculator", "No direct calendar booking link"],
            recommended_offer="Full-stack conversion engine & Google Business optimization",
            ticket_low=2500,
            ticket_high=6000,
            outreach_angle=f"{business.name} is missing a quick-quote form on their website, costing them inbound leads.",
            ai_reasoning="Discovered via high-intent local search with active web domain and public contact line.",
            confidence="high",
        )
        db.add(opportunity)

        # Add Score
        score = Score(
            business_id=business.id,
            commercial_score=85 + (number % 10),
            grade="A+" if number % 2 == 0 else "A",
            data_confidence=92,
            business_fit=90,
            digital_gap=80,
            offer_fit=88,
            buying_intent=85,
        )
        db.add(score)

        # ALWAYS ADD PUBLIC CRAWL CONTACT (Website crawled email & phone)
        db.add(DecisionMaker(
            business_id=business.id,
            first_name=biz_name,
            last_name="Office",
            title="General Inquiries",
            email=crawl_email,
            phone=crawl_phone,
            contact_type="company",
            source="website_crawl",
            source_url=f"https://{slug}.com/contact",
            verification_status="verified",
            confidence=1.0,
        ))

        # ONLY IF USER TOGGLED PERSONAL CONTACTS ON:
        if personal_email_enabled or phone_enabled:
            fn = first_names[(number - 1) % len(first_names)]
            ln = last_names[(number - 1) % len(last_names)]
            personal_email = f"{fn.lower()}.{ln.lower()}@{slug}.com" if personal_email_enabled else None
            personal_phone = f"+1 214-777-09{number:02d}" if phone_enabled else None

            db.add(DecisionMaker(
                business_id=business.id,
                first_name=fn,
                last_name=ln,
                title="Managing Partner",
                email=personal_email,
                phone=personal_phone,
                mobile=personal_phone,
                contact_type="personal",
                source="snovio",
                verification_status="verified",
                confidence=0.95,
            ))

        # Add CRM Lead
        db.add(CRMLead(business_id=business.id, stage="qualified", source="campaign"))

        activity_text = (
            f"Qualified with public crawl email ({crawl_email}) and crawled phone ({crawl_phone})."
            + (" Enriched with personal decision maker." if (personal_email_enabled or phone_enabled) else " Personal lookup toggles were OFF (default).")
        )
        db.add(CRMActivity(
            business_id=business.id,
            activity_type="qualified",
            body=activity_text,
            created_by="Lead Intelligence",
        ))

    campaign.status = "completed"
    db.add(JobRun(
        campaign_id=campaign.id,
        stage="lead_intelligence",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        metrics={"mode": "mock", "discovered": count, "qualified": count, "paid_requests": 0},
    ))
    db.commit()
    return {"status": "completed", "mode": "mock", "discovered": count, "qualified": count}
