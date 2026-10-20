# Phase 1 Task Plan: Retire Change Request File Input

## Phase Summary

**Goal:** Retire `sead_change_request` file validation and ingestion before the project-only replacement ships.

**Readiness: Validated.** [Phase 1 of the handoff phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) is ready for a task plan and has no upstream phase. The [source proposal](./IN_MEMORY_INGESTER_HANDOFF.md) fixes the retirement rule in `P-AC-6`. Current code and affected tests were verified; focused baseline tests pass. Implementation may begin without a new design decision.

**Constraints and dependencies:** Keep the shared file request and response models, file input for other ingesters, their `application:run_ingesters` check, and Excel dispatch unchanged. Do not add project-only routes or public table methods in this phase. The existing operator form must not submit the retired Change Request workbook request. The accepted temporary result is that Change Request generation has no operator entry point until later phases.

**Acceptance criteria**

1. `PH1-AC-1` (from `P-AC-6`): Change Request metadata lists no file formats. Its file routes, service calls, and file-oriented methods fail before source resolution, a `Path` or `str` cannot select in-memory data through `config.extra`, and the operator form cannot submit the retired workbook request.
2. `PH1-AC-2` (from `P-AC-6`): Other ingesters retain their file input and permission checks; Excel dispatch keeps its current output behavior.

## Repository Findings

**Repository basis:** Branch `dev`, commit `50a7e5bc`, planning date 2026-10-19. Existing staged proposal and plan changes were treated as user work. Graphify located the ingester route and service path; the findings below were checked against current code and tests. This records the planning baseline; implementation and current verification are recorded under Execution Evidence.

| Source | Current behavior | Phase 1 implication |
| --- | --- | --- |
| `ingesters/sead_change_request/ingester.py::get_metadata`, `validate`, `ingest` | Metadata advertises `xlsx` and `xls`. The public file methods call `_prepare_change_request` and contain the result-building and artifact-writing flow. | Set file formats to `[]`. Make file methods return structured input failures before preparation; keep the downstream flow available through private bundle-based methods for existing behavior tests and Phase 3. |
| `ingesters/sead_change_request/input_resolution.py::_resolve_source_bundle` | A `Path` or `str` is checked after `config.extra["source_bundle"]` and `config.extra["tables"]`; `_load_source_bundle_from_path` can open Excel. | Reject path-shaped input first, even when extras contain a bundle or tables. Remove the now-unused workbook reader and imports. Keep direct in-memory bundles available to private preparation. |
| `backend/app/services/ingester_service.py::validate`, `ingest` | The service reads caller config, builds trusted project context and `IngesterConfig`, then calls the ingester file methods. CLI validate and ingest also use this service. | Reject the Change Request key before project loading, config construction, runtime injection, or ingester creation. Preserve other keys' service flow. |
| `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data` | Shared routes authorize the application action and, for Change Request, the named project, then call the service. | Reject the Change Request key before calling the service. Leave the existing dependencies on both shared routes, including for other keys. |
| `backend/app/models/ingester.py`, `backend/app/ingesters/protocol.py` | Shared requests require `source`; metadata exposes a list of file formats; result types already represent domain failures. | Do not change shared models or the `Ingester` protocol. An empty file-format list and structured failures fit their existing types. |
| `backend/tests/api/test_ingesters.py`, `backend/tests/ingesters/test_ingester_infrastructure.py` | API tests mock successful Change Request file calls; the infrastructure test expects `['xlsx', 'xls']`. The API fixture overrides the application and project dependencies. | Replace successful Change Request route assertions with rejection checks, test metadata `[]`, and keep separate regression checks for `sead` and authentication. |
| `backend/tests/ingesters/test_sead_change_request_ingester.py`, `test_sead_change_request_inline_staging.py`, `test_sead_change_request_submission_sims_integration.py` | Many downstream tests pass fake `.xlsx` names while taking DataFrames from `config.extra["tables"]`; one test writes a real workbook. Disposable database tests may skip without a configured loopback database. | Move downstream tests to explicit `SourceTableBundle` input through private bundle methods. Replace the workbook-success case with file-rejection coverage. Keep disposable database tests collected, and run them when the disposable database is available. |
| `frontend/src/views/IngesterView.vue`, `frontend/src/components/ingester/IngesterForm.vue` | The standalone ingester view excludes `sead_change_request`, but the project Dispatch tab embeds the shared form without that exclusion. The form could still build and submit the retired file request. | Keep the project form visible to explain the retirement, but disable its actions and guard its handlers until the project-only client path is implemented. |
| `ingesters/sead_change_request/README.md`, `DIAGRAMS.md` | Package documentation still describes Excel loading and successful public `validate()`/`ingest()` calls. | Update those descriptions to match the retired file methods and internal bundle flow; do not describe later public table methods as shipped. |

