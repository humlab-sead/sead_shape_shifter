# Value Reference Column Pickers — Phase 4 Task Plan

## Phase Summary

**Goal:** Add guided `@value` entry and read-only inspection of ordered columns in the entity editor, using the current unsaved entity draft.

**Readiness:** Validated. The phase plan marks Phase 4 ready once Phases 1–3 provide their contracts. The current repository has the form-shape preservation, authorized draft-aware completion and resolution routes, and saved-project reference checks; focused tests for those contracts pass. No decision remains that changes this implementation.

**Sources:** [Proposal](VALUE_REFERENCE_COLUMN_PICKERS.md) and [phase plan](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_PLAN.md), Phase 4. This plan implements `VM-4` and preserves the following mappings:

1. [x] `PH4-AC-1` (from `P-AC-1`): Ordinary suggestions stay field-specific; FK key pickers stop appending the project-wide path list, and saved selected references remain visible.
2. [x] `PH4-AC-2` (from `P-AC-2`): Typing `@value` narrows entity and list-valued-property choices, while a full manually entered reference remains editable and checkable.
3. [x] `PH4-AC-3` (from `P-AC-3`): Inspection shows ordered draft-derived columns or a clear unresolved status without saving or changing the field.
4. [x] `PH4-AC-4` (from `P-AC-7`): Keyboard operation, project read authorization, and stale-result handling work for completion and inspection.

**Dependencies and limits:** Keep Phase 1's scalar/list and legacy `+` expression storage behavior; keep Phase 2's mapper-owned resolution and read authorization; leave Phase 3's saved-project errors in the existing validation flow. Do not add reference interaction to Fixed Entity Columns, change directive syntax, alter saved YAML, or add Phase 5 conflict annotations or **Replace with columns**.

## Repository Findings

**Repository basis:** Branch `value-reference-column-pickers`, commit `3259fde7`, planning date 2026-10-24. The untracked phase plan was read as the requested source. Other uncommitted backend test and documentation changes present during planning were not used or changed. Graphify's scoped query was used for navigation; the findings below were checked in source and tests.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/models/column_reference.py`; `backend/app/api/v1/endpoints/column_references.py`; `backend/app/services/column_reference_service.py` | Authorized POST `.../column-references/complete` accepts `entity_draft`, `prefix`, `edited_field_path`, and `preferred_entity`, and returns full directive candidates. POST `.../resolve` accepts `entity_draft` and a complete simple `directive`, and returns ordered `columns` or `status: unresolved` with a reason. The service checks candidates independently. | Add typed frontend calls to these routes. Do not parse or resolve directives in the browser or extend `/valid-directives`. |
| `frontend/src/api/entities.ts::entitiesApi.getColumnAvailability`; `frontend/src/composables/useColumnAvailability.ts::useColumnAvailability` | The entity API uses `apiRequest`; column availability requests are debounced and versioned against the draft. | Follow these API and stale-request patterns while keeping reference completion separate from ordinary column availability. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData` | The helper serializes the draft used by preview and column availability; its form controls use `columnAvailability` for Business Keys, Columns, Deduplication Columns, and Drop Empty Rows. The fixed Columns control shares the visual location with non-fixed Columns. | Send this serialized draft to reference routes. Enable the new control for Business Keys and the three other eligible controls, but retain the existing plain combobox for Fixed Entity Columns. |
| `frontend/src/components/entities/UnnestEditor.vue::cloneUnnest`; `EntityFormDialog.vue` Unnest mount | ID and Value Variables have separate ordinary candidates. The child normalizes scalar references into chips and emits form changes. | Pass the current serialized draft and field identity into both controls without changing their normalization or emitted values. |
| `frontend/src/components/entities/ForeignKeyEditor.vue::getLocalColumnItems`, `getRemoteKeyItems`, `getExtraColumnSourceItems`, `loadDirectives`, `validateLocalKeys`, `validateRemoteKeys` | Local/remote key suggestions append `getValidDirectives()` results on focus, and local suggestions also include references found in Columns. A separate saved-project directive check runs after key edits. Extra Column's Remote Column also receives the broad list. | Remove broad-path additions from these ordinary item lists. Use the draft-aware resolve route for committed FK key references; preserve free text and selected saved chips. Leave Extra Column outside the new reference interaction. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts`; `frontend/src/composables/__tests__/useColumnAvailability.test.ts` | Existing tests cover saved scalar/list round trips, FK candidate context, and stale column-availability results. The FK test still expects the old broad directive list. | Update that expectation and add tests for the new behavior without weakening Phase 1 storage checks. |

