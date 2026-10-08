# Business discovery and qualification

Campaigns select geography, industry/specialty, website presence, public discovery channels, a lead target, and a minimum score. Optional personal contact lookups retain the account's existing switches. Older campaigns default to Google Maps and all website states.

## Pipeline

1. `MultiChannelDiscoveryProvider` distributes a bounded candidate budget across the selected Google Maps, Google Search, directory, Facebook, Instagram, and LinkedIn channels. All use the configured Serper API. Social channels cover publicly indexed company pages; they are not direct platform integrations or exhaustive platform searches.
2. Adapters normalize business candidates and retain source URLs. Search candidates require city evidence in the title/snippet. Duplicate identities merge their sources and observed contact/website information. Candidate priority uses public phone, website opportunity, review count and rating before expensive research.
3. Website presence has three states: `has_website`, `no_website` (no official match found after a successful follow-up search), and `unknown` (not checked or lookup failed). A negative search is evidence, not proof that a business has no website. Unknown leads cannot qualify as no-website opportunities.
4. Candidates are filtered to the campaign's selected website group. Existing-site leads pass the crawler and scoring workflow. No-website leads use deterministic business-activity and contact scores. Both enforce the campaign's threshold, including a valid threshold of zero, and require an actionable email/phone. A named person without contact details does not satisfy that gate. Missing websites do not establish buying intent.
5. The worker stores evidence in `WebsiteEvidence`, sources in `BusinessSource`, and options in `Campaign.settings`, so this change needs no database migration. Qualified leads retain their scores. Unused research candidates remain available for a resume; existing qualified leads count toward the target.
6. The CRM sorts by commercial score, data confidence and a stable ID tie-breaker. Users can filter source, website presence and contactability, select leads on the current page, and export either the selection or every page matching the filters.

## Failures and coverage

Live discovery never falls back to mock data. Missing credentials or failure of every selected channel fails the job. Partial channel failures are retained in job metrics and shown in progress. Exhausted or limited public coverage can produce a partially filled target. Search page limits and the reserve pool bound requests; a target is not a guarantee of yield. Existing unknown records need fresh research before they can be treated as no-website opportunities.

Staging remains explicitly synthetic. No-website staging fixtures exercise the filter without claiming any live verification. Real source coverage, identity matching and current provider credits require a separate live campaign; unit tests use controlled responses and do not establish real-world lead accuracy.

## Verification

Backend regression tests cover option validation, missing credentials, partial channel failure, website lookup uncertainty, source merging, thresholds, contact filters, best-first pagination, incorrect duplicate matches, score retention and resumes. Frontend production builds now validate TypeScript instead of ignoring errors. Exports use the existing paginated fetch helper.
