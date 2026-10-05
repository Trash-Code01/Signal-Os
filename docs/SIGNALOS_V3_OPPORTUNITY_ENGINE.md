# SignalOS v3 — Opportunity Engine

## Product goal

SignalOS v3 should not optimize for the number of businesses collected. It should optimize for the number of **sales-worthy, evidence-backed opportunities** Devacia can realistically close.

The canonical question for every lead is:

> Why should Devacia contact this company now, what exact business function is missing, is the company commercially strong enough to buy, and can we reach the right person?

## What v3 fixes immediately

### 1. Evidence-first commercial scoring

The old scorer mostly rewarded:
- having a live website
- having a phone/email
- missing generic web features

It did not calculate real offer fit or buying intent and could over-score weak businesses.

v3 uses five bounded components:
- Business Fit — 25
- Digital Gap — 30
- Offer Fit — 20
- Opportunity Urgency — 15
- Contactability — 10

The score remains deterministic and explainable. AI can explain a lead, but it cannot make an unverified company an A+ opportunity.

### 2. No-website leads are no longer automatically A+

A missing website is a strong digital gap, not proof that the prospect is valuable.

v3 requires:
- evidence of real local demand (reviews/rating)
- an actionable contact path
- the campaign quality threshold

A weak business with almost no reviews cannot outrank an established local company only because it has no website.

### 3. Industry-aware gap scoring

A missing function matters only if it is commercially relevant to the industry.

Examples:
- Roofing/HVAC/Cleaning: quote/estimate funnel
- Restaurants/Clinics/Salons: booking/reservation flow
- D2C/Ecommerce: ecommerce capability
- B2B/Industrial: RFQ/catalogue flow

This prevents SignalOS from treating every missing booking widget or form as equally valuable.

### 4. Live campaigns never silently inject synthetic leads

Mock data is useful in staging but dangerous in a live sales CRM.

When Serper is unavailable or not configured, live discovery now returns no live records and reports provider health rather than silently substituting MockDiscoveryProvider output.

### 5. Qualified scores are preserved

The worker previously calculated a score, then deleted the Score row while rebuilding AI opportunity records. That could leave a qualified CRM lead without the score used to qualify it.

v3 preserves deterministic scoring independently from AI analysis.

## v3 lead model

Every lead should eventually have these independent dimensions.

### Company quality
- Rating
- Review count
- Review velocity
- Number of locations
- Team size proxy
- Years in operation
- Active service area
- Business category match
- Franchise/chain exclusion
- Estimated ability to pay

### Digital opportunity
- Website status
- Website age/modernity
- Mobile usability
- Speed/Core Web Vitals
- CTA clarity
- Quote/booking/order/RFQ flow
- Lead qualification
- Payment/deposit capability
- CRM/automation signals
- Conversion friction
- Ecommerce maturity
- Local SEO gaps

### Buying / change signals
This is the largest missing capability in the current codebase.

Add time-sensitive signals such as:
- recent hiring
- new location
- expansion
- recent rebrand
- new ownership
- active paid ads
- strong review growth
- recent social activity
- new services
- newly launched competitor pressure
- website redesign age
- broken booking/checkout
- seasonal demand window

These signals should be stored as evidence with observed_at timestamps and decay over time.

### Decision-maker quality
- named owner/founder/CEO/GM
- title relevance
- verified work email
- direct/mobile number
- public LinkedIn
- source provenance
- verification status
- confidence

### Offer fit
Map a lead to one specific productized Devacia offer:
- Conversion Website
- Booking System
- Quote / Lead System
- Property System
- Ecommerce System
- B2B Catalogue / RFQ

Each offer should define:
- required business signals
- required digital gaps
- disqualifiers
- expected ticket range
- evidence requirements

## Recommended qualification tiers

### A+ — sales-now
Requirements should include:
- strong business demand
- specific high-value digital gap
- strong offer match
- actionable decision-maker/contact path
- high data confidence
- no major disqualifier

### A — high priority
Strong business and offer fit but one piece of enrichment or urgency is weaker.

### B — nurture / research
Potentially good company, but evidence is incomplete or the opportunity is not urgent enough.

### Reject
Examples:
- weak/no commercial evidence
- national chain when local owner is not reachable
- already has a strong modern system
- duplicate
- wrong geography
- unreachable/dead business
- no practical Devacia offer match

## Architecture direction

### Stage 1 — Discovery
Use multiple providers behind one interface:
- Google Maps compatible provider
- DataForSEO
- search engine fallback
- optional vertical directories

Never let provider failure become synthetic production data.

### Stage 2 — Entity resolution
Merge by:
1. Place ID
2. Domain
3. Phone
4. normalized name + address
5. normalized name + city

Maintain source provenance.

### Stage 3 — Company validation
Reject weak/non-commercial entities before expensive analysis.

### Stage 4 — Website intelligence
Current aiohttp/BeautifulSoup crawler is useful for fast structural extraction.

Add a second browser-rendered deep-audit worker for top candidates:
- Playwright
- desktop/mobile rendering
- screenshots
- CTA visibility
- form completion path
- booking/order/quote flow
- actual layout evidence
- Lighthouse/PageSpeed

Do not call markup heuristics a visual UX audit.

### Stage 5 — Opportunity engine
Run deterministic scoring before AI.

Store:
- score_version
- component scores
- evidence IDs
- disqualifiers
- missing evidence
- score explanation

### Stage 6 — Contact enrichment
Only spend paid credits on leads that pass the commercial threshold.

Preferred order:
1. website-public leadership
2. public web search
3. premium people provider
4. email verification provider
5. optional phone reveal

### Stage 7 — AI SDR
AI should receive:
- company facts
- evidence
- score components
- detected gap
- selected offer
- decision maker

AI output:
- concise reason to contact
- exact recommended offer
- evidence-backed personalization
- outreach angle
- objection likely to appear
- confidence

AI must not create facts or override deterministic rejection gates.

## Next implementation phases

### Phase 1 — completed in branch
- v3 scoring engine
- industry-aware opportunity scoring
- no-website score guardrails
- live/mock separation
- score persistence fix
- threshold enforcement
- regression tests

### Phase 2 — high priority
- rendered browser audit for only top candidates
- temporal buying-signal table
- offer configuration engine
- named-decision-maker score boost after enrichment
- stronger chain/franchise detection
- location/business-size filters
- evidence-backed disqualifiers

### Phase 3
- provider ensemble and source confidence
- Apollo or equivalent premium enrichment adapter
- email verification
- lead freshness/decay
- campaign-level yield metrics
- cost per qualified lead / cost per A+ lead

### Phase 4
- learning loop from sales outcomes
- won/lost reason capture
- recalibrate weights from real Devacia conversion data
- industry-specific models
- recommended next-best action

## North-star metrics

Do not optimize only for leads discovered.

Track:
- qualified yield = qualified / discovered
- A+/A yield
- named decision-maker rate
- verified-contact rate
- evidence completeness
- duplicate rate
- provider cost per qualified lead
- reply rate by grade
- meeting rate by grade
- close rate by grade
- revenue per 100 researched businesses

SignalOS becomes defensible when its scores correlate with actual Devacia meetings and closed deals.