## Scope

**In scope:** Typed frontend requests; a reusable Vue/Vuetify column-list control with progressive `@value` entry, manual-entry checking, and per-chip inspection; integration for Business Keys, non-fixed Columns, Deduplication Columns, Drop Empty Rows, FK Local/Remote Keys, and unnest ID/Value Variables; removal of broad path suggestions from FK ordinary items; component and contract tests plus a keyboard/read-authorization check.

**Out of scope:** Fixed Entity Columns, FK Extra Columns as a reference-capable field, Phase 5 conflict attribution and replacement, backend route or Core changes, saved-project validation redesign, data migrations, and editing legacy `+` expressions. Keep a legacy expression as one raw chip; do not send it to the simple-reference inspection route.

**Data flow:** A control receives field-specific ordinary candidates and the serialized entity draft from `EntityFormDialog.vue`. Completion calls the existing `complete` route only while editing an `@value` prefix. A committed simple path or inspection action calls `resolve` with the same draft. Both routes already enforce `require_project(Action.READ)`; frontend errors must not turn a denied or failed read into a guessed list. Selection stays in form state until the ordinary save flow runs.

## Work Breakdown

### Area 1: Add the typed request and stale-result handling

**Objective:** Completion and inspection consume the Phase 2 routes with a current draft snapshot and never display results from an older request.

**Affected code:** `frontend/src/api/entities.ts::entitiesApi`; `frontend/src/composables/useColumnAvailability.ts` as a pattern; `frontend/src/composables/useColumnReferences.ts` (`NEW`); `frontend/src/composables/__tests__/useColumnReferences.test.ts` (`NEW`); `frontend/src/api/__tests__/entities.columnReferences.test.ts` (`NEW`).

**Dependencies:** Existing Phase 2 HTTP contract.

**Tasks**

* [x] `T1.1` **Add:** Typed `completeColumnReferences` and `resolveColumnReference` methods and matching request/response interfaces.
  * **Target:** `frontend/src/api/entities.ts::entitiesApi`; `frontend/src/api/__tests__/entities.columnReferences.test.ts` (`NEW`).
  * **Current → required:** The routes exist but `entitiesApi` exposes only column availability → both read operations use `apiRequest` and the exact backend payloads and response statuses.
  * **Implementation:** Model `candidates`, `directive`, `path`, `resolved`/`unresolved`, nullable `columns`, and backend reason codes. POST under `/projects/{projectName}/entities/{entityName}/column-references/{complete|resolve}`. Keep the raw directive and draft in the request; do not use the saved-project `validate-directive` or `valid-directives` endpoints.
  * **Validation:** `V-1`: assert both URLs and payloads, including `edited_field_path` and `preferred_entity`; typed unresolved responses remain available to callers.

* [x] `T1.2` **Implement:** A per-control request manager for completion and inspection.
  * **Target:** `frontend/src/composables/useColumnReferences.ts` (`NEW`); `frontend/src/composables/__tests__/useColumnReferences.test.ts` (`NEW`).
  * **Current → required:** Column availability versions its requests, but reference requests have no frontend state → results are cleared as soon as the input, entity, project, field, or serialized draft changes, including while an older call is pending.
  * **Implementation:** Debounce completion after a typed prefix; request only when the prefix starts `@value`. Resolve only a committed complete simple path or an inspected simple chip; use a syntax-only check to exclude legacy `+` expressions, leaving path resolution to the backend. Track separate completion and inspection generations plus the request inputs; ignore older success and error responses, and invalidate on control teardown. Keep unresolved reason text and HTTP errors distinct. Do not cache a result across drafts or persist a draft.
  * **Validation:** `V-1`: delayed old completion/resolve responses cannot overwrite newer results; a later edit clears shown columns and errors before the next response; unrelated backend failures do not become candidates or columns; empty and malformed input do not trigger a preview.

**Completion evidence:** Both frontend calls use authorized backend routes, and tests prove that only results matching the current draft and field can be shown.

