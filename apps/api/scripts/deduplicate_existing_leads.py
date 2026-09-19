"""Clean up redundant duplicate businesses and leads in the database."""
import os
import sys
from pathlib import Path
from collections import defaultdict

# Ensure API root is in path
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

import core.runtime
from core.database import SessionLocal
from core.models import (
    Business,
    BusinessSource,
    CRMLead,
    CRMActivity,
    Opportunity,
    Score,
    DecisionMaker,
    Website,
    WebsiteAudit,
    AIAnalysis,
    SocialProfile,
)


def deduplicate_existing_leads():
    db = SessionLocal()
    db.info["system_access"] = True
    try:
        active_businesses = (
            db.query(Business)
            .filter(Business.deleted_at.is_(None))
            .order_by(Business.id.asc())
            .all()
        )

        grouped = defaultdict(list)
        for b in active_businesses:
            # Group by account and domain (if present), or normalized name + city
            domain = (b.website_domain or "").strip().lower()
            if domain:
                key = (b.owner_id, "domain", domain)
            else:
                key = (b.owner_id, "name_city", (b.normalized_name or b.name or "").strip().lower(), (b.city or "").strip().lower())
            grouped[key].append(b)

        removed_count = 0
        merged_groups = 0

        for key, records in grouped.items():
            if len(records) <= 1:
                continue

            merged_groups += 1
            authoritative = records[0]
            duplicates = records[1:]

            for dup in duplicates:
                dup_id = dup.id
                # Delete child records for the redundant duplicate
                db.query(CRMActivity).filter(CRMActivity.business_id == dup_id).delete()
                db.query(CRMLead).filter(CRMLead.business_id == dup_id).delete()
                db.query(DecisionMaker).filter(DecisionMaker.business_id == dup_id).delete()
                db.query(Opportunity).filter(Opportunity.business_id == dup_id).delete()
                db.query(Score).filter(Score.business_id == dup_id).delete()
                db.query(AIAnalysis).filter(AIAnalysis.business_id == dup_id).delete()
                db.query(SocialProfile).filter(SocialProfile.business_id == dup_id).delete()
                db.query(BusinessSource).filter(BusinessSource.business_id == dup_id).delete()

                websites = db.query(Website).filter(Website.business_id == dup_id).all()
                for w in websites:
                    db.query(WebsiteAudit).filter(WebsiteAudit.website_id == w.id).delete()
                    db.delete(w)

                db.delete(dup)
                removed_count += 1

        db.commit()
        print(f"Successfully deduplicated database: merged {merged_groups} groups, removed {removed_count} redundant duplicate leads.")
        return removed_count
    finally:
        db.close()


if __name__ == "__main__":
    deduplicate_existing_leads()
