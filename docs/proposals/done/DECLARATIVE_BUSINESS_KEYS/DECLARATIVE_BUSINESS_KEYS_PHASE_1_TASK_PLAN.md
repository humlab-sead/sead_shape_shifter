# Declarative Business Keys — Phase 1 Task Plan

## Phase Summary

**Goal:** Make produced entity fields determine output columns and order; validate `keys` as references to those fields.

**Readiness:** Validated. The phase plan marks Phase 1 ready, the affected Core paths and tests are verified, and no implementation decision blocks this work.

**Source documents:** [Proposal](./DECLARATIVE_BUSINESS_KEYS.md) and [phase plan](./DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md), Phase 1.

**Constraints and dependencies**

- No prerequisite phase.
- Preserve business-key duplicate checks, foreign-key join behavior, and the three-tier identity model.
- Do not write project or values files during validation or reads.
- Do not fail structural validation for fields that are only knowable after source loading.
- Errors for missing keys must name the entity and key, explain that `keys` do not produce columns, and point to the required producer. Suggestion lists remain advisory and free-text key entry remains available.

**Acceptance criteria**

- [x] `PH1-AC-1` (from `P-AC-1`): Keys do not select, create, or reorder extracted output columns; order follows configured, detected, or explicitly configured producers.
- [x] `PH1-AC-2` (from `P-AC-2`): A key with no producer fails structural validation when its fields are known and runtime validation when a loader discovers its fields.
- [x] `PH1-AC-3` (from `P-AC-6`): Business-key suggestions come from known produced fields; incomplete suggestions stay advisory and allow free-text entry.

## Repository Findings

**Repository basis:** Branch `dev`, commit `d9477799`, planning date `2026-10-09`. The worktree was clean; no uncommitted changes were considered.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/model.py::TableConfig.keys_and_columns`, `get_columns`, `values_column_order`, `keys_columns_and_fks` | These methods currently insert keys into output fields and/or put keys before data columns. | Remove key metadata from output selection and ordering while retaining configured producer and identity behavior. |
| `src/extract.py::SubsetService.get_subset_columns` and `get_subset` | Extraction uses `keys_columns_and_fks`; missing requested columns are currently allowed by the normalizer caller. | Preserve detected source columns when no explicit column list exists, without relying on `keys` to select them. |
| `src/loaders/sql_loaders.py::SqlLoader._validate_columns`, `UCanAccessSqlLoader._configured_query_columns` | SQL has partial key-specific checks: the auto-detect loader checks raw key presence and the UCanAccess order starts with configured keys. | Keep detected output ordering producer-based and make missing-key errors consistent with the runtime rule. |
| `src/specifications/entity.py::EntityFieldsBaseSpecification`, `SqlColumnConfigurationSpecification`; `src/specifications/fields.py::KeysSubsetOfColumnsValidator`; `src/specifications/base.py::get_entity_columns` | The general keys-subset check is commented out. SQL has a limited manual-column check, while shared field availability includes keys as if they were produced. | Validate against configured and generated producers, not the `keys` list; defer checks that require loader metadata. |
| `src/normalizer.py::ShapeShifter._check_duplicate_keys` | Missing keys currently cause duplicate checking to be skipped rather than reported. This check runs after extra-column, link, and unnest processing. | Fail at the point where processed key fields should be available, allowing valid generated keys while rejecting missing loaded fields. |
| `src/column_availability.py::_get_source_candidates` | Configured keys and `values_column_order` are added as source candidates; `business_keys` is built from extracted candidates. | Remove key-only suggestions and retain known source/producer candidates. |
| `frontend/src/components/entities/EntityFormDialog.vue` and `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | The business-key `VCombobox` accepts typed values; an existing test saves a value absent from suggestions. | No frontend implementation change is required; retain this behavior and run its regression test. |

**Baseline checks:** All passed on the planning basis:

- Core focused files: `uv run pytest tests/model/test_model.py tests/process/test_subset_service.py tests/process/test_subset_service2.py tests/process/test_column_availability.py tests/specifications/test_entity.py tests/loaders/test_sql_loaders.py -q`
- Normalizer: `uv run pytest tests/process/test_shapeshifter.py -q`
- Suggestion API: `uv run pytest backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py -q`
- Editor free-text regression: `cd frontend && npm run test:run -- src/components/entities/__tests__/EntityFormDialog.test.ts` (16 tests passed)

## Scope

**In scope**

