# Direct Target-ID Foreign Key UX — Phase 5 Task Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)
Source phase plan: [DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md)

## Phase Summary

**Phase:** Phase 5 — Compatibility and regression verification

**Goal:** Prove that behavior shipped before the direct target-ID selector is unchanged, cover the one unverified selector behavior (a stored `public_id` entry appearing selected after reload), and align user documentation with the shipped editor and validation affordances.

**Readiness:** Validated. Every suite below was run on 2026-11-10 with a recorded baseline, the single new test extends existing fixtures and helpers, and no unresolved decision can change the work.

**Constraints and dependencies:**

- Verification only. No production code change in this phase. The only planned code change is one component test; the only planned document changes are two user-facing guides plus this plan's execution record.
- Depends on Phases 1–4 being present in the working tree, which is the current state: the direct-FK route, map preservation, selector, and validation navigation are implemented.
- Compare failure status, not exact suite counts, when another branch adds tests. The counts below are the baseline for this branch.
- Report a regression with the failing test and evidence instead of editing unrelated code. Fix only a failure whose cause is inside Phases 1–4.
- Do not regenerate `frontend/src/schemas/entitySchema.json`: no Pydantic entity model changed in Phases 1–4, and the existing schema test already pins the field.
- Documentation must describe only shipped behavior. Removal of stale or `system_id` entries stays YAML-only; the selector does not offer it.

**Phase criteria:** `PH5-AC-1` (source `P-AC-8`).

- [x] `PH5-AC-1` Existing YAML editing and schema completions, default `system_id` behavior, Core links, and change-request validation results are unchanged.

## Repository Findings

