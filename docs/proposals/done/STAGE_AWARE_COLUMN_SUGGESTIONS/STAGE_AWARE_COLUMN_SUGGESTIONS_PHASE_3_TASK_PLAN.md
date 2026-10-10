# Phase 3 Task Plan: Shared Entity-Editor Suggestions

## Phase Summary

**Goal:** Replace the entity form's independent candidate unions with operation-specific candidates from one debounced request for the current unsaved draft.

**Readiness:** Validated. Phase 3 is marked ready in the [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md). Phase 2's endpoint and response model are present, and the focused frontend baseline passes. No unresolved decision changes the frontend contract or behavior.

**Dependencies and constraints:** Use the Phase 2 `POST /projects/{project_name}/entities/{entity_name}/column-availability` contract. Keep operation and stage semantics in Python. Include current FK configuration in the submitted draft so selected-parent changes refresh the response, but leave FK selector migration to Phase 4. Candidates remain advisory, all existing suggestion controls remain free-text, and filter fields remain text inputs.

**Source documents:** [proposal](STAGE_AWARE_COLUMN_SUGGESTIONS.md), [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md), and [Phase 2 task plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_2_TASK_PLAN.md).

**Phase acceptance criteria**

1. `PH3-AC-1` (from `P-AC-2`, `P-AC-7`): In-scope entity-level controls display their operation-specific candidates from one debounced request for the current draft and selected-parent state; the frontend does not infer availability from pipeline stages.
2. `PH3-AC-2` (from `P-AC-6`, `P-AC-9`): A name absent from candidates remains enterable, and filter fields are not converted to comboboxes.

## Repository Findings

