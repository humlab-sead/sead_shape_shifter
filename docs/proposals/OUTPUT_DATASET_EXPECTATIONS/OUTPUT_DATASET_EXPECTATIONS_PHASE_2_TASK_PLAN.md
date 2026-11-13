# Output Dataset Expectations: Phase 2 Task Plan

## Phase Summary

**Phase:** 2, Measure Complete Normalized Output. **Readiness:** Validated. **Goal:** Calculate every configured output expectation from completed normalized tables before optional output transformations or writes.

Sources: [approved proposal](OUTPUT_DATASET_EXPECTATIONS.md) (`P-AC-3`, `P-AC-4`, `P-AC-5`); [phase plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_PLAN.md#phase-2-measure-complete-normalized-output) (`PH2-AC-1`, `PH2-AC-2`, `PH2-AC-3`, `VM-2`).

**Dependencies and fixed decisions**

- Use Phase 1's validated declaration contract. Do not duplicate its structural validation in the metric evaluator.
- Count only rows with non-null values in every configured business-key column for `distinct_key_count`.
- Evaluate null group values only when YAML `null` is explicitly configured. Report that value as a null `group_value`; do not report other unconfigured groups.
- Measure in-memory tables once. Do not issue source queries for metric values.
- Evaluate only full dispatcher and full project-table ingestion runs. Preview, materialization, and validation-only requests do not evaluate expectations.
- This phase produces results but does not add write gates or API/CLI reporting. Phases 3 and 4 own those changes.

1. [x] `PH2-AC-1` (from `P-AC-3`): Metrics use complete normalized tables and configured pre-translation names; foreign-key removal and column translation cannot change the measured values. `distinct_key_count` counts only rows whose configured key values are all non-null.
2. [x] `PH2-AC-2` (from `P-AC-5`): Every configured expectation and named group is evaluated, with an explicit failure and no measurement for an absent or incomplete expected entity. A configured null group is evaluated; unconfigured groups, including null, are not.
3. [x] `PH2-AC-3` (from `P-AC-4`): Each result includes the name, entity, metric, applicable group, measured value when available, expected limit, status, and failure reason when applicable; an explicitly configured null group is reported with a null group value.

## Repository Findings

**Repository basis:** Branch `feature/output-dataset-expectations`, commit `47b50814`, planning date `2026-11-12`. The uncommitted Phase 1 implementation and documentation changes were considered; they remain untouched. Baseline tests were run against the current worktree.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/specifications/output_expectations.py::OutputExpectationsSpecification`, `src/specifications/project.py::CompositeProjectSpecification` | The current Phase 1 changes validate declarations and register the specification; they do not measure table data. Group mappings are iterated without rejecting a null key. | Consume validated declarations and verify that an explicitly configured null group remains valid. Keep measurement separate from structural validation. |
| `src/workflow.py::normalize_project`, `src/workflow.py::workflow` | `normalize_project()` calls `ShapeShifter.normalize()`, then optionally drops foreign-key columns and translates column names. `workflow()` stores the returned tables and currently returns `None`. | Evaluate between normalization and those optional transformations. Return the internal evaluation result from `workflow()` for later dispatcher reporting. |
| `src/normalizer.py::ShapeShifter`, `src/normalizer.py::ShapeShifter.normalize`, `src/process_state.py::ProcessState` | `ShapeShifter` owns the `TableStore` and an `incomplete_entities` mapping. `normalize(continue_on_error=True)` records entity failures and continues processing other entities. | Pass incomplete reasons to the evaluator; do not treat an incomplete or absent entity as an empty table. Keep the existing fail-fast path when evaluation is not requested. |
| `src/model.py::TableConfig.safe_keys`, `src/model.py::TableConfig.get_key_columns` | `safe_keys` returns configured business-key columns. `get_key_columns()` also includes generated `system_id` and `public_id` columns. | Use `safe_keys` for `distinct_key_count`; generated identity columns are not business keys. |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService.validate_project_tables`, `ProjectIngesterService.ingest_project_tables` | Both methods call `src.workflow.normalize_project()`, but only ingestion is a full write path. | Enable evaluation only for `ingest_project_tables`; leave validation-only behavior unchanged. |
| `tests/test_workflow.py`, `tests/process/test_shapeshifter.py`, `backend/tests/services/test_project_ingester_service.py` | Existing tests cover transformation order, normalization behavior, continue-on-error, and project-table ingestion. | Extend these tests for measurement timing, result availability, incomplete entities, and the full-ingestion-only option. |

Baseline command run on the current worktree:

```text
rtk .venv/bin/pytest tests/test_workflow.py tests/process/test_shapeshifter.py tests/specifications/test_project.py backend/tests/services/test_project_ingester_service.py -q
```

Result: **Pass** (exit code 0). The new evaluator tests have not been run because their target file does not exist yet.

## Scope

**In scope**

- Add a pure Core evaluator and a typed result contract for row, distinct-key, and grouped row counts.
- Evaluate results from the complete in-memory tables before optional foreign-key removal or column translation.
- Make results available to the dispatcher workflow and full project-table ingestion path.
- Add focused metric, workflow, and ingestion tests, including the agreed null semantics.

**Out of scope**

- Preventing dispatcher or ingester writes after a failed expectation.
- Adding API response models, endpoint reporting, CLI output, or ingestion response fields.
- Changing configuration validation beyond verifying that a YAML `null` group is accepted.
- Evaluating previews, samples, materialization, or validation-only requests.
- Adding metrics, source queries, baselines, or arbitrary aggregates beyond the approved three.

## Work Breakdown

### Area 1: Add The Core Metric Evaluator

**Objective:** Return one structured result for each configured scalar expectation and each configured group.

**Affected code:** `src/output_expectations.py` **NEW**; `src/specifications/output_expectations.py::OutputExpectationsSpecification` (read-only contract).

**Dependencies:** Phase 1's declaration contract.

**Tasks:**

- [x] `T2.1` **Change:** Add the Core evaluation result types and metric evaluator.
  - **Target:** `src/output_expectations.py` **NEW**; `tests/test_output_expectations.py` **NEW**; `tests/specifications/test_project.py`.
  - **Current -> required:** Phase 1 validates expectation declarations, but no code measures them. Results must cover every configured check, including grouped checks, missing entities, and incomplete entities.
  - **Implementation:** Define an `OutputExpectationResult` with the expectation name, entity, metric, group value when applicable, measured value when available, expected limit, pass/fail status, and failure reason when applicable. Define an `OutputExpectationEvaluation` with the ordered results and an overall pass/fail value. Add a pure `evaluate_output_expectations()` function that accepts the Core project, completed tables, and incomplete-entity reasons.
    - Measure `row_count` with the number of rows, including rows with null values.
    - Measure `distinct_key_count` using `TableConfig.safe_keys`; exclude a row if any configured key value is null, then count unique key tuples.
    - For `grouped_row_count`, evaluate each configured group independently. Match an explicitly configured null group against null table values; return zero for any configured group absent from a present table. Do not return results for unconfigured values.
    - For an absent or incomplete expected entity, return a failed result for every configured check or group with no measured value and a missing-entity reason. If a required metric column is absent from a present table, return a failed result with no measured value and a reason rather than raising or reporting zero.
    - Apply `equals`, `min`, `max`, and inclusive `min`/`max` comparisons. Include a failure reason for each failed comparison and preserve the configured limit in its result.
  - **Constraints:** Use only the already normalized in-memory tables; do not load data, query sources, import backend models, or mutate the input tables. Use business keys from `safe_keys`, not generated identity columns. The metric distinguishes a scalar result from a grouped result whose `group_value` is null.
  - **Validation:** `V-1`: Test complete and empty tables, duplicate and null-containing key tuples, exact and inclusive bounds, present and absent groups, explicit and unconfigured null groups, missing and incomplete entities, missing metric columns, all result fields, and overall pass/fail. In `tests/specifications/test_project.py`, verify a grouped declaration with a null key passes the existing declaration specification.

**Completion evidence:** `V-1` verifies each metric and result shape, and no test requires source data access.

### Area 2: Measure Before Transformations On Full-Run Paths

**Objective:** Make the same evaluation available to dispatcher execution and full project-table ingestion without changing preview or validation-only behavior.

**Affected code:** `src/normalizer.py::ShapeShifter`, `src/workflow.py::normalize_project`, `src/workflow.py::workflow`, `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`, `tests/test_workflow.py`, `tests/process/test_shapeshifter.py`, `backend/tests/services/test_project_ingester_service.py`.

**Dependencies:** Area 1.

**Tasks:**

- [x] `T2.2` **Change:** Evaluate and retain results between normalization and optional output transformations.
  - **Target:** `src/normalizer.py::ShapeShifter`, `src/workflow.py::normalize_project`, `src/workflow.py::workflow`, `tests/test_workflow.py`, `tests/process/test_shapeshifter.py`.
  - **Current -> required:** `normalize_project()` currently normalizes, drops foreign-key columns, and then translates columns. `workflow()` currently stores the tables and returns `None`. The evaluation must use the completed pre-transformation tables and remain available to later phases.
  - **Implementation:** Add an optional `output_expectation_evaluation` result to `ShapeShifter`. Add an opt-in argument to `normalize_project()` and evaluate after `ShapeShifter.normalize()` but before `drop_foreign_key_columns()` or `translate()`. When evaluation is enabled and expectations are configured, use `normalize(continue_on_error=True)` so incomplete-entity reasons and results for other configured checks are available; keep the existing fail-fast behavior when evaluation is disabled or no expectations are configured. Have `workflow()` enable evaluation and return the evaluation after its existing store and shape-log calls; return `None` when no expectations are configured.
  - **Constraints:** Keep the existing pipeline order. Do not add a write gate or API/CLI reporting in this phase. Keep incomplete entities distinct from present empty tables so later phases can preserve the existing failure behavior and block writes.
  - **Validation:** `V-2`: Verify counts use pre-translation names and do not change when optional foreign-key removal or column translation is enabled. Verify all configured results are available before `store()`, incomplete expected entities have no measured value, projects without expectations retain the existing flow, and `normalize_project()` does not evaluate expectations unless explicitly requested.
- [x] `T2.3` **Change:** Enable evaluation only for full project-table ingestion.
  - **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`, `backend/tests/services/test_project_ingester_service.py`.
  - **Current -> required:** Both ingestion and validation-only methods call `normalize_project()`. Only the full ingestion path should request output expectation evaluation.
  - **Implementation:** Pass the evaluation option from `ingest_project_tables()` and leave `validate_project_tables()` unchanged. Keep results on the returned `ShapeShifter` for Phase 4; do not change ingestion response models or write behavior.
  - **Constraints:** Do not evaluate previews or validation-only requests. Do not duplicate the metric evaluator in the backend.
  - **Validation:** `V-2`: Assert the full ingestion path requests evaluation and can read its result before calling the ingester; assert the validation-only path does not request evaluation.

**Completion evidence:** `V-2` proves both full-run paths use the same pre-transformation evaluator and excluded request types do not evaluate expectations.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
|---|---|---|---|
| `PH2-AC-1` (from `P-AC-3`) | `T2.1`, `T2.2` | `V-1`, `V-2` | Counts use completed in-memory tables, business keys, and pre-translation columns; optional output transformations do not change results. |
| `PH2-AC-2` (from `P-AC-5`) | `T2.1`, `T2.2` | `V-1`, `V-2` | Every configured check and group has a result; absent or incomplete entities fail without a measured value; explicit null groups are checked. |
| `PH2-AC-3` (from `P-AC-4`) | `T2.1`, `T2.2`, `T2.3` | `V-1`, `V-2` | Results contain the required fields, including the configured limit and failure reason; both full-run paths retain the Core results. |

## Validation And Testing

Run commands from the repository root.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Metric calculations and result contract in `tests/test_output_expectations.py` **NEW**; null group declaration in `tests/specifications/test_project.py` | `rtk .venv/bin/pytest tests/test_output_expectations.py tests/specifications/test_project.py -q` | `PH2-AC-1`, `PH2-AC-2`, `PH2-AC-3` | All metrics, null rules, missing/incomplete cases, limits, and result fields pass. | Pass, rechecked 2026-11-13 in the combined Phase 1/2 focused test run. |
| `V-2` | Workflow timing and regression in `tests/test_workflow.py`, `tests/process/test_shapeshifter.py`, and `backend/tests/services/test_project_ingester_service.py` | `rtk .venv/bin/pytest tests/test_workflow.py tests/process/test_shapeshifter.py tests/specifications/test_project.py backend/tests/services/test_project_ingester_service.py -q` | `PH2-AC-1`, `PH2-AC-2`, `PH2-AC-3`, existing normalization and validation-only behavior | All checks pass; measurement precedes optional transformations, and only full-run paths request evaluation. | Pass, rechecked 2026-11-13 in the combined Phase 1/2 focused test run. |
| `V-3` | Repository type check | `rtk make pyright` | Python type safety | No new type errors. | Pass, rechecked 2026-11-13; 0 errors, 0 warnings, 0 informations. |
| `V-4` | Lint and formatting checks for changed Python files | `rtk uv run ruff check --output-format concise src/output_expectations.py src/normalizer.py src/workflow.py backend/app/services/project_ingester_service.py tests/test_output_expectations.py tests/specifications/test_project.py tests/test_workflow.py tests/process/test_shapeshifter.py backend/tests/services/test_project_ingester_service.py`<br>`rtk uv run pylint -j 0 src/output_expectations.py src/normalizer.py src/workflow.py backend/app/services/project_ingester_service.py tests/test_output_expectations.py tests/specifications/test_project.py tests/test_workflow.py tests/process/test_shapeshifter.py backend/tests/services/test_project_ingester_service.py`<br>`rtk uv run black --check src/output_expectations.py src/normalizer.py src/workflow.py backend/app/services/project_ingester_service.py tests/test_output_expectations.py tests/specifications/test_project.py tests/test_workflow.py tests/process/test_shapeshifter.py backend/tests/services/test_project_ingester_service.py`<br>`rtk uv run isort --check-only src/output_expectations.py src/normalizer.py src/workflow.py backend/app/services/project_ingester_service.py tests/test_output_expectations.py tests/specifications/test_project.py tests/test_workflow.py tests/process/test_shapeshifter.py backend/tests/services/test_project_ingester_service.py` | Python lint and formatting | No lint or formatting errors. | Pass, rechecked 2026-11-13; Ruff, full planned Pylint, Black, and isort all pass. |

`V-1` and `V-2` together cover phase milestone `VM-2`. Do not treat the later dispatcher and ingestion write gates as Phase 2 validation; those belong to Phases 3 and 4.

**Execution record (2026-11-12)**

- `V-1`: Passed. A first rerun caught an incorrect expected-limit assertion in the new grouped-count test; the expected value was corrected and the full command passed.
- `V-2`: Passed. The first run exposed existing ingestion test doubles that did not accept the new opt-in keyword. The test doubles were updated, and the full command passed.
- `V-3`: `rtk make pyright` failed on repository-wide diagnostics in existing backend test files, including the uncommitted Phase 1 `backend/tests/services/test_execute_service_expectations.py`. The targeted Pyright command on the Phase 2 source and test files passed; `tests/specifications/test_project.py` was excluded from that targeted run because it has pre-existing Phase 1 type diagnostics.
- `V-4`: Ruff, Black, and isort passed. The full Pylint command reported two `C1803` warnings in pre-existing Phase 1 assertions in `tests/specifications/test_project.py`; Pylint passed on the Phase 2 files when that file was excluded.

**Reassessment (2026-11-13, 16:05 CET)**

- Focused Phase 1 and 2 regression tests passed (240 tests):
  `rtk uv run pytest -n 0 tests/test_output_expectations.py tests/specifications/test_project.py tests/test_workflow.py tests/process/test_shapeshifter.py backend/tests/services/test_project_ingester_service.py backend/tests/services/test_validation_service.py backend/tests/services/test_execute_service_expectations.py -q`.
- Repository-wide `rtk make pyright` and the targeted Phase 2 Pyright check both passed with zero errors, warnings, or informations.
- Ruff, full planned Pylint (including `tests/specifications/test_project.py`), Black, and isort all passed. The previous repository-wide Pyright diagnostics and Pylint `C1803` warnings no longer reproduce.

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
|---|---|---|---|
| Core expectation evaluator and result types | `src/output_expectations.py` **NEW** | `T2.1` | `V-1` covers all three metrics and result cases. |
| Result storage and dispatcher workflow return | `src/normalizer.py::ShapeShifter`, `src/workflow.py::normalize_project`, `src/workflow.py::workflow` | `T2.2` | `V-2` verifies timing, availability, and unchanged no-expectation behavior. |
| Full-ingestion evaluation request | `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables` | `T2.3` | `V-2` verifies evaluation is enabled only for full ingestion. |
| Focused tests | `tests/test_output_expectations.py` **NEW**, `tests/specifications/test_project.py`, `tests/test_workflow.py`, `tests/process/test_shapeshifter.py`, `backend/tests/services/test_project_ingester_service.py` | `T2.1`–`T2.3` | `V-1` and `V-2` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Add the Core metric evaluator | Done | Phase 1 declaration contract | `T2.1`, `V-1` passed. |
| Area 2: Measure before transformations on full-run paths | Done | Area 1 | `T2.2`, `T2.3`, `V-2` passed. |

## Definition Of Done

- [x] `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3` have implementation and validation evidence.
- [x] Every configured expectation and group produces a result, including missing and incomplete entities.
- [x] Null key and null group rules match the Phase 2 decision in the phase plan.
- [x] Dispatcher and full-ingestion results are measured before optional transformations; validation-only and preview paths remain unchanged.
- [x] Focused Phase 2 tests, type checking, linting, and formatting checks pass. The focused tests, repository-wide and targeted Pyright, Ruff, full planned Pylint, Black, and isort all passed on 2026-11-13 (see the reassessment above).
- [x] Repository-wide `make pyright` and the full listed Pylint check pass; prior diagnostics are resolved.
- [x] The evaluation result remains a Core contract; no API DTO or backend domain logic is added.
- [x] Write gating and external result reporting remain assigned to Phases 3 and 4.
- [x] Incomplete-entity state is preserved for later write gates and is not converted into an empty-table measurement.

## Risks And Open Questions

- Evaluation-enabled normalization must continue far enough to report every configured check after an entity becomes incomplete. Keep the incomplete-entity reasons available to the result and to the later write gates. Do not let the no-write behavior in Phases 3 and 4 treat a partial table set as a complete run.
- This phase does not prevent writes when an expectation fails. Do not describe the feature as fully enforced until the dispatcher and ingestion gates from Phases 3 and 4 are complete.
- The Phase 1 declaration validator accepts an explicitly configured null group; `tests/specifications/test_project.py::TestOutputExpectationsSpecification.test_accepts_null_group_value` verifies this contract.

If current source behavior conflicts with these verified findings, stop and report the discrepancy with test results before changing the scope or design.
