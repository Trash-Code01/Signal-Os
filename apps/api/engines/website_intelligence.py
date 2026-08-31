import os
import asyncio
import re
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Set, Tuple

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
        
        if not start_url.startswith("http"):
            start_url = f"https://{start_url}"
            
        base_domain = urllib.parse.urlparse(start_url).netloc
            
        findings = {
            "is_live": False,
            "has_ssl": start_url.startswith("https"),
            "pages_checked": [],
            "emails": set(),
            "phones": set(),
            "social_profiles": {},
            "public_people": {},
            "technology_stack": set(),
            "booking_detected": False,
            "ecommerce_detected": False,
            "mobile_responsive": False, # Will detect below
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
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                while queue and pages_crawled < self.max_pages:
                    queue.sort(key=lambda item: self._page_priority(item[0]))
                    current_url, depth = queue.pop(0)
                    
                    normalized_url = current_url.split('#')[0].rstrip('/')
                    if normalized_url in visited:
                        continue
                        
                    visited.add(normalized_url)
                    
                    if depth > self.max_depth:
                        continue
                        
                    pages_crawled += 1
                    print(f"[Crawler] Fetching {pages_crawled}/{self.max_pages}: {current_url}")
                    
                    try:
                        async with session.get(current_url, ssl=False, allow_redirects=True) as response:
                            if response.status >= 400:
                                continue
                            
                            html = await response.text()
                            findings["is_live"] = True
                            findings["pages_checked"].append(current_url)
                            
                            soup = BeautifulSoup(html, "html.parser")
                            
                            # Remove script/style tags for cleaner text
                            for script in soup(["script", "style"]):
                                script.decompose()
                            
                            text = soup.get_text(separator=" ", strip=True)
                            
                            self._extract_from_html(current_url, html, text, soup, findings)
                            
                            # Find internal links
                            if depth < self.max_depth:
                                for a_tag in soup.find_all("a", href=True):
                                    href = a_tag["href"]
                                    full_url = urllib.parse.urljoin(current_url, href)
                                    if full_url.startswith('http'):
                                        link_domain = urllib.parse.urlparse(full_url).netloc
                                        if link_domain == base_domain:
                                            queue.append((full_url, depth + 1))
                                            
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

        findings["emails"] = list(findings["emails"])
        findings["phones"] = list(findings["phones"])
        findings["technology_stack"] = list(findings["technology_stack"])
        findings["social_profiles"] = [
            {"platform": platform, "url": url}
            for platform, url in findings["social_profiles"].items()
        ]
        findings["public_people"] = list(findings["public_people"].values())

        return findings

    def _page_priority(self, url: str) -> int:
        """Prioritize pages likely to have contact/booking info."""
        url_lower = url.lower()
        if any(term in url_lower for term in ['contact', 'about', 'book', 'schedule', 'appointment', 'team']):
            return 0
        if any(term in url_lower for term in ['service', 'pricing', 'quote']):
            return 1
        return 2

    def _extract_from_html(self, url: str, html: str, text: str, soup: BeautifulSoup, findings: Dict[str, Any]):
        html_lower = html.lower()
        text_lower = text.lower()
        
        # Responsive detection
        if 'name="viewport"' in html_lower or '@media' in html_lower or 'bootstrap' in html_lower or 'tailwind' in html_lower:
            findings["mobile_responsive"] = True
        
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
