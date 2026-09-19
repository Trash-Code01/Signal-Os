# Lead Pipeline Diagnosis and Antigravity Fix Plan

**Diagnosed:** 2026-08-28

## Executive result

The app is online and campaigns run, but the pipeline is not reliably producing
sales-ready leads. There are two kinds of failures:

1. Many campaigns finish immediately because Serper Places provides no official
   website for the discovered businesses, so they are stored as
   `rejected_no_website` and never reach audit, owner research, or qualification.
2. Some campaigns reach the CRM, but discovery and public-person parsing admit
   directories, unrelated LinkedIn results, and malformed names. This makes a
   lead look detailed while the details are not trustworthy.

Do **not** broaden campaigns or rerun all historical data until the P0/P1 fixes
below are in place.

## Evidence from the live system

### Recent campaigns

| Campaign | Result |
|---|---|
| Austin Real Estate (`40`) | 5 discovered, 5 saved, **0 audited**, 0 qualified; all 5 ended `rejected_no_website`. |
| Austin Restaurant (`38`) | 5 discovered, 5 saved, **0 audited**, 0 qualified; all 5 ended `rejected_no_website`. |
| Melbourne Restaurant (`35`) | 5 discovered, 5 saved, **0 audited**, 0 qualified; all 5 ended `rejected_no_website`. |
| Portland Roofing QA (`42`) | 5 discovered, 5 audited, 4 qualified—but some official website URLs are actually third-party directories. |
| Seattle Roofing QA (`39`) | 5 discovered, 5 audited, 5 qualified—but multiple stored owner records are unrelated or malformed. |

### Confirmed provider states

| Provider | State | Impact |
|---|---|---|
| Serper Places | Working | Discovery succeeds, but business records often lack official websites. |
| Serper Google Search | Working | Can find public owner evidence, but parser/matching is unsafe. |
| Apollo | **401 invalid API key** in recent worker logs | No Apollo names, titles, work emails, or phones. |
| Hunter | **429 rate-limited** | No email enrichment beyond public website data. |
| Gemini | Produces AI records for successful audits | Not the primary current blocker. |

## Root causes

### P0 — Incorrect official-website selection

**Files:** `apps/api/providers/serper_discovery_provider.py`, `apps/api/worker.py`

Serper Places frequently returns no `website`. The organic fallback returns the
first non-blocklisted result, which is not proof it is the business’s official
domain. The current blocklist misses directories such as MapQuest,
ServiceAgent, BBB, FMCSA, directory sites, marketplace pages, and many others.

Observed examples saved as business websites:

- `mapquest.com/...`
- `serviceagent.ai/directory/...`
- `safer.fmcsa.dot.gov/...`
- an official email/phone belonging to the directory itself

**Required fix:**

1. Create `is_official_business_website(candidate_url, business, place)`.
2. Reject known directory/marketplace/aggregator/government/social domains.
3. Reject any candidate whose fetched page title, canonical URL, JSON-LD
   `LocalBusiness`/`Organization` name, or visible header does not match the
   discovered business name with a conservative normalized similarity threshold.
4. Require at least two corroborating signals before accepting organic-search
   fallback: business-name match + address/phone/domain identity/structured data.
5. Store rejected candidate URLs as discovery evidence, not `business.website_url`.
6. Set a separate status `needs_official_website` instead of pretending the
   business has no website or qualifying a directory page.

**Acceptance:** no URL from MapQuest, ServiceAgent, BBB, FMCSA, Yelp, Facebook,
Google Maps, social, or a directory may enter `business.website_url`.

### P0 — Public-owner search produces false decision makers

**Files:** `apps/api/providers/serper_search_provider.py`,
`apps/api/worker.py`

The current parser extracts any name/role-looking phrase in the Google result
and does not verify the result belongs to the target business. It also accepts
poor person names and non-decision-maker titles.

Observed bad records include:

- `operated since` stored as an owner
- unrelated people from a similar-name business
- “Flow Roofing” stored as a person
- unrelated LinkedIn profiles returned for broad owner searches

**Required fix:**

1. Treat Serper results as **candidates**, never immediate CRM contacts.
2. Enforce a strict person validator:
   - exactly 2–4 proper-name tokens;
   - reject stopwords (`operated`, `since`, `details`, `company`, `roofing`,
     `service`, `contact`, etc.);
   - reject business name tokens as person names;
   - require an allowed decision-maker title.
3. Enforce business binding before saving:
   - result URL host equals official business domain; **or**
   - result title/snippet includes normalized business name and city; **or**
   - LinkedIn title includes normalized business name.
4. Search with the verified official domain once available, for example:
   - `site:official-domain.com (owner OR founder OR president OR CEO)`
   - `site:linkedin.com/in "Exact Business Name" "City"`
5. Save only one best `owner/founder/CEO/president` candidate by default; show
   additional people only if independently verified.
6. Persist source URL and exact search snippet as evidence. Set source to
   `serper_public_evidence`, confidence no higher than 0.75.
7. Add a quarantine/`needs_review` status for search-only people that fail a
   second corroboration check.

**Acceptance:** a lead must never show a public owner unless its record has a
valid full name, allowed role, source URL, and business-binding evidence.

### P0 — Unsafe qualification gate

**File:** `apps/api/worker.py`

The worker can qualify a business using a public/general email and company phone
even where the “website” is a directory. It also has a Gemini fallback that
creates a medium-confidence generic diagnosis if Gemini is unavailable. That
means a provider failure can still produce an apparently qualified lead.

**Required fix:**

