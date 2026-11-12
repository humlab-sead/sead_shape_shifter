# Direct Target-ID Foreign Key UX — Phase 4 Task Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)
Source phase plan: [DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md)

## Phase Summary

**Phase:** Phase 4 — Make a missing target ID column visible and fixable

**Goal:** Turn the existing `DIRECT_FK_OUTPUT_COLUMN_MISSING` conformance result into an actionable path that opens the affected project entity on its produced-column settings and explains how to add the column or clear the direct target-ID selection.

**Readiness:** Validated. Every target below was verified in the current working tree, the existing conformance issue already carries the entity and exact column, and the remaining work is the navigation affordance and its tests.

**Constraints and dependencies:**

- Core conformance stays authoritative. `ForeignKeyValueSourceConformanceValidator` already emits `DIRECT_FK_OUTPUT_COLUMN_MISSING` with `entity` and `column`; this phase adds no new validation rule and no second output-column check in the selector.
- `ValidationMapper.from_core_issue` collapses `issue.field or issue.column` into the API `field` property, so the exact missing column already reaches the frontend in `ValidationError.field`. No backend production change is planned unless the new tests show a gap.
- The navigation extends the existing `open-entity` event chain (`ValidationMessageList` → `ValidationPanel` → `ProjectDetailView` → `EntityListCard` → `EntityFormDialog`) instead of adding a parallel route.
- Depends on Phase 3: the `Direct target IDs` selector and `foreign_key_value_sources` handling in `EntityFormDialog.vue` are present and are the suggested fix path.
- The graph-double-click overlay (`entityStore.openEditorOverlay` and the top-level `entity-form-dialog` in `ProjectDetailView.vue`) is not part of this phase.

**Phase criteria:** `PH4-AC-1` (source `P-AC-4`).

- [x] `PH4-AC-1` A selected target with no produced ID column yields a validation issue naming the entity and exact column, and exposes an action that opens that entity's column settings.

## Repository Findings

**Repository basis:** branch `direct-target-id-foreign-key-ux`, commit `2a17adf9`, planning date 2026-11-10. Uncommitted Phase 1–3 changes are present and are the basis for this plan. Unrelated pending changes (`src/transforms/dsl.py`, `backend/app/api/v1/endpoints/projects.py`, advisor proposal documents) do not touch Phase 4 targets.

