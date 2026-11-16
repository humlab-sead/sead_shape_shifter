# Direct Target-ID Foreign Key UX — Phase 2 Task Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)
Source phase plan: [DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md)

## Phase Summary

**Phase:** Phase 2 — Preserve the complete value-source map through the entity dialog

**Goal:** Make the full `foreign_key_value_sources` map survive YAML parsing, form state, YAML/form switching, saving, and reload without altering any entry.

**Readiness:** Validated. Every target below was verified in the current working tree, and no unresolved decision changes the implementation.

**Constraints and dependencies:**

- Frontend only. The backend `Entity` model, the API mapper, Core accessors, conformance, and the change-request ingester are read-only references and must not change.
- Preserve entries verbatim. Do not normalize `system_id` entries, drop stale or ineligible targets, reorder keys, or reinterpret values.
- Do not create, modify, or derive project `foreign_keys` links or `depends_on` values from the map.
- No new UI. The **Direct target IDs** selector, eligibility labelling, conflict disabling, and the Phase 1 metadata client belong to Phase 3.
- Every payload and YAML path in the dialog must keep producing the same output when the entity has no map, so the key is omitted for an empty map.
- Depends on nothing from Phase 1; this phase can merge independently.

**Phase criteria:** `PH2-AC-1`, `PH2-AC-2` (sources `P-AC-6`, `P-AC-8`).

- [x] `PH2-AC-1` A mixed map containing `public_id`, explicit `system_id`, and stale entries survives YAML→form→YAML, save, and reload with every entry unchanged.
- [x] `PH2-AC-2` Preserved entries create no project FK link or dependency, and default `system_id` behavior is unchanged.

## Repository Findings

**Repository basis:** branch `direct-target-id-foreign-key-ux`, commit `2a17adf9`, planning date 2026-11-09. Uncommitted changes were present and considered: the Phase 1 backend work (models, service, route, tests, authorization inventory) and proposal documents. None of them touch `frontend/`, and Phase 2 edits no file that Phase 1 touched.

| Evidence | Finding | Planning implication |
| -------- | ------- | -------------------- |
| `frontend/src/components/entities/EntityFormDialog.vue::FormData` | The dialog form model lists every persisted entity field except `foreign_key_value_sources`. | Add one field; all other entities elsewhere in the file stay unchanged. |
| `frontend/src/components/entities/EntityFormDialog.vue::formData` | The shared `ref<FormData>` initializer is the first of four form-literal sites. | Extend the initializer so create mode starts with an empty map. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity` | Saved-entity hydration reads `entity.entity_data` with explicit field names and never reads `foreign_key_value_sources`. | This is the save→form loss point for edit mode. |
| `frontend/src/components/entities/EntityFormDialog.vue::yamlToFormData` | YAML→form parsing also builds an explicit literal and omits the map. | This is the YAML→form loss point, including the YAML-tab→form switch path. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildDefaultFormData` | Create mode returns an explicit literal with no map. | Default must be an empty object so serialization stays clean. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData` | Single serialization point used by `handleSubmit`, `handleSubmitAndClose`, `refreshPreview`, `formDataToYaml`, and `buildDirtySnapshot`. | Adding the map here covers both save paths, the YAML tab, previews, and dirty tracking in one place. |
| `frontend/src/components/entities/EntityFormDialog.vue::formDataToYaml` | Wraps `buildEntityConfigFromFormData` and reorders only `name`, `type`, and `system_id`. | No separate YAML-generation change is needed. |
| `frontend/src/components/entities/EntityFormDialog.vue::captureRawFieldRepresentations` | Raw-field preservation covers only `keys`, `columns`, FK key lists, `unnest`, and drop fields, for `@value:` shape fidelity. | Do not extend this machinery. The map is carried as a copied record, which already preserves values exactly. |
| `backend/app/models/entity.py::Entity.foreign_key_value_sources` | Typed as `dict[str, Literal["system_id", "public_id"]]` with default `{}`, and returned inside `EntityResponse.entity_data`. | The dialog can copy the stored mapping directly; no new API type is needed. |
| `backend/app/services/project/entity_operations.py::update_entity_by_name` | Persists the submitted `entity_data` wholesale; only `public_id` is back-filled when absent. | Omitting the key on save deletes it. The dialog must always send a non-empty map when one was loaded. |
| `backend/app/api/v1/endpoints/entities.py::EntityUpdateRequest` / `::EntityCreateRequest` | `entity_data` is a free-form `dict[str, Any]`. | Adding the key to the payload needs no backend DTO change. |
| `backend/app/api/v1/endpoints/columns.py` and `backend/app/api/v1/endpoints/preview.py` | Column availability and preview accept free-form entity drafts/overrides and pass them to Core. | Including the map in `buildEntityConfigFromFormData` cannot break preview or column availability; Core already understands the key. |
| `frontend/src/views/ProjectDetailView.vue::handleContextMenuDuplicate`, `::handleSaveQuickEdit` | Duplicate spreads `sourceEntity.entity_data`; quick edit loads and saves whole YAML. | Both already preserve the map. Out of scope, no change needed. |
| `frontend/src/components/entities/EntityEditorOverlay.vue` | Referenced only by the generated `frontend/src/components.d.ts`; no import site. | Not a live edit path. Do not touch. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | Already stubs `YamlEditor`, mounts edit mode with `initialTab: 'yaml'`, and asserts `mockState.update` payloads, including a raw-shape preservation case at the same level of detail. | Extend this file; no new test file or new test helper is required. |
| `tests/model/test_model.py::TestTableConfig.test_foreign_key_value_sources_do_not_create_project_links`, `::test_foreign_key_value_sources_default_to_empty_and_preserve_system_id` | Core already pins that the map creates no link or dependency and that absence still means `system_id`. | Phase 2 adds no Core code; these tests are the regression evidence for `PH2-AC-2`. |

## Scope

**In scope**

- `FormData` field for the map plus one small normalization helper in `EntityFormDialog.vue`.
- Hydration in `buildFormDataFromEntity`, `buildDefaultFormData`, and `yamlToFormData`.
- Serialization in `buildEntityConfigFromFormData`.
- Component tests in `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Out of scope**

