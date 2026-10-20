# Phase 2 Task Plan: Share Normalization Without Writing Output

## Phase Summary

**Goal:** Add one Core operation that returns completed normalized tables with the same options as the file-writing `workflow()`.

**Readiness: Validated.** [Phase 2 of the phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) is ready for a task plan. The [Phase 1 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_1_TASK_PLAN.md) records completion, current file-input rejection checks pass, and no further design decision is recorded. The verified targets and validation methods below are ready for implementation.

**Source:** [In-memory handoff proposal](./IN_MEMORY_INGESTER_HANDOFF.md), `P-AC-1`; [Phase 2 of the phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md), `PH2-AC-1` and `PH2-AC-2`.

**Constraints and dependencies:** Keep the Core pipeline order and the current order of `drop_foreign_keys` followed by `translate`. The new operation takes no output target or dispatcher. `workflow()` keeps its signature, `None` return, file output, and shape log. Do not add a `memory` dispatcher or import backend or ingester code into Core. Phase 1 retirement precedes this work.

**Acceptance criteria**

1. `PH2-AC-1` (from `P-AC-1`): The new step applies `drop_foreign_keys` and `translate` in the current order and returns completed tables without invoking a dispatcher or requiring an output target.
2. `PH2-AC-2` (from `P-AC-1`): Existing `workflow()` calls keep their file output, shape logging, signature, and `None` return value.

## Repository Findings

**Repository basis:** Branch `in-memory-ingester-handoff`, commit `1ecd31b5`, planning date 2026-10-19. `git status --short` was clean. Graphify identified the workflow and its callers; the findings below were checked in current source and tests. The source proposal's description of active Change Request workbook input is historical: Phase 1 has retired it in this checkout.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `src/workflow.py::resolve_config`, `workflow` | `workflow()` resolves a `ShapeShiftProject` or file path, constructs `ShapeShifter` with `default_entity`, awaits `normalize()`, then optionally drops FK columns and translates using `project.options["translation"]`. It calls `store(target, mode)` and `log_shapes(target)`, then implicitly returns `None`. | Extract project resolution, normalization, and both options into one async function in this file. Leave store and shape logging in `workflow()` in their current order. |
| `src/normalizer.py::ShapeShifter.normalize`, `drop_foreign_key_columns`, `translate`, `store`, `log_shapes` | `normalize()` returns `self`; completed DataFrames are held in `table_store`. `store()` selects a registered dispatcher; `log_shapes()` writes `table_shapes.tsv` beside the target. | Return the completed `ShapeShifter`; do not change the normalizer or invent a dispatcher. Test the no-write call for absence of both store and shape logging. |
| `src/transforms/translate.py::extract_translation_map` | Translation rows use `arbodat_field` and `english_column_name`; missing or empty metadata yields an empty map. | Reuse the exact current option logic. Include translation enabled with populated and empty metadata in tests. |
| `backend/app/services/execute_service.py::ExecuteService.execute_workflow`, `src/shapeshift.py::main` | Backend execution and CLI call `workflow()` with its existing target, mode, option, and project arguments. | Preserve the full public signature and output behavior; neither caller needs a Phase 2 change. |
| `backend/tests/data_providers/arbodat/test_workflow.py::test_workflow_does_not_use_legacy_project_mappings`, `tests/process/test_shapeshifter.py::test_log_shapes_writes_tsv`, `tests/test_dispatch.py`, `tests/test_dispatch_timezone.py` | Existing checks cover a mocked workflow call, the shape-log file, and dispatcher behavior. The provider test has a module-scoped JVM fixture. | Keep these as regressions. Add focused Core tests with an inline project and no external source rather than depending on provider files. |
| `ingesters/sead_change_request/ingester.py::get_metadata`, `validate`, `ingest`; `ingesters/sead_change_request/input_resolution.py::_resolve_source_bundle` | Metadata has no file formats; public file methods reject input, and path sources raise `SourceBundleError`. Focused API and resolver baselines pass. | Phase 1 retirement is present in code. Phase 2 does not reopen any file input. |

## Scope

**In scope**

- One reusable async normalization function in `src/workflow.py` that accepts the existing project and normalization options without `target` or `target_type`, and returns `ShapeShifter` with its `table_store` populated.
- Refactor `workflow()` to call that function, then perform its existing `store()` and `log_shapes()` calls.
- Core tests for option order, table parity before dispatch, no output writes, and preserved workflow output and return value.

**Out of scope**

