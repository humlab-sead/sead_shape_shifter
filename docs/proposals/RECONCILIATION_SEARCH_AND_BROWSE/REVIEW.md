# Review 1: Search and Browse Target Records During Reconciliation

## Overall assessment

The revised [proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md) incorporates the six simplifications in [REVIEW_YAGNI_KISS.md](./REVIEW_YAGNI_KISS.md): it blocks unverified accepted-link exports, uses a catalog-wide content hash, keeps drafts in the browser, bounds complete browse lists, defers target-existence checks to export, and rolls out capabilities per type. It also defers recent-query history and derived application-state calculation.

Those changes address several concerns from this review. Exact identifier search is now defined. Comparing the new workflow with the current workflow is explicitly out of scope; measurements of the new workflow establish a baseline for future improvements. Finding 1 still needs an explicit validation and repair path for invalid decisions already in, or introduced through replacement of, a catalog. Findings below are updated against the revised proposal; they are design findings, not defects in implemented code.

## Findings

### 1. High — Existing catalogs can bypass identifier validation — Addressed in the proposal

**Status.** The revised proposal specifies one type-aware local validator for all decision writes, whole-catalog replacements, existing catalog entries, and export preflight. It checks the exact type-specific URI format and saved type, requires a positive `target_id`, and verifies that the URI's parsed ID equals `target_id`. Invalid existing entries remain visible with row-specific issues; replacements containing invalid accepted references fail atomically and report all issues. Valid prior manual reconciliations remain reusable.

**Implementation check.** The current [catalog model](../../../backend/app/models/reconciliation.py#L25) checks decision status and fields, but does not establish that a URI belongs to the saved type or matches the numeric ID. Both [JSON and raw YAML routes](../../../backend/app/api/v1/endpoints/reconciliation.py#L89) can replace a catalog. The proposed shared validation and repair behavior must be applied to those existing paths.

**Decision.** Keep the no-unverified-export policy. Local syntax checks do not prove existence; successful Authority verification remains required before export. Invalid catalog entries must not be silently dropped or changed.

**Validation.** Exercise old and replacement catalogs with wrong-type, wrong-base and mismatched numeric IDs, both with Authority unavailable and with verification responses. Confirm invalid links remain visible for repair, never reach the sidecar, and unavailable verification blocks the export.

**Confidence:** High.

### 2. High — Legacy catalog saves can overwrite newer decisions — Addressed in the proposal

**Status.** The revised proposal requires the expected catalog content hash for every write, including legacy decision routes and whole-catalog JSON/YAML replacement. Stale or missing hashes conflict; the project lock alone is not treated as protection against stale input.

**Validation.** Load a catalog, save a new row decision, then submit the stale JSON and raw YAML copies. Both must report a conflict and preserve the newer decision. Test missing hashes on every legacy writer as well.

**Confidence:** High.

### 3. High — Shared-source authorization must cover review reads and saves — Addressed in the proposal

**Status.** The revised proposal removes server-owned review snapshots and resolves currently authorized source rows at batch save. It also requires project authorization and rejects unauthorized rows. This avoids a persistent snapshot token continuing to authorize data after access changes.

**Validation.** Confirm the existing shared-source authorization rules apply when review rows are loaded and are rechecked when saving drafts. Test an authorized project with an unauthorized source, an authorized source, and revocation before save; drafts must not preserve access after revocation.

**Confidence:** High. The snapshot lifecycle is removed from the proposed design; implementation must still preserve source-level authorization.

### 4. Medium — Identifier search is promised but not designed — Addressed in the proposal

**Status.** The revised proposal defines `id: <positive integer>` as an exact, type-scoped lookup. It distinguishes this syntax from ordinary OpenRefine fuzzy search and rejects malformed `id:` input without fuzzy fallback. Per-type capability metadata controls whether exact ID lookup is available.

**Design.** The Authority details lookup accepts a positive `target_id` scoped to the configured type and returns the exact record. This lookup answers an explicit identity query; it does not add a mandatory verification request when saving an accepted decision. Export verification remains required.

**Validation.** Test an ID not present in the record's label, an unknown ID, malformed `id:` syntax, and the same numeric ID in another type. Confirm malformed syntax never falls back to fuzzy search.

**Confidence:** High.

### 5. Medium — Cold-start outage behavior — Addressed in the proposal

**Status.** The revised proposal requires an Authority response when opening a new workspace and explicitly does not support cold-start offline capability discovery. After a workspace has opened, it permits the stated offline inspection and New-only workflow.

**Validation.** Cover a fresh session during an outage, an outage after a successful capability load, and recovery when the service returns. A fresh session must not infer capability from cached or absent metadata.

**Confidence:** Medium. The proposal leaves the implementation open; this is a design gap, not an observed runtime failure.

### 6. Medium — Workflow improvement baseline — Resolved by scope decision

**Status.** The proposal explicitly excludes comparing the new workflow with the current workflow because the current workflow has never been used in production and is not a suitable baseline. It records the new workflow's initial measurements for future comparisons.

**Decision.** Do not set a pass/fail target based on improvement over the current workflow. Future improvements can be compared with the new workflow baseline using the same fixture, environment, and measurement method. A technical latency budget may still gate interactive capability; it is not a comparative workflow target.

**Validation.** Record the initial timings, interactions, request counts, and preview/normalization invocations for each enabled type. No current-to-new workflow comparison is required.

**Confidence:** High.

## Planning readiness

**Ready for phase planning.** The revised proposal defines the invalid-catalog validation and repair contract as well as the stale-write, authorization, outage, identifier-search, and workflow-comparison decisions. Findings 1–6 have implementation validation criteria; no design finding in this review remains unresolved.

This review was updated by static inspection of the revised proposal. Tests and live database checks were not run; validation items above remain implementation checks, not completed results.
