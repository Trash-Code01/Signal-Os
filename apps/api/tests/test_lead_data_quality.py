import os
import asyncio

os.environ['ENVIRONMENT'] = 'staging'

from core.lead_quality import clean_email, clean_phone_for_country
from bs4 import BeautifulSoup
from engines.website_intelligence import WebsiteIntelligenceEngine
from providers.serper_discovery_provider import (
    SerperDiscoveryProvider,
    _is_junk_website,
    _parse_target_location,
)


def test_contact_validation_is_country_aware():
    assert clean_phone_for_country('+91 98765 43210', 'India') == '+91 98765 43210'
    assert clean_phone_for_country('011 4567 8901', 'India') == '011 4567 8901'
    assert clean_phone_for_country('+1 214-555-0199', 'India') is None
    assert clean_phone_for_country('+91 98765 43210', 'USA') is None
    assert clean_phone_for_country('(512) 555-0199', 'USA') == '(512) 555-0199'
    assert clean_phone_for_country('2026-09-20', 'India') is None


def test_email_validation_removes_markup_and_rejects_noise():
    assert clean_email(' MAILTO:Hello@Example.COM?subject=Hi ') == 'hello@example.com'
    assert clean_email('logo@example.com.png') is None
    assert clean_email('not an email') is None


def test_target_location_parser_does_not_invent_a_state():
    assert _parse_target_location('Delhi, India') == ('Delhi', None, 'India')
    assert _parse_target_location('Austin, Texas, USA') == ('Austin', 'Texas', 'USA')
    assert _parse_target_location('Melbourne, Australia') == ('Melbourne', None, 'Australia')


def test_official_website_matching_and_junk_domain_boundaries():
    provider = SerperDiscoveryProvider()
    assert provider._is_official_business_website(
        {'link': 'https://yogaliviya.com', 'title': 'Yogaliviya - Rooted in India', 'snippet': 'Yoga in Delhi'},
        'Yogaliviya',
    )
    assert not provider._is_official_business_website(
        {'link': 'https://directory.example.org/yogaliviya', 'title': 'Yogaliviya listings', 'snippet': 'Directory'},
        'Yogaliviya',
    )
    assert _is_junk_website('https://facebook.com/example')
    assert not _is_junk_website('https://notfacebook.com/example')


def test_crawler_extracts_international_phone_and_ignores_date():
    html = '''
        <html><head><title>Delhi Yoga</title></head><body>
        <p>Updated 2026-09-20</p>
        <p>Call our Delhi studio: +91 98765 43210</p>
        <a href="tel:+919876543210">Call now</a>
        </body></html>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    findings = {
        'emails': set(), 'phones': set(), 'social_profiles': {}, 'public_people': {},
        'technology_stack': set(), 'booking_detected': False, 'ecommerce_detected': False,
        'mobile_responsive': False, 'responsive_evidence': [], 'contact_form': False,
        'quote_form': False, 'phone_cta': False, 'evidence': [],
    }
    WebsiteIntelligenceEngine()._extract_from_html(
        'https://delhiyoga.example/contact', html, soup.get_text(' ', strip=True), soup, findings
    )
    assert '+91 98765 43210' in findings['phones']
    assert '+919876543210' in findings['phones']
    assert '2026-09-20' not in findings['phones']


def test_staging_crawler_never_invents_contacts_for_real_looking_url():
    result = asyncio.run(WebsiteIntelligenceEngine().audit_website('https://real-business-looking.example.com'))
    assert result['is_live'] is False
    assert result['emails'] == []
    assert result['phones'] == []
    assert result['public_people'] == []


def test_clean_website_url_unwraps_and_sanitizes():
    from core.lead_quality import clean_website_url, unwrap_redirect_url

    # 1. Google redirect unwrapping
    assert unwrap_redirect_url("https://www.google.com/url?q=https%3A%2F%2Fexample.com%2F&sa=U") == "https://example.com/"
    assert clean_website_url("https://www.google.com/url?q=https%3A%2F%2Fexample.com%2F&sa=U") == "https://example.com"

    # 2. Tracking parameters removal
    assert clean_website_url("https://newviewroofing.com/?utm_source=google&utm_medium=organic&utm_campaign=gmb") == "https://newviewroofing.com"
    assert clean_website_url("https://arringtonroofing.com/?utm_campaign=gmb&utm_medium=organic&utm_source=gbp&gclid=12345") == "https://arringtonroofing.com"

    # 3. Missing scheme and trailing slashes
    assert clean_website_url("sunshineroofingtx.com/") == "https://sunshineroofingtx.com"
    assert clean_website_url("http://www.dallasroofer.com///") == "http://www.dallasroofer.com"

    # 4. Common index/home paths normalized to root
    assert clean_website_url("https://example.com/index.html") == "https://example.com"
    assert clean_website_url("https://example.com/home") == "https://example.com"

    # 5. Junk / Social / Directory domains rejected
    assert clean_website_url("https://facebook.com/dallasroofing") is None
    assert clean_website_url("https://yelp.com/biz/arrington-roofing") is None
    assert clean_website_url("https://wikipedia.org/wiki/Roofing") is None
    assert clean_website_url("http://localhost:8000") is None