### Area 2: Build one accessible reference-capable column control

**Objective:** A user can enter a reference in steps and inspect a selected simple reference while keeping ordinary column suggestions short.

**Affected code:** `frontend/src/components/entities/ColumnReferenceCombobox.vue` (`NEW`); `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`); existing Vuetify `v-combobox` use in the entity editors.

**Dependencies:** Area 1.

**Tasks**

* [x] `T2.1` **Implement:** Progressive entry within a reusable multi-chip combobox.
  * **Target:** `frontend/src/components/entities/ColumnReferenceCombobox.vue` (`NEW`); `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`).
  * **Current → required:** Each field shows only its ordinary items or FK's broad list → ordinary items stay field-specific, and `@value` input offers backend-filtered root, entity, and eligible property choices.
  * **Implementation:** Accept `modelValue`, ordinary items, project/entity names, current serialized draft, edited field path, optional preferred entity, and existing field display/disabled props. Forward each field's rules, error state, and message slot to the underlying combobox. Use Vuetify combobox search updates for the typed prefix; present reference candidates only during reference entry. Selecting an intermediate `@value: entities.` or `entities.<name>.` choice continues the search instead of storing an incomplete chip. Selecting a complete property stores its full raw directive. Keep free-text entry for a complete manual path and add a small **Insert reference** action that starts the same flow. Preserve order, chip removal, and literal entry; never add all reference paths to ordinary items.
  * **Constraints:** Do not interpret directive values in TypeScript. Preserve stored scalar/list origin in the parent serializer and leave legacy `+` chips untouched.
  * **Validation:** `V-2`: prefix progression, list-valued `keys`/`columns`, filtered entities/properties, no incomplete chip, manual valid/invalid path, literals and selected saved chips, and keyboard completion.

* [x] `T2.2` **Implement:** Read-only inspection and local errors for a selected simple reference chip.
  * **Target:** `frontend/src/components/entities/ColumnReferenceCombobox.vue` (`NEW`); `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`).
  * **Current → required:** A chip hides its columns and a committed manual reference may have no local diagnosis → its inspection action shows the original path and ordered current columns or the backend's unresolved reason without changing the selected value.
  * **Implementation:** Add a keyboard-focusable, labeled inspection button to simple `@value:` chips. Request inspection on activation, not on every keystroke. Show loading, ordered columns including duplicates, empty-list result, or unresolved reason. Check a manually committed simple path through the same resolve call and show its local error. Keep an invalid saved chip visible and editable. Do not offer inspection of a legacy `+` expression as if it were a simple path, and do not expose replacement in this phase.
  * **Validation:** `V-2`: ordered/nested result, empty list, missing path, wrong type, broken dependency, unchanged model, keyboard opening/closing, and stale result dismissal.

**Completion evidence:** The shared control accepts ordinary and reference input, and a selected chip can show only a result from the current draft without changing the form.

### Area 3: Connect the main form and unnest fields

**Objective:** All non-FK in-scope controls use the same draft and reference interaction while Fixed Entity Columns remain plain.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`; `frontend/src/components/entities/UnnestEditor.vue::cloneUnnest`; their existing component tests.

**Dependencies:** Area 2.

**Tasks**

* [x] `T3.1` **Wire:** Business Keys, non-fixed Columns, Deduplication Columns, and Drop Empty Rows to the shared control.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  * **Current → required:** These fields receive stage-aware ordinary items but no reference completion or inspection → pass those same items and `buildEntityConfigFromFormData({ includeDerivedSqlColumns: true })` to the shared control, with each field's `entities.<name>.<field>` path.
  * **Implementation:** Compute the serialized draft once per form change and share it with the controls and child editors, rather than creating a fresh request object for each render. Keep the existing `formData` models, enabled/disabled rules, and `columnListOrigins` serialization. Only the Columns branch for `formData.type !== 'fixed'` uses the shared control; Fixed Entity Columns keep the existing combobox. Ensure a new or renamed entity uses its current form name in request URLs and field paths.
  * **Validation:** `V-3`: each field receives its own ordinary candidates and current draft; fixed Columns have no new action; unchanged scalar, mixed-list, and literal-first legacy expression forms still save as before.

* [x] `T3.2` **Wire:** Unnest ID and Value Variables to the shared control.
  * **Target:** `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  * **Current → required:** Unnest normalizes references but only offers separate ordinary items → pass the serialized parent draft, project/entity names, and `unnest.id_vars` or `unnest.value_vars` field paths through the child while keeping those separate item lists.
  * **Implementation:** Continue using `cloneUnnest`, the existing `update:modelValue` flow, and parent storage origins. A child edit must reach the parent serializer before its debounced reference request is sent. Disabling unnest clears its reference result and performs no read request.
  * **Validation:** `V-3`: both fields retain their distinct candidates, scalar/mixed references and chip order survive a save, and preview uses current unnest edits.

