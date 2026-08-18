# SignalOS Product Requirements & Architecture

## 1. Core Purpose
SignalOS is not merely a lead scraper. Its purpose is:
Discover businesses → collect business data → inspect their websites like a human SDR/web developer → identify digital/UX/conversion opportunities → qualify the business → find the actual decision maker → enrich personal contact information → recommend the exact Devacia service → store everything in a Notion-style CRM → export complete lead records to Google Sheets/CSV.

The system must produce sales-ready opportunities, not just lists of businesses.

## 2. Core Pipeline
The canonical pipeline must be:
CAMPAIGN → BUSINESS DISCOVERY → MULTI-SOURCE COLLECTION → DEDUPLICATION → BUSINESS VALIDATION → WEBSITE DISCOVERY → WEBSITE CRAWLER → TECHNICAL AUDIT → UX/UI AUDIT → CONVERSION AUDIT → BOOKING/ECOMMERCE/FUNCTIONALITY AUDIT → SOCIAL/BUSINESS PRESENCE → LEAD QUALIFICATION → DEVACIA OFFER MATCHING → LEAD SCORE → DECISION-MAKER ENRICHMENT → APOLLO PROVIDER POOL → CONTACT VERIFICATION/HUNTER → AI SDR ANALYSIS → OPPORTUNITY DOSSIER → CRM → EXPORT

## 3. Campaign Builder
Create `/campaigns/new` with fields:
- Geography: Country, State/Province, County, City, Postcode/ZIP (Allow: Multiple cities, Entire state, Selected counties, Radius)
- Industry: Industry, Sub-industry, Business category (e.g., Country: USA, State: Tennessee, City: Nashville, Industry: Restaurant)
- Target: Raw businesses desired, Minimum qualification score, A+ target, A target (e.g., Raw: 500, Min score: 75, A+: 50, A: 50)
- Research depth: Basic, Standard, Deep (Deep mode performs the complete website intelligence analysis).

## 4. Business Discovery
Build a provider abstraction: `providers/discovery/dataforseo`, `search/`, `local-business/`.
Collect: Company Name, Legal/Trading Name, Business Category, Industry, Sub-industry, Country, State, County, City, Address, ZIP/Postcode, Phone, Website, Google Business URL, Google Place ID, Google Rating, Review Count, Opening Hours, Latitude, Longitude.
Collect source information: source, source_url, source_id, discovered_at.

## 5. Multi-Source Discovery
Don't depend on one source. Create a Business Discovery Layer with provider adapters (DataForSEO, Brave Search, Google/Bing compatible sources, Apollo). The architecture must allow adding providers without rewriting the engine.

## 6. Deduplication Engine
This is critical. Merge same companies appearing across Google Maps, Search, Apollo, Facebook, Instagram, websites, directories.
Deduplication priority: 1. Place ID, 2. Domain, 3. Phone, 4. Normalized business name + address, 5. Business name + city.
Store all sources rather than throwing them away (e.g., ✓ Google, ✓ Website, ✓ Apollo).

## 7. Website Discovery
For every business: Does website exist? Is it reachable? Is HTTPS enabled? Is domain valid? Is website parked? Is website broken?
If no website: `website_status = NO_WEBSITE`. This should become a potentially valuable Devacia opportunity.

## 8. Website Crawler
Use Playwright + Python. The crawler must behave like a real browser.
Start with Homepage, then discover relevant pages: About, Services, Products, Pricing, Contact, Book, Booking, Appointment, Quote, Estimate, Get Started, Checkout, Locations, Team, FAQ.
Use intelligent page prioritization. Don't blindly crawl thousands of pages.

## 9. Website Data Extraction
Extract: Company name, Phone, Email, Address, Opening hours, Locations, Services, Products, Contact information.
Find emails from: Homepage, Contact page, Footer, About page, Team page, mailto links, structured data.
Store: email, email_type, source_url, confidence.
Do not confuse website contact emails with decision-maker personal emails.

## 10. Phone Extraction
Extract: Primary phone, Secondary phone, Mobile, Toll-free, WhatsApp.
Normalize phone numbers into international format. Store: raw_phone, normalized_phone, country_code, source.

## 11. Social Media Intelligence
Find: Facebook, Instagram, LinkedIn, TikTok, YouTube, X/Twitter, Pinterest.
Store: platform, profile_url, username, followers, source. Company profiles and personal profiles must be stored separately.

## 12. Website Technology Detection
Determine: WordPress, WooCommerce, Shopify, Wix, Squarespace, Webflow, Next.js, React, Laravel, Custom.
Detect: CMS, Analytics, Tag Manager, Payment providers, Booking platforms, Chat widgets, CRM, Forms, CDN.
Create: `technology_stack[]`

## 13. Technical Website Audit
Inspect Mobile (Responsive, Viewport, Text readable, Buttons usable, Navigation), Performance (Lighthouse, PageSpeed).
Capture: Performance, Accessibility, SEO, Best Practices, Core Web Vitals, Technical (HTTPS, Broken links, 404s, Redirects, Canonical, Meta tags, Schema, robots.txt, sitemap).