| Evidence | Finding | Planning implication |
| -------- | ------- | -------------------- |
| `src/target_model/conformance.py::ForeignKeyValueSourceConformanceValidator` | Emits `DIRECT_FK_OUTPUT_COLUMN_MISSING` with `entity=source_entity`, `column=target_spec.public_id`, and a message naming both, only when the target column is absent from `source_cfg.get_target_facing_columns()`. | Core already reports the required location. Phase 4 adds tests only. |
| `backend/app/mappers/validation_mapper.py::ValidationMapper.from_core_issue` | Sets `field=issue.field or issue.column`; `DIRECT_FK_OUTPUT_COLUMN_MISSING` has no `field`, so the API `field` is the missing column name. | The frontend can use `ValidationError.field` directly as the column. |
| `backend/app/validators/target_model_validator.py::TargetModelValidator.validate` | Maps every `ConformanceIssue` through `ValidationMapper.from_conformance_issue`; no field is dropped. | Adapter-level assertions can prove entity and column reach the API model. |
| `frontend/src/components/validation/ValidationMessageList.vue::handleOpenEntity`, `#item.location` | Renders the entity name as a button that emits `open-entity` with the entity name only; `item.field` is displayed beneath it. | The location is already visible; only an explicit actionable control is missing. |
| `frontend/src/components/validation/ValidationMessageList.vue::canTroubleshoot`, `#expanded-row` | Offers per-issue actions in the expanded row through a small outlined `v-btn` with `@click.stop`. | Add the new action with the same pattern and class-based test selector. |
| `frontend/src/components/validation/ValidationPanel.vue::handleOpenEntity`, `listEvents` | Re-emits `open-entity` with a single entity-name argument. | Forward an optional focus payload without changing the existing single-argument emit. |
| `frontend/src/views/ProjectDetailView.vue::handleOpenValidationEntity`, `::handleEditEntity`, `::handleEntityEditRequestConsumed` | Validation navigation sets `activeTab='entities'` and `entityToEdit=entityName`; the request is cleared when consumed. | Add a sibling `entityEditFocus` state and pass it to `entity-list-card`. |
| `frontend/src/components/entities/EntityListCard.vue::Props`, `::watch([pendingEntityToEdit, entities])`, `::handleEditEntity` | Resolves the edit request when the entity is loaded, opens its `EntityFormDialog`, and emits `entity-edit-request-consumed`. `handleEditEntity` and `handleSelectEntity` are the manual entry points. | Capture the focus request into local state before emitting the consume event; clear it on manual edits and when the dialog closes. |
| `frontend/src/components/entities/EntityFormDialog.vue::Props`, `::activeTab`, `::watch(() => props.initialTab)` | Props are `modelValue`, `projectName`, `entity`, `mode`, `initialTab`. `activeTab` defaults to `basic`; `initialTab` only maps `yaml`/`form`. | Add `initialFocus` and capture it when `modelValue` turns true. |
| `frontend/src/components/entities/EntityFormDialog.vue` Basic tab | Produced columns are the `Columns` combobox (`ref`-able, editable) for `entity`/`fixed`/file/merged types and the read-only `Detected Columns` combobox for `sql`; the `Direct target IDs` row follows them and carries `data-testid="direct-target-ids"`. | Focus the visible columns control and render guidance before the columns rows. Both rows are mutually exclusive, so one ref name is enough. |
| `frontend/src/components/entities/EntityFormDialog.vue::entityNameField` usage | `entityNameField.value?.focus()` inside `nextTick` is the existing focus pattern. | Reuse the same pattern for the columns control. |
| `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts::mountList`, `expandButtonAt` | Real Vuetify mount; rows expand on click and actions are queried by class. | Add action tests with the same helpers. |
| `frontend/src/views/__tests__/ProjectDetailView.test.ts::mountProjectDetailView` | `ValidationPanel` and `EntityListCard` are plain template stubs with no props or emits. | Extend those stubs to carry the focus payload and assert the wiring. |
| `backend/tests/validators/test_target_model_validator.py::_make_project`, `::_minimal_entity` | Adapter tests build a minimal resolved project and target model inline and assert API error fields. | Add the entity/field assertion here, not in the API endpoint suite. |

## Scope

**In scope**

- Core and backend adapter tests proving `DIRECT_FK_OUTPUT_COLUMN_MISSING` reports entity and column.
- A `ValidationEntityFocus` type in `frontend/src/types/validation.ts`.
- A column-settings action in `ValidationMessageList.vue` and focus forwarding in `ValidationPanel.vue`.
- Focus state and prop routing in `ProjectDetailView.vue` and `EntityListCard.vue`.
- `EntityFormDialog.vue` capture, Basic-tab focus of the columns control, and missing-column guidance.
- Tests for each of those changes.

**Out of scope**

- New conformance rules, severity changes, or output-column checks in the entity dialog or selector.
- The change-request ingester, Core project `foreign_keys` links, `depends_on`, and the target-model entity picker.
- The graph-double-click overlay route and `frontend/src/stores/entity.ts`.
- YAML authoring changes and documentation updates (Phase 5).

**Affected layers:** Core tests, backend tests, frontend types, validation components, project view, entity list, entity dialog.

## Work Breakdown

### Area 1: Pin the existing entity and column reporting

**Objective:** Tests prove that a declared `public_id` value source without a produced output column reports the project entity and the exact missing column, in both Core and the API model.

**Affected code:** `tests/model/test_target_model_conformance.py` (existing file); `backend/tests/validators/test_target_model_validator.py` (existing file).

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Add a Core conformance test that asserts the issue location.
  - **Target:** `tests/model/test_target_model_conformance.py`, beside `test_invalid_direct_public_id_fk_reports_specific_code`.
  - **Current → required:** Existing tests assert only that the code is present.
  - **Implementation:** Add `test_direct_public_id_missing_output_column_reports_entity_and_column`. Build `_minimal_target_model({"sample": {"foreign_keys": [{"entity": "dataset"}]}, "dataset": {"public_id": "dataset_id", "target_table": "public.dataset"}})` and `_minimal_project({"sample": {"columns": ["sample_name"], "foreign_key_value_sources": {"dataset": "public_id"}}})`. Filter issues by `code == "DIRECT_FK_OUTPUT_COLUMN_MISSING"`, assert exactly one issue, and assert `entity == "sample"` and `column == "dataset_id"`.
  - **Constraints:** Do not change the validator. Do not assert on message wording, which is not part of the contract.
  - **Validation:** `V-1`.

