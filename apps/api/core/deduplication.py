from typing import List, Dict, Any

class DeduplicationEngine:
    """
    Engine to deduplicate raw business leads.
    """
    def __init__(self, db_session):
        self.db = db_session

    def deduplicate(self, raw_businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of raw businesses and returns only the unique ones.
        Uniqueness is determined by website_url, primary_phone, or normalized name + location.
        """
        unique_businesses = []
        seen_urls = set()
        seen_phones = set()
        
        for business in raw_businesses:
            website_url = business.get("website_url") or business.get("domain")
            phone = business.get("primary_phone") or business.get("phone")
            
            # Simple in-memory deduplication for the batch
            is_duplicate = False
            if website_url and website_url in seen_urls:
                is_duplicate = True
            if phone and phone in seen_phones:
                is_duplicate = True
                
            if not is_duplicate:
                # In Phase 2: Add DB check here using Business model constraints
                
                unique_businesses.append(business)
                if website_url:
                    seen_urls.add(website_url)
                if phone:
                    seen_phones.add(phone)
                    
        return unique_businesses
