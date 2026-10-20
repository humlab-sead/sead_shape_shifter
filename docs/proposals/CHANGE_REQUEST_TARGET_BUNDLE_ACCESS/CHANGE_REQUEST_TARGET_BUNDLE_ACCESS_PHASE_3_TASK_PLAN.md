# Change Request Target Bundle Access — Phase 3 Task Plan

## Phase Summary

**Goal:** Let a principal with `project:execute` on a saved project validate and create its SEAD Change Request bundle without `application:run_ingesters`.

**Readiness:** Validated for a task plan. [Phase 3](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md#phase-3-cut-over-project-only-access) is marked ready after Phases 1 and 2 are accepted. The [Phase 1](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md) and [Phase 2](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_2_TASK_PLAN.md) task plans record their criteria and focused checks complete. Phase 2 recorded skipped live PostgreSQL and SIMS checks; its unit, route, and client checks passed. Recheck those safeguards before removing the permission gate, and stop if they regress.

**Sources:** [Proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) (`P-AC-1`–`P-AC-5`) and [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) (`VM-3.1`, `VM-3.2`). Keep `project:execute`, the authorized saved-project identity, the strict no-source request, backend-selected target connection and output root, exclusive run folders, read-only target verification, SIMS scope and run ID rules, and retired Change Request file input. The SEAD Release Cycle still reviews the generated bundle.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-1`): A principal with `project:execute` on the named saved project can use both project-only routes and the direct helper without `application:run_ingesters`; unauthenticated callers and principals without that project action remain denied.
2. [x] `PH3-AC-2` (from `P-AC-1`, `P-AC-4`): Change Request file input remains rejected; the shared file routes and other ingesters retain their application-action requirement.
3. [x] `PH3-AC-3` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-5`): The newly authorized project executor can validate and create a bundle using accepted output, database, SIMS, and retry behavior from Phases 1 and 2.

## Repository Findings

**Repository basis:** `change-request-target-bundle-access` at `2907e6f1`, planning date 2026-10-20. Uncommitted files under `TARGET_MODEL_GUIDED_ENTITY_CREATION` were not used. Graphify was used for navigation; source, tests, and documentation below were checked directly. The proposal and phase plan's Current Position describe pre-Phase-1 behavior; current code and the completed task plans govern this cutover.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/ingesters.py::validate_project_ingester`, `ingest_project_ingester` | Both dedicated routes depend on `project_ingester_operator_dependency` (`RUN_INGESTERS`) and `project_ingester_project_dependency` (`require_project(Action.EXECUTE, body_locator=True)`). | Remove only the dedicated application dependency and its unused route parameters. Keep the project dependency and the request/response types. |
| `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data` | The shared routes use the separate `ingester_operator_dependency` and reject the Change Request key before calling `IngesterService`. | Preserve their application gate and file-input rejection. |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService._guard_project_call` | The helper checks an `AuthorizedResource`, `Action.EXECUTE`, active project type and locator, typed `ProjectIngesterRequest`, exact project-name match, then repeats the application-action check. `authorization_service` is otherwise unused. | Delete only the repeated application check. Remove the now-unused service constructor dependency and update its route factory/test helper. Keep every project and request check before project loading. |
| `backend/app/authorization/dependencies.py::require_project`; `backend/app/models/ingester.py::ProjectIngesterRequest` | The project dependency authorizes the body or query locator; the helper catches a mismatch. The request model forbids extra source, output, database, and nested identity fields. | Preserve concealed `404` for missing/unauthorized projects and mismatched locators; keep `422` for forbidden request fields. |
| `backend/tests/api/test_project_ingester_routes.py`; `backend/tests/services/test_project_ingester_service.py` | Route tests already cover `401`, missing project action, forwarding, strict fields, and mismatch under the interim double gate. A service test currently expects the application check to reject a direct call. | Replace interim expectations with executor-only success and direct-helper checks; keep negative cases. |
| `backend/tests/api/test_ingesters.py`; `backend/tests/authorization/test_route_authentication.py` | Shared file-input rejection and route inventory/classification tests exist. The file tests override the generic application dependency. | Add a non-overridden route check for the generic gate; retain file-input and inventory regressions. |
| `ingesters/sead_change_request/artifact_writer.py`, `ingester.py`, `orchestration.py`; `frontend/src/stores/ingester.ts` | Phase 1 reserves exclusive managed run folders and returns the written path. Phase 2 blocks unresolved sequence IDs, keeps target reads, and retains an attempt run ID in the store. | Reuse these contracts in an executor workflow test; do not change bundle or identity logic in this phase. |
| `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, `docs/AUTHORIZATION.md`, `docs/USER_GUIDE.md`, `ingesters/sead_change_request/README.md` | The inventory and user guide still say project-only routes need the application action; `AUTHORIZATION.md` has older generic-ingester wording, and the package README still says there is no operator entry point. | Update only the descriptions affected by the shipped cutover; keep generic file-ingester guidance intact. |

