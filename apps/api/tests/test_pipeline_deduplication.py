import os
os.environ['ENVIRONMENT'] = 'staging'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from core.database import Base, SessionLocal
from core.models import User, Business, BusinessSource, Campaign, IndustryConfig, CRMLead, Score, DecisionMaker, CampaignLocation
from core.deduplication import find_existing_business, DeduplicationEngine
from core.staging_jobs import run_mock_campaign, sanitize_legacy_mock_data


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


def test_legacy_mock_contacts_are_sanitized(db_session):
    campaign = Campaign(id=90, name="Legacy mock", target_quantity=1, owner_id=1, settings={})
    db_session.add(campaign)
    db_session.add(CampaignLocation(campaign_id=90, city="Delhi", region_state=None, country="India", owner_id=1))
    db_session.flush()
    business = Business(
        campaign_id=90,
        name="Fake Delhi lead",
        website_url="https://fakedehli.com",
        website_domain="fakedehli.com",
        primary_phone="+1 214-555-0199",
        city="Delhi",
        state_province="Texas",
        country="India",
        owner_id=1,
    )
    db_session.add(business); db_session.flush()
    db_session.add(BusinessSource(business_id=business.id, source="mock", owner_id=1))
    db_session.add(DecisionMaker(business_id=business.id, email="contact@fakedehli.com", source="website_crawl", owner_id=1))
    db_session.commit()

    assert sanitize_legacy_mock_data(db_session.get_bind()) == 1
    db_session.expire_all()
    cleaned = db_session.get(Business, business.id)
    assert cleaned.website_domain.endswith('.test.invalid')
    assert cleaned.primary_phone is None
    assert cleaned.state_province is None
    assert db_session.query(DecisionMaker).filter(DecisionMaker.business_id == business.id).count() == 0
    assert db_session.get(Campaign, 90).settings['data_mode'] == 'synthetic'


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
    phones_c1 = {b.primary_phone for b in leads_c1 if b.primary_phone}
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
    phones_c2 = {b.primary_phone for b in leads_c2 if b.primary_phone}
    names_c2 = {b.name for b in leads_c2}

    # Verify ZERO overlap between Campaign 1 and Campaign 2
    assert domains_c1.isdisjoint(domains_c2), f"Overlapping domains found: {domains_c1 & domains_c2}"
    assert phones_c1.isdisjoint(phones_c2), f"Overlapping phones found: {phones_c1 & phones_c2}"
    assert names_c1.isdisjoint(names_c2), f"Overlapping company names found: {names_c1 & names_c2}"


@pytest.mark.parametrize("requested_quantity", [1, 37, 100, 300, 500])
def test_campaign_delivers_exact_requested_quantity(db_session, requested_quantity):
    industry = IndustryConfig(id=3, name="HVAC", owner_id=1)
    db_session.add(industry)
    db_session.commit()

    c3 = Campaign(
        id=3,
        name=f"HVAC {requested_quantity} Target",
        industry_id=3,
        target_quantity=requested_quantity,
        owner_id=1,
    )
    db_session.add(c3)
    db_session.add(CampaignLocation(campaign_id=3, city="Austin", region_state="Texas", country="USA", owner_id=1))
    db_session.commit()

    result = run_mock_campaign(db_session, c3)
    assert result["status"] == "completed"
    assert result["discovered"] == requested_quantity
    assert result["qualified"] == requested_quantity

    leads = db_session.query(Business).filter(Business.campaign_id == 3).all()
    assert len(leads) == requested_quantity
    assert len({lead.name for lead in leads}) == requested_quantity
    assert len({lead.website_domain for lead in leads}) == requested_quantity
    assert all(lead.website_domain.endswith('.test.invalid') for lead in leads)
    assert all(lead.primary_phone is None for lead in leads)
    assert db_session.query(DecisionMaker).filter(DecisionMaker.business_id.in_([b.id for b in leads])).count() == 0
    # Verify every delivered business has its CRM lead and score.
    crm_leads = db_session.query(CRMLead).filter(CRMLead.business_id.in_([b.id for b in leads])).all()
    assert len(crm_leads) == requested_quantity
    scores = db_session.query(Score).filter(Score.business_id.in_([b.id for b in leads])).all()
    assert len(scores) == requested_quantity


def test_mock_campaign_resume_tops_up_existing_leads(db_session):
    industry = IndustryConfig(id=4, name="Plumbing", owner_id=1)
    db_session.add(industry)
    campaign = Campaign(id=4, name="Resume to target", industry_id=4, target_quantity=20, owner_id=1)
    db_session.add(campaign)
    db_session.add(CampaignLocation(campaign_id=4, city="Austin", region_state="Texas", country="USA", owner_id=1))
    db_session.commit()

    first_result = run_mock_campaign(db_session, campaign)
    assert first_result["qualified"] == 20

    campaign.target_quantity = 100
    campaign.status = "processing"
    db_session.commit()
    resumed_result = run_mock_campaign(db_session, campaign)

    leads = db_session.query(Business).filter(Business.campaign_id == campaign.id).all()
    assert resumed_result["status"] == "completed"
    assert resumed_result["qualified"] == 100
    assert len(leads) == 100
    assert len({lead.website_domain for lead in leads}) == 100


def test_two_300_lead_campaigns_do_not_repeat_businesses(db_session):
    industry = IndustryConfig(id=5, name="Solar", owner_id=1)
    db_session.add(industry)
    db_session.commit()

    campaign_lead_sets = []
    for campaign_id in (5, 6):
        campaign = Campaign(
            id=campaign_id,
            name=f"Solar 300 Run {campaign_id}",
            industry_id=industry.id,
            target_quantity=300,
            owner_id=1,
        )
        db_session.add(campaign)
        db_session.add(CampaignLocation(
            campaign_id=campaign_id,
            city="Phoenix",
            region_state="Arizona",
            country="USA",
            owner_id=1,
        ))
        db_session.commit()

        result = run_mock_campaign(db_session, campaign)
        assert result["qualified"] == 300
        leads = db_session.query(Business).filter(Business.campaign_id == campaign_id).all()
        assert len(leads) == 300
        campaign_lead_sets.append({(lead.website_domain, lead.primary_phone) for lead in leads})

    assert campaign_lead_sets[0].isdisjoint(campaign_lead_sets[1])
