# Reliable Reconciliation Links to Existing SEAD Entities — Phase 1 Task Plan

## Phase Summary

**Phase:** 1 — Key-Correct Decisions and Full Coverage. **Readiness:** Validated for implementation; the source [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-1-key-correct-decisions-and-full-coverage) marks this phase ready. The goal is to persist one review decision per normalized `site` row, addressed by the ordered business key, without truncation or automatic acceptance.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-2`, persistence and rerun parts of `SS-AC-3`, catalog-format part of `SS-AC-4`) and [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-1` through `VM-3`). No Authority Service change is required.

**Acceptance criteria**

1. [x] `PH1-AC-1` (from `SS-AC-2`): Consider every row, including rows after 1,000, and use its ordered business key, including compound keys, for decisions.
2. [x] `PH1-AC-2` (from `SS-AC-2`): Distinguish equal search labels; report missing, duplicate, or ambiguous keys for the affected rows.
3. [x] `PH1-AC-3` (from `SS-AC-3`): Reruns retain accepted, rejected, and local-only operator decisions; matching never accepts a candidate.
4. [x] `PH1-AC-4` (from `SS-AC-4`): Ignore an old-format catalog without error and allow the rows to be reconciled anew.

**Constraints:** Keep the catalog separate from the mapping sidecar. A decision does not apply a link; export remains explicit. Use `keys`/sidecar `local_key` for row identity, not `system_id`, `public_id`, or the search label. Keep normalization offline and the pipeline unchanged. This phase delivers backend/domain persistence and reporting, not the finished review UI or export semantics.

## Repository Findings

