# Phase 4 Task Plan: FK Integration And Legacy Parity

## Phase Summary

**Goal:** Move foreign-key key and extra-column suggestions to the shared, draft-aware column-availability response and remove the editor's dependency on the legacy flattened suggestion path.

**Readiness:** Validated. Phase 4 is marked ready in the [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md). The Phase 2 endpoint returns ordered per-FK candidates, and Phase 3's shared composable is available and covered by passing tests. No unresolved decision changes the frontend contract or Phase 4 behavior.

**Dependencies and constraints:** Use the existing `POST /projects/{project_name}/entities/{entity_name}/column-availability` response. Match candidate entries to the FK by response index and target entity. Use the resolver's before- and after-unnest local-key lists without reproducing stage logic in TypeScript. Keep all key selectors as free-text comboboxes, preserve `@value` directive suggestions and validation, and keep the legacy GET response contract unchanged for compatibility.

**Source documents:** [proposal](STAGE_AWARE_COLUMN_SUGGESTIONS.md), [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md), and [Phase 3 task plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_3_TASK_PLAN.md).

**Phase acceptance criteria**

1. `PH4-AC-1` (from `P-AC-2`, `P-AC-4`, `P-AC-5`, `P-AC-8`): FK local selectors reflect FK order, while remote-key and extra-column source selectors use the selected parent's processed output, including `system_id` where available.
2. `PH4-AC-2` (from `P-AC-3`, `P-AC-6`): The FK suggestion path uses the current unnest shape, no longer relies on the legacy flattened calculation, and still permits fields absent from the candidate list.

## Repository Findings

**Repository basis:** Branch `stage-aware-column-suggestions`, commit `a1b35971`, planning date 2026-10-08. The worktree is clean.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `frontend/src/components/entities/EntityFormDialog.vue::useColumnAvailability` and `refreshColumnAvailability` watcher | The dialog makes one debounced request for the serialized current draft, including its `foreign_keys`, and already receives `ColumnAvailabilityResponse`. Its `ForeignKeyEditor` binding does not pass the response's `foreign_keys` array. | Pass the existing per-FK response to the editor; do not add another request or composable instance. |
| `frontend/src/components/entities/ForeignKeyEditor.vue::loadLocalColumns`, `loadRemoteColumns`, and template comboboxes | The editor calls `useColumnIntrospection` on focus, flattens legacy categories, caches local/remote items, and uses one remote list for both Remote Keys and extra-column sources. The controls are `v-combobox` inputs. | Replace legacy column loading with per-FK response fields; keep remote-key and extra-source candidates distinct and preserve free-text entry. |
| `frontend/src/api/entities.ts::ForeignKeyColumnCandidates` and `ColumnAvailabilityResponse` | Each FK response contains `index`, `entity`, `local_keys_before_unnest`, `local_keys_after_unnest`, `remote_keys`, and `extra_column_sources`. | Map only the matching response entry. Present the two resolver-provided local-key lists without inspecting the YAML unnest configuration or recalculating availability. |
| `src/column_availability.py::_link_candidates` and `backend/app/services/stage_aware_column_service.py::get_column_availability` | The resolver walks foreign keys in configured order and computes local candidates before and after unnest. The service resolves remote candidates from each selected parent's processed columns. | Keep order, unnest timing, and parent processing in Python; do not change the resolver or endpoint contract in this phase. |
| `frontend/src/composables/useColumnIntrospection.ts` and frontend imports | `ForeignKeyEditor.vue` is the only frontend caller of the legacy composable. | Remove the unused frontend composable after migrating the editor. |
| `backend/app/api/v1/endpoints/columns.py::get_available_columns` and `backend/tests/api/v1/test_columns.py::test_legacy_get_keeps_flat_response_contract` | The legacy GET remains a separately exposed API with a tested flat response contract. | Keep the route, service, and response contract unchanged; the FK editor must stop using it. |
| `tests/process/test_column_availability.py::test_foreign_key_candidates_follow_link_order_and_processed_parent_columns`, `backend/tests/services/test_stage_aware_column_service.py`, and `backend/tests/api/v1/test_columns.py` | Existing tests cover FK ordering, parent-derived columns and `system_id`, current unnest behavior, unsaved drafts, and the legacy GET contract. | Extend the endpoint test for multiple ordered FK entries; retain the existing core and service regressions. |

**Baseline results:** `EntityFormDialog.test.ts` and `ForeignKeyEditor.test.ts` passed: 11 tests. The focused core/backend column-availability tests passed: 12 tests. The Phase 3 full frontend suite passed: 41 test files and 666 tests. Targeted ESLint and `pnpm --dir frontend build` also passed in Phase 3; Vite emitted non-fatal dependency and chunk-size warnings.

## Scope

**In scope**

- Pass the shared per-FK response entries from `EntityFormDialog` to `ForeignKeyEditor`.
- Bind local keys, remote keys, and extra-column remote sources to their corresponding resolver results.
- Preserve directive suggestions and validation, FK edit behavior, and free-text entry.
- Remove the frontend-only legacy introspection composable once it has no callers.
- Extend backend endpoint coverage for response ordering across multiple FKs.