## 14. UX/UI Audit
Extremely important for Devacia. Analyze screenshots and page structure.
Check: Hero clarity, Headline, CTA visibility/hierarchy, Navigation, Typography, Spacing, Visual hierarchy, Color consistency, Trust signals, Testimonials, Reviews, Images, Cards, Forms, Mobile layout, Footer.
Create a UX score (e.g., 64/100) and evidence (e.g., "Weak mobile CTA").

## 15. Conversion Audit
Determine whether the business can convert visitors.
Check for: Contact form, Quote form, Estimate form, Booking, Appointment, Call CTA, Email CTA, Live chat, WhatsApp, Lead qualification, Newsletter, Checkout, Payment, Product catalog, Reservation.

## 16. Booking Intelligence
Actually inspect links/buttons/forms. Detect: Calendly, Fresha, Mindbody, Square Appointments, Acuity, OpenTable, Resy, custom systems.
Return: booking_available, booking_provider, booking_url, booking_flow_detected, booking_steps.

## 17. Ecommerce Intelligence
For D2C/ecommerce leads check: Product catalog, Product pages, Cart, Checkout, Payment, Search, Filters, Reviews, Wishlist, Account, Subscriptions, Upsells, Cross-sells. Detect: Shopify, WooCommerce, custom ecommerce.

## 18. Industry-Specific Intelligence
Configuration-driven (e.g., `industry-config/restaurants`, `roofing`, etc.). Each contains: search_queries, important_pages, important_features, required_functionality, conversion_signals, negative_signals, Devacia_offers, scoring_weights.

## 19-20. Examples
- Restaurant: Menu, Reservations, Online ordering. Offer: Restaurant Website, Reservation System.
- Clinic: Doctor profiles, Appointment booking. Offer: Clinic Booking System.

## 21. Lead Qualification Engine
Every lead gets a score: BUSINESS FIT (20) + WEBSITE GAP (20) + UX/UI GAP (15) + CONVERSION GAP (20) + OFFER FIT (15) + CONTACTABILITY (10) = TOTAL 100.
Output: A+ (90–100), A (80–89), B (70–79), C (60–69), Reject (<60).

## 22. Opportunity Detection (Most Important)
Answer: "Why should Devacia contact this company?"
Output a detected list of problems (e.g., "No online appointment booking") and Recommended Devacia Offer with Estimated ticket ($3,500–$5,000).

## 23. Apollo Decision-Maker Enrichment
Only run Apollo after qualification to protect credits. Implement an Apollo Pool to cycle through accounts. Use environment variables/encrypted secrets/provider_accounts table.

## 24-25. Decision-Maker Search & Contact Record
Search for Owner, Founder, CEO, etc., ranked by company size.
Obtain First Name, Last Name, Job Title, Personal/Business Email, Mobile, LinkedIn. Store source = Apollo. Do not overwrite company info.

## 26. Hunter
Use for email discovery/verification. Store: email_status, email_confidence, verification_source, verified_at.

## 27. AI SDR Analyst
Gemini receives company data, audits, and outputs structured JSON: lead_summary, why_this_is_a_good_lead, detected_problems, recommended_offer, estimated_offer_range, outreach_angle, personalization_points, confidence. Must never invent info.

## 28-29. CRM — Notion Style
Main table is high-density operational view. Clicking a lead opens a deep Lead Intelligence Dossier.

## 30. Evidence System
Every important finding must have evidence (e.g., "No booking CTA detected on homepage"). For visual issues: Mobile screenshot.

## 31-33. Lead Status, Ownership, Views
Statuses (NEW, QUALIFIED, A+, HOT, CONTACTED, etc.). Owners (SDR, Founder). Notion-style views (All Leads, A+, No Website, Booking Opportunities, etc.).

## 34-37. Search, Filters, Google Sheets Export
Global search across all entities. Powerful filters. CSV/XLSX and Google Sheets integration mirroring CRM schema.

## 38. Screenshot Storage
Store desktop/mobile screenshots for deeply audited websites. Make retention configurable.

## 39-40. Architecture & Stack
- Frontend: Next.js, React, TypeScript, Tailwind, shadcn/ui
- Backend: Python, FastAPI
- Workers: Python, Playwright, BeautifulSoup, lxml
- Database: PostgreSQL
- Queue: Redis
- AI: Gemini, DataForSEO, Apollo, Hunter
- Tools: Lighthouse, PageSpeed, n8n, Docker, GitHub

## 41-42. Database Schema & Provider Management
Create comprehensive tables (users, campaigns, businesses, websites, audits, etc.). Provider settings screen showing health and usage.

## 43-44. Job Monitoring & Failure Handling
Monitor progress of discovery, deduplication, audits. Every provider needs retry, timeout, rate-limit handling, dead-letter state. Don't stop campaign if one website fails.

## 45-46. First MVP & Definition of Done
Do NOT build every industry first. Build: USA, Texas, Dallas, Roofing.
Definition of Done: The system is complete ONLY when we can enter a campaign (e.g., Dallas Roofing 100 leads) and SignalOS automatically produces a deeply enriched, highly detailed, AI-analyzed lead in the CRM, ready to export to Google Sheets with ALL specified intelligence fields.

---
**The most important product principle:**
SignalOS is not a database with a scraper attached. It is an intelligence pipeline with a CRM attached. The actual competitive advantage is finding the 300 worth selling to from 10,000 businesses, verifying contact paths, and explaining exactly what Devacia should sell.