- Core output-column selection and ordering, including detected source fields.
- Structural and post-load key validation with the agreed error content.
- Business-key suggestion candidates returned by the Core column-availability resolver.
- Tests for producer order, supported generated fields, missing keys, and advisory/free-text suggestions.

**Out of scope**

- Backend fixed-schema and materialized-row changes, frontend order adoption, and legacy values-order retirement; these belong to later phases.
- Changes to foreign-key matching semantics, business-key duplicate checks, or automatic project/values migration.
- Frontend implementation changes; the existing free-text behavior is a regression constraint.

## Work Breakdown

### Area 1: Make producers determine extracted columns

**Objective:** Extract configured or detected data fields in producer order without inserting keys into the result.

**Affected code:** `src/model.py::TableConfig`; `src/extract.py::SubsetService`; `src/loaders/sql_loaders.py::SqlLoader._validate_columns` and `UCanAccessSqlLoader._configured_query_columns`.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Make `TableConfig` output helpers independent of `keys`.
  * **Target:** `src/model.py::TableConfig.keys_and_columns`, `get_columns`, `values_column_order`, `extra_fk_columns`, and `keys_columns_and_fks`.
  * **Current → required:** Key fields currently precede or supplement data fields; output helpers must return configured producer fields, explicit generated fields, and identity fields only where the helper's contract requires them.
  * **Implementation:** Remove key insertion and key-first ordering from output helpers. Remove the `include_keys` switch and update its verified internal caller and tests. Keep the `keys` property available for business-key checks. Preserve configured column order and existing FK/extra/unnest handling.
  * **Constraints:** A key already listed in a producer's output appears once in that producer's position. Do not change foreign-key values or identity-column meaning.
  * **Validation:** `V-1`.
* [x] `T1.2` **Change:** Select detected source fields without using keys as a fallback column list.
  * **Target:** `src/extract.py::SubsetService.get_subset_columns` and `get_subset`; `src/loaders/sql_loaders.py::SqlLoader._validate_columns` and `UCanAccessSqlLoader._configured_query_columns`.
  * **Current → required:** Subsetting uses `keys_columns_and_fks`; auto-detected SQL can return source fields while the configured `columns` list is empty, and UCanAccess derives query order with keys first. Detected source fields must remain available and retain their source order without key-driven selection or reordering.
  * **Implementation:** Pass detected source output through the existing subset path when auto-detection is active and no explicit columns define its order. Build SQL query-backed order from configured producer columns and detected query metadata, not `keys`. Do not treat an extra-column key as a raw source requirement.
  * **Constraints:** Keep explicit `columns` ordering authoritative when configured. Preserve FK and generated-column exclusions from raw extraction.
  * **Validation:** `V-1`, `V-2`.

**Completion evidence:** Model and extraction tests show keys add no columns or order positions, while configured, auto-detected, and explicitly generated fields retain their required order.

### Area 2: Validate keys against produced fields

**Objective:** Reject a key only when the entity does not produce it at the operation that uses it, and report actionable errors.

**Affected code:** `src/specifications/entity.py::EntityFieldsBaseSpecification` and `SqlColumnConfigurationSpecification`; `src/specifications/fields.py::KeysSubsetOfColumnsValidator`; `src/specifications/base.py::get_entity_columns`; `src/normalizer.py::ShapeShifter._check_duplicate_keys`.

**Dependencies:** Area 1's producer-based output model.

**Tasks:**

* [x] `T2.1` **Change:** Apply producer-aware structural validation when configured fields are known.
  * **Target:** `src/specifications/entity.py::EntityFieldsBaseSpecification`; `src/specifications/fields.py::KeysSubsetOfColumnsValidator`; `src/specifications/base.py::get_entity_columns`.
  * **Current → required:** The shared key-subset check is disabled, and availability aggregation treats keys themselves as available columns. Validation must count actual configured or generated producers and must not reject fields that depend on loader detection.
  * **Implementation:** Enable or extend the existing key validator using producer fields available at the relevant stage, including configured columns and declared extra-column, foreign-key, and unnest outputs where applicable. Exclude keys as a source of availability. Defer structural checks for source fields that cannot be known until loading. Preserve the existing field-list and unresolved-directive guards.
  * **Constraints:** Report the entity and each missing key, explain that `keys` do not create output columns, and name the relevant way to produce the field (for example, a configured column or its actual producer). Do not claim a dynamic source field is missing before loading.
  * **Validation:** `V-3`.
