import os
import json
from datetime import datetime
from core.database import Base, SessionLocal, engine
from core.models import IndustryConfig, DevaciaOffer, User, Campaign, Business, Score, Opportunity, CRMLead
from core.auth import get_password_hash


def seed_db():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ── 1. Admin user ──────────────────────────────────────────────────────
        admin_exists = db.query(User).filter(User.email == "admin@devacia.com").first()
        if not admin_exists:
            print("Seeding default Admin User...")
            db.add(User(
                email="admin@devacia.com",
                hashed_password=get_password_hash("admin123")
            ))
            db.commit()
            print("Admin user created.")

        # ── 2. Migrate local data if dump exists ───────────────────────────────
        dump_file = "data_dump.json"
        if os.path.exists(dump_file) and db.query(Campaign).count() == 0:
            print("Found data_dump.json and DB is empty – importing local data...")
            with open(dump_file, "r") as f:
                data = json.load(f)

            def parse_dates(row):
                out = {}
                for k, v in row.items():
                    if isinstance(v, str) and (k.endswith("_at") or k in ("created_at", "updated_at", "deleted_at")):
                        try:
                            out[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
                        except Exception:
                            out[k] = v
                    else:
                        out[k] = v
                return out

            print(f"  Inserting {len(data.get('campaigns', []))} campaigns...")
            for row in data.get("campaigns", []):
                db.merge(Campaign(**parse_dates(row)))
            db.commit()

            print(f"  Inserting {len(data.get('businesses', []))} businesses...")
            for row in data.get("businesses", []):
                db.merge(Business(**parse_dates(row)))
            db.commit()

            print(f"  Inserting {len(data.get('scores', []))} scores...")
            for row in data.get("scores", []):
                db.merge(Score(**parse_dates(row)))
            db.commit()

            print(f"  Inserting {len(data.get('opportunities', []))} opportunities...")
            for row in data.get("opportunities", []):
                db.merge(Opportunity(**parse_dates(row)))
            db.commit()

            print(f"  Inserting {len(data.get('crm_leads', []))} CRM leads...")
            for row in data.get("crm_leads", []):
                db.merge(CRMLead(**parse_dates(row)))
            db.commit()

            print("Data migration complete!")
        elif db.query(Campaign).count() > 0:
            print(f"DB already has {db.query(Campaign).count()} campaigns – skipping data import.")

        # ── 3. Industry configs ────────────────────────────────────────────────
        if db.query(IndustryConfig).count() == 0:
            print("Seeding Roofing Industry Config...")
            roofing = IndustryConfig(
                name="Roofing",
                signals={"strong_reviews": True, "service_area_business": True, "no_online_estimate": True},
            )
            db.add(roofing)
            db.commit()
            db.refresh(roofing)

            for name, desc in [
                ("Lead Capture", "Optimize homepage with high-converting capture forms."),
                ("Inspection Booking", "Automated calendar booking for roof inspections."),
                ("Quote Funnel", "Multi-step form to qualify leads and provide instant rough quotes."),
                ("Missed-Call Recovery", "Automated SMS follow-up for missed calls."),
            ]:
                db.add(DevaciaOffer(industry_id=roofing.id, name=name, description=desc))
            db.commit()

        print("Database seeding complete!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
