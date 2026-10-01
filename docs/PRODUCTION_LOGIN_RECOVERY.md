# Production login recovery — 2026-09-27

## Confirmed failure

The Render backend deployment exits with status 3 during application startup.
Its log reports `sqlalchemy.exc.OperationalError` / `psycopg.OperationalError`:
`failed to resolve host`, followed by `Application startup failed. Exiting.`
The frontend `/api/ping` also reports a backend timeout. The production frontend
already serves `Cross-Origin-Opener-Policy: same-origin-allow-popups` and the
Google client ID matches the supplied Google Cloud configuration. The Google
callback reaches the application's authentication request; the backend outage
prevents it from completing.

The database was reported active and in the same region. A stale or mismatched
`DATABASE_URL` is the next configuration check, not a confirmed explanation for
why DNS resolution failed.

## Restore the database connection

1. Open the active PostgreSQL database in Render. Confirm it and
   `devacia-backend` belong to the same workspace/account and region.
2. Copy that database's **Internal Database URL** from **Connect**. Compare its
   hostname to the failing deployment log. Do not paste the URL into chat,
   source files, or Git; it contains credentials.
3. In **devacia-backend → Environment**, set `DATABASE_URL` to the current URL,
   then save and redeploy. For a Blueprint-managed service, verify its database
   reference points to this active database. `render.yaml` already uses a
   `fromDatabase` reference to `devacia-db`.
4. If the current URL's hostname still fails to resolve from the service, check
   workspace/network isolation and Render service status/support. Do not guess
   an alternate hostname, replace the database, or discard existing data.
5. Confirm the backend logs `Application startup complete`, the deployment is
   live, and `https://devacia-backend.onrender.com/api/health` returns HTTP 200.
6. Confirm `https://devacia-frontend.onrender.com/api/ping` reports `ok: true`,
   then complete a real Google sign-in and check that `/api/auth/me` loads the
   intended account. Real Google sign-in requires the account owner.

Render's internal connection requirements:
https://render.com/docs/postgresql-creating-connecting

## Code safeguards in this change

- Stop launching Alembic concurrently with the API's existing additive startup
  migrations. A separate operator-run Alembic upgrade must finish with writers
  stopped before starting the API; this startup change does not stamp revision
  history or remove data.
- Bound PostgreSQL connection attempts and Google certificate HTTP requests.
- Set a backend health check so readiness requires a responding API.
- Fetch Google configuration from the reachable backend instead of masking an
  outage with a hardcoded client ID and apparently ready button.
- Bound frontend requests, expose retryable errors, and clear loading states.
- Validate upstream session tokens before setting cookies; retain nonce and
  origin checks, including origin validation for password login.

These safeguards do not repair an invalid production `DATABASE_URL`. Deploy
the backend and frontend changes after correcting the environment connection.

## Local validation

- `npm run test:auth` in `apps/web`: actual Next.js auth handlers with mocked
  upstream responses, nonce/origin rejection, session cookies, outage responses,
  and stalled connection/body deadlines.
- `node node_modules/typescript/bin/tsc --noEmit --incremental false`, targeted
  ESLint, and `npm run build` in `apps/web`.
- Existing backend auth/account and additive migration tests using isolated
  SQLite test databases. These do not verify Render's PostgreSQL DNS.
