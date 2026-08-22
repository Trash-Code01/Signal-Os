import os
import re
import aiohttp
from typing import List, Dict, Any, Optional

class BraveSearchProvider:
    """Fallback search provider for finding public decision makers."""
    def __init__(self):
        self.api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search_decision_makers(self, business_name: str, city: str) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        
        # We run no more than two targeted searches
        queries = [
            f'"{business_name}" "{city}" (owner OR founder OR CEO OR president)',
            f'site:linkedin.com/in "{business_name}" (owner OR founder OR CEO OR president)'
        ]
        
        results = []
        async with aiohttp.ClientSession(headers=headers) as session:
            for query in queries:
                try:
                    async with session.get(self.base_url, params={"q": query, "count": 10}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            web_results = data.get("web", {}).get("results", [])
                            for item in web_results:
                                person = self._extract_person(item.get("title", ""), item.get("description", ""), item.get("url", ""), business_name)
                                if person:
                                    results.append(person)
                except Exception as e:
                    print(f"BraveSearchProvider error: {e}")
                    
        return results

    def _extract_person(self, title: str, description: str, url: str, business_name: str) -> Optional[Dict[str, Any]]:
        # A simple check: business name should be present or very similar. 
        # But even better, look for explicit pairing of name and role.
        
        leadership = r"Owner|Co[- ]?Owner|Founder|Co[- ]?Founder|CEO|Chief Executive(?: Officer)?|President|Principal|Partner|Managing Director|Director|General Manager"
        name = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'.-]+(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'.-]+){1,3}"
        
        # Regex to find "Name - Title" or "Title - Name"
        # We look in the title first, as LinkedIn profiles often format it like "Jane Doe - Owner - Company"
        match = re.search(rf"(?P<name>{name})\s*(?:,|\||—|–|-)\s*(?P<title>{leadership})\b", title, re.IGNORECASE)
        if not match:
            match = re.search(rf"\b(?P<title>{leadership})\s*[:—–-]\s*(?P<name>{name})", title, re.IGNORECASE)
            
        if not match:
            # Try description
            match = re.search(rf"(?P<name>{name})\s*(?:,|\||—|–|-)\s*(?P<title>{leadership})\b", description, re.IGNORECASE)
        if not match:
            match = re.search(rf"\b(?P<title>{leadership})\s*[:—–-]\s*(?P<name>{name})", description, re.IGNORECASE)
            
        if match:
            clean_name = re.sub(r"\s+", " ", match.group("name").strip(" \t\n,|:-"))
            clean_title = re.sub(r"\s+", " ", match.group("title").strip(" \t\n,|:-"))
            
            # Additional validation: the url is LinkedIn only if it matches linkedin.com/in/
            linkedin_url = url if "linkedin.com/in/" in url.lower() else None
            
            return {
                "first_name": clean_name.split()[0],
                "last_name": " ".join(clean_name.split()[1:]),
                "title": clean_title,
                "linkedin_url": linkedin_url,
                "contact_type": "professional",
                "verification_status": "unknown",
                "confidence": 0.85,
                "source": "brave_search",
                "source_url": url
            }
            
        return None