- Table-input ingester methods, backend composition, project-only routes, and operator client changes; Phases 3–5 own them.
- Changes to `ShapeShifter`, dispatchers, the backend execute service, CLI, shared ingester requests, or Change Request file retirement.
- A workbook readback parity requirement; compare normalized DataFrames before dispatch because Excel conversions are documented as intentional differences.

## Work Breakdown

### Area 1: Extract the reusable Core normalization step

**Objective:** Both no-write callers and `workflow()` use one sequence for project resolution, normalization, FK dropping, and translation.

**Affected code:** `src/workflow.py::resolve_config`, `workflow`; proposed `normalize_project` function in the same existing file.

**Dependencies:** Phase 1 retirement is complete; no remaining upstream block.

**Tasks:**

* [x] `T2.1` **Extract:** Add `async normalize_project(project: str | ShapeShiftProject, translate: bool, drop_foreign_keys: bool, default_entity: str | None = None, env_file: str | None = None) -> ShapeShifter` in `src/workflow.py`.
  * **Target:** `src/workflow.py::normalize_project` (NEW symbol), `workflow`, `resolve_config`.
  * **Current → required:** Only `workflow()` applies the options, and it always writes output. A caller needs the same completed tables with no output target.
  * **Implementation:** Call existing `resolve_config(project, env_file)`, construct `ShapeShifter(project=resolved_project, default_entity=default_entity)`, await `normalize()`, call `drop_foreign_key_columns()` when requested, then derive the translation map from `resolved_project.options.get("translation") or []` and call `translate()` when requested. Return that same `ShapeShifter` instance. In `workflow()`, await `normalize_project()` with its existing arguments, then call `store(target=target, mode=target_type)` and `log_shapes(target=target)` in the existing order. Keep the `workflow()` parameter list and `-> None` annotation.
  * **Constraints:** No target or dispatcher argument on `normalize_project`; no `store()` or `log_shapes()` call there. Keep source reads allowed by configured loaders and preserve current errors from `resolve_config()` and `normalize()`. Do not duplicate option logic or change the Core pipeline order.
  * **Validation:** `V-1`, `V-2`, `V-3` — option calls and results match the existing sequence; no-write calls produce no output; existing workflow output remains.

**Completion evidence:** `normalize_project()` returns a populated `ShapeShifter`, and `workflow()` delegates normalization to it before writing and logging.

### Area 2: Test table parity and preserve the file workflow

**Objective:** Tests show the no-write result and the tables passed to dispatch are equal for representative option combinations, while file output and shape logging continue.

**Affected tests:** `tests/test_workflow.py` (NEW); existing regression targets named under Validation And Testing.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.2` **Test:** Add no-write and option-order coverage.
  * **Target:** `tests/test_workflow.py` (NEW).
  * **Current → required:** There is no focused test for a no-write workflow result or the exact post-normalization option order.
  * **Implementation:** Use `@pytest.mark.asyncio` and an inline `ShapeShiftProject` with fixed entities and a translation row using `arbodat_field` / `english_column_name`. Test all four `drop_foreign_keys` × `translate` combinations. Compare entity names and DataFrames from `normalize_project()` with deep copies of tables captured at `ShapeShifter.store()` when the same project is run through `workflow()`; use `pd.testing.assert_frame_equal` so dtypes and values are checked. Include an FK column affected by dropping and a separate translated column so each option produces an observable change. In a separate mocked case, assert `normalize()` completes before FK dropping, FK dropping precedes translation when both are enabled, `default_entity` is forwarded, the same `ShapeShifter` is returned, and neither `store()` nor `log_shapes()` is called. Cover translation enabled with no translation rows and `resolve_config()` failure for an invalid project input.
  * **Constraints:** Use inline Core data, no backend import, provider database, workbook readback, or real output target for the no-write call. Do not mock away the actual table comparison.
  * **Validation:** `V-1`, `V-2` — every option combination returns expected tables without output files and matches the pre-dispatch tables.
* [x] `T2.3` **Test:** Confirm the old workflow contract after delegation.
  * **Target:** `tests/test_workflow.py` (NEW).
  * **Current → required:** Existing tests establish dispatcher and shape-log behavior separately; the refactored `workflow()` must still call both and return `None`.
  * **Implementation:** With a temporary CSV target and the inline project, assert `workflow()` returns `None`, writes the expected table file(s), and writes `table_shapes.tsv` in the target directory with counts matching the dispatched tables. Capture `ShapeShifter.store()` and `log_shapes()` order in a focused mocked case. Retain existing provider, execute-service, and dispatcher tests as regressions.
  * **Constraints:** Keep `workflow()` callable with the current keyword arguments and preserve errors and output naming. Do not alter dispatcher implementation.
  * **Validation:** `V-2`, `V-3` — result is `None`, file and shape log exist, and current callers and dispatch tests pass.

**Completion evidence:** Focused Core tests pass for both paths; existing backend and dispatcher regressions pass without caller changes.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-1`) | `T2.1`, `T2.2` | `V-1`, `V-2` | No-write call returns the same completed tables that workflow sends to dispatch for all option combinations; it never stores or logs shapes. |
| `PH2-AC-2` (from `P-AC-1`) | `T2.1`, `T2.3` | `V-2`, `V-3` | The existing workflow signature and `None` return remain; CSV output, shape log, backend caller, CLI call shape, and dispatch tests remain valid. |

