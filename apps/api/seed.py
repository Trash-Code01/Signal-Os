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
        # Check if already seeded
        if db.query(IndustryConfig).count() > 0:
            print("Database already seeded.")
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
