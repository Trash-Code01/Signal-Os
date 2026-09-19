import os
os.environ['ENVIRONMENT'] = 'staging'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from core.database import Base, SessionLocal
from core.models import User, Business, Campaign, IndustryConfig, CRMLead, Score, DecisionMaker, CampaignLocation
from core.deduplication import find_existing_business, DeduplicationEngine
from core.staging_jobs import run_mock_campaign


@pytest.fixture
def db_session():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = SessionLocal(bind=engine)
    session.info["system_access"] = True
    # Create test user
    user = User(id=1, email='admin@devacia.com', hashed_password='hashed', role='admin')
    session.add(user)
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_find_existing_business_by_domain(db_session):
    b = Business(
        name="Acme Roofing LLC",
        normalized_name="acme roofing llc",
        website_url="https://acme-roofing.com/",
        website_domain="acme-roofing.com",
        city="Dallas",
        owner_id=1,
    )
    db_session.add(b)
    db_session.commit()

    # Exact domain
    match1 = find_existing_business(db_session, {"website_url": "https://www.acme-roofing.com"})
    assert match1 is not None
    assert match1.id == b.id

    # HTTP variant with trailing slash
    match2 = find_existing_business(db_session, {"website_url": "http://acme-roofing.com/"})
    assert match2 is not None
    assert match2.id == b.id

    # Non-existent domain
    match3 = find_existing_business(db_session, {"website_url": "https://other-domain.com"})
    assert match3 is None


def test_find_existing_business_by_phone(db_session):
    b = Business(
        name="Premier Plumbing",
        normalized_name="premier plumbing",
        primary_phone="+1 214-555-4321",
        city="Dallas",
        owner_id=1,
    )
    db_session.add(b)
    db_session.commit()

    # Formatted differently: (214) 555-4321
    match1 = find_existing_business(db_session, {"primary_phone": "(214) 555-4321"})
    assert match1 is not None
    assert match1.id == b.id

    # Raw digits: 2145554321
    match2 = find_existing_business(db_session, {"primary_phone": "2145554321"})
    assert match2 is not None
    assert match2.id == b.id

    # Different number
    match3 = find_existing_business(db_session, {"primary_phone": "2145559999"})
    assert match3 is None


def test_find_existing_business_by_name_and_city(db_session):
    b = Business(
        name="Lone Star Electric",
        normalized_name="lone star electric",
        city="Austin",
        owner_id=1,
    )
    db_session.add(b)
    db_session.commit()

    # Case-insensitive match in same city
    match1 = find_existing_business(db_session, {"name": "LONE STAR ELECTRIC", "city": "austin"})
    assert match1 is not None
    assert match1.id == b.id

    # Same name but different city should NOT match
    match2 = find_existing_business(db_session, {"name": "Lone Star Electric", "city": "Houston"})
    assert match2 is None


def test_consecutive_campaigns_never_repeat_leads(db_session):
    industry = IndustryConfig(id=1, name="Roofing", owner_id=1)
    db_session.add(industry)
    db_session.commit()

    # Create Campaign 1
    c1 = Campaign(id=1, name="Roofing Campaign 1", industry_id=1, target_quantity=5, owner_id=1)
    db_session.add(c1)
    db_session.add(CampaignLocation(campaign_id=1, city="Dallas", region_state="Texas", country="USA", owner_id=1))
    db_session.commit()

    result1 = run_mock_campaign(db_session, c1)
    assert result1["status"] == "completed"

    leads_c1 = db_session.query(Business).filter(Business.campaign_id == 1).all()
    assert len(leads_c1) == 5
    domains_c1 = {b.website_domain for b in leads_c1}
    phones_c1 = {b.primary_phone for b in leads_c1}
    names_c1 = {b.name for b in leads_c1}

    # Create Campaign 2 with the EXACT SAME industry and city
    c2 = Campaign(id=2, name="Roofing Campaign 2", industry_id=1, target_quantity=5, owner_id=1)
    db_session.add(c2)
    db_session.add(CampaignLocation(campaign_id=2, city="Dallas", region_state="Texas", country="USA", owner_id=1))
    db_session.commit()

    result2 = run_mock_campaign(db_session, c2)
    assert result2["status"] == "completed"

    leads_c2 = db_session.query(Business).filter(Business.campaign_id == 2).all()
    assert len(leads_c2) == 5
    domains_c2 = {b.website_domain for b in leads_c2}
    phones_c2 = {b.primary_phone for b in leads_c2}
    names_c2 = {b.name for b in leads_c2}

    # Verify ZERO overlap between Campaign 1 and Campaign 2
    assert domains_c1.isdisjoint(domains_c2), f"Overlapping domains found: {domains_c1 & domains_c2}"
    assert phones_c1.isdisjoint(phones_c2), f"Overlapping phones found: {phones_c1 & phones_c2}"
    assert names_c1.isdisjoint(names_c2), f"Overlapping company names found: {names_c1 & names_c2}"