- [x] `T1.2` **Change:** Add a backend adapter test that asserts the API model keeps entity and column.
  - **Target:** `backend/tests/validators/test_target_model_validator.py`, in `TestValidationErrorShape` or a new class beside the direct-FK pending-check test.
  - **Current → required:** No adapter test covers `DIRECT_FK_OUTPUT_COLUMN_MISSING`.
  - **Implementation:** Build the project with `_make_project` using an entity whose `data` is `{"type": "fixed", "values": []}`, `columns=["sample_name"]`, and `foreign_key_value_sources={"dataset": "public_id"}`, plus the target model from `T1.1`. Select the issue with `next(error for error in errors if error.code == "DIRECT_FK_OUTPUT_COLUMN_MISSING")` and assert `entity == "sample"`, `field == "dataset_id"`, `category == ValidationCategory.CONFORMANCE`, and `severity == "error"`.
  - **Constraints:** Do not add API endpoint fixtures; the adapter is the boundary that produces the payload the frontend reads.
  - **Validation:** `V-2`.

**Completion evidence:** `V-1` and `V-2` fail if either the entity or the column is removed from the issue.

### Area 2: Add the validation action and the focus contract

**Objective:** A `DIRECT_FK_OUTPUT_COLUMN_MISSING` result offers an action that emits `open-entity` with a `columns` focus and the missing column name, and the panel forwards it unchanged.

**Affected code:** `frontend/src/types/validation.ts`, `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/ValidationPanel.vue` (all existing files).

**Dependencies:** None.

**Tasks:**

- [x] `T2.1` **Change:** Add the focus payload type.
  - **Target:** `frontend/src/types/validation.ts`, after `ValidationEntityDataValidationResult` / beside `ValidationError`.
  - **Current → required:** No shared type describes a requested entity-editor focus.
  - **Implementation:** Add `export interface ValidationEntityFocus { field: 'columns'; column?: string | null }`. Keep `field` a single-member union so later focus targets extend it deliberately. The type is re-exported through `frontend/src/types/index.ts`.
  - **Constraints:** Do not modify `ValidationError`; `field` already carries the column name.
  - **Validation:** `V-4`.

- [x] `T2.2` **Change:** Add the column-settings action and emit the focus payload.
  - **Target:** `frontend/src/components/validation/ValidationMessageList.vue`, template `#expanded-row` beside the `link-troubleshooter-action` button, and script near `handleOpenEntity`.
  - **Current → required:** The expanded row offers only link troubleshooting; the entity link emits the entity name only.
  - **Implementation:**
    - Update `Emits` to `(e: 'open-entity', entityName: string, focus?: ValidationEntityFocus): void` and import the type from `@/types`.
    - Add `function columnSettingsFocus(item: ValidationTableMessage): ValidationEntityFocus | null` returning `{ field: 'columns', column: item.field ?? null }` only when `item.code === 'DIRECT_FK_OUTPUT_COLUMN_MISSING'` and `item.entity` is set; otherwise `null`.
    - Add `function handleOpenColumnSettings(item)` that emits `open-entity` with the entity name and the focus payload.
    - In `#expanded-row`, after the troubleshooter block, render `<v-btn v-if="columnSettingsFocus(item)" class="direct-fk-column-action" size="small" variant="outlined" prepend-icon="mdi-table-cog" @click.stop="handleOpenColumnSettings(item)">Open column settings</v-btn>`.
    - Leave `handleOpenEntity` unchanged so the entity link keeps emitting a single argument.
  - **Constraints:** Do not gate the action on severity, and do not add output-column logic here. Keep the entity link behavior identical.
  - **Validation:** `V-3`.

- [x] `T2.3` **Change:** Forward the optional focus from the panel.
  - **Target:** `frontend/src/components/validation/ValidationPanel.vue`, `Emits`, `handleOpenEntity`, `listEvents`.
  - **Current → required:** `handleOpenEntity(entityName: string)` drops any additional arguments.
  - **Implementation:** Accept `(entityName: string, focus?: ValidationEntityFocus)` and emit with two arguments when `focus` is provided, otherwise keep the single-argument emit. Import the type from `@/types`.
  - **Constraints:** Preserve the exact single-argument payload for non-focus navigation.
  - **Validation:** `V-3`.

