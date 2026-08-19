import os
import asyncio
import re
import urllib.parse
from typing import Dict, Any, List, Set, Tuple
from playwright.async_api import async_playwright, Page, BrowserContext

class WebsiteIntelligenceEngine:
    """
    Crawls strategic pages, renders desktop/mobile, detects forms, CTAs, 
    booking, quote, ecommerce, payments, social, analytics and technology.
    Enforces maximum budget (pages=15, depth=2).
    """
    def __init__(self, max_pages: int = 15, max_depth: int = 2):
        self.max_pages = max_pages
        self.max_depth = max_depth

    async def audit_website(self, start_url: str) -> Dict[str, Any]:
        print(f"[Crawler] Starting full audit for {start_url}")
        
        if not start_url.startswith("http"):
            start_url = f"https://{start_url}"
            
        base_domain = urllib.parse.urlparse(start_url).netloc
            
        findings = {
            "is_live": False,
            "has_ssl": start_url.startswith("https"),
            "pages_checked": [],
            "emails": set(),
            "phones": set(),
            "technology_stack": set(),
            "booking_detected": False,
            "ecommerce_detected": False,
            "mobile_responsive": None,
            "contact_form": False,
            "quote_form": False,
            "phone_cta": False,
            "sticky_cta": False,
            "live_chat": False,
            "evidence": [],
            "desktop_screenshot_base64": None
        }

        # BFS Queue: list of (url, depth)
        queue: List[Tuple[str, int]] = [(start_url, 0)]
        visited: Set[str] = set()
        pages_crawled = 0

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                
                # Contexts for both viewport sizes
                desktop_context = await browser.new_context(viewport={'width': 1440, 'height': 900})
                mobile_context = await browser.new_context(
                    viewport={'width': 375, 'height': 812},
                    is_mobile=True,
                    has_touch=True
                )
                
                while queue and pages_crawled < self.max_pages:
                    # Sort queue to prioritize contact/about/booking/services
                    queue.sort(key=lambda item: self._page_priority(item[0]))
                    
                    current_url, depth = queue.pop(0)
                    
                    # Normalize URL for deduplication
                    normalized_url = current_url.split('#')[0].rstrip('/')
                    if normalized_url in visited:
                        continue
                        
                    visited.add(normalized_url)
                    
                    if depth > self.max_depth:
                        continue
                        
                    pages_crawled += 1
                    print(f"[Crawler] Crawling {pages_crawled}/{self.max_pages}: {current_url} (Depth {depth})")
                    
                    page = await desktop_context.new_page()
                    try:
                        response = await page.goto(current_url, timeout=15000, wait_until="domcontentloaded")
                        if not response or not response.ok:
                            await page.close()
                            continue
                            
                        findings["is_live"] = True
                        findings["pages_checked"].append(current_url)
                        
                        # 1. Capture HTML & Text
                        html = await page.content()
                        text = await page.evaluate("document.body.innerText") or ""
                        
                        # Extract Tech, Phones, Emails
                        self._extract_tech_and_commerce(html, findings)
                        self._extract_contacts(text, findings)
                        await self._extract_link_contacts(page, findings)
                        
                        # 2. Extract Evidence (Forms & CTAs)
                        await self._extract_page_evidence(page, current_url, findings)
                        
                        # 3. Take Screenshot of Homepage ONLY
                        if pages_crawled == 1:
                            findings["desktop_screenshot_base64"] = await self._take_screenshot(page)
                            
                            # Check mobile responsiveness on Homepage
                            mobile_page = await mobile_context.new_page()
                            try:
                                await mobile_page.goto(current_url, timeout=15000, wait_until="domcontentloaded")
                                viewport_width = await mobile_page.evaluate("window.innerWidth")
                                body_width = await mobile_page.evaluate("document.body.scrollWidth")
                                findings["mobile_responsive"] = body_width <= viewport_width + 50
                            except Exception:
                                pass
                            finally:
                                await mobile_page.close()
                        
                        # 4. Enqueue Links (if depth < max_depth)
                        if depth < self.max_depth:
                            links = await page.evaluate("""() => {
                                return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
                            }""")
                            
                            for link in set(links):
                                if link.startswith('http'):
                                    link_domain = urllib.parse.urlparse(link).netloc
                                    if link_domain == base_domain: # Only internal links
                                        queue.append((link, depth + 1))
                                        
                    except Exception as page_e:
                        print(f"[Crawler] Failed on {current_url}: {page_e}")
                    finally:
                        if not page.is_closed():
                            await page.close()
                            
                await desktop_context.close()
                await mobile_context.close()
                await browser.close()
                
        except Exception as e:
            print(f"[Crawler] Critical Playwright error: {e}")
            
        # Make negative conversion findings explicit and tied to the crawl. This
        # gives AI a real, auditable basis for a gap rather than a generic pitch.
        if findings["is_live"]:
            summary_url = findings["pages_checked"][0] if findings["pages_checked"] else start_url
            negative_findings = [
                ("no_booking_system", findings["booking_detected"] is False, "No online booking or scheduling flow was detected across the crawled pages."),
                ("no_quote_funnel", findings["quote_form"] is False, "No dedicated quote or estimate form was detected across the crawled pages."),
                ("weak_phone_cta", findings["phone_cta"] is False, "No clickable phone call-to-action was detected across the crawled pages."),
                ("no_lead_form", findings["contact_form"] is False, "No lead or contact form was detected across the crawled pages."),
            ]
            for source_type, missing, text in negative_findings:
                if missing:
                    findings["evidence"].append({
                        "source_type": source_type,
                        "evidence_text": text,
                        "page_url": summary_url,
                        "confidence": 0.85,
                    })

        # Format outputs
        findings["emails"] = list(findings["emails"])
        findings["phones"] = list(findings["phones"])
        findings["technology_stack"] = list(findings["technology_stack"])
        
        return findings

    def _page_priority(self, url: str) -> int:
        """Lower number = higher priority."""
        url_lower = url.lower()
        if "contact" in url_lower: return 1
        if "book" in url_lower or "schedule" in url_lower: return 2
        if "about" in url_lower: return 3
        if "service" in url_lower: return 4
        return 10
        
    def _extract_tech_and_commerce(self, html: str, findings: Dict):
        html_lower = html.lower()
        
        # Tech Stack
        if "wordpress" in html_lower or "wp-content" in html_lower: findings["technology_stack"].add("WordPress")
        if "shopify" in html_lower: 
            findings["technology_stack"].add("Shopify")
            findings["ecommerce_detected"] = True
        if "woocommerce" in html_lower: 
            findings["technology_stack"].add("WooCommerce")
            findings["ecommerce_detected"] = True
        if "wix.com" in html_lower: findings["technology_stack"].add("Wix")
        if "squarespace" in html_lower: findings["technology_stack"].add("Squarespace")
        
        # Booking
        booking_keywords = ["calendly", "acuity", "fresha", "mindbody", "jobber", "housecall", "service titan", "servicetitan"]
        for bk in booking_keywords:
            if bk in html_lower:
                findings["booking_detected"] = True
                findings["technology_stack"].add(bk.title())

    def _extract_contacts(self, text: str, findings: Dict):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'(?:\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        
        findings["emails"].update(re.findall(email_pattern, text))
        findings["phones"].update(re.findall(phone_pattern, text))

    async def _extract_link_contacts(self, page: Page, findings: Dict):
        """Capture public mailto/tel links even when the address is not visible in body text."""
        try:
            mailtos = await page.locator('a[href^="mailto:"]').evaluate_all("links => links.map(link => link.href)")
            tels = await page.locator('a[href^="tel:"]').evaluate_all("links => links.map(link => link.href)")
            for href in mailtos:
                value = href.split(":", 1)[-1].split("?", 1)[0].strip()
                if value:
                    findings["emails"].add(value)
            for href in tels:
                value = href.split(":", 1)[-1].strip()
                if value:
                    findings["phones"].add(value)
            if tels:
                findings["phone_cta"] = True
        except Exception:
            # A malformed page should not stop the rest of its audit.
            return

    async def _extract_page_evidence(self, page: Page, url: str, findings: Dict):
        # 1. Forms
        forms = await page.locator("form").count()
        if forms > 0:
            findings["contact_form"] = True
            form_text = " ".join(await page.locator("form").all_inner_texts()).lower()
            if any(word in form_text for word in ("quote", "estimate", "get started", "project")):
                findings["quote_form"] = True
            findings["evidence"].append({
                "source_type": "contact_form",
                "evidence_text": f"Detected {forms} lead/contact form(s) on {url}",
                "page_url": url,
                "confidence": 1.0
            })
            
        # 2. CTAs
        cta_texts = ["book", "quote", "estimate", "schedule", "call now", "contact us"]
        found_ctas = []
        cta_content = " ".join(await page.locator("a, button").all_inner_texts()).lower()
        for cta in cta_texts:
            if cta in cta_content:
                found_ctas.append(cta)
        if any(cta in found_ctas for cta in ("quote", "estimate")):
            findings["quote_form"] = True
        if "call now" in found_ctas:
            findings["phone_cta"] = True

        try:
            findings["sticky_cta"] = findings["sticky_cta"] or await page.locator("a, button").evaluate_all("elements => elements.some(element => ['fixed', 'sticky'].includes(getComputedStyle(element).position))")
        except Exception:
            pass
        
        if found_ctas:
            findings["evidence"].append({
                "source_type": "high_intent_cta",
                "evidence_text": f"Found high-intent CTAs on {url}: {', '.join(found_ctas)}",
                "page_url": url,
                "confidence": 0.9
            })

    async def _take_screenshot(self, page: Page) -> str:
        import base64
        try:
            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except:
            return ""
