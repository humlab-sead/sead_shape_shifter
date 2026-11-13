# Output Dataset Expectations: Phase 3 Task Plan

## Phase Summary

**Phase:** 3, Gate Dispatcher Execution And Report CLI Results. **Readiness:** Validated. **Goal:** Prevent dispatcher output when any complete-run expectation fails, and report every result in full execution responses and CLI runs.

Sources: [approved proposal](OUTPUT_DATASET_EXPECTATIONS.md) (`P-AC-3`, `P-AC-4`, `P-AC-5`); [phase plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_PLAN.md#phase-3-gate-dispatcher-execution-and-report-cli-results) (`PH3-AC-1`–`PH3-AC-3`, `VM-3`); [Phase 2 task plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_2_TASK_PLAN.md).

**Selected group-value contract:** Group keys are restricted to JSON scalar values: strings, booleans, finite numbers, and `null`.

**Resolved prerequisite:** Phase 1 declaration validation rejects non-JSON-scalar group keys before full runs. Focused tests accept strings, booleans, finite numbers, and `null`, and reject dates, timestamps, binary values, `NaN`, and infinities. The Phase 1 task plan and configuration guide record this contract. Phase 2 evaluates the validated group keys and carries each value into its result without coercion. The source phase plan marks Phase 3 ready; no upstream contract decision blocks this plan.

**Fixed constraints:** Keep Extract → Filter → Link → Unnest → Translate → Store; use only complete normalized, pre-translation tables and Phase 2's null-key/null-group rules. An expectation mismatch is an execution validation failure, not a declaration error or a failed optional pre-run validation. Phase 4 owns the separate project-table ingestion write gate. Preserve full-run behavior when no expectations are configured.

1. [x] `PH3-AC-1` (from `P-AC-4`): Full execution responses and CLI runs report every result on success and expectation failure without conflating expectation status with pre-run `validation_passed`.
2. [x] `PH3-AC-2` (from `P-AC-5`): A failed check makes full execution fail and prevents dispatcher output even with pre-run validation disabled; the CLI exits unsuccessfully.
3. [x] `PH3-AC-3` (from `P-AC-3`): Dispatcher runs use the complete pre-transformation table set, never sampled or preview output.

## Repository Findings

**Repository basis:** Branch `feature/output-dataset-expectations`, commit `1fb59d02`, planning date `2026-11-13`. The uncommitted Phase 1 and Phase 2 implementation, tests, and planning changes were read and tested as the current worktree; only this Phase 3 task plan is being updated. Graphify identified the execution entry points; the findings below were checked in source and tests.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/output_expectations.py::OutputExpectationEvaluation`, `OutputExpectationResult`; `src/workflow.py::normalize_project` | Phase 2 returns ordered results and `passed`; each result has name, entity, metric, group value, measured value, expected limit, status, and failure reason. `normalize_project(check_output_expectations=True)` evaluates after normalization and before optional FK removal and translation. | Reuse the Core result without remeasuring, querying sources, or changing result/null semantics. |
| `src/normalizer.py::ShapeShifter.normalize`, `ShapeShifter.incomplete_entities` | With configured expectations, normalization continues after entity errors, recording incomplete entities; Phase 2 evaluates missing expected entities explicitly. | Do not dispatch partial output when an *unconfigured* entity is incomplete even if all configured checks pass. Preserve a clear failure for that case. |
| `src/workflow.py::workflow`; `tests/test_workflow.py::TestWorkflowContract` | The workflow checks declarations, awaits normalization, then calls `store()` and `log_shapes()` before returning the evaluation. Existing tests assert normal file output and ordering; a passing evaluation is currently stored even if it failed. | Gate both write calls before the first dispatcher side effect; return a failed evaluation for the service and CLI to report. |
| `backend/app/services/execute_service.py::ExecuteService.execute_workflow`; `backend/app/models/execute.py::ExecuteResult` | The service runs optional pre-run validation, separately checks declarations when it is off, invokes `workflow()` but discards its return, and reports success unless execution raises. `ExecuteResult` has no expectation results. | Map the returned Core results to API models on both pass and mismatch; keep `validation_passed=True` after a successful optional check and `None` when it was disabled, even on an expectation mismatch. |
| `backend/app/api/v1/endpoints/execute.py::execute_workflow`; `frontend/src/api/execute.ts::ExecuteResult`, `frontend/src/stores/execute.ts::useExecuteStore` | The authenticated `POST /api/v1/projects/{name}/execute` returns the service result as its response model. The frontend keeps the typed result and handles `success=false`. | Extend the existing response contract and its typed consumer; no new route or frontend display flow is required. |
| `src/shapeshift.py::main`; `backend/tests/scripts/test_ingest_cli.py` | The Click CLI uses `asyncio.run(workflow(...))`, ignores its result, and always prints success after a normal return. Other CLI tests use `CliRunner`; no tests for this CLI were found. | Print all results, and exit nonzero instead of printing success when the evaluation fails. Add focused Click tests. |
| `docs/CONFIGURATION_GUIDE.md` | The output-expectations section still says Phase 1 only validates declarations. | Update only the now-shipped dispatcher/CLI behavior and state that ingestion gating remains Phase 4 work. |
| `src/specifications/output_expectations.py::OutputExpectationsSpecification.is_satisfied_by`, `src/output_expectations.py::evaluate_output_expectations`, `OutputExpectationResult` | Phase 1 accepts only strings, booleans, finite numbers, and `null` as group keys; tests reject dates, timestamps, bytes, `NaN`, and infinities. Phase 2 carries each configured group value into its result without coercion. | Reuse the validated scalar contract and verify API/CLI reporting preserves the accepted values. |

Baseline checks on this worktree:

```text
rtk .venv/bin/pytest tests/test_output_expectations.py tests/test_workflow.py tests/specifications/test_project.py backend/tests/services/test_project_ingester_service.py backend/tests/services/test_execute_service_expectations.py -q
Pass (exit code 0), rechecked 2026-11-13.

rtk .venv/bin/pytest tests/test_workflow.py backend/tests/services/test_execute_service_expectations.py backend/tests/services/test_execute_service_output_paths.py backend/tests/authorization/test_service_access.py -q --disable-warnings
Pass (exit code 0), rechecked 2026-11-13.

cd frontend && pnpm exec vue-tsc --noEmit
Pass (exit code 0), rechecked 2026-11-13.

rtk make check-doc-links
Pass (exit code 0), rechecked 2026-11-13.
```

These are existing-contract baselines, not evidence that the planned write gate, API response, or CLI reporting already works.

## Scope

**In scope:** Gate `src.workflow.workflow()` before `ShapeShifter.store()` and `log_shapes()`; return and map all expectation results on dispatcher pass/fail; preserve optional validation status; print results and fail the CLI on mismatch; synchronize the frontend response type and dispatcher/CLI documentation; test write prevention and response/CLI output.

**Out of scope:** Project-table ingestion gating and responses (Phase 4); changes to Phase 2 metrics or declaration rules; preview, sampling, materialization, partial-entity, or validation-only requests; new frontend UI; atomicity of downstream writes after passing checks.

## Work Breakdown

### Area 1: Gate The Dispatcher Before Output

**Objective:** A failed evaluation or an incomplete normalization cannot invoke a dispatcher or write a shape log.

**Affected code:** `src/workflow.py::workflow`, `src/normalizer.py::ShapeShifter.incomplete_entities` (read-only contract), `tests/test_workflow.py::TestWorkflowContract`.

**Dependencies:** Source phase-plan readiness decision and Phase 2 result contract.

**Tasks:**

- [x] `T3.1` **Change:** Withhold dispatcher output on failed expectations without losing any results.
  - **Target:** `src/workflow.py::workflow`; `tests/test_workflow.py::TestWorkflowContract`.
  - **Current → required:** `workflow()` stores and logs shapes before returning even when the evaluation has failures → check the completed evaluation before either write, return its full failed result for reporting, and write only when it passes or is absent.
  - **Implementation:** Use the existing `normalize_project(..., check_output_expectations=True)` path; inspect its `output_expectation_evaluation` once. For a failed evaluation, return it without calling `store()` or `log_shapes()`. If any entity is incomplete but all configured checks pass, fail the run explicitly before dispatch rather than silently writing partial output. Keep the existing declaration-error path, normal success return, dispatcher behavior, and no-expectation flow unchanged.
  - **Constraints:** Do not recalculate metrics from transformed tables or enable the check for other callers of `normalize_project()`. A file-target parent directory may be prepared by the service; the no-write assertion concerns dispatcher output and shape logs, not path preparation. No claim of atomic writes after checks pass.
  - **Validation:** `V-1`: Use completed in-memory fixed-entity data with two failing expectations and a passing grouped check; assert all results are retained while `store()` and `log_shapes()` are not called and no output is created. Repeat with translation/FK options, an expected incomplete entity, and an unrelated incomplete entity whose configured checks pass. Assert passing and no-expectation runs still write and log shapes.

**Completion evidence:** `V-1` proves a mismatch cannot call either writer and preserves the full Phase 2 result list.

### Area 2: Report Full-Execution Results Through The API

**Objective:** Full execution returns structured results on both pass and mismatch while reporting optional pre-run validation separately.

**Affected code:** `backend/app/models/execute.py::ExecuteResult`; `backend/app/mappers/output_expectation_mapper.py` **NEW**; `backend/app/services/execute_service.py::ExecuteService.execute_workflow`; `backend/app/api/v1/endpoints/execute.py::execute_workflow` (response contract and endpoint description); `frontend/src/api/execute.ts::ExecuteResult`; `backend/tests/services/test_execute_service_expectations.py`; `backend/tests/api/v1/test_execute.py` **NEW**.

**Dependencies:** Area 1.

**Tasks:**

- [x] `T3.2` **Change:** Add an API result model and explicit Core-to-API mapping for each check.
  - **Target:** `backend/app/models/execute.py::ExecuteResult` and an `OutputExpectationResult` API model; `backend/app/mappers/output_expectation_mapper.py` **NEW**; `frontend/src/api/execute.ts::ExecuteResult`.
  - **Current → required:** Responses and the frontend type have no expectation field → add `output_expectation_results` (an empty list for projects without expectations) containing name, entity, metric, `group_value`, `measured_value`, `expected_limit`, status, and `failure_reason`.
  - **Implementation:** Map Core dataclasses to Pydantic DTOs in the backend mapper. Keep `group_value: null` for an explicitly configured null group; distinguish it from a scalar result using `metric`. Preserve missing measurements as `null`, include comparison limits, and serialize every result in evaluation order. Mirror the response shape in the frontend API type; no UI behavior is added.
  - **Constraints:** Do not put domain comparisons in API DTOs or import API types in Core. Rely on Phase 1 declaration validation to reject non-JSON-scalar group values; map accepted scalar values without coercion.
  - **Validation:** `V-2`, `V-3`, `V-5`: Assert JSON fields and their types for passing, failing, absent/incomplete, and no-expectation results; verify grouped string, boolean, finite-number, and null values are preserved without coercion; type-check the frontend consumer.
- [x] `T3.3` **Change:** Return failed execution on a mismatch without changing optional-validation status.
  - **Target:** `backend/app/services/execute_service.py::ExecuteService.execute_workflow`; `backend/app/api/v1/endpoints/execute.py::execute_workflow`; `backend/tests/services/test_execute_service_expectations.py`; `backend/tests/api/v1/test_execute.py` **NEW**.
  - **Current → required:** The service ignores the workflow return and reports success → return `success=False` with all mapped results, no download path, and a clear execution-validation message when `passed=False`; continue returning results with `success=True` after passing checks.
  - **Implementation:** Capture the workflow return and map it once. Keep existing pre-run configuration failures separate; on a mismatch leave `validation_passed=True` if pre-run validation succeeded and `None` if it was disabled. Preserve the existing authorized-project check, target handling, and response-model route. Leave unexpected workflow/dispatcher errors on the existing explicit failure path rather than presenting them as expectation results.
  - **Constraints:** Do not return a downloadable target on expectation failure or claim a dispatch occurred; keep invalid declarations blocked before writes even when `run_validation=False`.
  - **Validation:** `V-2`, `V-3`: For both `run_validation` settings, assert success and multi-result mismatch shapes, status separation, no output/download on failure, and unchanged invalid-declaration and no-expectation behavior. Use the authenticated `authorized_client` fixture and create the route-test project through `POST /api/v1/projects` before requesting execution.

**Completion evidence:** `V-2` and `V-3` verify the service decision and serialized API response, including all grouped and failed results.

### Area 3: Report CLI Results And Document Dispatcher Behavior

**Objective:** The full-run CLI displays the same results and returns a failing exit status after a mismatch.

**Affected code:** `src/shapeshift.py::main`; `tests/test_shapeshift_cli.py` **NEW**; `docs/CONFIGURATION_GUIDE.md`.

**Dependencies:** Area 1.

**Tasks:**

- [x] `T3.4` **Change:** Print all check results and fail CLI execution on a mismatch.
  - **Target:** `src/shapeshift.py::main`; `tests/test_shapeshift_cli.py` **NEW**.
  - **Current → required:** The CLI discards the workflow return and prints a success message → show every returned check (including limits, measured value when available, null group, status, and failure reason), print no success message on failure, and exit nonzero after reporting all results.
  - **Implementation:** Capture the `asyncio.run(workflow(...))` result. Render its ordered results using Click output, including a distinct null group value when `metric=grouped_row_count`. If it failed, finish rendering and raise a Click failure; retain existing output and exit status when no expectations are configured.
  - **Constraints:** Keep `--validate-then-exit` as validation-only and do not evaluate full-output expectations there. Do not suppress unexpected workflow exceptions.
  - **Validation:** `V-4`: `CliRunner` tests with a temporary project and mocked workflow for pass, two failures plus a passing group, explicitly configured null group, and no expectations; assert output content, result count/order, exit code, and absence of false success. `V-1` supplies the real no-write check.
- [x] `T3.5` **Change:** Document the implemented full dispatcher and CLI behavior.
  - **Target:** `docs/CONFIGURATION_GUIDE.md` output-expectations section.
  - **Current → required:** The section says declarations are checked but counts are not measured → describe the completed dispatcher result/gate and CLI output/exit behavior, while explicitly deferring ingestion enforcement to Phase 4.
  - **Constraints:** Preserve the existing YAML examples and Phase 2 null/group semantics; do not describe the whole feature as enforced on both write paths yet.
  - **Validation:** `V-6`: Check documented claims against the implementation and run the existing documentation link check.

**Completion evidence:** `V-4` proves a mismatch is reported completely and exits unsuccessfully; `V-6` confirms documentation distinguishes shipped and deferred behavior.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
|---|---|---|---|
| `PH3-AC-1` (from `P-AC-4`) | `T3.2`, `T3.3`, `T3.4` | `V-2`, `V-3`, `V-4` | Every result, including each grouped/null group and failure reason, appears in API JSON and CLI output on pass and mismatch; `validation_passed` remains independent. |
| `PH3-AC-2` (from `P-AC-5`) | `T3.1`, `T3.3`, `T3.4` | `V-1`, `V-2`, `V-4` | Mismatches return failed execution with validation disabled, no dispatcher write or shape log, and nonzero CLI exit. |
| `PH3-AC-3` (from `P-AC-3`) | `T3.1` | `V-1` | The Phase 2 evaluator runs once after full normalization and before transformations; dispatcher gating uses those results, not previews or samples. |

All three criteria have supporting implementation and validation evidence; the `V-1`–`V-6` results are recorded below.

## Validation And Testing

Run commands from the repository root. `V-1`–`V-4` together cover phase milestone `VM-3`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Core gate and timing in `tests/test_workflow.py`; Phase 2 metric cases in `tests/test_output_expectations.py` | `rtk .venv/bin/pytest tests/test_workflow.py tests/test_output_expectations.py -q` | `PH3-AC-2`, `PH3-AC-3` | All configured results use complete pre-transformation output; two failures, incomplete expected/unexpected entities, and optional output transformations cause no write; passing/unconfigured runs still write. | **Pass** for existing Phase 2 evaluator tests, including `rtk .venv/bin/pytest tests/test_output_expectations.py tests/specifications/test_project.py -q`; new gate cases not yet written. |
| `V-2` | Service and authorization in `backend/tests/services/test_execute_service_expectations.py`, `backend/tests/services/test_execute_service_output_paths.py`, `backend/tests/authorization/test_service_access.py` | `rtk .venv/bin/pytest backend/tests/services/test_execute_service_expectations.py backend/tests/services/test_execute_service_output_paths.py backend/tests/authorization/test_service_access.py -q` | `PH3-AC-1`, `PH3-AC-2` | Enabled/disabled pre-run validation, success, multi-failure, declaration error, missing entity, and no-expectation results preserve authorization and output-path behavior. | **Pass** for existing tests in the second baseline command; new response cases not yet written. |
| `V-3` | Authenticated API response contract in `backend/tests/api/v1/test_execute.py` **NEW** | `rtk .venv/bin/pytest backend/tests/api/v1/test_execute.py -q` | `PH3-AC-1` | HTTP response serializes all fields, grouped `null`, no measurement for missing entities, and `validation_passed` independently on pass/fail. | Not run: test file does not exist. |
| `V-4` | Click output and exit status in `tests/test_shapeshift_cli.py` **NEW** | `rtk .venv/bin/pytest tests/test_shapeshift_cli.py -q` | `PH3-AC-1`, `PH3-AC-2` | All checks print before a nonzero exit; passing checks and no-expectation runs retain success; validation-only does not run output checks. | Not run: test file does not exist. |
| `V-5` | Backend typing/formatting and frontend response type | `rtk .venv/bin/pyright src/workflow.py src/shapeshift.py backend/app/models/execute.py backend/app/mappers/output_expectation_mapper.py backend/app/services/execute_service.py`<br>`rtk .venv/bin/ruff check src/workflow.py src/shapeshift.py backend/app/models/execute.py backend/app/mappers/output_expectation_mapper.py backend/app/services/execute_service.py tests/test_workflow.py tests/test_shapeshift_cli.py backend/tests/services/test_execute_service_expectations.py backend/tests/api/v1/test_execute.py`<br>`rtk .venv/bin/black --check src/workflow.py src/shapeshift.py backend/app/models/execute.py backend/app/mappers/output_expectation_mapper.py backend/app/services/execute_service.py tests/test_workflow.py tests/test_shapeshift_cli.py backend/tests/services/test_execute_service_expectations.py backend/tests/api/v1/test_execute.py`<br>`rtk .venv/bin/isort --check-only src/workflow.py src/shapeshift.py backend/app/models/execute.py backend/app/mappers/output_expectation_mapper.py backend/app/services/execute_service.py tests/test_workflow.py tests/test_shapeshift_cli.py backend/tests/services/test_execute_service_expectations.py backend/tests/api/v1/test_execute.py`<br>`cd frontend && pnpm exec vue-tsc --noEmit` | Type and quality checks | No new diagnostics; compare any repository-wide failures with the Phase 2 record rather than claiming they pass. | Partial baseline, 2026-11-13: frontend `vue-tsc` passed; Phase 3-specific targets do not exist yet. |
| `V-6` | Documentation link and behavior check in `docs/CONFIGURATION_GUIDE.md` | `rtk make check-doc-links` and inspect the section against `src/workflow.py`, `src/shapeshift.py`, and `backend/app/services/execute_service.py` | Documentation accuracy | Links resolve and the guide distinguishes dispatcher enforcement from deferred ingestion enforcement. | `make check-doc-links` passed 2026-11-13; behavior review awaits the planned documentation update. |

### Validation Evidence (2026-11-13)

Implemented `T3.1`–`T3.5` in the current worktree.

| ID | Command or method | Result | Notes |
|---|---|---|---|
| `V-1` | `.venv/bin/python -m pytest tests/test_workflow.py tests/test_output_expectations.py -q` | Pass | New gate cases cover two failures plus a passing grouped check, optional translation/FK removal, an incomplete expected entity, an unconfigured incomplete entity, and unchanged passing/no-expectation writes. |
| `V-2` | `.venv/bin/python -m pytest backend/tests/services/test_execute_service_expectations.py backend/tests/services/test_execute_service_output_paths.py backend/tests/authorization/test_service_access.py -q` | Pass | New cases cover enabled/disabled pre-run validation, multi-result mapping, scalar and null group preservation, and passing-result reporting. |
| `V-3` | `.venv/bin/python -m pytest backend/tests/api/v1/test_execute.py -q` | Pass | Authenticated route tests create the project through `POST /api/v1/projects`, update its options, and assert serialized pass/fail results, scalar and null group values, and independent `validation_passed`. |
| `V-4` | `.venv/bin/python -m pytest tests/test_shapeshift_cli.py -q` | Pass | Click tests cover pass, two failures plus a passing group, explicit null group, no expectations, and validation-only mode. |
| `V-5` | `uv run pyright <changed files>`; `.venv/bin/ruff check <changed files>`; `.venv/bin/black --check <changed files>`; `.venv/bin/isort --check-only <changed files>`; `cd frontend && pnpm exec vue-tsc --noEmit` | Pass | The plan's `.venv/bin/pyright` invocation cannot resolve installed third-party imports in this environment, so the equivalent `uv run pyright` command was used; it reported 0 errors. Ruff, Black, isort, and `vue-tsc` passed. |
| `V-6` | `make check-doc-links` | Pass | Links resolve. The guide now describes dispatcher measurement, the write gate, API results, and CLI output/exit, and defers ingestion enforcement to Phase 4. |

Combined focused and regression run (191 tests): `tests/test_workflow.py`, `tests/test_output_expectations.py`, `tests/test_shapeshift_cli.py`, `tests/specifications/test_project.py`, `backend/tests/services/test_execute_service_expectations.py`, `backend/tests/services/test_execute_service_output_paths.py`, `backend/tests/authorization/test_service_access.py`, `backend/tests/services/test_project_ingester_service.py`, and `backend/tests/api/v1/test_execute.py` passed.

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
|---|---|---|---|
| Pre-dispatch write gate | `src/workflow.py::workflow`, `tests/test_workflow.py` | `T3.1` | `V-1` proves no dispatcher or shape-log write on failure. |
| API result models and conversion | `backend/app/models/execute.py::ExecuteResult`, `backend/app/mappers/output_expectation_mapper.py` **NEW**, `frontend/src/api/execute.ts::ExecuteResult` | `T3.2` | `V-2`, `V-3`, `V-5` verify complete serialized results and typed consumer. |
| Service/API failure reporting | `backend/app/services/execute_service.py::ExecuteService.execute_workflow`, `backend/app/api/v1/endpoints/execute.py::execute_workflow`, `backend/tests/services/test_execute_service_expectations.py`, `backend/tests/api/v1/test_execute.py` **NEW** | `T3.3` | `V-2`, `V-3` verify pass/fail and separate validation status. |
| CLI result and exit reporting | `src/shapeshift.py::main`, `tests/test_shapeshift_cli.py` **NEW** | `T3.4` | `V-4` verifies all checks print before a failing exit. |
| Dispatcher/CLI user documentation | `docs/CONFIGURATION_GUIDE.md` | `T3.5` | `V-6` matches the implemented behavior. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Gate the dispatcher before output | Done | Phase 1 JSON-scalar declaration contract; Phase 2 evaluation contract | `T3.1`, `V-1` passed. |
| Area 2: Report full-execution results through the API | Done | Area 1 | `T3.2`, `T3.3`, `V-2`, `V-3`, `V-5` passed. |
| Area 3: Report CLI results and document dispatcher behavior | Done | Area 1 | `T3.4`, `T3.5`, `V-4`, `V-6` passed. |

## Definition Of Done

- [x] Source phase plan marks Phase 3 ready after accepting the verified Phase 2 result contract.
- [x] Phase 1 declaration validation rejects dates, timestamps, binary values, `NaN`, and infinities while accepting strings, booleans, finite numbers, and `null`; focused tests and the configuration guide confirm the contract.
- [x] `PH3-AC-1`–`PH3-AC-3` have implementation and passing `V-1`–`V-4` evidence.
- [x] Every configured result is returned on success/mismatch and printed by the CLI, including an explicit null group; optional pre-run validation status is not repurposed.
- [x] A failed expectation or incomplete normalization cannot write dispatcher output, including when optional validation is off; passing and no-expectation runs preserve normal dispatch.
- [x] API models, mapper, frontend type, CLI behavior, tests, and dispatcher-specific documentation agree; Phase 4 ingestion behavior remains deferred.
- [x] Relevant tests, typing, formatting, and documentation checks pass or existing failures are recorded without claiming a pass.
- [x] Deviations and follow-up work are documented; no unresolved decision affects implementation or validation.

## Risks And Open Questions

- **Partial normalization:** `continue_on_error=True` can leave an *unconfigured* entity incomplete while all configured checks pass. `workflow()` now raises an execution error before dispatch in that case, and `V-1` confirms no dispatcher or shape-log write.
Implementation handoff: if repository state or the Phase 2 result contract differs from these verified findings, stop and report the conflict with focused test results before changing the design or scope.
