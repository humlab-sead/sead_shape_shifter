# Reconciliation Search and Browse: Phase 3 Task Plan

## Phase Summary

**Goal:** Deliver a persistent review workspace that opens without Find Candidates, searches or browses existing targets, stages decisions across source rows, warns about changed saved decisions, and saves drafts in one batch.

**Readiness:** Validated for implementation on 2026-11-20. The [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md), [Phase 3 in the phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-3-persistent-review-workspace), and [frozen Phase 2 save contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md) fix the required behavior. Phase 1's Authority API is implemented at `sead_authority_service` commit `1f3f1b8`; Phase 2's serialized writes, batch route, and export gate are present here at `c465a318`. Pilot capabilities remain disabled in the shipped Authority configuration. Enable them only in controlled tests; per-type live checks and advertisement belong to Phase 4.

**Constraints:** Keep the existing catalog and export routes, legacy review grid, source identity, project authorization, and read-only retrieval. The workspace warns before overwriting a decision changed since load, but the batch request has no expected-state field; a change between comparison and write remains last-writer-wins (backlog R33). A save is never retried automatically.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-8`): Open review without Find Candidates; move through ten rows using keyboard or labelled controls, stage or skip, and patch only affected rows/counts on batch success. Failure retains all unsaved drafts.
2. [x] `PH3-AC-2` (from `P-AC-3`, `P-AC-9`): Bounded ranked text search uses advertised context; `id: <positive integer>` uses exact type-scoped lookup. Unknown IDs, malformed syntax, and stale responses have distinct safe outcomes.
3. [x] `PH3-AC-3` (from `P-AC-4`, `P-AC-5`, `P-AC-9`): Filter/sort only complete browse lists locally; report too-large lists, preserve search/browse URI and numeric ID parity, and do not invent browse confidence or require details to save.
4. [x] `PH3-AC-4` (from `P-AC-7`, `P-AC-10`, `P-AC-12`): Never infer New from a miss or failure; require live Authority discovery to open a new workspace, retain New-only saves and exports after an outage, preserve legacy review without Browse, and distinguish Save decision from Export. In-workspace saved-decision inspection is deferred to backlog R34.
5. [x] `PH3-AC-5` (from `P-AC-2`, `P-AC-9`, `P-AC-11`): Restore only scoped browser drafts and focus/mode/filter/sort/query state; isolate rows and projects; ignore composition shortcuts and late requests; never restore a confirmed selection or fresh target collection.
6. [x] `PH3-AC-6` (from `P-AC-6`, `P-AC-8`): Compare affected keys against loaded saved decisions before saving, warn and retain drafts for changed decisions, ignore unrelated changes, and retain the documented advisory race and no-retry behavior.

## Repository Findings

**Repository basis:** Shape Shifter branch `reconciliation-search-and-browse`, commit `c465a318`; Authority Service branch `reconciliation-search-and-browse`, commit `1f3f1b8`; planning date 2026-11-20. Both working trees were clean at inspection. No Phase 3 task plan existed. These are source states, not proof of a paired deployment.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| `frontend/src/components/reconciliation/SpecificationsList.vue::reconcileSpec`, `ReconciliationView.vue::handleReconcileSpec` | The single specification action is disabled when batch matching is incompatible; the review tab itself can load preview without matching. | Add a separately labelled Review entry for keyed specifications without enabling Find Candidates. Preserve the legacy grid for unsupported selection capabilities. |
| `frontend/src/components/reconciliation/ReconciliationGrid.vue::gridData`, `AlternativeSearchDialog.vue::searchAlternatives` | The grid filters unresolved rows but uses modal per-row decisions. Alternative search calls prefix suggestions with a 400 ms debounce and has no response identity guard. | Build a persistent queue/pane for the new workflow; do not relabel prefix suggestions as ranked search or use the legacy single-decision save loop. |
| `frontend/src/stores/reconciliation.ts::loadPreviewData`, `updateMapping` | Preview loads have scoped request versions; single decisions reload the catalog and full preview. | Reuse scoped preview loading and add a separate batch action that patches returned keys/counts; leave legacy action behavior intact. |
| `frontend/src/utils/reconciliationManifest.ts::parseReconciliationManifest`, `backend/app/clients/reconciliation_client.py::get_service_manifest` | Legacy manifest parsing validates `supportedTypes` and properties; the backend caches manifests for 30 seconds. | Parse the optional versioned extension independently. A new workspace must fetch an Authority response, not open from the cached manifest during an outage. |
| `backend/app/api/v1/endpoints/reconciliation.py::save_decision_batch`, `backend/app/models/reconciliation.py::DecisionBatchResult` | `POST .../decisions` accepts `drafts` with encoded key, displayed values, accepted/local-only status, URI/ID and notes; success echoes ordered `saved` entries and `counts.specification`. GET `/projects/{project_name}/reconciliation` reads the catalog. | Consume these existing shapes; read the catalog for an advisory pre-save comparison, then patch only successful rows. Do not change the save contract. |
| `backend/app/services/reconciliation/service.py::get_reconciliation_preview`, `reference_validation.py::accepted_reference_error` | Preview includes source columns, encoded key, saved decision fields and row errors; the local validator checks accepted URI/type/ID without a remote existence lookup. | Preserve source values for `displayed_values`, show unreviewable keys/errors, and never use a saved decision as proof of target existence. |
| `sead_authority_service/src/api/router.py::record_selection_types`, `record_list`, `record_details`, `_handle_interactive_search`; `src/api/model.py::RecordSelectionTypeDescriptor` | Version 1 supplies `/records/types`, complete-or-error lists, exact `target_id` details, and marked bounded interactive reconciliation. The shipped flags for `feature_type` and `country` are all off. | Use fixed same-service endpoints through the Shape Shifter backend, independently gate each capability, and test with explicitly enabled fixture flags. |
| `frontend/src/api/reconciliation.ts::reconciliationServiceApi`, `backend/app/api/v1/endpoints/reconciliation.py::suggest_entities` | Frontend calls the Shape Shifter API; the old suggest route uses prefix matching and returns ten candidates. | Add authorized selection routes instead of sending the browser to the Authority host or changing legacy suggest behavior. |

Graphify's `AlternativeSearchDialog`/grid relationship was used for navigation; the file and contract findings above were checked in source. No graph-derived result is treated as an API contract.

## Scope

- **In:** Shape Shifter's authorized Authority selection adapter; typed frontend API and metadata; persistent source queue, Search/Browse, request guards, scoped browser drafts, atomic batch save, advisory stale-view warning, keyboard access, and directly affected user guidance/tests.
- **Out:** Authority implementation or production flag changes; Phase 4 live pilot/performance gates; target/SIMS writes on retrieval; server paging, recent-query history, derived application state, server review sessions, catalog preconditions or per-row versions (R33), and recovery of previously exported unverified links.
- **Affected contracts:** Authority's version-1 discovery, interactive search, list/details/error shapes; existing Shape Shifter preview/catalog/batch/export routes. No project YAML or Core transformation change is planned.

## Work Breakdown

### Area 1: Connect Authorized Record Selection

**Objective:** The browser can discover and query only the configured specification's Authority type via authenticated Shape Shifter endpoints, with distinct result/error states.

**Affected code:** `backend/app/models/reconciliation.py`, `backend/app/clients/reconciliation_client.py`, `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`; `backend/tests/api/v1/test_reconciliation_selection.py` (**NEW**), `backend/tests/test_reconciliation_client.py`.

**Dependencies:** Implemented Phase 1 contract and Phase 2 project authorization; no prior Phase 3 area.

**Tasks:**

- [x] `T1.1` **Change:** Add typed selection discovery, interactive search, type-scoped exact lookup, and complete list client calls.
  - **Target:** `backend/app/models/reconciliation.py` selection DTOs (**NEW symbols**); `backend/app/clients/reconciliation_client.py::ReconciliationClient`; `frontend/src/types/reconciliation.ts` selection interfaces (**NEW symbols**).
  - **Current → required:** Only manifest, legacy batch reconciliation, and prefix suggestions are wrapped → consume `reconciliation.record_selection` version 1 and `/records/types`, `POST /reconcile` with `X-Record-Selection: interactive` and one bounded query, `GET /records/{type}/details?target_id=...`, and `GET /records/{type}`.
  - **Implementation:** Use the configured client's base URL and fixed/same-service relative paths; reject absolute, cross-origin, or malformed discovery paths. Preserve existing manifest behavior but require a fresh Authority response for each new workspace. Model independent flags, field metadata and limits; validate record type, URI and positive numeric ID against the advertised type before offering selection. Adapt ranked candidate results without changing their scores; list records have no score. Do not turn 404, 409 `too_large_to_browse`, 422 unsupported/invalid, 503/unreachable, or malformed payloads into empty successes. No details call on save.
  - **Validation:** `V-1` mocks the Authority HTTP contract for both types, wrong-type IDs, limits, missing/invalid extension, cross-origin path, too-large/no-partial response, not-found, and outages; `V-7` checks the upstream contract.

- [x] `T1.2` **Change:** Expose read-only selection routes scoped to an authorized project and configured specification.
  - **Target:** `backend/app/services/reconciliation/service.py::ReconciliationService` (**NEW selection methods**), `backend/app/api/v1/endpoints/reconciliation.py` (**NEW** `.../{entity_name}/{target_field}/selection/capabilities`, `/selection/search`, `/selection/browse` routes); `frontend/src/api/reconciliation.ts::reconciliationServiceApi` (**NEW methods**).
  - **Current → required:** The suggest route takes a configured type but cannot browse or perform marked interactive/exact search → derive the type from the catalog specification after `require_project(Action.READ)`, not from a caller-selected URL or type; verify independent advertised flags and bounded positive limits. Treat `id:` plus malformed/zero/overflow/non-ASCII ID as input error, never fuzzy fallback; return unknown IDs as not-found. Validate only advertised property IDs against manifest settings and the specification's mappings; send optional context as ranking hints, not browse predicates. Keep backend error codes distinguishable in the existing `detail` envelope.
  - **Validation:** `V-1` checks authorization, no specification, no service type, independent flags, malformed inputs, supported context/limits, server failures, and absence of target/SIMS writes; `V-2` preserves old endpoints.

**Completion evidence:** Authorized calls yield versioned capabilities, bounded search or an exact record, and complete lists; unadvertised or failing operations return explicit errors without redirecting the browser.

### Area 2: Open and Resume a Continuous Review Workspace

**Objective:** A keyed specification opens a persistent source queue and pane without batch matching; all unsaved work is visible and isolated.

**Affected code:** `frontend/src/components/reconciliation/SpecificationsList.vue`, `ReconciliationView.vue`; `frontend/src/components/reconciliation/ReconciliationWorkspace.vue` (**NEW**), `frontend/src/stores/reconciliation.ts`, `frontend/src/types/reconciliation.ts`; `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` (**NEW**), `ReconciliationView.test.ts`, `frontend/src/stores/__tests__/reconciliation.test.ts`.

**Dependencies:** Area 1 discovery and existing preview/catalog routes.

**Tasks:**

- [x] `T2.1` **Change:** Add explicit Review entry and a Needs review queue beside a persistent selection pane.
  - **Target:** `SpecificationsList.vue::reconcileSpec`, `ReconciliationView.vue::handleReconcileSpec`, `ReconciliationWorkspace.vue` (**NEW**).
  - **Current → required:** Find Candidates eligibility gates the only specification action, and review decisions use repeated dialogs → keyed rows open review independently; show source label, encoded key, saved state/errors, notes, unsaved count, labelled next/previous/skip and stage selected/New controls. Keep invalid/duplicate/missing-key rows visible but unreviewable. Skip advances without staging or implying New; stage advances through visible Needs review rows without marking them saved. Keep existing grid/single-decision and manual-link flows available when the extension is missing or unsupported.
  - **Validation:** `V-3` runs a ten-row fixture (including skipped and initially unmatched rows) through buttons and keyboard; `V-4` checks unchanged legacy routes/grid.

- [x] `T2.2` **Change:** Persist only versioned, specification-scoped browser drafts and resume data.
  - **Target:** `frontend/src/stores/reconciliation.ts` (**NEW scoped workspace state/action**), `frontend/src/types/reconciliation.ts` (**NEW draft/resume types**), `ReconciliationWorkspace.vue` (**NEW**).
  - **Current → required:** Preview caches are scoped but neither drafts nor focus persist → store under a versioned key that includes project, entity, target field and per-row encoded business key; restore focused key, mode, text/field filters, sort, per-row query/notes and accepted/New decision drafts as *unsaved*. Retain `displayed_values` from source columns the operator actually saw for the Phase 2 source-change check. Reject/clear invalid-version or malformed entries explicitly without reusing another scope's state; do not store full target lists or a confirmed result selection. Show an error if browser storage cannot persist a draft rather than presenting it as durable.
  - **Validation:** `V-3` reloads the pane and switches rows/projects with equal labels/keys and compound keys; checks no carried selection, no fresh restored results, invalid-version handling, and unsaved indicators.

**Completion evidence:** Ten rows can be reviewed without Find Candidates or reopening a dialog; a reload restores only the correct scope's unsaved work.

### Area 3: Search and Browse Without Stale Selections

**Objective:** Search and Browse share trusted target identity while presenting their different completeness and confidence semantics.

**Affected code:** `frontend/src/components/reconciliation/ReconciliationWorkspace.vue` (**NEW**), `frontend/src/utils/reconciliationManifest.ts`, `frontend/src/api/reconciliation.ts`; `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` (**NEW**), `frontend/src/utils/__tests__/reconciliationManifest.test.ts`.

**Dependencies:** Areas 1–2.

**Tasks:**

- [x] `T3.1` **Change:** Implement capability-gated ranked search and exact-ID query states.
  - **Target:** `ReconciliationWorkspace.vue` (**NEW**), `frontend/src/utils/reconciliationManifest.ts::parseReconciliationManifest` (add independent selection-extension parsing without rejecting valid legacy metadata).
  - **Current → required:** The dialog uses prefix suggestions with no response guard → send operator text/context through the new backend API, with an advertised cap, initial 300 ms typeahead debounce and immediate Enter (cancel scheduled duplicate). Distinguish idle/loading/empty/error/unsupported/invalid-ID states. Ignore composition input; on row/project/specification/mode/query/context change invalidate selection immediately, cancel requests when possible and discard late successes *and errors* by request identity. Only current returned targets may be staged; numeric text without `id:` stays ranked text.
  - **Validation:** `V-3` uses delayed/reordered successes/failures, 300 ms timers, Enter/composition, context/limit checks, exact/wrong-type/unknown/malformed IDs, and row switches. `V-1` confirms remote errors are distinct.

- [x] `T3.2` **Change:** Download complete browse lists and filter/sort them locally.
  - **Target:** `ReconciliationWorkspace.vue` (**NEW**); `frontend/src/utils/reconciliationManifest.ts` selection field validation.
  - **Current → required:** No complete-list mode exists → fetch only when `browse_supported`; accept only `{items, completeness: "complete"}` within advertised limits and display `too_large_to_browse` as a specific result without partial items. Use only declared display/text/filter/sort fields. Apply literal case-insensitive substring text and AND field filters (`contains_ci`/scalar `equals`) locally; default order is label ascending, then numeric target ID, with a consistent locale/null policy for ties and alternate declared sorts. Switching mode preserves tab filters but clears selection unless the same record is present in current results. Preserve exact URI/ID from Authority for both modes; do not synthesize confidence or require details before save.
  - **Validation:** `V-3` covers duplicate labels/different IDs, nulls, `%`, `_`, `*`, field-filter conjunction, stable ties, unadvertised fields, incomplete/too-large/failed lists and search/browse parity; `V-7` checks complete-list upstream behavior.

**Completion evidence:** Every accepted selection belongs to the currently displayed response; Browse counts/filter/sort apply to a verified complete list and never masquerade as ranked results.

### Area 4: Save Atomically and Warn About Changed Decisions

**Objective:** Save only explicitly staged decisions, without losing drafts or overwriting newer visible decisions without warning.

**Affected code:** `frontend/src/stores/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationWorkspace.vue` (**NEW**), `ReconciliationView.vue`, `frontend/src/stores/__tests__/reconciliation.test.ts`, `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` (**NEW**), `ReconciliationView.test.ts`, `docs/other/RECONCILIATION_GUIDE.md`.

**Dependencies:** Areas 1–3 and existing Phase 2 batch/export routes.

**Tasks:**

- [x] `T4.1` **Change:** Send one batch and patch only its saved keys.
  - **Target:** `frontend/src/api/reconciliation.ts::reconciliationServiceApi` (**NEW batch method**), `frontend/src/stores/reconciliation.ts` (**NEW save/patch actions**), `ReconciliationWorkspace.vue` (**NEW**).
  - **Current → required:** `updateMapping` reloads full catalog and preview per decision → build `DecisionBatchRequest` with exactly one draft per keyed source row, its captured `displayed_values`, accepted URI/ID or reference-free `local-only`, and notes. On success use ordered `saved` and `counts.specification` to patch only affected preview rows, saved baseline and queue totals, then clear only successfully saved drafts; do not reload preview or call details/verification. On any failure, including `detail.issues` (`row_changed`, `protected_link`, etc.), keep all drafts unsaved and expose row issues for correction before a deliberate retry. Do not imply export or allocation on save.
  - **Validation:** `V-3` checks one request for ten staged rows, exact payload/response, changed-row/unauthorized rejection, untouched rows, and retained drafts; `V-2` protects backend atomicity and New-only outage behavior.

- [x] `T4.2` **Change:** Warn before replacing a changed saved decision for an affected key.
  - **Target:** `ReconciliationWorkspace.vue` (**NEW**), `frontend/src/stores/reconciliation.ts` (**NEW loaded-decision snapshots/comparison**).
  - **Current → required:** No long-lived view comparison exists → capture loaded saved decision state per encoded key from the catalog/preview before edits, fetch the authorized current catalog immediately before save (local, not Authority), and compare only drafted keys that would replace a changed decision. Include absence/presence, status, target URI/ID and notes in the comparison. Show old/current/staged values with confirm/cancel; leave *every* staged decision unchanged on warning, cancellation, or failed comparison. Confirmation sends the one batch without an expected-state field or automatic retry; report the advisory comparison-to-write race (R33). Refresh baseline only for keys returned by a successful batch.
  - **Validation:** `V-3` simulates changed same key, newly added decision for previously empty key, unrelated-key change, cancelled/confirmed warning, compare-read outage, and post-comparison change; assert drafts survive and only an explicit confirmation calls save once.

- [x] `T4.3` **Change:** Keep Save decision and Export distinct in UI and guidance.
  - **Target:** `ReconciliationView.vue::handleExportToMapping` and export guidance, `ReconciliationWorkspace.vue` (**NEW**), `docs/other/RECONCILIATION_GUIDE.md` review/export sections.
  - **Current → required:** The view already exposes Export, but its guidance still says accepted links can be exported unverified during an outage → label workspace batch Save decision separately from the existing explicit Export; state that accepted exports require successful verification, while valid New-only saves/exports work after an open workspace loses Authority. Preserve existing sidecar status/protection handling and legacy grid, without calculating application state.
  - **Validation:** `V-3`, `V-4` check labels, cold-start and already-open outages, and Save/Export independence; `V-6` checks keyboard operation; `V-8` checks guidance and links.

**Completion evidence:** Batch success confirms only saved keys; a failed batch or declined conflict leaves drafts; export remains a separate verified action.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` | `T2.1`, `T4.1` | `V-3`, `V-4`, `V-6` | `VM-7`: ten rows, skips, labelled/keyboard controls, one batch, patched keys/counts, failure retention. |
| `PH3-AC-2` | `T1.1`, `T1.2`, `T3.1` | `V-1`, `V-3`, `V-7` | `VM-8`: bounded/contextual search and exact ID, malformed/unknown and late-response safety. |
| `PH3-AC-3` | `T1.1`, `T3.2` | `V-1`, `V-3`, `V-7` | `VM-8`: complete-only local browse, literal/AND/stable ordering, parity without details or confidence. |
| `PH3-AC-4` | `T1.2`, `T2.1`, `T4.1`, `T4.3` | `V-1`, `V-2`, `V-3`, `V-4`, `V-6` | `VM-9`: live cold-start discovery, legacy fallback, already-open outage/New-only flow, distinct Save/Export. |
| `PH3-AC-5` | `T2.2`, `T3.1` | `V-3`, `V-4`, `V-6` | `VM-9`: versioned resume, scope isolation, composition and request ordering. |
| `PH3-AC-6` | `T4.1`, `T4.2` | `V-2`, `V-3` | `VM-10`: affected-key warning with drafts preserved, no unrelated warning, accepted race/no retry. |