**Completion evidence:** Expanding a direct-FK issue shows `Open column settings`, and clicking it emits `['sample', { field: 'columns', column: 'dataset_id' }]` through both components.

### Area 3: Route the focus request to the entity editor

**Objective:** `ProjectDetailView` keeps the focus request alongside the existing `entityToEdit` request, and `EntityListCard` hands it to the dialog that it opens for the request.

**Affected code:** `frontend/src/views/ProjectDetailView.vue`, `frontend/src/components/entities/EntityListCard.vue` (existing files).

**Dependencies:** Area 2 type.

**Tasks:**

- [x] `T3.1` **Change:** Add focus state to the validation navigation.
  - **Target:** `frontend/src/views/ProjectDetailView.vue`, near `entityToEdit`, `handleOpenValidationEntity`, `handleEntityEditRequestConsumed`, and the `entity-list-card` usage.
  - **Current → required:** Validation navigation carries only an entity name.
  - **Implementation:**
    - Add `const entityEditFocus = ref<ValidationEntityFocus | null>(null)` beside `entityToEdit` and import the type from `@/types`.
    - Change `handleOpenValidationEntity(entityName: string, focus?: ValidationEntityFocus)` to set `entityEditFocus.value = focus ?? null` before delegating to `handleEditEntity(entityName)`.
    - Clear `entityEditFocus.value = null` in `handleEntityEditRequestConsumed` and in `handleEditEntity` so manual edits start without focus.
    - Pass `:entity-edit-focus="entityEditFocus"` to `entity-list-card`.
    - Update the `validation-panel` listener only if Vue's template typing requires it; the emitted payload already matches `(entityName, focus?)`.
  - **Constraints:** Do not change the `activeTab`/`entityToEdit` behavior, the overlay dialog, or `entityStore`.
  - **Validation:** `V-4`, `V-6`.

- [x] `T3.2` **Change:** Capture and pass the focus request in the entity list.
  - **Target:** `frontend/src/components/entities/EntityListCard.vue`, `Props`, local state, `handleEditEntity`, `handleSelectEntity`, the request-resolution watcher, and the `entity-form-dialog` usage.
  - **Current → required:** The dialog receives only `modelValue`, `projectName`, `entity`, and `mode`.
  - **Implementation:**
    - Add `entityEditFocus?: ValidationEntityFocus | null` to `Props` and `import type { ValidationEntityFocus } from '@/types'`.
    - Add `const pendingEditFocus = ref<ValidationEntityFocus | null>(null)`.
    - In `handleEditEntity` and `handleSelectEntity`, set `pendingEditFocus.value = null` (manual entry has no focus).
    - In the `[pendingEntityToEdit, entities]` watcher, after `handleEditEntity(entity)` set `pendingEditFocus.value = props.entityEditFocus ?? null`, then clear `pendingEntityToEdit` and emit `entity-edit-request-consumed`. Assign before emitting so the value is fixed even when the parent clears its own state in the same tick.
    - Add `watch(showFormDialog, (open) => { if (!open) pendingEditFocus.value = null })`.
    - Pass `:initial-focus="pendingEditFocus"` to `entity-form-dialog`.
  - **Constraints:** Do not alter dialog open/close conditions, the entity store sync, or the consume-event contract.
  - **Validation:** `V-5`.

**Completion evidence:** A validation action opens the requested entity dialog with `initialFocus` set, and a manual edit opens the same dialog with `initialFocus` null.

### Area 4: Focus the columns control and explain the fix

**Objective:** When opened with a columns focus, the dialog selects the Basic tab, moves focus to the visible columns control, and shows guidance naming the missing column and the alternative of clearing the direct target-ID selection.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue` (existing file).

**Dependencies:** Areas 2 and 3.

**Tasks:**

- [x] `T4.1` **Change:** Accept and capture the focus request.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`, `Props`, script state, and watchers near `watch(() => props.initialTab)`.
  - **Current → required:** Props end at `initialTab`; nothing reacts to an open-time focus request.
  - **Implementation:**
    - Add `initialFocus?: ValidationEntityFocus | null` to `Props` with `import type { ValidationEntityFocus } from '@/types'`.
    - Add `const activeFocus = ref<ValidationEntityFocus | null>(null)` and `const columnsField = ref<{ focus: () => void } | null>(null)`.
    - Add `watch(() => props.modelValue, async (open) => { if (!open) { activeFocus.value = null; return } activeFocus.value = props.initialFocus ?? null; if (activeFocus.value?.field === 'columns') { activeTab.value = 'basic'; await nextTick(); columnsField.value?.focus() } }, { immediate: true })`.
    - Keep the existing `initialTab` and `overlayInitialTab` watchers unchanged; the focus path sets `activeTab` only when a focus request is captured.
  - **Constraints:** Clear the captured focus when the dialog closes so later manual edits do not show stale guidance. Do not write to `formData`.
  - **Validation:** `V-5`.

