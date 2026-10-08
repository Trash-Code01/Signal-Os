"""Conservative validation helpers for facts admitted into the lead CRM."""

from __future__ import annotations

import re
from typing import Optional


COUNTRY_ALIASES = {
    "us": "USA",
    "u.s.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "uk": "UK",
    "united kingdom": "UK",
}

COUNTRY_CALLING_CODES = {
    "USA": "1",
    "Canada": "1",
    "India": "91",
    "UK": "44",
    "Australia": "61",
    "New Zealand": "64",
}

EMAIL_RE = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


def canonical_country(value: Optional[str]) -> str:
    text = (value or "").strip()
    return COUNTRY_ALIASES.get(text.lower(), text)


def clean_email(value: Optional[str]) -> Optional[str]:
    """Return a normalized syntactically valid email, otherwise ``None``."""
    email = (value or "").strip().lower()
    if email.lower().startswith("mailto:"):
        email = email[7:].split("?", 1)[0]
    email = email.strip(" <>\"'.,;:")
    if (
        len(email) > 254
        or ".." in email
        or email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"))
        or not EMAIL_RE.fullmatch(email)
    ):
        return None
    return email


def clean_phone_for_country(value: Optional[str], country: Optional[str]) -> Optional[str]:
    """Reject obvious noise and explicit country-code mismatches.

    Local numbers are accepted only when their length is plausible for the
    selected campaign country. International numbers must use that country's
    calling code. This prevents US fixture/listing numbers from being admitted
    into an India campaign.
    """
    raw = re.sub(r"[\x00-\x1f\x7f]", "", (value or "")).strip()
    if not raw or raw.lower().startswith(("test", "mock", "sample")):
        return None

    digits = re.sub(r"\D", "", raw)
    if raw.startswith("00"):
        digits = digits[2:]
        explicit_international = True
    else:
        explicit_international = raw.startswith("+")

    if not 7 <= len(digits) <= 15:
        return None

    normalized_country = canonical_country(country)
    calling_code = COUNTRY_CALLING_CODES.get(normalized_country)
    if explicit_international and calling_code and not digits.startswith(calling_code):
        return None

    national = digits[len(calling_code):] if explicit_international and calling_code else digits
    if normalized_country in {"USA", "Canada"}:
        if len(national) != 10 or national[0] in "01":
            return None
    elif normalized_country == "India":
        # Mobile numbers have ten digits; fixed lines commonly include a
        # leading zero and ten further digits (for example Delhi 011...).
        if not (len(national) == 10 or (len(national) == 11 and national.startswith("0"))):
            return None
    elif normalized_country == "UK":
        if len(national) not in {9, 10, 11}:
            return None
    elif normalized_country == "Australia":
        if len(national) not in {9, 10}:
            return None

    return re.sub(r"\s+", " ", raw)


JUNK_WEBSITE_DOMAINS = {
    "justdial.com",
    "wikipedia.org", "yelp.com", "facebook.com", "tripadvisor.com", "instagram.com",
    "linkedin.com", "google.com", "doordash.com", "ubereats.com", "grubhub.com",
    "yellowpages.com", "angi.com", "houzz.com", "thumbtack.com", "homeadvisor.com",
    "opentable.com", "zillow.com", "realtor.com", "chamberofcommerce.com", "manta.com",
    "bizapedia.com", "zoominfo.com", "dnb.com", "glassdoor.com", "indeed.com",
    "trustpilot.com", "foursquare.com", "alignable.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "mapquest.com", "bbb.org", "fmcsa.dot.gov",
    "serviceagent.ai",
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "gbraid", "wbraid", "mc_cid", "mc_eid",
    "_ga", "_gl", "sc_clid", "msclkid", "gad_source", "campaignid", "adgroupid"
}


def unwrap_redirect_url(url: str) -> str:
    """Unwrap Google Search / Google Maps redirect wrappers to find the true destination URL."""
    import urllib.parse
    if not url:
        return ""
    raw = url.strip()
    # Check for Google redirect wrapper: /url?q=... or /url?url=...
    if "google.com/url?" in raw or "google." in raw and "/url?" in raw:
        try:
            parsed = urllib.parse.urlsplit(raw if "://" in raw else f"https://{raw}")
            query = urllib.parse.parse_qs(parsed.query)
            target = query.get("q", query.get("url", [None]))[0]
            if target and target.startswith("http"):
                return urllib.parse.unquote(target).strip()
        except Exception:
            pass
    return raw


def clean_website_url(value: Optional[str]) -> Optional[str]:
    """Clean, unwrap, and normalize a business website URL to a clean canonical homepage.

    - Unwraps Google redirect URLs (e.g. google.com/url?q=...).
    - Enforces https:// (or keeps http:// if already present).
    - Strips ad tracking query parameters (utm_*, gclid, fbclid, etc.).
    - Strips URL fragments and trailing slashes.
    - Discards directory, Wikipedia, and social media domains.
    - Normalizes common index paths (/index.html, /index.php, /home) to root.
    """
    import urllib.parse
    if not value:
        return None

    raw = unwrap_redirect_url(str(value).strip().strip("\"'<>"))
    if not raw:
        return None

    if "://" not in raw:
        raw = f"https://{raw}"

    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return None
    if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
        return None

    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname or "." not in hostname:
        return None

    # Reject localhost, loopback, or invalid IP addresses
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or hostname.endswith(".localhost"):
        return None

    # Reject junk / social / directory domains
    for junk in JUNK_WEBSITE_DOMAINS:
        if hostname == junk or hostname.endswith(f".{junk}"):
            return None

    # Filter tracking query parameters
    filtered_query_pairs = []
    if parsed.query:
        for key, val in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_"):
                filtered_query_pairs.append((key, val))

    clean_query = urllib.parse.urlencode(filtered_query_pairs)

    # Normalize path: strip generic home paths or trailing slashes for company root
    path = parsed.path.rstrip("/")
    if path.lower() in {"", "/index.html", "/index.php", "/index.htm", "/home", "/home/", "/default.aspx"}:
        path = ""

    scheme = parsed.scheme.lower() if parsed.scheme in {"http", "https"} else "https"
    netloc = parsed.netloc.lower()

    # Reconstruct clean canonical URL
    result = urllib.parse.urlunsplit((scheme, netloc, path, clean_query, ""))
    # Ensure no trailing slash for consistent display and deduplication
    return result.rstrip("/")
