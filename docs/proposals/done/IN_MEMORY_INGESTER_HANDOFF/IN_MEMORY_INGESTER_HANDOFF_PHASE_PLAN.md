# Hand Normalized Tables To The Ingester In Memory — Phase Plan

## Summary

This plan sequences [the in-memory handoff proposal](./IN_MEMORY_INGESTER_HANDOFF.md). Phases 1–3 retired Change Request file input and added no-write normalization and table-input support. Phase 4 added the guarded backend helper, and Phase 5 exposed its project-only routes and connected the saved-project operator client. The [target-bundle access proposal](../../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) owns the later permission change and per-run output rules.

## Problem

Change Request generation previously read a workbook written by normalization. That read accepted caller-supplied paths and could change names, values, types, and timezones. Phase 1 retired that input. The proposed project-only operation needs normalized tables in memory, trusted ingester settings, project validation, and authorization before any ingester work.

## Scope

This plan covers retirement of `sead_change_request` file input, the Core no-write step, table-input validation and ingestion, the backend helper, project-only API routes, and the operator client path.

It leaves Excel dispatch and file input for other ingesters unchanged. It does not implement the companion proposal's removal of `application:run_ingesters`, exclusive per-run output folders, or read-only target-database rule.

## Current Position

- `normalize_project()` applies normalization options and returns the completed tables without writing; `workflow()` calls it before its dispatcher write and shape log.
- `sead_change_request` advertises no file formats. Its file routes, service calls, and file-oriented methods reject Change Request input; its source resolver rejects a path-shaped input before checking `config.extra`.
- `TableSourceIngester` and the Change Request table methods are implemented. The adapter copies and sanitizes normalized tables; artifact rendering keeps date and clock fields without timezone conversion and rejects incompatible target column types.
- Shared ingester requests still require `source` and use the existing file-oriented service. The internal `ProjectIngesterService` validates authorization and project configuration, then passes normalized tables and trusted settings to table-capable ingesters. The project-only routes now expose this helper, and the saved-project Dispatch form uses those routes.
- Phases 1–5 are complete, as recorded in the [Phase 1](./IN_MEMORY_INGESTER_HANDOFF_PHASE_1_TASK_PLAN.md), [Phase 2](./IN_MEMORY_INGESTER_HANDOFF_PHASE_2_TASK_PLAN.md), [Phase 3](./IN_MEMORY_INGESTER_HANDOFF_PHASE_3_TASK_PLAN.md), [Phase 4](./IN_MEMORY_INGESTER_HANDOFF_PHASE_4_TASK_PLAN.md), and [Phase 5](./IN_MEMORY_INGESTER_HANDOFF_PHASE_5_TASK_PLAN.md) task plans. Project-only bundle generation is available through the saved-project operator path; both interim permissions remain required.

## Phase Plan

### Phase 1: Retire Change Request file input

**Goal**

Close the unused Change Request workbook entry points before building the project-only path.

**Focus**

- Report no supported file formats for `sead_change_request` and reject its shared file routes, service calls, and file-oriented ingester methods before source resolution.
- Reject `Path` and `str` in the Change Request source resolver before consulting `config.extra`, including when extras contain tables or a source bundle.
- Replace tests that used fake workbook inputs for downstream behavior with direct in-memory bundle preparation where applicable; preserve file behavior for other ingesters and Excel dispatch.

**Depends On**

- None. This is the first delivery step.

**Outputs**

- Change Request file input is unavailable at every entry point; the temporary gap before project-only generation is explicit.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-6`) Change Request metadata lists no file formats. Its file routes, service calls, and file-oriented methods fail before source resolution, and a `Path` or `str` cannot select in-memory data through `config.extra`.
- `PH1-AC-2` (from `P-AC-6`) Other ingesters retain their file input and permission checks; Excel dispatch keeps its current output behavior.

**Validation Milestones**

- `VM-1.1` Direct and routed Change Request file calls fail without opening a source path, including calls with table data in `config.extra` (covers `PH1-AC-1`).
- `VM-1.2` Metadata and regression checks show no Change Request file formats while other ingesters and Excel dispatch keep working (covers `PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Retire the path before the replacement project-only routes ship. Keep the shared file request and response models unchanged. Preserve useful downstream tests through in-memory preparation until table methods arrive in Phase 3.

**Readiness**

Completed. The [Phase 1 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_1_TASK_PLAN.md) records acceptance and validation results.

### Phase 2: Share normalization without writing output

**Goal**

Let a caller obtain the completed normalized tables with the same options as `workflow()`.

**Focus**

- Extract one Core normalization step that returns the completed `ShapeShifter` without a target or dispatcher.
- Keep `workflow()` calling that step before its existing store and shape-log operations.

**Depends On**

- Phase 1 retirement (complete), preserving the agreed delivery order.

**Outputs**