**Repository basis:** Branch `stage-aware-column-suggestions`, commit `88fe6a6b64b79fcf1ce92e27e55e6d3181d17f85`, planning date 2026-10-08. The worktree was clean; no uncommitted changes needed accommodation.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/columns.py::get_stage_aware_column_availability` and `backend/app/models/column_availability.py::ColumnAvailabilityResponse` | The protected POST accepts `entity_draft` and optional `source_columns`. Its response has `columns`, `business_keys`, `replacements`, `drop_duplicates`, `drop_empty_rows`, `extra_columns.sources`, stage-keyed `filters`, per-FK results, and `unnest.id_vars`/`unnest.value_vars`. | Add a typed frontend API method for this existing contract; do not change the backend or legacy GET. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData` | Serializes current form state, including columns, keys, cleanup settings, filters, unnest, extra columns, replacements, and foreign keys. The form also has editor-known source fields in `columnsOptions`. | Submit the serialized draft and already-known source fields; do not start new source, loader, or query discovery for suggestions. |
| `frontend/src/components/entities/EntityFormDialog.vue::availableColumns`, `availableColumnsForUnnest`, `availableColumnsForReplacements`, and `extraColumnsAvailableColumns` | These computed values combine configured fields and source metadata locally. Several controls share the same list even when their pipeline operations differ. | Remove client-side availability unions and bind each control to its response field. |
| `frontend/src/components/entities/UnnestEditor.vue` | Both `id_vars` and `value_vars` comboboxes currently receive one `availableColumns` prop. | Give the two operations separate candidate props and keep both as free-text comboboxes. |
| `frontend/src/components/entities/ExtraColumnsEditor.vue` and `ReplacementsEditor.vue` | Extra-column expressions use a text field with clickable suggestions; replacements receive a candidate list for their column selector. | Pass `extra_columns.sources` and `replacements` respectively without restricting manual text entry. |
| `frontend/src/components/entities/FiltersEditor.vue` | Fields whose schema type is `string` or `column` render as `v-text-field`. | Leave filter editing unchanged and add a regression assertion for text-field behavior. |
| `frontend/src/api/entities.ts::entitiesApi`, `frontend/src/api/client.ts::apiRequest`, and `frontend/src/composables/useEntityPreview.ts` | API methods use `apiRequest`; the existing VueUse `useDebounceFn` pattern is available. | Keep the request in the API layer and debounce centrally in one composable instance owned by the dialog. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` and `frontend/src/api/__tests__/entities.test.ts` | Existing focused tests cover the form and entity API. | Extend these tests for candidate mapping and the typed API call; add focused tests for the shared composable and unnest/filter input behavior. |

**Baseline results:** `pnpm --dir frontend exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/api/__tests__/entities.test.ts` passed: 24 tests (10 form tests and 14 API tests).

## Scope

**In scope**

- Add typed frontend request/response contracts and an API method for the existing draft-aware endpoint.
- Add one shared debounced composable and use it for the open entity form's current draft, selected FK parents, and any source columns already known to the editor.
- Map response candidates to entity columns, business keys, replacements, drop-duplicate columns, drop-empty-row columns, unnest ID/value variables, and entity extra-column sources.
- Keep all existing controls free-text; filter candidates remain unused by the UI in this phase.
- Add focused tests for the API contract, debounce behavior, operation mapping, free-text entry, and unchanged filter text fields.

**Out of scope**

- Core resolver, backend endpoint, response model, runtime pipeline, and validation changes.
- FK local/remote selectors and FK extra-column remote-source suggestions; these remain on the legacy path until Phase 4.
- Changing filter fields to comboboxes or wiring filter candidates into the filter editor.
- New source, loader, or query execution to discover candidate columns.

## Work Breakdown

### Area 1: Add Typed API Access And Shared Request State

**Objective:** Provide one typed frontend call and a reusable debounced result for the current entity draft.

**Affected code:** `frontend/src/api/entities.ts`, `frontend/src/api/__tests__/entities.test.ts`, `frontend/src/composables/index.ts`, and new composable/test files.

**Dependencies:** Phase 2 endpoint and response contract.

**Tasks:**

* [x] `T3.1` **Change:** Add typed API access for operation-aware column availability.
  * **Target:** `frontend/src/api/entities.ts::entitiesApi`; `frontend/src/api/__tests__/entities.test.ts`.
  * **Current → required:** `entitiesApi` has no method for the new POST. Add request and response interfaces matching the backend model and a method that posts `{ entity_draft, source_columns? }` to the draft-aware endpoint.
  * **Implementation:** Preserve the nested response shape, including per-operation arrays, `extra_columns.sources`, filter-stage candidates, per-FK results, and separate unnest arrays. Use `apiRequest`; do not alter the existing entity endpoints or the legacy column-introspection GET.
  * **Constraints:** Treat `source_columns` as optional known metadata. Do not run discovery from the API method.
  * **Validation:** `V-1`.
* [x] `T3.2` **Change:** Implement one debounced composable for column-availability requests.
  * **Target:** `frontend/src/composables/useColumnAvailability.ts` (NEW); `frontend/src/composables/__tests__/useColumnAvailability.test.ts` (NEW); export from `frontend/src/composables/index.ts`.
  * **Current → required:** The form has no shared request state for these candidates. Add a typed composable that accepts the project/entity identity, current draft, and optional known source columns, then exposes the latest response and loading/error state.
  * **Implementation:** Debounce changes to the effective request state so rapid edits produce one request for the latest draft. Ignore a late response when a newer request has already been made. Clear or skip requests when the project or entity name is not yet available. Keep request failure and empty results advisory so neither prevents typing or saving.
  * **Constraints:** Use one composable instance for the form's candidate controls. Do not put stage calculations or candidate unions in TypeScript.
  * **Validation:** `V-1`.

**Completion evidence:** The typed API test verifies the endpoint and body, and composable tests show that rapid draft/parent changes yield the latest debounced request and response.

### Area 2: Connect Entity Controls To Operation Results

**Objective:** Replace entity-form availability unions with the shared response and use distinct unnest candidates.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/UnnestEditor.vue`, and their component tests.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T3.3` **Change:** Submit the current form draft once and map the response to entity-level controls.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`, candidate computed properties, and the `UnnestEditor`, `ExtraColumnsEditor`, and `ReplacementsEditor` bindings; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  * **Current → required:** Columns, business keys, replacements, cleanup columns, unnest variables, and extra-column source suggestions are derived from separate local unions. Replace these availability calculations with the shared composable response.
  * **Implementation:** Watch the serialized draft and already-known `columnsOptions`, including its current `foreign_keys`, and pass them through one debounced composable call. Bind `columns`, `business_keys`, `replacements`, `drop_duplicates`, `drop_empty_rows`, and `extra_columns.sources` to their matching controls. Keep the FK editor on its existing path for Phase 4. Extend the form test to assert that edits and selected-parent state reach the request and that each control receives the matching response field.
  * **Constraints:** Do not reproduce pipeline-stage rules, combine response categories into a new availability union, or initiate source/loader/query discovery. Keep candidate absence non-blocking and preserve current controls' free-text behavior.
  * **Validation:** `V-2`.