## Scope

**In scope**

- Retire Change Request file input at metadata, resolver, direct ingester methods, service, and shared file routes.
- Prevent the project Dispatch form from submitting the retired Change Request workbook request.
- Preserve the existing validation and artifact code as private bundle-based preparation so substantive downstream tests remain meaningful before Phase 3 adds the public table capability.
- Migrate affected tests and update the package README and diagrams.
- Verify unchanged file behavior for `sead` and unchanged Excel dispatcher behavior.

**Out of scope**

- Public `validate_tables()` and `ingest_tables()`, adapter copying and sanitization, no-write normalization, project-only routes, backend-managed output, and the permission exception; later phases own these.
- Containment rules for the retired Change Request source path or changes to file input for other ingesters.
- Disposable database behavior changes; the two integration suites only need to stop relying on fake workbook paths.

## Work Breakdown

### Area 1: Retire the ingester file path and keep internal bundle preparation

**Objective:** No direct Change Request file method or path-shaped source can read a workbook, while in-memory preparation remains testable.

**Affected code:** `ingesters/sead_change_request/ingester.py` and `ingesters/sead_change_request/input_resolution.py`.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Refactor:** Keep the existing validation and ingestion work behind private methods that receive a `SourceTableBundle`.
  * **Target:** `ingesters/sead_change_request/ingester.py::_prepare_change_request`, `validate`, `ingest`; add private bundle-validation and bundle-ingestion methods in the same file.
  * **Current → required:** Public `validate()` and `ingest()` both resolve a source and then run the full downstream flow. Phase 1 must reject those public calls yet retain the preparation, validation-result, collision-check, rendering, and artifact-writing behavior for direct bundle tests and later table methods.
  * **Implementation:** Move the existing post-source behavior into private methods accepting `SourceTableBundle`; pass the bundle directly to `resolve_inputs`. Preserve `validate_first` behavior and result construction inside those methods. Keep `_prepare_change_request` limited to bundle input. Phase 3 can call the same private methods after its adapter builds a bundle.
  * **Constraints:** Do not expose a new public table protocol or route. Keep `validate()` and `ingest()` separate and preserve their structured result types. Do not change SQL, SIMS, collision, or artifact behavior.
  * **Validation:** `V-1`, `V-3` — existing in-memory validation and artifact assertions pass through explicit bundles, including warning propagation and `validate_first` cases.
* [x] `T1.2` **Retire:** Reject every file-oriented Change Request call and every path-shaped source before extras or file access.
  * **Target:** `ingesters/sead_change_request/ingester.py::get_metadata`, `validate`, `ingest`; `ingesters/sead_change_request/input_resolution.py::_resolve_source_bundle`, `_load_source_bundle_from_path`.
  * **Current → required:** Metadata advertises Excel; public methods can use an Excel path or a fake path that selects tables from extras. Paths must fail even with `source_bundle` or `tables` extras.
  * **Implementation:** Set `supported_formats=[]`. Return a clear `ValidationResult(is_valid=False)` or `IngestionResult(success=False)` from the file methods before they call preparation or inspect config; keep the declared signatures. In `_resolve_source_bundle`, raise `SourceBundleError` for `Path` and `str` before reading `config.extra`; remove the unreachable Excel reader and its unused imports.
  * **Constraints:** A direct `SourceTableBundle` still reaches private preparation. Do not add a containment check for the retired path. No source read, SIMS call, database call, or bundle write may occur for rejected file methods, including when `validate_first=False`.
  * **Validation:** `V-1` — `Path` and `str` inputs fail before extras or file access; direct file methods return structured failures with no side effects; metadata has no file formats.

