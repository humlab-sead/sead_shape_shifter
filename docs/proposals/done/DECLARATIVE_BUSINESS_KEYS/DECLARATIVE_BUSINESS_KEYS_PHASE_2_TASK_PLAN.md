# Declarative Business Keys — Phase 2 Task Plan

## Phase Summary

**Goal:** Make the backend fixed schema—managed identity columns followed by produced data columns—the only positional schema for fixed and materialized rows and external values.

**Readiness:** Validated. [Phase 2](./DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md) is ready after Phase 1; [Phase 1's task plan](./DECLARATIVE_BUSINESS_KEYS_PHASE_1_TASK_PLAN.md) records completion, and the affected paths and baseline tests were verified.

**Source documents:** [Proposal](./DECLARATIVE_BUSINESS_KEYS.md) (`P-AC-3`, `P-AC-4`) and [phase plan](./DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md) (Phase 2, `VM-2`).

**Constraints:** Preserve `system_id` and `public_id` identity semantics, business-key checks, foreign-key joins, explicit column types, optimistic locking, and the additive `fixed_schema` response. Do not write project or values files during validation or GET. Do not migrate existing files automatically. Retain only an exact, safely mappable legacy values-request order during the compatibility period; retiring it belongs to Phase 5. Frontend adoption and grouped integration validation belong to Phases 3 and 4.

**Acceptance criteria**

- [x] `PH2-AC-1` (from `P-AC-3`): Fixed and materialized rows use one backend schema of managed identity fields followed by produced data columns; keys add no positions and no null placeholders.
- [x] `PH2-AC-2` (from `P-AC-4`): Missing-key errors for fixed or materialized data include the expected positional column order and do not modify project or values files.
- [x] `PH2-AC-3` (from `P-AC-4`): Values requests accept the new order, remap only the recognized legacy order by column name, and reject duplicate, unknown, or ambiguous payloads.

## Repository Findings

**Repository basis:** Branch `declarative-business-keys`, commit `7e6a2a12`, planning date 2026-10-09. Worktree clean; no uncommitted changes considered. Graphify's scoped query was used for navigation; the following findings were verified in source and tests. The phase plan's Current Position describes the pre-Phase-1 state; use the committed Phase 1 behavior instead.

| Evidence | Current behavior | Planning implication |
|---|---|---|
| `src/types/fixed_entity_types.py::build_fixed_entity_full_columns` | Inserts `keys` ahead of configured columns; also used by Core fixed-value validation and backend schema/persistence. | Separate producer-defined canonical order from the precise legacy order used only to recognize compatible requests. |
| `src/specifications/entity.py::FixedEntityFieldsSpecification`, `src/loaders/fixed_loader.py::FixedLoader._resolve_columns_for_values` | Accept data-only or identity-bearing inline rows; Core validation and loading independently calculate widths and column types. | Keep both supported inline row layouts, but derive their field names and error order from the same identity-plus-data rule. |
| `backend/app/utils/fixed_schema.py::derive_fixed_schema`, `normalize_fixed_entity` | Derive `full_columns` from keys and persist that full order in `entity_data.columns`; `key_columns` and `editable_columns` are response metadata. | Persist data columns without managed identity fields; keep identity first in `full_columns` and keys only as metadata, with existing stored identity columns interpreted without writes on reads. |
| `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy` | Validates row widths and types using separate column/full-column choices; materialization inserts null key columns. `EntityOperations` calls the strategy on add/update. | Validate keys and rows before persistence; stop key padding and keep type checks aligned with resolved row layout. |
| `backend/app/services/materialization_service.py::_prepare_materialized_values`, `_create_materialized_entity` | Normalizes/serializes before persisting; both inline and external storage paths call the fixed strategy. The external path saves YAML before writing the sidecar. | Fail missing keys before either save; store data-only columns in YAML and full-order rows in inline/external values, preserving inferred types and source state. |
| `backend/app/services/entity_values_service.py::EntityValuesService.get_values`, `update_values` | GET returns the file's raw column order; PUT accepts only `derive_fixed_schema(...).full_columns` and writes request order. Shape checks precede file writes; `If-Match` protects updates. | Normalize recognized stored/legacy order on GET in memory; validate and map PUT before any write; reject unrecognized orders and widths. |
| `backend/app/api/v1/endpoints/entities.py::_build_entity_response`, `get_entity_values`, `update_entity_values` | Entity responses expose `fixed_schema`; values PUT forwards the original request rows to `sync_materialized_entity_mappings` after the write. | Keep response shape; pass the normalized saved columns/rows to mapping sync rather than the pre-remap request. No new route or request field is needed. |

## Scope

- **In scope:** Core fixed order, fixed specification and loader; backend schema derivation, fixed persistence, materialization, values GET/PUT and route mapping-sync handoff; focused tests and the affected fixed-values contract documentation in this plan.
- **Out of scope:** Frontend grid/editor changes, bulk repair of saved configurations or values, full cross-layer integration rollout, retirement of legacy requests, and changes to mapping-key or identity semantics.
- **Compatibility:** Existing stored `columns` may contain identity fields because the old persistence path wrote the full list. Read these as managed identity fields plus remaining stored data fields without rewriting them. A key in `keys` alone is not a data producer. A legacy request is recognizable only if the exact old identity/key/data ordering is a duplicate-free permutation of the authoritative full columns; a key absent from produced data cannot be mapped and must fail.

## Work Breakdown

### Area 1: Define and validate the fixed positional schema

**Objective:** One producer-defined identity-plus-data order supplies fixed metadata, inline row interpretation, and type checks.

**Affected code:** `src/types/fixed_entity_types.py::build_fixed_entity_full_columns`; `src/specifications/entity.py::FixedEntityFieldsSpecification`; `src/loaders/fixed_loader.py::FixedLoader._resolve_columns_for_values`; `backend/app/utils/fixed_schema.py::derive_fixed_schema`, `normalize_fixed_entity`; `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy`.

**Dependencies:** Committed Phase 1 output.

**Tasks:**

* [x] `T1.1` **Change:** Derive full fixed order without key insertion and persist only data fields in `entity_data.columns`.
  * **Target:** `src/types/fixed_entity_types.py::build_fixed_entity_full_columns`; `backend/app/utils/fixed_schema.py::build_fixed_full_columns`, `derive_fixed_schema`, `normalize_fixed_entity`.
  * **Current → required:** Keys currently create/reorder full positions, and persistence writes identity columns into `columns`; instead form `["system_id", public_id if configured, *data_columns]` with each managed identity appearing once, while data columns retain declared/stored order.
  * **Implementation:** Use the Core order helper for backend `full_columns`; strip managed identity fields from normalized persisted data columns and avoid mutating the input. For legacy stored full columns, derive the same full list in memory without reordering or writing the file. Keep `key_columns` as business-role metadata and `editable_columns` excluding identities and keys; preserve the additive response fields and `order_source` meaning.
  * **Constraints:** A key already produced appears once at its data position; a key not produced is never introduced. Keep explicit duplicate-column errors; do not silently deduplicate malformed data declarations.
  * **Validation:** `V-1` and `V-2`: identity-only, data-only, pre-stored identity columns, key/data overlap, key-only field, and duplicate input.
* [x] `T1.2` **Change:** Align Core fixed-value widths, column types, and missing-key errors with the fixed schema.
  * **Target:** `src/specifications/entity.py::FixedEntityFieldsSpecification`; `src/loaders/fixed_loader.py::FixedLoader._resolve_columns_for_values`; `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy._validate_fixed_entity_shape`, `_validate_types`, `prepare_for_persistence`.
  * **Current → required:** Core and persistence resolve widths/types independently, and missing-key or width errors omit the expected full order; use the same data-only and identity-plus-data layouts from `T1.1`.
  * **Implementation:** Before save, reject keys absent from produced data at their use point with entity name, missing keys, why `keys` do not create fields, producer guidance, and expected full positional order. Preserve data-only inline values and full-width rows; resolve each row's types against its actual layout and reject mismatched or inconsistent widths before indexing. Ensure Core specification/loader report the expected full order for fixed positional errors, including externally loaded dict rows missing produced fields.
  * **Constraints:** Do not reinterpret a data-only row as full order when widths coincide; avoid duplicate/unknown type declarations and preserve `system_id`/`public_id` coercion. Reads and validation remain side-effect-free.
  * **Validation:** `V-1`, `V-2`: valid data-only/full rows, incorrect width, missing key, duplicated column, typed identity/data, and unchanged files on failure.

**Completion evidence:** Fixed schema, persistence, and Core fixed loader/specification agree on columns and row layout without key-created positions.

### Area 2: Materialize only actual producer fields

**Objective:** Both inline and external materialization store the same full-order rows while YAML lists only data fields; missing keys fail before writes.

**Affected code:** `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy.normalize_materialized_dataframe`; `backend/app/services/materialization_service.py::_normalize_materialized_dataframe`, `_prepare_materialized_values`, `_create_materialized_entity`, `materialize_entity`.

**Dependencies:** Area 1's schema and error contract.

**Tasks:**

* [x] `T2.1` **Change:** Reject missing materialized keys instead of adding null columns.
  * **Target:** `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy.normalize_materialized_dataframe`; `backend/app/services/materialization_service.py::_prepare_materialized_values`.
  * **Current → required:** The strategy inserts null-valued columns for absent keys; reject the missing keys before serialization, YAML save, or sidecar write.
  * **Implementation:** Keep managed identity generation when needed and existing sanitized producer column order; validate every configured business key against actual columns with entity name, producer guidance, and expected full order. Convert the error through the materialization service's result path without treating failure as success.
  * **Constraints:** Keep `_sanitize_materialized_dataframe` before normalization; preserve nullable values in columns that actually exist and the current type-inference/convention behavior.
  * **Validation:** `V-3`: missing-key inline/external attempts return failure and save nothing; present keys retain non-null data and declared data order.
* [x] `T2.2` **Change:** Save materialized data columns separately from full-order row values.
  * **Target:** `backend/app/services/materialization_service.py::_create_materialized_entity`, `materialize_entity`.
  * **Current → required:** Materialized YAML currently stores `df.columns` including identity, whereas `entity_data.columns` must contain data fields only.
  * **Implementation:** Derive the data column list from the normalized full-order DataFrame by excluding managed identity fields; retain full-order values for inline storage or external `EntityValuesService.update_values`. Ensure `_create_materialized_entity`'s second normalization does not reintroduce keys/identity into YAML columns; preserve `source_state`, types, and file format.
  * **Constraints:** No read-time migration or change to unmaterialization/cascade behavior. The external update must validate against the newly saved data-only config without reordering columns.
  * **Validation:** `V-3`: inline and parquet/csv paths have identical `fixed_schema.full_columns`, data-only YAML columns, and rows in full order.

**Completion evidence:** Materialization never pads missing keys, stores the intended schema, and reports failure before project or values writes when a key is absent.

### Area 3: Convert external values safely and preserve the API contract

**Objective:** GET exposes authoritative column order without writing; PUT accepts the authoritative order and exactly recognized legacy requests while keeping mappings synchronized with saved rows.

**Affected code:** `backend/app/services/entity_values_service.py::EntityValuesService.get_values`, `update_values`; `backend/app/api/v1/endpoints/entities.py::get_entity_values`, `update_entity_values`; `backend/app/services/materialization_service.py::sync_materialized_entity_mappings` (consumer; change only if necessary for normalized handoff).

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Normalize fixed-values GET and exact, unambiguous PUT orders by column name.
  * **Target:** `backend/app/services/entity_values_service.py::EntityValuesService.get_values`, `_validate_fixed_columns`, `_validate_values_shape`, `update_values`; `backend/app/utils/fixed_schema.py` for a shared legacy-order helper if needed.
  * **Current → required:** GET returns file order unchanged and PUT permits only its current key-inclusive full order; use `fixed_schema.full_columns` on fixed responses and writes, accepting only the exact historical identity/keys/data order when it is a safe permutation.
  * **Implementation:** For a fixed entity, validate unique string column names, configured keys, and row widths before any write. Compute the historical ordering using the previous helper rule solely for recognition; compare the request to either the new full order or that exact legacy order, require the same unique column set, then reorder row cells by matching names. Reject unknown/missing/duplicate names, non-list or inconsistent rows, and legacy layouts requiring invented or dropped fields. On GET, reorder an existing compatible file in memory; reject an incompatible stored layout with the entity, missing fields and expected positional order rather than mutating it. Keep non-fixed behavior and etag checks unchanged; return normalized columns/rows from PUT for downstream callers.
  * **Constraints:** Do not accept arbitrary permutations, infer names from width, or let a zero-row request bypass name validation. Preserve Parquet/CSV dtype handling and make all validation occur before `_write_values_file` creates a parent directory.
  * **Validation:** `V-4`: canonical and exact legacy permutations, two+ keys in different order, empty rows, duplicate/unknown names, missing-key/width mismatch, unchanged file/etag on rejection, and in-memory GET normalization.
* [x] `T3.2` **Change:** Pass normalized saved rows to downstream materialized mapping sync and retain HTTP error semantics.
  * **Target:** `backend/app/api/v1/endpoints/entities.py::update_entity_values`, `get_entity_values`, `_build_entity_response`; `backend/app/services/materialization_service.py::sync_materialized_entity_mappings` if its contract needs updating.
  * **Current → required:** The endpoint currently sends pre-conversion request rows to mapping sync; it must use the service's normalized result while keeping `fixed_schema`, values response, authorization, and `If-Match` behavior.
  * **Implementation:** Pass `result.columns` and `result.values` to mapping sync after successful PUT. Keep client validation failures as 422 and etag conflicts as 409. GET returns normalized fixed rows and schema metadata without modifying YAML, sidecar, or mapping files.
  * **Constraints:** Do not change the JSON request/response field names or route registration; preserve mapping-local-key lookup and non-materialized no-op sync.
  * **Validation:** `V-5`: authorized route GET/PUT, exact legacy remap with mapping sidecar entries reflecting stored values, 422 rejection without writes, and 409 etag mismatch.

**Completion evidence:** Only validated full-order rows are written or passed to mapping sync; external GET/PUT and entity `fixed_schema` agree on order.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH2-AC-1` (from `P-AC-3`) | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`, `V-2`, `V-3` | One identity-plus-produced-data order; data-only YAML columns; no key placeholders in fixed/materialized rows. |
| `PH2-AC-2` (from `P-AC-4`) | `T1.2`, `T2.1`, `T3.1` | `V-1`, `V-2`, `V-3`, `V-4` | Errors name entity, missing key, producer guidance, and expected order; validation/GET do not write files. |
| `PH2-AC-3` (from `P-AC-4`) | `T3.1`, `T3.2` | `V-4`, `V-5` | Canonical and exact safe legacy inputs work; invalid orders/widths fail before writes; mapping sync sees saved rows. |

## Validation And Testing

Baseline on 2026-10-09: `uv run pytest tests/types/test_fixed_entity_types.py tests/specifications/test_entity.py tests/loaders/test_fixed_loader.py backend/tests/services/test_project_service.py backend/tests/services/test_entity_values_service.py backend/tests/services/test_materialization_service.py backend/tests/api/v1/test_entities.py -q` — **Pass** (all selected tests). Planned new cases below were **not run**; the baseline describes current behavior only.

Implementation evidence on 2026-10-09 (branch `declarative-business-keys`, base commit `7e6a2a12`): the same grouped command — **Pass** (387 tests, including the new cases added for `V-1`–`V-5`). Formatting and lint — `black --check` and `isort --check-only` on all changed Python files **Pass**; `ruff check` on the changed source files **Pass**. Full-suite `uv run pytest tests backend/tests -q` reported 17 failures; all 17 reproduce at base commit `7e6a2a12` and are pre-existing Phase 1 validation-spec failures, so Phase 2 introduced no new failures.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Core: `tests/types/test_fixed_entity_types.py`, `tests/specifications/test_entity.py`, `tests/loaders/test_fixed_loader.py`; inline data-only/full rows, key absent, identity present, duplicate columns, widths and typed values. | `uv run pytest tests/types/test_fixed_entity_types.py tests/specifications/test_entity.py tests/loaders/test_fixed_loader.py -q` | `PH2-AC-1`, `PH2-AC-2` | Canonical order ignores keys; bad rows report full order and do not write. | Pass on 2026-10-09 after implementation (grouped run). |
| `V-2` | Backend schema/persistence: `backend/tests/services/test_project_service.py`, `backend/tests/api/v1/test_entities.py`; new data-only and legacy stored full columns, key metadata, duplicate/missing keys, create/update/GET, unchanged YAML on validation failure. | `uv run pytest backend/tests/services/test_project_service.py backend/tests/api/v1/test_entities.py -q` | `PH2-AC-1`, `PH2-AC-2` | Stored columns exclude managed identities; responses retain `fixed_schema` shape and correct order without GET writes. | Pass on 2026-10-09 after implementation (grouped run). |
| `V-3` | Materialization: `backend/tests/services/test_materialization_service.py`; present/missing keys, inline and external storage, sanitized duplicate/helper columns, preserved types, no YAML/sidecar writes on missing key. | `uv run pytest backend/tests/services/test_materialization_service.py -q` | `PH2-AC-1`, `PH2-AC-2` | No null-key placeholders; full-order rows and data-only config; explicit failure before writes. | Pass on 2026-10-09 after implementation (grouped run). |
| `V-4` | Values service: `backend/tests/services/test_entity_values_service.py`; exact canonical/legacy permutation, ambiguous/unknown/duplicate names, mismatched widths, zero rows, compatible and incompatible GET, etag and file unchanged on rejection. | `uv run pytest backend/tests/services/test_entity_values_service.py -q` | `PH2-AC-2`, `PH2-AC-3` | Safe name-based remap and in-memory GET normalization; all invalid input fails before writing. | Pass on 2026-10-09 after implementation (grouped run). |
| `V-5` | Authorized API: `backend/tests/api/v1/test_entities.py`; fixed GET/PUT and materialized mapping sync from remapped rows; 422 invalid payload and 409 etag conflict. | `uv run pytest backend/tests/api/v1/test_entities.py -q` | `PH2-AC-3` | Response schema/order and mapping sidecar match saved values; failed requests preserve files. | Pass on 2026-10-09 after implementation (grouped run). |
| `V-6` | Focused regression and quality check after all tasks. | `uv run pytest tests/types/test_fixed_entity_types.py tests/specifications/test_entity.py tests/loaders/test_fixed_loader.py backend/tests/services/test_project_service.py backend/tests/services/test_entity_values_service.py backend/tests/services/test_materialization_service.py backend/tests/api/v1/test_entities.py -q`; `uv run black --check src/types/fixed_entity_types.py src/specifications/entity.py src/loaders/fixed_loader.py backend/app/utils/fixed_schema.py backend/app/services/project/entity_persistence_strategies.py backend/app/services/materialization_service.py backend/app/services/entity_values_service.py backend/app/api/v1/endpoints/entities.py`; `uv run isort --check-only` on the same Python files | `PH2-AC-1`–`PH2-AC-3`; preservation | All selected tests pass; formatting and imports clean. | Pass on 2026-10-09 after implementation; Black, isort, and Ruff clean. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Canonical fixed order and metadata | `src/types/fixed_entity_types.py::build_fixed_entity_full_columns`, `backend/app/utils/fixed_schema.py::derive_fixed_schema`, `normalize_fixed_entity` | `T1.1`, `T3.1` | `V-1`, `V-2`, `V-4` |
| Fixed value validation and coercion | `src/specifications/entity.py::FixedEntityFieldsSpecification`, `src/loaders/fixed_loader.py::FixedLoader`, `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy` | `T1.2`, `T2.1` | `V-1`, `V-2`, `V-3` |
| Materialized config and rows | `backend/app/services/materialization_service.py::MaterializationService` | `T2.1`, `T2.2` | `V-3` |
| Fixed external values and API handoff | `backend/app/services/entity_values_service.py::EntityValuesService`, `backend/app/api/v1/endpoints/entities.py::update_entity_values` | `T3.1`, `T3.2` | `V-4`, `V-5` |
| Focused tests | `tests/types/test_fixed_entity_types.py`, `tests/specifications/test_entity.py`, `tests/loaders/test_fixed_loader.py`, `backend/tests/services/test_project_service.py`, `backend/tests/services/test_materialization_service.py`, `backend/tests/services/test_entity_values_service.py`, `backend/tests/api/v1/test_entities.py` | `T1.1`–`T3.2` | `V-1`–`V-6` |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Fixed positional schema | Done | Phase 1 complete | `V-1`, `V-2` pass; missing keys rejected with expected order. |
| Area 2: Materialized rows | Done | Area 1 | `V-3` passes; no null-key placeholders or writes on missing key. |
| Area 3: External values and API | Done | Areas 1 and 2 | `V-4`, `V-5` pass; legacy remap and mapping sync verified. |

## Definition Of Done

- [x] `PH2-AC-1`–`PH2-AC-3` have implementation and validation evidence (`V-1`–`V-5`).
- [x] All tasks and deliverables are complete; `V-6` passes.
- [x] `fixed_schema.full_columns`, inline values, sidecar rows, GET/PUT results, and materialized mapping sync agree on the positional order.
- [x] Existing stored projects are read without mutation; missing-key and invalid values errors identify the expected full order and leave project/values files unchanged.
- [x] Typed values, identity semantics, data-only inline rows, materialization sanitization, etags, and non-fixed values are regression-tested.
- [x] No Phase 3 frontend behavior or Phase 5 legacy retirement was implemented; deviations and follow-up work are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.

**Implementation handoff:** If current repository state conflicts with any verified file, behavior, or compatibility rule above, stop affected work and report the discrepancy with its test evidence. Do not invent a replacement design or broaden Phase 2.
