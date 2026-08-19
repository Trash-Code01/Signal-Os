import asyncio
from typing import List, Dict, Any
from core.providers import BusinessDiscoveryProvider

class MockDiscoveryProvider(BusinessDiscoveryProvider):
    async def discover(self, query: str, location: str, industry: str, limit: int | None = None) -> List[Dict[str, Any]]:
        """Mock discovery returning predefined businesses for testing the pipeline."""
        print(f"Mock discovering: {query} in {location} for {industry}")
        
        # Simulate network delay
        await asyncio.sleep(1)
        
        businesses = [
            {
                "name": "Apex Roofing and Construction",
                "website_url": "https://apexroofingtx.com",
                "primary_phone": "+12145550199",
                "address": "123 Main St, Dallas, TX 75201",
                "city": "Dallas",
                "state_province": "TX",
                "country": "USA",
                "google_place_id": "ChIJ_mock_1",
                "source_metadata": {"source": "mock", "confidence": 0.9}
            },
            {
                "name": "Texas Star Roofing",
                "website_url": "https://texasstarroofing.com",
                "primary_phone": "+19725550188",
                "address": "456 Oak Rd, Houston, TX 77001",
                "city": "Houston",
                "state_province": "TX",
                "country": "USA",
                "google_place_id": "ChIJ_mock_2",
                "source_metadata": {"source": "mock", "confidence": 0.85}
            },
            {
                "name": "Bad Domain Roofing",
                "website_url": "https://thisdomaindoesnotexist.invalid",
                "primary_phone": "+15125550177",
                "address": "789 Pine Ln, Austin, TX 78701",
                "city": "Austin",
                "state_province": "TX",
                "country": "USA",
                "google_place_id": "ChIJ_mock_3",
                "source_metadata": {"source": "mock", "confidence": 0.7}
            }
        ]
        return businesses[:limit] if limit else businesses
