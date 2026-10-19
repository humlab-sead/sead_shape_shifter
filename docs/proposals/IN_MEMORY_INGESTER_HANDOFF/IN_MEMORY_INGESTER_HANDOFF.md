# Hand Normalized Tables To The Ingester In Memory

## Status

- Proposed feature
- Scope: a reusable normalization step, an optional table-input capability for ingesters, handoff rules, a backend composition helper, and project-only API and client entry points
- Goal: run normalization and change-request generation in one process without writing and re-reading an Excel workbook
- Depends on [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) for the permission that governs Change Request bundle creation; this proposal does not set that permission

## Summary

The backend currently hands normalized data to the change-request ingester through an Excel workbook. `workflow()` always writes its output, while the ingester reads a caller-supplied file path. Excel changes some names, types, and values during that round trip.

Recommend a shared normalization step that returns the completed `ShapeShifter` without dispatching, plus an explicit table-input capability on the ingester. A separate project-only API path calls the backend helper for validation and bundle creation; its requests have no source path. Retire `sead_change_request` workbook input immediately, independently of when the composed path ships. The file-writing `workflow()` stays available for dispatch.

## Problem

A backend caller that wants to run normalization and change-request generation together currently has to:

1. run `workflow()` with the `xlsx` dispatcher so a workbook is written;
2. find the output path;
3. pass that path to the ingester.

Lower-level calls can already reach the DataFrame-based ingester contract, but they do not provide a supported composition path with the same normalization options and ingester checks.

**The handoff changes data.** The `xlsx` dispatcher removes timezone information, and `pd.read_excel()` infers types and missing values. For example, a text business key such as `"001"` can become the number `1`, and `"NA"` can become null. The separate `openpyxl` dispatcher can also rewrite sheet names. The change-request ingester sanitizes column names after reading the workbook.

**The current file path permits an unconstrained read.** `_load_source_bundle_from_path` accepts any readable path with a `.xlsx`/`.xls` suffix and has no containment check. The `application:run_ingesters` gate does not constrain the path. Retiring this input closes that read for `sead_change_request` without adding containment to an unused workflow.

**The Excel workbook is the thing being replaced.** For `sead_change_request`, reading a dispatched workbook is the only current trigger for change-request generation. The user reports that this input has not been used and will not be used. Disable it now rather than keeping a route available while the composed path is built.