1. Require a verified **official website** before running scoring/qualification
   for website-service offers.
2. Do not qualify a lead when the website source is a directory or the official
   site is unverified.
3. When Gemini fails, retain `needs_research` and surface the provider failure;
   do not create a generic medium-confidence diagnosis that can pass the gate.
4. Require evidence-backed `primary_problem`, `recommended_offer`, and
   `outreach_angle` before CRM stage becomes `qualified`.
5. Company email + business phone are valid for outreach, but must be labeled
   `Website contact`; they must not satisfy the named-owner requirement.

### P1 — Campaign lifecycle reports success when target is not met

**File:** `apps/api/worker.py`

Campaigns currently end `completed` even if they produce zero qualified leads.
This is why the UI can say “done” despite there being no detailed lead output.

**Required fix:**

1. Track `discovered`, `official_website_verified`, `audited`, `needs_review`,
   `rejected`, `qualified`, and `target_quantity` separately.
2. Use campaign status:
   - `completed` only if qualified >= target;
   - `completed_partial` if no retryable candidates remain but target is unmet;
   - `needs_review` if candidates need verification;
   - `failed` for system/provider failures;
   - `processing` while work remains.
3. In the UI, show the reason behind each shortfall, such as “5 discovered;
   5 missing official websites; 0 qualified”.

### P1 — External enrichment accounts are failing

**Files:** `apps/api/providers/apollo_provider.py`,
`apps/api/providers/hunter_provider.py`, runtime `.env`

- Recent worker logs: Apollo `401 Invalid API key`.
- Recent worker logs: Hunter `429` rate-limited.

**Required fix:**

1. Add startup/health checks that store provider state without exposing secrets:
   `healthy`, `invalid_key`, `insufficient_scope`, `rate_limited`, `quota_exhausted`.
2. On Apollo 401, disable calls for the cooldown window and surface “Apollo
   key invalid” in Campaign/Settings; do not repeat it for every lead.
3. On Hunter 429, obey `Retry-After`, mark it rate-limited, and use public web
   contacts only until reset.
4. Never hard-code provider keys in source. The current Serper discovery
   provider includes a default key fallback; remove that and rotate the key
   because it has appeared in the repository and prior chat.

### P2 — Noisy historical data / duplicate enrichment

Historical CRM data contains wrong directory websites and false owner records.
Several business records also have excessive decision makers due to repeated
search runs.

**Required fix:**

1. Do not silently delete data. Add an admin-only **Revalidate/Quarantine**
   job that flags:
   - known directory websites;
   - source `serper_google_search` contacts failing new validation;
   - contacts without business-binding evidence.
2. Move flagged records out of the active CRM view into `needs_review`.
3. Add a unique key/deduplication rule on business + normalized person name +
   title + source URL (or update existing record).
4. Re-run only clean, approved candidates after the fixes.

## Correct target architecture

```text
Serper Places
  -> verify official website (name + address/phone/schema signals)
  -> crawl official site
  -> extract company email/phone/social
  -> extract named team/owner from website + JSON-LD
  -> only if no named person: Serper evidence search with business binding
  -> Apollo/Hunter when healthy (optional enrichment, never required for truth)
  -> audit + AI diagnosis only from official-site evidence
  -> quality gate
  -> qualified CRM lead
```

## Verification test matrix

Before allowing production campaigns:

1. A business with an official website is accepted and audited.
2. A Serper result pointing to MapQuest/ServiceAgent/BBB/FMCSA is rejected as
   an official website.
3. A company general inbox is labeled `Website contact`, not Owner.
4. A public owner found on the company website is saved with evidence URL.
5. An unrelated LinkedIn search result is rejected.
6. An Apollo invalid key or Hunter rate limit leaves the campaign in a truthful
   state without a fabricated person or generic diagnosis.
7. A campaign with 0 qualified leads ends `completed_partial`/`needs_review`,
   not `completed`.
8. The CRM list only exposes qualified, official-site-verified leads by default;
   review candidates are available only via an explicit filter.

## Suggested implementation order

1. P0 official-website verifier.
2. P0 rewrite Serper owner parser and add evidence validation.
3. P0 strengthen qualification gate and remove generic auto-qualification.
4. P1 truthful campaign lifecycle/status metrics.
5. P1 provider health/cooldown state.
6. P2 quarantine/revalidate historical data.
7. Run a small five-lead test campaign, inspect every lead manually, then scale.

## Apollo multi-account handoff (2026-08-28)

Three Apollo accounts are now registered in `provider_accounts` and their
credentials are supplied only through the ignored local file
`apps/api/.env.local`. Before enabling Apollo enrichment in production, fix:

1. In `apps/api/providers/apollo_provider.py`, return
   `account.api_key_ref`, not `account.api_key`. The ORM model has no
   `api_key` property, so the current pool raises an attribute error before
   making an Apollo request.
2. Implement actual round-robin selection. The current `.first()` query always
   chooses the first active account. Order by least-recently-used
   `last_request_at` (with a deterministic tie-breaker), then update it after
   each request.
3. Set and enforce the real per-account daily quota. Seeded records currently
   have no `limit_per_day`, so the exhaustion rule never advances to another
   account.
4. On a `401`/`403`, mark only the failing account unavailable and continue
   with the next active one where appropriate; do not mark all accounts failed.
5. Keep API credentials out of source and `.env.example`; the seed helper must
   read the three local environment variables and never contain key values.
6. Add an integration test using mocked Apollo responses proving first-account
   use, rate-limit fallback, auth-error fallback, and no-key behaviour.
