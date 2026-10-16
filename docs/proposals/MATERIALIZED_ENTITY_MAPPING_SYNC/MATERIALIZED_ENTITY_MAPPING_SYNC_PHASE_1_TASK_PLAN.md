# Fixed-Row Change Definition — Phase 1 Task Plan

## Phase Summary

**Goal:** Produce a validated, deterministic change set from previously saved and new fixed rows. This phase prepares and checks changes before persistence; Phase 2 applies the new change set to the sidecar.

**Readiness:** Validated. Phase 1 is marked ready in the [phase plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md), and no proposal decision blocks its comparison or validation rules.

**Sources:** [proposal](./MATERIALIZED_ENTITY_MAPPING_SYNC.md) (`P-AC-2`–`P-AC-5`) and [phase plan, Phase 1](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md#phase-1-define-fixed-row-changes) (`VM-1`, `VM-2`).

**Dependencies and constraints:** Use the existing missing-value predicate and local-key encoder. API-to-Core conversion remains in `ProjectMapper`; Core comparison code must not import `backend.*`. Preserve stored `EntityMapping.local_key` and `public_id`, sidecar-first normalization, and existing save responses. Do not add a sidecar write path or retry behavior in this phase; the current external post-save rebuild remains until Phase 2.

**Phase acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-3`): `None`, `NaN`, empty, and whitespace-only IDs compare as missing; zero is valid; invalid changed IDs and unusable keys prevent the row write.
2. [x] `PH1-AC-2` (from `P-AC-5`): Both default-entry paths use ordered `TableConfig.safe_keys`; an ordinary save does not rewrite an existing entry's mapping columns.
3. [x] `PH1-AC-3` (from `P-AC-4`): The change set excludes unchanged rows, distinguishes a deliberate ID edit from a saved-value/sidecar mismatch, and represents a key change as removal plus addition.
4. [x] `PH1-AC-4` (from `P-AC-2`): Only fixed entities qualify; a materialized fixed entity may propose a missing entry, and another fixed entity requires an existing entry.

## Repository Findings

**Repository basis:** Branch `materialized-entity-mapping-sync`, commit `122bd7f0ef33ebe26d9ff6e7da70f4a34c37c55f`, planned 2026-10-15. The uncommitted proposal and phase plan were used as sources. Other working-tree changes were left untouched. Graphify identified the relevant components; the findings below were checked in current source and tests.

| Source | Verified finding | Planning implication |
|---|---|---|
| `src/model.py::TableConfig.keys`, `safe_keys`, `type`, `is_materialized` | `keys` returns a set; `safe_keys` retains declared order. Entity type and materialization are separate properties. | Use `safe_keys` for new default keys and `type == "fixed"` for eligibility. |
| `backend/app/services/mapping_service.py::MappingService._default_local_key`, `_build_default_entity_mapping` | Mapping API defaults already use `safe_keys`; a missing entry can be returned as default metadata without saving it. | Retain its validation error and default-entry behavior while sharing the key rule. |
| `backend/app/services/materialization_service.py::MaterializationService._default_mapping_local_key`, `_ensure_mapping_entity`, `_extract_manual_links_from_rows` | Materialization defaults use unordered `keys`; the current rebuild reads all rows and uses `pd.isna` for IDs. | Change the default helper now; leave rebuild/link-write semantics for Phase 4. Existing mocks set `keys` but not `safe_keys`. |
| `src/types/fixed_entity_types.py::is_missing_fixed_entity_value`, `is_valid_fixed_entity_value` | The predicate recognizes null-like and blank scalars; fixed integer validation rejects non-integers and booleans. | Reuse these rules for both snapshots and changed target IDs. |
| `src/reconciliation/mapping_model.py::encode_local_key`, `EntityMapping`, `Link` | The encoder depends on column order and can encode null components as `<NULL>`; mapping entries store their own columns and link metadata. | Reject missing key components before encoding; compare against stored mapping columns when an entry exists. |
| `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name` | The inline update has the previous entity in memory and calls the fixed persistence strategy before `save_entity_boundary`, while holding a per-project lock. | Prepare and validate the change set before the boundary save; do not change the lock or write path in Phase 1. |
| `backend/app/services/entity_values_service.py::EntityValuesService.update_values`, `get_values` | External saves normalize request column order, check an optional ETag, and write the file; `get_values` reads and normalizes stored rows. | Read the previous rows and validate after request normalization but before `_write_values_file`; treat a not-yet-created values file as an empty prior snapshot. |
| `backend/app/services/project/entity_persistence_strategies.py::FixedEntityPersistenceStrategy` and `backend/app/utils/fixed_schema.py::derive_fixed_schema` | Inline values receive shape/type checks and a derived full column order, but no unique encoded-key check. External values do not use this fixed-value type gate. | Add the mapping-specific pre-write check to both paths without changing the existing column-order rules. |
| `backend/app/mappers/project_mapper.py::ProjectMapper._validate_mapping_sidecar` | Full Core conversion rejects a sidecar `public_id` that differs from current entity configuration. | For an existing entry, use its stored columns in the comparison without using a new Core conversion to infer them. Keep the mapper's current validation; configuration migration is outside this phase. |
| `src/normalizer.py` mapping-link application | Committed sidecar links can override a saved `public_id` during normalization. | Do not change normalization or treat a saved/sidecar difference alone as an edit. |

## Scope

**In scope:** One shared ordered-key helper; pure eligibility, row validation, and per-key change calculation; read-only preparation and pre-write rejection in inline and external fixed-value paths; focused tests.

**Out of scope:** Applying or locking sidecar writes, content hashes, pending responses, retry, client changes, administrative rebuild behavior, mapping-configuration migration, and non-fixed save synchronization.

**Affected parts:** Core mapping comparison, backend mapping/materialization default metadata, project entity and external-values persistence, existing entity APIs, and Core/backend tests. The existing mapping sidecar schema and API response models remain as they are in this phase.

## Work Breakdown

### Area 1: Share the ordered default key

**Objective:** New mapping entries have the same key order whether reached through the mapping API or materialization path.

**Affected code:** `src/reconciliation/fixed_entity_mapping_changes.py` **NEW**; `backend/app/services/mapping_service.py::MappingService._default_local_key`; `backend/app/services/materialization_service.py::MaterializationService._default_mapping_local_key`, `_ensure_mapping_entity`.

**Dependencies:** None.

**Tasks**

- [x] `T1.1` **Change:** Add one Core helper that returns a scalar key for one `TableConfig.safe_keys` item and an ordered list for multiple items; use it from both existing default-key methods.
  - **Target:** `src/reconciliation/fixed_entity_mapping_changes.py` **NEW**; `backend/app/services/mapping_service.py::MappingService._default_local_key`; `backend/app/services/materialization_service.py::MaterializationService._default_mapping_local_key`.
  - **Current → required:** Mapping API uses `safe_keys`, while materialization uses unordered `keys` → both use the same ordered rule. An absent key list still raises each service's existing error type.
  - **Implementation:** Keep service-level error translation in the existing wrappers. Do not replace an existing `EntityMapping.local_key` or `public_id`; only build defaults for an absent entry. Update materialization test mocks or use real `TableConfig` objects so `safe_keys` is meaningful.
  - **Constraints:** Preserve scalar-key format and `encode_local_key` behavior; no sidecar schema change or write-path change.
  - **Validation:** `V-1`, `V-2`: test single and ordered compound keys, missing keys, matching encoded values from both paths, and unchanged stored mapping columns.

**Completion evidence:** Mapping API and materialization default metadata encode the same two-column row in declared order, and an existing entry remains unchanged.

### Area 2: Calculate eligible fixed-row changes

**Objective:** A pure comparison reports only deliberate or missing-link changes and rejects ambiguous input.

**Affected code:** `src/reconciliation/fixed_entity_mapping_changes.py` **NEW**; `src/reconciliation/mapping_model.py::encode_local_key` and `src/types/fixed_entity_types.py` helpers are reused without changing them.

**Dependencies:** Area 1's default-key rule.

**Tasks**

- [x] `T1.2` **Change:** Define a typed, side-effect-free preparation result for eligibility, an optional proposed entry, and affected-key operations; compare previous and new row snapshots using the selected entry's stored columns.
  - **Target:** `src/reconciliation/fixed_entity_mapping_changes.py` **NEW**.
  - **Current → required:** The rebuild derives links from only the new saved rows → comparison uses both saved snapshots plus current links, without mutating the catalog or rows.
  - **Implementation:** Qualify only `type: fixed`. Propose a new entry only when materialization is enabled and no entry exists; otherwise return no sync work for a missing non-materialized entry. Require stored `local_key` and `public_id` columns in both usable snapshots. Reject missing key components and duplicate encoded keys, identifying row indexes. Use `is_missing_fixed_entity_value` for both ID snapshots and `is_valid_fixed_entity_value` plus integer conversion for every proposed non-blank upsert, including an unchanged row with a missing link. Record prior and new saved ID states and existing-link state for each affected key so later phases can apply or retry the exact changes.
  - **Constraints:** Unchanged key/ID pairs never overwrite links, including sidecar-only or older saved IDs. Add a missing link for an unchanged non-blank saved ID; keep a matching manual link without a replacement operation. A deliberate non-blank edit may replace any source at its key; a clear, row removal, or old side of a key change records a delete. Missing-to-missing does not delete a sidecar-only link. Do not save the proposed entry or links.
  - **Validation:** `V-1`: table-driven cases for blank IDs, zero, bool/float/invalid string IDs, absent columns, blank/duplicate/compound keys, unchanged and edited IDs, missing links, source replacement, row removal, and key changes. Assert exact operations and that input link metadata is unchanged.

**Completion evidence:** The new Core tests show a stable, complete change set and no mutation of its input catalog for every covered row transition.

### Area 3: Reject invalid saves before persistence

**Objective:** Both fixed-value save paths call the same preparation rule before writing rows.

**Affected code:** `backend/app/services/fixed_entity_mapping_change_service.py` **NEW**; `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/app/services/project_service.py::ProjectService.__init__`; `backend/app/services/entity_values_service.py::EntityValuesService.update_values`.

**Dependencies:** Area 2's comparison result. Phase 2 will coordinate the complete read/save/write sequence under the shared project lock.

**Tasks**

- [x] `T1.3` **Change:** Add a shared backend preparation service and invoke it before an inline fixed-entity boundary save.
  - **Target:** `backend/app/services/fixed_entity_mapping_change_service.py` **NEW**; `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/app/services/project_service.py::ProjectService.__init__`.
  - **Current → required:** Inline fixed rows are saved after the persistence strategy's shape/type checks without mapping-key comparison → prepare old and new full-column row snapshots and reject invalid mapping inputs before `save_entity_boundary`.
  - **Implementation:** Read the existing sidecar entry without writing it. Use the previously loaded project entity as the before-image and the normalized incoming fixed rows as the after-image; use `derive_fixed_schema` to align positional columns. Inject the preparation service into entity operations rather than importing `ProjectService` into the new module. The helper returns the change set for Phase 2 to consume when save coordination is added. Raise `SchemaValidationError` with the entity, field, and row for invalid ID or key data; the existing route decorator maps it to HTTP 400.
  - **Constraints:** Skip inline row comparison for `@load:`-backed entity-config edits, whose rows are saved through the external values path, and for non-fixed entities. An empty new row list still represents removals and must be compared. Do not change the entity ETag, rename path, or existing persistence strategy. An existing entry's columns take precedence over edited `entity.keys` or `entity.public_id`; do not rewrite its configuration.
  - **Validation:** `V-3`, `V-5`: verify the boundary save is not called on invalid changed ID, missing stored column, or duplicate key; valid and non-fixed updates retain their current behavior; mapper mismatch validation remains unchanged.

- [x] `T1.4` **Change:** Invoke the same preparation service before writing external fixed values.
  - **Target:** `backend/app/services/entity_values_service.py::EntityValuesService.update_values`; `backend/app/services/fixed_entity_mapping_change_service.py` **NEW**.
  - **Current → required:** External values are written before materialized mapping rebuild and lack mapping-key validation → compare normalized request rows with previously stored rows before `_write_values_file`.
  - **Implementation:** Keep the existing request-order and ETag checks first. Read prior values through the existing normalized read path when the file exists, or use an empty prior snapshot for a new file. Pass existing sidecar metadata and both snapshots to the Core comparison. Report the bad row or missing stored column through the route's current `ValueError` → HTTP 422 path. The helper returns the change set for Phase 2; do not apply it yet.
  - **Constraints:** Preserve CSV/parquet format handling, `@load:` rules, ETag behavior, and the current post-save rebuild until Phase 2 replaces that behavior. Do not create a directory or write a values file after a mapping-validation failure.
  - **Validation:** `V-4`: invalid changed ID, blank/duplicate key, and missing stored column leave the external file and sidecar unchanged; valid saves and legacy column-order remapping still work.

**Completion evidence:** Both routes reject invalid mapping inputs before row persistence and report the affected row or column; passing cases still use their existing response contracts.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` (`P-AC-3`) | `T1.2`, `T1.3`, `T1.4` | `V-1`, `V-3`, `V-4` | All missing-ID cases and zero compare correctly; invalid IDs/keys leave inline YAML or external values unchanged. |
| `PH1-AC-2` (`P-AC-5`) | `T1.1`, `T1.2`, `T1.3` | `V-1`, `V-2`, `V-3`, `V-5` | Both defaults encode ordered compound keys; an existing entry's columns are used without rewriting it. |
| `PH1-AC-3` (`P-AC-4`) | `T1.2` | `V-1` | Exact change sets exclude unchanged links and model old/new keys separately. |
| `PH1-AC-4` (`P-AC-2`) | `T1.2`, `T1.3`, `T1.4` | `V-1`, `V-3`, `V-4` | Fixed/materialized combinations produce the specified eligible or no-op result; non-fixed saves do not use the mapping comparison. |

## Validation And Testing

`V-1` and `V-2` complete phase milestone `VM-1`; `V-1`, `V-3`, and `V-4` complete `VM-2`. New tests use small inline rows and catalogs; protected API tests create projects through the authorized client.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Pure comparison in `tests/reconciliation/test_fixed_entity_mapping_changes.py` **NEW**; existing missing-value and encoder cases in `tests/types/test_fixed_entity_types.py` and `tests/reconciliation/test_mapping_sidecar.py` | `rtk uv run pytest tests/reconciliation/test_fixed_entity_mapping_changes.py tests/types/test_fixed_entity_types.py tests/reconciliation/test_mapping_sidecar.py -q` | `PH1-AC-1`–`PH1-AC-4` | Exact operations, errors with row indexes, immutable inputs; all tests pass. | Pass: the new Core file and the two existing files all pass. |
| `V-2` | Default-key behavior in `backend/tests/api/v1/test_mapping.py` and `backend/tests/services/test_materialization_service.py` | `rtk uv run pytest backend/tests/api/v1/test_mapping.py backend/tests/services/test_materialization_service.py -q` | `PH1-AC-2` | Mapping API and materialization choose the same ordered compound key; existing entry and error behavior remain valid. | Pass: both files passed in the focused baseline. |
| `V-3` | Inline pre-write and API checks in `backend/tests/services/project/test_entity_operations_boundary.py` and `backend/tests/api/v1/test_entities.py` | `rtk uv run pytest backend/tests/services/project/test_entity_operations_boundary.py backend/tests/api/v1/test_entities.py -q` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-4` | Invalid rows return HTTP 400 with row/field information and leave entity YAML unchanged; valid/non-fixed cases pass. | Pass: both files passed separately before changes. |
| `V-4` | External pre-write checks in `backend/tests/services/test_entity_values_service.py` and `backend/tests/api/v1/test_entities.py` | `rtk uv run pytest backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py -q` | `PH1-AC-1`, `PH1-AC-4` | Invalid rows return HTTP 422, leave an existing values file unchanged or create no new file, and preserve existing ETag and column-order behavior. | Pass: both files passed before changes. |
| `V-5` | Existing mapper rule in `backend/tests/mappers/test_project_mapper_file_path_integration.py` | `rtk uv run pytest backend/tests/mappers/test_project_mapper_file_path_integration.py -q` | `PH1-AC-2` preservation | Full Core conversion still rejects a sidecar/config `public_id` mismatch; comparison uses stored columns without migrating them. | Pass before changes. |
| `V-6` | Non-mutating formatting and lint checks for all changed Python files | Run the commands below. | All phase criteria | All checks pass after implementation. | Pass: all changed Python files pass `ruff`, `black --check`, and `isort --check-only`. |

```bash
phase1_files=(
  src/reconciliation/fixed_entity_mapping_changes.py
  backend/app/services/fixed_entity_mapping_change_service.py
  backend/app/services/mapping_service.py
  backend/app/services/materialization_service.py
  backend/app/services/project/entity_operations.py
  backend/app/services/project_service.py
  backend/app/services/entity_values_service.py
  tests/reconciliation/test_fixed_entity_mapping_changes.py
  backend/tests/api/v1/test_mapping.py
  backend/tests/services/test_materialization_service.py
  backend/tests/services/project/test_entity_operations_boundary.py
  backend/tests/services/test_entity_values_service.py
  backend/tests/api/v1/test_entities.py
)
rtk uv run ruff check "${phase1_files[@]}"
rtk uv run black --check "${phase1_files[@]}"
rtk uv run isort --check-only "${phase1_files[@]}"
```

**Existing broader baseline:** `rtk uv run pytest backend/tests/api/v1/test_entities.py backend/tests/services/test_project_service.py -q` failed before implementation only in `TestProjectService.test_load_configuration_multiple_entities`, `test_fixed_entity_persistence_accepts_strict_integer_ids`, and `test_add_entity_by_name_normalizes_fixed_columns`. Record these separately when running broader regression; do not attribute them to Phase 1. The focused mapping, materialization, value-service, fixed-type, and sidecar suite passed before changes.

After implementation, run `.venv/bin/graphify update .` as required by the root agent guide, then review the generated file changes. If a verified repository contract differs from this plan, stop and report the source and test results before changing the design or expanding scope.

### Implementation Evidence

Implemented and verified 2026-10-16 on branch `materialized-entity-mapping-sync` (HEAD `0dece8b9`). Commands used the repository virtualenv.

| Validation | Command | Result |
| --- | --- | --- |
| `V-1` | `pytest tests/reconciliation/test_fixed_entity_mapping_changes.py tests/types/test_fixed_entity_types.py tests/reconciliation/test_mapping_sidecar.py -q` | Pass |
| `V-2` | `pytest backend/tests/api/v1/test_mapping.py backend/tests/services/test_materialization_service.py -q` | Pass |
| `V-3` | `pytest backend/tests/services/project/test_entity_operations_boundary.py backend/tests/api/v1/test_entities.py -q` | Pass |
| `V-4` | `pytest backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py -q` | Pass |
| `V-5` | `pytest backend/tests/mappers/test_project_mapper_file_path_integration.py -q` | Pass |
| `V-6` | `ruff check`, `black --check`, `isort --check-only` on the phase file list | Pass |
| Broader regression | `pytest backend/tests/services backend/tests/api -q` | Pass |
| Broader baseline | `pytest backend/tests/api/v1/test_entities.py backend/tests/services/test_project_service.py -q` | One pre-existing failure: `TestProjectService::test_load_configuration_multiple_entities`. |
| Graphify | `.venv/bin/graphify update .` | Ran; the new modules and symbols are present in `graphify-out/graph.json`. |

The recorded broader baseline listed three failures. `test_fixed_entity_persistence_accepts_strict_integer_ids` and `test_add_entity_by_name_normalizes_fixed_columns` now pass, so only `test_load_configuration_multiple_entities` remains. It reproduces with the Phase 1 changes stashed, so it is a pre-existing, test-order-dependent project-cache failure rather than a Phase 1 regression; it fails only when the broader pair runs in one session.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Shared key rule and pure comparison **NEW** | `src/reconciliation/fixed_entity_mapping_changes.py` | `T1.1`, `T1.2` | Typed preparation result and passing `V-1`. |
| Mapping API default | `backend/app/services/mapping_service.py::MappingService._default_local_key` | `T1.1` | Ordered-key test passes in `V-2`. |
| Materialization default | `backend/app/services/materialization_service.py::MaterializationService._default_mapping_local_key` | `T1.1` | Ordered-key and existing-entry tests pass in `V-2`. |
| Backend read-only preparation **NEW** | `backend/app/services/fixed_entity_mapping_change_service.py` | `T1.3`, `T1.4` | Both save paths use one preparation rule without writing links. |
| Inline pre-write hook | `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/app/services/project_service.py::ProjectService.__init__` | `T1.3` | `V-3` proves rejection precedes boundary save. |
| External pre-write hook | `backend/app/services/entity_values_service.py::EntityValuesService.update_values` | `T1.4` | `V-4` proves rejection precedes file write. |
| Core comparison tests **NEW** | `tests/reconciliation/test_fixed_entity_mapping_changes.py` | `T1.1`, `T1.2` | `V-1` passes. |
| Default-key tests | `backend/tests/api/v1/test_mapping.py`; `backend/tests/services/test_materialization_service.py` | `T1.1` | `V-2` passes. |
| Save-path tests | `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/services/test_entity_values_service.py`; `backend/tests/api/v1/test_entities.py` | `T1.3`, `T1.4` | `V-3` and `V-4` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Ordered default key | Done | None | Mapping and materialization defaults share the Core helper; existing service error types retained. |
| Area 2: Eligible change set | Done | Area 1 | Pure Core comparison in `src/reconciliation/fixed_entity_mapping_changes.py`; no sidecar writes. |
| Area 3: Pre-write guards | Done | Area 2 | Both save paths call the read-only preparation service before persistence; Phase 2 still owns the coordinated write sequence. |

## Definition Of Done

- [x] `PH1-AC-1`–`PH1-AC-4` each have the task and validation results listed above; `VM-1` and `VM-2` are met.
- [x] All three areas and listed code/test deliverables are complete.
- [x] `V-1`–`V-6` pass; any broader-suite failures are compared with the recorded baseline and reported.
- [x] Existing non-fixed saves, ETag checks, mapper mismatch validation, normalization precedence, and mapping sidecar schema remain covered by regression checks.
- [x] No sidecar-write, retry, response-model, or mapping-configuration migration work has entered Phase 1.
- [x] The required graphify update has run and its generated changes have been reviewed.
- [x] Deviations and follow-up work are recorded; no unresolved question affects Phase 1 implementation or validation.

## Risks And Open Questions

- `ProjectMapper.to_core()` currently rejects a sidecar `public_id` that differs from entity config. The Phase 1 comparison must take an existing entry's stored columns directly; do not remove mapper validation or treat a config edit as a mapping migration. If that rule prevents the planned pre-write comparison in a real save path, report the conflicting call path before implementation changes its behavior.
- The external values service does not yet hold the shared project lock. Phase 1 only prepares and validates changes; Phase 2 must make its before-image read, row save, and sidecar update one coordinated sequence.
- Three `test_project_service.py` failures existed at planning time. Keep their baseline separate from new Phase 1 failures.