**Completion evidence:** Direct file methods and resolver path inputs fail without source access; private bundle tests still exercise the existing result and artifact flow.

### Area 2: Reject Change Request calls at the shared service and routes

**Objective:** No API or service caller can reach the retired Change Request file flow or construct its runtime collaborators.

**Affected code:** `backend/app/services/ingester_service.py` and `backend/app/api/v1/endpoints/ingesters.py`.

**Dependencies:** Area 1 supplies the retired ingester contract.

**Tasks:**

* [x] `T1.3` **Reject:** Add Change Request key checks before service work and at both shared file routes.
  * **Target:** `backend/app/services/ingester_service.py::IngesterService.validate`, `IngesterService.ingest`; `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data`.
  * **Current → required:** Service calls load the project and construct config before reaching the ingester; routes forward Change Request file requests to that service. Both layers must stop first.
  * **Implementation:** In the service, return the existing failed response shapes for `sead_change_request` before registry lookup, project-context loading, config copying, or runtime injection. Validation returns `is_valid=False` with a clear file-retirement error; ingestion returns `success=False`, `records_processed=0`, `output_path=None`, and error details. In each shared route, reject the key with `HTTP_400_BAD_REQUEST` and a clear message before the broad `try/except` and before calling the service, so the intended `400` is not caught and converted to `500`. Keep the current authentication and application/project authorization dependencies; an unauthenticated or unauthorized request may be denied by those dependencies before the route body runs.
  * **Constraints:** Preserve all behavior for other keys, including `application:run_ingesters` on both file routes. Do not widen the shared request models or add a key-based permission exemption. The CLI reaches the service and inherits its early rejection.
  * **Validation:** `V-2`, `V-4` — route and direct service calls reject Change Request input with no config construction or file read; other ingesters retain their file route and permission behavior.

**Completion evidence:** Both routes and both service methods reject Change Request file input before invoking the ingester, with existing authorization intact for other keys.

### Area 3: Move affected tests and align package documentation

**Objective:** The test suite no longer depends on fake workbook paths for in-memory behavior, and package documentation matches the shipped Phase 1 state.

**Affected tests and documentation:** `backend/tests/api/test_ingesters.py`, `backend/tests/api/test_sead_change_request_project_scope.py`, `backend/tests/ingesters/test_ingester_infrastructure.py`, `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_inline_staging.py`, `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`, `ingesters/sead_change_request/README.md`, and `ingesters/sead_change_request/DIAGRAMS.md`.

**Dependencies:** Areas 1 and 2 provide the new rejection points and private bundle methods.

**Tasks:**

* [x] `T1.4` **Test:** Replace old file-success assertions and move downstream tests to explicit bundle input.
  * **Target:** The six test files listed above.
  * **Current → required:** API tests expect Change Request file requests to reach a mocked service; ingester tests use fake `.xlsx` paths plus `config.extra["tables"]`, a direct bundle passed to the file method, and one real workbook-success case.
  * **Implementation:** Test API metadata `supported_formats=[]` and route `400` responses with the service mocked to fail if called. Test direct service response shapes with config, project loading, and runtime injection mocked to fail if reached. Add resolver tests for both `Path` and `str`, with and without `source_bundle` and `tables` extras; assert `SourceBundleError` before `pd.ExcelFile` or any path read. Test direct ingester file methods with `validate_first` both true and false, including valid in-memory extras, and assert no preparation, external client, or artifact calls. Replace fake-path downstream tests with `SourceTableBundle` input to the private methods; test malformed table mappings at `_build_source_bundle`, not by passing them to a retired file method. Replace the real workbook-success test with rejection coverage. In `test_sead_change_request_project_scope.py`, remove retired route success assertions and keep missing/inaccessible project authorization coverage for both routes. Update the disposable database suites' ingester calls to use explicit bundles without changing their target-database assertions.
  * **Constraints:** Keep substantive planning, identity, validation, SQL, and artifact assertions. The disposable database suites may skip without their loopback database; a skip does not prove database behavior and is not required for Phase 1 file-retirement acceptance.
  * **Validation:** `V-1`, `V-2`, `V-3` — focused tests pass and no test uses a fake workbook path to obtain in-memory tables.
