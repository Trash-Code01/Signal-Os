import os
import asyncio
from celery import Celery

from core.database import SessionLocal
from core.models import Campaign, Business, Website, Evidence, Opportunity, Score, IndustryConfig
from providers.mock_discovery import MockDiscoveryProvider
from providers.gemini_provider import GeminiProvider
from providers.hunter_provider import HunterProvider
from providers.apollo_provider import ApolloProvider
from engines.website_intelligence import WebsiteIntelligenceEngine
from engines.scoring import ScoringEngine
from core.deduplication import DeduplicationEngine

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

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
    # Pipeline: Discovery -> Deduplication -> Audit -> AI -> Scoring
    print(f"Processing campaign {campaign_id}")
    
    db = SessionLocal()
    try:
        # 1. Fetch Campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "reason": "Campaign not found"}
            
        industry_config_model = db.query(IndustryConfig).filter(IndustryConfig.id == campaign.industry_id).first()
        industry_config = industry_config_model.signals if industry_config_model else {}
        
        # 2. Discovery
        from providers.dataforseo_provider import DataForSEOProvider
        use_mock = os.environ.get("USE_MOCK_DISCOVERY", "true").lower() == "true"
        
        if use_mock:
            discovery_provider = MockDiscoveryProvider()
        else:
            discovery_provider = DataForSEOProvider()
            
        raw_businesses = asyncio.run(discovery_provider.discover(
            query=f"{campaign.industry.name} contractors", 
            location=campaign.cities[0] if campaign.cities else "Dallas, TX",
            industry=campaign.industry.name if campaign.industry else "Roofing"
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
                has_ssl=audit_result.get("has_ssl", False)
            )
            db.add(website)
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
            db.commit()
            
            # 6. AI SDR Reasoning
            ai_diagnosis = asyncio.run(gemini.analyze(evidence_records, industry_config))
            
            # 7. Scoring
            total_score = scorer.calculate_score(ai_diagnosis)
            
            score_record = Score(
                business_id=business.id,
                business_fit=ai_diagnosis.get("business_fit_score", 0),
                digital_gap=ai_diagnosis.get("digital_gap_score", 0),
                offer_fit=ai_diagnosis.get("offer_fit_score", 0),
                buying_intent=ai_diagnosis.get("buying_intent_score", 0),
                contactability=ai_diagnosis.get("contactability_score", 0),
                total_score=total_score
            )
            db.add(score_record)
            
            # 7.5 Contact Enrichment Waterfall (Only if score >= 80)
            if total_score >= 80:
                print(f"Lead {business.name} scored {total_score}. Initiating contact enrichment...")
                hunter = HunterProvider()
                apollo = ApolloProvider()
                
                # Waterfall: Try Hunter first
                contacts = asyncio.run(hunter.find_emails(domain=business.domain))
                
                # If Hunter fails or returns no contacts, fallback to Apollo
                if not contacts:
                    print(f"Hunter returned no contacts for {business.domain}. Falling back to Apollo...")
                    contacts = asyncio.run(apollo.find_emails(domain=business.domain))
                    
                # Save contacts
                from core.models import Contact
                for c_data in contacts:
                    new_contact = Contact(
                        business_id=business.id,
                        first_name=c_data.get("first_name"),
                        last_name=c_data.get("last_name"),
                        title=c_data.get("title"),
                        email=c_data.get("email"),
                        phone=c_data.get("phone"),
                        source=c_data.get("source"),
                        confidence=c_data.get("confidence")
                    )
                    db.add(new_contact)
                db.commit()
            
            # 8. Opportunity Generation
            opp = Opportunity(
                business_id=business.id,
                primary_problem=ai_diagnosis.get("primary_problem", ""),
                outreach_angle=ai_diagnosis.get("outreach_angle", ""),
                ai_reasoning=ai_diagnosis.get("reasoning", "")
                # recommended_offer_id can be mapped if we fetch offers
            )
            db.add(opp)
            db.commit()
            
            print(f"Finished pipeline for {business.name}. Score: {total_score}")
        
        return {"status": "success", "businesses_processed": len(unique_businesses)}
        
    except Exception as e:
        print(f"Error in campaign task: {e}")
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
