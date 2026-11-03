# `@value` Column Picker UX — Phase 2 Task Plan

## Phase Summary

**Phase:** 2, Suggestions and explicit preview. **Readiness:** Validated. The [proposal](./VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT.md) is marked Proposed feature; this plan implements the ready Phase 2 in the [phase plan](./VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT_PHASE_PLAN.md). Phase 1 has delivered `getCompletedEntitiesFor()`, `expandValueReference()`, and unchanged form-value preservation. `VM-2` checks the complete picker and save flow.

**Constraints:** Use only the completed entity cache for this feature. Do not merge unsaved form edits into referenced entities, request reference results from the backend, change Core or mapper behavior, or add project validation. Keep the existing FK edit validation separate from preview failure. The provider/schema business-key save guard remains a separate decision.

**Acceptance criteria:**

1. [x] `PH2-AC-1` (from `P-AC-1`): Supported pickers suggest only supported `keys` and `columns` references from the active project's completed cache.
2. [x] `PH2-AC-2` (from `P-AC-4`): Ordinary column suggestions remain field-specific, and Fixed Entity Columns have no reference suggestions or preview.
3. [x] `PH2-AC-3` (from `P-AC-2`, `P-AC-7`): A user-requested preview shows complete expanded columns as read-only cached configuration without changing the reference, form value, or saved YAML.
4. [x] `PH2-AC-4` (from `P-AC-3`): An unavailable preview shows no partial columns or form error and does not block editing or saving.
5. [x] `PH2-AC-5` (from `P-AC-6`): No backend reference endpoint, mapper resolution mode, project-level reference validation, or Core directive change is introduced.

## Repository Findings

**Repository basis:** `value-reference-column-ux-enhancement` at `a1fc26ee`, planned 2026-10-29. The working tree was clean. The Graphify query identified the form, but returned a broad, truncated result; the findings below were checked in current source and tests.

| Verified source | Finding | Planning implication |
| --- | --- | --- |
| `frontend/src/stores/entity.ts::getCompletedEntitiesFor`; `frontend/src/stores/project.ts::selectProject` | Phase 1 distinguishes a completed cache for the requested project from a pending or mismatched cache. Project selection resets the entity store on a switch. | Read suggestions and previews through the cache check using the dialog's `projectName`; also check it against the selected project so an old dialog cannot display references during a switch. Do not read `entities` from `useEntities()` for this feature. |
| `frontend/src/utils/valueReferenceColumns.ts::expandValueReference` | The helper returns an ordered `string[]`, including `[]`, or `null` for a missing or unsupported tree. It accepts complete `@value: entities.<entity>.keys/columns` paths. | Use it to admit only fully supported reference suggestions and to compute the preview. Keep `[]` distinct from unavailable. |
| `frontend/src/components/entities/EntityFormDialog.vue` | Business Keys, Columns, Deduplication Columns, and Drop Empty Rows are Vuetify comboboxes. `useColumnAvailability()` supplies distinct ordinary lists. The Columns combobox is also used by fixed entities. FK and unnest editors receive their ordinary lists as props. | Add reference choices alongside each field's existing list; gate the Columns enhancement on `type !== 'fixed'`. Pass cache data to FK and unnest editors without changing their ordinary candidates. |
| `frontend/src/components/entities/ForeignKeyEditor.vue::getLocalColumnItems`, `getRemoteKeyItems`, `loadDirectives`, `validateLocalKeys`, `validateRemoteKeys` | FK key lists currently mix field candidates with backend `getValidDirectives()` results; Local Keys also include directive text from the current entity's columns. Editing a directive calls the existing validation endpoint. Extra-column source suggestions use `loadDirectives()` too. | Replace FK Local/Remote reference suggestions with supported completed-cache choices, including when focused before a load. Preserve their existing edit validation and extra-column source behavior. A preview click must not call validation or edit a key. |
| `frontend/src/components/entities/UnnestEditor.vue` | ID and Value Variables are separate comboboxes with separate ordinary item props; the child emits its model on changes. | Add reference choices to both lists and preview chips without emitting a change for preview. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | Phase 1 preserves untouched scalar/list forms in Save and YAML. Existing tests cover mixed lists, legacy `+` text, FK child emissions, fixed columns, and operation-specific ordinary candidates. | Reuse the serializer; assert preview and suggestion selection do not expand saved values or mark the form dirty. Keep existing fixed-entity tests. |
| `frontend/src/views/ProjectDetailView.vue::handleValidate`; `frontend/src/views/__tests__/ProjectDetailView.test.ts` | Project validation has an existing view flow and regression test. | Run that regression; add no validation state or endpoint for this display helper. |
| `frontend/src/components/validation/DataValidationConfig.vue`; installed Vuetify `VCombobox` | This repository uses the combobox `#chip` slot, which supplies chip props including close handling. | Reuse those props in a shared preview chip so removal and keyboard behavior remain available. |