* [x] `T3.4` **Change:** Give unnest ID and value variables their own candidate lists.
  * **Target:** `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts` (NEW).
  * **Current → required:** Both comboboxes use the same `availableColumns` prop. Accept and bind separate ID-variable and value-variable candidates from `unnest.id_vars` and `unnest.value_vars`.
  * **Implementation:** Keep both controls as `v-combobox` inputs and retain the current unnest model shape. Test that each receives its corresponding candidates and accepts a name that is not in its list.
  * **Constraints:** Do not include generated legacy unnest names or make the list a validation constraint.
  * **Validation:** `V-2`.

**Completion evidence:** Form tests show each entity-level control receives only its operation-specific response list; unnest tests show the two lists remain distinct and manually entered values remain accepted.

### Area 3: Lock Advisory And Filter-Input Behavior

**Objective:** Prove that incomplete suggestions do not restrict edits and that filter column fields remain text inputs.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` and `frontend/src/components/entities/__tests__/FiltersEditor.test.ts` (NEW). `FiltersEditor.vue` is verified but is not changed.

**Dependencies:** Area 2.

**Tasks:**

* [x] `T3.5` **Change:** Add focused regressions for advisory suggestions and filter text fields.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/FiltersEditor.test.ts` (NEW); `frontend/src/components/entities/FiltersEditor.vue`.
  * **Current → required:** Existing tests do not assert that an absent candidate stays enterable or that filter column fields remain text inputs after this integration.
  * **Implementation:** Exercise a `v-combobox` with a value absent from its candidate items and assert it remains in the form model/save configuration. Mount the filter editor with a string/column field schema and assert it renders a `v-text-field`, not a `v-combobox`.
  * **Constraints:** Do not modify filter-editor behavior or treat absence from suggestions as a validation error.
  * **Validation:** `V-2` and `V-3`.

