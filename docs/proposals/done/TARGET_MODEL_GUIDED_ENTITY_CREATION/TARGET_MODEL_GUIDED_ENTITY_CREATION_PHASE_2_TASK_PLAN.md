# Target Model Guided Entity Creation — Phase 2 Task Plan

## Phase Summary

- **Phase:** 2 — Guided Identity Draft
- **Goal:** Let a user select a target-model entity and start a draft without changing manual creation or the existing save flow.
- **Readiness:** Validated. The phase plan marks Phase 2 ready, the Phase 1 read operation and frontend create flow exist, and no product decision remains open.

Sources: [proposal](TARGET_MODEL_GUIDED_ENTITY_CREATION.md) and [phase plan](TARGET_MODEL_GUIDED_ENTITY_CREATION_PHASE_PLAN.md#phase-2-guided-identity-draft), Phase 2. The phase's `VM-2` milestone is covered by `V-1` through `V-3` below.

**Constraints and dependencies:** Consume only the project-scoped Phase 1 response. Keep manual creation usable when no model is configured or the request fails. Selection changes local form state only; save through the existing entity-create action. Require a deliberate source-type selection for every selected target entity, and allow only `fixed` or `sql` for a selected classifier. Do not enable the create-mode Foreign Keys editor or display target requirements in this phase.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-2`): Manual creation remains usable when the picker is absent or reports a configured-model error.
2. [x] `PH2-AC-2` (from `P-AC-3`): Selection fills the exact target name and declared `public_id`, locks the name, protects edited identity fields when replacing a selection, and clearing the picker restores name editing.
3. [x] `PH2-AC-3` (from `P-AC-5`): A selected classifier can be saved only with `fixed` or `sql`.
4. [x] `PH2-AC-4` (from `P-AC-6`): Selecting an option makes no project write; the existing save action persists the completed form.
5. [x] `PH2-AC-5` (from `P-AC-9`): Saving a selected target entity requires an explicitly selected Shape Shifter source type; the default `entity` value alone does not satisfy this requirement.

## Repository Findings

**Repository basis:** Branch `target-model-guided-entity-creation`, commit `4a4028ee`, inspected 2026-10-28. The working tree has uncommitted changes in the source proposal and `SHAPESHIFTER_PROJECT_AI_ADVISOR.md`; those files were read as-is and were not changed. The target Phase 2 task plan did not exist.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/models/project.py::TargetModelEntityOption`, `TargetModelEntityOptionsResponse`; `backend/app/api/v1/endpoints/projects.py` | Phase 1 defines the project response with `configured` and `entities`; each option includes `name`, nullable `public_id`, nullable role, and target facts. The project route is `GET /api/v1/projects/{name}/target-model-entities`. | Add a typed frontend API method for this exact route. Send only the project name; do not accept a target-model path from the browser. |
| `frontend/src/components/entities/EntityListCard.vue` | The Add Entity action opens `EntityFormDialog` in create mode and passes `projectName`. The dialog handles the existing create flow. | Keep the caller and parent save behavior unchanged unless implementation evidence shows a necessary integration change. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildDefaultFormData`, `handleSubmit` | Create mode defaults `type` to `entity`; `handleSubmit` validates the form and calls the existing `create` action. `public_id` is part of the current form data and create payload. | Track explicit type selection separately from the default value. Keep target selection out of the save payload except for the identity values the user sees and may edit. |
| `frontend/src/api/projects.ts::projectsApi`, `frontend/src/api/index.ts` | Project API methods use `apiRequest`; `projectsApi` is exported through the central `api` object. | Add the Phase 1 read method to this API module and consume it through the existing `api` export. |
| `frontend/src/api/__tests__/projects.test.ts` | The project API has focused Vitest coverage, including target-model file listing. | Add a request/response test for the new target-entity options method in this file. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | The component tests provide a `mountEntityFormDialog` helper and mock the API and composables. | Extend the existing mock and add create-mode tests for loading, identity selection, type requirements, fallback, and save timing. |

Baseline checks passed:

- The focused API and dialog tests passed: 2 files, 62 tests.
- `vue-tsc --noEmit` completed successfully.

## Scope

**In scope**

- Add frontend response types and a project API method for the Phase 1 operation.
- Load the options in create mode and provide a clear error while leaving manual creation usable.
- Add the clearable picker, identity prefill and lock, and confirmation when replacing edited identity values.
- Require an explicit source-type choice for a selected option and restrict selected classifiers to `fixed` or `sql`.
- Test API routing, create-mode behavior, and the existing save path.

**Out of scope**

- Backend changes; Phase 1 already provides the project read operation.
- Target requirement display, post-save candidate refresh, and conformance guidance; those belong to Phase 3.
- Automatic changes to project `columns`, `foreign_keys`, or `keys`.
- Enabling Foreign Keys editing in create mode or changing entity create/update operations.
- Candidate ordering or prioritization changes.

## Work Breakdown

### Area 1: Add a typed client for target entity options

**Objective:** The frontend can request and type the Phase 1 response.

**Affected code:** `frontend/src/api/projects.ts`, `frontend/src/api/__tests__/projects.test.ts`.

**Dependencies:** Phase 1 project route and response contract.

**Tasks**

- [x] `T1.1` **Add:** Response types and a project API method for target-model entity options.
  - **Target:** `frontend/src/api/projects.ts`.
  - **Current → required:** The project API lists target-model files but has no method for the missing entity options → expose the Phase 1 response through a typed GET method.
  - **Implementation:** Type `configured`, `entities`, and the option fields used by the response, including nullable role and `public_id`. Add a method that requests `/projects/${projectName}/target-model-entities` with no body or model path.
  - **Constraints:** Preserve existing project API methods and use `apiRequest`. Keep this as a read request.
  - **Validation:** `V-1`, `V-3`.
- [x] `T1.2` **Test:** Verify the target entity options request and response.
  - **Target:** `frontend/src/api/__tests__/projects.test.ts`.
  - **Current → required:** No test covers the new route → assert the exact GET URL and that a valid options response is returned without reshaping its fields.
  - **Implementation:** Include a response with a classifier role and declared `public_id`, plus the unconfigured `{ configured: false, entities: [] }` result. Confirm request failures remain rejected to the caller.
  - **Constraints:** Reuse the existing `apiRequest` mock and do not test backend model resolution here.
  - **Validation:** `V-1`.

**Completion evidence:** The typed API method requests the Phase 1 route and its tests cover configured and unconfigured responses.

### Area 2: Load options without blocking manual creation

**Objective:** Create mode offers the project’s missing target entities while keeping the existing manual form available.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Area 1.

**Tasks**

- [x] `T2.1` **Add:** Create-mode loading and visible fallback behavior for target options.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`.
  - **Current → required:** The form opens with no target-model context → load the options when the create dialog opens and show a clearable picker when configured options are available.
  - **Implementation:** Use the new project API method. Do not render a target choice when the model is unconfigured or there are no candidates. Show a clear picker error if the configured-model request fails, without disabling the form or changing its manual defaults.
  - **Constraints:** Do not load target options in edit mode, write project data while loading, or expose target file paths or parser details.
  - **Validation:** `V-2`, `V-3`.
- [x] `T2.2` **Test:** Verify manual creation with no model and after a picker error.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** The test mock does not provide target options → cover an unconfigured response and a rejected configured-model request.
  - **Implementation:** Assert that no picker is offered for the unconfigured or empty response; for a rejected request, assert that the error is visible and manual fields remain usable. Submit a valid manual draft in both fallback cases and assert the existing create action is called.
  - **Constraints:** Keep the existing default `entity` behavior for manual creation.
  - **Validation:** `V-2`.

**Completion evidence:** Manual create mode remains usable without a target model and after a failed options request.

### Area 3: Apply and protect selected identity values

**Objective:** Selecting a target starts a draft with its declared identity without silently replacing user edits or saving anything.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Area 2.

**Tasks**

- [x] `T3.1` **Implement:** Target selection, name locking, clearing, and replacement protection.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`.
  - **Current → required:** The form has editable name and `public_id` fields but no target selection state → selecting an option sets its exact name and declared `public_id`, and locks the name until the picker is cleared.
  - **Implementation:** Keep `public_id` editable; when the selected option has no declared `public_id`, leave it for the user to enter. Clearing the picker unlocks the name and retains entered form values. Before a selection would replace an edited name or `public_id`, ask for confirmation; cancellation must preserve the current selection and values.
  - **Constraints:** Update only the local draft. Do not call create/update APIs or populate `columns`, `foreign_keys`, or `keys` from target facts.
  - **Validation:** `V-2`.
- [x] `T3.2` **Test:** Verify identity prefill and selection changes.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** No target-selection tests exist → assert exact identity prefill, name lock, and clear behavior.
  - **Implementation:** Cover a target with a `public_id` and one without it; verify clearing unlocks the name and retains entered values. Verify that replacing edited identity values asks for confirmation, cancellation leaves the draft unchanged, and confirmation applies the new option. Assert selection alone does not call create or update.
  - **Constraints:** Use mocked Phase 1 responses; do not write to a project in component tests.
  - **Validation:** `V-2`.

**Completion evidence:** Tests show that target identity values are copied only into the local draft and that user edits are not silently replaced.

### Area 4: Require an explicit source type and preserve the save flow

**Objective:** Every selected target has an intentional source type, and the completed draft saves only through the existing create action.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Dependencies:** Area 3.

**Tasks**

- [x] `T4.1` **Implement:** Selected-target source-type validation and classifier choices.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`.
  - **Current → required:** The form defaults to `type: entity`, which does not prove that the user chose a source type → block saving a selected target until a source type is explicitly selected.
  - **Implementation:** Track an explicit type choice separately from the default value and show guidance when the selection is required. For a selected classifier, restrict available choices and allowed values to `fixed` and `sql`, and explain that choice. Clear target-specific validation when the picker is cleared; preserve the manual form's existing type behavior.
  - **Constraints:** Keep type-specific entity configuration and persistence in the existing form and create action. Do not enable the Foreign Keys tab in create mode.
  - **Validation:** `V-2`, `V-3`.
- [x] `T4.2` **Test:** Verify explicit type choice, classifier restrictions, and normal save timing.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** Existing tests do not cover the target-selection save guard → test that the default `entity` value alone blocks a selected target, and that an explicit supported choice permits submission.
  - **Implementation:** For a selected classifier, assert that only `fixed` and `sql` are available and accepted. Assert that selecting an option makes no write, then completing and saving the form calls the existing create action once with the draft name and configured entity data. Also verify that clearing the picker restores manual type behavior.
  - **Constraints:** Do not add a new save endpoint or save target reference/requirement fields as entity data.
  - **Validation:** `V-2`.

**Completion evidence:** Selected targets cannot bypass explicit source-type selection, and a valid draft is persisted only by the existing create action.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-2`) | `T1.1`, `T2.1`, `T2.2` | `V-1`, `V-2` | No-model and failed-request cases leave manual creation usable; failed requests show a picker error. |
| `PH2-AC-2` (`P-AC-3`) | `T3.1`, `T3.2` | `V-2` | The selected name and declared ID are applied, the name is locked, clearing restores editing, and replacement does not silently discard edits. |
| `PH2-AC-3` (`P-AC-5`) | `T4.1`, `T4.2` | `V-2` | A selected classifier accepts only an explicit `fixed` or `sql` choice. |
| `PH2-AC-4` (`P-AC-6`) | `T3.1`, `T3.2`, `T4.1`, `T4.2` | `V-2` | Selection causes no write; saving a completed draft calls the existing create action. |
| `PH2-AC-5` (`P-AC-9`) | `T4.1`, `T4.2` | `V-2` | The default `entity` value alone cannot save a selected target; an explicit type choice is required. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Project API contract: `frontend/src/api/__tests__/projects.test.ts` | `cd frontend && rtk pnpm exec vitest run src/api/__tests__/projects.test.ts` | `PH2-AC-1`, API request contract | Tests assert the exact GET route and configured/unconfigured response handling. | Baseline: Pass, 33 tests; post-implementation: Pass, 36 tests. |
| `V-2` | Create dialog behavior: `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `cd frontend && rtk pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH2-AC-1`–`PH2-AC-5` | Tests cover fallback, error display, selection, identity replacement, explicit type choice, classifier restrictions, and save timing. | Baseline: Pass, 29 tests; post-implementation: Pass, 38 tests. |
| `V-3` | Frontend type check | `cd frontend && rtk pnpm exec vue-tsc --noEmit` | Typed API contract and form changes | Type checking completes without errors. | Baseline: Pass; post-implementation: Pass, exit code 0. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed target-options API method | `frontend/src/api/projects.ts` | `T1.1` | Method and response types match the Phase 1 route contract. |
| Project API tests | `frontend/src/api/__tests__/projects.test.ts` | `T1.2` | Request URL and response cases pass. |
| Guided create form | `frontend/src/components/entities/EntityFormDialog.vue` | `T2.1`, `T3.1`, `T4.1` | Picker, identity handling, type requirements, and existing save flow work together. |
| Guided create form tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T2.2`, `T3.2`, `T4.2` | Required fallback, selection, type, and persistence cases pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Typed client | Done | Phase 1 route | `T1.1`–`T1.2` complete; `V-1` and `V-3` pass. |
| Area 2: Options and fallback | Done | Area 1 | `T2.1`–`T2.2` complete; manual creation works without options and after request failure. |
| Area 3: Identity draft | Done | Area 2 | `T3.1`–`T3.2` complete; identity selection remains local and protects edits. |
| Area 4: Type and save | Done | Area 3 | `T4.1`–`T4.2` complete; `V-2` confirms explicit type choice and existing create flow. |

## Definition Of Done

- [x] Every `PH2-AC-*` has implementation and validation evidence in the coverage table.
- [x] All four work areas and listed deliverables are complete.
- [x] `V-1`, `V-2`, and `V-3` pass.
- [x] Manual creation works without a configured model and after an options request error.
- [x] Selecting an option causes no project write and does not infer columns, keys, or foreign keys.
- [x] Existing entity creation and edit behavior remains unchanged outside the selected-target validation.
- [ ] Any deviation from the Phase 1 contract or this plan is documented; stop and report evidence if repository behavior conflicts with the plan.

## Risks And Open Questions

- The Phase 1 endpoint reports configured-model failures through an HTTP error. The form must show a clear picker error without exposing parser details or disabling manual creation.
- No unresolved product decision blocks implementation.
