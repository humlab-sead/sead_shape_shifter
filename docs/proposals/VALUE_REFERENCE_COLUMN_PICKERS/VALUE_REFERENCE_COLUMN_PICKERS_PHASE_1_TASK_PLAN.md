# Value Reference Column Pickers — Phase 1 Task Plan

## Phase Summary

**Phase:** [Phase 1: Preserve references in the form](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_PLAN.md#phase-1-preserve-references-in-the-form)

**Source proposal:** [Make `@value` References Usable in Column Pickers](VALUE_REFERENCE_COLUMN_PICKERS.md)

**Readiness:** Validated

**Goal:** Opening an entity and saving an unrelated form edit retains the reference text, scalar or list storage form, and column order in every in-scope column-list field. This supplies the field set and storage rules needed by later phases.

**Constraints and dependencies:** Keep API and YAML directive text raw; do not resolve or expand references in the editor. Preserve the existing Core resolution rules. Keep Fixed Entity Columns on their positional schema path. Phase 1 depends only on the proposal's approved field scope and storage rules; later backend resolution, validation, and picker actions are separate phases.

**Acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-6`): An unchanged form save preserves scalar references, mixed lists, manually entered valid paths, and both supported scalar legacy `+` expression forms in every in-scope control.
2. [x] `PH1-AC-2` (from `P-AC-1`): Fixed Entity Columns remain outside the new reference interaction and validation field set.

**Phase milestone:** `VM-1` checks stored shape and column order through form round trips, and confirms the fixed-column exclusion.

## Repository Findings

**Repository basis:** Branch `value-reference-column-pickers`, commit `f25bc0c6`, planning date 2026-10-24. The untracked phase plan was read as the source for this document. Initial status showed only that untracked plan; unrelated concurrent edits in `src/transforms/filter.py` and `tests/reconciliation/test_mapping_sidecar.py` were later observed and were not used. Graphify was used for navigation and the behavior below was checked in source and tests.

| Source | Verified behavior | Planning implication |
| --- | --- | --- |
| `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `normalizeChipField` | Keys and Columns accept scalar text as one chip. Deduplication and Drop Empty Rows use arrays only, so a scalar selection loads empty. Unnest data is passed through raw. | Normalize each in-scope chip field on both API and YAML entry paths, while retaining its raw storage form. |
| `EntityFormDialog.vue::buildEntityConfigFromFormData` | Keys, non-fixed Columns, and FK keys collapse one `@value:` chip to a scalar; deduplication and Drop Empty Rows always save selected columns as lists; unnest is copied unchanged. A literal-first scalar `+` expression can become a one-item list. | Serialize from current chips plus their original raw form. Preserve an unchanged scalar expression even when it does not start with `@value:`. |
| `EntityFormDialog.vue::formDataToYaml`, `handleSubmit`, `handleSubmitAndClose`, `buildDirtySnapshot` | YAML output, both Save actions, and dirty-state comparison use the same entity serializer. | One shape-preserving serializer must feed all four paths; saving must not depend on the selected tab. |
| `frontend/src/components/entities/ForeignKeyEditor.vue::cloneForeignKey`, `frontend/src/components/entities/foreignKeyEditorUtils.ts::normalizeForeignKeyKeys` | FK local and remote scalar keys become chip arrays; the editor emits cloned rows. | Keep original local and remote storage forms with each editable FK row through clone and emit, including row reorder or removal. Do not leak form-only data into saved FK objects. |
| `frontend/src/components/entities/UnnestEditor.vue` | Its `id_vars` and `value_vars` model expects arrays and currently accepts raw scalar props. | Normalize those two editor values to arrays and have the parent restore unchanged scalar forms on save. |
| `EntityFormDialog.vue` fixed branch in `buildEntityConfigFromFormData` and `buildFormDataFromEntity`; `backend/app/utils/fixed_schema.py` | Fixed Columns use ordered positional columns and values, with `fixed_schema` metadata when available. | Leave the fixed-column branch separate. Do not add Fixed Entity Columns to the Phase 1 field set or later reference checks. |
| `backend/app/api/v1/endpoints/entities.py`, `frontend/src/api/entities.ts::EntityResponse`, `src/configuration/resolve.py::ReferenceResolver` | The entity API carries raw `entity_data`; the Core resolver handles stored directives and legacy expressions. | Phase 1 needs frontend form changes only. Do not alter the API, mapper, resolver, or stored YAML contract. |

## Scope

**In scope:** Business Keys (`keys`); non-fixed Columns (`columns`); each FK's `local_keys` and `remote_keys`; unnest `id_vars` and `value_vars`; Deduplication Columns (`drop_duplicates`); and Drop Empty Rows (`drop_empty_rows`). Preserve raw scalar strings, ordered lists with literal and reference items, and existing supported scalar `+` expressions in these fields. Preserve ordinary manual chip entry and existing boolean behavior for the two optional row operations.

**Out of scope:** Fixed Entity Columns; reference completion, inspection, replacement, and the new saved-project reference validator; Core directive parsing or resolution; backend contracts; storage migration; scalar fields outside this list. Existing Fixed Entity Columns may retain their current positional behavior, but must not enter the shared column-list reference handling.

**Affected files:** The entity form and unnest editor, their component tests, and a small frontend column-list value helper (`NEW`). The FK editor and its existing normalization helper are consumers to verify; change them only if the planned FK row-origin test shows the current clone path drops that form-only data. No backend, Core, configuration, or user documentation change is required for this compatibility phase.

## Work Breakdown

### Area 1: Preserve raw form in the entity dialog

**Objective:** A form or YAML load gives each in-scope chip control editable arrays without losing the original scalar or list value needed for an unchanged save.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue::normalizeChipField`, `buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`; `frontend/src/components/entities/columnListValue.ts` (`NEW`).

**Dependencies:** None.

**Tasks**

* [x] `T1.1` **Implement:** Add one form-local column-list value helper for chip normalization and shape-aware serialization.
  * **Target:** `frontend/src/components/entities/columnListValue.ts` (`NEW`); use it from `EntityFormDialog.vue`.
  * **Current → required:** Several field-specific conversions discard scalar/list origin → an unchanged chip sequence returns its original raw scalar or ordered list, including whitespace and a literal-first `+` expression stored as one scalar.
  * **Implementation:** Normalize a scalar string to one chip and list items to ordered chips. Compare current chips with the original value after the same normalization used by that editor; when equal, emit the original scalar or list value. For an edited/new single simple `@value:` chip, use the existing scalar shorthand; otherwise emit an ordered list. Do not parse, resolve, flatten, sort, or deduplicate reference expressions.
  * **Constraints:** Preserve current handling of empty selections and non-reference literal lists. Do not apply this helper to Fixed Entity Columns.
  * **Validation:** `V-1` in `EntityFormDialog.test.ts`: scalar `@value`, one-item list, mixed ordered list, `@value`-first expression, and literal-first expression retain their stored shapes after an unrelated edit and Save.

* [x] `T1.2` **Update:** Record and refresh original values for the dialog's top-level column-list controls on API load, YAML edit, and successful save; serialize them through the helper.
  * **Target:** `EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `formDataToYaml`, `handleSubmit`, `handleSubmitAndClose`.
  * **Current → required:** Deduplication and Drop Empty Rows scalar references appear as empty selections and save as a boolean or list → both controls show the scalar as one chip and save it as the same scalar when untouched; Business Keys and non-fixed Columns also retain one-item list and scalar legacy shapes.
  * **Implementation:** Keep original raw values separate from editable chip arrays and update that origin when YAML content becomes the active form data. Use the same serializer for preview drafts, YAML output, dirty comparison, Save, and Save & Close. After a successful save, advance the origin to the saved values so later edits compare with the current stored form. Keep optional row-operation disabled/empty behavior and `check_functional_dependency` intact.
  * **Constraints:** A field edit may change its shape according to current single-reference shorthand; unrelated edits must not. Retain the fixed-column `normalizeEditableFixedColumns` branch and its column order.
  * **Validation:** `V-1`, `V-3`: assert selected chips and exact `entity_data` passed to `update`, plus YAML-to-form round trip and fixed positional order.

**Completion evidence:** All four direct chip controls show existing scalar references, and the shared serializer emits their original values after an unrelated edit in either form or YAML mode.

### Area 2: Preserve nested FK and unnest values

**Objective:** FK and unnest chip editors accept scalar references while keeping each unchanged nested field's stored form.

**Affected code:** `EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `handleForeignKeysUpdate`; `frontend/src/components/entities/UnnestEditor.vue`; `ForeignKeyEditor.vue::cloneForeignKey` if its existing clone path does not retain row origin.

**Dependencies:** Area 1 helper and origin rules.

**Tasks**

* [x] `T2.1` **Update:** Keep each FK row's original `local_keys` and `remote_keys` form with that row, then serialize only public FK fields.
  * **Target:** `EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `handleForeignKeysUpdate`; verify `ForeignKeyEditor.vue::cloneForeignKey` and adjust it only if needed.
  * **Current → required:** The FK editor turns scalar keys into arrays, and the parent recognizes only `@value:`-first scalar values → both supported scalar legacy expressions and unchanged one-item lists retain their original forms for local and remote keys.
  * **Implementation:** Add form-only per-row origin for the two key fields on load; carry it through FK editor clone/update and row removal. Compare with the FK editor's normalized initial chips, since `normalizeForeignKeyKeys` deduplicates them, then use Area 1 serialization to restore untouched raw values. Build saved FK objects from the existing allowed fields so origin metadata never reaches API/YAML data. New FK rows use the existing single-reference shorthand when no origin exists.
  * **Constraints:** Keep ordinary FK settings (`entity`, `how`, `constraints`, `extra_columns`, `drop_remote_id`) and manual key entry unchanged. Preserve key order and existing directive text.
  * **Validation:** `V-1`, `V-2`: local and remote scalar/list variants round-trip through an emitted FK edit; removing a preceding FK row does not change the surviving row's shape, and request data contains no form-only metadata.

* [x] `T2.2` **Update:** Normalize unnest scalar references for `id_vars` and `value_vars`, and restore their unchanged raw forms on serialization.
  * **Target:** `frontend/src/components/entities/UnnestEditor.vue` model initialization and prop watcher; `EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`.
  * **Current → required:** The unnest editor passes scalar values to array chip controls → each scalar appears as one chip, while an untouched scalar or one-item list retains its original form after other unnest settings change.
  * **Implementation:** Clone incoming unnest settings into an editor model with array chip fields. Avoid mutating props and feedback loops in deep watchers. In the parent, serialize `id_vars` and `value_vars` against their raw origin and preserve `var_name`, `value_name`, and any other existing unnest settings without copying form-only data.
  * **Constraints:** Preserve current empty/default behavior and ordered list values.
  * **Validation:** `V-1`, `V-2`: both scalar fields render as single chips, emit editable arrays, and save in their original form; mixed lists and manual values remain ordered.

**Completion evidence:** An FK or unnest edit unrelated to a saved reference leaves that reference's text and stored shape unchanged in the saved request.

### Area 3: Verify the field set and round trips

**Objective:** Component tests prove the Phase 1 storage contract and make the Fixed Entity Columns exclusion explicit.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts`; existing `foreignKeyEditorUtils.test.ts` remains part of the focused run.

**Dependencies:** Areas 1 and 2.

**Tasks**

* [x] `T3.1` **Test:** Exercise the complete in-scope field matrix through dialog load, child editor updates, YAML edit, and saved request.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts`.
  * **Current → required:** Existing tests cover candidates and some manual entries but not scalar/list storage parity across all controls → tests assert each control's chip value and exact serialized field type, text, and order.
  * **Implementation:** Use saved `entity_data` fixtures with scalar simple references, one-item lists, mixed literal/reference lists, both scalar legacy `+` expression orders, and manually entered valid paths. Trigger an unrelated edit before Save because an unchanged edit dialog disables Save. Cover Save and Save & Close, then reload the returned shape. Include a YAML-to-form edit path and child editor emitted updates.
  * **Constraints:** Use component tests under `frontend/src`; Playwright e2e specs are currently skipped and are not the validation method for this phase.
  * **Validation:** `V-1`, `V-2`.

* [x] `T3.2` **Test:** Assert that Fixed Entity Columns remain on their positional path.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` existing fixed-entity fixtures and tests.
  * **Current → required:** Fixed columns already derive from `fixed_schema` and the values grid → tests confirm exact column and values order after a form save and no new reference UI or reference-field registration for fixed Columns.
  * **Implementation:** Extend an existing fixed-entity save case with a non-column edit and compare stored columns and positional values before/after. Assert the form's fixed Columns control does not receive the new shared reference handling. Record the confirmed Phase 1 field set in this plan for Phase 3 validation handoff.
  * **Constraints:** Do not introduce a Fixed Entity Columns scalar-reference fixture; that format is outside the approved scope.
  * **Validation:** `V-3`.

**Completion evidence:** Focused component tests cover every named field, both scalar legacy forms, list order, manual paths, and the fixed-column exclusion.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-6`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-1`, `V-2`, `V-4` | Every in-scope field shows saved references as chips and sends the same scalar/list form, text, and order after an unrelated edit; focused tests pass. |
| `PH1-AC-2` (from `P-AC-1`) | `T1.2`, `T3.2` | `V-3` | Fixed columns still use ordered positional serialization and have no new reference interaction or inclusion in the later validation field set. |

## Validation And Testing

Run commands from `frontend/`. A planned case is not a baseline pass. The existing `vue-tsc` failure is outside the Phase 1 files; compare diagnostics before declaring a regression.

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution result |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Dialog form/YAML/save round trips in `src/components/entities/__tests__/EntityFormDialog.test.ts` | `rtk pnpm test:run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH1-AC-1`, `VM-1` | New matrix passes: scalar simple and both legacy forms remain scalar; one-item/mixed lists and manual paths retain order and stored type across every in-scope control. | Pass for existing tests; new cases not run. | Pass: 1 file, 32 tests, including form, YAML, save, reload, and fixed positional cases. |
| `V-2` | Nested editor behavior in `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts`, and `foreignKeyEditorUtils.test.ts` under `src/components/entities/__tests__/` | `rtk pnpm test:run src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts src/components/entities/__tests__/foreignKeyEditorUtils.test.ts` | `PH1-AC-1`, `VM-1` | Scalar props become chips; edited lists emit in order; FK row origin survives clone and removal of a preceding row. Paired `V-1` assertions confirm saved data has no form-only metadata. | Pass for existing tests; new cases not run. | Pass: 3 files, 13 tests, including FK row-origin and unnest scalar cases. |
| `V-3` | Fixed positional regression in `EntityFormDialog.test.ts` | Run `V-1` and inspect fixed-entity assertions for stored columns, values, and absence of reference handling | `PH1-AC-2`, `VM-1` | Fixed column/value order is unchanged; fixed Columns stay excluded. | Pass for existing fixed tests; new exclusion assertion not run. | Pass via `V-1` and source review: the fixed serializer remains separate, and fixed Columns and positional values remain ordered after an unrelated edit. |
| `V-4` | Frontend quality checks | `rtk pnpm exec eslint src/components/entities/EntityFormDialog.vue src/components/entities/ForeignKeyEditor.vue src/components/entities/UnnestEditor.vue src/components/entities/columnListValue.ts src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts`; `rtk pnpm exec vue-tsc --noEmit` | Changed frontend files | Lint passes and type checking adds no new diagnostics. | Lint passed on existing affected component files. Type check failed before changes at `src/composables/__tests__/useMonacoYamlIntelligence.test.ts:36` (`TS7006`, implicit `any`). | Pass against baseline: ESLint exits 0; `vue-tsc` reports only the same TS7006 at the recorded unrelated test line. |
| `V-5` | Full frontend unit regression | `rtk pnpm test:run` | Existing frontend behavior | Suite passes, including `V-1`–`V-3`. | Not run: focused baseline was proportionate for planning. | Pass: 51 test files and 775 tests passed; no unhandled errors. |

The combined focused baseline (`V-1` plus `V-2`) passed before implementation: 4 files, 39 tests. The post-implementation focused checks passed: 4 files, 45 tests. No migration, generated artifact, authorization, or backend contract check is needed because this phase changes only frontend form conversion and makes no API call or server-side rule change.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Column-list value helper (`NEW`) | `frontend/src/components/entities/columnListValue.ts` | `T1.1` | Shape-aware normalization/serialization used by the form. |
| Form load/save and YAML compatibility | `frontend/src/components/entities/EntityFormDialog.vue` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | Raw shapes retained across in-scope fields and both Save paths; fixed branch separate. |
| Unnest chip normalization | `frontend/src/components/entities/UnnestEditor.vue` | `T2.2` | Scalar props shown as editable array chips without prop mutation. |
| FK clone change, only if the origin test requires it | `frontend/src/components/entities/ForeignKeyEditor.vue` | `T2.1` | Per-row origin survives clone and emit; no saved metadata. |
| Component regressions | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`, `UnnestEditor.test.ts` | `T3.1`, `T3.2` | `V-1`–`V-3` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Preserve raw form | Done | None | `T1.1`–`T1.2` complete; `V-1` and `V-4` pass. |
| Area 2: Nested fields | Done | Area 1 | `T2.1`–`T2.2` complete; FK clone already carries row origin, verified by `V-2`. |
| Area 3: Round-trip tests | Done | Areas 1–2 | `T3.1`–`T3.2` complete; confirmed field set: keys, non-fixed columns, FK local/remote keys, unnest ID/value variables, deduplication columns, and drop-empty columns. Fixed Entity Columns remain excluded. |

## Definition Of Done

* [x] `PH1-AC-1` and `PH1-AC-2` have passing implementation and validation results for `VM-1`.
* [x] Areas 1–3 and every required deliverable are complete; conditional FK editor changes are made only if its tests require them.
* [x] `V-1`, `V-2`, `V-3`, `V-5`, and focused lint pass; `vue-tsc` has no new diagnostics relative to its recorded unrelated baseline failure.
* [x] Regression tests preserve scalar/list form, expression text, manual paths, column order, optional row-operation booleans, and fixed positional values.
* [x] API/YAML data contains no form-only origin metadata; backend, Core, and stored-format contracts remain unchanged. No migration or generated artifact needs synchronization.
* [x] Any deviation or follow-up is recorded, and no unresolved question affects implementation or validation.

If implementation reveals a repository contract that conflicts with this verified plan, stop and report the conflicting source and test result before changing the design or expanding scope.
