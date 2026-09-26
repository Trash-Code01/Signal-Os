# Lead data quality controls

## Runtime boundary

- Staging creates synthetic workflow records and never calls paid discovery or contact providers.
- Synthetic websites use the reserved `.invalid` domain and contain no email, phone, or person records.
- Production uses live discovery. Campaign and export responses include `data_mode` so test records cannot be mistaken for researched leads.

## Geography

- A country and at least one city are required. State or province is optional and has no default.
- The campaign location is authoritative. Provider-specific address formatting cannot replace Delhi with Dallas or add Texas to an India campaign.
- A campaign without a saved city fails instead of silently searching Dallas.

## Business and website evidence

- Google Business Profile results are the primary business source.
- Directory and social domains are rejected as official websites.
- Organic website fallback requires a business-name match in the hostname and search evidence.
- The crawler follows redirects, stores the final public URL, and rejects redirects to directory or social domains.

## Contact evidence

- Business-listing phone and website-observed phone are separate fields.
- Website contacts are stored only when observed in page text, `mailto:` / `tel:` links, or structured data.
- Emails are syntax checked and image-like false matches are rejected.
- Phones are checked against the campaign country. An explicit US `+1` number is rejected for an India campaign, for example.
- Personal email and direct-phone providers run only when their campaign toggles are enabled.
- Exports include data mode, contact source, verification state, and evidence URL.

## Delivery behavior

- The requested qualified-lead count is preserved from the form through the API and worker.
- Duplicates are rejected account-wide by source id, website domain, phone, and normalized business identity.
- A live campaign is complete only when it reaches the requested number of qualified leads. Source exhaustion is reported as a partial result with a visible shortfall.