- Any selector, dropdown, checkbox, label, or badge in the dialog template.
- Phase 1 route consumption, eligibility rules, conflict disabling, and validation navigation.
- `frontend/src/api/entities.ts`, `frontend/src/api/projects.ts`, backend services and models, Core, and conformance.
- Changing `captureRawFieldRepresentations`, `getUnchangedRawChipField`, or the drop-field helpers.
- Documentation updates; the field is already documented in `docs/CONFIGURATION_GUIDE.md` and `frontend/src/schemas/entitySchema.json`.

**Affected layers:** frontend dialog component and its component tests. No API, backend, Core, schema, or documentation changes.

## Work Breakdown

### Area 1: Carry the map in form state

**Objective:** The dialog holds every entry of the entity's `foreign_key_value_sources` map, in source order, for both create and edit modes.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue` (existing file; `normalizeForeignKeyValueSourcesForForm` is **NEW**).

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Add the form field and the copy helper.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::FormData`, next to `foreign_keys`; `::normalizeForeignKeyValueSourcesForForm`, next to `normalizeForeignKeysForForm`; `::formData` initializer.
  - **Current → required:** `FormData` has no value-source field and the ref initializer has no default. Add both so every literal construction carries the map.
  - **Implementation:**
    - Declare `foreign_key_value_sources: Record<string, unknown>` on `FormData` with a comment stating that values are carried verbatim and that eligibility is not interpreted here.
    - Add `function normalizeForeignKeyValueSourcesForForm(value: unknown): Record<string, unknown>`: return `{}` unless `value` is a non-array object; otherwise return `{ ...(value as Record<string, unknown>) }` so key order and every string value survive. Do not filter, rename, sort, or coerce entries.
    - Initialise `foreign_key_value_sources: {}` in the `formData` ref literal.
  - **Constraints:** No template change. No import changes. Do not touch the raw-representation types or helpers.
  - **Validation:** `V-1`, `V-4`, `V-5`.

- [x] `T1.2` **Change:** Hydrate the map from a saved entity and default it for create mode.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`; `::buildDefaultFormData`.
  - **Current → required:** Both functions build explicit literals without the key, so edit mode drops it immediately on open and create mode never has it.
  - **Implementation:**
    - In `buildFormDataFromEntity`, set `foreign_key_value_sources: normalizeForeignKeyValueSourcesForForm(entity.entity_data.foreign_key_value_sources)` beside `foreign_keys`.
    - In `buildDefaultFormData`, set `foreign_key_value_sources: {}`.
  - **Constraints:** Leave every other hydrated field unchanged. Do not derive map entries from `entity.entity_data.foreign_keys`, and do not add `depends_on` entries.
  - **Validation:** `V-1`, `V-4`.

