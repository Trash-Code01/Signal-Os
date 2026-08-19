import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import google.generativeai as genai


class AISDROutput(BaseModel):
    """Full structured output from the Gemini AI SDR Analyst mapping to the Opportunity Table."""
    primary_problem: str = Field(description="The single most impactful problem Devacia can solve")
    problems: List[str] = Field(description="List of specific digital/UX/conversion problems detected, each grounded in evidence")
    recommended_offer: str = Field(description="The exact Devacia service to pitch, e.g. 'Clinic Booking System', 'Restaurant Reservation System'")
    ticket_low: int = Field(description="Lowest estimated project value in USD based on industry config")
    ticket_high: int = Field(description="Highest estimated project value in USD based on industry config")
    outreach_angle: str = Field(description="A specific, personalized outreach sentence referencing the actual observed problem")
    ai_reasoning: str = Field(description="Detailed reasoning chain citing specific pieces of evidence")
    confidence: str = Field(description="high / medium / low - how confident is the analysis given the evidence")
    evidence_types_used: List[str] = Field(description="The specific types of evidence relied upon for this analysis")


SYSTEM_PROMPT = """You are an elite AI Sales Development Representative (SDR) Analyst working for Devacia.
Devacia is a web development agency that builds booking systems, lead capture funnels, restaurant platforms, clinic management systems, and conversion-focused websites.

Your job is to analyze collected intelligence (in structured JSON arrays) about a business and produce a structured Opportunity dossier.

CRITICAL RULES:
1. NEVER invent information. Every claim MUST be grounded in the provided evidence JSON array.
2. If evidence is thin, acknowledge it. Confidence should be "low" if little was collected.
3. Problems must be SPECIFIC: NOT "poor CTA" but "Contact Us button is positioned below the fold on mobile with no sticky CTA visible"
4. Recommended offer MUST map to what Devacia ACTUALLY builds (booking systems, lead capture, restaurant sites, clinic systems, ecommerce, redesigns) and align with the provided Industry Config.
5. The outreach angle must be something the prospect would think: "How did they know that?" - not generic.
6. The ticket_low and ticket_high should be reasonable estimates in USD based on the Offer and Industry context.
"""


class GeminiProvider:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        # Gemini 1.5 was retired for this account. Keep the model configurable
        # so a provider retirement cannot silently create fake opportunity data.
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self.model = genai.GenerativeModel(self.model_name)

    async def analyze(self, evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> Dict[str, Any] | None:
        """Full AI SDR analysis using Gemini with structured JSON output."""

        if not evidence:
            return None

        prompt = f"""{SYSTEM_PROMPT}

Industry Configuration:
{json.dumps(industry_config, indent=2)}

Collected Evidence:
{json.dumps(evidence, indent=2)}

Analyze this business and return a complete AI SDR dossier in JSON format mapping perfectly to the Opportunity schema.
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
            return AISDROutput.model_validate(result_json).model_dump()

        except Exception as e:
            print(f"Gemini API error: {e}")
            return None
