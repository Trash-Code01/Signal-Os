import os
import asyncio
import json
import re
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Set, Tuple

from core.safe_http import PublicAddressResolver, fetch_public_http_text

class WebsiteIntelligenceEngine:
    """
    Crawls strategic pages using aiohttp & BeautifulSoup to eliminate Docker/Playwright dependencies.
    Detects forms, CTAs, booking, ecommerce, social, and technology at lightning speed.
    """
    def __init__(self, max_pages: int = 15, max_depth: int = 2):
        self.max_pages = max_pages
        self.max_depth = max_depth
        # Simulate a real browser to prevent 403s
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def audit_website(self, start_url: str) -> Dict[str, Any]:
        print(f"[Crawler] Starting fast native audit for {start_url}")
        
        parsed_start = urllib.parse.urlsplit(start_url.strip())
        if not parsed_start.scheme:
            start_url = f"https://{start_url}"
            
        base_domain = (urllib.parse.urlsplit(start_url).hostname or "").rstrip(".").lower()
            
        findings = {
            "is_live": False,
            "has_ssl": start_url.startswith("https"),
            "pages_checked": [],
            "page_details": [],
            "emails": set(),
            "phones": set(),
            "social_profiles": {},
            "public_people": {},
            "technology_stack": set(),
            "booking_detected": False,
            "ecommerce_detected": False,
            "mobile_responsive": False, # Will detect below
            "responsive_evidence": [],
            "contact_form": False,
            "quote_form": False,
            "phone_cta": False,
            "sticky_cta": False,
            "live_chat": False,
            "evidence": [],
            "desktop_screenshot_base64": None
        }

        queue: List[Tuple[str, int]] = [(start_url, 0)]
        visited: Set[str] = set()
        pages_crawled = 0

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            connector = aiohttp.TCPConnector(resolver=PublicAddressResolver())
            async with aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=connector,
                trust_env=False,
            ) as session:
                while queue and pages_crawled < self.max_pages:
                    queue.sort(key=lambda item: self._page_priority(item[0]))
                    current_url, depth = queue.pop(0)
                    
                    normalized_url = self._normalise_url(current_url)
                    if normalized_url in visited:
                        continue
                        
                    visited.add(normalized_url)
                    
                    if depth > self.max_depth:
                        continue
                        
                    pages_crawled += 1
                    print(f"[Crawler] Fetching {pages_crawled}/{self.max_pages}: {current_url}")
                    
                    try:
                        response = await fetch_public_http_text(session, current_url)
                        if response.status >= 400:
                            continue

                        html = response.text
                        findings["is_live"] = True
                        final_url = response.url
                        findings["pages_checked"].append(final_url)

                        soup = BeautifulSoup(html, "html.parser")

                        # Remove script/style tags for cleaner text
                        for script in soup(["script", "style"]):
                            script.decompose()

                        text = soup.get_text(separator=" ", strip=True)

                        page_detail = self._extract_from_html(final_url, html, text, soup, findings)
                        page_detail["status_code"] = response.status
                        findings["page_details"].append(page_detail)

                        # Find internal links
                        if depth < self.max_depth:
                            for a_tag in soup.find_all("a", href=True):
                                href = a_tag["href"]
                                full_url = urllib.parse.urljoin(final_url, href)
                                if full_url.startswith('http'):
                                    link_domain = (urllib.parse.urlsplit(full_url).hostname or "").rstrip(".").lower()
                                    if link_domain == base_domain:
                                        queue.append((self._normalise_url(full_url), depth + 1))
                                            
                    except Exception as e:
                        print(f"[Crawler] Failed on {current_url}: {e}")

        except Exception as e:
            print(f"[Crawler] Critical aiohttp error: {e}")
            
        # Finalize findings
        if findings["is_live"]:
            summary_url = findings["pages_checked"][0] if findings["pages_checked"] else start_url
            negative_findings = [
                ("no_booking_system", findings["booking_detected"] is False, "No online booking or scheduling flow was detected across the crawled pages."),
                ("no_quote_funnel", findings["quote_form"] is False, "No dedicated quote or estimate form was detected across the crawled pages."),
                ("weak_phone_cta", findings["phone_cta"] is False, "No clickable phone call-to-action was detected across the crawled pages."),
                ("no_lead_form", findings["contact_form"] is False, "No lead or contact form was detected across the crawled pages."),
            ]
            for key, condition, msg in negative_findings:
                if condition:
                    findings["evidence"].append({
                        "url": summary_url,
                        "type": "gap_detected",
                        "content": key,
                        "context": msg
                    })
            if not findings["mobile_responsive"]:
                findings["evidence"].append({
                    "url": summary_url,
                    "type": "mobile_responsiveness_risk",
                    "content": "No standard mobile responsiveness signals were found in the pages crawled.",
                    "context": "No viewport meta tag or responsive CSS framework/media query was detected. This is a crawl heuristic and should be visually verified.",
                    "confidence": 0.7,
                })

        findings["emails"] = list(findings["emails"])
        findings["phones"] = list(findings["phones"])
        findings["technology_stack"] = list(findings["technology_stack"])
        findings["social_profiles"] = [
            {"platform": platform, "url": url}
            for platform, url in findings["social_profiles"].items()
        ]
        findings["public_people"] = list(findings["public_people"].values())

        return findings

    @staticmethod
    def _normalise_url(url: str) -> str:
        """Remove fragments and tracking parameters before adding crawl work."""
        parsed = urllib.parse.urlsplit(url)
        tracking = {"fbclid", "gclid", "mc_cid", "mc_eid"}
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        clean_query = [
            (key, value) for key, value in query
            if key.lower() not in tracking and not key.lower().startswith("utm_")
        ]
        path = parsed.path.rstrip("/") or "/"
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, urllib.parse.urlencode(clean_query), ""))

    def _page_priority(self, url: str) -> int:
        """Prioritize pages likely to have contact/booking info."""
        url_lower = url.lower()
        if any(term in url_lower for term in ['contact', 'about', 'book', 'schedule', 'appointment', 'team']):
            return 0
        if any(term in url_lower for term in ['service', 'pricing', 'quote']):
            return 1
        return 2

    def _extract_from_html(self, url: str, html: str, text: str, soup: BeautifulSoup, findings: Dict[str, Any]) -> Dict[str, Any]:
        html_lower = html.lower()
        text_lower = text.lower()
        
        # Responsive detection is a transparent markup heuristic.  We report
        # the exact signals collected rather than pretending this is a visual
        # device test.
        responsive_signals: List[str] = []
        viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        if viewport:
            viewport_value = (viewport.get("content") or "").lower()
            if "width=device-width" in viewport_value:
                responsive_signals.append("viewport meta")
        if re.search(r"@media\s*(?:only\s*)?\([^)]*(?:max|min)-width", html_lower):
            responsive_signals.append("responsive media query")
        if any(marker in html_lower for marker in ("bootstrap", "tailwind", "foundation", "bulma", "mui", "material-ui")):
            responsive_signals.append("responsive framework")
        if soup.find("picture") or soup.find(attrs={"srcset": True}):
            responsive_signals.append("responsive images")
        if responsive_signals:
            findings["mobile_responsive"] = True
            findings["responsive_evidence"].append({"url": url, "signals": responsive_signals})
        
        # Technology Stack
        if "wordpress" in html_lower or "wp-content" in html_lower: findings["technology_stack"].add("WordPress")
        if "shopify" in html_lower or "cdn.shopify" in html_lower:
            findings["technology_stack"].add("Shopify")
            findings["ecommerce_detected"] = True
        if "woocommerce" in html_lower:
            findings["technology_stack"].add("WooCommerce")
            findings["ecommerce_detected"] = True
        if "wix.com" in html_lower: findings["technology_stack"].add("Wix")
        if "squarespace" in html_lower: findings["technology_stack"].add("Squarespace")

        self._extract_structured_data(url, soup, findings)
        
        # Booking engines
        booking_markers = ['calendly', 'acuity', 'mindbody', 'vagaro', 'fresha', 'janeapp', 'simplybook', 'setmore', 'boulevard', 'zenoti', 'opentable', 'resy']
        for bk in booking_markers:
            if bk in html_lower:
                findings["booking_detected"] = True
                findings["technology_stack"].add(bk.title())
                
        # Regex extraction
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        # Expanded phone regex to catch standard formats
        phone_pattern = r'(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?'
        
        found_emails = re.findall(email_pattern, text)
        findings["emails"].update([e for e in found_emails if not any(x in e.lower() for x in ['.png', '.jpg', 'sentry', 'wix'])])
        
        # Simple phone collection (could be noisy but good for AI)
        for p in re.finditer(phone_pattern, text):
            match = p.group(0).strip()
            if len(re.sub(r'\D', '', match)) >= 10:
                findings["phones"].add(match)

        # Links (Mailto, Tel, Social)
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if href.startswith('mailto:'):
                findings["emails"].add(href.replace('mailto:', '').split('?')[0])
            elif href.startswith('tel:'):
                findings["phones"].add(href.replace('tel:', ''))
                findings["phone_cta"] = True
            
            # Socials
            for platform in ['linkedin', 'facebook', 'twitter', 'instagram', 'youtube']:
                if f"{platform}.com" in href:
                    findings["social_profiles"].setdefault(platform, a['href'])

        # Team/People Extraction (Heuristics)
        # Look for visible owner/leadership snippets on contact/about/team pages.
        for p in soup.find_all(['p', 'h2', 'h3', 'h4', 'div']):
            content = p.get_text(strip=True)
            if any(title in content for title in ["CEO", "Founder", "Owner", "Director", "Dr.", "Doctor", "Manager"]):
                person = self._extract_public_person(content, url)
                if person:
                    key = f"{person['first_name']} {person['last_name']}".lower()
                    findings["public_people"][key] = person

        # Forms
        forms = soup.find_all('form')
        for form in forms:
            form_text = form.get_text(strip=True).lower()
            if 'quote' in form_text or 'estimate' in form_text:
                findings["quote_form"] = True
                findings["evidence"].append({
                    "url": url,
                    "type": "quote_form_detected",
                    "content": form_text[:100],
                    "context": "Found a form requesting a quote or estimate."
                })
            else:
                findings["contact_form"] = True

        # CTAs
        buttons = soup.find_all(['a', 'button'])
        for btn in buttons:
            btn_text = btn.get_text(strip=True).lower()
            if 'quote' in btn_text or 'estimate' in btn_text:
                findings["quote_form"] = True
            if 'call' in btn_text or 'schedule' in btn_text:
                findings["phone_cta"] = True

        title_tag = soup.find("title")
        description_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        return {
            "url": url,
            "page_type": self._page_type(url),
            "title": title_tag.get_text(" ", strip=True)[:500] if title_tag else None,
            "meta_description": (description_tag.get("content") or "")[:500] if description_tag else None,
            "word_count": len(text.split()),
            "responsive_signals": responsive_signals,
            "forms_found": len(forms),
        }

    @staticmethod
    def _page_type(url: str) -> str:
        value = (url or "").lower()
        if "contact" in value:
            return "contact"
        if any(term in value for term in ("book", "quote", "estimate", "schedule", "appointment")):
            return "booking"
        if "about" in value or "team" in value:
            return "about"
        if "service" in value or "pricing" in value:
            return "services"
        return "homepage"

    def _extract_structured_data(self, url: str, soup: BeautifulSoup, findings: Dict[str, Any]) -> None:
        """Collect public LocalBusiness/Person facts exposed through JSON-LD."""
        nodes: List[Dict[str, Any]] = []
        for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if isinstance(payload, list):
                nodes.extend(item for item in payload if isinstance(item, dict))
            elif isinstance(payload, dict):
                graph = payload.get("@graph")
                if isinstance(graph, list):
                    nodes.extend(item for item in graph if isinstance(item, dict))
                else:
                    nodes.append(payload)

        for node in nodes:
            node_type = node.get("@type") or ""
            types = {str(item).lower() for item in (node_type if isinstance(node_type, list) else [node_type])}
            email = (node.get("email") or "").strip().lower()
            phone = (node.get("telephone") or "").strip()
            if email:
                findings["emails"].add(email)
            if phone:
                findings["phones"].add(phone)
            for profile_url in node.get("sameAs") or []:
                if not isinstance(profile_url, str):
                    continue
                lower_url = profile_url.lower()
                for platform in ["linkedin", "facebook", "twitter", "instagram", "youtube"]:
                    if f"{platform}.com" in lower_url:
                        findings["social_profiles"].setdefault(platform, profile_url)
            if {"person", "employee"}.intersection(types):
                name = (node.get("name") or "").strip()
                parts = name.split()
                if len(parts) >= 2:
                    findings["public_people"][name.lower()] = {
                        "first_name": parts[0],
                        "last_name": " ".join(parts[1:]),
                        "title": node.get("jobTitle") or "Team member",
                        "email": email or None,
                        "phone": phone or None,
                        "linkedin_url": next((value for value in node.get("sameAs") or [] if isinstance(value, str) and "linkedin.com" in value.lower()), None),
                        "contact_type": "professional",
                        "verification_status": "unknown",
                        "confidence": 0.9,
                        "source": "website_structured_data",
                        "source_url": url,
                    }

    def _extract_public_person(self, content: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract a conservative name/title pair from short public page snippets."""
        text = re.sub(r'\s+', ' ', content or '').strip()
        if not text or len(text) > 160:
            return None

        titles = [
            "Owner",
            "Founder",
            "Co-Founder",
            "CEO",
            "President",
            "Director",
            "Managing Director",
            "General Manager",
            "Manager",
            "Doctor",
            "Dr.",
        ]
        title = next((item for item in titles if re.search(rf'\b{re.escape(item)}\b', text, re.IGNORECASE)), None)
        if not title:
            return None

        lower_text = text.lower()
        title_index = lower_text.find(title.lower())
        candidate_parts = []
        if title_index > 0:
            candidate_parts.append(text[:title_index])
        if title_index >= 0:
            candidate_parts.append(text[title_index + len(title):])
        candidate_parts.append(text)

        ignored = {item.lower().replace(".", "") for item in titles}
        ignored.update({"and", "the", "team", "our", "staff", "contact"})
        for part in candidate_parts:
            words = re.findall(r"[A-Z][A-Za-z'.-]+", part)
            words = [word.strip(".,:;|-") for word in words if word.strip(".,:;|-").lower().replace(".", "") not in ignored]
            if len(words) >= 2:
                return {
                    "first_name": words[0],
                    "last_name": words[-1],
                    "title": title.replace("Dr.", "Doctor"),
                    "linkedin_url": None,
                    "contact_type": "professional",
                    "verification_status": "unknown",
                    "confidence": 0.65,
                    "source": "website_crawl",
                    "source_url": url,
                }

        return None
