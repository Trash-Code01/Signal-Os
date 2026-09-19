# Staging setup for Google accounts

1. Run `./start-staging.ps1` from the repository root. The frontend uses http://localhost:3001 and the API uses http://127.0.0.1:8000. Stop any existing server on these ports first. Windows may require permission to spawn Next.js processes.
2. Create a Google OAuth **Web application** client and register these authorized JavaScript origins: `http://localhost:3001` and `http://127.0.0.1:3001`. Configure the consent screen/test users in Google Cloud. This Google Identity Services popup integration does not need a client secret or redirect URI.
3. Put `GOOGLE_CLIENT_ID=<web client ID>` and `GOOGLE_ADMIN_EMAIL=<your Gmail or Google Workspace email>` in `apps/api/.env.staging.local` (ignored by Git). Restart the staging API after changes.
4. Sign in with that account. In Settings, grant access to other Google email addresses as Admin, Member or Viewer. Each account has private campaigns/leads/exports; Admin does not get another account's business data. Invitations are stored in the app; no email is sent.
5. Set optional lookup defaults in Settings. Override them when creating a campaign, on its Job Monitor page (including while running), or before refreshing a lead's contacts. Defaults are off. Existing requests cannot be canceled; running campaigns reload settings before the next lead's optional lookup.

Staging creates only `apps/api/staging.db`, uses mock campaigns and cannot call paid contact providers. Local signing keys are generated in `apps/api/.staging-session-key`. Both files are ignored by Git. Redis/PostgreSQL are not required for this staging preview. Production still uses its configured PostgreSQL/Redis.

Personal work-email lookups use Snov.io. Phone research uses Serper snippets explicitly containing direct/mobile contact details and marks them for review; numbers are not guaranteed or independently verified. Public company/website details do not require these toggles. Discovery/AI usage is separate in production.

Before any future production rollout: set a fresh JWT secret (at least 32 random characters), Google client ID, admin email, and exact frontend origin in production. Back up the database, stop writers, run the auth/tenancy Alembic revision, and dry-run graph-wide ownership assignment. Record null-owner counts before and after; assign one verified user to each root and every related child inside a transaction; verify child/parent owners and unchanged row totals before commit. Roll back the transaction on any mismatch and keep the backup plus inverse assignment map until cross-account tests pass. Existing password sessions are invalidated. Global import/truncate/schema-maintenance HTTP endpoints are disabled.

Validation:
- `apps/api/venv312/Scripts/python.exe -m pytest apps/api/tests -q -p no:cacheprovider` with `PYTHONPATH=apps/api`.
- `npx tsc --noEmit --incremental false` in `apps/web`.
- `npm run build` in `apps/web`.
- A real Google login requires configured Google credentials and the account owner to complete sign-in.
