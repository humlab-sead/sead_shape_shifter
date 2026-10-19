# Hand Normalized Tables To The Ingester In Memory

These are the two main paths for outputing normalized data in Shape Shifter:

Dispatch: backend → workflow → normalize → dispatcher → output file
Ingestion: backend helper → normalize → tables → ingester → deploy artifact

## Status

- Proposed feature
- Scope: a reusable normalization step, an optional table-input capability for ingesters, handoff rules, and one backend composition helper
- Goal: run normalization and change-request generation in one process without writing and re-reading an Excel workbook
- Depends on [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) for the permission that governs Change Request bundle creation; this proposal does not set that permission

## Summary

The backend currently hands normalized data to the change-request ingester through an Excel workbook. `workflow()` always writes its output, while the ingester reads a caller-supplied file path. Excel changes some names, types, and values during that round trip.

Recommend a shared normalization step that returns the completed `ShapeShifter` without dispatching, plus an explicit table-input capability on the ingester. The backend helper uses these two interfaces and retains the current ingester authorization and configuration rules. The file-writing `workflow()` stays unchanged for dispatch. The Excel input to `sead_change_request` stays permitted until R3 closes, but the composed path replaces it as the operator path.

## Problem

A backend caller that wants to run normalization and change-request generation together currently has to:

1. run `workflow()` with the `xlsx` dispatcher so a workbook is written;
2. find the output path;
3. pass that path to the ingester.

Lower-level calls can already reach the DataFrame-based ingester contract, but they do not provide a supported composition path with the same normalization options and ingester checks.

**The handoff changes data.** The `xlsx` dispatcher removes timezone information, and `pd.read_excel()` infers types and missing values. For example, a text business key such as `"001"` can become the number `1`, and `"NA"` can become null. The separate `openpyxl` dispatcher can also rewrite sheet names. The change-request ingester sanitizes column names after reading the workbook.

**The composed path would require a source-file read.** `_load_source_bundle_from_path` accepts any readable path with a `.xlsx`/`.xls` suffix and has no containment check. [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) records that issue as R3. This proposal avoids that read in the composed operation; it does not close R3 for file input.

**The Excel workbook is the thing being replaced.** For `sead_change_request`, reading a dispatched workbook is not a convenience kept for operators or a format choice. It is the only current trigger for change-request generation, and it is the route that carries the unconstrained read. Being permitted until R3 closes does not make it the preferred operator path. After the composed path exists, it is a transitional input, not a supported way to work.