- [x] `T4.2` **Change:** Attach the columns ref and render the guidance.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`, Basic tab: the `Columns` `v-combobox`, the `Detected Columns` `v-combobox`, and a new block before those rows.
  - **Current → required:** Columns rows have no ref and no missing-column guidance.
  - **Implementation:**
    - Add `ref="columnsField"` to both comboboxes. They are mutually exclusive (`formData.type === 'sql'` versus the other types), so one ref name is safe.
    - Before the `Columns` form row, add `<v-alert v-if="activeFocus?.field === 'columns'" type="info" variant="tonal" density="compact" class="mb-4" data-testid="direct-target-id-column-guidance">` with text: with a column name, `This entity does not produce the target ID column "<column>". Add it to Columns or the SQL query, or clear the selection in Direct target IDs.`; without one, `This entity does not produce a target ID column for a selected target. Add the column or clear the selection in Direct target IDs.`
    - Interpolate `activeFocus.column` as `<code>` inside the sentence.
  - **Constraints:** Do not add validation rules, disable Save, or change the `Direct target IDs` row. Guidance must stay present regardless of `formData.type`.
  - **Validation:** `V-5`.

**Completion evidence:** Opening the dialog with `initialFocus={{ field: 'columns', column: 'dataset_id' }}` shows the guidance inside the Basic window item, calls the columns control's `focus`, and removes the guidance after the dialog closes.

### Area 5: Frontend tests for action, routing, and guidance

**Objective:** Component and view tests lock the action payload, the prop routing, the dialog capture, and the guidance lifecycle.

**Affected code:** `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`, `frontend/src/components/validation/__tests__/ValidationPanel.test.ts`, `frontend/src/components/entities/__tests__/EntityListCard.test.ts`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `frontend/src/views/__tests__/ProjectDetailView.test.ts` (existing files).

**Dependencies:** Areas 1–4.

**Tasks:**

- [x] `T5.1` **Change:** Test the action and its payload.
  - **Target:** `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`.
  - **Current → required:** No test covers a column-settings action.
  - **Implementation:**
    - Add `it('offers column settings for a missing direct-FK output column')`: mount a message `{ severity: 'error', entity: 'sample', field: 'dataset_id', code: 'DIRECT_FK_OUTPUT_COLUMN_MISSING', message: 'Entity \'sample\' must output target FK column \'dataset_id\'.' }`; click the row to expand; assert `.direct-fk-column-action` exists and its text contains `Open column settings`; click it and assert `wrapper.emitted('open-entity')?.[0]` equals `['sample', { field: 'columns', column: 'dataset_id' }]`.
    - Add `it('omits column settings for other issues')`: mount the default fixture and assert `.direct-fk-column-action` does not exist after expanding row 0.
    - Add `it('opens column settings without a column name when the issue has no field')`: same code with `field: null`; assert the payload is `['sample', { field: 'columns', column: null }]`.
  - **Constraints:** Keep the existing `emits open-entity ...` test passing unchanged.
  - **Validation:** `V-3`.

- [x] `T5.2` **Change:** Test panel forwarding.
  - **Target:** `frontend/src/components/validation/__tests__/ValidationPanel.test.ts`.
  - **Current → required:** No test asserts the second argument.
  - **Implementation:** Add `it('forwards the column focus from a direct-FK issue')` with a `ValidationResult` containing the direct-FK error. Click the message row to expand, click `.direct-fk-column-action`, and assert `wrapper.emitted('open-entity')?.[0]` equals `['sample', { field: 'columns', column: 'dataset_id' }]`.
  - **Constraints:** Reuse the existing `mountValidationPanel` helper and its Vuetify stubs.
  - **Validation:** `V-3`.

- [x] `T5.3` **Change:** Test list-to-dialog routing and reset.
  - **Target:** `frontend/src/components/entities/__tests__/EntityListCard.test.ts`.
  - **Current → required:** `EntityFormDialogStub` exposes only `modelValue` and `entity`.
  - **Implementation:**
    - Add `initialFocus` to the stub props and add `emits: ['update:modelValue', 'saved']` plus a `<button class="close-entity-dialog" @click="$emit('update:modelValue', false)" />` inside the stub template.
    - Add `it('passes an edit focus request to the dialog')`: mount with `entityToEdit: 'sample'`, `entityEditFocus: { field: 'columns', column: 'dataset_id' }`, and the entity loaded; after `nextTick`, assert `wrapper.findComponent({ name: 'EntityFormDialog' }).props('initialFocus')` deep-equals the request.
    - Add `it('clears the focus request when the dialog closes')`: from the same mount, click `.close-entity-dialog`, await `nextTick`, and assert `props('initialFocus')` is `null`.
  - **Constraints:** Do not modify the existing three tests or their assertions.
  - **Validation:** `V-5`.

- [x] `T5.4` **Change:** Test dialog capture, focus call, and guidance lifecycle.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** The `VCombobox` stub exposes no focus method and no test passes `initialFocus`.
  - **Implementation:**
    - Add `focusCombobox: vi.fn()` to `mockState` and `methods: { focus: mockState.focusCombobox }` to the `VCombobox` stub; reset it in `beforeEach`.
    - Add `it('opens column settings with guidance when focused on a missing column')`: mount `{ mode: 'edit', entity: createLocationEntity(), modelValue: true, initialFocus: { field: 'columns', column: 'dataset_id' } }`; await `nextTick()` and `flushPromises()`; assert `.v-window-item-stub[data-window-value="basic"] [data-testid="direct-target-id-column-guidance"]` contains `dataset_id` and `Direct target IDs`; assert `mockState.focusCombobox` was called.
    - Add `it('shows no column guidance without a focus request')`: mount the same entity without `initialFocus`; assert no guidance element exists.
    - Add `it('clears column guidance after the dialog closes and reopens')`: mount with the focus request, `await wrapper.setProps({ modelValue: false })`, then `await wrapper.setProps({ modelValue: true })` without changing `initialFocus`; assert the guidance element is gone.
  - **Constraints:** Use the existing `mountEntityFormDialog` and `createLocationEntity` helpers. Do not add fake timers.
  - **Validation:** `V-5`.

- [x] `T5.5` **Change:** Test the view wiring.
  - **Target:** `frontend/src/views/__tests__/ProjectDetailView.test.ts`.
  - **Current → required:** `ValidationPanel` and `EntityListCard` stubs have no props or emits.
  - **Implementation:**
    - Change the `ValidationPanel` stub to `{ name: 'ValidationPanel', emits: ['open-entity'], template: '<button data-testid="validation-panel" @click="$emit(\'open-entity\', \'sample\', { field: \'columns\', column: \'dataset_id\' })" />' }`.
    - Change the `EntityListCard` stub to declare `props: ['projectName', 'entityToEdit', 'entityEditFocus']`.
    - Add `it('opens the entity with the column focus from a validation issue')`: click `[data-testid="validation-panel"]`; find the `EntityListCard` stub component; assert `props('entityToEdit') === 'sample'` and `props('entityEditFocus')` deep-equals `{ field: 'columns', column: 'dataset_id' }`.
  - **Constraints:** Keep every existing test in the file passing; do not add store or API mocks.
  - **Validation:** `V-6`.

**Completion evidence:** All new tests fail against the pre-change components and pass after Areas 2–4, with the pre-existing 83 frontend tests in the four component files and the 10 view tests unchanged.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --------- | -------- | -------------- | ----------------- |
| `PH4-AC-1` | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2`, `T4.1`, `T4.2`, `T5.1`, `T5.2`, `T5.3`, `T5.4`, `T5.5` | `V-1`, `V-2`, `V-3`, `V-4`, `V-5`, `V-6` | Core and adapter tests report `sample` + `dataset_id`; the action emits a columns focus with the column; the dialog opens on Basic with guidance naming the column and focuses the columns control. |

