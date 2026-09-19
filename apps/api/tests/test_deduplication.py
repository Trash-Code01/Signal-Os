from core.deduplication import DeduplicationEngine


def test_deduplication_normalises_domains_phones_and_location_names():
    businesses = [
        {"name": "Acme Dental", "website_url": "https://www.acme.example/", "city": "Austin", "country": "USA"},
        {"name": "Acme Dental Clinic", "website_url": "acme.example", "city": "Austin", "country": "USA"},
        {"name": "North Star", "primary_phone": "+1 (512) 555-0199", "city": "Austin", "country": "USA"},
        {"name": "North Star LLC", "primary_phone": "512-555-0199", "city": "Austin", "country": "USA"},
        {"name": "Oak Bakery", "city": "Austin", "country": "USA"},
        {"name": "oak bakery", "city": "Austin", "country": "USA"},
        {"name": "Oak Bakery", "city": "Dallas", "country": "USA"},
    ]

    result = DeduplicationEngine().deduplicate(businesses)

    assert result == [businesses[0], businesses[2], businesses[4], businesses[6]]