**Repository basis:** `reconciliation-mvp` at `0ef47865`, inspected 2026-10-30. Uncommitted proposal and index files were read as the requested planning sources; no existing implementation or test changes were assumed. The target task-plan file did not exist.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/services/shapeshift_service.py::ShapeShiftService.preview_entity`, `PreviewResultBuilder.build` | `limit=None` returns all normalized output rows; row limiting happens after normalization, and `estimated_total_rows` is available. | Reuse the full normalized result instead of inventing a second pipeline or paging a fixed-size preview. Guard against any truncated result. |
| `backend/app/services/reconciliation/resolvers.py::TargetEntityReconciliationSourceResolver.resolve`, `AnotherEntityReconciliationSourceResolver.resolve`, `SqlQueryReconciliationSourceResolver.resolve` | Both entity resolvers ask for only 1,000 preview rows; SQL loads raw query rows. `ReconciliationSourceStrategy.determine_strategy` selects the resolver. | Anchor decisions to all normalized *target* rows. Where an alternate source supplies search properties, associate them by unambiguous business key; never substitute raw/query row order for target identity. |
| `backend/app/services/reconciliation/service.py::ReconciliationQueryService.create`, `ReconciliationService.auto_reconcile_entity` | Query IDs map back to search-field values; a dictionary collapses equal labels, scores above a threshold auto-create accepted links, and `total` counts returned candidate keys. | Retain query ID → encoded row key, create proposed candidates only, and count/report all rows and failures distinctly. Continue using existing batches and operation progress. |
| `src/reconciliation/model.py::EntityResolutionSet`, `ResolvedEntityPair`; `backend/app/models/reconciliation.py`; `backend/app/mappers/reconciliation_mapper.py` | Decisions are a list keyed by `source_value`, with `target_id`/`will_not_match` but no explicit proposed/rejected state or persisted candidates. | Define an explicit keyed decision/status contract and round-trip it through the DTO mapper, YAML, and service methods. |
| `src/reconciliation/mapping_model.py::encode_local_key`, `backend/app/services/mapping_service.py::MappingService._default_local_key`, `src/reconciliation/fixed_entity_mapping_changes.py::build_row_index` | The sidecar encodes ordered `local_key` values; the default comes from ordered `safe_keys`. Fixed-row indexing already rejects missing and duplicate keys. | Reuse the encoder and missing-value rules; report reconciliation row errors without merging or writing an invalid key. Read an existing sidecar's `local_key` before falling back to the default. |
| `backend/app/services/reconciliation/mapping_manager.py::EntityMappingManager.load_catalog`, `save_catalog` | Missing catalogs become empty version `2.0`; existing YAML goes directly through the DTO; there is no version gate. | Introduce one new supported catalog format (version `3.0`); ignore older versions with a warning and no migration. Reject malformed or unknown future formats rather than treating them as empty. |
| `backend/app/api/v1/endpoints/reconciliation.py` and `frontend/src/stores/reconciliation.ts` | Both async and sync reconcile routes exist; preview and edit routes still use search values. The store sends `source_value` for manual decisions. | Both run paths must use the same service behavior. Do not silently interpret a label as a business key. Full typed UI integration belongs to Phase 2. |
| `backend/app/services/reconciliation/service.py::_export_to_mapping_locked` | Export treats the stored source value as a sidecar key. | Until Phase 3 implements owned export, do not export proposed/rejected/local-only decisions or copy a label into a sidecar link. Preserve manual sidecar links. |

## Scope

**In scope:** Full normalized target-row loading, ordered key extraction and error reporting, query-ID correlation, proposed candidates, explicit accepted/rejected/local-only persistence, protected reruns, versioned catalog read/write, and backend/domain tests. Keep the existing source-strategy selector; alternate-source data, if used for search, must be joined unambiguously to normalized target rows by the same ordered key, otherwise report an error rather than guess.

**Out of scope:** Frontend review controls and confidence presentation (Phase 2); manual sidecar entry for fixed-valued entities (Phase 2); owned export, link cleanup and normalization checks (Phase 3); live candidate checks, SIMS adoption, and ingester changes (later phases). Do not alter the mapping-sidecar format or migrate old reconciliation catalogs.

## Work Breakdown

### Area 1: Identify all normalized rows by business key

**Objective:** Every normalized target row has a distinct encoded key or a reported row error; a search label never determines identity.

**Affected code:** `backend/app/services/reconciliation/resolvers.py`, `backend/app/services/reconciliation/service.py`, `backend/app/services/mapping_service.py` (reuse, not redesign), `src/reconciliation/mapping_model.py` (reuse encoder), `backend/tests/services/test_reconciliation_service.py`.

**Dependencies:** None.

* [x] `T1.1` **Change:** Load the complete normalized target entity for reconciliation.
  * **Target:** `TargetEntityReconciliationSourceResolver.resolve`, `AnotherEntityReconciliationSourceResolver.resolve`, `SqlQueryReconciliationSourceResolver.resolve`, `ReconciliationService.get_resolved_source_data`.
  * **Current → required:** A 1,000-row preview or raw SQL rows determine the reconciliation rows → the normalized target result with `limit=None` determines row coverage; alternate sources contribute search data only when they can be associated by key.
  * **Implementation:** Use the existing preview/strategy infrastructure and full-row count; ensure every target row participates, including rows with an empty search label (reported as not queried). For alternate sources, refuse missing, duplicate, or unjoinable business keys explicitly; do not correlate by position or silently truncate. Preserve the existing 50-query service batching and per-batch progress updates.
  * **Constraints:** Do not change `ShapeShifter` or start network calls during normalization.
  * **Validation:** `V-1`, `V-5`: 1,001 distinct normalized `site` rows produce coverage and progress through the last row; alternate-source ambiguity is reported.
* [x] `T1.2` **Change:** Derive and check the ordered business key before building queries.
  * **Target:** `ReconciliationService.get_resolved_source_data`, `ReconciliationQueryService.create`; reuse `MappingService.get_entity_mapping` / `MappingService._default_local_key`, `encode_local_key`.
  * **Current → required:** `target_field` is both the search value and decision key → `target_field` is only query text; the stored sidecar `local_key` (or its ordered default) identifies the row.
  * **Implementation:** Carry keyed rows and row-specific errors from source loading into query construction. Check required columns and all key components (missing/null/blank, including compound keys), encode in declared order, and detect collisions before any candidate is assigned. Report each affected row and key; do not silently drop it, overwrite another row, or write a decision for an invalid key. Map each query ID to its encoded key and carry that key through results. Preserve property mappings and candidate ordering.
  * **Constraints:** `system_id` and `public_id` must not become decision keys. Fail explicitly when the entity lacks a valid business-key definition.
  * **Validation:** `V-1`, `V-2`: duplicate labels with different keys remain distinct; escaped compound components and reversed component order produce the expected keys; missing/duplicate components produce row-specific errors.

**Completion evidence:** The full-row result reports every normalized row as keyed or invalid; all query responses are associated with valid encoded keys.

### Area 2: Persist operator decisions without automatic acceptance

**Objective:** Candidate refreshes affect only proposed decisions; operator decisions survive repeated runs and a YAML round trip.

**Affected code:** `src/reconciliation/model.py`, `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py`, `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/services/test_reconciliation_service.py`, `backend/tests/mappers/test_reconciliation_mapper.py`, `backend/tests/api/v1/test_reconciliation_decisions.py` (**NEW**).

**Dependencies:** Area 1.

* [x] `T2.1` **Change:** Represent decisions and candidates by encoded key.
  * **Target:** `ResolvedEntityPair`, `EntityResolutionSet` in Core and DTO; `ReconciliationMapper.mapping_item_to_domain`, `mapping_item_to_dto`, `entity_mapping_to_domain`, `entity_mapping_to_dto`.
  * **Current → required:** A list of source values and inferred target/unmatched states → an explicit `local_key_value`, display/search value, status (`proposed`, `accepted`, `rejected`, `local-only`), optional selected ID, notes, and persisted candidate list.
  * **Implementation:** Enforce one decision per encoded key in the domain model and on catalog load; reject duplicate entries or conflicting status/ID combinations instead of taking the last one. Keep persisted match suggestions separate from the selected target ID. Round-trip all fields through the mapper and YAML, including compound keys and empty candidate lists.
  * **Constraints:** Do not store `system_id` or treat `proposed` as a committed sidecar link.
  * **Validation:** `V-2`, `V-3`: typed DTO/domain/YAML round trips and invalid-state tests.
* [x] `T2.2` **Change:** Replace automatic acceptance with proposal-only rerun behavior.
  * **Target:** `ReconciliationQueryService.create`, `ReconciliationService.auto_reconcile_entity`, `auto_accept_candidates` (remove or replace), `get_reconciliation_preview`, `update_mapping`, `mark_as_unmatched`; both reconciliation run routes and `update_mapping`/`delete_mapping`/`mark_as_unmatched` routes in `backend/app/api/v1/endpoints/reconciliation.py`; `AutoReconcileResult` and a proposed typed decision request in `backend/app/models/reconciliation.py`.
  * **Current → required:** High scores overwrite mappings; preview uses label lookup → every candidate batch refreshes only proposed records keyed by `local_key_value`, and preview returns the decision for that key. Operator actions explicitly set accepted, rejected, or local-only and keep their state on rerun.
  * **Implementation:** Handle rejected separately from local-only. Give the existing mapping edit route a typed request containing encoded `local_key_value`, status, optional selected ID and notes; wire explicit accept/reject/local-only actions through the service. Require an unambiguous encoded key for all edit and delete operations, never fall back to `source_value` for duplicate labels. Return counts, candidates and row errors consistent with all processed rows; adapt progress messages and remove the misleading auto-accepted count/claim. Keep sync and async entry points consistent. Reject old label-only requests with a clear request error until the frontend sends the typed body in Phase 2.
  * **Constraints:** Do not introduce live verification or mark any proposal as accepted. Keep decisions in the catalog only. Update the existing reconciliation workflow in `docs/USER_GUIDE.md` so it does not claim matching auto-accepts.
  * **Validation:** `V-2`, `V-3`: repeated runs refresh proposed suggestions while preserving accepted/rejected/local-only IDs, notes and candidates; high scores never create accepted decisions; authorized typed edit routes and key-based preview distinguish duplicate labels, while label-only writes fail explicitly.

**Completion evidence:** Saved and reloaded operator decisions are unchanged after another match run; a high-score match remains proposed until an explicit operator action.

### Area 3: Gate catalog versions and protect downstream writes

**Objective:** Old-format catalogs cannot be mistaken for keyed decisions or applied links.

**Affected code:** `backend/app/services/reconciliation/mapping_manager.py`, `backend/app/models/reconciliation.py`, `src/reconciliation/model.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/services/reconciliation/service.py`, `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`.

**Dependencies:** Area 2.

* [x] `T3.1` **Change:** Load and save only the new decision catalog format.
  * **Target:** `EntityMappingManager.load_catalog`, `save_catalog`; `EntityResolutionCatalog` in Core and DTO; whole-catalog JSON/raw-YAML routes.
  * **Current → required:** Version `2.0` loads as a live decision catalog → a supported version `3.0` holds keyed decisions; missing/old versions load as a fresh empty catalog, without importing old decisions.
  * **Implementation:** Check version before DTO parsing. Warn that an old catalog was ignored, preserve its on-disk contents until an intentional new save, then write only the new format. Reject malformed YAML or unsupported newer versions with a clear error; prevent whole-catalog writes from reintroducing old-format decisions. A missing file creates an empty new-version catalog.
  * **Constraints:** No legacy migration; the independent mapping sidecar remains version `2.0`. Document the new catalog version and ignored old catalogs in `docs/DESIGN.md`.
  * **Validation:** `V-4`: load old and missing-version catalogs, recreate a spec and reconcile a row in the new format, save/reload it; malformed and future-version catalogs fail explicitly without erasing files.
* [x] `T3.2` **Change:** Prevent premature application through existing export.
  * **Target:** `ReconciliationService._export_to_mapping_locked` and its route result; `backend/tests/api/v1/test_reconciliation_export.py`.
  * **Current → required:** Export copies any resolved source value under that literal sidecar key → no proposed, rejected, or local-only decision may be exported; do not create an unowned reconciliation link in Phase 1.
  * **Implementation:** Make export fail explicitly until Phase 3 implements owned, key-correct export (or use an equivalent explicit guard with no sidecar write); retain the manual-link precedence and version-checked sidecar-write implementation for that phase. Do not rewrite or delete existing sidecar links.
  * **Constraints:** An accepted catalog decision is not yet a verified, applied link. Do not introduce partial export. Explain the temporary export restriction in `docs/USER_GUIDE.md`.
  * **Validation:** `V-4`: export attempt leaves the sidecar byte-for-byte unchanged and returns a clear error; current manual sidecar links remain usable.

**Completion evidence:** Only version `3.0` decisions can be used by matching; old catalogs never contribute decisions, and Phase 1 writes no mapping sidecar links.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected result |
| --- | --- | --- | --- |
| `PH1-AC-1` (`SS-AC-2`, `VM-1`) | `T1.1`, `T1.2` | `V-1` | 1,001+ normalized rows and ordered compound keys are all accounted for. |
| `PH1-AC-2` (`SS-AC-2`, `VM-1`) | `T1.2`, `T2.1`, `T2.2` | `V-2` | Duplicate labels have separate records; invalid keys identify affected rows. |
| `PH1-AC-3` (`SS-AC-3`, `VM-2`) | `T2.1`, `T2.2` | `V-3` | Reruns retain all operator statuses and never auto-accept. |
| `PH1-AC-4` (`SS-AC-4`, `VM-3`) | `T3.1`, `T3.2` | `V-4` | Old catalogs are ignored and rows can be proposed anew without writing sidecar links. |

## Validation And Testing

Tests below are **planned**, not already passing. The baseline was run read-only on the repository state above:
`rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_export.py tests/reconciliation/test_mapping_sidecar.py` — **Pass (116 tests)**.

| ID | Check and target | Command or executable method | Expected result | Baseline |
| --- | --- | --- | --- | --- |
| `V-1` | Full normalized rows and progress: `backend/tests/services/test_reconciliation_service.py` | `rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py` | Mock normalized preview with 1,001 keyed rows and assert `limit=None`, last-row candidate, accurate total, batch calls/progress, and explicit error when alternate data cannot be joined. | Pass (existing tests only; new cases not run). |
| `V-2` | Key and DTO correctness: `backend/tests/services/test_reconciliation_service.py`, `backend/tests/mappers/test_reconciliation_mapper.py`, `tests/reconciliation/test_mapping_sidecar.py` | `rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py tests/reconciliation/test_mapping_sidecar.py` | Same label/two keys stay separate, compound order and escaped values match sidecar encoding, missing/duplicate/ambiguous keys report affected rows, invalid states/duplicate decisions fail. | Pass (existing tests only; new cases not run). |
| `V-3` | Decision persistence: `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py` (**NEW**) | `rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py` | Seed accepted, rejected and local-only decisions, rerun with different high-scoring candidates, save/reload and assert unchanged operator states, IDs, notes and candidates; proposed entries may refresh; authenticated typed edits work; ambiguous label-only edits fail; sync/async routes preserve semantics. | Existing service tests pass; new route tests not run (file not yet created). |
| `V-4` | Version and sidecar guard: `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_export.py` | `rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_export.py` | Old catalog ignored with warning, missing/new catalog works, unsupported/malformed fails without overwrite, re-reconciliation works; premature export returns an error without changing the sidecar. Update old-version fixtures/tests to assert the intended new behavior. | Pass (existing tests only; new cases not run). |
| `V-5` | Focused regression and quality checks | `rtk uv run pytest -q backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_decisions.py tests/reconciliation/test_mapping_sidecar.py`; `rtk make lint` | Tests pass; lint passes. Verify typed route responses and authorization using the existing `authorized_client` fixture. | Existing five-file baseline passes (116); new route test not run (file not yet created); lint not run (planning-only). |

**Execution evidence (2026-10-30):**

- `V-1`: `uv run rtk pytest -o addopts='' -q backend/tests/services/test_reconciliation_service.py` — 65 passed. The 1,001-row test verifies the final keyed candidate, 21 batches and progress to the last row; resolver tests verify `limit=None`.
- `V-2`: `uv run rtk pytest -o addopts='' -q backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py tests/reconciliation/test_mapping_sidecar.py` — 104 passed. Compound-key order and escaping, duplicate labels, invalid keys and typed round trips are covered.
- `V-3`: `uv run rtk pytest -o addopts='' -q backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py` — 71 passed. Reruns and an edit during matching preserve operator states, candidates and notes; authorized keyed edits and preview distinguish equal labels; both run routes use keyed candidate matching.
- `V-4`: `uv run rtk pytest -o addopts='' -q backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_export.py` — 69 passed. Old and missing-version catalogs are ignored without a write, rows can be proposed anew, malformed/future versions fail, and blocked export preserves the sidecar. A route test also verifies clear 400 errors without rewriting invalid catalogs.
- `V-5` focused tests: `uv run rtk pytest -o addopts='' -q backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_decisions.py tests/reconciliation/test_mapping_sidecar.py` — 131 passed. `rtk uv run pytest -q backend/tests tests/reconciliation` also passed on the final code (with pre-existing skips).
- `V-5` quality: `rtk make pylint-changed` passed (10.00/10); `rtk uv run black --check src/reconciliation/model.py backend/app/models/reconciliation.py backend/app/mappers/reconciliation_mapper.py backend/app/api/v1/endpoints/reconciliation.py backend/app/services/reconciliation backend/tests/services/test_reconciliation_service.py backend/tests/mappers/test_reconciliation_mapper.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_decisions.py` passed (13 files); `rtk uv run isort --check-only backend/app/services/reconciliation/mapping_manager.py backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py` and `rtk git diff --check` passed. `rtk make lint` formatted four changed files and then failed on the unrelated, unchanged `tests/test_generate_user_release_notes.py:122` pylint `W1404` warning. The full-lint part of `V-5` remains open; that file is outside this phase's deliverables.

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
| --- | --- | --- | --- |
| Complete normalized-row and keyed query service | `backend/app/services/reconciliation/resolvers.py`, `service.py` | `T1.1`, `T1.2`, `T2.2` | Full row count, row errors, and proposals keyed correctly. |
| Decision domain, DTO and conversion | `src/reconciliation/model.py`, `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py` | `T2.1`, `T3.1` | Versioned YAML and DTO/domain round trip. |
| Guarded catalog and route behavior | `backend/app/services/reconciliation/mapping_manager.py`, `service.py`, `backend/app/api/v1/endpoints/reconciliation.py` | `T2.2`, `T3.1`, `T3.2` | Old catalog ignored and no unsafe sidecar write. |
| Focused tests | `backend/tests/services/test_reconciliation_service.py`, `backend/tests/mappers/test_reconciliation_mapper.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_decisions.py` (**NEW**), `tests/reconciliation/test_mapping_sidecar.py` | `T1.1`–`T3.2` | `V-1`–`V-5` pass after implementation. |
| Updated behavior documentation | `docs/DESIGN.md`, `docs/USER_GUIDE.md` | `T2.2`, `T3.1`, `T3.2` | Replace claims of auto-accept and unrestricted export; document new catalog format, old-format warning and the Phase 1 restriction without describing later phases as shipped. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Identify rows | Complete | None | `V-1`, `V-2`: 1,001 rows and ordered compound keys tested. |
| Area 2: Persist decisions | Complete | Area 1 | `V-2`, `V-3`: proposed candidates and protected operator states tested. Phase 2 must update the label-based UI. |
| Area 3: Gate versions | Complete | Area 2 | `V-4`: version `3.0` and export guard tested. Phase 3 must implement owned export. |

## Definition Of Done

- [x] `PH1-AC-1`–`PH1-AC-4` have passing `V-1`–`V-4` evidence with actual values/keys, not just HTTP counts.
- [ ] All areas and deliverables are implemented; `V-5` passes and the tracker records results.
- [x] Normalization remains offline; no candidate becomes a link without an explicit later export, and existing manual links remain intact.
- [x] API, domain, mapper, YAML version and documentation agree; no old-format decisions are silently reused.
- [x] Any deviation or follow-up for the Phase 2 UI / Phase 3 export is recorded; no unresolved question changes this phase's implementation or validation.
- [ ] If current repository code or project configuration conflicts with this plan during implementation, stop and report the evidence rather than inventing a replacement design or expanding scope.

## Risks And Open Questions

- The current frontend store sends search values, not encoded keys. Phase 1 must refuse ambiguous writes; Phase 2 updates the review view and typed request/response contract. Do not claim existing UI review is correct at the end of Phase 1.
- An explicit alternate entity or SQL source can supply useful search attributes but may not contain the target business key. Preserve its strategy for loading search data only; report an unjoinable row rather than infer identity from labels or position. The default `site` target-entity strategy has no such join.
- Existing export assumes source values are sidecar keys. It must not be used to apply Phase 1 decisions until Phase 3 supplies owned, verified export. Existing old sidecar data is not a reconciliation catalog migration target.