Observed evidence: `V-1` and `V-2` assert the issue code, entity, and column in both Core and the API model; `V-3` asserts the action label and the `['sample', { field: 'columns', column: 'dataset_id' }]` payload through both components; `V-5` asserts the dialog guidance text, the columns-control focus call, the list pass-through, and the clear-on-close behavior; `V-4` asserts the view routing to `entityToEdit` and `entityEditFocus`.

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| -- | ---------------- | ----------------- | ------ | --------------- | -------- |
| `V-1` | Core conformance location | `.venv/bin/python -m pytest tests/model/test_target_model_conformance.py -q -n 0` | `PH4-AC-1` (entity and column) | New test passes; existing tests pass | Pass 2026-11-10: passed, exit 0, after the Black reformat of the new test |
| `V-2` | Backend adapter and mapper | `.venv/bin/python -m pytest backend/tests/validators/test_target_model_validator.py backend/tests/mappers/test_validation_mapper.py -q -n 0` | `PH4-AC-1` (API payload) | New adapter test passes; existing tests pass | Pass 2026-11-10: passed, exit 0 |
| `V-3` | Validation message and panel tests | `cd frontend && npx vitest run src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts` | `PH4-AC-1` (action and payload) | New action tests pass; 19 message-list and 8 panel tests unchanged | Pass 2026-11-10: 2 files, 31 tests passed (22 message-list, 9 panel) |
| `V-4` | View wiring and types | `cd frontend && npx vitest run src/views/__tests__/ProjectDetailView.test.ts && npx vue-tsc --noEmit` | `PH4-AC-1` (routing) | New view test passes; no diagnostics | Pass 2026-11-10: 11 view tests passed; `vue-tsc` reported nothing |
| `V-5` | Entity list and dialog tests | `cd frontend && npx vitest run src/components/entities/__tests__/EntityListCard.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH4-AC-1` (focus and guidance) | New routing, capture, and guidance tests pass; 3 list and 53 dialog tests unchanged | Pass 2026-11-10: 5 list tests and 56 dialog tests passed |
| `V-6` | Formatting and lint | `cd frontend && npx prettier --check src/types/validation.ts src/components/validation/ValidationMessageList.vue src/components/validation/ValidationPanel.vue src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts src/components/entities/EntityListCard.vue src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityListCard.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts src/views/ProjectDetailView.vue src/views/__tests__/ProjectDetailView.test.ts && npx eslint <same paths>` | Implementation quality | Both pass | Pass 2026-11-10: Prettier flagged `EntityFormDialog.vue` and `ProjectDetailView.test.ts`; both passed after `prettier --write`. ESLint reported no issues |
| `V-7` | Python formatting and lint for the two test files | `.venv/bin/black --check tests/model/test_target_model_conformance.py backend/tests/validators/test_target_model_validator.py && .venv/bin/isort --check-only tests/model/test_target_model_conformance.py backend/tests/validators/test_target_model_validator.py` | `PH4-AC-1` (test quality) | Both pass | Pass 2026-11-10: Black flagged one long `_minimal_project` call; passed after `black tests/model/test_target_model_conformance.py`. isort passed |

