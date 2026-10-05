from __future__ import annotations

from typing import Any, Dict


# SignalOS v3 scores opportunities, not merely missing website features.
# Each component has a fixed maximum so the commercial score remains explainable.
INDUSTRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "roofing": {"motion": "quote", "min_reviews": 20},
    "hvac": {"motion": "quote", "min_reviews": 20},
    "cleaning": {"motion": "quote", "min_reviews": 20},
    "construction": {"motion": "quote", "min_reviews": 15},
    "plumbing": {"motion": "quote", "min_reviews": 20},
    "electrical": {"motion": "quote", "min_reviews": 15},
    "landscaping": {"motion": "quote", "min_reviews": 15},
    "painting": {"motion": "quote", "min_reviews": 15},
    "pest": {"motion": "quote", "min_reviews": 20},
    "solar": {"motion": "quote", "min_reviews": 15},
    "real_estate": {"motion": "lead", "min_reviews": 10},
    "restaurant": {"motion": "booking", "min_reviews": 25},
    "wedding": {"motion": "booking", "min_reviews": 15},
    "photography": {"motion": "booking", "min_reviews": 15},
    "clinic": {"motion": "booking", "min_reviews": 20},
    "dental": {"motion": "booking", "min_reviews": 20},
    "salon": {"motion": "booking", "min_reviews": 25},
    "spa": {"motion": "booking", "min_reviews": 25},
    "hotel": {"motion": "booking", "min_reviews": 30},
    "travel": {"motion": "booking", "min_reviews": 10},
    "d2c": {"motion": "ecommerce", "min_reviews": 10},
    "ecommerce": {"motion": "ecommerce", "min_reviews": 10},
    "wholesale": {"motion": "rfq", "min_reviews": 5},
    "industrial": {"motion": "rfq", "min_reviews": 5},
}


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(int(value), high))


