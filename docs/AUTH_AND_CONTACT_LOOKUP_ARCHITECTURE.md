# Google auth, per-account data and contact lookup architecture

## Verified code paths
- Next.js 15.3.9 (`apps/web`); browser requests use `/api`, rewritten to FastAPI.
- FastAPI `main.py` owns campaign, CRM, export and maintenance routes.
- `worker.py` queues/runs Celery jobs; PostgreSQL and Redis are used outside staging.
- SQLAlchemy `core/models.py` stores campaigns and business-related records.
- `process_campaign_task` runs discovery, website crawl, scoring, contact lookup and Groq analysis.
- The website crawler extracts public contacts without an enrichment API.
- Snov.io `find_emails` requests personal work emails. Serper contact search originally returned only names/roles/links. The new optional path extracts email and explicitly labeled direct/mobile phone details from the same source snippet, marked needs_review. Proxycurl's current `get_executives` returns names/titles/LinkedIn, not phone numbers.
- Existing password auth protected neither all API routes nor account data. Existing staging launch scripts were malformed; mock discovery alone did not prevent downstream paid requests.

## Implementation contract
- Google Identity Services ID tokens are verified server-side; only invited accounts or the configured initial admin can join. Google subject IDs bind identities.
- Admin manages users/roles. Admin, Member and Viewer all see only their own business data. Viewer cannot mutate business data.
- Each domain record carries `owner_id`. ORM filtering covers selects, aggregates, updates and deletes; inserts are stamped server-side. Background jobs recover their owner from the trusted stored campaign/lead record.
- Existing rows with no owner remain hidden. Never assign them to whoever signs in first. Production migration/assignment needs an explicit data owner before deployment.
- Personal-email and phone-research options default off, persist per user and per campaign, and gate requests before contacting providers. Public website/company contacts remain available.
- Campaign option updates apply at the next contact lookup boundary, not to a request already sent. No promise of guaranteed mobile-number enrichment is made: the current provider implementation does not support it.
- Staging uses a separate local SQLite file, in-process mock jobs and no paid-provider requests. Production credentials/database are not used.

## Role and action matrix

| Action | Admin | Member | Viewer |
|---|---:|---:|---:|
| View own campaigns, leads and exports | Yes | Yes | Yes |
| Create campaigns and edit own leads | Yes | Yes | No |
| Run optional email/phone research | Yes | Yes | No |
| Change personal lookup defaults | Yes | Yes | Yes |
| Invite, disable or change user roles | Yes | No | No |
| Read another account's business data | No | No | No |

Admin is an account-management role; it does not bypass ownership filters for campaigns, leads, contacts or exports.

## Trust boundaries

- The browser obtains a Google credential with a nonce created by the Next.js BFF. The nonce is stored in an HttpOnly, same-site cookie and must match the verified Google token claim.
- FastAPI verifies Google audience, issuer, verified email, subject binding, invitation status and account activity before issuing its own short-lived JWT. `session_version` revokes old JWTs after logout, role changes or disabling an account.
- Cookie-authenticated writes require an exact allowed `Origin`; bearer tokens are intended for controlled API clients. Password-era tokens without the current session-version claim are rejected.
- Every ORM query, aggregate and bulk mutation involving `OwnedRecord` receives an owner criterion. New child records inherit the authenticated owner and a cross-owner `owner_id` is rejected. Request code must not use raw SQL for business data. System migrations and workers may bypass filters only long enough to load a stored job, then restore its persisted owner.
- Staging mode is decided once during boot. SQLite without an explicit environment fails closed to staging, which forces the staging database, mock discovery, eager in-memory jobs and empty paid-provider credentials.

## Legacy ownership rollout

1. Back up PostgreSQL and record the current Alembic revision. Stop API and worker writes.
2. Run `alembic upgrade 20260919_google_auth_tenancy`. This only adds nullable ownership columns and account fields; it never assigns legacy data.
3. In a read-only dry run, count `owner_id IS NULL` for every owned table and build a graph assignment from each campaign/business root through all child rows. Reject ambiguous or orphaned graphs.
4. In one transaction per intended account, assign the same verified `users.id` to the root and every related campaign, location, job, website, contact, score, opportunity, CRM activity and export. Never assign all legacy rows to the first login.
5. Before commit, verify each graph has one distinct non-null owner, child owners match their parent, and the pre/post row totals are identical. After commit, sign in as two test accounts and repeat list, detail, export, update and delete isolation checks.
6. If verification fails, roll back the open assignment transaction. After a committed rollout, restore the backup or apply the saved inverse assignment map. Use Alembic downgrade only to remove the schema after the data rollback and application rollback are complete.

## Sources consulted
- Google token verification: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- Google JS API and nonce: https://developers.google.com/identity/gsi/web/reference/js-reference
- Next route handlers: https://nextjs.org/docs/app/api-reference/file-conventions/route
- Bundled Next documentation requested by AGENTS.md is absent from this installation; official documentation was used as fallback.

Serena was requested but unavailable in installed tools and plugin search. Inspection used the repository itself; validation must exercise cross-account access, permissions and provider-call counts.