Full frontend regression run for confidence: `cd frontend && npx vitest run` passed 1054 tests across 68 files.

Negative and boundary cases covered by `V-3` and `V-5`: issue without `field`, non-matching code, dialog without a focus request, dialog reopen after close, and manual edit after a focused open.

### Execution Notes

- Run the focused commands above; the full frontend suite belongs to Phase 5.
- The dialog test mounts with a `VDialog` stub that always renders content, so focus is observable there. In the running app the dialog renders lazily; focus is best-effort, while the Basic tab selection and guidance alert are the guaranteed outcome.
- If verified repository state differs from the findings table (for example the issue no longer carries `entity` or `column`), stop and report the evidence instead of inventing a replacement design.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| ----------- | ------ | -------- | ------------------- |
| Core location test | `tests/model/test_target_model_conformance.py::test_direct_public_id_missing_output_column_reports_entity_and_column` | `T1.1` | `V-1` passes |
| Adapter payload test | `backend/tests/validators/test_target_model_validator.py` | `T1.2` | `V-2` passes |
| Focus type | `frontend/src/types/validation.ts::ValidationEntityFocus` | `T2.1` | `V-4` reports no diagnostics |
| Validation action | `frontend/src/components/validation/ValidationMessageList.vue::columnSettingsFocus`, `::handleOpenColumnSettings` | `T2.2` | `V-3` passes |
| Panel forwarding | `frontend/src/components/validation/ValidationPanel.vue::handleOpenEntity` | `T2.3` | `V-3` passes |
| View focus state | `frontend/src/views/ProjectDetailView.vue::entityEditFocus`, `::handleOpenValidationEntity` | `T3.1` | `V-4` passes |
| List pass-through | `frontend/src/components/entities/EntityListCard.vue::pendingEditFocus` | `T3.2` | `V-5` passes |
| Dialog focus and guidance | `frontend/src/components/entities/EntityFormDialog.vue::activeFocus`, `::columnsField`, guidance alert | `T4.1`, `T4.2` | `V-5` passes |
| Frontend tests | The five test files listed in Area 5 | `T5.1`–`T5.5` | `V-3`–`V-6` pass |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| ---- | ------ | ------------ | ----- |
| Area 1: Pin the existing entity and column reporting | Done | None | Tests only; no production change needed. `V-1`, `V-2` pass |
| Area 2: Add the validation action and the focus contract | Done | None | `ValidationEntityFocus`, `direct-fk-column-action`, panel forwarding. `V-3` passes |
| Area 3: Route the focus request to the entity editor | Done | Area 2 | `entityEditFocus` in the view, `pendingEditFocus` in the list. `V-4`, `V-5` pass |
| Area 4: Focus the columns control and explain the fix | Done | Areas 2–3 | `activeFocus`, `columnsField`, guidance alert. `V-5` passes |
| Area 5: Frontend tests for action, routing, and guidance | Done | Areas 1–4 | Six new tests across five files. `V-3`–`V-6` pass |

