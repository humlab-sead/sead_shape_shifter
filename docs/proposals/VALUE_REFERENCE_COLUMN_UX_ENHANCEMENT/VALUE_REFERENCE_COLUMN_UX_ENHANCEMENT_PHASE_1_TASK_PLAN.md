# `@value` Column Picker UX — Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Safe cached reference data. **Readiness:** Validated. The [proposal](./VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT.md) is still marked Proposed feature. This plan implements the Phase 1 output in the [phase plan](./VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT_PHASE_PLAN.md): a project-owned entity cache, a frontend expansion result, and unchanged form-value round trips. It does not add picker suggestions or preview UI. The phase has no earlier-phase dependency and uses the proposal's cached-data and supported-syntax rules.

**Acceptance criteria** (`VM-1` in the phase plan):

1. [ ] `PH1-AC-1` (from `P-AC-1`): Reference results are available only after a completed cache load for the active project.
2. [ ] `PH1-AC-2` (from `P-AC-2`): Supported scalar and nested list-item references expand like Core, in the same order and with duplicates retained.
3. [ ] `PH1-AC-3` (from `P-AC-3`): A missing cache, entity, or path, a cycle, or an unsupported nested value returns no partial columns.
4. [ ] `PH1-AC-4` (from `P-AC-5`): An unchanged load and save retains scalar references, mixed lists, and legacy `+` expressions in their original scalar or list form.

## Repository Findings

**Repository basis:** `value-reference-column-ux-enhancement` at `8f633a5e`, planned 2026-10-25. The untracked Phase Plan was considered. No implementation changes were present when planning began.

| Verified source | Finding | Planning implication |
| --- | --- | --- |
| `frontend/src/api/entities.ts::entitiesApi.list`; `backend/app/api/v1/endpoints/entities.py::list_entities` | The list request returns each entity's raw `entity_data`; `EntityResponse.entity_data` is `Record<string, unknown>`. | Read references from the existing list. No new request or backend contract is needed. |
| `frontend/src/stores/entity.ts::fetchEntities`, `reset`, `createEntity`, `updateEntity`, `deleteEntity`, `syncCachedEntity`; `frontend/src/stores/project.ts::selectProject` | `currentProjectName` changes before the list completes; project selection resets the entity store. A late list response can still write after reset, and mutations can change `entities`. | Track completed-cache ownership separately from the requested project, reject stale responses, and keep ownership accurate after mutations. |
| `frontend/src/composables/useEntities.ts::fetch`; `frontend/src/views/ProjectDetailView.vue` | The project view loads entities through the entity store. | Keep existing store consumers working; expose one cache check for Phase 2 callers. |
| `src/configuration/resolve.py::ReferenceResolver._resolve_ref_value`; `tests/configuration/test_utility.py::_resolve` | Core recursively resolves references and flattens referenced lists in place. Existing tests cover basic flattening, but not the proposed nested entity fixture. | Compare supported acyclic frontend results with Core; do not change Core resolution. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `buildDirtySnapshot` | Form fields use arrays, and serializers collapse a one-item `@value` list to a scalar. Scalar `drop_duplicates` and `drop_empty_rows` values load as enabled with empty column arrays. YAML and Save both use the form conversion. | Retain original field shapes beside normalized editor values and restore them when the field is unchanged. Cover both entity and YAML load paths. |
| `frontend/src/components/entities/ForeignKeyEditor.vue::cloneForeignKey`; `frontend/src/components/entities/UnnestEditor.vue` | FK keys are normalized to arrays and emitted to the parent; unnest comboboxes expect arrays. | Keep the editors' array interface and test that the parent preserves loaded scalar forms. |
| `value-reference-column-pickers:frontend/src/composables/useColumnReferences.ts` | The prototype composable calls backend completion and resolution endpoints using a draft. | Do not port that data flow into Phase 1. |

## Scope

**In scope:** Entity-store cache ownership; a pure frontend helper for complete `@value: entities.<entity>.keys` and `.columns` references; form adapters for Business Keys, non-fixed Columns, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows; focused frontend tests and a Core parity test.

**Out of scope:** Picker suggestions and preview UI (Phase 2), Fixed Entity Columns changes, per-reference requests, unsaved-draft merging, backend or mapper changes, project validation, Core runtime changes, and the separate provider/schema business-key save guard. Existing field-specific suggestions, Save behavior, and fixed-entity handling remain as they are.

## Work Breakdown

