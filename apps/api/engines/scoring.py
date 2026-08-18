from typing import Dict, Any, List

class ScoringEngine:
    def __init__(self, industry_config: Dict[str, Any]):
        self.config = industry_config
        # Example weight distribution from PDF
        self.weights = {
            "business_fit": 0.20,
            "digital_gap": 0.25,
            "offer_fit": 0.20,
            "buying_intent": 0.20,
            "contactability": 0.15
        }

    def calculate_score(self, ai_reasoning_output: Dict[str, Any]) -> int:
        """
        Calculate total score based on AI reasoning output and configuration weights.
        The AI reasoning output should already contain raw 0-100 scores for each factor.
        """
        if not ai_reasoning_output.get("is_qualified", False):
            return 0
            
        business_fit = ai_reasoning_output.get("business_fit_score", 0) * self.weights["business_fit"]
        digital_gap = ai_reasoning_output.get("digital_gap_score", 0) * self.weights["digital_gap"]
        offer_fit = ai_reasoning_output.get("offer_fit_score", 0) * self.weights["offer_fit"]
        buying_intent = ai_reasoning_output.get("buying_intent_score", 0) * self.weights["buying_intent"]
        contactability = ai_reasoning_output.get("contactability_score", 0) * self.weights["contactability"]
        
        total_score = sum([business_fit, digital_gap, offer_fit, buying_intent, contactability])
        
        return int(total_score)
        
    def get_grade(self, score: int) -> str:
        """Thresholds: 90–100 = A+, 80–89 = A, 70–79 = B, 60–69 = C, below 60 = Reject."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "Reject"
