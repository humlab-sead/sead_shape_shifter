# Output Dataset Expectations: Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Declare And Validate Expectations. **Readiness:** Validated. **Goal:** Validate `options.output_expectations` declarations before either full-run write path, independently of optional pre-run validation.

Sources: [approved proposal](OUTPUT_DATASET_EXPECTATIONS.md) (`P-AC-1`, `P-AC-2`); [phase plan](OUTPUT_DATASET_EXPECTATIONS_PHASE_PLAN.md), Phase 1 (`PH1-AC-1`, `PH1-AC-2`, `VM-1`). The approved proposal is the only phase dependency. This phase defines and checks declarations; it does not measure output or gate on measured values.

- [ ] `PH1-AC-1` (from `P-AC-1`): Valid declarations accept `row_count`, `distinct_key_count`, and `grouped_row_count` with `equals`, `min`, `max`, or an inclusive range.
- [ ] `PH1-AC-2` (from `P-AC-2`): Invalid entity, pre-translation grouping column, missing business keys, metric, or numeric limit declarations fail before either write, including when optional pre-run validation is disabled.

## Repository Findings

**Repository basis:** Branch `value-reference-column-ux-enhancement`, commit `4af1ca4a`, 2026-10-29. Uncommitted changes to the proposal, index, and phase plan were considered; none of those files is an implementation target.