## Scope

**In scope:** A completed-cache reference suggestion builder; wiring for Business Keys, non-fixed Columns, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows; an explicit read-only chip preview; focused frontend tests and existing editor, fixed-entity, and validation regressions.

**Out of scope:** Fixed Entity Columns, FK extra-column sources, other column pickers, backend/mapper/Core changes, new project validation, unsaved-draft resolution, automatic replacement or expansion on save, and the provider/schema business-key save guard. Existing field-specific ordinary suggestions, FK edit validation, and project validation remain as implemented.

## Work Breakdown

### Area 1: Supply supported suggestions from the completed cache

**Objective:** Each supported picker receives complete `keys`/`columns` reference strings only while the active project's entity cache is available.

**Affected code:** `frontend/src/utils/valueReferenceColumns.ts`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/UnnestEditor.vue`; corresponding existing tests.

**Dependencies:** Completed Phase 1 cache and expansion contracts.

**Tasks:**

* [x] `T1.1` **Change:** Build cache-derived reference choices.
  * **Target:** `frontend/src/utils/valueReferenceColumns.ts`.
  * **Current → required:** The helper expands one supplied reference → it also provides a deterministic list of complete `@value: entities.<entity>.keys` and `.columns` strings whose entire value expands successfully.
  * **Implementation:** Add a pure suggestion function over `EntityResponse[] | null`. Iterate both properties for each cached entity, call `expandValueReference()`, and include a path only when the result is non-null. Return `[]` for unavailable or empty cache, without mutating data. Do not suggest missing properties, cycles, legacy expressions, or partially supported trees. Keep literal empty lists eligible.
  * **Validation:** `V-1`: use cached entities with literal, scalar, nested, empty, missing, cyclic, and unsupported properties; assert exact choices and no input mutation.
* [x] `T1.2` **Change:** Connect the suggestion list to the supported pickers.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue` comboboxes and child props; `frontend/src/components/entities/ForeignKeyEditor.vue::getLocalColumnItems`, `getRemoteKeyItems`; `frontend/src/components/entities/UnnestEditor.vue` ID/Value comboboxes.
  * **Current → required:** Only ordinary lists or older FK directive lists appear → supported pickers show their own ordinary column list plus the cache-derived reference choices, with no choices from a pending, failed, or different-project cache.
  * **Implementation:** Compute `completedCacheEntities` from `entityStore.getCompletedEntitiesFor(props.projectName)` only when `projectStore.currentProjectName` equals `props.projectName`, then derive the reference list from it. Pass both as typed props to FK and unnest. Keep ordinary candidate arrays in their current field-specific order; add reference strings as separate choices without changing ordinary candidate computation or free-text entry. Gate the Columns combobox on non-fixed type. For FK Local/Remote Keys, remove `directiveItems` and `extractColumnDirectives()` from their suggestion lists and remove their `loadDirectives()` focus handlers. Retain `loadDirectives()` for the existing extra-column source and retain `validateLocalKeys()`/`validateRemoteKeys()` on edits. Clear any displayed choices reactively when cache ownership or active project changes.
  * **Validation:** `V-2`: assert all eight supported picker locations, distinct ordinary candidates, wrong/pending project, successful empty cache, unsupported paths, FK extra-column behavior, and fixed Columns exclusion.
