from engines.scoring import ScoringEngine


def test_no_website_prospect_is_not_automatically_a_plus():
    scorer = ScoringEngine()
    result = scorer.calculate_no_website_score({
        "industry": "roofing contractor",
        "primary_phone": "+1 214-555-0199",
        "review_count": 2,
        "rating": 4.8,
        "google_place_id": "abc123",
    })
    assert result["commercial_score"] <= 69
    assert result["grade"] != "A+"


def test_strong_local_business_with_relevant_gap_scores_above_weak_business():
    scorer = ScoringEngine()
    audit = {
        "is_live": True,
        "mobile_responsive": True,
        "contact_form": True,
        "quote_form": False,
        "phone_cta": True,
        "booking_detected": False,
        "ecommerce_detected": False,
        "pages_checked": ["https://example.com", "https://example.com/contact"],
        "evidence": [{"type": "gap_detected"}],
    }

    strong = scorer.calculate_score({
        "industry": "roofing contractor",
        "primary_phone": "+1 214-555-0199",
        "website_url": "https://example.com",
        "website_email": "hello@example.com",
        "review_count": 120,
        "rating": 4.7,
        "has_decision_maker": True,
    }, audit)

    weak = scorer.calculate_score({
        "industry": "roofing contractor",
        "primary_phone": "+1 214-555-0198",
        "website_url": "https://weak.example.com",
        "website_email": None,
        "review_count": 3,
        "rating": 4.9,
        "has_decision_maker": False,
    }, audit)

    assert strong["commercial_score"] > weak["commercial_score"]
    assert weak["commercial_score"] <= 69


def test_industry_motion_changes_gap_weighting():
    booking_audit = {
        "is_live": True,
        "mobile_responsive": True,
        "contact_form": True,
        "quote_form": True,
        "phone_cta": True,
        "booking_detected": False,
        "ecommerce_detected": False,
        "pages_checked": ["https://example.com"],
        "evidence": [],
    }

    common = {
        "primary_phone": "+1 214-555-0199",
        "website_url": "https://example.com",
        "website_email": "hello@example.com",
        "review_count": 80,
        "rating": 4.6,
    }

    restaurant = ScoringEngine().calculate_score({**common, "industry": "restaurant"}, booking_audit)
    roofing = ScoringEngine().calculate_score({**common, "industry": "roofing contractor"}, booking_audit)

    assert restaurant["digital_gap"] > roofing["digital_gap"]


def test_unreachable_site_is_rejected():
    result = ScoringEngine().calculate_score(
        {"industry": "roofing contractor", "review_count": 100, "rating": 4.9},
        {"is_live": False},
    )
    assert result["commercial_score"] == 0
    assert result["grade"] == "Reject"