* [x] `T1.5` **Document:** Describe the retired file methods and temporary internal bundle path accurately.
  * **Target:** `ingesters/sead_change_request/README.md`, `ingesters/sead_change_request/DIAGRAMS.md`.
  * **Current → required:** Both documents show successful public file validation or ingestion, and the README says Excel workbooks can be loaded. Phase 1 removes that input before public table methods exist.
  * **Implementation:** Remove workbook-loading claims and show the file methods returning input failures. Describe the private bundle preparation used for tests and later table methods. Keep artifact and domain-flow descriptions accurate; label the project-only operator path as future work.
  * **Constraints:** Do not document Phase 3 table methods or Phase 5 routes as shipped.
  * **Validation:** `V-6` — package documentation contains no active Change Request workbook-ingest instruction and repository links resolve.

**Completion evidence:** Focused tests pass through explicit bundles, rejection tests pass at each entry point, and package documentation matches the retired input contract.

### Area 4: Disable the retired Change Request form submission

**Objective:** The project Dispatch form cannot send Change Request workbook requests to the retired file routes.

**Affected code and tests:** `frontend/src/components/ingester/IngesterForm.vue` and `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`.

**Dependencies:** Areas 1 and 2 retire the backend file entry points.

**Tasks:**

* [x] `T1.6` **Disable:** Keep the Change Request form non-submittable until the project-only client path is available.
  * **Target:** `IngesterForm.vue` action buttons and `handleValidate()` / `handleIngest()`; `IngesterForm.test.ts`.
  * **Current → required:** The standalone ingester page excludes `sead_change_request`, but the saved-project Dispatch tab uses the shared form directly. Its buttons and handlers could still call the retired routes.
  * **Implementation:** Show a retirement warning, disable Validate and Dispatch for `sead_change_request`, and return early from both handlers as a safeguard against stale or programmatic calls. Keep other ingesters actionable and preserve project locator display.
  * **Constraints:** Do not add the project-only endpoints or claim that the replacement is available. Do not change other ingester request behavior.
  * **Validation:** `V-9` — component tests verify the retired actions remain disabled before and after the project loads, direct handler calls do not call the ingester store, and ordinary ingesters remain actionable.

