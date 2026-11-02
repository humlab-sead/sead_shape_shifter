# Reconciliation MVP Status Assessment

## Purpose

Record the verified status behind the [Reliable Reconciliation Links to Existing SEAD Entities proposal](RECONCILIATION_MVP.md). Assessment date: 2026-10-30. The intended outcome is to link imported rows to the correct existing tracked SEAD entities, not merely to find a plausible fuzzy-search candidate. The earlier [investigation map](../../investigations/reconciliation-feature-status/findings.md) locates the related records and code paths.

## Current State

**Verdict: not MVP-ready for that outcome.** Reconciliation results and specifications are saved in a reconciliation catalog. Only exported links in the separate mapping sidecar affect normalization. For an entity whose reconciliation field equals its sidecar local key, export writes committed IDs and normalization applies them to `public_id` ([export](../../../backend/app/services/reconciliation/service.py#L217), [normalization](../../../src/normalizer.py#L536)). The change-request ingester treats a populated `public_id` as a reference to an existing entity ([planning](../../../ingesters/sead_change_request/planning.py#L96)).

| Area | Observed status | Limit |
|---|---|---|
| Configuration and candidate search | Implemented | Batch matching and thresholds store results; a candidate is not proof of eligible tracked identity ([reconciliation service](../../../backend/app/services/reconciliation/service.py#L290)). |
| Export and normalization | Verified for equal search/local keys | Export uses `source_value` as the key; normalization looks up `local_key` ([export](../../../backend/app/services/reconciliation/service.py#L237), [normalization](../../../src/normalizer.py#L552)). |
| Review and decisions | Incomplete | The UI's JSON requests do not match the review routes' query-parameter contract ([UI store](../../../frontend/src/stores/reconciliation.ts#L171), [routes](../../../backend/app/api/v1/endpoints/reconciliation.py#L423)). |
| Downstream identity | Partially connected | The ingester has a separate path that promotes an unreviewed best candidate to a SIMS-approved-ID request ([adapter](../../../backend/app/services/ingester_runtime.py#L320), [orchestration](../../../ingesters/sead_change_request/orchestration.py#L131)). |

## Completed Work

- The backend can configure multiple reconciliation specifications, query the OpenRefine-compatible service, save auto-matched results, and export accepted-looking entries to a version-checked sidecar. Manual sidecar links are not overwritten on export ([service](../../../backend/app/services/reconciliation/service.py#L223)).
- Core applies committed sidecar links to `public_id`. The [export-to-normalization test](../../../backend/tests/api/v1/test_reconciliation_export.py#L227) covers the same-key path.
- Fixed-entity row saves and mapping sync have their own implemented follow-up; this assessment does not reopen that work ([mapping-sync status](../done/MATERIALIZED_ENTITY_MAPPING_SYNC/MATERIALIZED_ENTITY_MAPPING_SYNC.md)).

## Risks

1. **Service readiness is not matching readiness.** The assessed local authority service at `127.0.0.1:8024` returned HTTP 200 and 13 advertised types for its manifest, but a real site match returned HTTP 500: its connected database did not have `authority.fuzzy_site`. Shape Shifter's configured URL may differ; its default is port 8000, which did not answer during this assessment ([settings](../../../backend/app/core/config.py#L89), [client](../../../backend/app/clients/reconciliation_client.py#L67)). This is an observed local-environment failure, not a claim about all deployments.
2. **The wrong row can be linked, or no row linked.** Query results are indexed by the chosen field's value, and duplicate labels collapse in the candidate map. Export writes that raw value, while normalization expects the sidecar's ordered `local_key`; a different or compound business key is not translated ([query construction](../../../backend/app/services/reconciliation/service.py#L53), [candidate mapping](../../../backend/app/services/reconciliation/service.py#L422), [export](../../../backend/app/services/reconciliation/service.py#L237)).
3. **Source coverage stops at preview limits.** The target-entity and another-entity source resolvers each request at most 1,000 rows ([resolvers](../../../backend/app/services/reconciliation/resolvers.py#L72)).
4. **Review UI actions fail or mislead.** The running app's OpenAPI schema declares `source_value` as a required query parameter and no body for both manual mapping and mark-unmatched, while the UI sends JSON bodies ([mapping route](../../../backend/app/api/v1/endpoints/reconciliation.py#L423), [mark-unmatched route](../../../backend/app/api/v1/endpoints/reconciliation.py#L520), [grid](../../../frontend/src/components/reconciliation/ReconciliationGrid.vue#L718)). The view discards candidate lists when it reloads preview; confidence stored as 0–1 is displayed as 0–100, and accepting a candidate multiplies its 0–100 score again ([view](../../../frontend/src/components/reconciliation/ReconciliationView.vue#L254), [grid](../../../frontend/src/components/reconciliation/ReconciliationGrid.vue#L400), [candidate acceptance](../../../frontend/src/components/reconciliation/ReconciliationGrid.vue#L619)).
5. **Decisions do not remain authoritative.** Auto-reconcile can replace a manual or local-only catalog decision when a candidate exceeds the threshold ([service](../../../backend/app/services/reconciliation/service.py#L450)). Removing or rejecting a catalog entry does not delete a previously exported reconciliation sidecar link, because export only writes eligible current entries ([export](../../../backend/app/services/reconciliation/service.py#L233)).
6. **Tracked eligibility is unproven.** The authority service's reconciliation endpoint returns fuzzy database candidates and does not check the SIMS tracked-identity policy; a returned numeric URI is insufficient proof. Its available strategy types and SIMS tracked types are not identical. Shape Shifter extracts a trailing numeric ID without checking the expected entity type or eligibility ([ID extraction](../../../backend/app/services/reconciliation/service.py#L197)). The ingester's independent adapter picks the best candidate even when `match` is false, whereas a pre-linked `public_id` skips its reconciliation/binding branch ([adapter](../../../backend/app/services/ingester_runtime.py#L342), [planning](../../../ingesters/sead_change_request/planning.py#L100)).
7. **Concurrent writes have a deployment limit.** Sidecar writes use atomic replacement and content versions, but the shared project lock is process-local; independent writers require a further serialization decision ([mapping-sync status](../done/MATERIALIZED_ENTITY_MAPPING_SYNC/MATERIALIZED_ENTITY_MAPPING_SYNC.md)).

## Validation Performed

- `uv run pytest backend/tests/api/v1/test_reconciliation_export.py backend/tests/services/test_reconciliation_service.py tests/reconciliation/test_mapping_sidecar.py -q --disable-warnings -o addopts=''`: **78 passed**.
- `uv run pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/api/v1/test_reconciliation_specifications.py -q --disable-warnings -o addopts=''`: **55 passed, 3 skipped**.
- `npm --prefix frontend run test:run -- src/components/reconciliation/__tests__/ReconciliationView.test.ts`: **3 passed**.
- Live local check: `GET /reconcile` at port 8024 succeeded; a site match through the Shape Shifter reconciliation client failed with **HTTP 500** due to missing `authority.fuzzy_site`. Port 8000 did not accept a connection. No successful live-database, reviewed-match-to-import test was established.

These results verify individual components, not the end-to-end identity outcome.

## Key References

- [Reconciliation Persistence Consolidation](../done/RECONCILIATION_PERSISTENCE_CONSOLIDATION.md) records the two-store and export design; its header status is historical and should not be used alone as current completion evidence.
- [Reconciliation Future Improvements](../RECONCILIATION_FUTURE_IMPROVEMENTS.md) defers lifecycle and export-key alignment; the latter is required for the proposed MVP, while full audit and rollback can remain deferred.
- [Assessment source map](../../investigations/reconciliation-feature-status/findings.md) contains the starter inventory.

## Next Actions

Use the [proposal](RECONCILIATION_MVP.md) to decide the MVP scope and its tracked-identity rule. First establish a working database-backed pilot and target eligibility check; then validate key alignment, durable review decisions, export, normalization, and change-request output as one workflow. No production-readiness conclusion follows from the currently passing component tests.

## Open Decisions

- Which service or database operation is authoritative for confirming that a proposed SEAD ID is an eligible existing tracked identity?
- Should an already populated `public_id` require SIMS binding, or is an equivalent read-only eligibility check sufficient for the reference-existing path?
- Is `site` the pilot entity type once its database-backed matching route is operational?
- Will the MVP deployment permit concurrent sidecar writers in separate processes?