* [x] `T1.3` **Test:** Pin down cache and field scoping in component tests.
  * **Target:** `frontend/src/utils/__tests__/valueReferenceColumns.test.ts`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts`.
  * **Current → required:** Existing tests cover expansion and ordinary lists, but not cache-derived picker choices → tests prove supported choices appear only with completed active-project data.
  * **Implementation:** Extend the dialog's mocked entity store with the Phase 1 getter. Use a `site` fixture with supported `keys` and nested `columns`, plus `broken.keys` set to an unsupported nested value; assert only `site.keys`/`site.columns` appear. Switch the mocked active project or make the getter return `null`; assert references disappear while ordinary candidates remain. Update the FK test that currently expects backend directive results in Local/Remote lists; assert their focus no longer loads backend suggestions, while editing still invokes existing directive validation and the extra-column source still offers its existing suggestions.
  * **Validation:** `V-1`, `V-2`.

**Completion evidence:** The same completed-cache reference list is offered in all supported fields, and each field's ordinary list remains unchanged.

### Area 2: Preview a selected reference without editing it

**Objective:** A user can request a complete, read-only preview from a reference chip; unavailable results remain quiet and leave the chip intact.

**Affected code:** `frontend/src/components/entities/ValueReferenceChip.vue` **NEW**; the supported combobox chip slots in `EntityFormDialog.vue`, `ForeignKeyEditor.vue`, and `UnnestEditor.vue`; component tests.

**Dependencies:** Area 1 passes completed-cache data to each picker.

**Tasks:**

* [x] `T2.1` **Change:** Implement one reusable reference preview chip.
  * **Target:** `frontend/src/components/entities/ValueReferenceChip.vue` **NEW**.
  * **Current → required:** Selected chips have no reference inspection action → a chip containing `@value:` text has a keyboard-accessible explicit Preview action and a read-only popover or equivalent view.
  * **Implementation:** Accept the raw chip text, Vuetify chip props, and `EntityResponse[] | null`. Bind the supplied chip props to preserve close behavior. On Preview, call `expandValueReference()` with the current completed-cache data. Show the ordered result, including duplicates, with the label “Based on cached configuration”; display an empty-result message for `[]`. For `null`, show “Preview unavailable” with no partial list. Keep the raw reference visible. Stop Preview-action events from selecting, removing, or editing the chip. Do not emit an update, validate a directive, or fetch data. Recompute or close an open preview if the supplied cache becomes unavailable or changes projects so old columns cannot remain visible.
  * **Validation:** `V-3`: actual Vuetify combobox chip-slot interaction, click and keyboard action, chip close, success, empty result, unavailable result, and cache change while open.
* [x] `T2.2` **Change:** Render the shared preview chip in the eight supported picker locations.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue` Business Keys, non-fixed Columns, Deduplication Columns, Drop Empty Rows; `frontend/src/components/entities/ForeignKeyEditor.vue` Local/Remote Keys; `frontend/src/components/entities/UnnestEditor.vue` ID/Value Variables.
  * **Current → required:** Selected values render ordinary chips → supported `@value:` chips expose Preview while ordinary chips remain normal; fixed Columns has no Preview action.
  * **Implementation:** Use each combobox's `#chip` slot and pass its chip props through the shared component. Preserve each field's existing `v-model`, disabled state, label, rules, and ordinary items. In the Columns slot, use the ordinary chip when `formData.type === 'fixed'`. Pass the same completed-cache value used by suggestions; keep preview display state separate from `formData`, YAML, dirty-state, and existing entity-data preview state.
  * **Validation:** `V-2`, `V-3`, `V-4`: preview action presence in every supported field, no action on ordinary or fixed chips, and unchanged Save/YAML payloads.