### Area 1: Identify a completed project cache

**Objective:** Phase 2 can request the active project's entity list and receive either its completed list, including an empty list, or an unavailable result.

**Affected code:** `frontend/src/stores/entity.ts::fetchEntities`, `reset`, cache mutation methods; `frontend/src/components/entities/EntityFormDialog.vue::handleMaterialized`, `handleUnmaterialized`; `frontend/src/stores/__tests__/entity.test.ts`.

**Dependencies:** None.

**Tasks:**

* [ ] `T1.1` **Change:** Add a project-owned completed-cache check to the entity store.
  * **Target:** `frontend/src/stores/entity.ts::fetchEntities`, `reset`, `createEntity`, `updateEntity`, `deleteEntity`, `syncCachedEntity`; `frontend/src/components/entities/EntityFormDialog.vue::handleMaterialized`, `handleUnmaterialized`.
  * **Current → required:** The requested name can identify the previous list during a load → a proposed `getCompletedEntitiesFor(activeProjectName): EntityResponse[] | null` returns a list only when a successful, current load owns it. `[]` is a valid completed cache; `null` means unavailable.
  * **Implementation:** Keep completed ownership separate from `currentProjectName`. Invalidate it when a new list request begins or the store resets. Use a request generation so an older success or failure cannot re-establish ownership after a newer request or reset. Preserve ownership after same-project mutations; invalidate it if a mutation cannot be tied to the owned project. Pass `props.projectName` to the materialization refresh sync so that call can be checked. Leave normal entity-list and selected-entity behavior intact.
  * **Validation:** `V-1`: pending A→B switch, wrong active name, failed load, empty successful load, late response after reset, out-of-order responses, and same-project refresh.
* [ ] `T1.2` **Test:** Extend store tests for ownership and request ordering.
  * **Target:** `frontend/src/stores/__tests__/entity.test.ts::fetchEntities`, `reset`, cache mutation cases.
  * **Current → required:** Existing tests assert loaded entities and errors → new tests also assert the proposed cache check never exposes mixed, pending, or stale data.
  * **Implementation:** Use controlled promises for overlapping requests and reset; check that a completed empty list is distinct from unavailable. Check that same-project updates do not silently make ownership unknown and cross-project updates do not make a mixed list trusted.
  * **Validation:** `V-1`; assert the returned list or `null` and unchanged existing store behavior.

**Completion evidence:** Store tests demonstrate that only the latest completed list for the active project can feed reference expansion.

### Area 2: Expand supported references locally

**Objective:** Return a complete ordered column list for supported cached references, or one unavailable result.

**Affected code:** `frontend/src/utils/valueReferenceColumns.ts` **NEW**; `frontend/src/utils/__tests__/valueReferenceColumns.test.ts` **NEW**; `tests/configuration/test_utility.py::ReferenceResolver` tests.

**Dependencies:** Area 1 supplies a trusted entity list; the helper itself remains pure and testable with explicit input data.

**Tasks:**

* [ ] `T2.1` **Change:** Implement a pure reference parser and expansion helper.
  * **Target:** `frontend/src/utils/valueReferenceColumns.ts` **NEW**.
  * **Current → required:** There is no local expansion helper → a proposed `expandValueReference(reference: string, entities: EntityResponse[] | null): string[] | null` expands only complete `entities.<entity>.keys` or `.columns` paths from supplied cached entities, and returns `null` for unavailable cache input.
  * **Implementation:** At each referenced property, accept a literal string list, a scalar complete reference, or a mixed list of strings and complete references. Recursively flatten referenced lists in place; retain order and duplicates. Use a recursion stack so repeated sibling references are allowed but cycles fail. Reject missing paths, nulls, numbers, objects, nested arrays, partial or legacy `+` expressions, and other directive text as one unavailable result. Never return partial columns or mutate input. Keep `[]` distinct from `null`.
  * **Validation:** `V-2`, `V-3`; compare only supported acyclic forms with Core, and test failure cases in the frontend.