class ScoringEngine:
    """Evidence-first commercial opportunity scoring for SignalOS v3.

    The score is deliberately deterministic. AI may explain an opportunity, but
    AI is not allowed to decide whether an unverified business becomes an A+ lead.

    Component maxima:
      business_fit   25
      digital_gap    30
      offer_fit      20
      buying_intent  15  (opportunity urgency proxy, not confirmed purchase intent)
      contactability 10
    """

    VERSION = "v3-opportunity"

    def __init__(self, industry_config: Dict[str, Any] | None = None):
        self.config = industry_config or {}

    def _profile(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        configured = self.config if isinstance(self.config, dict) else {}
        motion = configured.get("motion") or configured.get("sales_motion")
        min_reviews = configured.get("min_reviews")

        industry = str(business_data.get("industry") or "").lower().replace("-", "_")
        matched = next(
            (profile for key, profile in INDUSTRY_PROFILES.items() if key in industry),
            {},
        )
        return {
            "motion": motion or matched.get("motion") or "lead",
            "min_reviews": int(min_reviews if min_reviews is not None else matched.get("min_reviews", 10)),
        }

    @staticmethod
    def _demand_points(review_count: int, rating: float | None) -> int:
        points = 0
        if review_count >= 250:
            points += 12
        elif review_count >= 100:
            points += 10
        elif review_count >= 50:
            points += 8
        elif review_count >= 25:
            points += 6
        elif review_count >= 10:
            points += 4
        elif review_count >= 5:
            points += 2

        if rating is not None:
            if rating >= 4.6:
                points += 5
            elif rating >= 4.3:
                points += 4
            elif rating >= 4.0:
                points += 2
            elif rating < 3.5:
                points -= 2
        return _clamp(points, 0, 17)

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        return "Reject"

    def _confidence(self, business_data: Dict[str, Any], audit_data: Dict[str, Any]) -> int:
        score = 20
        if business_data.get("primary_phone"):
            score += 15
        if business_data.get("website_url"):
            score += 10
        if business_data.get("website_email"):
            score += 15
        if business_data.get("rating") is not None:
            score += 8
        if business_data.get("review_count") is not None:
            score += 7

        pages = audit_data.get("pages_checked") or []
        score += min(len(pages), 5) * 3
        evidence = audit_data.get("evidence") or []
        score += min(len(evidence), 5) * 2
        return _clamp(score)

    def calculate_score(self, business_data: Dict[str, Any], audit_data: Dict[str, Any]) -> Dict[str, Any]:
        if audit_data.get("is_live") is not True:
            return {
                "commercial_score": 0,
                "data_confidence": 0,
                "grade": "Reject",
                "business_fit": 0,
                "digital_gap": 0,
                "offer_fit": 0,
                "buying_intent": 0,
                "contactability": 0,
            }

        profile = self._profile(business_data)
        motion = profile["motion"]
        min_reviews = profile["min_reviews"]
        reviews = max(int(business_data.get("review_count") or 0), 0)
        rating_raw = business_data.get("rating")
        rating = float(rating_raw) if rating_raw not in (None, "") else None

        # 1) Business fit: proven local demand + enough identity/contact evidence.
        business_fit = 4 + self._demand_points(reviews, rating)
        if business_data.get("primary_phone"):
            business_fit += 2
        if business_data.get("website_email"):
            business_fit += 1
        if reviews >= min_reviews:
            business_fit += 1
        business_fit = _clamp(business_fit, 0, 25)

        # 2) Digital gap: only score missing capabilities relevant to the buying motion.
        digital_gap = 0
        if audit_data.get("mobile_responsive") is False:
            digital_gap += 6
        if audit_data.get("contact_form") is False:
            digital_gap += 4
        if audit_data.get("phone_cta") is False:
            digital_gap += 3

        if motion in {"quote", "rfq"}:
            if audit_data.get("quote_form") is False:
                digital_gap += 10
            if audit_data.get("booking_detected") is False:
                digital_gap += 2
        elif motion == "booking":
            if audit_data.get("booking_detected") is False:
                digital_gap += 10
            if audit_data.get("quote_form") is False:
                digital_gap += 2
        elif motion == "ecommerce":
            if audit_data.get("ecommerce_detected") is False:
                digital_gap += 12
            if audit_data.get("contact_form") is False:
                digital_gap += 2
        else:
            if audit_data.get("quote_form") is False:
                digital_gap += 5
            if audit_data.get("booking_detected") is False:
                digital_gap += 3
        digital_gap = _clamp(digital_gap, 0, 30)

        # 3) Offer fit: reward gaps Devacia can productize and businesses that can plausibly buy.
        if digital_gap >= 22:
            offer_fit = 14
        elif digital_gap >= 15:
            offer_fit = 11
        elif digital_gap >= 8:
            offer_fit = 7
        elif digital_gap >= 4:
            offer_fit = 4
        else:
            offer_fit = 0
        if reviews >= min_reviews:
            offer_fit += 3
        if reviews >= max(50, min_reviews * 2):
            offer_fit += 2
        if rating is not None and rating >= 4.2:
            offer_fit += 1
        offer_fit = _clamp(offer_fit, 0, 20)

        # 4) "Buying intent" is an urgency proxy. We do not claim real purchase intent
        # unless SignalOS later adds temporal intent signals (hiring, ads, redesign, expansion).
        buying_intent = 0
        if reviews >= min_reviews:
            buying_intent += 4
        if reviews >= max(50, min_reviews * 2):
            buying_intent += 3
        if rating is not None and rating >= 4.3:
            buying_intent += 2
        if digital_gap >= 15:
            buying_intent += 4
        if digital_gap >= 22:
            buying_intent += 2
        buying_intent = _clamp(buying_intent, 0, 15)

        # 5) Contactability: company contact data first; named decision makers can add more later.
        contactability = 0
        if business_data.get("primary_phone"):
            contactability += 4
        if business_data.get("website_email"):
            contactability += 4
        if business_data.get("has_decision_maker"):
            contactability += 2
        contactability = _clamp(contactability, 0, 10)

        commercial_score = business_fit + digital_gap + offer_fit + buying_intent + contactability

        # Guardrails against attractive-looking but commercially weak records.
        if reviews < max(3, min_reviews // 3):
            commercial_score = min(commercial_score, 69)
        if not business_data.get("primary_phone") and not business_data.get("website_email"):
            commercial_score = min(commercial_score, 69)

        commercial_score = _clamp(commercial_score)
        return {
            "commercial_score": commercial_score,
            "data_confidence": self._confidence(business_data, audit_data),
            "grade": self._grade(commercial_score),
            "business_fit": business_fit,
            "digital_gap": digital_gap,
            "offer_fit": offer_fit,
            "buying_intent": buying_intent,
            "contactability": contactability,
        }

    def calculate_no_website_score(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score no-website prospects without automatically calling every one A+.

        Missing a website is a strong digital gap only when the business itself
        shows evidence of demand and there is a usable contact path.
        """
        profile = self._profile(business_data)
        min_reviews = profile["min_reviews"]
        reviews = max(int(business_data.get("review_count") or 0), 0)
        rating_raw = business_data.get("rating")
        rating = float(rating_raw) if rating_raw not in (None, "") else None

        business_fit = _clamp(4 + self._demand_points(reviews, rating) + (2 if business_data.get("primary_phone") else 0), 0, 25)
        digital_gap = 28
        offer_fit = 12 + (4 if reviews >= min_reviews else 0) + (2 if rating is not None and rating >= 4.2 else 0)
        offer_fit = _clamp(offer_fit, 0, 20)

        buying_intent = 2
        if reviews >= min_reviews:
            buying_intent += 5
        if reviews >= max(50, min_reviews * 2):
            buying_intent += 3
        if rating is not None and rating >= 4.3:
            buying_intent += 2
        buying_intent = _clamp(buying_intent, 0, 15)

        contactability = 6 if business_data.get("primary_phone") else 0
        if business_data.get("has_decision_maker"):
            contactability += 2
        contactability = _clamp(contactability, 0, 10)

        commercial_score = business_fit + digital_gap + offer_fit + buying_intent + contactability
        if reviews < max(3, min_reviews // 3):
            commercial_score = min(commercial_score, 69)
        if not business_data.get("primary_phone"):
            commercial_score = min(commercial_score, 69)
        commercial_score = _clamp(commercial_score)

        confidence = 35
        if business_data.get("primary_phone"):
            confidence += 20
        if business_data.get("rating") is not None:
            confidence += 10
        if business_data.get("review_count") is not None:
            confidence += 10
        if business_data.get("google_place_id"):
            confidence += 15

        return {
            "commercial_score": commercial_score,
            "data_confidence": _clamp(confidence),
            "grade": self._grade(commercial_score),
            "business_fit": business_fit,
            "digital_gap": digital_gap,
            "offer_fit": offer_fit,
            "buying_intent": buying_intent,
            "contactability": contactability,
        }
