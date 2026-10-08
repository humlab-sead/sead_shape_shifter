# Phase 1 Task Plan: Core Operation-Aware Resolver

## Phase Summary

**Goal:** Implement a pure core resolver that returns operation-specific column candidates from the current entity draft and known declarative source metadata, without executing loaders or queries.

**Readiness:** Validated. Phase 1 is marked ready in the [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md). The source-metadata policy is settled: unknown metadata may yield incomplete suggestions; missing candidates do not invalidate a field.

**Dependencies and constraints:** No prior phase is required. Keep stage semantics in `src/`, preserve the runtime pipeline order, and do not import backend models into core. Loader configuration schemas are not output-column schemas.

**Source documents:** [proposal](STAGE_AWARE_COLUMN_SUGGESTIONS.md), [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md), and [column-availability investigation](ENTITY_COLUMN_AVAILABILITY.md).

**Phase acceptance criteria**

1. `PH1-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`): The resolver returns operation-specific candidates for the modeled stages and uses the current `id_vars`, `value_vars`, `var_name`, and `value_name` unnest shape.
2. `PH1-AC-2` (from `P-AC-2`, `P-AC-5`): FK local candidates reflect the FK's link position, and generated `system_id` is excluded before identity assignment and included for processed parent output where applicable.

## Repository Findings

**Repository basis:** Branch `stage-aware-column-suggestions`, commit `abccbb89`, planning date 2026-10-07. The proposal directory is untracked on this branch; its proposal and phase plan were treated as user-provided inputs. No implementation files were changed during planning.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `src/normalizer.py::ShapeShifter._process_entity` | Extraction and `extract` filters precede initial deduplication and linking. Deferred extra columns and `after_link` filters follow linking. Unnesting triggers another FK-link pass and `after_unnest` filters; delayed deduplication and `drop_empty_rows` follow. Identity columns are added later. | Candidate computation must model the configured operation timing without changing this runtime sequence. |
| `src/extract.py::SubsetService.get_subset` and `get_subset_columns` | The subset uses configured keys, columns, and FK columns; it excludes pending unnest and extra-column outputs. The subset path evaluates eligible extras and applies configured transformations. | Start with known configured/source fields, then add outputs only at their actual operation stage. |
| `src/transforms/link.py::ForeignKeyLinker.link_entity` | FKs are visited in configured order. Each successful link updates the stored local table before the next FK; the normalizer calls linking again after unnesting. | Later FK local candidates can include earlier FK outputs; post-unnest candidates need the second link pass. |
| `src/specifications/foreign_key.py::ForeignKeyDataSpecification.get_missing_pending_fields` | Runtime linking defers while either configured unnest output column is absent, even when the FK local keys are present; the normalizer retries after unnesting. | Do not expose generated FK columns before unnest for entities whose unnest outputs are still pending. |
| `src/transforms/filter.py::normalize_filter_stage` and `apply_filters` | Supported stages are `extract`, `after_link`, and `after_unnest`; an omitted stage defaults to `extract`. | Candidate sets for filter operations must use the normalized configured stage. |
| `src/transforms/unnest.py::unnest` and `src/model.py::UnnestConfig` | Runtime unnest uses `id_vars`, `value_vars`, `var_name`, and `value_name`. The output retains ID variables and creates the variable/value columns; value variables are consumed unless also ID variables. | Use the current configuration shape; do not generate legacy `value_id` candidates. |
| `src/model.py::TableConfig` and `ShapeShiftProject` | Core wrappers expose FK, append/branch, extra-column, deduplication, filter, unnest, and identity configuration. `get_target_facing_columns()` describes final output and deliberately excludes internal `system_id`. | Reuse core configuration helpers for known inputs and final parent output only; compute intermediate operation candidates separately and handle generated `system_id` explicitly. Do not access `table_cfg.columns` directly. |
| `src/loaders/base_loader.py::DataLoader.schema` and `src/loaders/driver_metadata.py::DriverSchema` | Loader schemas describe driver configuration fields, not result columns. Some loader results cannot be known without reading a source or running a query. | Do not use `DriverSchema.fields` as output columns. Accept only declarative source-column metadata already supplied; leave unknown source fields unknown. |
| `tests/process/test_shapeshifter.py`, `tests/process/test_subset_service.py`, `tests/process/test_subset_service2.py`, `tests/transforms/test_unnest.py`, `tests/transforms/test_drop_duplicates.py`, `tests/transforms/test_extra_columns.py`, `tests/transforms/test_link.py` | Existing tests use inline project/data fixtures for the pipeline, subset, linking, extra-column, unnest, and deduplication behavior. | Add focused resolver tests under `tests/process/` and use inline deterministic inputs for runtime comparisons. |