* [x] `T2.2` **Change:** Fail runtime validation when processed output is missing a configured key.
  * **Target:** `src/normalizer.py::ShapeShifter._check_duplicate_keys`; SQL runtime key validation in `src/loaders/sql_loaders.py` where needed to use the same error detail.
  * **Current → required:** `_check_duplicate_keys` silently skips missing keys; SQL checks only a subset of auto-detected raw fields and reports a separate message. Runtime validation must fail consistently after the configured producers have run.
  * **Implementation:** At the existing post-link/post-unnest key-check point, raise the repository-standard validation error for each key absent from processed output before attempting duplicate checks. Align or remove SQL-only missing-key checks so generated keys are not rejected before their producer runs and all loader-backed failures use the same actionable detail.
  * **Constraints:** Check after extra columns, FK linking, and unnesting so supported generated keys can exist. Keep duplicate-key detection behavior unchanged when all keys are present.
  * **Validation:** `V-2`, `V-4`.

**Completion evidence:** Known missing keys fail project validation; loader-discovered missing keys fail normalization with consistent detail; keys produced by supported later stages remain valid.

### Area 3: Base suggestions on produced fields

**Objective:** Return known source and producer fields as advisory business-key suggestions without suggesting a key merely because it is configured.

**Affected code:** `src/column_availability.py::_get_source_candidates` and `resolve_column_availability`; `tests/process/test_column_availability.py`; suggestion service/API tests; existing entity editor regression test.

**Dependencies:** Area 1's producer-based column helpers.

**Tasks:**

* [x] `T3.1` **Change:** Remove key-only candidates from business-key suggestions.
  * **Target:** `src/column_availability.py::_get_source_candidates`; `tests/process/test_column_availability.py`; `backend/tests/services/test_stage_aware_column_service.py`; `backend/tests/api/v1/test_columns.py`.
  * **Current → required:** Configured keys and key-inclusive fixed order can be seeded as source candidates, so an unproduced field can be suggested. Suggestions must reflect known source and produced fields only.
  * **Implementation:** Derive source and business-key candidates from source metadata and producer outputs. Keep partial results advisory and leave free-text entry available; do not turn suggestion membership into validation.
  * **Constraints:** Preserve operation-stage candidate lists and existing response shape.
  * **Validation:** `V-5`, `V-6`.

**Completion evidence:** Resolver and API tests omit key-only fields and retain produced fields; the editor still accepts and saves a key absent from suggestions.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2` | `V-1`, `V-2` | Keys add no extracted fields or ordering; configured, detected, and generated producer fields retain their order. |
| `PH1-AC-2` (from `P-AC-2`) | `T2.1`, `T2.2` | `V-2`, `V-3`, `V-4` | Known missing keys fail structurally; loader-discovered missing keys fail at runtime; generated keys pass when present at use time. |
| `PH1-AC-3` (from `P-AC-6`) | `T3.1` | `V-5`, `V-6` | Suggestions omit unproduced keys, remain advisory, and typed values absent from suggestions can still be saved. |

## Validation And Testing

The implementation was validated with the following checks. The named existing test files were updated; no new test file was required.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Model and extraction order: `tests/model/test_model.py`, `tests/process/test_subset_service.py`, `tests/process/test_subset_service2.py`. Cover keys absent from configured columns, keys already present in columns, explicit column order, and auto-detected source columns. | `uv run pytest tests/model/test_model.py tests/process/test_subset_service.py tests/process/test_subset_service2.py -q` | `PH1-AC-1` | Tests pass; output excludes key-only fields and preserves producer order. | Pass; included in the focused Core baseline command. |
| `V-2` | SQL and pipeline runtime: `tests/loaders/test_sql_loaders.py`, `tests/process/test_shapeshifter.py`. Cover detected columns, SQL key absent from detected results, generated keys, and no change to duplicate checks for present keys. | `uv run pytest tests/loaders/test_sql_loaders.py tests/process/test_shapeshifter.py -q` | `PH1-AC-1`, `PH1-AC-2` | Tests pass; missing keys fail with entity/key/producer detail after producers run. | Pass; both files passed in separate baseline commands. |
| `V-3` | Structural validation: `tests/specifications/test_entity.py`. Cover configured producer fields, extra-column/FK/unnest-produced keys, truly unproduced keys, and dynamic source fields that must be deferred. | `uv run pytest tests/specifications/test_entity.py -q` | `PH1-AC-2` | Tests pass; known invalid configurations fail with actionable errors and dynamic fields are not rejected prematurely. | Pass; included in the focused Core baseline command. |
| `V-4` | Normalizer runtime validation: add cases to `tests/process/test_shapeshifter.py` for a loader-discovered missing key and for a key produced after extraction. | `uv run pytest tests/process/test_shapeshifter.py -q` | `PH1-AC-2` | Missing runtime key raises the expected validation error; produced keys continue through normalization. | Pass; 45 tests passed. |
| `V-5` | Candidate resolver and API contract: `tests/process/test_column_availability.py`, `backend/tests/services/test_stage_aware_column_service.py`, `backend/tests/api/v1/test_columns.py`. Cover key-only candidates being omitted and known producer candidates remaining in the existing response shape. | `uv run pytest tests/process/test_column_availability.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py -q` | `PH1-AC-3` | Tests pass; suggestions contain only known source/producer fields and remain advisory. | Pass; Core resolver tests passed in the Core baseline; backend service/API tests passed in the suggestion API baseline. |
| `V-6` | Free-text regression: `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, especially “maps operation-specific candidates and saves values absent from suggestions.” | `cd frontend && npm run test:run -- src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH1-AC-3` | The editor still accepts and saves typed business keys absent from suggestions. | Pass; 16 tests passed. |

