from core.runtime import IS_STAGING
from providers.snovio_provider import SnovioProvider
from providers.serper_search_provider import SerperSearchProvider

async def lookup_optional_contacts(business, personal_email_enabled=False, phone_enabled=False):
    """Gate requests BEFORE provider calls, not merely the displayed results.

    Snov supplies personal work emails. Public search may supply a phone;
    the current Proxycurl executive endpoint supplies neither phone nor email.
    """
    if IS_STAGING or not (personal_email_enabled or phone_enabled):
        return []
    from urllib.parse import urlparse
    domain = urlparse(business.website_url or "").hostname
    contacts = []
    if personal_email_enabled and domain:
        contacts.extend(await SnovioProvider().find_emails(domain, business.name))
    if phone_enabled or (personal_email_enabled and not domain):
        contacts.extend(await SerperSearchProvider().search_decision_makers(business.name, business.city, domain, include_email=personal_email_enabled, include_phone=phone_enabled))
    for contact in contacts:
        if not personal_email_enabled:
            contact["email"] = None
        if not phone_enabled:
            contact["phone"] = None
            contact["mobile"] = None
    return contacts
