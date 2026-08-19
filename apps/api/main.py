from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from worker import process_campaign_task
from core.database import get_db, engine
from core.database import Base
from core.models import *
import os
import httpx

app = FastAPI(title="Devacia Lead Intelligence OS", version="1.0.0")

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        country=req.country,
        cities=req.cities,
        industry_id=industry.id,
        target_quantity=req.target_quantity,
        min_quality_score=req.min_quality_score,
        status="processing"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Trigger worker
    task = process_campaign_task.delay(campaign.id)
    return {"status": "accepted", "campaign_id": campaign.id, "task_id": task.id}

@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    """Fetch opportunities (leads) for the UI."""
    opportunities = db.query(Opportunity).all()
    results = []
    
    for opp in opportunities:
        business = opp.business
        score = db.query(Score).filter(Score.business_id == business.id).first()
        contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == business.id).all()
        campaign = db.query(Campaign).filter(Campaign.id == business.campaign_id).first()
        industry_name = campaign.industry.name if campaign and campaign.industry else "Detected"
        
        formatted_contacts = []
        for c in contacts:
            name = f"{c.first_name or ''} {c.last_name or ''}".strip()
            if not name or name == "None None":
                name = c.email or 'Unknown'
            formatted_contacts.append({"name": name, "email": c.email, "title": c.title})
            
        results.append({
            "id": business.id,
            "name": business.name,
            "domain": business.domain,
            "city": business.city,
            "state": business.state,
            "industry": industry_name,
            "total_score": score.total_score if score else 0,
            "primary_problem": opp.primary_problem,
            "outreach_angle": opp.outreach_angle,
            "recommended_offer": opp.recommended_offer if hasattr(opp, "recommended_offer") else "Devacia Service",
            "contacts": formatted_contacts,
        })
        
    return {"leads": results}

@app.get("/api/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch aggregated stats for the dashboard."""
    total_campaigns = db.query(Campaign).count()
    total_businesses = db.query(Business).count()
    total_opportunities = db.query(Opportunity).count()
    
    # Calculate average score (approximate)
    scores = db.query(Score.total_score).all()
    avg_score = sum([s[0] for s in scores]) / len(scores) if scores else 0
    
    a_plus = len([s for s in scores if s[0] >= 90])
    
    recent_campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).limit(5).all()
    
    return {
        "stats": {
            "campaigns": total_campaigns,
            "raw_leads": total_businesses,
            "qualified_opportunities": total_opportunities,
            "average_score": int(avg_score),
            "a_plus_leads": a_plus
        },
        "recent_campaigns": [
            {"id": c.id, "name": c.name, "status": c.status, "target": c.target_quantity, "progress": min(c.target_quantity, total_opportunities), "country": c.country, "city": c.cities[0] if c.cities else "", "industry": c.industry.name if c.industry else ""} 
            for c in recent_campaigns
        ]
    }

@app.get("/api/leads/{lead_id}")
def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    """Fetch full dossier for a specific lead."""
    business = db.query(Business).filter(Business.id == lead_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    opp = db.query(Opportunity).filter(Opportunity.business_id == lead_id).first()
    score = db.query(Score).filter(Score.business_id == lead_id).first()
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == lead_id).all()
    evidence = db.query(Evidence).filter(Evidence.business_id == lead_id).all()
    
    return {
        "id": business.id,
        "name": business.name,
        "domain": business.domain,
        "phone": business.phone,
        "location": f"{business.city}, {business.state}" if business.city else None,
        "score": score.total_score if score else 0,
        "primary_problem": opp.primary_problem if opp else "No specific problem detected.",
        "outreach_angle": opp.outreach_angle if opp else "No outreach angle generated.",
        "contacts": [{"name": f"{c.first_name} {c.last_name}", "title": c.title, "email": c.email} for c in contacts],
        "evidence": [{"source": e.source_type, "text": e.evidence_text} for e in evidence]
    }

@app.post("/api/leads/{lead_id}/export")
async def export_lead(lead_id: int, db: Session = Depends(get_db)):
    """Export a lead to n8n webhook / CRM."""
    opp = db.query(Opportunity).filter(Opportunity.business_id == lead_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    business = opp.business
    contacts = db.query(DecisionMaker).filter(DecisionMaker.business_id == business.id).all()
    score = db.query(Score).filter(Score.business_id == business.id).first()
    
    payload = {
        "company_name": business.name,
        "domain": business.domain,
        "score": score.total_score if score else 0,
        "primary_problem": opp.primary_problem,
        "outreach_angle": opp.outreach_angle,
        "contacts": [{"name": f"{c.first_name} {c.last_name}", "email": c.email} for c in contacts]
    }
    
    # Fire and forget webhook to n8n
    webhook_url = os.environ.get("N8N_WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(webhook_url, json=payload)
            except Exception as e:
                print(f"Failed to trigger n8n webhook: {e}")
                
    return {"status": "exported", "payload": payload}
