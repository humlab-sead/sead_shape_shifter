# Reliable Reconciliation Links to Existing SEAD Entities — Phase 2 Task Plan

## Phase Summary

**Phase:** 2 — Review View Contract and Manual Links. **Readiness:** Validated for implementation. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-2-review-view-contract-and-manual-links) marks Phase 2 ready; the [Phase 1 task plan](RECONCILIATION_MVP_PHASE_1_TASK_PLAN.md) records delivery of the keyed decision store. This phase makes review actions work for `site`, including a fixed-valued `site`, without exporting accepted decisions automatically.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-3`) and [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-4`, `VM-5`).

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `SS-AC-3`): The UI persists accept, reject, local-only, and manual decisions, and shows candidates and confidence on one scale.
2. [x] `PH2-AC-2` (from `SS-AC-3`): The UI reports failures and unresolved rows to the operator.
3. [x] `PH2-AC-3` (from `SS-AC-3`): A manual link on a `type: fixed` entity survives a save that leaves that key's row ID unchanged, overrides the row ID during normalization, and is replaced when that key's row ID is edited.

**Dependencies and constraints:** Keep the Phase 1 `version: "3.0"` catalog and encoded `local_key_value` contract. The catalog is for decisions; only committed sidecar links affect normalization. Manual links use the existing protected mapping-link API, are trusted without an Authority Service check, and are not subject to reconciliation cleanup. No auto-accept or bulk accept. Keep normalization offline, manual-link precedence, the existing fixed-row synchronization, and version-checked sidecar writes. Phase 3 owns reconciliation export and link ownership; Phase 5 owns live verification. The existing export route explicitly rejects requests until Phase 3, so this UI must not suggest export is available.

## Repository Findings

