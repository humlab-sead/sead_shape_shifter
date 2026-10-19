# Expose Project-Only Change Request Routes And Operator Client — Phase 5 Task Plan

## Phase Summary

**Goal:** Let an authorized operator validate and generate a SEAD Change Request from an open saved project without supplying a source workbook path.

**Readiness: Validated.** [Phase 5 of the phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md#phase-5-expose-project-only-routes-and-switch-the-operator-client) is marked ready. The completed [Phase 4 helper](./IN_MEMORY_INGESTER_HANDOFF_PHASE_4_TASK_PLAN.md), strict project request model, authorization dependencies, and Dispatch form were verified in the repository. The checks below can be run without a live SIMS or target database.

**Sources and constraints:** [Source proposal](./IN_MEMORY_INGESTER_HANDOFF.md); phase criteria `PH5-AC-1`–`PH5-AC-4`; milestones `VM-5.1`–`VM-5.3`. Phase 4's `ProjectIngesterService` remains responsible for direct-call authorization, mandatory project specification and ingester data validation, trusted settings, no-write normalization, and response mapping. Both new routes require `project:execute` and the interim `application:run_ingesters` action. The [companion proposal](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) owns exclusive per-run output, read-only target-database access, removal of this application action from the project-only path, and persistent `run_id` reuse by the client.

**Acceptance criteria**

1. `PH5-AC-1` (from `P-AC-8`): Both project-only routes require an authenticated project executor and the interim application action, reject source paths and arbitrary config, and pass the authorized project to the helper.
2. `PH5-AC-2` (from `P-AC-10`): The operator client sends only named project and submission fields to the project-only routes; file-only ingesters continue using the shared file routes.
3. `PH5-AC-3` (from `P-AC-12`): Route calls and direct helper calls retain the project-resource guard and reject invalid authorization before work.
4. `PH5-AC-4` (from `P-AC-13`): Both routes report project-specification failures in the existing response models before normalization or ingester work; failed ingester data validation blocks bundle writing.

## Repository Findings

**Repository basis:** Branch `in-memory-ingester-handoff`, commit `51fa3c425de990d5dad8afb627bb10af90c0850c`, planning date 2026-10-19. The working tree was clean when this document was drafted. The Phase 4 files were initially uncommitted during inspection, then committed at this revision; the focused baselines passed against those same files. The Graphify query surfaced the route and model files but not the then-untracked Phase 4 helper; source and tests established its current interface.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService.validate_project_tables`, `ingest_project_tables`, `_guard_project_call`; `backend/app/models/ingester.py::ProjectIngesterRequest`, `ProjectSubmissionOptions` | The helper accepts a typed request and `AuthorizedResource`. It checks `EXECUTE`, active `PROJECT`, exact locator, and `RUN_INGESTERS` before loading; both operations return the existing response types. The request and nested options use `extra="forbid"`. | Routes should supply the real authorized resource and the strict model, call the fixed `sead_change_request` key, and preserve helper responses and denials. Do not add another caller-controlled config path. |
| `backend/app/authorization/dependencies.py::require_project`, `require_application_action`; `backend/app/authorization/policy.py::PROJECT_ROLE_ACTIONS`, `DEPLOYMENT_ROLE_ACTIONS` | `require_project(Action.EXECUTE, body_locator=True)` reads a top-level body locator and conceals missing or unauthorized resources with 404; the application dependency rejects a principal without `RUN_INGESTERS` with 403. Project executor and application operator are separate grants. | Attach both dependencies to each route. A query/body locator mismatch must still fail the helper's exact-match guard before project loading. |
| `backend/app/api/v1/endpoints/ingesters.py`; `backend/app/api/v1/api.py`; `backend/tests/api/test_ingesters.py` | The shared `/{key}/validate` and `/{key}/ingest` routes use file request models, keep the application action, and reject retired Change Request file input. `ingesters.router` is already registered under `/ingesters`. | Add two fixed project-only paths to the existing router. No router registration change is needed. Preserve shared file routes and their tests. |
| `backend/tests/conftest.py::authorized_client`; `backend/tests/api/v1/test_data_source_file_authorization.py`; `backend/tests/services/test_project_ingester_service.py` | Protected route tests use an async ASGI client and an isolated authorization store. The direct helper tests already cover bad resources, application denial, project errors, warning-only projects, and failed ingester data validation. Project resources in route tests must be created through `POST /api/v1/projects`. | Add route tests with real authorization dependencies and a replaceable helper dependency; retain the direct helper suite as a regression check. Stub normalization, SIMS, and database work. |
| `frontend/src/api/ingester.ts`; `frontend/src/types/ingester.ts`; `frontend/src/stores/ingester.ts` | The client and Pinia store expose only file-request `validate` and `ingest` methods. The file types require `source` and permit arbitrary `config`. | Add separate typed project requests and API/store methods. Keep file method signatures and state/error handling for other ingesters. |
| `frontend/src/components/ingester/IngesterForm.vue`; `frontend/src/views/IngesterView.vue`; `frontend/src/views/ProjectDetailView.vue` | Change Request buttons are disabled, a workbook path remains required, and its builders include `source`, `config`, and caller `data_provider_code`. The project Dispatch tab passes `projectName`; the top-level Ingestion view excludes Change Request. The form also shows project data-source and ignore-column controls, though the helper chooses backend settings. | Enable Change Request only for the loaded route project, build the allowlisted request, hide file-only controls, and keep ordinary ingesters on file routes. Keep the top-level exclusion. |
| `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`; `frontend/src/views/__tests__/IngesterView.test.ts`; `docs/USER_GUIDE.md` | Component tests cover the disabled state and ordinary file ingesters. The guide says Dispatch requires prior Execute output, which is incorrect for the new Change Request path. | Replace the retired-state assertions with saved-project request checks, preserve file-route regression tests, and update the user workflow description. |

## Scope

**In scope:** Two fixed project-only FastAPI routes, dependency injection for the existing helper, route authorization and response tests, separate frontend request types and API/store methods, the saved-project Dispatch form switch, focused client and component tests, and the relevant user-guide workflow.

**Out of scope:** Changes to `ProjectIngesterService`, `ProjectIngesterRequest`, Core normalization, table ingester methods, shared file request/response schemas, other ingesters' file routes, Excel dispatch, or the companion proposal's output, database, permission, and `run_id` rules. Project-only ingestion still uses the Phase 4 managed output root and interim application gate.

## Work Breakdown

### Area 1: Publish guarded project-only routes

**Objective:** Both fixed routes authorize the saved project and interim application action, call the existing helper, and return its current response shapes.

**Affected code:** `backend/app/api/v1/endpoints/ingesters.py`; `backend/app/models/ingester.py::ProjectIngesterRequest` and `backend/app/services/project_ingester_service.py::ProjectIngesterService` (reuse only); `backend/tests/api/test_project_ingester_routes.py` (**NEW**).

**Dependencies:** Phase 4 helper and strict request model are complete.

**Tasks:**

* [x] `T5.1` **Add project-only route handlers:** Publish `POST /api/v1/ingesters/sead_change_request/from-project/validate` and `/ingest` on the existing ingester router.
  * **Target:** `backend/app/api/v1/endpoints/ingesters.py::router` and `get_project_ingester_service` (**NEW** function in the existing file).
  * **Current → required:** The existing Change Request file routes reject requests and no project-only route calls the Phase 4 helper. The new routes accept `ProjectIngesterRequest`, require `require_project(Action.EXECUTE, body_locator=True)` and `require_application_action(Action.RUN_INGESTERS)`, and return `ValidateResponse` or `IngestResponse` from the corresponding helper method.
  * **Implementation:** Inject the same request-scoped `AuthorizationService` into a small `get_project_ingester_service` dependency that constructs `ProjectIngesterService`; make that dependency overridable in route tests. Pass the dependency's `AuthorizedResource` and the fixed `CHANGE_REQUEST_INGESTER_KEY` to `validate_project_tables` or `ingest_project_tables`. Preserve the helper's failure response body rather than converting it into an HTTP error. Convert a helper `PermissionError` caused by a forged direct-call input or query/body mismatch to a denial before project work; let the existing project dependency conceal missing or unauthorized resources. Keep the shared routes and `ingester_operator_dependency` unchanged.
  * **Constraints:** Do not accept `source`, `config`, `output_folder`, target connection, provider identity, `run_validation`, or `validate_first` on these routes. Do not remove `RUN_INGESTERS` from either route or the direct helper.
  * **Validation:** `V-1`, `V-2` — route registration, dependency decisions, exact resource forwarding, strict body rejection, and response forwarding.

* [x] `T5.2` **Test route authorization and failure results:** Exercise both routes with real authorization dependencies and a stubbed or injected helper, then test the established direct-call guard alongside them.
  * **Target:** `backend/tests/api/test_project_ingester_routes.py` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (regression, no planned change).
  * **Current → required:** Service tests verify the guard and response mapping, but no HTTP test verifies either new route. Add an isolated authorization store and async ASGI client as in existing protected-route tests; create the saved project through `POST /api/v1/projects` before calling it.
  * **Implementation:** Cover unauthenticated 401, missing/inaccessible or non-executable project 404, project executor without application action 403, and application operator without project execute 404. Check that denial never calls the helper. Send valid requests for each route and assert the helper receives the exact authorized locator and typed request. Send top-level and nested forbidden fields, including `source`, `config`, provider identity, and `validate_first`, and assert 422 with no helper call. Exercise a query/body locator mismatch to confirm the helper guard denies before loading another project. Return project-specification errors and ingester data-validation failure through the helper and assert the exact `ValidateResponse` / `IngestResponse` fields, zero records, no output path or bundle, and no normalization or artifact call. Reuse Phase 4 direct-helper tests for invalid `AuthorizedResource` cases and `validate_first=True`.
  * **Validation:** `V-1`, `V-2`, `V-5` — auth matrix, invalid body, early-stop outcomes, and file-route regressions.

**Completion evidence:** Both paths are visible on the registered router; accepted calls reach the helper with its authorized resource, and denied or invalid calls cannot begin project or ingester work.

### Area 2: Add typed project requests to the operator client

**Objective:** The API client and store can submit a strict saved-project request while leaving file ingesters on their current methods.

**Affected code:** `frontend/src/types/ingester.ts`; `frontend/src/api/ingester.ts`; `frontend/src/stores/ingester.ts`; `frontend/src/api/__tests__/ingester.test.ts` (**NEW**); `frontend/src/stores/__tests__/ingester.test.ts` (**NEW**).

**Dependencies:** Area 1 fixes route paths and response contracts.

**Tasks:**

* [x] `T5.3` **Add a separate project request and client path:** Model the strict backend request and add validate/ingest methods for the two fixed paths.
  * **Target:** `frontend/src/types/ingester.ts::ProjectIngesterRequest`, `ProjectSubmissionOptions` (**NEW** interfaces); `frontend/src/api/ingester.ts::ingesterApi`.
  * **Current → required:** Existing `ValidateRequest` and `IngestRequest` are file-shaped and permit arbitrary config. The project path needs `project_name`, optional `translate`, `drop_foreign_keys`, `default_entity`, typed `submission_context` (`submission_name`, `timestamp`, `datatype`, `identifier`, optional `description`, `issue_identifier`, `author`, `run_id`), and optional `deploy_strategy` only.
  * **Implementation:** Add `validateProject(request)` and `ingestProject(request)` to `ingesterApi` using the fixed `/ingesters/sead_change_request/from-project/validate` and `/ingest` paths. Reuse `ValidateResponse` and `IngestResponse`. Keep the file methods' signatures and paths unchanged. `run_id` may be represented as an optional field; generating and reusing one across an attempt belongs to the companion work.
  * **Validation:** `V-3` — mock `apiClient.post` and assert exact URL, body, and response for both project methods and unchanged file methods.

* [x] `T5.4` **Expose project actions in the ingester store:** Add separate store actions for the new client methods.
  * **Target:** `frontend/src/stores/ingester.ts::useIngesterStore`; `frontend/src/api/__tests__/ingester.test.ts` (**NEW**); `frontend/src/stores/__tests__/ingester.test.ts` (**NEW**).
  * **Current → required:** Store actions always call file routes. Add `validateProject` and `ingestProject` that populate the existing result, loading, and error state from the corresponding project API methods; keep `validate` and `ingest` for file input.
  * **Implementation:** Use the same error detail fallback and state clearing as the existing actions. Keep selected-ingester checks consistent. Do not merge project data into a file request or add an arbitrary config dictionary.
  * **Validation:** `V-3` — test success and API failure state for project actions, plus regression calls from file actions to existing methods.

**Completion evidence:** API and store tests show project calls serialize the strict type to the two fixed paths while ordinary file calls retain their current paths and state behavior.

### Area 3: Switch the saved-project Dispatch form and guide

**Objective:** A loaded saved project's Change Request form validates and ingests through the project-only client without asking for or sending a workbook path.

**Affected code:** `frontend/src/components/ingester/IngesterForm.vue`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`; `frontend/src/views/IngesterView.vue` and `frontend/src/views/ProjectDetailView.vue` (reuse only); `docs/USER_GUIDE.md`.

**Dependencies:** Area 2 project actions exist.

**Tasks:**

* [x] `T5.5` **Route Change Request form actions to project methods:** Build one allowlisted project request from the open saved project and named submission inputs, and use it for validation and ingestion.
  * **Target:** `frontend/src/components/ingester/IngesterForm.vue::handleValidate`, `handleIngest`, request builders and form template; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`.
  * **Current → required:** The form disables Change Request, requires `form.source`, and builds file requests containing `source`, `config`, and caller provider code. Enable Change Request only when the route's `projectName` identifies the loaded `selectedProject`; leave it disabled while the project loads, is missing, or mismatches. Keep the top-level Ingestion view's Change Request exclusion.
  * **Implementation:** Hide the workbook path and file-only `Ignore Columns` and data-source status controls for Change Request. Replace the retired warning with saved-project guidance. Build `ProjectIngesterRequest` from the fixed route project name, existing submission-name/timestamp/datatype/identifier and optional description/issue/author inputs, plus selected deploy strategy; omit absent workflow options or use their backend defaults. Send no `source`, `config`, provider code, target model, database, output folder, or `validate_first`. Use store `validateProject` and `ingestProject`; keep the existing pending-confirmation and deploy-artifact result display. Preserve ordinary ingesters' source field, registration and explode options, form validation, and file actions.
  * **Constraints:** The project locator comes from the open route project, not a free-text override or nested submission field. Do not implement companion `run_id` persistence in this phase.
  * **Validation:** `V-4` — loading/mismatch disables actions; an accepted project submits exact allowlisted payloads to each project action; no file action runs; ordinary ingester still sends its file request.

* [x] `T5.6` **Update the operator instructions:** Explain the saved-project Change Request workflow after the client switch.
  * **Target:** `docs/USER_GUIDE.md::Dispatch Tab (in Project Workspace)`, `SEAD Change Request Requirements`.
  * **Current → required:** The guide says Dispatch requires prior Execute output. Clarify that Change Request uses the saved project's normalized tables directly: open the project, enter the named submission details, validate, then generate and review the deploy bundle. Keep the prior-output guidance only where it applies to file ingesters; mention both interim permissions without implying the companion exception has shipped.
  * **Validation:** `V-4`, `V-5` — manual comparison with the form and routes, and documentation link check.

**Completion evidence:** In the saved project's Dispatch tab, Change Request can run without a source path; a mismatched or absent route project cannot submit, and file-only ingesters behave as before.

## Acceptance-Criteria Coverage

| Criterion and source | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH5-AC-1` (`P-AC-8`) | `T5.1`, `T5.2` | `V-1`, `V-2` | Both strict routes enforce project execute and interim application action, then pass the authorized project to the helper. |
| `PH5-AC-2` (`P-AC-10`) | `T5.3`, `T5.4`, `T5.5`, `T5.6` | `V-3`, `V-4`, `V-5` | Dispatch sends only the named project request to the fixed paths; file-only ingesters retain their file routes. |
| `PH5-AC-3` (`P-AC-12`) | `T5.1`, `T5.2` | `V-1`, `V-2` | Route and direct-call denial occurs before project loading or side effects. |
| `PH5-AC-4` (`P-AC-13`) | `T5.1`, `T5.2` | `V-2` | Project failures return existing failure bodies; failed ingester validation writes no bundle. |

`VM-5.1` maps to `V-1` and `V-2`; `VM-5.2` maps to `V-2`; `VM-5.3` maps to `V-3`, `V-4`, and `V-5`.

## Validation And Testing

Use `tmp_path`, an isolated authorization repository, and stubbed project loading/normalization/SIMS/database collaborators for new backend route tests. Do not call a live target database or SIMS. New client tests mock `apiClient`; form tests use the existing mocked stores and loaded/mismatched project fixtures.

| ID | Check and target | Command or method | Covers | Expected result after implementation | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Route auth and strict input in `backend/tests/api/test_project_ingester_routes.py` (**NEW**) | `rtk .venv/bin/pytest backend/tests/api/test_project_ingester_routes.py backend/tests/models/test_project_ingester.py -q` | `PH5-AC-1`, `PH5-AC-3` | 401/403/404/422 cases deny before helper work; accepted requests forward the exact typed body and authorized locator. | Not run: route test file and routes do not exist yet. Existing strict model tests passed in the focused baseline. |
| `V-2` | Project/ingester failure mapping in `backend/tests/api/test_project_ingester_routes.py` (**NEW**) and existing direct-helper tests | `rtk .venv/bin/pytest backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py -q` | `PH5-AC-1`, `PH5-AC-3`, `PH5-AC-4` | Route bodies preserve project errors, warning-only success, and failed data validation; no normalization, SIMS call, or bundle on an early failure; direct guard remains enforced. | Not run: route cases do not exist yet. Existing direct-helper suite passed in the focused baseline. |
| `V-3` | API/store contract in `frontend/src/api/__tests__/ingester.test.ts` and `frontend/src/stores/__tests__/ingester.test.ts` (both **NEW**) | `rtk proxy pnpm --dir frontend exec vitest run src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts` | `PH5-AC-2` | Exact fixed URLs, allowlisted bodies, response and error state, and unchanged file-method calls. | Not run: both test files and project methods do not exist yet. |
| `V-4` | Dispatch form and navigation in `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`, `frontend/src/views/__tests__/IngesterView.test.ts`; guide check | `rtk proxy pnpm --dir frontend exec vitest run src/components/ingester/__tests__/IngesterForm.test.ts src/views/__tests__/IngesterView.test.ts`; compare `docs/USER_GUIDE.md` with the implemented form | `PH5-AC-2` | Route project can submit without a source; loading/mismatch blocks; payload excludes arbitrary fields; file-only behavior and top-level exclusion remain; guide matches the UI. | Pass: current 9 component/view tests, which still assert the retired Change Request state. New behavior not run. |
| `V-5` | Existing backend routes, TypeScript, lint, formatting, and docs | Run the commands below. | All criteria and preserved behavior | Shared file routes still reject Change Request and work for other ingesters; direct guard and quality checks pass; docs links resolve. | Pass: current focused backend model/service/file-route suite and `vue-tsc --noEmit`. New route, API, and form checks not run. |

**Execution results (2026-10-19):**

- `V-1` and `V-2`: The new project-route tests, shared file-route regressions, project-scope tests, and direct-helper tests passed:
  `rtk .venv/bin/pytest backend/tests/api/test_project_ingester_routes.py backend/tests/api/test_ingesters.py backend/tests/api/test_sead_change_request_project_scope.py backend/tests/services/test_project_ingester_service.py -q`.
- `V-3` and `V-4`: The project API/store tests, Dispatch form tests, and top-level Ingestion exclusion tests passed (19 tests):
  `rtk proxy pnpm --dir frontend exec vitest run src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts src/views/__tests__/IngesterView.test.ts`.
- `V-5`: Backend Ruff, Black, and isort checks passed. Frontend `vue-tsc --noEmit`, ESLint, Prettier, `make check-doc-links`, and `git diff --check` passed.
- Acceptance evidence: `PH5-AC-1` and `PH5-AC-3` are supported by `V-1` and `V-2`; `PH5-AC-4` by `V-2`; `PH5-AC-2` by `V-3`, `V-4`, and `V-5`.

`V-5` commands after implementation:

```bash
rtk .venv/bin/pytest backend/tests/api/test_ingesters.py backend/tests/api/test_sead_change_request_project_scope.py backend/tests/services/test_project_ingester_service.py -q
rtk .venv/bin/ruff check backend/app/api/v1/endpoints/ingesters.py backend/tests/api/test_project_ingester_routes.py
rtk .venv/bin/black --check backend/app/api/v1/endpoints/ingesters.py backend/tests/api/test_project_ingester_routes.py
rtk .venv/bin/isort --check-only backend/app/api/v1/endpoints/ingesters.py backend/tests/api/test_project_ingester_routes.py
rtk proxy pnpm --dir frontend exec vue-tsc --noEmit
rtk proxy pnpm --dir frontend exec eslint src/api/ingester.ts src/stores/ingester.ts src/components/ingester/IngesterForm.vue src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts
rtk proxy pnpm --dir frontend exec prettier --check src/api/ingester.ts src/types/ingester.ts src/stores/ingester.ts src/components/ingester/IngesterForm.vue src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts
rtk make check-doc-links
rtk git diff --check
```

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Project-only HTTP entry points and dependency | `backend/app/api/v1/endpoints/ingesters.py::router`, `get_project_ingester_service` (**NEW** function) | `T5.1` | `V-1`, `V-2` pass for both fixed paths. |
| Route contract and authorization tests | `backend/tests/api/test_project_ingester_routes.py` (**NEW**) | `T5.2` | Auth, strict-body, resource forwarding, and failure-result cases pass. |
| Typed project client and store | `frontend/src/types/ingester.ts::ProjectIngesterRequest`, `ProjectSubmissionOptions` (**NEW** interfaces); `frontend/src/api/ingester.ts::ingesterApi`; `frontend/src/stores/ingester.ts::useIngesterStore` | `T5.3`, `T5.4` | `V-3` passes; file methods stay callable. |
| Client and store tests | `frontend/src/api/__tests__/ingester.test.ts` (**NEW**); `frontend/src/stores/__tests__/ingester.test.ts` (**NEW**) | `T5.3`, `T5.4` | Exact path/payload and state assertions pass. |
| Saved-project Dispatch form and tests | `frontend/src/components/ingester/IngesterForm.vue`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `T5.5` | `V-4` passes for project and file workflows. |
| Operator instructions | `docs/USER_GUIDE.md` | `T5.6` | Guide describes the shipped project-only workflow and passes `V-5`. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Publish guarded project-only routes | Done | Phase 4 helper | `T5.1`–`T5.2` complete; auth, strict-body, response, and direct-helper checks passed. |
| Area 2: Add typed project requests to the operator client | Done | Area 1 | `T5.3`–`T5.4` complete; fixed project paths and unchanged file methods passed. |
| Area 3: Switch the saved-project Dispatch form and guide | Done | Area 2 | `T5.5`–`T5.6` complete; matched-project and file-only workflows passed. |

## Definition Of Done

- [x] The implementation agent confirms the verified repository targets still match this plan; on a material conflict, stop and report the difference before changing scope.
- [x] `PH5-AC-1`–`PH5-AC-4` each have passing task and validation results, including `VM-5.1`–`VM-5.3`.
- [x] Both project-only routes enforce both interim permissions and reject unknown top-level and nested input before helper work.
- [x] The helper's direct project guard, mandatory project and ingester checks, failure bodies, and no-workbook behavior remain covered by regression tests.
- [x] The saved-project Dispatch form sends only named project and submission fields; loading or mismatched projects cannot submit, while other ingesters still use their file routes.
- [x] The user guide matches the shipped workflow; focused tests, TypeScript, backend/frontend lint and formatting, documentation links, and whitespace checks pass.
- [x] All deliverables are complete; deviations and follow-up work are recorded. The companion output/database rules remain prerequisites for removing `RUN_INGESTERS` or adding persistent `run_id` reuse.

## Risks And Open Questions

- **Interim output rule:** The Phase 4 bundle writer can replace a same-name output. Retain the application action on both routes and the helper until the companion phase supplies exclusive output and read-only database access.
- **Route input order:** `require_project(..., body_locator=True)` may read a query locator when present. The helper's exact match with the typed body is therefore required, and the route tests must cover this case before any project load.