**Baseline results**

- `uv run pytest tests/process/test_shapeshifter.py tests/process/test_subset_service.py tests/process/test_subset_service2.py tests/transforms/test_unnest.py tests/transforms/test_drop_duplicates.py tests/transforms/test_extra_columns.py tests/transforms/test_link.py -o addopts= -q`: 248 passed, 4 existing pandas `FutureWarning`s.
- Ruff check on the verified core and test files: passed.
- isort check on the verified core and test files: passed.
- Black check on those files: reports that `src/model.py` would be reformatted; the other 15 files are unchanged. Do not reformat `src/model.py` as part of Phase 1. Run formatting checks on the new files only.

## Scope

**In scope**

- Add a core-only resolver and its operation-specific result contract.
- Derive candidates from the entity draft, known source configuration, and optional declarative source-column metadata without source reads or loader/query execution.
- Model operation timing for source fields, eligible and deferred extra columns, replacements, filters, deduplication, FK linking, unnesting, drop-empty, and identity assignment.
- Add operation-level tests and deterministic comparisons with columns observed at corresponding runtime operations.

**Out of scope**

- Backend endpoints, API request/response models, frontend composables, and editor controls. These belong to later phases.
- Changes to `ShapeShifter.normalize()` or runtime stage order.
- Dynamic source inspection, loader execution, or SQL execution to discover result columns.
- Changes to project validation, runtime availability checks, or `get_target_facing_columns()`.
- Formatting unrelated existing files, including `src/model.py`.

## Work Breakdown

### Area 1: Implement Core Candidate Resolution

**Objective:** Provide one pure core implementation that models known columns at each editor operation.

**Affected code:** `src/column_availability.py` (NEW); existing contracts in `src/model.py::TableConfig`, `src/model.py::ShapeShiftProject`, `src/loaders/base_loader.py::DataLoader`, and `src/loaders/driver_metadata.py::DriverSchema`; runtime order in `src/normalizer.py::ShapeShifter._process_entity` and the transform modules listed in Repository Findings.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Add a core resolver entry point and operation-keyed result contract in a new module.
  * **Target:** `src/column_availability.py` (NEW); `src/model.py::TableConfig`; `src/model.py::ShapeShiftProject`.
  * **Current → required:** No core operation-aware resolver exists. Add a core-only input boundary for the current entity draft and optional known source-column names, and return candidates grouped by editor operation rather than exposing pipeline stages as the public result.
  * **Implementation:** Use existing core configuration wrappers where they provide the needed values. Keep the resolver independent of API DTOs, filesystem/database access, and loader execution. Treat absent source-column metadata as unknown; return candidates derivable from known configuration without claiming completeness. For final parent output, use the existing final-output helper where applicable and add generated `system_id` explicitly because that helper excludes it.
  * **Constraints:** Do not read source files, execute queries/loaders, or interpret `DriverSchema.fields` as row columns. Do not use final target-facing columns as the candidate set for every intermediate operation. Do not access `table_cfg.columns` directly; do not redesign `get_target_facing_columns()`.
  * **Validation:** `V-1`, `V-2`, and `V-4`.
