# Pipeline QA — 2026-10-08

Local changes verified. New live discovery is **blocked by exhausted Serper credits**. Snov contact enrichment is also blocked by exhausted credits. This is not a production deployment or a claim that every external API is operational.

## Results

| Check | Result |
| --- | --- |
| Backend regression suite | 90 passed; four dependency deprecation warnings |
| Frontend auth and discovery tests | 11 passed |
| Production frontend build | Passed compilation, TypeScript validation, and page generation; build configuration skips ESLint |
| Desktop and mobile browser workflow | Passed campaign submission, channel selection, zero score threshold, website filters, pagination, selection, viewport overflow, and runtime-error checks |
| Synthetic HTTP campaign workflow | Passed create, completion, CRM delivery, resume, contact options, trash, recovery, and permanent deletion |
| CRM API workflow | Passed creation, nullable owner update, bulk selection, activities, CSV/TSV/JSON export, import, deletion, and recovery |
| Live existing-lead research | Completed; one qualified lead scored 80/100, 14 crawled pages, one contact, one score, and one visible AI analysis saved |
| Live Groq | Model endpoint and actual analysis/email generation succeeded; email draft source was `groq` |
| Live six-channel discovery | All six channels failed with Serper HTTP 400, exhausted credits; zero new leads, no synthetic substitution |
| Live Snov | OAuth succeeded; actual domain email search returned HTTP 400, exhausted credits; zero contacts from Snov |

The live research test copied the already-known public business NEPA Wholesale into a separate QA database, then resumed the real worker through the HTTP API. It verifies crawling, scoring, enrichment from the website, AI analysis, persistence, and export. It does **not** count as newly discovering a business without a website. One earlier website could not be crawled and was correctly rejected.

The six-channel test selected Google Maps, Google Search, directories, Facebook, Instagram, and LinkedIn for one no-website lead in Pune. These channels currently depend on Serper, including indexed public social results. Channel-specific credit failures are preserved in campaign status.

## Bugs fixed

- Bulk CRM updates referenced a missing helper and returned a server error.
- Clearing a lead's owner with `null` returned a server error.
- CSV and TSV exports streamed from the end of the buffer and returned empty files. Exports now retain listing phone numbers, website status, and source links.
- Malformed JSON import rows returned server errors; invalid row shapes now return HTTP 400. Non-finite imported scores no longer crash parsing.
- Explicit live staging disabled Groq, and provider status misreported live requests as mock or assumed configured credentials were healthy.
- Serper and Snov HTTP 400 credit failures were classified as generic outages. They now show exhausted credits and required action.
- Optional contact-provider exceptions could abort the campaign. Other contact results now survive, with bounded provider request timeouts.
- Failed campaigns lost channel diagnostics. Failure reasons now remain available through status, and failed discovery is marked failed.
- The dashboard fabricated chart values, used account-wide totals for individual campaign progress, and counted discarded/review-only data as qualified. Counts now come from active qualified records and actual opportunity dates.
- A CRM status update flushed pending AI analysis while ownership stamping was disabled, leaving the analysis invisible to its account. Pending research now receives ownership before that operation. Regression and live tests verify visibility.

## Reproduce automated checks

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH='apps/api'
$env:ENVIRONMENT='staging'
$env:DISCOVERY_MODE='mock'
& apps/api/venv312/Scripts/python.exe -m pytest apps/api/tests -q -p no:cacheprovider
```

From `apps/web`:

```powershell
node --test tests/auth.test.cjs tests/discovery.test.cjs
npm run build
```

HTTP regression cases are in `apps/api/tests/test_api_workflows.py`. Local live-run reports and browser screenshots are in ignored `.staging-logs/qa-live-pipeline.json`, `.staging-logs/qa-live-discovery.json`, and `.staging-logs/discovery-*.png`. Credentials are not included in these reports. Live QA used isolated SQLite databases, not production records.

## Remaining verification

1. Replenish Serper and rerun the no-website campaign to verify new real lead delivery, source evidence, ranking, selection, and export.
2. Replenish Snov to verify successful optional personal-work-email discovery. Public website contacts already worked independently.
3. Production deployment, its Redis/Celery transport, interactive Google OAuth, and unused Hunter/Proxycurl integrations were not live-tested. Local HTTP tests, worker execution, and frontend browser checks do not certify those external systems.

The existing frontend `authRequest.ts` change was preserved. No outreach was sent and no production data was modified.
