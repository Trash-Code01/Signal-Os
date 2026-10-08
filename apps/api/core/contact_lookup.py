import os
from urllib.parse import urlparse
from core.runtime import IS_STAGING
from core.provider_health import report_provider_state
from providers.snovio_provider import SnovioProvider
from providers.serper_search_provider import SerperSearchProvider

async def lookup_optional_contacts(business, personal_email_enabled=False, phone_enabled=False):
    """Gate requests BEFORE provider calls, not merely the displayed results.

    Snov supplies personal work emails. Public search may supply a phone;
    the current Proxycurl executive endpoint supplies neither phone nor email.
    """
    is_live = os.getenv("DISCOVERY_MODE", "").strip().lower() == "live"
    if (IS_STAGING and not is_live) or not (personal_email_enabled or phone_enabled):
        return []
    domain = urlparse(business.website_url or "").hostname
    contacts = []
    if personal_email_enabled and domain:
        try:
            contacts.extend(await SnovioProvider().find_emails(domain, business.name))
        except Exception:
            report_provider_state('snovio', 'unavailable', 'Contact lookup failed. Public search will be attempted.')
    if phone_enabled or (personal_email_enabled and not contacts):
        try:
            contacts.extend(await SerperSearchProvider().search_decision_makers(
                business.name,
                business.city,
                domain,
                include_email=personal_email_enabled,
                include_phone=phone_enabled,
            ))
        except Exception:
            report_provider_state('serper', 'unavailable', 'Public contact lookup failed. Existing contacts were retained.')
    for contact in contacts:
        if not personal_email_enabled:
            contact["email"] = None
        if not phone_enabled:
            contact["phone"] = None
            contact["mobile"] = None
    return contacts