**Execution results (2026-10-09):**

- `V-1`–`V-5`: `uv run pytest tests/model/test_model.py tests/process/test_subset_service.py tests/process/test_subset_service2.py tests/loaders/test_sql_loaders.py tests/process/test_shapeshifter.py tests/specifications/test_entity.py tests/specifications/test_real_world_errors.py tests/process/test_column_availability.py tests/model/test_target_model_conformance.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py backend/tests/services/test_shapeshift_service.py backend/tests/test_shapeshift_service_include_bug.py -q` — passed.
- `V-6`: `cd frontend && npm run test:run -- src/components/entities/__tests__/EntityFormDialog.test.ts` — passed, 16 tests.
- Formatting: Black check passed for the 20 changed Python files; isort check passed.
- Additional related regressions in `tests/model/test_target_model_conformance.py` and `tests/specifications/test_real_world_errors.py` passed with the focused pytest command. The conformance expectations include a newly reported missing output column where a key previously implied that column.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Core output helpers and extraction | `src/model.py`, `src/extract.py`, `src/loaders/sql_loaders.py` | `T1.1`, `T1.2` | Producer-based extraction and ordering tests pass. |
| Structural and runtime key validation | `src/specifications/entity.py`, `src/specifications/fields.py`, `src/specifications/base.py`, `src/normalizer.py` | `T2.1`, `T2.2` | Structural and runtime missing-key cases pass with required error detail. |
| Business-key suggestions | `src/column_availability.py` | `T3.1` | Resolver/API tests omit unproduced key suggestions; editor free-text regression passes. |
| Updated focused tests | `tests/model/test_model.py`, `tests/process/test_subset_service.py`, `tests/process/test_subset_service2.py`, `tests/process/test_shapeshifter.py`, `tests/process/test_column_availability.py`, `tests/specifications/test_entity.py`, `tests/loaders/test_sql_loaders.py`, `backend/tests/services/test_stage_aware_column_service.py`, `backend/tests/api/v1/test_columns.py` | `T1.1`–`T3.1` | All validations `V-1`–`V-6` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Producer-defined output | Done | None | `T1.1`–`T1.2`; `V-1`–`V-2` passed. |
| Area 2: Structural and runtime key validation | Done | Area 1 | `T2.1`–`T2.2`; `V-2`–`V-4` passed. |
| Area 3: Producer-based suggestions | Done | Area 1 | `T3.1`; `V-5`–`V-6` passed. |

## Definition Of Done

- [x] All Phase 1 acceptance criteria have implementation and test evidence.
- [x] Keys no longer select or reorder output fields; configured and detected producer order is preserved.
- [x] Structural and runtime errors identify the entity, missing key, reason, and relevant producer guidance.
- [x] Validation defers unknown source fields until loader output is available and accepts keys produced at later supported stages.
- [x] Suggestion lists exclude fields inferred only from `keys` and remain advisory; free-text entry remains functional.
- [x] Business-key duplicate checks, foreign-key joins, and identity behavior remain covered by regression tests.
- [x] No validation or read path writes project or values files.
- [x] All validations `V-1`–`V-6` pass; any deviations or follow-up work are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.
