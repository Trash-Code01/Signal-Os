# Public Decision-Maker Research — Antigravity Handoff

## Objective

When Apollo People API access is unavailable, enrich qualified CRM leads using
only public information from the company website and web-search results.

The CRM should display real, evidence-backed public decision makers:

- owner/founder/CEO/president/partner/director name
- publicly stated role/title
- public LinkedIn profile URL when the company website or a search result
  directly identifies it
- publicly listed email or phone only when attached to that person or clearly
  published by the company
- public company Facebook, Instagram, LinkedIn, YouTube, TikTok, and X links
- source and confidence for each fact

Never generate names, titles, email addresses, phone numbers, or LinkedIn
profiles. A generic address such as `info@company.com` is a **website contact**,
not an owner.

## Why this fallback is required

The configured Apollo Free plan currently returns `403 API_INACCESSIBLE` for
People Search. Apollo enrichment should remain enabled for accounts with paid
API access, but public-web research must work independently of Apollo.

## Existing assets

- `apps/api/engines/website_intelligence.py`
  - Playwright crawler already visits homepage, contact, booking, about, and
    service pages.
  - Captures page text, email/tel links, and public company social links.
  - A draft `public_people` extractor has been started but is unbuilt and
    undeployed; review/refine it rather than treating it as complete.
- `apps/api/core/models.py`
  - `DecisionMaker` already stores name, title, email, phone, mobile,
    LinkedIn URL, source, and confidence.
  - `SocialProfile` stores company social links.
- `apps/api/.env`
  - `BRAVE_SEARCH_API_KEY` is configured.
- `apps/api/providers/apollo_provider.py`
  - Keep Apollo as the premium enrichment source. Do not remove it.
- `apps/web/src/app/leads/page.tsx`
  - Already has a multi-contact Decision makers section and Social media
    section in the dossier.

## Implementation plan

### 1. Define contact classes and evidence

Use these values consistently:

| Contact type | Definition | Example source | Can be called owner? |
|---|---|---|---|
| `professional` | Named person holding a leadership role | Team page / Apollo / public LinkedIn result | Yes, when title is owner/founder/etc. |
| `company` | General business mailbox or business phone | Website footer / contact page | No |
| `personal` | Person-specific contact detail published publicly | Team card or person-owned profile | Only with evidence |

Use sources such as `website_public`, `brave_search`, `apollo`,
`hunter`, and `website_crawl`. Add a short activity record showing the
number and kind of public records found.

### 2. Website extraction

Extend `WebsiteIntelligenceEngine` to extract named decision makers from every
already-crawled page. Prefer, in order:

1. JSON-LD `Person` objects with `name`, `jobTitle`, `email`, `telephone`, and
   `sameAs` (for LinkedIn).
2. Team/About/Leadership card markup containing a name and leadership title.
3. Text explicitly formatted as `Jane Doe — Owner` or `Founder: Jane Doe`.
4. LinkedIn `/in/` links only if their nearby page text explicitly identifies
   the linked person and leadership role.

Accept only roles matching a conservative allow-list:

`owner`, `co-owner`, `founder`, `co-founder`, `CEO`, `chief executive`,
`president`, `principal`, `partner`, `managing director`, `director`,
`general manager`.

Reject ambiguous phrases, employee lists without a role, and generic words such
as “our owner” that are not paired with a full name.

Return each result with `source_url` and confidence. Do not put source URLs into
the current `DecisionMaker.source` field because it is a short provider label;
either add a compact evidence record or extend the model/API with a dedicated
provenance field.

### 3. Web-search fallback

Create `apps/api/providers/brave_search_provider.py` implementing the existing
`SearchProvider` contract.

Use the official Brave Web Search endpoint:

`GET https://api.search.brave.com/res/v1/web/search`

with header `X-Subscription-Token: $BRAVE_SEARCH_API_KEY`.

Run no more than two targeted searches per business, only if the website did not
produce a named decision maker:

```text
"{business name}" "{city}" (owner OR founder OR CEO OR president)
site:linkedin.com/in "{business name}" (owner OR founder OR CEO OR president)
```

Parse a result only if its title/description explicitly couples a plausible full
name with an allowed leadership role and references the business. Preserve the
result URL as evidence. A LinkedIn URL is valid only from a `linkedin.com/in/`
result that passes this check.

Do not scrape behind login pages, bypass rate limits, or infer contact details
from email patterns.

### 4. Persistence and deduplication

Update `_save_contact` in `apps/api/worker.py` so a named decision maker with a
public leadership role can be saved even when they have no email or phone. The
current function rejects any contact without email/phone, which hides exactly
the names this fallback can find.

Deduplicate in this order:

1. Same business + email
2. Same business + LinkedIn URL
3. Same business + normalized full name + title
4. Same business + direct phone

When a later source adds an email, phone, or LinkedIn URL, merge it into the
existing person record instead of adding a duplicate card.

### 5. Worker flow

In `enrich_lead_contacts_task`:

1. Crawl the website.
2. Save social profiles.
3. Save website-public decision makers.
4. If no named professional decision maker exists, use Brave Search fallback.
5. Attempt Apollo separately. A `403` must not stop public-web enrichment.
6. Save a CRM activity summarizing public-web, Brave, and Apollo counts.

In `process_campaign_task`, run public-web research before final qualification.
The existing real website email and company phone can still satisfy the basic
contactability gate, while a named decision maker increases usefulness.

### 6. UI/API requirements

- API lead detail must return every contact’s `source`, `confidence`, and
  provenance/evidence URL.
- The owner section should select a named professional contact first.
- Generic company inboxes must render as `Website contact`, never `Owner`.
- Decision maker cards should show name, role, source, email, phone, and
  LinkedIn only when those fields were actually returned.
- Social media links are company links, visibly separate from personal LinkedIn.
- Add a visible result/status when **Enrich with Apollo** runs; label the action
  more generally as **Refresh contact research** if it now invokes multiple
  sources.

### 7. Verification

Use a qualified existing lead such as `Georgia TLC Events` (business ID `131`).

1. Run the enrichment task.
2. Confirm social links still appear.
3. Inspect the `decision_makers` records and `GET /api/crm/leads/131`.
4. Confirm no generic website email is presented as the owner.
5. If a public owner is found, confirm a source/evidence URL is available.
6. Test an intentionally contactless/unrelated website result to ensure no
   guessed person is saved.
7. Run `python -m compileall apps/api` and `npm run build` in `apps/web`.
8. Rebuild the local services:

```powershell
docker compose -f docker-compose.prod.yml up -d --build --force-recreate api worker web
```

## Acceptance criteria

- A lead detail panel can display a real public owner/decision maker without
  Apollo API access when the information exists on the website or reliable
  search result.
- The CRM never fakes owner information.
- The API preserves source/provenance and confidence.
- Apollo remains available as a higher-quality enrichment source when the
  account is upgraded.