**Repository basis:** Branch `reconciliation-mvp`, commit `315f9acf`, inspected 2026-10-30. The worktree was clean; the repository versions of the proposal and phase plan were used alongside the attached phase-plan snapshot. No implementation or test changes were made while planning.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/models/reconciliation.py::DecisionUpdateRequest`, `backend/app/api/v1/endpoints/reconciliation.py::update_mapping`, `ReconciliationService.update_mapping` | The authenticated POST body is `{local_key_value, status, target_id?, notes?}` with `accepted`, `rejected`, or `local-only`. An accepted decision requires an ID; the service refuses unknown keys. DELETE uses a `local_key_value` query parameter. | Use the existing typed POST for each review action, not the search label, old `mark-unmatched` form, or whole-catalog PUT. Reject validation errors visibly. |
| `ReconciliationService.get_reconciliation_preview`, `backend/app/models/reconciliation.py::AutoReconcileResult` | Preview rows include `local_key_value`, `status`, `target_id`, `confidence` (0–1), `candidates`, and per-row `errors`. The synchronous matching result includes `proposed`, `unmatched`, `total`, and keyed `errors`; candidate scores are 0–100. The service currently sets accepted confidence to `1.0`, irrespective of the selected candidate's score. | Type the actual response; retain candidates on reload, preserve error rows, and display a single 0–100% scale without treating score as approval. Keep the selected candidate's score when one is accepted. |
| `frontend/src/types/reconciliation.ts`, `frontend/src/stores/reconciliation.ts::updateMapping`, `deleteMapping`, `loadPreviewData`, `autoReconcile` | Frontend types still describe `source_value`, `will_not_match`, `auto_accepted`, and old match statuses. Writes send a search label without `status`; preview-load failures become empty arrays. | Align types and store calls to Phase 1; keep request failures distinct from a genuinely empty preview. Key preview state by entity and target so switching specifications cannot display another field's rows. |
| `ReconciliationView.vue::handleUpdateMapping`, `ReconciliationGrid.vue::acceptCandidate`, `confirmMarkUnmatched`, `confirmBulkReject`, `saveChanges` | The view passes the target-field value as identity. The grid mutates props, sends some updates without awaiting them, calls `fetch` outside `apiClient` for local-only, and simulates save success. Bulk accept selects the top candidate; filters and labels imply automatic acceptance. | Make explicit per-row actions await the store, reload persisted state, and show errors without a false success or automatic/bulk acceptance. Use `apiClient` for authenticated routes. |
| `ReconciliationGrid.vue`, `PreviewMatchedDataDialog.vue`, `AlternativeSearchDialog.vue` | Candidate scores are multiplied by 100 in one view; confidence and thresholds are displayed as if already percentages in others. The preview dialog labels accepted rows as “Auto-Matched” based on score. | Convert candidate scores from 0–100 only for display and stored confidence/thresholds from 0–1 to percentages. Render actual decision status and unresolved/error states in both grid and preview dialog. `ReconciliationStatsCard.vue` is not mounted by this view and need not be changed. |
| `backend/app/api/v1/endpoints/mapping.py::get_entity_mapping`, `put_mapping_link`, `backend/app/models/mapping.py`, `MappingService.put_link` | GET exposes `local_key`, `public_id`, and links by encoded key; PUT accepts a bare integer `target_id` and optional notes and writes `source: manual` under the project lock. Only committed links apply. There is no `verified_at` field yet. | Load sidecar metadata and links for the selected entity; display a committed sidecar target as the effective ID, even if a fixed row or catalog decision has a different ID. Distinguish manual/trusted from reconciliation/not yet checked; do not claim a SEAD check took place. Phase 5 can extend the verification display. |
| `src/reconciliation/fixed_entity_mapping_changes.py::compute_fixed_row_change_set`, `src/normalizer.py::ShapeShifter._apply_mapping_sidecar_links` | A fixed-row save with the same key and saved ID retains an existing manual link; an ID edit upserts a new manual link. Normalization uses a committed sidecar target in preference to the row's own `public_id`. | Exercise the full PUT → fixed-row save → normalization path, rather than changing the fixed-row algorithm on speculation. Preserve unaffected links and metadata. |
| `backend/tests/api/v1/test_reconciliation_decisions.py`, `test_mapping.py`, `test_entities.py`; `tests/process/test_shapeshifter.py`; `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts` | Existing tests cover keyed API edits and separate mapping/fixed-row behavior; the frontend view tests cover YAML mode and the export button but not keyed review. The view fixture still uses catalog version `2.0`. | Extend these tests, add focused store/grid tests, and replace outdated UI expectations without removing the temporary export guard. |

## Scope

**In scope:** Typed frontend catalog/preview/decision and sidecar contracts; keyed, per-row accept/reject/local-only actions; candidate search and consistent confidence display; visible row errors, unmatched/proposed rows, and request failures; manual key + integer ID entry, committed sidecar effective-ID display, and fixed-row/normalization regression coverage; user workflow documentation.

**Out of scope:** Candidate verification or Authority Service changes, owned export and cleanup, auto/bulk accept, ingester changes, catalog migration, alteration of fixed rows by the manual-link form, or changes to normalization behavior. Do not equate an accepted catalog decision with an applied sidecar link. A link lacking verification metadata is **not checked**, not verified.

## Work Breakdown

### Area 1: Align typed review requests and confidence

**Objective:** All UI reads and writes use the Phase 1 keyed API; the score shown after acceptance represents the candidate actually selected.

**Affected code:** `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `backend/app/services/reconciliation/service.py::update_mapping`, `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `frontend/src/stores/__tests__/reconciliation.test.ts` (**NEW**).

**Dependencies:** Phase 1 decision store.

* [x] `T1.1` **Change:** Replace label-based store and type contracts with typed keyed decisions.
  * **Target:** `frontend/src/types/reconciliation.ts::{ResolvedEntityPair, ReconciliationPreviewRow, AutoReconcileResult, ReconciliationCandidate}`, `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts::{updateMapping, deleteMapping, loadPreviewData, autoReconcile}`.
  * **Current → required:** Search-label POST and legacy result types → body `{local_key_value, status, target_id?, notes?}` accepted by `DecisionUpdateRequest`, keyed DELETE, correct result/preview fields, and a reload that retains persisted candidates.
  * **Implementation:** Route requests through `apiClient` (or its existing `apiRequest` wrapper); keep `previewData` scoped to entity **and** target. Propagate HTTP failures, preserve the previous preview or show an explicit error (never replace failure with an empty success state), and discard stale responses after a selection change. Refresh catalog and preview after a successful action; no whole-catalog PUT to save individual decisions.
  * **Constraints:** Do not accept a missing key, infer a key from `source_value`, or silently convert a rejected/local-only action into a DELETE. Use the existing authenticated project routes.
  * **Validation:** `V-1`, `V-2`: duplicate labels with different keys remain independent; missing key, invalid accepted body, and preview 500 report errors without clearing candidates or claiming success.
* [x] `T1.2` **Change:** Preserve the selected candidate's match score on explicit acceptance.
  * **Target:** `backend/app/services/reconciliation/service.py::update_mapping`; `backend/tests/services/test_reconciliation_service.py`; `backend/tests/api/v1/test_reconciliation_decisions.py`.
  * **Current → required:** Every accepted decision receives confidence `1.0` → an accepted listed candidate stores its 0–100 score divided by 100 (or `None` when no candidate score exists); rejecting/local-only has no score.
  * **Implementation:** Match the selected ID against the existing candidate list using the service's ID extraction logic, without treating candidate `match` or threshold as consent; retain candidates and notes across the catalog write. An accepted ID not present in the list must not be assigned a fabricated candidate score.
  * **Constraints:** Preserve the existing request body and accepted-ID validation; matching alone must not modify an operator decision.
  * **Validation:** `V-1`: accepting an 82-point candidate yields `0.82` in catalog/preview and 82% in the UI; a missing score is shown as unknown, not 100%.

**Completion evidence:** Backend request/response and frontend types agree. `V-1` passed with 74 tests, including the selected candidate score and missing-score cases; `V-2` passed with 16 frontend tests.

### Area 2: Make review actions and failures visible

**Objective:** Operators can decide each keyed row and distinguish failures, proposed/unresolved rows, and their own decisions.

**Affected code:** `frontend/src/components/reconciliation/ReconciliationView.vue`, `ReconciliationGrid.vue`, `PreviewMatchedDataDialog.vue`, `AlternativeSearchDialog.vue`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`, `ReconciliationGrid.test.ts` (**NEW**).