## Validation And Testing

Commands run from the Shape Shifter root unless otherwise indicated. Results below were recorded after implementation on 2026-11-20; the baseline column keeps the pre-implementation state where it differs.

| ID | Check and target | Command or executable method | Expected result | Baseline (2026-11-20) |
| --- | --- | --- | --- | --- |
| `V-1` | Authorized selection adapter and HTTP routes; `backend/tests/test_reconciliation_client.py`, `backend/tests/api/v1/test_reconciliation_selection.py` (**NEW**) | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/test_reconciliation_client.py backend/tests/api/v1/test_reconciliation_selection.py` | Mock the Phase 1 response for `feature_type`/`country`; assert exact IDs, per-flag gating, max limits, field/context validation, wrong-type/unknown ID, no cross-origin URL, distinct error codes/no partial list, read authorization and no writes. | Pass (exit 0; 73 client tests plus 34 route tests). The route tests cover one type only; per-type parity stays with `V-7` and Phase 4. |
| `V-2` | Phase 2 batch/export regression; existing `backend/tests/api/v1/test_reconciliation_decisions_batch.py`, `test_reconciliation_export.py`, `backend/tests/test_reconciliation_client.py` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/api/v1/test_reconciliation_decisions_batch.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/test_reconciliation_client.py` | Batch atomicity, changed-row and protected-link errors, verified accepted exports, New-only outage and existing client behavior remain correct. | Pass (exit 0; 74 tests). |
| `V-3` | Workspace component/state/API; `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` (**NEW**), `frontend/src/stores/__tests__/reconciliation.test.ts`, `frontend/src/utils/__tests__/reconciliationManifest.test.ts`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts` | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts src/stores/__tests__/reconciliation.test.ts src/utils/__tests__/reconciliationManifest.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | Enabled-capability fixtures with duplicate names/different IDs and compound keys; ten-row save, errors, request races, filter literals, versioned storage, composition, stale warning, same-key and unrelated-key changes. | Pass: 4 files, 80 tests (18 workspace, 12 store, 24 manifest, 26 view). |
| `V-4` | Legacy grid/view/store/manifest regressions | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationView.test.ts src/components/reconciliation/__tests__/ReconciliationGrid.test.ts src/stores/__tests__/reconciliation.test.ts src/utils/__tests__/reconciliationManifest.test.ts` | Existing review, preview loading, matching, manual link, and manifest validation still pass. | Pass: 4 files, 87 tests. Expected logged errors are from error-path fixtures. |
| `V-5` | Frontend types and read-only lint for changed files | `cd frontend && pnpm exec vue-tsc --noEmit && pnpm exec eslint src/components/reconciliation/ReconciliationView.vue src/components/reconciliation/ReconciliationWorkspace.vue src/components/reconciliation/SpecificationsList.vue src/stores/reconciliation.ts src/api/reconciliation.ts src/types/reconciliation.ts src/utils/reconciliationManifest.ts` | Zero type errors and lint errors; extend lint list to changed tests. | Pass: `vue-tsc` exit 0; eslint 0 errors on the source files and the changed tests. |
| `V-6` | Manual keyboard and error-state check against a controlled, capability-enabled service fixture | For the next follow-up, reuse prior pass evidence and run only the changed or unverified cases in one prepared browser session; see **V-6 Targeted Follow-up** below. Repeat prior passing flows only if relevant code changes. | Focus remains visible, no bare-letter decisions during typing, no inherited selection, unsaved drafts retained; B shows neither A's draft nor selection, and A's draft remains after return/reload. Cold-start requires a response, but opened New-only workflow and legacy review remain usable. This is a controlled UI check, not Phase 4 live pilot evidence. | **Pass (2026-11-20).** The four targeted follow-up checks passed; prior unaffected scenarios were reused. See **V-6 Targeted Browser Follow-up (2026-11-20)** below. Saved-decision inspection is deferred to R34 and is not a Phase 3 acceptance gate. |
| `V-7` | Upstream contract fixture | `cd ../sead_authority_service && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/api/test_record_selection.py` | Marked interactive search, exact-ID details, independently gated discovery and complete-or-too-large list behave as consumed by `V-1`/`V-3`. | Pass: 55 tests; one Starlette deprecation warning. Shipped pilot flags remain off. |
| `V-8` | User guidance and document links | `bash scripts/ci/check_doc_links.sh`; manually check the review/export sections of `docs/other/RECONCILIATION_GUIDE.md` because the script does not check every proposal/other document. | Documentation names the enabled/unsupported modes, Save decision versus Export, outage behavior and verification gate; references resolve. | Links pass (exit 0). Guidance reviewed against the implemented labels and outage behavior in section 3.0 and section 4. |

