from datetime import datetime, timezone
from core.models import Business, BusinessSource, CRMLead, JobRun, CampaignLocation


def run_mock_campaign(db, campaign):
    """Deterministic fixtures; never instantiate a network provider or crawler."""
    if db.query(Business.id).filter(Business.campaign_id == campaign.id).first():
        return {"status": "completed", "mode": "mock"}
    location = db.query(CampaignLocation).filter(CampaignLocation.campaign_id == campaign.id).first()
    count = min(max(campaign.target_quantity or 1, 1), 20)
    for number in range(1, count + 1):
        business = Business(campaign_id=campaign.id, name=f"Staging Sample {number}",
            industry=campaign.industry.name, country=location.country if location else "USA",
            city=location.city if location else "Sample City", status="new")
        db.add(business)
        db.flush()
        db.add(BusinessSource(business_id=business.id, source="mock"))
        db.add(CRMLead(business_id=business.id, stage="new", source="campaign"))
    campaign.status = "completed"
    db.add(JobRun(campaign_id=campaign.id, stage="lead_intelligence", status="completed",
        completed_at=datetime.now(timezone.utc), metrics={"mode": "mock", "discovered": count, "paid_requests": 0}))
    db.commit()
    return {"status": "completed", "mode": "mock", "discovered": count}