- [x] `T1.3` **Change:** Parse the map from YAML edits.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::yamlToFormData`.
  - **Current → required:** The YAML→form literal omits the key, so switching from the YAML tab back to the form silently discards it.
  - **Implementation:** Set `foreign_key_value_sources: normalizeForeignKeyValueSourcesForForm(data.foreign_key_value_sources)` in the `formData.value = {...}` literal, beside `foreign_keys`.
  - **Constraints:** Preserve the existing early return on invalid YAML, which leaves the previous form state intact. Do not move or restructure the `suppressFixedSchemaRemap` block.
  - **Validation:** `V-1`, `V-4`.

**Completion evidence:** After opening an entity that declares a mixed map and after parsing equivalent YAML, the component's form state contains every entry unchanged.

### Area 2: Emit the map from the single serialization point

**Objective:** Every payload and YAML rendering produced by the dialog contains the map exactly as held, and omits the key when the map is empty.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`.

**Dependencies:** Area 1.

**Tasks:**

- [x] `T2.1` **Change:** Include the map in the serialized entity configuration.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`, in the block that emits `foreign_keys` and `depends_on`.
  - **Current → required:** The serializer lists explicit fields and never emits `foreign_key_value_sources`, so `update_entity_by_name` replaces the stored entity without it and the stored declaration is lost.
  - **Implementation:**
    - After the `foreign_keys` block and before `depends_on`, emit `entityData.foreign_key_value_sources = { ...formData.value.foreign_key_value_sources }` only when `Object.keys(formData.value.foreign_key_value_sources).length > 0`.
    - Rely on the existing callers for coverage: `handleSubmit` and `handleSubmitAndClose` (save), `formDataToYaml` (YAML tab), `refreshPreview` (preview body), and `buildDirtySnapshot` (dirty tracking and Save enablement).
    - Do not add a separate branch to `formDataToYaml`.
  - **Constraints:** Emit a shallow copy so later form mutations cannot alter an already-built payload. Keep insertion order. Do not emit the key for entities saved without it, so existing YAML output stays byte-identical. Do not add or reorder any other serialized field.
  - **Validation:** `V-1`, `V-2`, `V-3`, `V-4`.

**Completion evidence:** Saving an untouched entity that declares the map produces a payload with an identical map, no new `foreign_keys` or `depends_on` entries, and an unchanged YAML tab rendering; an entity without the map serializes exactly as before.

### Area 3: Prove preservation and absence of side effects

**Objective:** Component tests lock the round-trip, the dirty-state behavior, and the absence of link and dependency changes.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` (existing file).

**Dependencies:** Areas 1 and 2.

**Tasks:**

