from playwright.async_api import async_playwright
from typing import Dict, Any, List
import asyncio
import aiohttp
import os

class WebsiteIntelligenceEngine:
    """
    Crawls strategic pages, renders desktop/mobile, detects forms, CTAs, 
    booking, quote, ecommerce, payments, social, analytics and technology.
    """
    async def audit_website(self, url: str) -> Dict[str, Any]:
        """
        Perform a Playwright-based audit of a single website.
        """
        print(f"Starting audit for {url}")
        
        # In a real system, you would check URL format, add scheme if missing
        if not url.startswith("http"):
            url = f"https://{url}"

        findings = {
            "is_live": False,
            "has_ssl": url.startswith("https"),
            "pages_checked": [],
            "evidence": []
        }
        
        try:
            async with async_playwright() as p:
                # Launch browser (headless by default)
                browser = await p.chromium.launch()
                
                # Create desktop context
                desktop_context = await browser.new_context(
                    viewport={'width': 1440, 'height': 900}
                )
                
                page = await desktop_context.new_page()
                
                try:
                    response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    if response and response.ok:
                        findings["is_live"] = True
                        findings["pages_checked"].append(url)
                        
                        # 1. Look for forms (Booking / Quotes)
                        forms = await page.locator("form").count()
                        if forms > 0:
                            findings["evidence"].append({
                                "source_type": "playwright_crawler",
                                "evidence_text": f"Found {forms} form(s) on the homepage.",
                                "confidence": 1.0,
                                "page_url": url
                            })
                            
                        # 2. Look for common CTAs (Call, Quote, Estimate, Book)
                        cta_texts = ["book", "quote", "estimate", "schedule", "call now", "contact us"]
                        found_ctas = []
                        for cta in cta_texts:
                            # Simple text search heuristic
                            cta_count = await page.locator(f"text={cta}").count()
                            if cta_count > 0:
                                found_ctas.append(cta)
                        
                        if found_ctas:
                            findings["evidence"].append({
                                "source_type": "playwright_crawler",
                                "evidence_text": f"Found CTAs matching: {', '.join(found_ctas)}",
                                "confidence": 0.9,
                                "page_url": url
                            })
                            
                        # 3. Simple text capture for AI reasoning later
                        page_text = await page.evaluate("document.body.innerText")
                        page_text = page_text[:5000] if page_text else ""
                        findings["text_content"] = page_text
                        
                        findings["evidence"].append({
                            "source_type": "playwright_crawler",
                            "evidence_text": f"Homepage text snippet: {page_text[:500]}...",
                            "confidence": 1.0,
                            "page_url": url
                        })

                        # Extract Emails & Phones
                        import re
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        phone_pattern = r'(\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
                        findings["emails"] = list(set(re.findall(email_pattern, page_text)))
                        findings["phones"] = list(set(re.findall(phone_pattern, page_text)))
                        
                        # Detect Tech/Booking keywords in HTML
                        html = await page.content()
                        html_lower = html.lower()
                        tech_stack = []
                        if "wordpress" in html_lower or "wp-content" in html_lower: tech_stack.append("WordPress")
                        if "shopify" in html_lower: tech_stack.append("Shopify")
                        if "woocommerce" in html_lower: tech_stack.append("WooCommerce")
                        if "calendly" in html_lower or "acuity" in html_lower or "fresha" in html_lower: tech_stack.append("Booking Software")
                        findings["technology_stack"] = tech_stack
                        
                        # 4. Take Screenshots (Disk + Base64)
                        screenshot_dir = os.path.join(os.getcwd(), "screenshots")
                        os.makedirs(screenshot_dir, exist_ok=True)
                        desktop_path = os.path.join(screenshot_dir, f"{url.replace('https://', '').replace('/', '_')}_desktop.png")
                        screenshot_bytes = await page.screenshot(path=desktop_path, type="jpeg", quality=60)
                        
                        import base64
                        findings["desktop_screenshot_base64"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                        
                        # 5. Call Google PageSpeed Insights (if API key available)
                        ps_api_key = os.environ.get("PAGESPEED_API_KEY")
                        if ps_api_key:
                            ps_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={ps_api_key}&strategy=mobile"
                            async with aiohttp.ClientSession() as ps_session:
                                async with ps_session.get(ps_url) as ps_response:
                                    if ps_response.status == 200:
                                        ps_data = await ps_response.json()
                                        score = ps_data.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0)
                                        perf_score = int(score * 100)
                                        findings["evidence"].append({
                                            "source_type": "pagespeed_api",
                                            "evidence_text": f"Lighthouse mobile performance score: {perf_score}/100",
                                            "confidence": 1.0,
                                            "page_url": url
                                        })
                        
                except Exception as page_e:
                    print(f"Failed to load {url}: {page_e}")
                    
                finally:
                    await desktop_context.close()
                    await browser.close()
                    
        except Exception as e:
            print(f"Playwright error for {url}: {e}")
            
        return findings

# Example usage for local testing
if __name__ == "__main__":
    engine = WebsiteIntelligenceEngine()
    result = asyncio.run(engine.audit_website("apexroofingtx.com"))
    import json
    print(json.dumps(result, indent=2))