- A no-write Core operation available to the later backend helper.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`) The new step applies `drop_foreign_keys` and `translate` in the current order and returns completed tables without invoking a dispatcher or requiring an output target.
- `PH2-AC-2` (from `P-AC-1`) Existing `workflow()` calls keep their file output, shape logging, signature, and `None` return value.

**Validation Milestones**

- `VM-2.1` The no-write step returns the same normalized tables as the file-writing workflow for representative option combinations, before dispatch (covers `PH2-AC-1`).
- `VM-2.2` Existing workflow output and return-value checks pass (covers `PH2-AC-2`).

**Task-Plan Handoff**

- Keep the normalization and option order in `src/`. Do not add a `memory` dispatcher or import backend or ingester code into Core.

**Readiness**

Completed. The [Phase 2 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_2_TASK_PLAN.md) records acceptance and validation results.

### Phase 3: Accept normalized tables in the Change Request ingester

**Goal**

Make table validation and ingestion explicit without using Excel as the input contract.

**Focus**

- Add the separate `TableSourceIngester` capability and a Change Request adapter that copies and sanitizes columns while preserving entity names, values, dtypes, and timezones.
- Reuse the existing post-resolution validation and ingestion checks for table methods. Reject invalid tables and unsupported timezone values clearly.
- Use normalized table values for business-key decisions and generated artifacts.

**Depends On**

- Phases 1 and 2 provide the retired file contract and no-write normalized tables.

**Outputs**

- Table-source methods that the backend helper can call; Change Request downstream tests use those methods rather than retired file methods.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-2`) A protocol check discovers table support without changing the shared `Ingester` protocol or shared file request and response models.
- `PH3-AC-2` (from `P-AC-3`) The adapter copies valid tables, preserves normalized entity names and values, sanitizes columns, and rejects invalid input with `SourceBundleError`.
- `PH3-AC-3` (from `P-AC-4`) Table-based business-key decisions and generated change-request artifacts use normalized table values.
- `PH3-AC-4` (from `P-AC-3`, `P-AC-8`) Table validation and ingestion run the existing post-preparation checks and preserve `validate_first` behavior. Date and timestamp values retain their normalized calendar and clock fields in generated literals; timezone metadata is removed without conversion. Incompatible timezone-aware target columns fail clearly.

**Validation Milestones**

- `VM-3.1` Protocol, adapter, and invalid-input checks establish the table contract (covers `PH3-AC-1`, `PH3-AC-2`).
- `VM-3.2` Table validation and ingestion exercise preconditions and collision checks; artifact checks confirm date and clock fields are unchanged, timezone metadata is not converted, and incompatible target column types fail before artifact writing (covers `PH3-AC-4`).
- `VM-3.3` Fixtures verify business-key decisions and generated change-request artifacts use normalized table values (covers `PH3-AC-3`).

**Task-Plan Handoff**

- Keep source entity names separate from target table names: `TargetModel.entities` identifies the entity, and `target_table` selects the SQL table when present. Do not apply Excel sheet-name rules or require workbook decision parity.
- Here, an input column is a column in a normalized entity DataFrame passed to the table methods. Its target is the same-named column in the destination table for that entity, described by `TargetModel.entities[entity].columns` and `target_table` (or the entity name when `target_table` is unset).
- For a `date` target, use the calendar date shown in the normalized input value. For a timestamp without time zone target, use its calendar and clock fields as written. Remove any timezone metadata from normalized datetime values without changing those fields; do not convert through UTC or a target/session timezone. Require timezone-naive target columns and reject incompatible target types.
- Verify that each deploy-artifact strategy (`inline_insert`, `copy_csv`, and `inline_staging`) writes those literal values without shifting the date or clock fields, and rejects incompatible target types before artifact writing.

**Readiness**

Completed. The [Phase 3 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_3_TASK_PLAN.md) records the table-method, literal-rendering, and incompatible-target validation results.

### Phase 4: Build the guarded project composition helper

**Goal**

Compose authorized project normalization and table ingestion with server-selected inputs.

**Focus**

- Check the supplied `AuthorizedResource` and the interim `application:run_ingesters` action before loading or processing a project.
- Map the authorized saved project, require `CompositeProjectSpecification` to pass, then normalize and call a table-capable ingester with mandatory data validation.
- Build `IngesterConfig` from the mapped target model, trusted project context, backend target connection, managed `INGEST_OUTPUT_DIR` root, and named submission options. Reject caller overrides and missing trusted inputs.

**Depends On**

- Phases 2 and 3 provide the no-write step and table methods (both complete).

**Outputs**

