# Campaign pipeline follow-up QA — 2026-10-13

The local Redis/Celery pipeline completed research for an existing public business and delivered one qualified CRM record. New discovery remains blocked by Serper account credits: the latest live Places and Search probes both returned HTTP 400, `Not enough credits`, with zero results. All six discovery channels currently depend on Serper.

## Fixes

- The backend container starts both API and worker. The startup script supervises both processes and exits for restart if either dies; production requires Redis.
- Production dispatch checks for a consumer on `devacia_queue`, bounds broker connections, and reports queue/worker failures instead of launching an untracked fallback thread. Failed dispatch is persisted as a failed, retryable campaign.
- Public NAT64 DNS answers no longer prevent crawling valid public websites. The embedded IPv4 destination is checked against the same restrictions; private and reserved targets remain blocked.
- Failed campaigns expose a retry control. Campaign creation describes the backend's actual discovery mode and provider-credit usage.
- Research retries count each business once in website and AI progress. Terminal status clears the stale “Continuing discovery” message.
- Backend health exposes the Render commit identifier when available so deployment revisions can be verified.

## Evidence

| Check | Result |
| --- | --- |
| Backend regression suite | 107 passed; four existing dependency deprecation warnings |
| Frontend auth and discovery tests | 11 passed |
| Frontend production build | Compilation, type checking and all 19 pages passed; existing build configuration skips lint |
| Startup supervision | Worker exit, API exit and missing production Redis smoke checks passed; Bash syntax passed |
| Real local Redis/Celery research run | Campaign 2 completed; one qualified business, score 80, 14 crawled pages, one contact, one AI analysis and one CRM record |
| Signed-in browser | Completed job shows 1/1 stage counts; CRM shows qualified business, public email and phone |
| Live Serper recheck | Places and Search both HTTP 400, insufficient credits; zero new leads |

The live research campaign is named `QA existing lead - live research continuation`. Its seed is the previously known public business NEPA Wholesale, explicitly marked `qa_existing_lead`. It proves downstream research and CRM delivery, **not successful new discovery or discovery of a business without a website**. The earlier six-channel no-website campaign correctly terminated with provider-credit errors. Testing used an isolated local database and a Redis service bound to localhost.

The automated consumer regression uses a real Celery worker with memory transport and synthetic discovery. This is separate from the local live Redis research run. Contact lookups were disabled for that live run; contacts came from public website research. Snov previously returned exhausted credits for actual domain email lookup; successful optional Snov enrichment remains unverified.

## Remaining checks

1. Replenish the configured Serper account, then retry the no-website campaign and verify new real leads, source evidence, selection and export.
2. Replenish Snov before validating paid personal-email enrichment.
3. Confirm the deployed Render revision and run an authenticated production campaign. Local success and public health alone do not verify production worker delivery.

Reproduction commands are in `docs/qa-pipeline-report.md`. No outreach was sent during these checks.
