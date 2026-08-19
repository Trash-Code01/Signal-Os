import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import google.generativeai as genai


class AISDROutput(BaseModel):
    """Full structured output from the Gemini AI SDR Analyst."""
    # Lead qualification
    is_qualified: bool = Field(description="Whether this business is worth pursuing for Devacia")
    lead_summary: str = Field(description="1-2 sentence human-readable summary of the lead")
    why_this_is_a_good_lead: str = Field(description="Specific reasons this is a good lead, citing observed evidence")

    # Scoring components (0-20 each)
    business_fit_score: int = Field(description="Score 0-20: Is this the type of business Devacia serves?")
    website_gap_score: int = Field(description="Score 0-20: How significant are their website problems?")
    ux_ui_gap_score: int = Field(description="Score 0-15: How poor is the UX/UI?")
    conversion_gap_score: int = Field(description="Score 0-20: How weak is their conversion setup?")
    offer_fit_score: int = Field(description="Score 0-15: How well does a Devacia offer match their needs?")
    contactability_score: int = Field(description="Score 0-10: How likely can we reach them?")

    # Problems
    detected_problems: List[str] = Field(description="List of specific digital/UX/conversion problems detected, each grounded in evidence")
    primary_problem: str = Field(description="The single most impactful problem Devacia can solve")

    # Opportunity
    recommended_offer: str = Field(description="The exact Devacia service to pitch, e.g. 'Clinic Booking System', 'Restaurant Reservation System'")
    estimated_offer_range: str = Field(description="Estimated project value, e.g. '$3,500 - $5,000'")

    # Outreach
    outreach_angle: str = Field(description="A specific, personalized outreach sentence referencing the actual observed problem")
    personalization_points: List[str] = Field(description="2-4 specific facts about this business to use in outreach (from evidence only)")

    # Confidence
    confidence: str = Field(description="high / medium / low — how confident is the analysis given the evidence")
    reasoning: str = Field(description="Detailed reasoning chain citing specific pieces of evidence")


SYSTEM_PROMPT = """You are an elite AI Sales Development Representative (SDR) Analyst working for Devacia, a web development agency that builds booking systems, lead capture funnels, restaurant platforms, clinic management systems, and conversion-focused websites.

Your job is to analyze collected intelligence about a business and produce a structured SDR dossier.

CRITICAL RULES:
1. NEVER invent information. Every claim must be grounded in the provided evidence.
2. If evidence is thin, acknowledge it. Confidence should be "low" if little was collected.
3. Problems must be SPECIFIC: NOT "poor CTA" but "Contact Us button is positioned below the fold on mobile with no sticky CTA visible"
4. Recommended offer must map to what Devacia ACTUALLY builds — booking systems, lead capture, restaurant sites, clinic systems, ecommerce, redesigns.
5. Outreach angle must be something the prospect would think: "How did they know that?" — not generic.
6. Focus on the GAP: what the business is MISSING that costs them customers/revenue.
"""


class GeminiProvider:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3.6-flash')

    async def analyze(self, evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> Dict[str, Any]:
        """Full AI SDR analysis using Gemini with structured JSON output."""

        evidence_text = "\n".join([
            f"- [{e.get('source_type', 'unknown')}] {e.get('evidence_text', '')}"
            for e in evidence
        ])

        prompt = f"""{SYSTEM_PROMPT}

Industry Configuration:
{json.dumps(industry_config, indent=2)}

Collected Evidence:
{evidence_text}

Analyze this business and return a complete AI SDR dossier in JSON format.
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=AISDROutput,
                )
            )
            result_json = json.loads(response.text)
            return result_json

        except Exception as e:
            print(f"Gemini API error: {e}")
            return {
                "is_qualified": False,
                "lead_summary": "Analysis failed",
                "why_this_is_a_good_lead": "N/A",
                "business_fit_score": 0,
                "website_gap_score": 0,
                "ux_ui_gap_score": 0,
                "conversion_gap_score": 0,
                "offer_fit_score": 0,
                "contactability_score": 0,
                "detected_problems": ["Failed to analyze — Gemini API error"],
                "primary_problem": f"Error: {str(e)}",
                "recommended_offer": "None",
                "estimated_offer_range": "N/A",
                "outreach_angle": "N/A",
                "personalization_points": [],
                "confidence": "low",
                "reasoning": f"Gemini error: {e}"
            }