- An internal helper ready for project-only routes, still behind both the project and application permission checks.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-12`) Direct helper calls reject missing, wrong-action, wrong-type, inactive, empty, or mismatched project authorization before project loading or side effects; the interim application check also applies.
- `PH4-AC-2` (from `P-AC-13`) Project-specification failures stop before normalization or ingester work and return project errors; warnings allow work to continue, while failed ingester data validation stops artifact generation.
- `PH4-AC-3` (from `P-AC-11`) The helper uses only trusted project and backend inputs plus named submission options; caller overrides and missing required inputs fail before SIMS access or bundle writing.
- `PH4-AC-4` (from `P-AC-7`) An ingester without table support gets a clear file-input-required error.
- `PH4-AC-5` (from `P-AC-5`) The helper does not create or read a source workbook, and `source_name` is diagnostic only.
- `PH4-AC-6` (from `P-AC-9`) A successful run writes only the deploy artifact bundle as its audit record, with no per-call Excel workbook.

**Validation Milestones**

- `VM-4.1` Direct-call authorization and caller-override checks stop before project loading, normalization, database or SIMS access, and file writing (covers `PH4-AC-1`, `PH4-AC-3`).
- `VM-4.2` Invalid projects and ingester data fail in the stated order; warning-only projects continue (covers `PH4-AC-2`).
- `VM-4.3` An accepted table run uses trusted inputs, rejects unsupported ingesters, reads no source workbook, and writes only the deploy bundle (covers `PH4-AC-3` through `PH4-AC-6`).

**Task-Plan Handoff**

- Use `ProjectMapper.to_core()` and the authorized locator. Keep project validation mandatory and retain the direct-call guard even after the companion proposal later removes only the application check.
- This phase supplies the managed output root. The companion proposal owns exclusive per-run folders and read-only target-database behavior before its permission exception takes effect.

**Readiness**

Completed. The [Phase 4 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_4_TASK_PLAN.md) records implementation and validation for `PH4-AC-1`–`PH4-AC-6`. The helper retains the interim application permission check; the companion proposal's output and database rules remain prerequisites for removing it.

### Phase 5: Expose project-only routes and switch the operator client

**Goal**

Let an authorized operator validate and generate a Change Request from a saved project without sending a source path.

**Focus**

- Add separate project-only validation and ingest routes with strict request models, `project:execute` authorization, and the interim `application:run_ingesters` requirement.
- Pass the authorized project to the helper; return the existing validation and ingestion response shapes, including project-validation failures.
- Switch the saved-project Change Request client path to those routes. Keep file-only ingesters on their existing routes.

**Depends On**

- Phase 4 supplies the guarded helper and trusted input construction.

**Outputs**

- A usable project-only operator path behind both permissions. The companion permission and output phase can begin after the handoff criteria are met.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-8`) Both project-only routes require an authenticated project executor and the interim application action, reject source paths and arbitrary config, and call the helper with the authorized project.
- `PH5-AC-2` (from `P-AC-10`) The operator client sends only named project and submission fields to the project-only routes; file-only ingesters continue using the shared file routes.
- `PH5-AC-3` (from `P-AC-12`) Route calls and direct helper calls retain the project-resource guard and reject invalid authorization before work.
- `PH5-AC-4` (from `P-AC-13`) Both routes report project-specification failures in the existing response models before normalization or ingester work; failed ingester data validation blocks bundle writing.

**Validation Milestones**

- `VM-5.1` Route and direct-helper checks enforce both interim permissions, reject extra request input and invalid project authorization, and avoid side effects on denial (covers `PH5-AC-1`, `PH5-AC-3`).
- `VM-5.2` Project and ingester validation failures return the specified results without a bundle (covers `PH5-AC-4`).
- `VM-5.3` The operator client sends project-only requests without `source` or arbitrary `config`; file-only ingesters keep their existing behavior (covers `PH5-AC-2`).

**Task-Plan Handoff**

- Keep both permissions until the companion proposal's exclusive output and read-only database rules ship. Do not remove `application:run_ingesters` from the shared file routes.
- The companion phase depends on handoff `P-AC-1`, `P-AC-8`, `P-AC-10`, `P-AC-11`, `P-AC-12`, and `P-AC-13`; its client work adds persistent `run_id` reuse across one submission attempt.

**Readiness**

Completed. The [Phase 5 task plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_5_TASK_PLAN.md) records implementation and passing validation for `PH5-AC-1`–`PH5-AC-4`. Both `project:execute` and the interim `application:run_ingesters` permission remain required. The companion proposal still owns exclusive per-run output and read-only target-database access before the application permission can be removed.

## Cross-Phase Rules

- Retire Change Request file input before exposing the replacement path; keep other ingesters' file routes and Excel dispatch unchanged.
- Preserve normalized table values. Workbook fixtures document conversion differences; retired workbook ingestion is not a parity target.
- Keep the direct helper's project guard and mandatory project and ingester validation. Do not enable the project-only permission exception in this plan.
- Use the deploy bundle as the run's audit record. Do not write a workbook for project-only ingestion.

## Validation Strategy

Validate each phase before using its output in the next: file-input rejection, no-write workflow option parity, table and artifact behavior, direct-helper authorization and trusted inputs, then route and client behavior. Each validation milestone above names the acceptance criteria it covers. Phase task plans should select the exact tests and commands.