For `V-3`, use controlled deferred promises and fake timers, not a live service, to prove that scheduled and out-of-order results cannot re-enable acceptance. For `V-1`, inject a mock Authority transport and authorized temporary projects; test response bodies and status codes, not only helper output. Phase 4 owns the live paired-service test and response-time baseline.

### V-6 Fixture And Runbook

Prepared on 2026-11-20 against the Phase 1 disposable Podman database `sead-sims-candidate-verification` (`127.0.0.1:55432/sead_staging`). Both fixture files are local and untracked: `data/` is gitignored in Shape Shifter, and `tmp/` is gitignored in the Authority Service.

**Fixture artifacts**

| Artifact | Purpose |
| --- | --- |
| `data/projects/v6-fixture/shapeshifter.yml` | Throwaway project with `feature_type_src` (single-column key `feature_code`) and `country_src` (compound key `project_code`/`country_code`), 12 inline rows each. `FT-011`, `FT-012`, `SE-011`, and `SE-012` have no matching target record. `public_id` columns hold placeholder IDs, because a null `public_id` becomes `NaN` and `NaN` is not JSON-serializable. |
| `data/projects/v6-fixture/shapeshifter.reconciliation.yml` | Keyed specifications `feature_type_src.feature_type_name` (`service_type: feature_type`) and `country_src.country_name` (`service_type: country`), no saved decisions, so every row starts in Needs review. |
| `../sead_authority_service/tmp/v6.config.yml` | Copy of `config/config.yml` with all five pilot flags enabled for both types and its `@include` paths rewritten to `../config/`. Regenerate it from the tracked file before reuse so it cannot drift. |

