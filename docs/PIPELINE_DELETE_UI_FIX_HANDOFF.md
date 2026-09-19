# Pipeline, Trash, and Lead Detail Fix Handoff

Updated: 2026-08-29

## What was fixed in code

1. CRM stage no longer overwrites pipeline status.
   - Before: moving a qualified lead to `contacted`, `proposal`, or `won` changed `Business.status`, then the default lead query hid the lead.
   - Now: `CRMLead.stage` is CRM-only. `Business.status` remains the pipeline/research status.

2. Active Leads now show all active CRM records by default.
   - Before: `/api/crm/leads` defaulted to `qualified_only=true`, hiding `needs_review` and partial pipeline records.
   - Now: the CRM defaults to all active, non-deleted CRM records. Exports can still request `qualified_only=true`.

3. Trash/delete is no longer self-recreating.
   - Before: permanent lead delete removed only `CRMLead`; `_ensure_crm_records()` could recreate it from the still-existing `Business`.
   - Now: soft delete marks both `CRMLead.deleted_at` and `Business.deleted_at`; recover clears both; permanent delete removes the business and dependent records.

4. Campaign permanent delete is FK-safe.
   - Before: deleting only `Campaign` could fail or leave orphaned business/contact rows.
   - Now: campaign hard delete removes related businesses, contacts, website audit data, scores, opportunities, CRM rows, activities, locations, and jobs in dependency order.

5. Existing production DBs self-repair the soft-delete columns at API startup.
   - `campaigns.deleted_at`
   - `businesses.deleted_at`
   - `crm_leads.deleted_at`

6. Campaign status is now truthful.
   - Before: `completed_partial`, `needs_review`, and `failed` were mapped to `completed` for the UI.
   - Now: the API returns actual `status`, `terminal`, `summary`, and counts for `qualified`, `needs_review`, `rejected`, `target`, and enrichment.

7. Job Monitor handles terminal states.
   - It stops polling when `terminal=true`.
   - It shows partial/review/failure states instead of always showing "Pipeline Complete".

8. Trash UI can show deleted review records.
   - Before: trash page forced `qualified_only=true`.
   - Now: trash page asks for all deleted records.

9. Export now includes all contact data.
   - Added all emails, website emails, Apollo emails, all phones, LinkedIn profiles, and primary contact title.

10. Lead detail contact collection was already patched.
   - Website crawl emails/phones are persisted as contact rows.
   - Apollo people with multiple emails expand into multiple CRM contact rows.

## Files changed

- `apps/api/main.py`
- `apps/api/worker.py`
- `apps/api/providers/apollo_provider.py`
- `apps/api/engines/website_intelligence.py`
- `apps/web/src/app/jobs/page.tsx`
- `apps/web/src/app/trash/page.tsx`

## Required deploy steps

1. Rebuild and recreate API and worker containers.
   - The running containers will not pick up these Python changes until recreated.

2. Restart/rebuild web.
   - The frontend build passed locally.

3. Run one small QA campaign.
   - Use 3-5 leads in one city/industry.
   - Confirm campaign status does not say completed unless target qualified count is reached.

4. Re-enrich existing leads.
   - Old leads will not automatically get newly persisted website/Apollo email rows unless enrichment runs again.

5. Revalidate historical junk data.
   - Flag directory websites and false decision makers as `needs_review`.
   - Do not bulk-delete historical data until reviewed.

## Acceptance checklist

1. Create a campaign with target 3.
2. When pipeline finishes, Job Monitor shows one of:
   - `completed`
   - `completed_partial`
   - `needs_review`
   - `failed`
3. Leads page shows active CRM records, including review records.
4. Select one lead, move to Trash, refresh, confirm it disappears from Leads.
5. Open Trash, confirm the deleted lead appears.
6. Recover it, refresh, confirm it returns to Leads.
7. Permanent-delete it, refresh Trash, confirm it stays gone.
8. Click a lead after changing CRM stage to `contacted`; it must still open.
9. Export CSV and confirm:
   - primary contact
   - all emails
   - website emails
   - Apollo emails
   - phones
   - LinkedIn profiles
10. Open a detailed lead page and confirm website crawl contacts and Apollo contacts appear separately.

## Known remaining production risks

1. Apollo personal emails still require account permission/credits and `APOLLO_REVEAL_PERSONAL_EMAILS=true`.
2. Provider keys should be rotated because secrets were pasted into chat.
3. Any secrets still stored in tracked `.env` should be migrated to ignored local or deployment secrets.
4. The official website verifier and Serper decision-maker validator still need the full P0 hardening from `docs/PIPELINE_DIAGNOSIS_AND_ANTIGRAVITY_FIX_PLAN.md`.