## Definition Of Done

- [x] `PH4-AC-1` has implementation and validation evidence under `V-1`–`V-6`.
- [x] All five work areas and deliverables are complete.
- [x] Core and backend tests assert the issue code, entity, and column.
- [x] The new action emits a columns focus with the missing column and preserves the existing single-argument entity link emit.
- [x] The entity dialog opens on the Basic tab, focuses the visible columns control, and shows guidance naming the column and the `Direct target IDs` alternative.
- [x] Guidance clears when the dialog closes and does not reappear for a manual edit.
- [x] No new conformance rule, selector check, project `foreign_keys` link, `depends_on`, or Core behavior is introduced.
- [x] `V-1`–`V-6` pass with the recorded baselines unchanged.
- [x] Any deviation from this plan is documented in the plan before handoff.

## Execution Record

Deviations from the planned instructions:

1. **View focus ordering.** `T3.1` asked `handleOpenValidationEntity` to set `entityEditFocus` before calling `handleEditEntity`, and also asked `handleEditEntity` to clear it. Those two instructions cancel each other. `handleOpenValidationEntity` now calls `handleEditEntity` first and assigns the focus afterwards, which produces the intended outcome: validation navigation carries the focus and manual edits start without it.
2. **Repeated focus requests.** `T4.1` described the `modelValue` watcher as re-reading `initialFocus` on every open. Because the parent clears the request on close, that alone is enough in the app, but the planned reopen test keeps the same `initialFocus` prop. The dialog therefore records the applied request and skips re-applying the same request object on a later open, so stale guidance cannot reappear.
3. **Action placement.** The planned `T2.2` markup placed the action inside the troubleshooter block. It is rendered directly after that block as a sibling with the same `@click.stop` pattern, so an issue that offers both actions shows both.

## Risks And Open Questions

- **Lazy dialog rendering.** Vuetify renders dialog content on open, so the programmatic focus can run before the columns control mounts. The tab switch and guidance alert do not depend on focus; if focus proves unreliable in manual testing, keep the tab and alert and report the limitation rather than adding timers.
- **SQL-type entities.** For `data.type: sql`, the produced columns come from the read-only `Detected Columns` control, so the fix is in the query. The guidance text names both `Columns` and the SQL query; no type-specific branching is planned.
- **Entity no longer in the project.** If the issue names an entity that is absent from the loaded entity list, `EntityListCard` never resolves the request, matching existing entity-link behavior. This phase does not change that.
- **Severity overrides.** The action is rendered by issue code, not severity, so a downgraded issue still offers the fix path. No behavior depends on the configured severity.
- **`field` as the column source.** The frontend reads the column from `ValidationError.field`, which the mapper fills from `issue.column`. `V-2` locks that mapping; if it changes later, the action still opens column settings with no column name.