## Scope

**In scope:** The two dedicated project-only route dependencies, the direct helper's authorization check and construction, authorization/workflow tests, the authorization inventory, the user guide, and the Change Request package's entry-point description.

**Out of scope:** Shared file-route permissions, other ingesters, authorization roles or grant policy, project request fields, Phase 1 bundle output, Phase 2 target/SIMS/client behavior, generated SQL execution, and SEAD Release Cycle review.

## Work Breakdown

### Area 1: Cut over only the project-only permission checks

**Objective:** The dedicated routes and direct helper accept a project executor without an application role while still requiring the exact authorized saved project.

**Affected code:** `backend/app/api/v1/endpoints/ingesters.py::validate_project_ingester`, `ingest_project_ingester`, `get_project_ingester_service`; `backend/app/services/project_ingester_service.py::ProjectIngesterService._guard_project_call`, `__init__`.

**Dependencies:** Recheck accepted Phase 1 output and Phase 2 read-only/identity results (`V-0`). If a safeguard fails, leave the interim gate and report the failure.

**Tasks:**

* [x] `T3.1` **Change:** Remove the application-action dependency from the two dedicated routes.
  * **Target:** `backend/app/api/v1/endpoints/ingesters.py::project_ingester_operator_dependency`, `validate_project_ingester`, `ingest_project_ingester`.
  * **Current → required:** Both routes require `RUN_INGESTERS` and project `EXECUTE`. Keep `Depends(project_ingester_project_dependency)` on each; remove only the dedicated `RUN_INGESTERS` dependency and unused principal parameter.
  * **Implementation:** Preserve the static paths, fixed `CHANGE_REQUEST_INGESTER_KEY`, typed `ProjectIngesterRequest`, helper calls, response models, and existing exception mapping. Do not change `ingester_operator_dependency` or `ingester_project_dependency` on shared routes.
  * **Constraints:** Authorization must still run before project normalization. An unauthenticated or unauthorized project request must not reach the helper.
  * **Validation:** `V-1`, `V-2`, `V-4`; executor-only `200`, unauthenticated `401`, missing project action `404`, and unchanged shared-route `403`.
* [x] `T3.2` **Change:** Remove the direct helper's application check while keeping its authorized-resource guard.
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService._guard_project_call`, `__init__`; `backend/app/api/v1/endpoints/ingesters.py::get_project_ingester_service`.
  * **Current → required:** `_guard_project_call` rejects a valid project executor when `can_perform_application_action(..., Action.RUN_INGESTERS)` is false. It must return the authorized project locator after its existing resource/action/type/lifecycle/request/match checks, with no application-role lookup.
  * **Implementation:** Remove the now-unused `AuthorizationService` constructor parameter and field, and simplify the FastAPI service factory. Update test construction. Keep `AuthorizedResource` mandatory for direct calls; reject wrong action, inactive/wrong resource, untyped request, or mismatched project before loading project data.
  * **Constraints:** Do not treat a caller-supplied project name as an authorization grant or bypass `ProjectMapper` and trusted project config construction.
  * **Validation:** `V-1`, `V-3`; both direct methods work without an application role, and invalid authorization data performs no project load.

**Completion evidence:** `VM-3.1` shows the dedicated permission exception with project authorization intact; the shared gate remains separate.

### Area 2: Test denied callers, unchanged file routes, and the full executor workflow

**Objective:** The newly authorized principal completes the project-only workflow, while callers without project access and all shared file routes retain their previous behavior.

**Affected tests:** `backend/tests/api/test_project_ingester_routes.py`; `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_ingesters.py`; `backend/tests/authorization/test_route_authentication.py`; existing Phase 1/2 ingester and frontend tests.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T3.3` **Test:** Replace double-gate expectations with the new route and direct-helper matrix.
  * **Target:** `backend/tests/api/test_project_ingester_routes.py::test_project_routes_require_authentication_and_both_permissions`, `test_project_routes_forward_authorized_resource_request_and_response`, `test_project_route_query_body_mismatch_is_concealed_before_project_work`; `backend/tests/services/test_project_ingester_service.py::test_application_permission_is_required_before_project_load`, `test_invalid_project_resource_is_rejected_before_project_load`, `test_mismatched_project_name_is_rejected_before_application_check`.
  * **Current → required:** A project executor without `operator` gets `403`, and direct ingestion is denied by the application check. Replace those assertions: executor without an application role reaches both helper methods; an application operator with no project grant, a viewer with the application role, an unauthenticated caller, an inactive project, and a mismatched locator remain denied before work.
  * **Implementation:** Reuse `authorization_repository`, `client_for_principal`, `create_project`, and `install_project_ingester_stub` in the route tests. Remove the obsolete `FakeAuthorizationService` and its test-helper argument when the service constructor changes; replace the old application-denial test with a direct-call success test for each operation using `authorized_project()`. Parameterize the resource, request-type, and locator failures for both direct methods. Keep `test_project_routes_reject_file_and_caller_configuration_fields` and response forwarding assertions.
  * **Constraints:** Preserve `401`/concealed `404`/`422` response distinctions; do not grant `operator` merely to make executor tests pass.
  * **Validation:** `V-2`, `V-3`.
