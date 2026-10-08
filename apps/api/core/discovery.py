"""Shared discovery vocabulary and evidence-based candidate ranking."""
from typing import Literal

DiscoveryChannel = Literal['google_maps', 'google_search', 'directories', 'facebook', 'instagram', 'linkedin']
WebsiteFilter = Literal['all', 'no_website', 'has_website']
CHANNELS = ('google_maps', 'google_search', 'directories', 'facebook', 'instagram', 'linkedin')


def candidate_priority(candidate: dict) -> tuple:
    """Prioritize observed contact and business signals before expensive research."""
    return (
        bool(candidate.get('primary_phone')),
        candidate.get('website_status') == 'no_website',
        int(candidate.get('review_count') or 0),
        float(candidate.get('rating') or 0),
    )


def no_website_score(*, phone: bool, contact: bool, reviews: int, rating: float, checked: bool) -> dict:
    fit = 20 + (10 if reviews > 5 else 0) + (10 if reviews > 50 else 0) + (5 if rating >= 4 else 0)
    reach = 20 if contact else 10 if phone else 0
    gap = 30 if checked else 0
    total = min(100, fit + reach + gap)
    return dict(commercial_score=total, data_confidence=min(95, (45 if checked else 10) + reach + (15 if reviews else 0)),
                grade='A+' if total >= 90 else 'A' if total >= 80 else 'B' if total >= 70 else 'C' if total >= 50 else 'Reject',
                business_fit=fit, digital_gap=gap, contactability=reach, offer_fit=0, buying_intent=0)
