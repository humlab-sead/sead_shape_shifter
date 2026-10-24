# Value Reference Column Pickers — Phase 5 Task Plan

## Phase Summary

**Goal:** Show which columns in an inspected `@value` reference caused a validated unnest overlap or non-produced business key, then let the user replace one simple reference with literal columns and undo that edit before saving.

**Readiness:** Validated. Phase 3 reference validation and Phase 4 draft inspection exist in the inspected tree. Complete Phase 4's outstanding authorized browser check before implementing Phase 5; report any resulting contract change before following this plan.

**Sources:** [Proposal](VALUE_REFERENCE_COLUMN_PICKERS.md) (`P-AC-4`–`P-AC-6`) and [phase plan](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_PLAN.md#phase-5-attribute-conflicts-and-replace-simple-references) (`VM-5`).

**Constraints:** Keep API and YAML directive text raw; use `ProjectMapper` for Core conversion. Use the existing structural validators and their severity. A column candidate missing from a stage-aware suggestion list is advisory, not a hard error. Preserve untouched scalar, mixed-list, manual-path, and legacy `+` forms; exclude Fixed Entity Columns. The draft validation and reference reads require project read authorization and must not write the project.

**Acceptance criteria**

1. [ ] `PH5-AC-1` (from `P-AC-4`) Draft-matched validation identifies the expanded columns behind an unnest overlap or non-produced business key; later edits remove stale annotations, and saved-only findings are labeled.
2. [ ] `PH5-AC-2` (from `P-AC-5`) Replacing one resolvable simple reference yields ordered literal chips in place, explains the lost link, and can be undone before save; unresolved and legacy expressions cannot be replaced.
3. [ ] `PH5-AC-3` (from `P-AC-6`) The complete editor preserves untouched scalar, mixed-list, and legacy expression storage forms and leaves valid Core resolution unchanged.

## Repository Findings

**Repository basis:** Branch `value-reference-column-pickers`, commit `3259fde7`, planning date 2026-10-24 (Europe/Stockholm). Uncommitted changes were considered, including the untracked phase plan, Phase 4 task plan, shared picker, and its tests. These files exist in the working tree but are not all committed. Graphify was used for navigation; each finding below was checked in source or tests.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `frontend/src/components/entities/ColumnReferenceCombobox.vue`, `frontend/src/composables/useColumnReferences.ts` | The shared picker resolves a simple chip on inspection, shows ordered `columns` or an unresolved reason, and clears old inspection when the serialized draft changes. It has no conflict annotation, replacement, or undo. | Extend this one control. Gate replacement on a resolved inspection tied to the current draft and the selected chip occurrence. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`, `frontend/src/components/entities/columnListValue.ts::serializeColumnListValue` | The parent already serializes one draft for preview and child pickers and retains original scalar/list values when chips are unchanged. | Feed validation the same serialized draft. A replacement must be a deliberate model change; untouched fields must keep their original storage shape. |
| `frontend/src/components/entities/ForeignKeyEditor.vue`, `frontend/src/components/entities/UnnestEditor.vue` | These child editors host the same picker and emit list changes to the parent; FK fields have indexed paths. | Verify replacement and undo through both child update paths, including multiple FK rows and a disabled unnest. |
| `backend/app/api/v1/endpoints/validation.py::validate_entity`, `frontend/src/api/validation.ts::validateEntity` | Entity validation has no request body and validates the saved project. `frontend/src/stores/validation.ts` holds saved-project results. | Add an authorized read-only draft validation request. Never label the existing saved result as a current-draft result. |
| `backend/app/services/validation_service.py::validate_entity`, `backend/app/mappers/project_mapper.py::to_core_dict` | Validation gathers raw reference errors, converts via `ProjectMapper.to_core()`, runs project specifications, and filters by entity. The project model carries its YAML source path. | Reuse this path on a deep copy with one submitted entity applied; preserve reference errors and source-relative resolution. Do not add a second validator implementation. |
| `src/specifications/entity.py` unnest overlap check; `src/specifications/fields.py::KeysSubsetOfColumnsValidator`; `backend/app/services/validation_service.py::_map_issue` | The overlap is a **warning** on `unnest.value_vars`; missing produced keys are **errors** on `keys`. Both messages include column names, but the API has no structured column list for either issue. | Add stable issue codes and structured affected columns to these existing issues and map them into `ValidationError`; retain messages and severity. Do not parse message text in TypeScript. |
| `backend/app/models/validation.py::ValidationError`, `frontend/src/types/validation.ts::ValidationError` | The issue contract has `severity`, `entity`, `field`, `message`, and optional `code`, but no affected-column field or draft identifier. | Add optional `related_columns` for the two findings. Match a draft response to a local serialized-draft key; keep saved results separately labeled. |
| `frontend/src/views/ProjectDetailView.vue`, `frontend/src/components/entities/EntityListCard.vue`, `frontend/src/views/EntitiesView.vue` | The form opens from the project page or entity list. The project page has a structural validation result; the entity list may be used without one. | Pass saved results to the form only where available, with an explicit saved-project label; lack of a saved result must not block draft validation. |
| `frontend/node_modules/vuetify/lib/components/VCombobox/VCombobox.js` | The chip slot supplies `index` alongside `item` and `props`. | Use the selected occurrence's index so two identical reference chips do not cause replacement of the wrong chip. |
| `frontend/node_modules/vuetify/lib/components/VWindow/VWindowItem.js`, `frontend/node_modules/vuetify/lib/composables/lazy.js` | A tab's content can unmount after it becomes inactive. | Keep the replacement Undo snapshot in `EntityFormDialog`, not only inside the picker. |

## Scope

**In scope:** Draft structural validation for the edited entity; structured columns for the two existing findings; attribution to an inspected reference only when both validation and inspection match the current serialized draft; saved-project labeling; explicit replacement, one-step undo, and focused user guidance. Test the complete form path for Business Keys, non-fixed Columns, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows.

**Out of scope:** New hard rules from candidate lists; data-row validation; general conflict inference for unrelated validators; editing legacy expressions; replacement in Fixed Entity Columns or FK Extra Columns; changes to directive syntax or Core resolution.

## Work Breakdown

### Area 1: Return draft-matched structural findings with affected columns

**Objective:** An authorized request validates an unsaved entity copy and returns the existing warning/error with exact affected columns.

**Affected code:** `src/specifications/entity.py`, `src/specifications/fields.py`, `backend/app/services/validation_service.py`, `backend/app/models/validation.py`, `backend/app/api/v1/endpoints/validation.py`; their existing tests.

**Dependencies:** Phase 3 validator and Phase 4 inspection contracts; complete the Phase 4 browser check before implementation.

**Tasks**

* [x] `T1.1` **Expose affected columns from existing validators.**
  * **Target:** `src/specifications/entity.py` unnest overlap check; `src/specifications/fields.py::KeysSubsetOfColumnsValidator.rule_fail`; `backend/app/services/validation_service.py::_map_issue`; `backend/app/models/validation.py::ValidationError`.
  * **Current → required:** Both validators name the columns only in message text → each issue keeps its current severity/message and also supplies a stable code and ordered `related_columns` field in the API result.
  * **Implementation:** Add issue metadata for the computed overlap or missing-key set, with planned codes `UNNEST_VARIABLE_OVERLAP` and `BUSINESS_KEY_NOT_PRODUCED`; map it through `_map_issue` and expose optional `related_columns` on the API model. Use a deterministic order consistent with the current sorted message; leave other issues without this field. Do not create a new validation rule or change when either finding is emitted.
  * **Validation:** `V-1` uses `columns=["shared", "id"]`, `id_vars=["shared", "id"]`, `value_vars=["shared"]` to assert a warning with `related_columns=["shared"]`, and `keys=["missing"]`, `columns=["present"]` to assert an error with `related_columns=["missing"]`. Check exact codes, existing messages, and no issue for disjoint unnest or produced keys. `V-5` checks existing validation behavior.

* [x] `T1.2` **Validate one submitted entity draft without saving.**
  * **Target:** `backend/app/models/validation.py` (request model); `backend/app/api/v1/endpoints/validation.py` (planned `POST /projects/{name}/entities/{entity_name}/validate-draft`); `backend/app/services/validation_service.py::validate_entity`; `backend/tests/api/v1/test_validation.py`; `backend/tests/services/test_validation_service.py`.
  * **Current → required:** `/validate` reads saved entity values → the new route accepts `entity_draft` (and the original saved entity name for an edit/rename), validates an isolated project copy with the draft at the current entity name, and returns `ValidationResult` without persistence.
  * **Implementation:** Add planned `DraftEntityValidationRequest` with `entity_draft` and optional `original_entity_name`. Require `require_project(Action.READ)` and load through the authorized locator. Copy the loaded `Project` deeply, replace/remove the original entity key as appropriate, keep its source path, and call the existing `ValidationService.validate_entity`. Return entity and project-resolution errors already produced by that path. Do not run data validation or use `asyncio.run()`.
  * **Validation:** `V-1` uses `authorized_client` and an API-created project with saved `site.keys=["saved"]` and draft `site.keys=["draft"]`; assert findings use the draft, then GET the saved entity and assert `"saved"` remains. Cover nested references, rename, unresolved draft reference, mapping failure, missing project, read denial, OpenAPI request/response models, and unchanged ordered values from default `ProjectMapper.to_core()`.

**Completion evidence:** The draft route returns the current structural finding with structured columns and never changes the saved project; existing saved `/validate` behavior remains intact.

### Area 2: Show only current-draft conflicts and label saved findings

**Objective:** An inspected chip shows the intersection of its resolved columns and a matching validator finding, with the validator's severity.

**Affected code:** `frontend/src/api/validation.ts`, `frontend/src/types/validation.ts`, `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/ColumnReferenceCombobox.vue`, `frontend/src/components/entities/EntityListCard.vue`, `frontend/src/views/ProjectDetailView.vue`; proposed composable and tests marked `NEW` below.

**Dependencies:** Area 1.

**Tasks**

* [x] `T2.1` **Request and retain validation only for the current serialized draft.**
  * **Target:** `frontend/src/api/validation.ts`; `frontend/src/api/__tests__/validation.test.ts`; `frontend/src/types/validation.ts`; `frontend/src/composables/useDraftEntityValidation.ts` (`NEW`); `frontend/src/composables/__tests__/useDraftEntityValidation.test.ts` (`NEW`).
  * **Current → required:** The frontend can validate only saved data → a typed draft request returns structural findings, and delayed results from a prior draft, entity, or dialog session are discarded.
  * **Implementation:** Send a copied `serializedEntityDraft` to the new route. Debounce requests made while an in-scope inspection is open, record the project/entity/draft key used for each request, and expose findings only while that key equals the current form. Increment a request version on draft change, dialog close, entity rename, or component disposal. A failed or denied request shows a read error, never a guessed conflict. Keep saved-project results in a separate value.
  * **Validation:** `V-2` checks exact method/path/body, delayed success and error, draft change before response, close/rename, and no requests for a closed form.

* [x] `T2.2` **Attribute validator findings to the inspected reference.**
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/ColumnReferenceCombobox.vue`; `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/EntityListCard.vue`; `frontend/src/views/ProjectDetailView.vue`; existing component tests.
  * **Current → required:** Inspection lists columns without explaining validator conflicts → it identifies only `related_columns` that occur in this chip's resolved list when the finding and inspection both describe the same draft. Saved-project findings appear under a clear “Saved project” label and do not annotate unsaved chips.
  * **Implementation:** Emit an inspection event from the shared picker to start draft validation; use issue code, entity, and field to select the two supported findings. For unnest, check both ID and Value Variable chips against the overlap columns; for business keys, check the Keys chip against missing produced keys. Show the original validator severity and message beside the specific matching expanded columns. Clear annotations on every serialized-draft change, changed selected chip, disabled field, and dialog close. Pass an optional saved structural result from `ProjectDetailView` through `EntityListCard` to the form only when it belongs to the current project; do not relabel it as draft data. Stage-aware candidates remain suggestions only.
  * **Validation:** `V-3` inspects `@value: entities.site.keys` resolving to `["shared", "other", "shared"]` beside an unrelated chip; assert only `"shared"` is marked by the overlap warning, with its original severity. Repeat for `keys=["missing"]` and a non-produced-key error. Cover nested expansion, incomplete source candidates, saved-only label, stale responses, and no annotation for Fixed Entity Columns.

**Completion evidence:** A user can see the exact expanded column(s) implicated by a current warning/error, while old or saved-only results cannot appear as current-draft conflicts.

### Area 3: Replace one chip and preserve all other storage forms

**Objective:** An explicit action converts the inspected simple reference to ordered literal chips, with undo before Save.

**Affected code:** Shared picker, parent form, FK/unnest child editors, serialization tests, and `docs/USER_GUIDE.md`.

**Dependencies:** Area 2, so the inspection result and current-draft check are available.

**Tasks**

* [x] `T3.1` **Add Replace with columns and one-step undo.**
  * **Target:** `frontend/src/components/entities/ColumnReferenceCombobox.vue`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/UnnestEditor.vue`; existing component tests.
  * **Current → required:** The inspection card is read-only → a resolved simple chip has an explicit **Replace with columns** action that splices its ordered columns at that chip index and offers Undo until the next edit to that field or Save, including after a tab switch.
  * **Implementation:** Use Vuetify's chip-slot index and require a current resolved response for that exact directive and draft. Explain before the action that literal names are a snapshot and will not follow source changes. Emit the new array through existing `v-model`/child update flows and forward a replacement event carrying field path and before/after arrays through FK/unnest editors to `EntityFormDialog`; never mutate prop arrays or save from the action. Keep one before/after snapshot in the form, offer Undo from the form, and restore through the same field update path only while that field still equals the after-state. Clear the snapshot on a later edit to that field, successful save, close, or field/row removal. An empty resolved list removes just that chip and remains undoable. Do not offer the action for unresolved results, API errors, incomplete paths, or legacy `+` expressions.
  * **Validation:** `V-4` starts with `["before", "@value: entities.site.keys", "after"]` and a result `["a", "b", "a"]`; assert `["before", "a", "b", "a", "after"]`, then exact restoration on Undo. Cover two identical reference chips (only chosen index changes), empty list, FK and unnest propagation, undo after a tab switch, save clearing, stale resolve, and negative cases.

* [ ] `T3.2` **Confirm storage and user guidance.**
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts`; `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts`; `docs/USER_GUIDE.md`.
  * **Current → required:** Phase 1 tests cover untouched storage, but not explicit conversion and undo across the complete editor → tests prove that untouched fields retain exact scalar/list/legacy forms and only the chosen reference changes after Save.
  * **Implementation:** Exercise all eight in-scope control groups from an opened saved entity, including a manual path and literal-first legacy expression. Compare the serialized draft before replacement, after replacement, after undo, and after Save. Confirm a valid reference resolves to the same ordered Core values before replacement and that an explicit replacement stores literals. Add brief user steps for inspect, conflict labels, replacement's snapshot behavior, and undo in the entity editing section of the guide.
  * **Validation:** `V-4` and `V-5` cover parity, saved YAML, and Core resolution; `V-6` checks quality and documentation.

**Completion evidence:** Only the selected reference is converted on Save; Undo restores the exact previous chips before Save; untouched references and Core behavior remain unchanged.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH5-AC-1` (from `P-AC-4`) | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`, `V-2`, `V-3`, `V-5` | Existing warning/error identifies columns only for the matching draft; stale findings clear; saved results are labeled. |
| `PH5-AC-2` (from `P-AC-5`) | `T3.1`, `T3.2` | `V-4`, `V-5` | One simple chip becomes ordered literals; snapshot text and Undo work; unresolved/legacy chips have no action. |
| `PH5-AC-3` (from `P-AC-6`) | `T1.2`, `T3.1`, `T3.2` | `V-1`, `V-4`, `V-5`, `V-6` | Unchanged storage forms and valid Core results match the pre-change values. |

## Validation And Testing

These checks fulfill `VM-5`. Run repository-root Python commands from the root and `pnpm` commands from `frontend/`. Baselines were run against the inspected working tree; they are not Phase 5 results. Planned new tests have no baseline.

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution result |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Existing and added Core/backend tests in `tests/specifications/test_runtime_error_prevention.py`, `backend/tests/services/test_validation_service.py`, `backend/tests/services/test_column_list_reference_validation.py`, `backend/tests/services/test_column_reference_service.py`, `backend/tests/mappers/test_project_mapper_requested_reference.py`, `backend/tests/api/v1/test_validation.py`, and `backend/tests/api/v1/test_column_references.py` | `rtk uv run pytest -p no:cacheprovider backend/tests/services/test_validation_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/services/test_column_reference_service.py backend/tests/mappers/test_project_mapper_requested_reference.py backend/tests/api/v1/test_validation.py backend/tests/api/v1/test_column_references.py tests/specifications/test_runtime_error_prevention.py -q` | `PH5-AC-1`, `PH5-AC-3` | Exact affected columns and unchanged severity; draft route is authorized/read-only; saved route, reference errors, and valid resolution stay intact. | Pass: 81 tests in the first five-file run and 15 tests in the two additional reference/mapper files. Phase 5 cases not yet written. | Pass; command exited 0. |
| `V-2` | Draft request and stale-result manager in `src/api/__tests__/validation.test.ts` and `src/composables/__tests__/useDraftEntityValidation.test.ts` (`NEW`) | `rtk pnpm exec vitest run src/api/__tests__/validation.test.ts src/composables/__tests__/useDraftEntityValidation.test.ts` | `PH5-AC-1` | Exact request; old success/error cannot be shown after edit, rename, or close. | Not run: planned composable/test do not exist. | Pass: 23 tests. |
| `V-3` | Conflict UI in `src/components/entities/__tests__/EntityFormDialog.test.ts`, `src/components/entities/__tests__/ColumnReferenceCombobox.test.ts`, and `src/components/entities/__tests__/UnnestEditor.test.ts` | `rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ColumnReferenceCombobox.test.ts src/components/entities/__tests__/UnnestEditor.test.ts` | `PH5-AC-1` | Draft warning/error intersects the inspected columns; saved-only and stale results never appear as current conflicts; no candidate-only hard error. | Pass: existing 42 tests. Phase 5 cases not yet written. | Pass: 49 tests. |
| `V-4` | Replacement and form-storage tests in `src/components/entities/__tests__/EntityFormDialog.test.ts`, `src/components/entities/__tests__/ColumnReferenceCombobox.test.ts`, `src/components/entities/__tests__/ForeignKeyEditor.test.ts`, and `src/components/entities/__tests__/UnnestEditor.test.ts` | `rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ColumnReferenceCombobox.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts` | `PH5-AC-2`, `PH5-AC-3` | Ordered splice, duplicate chip index, empty list, Undo, disabled actions, and untouched storage forms pass. | Pass: existing 49 tests. Phase 5 cases not yet written. | Pass: 58 tests, including FK duplicate-order propagation. |
| `V-5` | Running-editor and saved-YAML parity | Start `make backend-run` and `make frontend-run` from the root. In a project with scalar and mixed `@value` references plus a literal-first legacy expression, open each in-scope control; inspect an overlap and a missing business key, edit the draft, re-inspect, replace one simple chip, switch tabs and Undo, replace again, then Save and inspect the YAML. Repeat a draft validation POST without read access in browser network tools. Compare an unchanged reference's ordered scoped result before/after with the existing `/column-references/resolve` route. | `PH5-AC-1`–`PH5-AC-3` | Draft warning/error and saved-only labels are distinct; stale findings clear; only the selected chip becomes literals; denied reads reveal no columns; untouched YAML and scoped values match. | Not run at planning. The Phase 4 authorized browser check was completed under the Phase 4 task plan before Phase 5 implementation. | Partial. On 2026-10-24, Playwright 1.57.0 with headless Chromium in `mcr.microsoft.com/playwright:v1.57.0-noble` opened the editor. Business Keys inspection displayed the `missing` key error and Unnest inspection displayed the `shared` overlap warning. Replacing the provider-bound Business Keys reference and saving stored ordered literals `["shared", "missing"]`; the untouched Columns, foreign-key, Unnest, deduplication, and empty-row references remained raw in saved YAML. The unchanged Columns reference still resolved to `["shared", "site_name"]`; a draft-validation POST from a principal without project read access returned 404. Existing persistence checks pass: `backend/tests/services/test_project_service_boundary.py` (29 tests) and `backend/tests/services/test_project_service.py` (118 tests), including allowance for the same ordered provider-bound Business Keys and rejection of unresolved, reordered, or changed keys. Full V-5 remains incomplete: adding literal `missing` beside `@value: entities.site.columns` caused both `/column-availability` and `/validate-draft` to return 500. Mapping the list reference produces a nested list; `TableConfig.columns` in `src/model.py` passes it to `unique` in `src/utility.py`, which raises `TypeError` because a list is unhashable. The task plan says to stop when an existing contract conflicts; no implementation or contract change was made. |
| `V-6` | Frontend and Python quality; generated graph after code changes | From `frontend/`: `rtk pnpm exec eslint src/api/validation.ts src/composables/useDraftEntityValidation.ts src/components/entities/ColumnReferenceCombobox.vue src/components/entities/EntityFormDialog.vue src/components/entities/ForeignKeyEditor.vue src/components/entities/UnnestEditor.vue src/types/validation.ts`; `rtk pnpm exec prettier --check src/api/validation.ts src/composables/useDraftEntityValidation.ts src/components/entities/ColumnReferenceCombobox.vue src/components/entities/EntityFormDialog.vue src/components/entities/ForeignKeyEditor.vue src/components/entities/UnnestEditor.vue src/types/validation.ts`; `rtk pnpm exec vue-tsc --noEmit`. From root: `rtk uv run black --check src/specifications/entity.py src/specifications/fields.py backend/app/models/validation.py backend/app/services/validation_service.py backend/app/api/v1/endpoints/validation.py backend/app/services/project_service.py backend/tests/services/test_project_service_boundary.py`; `rtk uv run isort --check-only src/specifications/entity.py src/specifications/fields.py backend/app/models/validation.py backend/app/services/validation_service.py backend/app/api/v1/endpoints/validation.py backend/app/services/project_service.py backend/tests/services/test_project_service_boundary.py`; `rtk uv run ruff check src/specifications/entity.py src/specifications/fields.py backend/app/models/validation.py backend/app/services/validation_service.py backend/app/api/v1/endpoints/validation.py backend/app/services/project_service.py backend/tests/services/test_project_service_boundary.py`; `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .`. Review generated graph changes and the user-guide steps. | `PH5-AC-3`, quality | No new lint/format/type errors; generated graph reflects code; instructions are accurate. | Type check fails on pre-existing `TS7006` at `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts:36`; other checks not run during planning. Require no new type errors. | Frontend checks pass with only the previously recorded `vue-tsc` `TS7006` at `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts:36`; Black, isort, and Ruff pass for the follow-up service and regression tests. Graphify update exited 0; 18,315 nodes, 33,335 edges, 1,001 communities. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Structured columns from existing findings | `src/specifications/entity.py`; `src/specifications/fields.py`; `backend/app/services/validation_service.py`; `backend/app/models/validation.py`; `frontend/src/types/validation.ts` | `T1.1`, `T2.1` | Overlap warning and missing-key error carry exact `related_columns`. |
| Authorized draft validation | `backend/app/api/v1/endpoints/validation.py`; `backend/app/models/validation.py`; `backend/app/services/validation_service.py`; `backend/tests/api/v1/test_validation.py`; `backend/tests/services/test_validation_service.py`; `tests/specifications/test_runtime_error_prevention.py` | `T1.1`, `T1.2` | `V-1` passes; saved project remains unchanged. |
| Typed frontend request and current-draft state | `frontend/src/api/validation.ts`; `frontend/src/api/__tests__/validation.test.ts`; `frontend/src/composables/useDraftEntityValidation.ts` (`NEW`); `frontend/src/composables/__tests__/useDraftEntityValidation.test.ts` (`NEW`) | `T2.1` | `V-2` passes. |
| Conflict display and saved-result labeling | `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/ColumnReferenceCombobox.vue`; `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/EntityListCard.vue`; `frontend/src/views/ProjectDetailView.vue`; their existing component tests | `T2.2` | `V-3` passes for both validators and stale/saved states. |
| Replacement, undo, and storage parity | `frontend/src/components/entities/ColumnReferenceCombobox.vue`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/UnnestEditor.vue`; their existing component tests | `T3.1`, `T3.2` | `V-4` and saved-YAML part of `V-5` pass. |
| User steps | `docs/USER_GUIDE.md` | `T3.2` | Inspect, replacement snapshot, and Undo are described in the entity workflow. |
| Generated graph, if changed by the required update | `graphify-out/graph.json` | `T3.2` | Graphify update succeeds and generated changes are reviewed. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Draft findings | Complete | Phase 4 authorized browser check passed before implementation | V-1 and V-2 pass; the route is read-only and denied reads return 404. |
| Area 2: Conflict display | Complete | Area 1 | V-3 passes; current-draft findings and saved findings remain separate. |
| Area 3: Replace and preserve | Partial | Area 2 | Podman browser checks passed for scalar-reference inspection, replacement, save, untouched YAML, Core resolution, and no-read authorization. Full V-5 remains incomplete because editing a mixed list containing `@value: entities.site.columns` produces a nested list and causes draft validation and column availability to return 500; see the V-5 result. |

## Definition Of Done

* [ ] `PH5-AC-1`–`PH5-AC-3` have passing `V-1`–`V-5` results and recorded examples for `VM-5`.
* [ ] Every task and deliverable is complete, including the user-guide update.
* [x] Draft validation is read-only and authorized; stale or saved-only results never appear as current-draft conflicts.
* [x] Existing overlap-warning and missing-key-error severity, unrelated errors, and advisory candidate behavior are preserved.
* [x] Replacement and Undo work for every in-scope control; unresolved/legacy/Fixed Entity Columns remain excluded.
* [ ] Untouched scalar, mixed-list, manual-path, and legacy expressions retain their stored shape; valid Core resolution matches the baseline.
* [x] `V-6` has no new quality errors, Graphify is refreshed after code edits, and any deviation is recorded.
* [ ] No unresolved question affects implementation or validation.

If implementation finds a source or test contract that conflicts with this verified plan, stop and report the exact file and result before changing the design or broadening scope.

## Risks And Open Questions

The draft validation path resolves the full project, so an unrelated broken directive may prevent the structural validators from running. In that case show the returned reference/project-resolution error and no invented conflict annotation. A new read-only draft route will run existing validation rather than independent conflict logic. The remaining Phase 4 authorized browser check could expose a prerequisite defect; finish it before Phase 5 implementation and update this plan only if the checked contract changes.
