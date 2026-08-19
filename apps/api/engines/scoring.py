from typing import Dict, Any

class ScoringEngine:
    """
    Deterministically scores leads based on digital presence and CRM fit.
    """
    def __init__(self, industry_config: Dict[str, Any] = None):
        self.config = industry_config or {}

    def calculate_score(self, business_data: Dict[str, Any], audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates business_fit, digital_gap, offer_fit, buying_intent, contactability,
        and aggregates into commercial_score and data_confidence.
        """
        # A dead or unreachable website is not a qualified website opportunity.
        # Never give it a score high enough to enter the sales CRM.
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

        # 1. Data confidence: score only information that was actually found.
        data_confidence = 35
        if business_data.get("primary_phone"):
            data_confidence += 20
        if business_data.get("website_url"):
            data_confidence += 15
        if business_data.get("website_email"):
            data_confidence += 20
        if audit_data.get("pages_checked"):
            data_confidence += 10

        # 2. Business fit: a real business with a reachable website and local signals.
        business_fit = 35
        if business_data.get("primary_phone"):
            business_fit += 10
        if business_data.get("website_url"):
            business_fit += 5
        reviews = business_data.get("review_count") or 0
        if reviews > 5:
            business_fit += 5
        if reviews > 50:
            business_fit += 5
        
        # 3. Digital Gap (Where do they lack?)
        digital_gap = 0
        if audit_data.get("mobile_responsive") is False:
            digital_gap += 10
        if audit_data.get("booking_detected") is False:
            digital_gap += 10
        if audit_data.get("quote_form") is False:
            digital_gap += 10
        if audit_data.get("phone_cta") is False:
            digital_gap += 5
        if audit_data.get("contact_form") is False:
            digital_gap += 5

        # 4. Contactability is a quality signal, not an invented conclusion.
        contactability = 0
        if business_data.get("primary_phone"):
            contactability += 8
        if business_data.get("website_email"):
            contactability += 12

        # Calculate totals
        commercial_score = min(100, business_fit + digital_gap + contactability)
        grade = "C"
        if commercial_score >= 90: grade = "A+"
        elif commercial_score >= 80: grade = "A"
        elif commercial_score >= 70: grade = "B"
        elif commercial_score < 50: grade = "Reject"
        
        return {
            "commercial_score": commercial_score,
            "data_confidence": min(100, data_confidence),
            "grade": grade,
            "business_fit": business_fit,
            "digital_gap": digital_gap,
            "offer_fit": 0,
            "buying_intent": 0,
            "contactability": contactability
        }
