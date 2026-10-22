# Build The Guarded Project Composition Helper — Phase 4 Task Plan

## Phase Summary

**Goal:** Add an internal backend helper that checks project and interim application authorization, validates a saved project, normalizes it without writing a workbook, and passes its tables to a table-capable ingester using server-selected settings.

**Readiness: Validated.** [Phase 4 of the phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md#phase-4-build-the-guarded-project-composition-helper) is marked ready. Current code and the completed [Phase 2](./IN_MEMORY_INGESTER_HANDOFF_PHASE_2_TASK_PLAN.md) and [Phase 3](./IN_MEMORY_INGESTER_HANDOFF_PHASE_3_TASK_PLAN.md) task plans show the no-write and table-method dependencies are satisfied and the timezone rule is fixed. The targets, task order, and validation methods below are ready for implementation.

**Sources and constraints:** [Source proposal](./IN_MEMORY_INGESTER_HANDOFF.md), Phase 4 criteria `PH4-AC-1`–`PH4-AC-6`, and milestones `VM-4.1`–`VM-4.3`. Keep the direct-call project guard and `Action.RUN_INGESTERS` check. Project specification and ingester data validation are mandatory. Use `ProjectMapper.to_core()` for directive resolution, `normalize_project()` for the no-write step, and `TableSourceIngester` for capability detection. Phase 5 owns routes and the operator client. The [companion proposal](../../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) owns exclusive per-run output folders, the no-replacement writer rule, the read-only target-database rule, and the later application-permission exception.

**Acceptance criteria**

1. `PH4-AC-1` (from `P-AC-12`): Direct helper calls reject missing, wrong-action, wrong-type, inactive, empty, or mismatched project authorization before project loading or side effects; the interim application check also applies.
2. `PH4-AC-2` (from `P-AC-13`): Project-specification failures stop before normalization or ingester work and return project errors; warnings allow work to continue, while failed ingester data validation stops artifact generation.
3. `PH4-AC-3` (from `P-AC-11`): The helper uses only trusted project and backend inputs plus named submission options; caller overrides and missing required inputs fail before SIMS access or bundle writing.
4. `PH4-AC-4` (from `P-AC-7`): An ingester without table support gets a clear file-input-required error.
5. `PH4-AC-5` (from `P-AC-5`): The helper does not create or read a source workbook, and `source_name` is diagnostic only.
6. `PH4-AC-6` (from `P-AC-9`): A successful run writes only the deploy artifact bundle as its audit record, with no per-call Excel workbook.

## Repository Findings

**Repository basis:** Branch `in-memory-ingester-handoff`, commit `4e4b4063`, planning date 2026-10-19. The pre-existing uncommitted `graphify-out/` files were used for navigation only. An uncommitted assertion edit in `backend/tests/ingesters/test_sead_change_request_inline_staging.py` appeared after the baseline runs; it was not used as an implementation source or changed for this plan. The source phase plan now records Phase 3 complete and Phase 4 ready.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/services/execute_service.py::ExecuteService.execute_workflow`, `_validate_project`; `backend/app/authorization/models.py::AuthorizedResource`; `backend/app/authorization/service.py::AuthorizationService.can_perform_application_action` | Execute checks action, project type, and active state before loading. Its optional specification check converts exceptions to errors. The authorization service has the interim application-action check. | Add a stricter direct-call guard that also checks nonblank locator and exact request match, then require `RUN_INGESTERS` before any project work. Make specification validation unconditional. |
| `backend/app/services/project_service.py::ProjectService.load_project`; `backend/app/mappers/project_mapper.py::ProjectMapper.to_core`; `src/specifications/project.py::CompositeProjectSpecification` | The saved API project is loaded by name; the mapper resolves directives and paths; the composite specification exposes errors and warnings. | Load only the authorized locator, map the saved API project, and run the specification before normalization, provider-context work, or ingester calls. The existing provider-context builder also maps that same project. |
| `src/workflow.py::normalize_project`; `src/table_store.py::TableStore` | The async no-write step returns a `ShapeShifter` with `table_store` after the established option order. | Pass the mapped project and named workflow options to this step; hand its entity-name-to-DataFrame mapping to table methods. Never call `workflow()` or `store()`. |
| `backend/app/ingesters/protocol.py::TableSourceIngester`, `IngesterConfig`; `backend/app/ingesters/registry.py::get_ingester_registry`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` | The table protocol and public `validate_tables()`/`ingest_tables()` methods exist. The latter has `validate_first=True` and writes an artifact only after its checks pass. | Detect support through the separate protocol and call the table methods with a diagnostic `source_name`; force `validate_first=True` on ingestion. |
| `backend/app/services/project_data_provider_service.py::ProjectDataProviderService.build_trusted_context`; `ingesters/sead_change_request/input_resolution.py::_resolve_target_model`, `_resolve_submission_context` | The provider service builds registered scope, fixed provider ID, and business keys from a saved project. The ingester reads a `TargetModel` and submission context from `IngesterConfig.extra`. | Build the trusted context from the same authorized saved project after specification validation; validate the mapped target model and copy only named submission fields. |
| `backend/app/services/ingester_service.py::IngesterService._create_config`; `backend/app/services/ingester_runtime.py::inject_ingester_runtime_dependencies`, `inject_ingester_database_dependencies` | The shared file service copies caller config. `_create_config()` uses caller `database` and does not assign `IngesterConfig.output_folder`, so it retains the default output path. Runtime injection uses `setdefault`, allowing supplied collaborators to remain. | Construct a fresh `IngesterConfig` in the new helper with an explicit managed output root; call the injection functions only after building an allowlisted `extra` dict and backend database connection. Leave shared file behavior unchanged. |
| `backend/app/core/config.py::Settings`; `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md` | Settings has no dedicated ingester target database or `INGEST_OUTPUT_DIR`. The existing `SEAD_*` values are available to project data-source definitions. | Add separate backend settings and document that project sources and requests cannot select the target connection or output root. |
| `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `backend/app/ingesters/protocol.py::IngestionResult` | The writer emits SQL, manifest, and payload files under `config.output_folder`; an existing bundle directory is currently removed and recreated. `IngestionResult` carries row and table counts but no dedicated output-path field. | Verify the Phase 4 helper produces only that bundle under the managed root. Retain the interim application gate; exclusive run directories and accurate bundle-directory response paths belong to the companion phase. |
| `backend/app/models/ingester.py`; `backend/app/api/v1/endpoints/ingesters.py`; `backend/tests/api/test_ingesters.py` | Shared file requests require `source` and accept an open-ended `config`; file routes reject `sead_change_request`. | Add a separate strict project-input type for direct helper calls without changing the shared file models or routes. Phase 5 will expose it through project-only routes. |

## Scope

**In scope:** An internal backend composition service and typed project input, a dedicated backend target connection and managed `INGEST_OUTPUT_DIR`, mandatory authorization and project validation, trusted ingester config construction, table-method invocation, response mapping, service/model/settings tests, and deployment-setting documentation.

**Out of scope:** New API routes or client calls; shared file request and response changes; workbook input restoration; changes to Core normalization or ingester table methods; the companion proposal's unique per-run output, no-replacement writer, read-only database, or permission exception. Preserve file input for other ingesters and Excel dispatch for normal workflow execution.

## Work Breakdown

### Area 1: Define project input and backend-owned settings

**Objective:** Direct callers have one typed, allowlisted project input, and the helper can select a target connection and managed output root without reading request or project data-source settings.

**Affected code:** `backend/app/models/ingester.py`; `backend/app/core/config.py::Settings`; `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md`.

**Dependencies:** None within Phase 4; Phases 2 and 3 are complete.

**Tasks:**

* [x] `T4.1` **Add backend settings:** Define `INGEST_TARGET_HOST`, `INGEST_TARGET_PORT`, `INGEST_TARGET_DBNAME`, `INGEST_TARGET_USER`, and `INGEST_OUTPUT_DIR` on `Settings`.
  * **Target:** `backend/app/core/config.py::Settings`; `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md`; `backend/tests/test_config.py`.
  * **Current → required:** No dedicated ingester target connection or managed bundle root exists. Add backend-only values with `SHAPE_SHIFTER_` environment names, resolve the output path under `APPLICATION_ROOT` when relative, and require nonblank host, database name, and user before a project run. Use a validated port and the existing PostgreSQL password-file arrangement; do not copy project `SEAD_*` source settings into this connection.
  * **Implementation:** Use `None` defaults for host, database name, user, and output root, and a validated `5432` default for port. Resolve a configured relative output root under `APPLICATION_ROOT`; require an explicit output-root setting for project runs. Allow settings to load when these optional values are unconfigured, since the existing file routes and other backend features still start. Fail the project helper before normalization, SIMS, or bundle writing when required values are absent. Set `IngesterConfig.output_folder` explicitly to the resolved `INGEST_OUTPUT_DIR`; do not rely on its `"output"` default. Document setting purpose and required deployment values without adding a password to a project file or example environment file.
  * **Validation:** `V-3`, `V-4` — settings path/default and missing-connection cases; accepted config has the server-selected connection and root.

* [x] `T4.2` **Add strict project input:** Define an internal project-ingester request type and nested submission-options type for the helper.
  * **Target:** `backend/app/models/ingester.py::ProjectIngesterRequest`, `ProjectSubmissionOptions` (new types); `backend/tests/models/test_project_ingester.py` (**NEW**).
  * **Current → required:** `ValidateRequest` and `IngestRequest` require a source path and accept arbitrary config. The project helper needs `project_name`, `translate`, `drop_foreign_keys`, `default_entity`, named submission fields, and an optional `deploy_strategy`, with unknown fields rejected at both levels.
  * **Implementation:** Use Pydantic v2 `extra="forbid"` on both new types. The nested type permits only `submission_name`, `timestamp`, `datatype`, `identifier`, `description`, `issue_identifier`, `author`, and optional `run_id`; require the fields needed by `_resolve_submission_context`. Reject blank project names and unknown top-level or nested values such as `source`, `config`, `database`, `target_model`, `output_folder`, `provider_schema`, `scope_name`, `sims_client`, `run_validation`, and `validate_first`. Preserve exact project-name comparison in the helper guard.
  * **Constraints:** Do not modify shared request/response model fields or permit a free-form `extra` mapping.
  * **Validation:** `V-3` — valid named options parse; top-level and nested override attempts fail without invoking the helper.

**Completion evidence:** The new input types reject unlisted fields, and settings tests prove the target connection and output root are backend-owned.

### Area 2: Guard and validate the authorized saved project

**Objective:** Invalid direct calls stop before any project or ingester work, and a valid saved project passes mandatory specification checks before normalization.

**Affected code:** `backend/app/services/project_ingester_service.py` (**NEW**); existing `AuthorizedResource`, `AuthorizationService`, `ProjectService`, `ProjectMapper`, and `CompositeProjectSpecification` interfaces.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T4.3` **Guard direct calls:** Add `ProjectIngesterService` with a required, constructor-injected `AuthorizationService` and direct-call checks shared by its validate and ingest operations.
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (**NEW**).
  * **Current → required:** Route dependencies cannot protect an internal direct call; `ExecuteService` does not check locator equality. Reject a missing/non-`AuthorizedResource`, any action other than `EXECUTE`, non-`PROJECT` type, inactive resource, blank locator, and a locator different from `request.project_name` with `PermissionError`.
  * **Interface:** Add async `validate_project_tables(key: str, authorized_project: AuthorizedResource, request: ProjectIngesterRequest) -> ValidateResponse` and `ingest_project_tables(key: str, authorized_project: AuthorizedResource, request: ProjectIngesterRequest) -> IngestResponse`. Phase 5 routes pass the fixed `sead_change_request` key; a direct call with a registered file-only key exercises the capability error.
  * **Implementation:** Check the resource first. Require a validated `ProjectIngesterRequest` for direct calls; reject a raw mapping or other object rather than reading arbitrary fields from it. Compare the authorized locator exactly with its `project_name`, then call `authorization_service.can_perform_application_action(principal, Action.RUN_INGESTERS)` and deny on false. Use the authorized resource's locator thereafter. Do this before `ProjectService.load_project`, mapping, settings-dependent config construction, normalization, database/SIMS collaborators, or file writing. Do not accept an optional authorization service that silently skips the application check.
  * **Validation:** `V-1` — parameterized invalid-resource and application-denial tests spy on project loading, mapper, normalization, runtime injection, database/SIMS access, and output writing; none run on denial. An accepted resource loads its exact authorized locator.

* [x] `T4.4` **Validate the saved project:** Load the guarded locator, map it through `ProjectMapper.to_core()`, and run `CompositeProjectSpecification(core_project.cfg)` on every call.
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (**NEW**).
  * **Current → required:** `ExecuteService` can skip its specification check through `run_validation`; the project helper must never skip it. A failed specification or exception must become project errors before normalization, provider-context construction, ingester methods, SIMS, or bundle writing.
  * **Implementation:** Convert `specification.errors` to strings, use `"Project configuration validation failed"` if a failure contains no message, and turn exceptions into a validation error as `_validate_project()` does. Return `ValidateResponse(is_valid=False, errors=...)` or `IngestResponse(success=False, records_processed=0, message="Project validation failed", output_path=None, error_details=...)`. Carry specification warnings into a successful validate response; warnings alone do not block either operation.
  * **Validation:** `V-2` — failing, exception-raising, and warning-only specifications; assert exact stop order and response fields.

**Completion evidence:** Direct denials raise `PermissionError` with zero downstream calls; invalid projects return project errors and never normalize data.

### Area 3: Select trusted ingester inputs

**Objective:** The ingester receives a validated target model, provider context, backend database connection and output root, and only named submission options.

**Affected code:** `backend/app/services/project_ingester_service.py` (**NEW**); `backend/app/services/project_data_provider_service.py::build_trusted_context` and `backend/app/services/ingester_runtime.py` (reuse only); `src/target_model/models.py::TargetModel` (reuse only).

**Dependencies:** Areas 1–2.

**Tasks:**

* [x] `T4.5` **Construct trusted config:** Build `IngesterConfig` directly after the project guard and specification pass, using only server-selected and named fields.
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (**NEW**).
  * **Current → required:** The shared file service copies arbitrary caller config, and its `_create_config()` leaves `output_folder` at the default. The new helper must use the mapped project's resolved `metadata.target_model`, the same loaded API project's `ProjectDataProviderService.build_trusted_context()`, the dedicated settings, and the named submission options.
  * **Implementation:** Validate the target model with `TargetModel.model_validate()` and fail clearly if absent or invalid. Require registered provider scope and fixed provider ID through the existing provider service. Set `IngesterConfig.host`, `port`, `dbname`, `user`, `submission_name`, `data_types`, and `output_folder` explicitly. Put only `target_model`, `trusted_project_context`, normalized submission context, and optional `deploy_strategy` in `extra`; derive project and provider identity from the authorized context, never the nested request. After those values are selected, call `inject_ingester_runtime_dependencies()` and `inject_ingester_database_dependencies()` with that allowlisted `extra` and backend connection. Do not use `IngesterService._create_config()` or pass request dictionaries to `setdefault`-based injection.
  * **Constraints:** Missing model, provider binding/fixed row, database connection, or output root fails before SIMS or bundle writing. Runtime clients and collision checker cannot be supplied by the caller. Do not add the companion phase's read-only database policy here.
  * **Validation:** `V-4` — assert every config field's source, rejected/missing trusted values, and injection order; no SIMS or artifact call occurs on failure.

**Completion evidence:** A captured config contains only the expected server and named values; missing or forged input never reaches a runtime collaborator.

### Area 4: Normalize and invoke table methods

**Objective:** Successful validation and ingestion use completed in-memory tables, preserve ingester checks, and write only a deploy bundle on ingest.

**Affected code:** `backend/app/services/project_ingester_service.py` (**NEW**); `src/workflow.py::normalize_project`; `backend/app/ingesters/protocol.py::TableSourceIngester`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` (reuse only).

**Dependencies:** Areas 2–3.

**Tasks:**

* [x] `T4.6` **Compose table validation and ingestion:** Resolve the registered ingester, require `TableSourceIngester`, normalize the mapped project with the named options, then call `validate_tables()` or `ingest_tables(validate_first=True)` on `ShapeShifter.table_store`.
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (**NEW**).
  * **Current → required:** There is no composed backend call. The helper must reject a registered file-only ingester with a clear “file input required” result, use `source_name=f"project:{authorized_locator}"` only for diagnostics, and never call the file `validate()`/`ingest()` methods or `workflow()`.
  * **Implementation:** Check table capability before normalization. For a registered file-only ingester, return `ValidateResponse(is_valid=False, errors=[...])` or `IngestResponse(success=False, records_processed=0, message="File input required", output_path=None, error_details=...)`, with the error naming the file-input requirement. Pass `translate`, `drop_foreign_keys`, and `default_entity` to `normalize_project()` with the mapped project. Map `ValidationResult` and `IngestionResult` to the existing `ValidateResponse` and `IngestResponse` shapes, preserving errors, warnings, infos, pending confirmation, deploy artifact, scope/run IDs, and ingested row count. Include entity and row counts in internal diagnostics/results without changing shared response schemas. A failed ingester validation returns failure and no bundle; ingest never exposes a `validate_first=False` option. A successful ingest writes the existing bundle under the managed root; validation writes none.
  * **Constraints:** No path-shaped source is accepted or opened. Keep other ingesters' shared file route/service behavior and Core `workflow()` unchanged. The current writer may replace an existing bundle name; the companion phase will remove that behavior before relaxing the application gate.
  * **Validation:** `V-2`, `V-5`, `V-6` — ordered failure and warning cases, file-only rejection, no workbook reads/writes, correct options and diagnostic name, failed data-validation stop, and successful bundle-only output.

**Completion evidence:** A direct helper call reaches public table methods with the normalized tables; successful ingestion has a bundle but no workbook, and all negative cases stop at the stated stage.

## Acceptance-Criteria Coverage

| Criterion and source | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH4-AC-1` (`P-AC-12`) | `T4.3` | `V-1` | Invalid project resource or missing interim application action raises before downstream calls. |
| `PH4-AC-2` (`P-AC-13`) | `T4.4`, `T4.6` | `V-2` | Project failures return project errors; warnings continue; failed ingester validation emits no bundle. |
| `PH4-AC-3` (`P-AC-11`) | `T4.1`, `T4.2`, `T4.5` | `V-3`, `V-4` | Only saved-project and backend facts plus named options reach config and runtime injection. |
| `PH4-AC-4` (`P-AC-7`) | `T4.6` | `V-5` | File-only ingester returns a clear file-input-required error. |
| `PH4-AC-5` (`P-AC-5`) | `T4.6` | `V-5`, `V-6` | No source workbook read or write; `source_name` remains a diagnostic label. |
| `PH4-AC-6` (`P-AC-9`) | `T4.1`, `T4.5`, `T4.6` | `V-6` | Only deploy bundle files appear under the managed root after a successful ingest. |

`VM-4.1` is covered by `V-1`, `V-3`, and `V-4`; `VM-4.2` by `V-2`; `VM-4.3` by `V-4`, `V-5`, and `V-6`.

## Validation And Testing

All proposed tests use `tmp_path` and mocks/fakes for project loading, the database, SIMS, reconciliation, and file I/O. `backend/tests/services/test_project_ingester_service.py` and `backend/tests/models/test_project_ingester.py` are planned **NEW** files. The existing baseline suites below were run on the repository basis; a planned check is not shown as a current pass.

| ID | Check and target | Command or method | Covers | Expected result after implementation | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Direct-call guard cases in `backend/tests/services/test_project_ingester_service.py` (**NEW**) | `rtk .venv/bin/pytest backend/tests/test_config.py backend/tests/models/test_project_ingester.py backend/tests/services/test_project_ingester_service.py -q` | `PH4-AC-1` | Missing, wrong action/type/state, blank/mismatched locator and denied `RUN_INGESTERS` raise before downstream calls; accepted calls load only the authorized locator. | Pass: direct-call guard and application-denial cases. |
| `V-2` | Specification and ingester validation in `backend/tests/services/test_project_ingester_service.py` (**NEW**) | Same focused command as `V-1` | `PH4-AC-2` | Specification failures and exceptions return project errors; warnings allow validation; failed table ingestion uses `validate_first=True` and creates no output. | Pass: specification failure, exception, warning, and failed-ingest cases. |
| `V-3` | Strict request and setting resolution in `backend/tests/models/test_project_ingester.py` (**NEW**) and `backend/tests/test_config.py` | Same focused command as `V-1` | `PH4-AC-3` | Valid named input parses; top-level and nested overrides fail; relative output root resolves under the application root; blank output root is unset and invalid ports fail. | Pass: strict model and settings cases. |
| `V-4` | Trusted-config and missing-input cases in `backend/tests/services/test_project_ingester_service.py` (**NEW**) | Same focused command as `V-1` | `PH4-AC-3`, `PH4-AC-6` | Model, provider context, connection, and output root come from trusted sources; missing or invalid model, provider binding, connection, or root stops before runtime injection or normalization. | Pass: captured config, injection order, missing-setting, model, and provider-binding cases. |
| `V-5` | Table capability and no-workbook calls in `backend/tests/services/test_project_ingester_service.py` (**NEW**) | Same focused command as `V-1` | `PH4-AC-4`, `PH4-AC-5` | File-only ingester reports file input required; table methods receive normalized frames and diagnostic project name; workbook reads and file methods are not called. | Pass: file-only, source-name, file-method, and workbook-read checks. |
| `V-6` | Accepted ingest and bundle-only output in `backend/tests/services/test_project_ingester_service.py` (**NEW**) | Same focused command as `V-1`; `tmp_path` reference-only table and target model matching the existing bundle test | `PH4-AC-5`, `PH4-AC-6` | Successful ingest writes the managed-root bundle's deploy, revert, verify, manifest, and payload files; no workbook or extra audit file appears; validation-only writes nothing. | Pass: real table-ingester validation and bundle generation; external runtime collaborators were stubbed. |
| `V-7` | Existing regressions and changed-file quality | Run the exact commands below. | Existing behavior and all criteria | Existing tests remain green; changed Python files pass quality checks; settings docs match the implementation. | Pass: all listed regression, lint, formatting, import-order, and whitespace checks. |

`V-7` commands:

```bash
rtk .venv/bin/pytest tests/test_workflow.py backend/tests/authorization/test_service_access.py backend/tests/api/test_ingesters.py backend/tests/ingesters/test_ingester_infrastructure.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/test_config.py -q
rtk .venv/bin/ruff check backend/app/core/config.py backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/test_config.py backend/tests/models/test_project_ingester.py backend/tests/services/test_project_ingester_service.py
rtk .venv/bin/black --check backend/app/core/config.py backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/test_config.py backend/tests/models/test_project_ingester.py backend/tests/services/test_project_ingester_service.py
rtk .venv/bin/isort --check-only backend/app/core/config.py backend/app/models/ingester.py backend/app/services/project_ingester_service.py backend/tests/test_config.py backend/tests/models/test_project_ingester.py backend/tests/services/test_project_ingester_service.py
rtk git diff --check
```

Do not run the disposable PostgreSQL integration tests from `backend/tests/ingesters/test_sead_change_request_inline_staging.py` without their documented loopback database. The new helper tests must stub external services and verify their call order without a live target.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Guarded composition service | `backend/app/services/project_ingester_service.py` (**NEW**) | `T4.3`–`T4.6` | Guard, project checks, trusted config, and table calls satisfy `V-1`, `V-2`, `V-4`–`V-6`. |
| Strict project input | `backend/app/models/ingester.py::ProjectIngesterRequest`, `ProjectSubmissionOptions` (new types) | `T4.2` | Unknown top-level and nested fields fail `V-3`. |
| Backend-owned settings | `backend/app/core/config.py::Settings` | `T4.1` | Target connection and output root checks pass `V-3`, `V-4`. |
| Model, service, and settings tests | `backend/tests/models/test_project_ingester.py` (**NEW**); `backend/tests/services/test_project_ingester_service.py` (**NEW**); `backend/tests/test_config.py` | `T4.1`–`T4.6` | `V-1`–`V-6` pass. |
| Deployment guidance | `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md` | `T4.1` | New backend settings and password-file use are documented. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Define project input and backend settings | Done | None | `T4.1`–`T4.2`; `V-3` passed. |
| Area 2: Guard and validate the project | Done | Area 1 | `T4.3`–`T4.4`; `V-1`–`V-2` passed. |
| Area 3: Select trusted ingester inputs | Done | Areas 1–2 | `T4.5`; `V-3`–`V-4` passed. |
| Area 4: Normalize and invoke table methods | Done | Areas 2–3 | `T4.6`; `V-2`, `V-5`, and `V-6` passed. |

## Definition Of Done

- [x] The source phase plan marks Phase 4 ready for a task plan.
- [x] The implementation agent confirms the repository still matches the verified targets and stops to report any material conflict.
- [x] `PH4-AC-1`–`PH4-AC-6` each have passing task and validation results, including the interim application check.
- [x] All four areas and listed deliverables are complete; Phase 5 can use the helper without changing its direct-call guard.
- [x] Invalid authorization, project errors, missing trusted inputs, unsupported table capability, and failed ingester validation stop at the stated stages without SIMS or bundle side effects.
- [x] An accepted call uses only the authorized locator and server-selected config, creates no source workbook, and writes only the deploy bundle for ingestion.
- [x] Focused tests, existing file-route and workflow regressions, formatting, lint, import order, and whitespace checks pass; settings documentation matches code.
- [x] The companion phase's output and database rules remain a prerequisite for removing `Action.RUN_INGESTERS`; any deviations or follow-up work are recorded.

## Risks And Open Questions

- **Current bundle replacement:** `write_artifact_bundle()` removes an existing same-name bundle directory. Phase 4 must retain the interim application gate and cannot claim exclusive per-run output. The companion proposal changes that writer and output layout before its permission exception.
- **Repository drift:** If the target database settings, output rules, or Phase 3 table contract change before execution, stop and report the verified difference. Do not substitute a broader design during this phase.