- [x] `T3.1` **Change:** Add three component tests covering the mixed map, the invalid-YAML path, and the no-map case.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, next to `preserves unchanged reference field shapes through form edits and invalid YAML`.
  - **Current → required:** No test covers the value-source map, so a future serialization edit could drop it silently.
  - **Implementation:**
    1. Shared fixture: `const mixedValueSources = { location_type: 'public_id', method: 'system_id', stale_target: 'public_id' }`, used with an entity named `location` (`public_id: 'location_id'`) that also declares one `foreign_keys` entry and one `depends_on` entry.
    2. `it('round-trips a mixed foreign_key_value_sources map through YAML output, save, and reload')`:
       - Mount edit mode with the fixture entity, `await flushPromises()`, `await nextTick()`.
       - Parse `wrapper.findComponent({ name: 'YamlEditor' }).props('modelValue')` with the file's existing `loadYaml` import and assert `foreign_key_value_sources` deep-equals `mixedValueSources`.
       - Change `Public ID *` with `setTextFieldValue`, because edit-mode Save stays disabled until something else is pending. Then assert the Save button is enabled and click it.
       - Assert `mockState.update` was called with `('location', { entity_data: expect.objectContaining({ foreign_key_value_sources: mixedValueSources }) })`.
       - Assert that same call's `entity_data.foreign_keys` and `entity_data.depends_on` equal the fixture values, proving no link or dependency was added.
       - Capture the saved `entity_data` from `mockState.update.mock.calls.at(-1)`, mount a fresh wrapper with `createEntity('location', savedEntityData)`, and assert its YAML output again deep-equals `mixedValueSources` to cover reload.
    3. `it('keeps a YAML-authored value-source map when the YAML tab is invalid')`:
       - Mount edit mode with the fixture entity and `initialTab: 'yaml'`.
       - Emit a YAML document whose only change is an added `stale_target` entry via `update:modelValue`, `change`, and `validate` with `true`, mirroring the existing YAML-shape test.
       - Assert the Save button is enabled, proving a map-only change counts as a pending change.
       - Emit `'name: [broken'` through `update:modelValue`, `change`, and `validate` with `false`, then change `Public ID *`.
       - Save and assert the payload map contains `location_type`, `method`, and `stale_target` unchanged.
    4. `it('omits foreign_key_value_sources from payloads when the entity has none')`:
       - Mount create mode, set Entity Name and Public ID, save, and assert `mockState.create` was called with `entity_data` that does not have a `foreign_key_value_sources` key using `expect(entity_data).not.toHaveProperty('foreign_key_value_sources')`.
       - Mount edit mode with `sourceEntities[0]`, change `Public ID *`, save, and assert the same absence plus `entity_data` without `foreign_keys`.
  - **Constraints:** Reuse `mountEntityFormDialog`, `createEntity`, `setTextFieldValue`, `loadYaml`, and `mockState`; do not add new mocks, helper files, or stubs. Do not modify existing tests. Use `expect.objectContaining` for payload assertions and the explicit `not.toHaveProperty` assertion for the absent case.
  - **Validation:** `V-1`.

**Completion evidence:** The three tests fail against the pre-change component and pass after Areas 1 and 2, and the existing 44 dialog tests still pass.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --------- | -------- | -------------- | ----------------- |
| `PH2-AC-1` | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T3.1` | `V-1`, `V-2` | A mixed map of `public_id`, `system_id`, and stale entries appears unchanged in the YAML tab, in the save payload, and again after remounting from the saved payload. |
| `PH2-AC-2` | `T2.1`, `T3.1` | `V-1`, `V-2`, `V-3` | The save payload keeps `foreign_keys` and `depends_on` equal to the fixture; Core tests still report no link, no dependency, and `system_id` as the default when the map is absent. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| -- | ---------------- | ----------------- | ------ | --------------- | -------- |
| `V-1` | Dialog component tests | `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH2-AC-1`, `PH2-AC-2` | Three new tests pass; all 44 existing tests still pass | Pass 2026-11-09: 47 passed (3 new + 44 existing) |
| `V-2` | Core map semantics and mapper round-trip | `.venv/bin/python -m pytest tests/model/test_model.py backend/tests/mappers/test_project_mapper_nested_models.py -n 0 -q -k foreign_key_value_sources` | `PH2-AC-1`, `PH2-AC-2` | No project link, no dependency, `system_id` default retained, mapper round-trip intact | Pass 2026-11-09: 4 passed (2 per file) |
| `V-3` | Core conformance regression | `.venv/bin/python -m pytest tests/model/test_target_model_conformance.py -n 0 -q` | `PH2-AC-2` | 52 tests pass, no new issues | Pass 2026-11-09: 52 passed |
| `V-4` | Frontend type check | `cd frontend && npx vue-tsc --noEmit` | Implementation correctness | No errors | Pass 2026-11-09: no diagnostics (re-verified after implementation) |
| `V-5` | Formatting and lint | `cd frontend && npx prettier --check src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts && npx eslint src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts` | Implementation quality | Both pass with no findings | Pass 2026-11-09: prettier clean, ESLint clean (re-verified after implementation) |

Boundary and negative cases covered by `V-1`: map absent, map with explicit `system_id`, map with a stale target, YAML-tab edit, invalid YAML after a form edit, and reload from a saved payload.

### Execution Notes

- Run `npx vitest run <file>` for the focused check; `npm run test:run` runs the whole frontend suite and is unnecessary for this phase.
- `.venv/bin/python -m pytest` is used instead of `uv run pytest` because `uv run pytest` collects no tests in this environment.
- No baseline check is recorded for the full frontend suite; `V-1` is the suite that covers every changed line.

### Execution Evidence (2026-11-09)

- Implemented `frontend/src/components/entities/EntityFormDialog.vue`: `FormData.foreign_key_value_sources`, `normalizeForeignKeyValueSourcesForForm`, the `formData` initializer, `buildFormDataFromEntity`, `buildDefaultFormData`, `yamlToFormData`, and the emission block in `buildEntityConfigFromFormData` (20 added lines, no template change).
- Added three tests to `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` with the shared `mixedValueSources`, `locationForeignKeys`, `locationDependsOn`, and `createLocationEntity` fixtures.
- `V-1`: 47 passed after implementation.
- Negative control: with `EntityFormDialog.vue` reverted to the pre-change version, `round-trips a mixed foreign_key_value_sources map through YAML output, save, and reload` and `keeps a YAML-authored value-source map when the YAML tab is invalid` failed (2 failed, 45 passed). The component change is what makes them pass.
- Deviation from the planned completion evidence: `omits foreign_key_value_sources from payloads when the entity has none` passes before and after the change. Pre-change behavior already omitted the key, so this test is a forward guard against emitting an empty map rather than a failing-first test. No plan content was changed to accommodate this.
- `V-2`: 4 passed. `V-3`: 52 passed. `V-4`: no diagnostics. `V-5`: prettier and ESLint clean.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| ----------- | ------ | -------- | ------------------- |
| Form field and copy helper | `frontend/src/components/entities/EntityFormDialog.vue::FormData`, `::normalizeForeignKeyValueSourcesForForm`, `::formData` | `T1.1` | Every form literal carries the field |
| Edit-mode hydration | `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity` | `T1.2` | Mixed map appears in form state after open |
| Create-mode default | `frontend/src/components/entities/EntityFormDialog.vue::buildDefaultFormData` | `T1.2` | Create payload omits the key |
| YAML parsing | `frontend/src/components/entities/EntityFormDialog.vue::yamlToFormData` | `T1.3` | YAML-authored map survives the YAML tab |
| Serialization | `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData` | `T2.1` | Save payload and YAML tab output contain the unchanged map |
| Component tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T3.1` | `V-1` passes |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| ---- | ------ | ------------ | ----- |
| Area 1: Carry the map in form state | Done | None | Field, `normalizeForeignKeyValueSourcesForForm`, and all three form literals updated |
| Area 2: Emit the map from the serializer | Done | Area 1 | Emitted only when the map is non-empty, in `buildEntityConfigFromFormData` |
| Area 3: Prove preservation and absence of side effects | Done | Areas 1 and 2 | Three tests added beside the existing raw-shape test |

