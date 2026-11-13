# Output Dataset Expectations: Phase 4 Task Plan

## Phase Summary

**Phase:** 4, Gate Project-Table Ingestion. **Readiness:** Validated. **Goal:** Report every complete-output expectation result from project-table ingestion and prevent ingester writes when any check fails.

Sources: [approved proposal](OUTPUT_DATASET_EXPECTATIONS.md) (`P-AC-3`, `P-AC-4`, `P-AC-5`); [phase plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_PLAN.md#phase-4-gate-project-table-ingestion) (`PH4-AC-1`–`PH4-AC-3`, `VM-4`); [Phase 2 task plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_2_TASK_PLAN.md); [Phase 3 task plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_3_TASK_PLAN.md).

**Resolved prerequisite:** The phase plan now marks Phase 4 ready and records Phase 3 dispatcher/CLI gating as delivered. Its dependencies are verified in the current worktree on 2026-11-13:

- `src/workflow.py::normalize_project` evaluates complete normalized tables before foreign-key removal and translation and records `ShapeShifter.output_expectation_evaluation`; Phase 2 result and null semantics are unchanged.
- `src/workflow.py::workflow` returns a failed evaluation before `store()` and `log_shapes()` and raises on incomplete output; only `workflow()` and `ProjectIngesterService.ingest_project_tables` pass `check_output_expectations=True`.
- `backend/app/mappers/output_expectation_mapper.py::OutputExpectationMapper.to_api_results`, `backend/app/models/execute.py::OutputExpectationResult`, and `backend/tests/api/v1/test_execute.py` provide the Phase 3 result mapper, API model, and passing route evidence.
- `.venv/bin/python -m pytest tests/test_output_expectations.py tests/test_workflow.py tests/test_shapeshift_cli.py backend/tests/services/test_execute_service_expectations.py backend/tests/api/v1/test_execute.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py -q` passed (159 tests, exit 0).

No upstream decision blocks this plan.

**Fixed constraints:** Use the Phase 2 evaluation of complete normalized tables before optional FK removal and column translation. Preserve configured JSON-scalar group values (strings, booleans, finite numbers, and `null`) and the null-key/null-group rules. Do not evaluate full-output expectations in project-table validation, previews, samples, materialization, or partial-entity requests. Preserve existing ingestion validation, reconciliation, and write behavior after checks pass; a passing check does not guarantee atomic downstream writes.

1. [x] `PH4-AC-1` (from `P-AC-4`): Project-table ingestion responses include every expectation result on success and expectation failure, including each configured group.
2. [x] `PH4-AC-2` (from `P-AC-5`): Any failed expectation prevents all project-table ingester writes for that run; absent or incomplete expected entities fail explicitly.
3. [x] `PH4-AC-3` (from `P-AC-3`): Ingestion measures complete output before translation or foreign-key removal; previews, samples, materialization, and partial-entity requests do not evaluate full-output expectations.

## Repository Findings

**Repository basis:** Branch `feature/output-dataset-expectations`, commit `1fb59d02`, planning date `2026-11-13`. Uncommitted Phase 1–3 code, tests, documentation, and phase-plan changes were considered as the current worktree. Graphify was used for navigation; the following findings were checked against current source and tests and re-verified after the phase-plan readiness update.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/workflow.py::normalize_project`, `src/output_expectations.py::evaluate_output_expectations` | With `check_output_expectations=True` and declarations present, full normalization collects incomplete entities, evaluates the pre-transformation table store once, and records an `OutputExpectationEvaluation` on `ShapeShifter`. FK removal and translation follow evaluation. With no declarations, normalization retains its prior behavior. | Consume the recorded evaluation; do not measure transformed tables, re-query sources, or duplicate metric logic. |
| `src/workflow.py::workflow`; `tests/test_workflow.py::TestWorkflowContract` | The dispatcher returns failed evaluation results before `store()` and `log_shapes()`, and refuses partial output if an unconfigured entity is incomplete. | Match its no-write and completeness rules without invoking the dispatcher from ingestion. |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables` | The method validates project declarations, calls `normalize_project(..., check_output_expectations=True)`, then proceeds to attach approvals and call `ingester.ingest_tables(..., validate_first=True)` without checking the recorded evaluation or incomplete entities. | Gate immediately after normalization and before any ingester write; preserve the existing downstream flow for a passing or unconfigured run. |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService.validate_project_tables`; `backend/app/models/ingester.py::ProjectIngesterRequest` | Validation-only normalization does not opt into expectations. `default_entity` is a source fallback used by `ShapeShifter`, not a target-entity selection; materialization uses its own `target_entities` path. | Do not mistake `default_entity` for a partial-entity request or add checks to validation-only and other excluded paths. |
| `backend/app/models/ingester.py::IngestResponse`; `backend/app/api/v1/endpoints/ingesters.py::ingest_project_ingester`; `backend/app/mappers/output_expectation_mapper.py::OutputExpectationMapper` | The project-only route serializes `IngestResponse`, which has no expectation-results field. The Phase 3 mapper already converts Core results to API models without coercing group values. Generic file ingestion uses the same response model. | Add a default-empty results field and reuse the mapper; leave endpoint authorization and generic file-ingester behavior intact. |
| `backend/tests/services/test_project_ingester_service.py::install_common_mocks`, `test_valid_output_expectation_reaches_project_ingestion`; `backend/tests/api/test_project_ingester_routes.py` | Existing tests verify declaration blocking and that valid expectations request evaluation, but not the evaluation gate. Some fake normalizers omit evaluation/incomplete-entity attributes; one uses a placeholder `object()` as an evaluation. Route tests exercise authenticated response serialization and authorization. | Update the fake ShapeShifter contract instead of hiding absent fields with service fallbacks; test both the service gate and the serialized API response. |
| `frontend/src/types/ingester.ts::IngestResponse`, `frontend/src/api/ingester.ts::ingesterApi.ingestProject`, `frontend/src/stores/ingester.ts::useIngesterStore` | The frontend types and stores the project ingestion response; its form currently shows the message and error details, not a per-check result list. | Keep the typed response in sync; no new UI presentation is required by this phase's API-response criteria. |
| `docs/CONFIGURATION_GUIDE.md` output-expectations section | The guide explicitly says project-table ingestion enforcement is deferred. | Replace that statement only when the ingestion gate and responses are verified. |

Baseline checks on this uncommitted worktree, 2026-11-13:

- **Pass:** `.venv/bin/python -m pytest tests/test_output_expectations.py tests/test_workflow.py tests/test_shapeshift_cli.py backend/tests/services/test_execute_service_expectations.py backend/tests/api/v1/test_execute.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py -q` (159 tests, exit 0). These prove the Phase 2/3 contracts but do **not** prove the planned ingestion write gate.
- **Pass:** `.venv/bin/python -m pytest backend/tests/api/test_ingesters.py -q` (16 tests, exit 0).
- **Pass:** `cd frontend && rtk pnpm exec vue-tsc --noEmit` (exit 0).
- **Pass:** `cd frontend && rtk pnpm exec vitest run src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts` (11 tests).

## Scope

**In scope:** The full project-table ingestion write gate, result mapping and response serialization on success and mismatch, failure on incomplete output, focused tests and regression checks, the ingestion response type, and the existing configuration guide.

**Out of scope:** Changes to the Phase 1 declaration or Phase 2 metric contracts, dispatcher/CLI changes, new frontend UI, file-ingester expectation enforcement, validation-only evaluation, previews/samples, entity materialization, partial-entity runs, and atomicity after checks pass.

## Work Breakdown

Work below is ready for implementation. If the worktree or upstream contract changes first, stop and report the conflict rather than silently redesigning this plan.

### Area 1: Gate Project-Table Writes

**Objective:** A failed expectation or incomplete full-run output cannot reach `ingester.ingest_tables()`.

**Affected code:** `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`, `ProjectIngesterService._ingestion_failure`; `backend/tests/services/test_project_ingester_service.py::install_common_mocks` and focused service tests.

**Dependencies:** The phase plan marks Phase 4 ready, and the Phase 2/3 contracts listed above are verified.

**Tasks:**

- [x] `T4.1` **Change:** Enforce the recorded evaluation before any project-table ingester work.
  - **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`; `backend/tests/services/test_project_ingester_service.py`.
  - **Current → required:** A failed `output_expectation_evaluation` is ignored and `ingester.ingest_tables()` runs → return an explicit failed ingestion response with every result, zero processed records, and no output path or deploy artifact, before attaching approvals or creating an ingester.
  - **Implementation:** After `normalize_project()`, inspect `shapeshifter.output_expectation_evaluation`; if present and not passed, map all results and return an execution-validation failure. If configured checks pass but any other entity is incomplete, refuse ingestion with an explicit entity/reason error and retain the available results. Keep early declaration errors and ordinary normalization errors on their existing paths. Only then attach approvals and call the existing `ingest_tables(..., validate_first=True)` flow. Do not suppress exceptions or fabricate a passing evaluation.
  - **Constraints:** No extra source queries; do not reuse post-transformation `table_store` for counts; no effect on `validate_project_tables()` or projects without expectations. Update fake normalizers to expose `output_expectation_evaluation=None` and `incomplete_entities={}` where appropriate, replacing the placeholder `object()` with a real evaluation.
  - **Validation:** `V-1`, `V-3`: With two failed expectations and another passing group, assert all results and zero ingester instances/calls, records, artifacts, and paths. Cover an absent expected entity, an incomplete expected entity, an incomplete unconfigured entity, passing checks, and no declarations.

**Completion evidence:** `V-1` proves a failed or incomplete full run never invokes an ingester, while passing and unconfigured runs retain the existing write path.

### Area 2: Report Results Through The Ingestion API

**Objective:** The authenticated project-only ingestion endpoint returns the complete, typed result list on success and expectation failure.

**Affected code:** `backend/app/models/ingester.py::IngestResponse`; `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`; `backend/app/mappers/output_expectation_mapper.py::OutputExpectationMapper` (reuse, no change planned); `backend/tests/api/test_project_ingester_routes.py`; `backend/tests/services/test_project_ingester_service.py`.

**Dependencies:** Area 1.

**Tasks:**

- [x] `T4.2` **Change:** Add expectation results to the project-ingestion response without duplicating conversion logic.
  - **Target:** `backend/app/models/ingester.py::IngestResponse`; `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`; `backend/tests/api/test_project_ingester_routes.py`.
  - **Current → required:** The shared response contains only ingestion metadata, even after a completed evaluation → expose `output_expectation_results` with the Phase 3 field shape, defaulting to `[]` for responses without an evaluation.
  - **Implementation:** Reuse `OutputExpectationMapper.to_api_results()` for both the mismatch response and the downstream `IngestResponse` returned after an evaluation passes, including downstream validation failures. Preserve result order, `group_value` types (including a configured `null`), `measured_value=null` and failure reason for missing/incomplete expected entities, and expected limits. Keep early configuration failures distinct from execution mismatches. Leave the existing route and authorization dependency in place.
  - **Constraints:** Do not add domain comparisons to Pydantic DTOs or Core imports of backend models. The shared `IngestResponse` also serves generic file routes; their result list must remain empty.
  - **Validation:** `V-1`, `V-2`: Assert all fields and types in authenticated HTTP JSON for passing, multi-failure, missing/incomplete, grouped string/boolean/number/null, and unconfigured runs; assert existing route authorization, rejection, and generic file responses remain unchanged apart from the empty default field.

**Completion evidence:** `V-2` shows all evaluated checks in project-only API responses on both success and mismatch without leaking results into other ingester modes.

### Area 3: Preserve Excluded Paths And Synchronize Documentation

**Objective:** Only full project-table ingestion evaluates expectations, and the typed consumer and guide describe the shipped response.

**Affected code:** `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py`, `frontend/src/types/ingester.ts::IngestResponse`, `frontend/src/api/__tests__/ingester.test.ts`, `frontend/src/stores/__tests__/ingester.test.ts`, `docs/CONFIGURATION_GUIDE.md`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

- [x] `T4.3` **Change:** Lock down evaluation timing and excluded request behavior.
  - **Target:** `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_project_ingester_routes.py`; existing `tests/test_workflow.py` and `tests/test_output_expectations.py` (regression only).
  - **Current → required:** Tests assert ingestion requests evaluation but do not assert gate timing or exclusions → prove evaluation is consumed from complete pre-translation output, including when both output transformations are requested; validate-only calls never opt in, and previews, materialization, and partial-entity paths remain outside the changed service.
  - **Implementation:** Use an in-memory fixed-entity project or a controlled normalizer with pre/post-transformation tables and a real Phase 2 evaluation; assert the ingester receives transformed tables only on pass, while the result uses original column names and counts. Assert `/from-project/validate` requests no evaluation, including when expectations exist. Keep other paths unchanged rather than adding expectation calls to them.
  - **Constraints:** `default_entity` is not a partial-entity selector. Do not infer exclusion by disabling evaluation for this field; do not require a live database or SIMS service for these tests.
  - **Validation:** `V-1`, `V-2`, `V-3`: Assert full-run pre-transformation count and no-write-on-failure, validation-only unchanged, and existing Core exclusions/regressions pass.
- [x] `T4.4` **Change:** Sync the typed response and document ingestion enforcement.
  - **Target:** `frontend/src/types/ingester.ts::IngestResponse`; `frontend/src/api/__tests__/ingester.test.ts`; `frontend/src/stores/__tests__/ingester.test.ts`; `docs/CONFIGURATION_GUIDE.md` output-expectations section.
  - **Current → required:** The frontend response type has no expectation results and the guide defers ingestion enforcement → type the result list with the Phase 3 field shape, verify the API/store preserve it, and explain ingestion's no-write failure and result reporting while retaining the exclusions.
  - **Implementation:** Keep `ingesterApi.ingestProject()` and store flow; no per-check UI is required. Describe pre-transformation measurement and distinct declaration versus execution failures in the existing guide section; remove only the outdated deferral.
  - **Constraints:** Preserve generic ingestion and validation response behavior. Do not change project YAML examples or claim downstream writes are atomic.
  - **Validation:** `V-4`, `V-5`: Frontend API/store tests preserve grouped results and failed responses; TypeScript type-check and documentation link check pass.

**Completion evidence:** `V-3`–`V-5` establish excluded-path behavior and synchronized API typing/documentation.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
|---|---|---|---|
| `PH4-AC-1` (from `P-AC-4`) | `T4.2`, `T4.4` | `V-1`, `V-2`, `V-4` | Every scalar and configured grouped result is serialized on success and expectation failure; accepted JSON-scalar group values are preserved. |
| `PH4-AC-2` (from `P-AC-5`) | `T4.1`, `T4.2` | `V-1`, `V-2` | Mismatches and absent/incomplete expected entities fail explicitly, without any ingester write, artifact, or output path. |
| `PH4-AC-3` (from `P-AC-3`) | `T4.1`, `T4.3` | `V-1`, `V-2`, `V-3` | Pre-translation complete tables supply metrics despite output options; validation-only and other excluded paths do not evaluate full-output expectations. |

## Validation And Testing

Run commands from the repository root unless a command changes directory. `V-1`–`V-3` together cover phase milestone `VM-4`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Service gate and complete-output cases in `backend/tests/services/test_project_ingester_service.py`; existing Core metric and dispatcher checks in `tests/test_output_expectations.py`, `tests/test_workflow.py` | `rtk .venv/bin/pytest backend/tests/services/test_project_ingester_service.py tests/test_output_expectations.py tests/test_workflow.py -q` | `PH4-AC-1`–`PH4-AC-3` | Failures retain every result and never invoke ingester writes; pass/unconfigured runs still ingest; full-run counts use original tables despite translation/FK removal. | Pass for existing tests in the combined baseline; planned gate cases not yet written. |
| `V-2` | Project-only HTTP serialization and authorization in `backend/tests/api/test_project_ingester_routes.py`; generic response regression in `backend/tests/api/test_ingesters.py` | `rtk .venv/bin/pytest backend/tests/api/test_project_ingester_routes.py backend/tests/api/test_ingesters.py -q` | `PH4-AC-1`–`PH4-AC-3` | Authenticated ingest JSON reports every check and failure; validation-only response has no expectation results; unauthorized and generic file requests retain existing behavior. | Pass for existing project-only and generic route tests; planned serialization cases not yet written. |
| `V-3` | Full-run isolation and dispatcher regression in `tests/test_workflow.py` and `backend/tests/services/test_execute_service_expectations.py`; validate-only path in `backend/tests/services/test_project_ingester_service.py` | `rtk .venv/bin/pytest tests/test_workflow.py backend/tests/services/test_execute_service_expectations.py backend/tests/services/test_project_ingester_service.py -q` | `PH4-AC-3`, existing behavior | Dispatcher still gates on the same evaluation; no expectations retain prior writes; validate-only does not evaluate. Verify preview/materialization/partial-entity code still does not opt into `check_output_expectations` by inspecting its callers in `backend/app/services/shapeshift_service.py`, `backend/app/services/materialization_service.py`, and `src/workflow.py`. | Pass for existing tests in the combined baseline; planned exclusion cases not yet written. |
| `V-4` | Frontend typed project-ingester response in `frontend/src/api/__tests__/ingester.test.ts` and `frontend/src/stores/__tests__/ingester.test.ts` | `cd frontend && rtk pnpm exec vitest run src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts`<br>`cd frontend && rtk pnpm exec vue-tsc --noEmit` | `PH4-AC-1`, consumer regression | Project result list survives API/store transfer on pass and mismatch; no type errors. | Pass: 11 tests and type-check; planned result cases not yet written. |
| `V-5` | Focused backend type, lint, formatting, frontend lint, and guide links | `rtk uv run pyright backend/app/models/ingester.py backend/app/services/project_ingester_service.py`<br>`rtk .venv/bin/ruff check backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py`<br>`rtk .venv/bin/black --check backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py`<br>`rtk .venv/bin/isort --check-only backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py`<br>`cd frontend && rtk pnpm exec eslint src/types/ingester.ts src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts`<br>`rtk make check-doc-links` | Quality and documentation | Changed code passes checks; guide links resolve and accurately describe tested behavior. | Not run: no Phase 4 implementation or documentation edits to validate yet. |

### Validation Evidence (2026-11-13)

Implemented `T4.1`–`T4.4` in the current worktree.

| ID | Command or method | Result | Notes |
|---|---|---|---|
| `V-1` | `.venv/bin/python -m pytest backend/tests/services/test_project_ingester_service.py tests/test_output_expectations.py tests/test_workflow.py -q` | Pass | 104 tests. New gate cases cover two failed checks plus a passing grouped check with preserved string/boolean group values, an absent expected entity with a null measurement, an incomplete unconfigured entity, passing checks with both output transformations requested, and projects without declarations. Failures retained every result with no `FakeTableIngester` instance. |
| `V-2` | `.venv/bin/python -m pytest backend/tests/api/test_project_ingester_routes.py backend/tests/api/test_ingesters.py -q` | Pass | 63 tests. New authenticated route tests assert the serialized result list on expectation failure (scalar, grouped boolean, configured null group, missing entity with null measurement) and that the validation-only response has no result field; authorization, rejection, and generic file-ingester responses are unchanged apart from the empty default list. |
| `V-3` | `.venv/bin/python -m pytest tests/test_workflow.py backend/tests/services/test_execute_service_expectations.py backend/tests/services/test_project_ingester_service.py -q` | Pass | 98 tests. Dispatcher gating and no-expectation writes are unchanged. `check_output_expectations=True` remains limited to `src/workflow.py::workflow` and `ProjectIngesterService.ingest_project_tables`; `backend/app/services/shapeshift_service.py` and `backend/app/services/materialization_service.py` have no such caller, and `validate_project_tables()` still omits the flag. |
| `V-4` | `cd frontend && pnpm exec vitest run src/api/__tests__/ingester.test.ts src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts`<br>`cd frontend && pnpm exec vue-tsc --noEmit` | Pass | 22 tests. API and store tests preserve grouped results and failed responses; type-check reports no diagnostics. |
| `V-5` | `uv run pyright backend/app/models/ingester.py backend/app/services/project_ingester_service.py`; `.venv/bin/ruff check`, `.venv/bin/black --check`, `.venv/bin/isort --check-only` on the changed backend files; `cd frontend && pnpm exec eslint` on the changed frontend files; `make check-doc-links` | Pass | Pyright reports 0 errors; Ruff, Black, isort, ESLint, and the link check pass. |

Combined focused and regression run: the eight focused backend files above passed (184 tests), and `backend/tests/api backend/tests/services` passed (1554 passed, 3 skipped).

## Deliverables

All implementation targets below already exist; no new implementation files are required by this plan.

| Deliverable | Target | Tasks | Completion evidence |
|---|---|---|---|
| Ingestion no-write gate and complete-result response | `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables` | `T4.1`, `T4.2` | `V-1`, `V-2` |
| Typed API response contract | `backend/app/models/ingester.py::IngestResponse` | `T4.2` | `V-2`, `V-5` |
| Service and route regression tests | `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py` | `T4.1`–`T4.3` | `V-1`–`V-3` |
| Typed frontend consumer tests | `frontend/src/types/ingester.ts`, `frontend/src/api/__tests__/ingester.test.ts`, `frontend/src/stores/__tests__/ingester.test.ts` | `T4.4` | `V-4`, `V-5` |
| Ingestion behavior documentation | `docs/CONFIGURATION_GUIDE.md` | `T4.4` | `V-5` and comparison with `V-1`/`V-2` |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Gate project-table writes | Done | Phase plan marks Phase 4 ready; Phase 2/3 contracts verified | `T4.1`, `V-1`, `V-3` passed. |
| Area 2: Report results through the ingestion API | Done | Area 1 | `T4.2`, `V-1`, `V-2` passed. |
| Area 3: Preserve excluded paths and synchronize documentation | Done | Areas 1 and 2 | `T4.3`, `T4.4`, `V-3`–`V-5` passed. |

## Definition Of Done

- [x] The source phase plan explicitly marks Phase 4 ready after confirming its dependencies.
- [x] `PH4-AC-1`–`PH4-AC-3` each have completed task and passing `V-1`–`V-4` evidence.
- [x] All areas and listed deliverables are complete; mismatch or incomplete output cannot reach `ingest_tables()`, and pass/no-expectation paths retain existing downstream behavior.
- [x] Required tests and quality checks pass, and the frontend contract and configuration guide match the API response.
- [x] Excluded request paths and authorization are regression-tested; downstream failures are not described as atomic.
- [x] Any deviation or follow-up work is documented and no unresolved question affects correctness or validation.

## Risks And Open Questions

- **Partial normalization:** With expectations configured, normalization may continue after an unrelated entity fails. A passing evaluation must not permit a partial project-table write; `T4.1` and `V-1` explicitly cover this case.
