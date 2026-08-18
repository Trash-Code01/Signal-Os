import os
import asyncio
from celery import Celery

from core.database import SessionLocal
from core.models import (
    Campaign, Business, Website, WebsiteAudit, Evidence, 
    Opportunity, Score, IndustryConfig, DecisionMaker, SocialProfile
)
from providers.mock_discovery import MockDiscoveryProvider
from providers.gemini_provider import GeminiProvider
from providers.hunter_provider import HunterProvider
from providers.apollo_provider import ApolloProvider
from engines.website_intelligence import WebsiteIntelligenceEngine
from engines.scoring import ScoringEngine
from core.deduplication import DeduplicationEngine

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "devacia_worker",
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task
def process_campaign_task(campaign_id: int):
    # Pipeline: Discovery -> Deduplication -> Audit -> AI -> Scoring -> Enrichment
    print(f"Processing campaign {campaign_id}")
    
    db = SessionLocal()
    try:
        # 1. Fetch Campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "reason": "Campaign not found"}
            
        industry_config_model = db.query(IndustryConfig).filter(IndustryConfig.id == campaign.industry_id).first()
        industry_config = industry_config_model.signals if industry_config_model else {}
        industry_name = campaign.industry.name if campaign.industry else "Roofing"
        location = campaign.cities[0] if campaign.cities else "Dallas, TX"
        
        # 2. Discovery
        use_mock = os.environ.get("USE_MOCK_DISCOVERY", "true").lower() == "true"
        if use_mock:
            discovery_provider = MockDiscoveryProvider()
        else:
            from providers.dataforseo_provider import DataForSEOProvider
            discovery_provider = DataForSEOProvider()
            
        raw_businesses = asyncio.run(discovery_provider.discover(
            query=f"{industry_name} contractors", 
            location=location,
            industry=industry_name
        ))
        
        # 3. Deduplication
        dedupe_engine = DeduplicationEngine(db_session=db)
        unique_businesses = dedupe_engine.deduplicate(raw_businesses)
        
        # 4. Save to Database
        saved_businesses = []
        for b_data in unique_businesses:
            new_business = Business(
                campaign_id=campaign_id,
                name=b_data["name"],
                domain=b_data.get("domain"),
                phone=b_data.get("phone"),
                address=b_data.get("address"),
                city=b_data.get("city"),
                state=b_data.get("state"),
                country=b_data.get("country"),
                place_id=b_data.get("place_id"),
                source_metadata=b_data.get("source_metadata", {})
            )
            db.add(new_business)
            db.commit()
            db.refresh(new_business)
            saved_businesses.append(new_business)
            
        print(f"Saved {len(saved_businesses)} new unique businesses.")

        # 5. Website Intelligence Engine & Evidence
        crawler = WebsiteIntelligenceEngine()
        gemini = GeminiProvider()
        scorer = ScoringEngine(industry_config)
        
        for business in saved_businesses:
            if not business.domain:
                continue
                
            # Playwright Crawl
            audit_result = asyncio.run(crawler.audit_website(business.domain))
            
            # Save Website Record
            website = Website(
                business_id=business.id,
                url=f"https://{business.domain}",
                is_live=audit_result.get("is_live", False),
                has_ssl=audit_result.get("has_ssl", False),
                technology_stack=audit_result.get("technology_stack", [])
            )
            db.add(website)
            
            # Update Business Emails/Phones from website crawler
            if audit_result.get("emails"):
                business.company_email = audit_result["emails"][0]
            
            db.commit()
            
            # Save Website Audit Record
            website_audit = WebsiteAudit(
                business_id=business.id,
                booking_detected=audit_result.get("booking_detected", False),
                ecommerce_detected=audit_result.get("ecommerce_detected", False),
            )
            db.add(website_audit)
            db.commit()
            
            # Save Evidence
            evidence_records = []
            for ev in audit_result.get("evidence", []):
                new_ev = Evidence(
                    business_id=business.id,
                    source_type=ev["source_type"],
                    evidence_text=ev["evidence_text"],
                    confidence=ev["confidence"],
                    page_url=ev["page_url"]
                )
                db.add(new_ev)
                evidence_records.append({"evidence_text": ev["evidence_text"]}) # Pass to AI
                
            if audit_result.get("desktop_screenshot_base64"):
                new_ev = Evidence(
                    business_id=business.id,
                    source_type="playwright_screenshot",
                    evidence_text="Desktop Screenshot Captured",
                    confidence=1.0,
                    evidence_url="Base64 Image Stored"
                )
                db.add(new_ev)
                
            db.commit()
            
            # 6. AI SDR Reasoning
            ai_diagnosis = asyncio.run(gemini.analyze(evidence_records, industry_config))
            
            # 7. Scoring
            # Calculate mock scores based on AI output for MVP
            score_record = Score(
                business_id=business.id,
                business_fit=20,
                website_gap=15,
                ux_ui_gap=10,
                conversion_gap=15,
                offer_fit=15,
                contactability=10,
                total_score=85 # Hardcoded standard passing score for MVP
            )
            db.add(score_record)
            db.commit()
            
            # 7.5 Contact Enrichment Waterfall (Only if score >= 80)
            if score_record.total_score >= 80:
                print(f"Lead {business.name} scored {score_record.total_score}. Initiating contact enrichment...")
                hunter = HunterProvider()
                apollo = ApolloProvider()
                
                # Waterfall: Try Hunter first
                contacts = asyncio.run(hunter.find_emails(domain=business.domain))
                
                # If Hunter fails or returns no contacts, fallback to Apollo
                if not contacts:
                    print(f"Hunter returned no contacts for {business.domain}. Falling back to Apollo...")
                    contacts = asyncio.run(apollo.find_emails(domain=business.domain))
                    
                # Save contacts
                for c_data in contacts:
                    new_contact = DecisionMaker(
                        business_id=business.id,
                        first_name=c_data.get("first_name"),
                        last_name=c_data.get("last_name"),
                        title=c_data.get("title", "Owner"),
                        email=c_data.get("email"),
                        phone=c_data.get("phone"),
                        source=c_data.get("source", "apollo"),
                        email_status="verified"
                    )
                    db.add(new_contact)
                db.commit()
            
            # 8. Opportunity Generation
            opp = Opportunity(
                business_id=business.id,
                primary_problem=ai_diagnosis.get("primary_problem", "No booking system found"),
                outreach_angle=ai_diagnosis.get("outreach_angle", "Pitch standard booking system"),
                ai_summary=ai_diagnosis.get("reasoning", "Good fit"),
                estimated_value="$3,500"
            )
            db.add(opp)
            db.commit()
            
            print(f"Finished pipeline for {business.name}. Score: {score_record.total_score}")
        
        return {"status": "success", "businesses_processed": len(unique_businesses)}
        
    except Exception as e:
        print(f"Error in campaign task: {e}")
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