## Definition Of Done

- [x] Every acceptance criterion has implementation and validation evidence recorded under `V-1`–`V-5`.
- [x] All three work areas and their deliverables are complete.
- [x] `V-1` passes with the three new tests and all 44 pre-existing dialog tests.
- [x] `V-2`–`V-5` pass with no new findings.
- [x] A mixed map of `public_id`, `system_id`, and stale entries round-trips unchanged through YAML, save, and reload.
- [x] Saving an entity that has no map produces a payload without the key and no other payload change.
- [x] No template, API client, backend, Core, schema, or documentation file is modified.
- [x] Deviations and follow-up work for Phase 3 are documented.

## Risks And Open Questions

Decided normalizations, applied by the tasks above:

- **Empty map is not written.** An entity whose YAML explicitly declares `foreign_key_value_sources: {}` is saved without the key. Omission loses no declaration, keeps every entity that does not use the feature byte-identical, and matches the backend default. `PH2-AC-1` covers entries, not an empty container.
- **Invalid field shapes are not repaired.** A non-mapping value (`foreign_key_value_sources: public_id`) normalizes to `{}`, and a mapping with non-string values is copied verbatim. The backend contract cannot represent either shape. Preserving the dialog's readability and letting validation report the original problem is preferred over blocking the editor.

Residual risks, no decision required before implementation:

- **Phase 3 reads this field.** Phase 3 interprets entries (`'public_id'` means selected, `'system_id'` means preserved but not selected). Storing `Record<string, unknown>` keeps preservation lossless here, so Phase 3 compares against the string and narrows the type where needed. A narrower type belongs in Phase 3, not here.
- **Dirty-state coupling.** `buildDirtySnapshot` consumes the serializer, so adding the map also makes a map-only change count as a pending change. That is required for saving, but a future change that removes the map from the serializer would silently disable saving such edits. The `T3.1` assertions on the Save button and on the payload guard this.