**Completion evidence:** Every non-FK in-scope control can complete and inspect a reference from the current serialized draft; Fixed Entity Columns cannot.

### Area 4: Replace FK broad suggestions and verify the editor flow

**Objective:** FK Local/Remote Keys use local or remote context with typed completion; old untyped path suggestions disappear.

**Affected code:** `frontend/src/components/entities/ForeignKeyEditor.vue::getLocalColumnItems`, `getRemoteKeyItems`, `getExtraColumnSourceItems`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Areas 2–3.

**Tasks**

* [x] `T4.1` **Replace:** FK key directive loading and saved-project-only checks with the shared draft-aware interaction.
  * **Target:** `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`.
  * **Current → required:** Focus appends `valid-directives` to both key lists, and key edits call `validate-directive` against saved data → local and remote key inputs keep only their field-specific ordinary items and use `complete`/`resolve` with the current draft.
  * **Implementation:** Pass the serialized parent draft through the FK editor. Use `preferred_entity = current entity` for Local Keys and the selected FK target for Remote Keys; pass distinct indexed edited-field paths and retain FK row identity when targets or rows change. Remove `loadDirectives`, broad-path additions, and old key-only validation/error state that would contradict draft-aware results. Remove the broad list from Extra Column's Remote Column ordinary items too, without adding the new interaction to that out-of-scope field. Keep free-text input and saved selected references visible even when absent from ordinary items. Ensure the parent receives FK edits before a debounced request takes its draft snapshot.
  * **Validation:** `V-3`: local/remote preferred order, two FK rows and target change, saved-chip visibility, free text, selected manual path checking, no `valid-directives` call, and current FK draft in request bodies.

* [x] `T4.2` **Verify:** Cross-field user behavior and authorization in the running editor.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`; `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`).
  * **Current → required:** Existing tests prove Phase 1 form storage and field candidates, but not keyboard entry, stale reference results, or denied reads → cover the complete Phase 4 user path without changing backend contracts.
  * **Implementation:** Test a saved simple reference, a mixed list, a nested result, an unrelated broken reference, and a broken requested dependency. Make a later draft edit, entity rename, FK target change, dialog close, or control disable invalidate pending results. Simulate keyboard search and inspection; also run the manual authorized/denied request check in `V-4` because a stubbed component cannot establish real read behavior.
  * **Validation:** `V-2`–`V-5`.

**Completion evidence:** No FK key picker loads the project-wide path list, and all in-scope controls pass the Phase 4 scenarios without changing saved data until Save.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH4-AC-1` (from `P-AC-1`) | `T2.1`, `T3.1`, `T3.2`, `T4.1` | `V-2`, `V-3`, `V-5` | Ordinary items stay field-specific; FK broad paths disappear; selected saved references remain visible; Fixed Entity Columns stay plain. |
| `PH4-AC-2` (from `P-AC-2`) | `T1.1`, `T2.1`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4` | Progressive root/entity/property results, manual full-path checks, and independently available valid candidates. |
| `PH4-AC-3` (from `P-AC-3`) | `T1.2`, `T2.2`, `T3.1`, `T3.2`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4` | Ordered draft columns or local reason; inspection leaves the chip and saved project unchanged. |
| `PH4-AC-4` (from `P-AC-7`) | `T1.2`, `T2.1`, `T2.2`, `T4.2` | `V-1`, `V-2`, `V-3`, `V-4` | Keyboard entry/inspection, authorized reads, denied reads, and stale-response rejection. |

## Validation And Testing

