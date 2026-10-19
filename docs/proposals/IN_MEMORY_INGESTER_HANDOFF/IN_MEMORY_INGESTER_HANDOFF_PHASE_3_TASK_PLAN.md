# Accept Normalized Tables In The Change Request Ingester — Phase 3 Task Plan

## Phase Summary

**Goal:** Add an explicit in-memory table contract for `sead_change_request`, reuse its existing validation and ingestion flow, and render normalized date and datetime values without changing their calendar or clock fields.

**Readiness: Validated.** [Phase 3 of the handoff phase plan](./IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md#phase-3-accept-normalized-tables-in-the-change-request-ingester) is ready for a task plan. Its acceptance criteria and the user's timezone decision define the implementation. The [source proposal](./IN_MEMORY_INGESTER_HANDOFF.md) still contains an older open timezone question; this plan follows the resolved Phase 3 rule recorded in the phase plan.

**Constraints and dependencies:** Phases 1 and 2 are complete. Keep `Ingester`, shared file request and response models, and other ingesters' file input unchanged. Do not add routes or the backend project helper in this phase. Preserve timezone information in copied normalized DataFrames; remove it only when generating SQL and payload values. Use the target column with the same name as the input DataFrame column in `TargetModel.entities[entity].columns`; the SQL relation is `target_table` when present, otherwise the entity name.

**Acceptance criteria**

1. `PH3-AC-1` (from `P-AC-2`): A protocol check discovers table support without changing the shared `Ingester` protocol or shared file request and response models.
2. `PH3-AC-2` (from `P-AC-3`): The adapter copies valid tables, preserves normalized entity names and values, sanitizes columns, and rejects invalid input with `SourceBundleError`.
3. `PH3-AC-3` (from `P-AC-4`): Table-based business-key decisions and generated Change Request artifacts use normalized table values.
4. `PH3-AC-4` (from `P-AC-3`, `P-AC-8`): Table validation and ingestion run the existing post-preparation checks and preserve `validate_first`. Date and timestamp values retain their normalized calendar and clock fields in generated literals; timezone metadata is removed without conversion. Incompatible timezone-aware target columns fail clearly.

## Repository Findings

**Repository basis:** Branch `in-memory-ingester-handoff`, commit `323443e6`, planning date 2026-10-19. The uncommitted Phase 3 edits in the phase plan were treated as the approved source of scope and timezone behavior. Existing dirty `graphify-out/` files are navigation output and are not deliverables for this plan.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/ingesters/protocol.py::Ingester`; `backend/app/ingesters/__init__.py` | `Ingester` is a `runtime_checkable` protocol with file-oriented `validate()` and `ingest()` methods, re-exported from the package. | Add and re-export the proposal's separate `runtime_checkable` `TableSourceIngester`; leave `Ingester` and shared models unchanged. |
| `ingesters/sead_change_request/input_resolution.py::_build_source_bundle` | Accepts a `dict`, validates non-empty string table names and DataFrame values, and stores the original DataFrames without copying or sanitizing columns. | Extend the adapter to accept a `Mapping`, copy frames, sanitize copied column labels with `src.utility.sanitize_columns`, and retain entity names, values, dtypes, and timezones. |
| `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` | Public `validate()` and `ingest()` reject retired file input. `_validate_bundle()` and `_ingest_bundle()` contain the reusable preparation, result, precondition, collision, artifact, and write flow. | Add public table methods that adapt tables then delegate to the existing bundle methods; preserve structured errors and `validate_first`. |
| `src/target_model/models.py::ColumnSpec`, `EntitySpec`; `resources/target_models/sead_standard_model.yml` | `ColumnSpec.type` is an optional string. The standard model declares `date` columns but no timestamp type. The entity spec maps input entity names to target columns and optional target table names. | Check declared target type metadata when rendering temporal values. Use synthetic target models for timestamp and timezone-aware type cases; do not depend on a live database schema. |
| `ingesters/sead_change_request/sql_rendering.py::render_literal`; `sql_builder.py::InlineInsertDeployStrategy`, `CopyCsvDeployStrategy`, `InlineStagingDeployStrategy`; `inline_staging_sql.py` | `render_literal()` currently serializes aware datetimes with their offset. `copy_csv` has its own timestamp serializer. Inline staging calls shared literal rendering. | Apply one no-conversion rule across all three artifact strategies and reject explicitly timezone-aware target types before artifact writing. |
| `backend/tests/ingesters/test_ingester_infrastructure.py`, `test_sead_change_request_input_resolution.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_sql_builder.py` | These files test protocol registration, source resolution, bundle helpers, business-key behavior, and the three artifact strategies. Existing downstream tests call private bundle methods through helpers. | Extend focused tests and migrate downstream test helpers to the public table methods. Assert protocol discovery and literal values, not Excel parity. |
| `ingesters/sead_change_request/README.md`, `DIAGRAMS.md`, `backend/app/ingesters/README.md` | Documentation describes private bundle calls as the only in-memory path; the deploy-strategy list omits `inline_staging`. | Update the package and protocol documentation to describe the additive table capability and the three strategies accurately. |
| `docs/proposals/IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md`; Phase 3/4 in the phase plan | The proposal retains an earlier open question about timezone-aware rendering, and Phase 4 readiness still lists the timezone decision as a block. Phase 3 itself now resolves the rule and is marked ready. | This task plan follows the current Phase 3 rule. Record the stale status wording for later document cleanup; it does not change Phase 3 implementation. |

## Scope

**In scope**

- Add the optional `TableSourceIngester` protocol with the signatures specified in the source proposal.
- Adapt `Mapping[str, DataFrame]` inputs into copied, sanitized `SourceTableBundle` values and add public `validate_tables()` and `ingest_tables()` methods to `SeadChangeRequestIngester`.
- Keep normalized DataFrame values, dtypes, and timezone information intact through adaptation and existing preparation, business-key, and artifact-selection logic.
- Render `date` targets from the input calendar date. Render timezone-naive timestamp targets from the input calendar and clock fields, dropping timezone metadata without conversion. Reject explicitly timezone-aware target column types before writing an artifact bundle.
- Add or update protocol, adapter, table-method, business-key, and SQL strategy tests; update the affected ingester documentation.

**Out of scope**

- Changes to `Ingester`, shared file request/response models, Excel dispatch, other ingesters, Phase 4 backend helper, project routes, or frontend behavior.
- Reading database catalogs to infer target column types; the handoff names `TargetModel.entities[entity].columns` as the target-column description.
- Updating the source proposal or phase plan. The stale timezone question and Phase 4 readiness wording are noted for a later documentation update.
- Workbook comparison or parity tests. The retired Excel conversion behavior is not the expected result.

## Work Breakdown

### Area 1: Add the table capability and adapter

**Objective:** Callers can detect table support without changing the shared file protocol, and the Change Request adapter produces an independent, validated bundle.

**Affected code:** `backend/app/ingesters/protocol.py`; `ingesters/sead_change_request/input_resolution.py`; `src/utility.py::sanitize_columns` (existing helper).

**Dependencies:** None within Phase 3.

**Tasks:**

* [x] `T3.1` **Add:** Define and export the optional runtime-checkable table source protocol.
  * **Target:** `backend/app/ingesters/protocol.py::TableSourceIngester` (new protocol); `backend/app/ingesters/__init__.py` public exports.
  * **Current → required:** Only the runtime-checkable file-oriented `Ingester` protocol exists. Add a separate protocol with `validate_tables(tables: Mapping[str, pd.DataFrame], *, source_name: str = "")` and `ingest_tables(tables: Mapping[str, pd.DataFrame], *, source_name: str = "", validate_first: bool = True)`, returning the existing result types.
  * **Implementation:** Import `Mapping` and pandas types as needed. Keep the protocol structural and runtime-checkable, and re-export it beside `Ingester` from the package. Make no edits to `Ingester`, metadata, or shared request/response models.
  * **Constraints:** Table capability remains independent from `supported_formats`; do not add table methods to unrelated ingesters.
  * **Validation:** `V-1` — `SeadChangeRequestIngester` satisfies both `Ingester` and `TableSourceIngester`; `SeadIngester` satisfies `Ingester` but not `TableSourceIngester`.

* [x] `T3.2` **Adapt:** Copy and sanitize each input table before building the source bundle.
  * **Target:** `ingesters/sead_change_request/input_resolution.py::_build_source_bundle`, `_resolve_source_bundle`.
  * **Current → required:** The builder accepts only dictionaries and retains the caller's frame objects and column labels. It must accept the protocol's `Mapping`, copy each frame, sanitize only copied column labels, and preserve the original entity/table names.
  * **Implementation:** Keep rejecting empty mappings, blank or non-string table names, and non-DataFrame values with `SourceBundleError`. Store `source_name` as diagnostic metadata, never as a path. Use the existing `sanitize_columns()` helper so duplicate sanitized labels remain unique. Preserve values, dtypes, and timezone-aware values in the copied frames.
  * **Constraints:** Do not apply Excel sheet-name rules, skip `data_table_index`, infer types, or mutate caller-owned DataFrames. Do not change retired path rejection.
  * **Validation:** `V-2` — assert the table/entity names remain unchanged; sanitized columns are unique; source frames are unchanged; `pandas.testing.assert_frame_equal` confirms copied values and dtypes, including a timezone-aware column. Empty mapping, blank/non-string table names, and non-DataFrame values raise `SourceBundleError`.

**Completion evidence:** Runtime protocol checks distinguish the two capabilities, and the adapter returns copied, sanitized tables with input values and types intact.

### Area 2: Expose table validation and ingestion through the existing workflow

**Objective:** Public table methods run the existing preparation, validation, ingestion preconditions, and artifact flow while retaining the retired file contract.

**Affected code:** `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester`; tests in `backend/tests/ingesters/test_sead_change_request_ingester.py`, `test_sead_change_request_inline_staging.py`, and `test_sead_change_request_submission_sims_integration.py`.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T3.3` **Expose:** Implement `validate_tables()` and `ingest_tables()` and move downstream test callers onto them.
  * **Target:** `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester`; the three named test files and their bundle helper functions.
  * **Current → required:** The public file methods reject input, while substantive in-memory tests call private `_validate_bundle()` or `_ingest_bundle()`. The new public methods must accept tables and reuse those private bundle workflows after the adapter runs.
  * **Implementation:** Build a `SourceTableBundle` from the supplied mapping and `source_name`, then delegate to `_validate_bundle()` or `_ingest_bundle()` respectively. Convert adapter `SourceBundleError` into the existing structured validation or ingestion result. Preserve warning propagation, source-name diagnostics, existing post-preparation checks, collision checks, artifact writing, and both `validate_first=True` and `False` behavior. Keep file methods rejecting `Path` and `str`. Update shared downstream test helpers and direct private-method test calls to use public table methods; retain focused private-method tests only if they specifically test private implementation behavior.
  * **Constraints:** Do not change the order or rules of preparation, identity handling, business-key resolution, validation, collision checks, SIMS calls, or artifact writing. The `source_name` must not be opened or resolved as a path.
  * **Validation:** `V-3`, `V-4` — valid tables produce the same preparation and ingestion results through the public methods; invalid mappings return structured failures; `validate_first=True` stops on validation failure and `False` retains the existing bypass behavior. Existing business-key fixtures continue to select the same rows and values.

**Completion evidence:** Downstream behavior tests exercise the public table API, and the existing file methods still reject file input without consulting table configuration.

### Area 3: Preserve literal date and clock fields in all artifact strategies

**Objective:** SQL and sidecar values preserve normalized calendar and clock fields, and an explicitly timezone-aware target type fails before any artifact bundle is written.

**Affected code:** `ingesters/sead_change_request/sql_rendering.py::render_literal`; `sql_builder.py` renderer strategies and copy CSV helpers; `inline_staging_sql.py` if target column metadata must be passed through.

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.4` **Render:** Apply target-aware temporal formatting and reject explicitly timezone-aware target columns.
  * **Target:** `ingesters/sead_change_request/sql_rendering.py::render_literal`; `ingesters/sead_change_request/sql_builder.py::InlineInsertDeployStrategy`, `CopyCsvDeployStrategy`, `_render_copy_csv_field`, `_render_copy_csv_timestamp`; `ingesters/sead_change_request/inline_staging_sql.py::render_inline_staging_deploy` and its column rendering path as needed.
  * **Current → required:** Inline SQL uses `isoformat()` including a timezone offset, and `copy_csv` independently writes the offset. No target-column compatibility check exists. All three strategies must apply the same no-conversion rule before artifact output.
  * **Implementation:** Use the entity's `ColumnSpec.type` for each same-named target column. For a `date` target, emit only the normalized input calendar date. For a timezone-naive timestamp target (such as `timestamp` or `timestamp without time zone`), remove timezone metadata while retaining the original date and clock fields; do not convert to UTC, the target zone, or a session zone. Apply the same no-timezone rule to datetime values with no declared type, consistent with the agreed assumption that targets have no timezone. Reject explicitly timezone-aware target types (including PostgreSQL `timestamp with time zone` and `timestamptz` descriptors) with a clear `ValueError` before the artifact bundle writer is called. Preserve current formatting for non-temporal values and columns.
  * **Constraints:** Keep timezone-aware values intact in the adapter and prepared DataFrames. Do not query a database for column types or use the machine's local timezone. Preserve existing `date` handling and artifact strategy names: `inline_insert`, `copy_csv`, and `inline_staging`.
  * **Validation:** `V-5` — synthetic target models cover `date`, timezone-naive timestamp, and explicitly timezone-aware timestamp types. Assert a date target keeps its date; a timestamp target keeps both date and clock fields without an offset; two aware values representing the same instant in different zones retain their respective input clock readings. Assert an incompatible target type returns a clear failure and no artifact bundle is written.

* [x] `T3.5` **Test:** Verify literal behavior and business-key preservation through every artifact strategy.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_sql_builder.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_inline_staging.py` where a public table-method integration assertion is needed.
  * **Current → required:** Existing tests verify strategy payloads and date-only timestamps, but do not verify timezone dropping without conversion across all strategies or rejection before file output.
  * **Implementation:** Add direct artifact assertions for inline SQL, the decompressed `copy_csv` sidecar payload, and inline staging SQL. Include timezone-naive and timezone-aware timestamps, a `date` target, and the explicit incompatible target types. Add an ingestion-level check that rejection leaves the configured output directory without a deploy bundle. Keep business-key fixtures with normalized string values such as `"001"` and assert the same values reach key decisions and emitted artifacts.
  * **Constraints:** Do not execute generated SQL against a shared or production database. Use pure artifact builders or existing test fakes; disposable database tests remain loopback-only.
  * **Validation:** `V-4`, `V-5` — all strategy payloads preserve literal values; business-key and emitted artifact values match normalized table input; incompatible target types fail before bundle writing.

**Completion evidence:** The three artifact strategies produce the required date/clock literals and all reject an explicitly timezone-aware target before writing files.

### Area 4: Synchronize the documentation

**Objective:** Package documentation describes the public table capability and the current artifact strategies without claiming the project routes are shipped.

**Affected documentation:** `backend/app/ingesters/README.md`; `ingesters/sead_change_request/README.md`; `ingesters/sead_change_request/DIAGRAMS.md`.

**Dependencies:** Areas 1–3.

**Tasks:**

* [x] `T3.6` **Update:** Document how callers discover and use the table methods, and show the current preparation/ingestion flow.
  * **Target:** The three documentation files above.
  * **Current → required:** The backend README describes only the shared file protocol; the Change Request README and diagrams describe private bundle methods as the only in-memory path and omit `inline_staging` from the strategy list.
  * **Implementation:** Describe the optional `TableSourceIngester` protocol, public `validate_tables()` and `ingest_tables()` methods, the adapter's copy/sanitize behavior, and the date/timezone literal rule. Update diagrams to show table input reaching the adapter and shared bundle workflow. List all three deploy strategies. State that project-only routes remain later work.
  * **Constraints:** Keep shared file protocol examples accurate and do not describe planned Phase 4 or 5 behavior as shipped.
  * **Validation:** `V-6` — review the updated docs against protocol signatures, method behavior, strategy names, and the three Phase 3 criteria; run `rtk git diff --check`.

**Completion evidence:** Documentation matches the implemented public table entry points, timezone rule, and currently available artifact strategies.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-2`) | `T3.1`, `T3.6` | `V-1`, `V-6` | Table support is discoverable with the separate protocol; shared `Ingester` and file models remain unchanged. |
| `PH3-AC-2` (from `P-AC-3`) | `T3.2` | `V-2` | Input tables are copied and columns sanitized; names, values, dtypes, and timezones are preserved; invalid mappings raise `SourceBundleError`. |
| `PH3-AC-3` (from `P-AC-4`) | `T3.3`, `T3.5` | `V-3`, `V-4` | Business-key decisions and generated artifact values use the normalized table data. |
| `PH3-AC-4` (from `P-AC-3`, `P-AC-8`) | `T3.3`, `T3.4`, `T3.5` | `V-3`, `V-5` | Existing checks and `validate_first` behavior remain; temporal literals do not shift; timezone-aware target types fail before artifact writing. |

`VM-3.1` is covered by `V-1` and `V-2`; `VM-3.2` is covered by `V-3` and `V-5`; `VM-3.3` is covered by `V-3` and `V-4`.

## Validation And Testing

Run the focused unit suites after implementation. The execution run on 2026-10-19 used the repository virtualenv and recorded the observed outcome in the Baseline column. A full `backend/tests/ingesters` run also passed, with 17 integration tests skipped because they require a disposable loopback PostgreSQL instance.

| ID | Check and target | Command or method | Covers | Expected result after implementation | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Protocol discovery and preservation of shared file protocol in `backend/tests/ingesters/test_ingester_infrastructure.py` | `rtk uv run pytest backend/tests/ingesters/test_ingester_infrastructure.py -q` | `PH3-AC-1` | `SeadChangeRequestIngester` passes both runtime checks; `SeadIngester` passes only `Ingester`; existing registry and metadata tests pass. | Pass (2026-10-19): suite passed with the new capability checks. |
| `V-2` | Adapter inputs and copy/sanitize behavior in `backend/tests/ingesters/test_sead_change_request_input_resolution.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_input_resolution.py -q` | `PH3-AC-2` | Valid mappings preserve names, values, dtypes, and timezones in copied frames; invalid table names, empty mappings, and non-DataFrame values return `SourceBundleError`; path rejection remains. | Pass (2026-10-19): suite passed; covered copied values, dtype and timezone preservation, sanitized duplicates, preserved internal labels, and `Mapping` input. |
| `V-3` | Public table validation/ingestion and downstream checks in `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-3`, `PH3-AC-4` | Valid and invalid inputs produce structured results; existing checks and `validate_first` behavior remain; file methods still reject paths; downstream tests use the table methods. | Pass (2026-10-19): suite passed after moving downstream helpers onto `validate_tables()` and `ingest_tables()`; retired file methods still reject input. |
| `V-4` | Normalized business-key and artifact values in `backend/tests/ingesters/test_sead_change_request_ingester.py` and `test_sead_change_request_sql_builder.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_sql_builder.py -q` | `PH3-AC-3` | String keys such as `"001"` remain strings in identity decisions and generated output; each strategy uses the prepared normalized values. | Pass (2026-10-19): combined suites passed; a zero-padded key stays a string in the identity decision and emitted SQL, and the temporal strategy cases assert prepared values. |
| `V-5` | Date/time rendering and unsupported target types in `backend/tests/ingesters/test_sead_change_request_sql_builder.py` and `test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-4` | Inline insert, copy CSV payload, and inline staging retain the date/clock fields without offsets or conversion; timezone-aware target types return a clear failure before bundle writing. | Pass (2026-10-19): combined suites passed with new date, timestamp, same-instant, and `timestamp with time zone` / `timestamptz` rejection cases. |
| `V-6` | Documentation and whitespace review | `rtk git diff --check`; manually compare the three updated docs with the protocol and implementation | `PH3-AC-1` | No whitespace errors; documentation accurately describes table methods, the timezone rule, and all artifact strategies. | Pass (2026-10-19): `git diff --check` reported no errors; the three documents match the implemented protocol, methods, rule, and strategies. |
| `V-7` | Python formatting and lint for ingester source and test trees | `rtk uv run ruff check backend/app/ingesters ingesters/sead_change_request backend/tests/ingesters`; `rtk uv run black --check backend/app/ingesters ingesters/sead_change_request backend/tests/ingesters`; `rtk uv run isort --check-only backend/app/ingesters ingesters/sead_change_request backend/tests/ingesters` | All criteria | All changed Python source and test files pass lint, formatting, and import checks. | Pass (2026-10-19): ruff, black `--check`, and isort `--check-only` all reported no changes. |

`test_sead_change_request_inline_staging.py` contains loopback-only disposable PostgreSQL integration tests. Keep those tests restricted to their documented disposable database; the pure SQL builder assertions in `V-5` verify rendered staging SQL without needing a database.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Additive table protocol | `backend/app/ingesters/protocol.py::TableSourceIngester` (new); `backend/app/ingesters/__init__.py` export | `T3.1` | Runtime protocol checks pass; `Ingester` stays unchanged. |
| Validating table adapter | `ingesters/sead_change_request/input_resolution.py::_build_source_bundle`, `_resolve_source_bundle` | `T3.2` | Copied and sanitized table bundle preserves source values and dtypes. |
| Public table entry points | `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester.validate_tables`, `ingest_tables` (new methods) | `T3.3` | Structured results reuse existing workflows and checks. |
| Date/time artifact handling | `ingesters/sead_change_request/sql_rendering.py`, `sql_builder.py`, `inline_staging_sql.py` | `T3.4`, `T3.5` | Three strategies keep literal date/clock fields and reject incompatible target types before file writing. |
| Protocol, adapter, workflow, and renderer tests | `backend/tests/ingesters/test_ingester_infrastructure.py`; `test_sead_change_request_input_resolution.py`; `test_sead_change_request_ingester.py`; `test_sead_change_request_sql_builder.py`; `test_sead_change_request_inline_staging.py`; `test_sead_change_request_submission_sims_integration.py` | `T3.1`–`T3.5` | `V-1`–`V-5` pass; database tests remain loopback-only. |
| Synchronized ingester documentation | `backend/app/ingesters/README.md`; `ingesters/sead_change_request/README.md`; `ingesters/sead_change_request/DIAGRAMS.md` | `T3.6` | Docs describe shipped Phase 3 behavior and do not claim later routes exist. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Add the table capability and adapter | Done | None | `TableSourceIngester` protocol exported; adapter deep-copies tables and sanitizes caller-visible labels. |
| Area 2: Expose table validation and ingestion | Done | Area 1 | Public `validate_tables()` and `ingest_tables()` reuse the existing bundle workflow; downstream tests use them. |
| Area 3: Preserve literal date and clock fields | Done | Areas 1–2 | All three strategies use declared target types; timezone metadata is dropped without conversion; aware target types fail before writing. |
| Area 4: Synchronize the documentation | Done | Areas 1–3 | Protocol, package, and diagram documents describe shipped Phase 3 behavior only. |

### Execution Notes

- Implementation and checks ran on 2026-10-19 on branch `in-memory-ingester-handoff` commit `323443e6` with the Phase 3 changes uncommitted.
- Adapter deviation from the planned wording: `sanitize_columns()` rewrites the internal `__existing` suffix, so the adapter sanitizes only caller-visible labels and keeps labels that start with `_` or end with `__existing` unchanged. Without this, existing-row update planning and row-state handling regress. `V-2` covers the preserved internal labels.
- `_render_copy_csv_timestamp()` carries the timezone-aware rejection inline instead of importing the shared message helper. This keeps `sql_builder.py` importable under both isort and ruff, which disagree on mixing aliased and plain imports from one module.
- Pylint reports three pre-existing `W0613 unused-argument` warnings on the retired `validate()` and `ingest()` methods. They exist at the planning commit and are not caused by Phase 3.

## Definition Of Done

- [x] Every Phase 3 acceptance criterion has implementation and validation evidence.
- [x] All four work areas and listed deliverables are complete.
- [x] Protocol, adapter, public table methods, business-key, and all three renderer tests pass.
- [x] Normalized values, dtypes, and timezones remain intact through adaptation; generated temporal literals do not convert calendar or clock fields.
- [x] Explicit timezone-aware target types fail before a deploy artifact bundle is written.
- [x] Retired file input and other ingesters' shared file behavior remain unchanged.
- [x] Documentation matches the shipped table capability and does not describe later routes as available.
- [x] Lint, formatting, import, and whitespace checks pass; any environment-dependent integration skips are recorded accurately.
- [x] The stale source-proposal question and Phase 4 readiness wording are recorded for follow-up; neither is treated as a Phase 3 implementation decision.
- [x] No unresolved question affects Phase 3 implementation, correctness, or validation.

## Risks And Open Questions

- **Stale planning wording:** The source proposal still lists timezone rendering as an open question, and Phase 4 readiness still says Phase 3 is blocked on it. Phase 3's current handoff resolves that question. Keep this task plan aligned with the Phase 3 decision and correct the stale wording before Phase 4 planning.
- **Target type metadata:** `ColumnSpec.type` is optional and the standard target model currently has no timestamp columns. Use synthetic `TargetModel` fixtures for timestamp-naive and timezone-aware cases. If the implementation cannot identify an explicitly timezone-aware type from target-model metadata, stop and report the exact mismatch rather than querying a live database or silently allowing the combination.