* [x] `T3.4` **Test:** Prove shared file routes still require the application action and reject retired Change Request input.
  * **Target:** `backend/tests/api/test_project_ingester_routes.py` (add route checks using its non-overridden authorization fixture); `backend/tests/api/test_ingesters.py::test_validate_rejects_retired_change_request_file_input`, `test_ingest_rejects_retired_change_request_file_input`.
  * **Current → required:** File-route tests override `ingester_operator_dependency`, so they do not prove its gate remains. With a project executor but no application role, generic `/sead/validate` and `/sead/ingest` must return `403` before the ingester service. With an operator role, Change Request file input must still return `400`, while `/sead` retains its existing generic route behavior.
  * **Implementation:** Use `client_for_principal` without overriding `ingester_operator_dependency`; grant the operator role only to the positive generic-route cases. Patch `get_ingester_service` with a stub/spy for `/sead` calls. Check validation and ingestion separately and assert the service is untouched on denied or retired-input requests. Keep the existing direct service/ingester retired-file tests as regressions.
  * **Constraints:** Leave `require_ingester_project` and shared route models unchanged.
  * **Validation:** `V-4`.
* [x] `T3.5` **Test:** Run validation and bundle creation as a project executor without an application role through the assembled app.
  * **Target:** `backend/tests/api/test_project_ingester_routes.py` (add one workflow test); `backend/tests/services/test_project_ingester_service.py::test_successful_ingest_writes_only_bundle_under_managed_root`; `frontend/src/stores/__tests__/ingester.test.ts` (existing retry checks).
  * **Current → required:** Route tests use a stub helper, and the real-ingester service test uses a helper without an HTTP principal. Add a route-to-real-helper test with an executor grant and no `operator` role that posts the same explicit `run_id` to validate and ingest.
  * **Implementation:** Reuse the route test's registered project fixture and the service test's isolated `ProjectMapper`, `CompositeProjectSpecification`, `normalize_project`, target-model, and trusted-context patterns. Override only `get_project_ingester_service` with a configured **real** `ProjectIngesterService`, not a method stub. Inject recording SIMS and target-verification fakes through the existing runtime dependency hooks; supply normalized rows with declared business keys, a temporary `INGEST_OUTPUT_DIR`, and the same explicit `run_id` in both requests. Assert a valid response, successful bundle, manifest and response run ID, output path under the managed root, provider-schema SIMS scope and key, and target verification calls without a write or sequence call. Run a second distinct ID and assert its output does not change the first bundle; leave pending-confirmation retry and client ID reuse to the existing ingester and frontend store tests.
  * **Constraints:** Do not use live target or SIMS services in this test. Preserve Phase 1 collision/cleanup tests and Phase 2 key/sequence tests; report any failure before declaring the cutover complete.
  * **Validation:** `V-0`, `V-5`, `V-6`.

**Completion evidence:** `VM-3.1` and `VM-3.2` pass: executor-only access creates the expected managed bundle; denied callers and generic routes retain their checks.

### Area 3: Document the shipped permission rule

**Objective:** Operators and maintainers can see which Change Request routes require project access and which generic ingester routes still require the application action.