Run commands from `frontend/` unless stated otherwise. `V-1`–`V-4` fulfill `VM-4`; `V-5` checks preservation. Planned `NEW` tests have no planning baseline.

| ID | Check and target | Command or method | Covers | Expected result | Baseline / execution result |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Typed API and request manager in `src/api/__tests__/entities.columnReferences.test.ts` (`NEW`) and `src/composables/__tests__/useColumnReferences.test.ts` (`NEW`) | `rtk pnpm exec vitest run src/api/__tests__/entities.columnReferences.test.ts src/composables/__tests__/useColumnReferences.test.ts` | `PH4-AC-2`–`PH4-AC-4` | Exact route/payload contract; delayed old success and error responses never appear; current draft wins. | Planning baseline not run: both files were new. Execution: Pass, 7 tests. |
| `V-2` | Shared control in `src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`) | `rtk pnpm exec vitest run src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` | `PH4-AC-1`–`PH4-AC-4` | Progressive typed and keyboard entry; saved/manual chips, ordered/empty/unresolved inspection, and no model change on inspection. | Planning baseline not run: file was new. Execution: Pass, 6 tests, including incomplete-prefix blur handling. |
| `V-3` | Form, FK, and unnest integration tests | `rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts src/composables/__tests__/useColumnAvailability.test.ts` | `PH4-AC-1`–`PH4-AC-4` | Current serialized draft and FK context reach controls; old broad list is absent; scalar/list/legacy storage and ordinary candidates remain correct. | Planning baseline: Pass, 44 tests. Execution: Pass, 47 tests. |
| `V-4` | Running editor and authorized read behavior | Run `make backend-run` and `make frontend-run` in separate terminals from the repository root. In an authorized project, edit an entity with a saved `@value: entities.site.keys` and another unrelated bad reference; type `@value`, select entity then `keys`, inspect, change unsaved `site`-dependent draft columns or the selected chip, then inspect again. Use Tab, arrows, Enter, and Escape. In browser network tools, repeat a `complete` and `resolve` POST without project read access. | `PH4-AC-2`–`PH4-AC-4` | Ordered columns come from the current draft, unrelated failure does not hide them, old results disappear after edits, no save occurs, keyboard controls work, and denied requests fail without revealing columns. | Execution: Pass using the isolated backend on port 8014 and Vite on 5173. In the authorized browser flow, ArrowDown/Enter completed the root, entity, and property choices; inspection showed ordered unsaved columns; a delayed result disappeared after a draft edit and re-inspection showed the added column. Tab left an incomplete `@value` prefix out of saved chips, and Escape closed the suggestions. A draft with an unrelated broken `drop_empty_rows` reference still returned valid candidates. Authorized completion and resolve returned 200; an authenticated principal without project access received 404, and a missing identity received 401. A project GET after the flow still showed the original saved keys and columns. The minimal fixture also returned 500 from task-status and stage-aware column-availability requests; the column-reference flows remained successful. |
| `V-5` | Existing backend contract plus frontend regressions and quality | Run the exact commands below from the indicated directories. | `PH4-AC-1`, preservation, authorization | Backend and frontend focused tests pass; lint/format introduce no errors; TypeScript has no new errors. | Planning baseline: Pass, 28 backend tests and 44 frontend tests. Execution: Pass, 28 backend tests and 47 frontend tests; ESLint and Prettier pass. `vue-tsc` still reports only the baseline `TS7006` at `src/composables/__tests__/useMonacoYamlIntelligence.test.ts:36`. |

`V-5` commands:

```bash
# Repository root
rtk uv run pytest -p no:cacheprovider backend/tests/api/v1/test_column_references.py backend/tests/services/test_column_reference_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/authorization/test_cross_resource_access.py -q

# frontend/
rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts src/composables/__tests__/useColumnAvailability.test.ts
rtk pnpm exec eslint src/api/entities.ts src/api/__tests__/entities.columnReferences.test.ts src/composables/useColumnReferences.ts src/composables/__tests__/useColumnReferences.test.ts src/components/entities/ColumnReferenceCombobox.vue src/components/entities/__tests__/ColumnReferenceCombobox.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/ForeignKeyEditor.vue src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/UnnestEditor.vue src/components/entities/__tests__/UnnestEditor.test.ts
rtk pnpm exec prettier --check src/api/entities.ts src/api/__tests__/entities.columnReferences.test.ts src/composables/useColumnReferences.ts src/composables/__tests__/useColumnReferences.test.ts src/components/entities/ColumnReferenceCombobox.vue src/components/entities/__tests__/ColumnReferenceCombobox.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/ForeignKeyEditor.vue src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/UnnestEditor.vue src/components/entities/__tests__/UnnestEditor.test.ts
rtk pnpm exec vue-tsc --noEmit

# Repository root, after implementation code changes
GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .
```