* [x] `T1.2` **Change:** Compute candidates at the operation and FK-link positions specified by the phase criteria.
  * **Target:** `src/column_availability.py` (NEW); behavior verified against `src/normalizer.py::ShapeShifter._process_entity`, `src/extract.py::SubsetService`, `src/transforms/filter.py`, `src/transforms/link.py::ForeignKeyLinker.link_entity`, and `src/transforms/unnest.py::unnest`.
  * **Current → required:** Existing runtime transformations know their own stage, but no shared resolver maps the unsaved entity configuration to candidate sets for those stages.
  * **Implementation:** Model known source/input columns; eligible and deferred extra-column outputs; replacement and filter timing; pre-unnest versus delayed deduplication; configured FK order and the second post-unnest linking pass; `id_vars`, `value_vars`, `var_name`, and `value_name`; final `drop_empty_rows`; and post-cleanup identity assignment. For remote parent candidates, include `system_id` only at the processed-parent stage. Keep fields not derivable from metadata out of suggestions without treating them as invalid.
  * **Constraints:** Match the current implementation order, including extract filters before linking and `drop_empty_rows` before identity assignment. Preserve FK local values as child-side matching inputs and parent `system_id` as the linked identity value. Keep suggestions advisory.
  * **Validation:** `V-1`, `V-2`, and `V-3`.

**Completion evidence:** The new module returns the two phase criteria's operation-specific candidate sets, and tests demonstrate stage timing, partial source metadata, FK order, current unnest behavior, and identity timing.

### Area 2: Add Resolver And Runtime-Comparison Tests

**Objective:** Verify the resolver independently and compare its predictions with deterministic runtime behavior.

**Affected code:** `tests/process/test_column_availability.py` (NEW); existing inline fixture patterns in `tests/process/test_shapeshifter.py`, `tests/process/test_subset_service.py`, and `tests/transforms/`.

**Dependencies:** `T1.1` and `T1.2` establish the resolver contract and behavior.

**Tasks:**

* [x] `T1.3` **Change:** Add focused tests for known and unknown input fields and each operation stage.
  * **Target:** `tests/process/test_column_availability.py` (NEW); core inputs from `src/model.py::ShapeShiftProject` and `TableConfig`.
  * **Current → required:** Existing tests cover runtime transforms but not operation-specific suggestions. Add inline configuration tests for fixed and entity/merged sources where fields can be derived, optional known external-source fields, and unknown or incomplete loader metadata.
  * **Implementation:** Assert candidate behavior for replacements and extra-column dependencies, the three filter stages and default stage, FK order including outputs from earlier links, normal and delayed deduplication, drop-empty after unnest, current unnest output names, and `system_id` before versus after identity assignment. Confirm that unknown source metadata does not cause an exception or turn an omitted candidate into a validity result.
  * **Constraints:** Follow `tests/AGENTS.md`: use `ShapeShiftProject(cfg={...})`, inline data, absolute imports, and no backend or external-service dependency.
  * **Validation:** `V-1` and `V-4`.
* [x] `T1.4` **Change:** Add deterministic comparisons between resolver candidates and columns observed at matching runtime operations.
  * **Target:** `tests/process/test_column_availability.py` (NEW); runtime entry points in `src/normalizer.py::ShapeShifter.normalize` and `_process_entity`.
  * **Current → required:** Existing pipeline tests establish transform behavior, but they do not compare it with resolver candidates. Add small in-memory fixtures with known source columns and capture the columns available at the relevant operation calls.
  * **Implementation:** Compare known-field candidate sets with columns observed before and after linking, unnesting, delayed deduplication, and cleanup. Include a parent/child fixture for generated `system_id` and FK order. Keep these comparisons limited to deterministic fixtures; do not assert completeness for dynamic file or SQL sources.
  * **Constraints:** Do not call `asyncio.run()` or use external loaders, queries, or database connections. Use async pytest tests only if invoking `ShapeShifter.normalize()`.
  * **Validation:** `V-2` and `V-3`.

