# Target Model Guided Entity Creation — Phase 3 Task Plan

## Phase Summary

- **Phase:** 3 — Requirements and Completion
- **Goal:** Show target requirements beside the draft and keep the picker accurate after save.
- **Readiness:** Validated. The phase plan marks Phase 3 ready, the Phase 1 options contract and Phase 2 create flow are present, and the repository has executable checks for the planned UI and validation work. No product decision remains open. This describes plan readiness; implementation is not complete.

Sources: [proposal](TARGET_MODEL_GUIDED_ENTITY_CREATION.md) and [phase plan](TARGET_MODEL_GUIDED_ENTITY_CREATION_PHASE_PLAN.md#phase-3-requirements-and-completion), Phase 3. `VM-3` is covered by `V-1` through `V-5`.

**Dependencies and constraints:** Use the Phase 1 project-scoped target facts and Phase 2 selection and save behavior. Keep target columns and links as read-only requirements; do not copy them into `columns`, `foreign_keys`, or `keys`. Use the normal entity-create action for writes, preserve the post-create Foreign Keys editor, and do not change candidate ordering. If implementation-time repository behavior conflicts with these verified findings, stop and report the evidence rather than changing the API contract or broadening scope.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-4`): Selecting an option adds no target facts to project `columns`, `foreign_keys`, or `keys`; only user-configured values are saved.
2. [x] `PH3-AC-2` (from `P-AC-8`): The form shows required non-generated columns and direct or bridged link paths without suggesting a direct FK for a `via` link. Conditional links are labeled Conditional, show their trigger, and explain when they are required.
3. [x] `PH3-AC-3` (from `P-AC-7`): Existing entities are absent from the options, and a newly saved entity disappears after the options refresh.
4. [x] `PH3-AC-4` (from `P-AC-6`): Viewing requirements makes no project write; existing validation reports remaining gaps for an incomplete saved entity.

## Repository Findings

**Repository basis:** Branch `target-model-guided-entity-creation`, commit `5fb18375`, inspected 2026-10-28. The worktree was dirty. The source proposal had uncommitted edits and was read as the current input; unrelated changes were left untouched. This Phase 3 task plan did not exist.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `frontend/src/api/projects.ts::TargetModelEntityOption`, `TargetModelRequiredLink` | The client has `required_columns` and link `path`, `missing_entities`, and `required_when_has_new_rows` fields, alongside role, description, target table, and public ID. | Render these returned facts as reference information; no API response change is needed. |
| `frontend/src/components/entities/EntityFormDialog.vue::loadTargetModelEntityOptions`, `handleSubmit` | Create mode loads options when opened. Selection is held separately from form data, and the existing create action serializes the form data. The form does not yet show selected target requirements. | Add a read-only requirements section and test that requirement fields do not enter the save payload. |
| `frontend/src/components/entities/EntityListCard.vue::handleEntitySaved` | After creation, the parent switches the dialog to edit mode. Re-entering create mode resets target state and requests options again. | Add a regression test that the next create session fetches current candidates and omits the entity just saved. |
| `backend/app/api/v1/endpoints/validation.py::validate_entity`, `validate_target_model` | The project already has read-authorized structural entity validation and target-model conformance validation routes. | Preserve both routes and verify an incomplete saved entity is reported by the existing conformance route. |
| `backend/tests/services/test_target_model_entity_options_service.py::test_returns_sorted_missing_entities_and_reference_requirements`; `backend/tests/validators/test_target_model_validator.py`; `tests/model/test_target_model_conformance.py` | Existing tests cover generated-column exclusion, direct and bridged links, missing entities, conditional-link triggers, and target-model gaps. | Reuse these contract and conformance checks; keep Phase 3 focused on presentation, refresh behavior, and post-save validation. |
| `backend/tests/api/v1/test_validation.py` | It tests structural validation, but no current API test calls `/projects/{name}/validate/target-model`. | Add a route-level regression case for the incomplete saved-entity workflow. |

Baseline checks passed on 2026-10-28:

- The focused frontend API and dialog suites passed: 74 tests.
- `vue-tsc --noEmit` passed.
- The target-model options service, structural validation API, and core conformance tests passed.
- The target-model validator suite passed: 23 tests.
- Targeted ESLint checks for the dialog and its test passed.

## Scope

**In scope**

- Show selected target role, description, target table, required columns, and link requirements beside the draft.
- Show direct links as target entities and `via` links as paths, marking path entities listed in `missing_entities`.
- Label conditional links, show the `required_when_has_new_rows` trigger, and explain that the link applies only when reconciliation selects one or more rows from that entity for insertion.
- Keep target requirements out of the entity form data and verify the normal create payload contains only user-configured mappings.
- Verify candidate options are refreshed when create mode is entered after a save.
- Add an API regression test for structural and target-model validation of an incomplete saved entity.

**Out of scope**

- Changes to the target-model options API, target-model schema, validation behavior, entity-create operation, full template generator, or command-line helper.
- Automatic source-column, key, FK, join, or dependency configuration.
- Changes to candidate ordering or prioritization.
- Enabling the Foreign Keys editor before the entity is created.

**Affected targets:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, and `backend/tests/api/v1/test_validation.py`. No new files are required.

## Work Breakdown

### Area 1: Show target requirements without changing project data

**Objective:** The selected target's requirements are clear beside the form and remain separate from saved entity fields.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Phase 1 target-options response and Phase 2 target selection, both present.

**Tasks**

- [x] `T1.1` **Add:** A read-only requirements section for the selected target entity.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`.
  - **Current → required:** The selected option supplies target facts, but the form does not display its requirements → show available role, description, and target table, required columns, and required links beside the draft.
  - **Implementation:** Render direct link paths as their target entity and `via` paths as the returned bridge-to-target sequence. Mark missing path entities using `missing_entities`. For conditional links, display **Conditional**, name the returned trigger entity, and explain when the link is required. Render only facts from the selected option.
  - **Constraints:** Do not write to the project while displaying requirements. Do not convert a link path into a project FK or copy target facts into `columns`, `foreign_keys`, or `keys`. Do not present conditional links as always required or predict reconciliation results.
  - **Validation:** `V-1`, `V-2`, `V-5`.
- [x] `T1.2` **Test:** Requirement presentation and save-payload separation.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** Existing tests cover target selection and save behavior, but not requirement display or contamination of saved mappings → cover required columns, a direct link, a bridged path with missing entities, and a conditional link with its trigger and explanation.
  - **Implementation:** Before saving, assert that viewing requirements calls neither create nor update. Save after configuring only the intended form values; assert target column names and link paths were not added to `columns`, `foreign_keys`, or `keys`, while user-configured values remain in the create payload.
  - **Constraints:** Use the existing Phase 1 response shape. Include only non-generated columns in the response fixture, consistent with the server contract.
  - **Validation:** `V-1`, `V-2`.

**Completion evidence:** The dialog displays direct and bridged requirements distinctly, explains conditional triggers, and the save test proves those facts do not populate project mappings.

### Area 2: Refresh candidates after creation

**Objective:** A new create session uses the current server candidate list and does not offer an entity saved in the previous session.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Phase 2 create and save flow, present.

**Tasks**

- [x] `T2.1` **Test:** Verify a fresh options request after a target entity is saved.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; update `frontend/src/components/entities/EntityFormDialog.vue` only if this lifecycle check exposes stale options.
  - **Current → required:** The component fetches options on create-mode entry, and the parent changes to edit mode after saving → prove that opening create mode again fetches the updated list.
  - **Implementation:** Return a target option on the first request, select and save it through the existing create action, then simulate the parent switching to edit mode and reopening create mode. Return a second response without the saved entity and assert the request occurs again and the saved name is not offered.
  - **Constraints:** Preserve server ordering and the existing create action. Do not add a separate candidate cache, endpoint, or prioritization rule.
  - **Validation:** `V-1`, `V-2`.

**Completion evidence:** The reopened create form displays the latest options response, which excludes the entity just saved.

### Area 3: Verify validation after an incomplete save

**Objective:** Existing structural and target-model validation remain available after the user saves an entity with unfinished source or target configuration.

**Affected code:** `backend/tests/api/v1/test_validation.py::TestEntityValidation`.

**Dependencies:** Existing entity-save behavior and validation routes; no new API behavior is required.

**Tasks**

- [x] `T3.1` **Test:** Validate a persisted entity with remaining target requirements.
  - **Target:** Add `TestEntityValidation::test_incomplete_target_entity_reports_remaining_gaps` to `backend/tests/api/v1/test_validation.py`.
  - **Current → required:** The test file covers structural entity validation, but does not call the target-model conformance route → verify both existing validation paths against a saved, structurally valid entity that lacks a required target column and required link.
  - **Implementation:** Create an authorized test project and configure an inline target model using the existing project test setup pattern. Persist an entity with valid project structure but without the required target column and FK. Call `POST /api/v1/projects/{name}/entities/{entity_name}/validate` and `POST /api/v1/projects/{name}/validate/target-model`. Assert both return their standard validation result; assert the conformance result reports `MISSING_REQUIRED_COLUMN` and `MISSING_REQUIRED_FOREIGN_KEY_TARGET` for the incomplete entity.
  - **Constraints:** Do not change validation rules or make target requirements part of entity creation. Keep the project's configured target model and entity data as the test inputs.
  - **Validation:** `V-3`, `V-4`.

**Completion evidence:** The saved entity can be checked by the existing routes, and target conformance reports its outstanding column and link requirements.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-4`) | `T1.1`, `T1.2` | `V-1` | Selection and requirement display do not write project data; target facts do not enter `columns`, `foreign_keys`, or `keys`, while user-configured fields are saved. |
| `PH3-AC-2` (`P-AC-8`) | `T1.1`, `T1.2` | `V-1`, `V-2` | Required columns, direct links, bridge paths, missing path entities, and conditional triggers are displayed without implying direct FKs for bridged links. |
| `PH3-AC-3` (`P-AC-7`) | `T2.1` | `V-1`, `V-2` | Re-entering create mode makes a fresh request and does not offer the entity saved in the previous session. |
| `PH3-AC-4` (`P-AC-6`) | `T1.2`, `T3.1` | `V-1`, `V-4` | Requirement display causes no write; after save, existing validation reports remaining target requirements. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline / final result |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Dialog and project API tests: `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `frontend/src/api/__tests__/projects.test.ts` | `cd frontend && rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts src/api/__tests__/projects.test.ts` | `PH3-AC-1`–`PH3-AC-4` | Tests cover requirements display, read-only selection, save payload, and refreshed candidates. | Baseline pass: 74 tests; final pass: 76 tests. |
| `V-2` | Target option response contract: `backend/tests/services/test_target_model_entity_options_service.py` | `rtk .venv/bin/pytest -q -p no:cacheprovider backend/tests/services/test_target_model_entity_options_service.py` | `PH3-AC-2`, `PH3-AC-3` | Generated required columns stay excluded; bridge paths, conditional triggers, and missing-entity filtering remain correct. | Baseline pass; final pass. |
| `V-3` | Target-model validator and core conformance: `backend/tests/validators/test_target_model_validator.py`, `tests/model/test_target_model_conformance.py` | `rtk .venv/bin/pytest -q -p no:cacheprovider backend/tests/validators/test_target_model_validator.py tests/model/test_target_model_conformance.py` | `PH3-AC-4` | Existing validators report missing required columns and links and continue to ignore required generated columns. | Baseline pass; final pass. |
| `V-4` | Validation API: `backend/tests/api/v1/test_validation.py`, including `TestEntityValidation::test_incomplete_target_entity_reports_remaining_gaps` | `rtk .venv/bin/pytest -q -p no:cacheprovider backend/tests/api/v1/test_validation.py` | `PH3-AC-4` | Structural and target-model validation routes return their standard results; the new case reports the incomplete entity's target gaps. | Existing route tests passed at baseline; final pass including the new regression case. |
| `V-5` | Frontend type check | `cd frontend && rtk pnpm exec vue-tsc --noEmit` | `PH3-AC-1`–`PH3-AC-3` | No TypeScript or Vue type errors. | Baseline pass; final pass. |
| `V-6` | Targeted frontend lint | `cd frontend && rtk pnpm exec eslint src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH3-AC-1`–`PH3-AC-3` | The changed Vue component and tests pass ESLint. | Baseline pass; final pass with no warnings. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Read-only requirements display | `frontend/src/components/entities/EntityFormDialog.vue` | `T1.1` | Selected target facts are visible and are not written into project mappings. |
| Dialog behavior and refresh tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T1.2`, `T2.1` | Tests cover target requirements, payload separation, and candidate refresh after save. |
| Validation regression test | `backend/tests/api/v1/test_validation.py::TestEntityValidation` | `T3.1` | A saved incomplete entity reports outstanding target column and FK requirements through the existing validation route. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Show target requirements without changing project data | Done | Phase 1 options contract; Phase 2 selection flow | `T1.1` and `T1.2` complete; `V-1`, `V-2`, `V-5`, and `V-6` passed. |
| Area 2: Refresh candidates after creation | Done | Phase 2 create and save flow | `T2.1` complete; `V-1` passed and refreshed options exclude the saved entity. |
| Area 3: Verify validation after an incomplete save | Done | Existing project and validation routes | `T3.1` complete; `V-3` and `V-4` passed, with both expected conformance gaps reported. |

## Definition Of Done

- [x] Every Phase 3 acceptance criterion has implementation and validation evidence.
- [x] Requirement details are display-only and do not populate `columns`, `foreign_keys`, or `keys`.
- [x] Direct links, `via` paths, missing path entities, and conditional triggers are rendered correctly.
- [x] A new create session fetches current candidates after a prior save.
- [x] Structural and target-model validation report the expected results for a saved incomplete entity.
- [x] Focused frontend tests, backend tests, type checking, and linting pass.
- [x] Existing manual creation, entity save behavior, and candidate ordering remain unchanged.
- [x] Any deviation or follow-up work is documented; no unresolved question changes implementation or validation.
