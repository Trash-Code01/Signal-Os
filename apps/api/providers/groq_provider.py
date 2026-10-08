from core.runtime import IS_STAGING
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.provider_health import report_provider_state


# ── Output schema (identical to the old Gemini schema so worker.py needs no changes) ──
class AISDROutput(BaseModel):
    primary_problem: str = Field(description="The single most impactful problem Devacia can solve")
    problems: List[str] = Field(description="List of specific digital/UX/conversion problems detected")
    recommended_offer: str = Field(description="The exact Devacia service to pitch")
    ticket_low: int = Field(description="Lowest estimated project value in USD")
    ticket_high: int = Field(description="Highest estimated project value in USD")
    outreach_angle: str = Field(description="A specific personalised outreach sentence")
    ai_reasoning: str = Field(description="Detailed reasoning chain citing evidence")
    confidence: str = Field(description="high / medium / low")
    evidence_types_used: List[str] = Field(default_factory=list)


SYSTEM_PROMPT = """You are an elite AI Sales Development Representative (SDR) Analyst working for Devacia.
Devacia is a web development agency that builds booking systems, lead capture funnels, restaurant platforms,
clinic management systems, and conversion-focused websites.

Your job is to analyze collected intelligence about a business and produce a structured Opportunity dossier.

CRITICAL RULES:
1. NEVER invent information. Every claim MUST be grounded in the provided evidence.
2. If evidence is thin, set confidence to "low".
3. Problems must be SPECIFIC - not "poor CTA" but "no sticky call-to-action visible on mobile".
4. Recommended offer MUST be something Devacia actually builds: booking systems, lead capture funnels,
   restaurant/clinic/ecommerce sites, or conversion-focused redesigns. Focus heavily on how this offer specifically solves their exact weak point.
5. The outreach angle must be a hyper-personalised, top-tier pitch. Pitch them dynamically on their exact weak points and what Devacia offers.
6. ticket_low / ticket_high are USD estimates based on scope.
7. Return ONLY valid JSON matching the schema. NO MARKDOWN. NO CODE FENCES. NO CONVERSATION. JUST THE RAW JSON OBJECT starting with { and ending with }. NEVER include any text before or after the JSON.
"""


class GroqProvider:
    """
    Free AI SDR analysis via Groq (Qwen 3 27B).
    Free tier: high daily request allowance — no credit card required.
    Drop-in replacement for GeminiProvider. Same output schema.
    """

    MODEL = "qwen/qwen3.8-27b"   # Best reasoning model on this Groq account, avoids OTPM limits

    def __init__(self):
        self.live_enabled = not IS_STAGING or os.getenv('DISCOVERY_MODE', '').strip().lower() == 'live'
        self.api_key = os.environ.get("GROQ_API_KEY", "").strip() if self.live_enabled else ''
        self.model_name = os.environ.get("GROQ_MODEL", self.MODEL)
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                report_provider_state("groq", "not_configured", "GROQ_API_KEY is missing.")
                raise RuntimeError("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys")
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client

    def _build_prompt(self, evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> str:
        schema = {
            "primary_problem": "string",
            "problems": ["string"],
            "recommended_offer": "string",
            "ticket_low": 0,
            "ticket_high": 0,
            "outreach_angle": "string",
            "ai_reasoning": "string",
            "confidence": "high|medium|low",
            "evidence_types_used": ["string"],
        }
        return f"""{SYSTEM_PROMPT}

Industry Configuration:
{json.dumps(industry_config, indent=2)}

Collected Evidence:
{json.dumps(evidence, indent=2)}

Required JSON schema (return ONLY this JSON, nothing else):
{json.dumps(schema, indent=2)}

Analyze this business and return the JSON dossier:"""

    async def analyze(
        self,
        evidence: List[Dict[str, Any]],
        industry_config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Async SDR analysis via Groq. Returns dict matching AISDROutput or None."""
        if not evidence:
            return None

        prompt = self._build_prompt(evidence, industry_config)
        if not self.live_enabled:
            return None
        if not self.api_key:
            report_provider_state('groq', 'not_configured', 'GROQ_API_KEY is missing.')
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Devacia-SDR/1.0",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1000,
        }

        for attempt in range(3):
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=45),
                    ) as resp:
                        if resp.status != 200:
                            err_body = await resp.text()
                            raise RuntimeError(f"HTTP {resp.status}: {err_body[:200]}")
                        data = await resp.json()
                        raw = data["choices"][0]["message"]["content"]
                
                # Strip out Qwen <think> blocks if present
                import re as re_lib
                raw_clean = re_lib.sub(r'<think>.*?</think>', '', raw, flags=re_lib.DOTALL).strip()
                
                # Extract just the JSON object from the remaining text
                start = raw_clean.find('{')
                end = raw_clean.rfind('}')
                if start != -1 and end != -1:
                    raw_clean = raw_clean[start:end+1]
                    
                result_json = json.loads(raw_clean)
                # Validate and coerce through Pydantic
                parsed = AISDROutput.model_validate(result_json)
                report_provider_state("groq", "active", "AI analysis completed.", 200)
                return parsed.model_dump()

            except Exception as e:
                err_str = str(e)
                print(f"GroqProvider: API error (attempt {attempt + 1}): {err_str[:200]}")
                lowered = err_str.lower()
                state = "cooldown" if "429" in err_str or "rate limit" in lowered or "rate_limit" in lowered else "invalid_key" if "401" in err_str else "exhausted" if any(code in err_str for code in ("402", "403")) else "unavailable"
                report_provider_state("groq", state, f"AI analysis failed: {err_str[:180]}")
                if 'raw_clean' in locals():
                    print(f"Debug raw_clean: {raw_clean!r}")
                if attempt < 2 and ("429" in err_str or "rate_limit" in err_str.lower() or "rate limit" in err_str.lower()):
                    wait = 10 * (attempt + 1)
                    print(f"GroqProvider: Rate limited. Waiting {wait}s before retry...")
                    await asyncio.sleep(wait)
                    continue
                return None

        return None
