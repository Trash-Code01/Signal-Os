from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BusinessDiscoveryProvider(ABC):
    @abstractmethod
    async def discover(self, query: str, location: str, industry: str) -> List[Dict[str, Any]]:
        """Discover raw businesses based on a query and location."""
        pass

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Perform open web search."""
        pass

class EmailProvider(ABC):
    @abstractmethod
    async def find_emails(self, domain: str, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find emails for a domain or specific person."""
        pass

class AIProvider(ABC):
    @abstractmethod
    async def analyze(self, evidence: List[Dict[str, Any]], industry_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze evidence and generate diagnosis, score, and outreach angle."""
        pass

class TechnologyProvider(ABC):
    @abstractmethod
    async def detect(self, url: str) -> List[str]:
        """Detect technologies used on a website."""
        pass