* [x] `T2.3` **Test:** Exercise preview behavior and form isolation.
  * **Target:** `frontend/src/components/entities/__tests__/ValueReferenceChip.test.ts` **NEW**; `EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, and `UnnestEditor.test.ts` in the same test directory.
  * **Current → required:** Existing component tests do not render reference previews → tests cover explicit action, read-only result, unavailable state, and no model changes.
  * **Implementation:** Use the Phase 1 nested fixture (`sample.columns` expands to `['sample_id', 'name', 'site_id', 'site_id']`), and cases for empty list, missing path, cycle, unsupported nested value, and legacy `+` text. Assert no expansion before a click, exact ordered text after a click, no partial text on failure, and no chip update or removal from Preview. Include a real Vuetify `VCombobox` slot test so click and close behavior is verified beyond a shallow stub. In the dialog, edit an unrelated field after Preview and assert exact raw `@value` strings and scalar/list forms in both YAML and update payload; assert no new form error or save disablement.
  * **Validation:** `V-3`, `V-4`.

**Completion evidence:** Every supported reference chip can show a complete or unavailable cached preview without changing the selected value or serialized configuration.

### Area 3: Confirm unchanged editor and validation behavior

**Objective:** The full editor flow retains Phase 1 representation rules, fixed-entity behavior, and existing project validation.

**Affected code:** Existing frontend component and view tests only; no backend or Core targets.

**Dependencies:** Areas 1–2.

**Tasks:**

* [x] `T3.1` **Test:** Run and extend the focused regressions where needed.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts`; `frontend/src/views/__tests__/ProjectDetailView.test.ts`; Phase 1 `frontend/src/stores/__tests__/entity.test.ts` and `frontend/src/utils/__tests__/valueReferenceColumns.test.ts`.
  * **Current → required:** Existing tests cover Phase 1 round trips, fixed columns, and project validation → the same behavior passes with suggestion and preview UI connected.
  * **Implementation:** Assert an unavailable preview leaves Save enabled after an unrelated valid edit, does not set a form error, and does not call project validation. Keep the existing fixed-grid, FK edit-validation, cache-switch, and project-validation assertions. If the modified UI changes existing test stubs, update the stubs to preserve their original assertions rather than weakening them.
  * **Validation:** `V-2`, `V-4`, `V-5`.

**Completion evidence:** Focused tests and quality checks pass, and the changed-file review confirms a frontend-only feature.

## Acceptance-Criteria Coverage

| Phase criterion | Source | Tasks | Validation | Expected result |
| --- | --- | --- | --- | --- |
| `PH2-AC-1` | `P-AC-1` | `T1.1`–`T1.3` | `V-1`, `V-2` | Only complete supported references from the active completed cache appear. |
| `PH2-AC-2` | `P-AC-4` | `T1.2`, `T1.3`, `T2.2`, `T3.1` | `V-2`, `V-4` | Ordinary lists stay scoped; fixed Columns has no reference UI. |
| `PH2-AC-3` | `P-AC-2`, `P-AC-7` | `T2.1`–`T2.3`, `T3.1` | `V-3`, `V-4` | Explicit read-only preview shows complete ordered data without changing raw values. |
| `PH2-AC-4` | `P-AC-3` | `T2.1`–`T2.3`, `T3.1` | `V-3`, `V-4` | Failure shows no partial columns, error, or save block. |
| `PH2-AC-5` | `P-AC-6` | `T1.2`, `T2.1`, `T3.1` | `V-4`, `V-5` | Only frontend display and tests change; existing validation remains. |

## Validation And Testing

