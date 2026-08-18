import asyncio
from typing import List, Dict, Any
from core.providers import BusinessDiscoveryProvider

class MockDiscoveryProvider(BusinessDiscoveryProvider):
    async def discover(self, query: str, location: str, industry: str) -> List[Dict[str, Any]]:
        """Mock discovery returning predefined businesses for testing the pipeline."""
        print(f"Mock discovering: {query} in {location} for {industry}")
        
        # Simulate network delay
        await asyncio.sleep(1)
        
        return [
            {
                "name": "Apex Roofing and Construction",
                "domain": "apexroofingtx.com",
                "phone": "+12145550199",
                "address": "123 Main St, Dallas, TX 75201",
                "city": "Dallas",
                "state": "TX",
                "country": "USA",
                "place_id": "ChIJ_mock_1",
                "source_metadata": {"source": "mock", "confidence": 0.9}
            },
            {
                "name": "Texas Star Roofing",
                "domain": "texasstarroofing.com",
                "phone": "+19725550188",
                "address": "456 Oak Rd, Houston, TX 77001",
                "city": "Houston",
                "state": "TX",
                "country": "USA",
                "place_id": "ChIJ_mock_2",
                "source_metadata": {"source": "mock", "confidence": 0.85}
            },
            {
                "name": "Bad Domain Roofing",
                "domain": "thisdomaindoesnotexist.invalid",
                "phone": "+15125550177",
                "address": "789 Pine Ln, Austin, TX 78701",
                "city": "Austin",
                "state": "TX",
                "country": "USA",
                "place_id": "ChIJ_mock_3",
                "source_metadata": {"source": "mock", "confidence": 0.7}
            }
        ]