**No ingester will need Excel input once `sead` is gone.** `sead_change_request` is the only ingester this proposal changes. The other registered ingester, `sead`, is a file-only direct-to-database importer that is separately deprecated and scheduled for removal ([#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569)). The file-writing `workflow()` and the `xlsx` dispatcher stay unchanged, so dispatched workbooks remain available for review and for any future file-only ingester; they stop being the change-request trigger.

**The existing workflow always writes.** `ShapeShifter.normalize()` exposes the tables, but a caller that bypasses `workflow()` must repeat its `drop_foreign_keys` and `translate` option handling.

## Scope

- A Core normalization step that applies the same options as `workflow()` and returns the completed entity tables without dispatching them.
- An additive, optional table-input capability on the ingester protocol, implemented by `sead_change_request`.
- One adapter that converts normalized tables into the ingester's source bundle without Excel conversions.
- One backend composition helper that runs normalization and ingestion for an authorized project.
- Separate project-only validation and bundle-creation endpoints, with an operator client path that uses them for an authorized saved project.
- A trusted configuration rule for the project-only helper and routes.
- Immediate retirement of `sead_change_request` workbook input at the file routes, service, and ingester entry points.

## Non-Goals

- Removing Excel dispatch or changing file input for other ingesters. The deprecated `sead` ingester still requires file input until its separate removal ([#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569)). The `xlsx` and `openpyxl` dispatchers are unchanged.
- Writing an Excel workbook per composed call as an audit artifact. The deploy artifact bundle is the audit record; see Proposed Design §5.
- Adding containment for the retired Change Request workbook input. [Ingester Authorization](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) still governs any remaining path-based ingester operations.
- Changing the shared `IngestRequest`, `ValidateRequest`, `IngestResponse`, or `ValidateResponse` contracts for other ingesters.
- Adding a new operator control to choose between workbook and project input; the project workflow uses the new project-only endpoints.
- Removing the ingester or routing ingestion through a dispatcher. The ingester stays a separate extension point with its own authorization and validation rules.
- Eliminating all filesystem activity. Normalization may read configured sources, and successful ingestion still writes a deploy artifact bundle.
- Introducing a streamed or chunked handoff. Tables stay in memory as DataFrames.

## Current Behavior

Verified in the repository:

- `ShapeShifter.normalize()` returns `self`, and completed tables are available in `self.table_store` (`src/normalizer.py`, `src/table_store.py`).
- `ShapeShifter.store()` resolves a dispatcher and calls `dispatcher.dispatch(target=..., data=self.table_store)` (`src/normalizer.py`). `IDispatcher.dispatch` returns `None` (`src/dispatch.py`).
- `workflow()` resolves the project, runs `normalize()`, applies optional `drop_foreign_keys` and `translate` steps, then unconditionally calls `store()` and `log_shapes()`. It returns `None` (`src/workflow.py`).
- `_resolve_source_bundle` already accepts a `SourceTableBundle`, a `SourceTableBundle` under `config.extra["source_bundle"]`, a raw table mapping, or a `Path`/`str` (`ingesters/sead_change_request/input_resolution.py`). It checks the extras before a path, so a path-shaped source can select hidden in-memory input. The mapping branch calls `_build_source_bundle`, which validates types only and does not sanitize columns.
- The path branch accepts `.xlsx`/`.xls`, reads each usable sheet with `pd.read_excel()`, sanitizes its columns, and skips `data_table_index`. Pandas may change dtypes and values while reading Excel.
- `SeadChangeRequestIngester.get_metadata()` still advertises `xlsx` and `xls` as supported file formats (`ingesters/sead_change_request/ingester.py`).
- The shared `Ingester` protocol accepts paths. `SeadChangeRequestIngester` passes its source to `resolve_inputs`, but `validate()` and `ingest()` each perform work after shared preparation (`backend/app/ingesters/protocol.py`, `ingesters/sead_change_request/ingester.py`).
- The current ingester route checks both `application:run_ingesters` and project `execute` authorization. `IngesterService` supplies trusted project context and runtime dependencies (`backend/app/api/v1/endpoints/ingesters.py`, `backend/app/services/ingester_service.py`).
- The existing validate and ingest requests require `source`. Both routes pass it to file-oriented ingester methods, and the operator form sends it (`backend/app/models/ingester.py`, `backend/app/api/v1/endpoints/ingesters.py`, `frontend/src/components/ingester/IngesterForm.vue`).
- `IngesterService` copies caller `request.config`; `_create_config()` takes its target database from `config["database"]`. The Change Request ingester reads `target_model` from `IngesterConfig.extra`, and its writer uses `IngesterConfig.output_folder`. The saved project's `metadata.target_model` is available after `ProjectMapper.to_core()`, but there is no dedicated backend target-database setting yet (`backend/app/services/ingester_service.py`, `ingesters/sead_change_request/input_resolution.py`, `ingesters/sead_change_request/artifact_writer.py`, `backend/app/models/project.py`).

The gaps are a no-write normalization step with shared option handling, an explicit ingester capability, defined rules for differences from Excel, and a project request path that calls the new helper without accepting a source path.

## Proposed Design

### 1. Reuse normalization without dispatching

Extract the normalization and option steps from `workflow()` into a Core function in `src/workflow.py` that returns the completed `ShapeShifter`. It resolves the project, calls `normalize()`, then applies `drop_foreign_keys` and `translate` in their current order. It does not call `store()` or `log_shapes()` and does not require an output target or dispatcher.

`workflow()` calls this function, then performs its existing `store()` and `log_shapes()` calls. Its signature, `None` return value, and file-writing behavior remain unchanged. The backend composition helper calls the no-write function directly. Both paths apply the same normalization options without duplicating their order.

### 2. Add an optional table-input capability to the ingester protocol

Add a second, `runtime_checkable` protocol beside `Ingester`:

```python
@runtime_checkable
class TableSourceIngester(Protocol):
    async def validate_tables(self, tables: Mapping[str, pd.DataFrame], *, source_name: str = "") -> ValidationResult: ...
    async def ingest_tables(
        self, tables: Mapping[str, pd.DataFrame], *, source_name: str = "", validate_first: bool = True
    ) -> IngestionResult: ...
```

Using a separate protocol keeps `Ingester` unchanged, so existing ingesters and `isinstance` checks keep working. A caller detects support with `isinstance(ingester, TableSourceIngester)`.

`IngesterMetadata.supported_formats` stays about file formats. Once workbook input is retired, `sead_change_request` reports an empty list. Table support is discovered through the protocol check.

In `sead_change_request`:

- The table methods build a `SourceTableBundle` through the adapter.
- The table methods use the existing post-resolution validation and ingestion checks, including result construction, preconditions, collision checks, SQL rendering, and artifact writing.
- The file-oriented `validate()` and `ingest()` methods return input failures for `sead_change_request` without resolving a source or consulting `config.extra`. The source resolver also rejects `Path` or `str` before checking `config.extra["source_bundle"]` or `config.extra["tables"]`, so a path cannot select hidden table input. The shared file routes and service reject this key before source resolution.

### 3. Define the in-memory handoff

Add one adapter in `ingesters/sead_change_request/` that copies and sanitizes the tables, then uses the existing bundle validation. Its rules are:

| Input | In-memory behavior |
|---|---|
| Table names | Keep `TableStore` entity names unchanged; reject empty or non-string names. Do not apply Excel sheet-name rules. |
| Column names | Apply `sanitize_columns` to each copied frame, as the Excel read path does after parsing the workbook. |
| Empty mapping or non-DataFrame value | Reject with `SourceBundleError`. |
| Values and dtypes | Preserve the normalized DataFrame values and dtypes; do not imitate `pd.read_excel()` type inference or missing-value conversion. |
| Timezone-aware datetimes | Preserve timezone information in the bundle. Verify downstream rendering before supporting such columns in an ingest run. |
| `data_table_index` | Do not skip an entity with this name; the skip is a rule of the Excel reader. |
| `source_name` | Use a diagnostic label such as `project:<project-name>`; never interpret it as a source path. |

Each table name identifies an entry in `TargetModel.entities`; planning reports an unknown entity name as an error. SQL generation uses that entity's `target_table` when set, otherwise the entity name. The in-memory handoff preserves normalized entity names and values. Representative workbook fixtures document conversion differences that could affect business keys or generated change-request data.

### 4. Compose the two operations in the backend

Add one internal helper that:

1. receives an `AuthorizedResource` for the saved project and rejects an invalid authorization before loading the project or accessing data;
2. loads the authorized project through the existing service and `ProjectMapper.to_core()`, validates its configuration, then runs the no-write normalization step with the requested options only if validation passes;
3. selects trusted ingester inputs from the authorized project and backend settings, then constructs `IngesterConfig` and injects runtime dependencies;
4. checks `TableSourceIngester`, calls `validate_tables` or `ingest_tables`, and returns that result with entity and row counts; an ingester without table support gets a clear file-input-required error.

The helper accepts the `AuthorizedResource` and a typed project request. Before loading the project, mapping it, normalizing tables, constructing a database checker, or writing files, it verifies that the authorization input is an `AuthorizedResource`, its resource is a `PROJECT`, its action is `EXECUTE`, its lifecycle state is `active`, and its locator is non-empty and exactly matches the request's top-level `project_name`. It raises `PermissionError` if any check fails. It uses only `authorized_project.resource.locator` to load the saved project and build trusted context. This mirrors the guard already used by `ExecuteService` and prevents a direct caller from substituting another project name.

After `ProjectMapper.to_core()`, the helper always runs `CompositeProjectSpecification(core_project.cfg)`, as `ExecuteService` does when `run_validation` is true. Neither project-only request nor a direct helper call can skip this check. A failed specification or validation exception stops before normalization, ingester validation or ingestion, SIMS access, or bundle writing. The project-only validate route returns `ValidateResponse(is_valid=False)` with the specification errors in `errors`; the ingest route returns `IngestResponse(success=False, records_processed=0, message="Project validation failed", output_path=None)` with those errors in `error_details`. A validator exception becomes a validation error, as in `ExecuteService`; if the specification fails without an error message, both responses use `Project configuration validation failed`. Warnings alone do not block the run and appear in the validate response's `warnings`. Ingester data validation remains a separate later check, and the project-only ingest path keeps `validate_first=True` so a failed ingester validation also prevents artifact generation.

No source workbook is created or read by this helper. Ingestion still writes its deploy artifact bundle. The helper alone is an internal capability; it does not give an operator a request path.

Add `POST /api/v1/ingesters/sead_change_request/from-project/validate` and `POST /api/v1/ingesters/sead_change_request/from-project/ingest`. Both routes use `require_project(Action.EXECUTE, body_locator=True)` to authorize the top-level `project_name` and pass its `AuthorizedResource` to the helper. The validate route returns `ValidateResponse`; the ingest route returns `IngestResponse`. The route dependency supplies authentication and the project decision; the helper independently checks the authorized resource before doing work.

The project request models accept `project_name`; the existing workflow options `translate`, `drop_foreign_keys`, and `default_entity`; a typed submission context limited to `submission_name`, `timestamp`, `datatype`, `identifier`, `description`, `issue_identifier`, `author`, and optional `run_id`; and an optional supported `deploy_strategy` name. The backend derives the ingester's `submission_name` and `data_types` from that context. It supplies `project_name` and provider identity inside the ingester's submission context from the authorized project, not from nested caller fields. The models reject unknown top-level and nested fields. They do not accept `source`, `output_folder`, `config`, `database`, `target_model`, `run_validation`, `validate_first`, or injected collaborators.

Before calling `_create_config()` or its runtime injection functions, the helper builds a new configuration from these sources:

| Ingester input | Trusted source for a project-only run |
|---|---|
| `target_model` | The authorized saved project's resolved `metadata.target_model`, obtained through `ProjectMapper.to_core()` and validated as a `TargetModel`. A missing or invalid model fails the run. |
| `trusted_project_context` | `ProjectDataProviderService` applied to the same authorized saved project. Caller metadata cannot replace the provider scope, provider ID, or business keys. |
| Target database connection | Dedicated backend deployment settings for the Change Request target connection. The request and project data-source definitions cannot select it. A missing connection fails validation and ingestion before SIMS work or bundle writing. |
| `output_folder` | A backend-owned `INGEST_OUTPUT_DIR` setting, never a request field. This handoff provides the managed root; the companion proposal adds the exclusive per-run folder and no-replacement writer rule before removing the application permission. |
| Submission options | Only the named request fields above, checked before they are copied into `IngesterConfig`. Runtime clients and database checkers are injected afterward from backend-owned settings. |

The helper never forwards `request.config` or an arbitrary extras mapping to `_create_config()`. It rejects a project request that tries to provide a target model, database, output path, source path, project identity override, or runtime collaborator, including through nested input.

This handoff delivers the project-only routes behind `require_application_action(Action.RUN_INGESTERS)` as well as the project dependency. Until the companion's output and database rules ship, the helper uses its required, constructor-injected `AuthorizationService` to check `can_perform_application_action(authorized_project.principal, Action.RUN_INGESTERS)` after the project-resource guard and before any work. A direct call therefore cannot bypass the interim application gate. [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) later removes that check from the project-only helper and routes, after its exclusive managed-output and read-only target-database rules are in force. The helper's `AuthorizedResource` check remains. The existing `/{key}/validate` and `/{key}/ingest` file routes continue to require `application:run_ingesters` for other ingesters. They reject `sead_change_request` file requests regardless of permission; the file-oriented service and ingester methods reject the same input before reading a path. No key-based permission exemption is applied to the shared routes.

The operator client sends Change Request validation and ingestion for a saved project to the project-only routes, without a `source` value. File-only ingesters continue to use the existing source-path routes. The companion proposal adds one persistent `run_id` per submission attempt to these project requests.

### 5. Treat the deploy bundle as the audit record

Do not write an Excel workbook per call for traceability. The bundle is a stronger record of the handover, and it covers a scope the workbook cannot.

Verified in `ingesters/sead_change_request/sql_builder.py` and `artifact_writer.py`. Each bundle contains `deploy/`, `revert/`, and `verify/` SQL files, `manifest.json`, and gzipped TSV payloads of the rows the deploy SQL inserts. The manifest records the submission context, emitted table order, per-table row counts, statement count, payload format, and a `sha256` checksum per payload file.

The two artifacts have different scopes, which is the point:

| Artifact | Records |
|---|---|
| Deploy bundle | The rows and statements handed to the target, checksummed and replayable. Rows the change request does not emit are absent. |
| Dispatched workbook | Every normalized row and column for the project at that moment, including rows the target path excludes, but after Excel converts names, types, and timezones. |

So a workbook is not a superset of the bundle's audit value, and it is a less faithful record than the data it came from. A per-call workbook adds volume and Excel conversions without adding a guarantee the bundle lacks.

If source-level reproducibility is later required, that is a provenance question, not a workbook question: record the project configuration version, source references, and run identifiers. Materializing normalized tables is a debugging aid at most; if it is added, it should be labelled a debug snapshot rather than an audit record.

This proposal does not choose where bundle output lives. That is the managed output location decision in [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md). Projects currently have `data/`, `materialized/`, and `backups/` sub-folders and no `output/` folder; any new sub-folder would be that decision, and would need containment through `resolve_contained_path`.

## Alternatives Considered

**Return the `ShapeShifter` from the existing `workflow()`.** Rejected as the no-write contract. `workflow()` would still call `store()` before returning, so its return value alone would not remove the Excel workbook. A shared no-write step also keeps option handling in one place.

**A `memory` dispatcher registered in `Dispatchers`.** Rejected. `IDispatcher.dispatch` returns `None`, and the registry is shown as selectable output modes through `ExecuteService.get_dispatchers()`. A non-writing mode would appear as an output option without an artifact.

**Accept tables through `config.extra["tables"]`.** Rejected as the public capability. The branch exists, but it skips column sanitization and hides the table-input contract in an extras dict.

**Widen `Ingester.ingest()` to accept paths or tables.** Rejected. It would change the shared contract for file-only ingesters.

**Add a project mode to the shared file routes.** Rejected. Their request models require `source`, and their shared permission dependency cannot distinguish a file request from a project request by ingester key alone. Separate routes keep the no-source contract and permission rule explicit.

**Replace ingestion with a `deploy` dispatcher and drop the ingester.** Rejected as a way to get one path. Dispatchers live in `src/dispatch.py`, and `src/` must not import `ingesters/` or `backend/`, so a deploy dispatcher would still have to receive an ingester from the backend layer. That is the composition helper this proposal already adds, under a different name. Two contracts also do not fit: `IDispatcher.dispatch()` returns `None`, while validation and ingestion return errors, warnings, and a pending-confirmation report that an operator must act on. `Dispatchers.items` is listed directly as the selectable output set and has no validate-only mode and no `application:run_ingesters` check. Removing ingestion would additionally delete the `/ingesters` routes, their request and response models, `IngesterService`, and the UI, none of which this proposal scopes.

The shared in-memory tables do allow one output selection later: a single backend concept that offers either a dispatcher or a table-source ingester as the sink. That is a backend wrapper over both extension points, not a move of ingester logic into `src/dispatch.py`, and it needs its own authorization design. It is a follow-up decision, not part of this work.

## Risks And Tradeoffs

- **Memory.** Normalized tables, adapter copies, and ingester-derived tables coexist. Large projects may need more peak memory.
- **Different values after Excel.** The in-memory path preserves values that Excel changes. Tests should use representative workbook fixtures to document the differences, especially for business keys, without keeping workbook ingestion available.
- **Timezone support needs verification.** Preserving timezone-aware values does not establish that every target column and SQL renderer handles them. If a value cannot be rendered correctly, the table path must reject it clearly rather than silently dropping the timezone.
- **Change Request generation is unavailable until the project-only path ships.** Immediate retirement of the unused workbook input leaves no Change Request generation entry point for that interval.
- **The project-only request path adds two endpoints.** Separate routes make the permission rule clear, but the companion task plan and operator client must use those routes before the permission exception is useful.
- **Saved project and target database can disagree.** The project target model and backend target connection are selected independently. If required model data, connection settings, or provider-row confirmation are missing or invalid, the project-only run fails; it does not fall back to caller configuration.

## Testing And Validation

- Test adapter copies, column sanitization, invalid table names, empty input, non-DataFrame values, and preservation of values, dtypes, and timezones.
- Verify the adapter retains normalized entity names and row counts, and SQL uses each entity's `target_table` or the entity-name fallback. Do not invoke retired workbook ingestion.
- Use fixtures containing leading-zero text, `"NA"`, empty strings, nullable integers, and timezone-aware datetimes to verify that the in-memory path preserves normalized data and to document differences from Excel. Check business-key decisions and generated artifact content where those differences matter.
- Verify `translate` and `drop_foreign_keys` yield the same normalized tables for the file-writing workflow and the no-write step.
- Verify both project-only routes and direct helper calls run `CompositeProjectSpecification` on the mapped project. For an invalid project or specification exception, validation returns `is_valid=False` with errors and ingestion returns `success=False`, zero processed records, and error details. Neither path normalizes data, calls ingester methods or SIMS, or writes a bundle. Confirm a project with warnings only continues and the project-only ingest path cannot disable ingester validation.
- Verify table validation and ingestion run the existing post-preparation checks, including `validate_first`, preconditions, collision checks, and artifact generation. Check that unsupported timezone values fail clearly if downstream rendering cannot preserve them.
- Call the helper directly with no authorization, the wrong action, the wrong resource type, an inactive resource, an empty locator, and a locator that differs from the request's `project_name`. Each call must raise `PermissionError` before project loading, mapping, normalization, database access, SIMS access, or file writing. Confirm an accepted call loads only the authorized locator and rejects an ingester without table support.
- Before the companion permission change, verify a direct helper call by a project executor without `application:run_ingesters` is denied before any work. After that change, verify project-only calls no longer require the application action, while all invalid project-resource cases remain denied.
- Verify both project-only routes reject a caller-supplied `source` or nested configuration, reject unauthenticated callers and callers without `project:execute`, and call the helper with the authorized project. Until the companion permission change ships, both routes also reject callers without `application:run_ingesters`.
- Verify the helper uses the mapped saved project's target model and trusted project context, the backend target connection, and `INGEST_OUTPUT_DIR`. Reject top-level or nested attempts to set target model, database, output path, provider identity, or injected collaborators. Confirm missing trusted inputs fail before SIMS access or file writing.
- Verify named submission options reach the ingester, and backend runtime injection runs after trusted input selection.
- Verify `sead_change_request` reports no supported file formats and its file methods fail at the shared routes, service, and ingester entry points before source resolution, even when `config.extra` contains `source_bundle` or `tables` and the caller holds `application:run_ingesters`. Verify the resolver rejects a `Path` or `str` before consulting those extras. Move tests that use fake workbook paths or direct bundles to exercise in-memory behavior onto the table methods or direct bundle preparation, as appropriate. Other ingesters retain their file-route permission check. Verify the operator client uses project-only routes with only the named fields and no `source` or arbitrary `config`.
- Confirm existing `workflow()` output, shared file request and response models, and file ingestion for other ingesters remain unchanged.

## Acceptance Criteria

- `P-AC-1` The no-write normalization step returns a completed `ShapeShifter` after applying the requested options, without requiring an output target or invoking a dispatcher. Existing `workflow()` callers still get the same output and `None` return value.
- `P-AC-2` Table-input support is discoverable through a protocol check. `Ingester`, `IngestRequest`, `IngestResponse`, `ValidateRequest`, and `ValidateResponse` are unchanged.
- `P-AC-3` The adapter passes copied tables with unchanged entity names and sanitized column names to the ingester while preserving normalized values, dtypes, and timezones. It rejects invalid input with `SourceBundleError`.
- `P-AC-4` Representative fixtures establish how normalized tables differ from workbook-parsed values, dtypes, or timezones. The table path preserves the normalized values used for business keys and generated change-request data.
- `P-AC-5` The composed operation creates and reads no source workbook; `source_name` is diagnostic only. Successful ingestion may still write its deploy artifact bundle.
- `P-AC-6` Retire `sead_change_request` file validation and ingestion immediately, before the project-only path ships. Its metadata reports no supported file formats. The shared file routes and service reject that key regardless of role; its file-oriented methods fail before source resolution, and the resolver rejects `Path` or `str` before consulting `config.extra`, even when it contains in-memory tables. The later table methods provide the supported input. Other ingesters and Excel dispatch keep their existing behavior. No source-containment work is planned for the retired Change Request input.
- `P-AC-7` An ingester that does not support table input is rejected by the composition helper with an error that names the required file input.
- `P-AC-8` Table validation and ingestion use the existing post-preparation checks. Separate project-only validate and ingest routes accept no caller source path or arbitrary config, obtain an authenticated project's `AuthorizedResource` through `require_project(Action.EXECUTE, body_locator=True)`, and pass it to the helper. Both routes initially require `application:run_ingesters`. Existing file routes retain that requirement for other ingesters and reject `sead_change_request`.
- `P-AC-9` The composed operation writes no Excel workbook, and the deploy artifact bundle remains the only audit record for a run.
- `P-AC-10` The operator client uses the project-only routes for saved-project Change Request validation and ingestion and sends only the named fields, with no `source` or arbitrary `config`. File-only ingesters continue to use the existing routes.
- `P-AC-11` For project-only validation and ingestion, the helper builds `IngesterConfig` from the mapped authorized project's target model and trusted project context, backend-owned target-database settings and `INGEST_OUTPUT_DIR`, and only the named submission options. It rejects caller overrides, fails when required trusted inputs are missing, and injects runtime dependencies after selecting those inputs. The application-permission exception cannot be enabled until the companion's exclusive output and read-only database rules apply.
- `P-AC-12` Direct project-only helper calls require an `AuthorizedResource` with `Action.EXECUTE`, an active `ResourceType.PROJECT`, and a non-empty locator matching the request's `project_name`. Invalid inputs raise `PermissionError` before loading or mapping a project, normalization, database or SIMS access, or file writing. During the handoff stage, direct calls also require `Action.RUN_INGESTERS` through the authorization service. The companion removes only that application check after its output and database rules ship; the project-resource guard remains.
- `P-AC-13` Both project-only routes and direct helper calls require `CompositeProjectSpecification` to pass on the mapped saved project before normalization or ingester work. No request option can skip it. A failure or validation exception returns project errors in `ValidateResponse(is_valid=False)` or `IngestResponse(success=False, records_processed=0, message="Project validation failed", output_path=None, error_details=...)`; it performs no normalization, ingester call, SIMS access, or bundle writing. Warnings alone do not block. The project-only ingest path also keeps ingester data validation enabled and stops before artifact generation if it fails.

## Planning Handoff

Confirmed decisions:

- Add a shared no-write normalization step; keep `workflow()` file-writing and its return value unchanged. Do not add a `memory` dispatcher.
- Use a separate `TableSourceIngester` protocol; do not widen `Ingester.ingest()`.
- Define the handoff through one adapter in `ingesters/sead_change_request/` and reuse existing bundle validation.
- Preserve normalized values, dtypes, and timezones rather than imitating Excel conversions. Use workbook fixtures only to document differences; do not keep Change Request workbook ingestion available for comparison.
- Reuse the existing post-resolution validation and ingestion checks for table input.
- Expose separate project-only validate and ingest routes in this work. Their strict request models exclude source paths and arbitrary config. Each route uses `require_project(Action.EXECUTE, body_locator=True)` and initially requires `application:run_ingesters`. The helper checks the supplied `AuthorizedResource`, its locator, and the interim application action before any work. The companion proposal removes the application check from the helper and these routes after its output and database rules are in force.
- Validate the mapped saved project with `CompositeProjectSpecification` on every project-only request and direct helper call. Do not expose a `run_validation` or `validate_first` bypass. Return the existing response models with project errors and stop before normalization or ingester work when validation fails.
- Derive the target model and trusted context from the mapped authorized project; add backend-owned target-database settings and the `INGEST_OUTPUT_DIR` managed root for project-only runs. Copy only typed submission options into the new config, then inject runtime collaborators. Do not reuse the file route's caller `config` dictionary.
- Treat the deploy artifact bundle as the audit record for a run. Do not write an Excel workbook per call; do not add an `output/` folder to project folders in this work.
- Retire `sead_change_request` file input before delivering the project-only path. Advertise no file formats and reject file-oriented calls at the routes, service, and ingester before source resolution; reject `Path` or `str` before extras in the resolver. Keep in-memory input on the table methods.

Constraints and behavior to preserve:

- `src/` must not import `backend/` or `ingesters/`. The adapter belongs in `ingesters/`, which may import `src/utility.sanitize_columns`.
- Existing shared file request and response models and file behavior for other ingesters remain unchanged. The new project request models reject extra fields.
- The backend uses `ProjectMapper.to_core()` for the saved project and may reuse `_create_config()` and runtime injection only after constructing server-selected inputs.
- Ingestion still writes its deploy artifact bundle; the removed file operation is the intermediate source workbook.

Expected validation outcomes:

- Fixtures document the relevant Excel conversion differences, while the table path preserves normalized values.
- The no-write step and `workflow()` apply options identically. Existing execute and other-ingester file tests keep their behavior; Change Request tests using the retired file methods for in-memory data move to table methods or direct bundle preparation.
- Invalid project configuration blocks both project-only routes before normalization and ingester work and returns project errors in the existing response models; ingester data validation remains mandatory for project-only ingestion.
- Route and direct helper calls reject missing, wrong-action, wrong-type, inactive, or mismatched project authorization before project loading, normalization, database access, or file writing. The interim application check also runs before work and is removed only for the composed path by the companion.
- The operator client sends no source path for a saved-project Change Request run. After the companion permission change, a project executor without `application:run_ingesters` can use the project-only routes. Change Request file requests remain rejected regardless of role.
- Project-only runs reject caller config overrides and use the authorized project's target model, backend target connection, and managed output root. Missing or invalid trusted inputs fail before SIMS access or bundle writing.

The companion Phase 1 task `T1.1` removes the application gate only from these dedicated routes and their helper after its output and database rules apply. Its client task `T1.6` sends the one-attempt `run_id` through the project-only validation and ingestion requests.

Open questions:

- Which target columns and SQL renderers support timezone-aware datetimes? Resolve before completing the table capability; reject unsupported values clearly.
- Should one backend output selection later cover both dispatchers and table-source ingesters? Decide before adding a deploy-artifact sink; this proposal keeps the two extension points separate.

## Final Recommendation

Retire Change Request workbook input now, then proceed with a shared no-write normalization step, an explicit table-input capability, and a backend helper reached through dedicated project-only validation and ingest routes. Build its ingester config from the authorized project, backend settings, and named submission options. Route the operator's saved-project Change Request flow through the new requests. Treat the normalized DataFrames as the source of data for the in-memory path and document the intended differences from Excel with fixtures.