**Affected documentation:** `docs/USER_GUIDE.md`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md`; `docs/AUTHORIZATION.md`; `ingesters/sead_change_request/README.md`.

**Dependencies:** Areas 1 and 2 pass.

**Tasks:**

* [x] `T3.6` **Document:** Replace the interim permission text with the tested rule.
  * **Target:** `docs/USER_GUIDE.md::Dispatch Tab (in Project Workspace)`, `docs/USER_GUIDE.md::SEAD Change Request Requirements`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md::Ingester, Filters, Logs, And Release Notes`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md::Classification Review`; `docs/AUTHORIZATION.md::Purpose`, `docs/AUTHORIZATION.md::Current Coverage`; `ingesters/sead_change_request/README.md::Current Scope`.
  * **Current → required:** The user guide and route inventory say both permissions are required, and the package README says there is no project entry point. State that a saved-project Change Request needs `project:execute` on that project, while generic file ingesters still need `application:run_ingesters`; Change Request file input remains retired.
  * **Implementation:** Update the two inventory rows and nearby explanation, plus summary counts affected by their new classification. Explain in the user guide where the operator validates, dispatches, finds `output_path`, and reuses the run ID for a pending Binding Set. Keep permission details out of the general file-ingester steps. Remove or qualify stale generic-ingester wording in `AUTHORIZATION.md` without claiming unrelated authorization follow-up is complete.
  * **Constraints:** Do not describe the generated SQL as applied by Shape Shifter or transfer review to it; retain SEAD Release Cycle responsibility.
  * **Validation:** `V-7`; links pass and docs match the route/service tests.

**Completion evidence:** The inventory, operator instructions, and package README agree with tested behavior, and the route inventory still matches the assembled app.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-1`) | `T3.1`–`T3.3` | `V-1`–`V-3` | Project executor succeeds without application role; denied callers never reach project work. |
| `PH3-AC-2` (from `P-AC-1`, `P-AC-4`) | `T3.1`, `T3.4`, `T3.6` | `V-2`, `V-4`, `V-7` | Generic routes retain the application gate; retired Change Request file input remains rejected. |
| `PH3-AC-3` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-5`) | `T3.1`–`T3.2`, `T3.5`–`T3.6` | `V-0`, `V-5`–`V-7` | Executor-only validate/ingest writes a managed bundle with read-only target access and consistent SIMS/run data. |

## Validation And Testing

Baseline on 2026-10-20: `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_ingesters.py`, and `backend/tests/authorization/test_route_authentication.py` pass under the interim gate. The Change Request ingester, artifact writer, and orchestration suites pass. Focused frontend store/form suites pass (17 tests). These are current-state results, not Phase 3 acceptance. Phase 2's completed plan records live PostgreSQL/SIMS skips because local service variables were unavailable.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-0` | Recheck Phase 1/2 safeguards before removing the gate | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_artifact_writer.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_sql_builder.py -q`<br>`rtk pnpm --dir frontend test:run src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts` | Prerequisite to `PH3-AC-3` | Phase 1 output/collision/cleanup and Phase 2 read-only/key/retry cases pass; report service-dependent skips. Stop before `T3.1` if a safeguard fails. | Pass: all five Change Request backend suites and both frontend suites passed; 3 service-dependent skips remain, unchanged from Phase 2. |
| `V-1` | Narrow dependency and helper source check | Inspect `backend/app/api/v1/endpoints/ingesters.py::validate_project_ingester`, `ingest_project_ingester`, `validate_data`, `ingest_data`, and `backend/app/services/project_ingester_service.py::_guard_project_call`; confirm only the project-only app checks are removed. | `PH3-AC-1`, `PH3-AC-2` | Project-only routes retain `require_project(Action.EXECUTE, body_locator=True)`; shared routes retain `require_application_action(Action.RUN_INGESTERS)`; direct guard retains exact authorized-project checks. | Pass: only the project-only application checks were removed; the shared gate and direct guard are unchanged. |
| `V-2` | Project-only route authorization in `backend/tests/api/test_project_ingester_routes.py` | `rtk uv run pytest backend/tests/api/test_project_ingester_routes.py -q` | `PH3-AC-1`, `PH3-AC-2` | Executor-only calls reach both helpers; unauthenticated, no-project-action, wrong-project, and forbidden-field calls remain denied. | Pass: executor-only calls reach the helper; denied callers remain 401/404/422. |
| `V-3` | Direct helper in `backend/tests/services/test_project_ingester_service.py` | `rtk uv run pytest backend/tests/services/test_project_ingester_service.py -q` | `PH3-AC-1` | Both direct methods accept valid `AuthorizedResource` without an app role; invalid resources and request mismatches stop before project load. | Pass: both direct methods accept a valid `AuthorizedResource` without an app role; invalid input stops before project load. |
| `V-4` | Shared-route and retired-file regressions in `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/api/test_ingesters.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/api/test_project_ingester_routes.py backend/tests/api/test_ingesters.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-2` | Project executor without app role gets `403` from generic routes; operator can use other ingesters; Change Request file input gets `400` with app role. | Pass: generic routes return 403 for a project executor, and retired Change Request file input returns 400 for an operator. |
| `V-5` | Executor workflow through `backend/tests/api/test_project_ingester_routes.py` plus existing service/ingester tests | `rtk uv run pytest backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-3` | One no-operator executor validates and creates a real bundle with managed output, unchanged run ID, SIMS scope/key, and verification-only target calls. | Pass: the executor-only workflow creates a real managed bundle with the unchanged run ID and provider-schema scope. |
| `V-6` | Frontend attempt-ID regression in `frontend/src/stores/__tests__/ingester.test.ts`, `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `rtk pnpm --dir frontend test:run src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts` | `PH3-AC-3` | Validation, ingestion, and pending retry use one ID; success or changed identity mints another. | Pass: 17 tests. |
| `V-7` | Authorization inventory, docs, formatting, and whitespace | `rtk uv run pytest backend/tests/authorization/test_route_authentication.py backend/tests/authorization/test_dependencies.py -q`<br>`rtk .venv/bin/black --check backend/app/api/v1/endpoints/ingesters.py backend/app/services/project_ingester_service.py backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py`<br>`rtk .venv/bin/isort --check-only backend/app/api/v1/endpoints/ingesters.py backend/app/services/project_ingester_service.py backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py`<br>`rtk make check-doc-links`<br>`rtk git diff --check` | `PH3-AC-2`, `PH3-AC-3` | Route classification and inventory checks, formatting, links, and diff pass; docs describe the shipped rule. | Pass: route classification/inventory, black, isort, doc links, and git diff --check all pass. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Project-only route permission | `backend/app/api/v1/endpoints/ingesters.py::validate_project_ingester`, `backend/app/api/v1/endpoints/ingesters.py::ingest_project_ingester`, `backend/app/api/v1/endpoints/ingesters.py::get_project_ingester_service` | `T3.1`, `T3.2` | Only project authorization remains on the dedicated routes. |
| Direct helper permission | `backend/app/services/project_ingester_service.py::ProjectIngesterService._guard_project_call`, `backend/app/services/project_ingester_service.py::ProjectIngesterService.__init__` | `T3.2` | Authorized project executor passes; invalid project input is denied. |
| Authorization and workflow tests | `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_ingesters.py` | `T3.3`–`T3.5` | `VM-3.1` and `VM-3.2` pass, including generic route denial. |
| Operator and authorization documentation | `docs/USER_GUIDE.md`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, `docs/AUTHORIZATION.md`, `ingesters/sead_change_request/README.md` | `T3.6` | Described permissions match tested routes and helper. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Cut over project-only checks | Done | `V-0` prerequisite | Dedicated routes and helper now accept a project executor without an application role. |
| Area 2: Test access and workflow | Done | Area 1 | Executor, denied callers, generic routes, and a real bundle are covered. |
| Area 3: Document shipped rule | Done | Areas 1 and 2 | Operator and authorization text now match the tested rule. |