**Prerequisites**

```bash
podman start sead-sims-candidate-verification
cd ../sead_authority_service
export PGPASSWORD="$(podman exec sead-sims-candidate-verification printenv POSTGRES_PASSWORD)"
export SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=127.0.0.1
export SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=55432
export SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
export SEAD_AUTHORITY_OPTIONS_DATABASE_USER=postgres
CONFIG_FILE=tmp/v6.config.yml .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

`PGPASSWORD` supplies the password that `config/config.yml` does not store; it stays in the shell and never in a tracked file.

Shape Shifter needs the local service URL and the development principal. `SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL` in `.env` points at `host.docker.internal:8000`, which does not resolve on the Linux host, so export the loopback URL for the backend process. Register the fixture in the development authorization store once, then start both servers with the same four variables:

```bash
cd ../sead_shape_shifter
SHAPE_SHIFTER_ENVIRONMENT=development \
SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false \
SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer \
SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-dev.sqlite3 \
SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://localhost:8000 \
uv run sead-authorization dev-bootstrap

SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://localhost:8000 make backend-run
make frontend-run
```

**Verified readiness (2026-11-20), no browser involved**

| Check | Result |
| --- | --- |
| Fixture discovery and load | `v6-fixture` is listed and loads with no `load_errors` or `load_warnings`; catalog business keys validate. |
| Preview rows | 12 keyed rows per specification, no row errors, keys `FT-001`–`FT-012` and `V6\|SE`–`V6\|YY`. The rows serialize strictly. |
| Capability discovery over HTTP | `reconciliation.record_selection` is `{"version":1,"types_path":"/records/types"}`; `feature_type` and `country` each report all five flags `true` with 500-row and 50-result limits. |
| Complete lists | `GET /records/feature_type` returns 156 items with `completeness: complete`; `GET /records/country` returns 266. Both are far below the advertised row and byte limits. |
| Ranked search | `castle` returns `Castle` (`feature_type/576`, score 100); `swed` returns `Sweden` (`country/205`); `zzzqqqxxx`, `Atlantis`, and `V6 Unlisted Territory` return no items. |
| Exact lookup | `id: 1` returns `Afghanistan` (`country/1`); `id: 99999999` returns `record_not_found` (404), which the workspace surfaces as an exact-mode empty result. |
| Record URIs | `feature_type/…` and `country/…` match the type segment Shape Shifter validates, so neither type is dropped as a wrong-type record. |
| Shape Shifter adapter | `get_selection_capabilities`, `browse_selection`, and `search_selection` all succeed against the live Authority for both specifications. |

**Cleanup after the check**

Delete `data/projects/v6-fixture/` and rerun `dev-bootstrap`. Remove `../sead_authority_service/tmp/v6.config.yml`, stop the container, and revert any saved decision or `shapeshifter.mapping.yml` the check created.


## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed selection bridge/routes and focused backend tests | `backend/app/models/reconciliation.py`, `backend/app/clients/reconciliation_client.py`, `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/test_reconciliation_client.py`, `backend/tests/api/v1/test_reconciliation_selection.py` (**NEW**) | `T1.1`, `T1.2` | `V-1`, `V-2` pass. |
| Typed browser API and extension parsing | `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/utils/reconciliationManifest.ts`, `frontend/src/utils/__tests__/reconciliationManifest.test.ts` | `T1.1`, `T1.2`, `T2.2`, `T3.1`, `T3.2`, `T4.1` | `V-3`, `V-5` pass. |
| Persistent workspace, navigation, scoped drafts, saved-row patch and UI tests | `frontend/src/components/reconciliation/SpecificationsList.vue`, `ReconciliationView.vue`, `ReconciliationWorkspace.vue` (**NEW**), `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` (**NEW**), `ReconciliationView.test.ts`, `frontend/src/stores/__tests__/reconciliation.test.ts` | `T2.1`, `T2.2`, `T3.1`, `T3.2`, `T4.1`, `T4.2`, `T4.3` | `V-3`–`V-6` pass; no full preview reload on batch success. |
| Updated reviewer guidance | `docs/other/RECONCILIATION_GUIDE.md` | `T4.3` | `V-8` passes and instructions match implemented behavior. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| 1. Connect authorized record selection | Done | Phase 1/2 outputs | Capabilities, search, exact lookup, and browse routes plus client transport. `V-1`, `V-2`, `V-7` pass. |
| 2. Open and resume continuous review | Done | Area 1 | `T2.1` and `T2.2` pass focused tests and browser checks. The follow-up confirms visible focus through `FT-010`, draft restoration after reload, and project isolation. |
| 3. Search and browse safely | Done | Areas 1–2 | `T3.2` passes the browser filter check; the follow-up also confirms the malformed-`id:` detail and visible focus behavior. |
| 4. Save and warn | Done | Areas 1–3 | One batch save, advisory pre-save comparison, Save/Export guidance. `V-2`, `V-3`, `V-8` pass; the browser saved and exported two New decisions during an outage. A Saved decisions view is deferred to R34. |

## Execution Record (2026-11-20)

Implemented `T1.1`–`T4.3` on Shape Shifter branch `reconciliation-search-and-browse` from `c465a318`. The Authority Service was not modified; it was read at `1f3f1b8` and its contract tests were re-run.

Design decisions taken within the plan's scope:

- Selection failures use the existing `detail` envelope with distinct codes: `RECORD_SELECTION_UNSUPPORTED`, `RECORD_SELECTION_INVALID_INPUT`, `RECORD_SELECTION_TOO_LARGE`, `RECORD_SELECTION_UNAVAILABLE`, `RECORD_SELECTION_INVALID_RESPONSE`.
- An exact lookup for an unknown ID returns `{mode: "exact", items: []}` instead of an HTTP error, so the pane can distinguish it from an empty ranked search without inventing a New decision.
- Declared context is validated against the manifest's property settings and forwarded as `properties`; the shipped pilot types declare none, so the workspace offers no context controls.
- Drafts are stored under `shapeshifter.reconciliation.workspace` version 1, scoped by project, entity, target field, and encoded key. Absent or blocked browser storage is reported rather than treated as durable.
- A successful batch clears reconciliation messages for the saved keys, because the batch validated those rows against current source data.

Changed deliverables: `backend/app/models/reconciliation.py`, `backend/app/clients/reconciliation_client.py`, `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/api/v1/test_reconciliation_selection.py` (NEW), `backend/tests/test_reconciliation_client.py`, `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/utils/reconciliationManifest.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationWorkspace.vue` (NEW), `ReconciliationView.vue`, `SpecificationsList.vue`, the four affected test files, and `docs/other/RECONCILIATION_GUIDE.md`.

### V-6 Resume Check (2026-11-20)

The browser used the controlled fixture and a same-origin Vite proxy to the local development API. The shipped Authority configuration was not changed. The fixture catalog was restored and the generated mapping sidecar removed after the check.

- **Initially failed, selection safety (`T3.2`, `PH3-AC-3`):** Set the Browse filter to `*`, return to Search, select Castle, then switch to Browse. Browse shows `0 of 156 complete records`, but **Stage selected & next** remains enabled. The selected record is in the complete list but not in the displayed filtered results. `onModeChange` now preserves the selection only if the record is in the visible results, and Browse clears a selection when a filter hides it.
- **Initially failed, resume focus (`T2.2`, `PH3-AC-5`):** Focus `FT-012` without staging a decision for it, with other rows staged, then reload and reopen the same specification. Storage contains `focusedKey: FT-012` and both drafts are restored, but the pane says **Select a row**. `restoreDraft` now restores focus when the key is still in the reviewable queue, even if that row has no draft entry.
- **Initially failed, shortcut (`T2.1`, `PH3-AC-1`):** After selecting Castle, `Alt+Enter` from the search input or the focused result does not stage or advance. From the search input it also clears the selection. The workspace now handles shortcuts during capture and skips the search field's normal Enter action for `Alt+Enter`.
- **Passed portions:** Review opened without Find Candidates for both specifications. Ten consecutive feature rows were traversed with Next/Enter and `Alt+Right`; Skip did not add a draft, and `Alt+Backspace` staged New. Search debounce and immediate Enter, exact and invalid IDs, the empty exact response, complete lists of 156 feature types and 266 countries, literal `%`, `_`, `*` filtering without additional browse requests, simulated composition, row/specification isolation, and restoration of unsaved drafts without a target selection or result list were checked. One batch saved two drafts and reduced the queue by two. With Authority stopped after opening, a New-only decision saved and exported; after a cold start offline, the legacy grid displayed saved decisions and an offline manual link was saved.
- **Not verified manually:** Cross-project isolation, visible focus throughout a full keyboard-only ten-row review, and saved-decision inspection without leaving an already-open workspace during an outage. The browser check must be repeated after the failures are corrected. The invalid-ID response also contains a useful validation message, but the UI displays only `Request failed with status code 400`.

The resumed checks passed: combined `V-1`/`V-2` backend tests; the five-file union of `V-3`/`V-4` (105 tests); `V-5` type checking and lint (zero errors, one Prettier warning in the workspace test); `V-7` (55 tests, one Starlette deprecation warning); and the `V-8` link checker. The earlier manual guidance review was not repeated.

The focused regressions in `frontend/src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` cover both selection-safety scenarios, restore `K3` as the focused row while retaining `K2`'s staged New decision, and stage from `Alt+Enter` on both the search input and selected result. `rtk pnpm --dir frontend exec vitest run src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` passed all 21 tests. `rtk pnpm --dir frontend exec vue-tsc --noEmit` passed. `rtk pnpm --dir frontend exec eslint src/components/reconciliation/ReconciliationWorkspace.vue src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` reported zero errors and one existing Prettier warning at the test setup.

Repeat the V-6 browser check before treating `PH3-AC-1`, `PH3-AC-3`, or `PH3-AC-5` as accepted; the remaining V-6 findings and unverified cases above remain open.

### V-6 Browser Rerun (2026-11-20)

Used `v6-fixture` through the same-origin Vite proxy. The controlled Authority advertised 53 types while online; its shipped configuration was not changed. Authority was stopped only for the outage checks.

- **Passed:** Both keyed specifications opened without Find Candidates and each showed 12 rows. The country queue showed compound keys such as `V6|SE` and did not inherit feature-type drafts. Feature-type Search returned `Castle` (`feature_type/576`); `Alt+Enter` staged and advanced from both the search input and selected result. Country Search returned `Sweden` (`country/205`), and its complete Browse list showed 266 records. The feature-type Browse list showed 156 records.
- **Passed:** With Browse filtered to `*`, selecting Castle in Search and returning to Browse cleared the selection and disabled **Stage selected & next**. Typing notes did not stage a decision; a simulated composing `Alt+Enter` did not stage or advance; `Alt+Down` skipped without adding a draft. A note staged with New remained after reload.
- **Passed after reload:** With four drafts staged and `FT-012` focused but unstaged, reloading and reopening the same specification restored `FT-012`, all four drafts, and Browse mode. Target selection and result rows were not restored.
- **Failed, visible focus:** Tab and Enter focused `FT-001`; `Alt+Right` advanced the review panel through `FT-010`, but `:focus-visible` stayed on `FT-001` for the remaining rows. Logical navigation completed, but visible focus did not follow the reviewed row.
- **Passed during outage:** With Authority stopped after opening the workspace, a batch saved two New decisions and reduced Needs review from 12 to 10. Export wrote local-only approvals for `FT-004` and `FT-005` to the mapping sidecar; a second export returned zero new approvals. After a cold reload, the UI reported Offline, the legacy grid displayed `New (2)`, and a manual link for `FT-006` with target ID `9999` saved. Opening the new workspace cold-start offline showed that review was unavailable and offered the legacy grid.
- **Not verified:** Cross-project isolation. Inspecting individual saved decisions without leaving the already-open workspace during an outage was not tested; that feature is deferred to R34 and is not a Phase 3 acceptance gate. The cold-start legacy grid did show both saved New decisions. Search, Browse, queue, and draft scoping were checked only within `v6-fixture`.

### V-6 Keyboard Focus Follow-up (2026-11-20)

- **Change:** `focusRow` moves DOM focus to the newly active queue row after Vue updates it. A queued focus callback does nothing if the reviewer has already moved to another row.
- **Regression test:** `ReconciliationWorkspace.test.ts` mounts the workspace in the document and verifies that `Alt+Right` moves `document.activeElement` from the first row to the second.
- **Validation:** `cd frontend && rtk pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` passed 22 tests. `cd frontend && rtk pnpm exec vue-tsc --noEmit` passed. ESLint reported zero errors and one existing Prettier warning in the test setup.
- **Status:** The targeted browser follow-up below confirms visible focus follows `FT-001` through `FT-010`; the component regression remains passing.

### V-6 Invalid-ID Message Follow-up (2026-11-20)

- **Change:** `selectionErrorMessage` now prefers an Authority response's `detail.message` over the generic Axios `Error.message`.
- **Regression test:** The malformed-`id:` test uses an Axios-like error with both messages and asserts that the invalid-input alert shows `Enter a whole number.` and not `Request failed with status code 400`.
- **Validation:** `cd frontend && rtk pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationWorkspace.test.ts` passed 22 tests. `cd frontend && rtk pnpm exec vue-tsc --noEmit` passed. ESLint reported zero errors and one existing Prettier warning in the test setup.
- **Status:** The message behavior passes the component test and the targeted browser follow-up below.

### V-6 Targeted Follow-up

The full browser run on 2026-11-20 took about 23 minutes. The prior run already passed Search/Browse behavior, notes and composition, New-only save/export during an outage, cold-start offline fallback, and offline manual linking. Since the changes since that run affect row focus and malformed-ID messaging, and project isolation was not tested, reuse the unaffected results rather than repeating those scenarios.

Prepare both controlled projects and start the required services before the timed browser check. Keep one browser session open; no Authority restart or outage simulation is needed for this follow-up.

1. In project A, stage a draft for one row and select a target for another. Open project B with the same entity, target field, and business keys; confirm B has neither A's draft nor its selected target.
2. Return to A and reload. Confirm A's draft remains. Do not expect the target selection to restore; target results and selections are not persisted.
3. Use `Alt+Right` to traverse the ten-row queue and confirm visible focus follows the active row through `FT-010`.
4. Search for malformed input such as `id: abc`; confirm the visible alert shows the validation detail instead of Axios's generic status message.

Reuse prior V-6 pass evidence for every unaffected scenario. Rerun a previously passed scenario only if a later code change can affect it. The four targeted checks passed; results are recorded below.

The Phase 3 handoff requires Phase 1 and Phase 2 outputs; both were present before implementation, satisfying that prerequisite.

### V-6 Targeted Browser Follow-up (2026-11-20)

Used controlled projects `v6-isolation-a` and `v6-isolation-b`, with the same `feature_type_src.feature_type_name` specification and keys `FT-001` through `FT-012`. No decision was saved during this run.

- **Passed, project isolation:** In A, staged New for `FT-001` and selected Castle (`feature_type/576`) for `FT-002`. B showed `0 unsaved decisions`; `FT-002` had no selected target or results, and **Stage selected & next** was disabled. Returning to A and reloading restored its one unsaved New decision. The workspace reported that no target selection or result list was restored.
- **Passed, keyboard focus:** With keyboard modality established, used `Alt+Left` to return to `FT-001`, then `Alt+Right` through `FT-010`. At each step, `:focus-visible` matched the active row (`workspace-row-0` through `workspace-row-9`).
- **Passed, malformed ID:** Searching `id: abc` displayed `Enter 'id:' followed by a positive whole-number target ID, for example 'id: 42'.` instead of Axios's generic status message.
- **Reused prior evidence:** The unchanged Search/Browse, composition, outage, cold-start, and Save/Export checks from the earlier V-6 browser rerun were not repeated. Saved-decision inspection inside the workspace remains deferred to R34 and is not a Phase 3 acceptance gate.

### VM-9 Independent Corroboration (2026-11-20)

The `V-6 Targeted Browser Follow-up` above already passed project isolation, superseding the earlier "Not verified" notes in the two preceding sections. This run adds independent evidence on the pinned pilot pair, and an automated guard so the behaviour cannot regress silently.

- **Environment:** Shape Shifter `7340510f` and Authority Service `1f3f1b8`, both built from published refs and pinned by image tag; one shared snapshot database.
- **Fixtures:** New controlled projects `vm9-alpha` and `vm9-beta`, each a `fixed` `feature_type` entity with the same target field `feature_type_name` and the same business key `vm9-shared`. Only the project name differs.
- **Passed, live catalog isolation:** With `vm9-alpha` holding an accepted decision for `vm9-shared` to `feature_type/12`, `vm9-beta` reported no decision for the same key. Saving `vm9-shared` to `feature_type/576` in `vm9-beta` left `vm9-alpha` unchanged at `12`. Each project persisted and read back only its own decision.
- **Passed, automated scope regression:** `ReconciliationWorkspace.test.ts` gained a cross-project case that stages a decision in one project, mounts a second project with identical entity, field, and keys, and asserts the second shows no draft, no restored notice, and no carried-over selection, then returns to the first and asserts its draft is restored. The check was mutation-tested: making the draft store ignore the project name fails it with `expected 'Save decisions (1)' to contain '0'`, and keying the scope without the project fails the scope assertion. Suite result: 23 tests in that file, 35 across it and the store test, and 102 across `src/components/reconciliation` plus the store test; `vue-tsc` and ESLint are clean.
- **Limit:** This host has no browser available and Playwright does not support Ubuntu 26.04, so these runs are API- and component-level rather than browser-level. The browser-level project-isolation result remains the `V-6 Targeted Browser Follow-up` above, which this evidence corroborates rather than replaces.

## Definition Of Done

- [x] Every `PH3-AC-*` criterion has passing task and validation evidence for `VM-7`–`VM-10`.
- [x] All four areas and their tests, browser/API contracts, and reviewer guidance are complete.
- [x] `V-1`–`V-8` pass. `V-6` targeted browser follow-up passed; unaffected scenarios reuse the earlier browser evidence.
- [x] Existing matching, single-decision routes, catalog reads, verified export, manual links and sidecar behavior pass regressions.
- [x] Save success patches only saved keys/counts; failures and stale-view warnings retain drafts; no source IDs/labels, target records or SIMS state change during review.
- [x] No server precondition, automatic retry, production pilot flag change, or Phase 4 claim is introduced.
- [x] If the Authority contract, baseline repository state, or Phase 2 response differs from the verified plan, stop implementation and report the discrepancy rather than substitute a new design. No such discrepancy was found.

## Risks And Open Questions

- The shipped pilot flags are disabled. Phase 3 tests must enable them only in a controlled Authority fixture; **do not** present the UI's existence as a Phase 4 capability-release result.
- A catalog change between the client comparison and the locked batch write can still replace the same key. The warning is advisory, not a server-enforced conflict. R33 remains deferred.
- Inspecting saved decisions within the Search/Browse workspace is deferred to backlog R34 and is not required for Phase 3 acceptance.
- **Observed while preparing the V-6 fixture:** `GET /projects/{project}/reconciliation/{entity}/{field}/preview` returns rows unchanged, and a `fixed` entity whose `public_id` column is null normalizes that column to `NaN`. Starlette serializes JSON with `allow_nan=False`, so such a preview raises `ValueError: Out of range float values are not JSON compliant`. This is pre-existing behavior outside the Phase 3 deliverables, not introduced by these changes, and it affects any keyed entity with unset target IDs. The fixture works around it with placeholder `public_id` values; whether to convert `NaN` to `null` in the preview response needs its own decision.