* [ ] `T2.2` **Test:** Pin down expansion and Core parity.
  * **Target:** `frontend/src/utils/__tests__/valueReferenceColumns.test.ts` **NEW**; `tests/configuration/test_utility.py`.
  * **Current → required:** Core tests cover simple references and list flattening → both suites use `site.keys = ['site_id', 'site_id']`, `site.columns = ['name', '@value: entities.site.keys']`, `sample.keys = '@value: entities.site.columns'`, and `sample.columns = ['sample_id', '@value: entities.sample.keys']`. Both expect `['sample_id', 'name', 'site_id', 'site_id']` from `sample.columns`.
  * **Implementation:** Test scalar and mixed references, nested list items, duplicate order, empty list, and repeated sibling references. Test missing cache input, entity/path, cycles, unsupported nested values and syntax; assert `null` without partial output and no input mutation. Add a Core test for the positive fixture only; leave Core code unchanged.
  * **Validation:** `V-2`, `V-3`.

**Completion evidence:** The frontend fixture matches Core for supported forms, while every unsupported or incomplete tree produces only `null`.

### Area 3: Preserve unchanged field representation

**Objective:** Opening a form and saving an unrelated edit does not rewrite reference fields from scalar to list or list to scalar.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `buildDirtySnapshot`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `ForeignKeyEditor.test.ts`. `ForeignKeyEditor.vue` and `UnnestEditor.vue` remain array-based consumers.

**Dependencies:** None on the expansion helper; implement after Area 1 because both touch `EntityFormDialog.vue`.

**Tasks:**

* [ ] `T3.1` **Change:** Preserve each supported field's loaded scalar or list shape during form conversion.
  * **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `yamlToFormData`, `buildEntityConfigFromFormData`, `buildDirtySnapshot`.
  * **Current → required:** Normalized chip arrays and singleton-reference serializers can rewrite unchanged input → keep a raw value and normalized comparison value per affected field, restore the raw value only when that field has no semantic edit, and serialize edited fields using the existing form rules.
  * **Implementation:** Cover `keys`, non-fixed `columns`, each FK's `local_keys`/`remote_keys`, `unnest.id_vars`/`value_vars`, `drop_duplicates`, and `drop_empty_rows`. Normalize scalar unnest and drop-list references for array-based editors without losing their raw form; keep boolean drop settings and Fixed Entity Columns behavior. Refresh raw values when valid YAML is applied or an entity is reloaded; invalid YAML must not replace them. Ensure an unrelated edit and child array emissions do not change untouched fields in Save payloads or YAML view. Keep dirty-state comparison consistent with the serialized result.
  * **Validation:** `V-4`–`V-7`; test scalar, one-item list, mixed list, and legacy `+` text without expanding them.
* [ ] `T3.2` **Test:** Exercise form and child-editor round trips.
  * **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts`.
  * **Current → required:** Current tests cover ordinary saves and fixed rows → add edit-dialog cases that change an unrelated field, then assert the exact saved `entity_data` shapes for the fields above. Assert YAML-form switching keeps an explicit one-item list, and a valid YAML shape edit is respected. Simulate FK child normalization and verify the parent saves the original scalar if the keys are unchanged.
  * **Implementation:** Include a scalar `keys` reference, a one-item `columns` reference list, scalar and list FK keys, scalar `unnest.id_vars`, mixed `unnest.value_vars`, scalar `drop_duplicates`, list `drop_empty_rows`, and a legacy expression such as `@value: entities.site.keys + ['other']`. Use an unrelated valid form edit to enable Save; compare exact raw values in the update request. Retain the existing fixed-entity regression cases.
  * **Validation:** `V-4`; assert unchanged raw values in update payloads and YAML output, with no new save error.

**Completion evidence:** Form tests show unchanged reference fields keep their input representation after editor normalization and an unrelated save.

## Acceptance-Criteria Coverage

| Phase criterion | Source | Tasks | Validation | Expected result |
| --- | --- | --- | --- | --- |
| `PH1-AC-1` | `P-AC-1` | `T1.1`, `T1.2` | `V-1` | Only the active project's completed cache is available. |
| `PH1-AC-2` | `P-AC-2` | `T2.1`, `T2.2` | `V-2`, `V-3` | Nested, ordered, duplicate-preserving output matches Core. |
| `PH1-AC-3` | `P-AC-3` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`, `V-2` | Missing or unsupported input yields no partial result. |
| `PH1-AC-4` | `P-AC-5` | `T3.1`, `T3.2` | `V-4` | Unchanged field shapes remain intact in YAML and save payloads. |

## Validation And Testing