`VM-2.1` is checked by `V-1` and `V-2`; `VM-2.2` is checked by `V-2` and `V-3`.

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result after implementation | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | No-write result and option order in `tests/test_workflow.py` (NEW) | `rtk uv run pytest tests/test_workflow.py -q` | `PH2-AC-1` | Four option combinations, no-write guard, default entity, empty translation, and invalid project tests pass. | Pass 2026-10-19: 15 tests pass. |
| `V-2` | Pre-dispatch table parity and real CSV workflow in `tests/test_workflow.py` (NEW) | `rtk uv run pytest tests/test_workflow.py -q` | `PH2-AC-1`, `PH2-AC-2` | DataFrames match before dispatch; workflow returns `None` and writes table files plus `table_shapes.tsv`. | Pass 2026-10-19: same run as `V-1`. |
| `V-3` | Existing provider workflow, shape log, backend service access, and dispatcher regressions | `rtk uv run pytest backend/tests/data_providers/arbodat/test_workflow.py::test_workflow_does_not_use_legacy_project_mappings tests/process/test_shapeshifter.py::TestShapeShifter::test_log_shapes_writes_tsv backend/tests/authorization/test_service_access.py tests/test_dispatch.py tests/test_dispatch_timezone.py -q` | `PH2-AC-2`, preserved behavior | All pass with no changed backend or CLI call; dispatcher output and shape logging remain. | Pass 2026-10-19: 56 tests pass after the refactor, with no caller changes. |
| `V-4` | Formatting, imports, and whitespace for changed files | `rtk uv run ruff check src/workflow.py tests/test_workflow.py`; `rtk uv run black --check src/workflow.py tests/test_workflow.py`; `rtk uv run isort --check-only src/workflow.py tests/test_workflow.py`; `rtk git diff --check` | Changed code and tests | All checks pass. | Pass 2026-10-19: all four checks pass after applying black/isort to the new test file. |
| `V-5` | Confirm Phase 1 retirement stays in place | `rtk uv run pytest backend/tests/api/test_ingesters.py backend/tests/ingesters/test_sead_change_request_input_resolution.py -q` | Phase dependency and regression | Retired Change Request file input remains rejected. | Pass 2026-10-19: 47 tests pass. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared Core normalization and preserved file workflow | `src/workflow.py::normalize_project` (NEW symbol), `workflow` | `T2.1` | One option sequence; no-write result available; existing workflow stores and logs. |
| Focused Core contract and parity tests | `tests/test_workflow.py` (NEW) | `T2.2`, `T2.3` | `V-1` and `V-2` pass for option combinations, output absence, table parity, and file output. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Extract the reusable Core normalization step | Done | Phase 1 retirement (complete) | `normalize_project` added; `workflow()` delegates before store and shape logging. |
| Area 2: Test table parity and preserve the file workflow | Done | Area 1 | `tests/test_workflow.py` added; 15 tests pass (V-1, V-2). |

## Definition Of Done

- [x] Phase plan marks Phase 2 ready after accepting the completed Phase 1 retirement.
- [x] `PH2-AC-1` and `PH2-AC-2` have passing task and validation results as mapped above.
- [x] `T2.1`–`T2.3` and both deliverables are complete; no-write callers receive completed tables without output files.
- [x] `V-1`–`V-5` pass, with any environment-dependent provider-test result recorded accurately.
- [x] Existing workflow output, shape logging, signature, and `None` return are unchanged; file-only ingester and Excel dispatch behavior remains tested.
- [x] No backend, ingester, dispatcher, or shared API contract changes are included. Any deviation is documented before implementation continues.

## Risks And Open Questions

- **Implementation drift:** If current source or tests differ from the verified repository basis when implementation begins, stop and report the exact conflict and check result. Do not replace the approved design or broaden this phase.