**Repository basis:** branch `direct-target-id-foreign-key-ux`, commit `2a17adf9`, planning date 2026-11-10. Uncommitted changes were present and considered: the Phase 1–4 implementation (`backend/app/*`, `backend/tests/*`, `frontend/src/*`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`) plus unrelated pending changes (`src/transforms/dsl.py`, advisor proposal documents, `graphify-out/`). None of the unrelated changes touch the Phase 5 targets.

| Evidence | Finding | Planning implication |
| -------- | ------- | -------------------- |
| `frontend/src/components/entities/EntityFormDialog.vue::selectedDirectTargetIds` | The getter returns map entries whose value is `'public_id'` and whose key is in `eligibleDirectTargets`; the setter ignores changes unless `directTargetIdsUiState === 'ready'` and never touches `foreign_keys` or `depends_on`. | A stored eligible `public_id` entry already appears selected after reload. One test is needed to pin it; no production change. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts::createLocationEntity`, `::directFkRelationships`, `::waitForDirectForeignKeys`, `::findSelectByLabel` | Helpers exist and are used by the six selector tests. `createLocationEntity` declares a project FK to `method`, and `directFkRelationships` includes `location_type`, `method`, and `weather_type` whose ID columns the entity does not produce. | Add one test with `{ location_type: 'public_id', method: 'system_id' }`: `location_type` is eligible and unconflicted, `method` is preserved and conflicted. No new mock or helper is required. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` selector tests | Cover resolved labels, `not_configured`, `unresolvable`, request failure, selection/clearing, `system_id` and stale entries, and the pending state. None asserts an eligible stored `public_id` entry is already selected on load. | That is the single coverage gap Phase 5 closes; it verifies Phase 2 + Phase 3 integration, not new behavior. |
| `docs/CONFIGURATION_GUIDE.md` § `foreign_key_value_sources` | Documents YAML semantics, eligibility, ingester checks, and the manifest key. It does not mention the **Direct target IDs** control or the column-settings validation action. | Add one short editor paragraph; do not restate the YAML rules. |
| `docs/USER_GUIDE.md` § `Entity Editor Tabs`, § `Foreign Keys` | The Basic row reads "Core settings"; the Foreign Keys section covers links only. | Add a short subsection describing direct target IDs, preserved entries, project-FK conflicts, and the column-settings action. |
| `tests/model/test_model.py::TestTableConfig.test_foreign_key_value_sources_do_not_create_project_links`, `::test_foreign_key_value_sources_default_to_empty_and_preserve_system_id` | Pin no Core link, no `depends_on` entry, empty default, and exact pass-through of an explicit `system_id`. | Primary Core evidence for `PH5-AC-1`. No new Core test. |
| `tests/specifications/test_project.py` (value-source cases) | Pin rejection of non-map and unsupported values plus the composite specification run. | YAML validation evidence for `PH5-AC-1`. |
| `tests/scripts/test_generate_schemas.py::test_entity_schema_describes_direct_foreign_key_value_sources`; `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | Pin the generated schema default, enum, description, and the editor schema registration. | Evidence that schema completions are unchanged; regeneration is unnecessary. |
| `backend/tests/services/test_project_ingester_service.py::test_saved_direct_fk_map_reaches_validation_and_ingestion_through_real_mapper_and_ingester`, `::test_saved_default_and_explicit_system_id_keep_the_core_link_and_config_shape` | Exercise validation and ingestion through the real mapper and ingester, including the `direct_target_id_foreign_keys` manifest and the absent-map case. | Change-request validation evidence for `PH5-AC-1` without a live database. |
| `backend/tests/ingesters/test_sead_change_request_target_projection.py::test_direct_foreign_key_keeps_the_target_id_without_a_parent_table`, `backend/tests/ingesters/test_sead_change_request_package_builder.py::test_direct_fk_is_not_added_to_the_local_mapping_list`, `backend/tests/ingesters/test_sead_change_request_sql_builder.py::test_direct_fk_value_and_manifest_metadata_are_preserved_for_all_strategies` | Pin projection, package, and SQL behavior for direct FKs. | Support the "packages as before" claim. |
| `backend/tests/data_providers/arbodat/test_validation.py` | Loads `tests/test_data/projects/arbodat/shapeshifter.yml`, which declares `foreign_key_value_sources: {data_type: public_id}` on `dataset`, and pins the Core specification, target-model conformance, and stable conformance issue families. | Direct evidence that a project configured only through YAML still validates the same way. |
| `backend/tests/services/test_validation_service.py::test_direct_fk_declaration_without_target_model_returns_specific_error`, `::test_direct_fk_declaration_with_missing_target_model_file_returns_specific_error` | Pin the project-validation errors for the declaration. | Validation-result evidence for `PH5-AC-1`. |
| `backend/tests/api/v1/test_target_model_direct_foreign_keys.py`, `backend/tests/api/v1/test_target_model_entity_options.py` | Pin the new read-only route and the unchanged picker route. | Included in the backend regression run; no edits. |
| `frontend/package.json::scripts.test:run` | `vitest run` is the full frontend suite. | Use it for the phase-level regression run. |

## Scope

**In scope**

- One new component test in `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
- Core, backend, ingester, and frontend regression runs with recorded outcomes.
- Editor guidance in `docs/CONFIGURATION_GUIDE.md` and `docs/USER_GUIDE.md`.
- The verification record in this plan's execution section and the pull request description.

**Out of scope**

- Production code, backend routes, services, models, Core, conformance, and the change-request ingester.
- Schema regeneration, dependency changes, and new test helpers or mocks.
- Fixing pre-existing failures outside this feature, including the documentation-inventory failure noted in repository memory when it is unrelated to this branch.
- Removing stale or `system_id` entries through the selector; that remains a YAML-only edit.

**Affected layers:** frontend component test, user-facing documentation, plan record. No API, backend, Core, schema, or build change.

## Work Breakdown

### Area 1: Pin selector state after reload

**Objective:** A saved entity whose map declares an eligible `public_id` entry opens with that target selected, and saving without edits changes nothing.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` (existing file; one **NEW** test).

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Add one reload-selection test beside the existing selector tests.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, after `keeps only eligible public_id entries selected and preserves the rest`.
  - **Current → required:** The suite proves `system_id` and stale entries are not selected, but never proves an eligible stored `public_id` entry is selected.
  - **Implementation:**
    1. `it('selects a stored public_id entry and preserves the rest after reload', async () => {...})`.
    2. Mock `mockState.getTargetModelDirectForeignKeys` with `{ state: 'resolved', relationships: directFkRelationships }` before mounting, matching the existing selector tests.
    3. Mount `mountEntityFormDialog({ mode: 'edit', entity: createLocationEntity({ location_type: 'public_id', method: 'system_id' }) })`, then `await flushPromises()` and `await waitForDirectForeignKeys(wrapper)`.
    4. Assert `findSelectByLabel(wrapper, 'Direct target IDs')` returns an enabled select whose `modelValue` equals `['location_type']`.
    5. Assert `wrapper.text()` contains `method` and `Uses system_id.` from the preserved-value-source block.
    6. Change `Public ID *` with `setTextFieldValue`, click the enabled Save button, and assert `mockState.update` was called with `('location', { entity_data: expect.objectContaining({ foreign_key_value_sources: { location_type: 'public_id', method: 'system_id' } }) })`.
    7. Assert that call's `entity_data.foreign_keys` equals `locationForeignKeys` and `entity_data.depends_on` equals `locationDependsOn`.
  - **Constraints:** Reuse the existing fixtures and helpers; add no mock, stub, or helper. Do not modify existing tests or the component. `method` is conflicted by `locationForeignKeys`, so it cannot become selected; `location_type` is not conflicted.
  - **Validation:** `V-1`, `V-6`, `V-7`.

**Completion evidence:** The new test fails if the selector drops stored `public_id` entries or if saving rewrites the map, and passes against the current component.

### Area 2: Re-run Python verification

**Objective:** Core, backend, and ingester suites report the same results as before this feature's UI work, and the YAML-only project still validates the same way.

**Affected code:** No file changes. Suites under `tests/` and `backend/tests/`.

**Dependencies:** None.

**Tasks:**

- [x] `T2.1` **Change:** Run the Core model, conformance, specification, and schema suites.
  - **Target:** `tests/model/test_model.py`, `tests/model/test_target_model_conformance.py`, `tests/specifications/test_project.py`, `tests/scripts/test_generate_schemas.py`.
  - **Current → required:** Baseline recorded today; re-run and compare.
  - **Implementation:** `.venv/bin/python -m pytest tests/model/test_model.py tests/model/test_target_model_conformance.py tests/specifications/test_project.py tests/scripts/test_generate_schemas.py -n 0 -o addopts="" -q`.
  - **Constraints:** Do not edit these tests to make them pass. `-o addopts=""` is required because the repository default `-qq` hides the summary line.
  - **Validation:** `V-2`.

- [x] `T2.2` **Change:** Run the backend service, validator, mapper, and API suites for this feature.
  - **Target:** `backend/tests/services/test_project_ingester_service.py`, `backend/tests/services/test_validation_service.py`, `backend/tests/validators/test_target_model_validator.py`, `backend/tests/api/v1/test_target_model_entity_options.py`, `backend/tests/services/test_target_model_entity_options_service.py`, `backend/tests/api/v1/test_target_model_direct_foreign_keys.py`, `backend/tests/mappers/test_project_mapper_nested_models.py`.
  - **Current → required:** Baseline recorded today; re-run and compare.
  - **Implementation:** `.venv/bin/python -m pytest backend/tests/services/test_project_ingester_service.py backend/tests/services/test_validation_service.py backend/tests/validators/test_target_model_validator.py backend/tests/api/v1/test_target_model_entity_options.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_direct_foreign_keys.py backend/tests/mappers/test_project_mapper_nested_models.py -n 0 -o addopts="" -q`.
  - **Constraints:** Do not add API fixtures or modify the picker tests.
  - **Validation:** `V-3`.

- [x] `T2.3` **Change:** Run the change-request ingester direct-FK suites and the real YAML project validation module.
  - **Target:** `backend/tests/ingesters/test_sead_change_request_target_projection.py`, `backend/tests/ingesters/test_sead_change_request_package_builder.py`, `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `backend/tests/ingesters/test_sead_change_request_contracts.py`, `backend/tests/data_providers/arbodat/test_validation.py`.
  - **Current → required:** Baseline recorded today; re-run and compare.
  - **Implementation:** `.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_contracts.py backend/tests/data_providers/arbodat/test_validation.py -n 0 -o addopts="" -q`. The arbodat module initializes a JVM and reads `data/test.env`; it passed in 5.2 s during planning.
  - **Constraints:** Marked integration tests that need PostgreSQL are excluded by path selection; do not enable them for this phase.
  - **Validation:** `V-4`, `V-5`.

**Completion evidence:** Each command reports no failures and the same counts as the recorded baseline.

### Area 3: Re-run frontend verification

**Objective:** Frontend suites and quality checks report the same results as before this phase, with only the new test added.

**Affected code:** No production file changes. Suites under `frontend/src`.

**Dependencies:** Area 1 for the new test.

**Tasks:**

- [x] `T3.1` **Change:** Run the focused frontend suites touched by Phases 2–4.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `frontend/src/components/entities/__tests__/EntityListCard.test.ts`, `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts`, `frontend/src/api/__tests__/projects.test.ts`, `frontend/src/views/__tests__/ProjectDetailView.test.ts`, `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`, `frontend/src/components/validation/__tests__/ValidationPanel.test.ts`.
  - **Current → required:** Baseline recorded today (7 files, 144 tests); re-run with the new test.
  - **Implementation:** `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/EntityListCard.test.ts src/composables/__tests__/useMonacoYamlIntelligence.test.ts src/api/__tests__/projects.test.ts src/views/__tests__/ProjectDetailView.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts`.
  - **Constraints:** Use file-scoped runs; `npm run test:run` belongs to `T3.2`.
  - **Validation:** `V-6`.

- [x] `T3.2` **Change:** Run the full frontend suite.
  - **Target:** `frontend/src` via `cd frontend && npx vitest run`.
  - **Current → required:** Baseline recorded today (68 files, 1054 tests); re-run with the new test.
  - **Implementation:** `cd frontend && npx vitest run`.
  - **Constraints:** Report failure status first and counts second; another branch can change the total legitimately.
  - **Validation:** `V-7`.

- [x] `T3.3` **Change:** Run frontend type, format, and lint checks on the touched test file.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** `vue-tsc --noEmit` reported no diagnostics today; Prettier and ESLint must accept the new test.
  - **Implementation:** `cd frontend && npx vue-tsc --noEmit` then `npx prettier --check src/components/entities/__tests__/EntityFormDialog.test.ts` and `npx eslint src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Constraints:** Do not reformat unrelated files.
  - **Validation:** `V-8`.

**Completion evidence:** The focused run reports 7 files with 145 tests, the full run reports 68 files with 1055 tests, and the type, format, and lint checks pass.

### Area 4: Align user documentation with shipped behavior

**Objective:** Readers can find the **Direct target IDs** control, understand preserved entries and project-FK conflicts, and know how a missing output column is reported.

**Affected code:** `docs/CONFIGURATION_GUIDE.md`, `docs/USER_GUIDE.md` (existing files).

**Dependencies:** None, but the text must match the shipped selector and validation action already in the working tree.

**Tasks:**

- [x] `T4.1` **Change:** Add the editor note to the `foreign_key_value_sources` section.
  - **Target:** `docs/CONFIGURATION_GUIDE.md` § `foreign_key_value_sources`, after the existing bullet list and before "The declaration is not a shared target-model setting".
  - **Current → required:** The section documents YAML only; the editor control and validation action are undocumented.
  - **Implementation:** Add three or four sentences or bullets: the entity editor Basic section exposes **Direct target IDs**, which writes `foreign_key_value_sources.<target>: public_id`; it offers every direct target-model FK the target model declares, whether or not the source produces the ID column; choices with an existing project `foreign_keys` link to the same target are disabled until that link is removed; `system_id` and stale entries are kept and shown as preserved, and removing them requires YAML editing; a missing output column appears as validation error `DIRECT_FK_OUTPUT_COLUMN_MISSING` with an **Open column settings** action.
  - **Constraints:** Do not restate eligibility or ingester rules already in the section. Follow `.github/instructions/writing-style.instructions.md` and use plain, concrete wording. Use the exact UI labels.
  - **Validation:** `V-9`.

- [x] `T4.2` **Change:** Add a short user-guide section for direct target IDs.
  - **Target:** `docs/USER_GUIDE.md`, after § `Foreign Keys`.
  - **Current → required:** The guide covers project Foreign Keys only; direct target IDs are unmentioned.
  - **Implementation:** Add `## Direct Target IDs` with two short paragraphs: when to use it (the source already holds an existing target ID for a direct target-model relation), where the control is (entity editor, Basic tab), that selecting adds a `public_id` value source and clearing removes only that entry, that a conflicting project Foreign Key must be removed first, that preserved entries are shown with an explanation, and that validation offers **Open column settings** when the output column is missing. Link to `CONFIGURATION_GUIDE.md` for field rules instead of repeating them.
  - **Constraints:** Keep it under roughly 150 words. Do not document selector-based removal of `system_id` or stale entries. Do not change the tabs table or other sections.
  - **Validation:** `V-9`.

**Completion evidence:** Both documents name the shipped control and action, match the component labels, and claim no behavior the selector does not provide.

### Area 5: Record the verification outcome

**Objective:** The phase closes with a recorded result set, explicit deviations, and no claim that unrun checks passed.

**Affected code:** This task plan (execution record) and the pull request description.

**Dependencies:** Areas 1–4.

**Tasks:**

- [x] `T5.1` **Change:** Record results and deviations.
  - **Target:** This file, a new `## Execution Evidence (2026-11-10)` section after `Validation And Testing`; and the pull request description.
  - **Current → required:** No record exists for Phase 5.
  - **Implementation:** Add one row per validation ID with Pass or Fail, the observed counts, and the command actually run. List every deviation from this plan, including any test that passed before the change and any suite whose count differs from the baseline. State explicitly when a check was not run and why.
  - **Constraints:** Do not mark `PH5-AC-1` complete until `V-1`–`V-9` are recorded. Follow `.github/instructions/github-workflow.instructions.md` when preparing the commit and pull request text.
  - **Validation:** `V-9`.

**Completion evidence:** The recorded table covers every validation ID and names each deviation or states that none occurred.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --------- | -------- | -------------- | ----------------- |
| `PH5-AC-1` | `T1.1`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2`, `T3.3`, `T4.1`, `T4.2`, `T5.1` | `V-1`–`V-9` | Core schema, specification, link, and dependency tests pass unchanged; the real YAML project keeps its conformance issue families; ingester validation and packaging pass; the full frontend suite passes; the new test proves a stored `public_id` entry stays selected; documentation matches the shipped controls. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| -- | ---------------- | ----------------- | ------ | --------------- | -------- |
| `V-1` | Reload-selection component test | `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH5-AC-1` (selector reflects stored entries) | 57 tests pass (56 baseline + 1 new) | Pass 2026-11-09: 56 passed before the new test. Pass 2026-11-10: 57 passed after it |
| `V-2` | Core model, conformance, specification, and schema | `.venv/bin/python -m pytest tests/model/test_model.py tests/model/test_target_model_conformance.py tests/specifications/test_project.py tests/scripts/test_generate_schemas.py -n 0 -o addopts="" -q` | `PH5-AC-1` (Core links, dependencies, defaults, schema) | No failures; 231 tests | Pass 2026-11-10: 231 passed in 1.10 s |
| `V-3` | Backend services, validators, mapper, and target-model API | `.venv/bin/python -m pytest backend/tests/services/test_project_ingester_service.py backend/tests/services/test_validation_service.py backend/tests/validators/test_target_model_validator.py backend/tests/api/v1/test_target_model_entity_options.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_direct_foreign_keys.py backend/tests/mappers/test_project_mapper_nested_models.py -n 0 -o addopts="" -q` | `PH5-AC-1` (validation results, picker unchanged) | No failures; 136 tests | Pass 2026-11-10: 136 passed in 1.46 s |
| `V-4` | Change-request ingester direct-FK suites | `.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_contracts.py -n 0 -o addopts="" -q` | `PH5-AC-1` (packaging behavior) | No failures; 87 tests | Pass 2026-11-10: 87 passed in 0.19 s |
| `V-5` | Real YAML-only project validation | `.venv/bin/python -m pytest backend/tests/data_providers/arbodat/test_validation.py -n 0 -o addopts="" -q` | `PH5-AC-1` (YAML-only authoring still validates) | No failures; 6 tests, including the stable conformance issue families | Pass 2026-11-10: 6 passed in 5.24 s |
| `V-6` | Focused frontend suites | `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/EntityListCard.test.ts src/composables/__tests__/useMonacoYamlIntelligence.test.ts src/api/__tests__/projects.test.ts src/views/__tests__/ProjectDetailView.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts` | `PH5-AC-1` (YAML intelligence, dialog, validation navigation) | No failures; 7 files, 145 tests | Pass 2026-11-10: 7 files, 144 tests before the new test; 7 files, 145 tests after it |
| `V-7` | Full frontend suite | `cd frontend && npx vitest run` | `PH5-AC-1` (no frontend regressions) | No failures; 68 files, 1055 tests | Pass 2026-11-10: 68 files, 1054 tests before the new test; 68 files, 1055 tests after it |
| `V-8` | Frontend types, formatting, lint | `cd frontend && npx vue-tsc --noEmit && npx prettier --check src/components/entities/__tests__/EntityFormDialog.test.ts && npx eslint src/components/entities/__tests__/EntityFormDialog.test.ts` | Test quality | No diagnostics and no findings | Pass 2026-11-10: `vue-tsc` exit 0 with no output, Prettier reported all files formatted, ESLint reported no issues |
| `V-9` | Documentation consistency | Manual check: read both edited sections against `frontend/src/components/entities/EntityFormDialog.vue` (labels, preserved-entry reasons) and `frontend/src/components/validation/ValidationMessageList.vue` (`Open column settings`, code `DIRECT_FK_OUTPUT_COLUMN_MISSING`); confirm no claim about selector-based removal of `system_id` or stale entries | `PH5-AC-1` (documentation synchronized) | Labels and behavior match the code; no unsupported claim | Pass 2026-11-10: verified `Direct target IDs`, `Preserved value sources`, `Open column settings`, and the `Uses system_id.` / `Not declared by the target model.` reasons in the components; no documented selector-based removal |

Negative and boundary cases covered by `V-1`: stored eligible `public_id` entry, stored `system_id` entry, conflicted target, and save without user map edits. `V-2` covers the absent-map default and explicit `system_id`; `V-5` covers a real project whose only direct-ID configuration is YAML.

### Execution Notes

- Run Python checks with `.venv/bin/python -m pytest`. In this environment `uv run pytest` collects no tests, and the default `addopts` (`-qq`) suppresses the summary line, so pass `-o addopts=""` to read counts.
- The graphify graph was not used for this phase: the plan is suite-based verification, and every target was confirmed by reading the current test and source files.
- `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` and `backend/tests/ingesters/test_sead_change_request_inline_staging.py` are `pytest.mark.integration` suites that need PostgreSQL. They are not part of `V-4`; note them as not run rather than as passing.
- If `backend/tests/data_providers/arbodat/test_validation.py` cannot start the JVM on another machine, record an environment blocker for `V-5` instead of a regression, and state that `V-3` and `V-4` carry the equivalent declaration-path evidence for that environment.

## Execution Evidence (2026-11-10)

All tasks `T1.1`–`T5.1` completed on branch `direct-target-id-foreign-key-ux` with Phases 1–4 uncommitted in the working tree.

| ID | Result | Command actually run | Observed evidence |
| -- | ------ | -------------------- | ----------------- |
| `V-1` | Pass | `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | 57 passed (56 baseline + 1 new) |
| `V-2` | Pass | `.venv/bin/python -m pytest tests/model/test_model.py tests/model/test_target_model_conformance.py tests/specifications/test_project.py tests/scripts/test_generate_schemas.py -n 0 -o addopts="" -q` | 231 passed in 1.10 s, unchanged from baseline |
| `V-3` | Pass | `.venv/bin/python -m pytest backend/tests/services/test_project_ingester_service.py backend/tests/services/test_validation_service.py backend/tests/validators/test_target_model_validator.py backend/tests/api/v1/test_target_model_entity_options.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_direct_foreign_keys.py backend/tests/mappers/test_project_mapper_nested_models.py -n 0 -o addopts="" -q` | 136 passed in 1.46 s, unchanged from baseline |
| `V-4` | Pass | `.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_contracts.py -n 0 -o addopts="" -q` | 87 passed in 0.19 s, unchanged from baseline |
| `V-5` | Pass | `.venv/bin/python -m pytest backend/tests/data_providers/arbodat/test_validation.py -n 0 -o addopts="" -q` | 6 passed in 5.20 s, including the stable conformance issue families |
| `V-6` | Pass | `cd frontend && npx vitest run <T3.1 seven paths>` | 7 files, 145 tests passed (144 baseline + 1 new) |
| `V-7` | Pass | `cd frontend && npx vitest run` | 68 files, 1055 tests passed (1054 baseline + 1 new) |
| `V-8` | Pass | `cd frontend && npx vue-tsc --noEmit`; `npx prettier --check src/components/entities/__tests__/EntityFormDialog.test.ts`; `npx eslint src/components/entities/__tests__/EntityFormDialog.test.ts` | `vue-tsc` exit 0 with no output; Prettier "All files formatted correctly"; ESLint "No issues found" |
| `V-9` | Pass | Manual comparison of both edited sections with `EntityFormDialog.vue` and `ValidationMessageList.vue` | Documented labels exist verbatim; no documented behavior that the selector lacks |

New-test negative control: with `selectedDirectTargetIds` temporarily changed to drop stored entries, the new test failed with `AssertionError: expected [] to deeply equal [ 'location_type' ]` (1 failed, 56 skipped). The component was restored immediately, and `git diff` contains no negative-control string, so the only component change remains the pre-existing Phase 2–4 work.

Checks not run, and why:

- `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` and `backend/tests/ingesters/test_sead_change_request_inline_staging.py` are `pytest.mark.integration` suites that need PostgreSQL. They are excluded by path selection in `V-4` and were not run.
- The full backend suite was not run. `T2.2` and `T2.3` are the suites that cover the declaration path, the picker, the new route, validation, and packaging; the remaining backend tests were outside this phase's named targets.

Deviations from the plan text, all inside the authorized scope:

- `T1.1`: the plan's step 4 used a lowercase-label lookup as a label assertion. The implemented test asserts the exact label through the existing `findSelectByLabel(wrapper, 'Direct target IDs')` helper plus `disabled` and `modelValue`, matching the neighbouring tests.
- `T4.1`, `T4.2`: the plan suggested three or four sentences. Both sections ended up as a short lead sentence plus bullets or paragraphs, and two facts were added because they are shipped and easy to misread: the control is disabled when no target model is configured, and the column action lives in the expanded validation issue.
- Baseline dates for `V-1`, `V-6`, and `V-7` were recorded on 2026-11-09 during earlier phase work and re-confirmed on 2026-11-10 before this phase's edit; the table now shows both.

Follow-up work: none identified for this feature. The committed change for this phase is one component test plus two documentation sections.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| ----------- | ------ | -------- | ------------------- |
| Reload-selection test | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` (**NEW** test) | `T1.1` | `V-1` passes |
| Core verification result | `docs/proposals/done/DIRECT_TARGET_ID_FOREIGN_KEY_UX/DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_5_TASK_PLAN.md` execution record | `T2.1` | `V-2` recorded |
| Backend verification result | Same execution record | `T2.2` | `V-3` recorded |
| Ingester and YAML-project verification result | Same execution record | `T2.3` | `V-4`, `V-5` recorded |
| Frontend verification result | Same execution record | `T3.1`, `T3.2`, `T3.3` | `V-6`, `V-7`, `V-8` recorded |
| Configuration guide note | `docs/CONFIGURATION_GUIDE.md` § `foreign_key_value_sources` | `T4.1` | `V-9` passes |
| User guide section | `docs/USER_GUIDE.md` § `Direct Target IDs` (**NEW** section) | `T4.2` | `V-9` passes |
| Deviation record | Execution record and pull request description | `T5.1` | Every validation ID recorded with Pass or Fail |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| ---- | ------ | ------------ | ----- |
| Area 1: Pin selector state after reload | Done | None | One test added; negative control confirmed it detects a dropped stored entry |
| Area 2: Re-run Python verification | Done | None | `V-2`–`V-5` pass with baseline counts |
| Area 3: Re-run frontend verification | Done | Area 1 | `V-6`–`V-8` pass; 1055 frontend tests |
| Area 4: Align user documentation | Done | None | `CONFIGURATION_GUIDE.md` and `USER_GUIDE.md` updated; `V-9` pass |
| Area 5: Record the verification outcome | Done | Areas 1–4 | Execution evidence recorded above |

## Definition Of Done

- [x] Every acceptance criterion has implementation and validation evidence: `PH5-AC-1` mapped to `T1.1`–`T5.1` and `V-1`–`V-9`.
- [x] All five work areas and deliverables are complete.
- [x] `V-1`–`V-8` pass with the recorded counts, and `V-9` confirms documentation matches the shipped labels and behavior.
- [x] Core links, `depends_on`, and the `system_id` default are confirmed unchanged by the named Core and ingester tests.
- [x] A stored eligible `public_id` entry appears selected after reload and survives a save unchanged.
- [x] The real YAML-only project still validates with the same conformance issue families.
- [x] Deviations, skipped checks, and follow-up work are recorded, including any integration suite not run.
- [x] No production code, schema, dependency, or unrelated test file is modified.

## Risks And Open Questions

- **Pass/fail suites cannot prove absence of change by themselves.** Mitigation: the named tests pin the specific contracts (schema enum and description, no link or dependency, default mode, manifest metadata, stable conformance issue families). If a reviewer wants stronger evidence, add a new assertion rather than lowering the claim in the plan.
- **Count drift from other branches.** Exact totals in `V-6` and `V-7` move when other branches add tests. Treat a changed total with zero failures as acceptable and record the observed number.
- **Environment-dependent YAML project check.** `backend/tests/data_providers/arbodat/test_validation.py` needs a working JVM and `data/test.env`. It passed during planning; if another environment fails during setup, record the blocker for `V-5` and rely on `V-3` and `V-4` for the declaration-path evidence.
- **Documentation may outrun the UI.** The selector does not remove `system_id` or stale entries and does not show a separate message when the entity is absent from the target model (that case renders the neutral empty state). Both guides must stay silent or explicit on those points to avoid promising behavior the editor lacks.
- **Unknown-entity state wording.** Phase 1 recorded that a resolved model without the named entity returns `resolved` with no relationships and the dialog renders the neutral empty state. If Phase 5 documentation is later expanded, describe that as "the target model declares no direct foreign key for this entity" and do not invent a fourth state.