## Definition Of Done

- [x] Before implementation, verify the named repository targets still match; on a material conflict, stop and report it rather than broadening this phase.
- [x] `V-0` confirms the accepted Phase 1/2 safeguards before the permission is removed; environment-dependent skips and their limits are recorded.
- [x] `PH3-AC-1`–`PH3-AC-3` each have passing task and validation results, including `VM-3.1` and `VM-3.2`.
- [x] All work areas and deliverables are complete; `V-1`–`V-7` pass or documented service-dependent skips retain their stated limits.
- [x] Project and request authorization failures, shared route permissions, file-input retirement, managed output, read-only target access, SIMS scope, and client run ID are regression-tested.
- [x] Authorization inventory, operator guide, and package documentation match the implemented behavior; deviations and follow-up work are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

- Phase 2's disposable PostgreSQL and live SIMS checks were skipped without configured local services. The cutover workflow must use recording fakes and the completed unit/contract tests; rerun the disposable checks when those services are available and report any remaining untested limit. A failure of a safeguard blocks the permission change.
- Route tests that replace the helper alone can prove authorization but cannot prove bundle safety. `T3.5` uses the assembled route with the real helper and ingester, while external services are injected as fakes.
- No permission decision remains open: the exception is limited to the two project-only routes and their helper.
