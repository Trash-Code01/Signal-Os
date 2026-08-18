import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from core.providers import AIProvider
import google.generativeai as genai

class AIReasoningOutput(BaseModel):
    is_qualified: bool = Field(description="Whether the business is qualified as a lead based on evidence.")
    business_fit_score: int = Field(description="Score 0-100 for business fit.")
    digital_gap_score: int = Field(description="Score 0-100 for digital gap (higher means bigger gap/problem).")
    offer_fit_score: int = Field(description="Score 0-100 for Devacia offer fit.")
    buying_intent_score: int = Field(description="Score 0-100 for buying intent/signals.")
    contactability_score: int = Field(description="Score 0-100 for contactability.")
    primary_problem: str = Field(description="The primary digital problem identified from evidence.")
    recommended_offer: str = Field(description="The recommended Devacia offer (e.g. Lead Capture, Quote Funnel).")
    outreach_angle: str = Field(description="A human-readable SDR outreach angle based ONLY on observed problems.")
    reasoning: str = Field(description="Detailed reasoning citing specific evidence.")

class GeminiProvider(AIProvider):
    def __init__(self):
        # Configure Gemini API key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro') # Or the specified model

    async def analyze(self, evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze evidence and generate diagnosis using Gemini."""
        
        prompt = f"""
        You are an expert SDR (Sales Development Representative) Analyst.
        Your task is to analyze a business based on collected evidence and qualify them for a Devacia agency offer.
        
        Industry Configuration:
        {json.dumps(industry_config, indent=2)}
        
        Collected Evidence:
        {json.dumps(evidence, indent=2)}
        
        RULES:
        1. Reason ONLY from the collected evidence provided. Do not invent missing facts.
        2. If the website does not exist or has critical issues that prevent analysis, score it low.
        3. Match the diagnosis to the closest offer specified in the Industry Configuration.
        4. Produce a human-readable outreach angle based on the OBSERVED problem, not generic personalization.
        
        Provide your analysis in JSON format matching the schema.
        """
        
        try:
            # Using generate_content with JSON mode/schema enforcement if available
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=AIReasoningOutput,
                )
            )
            
            # Parse the JSON response
            result_json = json.loads(response.text)
            return result_json
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback/error response
            return {
                "is_qualified": False,
                "business_fit_score": 0,
                "digital_gap_score": 0,
                "offer_fit_score": 0,
                "buying_intent_score": 0,
                "contactability_score": 0,
                "primary_problem": "Failed to analyze",
                "recommended_offer": "None",
                "outreach_angle": "None",
                "reasoning": f"Error calling Gemini: {e}"
            }