**Completion evidence:** Unit cases cover each operation context, and deterministic fixtures show the resolver agrees with the runtime columns observed at corresponding operations.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`) | `T1.1`, `T1.2`, `T1.3`, `T1.4` | `V-1`, `V-2`, `V-3`, `V-4` | Operation-keyed results model stage timing and use the current unnest fields; deterministic runtime fixtures agree where source fields are known. |
| `PH1-AC-2` (from `P-AC-2`, `P-AC-5`) | `T1.1`, `T1.2`, `T1.3`, `T1.4` | `V-1`, `V-2`, `V-3`, `V-4` | FK local candidates follow configured link order; `system_id` is omitted before assignment and included for processed parent candidates. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Resolver unit cases in the new test module | `uv run pytest tests/process/test_column_availability.py -q` | `PH1-AC-1`, `PH1-AC-2` | Stage-specific candidate, unknown-metadata, FK-order, unnest, and identity cases pass. | Pass: 7 tests passed. |
| `V-2` | Controlled comparisons against runtime operation inputs in the new test module | `uv run pytest tests/process/test_column_availability.py -q` | `PH1-AC-1`, `PH1-AC-2` | For deterministic inline source fields, resolver candidates match the columns observed at each corresponding operation. | Pass: runtime comparison covers both FK link passes, unnest, delayed deduplication, and pre-cleanup columns. |
| `V-3` | Existing pipeline regression suite | `uv run pytest tests/process/test_shapeshifter.py tests/process/test_subset_service.py tests/process/test_subset_service2.py tests/transforms/test_unnest.py tests/transforms/test_drop_duplicates.py tests/transforms/test_extra_columns.py tests/transforms/test_link.py -q` | `PH1-AC-1`, `PH1-AC-2` | Existing extraction, linking, extra-column, filter, unnest, deduplication, and cleanup behavior remains unchanged. | Pass: 248 passed, 4 pandas `FutureWarning`s. |
| `V-4` | Targeted lint and formatting checks on new files | `uv run ruff check --output-format concise src/column_availability.py tests/process/test_column_availability.py`<br>`uv run black --check src/column_availability.py tests/process/test_column_availability.py`<br>`uv run isort --check-only src/column_availability.py tests/process/test_column_availability.py` | `PH1-AC-1`, `PH1-AC-2` | All checks pass without modifying files. | Pass: Ruff, Black, and isort all passed. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Core operation-aware resolver | `src/column_availability.py` (NEW) | `T1.1`, `T1.2` | Pure core entry point returns operation-specific candidates using known declarative inputs. |
| Resolver unit and runtime-comparison tests | `tests/process/test_column_availability.py` (NEW) | `T1.3`, `T1.4` | Focused tests pass and deterministic fixtures match runtime operation columns. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Implement Core Candidate Resolution | Done | None | Added the pure resolver and modeled runtime FK deferral before pending unnest outputs. |
| Area 2: Add Resolver And Runtime-Comparison Tests | Done | Area 1 | Six focused tests cover operation sets, partial metadata, FK ordering, merged branches, deduplication, unnest, and runtime checkpoints. |

## Definition Of Done

- [x] `PH1-AC-1` and `PH1-AC-2` each have implementation and validation evidence.
- [x] Both new files are complete and all planned tests and targeted quality checks pass.
- [x] Regression tests confirm the runtime pipeline remains unchanged.
- [x] The resolver does not execute loaders, queries, or source reads and does not treat unknown metadata as proof that a field is invalid.
- [x] FK order, both link passes, current unnest fields, delayed deduplication, cleanup timing, and generated `system_id` are covered.
- [x] Any implementation deviation or follow-up needed by Phase 2 is recorded; no unresolved question affects correctness or validation.

## Risks And Open Questions

- Loader `DriverSchema` metadata describes configuration fields rather than query/file result columns. Keep these distinct; where no declarative output fields are available, return only candidates derivable from known configuration and caller-supplied metadata.
- `TableConfig.get_target_facing_columns()` deliberately excludes `system_id` and describes final output only. Use it only where final parent output is appropriate, add generated `system_id` separately for processed-parent matching, and compute intermediate operation candidates from the stage model.
- Runtime FK linking defers while configured unnest output columns are absent, then retries after unnest. The resolver reflects that behavior by withholding linked outputs before unnest for those entities.
- The broad baseline Black check reports that existing `src/model.py` would be reformatted. This phase does not require changing that file; target the new files for formatting checks.
- No blocking decisions remain. The resolver result contract is operation-specific, and missing candidates remain advisory rather than validation failures.