**Dependencies:** Area 1.

* [x] `T2.1` **Change:** Submit explicit, awaited review actions from the grid.
  * **Target:** `ReconciliationGrid.vue::{acceptCandidate, handleAlternativeAccept, confirmMarkUnmatched, confirmBulkAccept, confirmBulkReject, saveChanges}`, `ReconciliationView.vue::handleUpdateMapping`.
  * **Current → required:** Optimistic row mutation, wrong identity, direct `fetch`, bulk top-candidate acceptance, and simulated save → explicit single-row accept/reject/local-only requests keyed by `row.local_key_value`, with server-confirmed reload before showing success.
  * **Implementation:** Provide distinct reject and local-only controls; require an explicit candidate choice for acceptance. Use the store action for each, await completion, prevent duplicate submissions, and keep the previous state plus a visible error on failure. Remove misleading Save Changes and bulk-accept paths rather than firing unawaited requests. Keep candidate search through the existing authenticated suggest endpoint.
  * **Constraints:** A proposed candidate is not an applied link; no auto-accept based on score. Do not edit the normalized/fixed source row when recording a decision.
  * **Validation:** `V-2`: per-row accept, reject, and local-only send exact keys/statuses; two identical labels remain independent; failed requests do not show success or mutate displayed decisions.
* [x] `T2.2` **Change:** Render actual status, candidates, confidence, and row-level failures.
  * **Target:** `ReconciliationGrid.vue::{filteredRowData, stats, columnDefs}`, `PreviewMatchedDataDialog.vue::{stats, getStatusLabel}`, `AlternativeSearchDialog.vue::getScoreColor`, `ReconciliationView.vue::{handleAutoReconcile, entityPreviewData}`.
  * **Current → required:** Threshold-derived “Auto-Accepted” and multiplying 0–100 scores again → actual `status` labels and candidate lists; internal 0–1 confidence/thresholds shown as 0–100%; candidate scores shown directly as 0–100%.
  * **Implementation:** Show `errors` on the affected preview rows, no-key rows as unreviewable, proposed rows without candidates and rows without decisions as unresolved, plus `AutoReconcileResult.errors`, `unmatched`, and `total` after a run. Show load/network errors separately from an empty result. Update the preview dialog and CSV labels so they do not call an unexported decision a final linked ID. Keep the export button unavailable with an explanation until Phase 3 (adjust existing export-button tests).
  * **Constraints:** Do not infer acceptance from threshold, `match`, or score. Avoid describing any link as SEAD-verified; `verified_at` does not yet exist.
  * **Validation:** `V-2`: 0-, 82-, and 100-point candidates; `0`, `0.82`, `1.0`, and null stored confidence; 0.70/0.95 thresholds; key errors, missing candidates, preview failure, and matching failure all have distinct visible outcomes.

**Completion evidence:** `V-2` passed with 16 frontend tests covering keyed actions, explicit candidate selection, errors, unresolved rows, confidence display, and manual target ID zero.

### Area 3: Add manual sidecar entry and prove fixed-row behavior