**Completion evidence:** A manually entered value absent from the response remains in the form configuration, and filter string/column fields continue to render as text fields.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-2`, `P-AC-7`) | `T3.1`, `T3.2`, `T3.3`, `T3.4` | `V-1`, `V-2` | One typed, debounced request carries the current draft and selected-parent configuration; all in-scope controls receive their matching operation candidates, including distinct unnest lists, with no frontend stage inference. |
| `PH3-AC-2` (from `P-AC-6`, `P-AC-9`) | `T3.3`, `T3.4`, `T3.5` | `V-2`, `V-3` | Values absent from candidate lists remain enterable and serializable; filter column fields remain text inputs. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Typed endpoint call and shared composable: `frontend/src/api/__tests__/entities.test.ts`; `frontend/src/composables/__tests__/useColumnAvailability.test.ts` (NEW) | `pnpm --dir frontend exec vitest run src/api/__tests__/entities.test.ts src/composables/__tests__/useColumnAvailability.test.ts` | `PH3-AC-1` | API test asserts POST path/body and response typing; composable tests assert debounce, current draft/parent state, latest-response handling, and non-blocking errors. | Pass: 18 tests. |
| `V-2` | Entity form and unnest mapping: `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts` (NEW) | `pnpm --dir frontend exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/UnnestEditor.test.ts` | `PH3-AC-1`, `PH3-AC-2` | Response fields map to the intended controls; one draft/selected-parent state supplies the request; unnest lists are separate; absent candidate values remain enterable and serializable. | Pass: 11 tests. |
| `V-3` | Filter text-field regression: `frontend/src/components/entities/__tests__/FiltersEditor.test.ts` (NEW) | `pnpm --dir frontend exec vitest run src/components/entities/__tests__/FiltersEditor.test.ts` | `PH3-AC-2` | String/column filter fields render as text fields and are not converted to comboboxes. | Pass: 1 test. |
| `V-4` | Targeted ESLint and frontend typecheck/build for all changed frontend files | `pnpm --dir frontend exec eslint src/api/entities.ts src/api/__tests__/entities.test.ts src/composables/index.ts src/composables/useColumnAvailability.ts src/composables/__tests__/useColumnAvailability.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/UnnestEditor.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/UnnestEditor.test.ts src/components/entities/__tests__/FiltersEditor.test.ts`<br>`pnpm --dir frontend build` | `PH3-AC-1`, `PH3-AC-2` | ESLint, `vue-tsc`, and Vite build pass; no autofix is run by the lint command. | Pass: ESLint 9.39.5 reports 0 errors and 0 warnings across all 10 targets; `pnpm --dir frontend build` passes `vue-tsc` and Vite build. |
| `V-5` | Full frontend regression suite | `make frontend-test` | `PH3-AC-1`, `PH3-AC-2`; existing frontend behavior | All frontend tests pass. | Pass: 41 test files and 666 tests passed. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed column-availability API method and contract tests | `frontend/src/api/entities.ts`; `frontend/src/api/__tests__/entities.test.ts` | `T3.1` | Typed request/response match the existing backend contract and POST request assertions pass. |
| Shared debounced composable and tests | `frontend/src/composables/useColumnAvailability.ts` (NEW); `frontend/src/composables/__tests__/useColumnAvailability.test.ts` (NEW); `frontend/src/composables/index.ts` | `T3.2` | One debounced request represents the latest draft and selected-parent state. |
| Entity form request and operation mapping | `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T3.3`, `T3.5` | Form controls consume matching response fields; absent values remain in the form model/configuration. |
| Separate unnest candidate props and tests | `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts` (NEW) | `T3.4` | ID and value controls receive separate candidates and preserve free-text entry. |
| Filter text-field regression | `frontend/src/components/entities/__tests__/FiltersEditor.test.ts` (NEW) | `T3.5` | Filter column fields remain text inputs. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Add Typed API Access And Shared Request State | Done | Phase 2 | V-1 passed: API contract and composable tests (18 total). |
| Area 2: Connect Entity Controls To Operation Results | Done | Area 1 | T3.3 and T3.4 complete; V-2 passed (11 tests). Keep FK selector wiring for Phase 4. |
| Area 3: Lock Advisory And Filter-Input Behavior | Done | Area 2 | T3.5 complete; V-2 and V-3 passed. Keep `FiltersEditor.vue` behavior unchanged. |

## Definition Of Done

- [x] `PH3-AC-1` and `PH3-AC-2` each have implementation and focused validation evidence.
- [x] The entity form makes one debounced request for the current draft and selected-parent state.
- [x] Every in-scope entity-level control uses its matching response field; the frontend does not calculate stage availability.
- [x] Unnest ID-variable and value-variable controls use separate response lists.
- [x] Names absent from candidate lists remain enterable and persist in the form configuration.
- [x] Filter fields remain text inputs; FK controls and the legacy FK introspection path remain unchanged in this phase.
- [x] Targeted tests, ESLint, frontend typecheck/build, and the full frontend test suite pass.
- [x] No source, loader, or query discovery was added for suggestions, and no unresolved question affects implementation or validation.

## Risks And Open Questions

- Source metadata may be incomplete or a request may fail. The form must keep accepting user-entered values and saving; an empty candidate list is not a validation result.
- The endpoint requires a project and entity name in its path. Do not request candidates until both are available, particularly while creating an unnamed entity.
- `columnsOptions` may already contain metadata obtained by existing editor behavior. Forward it only when already available; do not add discovery work to the suggestion request.
- No blocking questions remain. FK selector migration and legacy-path parity are intentionally assigned to Phase 4.