Commands run from the stated directory. The baseline is from the planning checkout before implementation.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Entity cache ownership and races | From `frontend/`: `rtk proxy pnpm test:run src/stores/__tests__/entity.test.ts` | `PH1-AC-1`, `PH1-AC-3` | Ownership cases and existing store tests pass. | Pass: 34 existing tests. |
| `V-2` | Pure frontend expansion, positive and failure cases | From `frontend/`: `rtk proxy pnpm test:run src/utils/__tests__/valueReferenceColumns.test.ts` | `PH1-AC-2`, `PH1-AC-3` | Exact arrays or `null`; no partial output or mutation. | Not run: test file is **NEW**. |
| `V-3` | Core parity fixture | From repo root: `rtk uv run pytest tests/configuration/test_utility.py -q` | `PH1-AC-2` | New positive fixture and existing Core tests pass; runtime code is unchanged. | Pass: 8 existing tests. The proposed nested fixture was also checked directly with `ReferenceResolver` and returned `['sample_id', 'name', 'site_id', 'site_id']`. |
| `V-4` | Form, FK, and unnest regressions | From `frontend/`: `rtk proxy pnpm test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts src/components/entities/__tests__/UnnestEditor.test.ts` | `PH1-AC-4` | New shape cases and existing editor tests pass. | Pass: 35 existing tests. |
| `V-5` | Frontend type check | From `frontend/`: `rtk proxy pnpm exec vue-tsc --noEmit` | Changed TypeScript and Vue contracts | No new diagnostics. | Fail: existing `TS7006` at `src/composables/__tests__/useMonacoYamlIntelligence.test.ts:36` (`schema` has implicit `any`). Do not change that unrelated test in this phase. |
| `V-6` | Frontend lint on changed files | From `frontend/`: `rtk proxy pnpm exec eslint src/stores/entity.ts src/stores/__tests__/entity.test.ts src/utils/valueReferenceColumns.ts src/utils/__tests__/valueReferenceColumns.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts` | Phase 1 frontend changes | No lint errors. | Pass on the five existing targets; two **NEW** targets not run. |
| `V-7` | Formatting and Core test lint | From `frontend/`: `rtk proxy pnpm exec prettier --check src/stores/entity.ts src/stores/__tests__/entity.test.ts src/utils/valueReferenceColumns.ts src/utils/__tests__/valueReferenceColumns.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/ForeignKeyEditor.test.ts`. From repo root: `rtk uv run ruff check tests/configuration/test_utility.py` and `rtk uv run black --check tests/configuration/test_utility.py`. | Phase 1 changes | No formatting or Python lint errors. | Pass on the five existing frontend targets and Core test file; two **NEW** targets not run. |

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
| --- | --- | --- | --- |
| Owned entity cache | `frontend/src/stores/entity.ts` | `T1.1` | `V-1` passes. |
| Project-aware refresh call | `frontend/src/components/entities/EntityFormDialog.vue` | `T1.1`, `T3.1` | Cache and form tests pass. |
| Cache tests | `frontend/src/stores/__tests__/entity.test.ts` | `T1.2` | `V-1` covers switches and stale responses. |
| Expansion helper | `frontend/src/utils/valueReferenceColumns.ts` **NEW** | `T2.1` | `V-2` passes. |
| Expansion tests | `frontend/src/utils/__tests__/valueReferenceColumns.test.ts` **NEW** | `T2.2` | `V-2` covers supported and rejected trees. |
| Core parity test | `tests/configuration/test_utility.py` | `T2.2` | `V-3` passes. |
| Form round-trip tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `frontend/src/components/entities/__tests__/ForeignKeyEditor.test.ts` | `T3.2` | `V-4` checks exact representations. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Completed project cache | Not started | None | Establish the data source for Phase 2. |
| Area 2: Local expansion | Not started | Area 1 contract | Keep helper pure. |
| Area 3: Form representation | Not started | Area 1 edit to dialog | No preview UI in this phase. |

## Definition Of Done

* [ ] `PH1-AC-1`–`PH1-AC-4` have the task and validation results in the coverage table; `VM-1` is satisfied.
* [ ] All Area 1–3 tasks and listed deliverables are complete.
* [ ] `V-1`–`V-4`, `V-6`, and `V-7` pass; `V-5` has no diagnostics beyond the recorded baseline failure.
* [ ] Fixed Entity Columns, ordinary field suggestions, Save behavior, and Core runtime behavior retain their existing results.
* [ ] The Phase 2 handoff is the completed-cache check, expansion helper, and form representation rule; any deviation is documented.
* [ ] No unresolved question affects implementation, correctness, or validation.
* [ ] If implementation findings conflict with verified repository behavior in this plan, stop and report the difference before changing the design or scope.