**Objective:** A manual key/ID override appears as the effective ID and survives an unrelated fixed-row save.

**Affected code:** `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `ReconciliationView.vue`, `ReconciliationGrid.vue`, `frontend/src/types/reconciliation.ts`, `backend/app/api/v1/endpoints/mapping.py`, `backend/tests/api/v1/test_mapping.py`, `backend/tests/api/v1/test_entities.py`, `tests/process/test_shapeshifter.py`, and the frontend tests from Areas 1–2.

**Dependencies:** Areas 1–2 for keyed selection and visible errors; existing mapping endpoint and fixed-row save behavior.

* [x] `T3.1` **Change:** Add manual key + target-ID entry to the review view, including a fixed-valued `site`.
  * **Target:** `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/types/reconciliation.ts`, `ReconciliationView.vue`, `ReconciliationGrid.vue`.
  * **Current → required:** Review has no manual sidecar action and shows only catalog `target_id` → use `GET /projects/{project}/mapping/{entity}` for key metadata/links and `PUT /projects/{project}/mapping/{entity}/{key}` with `{target_id, notes?}` for manual entry.
  * **Implementation:** Accept an explicit encoded key (or a keyed preview-row selection) and integer target ID; support zero as an integer, not a falsy “missing” value. Encode the key in the URL. Reload the sidecar after PUT and on entity selection; display the committed sidecar ID as **effective**, while showing the saved fixed-row ID and catalog decision separately. Mark `source: manual` as trusted/not checked; mark an existing reconciliation link without verification metadata as not checked, not verified. If sidecar loading fails, show the error instead of asserting an effective ID from incomplete data.
  * **Constraints:** Do not change fixed row values, convert the manual ID to a candidate URI, or call the Authority Service. A catalog acceptance alone is not a sidecar link. Keep this entry usable when a fixed-valued row has no candidate.
  * **Validation:** `V-2`, `V-3`: manual PUT uses the encoded key and returns `source: manual`; reloading shows the sidecar ID over a different saved row ID and never labels it verified.
* [x] `T3.2` **Change:** Cover key encoding and the fixed-row save/normalization contract without redesigning synchronization.
  * **Target:** `backend/app/api/v1/endpoints/mapping.py::{get_mapping_link, put_mapping_link}` if needed to accept slash-containing encoded keys; `backend/tests/api/v1/test_mapping.py`, `backend/tests/api/v1/test_entities.py`, `tests/process/test_shapeshifter.py`.
  * **Current → required:** Separate tests cover PUT, fixed-row changes, and entity normalization → one scenario proves PUT for a fixed row with saved ID 10 and manual ID 99, an unchanged-ID save retaining 99, normalization producing 99, then an edited row ID 11 replacing the sidecar target with 11. Include both inline fixed-row save and the existing materialized values save path.
  * **Implementation:** Test URL encoding for compound keys (including escaped separators), and a slash-containing key; if the route rejects a valid encoded slash, use the existing path parameter's `:path` converter while preserving GET/PUT route ordering. Assert persisted sidecar `source`, `target_id`, and untouched-link metadata as well as normalized `public_id`; do not test only HTTP 200.
  * **Constraints:** Keep `compute_fixed_row_change_set`, project locking, and version-checked writes; alter them only if the new end-to-end assertion demonstrates a defect. Normalization must remain offline.
  * **Validation:** `V-3`: fixed-row contract and encoded-key route tests pass, including negative cases for malformed manual input or a missing entity.

**Completion evidence:** `V-3` passed with 167 tests. Both inline and materialized saves retain manual target 99 for an unchanged row ID, normalization uses 99, and editing the row ID replaces the sidecar target with 11; encoded-key route tests pass.

### Area 4: Document and verify the delivered workflow

**Objective:** User guidance and quality checks describe only functionality that Phase 2 actually ships.

**Affected code:** `docs/USER_GUIDE.md`, existing and new tests above.

**Dependencies:** Areas 1–3.

* [x] `T4.1` **Change:** Update the reconciliation user workflow and run the focused regression checks.
  * **Target:** `docs/USER_GUIDE.md::Reconciliation Workflow`, `Materialized Entity Edits`; validation targets below.
  * **Current → required:** The guide warns that the grid sends labels and says to use the API for manual links → describe the keyed UI actions, candidate review, unresolved/error display, effective manual ID, and fixed-row save rule. Retain the warning that reconciliation export remains unavailable until Phase 3; do not promise live verification.
  * **Implementation:** Record actual check results and any deviations in this plan's tracker during implementation; stop and report if current source or project configuration conflicts with this task plan rather than inventing a replacement design or broadening scope.
  * **Constraints:** Preserve the guide's user-facing organization; avoid describing Phase 3 or Phase 5 as shipped.
  * **Validation:** `V-4`, `V-5`.

**Completion evidence:** The guide matches the tested UI. `V-4` passed the frontend type check and 16 tests; `V-5` passed Python formatting, frontend lint, and the documentation-link check.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`SS-AC-3`, `VM-4`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-1`, `V-2`, `V-3` | Authenticated keyed bodies persist all three catalog statuses; manual PUT persists a link; reload retains candidates and displays the actual score. |
| `PH2-AC-2` (`SS-AC-3`, `VM-4`) | `T1.1`, `T2.1`, `T2.2` | `V-1`, `V-2` | Key errors, no-candidate rows, HTTP failure and service failure are visible and cannot masquerade as success. |
| `PH2-AC-3` (`SS-AC-3`, `VM-5`) | `T3.1`, `T3.2` | `V-3` | Same-key, same-ID fixed save retains manual 99; normalization uses 99 over saved 10; row ID edit changes the link to 11. |

