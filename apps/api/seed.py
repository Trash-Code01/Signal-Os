import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base, SessionLocal, engine
from core.models import IndustryConfig, DevaciaOffer

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Seed Admin User if not exists
        from core.models import User
        from core.auth import get_password_hash
        admin_exists = db.query(User).filter(User.email == "admin@devacia.com").first()
        if not admin_exists:
            print("Seeding default Admin User...")
            admin_user = User(
                email="admin@devacia.com",
                hashed_password=get_password_hash("admin123")
            )
            db.add(admin_user)
            db.commit()

        # Check if already seeded configs
        if db.query(IndustryConfig).count() > 0:
            print("Database already seeded with configs.")
            return

        print("Seeding Roofing Industry Config...")
        roofing_config = IndustryConfig(
            name="Roofing",
            signals={
                "strong_reviews": True,
                "service_area_business": True,
                "no_online_estimate": True
            }
        )
        db.add(roofing_config)
        db.commit()
        db.refresh(roofing_config)

        print("Seeding Devacia Offers for Roofing...")
        offers = [
            DevaciaOffer(
                industry_id=roofing_config.id,
                name="Lead Capture",
                description="Optimize homepage with high-converting capture forms."
            ),
            DevaciaOffer(
                industry_id=roofing_config.id,
                name="Inspection Booking",
                description="Automated calendar booking for roof inspections."
            ),
            DevaciaOffer(
                industry_id=roofing_config.id,
                name="Quote Funnel",
                description="Multi-step form to qualify leads and provide instant rough quotes."
            ),
            DevaciaOffer(
                industry_id=roofing_config.id,
                name="Missed-Call Recovery",
                description="Automated SMS follow-up for missed calls."
            )
        ]
        
        for offer in offers:
            db.add(offer)
            
        db.commit()
                                import json
        import os
        from dateutil.parser import parse as parse_date
        
        dump_file = 'data_dump.json'
        if os.path.exists(dump_file):
            print("Found data_dump.json, force-syncing local data by dropping and recreating tables...")
            with open(dump_file, 'r') as f:
                data = json.load(f)
            
            from core.models import Campaign, Business, Score, Opportunity, CRMLead, Base
            from core.database import engine
            
            print("Dropping and recreating all tables to avoid foreign key violations...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            
            # Helper to parse dates
            def parse_dates(row):
                for k, v in row.items():
                    if isinstance(v, str) and (k.endswith('_at') or k == 'created_at' or k == 'updated_at'):
                        try:
                            row[k] = parse_date(v)
                        except:
                            pass
                return row
            
            print("Inserting campaigns...")
            for row in data.get('campaigns', []):
                db.add(Campaign(**parse_dates(row)))
            db.commit()
            
            print("Inserting businesses...")
            for row in data.get('businesses', []):
                db.add(Business(**parse_dates(row)))
            db.commit()
            
            print("Inserting scores...")
            for row in data.get('scores', []):
                db.add(Score(**parse_dates(row)))
            db.commit()
            
            print("Inserting opportunities...")
            for row in data.get('opportunities', []):
                db.add(Opportunity(**parse_dates(row)))
            db.commit()
            
            print("Inserting crm_leads...")
            for row in data.get('crm_leads', []):
                db.add(CRMLead(**parse_dates(row)))
            db.commit()
            
            print("Data migration complete! All local data is now securely in production.")
        print("Database seeding complete!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # If docker is not running, we might want to fallback to sqlite for local dev test without docker
    if not os.environ.get("DATABASE_URL") and not engine.dialect.name == 'sqlite':
        print("Warning: Running against default Postgres, ensure it is up!")
    seed_db()



