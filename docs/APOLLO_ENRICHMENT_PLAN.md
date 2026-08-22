# Apollo Decision-Maker Enrichment Plan

## Goal

Every qualified CRM lead should show provider-backed contact information rather
than a generic website inbox being presented as an owner:

- decision-maker name and job title
- work email and, where Apollo returns it, personal email
- direct/mobile phone where Apollo reveals it
- personal LinkedIn URL
- public company social profile links

## Current implementation status

1. **Apollo provider flow — implemented, needs live verification**
   - Search owner, founder, CEO, and president roles with Apollo People Search.
   - Pass the returned Apollo person IDs into Bulk People Enrichment.
   - Store every returned person as a separate `decision_makers` record with
     name, title, email, phone/mobile, LinkedIn URL, source, and confidence.
   - Apollo People Search alone does not return contact email/phone fields;
     bulk enrichment is intentional and required.

2. **CRM detail UI — implemented**
   - The owner block prefers a named professional contact.
   - A new **Decision makers & contact data** section lists every contact,
     including the data source and click-to-email/call/LinkedIn actions.
   - The panel has an **Enrich with Apollo** action for an existing lead.

3. **Company social profiles — implemented**
   - Website crawling captures public Facebook, Instagram, LinkedIn, X,
     YouTube, and TikTok links.
   - The lead dossier displays these under **Social media**.

4. **Phone/webhook delivery — implemented, requires public deployment**
   - Apollo phone/mobile reveal is asynchronous.
   - `POST /api/webhooks/apollo` stores callback data against the relevant
     business using a secret token.

## Required configuration

Add the following to `apps/api/.env` for the API and worker containers. Never
commit real credentials.

```dotenv
APOLLO_API_KEY=...
APOLLO_REVEAL_PERSONAL_EMAILS=false
APOLLO_REVEAL_PHONE=false
APOLLO_WEBHOOK_URL=https://your-public-api.example.com/api/webhooks/apollo
APOLLO_WEBHOOK_SECRET=use_a_long_random_value
```

Start with both reveal flags set to `false`. This still retrieves the standard
Apollo enrichment data the account permits. Enable `APOLLO_REVEAL_PERSONAL_EMAILS`
only after confirming the Apollo plan/credits allow it. Enable
`APOLLO_REVEAL_PHONE` only when the API is publicly reachable over HTTPS;
localhost cannot receive Apollo callbacks.

## Resume checklist

1. Start Docker Desktop.
2. Rebuild the services:

   ```powershell
   docker compose -f docker-compose.prod.yml up -d --build --force-recreate api worker web
   ```

3. Confirm Apollo authentication without printing the key:

   ```powershell
   docker compose -f docker-compose.prod.yml exec -T api python -c "import os,http.client; c=http.client.HTTPSConnection('api.apollo.io',timeout=15); c.request('GET','/api/v1/auth/health',headers={'x-api-key':os.environ['APOLLO_API_KEY']}); print(c.getresponse().status)"
   ```

   `200` means the key is valid. It does not by itself prove that the key has
   the People Search and Bulk People Enrichment scopes.

4. In the CRM, open a qualified lead and choose **Enrich with Apollo**.
5. Wait for the worker to finish, refresh the dossier, and verify that rows
   with source `apollo` include actual returned person data.
6. If Apollo returns `403`, check the key's API scopes/plan for:
   - `mixed_people_api_search`
   - `people_bulk_match`
   - optional personal-email/mobile reveal capability

## Verification requirements

Do not call a generic website email an owner. A person is shown as an owner or
decision-maker only when Apollo/Hunter returns a name and/or title. Do not
invent an email, phone number, LinkedIn profile, social profile, or title.

## Remaining live-test blocker at last check

Docker Desktop was stopped on 2026-08-20, so the API/worker could not perform
the final live Apollo test. The key had previously returned HTTP 200 from
Apollo's health endpoint, so the next check is whether it has the required
People Search and Bulk People Enrichment scopes.