## Validation And Testing

| ID | Check and target | Exact command or method | Covers | Expected result | Baseline (2026-10-30) | Implementation result |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Backend typed decision and confidence tests in `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/services/test_reconciliation_service.py`; valid/invalid status, equal labels, candidates and scores | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/services/test_reconciliation_service.py` | `PH2-AC-1`, `PH2-AC-2` | Body round-trips with correct key, status, candidate score, and error response. | Pass: these files were included in a 140-pass focused Core/backend run; new score assertions not run. | Pass: 74 tests. |
| `V-2` | Frontend store/grid/view tests in `frontend/src/stores/__tests__/reconciliation.test.ts` (**NEW**), `frontend/src/components/reconciliation/__tests__/ReconciliationGrid.test.ts` (**NEW**), `ReconciliationView.test.ts`; action bodies, duplicate labels, no auto-accept, preview/errors and manual/effective ID | `cd frontend && pnpm exec vitest run src/stores/__tests__/reconciliation.test.ts src/components/reconciliation/__tests__/ReconciliationGrid.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | `PH2-AC-1`, `PH2-AC-2` | All actions await a keyed response; 0–100% display and error states match backend values. | Pass: existing view test file, 3 tests. Not run: two planned test files do not exist yet. | Pass: 16 tests across 3 files. |
| `V-3` | Mapping/fixed-row/normalization tests in `backend/tests/api/v1/test_mapping.py`, `backend/tests/api/v1/test_entities.py`, `tests/process/test_shapeshifter.py`, `tests/reconciliation/test_fixed_entity_mapping_changes.py`; unchanged and edited ID, inline/materialized saves, URI-encoded keys | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_mapping.py backend/tests/api/v1/test_entities.py tests/process/test_shapeshifter.py tests/reconciliation/test_fixed_entity_mapping_changes.py` | `PH2-AC-1`, `PH2-AC-3` | Full fixed-row lifecycle and sidecar provenance/ID assertions pass without network access. | Pass: mapping and change-set tests were in the 140-pass run; one existing materialized-save test passed and one existing sidecar-normalization test passed separately. New combined assertions not run. | Pass: 167 tests. |
| `V-4` | Frontend type check and focused tests after implementation | `cd frontend && pnpm exec vue-tsc --noEmit` and `cd frontend && pnpm exec vitest run src/stores/__tests__/reconciliation.test.ts src/components/reconciliation/__tests__/ReconciliationGrid.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | All UI changes | No new type errors or UI regressions. | Pass: `vue-tsc --noEmit` exited 0 and existing view tests passed (3). | Pass: `vue-tsc --noEmit`; V-2's 16 tests passed. |
| `V-5` | Focused Python formatting, frontend lint, all affected tests, and guide links | `uv run black --check backend/app/services/reconciliation/service.py backend/app/api/v1/endpoints/mapping.py backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_mapping.py backend/tests/api/v1/test_entities.py tests/process/test_shapeshifter.py`; `cd frontend && pnpm exec eslint src/types/reconciliation.ts src/api/reconciliation.ts src/stores/reconciliation.ts src/components/reconciliation/ReconciliationView.vue src/components/reconciliation/ReconciliationGrid.vue src/components/reconciliation/PreviewMatchedDataDialog.vue src/components/reconciliation/AlternativeSearchDialog.vue src/components/reconciliation/__tests__/ReconciliationView.test.ts src/components/reconciliation/__tests__/ReconciliationGrid.test.ts src/stores/__tests__/reconciliation.test.ts`; `make check-doc-links` | Phase quality, guide | Checks pass; if a check fails on unrelated existing files, record the failure separately. | Pass: `make check-doc-links` reports valid links including this plan. Not run: formatting and lint for planned implementation files. | Pass: Black left 7 files unchanged; ESLint reported no issues; `make check-doc-links` reported valid links. |