Run commands from the stated directory. Baselines were recorded before Phase 2 implementation; a **NEW** test file has no baseline. `VM-2` is complete only when `V-1`–`V-5` pass after implementation.

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Suggestion eligibility and Phase 1 cache/expansion | From `frontend/`: `rtk proxy pnpm test:run src/utils/__tests__/valueReferenceColumns.test.ts src/stores/__tests__/entity.test.ts` | `PH2-AC-1` | New exact-choice cases and existing cache/expansion tests pass. | Pass: 56 existing tests. | Pass: 58 tests (18 helper, 40 store), including supported, empty, missing, cyclic, unsupported, and unavailable-cache cases. |
| `V-2` | All picker locations and ordinary candidates | From `frontend/`: `rtk proxy pnpm test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts` | `PH2-AC-1`, `PH2-AC-2` | Supported references appear only with the active completed cache; field-specific and fixed behavior pass. | Pass: 51 existing tests. | Pass: 53 tests (44 dialog, 8 FK, 1 Unnest), including pending/mismatched/empty cache, all eight picker locations, ordinary candidate ordering, fixed Columns exclusion, and FK extra-column behavior. |
| `V-3` | Explicit chip preview | From `frontend/`: `rtk proxy pnpm test:run src/components/entities/__tests__/ValueReferenceChip.test.ts` | `PH2-AC-3`, `PH2-AC-4` | Click/keyboard, ordered duplicates, `[]`, unavailable tree, cache switch, close, and unchanged model pass. | Not run: test file is **NEW**. | Pass: 10 tests using a real Vuetify `VCombobox`; click and keyboard actions, ordered duplicates, empty/unavailable results, close behavior, unchanged model, and cache change. `VMenu` positioning is stubbed for jsdom. |
| `V-4` | Form/YAML/save and project validation regression | From `frontend/`: `rtk proxy pnpm test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts src/views/__tests__/ProjectDetailView.test.ts` | `PH2-AC-2`–`PH2-AC-5` | Preview does not edit/save expanded columns or create form/project errors; existing FK and project validation cases pass. | Pass: 61 existing tests. | Pass: 63 tests (44 dialog, 8 FK, 1 Unnest, 10 project view), including unavailable preview save/YAML isolation and existing FK/project validation behavior. |
| `V-5` | Types, lint, formatting, and scope | From `frontend/`: `rtk proxy pnpm exec vue-tsc --noEmit`; run `rtk proxy pnpm exec eslint` and `rtk proxy pnpm exec prettier --check` on `src/utils/valueReferenceColumns.ts`, `src/utils/__tests__/valueReferenceColumns.test.ts`, `src/components/entities/ValueReferenceChip.vue`, `src/components/entities/__tests__/ValueReferenceChip.test.ts`, `src/components/entities/EntityFormDialog.vue`, `src/components/entities/ForeignKeyEditor.vue`, `src/components/entities/UnnestEditor.vue`, `src/components/entities/__tests__/EntityFormDialog.test.ts`, `src/components/entities/__tests__/ForeignKeyEditor.test.ts`, and `src/components/entities/__tests__/UnnestEditor.test.ts`. From repo root: `rtk git diff --name-only a1fc26ee` and `rtk git status --short`; inspect all changed and untracked files. | `PH2-AC-5`, changed frontend contracts | No type, lint, or formatting errors. No backend, mapper, Core, or project-validation implementation change. | Pass: type check and lint/Prettier on existing Phase 2 code targets. Working tree clean at planning; **NEW** targets not run. | Pass: `vue-tsc --noEmit`; ESLint reports no issues; Prettier check passes; `git diff --check` passes. Scope review found frontend sources/tests, generated `components.d.ts`, required Graphify outputs, and this task plan only; no backend, mapper, Core, or project-validation implementation changes. |

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
| --- | --- | --- | --- |
| Cached reference choices | `frontend/src/utils/valueReferenceColumns.ts`; `frontend/src/utils/__tests__/valueReferenceColumns.test.ts` | `T1.1`, `T1.3` | `V-1` passes. |
| Form picker wiring and flow tests | `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T1.2`, `T1.3`, `T2.2`, `T2.3`, `T3.1` | `V-2`, `V-4` pass. |
| FK picker wiring and tests | `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `T1.2`, `T1.3`, `T2.2`, `T2.3`, `T3.1` | `V-2`, `V-4` pass. |
| Unnest picker wiring and tests | `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts` | `T1.2`, `T1.3`, `T2.2`, `T2.3`, `T3.1` | `V-2`, `V-4` pass. |
| Shared preview chip and tests | `frontend/src/components/entities/ValueReferenceChip.vue` **NEW**; `frontend/src/components/entities/__tests__/ValueReferenceChip.test.ts` **NEW** | `T2.1`, `T2.3` | `V-3` passes. |

The existing project-view, store, and helper tests are validation targets, not planned implementation files beyond the helper test update listed above.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Cache-derived suggestions | Done | Phase 1 outputs | `T1.1`–`T1.3` complete. `V-1` and `V-2` pass; project ownership, empty cache, field-specific items, and fixed Columns exclusion are covered. |
| Area 2: Explicit chip preview | Done | Area 1 | `T2.1`–`T2.3` complete. `V-3` passes; all eight planned slots use the shared read-only preview chip. |
| Area 3: Editor and validation regression | Done | Areas 1–2 | `T3.1` complete. `V-4` and `V-5` pass; save/YAML, fixed behavior, FK validation, and project validation regressions pass. |

## Definition Of Done

* [x] `PH2-AC-1`–`PH2-AC-5` have task and validation results; `VM-2` is satisfied.
* [x] All three areas and listed deliverables are complete.
* [x] `V-1`–`V-5` pass after implementation.
* [x] Phase 1 scalar/list preservation, field-specific ordinary suggestions, fixed-entity behavior, FK edit validation, and project validation retain their tested behavior.
* [x] The changed-file review confirms no backend, mapper, Core, or new project-validation implementation changes.
* [x] Deviations and follow-up work are recorded; no unresolved question affects implementation or validation.

If implementation finds repository behavior that conflicts with this plan, stop and report the verified source and test results before changing the design or broadening scope.
