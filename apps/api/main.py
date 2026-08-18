from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from worker import process_campaign_task
from core.database import get_db, engine
from core.database import Base
from core.models import Campaign, Business, Opportunity, Score, Contact, Evidence
import os

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

class CampaignCreateRequest(BaseModel):
    industry: str
    country: str
    target_quantity: int
    min_quality_score: int

@app.post("/api/campaigns")
def create_and_start_campaign(req: CampaignCreateRequest, db: Session = Depends(get_db)):
    # Create industry config if it doesn't exist
    from core.models import IndustryConfig
    industry = db.query(IndustryConfig).filter(IndustryConfig.name == req.industry).first()
    if not industry:
        industry = IndustryConfig(name=req.industry)
        db.add(industry)
        db.commit()
        db.refresh(industry)

    # Create campaign
    campaign = Campaign(
        name=f"{req.industry} in {req.country}",
        country=req.country,
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
        contacts = db.query(Contact).filter(Contact.business_id == business.id).all()
        evidence = db.query(Evidence).filter(Evidence.business_id == business.id).all()
        
        results.append({
            "id": business.id,
            "name": business.name,
            "domain": business.domain,
            "city": business.city,
            "state": business.state,
            "total_score": score.total_score if score else 0,
            "primary_problem": opp.primary_problem,
            "outreach_angle": opp.outreach_angle,
            "contacts": [{"name": f"{c.first_name} {c.last_name}", "email": c.email, "title": c.title} for c in contacts],
            "evidence": [{"text": e.evidence_text, "source": e.source_type} for e in evidence]
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
    
    recent_campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).limit(5).all()
    
    return {
        "stats": {
            "campaigns": total_campaigns,
            "raw_leads": total_businesses,
            "qualified_opportunities": total_opportunities,
            "average_score": int(avg_score)
        },
        "recent_campaigns": [
            {"id": c.id, "name": c.name, "status": c.status, "target": c.target_quantity} 
            for c in recent_campaigns
        ]
    }

import httpx

@app.get("/api/leads/{lead_id}")
def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    """Fetch full dossier for a specific lead."""
    business = db.query(Business).filter(Business.id == lead_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    opp = db.query(Opportunity).filter(Opportunity.business_id == lead_id).first()
    score = db.query(Score).filter(Score.business_id == lead_id).first()
    contacts = db.query(Contact).filter(Contact.business_id == lead_id).all()
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
    contacts = db.query(Contact).filter(Contact.business_id == business.id).all()
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