The existing export-button test currently assumes successful export; adjust it to assert the Phase 1 export guard and explanatory UI until Phase 3. Do not turn the export route on to satisfy a frontend test.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed keyed decision and sidecar clients | `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts` | `T1.1`, `T3.1` | Correct POST/GET/PUT bodies, typed responses and reliable reload/error state. |
| Candidate confidence persistence | `backend/app/services/reconciliation/service.py::update_mapping` | `T1.2` | Accepted score round-trips on a 0–1 scale without automatic acceptance. |
| Review and manual UI | `frontend/src/components/reconciliation/ReconciliationView.vue`, `ReconciliationGrid.vue`, `PreviewMatchedDataDialog.vue`, `AlternativeSearchDialog.vue` | `T2.1`, `T2.2`, `T3.1` | Reviewed decisions, errors, sidecar effective ID and manual status visible. |
| Encoded-key compatibility, if exercised | `backend/app/api/v1/endpoints/mapping.py::{get_mapping_link, put_mapping_link}` | `T3.2` | Valid slash/compound keys round-trip; no endpoint regression. |
| Backend and Core regression tests | `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `test_mapping.py`, `test_entities.py`, `tests/process/test_shapeshifter.py` | `T1.2`, `T3.2` | `V-1`, `V-3` pass with actual IDs. |
| Frontend tests | `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`, `ReconciliationGrid.test.ts` (**NEW**), `frontend/src/stores/__tests__/reconciliation.test.ts` (**NEW**) | `T1.1`, `T2.1`, `T2.2`, `T3.1` | `V-2` passes including failure and boundary scenarios. |
| User workflow | `docs/USER_GUIDE.md::Reconciliation Workflow`, `Materialized Entity Edits` | `T4.1` | Phase 2 UI instructions agree with tested behavior. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Typed requests and confidence | Complete | Phase 1 | `T1.1`–`T1.2` complete; `V-1` passed with 74 tests, including candidate-score persistence and missing-score behavior. |
| Area 2: Review actions and failures | Complete | Area 1 | `T2.1`–`T2.2` complete; `V-2` passed with 16 tests for keyed actions, explicit candidate selection, errors, and unresolved states. |
| Area 3: Manual links and fixed rows | Complete | Areas 1–2 | `T3.1`–`T3.2` complete; `V-3` passed with 167 tests, including inline/materialized fixed-row saves and normalization. |
| Area 4: Documentation and checks | Complete | Areas 1–3 | `T4.1` complete; `V-4` passed the type check and 16 frontend tests; `V-5` passed with 7 Python files unchanged, no ESLint issues, and valid documentation links. |

## Definition Of Done

- [x] `PH2-AC-1`–`PH2-AC-3` have passing `V-1`–`V-3` evidence, including actual persisted and normalized target IDs.
- [x] Every area and listed deliverable is complete; `V-4` and applicable `V-5` checks pass or a pre-existing failure is documented.
- [x] Preview reload preserves candidates; distinct keys with the same label remain distinct; failures and unresolved rows are not shown as success.
- [x] Manual entry uses the sidecar without editing fixed values; unchanged-ID saves retain it, edited-ID saves replace it, and normalization stays offline.
- [x] User guide, typed frontend contract, backend decision body, and temporary export guard describe the same shipped behavior.
- [x] If current repository code or project configuration conflicts with this plan during implementation, stop and report the evidence rather than inventing a replacement design or broadening scope.

## Risks And Open Questions

- The sidecar API does not expose `verified_at` yet; distinguish **not checked** from **verified** until Phases 3 and 5 provide verification metadata. Manual links remain trusted without a check.
- A route path parameter may reject a slash even when the frontend percent-encodes it. `T3.2` includes an authenticated route test and a narrow converter fix if the test demonstrates that failure.
- The Phase 1 tracker records a full-lint failure in an unrelated, unchanged test file. Do not treat it as a Phase 2 regression; report any new failure in files touched by this phase.
