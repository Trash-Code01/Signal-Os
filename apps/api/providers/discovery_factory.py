import os
import json
import asyncio
from typing import List, Dict, Any
from core.providers import BusinessDiscoveryProvider
from .serper_discovery_provider import SerperDiscoveryProvider
from .mock_discovery import MockDiscoveryProvider

class FixtureDiscoveryProvider(BusinessDiscoveryProvider):
    def __init__(self, fixture_path: str = "tests/fixtures/discovery.json"):
        self.fixture_path = fixture_path

    async def discover(self, query: str, location: str, industry: str, limit: int | None = None) -> List[Dict[str, Any]]:
        print(f"Fixture discovering: {query} in {location} for {industry}")
        if not os.path.exists(self.fixture_path):
            print(f"Fixture file not found: {self.fixture_path}")
            return []
            
        with open(self.fixture_path, 'r') as f:
            data = json.load(f)
            return data[:limit] if limit else data

def get_discovery_provider(channels=None) -> BusinessDiscoveryProvider:
    # Live discovery is the safe production default. Mock and fixture data must
    # be explicitly opted into so it can never silently appear in a sales CRM.
    mode = os.environ.get("DISCOVERY_MODE", "live").strip().lower()

    if mode == "live":
        from .multichannel_discovery import MultiChannelDiscoveryProvider
        return MultiChannelDiscoveryProvider(channels or ['google_maps'])
    if mode == "fixture":
        return FixtureDiscoveryProvider()
    if mode == "mock":
        return MockDiscoveryProvider()
    raise ValueError("DISCOVERY_MODE must be 'live', 'fixture', or 'mock'")
