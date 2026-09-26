# Campaign target delivery

`target_quantity` is the requested number of qualified CRM leads. Stage completion and target delivery are separate concepts: a run may finish every stage while still missing its target.

## Execution flow

1. Discovery requests a reserve candidate pool of up to twice the remaining target (bounded at 1,000 candidates for a maximum 500-lead campaign).
2. Account-scoped deduplication removes businesses already present for that account.
3. Candidates are researched and scored until the qualified total reaches the target.
4. Unused reserve candidates are removed before totals are reported.
5. The worker reads the persisted qualified count and sets:
   - `completed` when the target is reached.
   - `completed_partial` when processing finishes below target.
6. A partial campaign can be resumed. The worker keeps existing qualified leads, searches for only the missing quantity, and never repeats stored businesses.

## Staging behavior

Staging creates deterministic mock businesses and performs no paid discovery or contact-provider calls. Re-running an older partial staging campaign adds only the missing leads. Targets from 1 through 500 therefore finish with the exact requested number of discovered and qualified records.

## Monitor behavior

The Job Monitor reports stage execution and lead yield separately. A discovery shortfall is amber, shows the missing count, and offers **Continue for N leads** to Admin and Member users. Viewer access remains read-only.

Provider inventory can still be exhausted in production. In that case the run remains `completed_partial` instead of claiming success, and can be resumed after changing locations, provider availability, or discovery inventory.