| Source | Verified finding | Planning implication |
|---|---|---|
| `backend/app/models/project.py::Project.options`, `backend/app/mappers/project_mapper.py::ProjectMapper.to_core_dict`, `src/model.py::ShapeShiftProject.options` | Project options already pass as a dictionary through API-to-Core conversion. | Preserve this contract; no new API DTO field is needed for Phase 1. |
| `src/specifications/project.py::CompositeProjectSpecification`, `src/specifications/base.py::ProjectSpecification` | Composite validation collects Core structural issues from project-level specifications. | Add a dedicated Core specification and register it in the default composite. |
| `src/model.py::TableConfig.get_target_facing_columns`, `src/specifications/base.py::ProjectSpecification.get_entity_columns` | The target-facing helper accounts for surviving unnest columns and configured/generated target-facing columns; the broader helper can include unnest inputs that do not survive. | Use the target-facing contract for grouping-column declarations; reject columns not established from configuration instead of querying source data. |
| `backend/app/services/validation_service.py::ValidationService.validate_project`, `src/workflow.py::validate_project` | Both delegate to the composite specification. | Regular structural validation should report the same declaration issues; do not make all other project checks mandatory for every run. |
| `backend/app/services/execute_service.py::ExecuteService.execute_workflow` | Composite validation runs only when `request.run_validation` is true; target resolution precedes `workflow()`. | Check expectation declarations before target resolution and workflow even when that flag is false; preserve `validation_passed` semantics. |
| `src/workflow.py::workflow`, `src/shapeshift.py::main` | CLI execution calls `workflow()` directly; `--validate-then-exit` is optional. | Require declaration checks in the direct workflow path when expectations are present; leave normalization-only paths unchanged. |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService._load_validated_project` | The ingestion path runs the composite specification before normalization or `ingest_tables()`. | The new composite check covers this path without an extra ingestion validator. |
| `scripts/generate_schemas.py::SCHEMA_CONFIG`, `frontend/src/schemas/projectSchema.json` | Editor schema generation uses the API `Project` model, whose `options` is free-form. | No generated schema edit is planned; keep the existing schema check as a regression gate. |

## Scope

**In scope:** Define opt-in declaration rules; report Core structural issues with useful entity and field context; register the check in existing validation; require it before dispatcher/CLI and ingestion writes; document the YAML shape. Affected layers are Core specifications, full-run entry points, existing API-to-Core configuration flow, focused tests, and the configuration guide.

**Out of scope:** Count computation, complete-output results, runtime mismatch handling, response-model changes, output transformations, preview/sample/materialization validation, and altering existing authorization checks. Phase 2 owns metric semantics, including null values.

## Work Breakdown

### Area 1: Define And Register Declaration Validation

**Objective:** Invalid declarations become structural issues; valid or absent declarations do not change existing validation.

**Affected code:** `src/specifications/output_expectations.py` **NEW**, `src/specifications/project.py::CompositeProjectSpecification`, `src/model.py::TableConfig.get_target_facing_columns` (read-only contract), `tests/specifications/test_project.py`.

**Dependencies:** None.

**Tasks:**

- [ ] `T1.1` **Change:** Add a pure Core project specification for `options.output_expectations`.
  - **Target:** `src/specifications/output_expectations.py` **NEW**; use `ProjectSpecification` and `SpecificationIssue` conventions from `src/specifications/base.py`.
  - **Current -> required:** There is no expectation declaration check; absent expectations remain a no-op, while a present declaration must be a list of named, uniquely identifiable expectations referring to configured entities.
  - **Implementation:** Validate each item's shape, nonempty name, entity and metric; allow `row_count` and `distinct_key_count` with exactly one comparison mode (`equals`, `min`, `max`, or `min` plus `max`), and `grouped_row_count` with one configured column and a nonempty `groups` map whose values each use that comparison rule. Require nonnegative integer limits (not booleans), with `min <= max`; reject empty/malformed bounds, conflicting `equals` and range bounds, unsupported fields/metrics, missing keys for `distinct_key_count`, and groups/columns on incompatible metrics. Check group columns against the configured pre-translation output contract using `TableConfig.get_target_facing_columns`; fail when a column cannot be established without loading data. Accumulate issues with entity and `options.output_expectations` field context rather than raising or stopping at the first error.
  - **Constraints:** Do not read source data, resolve directives in Core, or validate measured counts. Keep optional projects unaffected.
  - **Validation:** `V-1` in `tests/specifications/test_project.py`: inline project dictionaries with valid exact/min/max/range and grouped declarations, and invalid entity, column (including an unnest input removed from output), key, metric, malformed shape, missing/conflicting bounds, boolean/negative/fractional limits, and reversed range; assert structural issues and no errors for absent expectations.
- [ ] `T1.2` **Change:** Include the new check in default structural validation.
  - **Target:** `src/specifications/project.py::CompositeProjectSpecification.get_default_specifications`; `tests/specifications/test_project.py::TestCompositeProjectSpecification`.
  - **Current -> required:** Existing composite checks do not inspect output expectations; the composite must include their errors without changing other specification behavior.
  - **Implementation:** Register the new specification with other project-level checks; keep the existing issue aggregation and reuse behavior.
  - **Constraints:** No backend imports in Core; preserve existing validators and their warning/error behavior.
  - **Validation:** `V-1` and `V-2`: invalid declaration fails the composite; valid or absent declarations and existing project checks retain their behavior.

**Completion evidence:** `V-1` exercises valid and invalid declarations through both the new specification and composite.

### Area 2: Enforce The Declaration Check On Full Writes

**Objective:** Optional pre-run validation cannot bypass declaration errors; CLI and ingestion also reject invalid declarations before writing.

**Affected code:** `backend/app/services/execute_service.py::ExecuteService.execute_workflow`, `src/workflow.py::workflow`, `backend/app/services/project_ingester_service.py::ProjectIngesterService._load_validated_project` (existing composite consumer), `tests/test_workflow.py`, `backend/tests/services/test_execute_service_expectations.py` **NEW**, `backend/tests/services/test_project_ingester_service.py`.

**Dependencies:** Area 1.

**Tasks:**

- [ ] `T2.1` **Change:** Make the declaration check mandatory at dispatcher entry while leaving other validation optional.
  - **Target:** `backend/app/services/execute_service.py::ExecuteService.execute_workflow`; `backend/tests/services/test_execute_service_expectations.py` **NEW**.
  - **Current -> required:** `run_validation=False` bypasses all composite checks; invalid expectations must instead return failure before output target resolution or `workflow()`.
  - **Implementation:** After authorized project loading and mapping, inspect expectation declarations through the shared Core check even if `run_validation=False`. When `run_validation=True`, preserve composite validation and avoid replacing its other checks. Return declaration errors in the existing failure response; leave `validation_passed` as `None` when optional validation was skipped. Do not start normalization or create output paths on invalid declarations.
  - **Constraints:** Preserve authorization and dispatcher-key guards and existing success/failure response shapes; measured expectation results are later-phase work.
  - **Validation:** `V-3`: stub project, target resolution, and workflow in the existing service style; assert invalid declarations fail for both flag values without target/workflow calls, and valid/absent declarations follow existing optional validation behavior.
- [ ] `T2.2` **Change:** Guard direct full workflow calls and cover ingestion through its existing composite check.
  - **Target:** `src/workflow.py::workflow`, `tests/test_workflow.py::TestWorkflowContract`, `backend/tests/services/test_project_ingester_service.py`.
  - **Current -> required:** CLI calls the workflow without mandatory validation; ingestion already runs composite validation before normalization. Both must reject invalid declarations before any output write.
  - **Implementation:** Validate declarations on the resolved project before workflow normalization/store, without making `normalize_project()` a full-run check. Add ingestion tests using a real composite through the existing mapper path rather than mocking the new check; verify failure before `normalize_project()`/`ingest_tables()`. Preserve validation-only, preview, and materialization behavior.
  - **Constraints:** Do not write output for a declaration failure; do not make full composite validation mandatory on CLI when no expectations are configured.
  - **Validation:** `V-3`: workflow tests assert invalid declarations raise and `store()` is not called, valid/absent projects still write; ingestion tests assert rejection precedes normalization and ingestion, while valid declarations proceed.

**Completion evidence:** `V-3` shows failures before either writer and no changes to optional pre-run validation status.

### Area 3: Document And Recheck The Contract

**Objective:** Project authors can write supported declarations and know which errors are reported before a full run.

**Affected documentation:** `docs/CONFIGURATION_GUIDE.md`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

- [ ] `T3.1` **Change:** Document `options.output_expectations` and the Phase 1 declaration rules.
  - **Target:** `docs/CONFIGURATION_GUIDE.md`, project options section.
  - **Current -> required:** The guide does not describe output expectations; it must show supported shapes, named groups, pre-translation grouping columns, valid comparisons, and errors for unsupported declarations.
  - **Implementation:** Add a concise YAML example and distinguish declaration validation from later runtime metric evaluation; do not claim count checks already exist at Phase 1 completion.
  - **Constraints:** Keep examples consistent with the approved proposal and the implemented declaration schema.
  - **Validation:** `V-4`: inspect the guide against `T1.1` cases and run the existing generated-schema check without editing generated JSON unless a real model change requires it.

**Completion evidence:** The guide matches the tested declaration contract, and schema generation remains in sync.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2`, `T3.1` | `V-1`, `V-2`, `V-4` | All three metric declarations and four comparison modes validate; absent expectations preserve existing behavior. |
| `PH1-AC-2` (from `P-AC-2`) | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`, `V-3` | Invalid declarations report structural issues and prevent full-run writes when optional validation is disabled. |

## Validation And Testing

All commands run from the repository root. `V-1` through `V-4` together provide the Phase 1 `VM-1` result; planned tests are not claimed as already passing.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | New specification and composite declarations in `tests/specifications/test_project.py`; valid exact/min/max/range and groups, invalid entity/column/key/metric/limits, no-op absence | `.venv/bin/pytest tests/specifications/test_project.py -q` | `PH1-AC-1`, `PH1-AC-2` | All structural cases pass, with issue context and no data loading. | Pass: existing file in focused baseline; new cases not run. |
| `V-2` | Existing specification and backend validation regression in `tests/specifications/test_project.py`, `backend/tests/services/test_validation_service.py` | `.venv/bin/pytest tests/specifications/test_project.py backend/tests/services/test_validation_service.py -q` | `PH1-AC-1`, existing structural behavior | No regression in composite and API-side validation. | Pass: both files ran in the two focused baselines; combined command not run. |
| `V-3` | Dispatcher flag on/off in `backend/tests/services/test_execute_service_expectations.py` **NEW**, direct CLI workflow in `tests/test_workflow.py`, ingestion in `backend/tests/services/test_project_ingester_service.py` | `.venv/bin/pytest backend/tests/services/test_execute_service_expectations.py tests/test_workflow.py backend/tests/services/test_project_ingester_service.py -q` | `PH1-AC-2`, write and authorization boundaries | Invalid declarations stop target creation, store, and ingestion; valid/absent declarations continue; `validation_passed` stays distinct. | Not run: new file and cases do not exist; both existing test files passed independently in focused baselines. |
| `V-4` | Generated editor schema and guide match implemented declarations | `make check-schemas` and review `docs/CONFIGURATION_GUIDE.md` against the `V-1` cases | `PH1-AC-1`, documentation/schema regression | Generated JSON remains synchronized, examples match validation rules. | Not run: check is for implementation handoff. |

Baseline commands already run: `.venv/bin/pytest tests/specifications/test_project.py backend/tests/services/test_project_ingester_service.py backend/tests/services/test_execute_service_output_paths.py -q` and `.venv/bin/pytest tests/test_workflow.py backend/tests/services/test_validation_service.py -q`; both passed on the recorded repository state.

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
|---|---|---|---|
| Declaration specification | `src/specifications/output_expectations.py` **NEW** | `T1.1` | `V-1` structural cases pass. |
| Composite registration | `src/specifications/project.py::CompositeProjectSpecification.get_default_specifications` | `T1.2` | `V-1`, `V-2` pass. |
| Mandatory full-run checks | `backend/app/services/execute_service.py::ExecuteService.execute_workflow`, `src/workflow.py::workflow` | `T2.1`, `T2.2` | `V-3` proves pre-write rejection. |
| Tests | `tests/specifications/test_project.py`, `backend/tests/services/test_execute_service_expectations.py` **NEW**, `tests/test_workflow.py`, `backend/tests/services/test_project_ingester_service.py` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1` through `V-3` pass. |
| Configuration guidance | `docs/CONFIGURATION_GUIDE.md` | `T3.1` | `V-4` guide review and schema check pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Declare and validate | Not started | Approved proposal | Existing structural tests pass. |
| Area 2: Enforce before writes | Not started | Area 1 | No measured results in this phase. |
| Area 3: Document and recheck | Not started | Areas 1 and 2 | No generated schema change expected. |

## Definition Of Done

- [ ] `PH1-AC-1` and `PH1-AC-2` have task and validation evidence (`T1.1`-`T3.1`, `V-1`-`V-4`; Phase 1 `VM-1`).
- [ ] All three areas and listed deliverables are complete; the plan's progress tracker and evidence are updated.
- [ ] Focused tests and schema synchronization check pass; invalid declarations cause no dispatcher, CLI, or ingester write.
- [ ] Existing authorized execution, optional validation status, and projects without expectations retain their behavior.
- [ ] The configuration guide matches the shipped Phase 1 contract; generated artifacts change only if the underlying model changes.
- [ ] Deviations and follow-up work are recorded, and no unresolved decision affects implementation or verification.

If repository behavior differs from these verified paths during implementation, stop and report the discrepancy with test results before changing the design or scope.