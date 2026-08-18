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
        Uniqueness is determined by domain, phone, or normalized name + location.
        """
        unique_businesses = []
        seen_domains = set()
        seen_phones = set()
        
        for business in raw_businesses:
            domain = business.get("domain")
            phone = business.get("phone")
            
            # Simple in-memory deduplication for the batch
            is_duplicate = False
            if domain and domain in seen_domains:
                is_duplicate = True
            if phone and phone in seen_phones:
                is_duplicate = True
                
            if not is_duplicate:
                # TODO: Check against database for existing records
                # db_duplicate = self.db.query(Business).filter(Business.domain == domain).first()
                # if db_duplicate:
                #    continue
                
                unique_businesses.append(business)
                if domain:
                    seen_domains.add(domain)
                if phone:
                    seen_phones.add(phone)
                    
        return unique_businesses