**No ingester will need Excel input once `sead` is gone.** `sead_change_request` is the only ingester this proposal changes. The other registered ingester, `sead`, is a file-only direct-to-database importer that is separately deprecated and scheduled for removal ([#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569)). The file-writing `workflow()` and the `xlsx` dispatcher stay unchanged, so dispatched workbooks remain available for review and for any future file-only ingester; they stop being the change-request trigger.

**The existing workflow always writes.** `ShapeShifter.normalize()` exposes the tables, but a caller that bypasses `workflow()` must repeat its `drop_foreign_keys` and `translate` option handling.

## Scope

- A Core normalization step that applies the same options as `workflow()` and returns the completed entity tables without dispatching them.
- An additive, optional table-input capability on the ingester protocol, implemented by `sead_change_request`.
- One adapter that converts normalized tables into the ingester's source bundle without Excel conversions.
- One backend composition helper that runs normalization and ingestion for an authorized project.

## Non-Goals

- Removing or restricting the Excel input path everywhere. Its status depends on the ingester: for `sead_change_request` it is the path being replaced and becomes transitional once the composed path exists, staying permitted only until R3 closes; for the deprecated `sead` ingester it is still required and disappears with that ingester ([#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569)). The `xlsx` and `openpyxl` dispatchers are unchanged.
- Writing an Excel workbook per composed call as an audit artifact. The deploy artifact bundle is the audit record; see Proposed Design §5.
- Closing R3. The path branch of `_resolve_source_bundle` keeps its current behavior. This proposal removes the filesystem read from the programmatic pipeline, not from the upload route.
- Changing `IngestRequest`, `IngestResponse`, `ValidateRequest`, or `ValidateResponse`.
- Adding an HTTP endpoint or UI control for the composed operation.
- Removing the ingester or routing ingestion through a dispatcher. The ingester stays a separate extension point with its own authorization and validation rules.
- Eliminating all filesystem activity. Normalization may read configured sources, and successful ingestion still writes a deploy artifact bundle.
- Introducing a streamed or chunked handoff. Tables stay in memory as DataFrames.

## Current Behavior

Verified in the repository:

- `ShapeShifter.normalize()` returns `self`, and completed tables are available in `self.table_store` (`src/normalizer.py`, `src/table_store.py`).
- `ShapeShifter.store()` resolves a dispatcher and calls `dispatcher.dispatch(target=..., data=self.table_store)` (`src/normalizer.py`). `IDispatcher.dispatch` returns `None` (`src/dispatch.py`).
- `workflow()` resolves the project, runs `normalize()`, applies optional `drop_foreign_keys` and `translate` steps, then unconditionally calls `store()` and `log_shapes()`. It returns `None` (`src/workflow.py`).
- `_resolve_source_bundle` already accepts a `SourceTableBundle`, a `SourceTableBundle` under `config.extra["source_bundle"]`, a raw table mapping, or a `Path`/`str` (`ingesters/sead_change_request/input_resolution.py`). The mapping branch calls `_build_source_bundle`, which validates types only and does not sanitize columns.
- The path branch accepts `.xlsx`/`.xls`, reads each usable sheet with `pd.read_excel()`, sanitizes its columns, and skips `data_table_index`. Pandas may change dtypes and values while reading Excel.
- The shared `Ingester` protocol accepts paths. `SeadChangeRequestIngester` passes its source to `resolve_inputs`, but `validate()` and `ingest()` each perform work after shared preparation (`backend/app/ingesters/protocol.py`, `ingesters/sead_change_request/ingester.py`).
- The current ingester route checks both `application:run_ingesters` and project `execute` authorization. `IngesterService` supplies trusted project context and runtime dependencies (`backend/app/api/v1/endpoints/ingesters.py`, `backend/app/services/ingester_service.py`).

The gaps are a no-write normalization step with shared option handling, an explicit ingester capability, and defined rules for differences from Excel.

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

`IngesterMetadata.supported_formats` stays about file formats. Capability discovery uses the protocol check, not metadata.

In `sead_change_request`:

- The table methods build a `SourceTableBundle` through the adapter.
- File and table methods share the complete validation and ingestion flows after source resolution, including result construction, preconditions, collision checks, SQL rendering, and artifact writing. Shared preparation alone does not perform all of those steps.
- File input keeps its existing `.xlsx`/`.xls` restriction and behavior.

### 3. Define the in-memory handoff

Add one adapter in `ingesters/sead_change_request/` that copies and sanitizes the tables, then uses the existing bundle validation. Its rules are:

| Input | In-memory behavior |
|---|---|
| Table names | Keep `TableStore` entity names unchanged; reject empty or non-string names. |
| Column names | Apply `sanitize_columns` to each copied frame, as the Excel read path does after parsing the workbook. |
| Empty mapping or non-DataFrame value | Reject with `SourceBundleError`. |
| Values and dtypes | Preserve the normalized DataFrame values and dtypes; do not imitate `pd.read_excel()` type inference or missing-value conversion. |
| Timezone-aware datetimes | Preserve timezone information in the bundle. Verify downstream rendering before supporting such columns in an ingest run. |
| `data_table_index` | Do not skip an entity with this name; the skip is a rule of the Excel reader. |
| `source_name` | Use a diagnostic label such as `project:<project-name>`; never interpret it as a source path. |

The adapter does not promise byte-for-byte equality with an Excel round trip. For Excel-representable values and safe table and column names, the two input methods should produce the same ingester decisions. Where Excel changes a value, dtype, timezone, or sheet name, the in-memory input retains the normalized value or name. These differences are intentional and must be covered by tests, especially for business keys and generated change-request data.

### 4. Compose the two operations in the backend

Add one internal helper that:

1. requires project `execute` authorization for the saved project; the application-level permission for Change Request bundle creation follows [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) and is not fixed here;
2. loads the authorized project through the existing service and `ProjectMapper.to_core()`, then runs the no-write normalization step with the requested options;
3. constructs the ingester through the existing configuration path so trusted project context, target-model input, submission options, and runtime dependencies are supplied as they are for file input;
4. checks `TableSourceIngester`, calls `validate_tables` or `ingest_tables`, and returns that result with entity and row counts; an ingester without table support gets a clear file-input-required error.

No source workbook is created or read by this helper. Ingestion still writes its deploy artifact bundle. Any future HTTP route is a separate decision and must apply the authorization policy approved for that route.

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

**Replace ingestion with a `deploy` dispatcher and drop the ingester.** Rejected as a way to get one path. Dispatchers live in `src/dispatch.py`, and `src/` must not import `ingesters/` or `backend/`, so a deploy dispatcher would still have to receive an ingester from the backend layer. That is the composition helper this proposal already adds, under a different name. Two contracts also do not fit: `IDispatcher.dispatch()` returns `None`, while validation and ingestion return errors, warnings, and a pending-confirmation report that an operator must act on. `Dispatchers.items` is listed directly as the selectable output set and has no validate-only mode and no `application:run_ingesters` check. Removing ingestion would additionally delete the `/ingesters` routes, their request and response models, `IngesterService`, and the UI, none of which this proposal scopes.

The shared in-memory tables do allow one output selection later: a single backend concept that offers either a dispatcher or a table-source ingester as the sink. That is a backend wrapper over both extension points, not a move of ingester logic into `src/dispatch.py`, and it needs its own authorization design. It is a follow-up decision, not part of this work.

## Risks And Tradeoffs

- **Memory.** Normalized tables, adapter copies, and ingester-derived tables coexist. Large projects may need more peak memory.
- **Different values after Excel.** The in-memory path preserves values that Excel changes. This can change business-key resolution, validation, or generated SQL compared with a workbook run. Tests must show both agreement for Excel-representable values and the intended differences for lossy values.
- **Input rules can drift.** The Excel reader and adapter both sanitize columns. A shared compatibility test should detect changes to either path.
- **Timezone support needs verification.** Preserving timezone-aware values does not establish that every target column and SQL renderer handles them. If a value cannot be rendered correctly, the table path must reject it clearly rather than silently dropping the timezone.
- **The existing file-input exposure remains.** R3 and the current path branch are unchanged. The composed helper removes only its source-workbook read.

## Testing And Validation

- Test adapter copies, column sanitization, invalid table names, empty input, non-DataFrame values, and preservation of values, dtypes, and timezones.
- Run an Excel-representable fixture through both input methods with the same project, options, submission context, and injected collaborators. Compare table names, sanitized columns, row counts, values, and meaningful validation and ingestion outcomes. Ignore path-specific diagnostic labels and artifact locations.
- Use fixtures containing leading-zero text, `"NA"`, empty strings, nullable integers, and timezone-aware datetimes to verify that the in-memory path preserves normalized data and to document differences from Excel. Check business-key decisions and generated artifact content where those differences matter.
- Verify `translate` and `drop_foreign_keys` yield the same normalized tables for the file-writing workflow and the no-write step.
- Verify file and table methods run the same post-preparation checks, including `validate_first`, preconditions, collision checks, and artifact generation. Check that unsupported timezone values fail clearly if downstream rendering cannot preserve them.
- Verify the helper rejects a missing project-execute authorization, avoids source-workbook creation and reads, and rejects ingesters without table support.
- Confirm existing `workflow()` output, request and response payloads, and `.xlsx`/`.xls` change-request ingestion remain unchanged.

## Acceptance Criteria

- `P-AC-1` The no-write normalization step returns a completed `ShapeShifter` after applying the requested options, without requiring an output target or invoking a dispatcher. Existing `workflow()` callers still get the same output and `None` return value.
- `P-AC-2` Table-input support is discoverable through a protocol check. `Ingester`, `IngestRequest`, `IngestResponse`, `ValidateRequest`, and `ValidateResponse` are unchanged.
- `P-AC-3` The adapter passes copied tables with sanitized column names to the ingester while preserving normalized values, dtypes, and timezones. It rejects invalid input with `SourceBundleError`.
- `P-AC-4` For Excel-representable values and safe names, both methods produce equivalent ingester decisions and generated change-request data. Tests establish the intended differences where Excel changes values, dtypes, timezones, or names.
- `P-AC-5` The composed operation creates and reads no source workbook; `source_name` is diagnostic only. Successful ingestion may still write its deploy artifact bundle.
- `P-AC-6` The Excel input path keeps its current behavior, including the `.xlsx`/`.xls` restriction. It remains permitted for `sead_change_request` until R3 closes, but it is a transitional input, not the operator path, once the composed path ships.
- `P-AC-7` An ingester that does not support table input is rejected by the composition helper with an error that names the required file input.
- `P-AC-8` File and table methods use the same post-preparation validation and ingestion checks. The helper requires project-execute authorization for the saved project, inherits the application-level permission approved for Change Request bundle creation, and supplies the same trusted project context and runtime dependencies as file input.
- `P-AC-9` The composed operation writes no Excel workbook, and the deploy artifact bundle remains the only audit record for a run.

## Planning Handoff

Confirmed decisions:

- Add a shared no-write normalization step; keep `workflow()` file-writing and its return value unchanged. Do not add a `memory` dispatcher.
- Use a separate `TableSourceIngester` protocol; do not widen `Ingester.ingest()`.
- Define the handoff through one adapter in `ingesters/sead_change_request/` and reuse existing bundle validation.
- Preserve normalized values, dtypes, and timezones rather than imitating Excel conversions. Compare decisions on Excel-representable inputs and test intentional differences separately.
- Keep file and table entry points on the same full validation and ingestion flows.
- Expose no HTTP route in this work. The internal helper applies project `execute` authorization and inherits the application-level permission approved for Change Request bundle creation in [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md).
- Treat the deploy artifact bundle as the audit record for a run. Do not write an Excel workbook per call; do not add an `output/` folder to project folders in this work.
- Treat the Excel input to `sead_change_request` as transitional: permitted until R3 closes, no longer the operator path once the composed path exists.

Constraints and behavior to preserve:

- `src/` must not import `backend/` or `ingesters/`. The adapter belongs in `ingesters/`, which may import `src/utility.sanitize_columns`.
- API request and response models, file-based ingestion, and `_resolve_source_bundle` path behavior remain unchanged.
- The backend uses `ProjectMapper.to_core()` and the existing ingester configuration path for trusted context and runtime dependencies.
- Ingestion still writes its deploy artifact bundle; the removed file operation is the intermediate source workbook.

Expected validation outcomes:

- The file and table paths agree on Excel-representable fixtures and show documented differences on lossy Excel fixtures.
- The no-write step and `workflow()` apply options identically; existing execute and ingest tests pass unchanged.
- The project-execute check and the application-level permission approved for Change Request bundle creation are enforced before the composition helper runs normalization or ingestion.

Open questions:

- Which target columns and SQL renderers support timezone-aware datetimes? Resolve before completing the table capability; reject unsupported values clearly.
- Which interface, if any, should expose the composed operation later? Decide its authorization policy before a phase that adds a route.
- Should one backend output selection later cover both dispatchers and table-source ingesters? Decide before adding a deploy-artifact sink; this proposal keeps the two extension points separate.
- Should the `sead_change_request` Excel input be removed outright, or kept as a transitional route until R3 closes and `sead` is removed ([#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569))? Decide when the composed path ships; this proposal keeps the route working.

## Final Recommendation

Proceed with a shared no-write normalization step, an explicit table-input capability, and one backend helper that applies current authorization and ingester checks. Treat the normalized DataFrames as the source of data for the in-memory path, and test the intended differences from Excel rather than promising exact workbook parity.