## Deliverables

| Deliverable | Target | Task IDs | Completion result |
| --- | --- | --- | --- |
| Typed frontend read methods | `frontend/src/api/entities.ts` | `T1.1` | Both backend route contracts are represented. |
| API contract tests | `frontend/src/api/__tests__/entities.columnReferences.test.ts` (`NEW`) | `T1.1` | `V-1` checks request paths and bodies. |
| Current-draft request manager and tests | `frontend/src/composables/useColumnReferences.ts` (`NEW`); `frontend/src/composables/__tests__/useColumnReferences.test.ts` (`NEW`) | `T1.2` | Old completion and inspection results are ignored. |
| Shared picker and tests | `frontend/src/components/entities/ColumnReferenceCombobox.vue` (`NEW`); `frontend/src/components/entities/__tests__/ColumnReferenceCombobox.test.ts` (`NEW`) | `T2.1`, `T2.2`, `T4.2` | Progressive entry and read-only inspection work with keyboard input. |
| Main form integration and tests | `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T3.1`, `T3.2`, `T4.1`, `T4.2` | In-scope fields use current draft; Fixed Entity Columns remain plain. |
| Unnest integration and tests | `frontend/src/components/entities/UnnestEditor.vue`; `frontend/src/components/entities/__tests__/UnnestEditor.test.ts` | `T3.2` | Both variable lists retain order and storage behavior. |
| FK integration and tests | `frontend/src/components/entities/ForeignKeyEditor.vue`; `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `T4.1`, `T4.2` | Local/remote keys use typed draft checks and no broad path list. |
| Generated graph, if the required post-code update changes it | `graphify-out/graph.json` | `T4.2` | `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .` succeeds after implementation; generated changes are reviewed. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Typed requests and stale results | Done | Phase 2 route contract | `T1.1`–`T1.2` complete; `V-1` passes with delayed stale success and error coverage. |
| Area 2: Shared control | Done | Area 1 | `T2.1`–`T2.2` complete; `V-2` passes for keyboard entry, inspection, errors, and chip preservation. |
| Area 3: Main form and unnest | Done | Area 2 | `T3.1`–`T3.2` complete; `V-3` passes, including existing scalar/list and legacy expression round trips. |
| Area 4: FK and editor verification | Done | Areas 2–3 | `T4.1`–`T4.2` complete; `V-4` passes with keyboard, current-draft, stale-result, and authorization checks. |

## Definition Of Done

* [x] Every `PH4-AC-*` criterion has a completed task and passing validation result for `VM-4`.
* [x] All four areas and every listed deliverable are complete.
* [x] `V-1`–`V-5` pass, or any pre-existing failure is recorded with a before/after comparison; frontend type checking introduces no new error.
* [x] Saved scalar, mixed-list, manual-path, and legacy `+` expression forms remain unchanged through form/YAML saves; valid Core resolution is unchanged.
* [x] Fixed Entity Columns and FK Extra Columns have no new reference interaction; Phase 5 actions and annotations are absent.
* [x] Unauthorized read requests reveal no columns; unsaved drafts are never persisted by completion or inspection; stale results are discarded.
* [x] Graphify is updated after implementation code changes, any generated changes are reviewed, and deviations or follow-up work are recorded.

If implementation finds a current source or test contract that conflicts with this verified plan, stop and report the conflicting file and result before changing the design or broadening scope.

## Risks And Open Questions

Vuetify's combobox can commit a search value as a free-text chip. The intermediate root and entity choices must update the search without committing incomplete directives; `V-2` and `V-4` check this. FK edits flow through a child component before the parent serializes the full draft, so requests must wait for that update and reject responses tied to an older FK target or row; `V-1` and `V-3` check this. These are implementation risks with specified checks, not unresolved decisions.