**Completion evidence:** The project Dispatch form explains that file-based Change Request is retired, never enables its actions, and cannot call either store operation for that key.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-6`) | `T1.1`–`T1.6` | `V-1`, `V-2`, `V-3`, `V-6`, `V-9` | No Change Request file format is advertised; paths fail before extras or file access at resolver, ingester, service, and routes; the operator form cannot submit the retired request; useful in-memory tests remain. |
| `PH1-AC-2` (from `P-AC-6`) | `T1.3`, `T1.4` | `V-2`, `V-4`, `V-5` | Other ingesters still accept file requests behind their existing permission check, and Excel dispatch output is unchanged. |

The phase-plan milestones are covered by `V-1` and `V-2` for `VM-1.1`, and by `V-2`, `V-4`, and `V-5` for `VM-1.2`.

## Validation And Testing

Baseline commands below were run before implementation. They pass under the current file-input behavior; retirement assertions have not been added yet. No disposable database test was run against a live database during planning.

| ID | Check and target | Command or method | Covers | Expected result after implementation | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Resolver, direct ingester rejection, and internal bundle behavior in `test_sead_change_request_input_resolution.py` and `test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-1` | New path and extras rejection tests pass; existing downstream validation and artifact assertions pass through bundles. | Pass in the combined focused baseline run. |
| `V-2` | API, service, metadata, and other-ingester checks in `test_ingesters.py` and `test_ingester_infrastructure.py` | `rtk uv run pytest backend/tests/api/test_ingesters.py backend/tests/ingesters/test_ingester_infrastructure.py -q` | `PH1-AC-1`, `PH1-AC-2` | Change Request route `400` and structured service failures occur before service work; metadata is `[]`; `sead` behavior remains. | Pass in the combined focused baseline run. |
| `V-3` | Migrated disposable database suites in `test_sead_change_request_inline_staging.py` and `test_sead_change_request_submission_sims_integration.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_inline_staging.py backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py -q` | `PH1-AC-1` | Tests collect and use bundles. Without a configured disposable database they skip; with one, their existing database assertions pass. Skips are not evidence of database behavior. | Inline staging was included in the focused baseline: 13 skipped. Submission SIMS integration not run because it can use a disposable database. |
| `V-4` | Existing CLI and route-authentication regression | `rtk uv run pytest backend/tests/scripts/test_ingest_cli.py backend/tests/authorization/test_route_authentication.py -q` | `PH1-AC-2` | CLI for other ingesters and route authentication keep their existing behavior; Change Request receives no file-route permission exemption. | Pass in separate baseline runs; five CLI tests skipped. |
| `V-5` | Excel dispatcher regression | `rtk uv run pytest tests/test_dispatch.py tests/test_dispatch_timezone.py -q` | `PH1-AC-2` | Existing Excel output behavior is unchanged. | Pass. |
| `V-6` | Package documentation and links | Review `ingesters/sead_change_request/README.md` and `DIAGRAMS.md`; run `rtk make check-doc-links` | `PH1-AC-1` | No active workbook-ingest instruction remains for Change Request; repository documentation links pass. | Link check passes; content review found stale workbook instructions. |
| `V-7` | Non-mutating quality checks on changed Python files | `rtk uv run ruff check ingesters/sead_change_request/ingester.py ingesters/sead_change_request/input_resolution.py backend/app/services/ingester_service.py backend/app/api/v1/endpoints/ingesters.py backend/tests/api/test_ingesters.py backend/tests/ingesters/test_ingester_infrastructure.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_inline_staging.py backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`; run `rtk uv run black --check` and `rtk uv run isort --check-only` on the same paths; run `rtk git diff --check` | All changed Python files | Ruff, Black, isort, and whitespace checks pass without rewriting unrelated files. | Not run: no Python file was changed during planning. |
| `V-8` | Backend regression after focused tests | `rtk uv run pytest backend/tests -q` | `PH1-AC-1`, `PH1-AC-2` | No new backend failures; report any pre-existing or environment-dependent skips separately. | Not run: the focused baseline was sufficient to plan Phase 1. |
| `V-9` | Frontend regression for the retired form and other ingesters | `npm --prefix frontend run test -- --run --reporter=dot` | `PH1-AC-1`, `PH1-AC-2` | The form blocks both retired actions, including direct handler calls; other ingester workflows remain actionable. | Not run during planning. |

### Execution Evidence (2026-10-19)

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Pass | `backend/tests/ingesters/test_sead_change_request_input_resolution.py` and `test_sead_change_request_ingester.py` pass, including `Path`/`str` rejection with and without `source_bundle`/`tables` extras, public-method rejection with `validate_first` true and false, and the migrated bundle assertions. |
| `V-2` | Pass | `backend/tests/api/test_ingesters.py` and `test_ingester_infrastructure.py` pass: metadata `[]`, route `400` with the service not called, service rejection with project loading and config construction patched to fail, and unchanged `sead` behavior. |
| `V-3` | Collected, skipped | 13 tests collected and skipped because no disposable loopback database is configured. Both suites now call the private bundle methods. Skips are not database evidence. |
| `V-4` | Pass | `test_ingest_cli.py` and `test_route_authentication.py` pass (5 CLI tests skipped). |
| `V-5` | Pass | `tests/test_dispatch.py` and `tests/test_dispatch_timezone.py` pass. |
| `V-6` | Pass | `make check-doc-links` reports valid links; package README and diagrams no longer describe workbook ingestion. |
| `V-7` | Pass | Ruff, Black, isort, and `git diff --check` pass on all changed Python files. |
| `V-8` | Pass | `rtk uv run pytest backend/tests -q` completed with no failures. Database-dependent tests that require a disposable loopback database remain skipped. |
| `V-9` | Pass | `npm --prefix frontend run test -- --run --reporter=dot` reports 47 test files and 739 tests passed. |

### Route-Test Disposition

The obsolete workbook-driven route success assertions in `backend/tests/api/test_sead_change_request_project_scope.py` were removed. The module now covers missing and inaccessible top-level project authorization for both routes; the shared route tests in `backend/tests/api/test_ingesters.py` cover the retired-input `400` responses. The full backend suite passes with this disposition, so the prior `V-8` blocker is resolved.

## Deliverables

All targets below already exist; Phase 1 creates no new implementation file.

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Retired ingester input and preserved bundle core | `ingesters/sead_change_request/ingester.py`, `ingesters/sead_change_request/input_resolution.py` | `T1.1`, `T1.2` | Public file calls fail; private bundle-based results and artifacts retain their behavior. |
| Service and route rejection | `backend/app/services/ingester_service.py`, `backend/app/api/v1/endpoints/ingesters.py` | `T1.3` | Change Request key is stopped before service preparation; other keys retain their routes. |
| Focused and migrated tests | `backend/tests/api/test_ingesters.py`, `backend/tests/api/test_sead_change_request_project_scope.py`, `backend/tests/ingesters/test_ingester_infrastructure.py`, `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_inline_staging.py`, `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py` | `T1.4` | Rejection and preserved in-memory behavior have passing tests. |
| Package documentation | `ingesters/sead_change_request/README.md`, `ingesters/sead_change_request/DIAGRAMS.md` | `T1.5` | Documentation states the shipped input behavior and passes link checks. |
| Retired frontend submission guard | `frontend/src/components/ingester/IngesterForm.vue`, `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `T1.6` | Retired Change Request actions remain disabled and do not call the ingester store; other ingesters remain actionable. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Retire ingester file path | Complete | None | `supported_formats=[]`; public file methods and `Path`/`str` sources reject before extras; private `_validate_bundle()`/`_ingest_bundle()` keep the downstream flow. Verified by `V-1`. |
| Area 2: Reject service and route calls | Complete | Area 1 | Service returns the failed response shapes before project loading or config construction; both routes raise `400` before the broad handler; authorization dependencies unchanged. Verified by `V-2` and `V-4`. |
| Area 3: Move tests and docs | Done | Areas 1 and 2 | Planned tests migrated; obsolete route-success assertions removed; package README and diagrams updated; link check passes. |
| Area 4: Disable retired form submission | Done | Areas 1 and 2 | Project Dispatch form disables both actions and guards both handlers; `V-9` passes. |
| Phase 1 completion | Done | Areas 1–4 | Backend and frontend suites pass. Disposable database checks remain skipped where the required loopback database is unavailable. |

## Definition Of Done

- [x] `PH1-AC-1` and `PH1-AC-2` have the task and validation results mapped above.
- [x] `T1.1`–`T1.5` and every deliverable are complete; no active Change Request file entry point or advertised file format remains in the named deliverables.
- [x] `V-1`, `V-2`, `V-4`, `V-5`, `V-6`, `V-7`, `V-8`, and `V-9` pass. `V-3` is migrated and collected; skipped disposable database checks are reported and are not counted as database validation.
- [x] Rejected file calls do not load projects, resolve paths, call SIMS or the target database, or write bundles. Other ingesters and Excel dispatch pass regression checks.
- [x] Shared file models and the `Ingester` protocol remain unchanged; package documentation matches the Phase 1 state.
- [x] Obsolete route-success tests are replaced with project-authorization coverage, and the retired frontend form cannot submit the file request.

## Risks And Open Questions

- **Temporary generation gap:** File input closes before public table methods and project-only routes exist. This is an accepted source-proposal decision and must be visible in release notes or deployment communication when Phase 1 ships.
- **Disposable database tests:** The integration suites can skip without a configured loopback database. Their calls must be migrated in this phase, but Phase 1 acceptance rests on file-input rejection and unaffected-path regressions, not on skipped database assertions.