**Out of scope**

- Changes to the Python resolver, stage-aware service, response model, or draft-aware endpoint behavior.
- Removal or alteration of the legacy GET endpoint and its flat response contract.
- Changes to FK validation, parent selection, FK extra-column syntax, filter controls, or the Phase 3 request debounce.
- Making candidate absence a validation or save error.

## Work Breakdown

### Area 1: Connect FK Controls To The Shared Response

**Objective:** Supply every FK control with candidates from the same debounced response used by the other entity-editor controls.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/ForeignKeyEditor.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, and `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`.

**Dependencies:** Phase 3 shared composable and Phase 2 per-FK response contract.

**Tasks:**

* [x] `T4.1` **Change:** Pass per-FK candidate results into the FK editor.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue` relationship-tab binding; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  * **Current → required:** The dialog receives `columnAvailability.foreign_keys` but passes no candidate data to `ForeignKeyEditor`. Its test stub accepts only `modelValue`.
  * **Implementation:** Add a typed optional prop for the per-FK candidates and bind `columnAvailability?.foreign_keys ?? []`. Extend the test fixture and stub to verify the matching response is passed while FK edits continue to update the serialized draft and trigger the shared request.
  * **Constraints:** Do not add a second request in `ForeignKeyEditor`; keep FK changes in the dialog's existing request state.
  * **Validation:** `V-1`.
* [x] `T4.2` **Change:** Bind each FK selector to its operation-specific candidates.
  * **Target:** `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`.
  * **Current → required:** Local and remote selectors load flattened categories on focus, and the remote-key list is also used for extra-column sources. Use the response entry whose `index` and `entity` match the current FK.
  * **Implementation:** Populate Local Keys from the response's before- and after-unnest candidate lists, deduplicating only for presentation. Populate Remote Keys from `remote_keys` and each extra-column Remote Column selector from `extra_column_sources`. Clear candidates when no response entry matches the current FK. Test multiple FKs with different candidates, response updates after a parent change, the separate remote/source lists, and manually entered keys absent from suggestions.
  * **Constraints:** Do not infer stage availability from the draft or merge candidates from different FKs. Keep selectors as `v-combobox`; preserve `@value` suggestions and the existing directive validation behavior.
  * **Validation:** `V-1`.

**Completion evidence:** Each FK control displays only candidates for its matching FK and operation; FK order and parent changes update those candidates, while unlisted values remain enterable.

### Area 2: Retire The Editor's Legacy Path And Verify Parity

**Objective:** Remove the editor's dependency on config-only flattened suggestions while retaining compatibility for the separately exposed legacy GET endpoint.

**Affected code:** `frontend/src/composables/useColumnIntrospection.ts` (DELETE), `frontend/src/components/entities/ForeignKeyEditor.vue`, and `backend/tests/api/v1/test_columns.py`.

**Dependencies:** `T4.2` for replacing the editor's legacy fetch path; Phase 2 endpoint and core resolver tests.

**Tasks:**

* [x] `T4.3` **Change:** Remove the unused frontend column-introspection composable and fetch/cache path.
  * **Target:** `frontend/src/composables/useColumnIntrospection.ts` (DELETE); `frontend/src/components/entities/ForeignKeyEditor.vue`.
  * **Current → required:** The composable has one frontend caller, which is the FK editor. The editor currently fetches and flattens the legacy GET response on focus.
  * **Implementation:** Remove the import, composable call, legacy cache, and focus-triggered column loads after `T4.2` uses the shared response. Keep directive lookup and validation. Leave the backend GET route, service, and flat response contract unchanged for compatibility.
  * **Constraints:** Do not remove the backend endpoint or change its response in this phase; no FK suggestion control may continue to use it.
  * **Validation:** `V-1`, `V-3`, `V-4`, and `V-5`; retain the legacy GET contract assertion in `V-2`.
* [x] `T4.4` **Change:** Verify endpoint response order and per-parent FK results for a multi-FK draft.
  * **Target:** `backend/tests/api/v1/test_columns.py::test_post_uses_unsaved_draft_and_returns_operation_and_stage_candidates`.
  * **Current → required:** The endpoint test submits one FK, while the core resolver test already covers link order for multiple FKs.
  * **Implementation:** Submit at least two FKs with distinct target entities and assert response `index` and `entity` order, later-FK local candidates include output made available by the earlier FK, remote candidates include each selected parent's processed columns and `system_id`, and before/after-unnest lists use the current `id_vars`/`value_vars` shape without legacy `value_id` suggestions.
  * **Constraints:** Keep the endpoint and response model unchanged; use deterministic in-test project fixtures and do not invoke loaders or queries.
  * **Validation:** `V-2`.

**Completion evidence:** The editor has no frontend caller of the legacy columns GET, the legacy API contract remains covered, and the endpoint test proves ordered, parent-specific candidate entries for multiple FKs.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` (from `P-AC-2`, `P-AC-4`, `P-AC-5`, `P-AC-8`) | `T4.1`, `T4.2`, `T4.4` | `V-1`, `V-2` | Matching FK indices use candidates from their link position; remote-key and extra-column source controls receive selected-parent processed candidates, including `system_id` where returned. |
| `PH4-AC-2` (from `P-AC-3`, `P-AC-6`) | `T4.2`, `T4.3`, `T4.4` | `V-1`, `V-2`, `V-4` | FK suggestions use current unnest candidates, no editor control uses the legacy flattened response, and missing suggestions do not prevent free-text entry. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Latest result |
| --- | --- | --- | --- | --- | --- |
| `V-1` | FK editor and parent-dialog integration: `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `pnpm --dir frontend exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `PH4-AC-1`, `PH4-AC-2` | Parent passes the shared response; FK indices and targets map to their own local, remote, and extra-source candidates; response updates are reflected; free-text keys remain accepted. | Pass: 14 tests. |
| `V-2` | Resolver, service, and endpoint regressions: `tests/process/test_column_availability.py`; `backend/tests/services/test_stage_aware_column_service.py`; `backend/tests/api/v1/test_columns.py` | `uv run pytest tests/process/test_column_availability.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py -q` | `PH4-AC-1`, `PH4-AC-2` | Core tests verify FK order and both unnest stages; service/endpoint tests verify selected-parent processed output, `system_id`, per-FK ordering, current unnest fields, and the unchanged legacy GET response. | Pass: 12 tests, including the extended multi-FK endpoint case. |
| `V-3` | Targeted ESLint and frontend typecheck/build for changed frontend files | `pnpm --dir frontend exec eslint src/components/entities/EntityFormDialog.vue src/components/entities/ForeignKeyEditor.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts`<br>`pnpm --dir frontend build` | `PH4-AC-1`, `PH4-AC-2` | ESLint reports no issues; `vue-tsc` and the Vite build pass. | Pass: ESLint clean; typecheck/build passed with non-fatal dependency and chunk-size warnings. |
| `V-4` | Full frontend Vitest regression suite | `make frontend-test` | `PH4-AC-1`, `PH4-AC-2`; existing frontend behavior | All frontend Vitest tests pass. | Pass: 41 test files and 669 tests. |
| `V-5` | Playwright e2e collection and disabled-suite check | `pnpm --dir frontend exec playwright test` | Existing e2e test-runner behavior | All four e2e files collect without a registration error and their 19 tests remain skipped. | Pass: 19 tests skipped. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared FK candidates passed into the editor | `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T4.1` | Test confirms current per-FK results reach the editor and FK edits remain part of the shared request draft. |
| Operation-specific FK suggestions and regressions | `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `T4.2`, `T4.3` | Local, remote, and extra-source suggestions use their matching response fields; manual entry and directive validation remain available. |
| Retired frontend legacy introspection path | `frontend/src/composables/useColumnIntrospection.ts` (DELETE) | `T4.3` | No frontend import or call to the legacy columns GET remains; backend GET contract is unchanged. |
| Multi-FK endpoint parity coverage | `backend/tests/api/v1/test_columns.py` | `T4.4` | API response preserves FK order, parent-specific candidates, generated IDs, and current unnest candidates. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Connect FK Controls To The Shared Response | Done | Phase 2 endpoint; Phase 3 composable | `T4.1`–`T4.2` complete; `V-1` passes. |
| Area 2: Retire The Editor's Legacy Path And Verify Parity | Done | Area 1; existing resolver and endpoint contract | `T4.3`–`T4.4` complete; `V-2`–`V-5` pass; legacy GET contract unchanged. |

## Definition Of Done

- [x] `PH4-AC-1` and `PH4-AC-2` each have implementation and validation evidence.
- [x] FK candidate results are matched by FK index and entity, and the editor uses one shared debounced response.
- [x] Local keys use resolver-provided before- and after-unnest candidates; remote keys and extra-column sources use their separate response fields.
- [x] FK selectors remain free-text and preserve `@value` suggestions and validation.
- [x] The frontend editor no longer imports or calls the legacy column-introspection composable; the legacy GET response contract remains unchanged.
- [x] Multi-FK endpoint tests verify ordering, selected-parent results, `system_id`, and current unnest fields.
- [x] Targeted frontend/backend tests, ESLint, frontend typecheck/build, the full frontend suite, and Playwright collection pass.
- [x] No stage or availability rules are reimplemented in TypeScript, and no loader or query discovery is added.
- [x] No unresolved question affects implementation, compatibility, or validation.

## Risks And Open Questions

- Candidate results may be empty or incomplete when source metadata is unavailable. Keep the comboboxes editable and do not turn a missing suggestion into a validation error.
- The shared response identifies each FK by index and target entity. Clear a candidate entry when either no longer matches the current FK so a changed parent does not display stale suggestions while the debounced request updates.
- The legacy GET remains available to preserve its tested response contract, but the entity editor must not use it after this phase.