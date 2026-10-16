# Sync Mapping Links After Fixed Entity Saves — Phase 2 Task Plan

## Phase Summary

**Goal:** Apply successful fixed-row changes during both ordinary save flows and serialize every backend mapping-sidecar writer.

**Readiness:** Validated. [Phase 2](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md#phase-2-coordinate-sidecar-writes-and-ordinary-saves) is marked ready after Phase 1. The [Phase 1 task plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_1_TASK_PLAN.md) records its comparison and pre-write guards as done, and those files and focused tests are present in the current workspace. Implementation must retain that output.

**Sources:** [Proposal](./MATERIALIZED_ENTITY_MAPPING_SYNC.md) and [phase plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md). Phase 2 covers `P-AC-1`, `P-AC-2`, `P-AC-4`, `P-AC-6`, and `P-AC-7`, with Phase 1's `P-AC-3` and `P-AC-5` rules as prerequisites.

**Constraints:** Keep the current mapping schema and sidecar-first normalization. An existing entry's stored `local_key` and `public_id` control row comparison; ordinary saves do not migrate them. Keep the administrative rebuild's current replacement behavior until Phase 4. Phase 3 owns the HTTP 200 pending result, retry endpoint, and client recovery; Phase 2's `VM-3` and `VM-4` establish successful writes only.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-7`): Every backend sidecar writer holds the project lock, uses a content version from exact disk bytes, writes atomically, and leaves no stale cached catalog. A missing sidecar has a distinct version token.
2. [x] `PH2-AC-2` (from `P-AC-1`, `P-AC-2`): A successful eligible inline or external save applies additions, ID edits or clears, removals, and row key changes without another ordinary request. Non-fixed saves and fixed entities without an eligible entry follow their existing limits.
3. [x] `PH2-AC-3` (from `P-AC-4`, `P-AC-6`): Both paths use the same affected-key rules. Untouched links retain source and metadata; an empty change set causes no sidecar write; an already matching manual link retains its metadata.

## Repository Findings

**Repository basis:** Branch `materialized-entity-mapping-sync`, commit `a231bd4b`, planning date 2026-10-16. The Phase 2 implementation and tests are uncommitted; the task plan is untracked. Graphify outputs were refreshed after implementation and retained. Graphify identified the mapping and save services; the findings below were checked in source and tests.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/reconciliation/mapping_manager.py::MappingManager.load`, `save` | Each instance caches catalogs; `load` may return a stale mutable object. `save` uses a temporary file and `os.replace`, then caches that instance, but has no disk content check. | Add a fresh disk snapshot with exact-byte SHA-256 or a distinct missing token; compare that version before atomic replacement and make later loads observe other writers' saves. Keep `MappingCatalog.version == "2.0"` as the schema version. |
| `backend/app/services/project_service.py::ProjectService._get_lock`; `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name` | A class-level `threading.Lock` serializes inline entity updates. Phase 1 prepares a change set inside that lock but discards it before `save_entity_boundary`. | Read the sidecar snapshot, compare rows, save the entity, and apply links in this existing lock scope. Do not acquire the same non-reentrant lock again in the shared sync helper. |
| `backend/app/services/entity_values_service.py::EntityValuesService.update_values`; `backend/app/api/v1/endpoints/entities.py::update_entity_values` | External saves check the ETag, prepare changes, write CSV/parquet, and return a file ETag without a project lock. The route then calls a full materialized rebuild. | Move the whole read/check/write/sync sequence under the project lock and replace the route's rebuild call with the shared affected-key save path. Preserve format, column normalization, and `If-Match` behavior. |
| `backend/app/services/fixed_entity_mapping_change_service.py::FixedEntityMappingChangeService`; `src/reconciliation/fixed_entity_mapping_changes.py::FixedRowChangeSet` | Phase 1 supplies the existing entry's columns, a proposed entry when eligible, and exact upsert/delete operations with saved-ID and prior-link states. Its current helper independently loads a catalog. | Prepare against the same fresh sidecar snapshot that will be written, then apply only the recorded operations. Keep the recorded states available for Phase 3. |
| `backend/app/services/mapping_service.py::MappingService.put_link`, `delete_link`; `backend/app/services/reconciliation/service.py::ReconciliationService.export_to_mapping`; `backend/app/services/materialization_service.py::MaterializationService.sync_materialized_entity_mappings` | These are the other three backend sidecar write paths. None holds the shared project lock around sidecar load and save. Reconciliation export skips existing manual links; the rebuild currently replaces manual links. | Lock their whole read/modify/write sequences and use disk versions. Preserve each operation's present link rules until Phase 4 changes the rebuild. |
| `backend/app/api/v1/endpoints/entities.py::EntityResponse`, `EntityValuesResponse`; `backend/app/services/project/entity_operations.py::compute_entity_etag`; `backend/app/services/entity_values_service.py::EntityValuesService._generate_etag` | Both save routes have established response models and different row-version calculations: a canonical entity-data hash for inline YAML and an mtime/size ETag for external files. | Reuse these row versions internally for Phase 3. Do not introduce the pending response fields in Phase 2. |

## Scope

**In scope:** Core sidecar snapshot/version and affected-key application; backend coordination for mapping CRUD, reconciliation export, the existing administrative rebuild, and inline/external fixed-value updates; focused concurrency, integrity, API, and regression tests.

**Out of scope:** Mapping schema changes, mapping-configuration migration, normalization precedence, a new retry route, pending response models, client changes, and Phase 4's additive rebuild behavior. Direct materialization is not an ordinary entity edit; its existing `EntityValuesService.update_values` call must still work when it writes external fixed values.

## Work Breakdown

### Area 1: Read and save versioned sidecar snapshots

**Objective:** A writer can identify the exact sidecar bytes it read, reject a stale write, and leave later readers with the latest catalog.

**Affected code:** `src/reconciliation/mapping_manager.py::MappingManager.load`, `save`, `invalidate`; `tests/reconciliation/test_mapping_sidecar.py`.

**Dependencies:** None.

**Tasks**

- [x] `T2.1` **Change:** Add a fresh sidecar snapshot and expected-version save to `MappingManager`.
  - **Target:** `src/reconciliation/mapping_manager.py::MappingManager.load`, `save`; `tests/reconciliation/test_mapping_sidecar.py`.
  - **Current → required:** A cached catalog and unguarded atomic save can overwrite changes → read exact bytes from disk, return a parsed catalog plus SHA-256 content version (or a distinct missing-file token), and compare that version immediately before `os.replace`.
  - **Implementation:** Add a disk-read snapshot method and a specific stale-version error in the existing module. Use the same raw bytes for hashing and YAML parsing; do not hash serialized models, timestamps, mtime, or `MappingCatalog.version`. Keep a missing-file token outside the hash format. Ensure the snapshot is independent of any cached mutable catalog. On a successful save, update or invalidate this manager's cache; on every later `load`, detect a changed disk version before returning a cached catalog. Preserve temporary-file cleanup on failure and return the post-write content version for later pending/retry work. Keep existing Core callers of `save` compatible, while requiring backend writers to pass an expected content version.
  - **Constraints:** Do not change YAML fields, sidecar naming, or atomic replacement. A failed version check must not mutate disk or cache; an empty save-time change set will skip `save` entirely.
  - **Validation:** `V-1`: test absent token, exact-byte hash changes from a whitespace-only edit, schema/content version distinction, stale-save rejection, atomic replacement failure cleanup, and a manager seeing another manager's save.

**Completion evidence:** A stale catalog cannot pass the expected-version check; every reload observes the saved sidecar, and the file remains intact on failed replacement.

### Area 2: Serialize all current backend sidecar writers

**Objective:** Mapping CRUD, reconciliation export, and the administrative rebuild read and write the sidecar under the same project lock used by entity updates.

**Affected code:** `backend/app/services/mapping_service.py::MappingService.put_link`, `delete_link`; `backend/app/services/reconciliation/service.py::ReconciliationService.export_to_mapping`; `backend/app/services/materialization_service.py::MaterializationService.sync_materialized_entity_mappings`; relevant existing route and service tests; `backend/tests/services/test_mapping_write_coordination.py` **NEW**.

**Dependencies:** `T2.1`.

**Tasks**

- [x] `T2.2` **Change:** Guard mapping CRUD and reconciliation export from project load through versioned sidecar save.
  - **Target:** `backend/app/services/mapping_service.py::MappingService.put_link`, `delete_link`; `backend/app/services/reconciliation/service.py::ReconciliationService.export_to_mapping`; `backend/tests/api/v1/test_mapping.py`; `backend/tests/api/v1/test_reconciliation_export.py`; `backend/tests/services/test_mapping_write_coordination.py` **NEW**.
  - **Current → required:** Each writer loads and mutates a sidecar without the project lock → each holds `ProjectService._get_lock(project_name)` across project/sidecar reads, link decisions, and expected-version save.
  - **Implementation:** Reuse the existing project lock and the fresh snapshot from `T2.1`. Keep the manual-link priority check inside the lock for export. Do not route export through `put_link`, which would change reconciliation provenance. Propagate a stale-version error without writing an older catalog.
  - **Constraints:** Preserve mapping endpoint authorization and response shapes, 404 behavior, `created_by` and confidence metadata, and export counts.
  - **Validation:** `V-2`: deterministic competing-writer test using two service instances and a synchronization event; route tests prove put/delete and export preserve unrelated links and manual-link priority.

- [x] `T2.3` **Change:** Guard the existing administrative materialized rebuild with the same versioned write sequence.
  - **Target:** `backend/app/services/materialization_service.py::MaterializationService.sync_materialized_entity_mappings`; `backend/tests/services/test_materialization_service.py`.
  - **Current → required:** Rebuild currently loads, replaces, and saves without a project lock or expected content version → hold that lock across saved-row read, sidecar read, replacement decision, and save.
  - **Implementation:** Load the sidecar from disk while locked and pass its content version to `MappingManager.save`. Keep `require_materialized`, result fields, and current full manual-link replacement semantics.
  - **Constraints:** Do not call this lock-acquiring administrative method from inside the newly locked external save; Phase 4 will change its bodyless behavior.
  - **Validation:** `V-2`, `V-6`: concurrent writer check and existing materialization/rebuild tests.

**Completion evidence:** Every backend `MappingManager.save` call has a matching lock-held disk snapshot; concurrent updates to different keys survive in one sidecar.

### Area 3: Apply only the recorded fixed-row changes

**Objective:** The Phase 1 change set changes only affected links and creates an entry only when it proposes one.

**Affected code:** `src/reconciliation/fixed_entity_mapping_changes.py::FixedRowChangeSet`; `backend/app/services/fixed_entity_mapping_change_service.py::FixedEntityMappingChangeService`; `backend/app/services/fixed_entity_mapping_sync_service.py` **NEW**; `tests/reconciliation/test_fixed_entity_mapping_changes.py`; `backend/tests/services/test_fixed_entity_mapping_sync_service.py` **NEW**.

**Dependencies:** `T2.1` and Phase 1's comparison output.

**Tasks**

- [x] `T2.4` **Change:** Implement a pure affected-key application function for `FixedRowChangeSet`.
  - **Target:** `src/reconciliation/fixed_entity_mapping_changes.py` (new function); `tests/reconciliation/test_fixed_entity_mapping_changes.py`.
  - **Current → required:** The change set is computed but not applied → create its proposed entry if needed, delete only recorded keys, and add or replace only recorded upserts with committed manual links.
  - **Implementation:** Preserve all unrelated `EntityMapping` fields and link objects; retain an already matching manual link without changing `created_at`, `committed_at`, `created_by`, confidence, notes, or review metadata. A deliberate edit can replace a reconciliation/import link at its key; a clear or removal deletes any source at its key. Return whether the catalog actually changed, including entry-only creation. Keep the recorded previous links and saved states stable for Phase 3.
  - **Constraints:** No file I/O or backend imports in Core; no whole-entity manual-link replacement.
  - **Validation:** `V-3`: table-driven add/edit/clear/remove/key-change, no-entry eligibility, untouched sidecar-only and older-ID links, matching-manual metadata, and zero-ID cases. Assert the exact changed keys and unchanged unrelated metadata.

- [x] `T2.5` **Change:** Add backend orchestration that prepares from one supplied disk snapshot and applies the change set after a successful row write.
  - **Target:** `backend/app/services/fixed_entity_mapping_change_service.py::FixedEntityMappingChangeService`; `backend/app/services/fixed_entity_mapping_sync_service.py` **NEW**; `backend/tests/services/test_fixed_entity_mapping_sync_service.py` **NEW**.
  - **Current → required:** Phase 1 preparation loads its own catalog and callers discard the result → accept the lock-held catalog snapshot, preserve the change set through the row save, then apply it and save only when it is non-empty.
  - **Implementation:** Keep Phase 1's pre-write errors and stored-column rules. Give the shared apply service the prepared change set, snapshot catalog and version, project path, and post-write row version; return internal success data with the row version and resulting sidecar content version. Check the expected disk version at save. Do not rederive changes from newly saved rows. The caller owns the project lock so this helper must not acquire it.
  - **Constraints:** A no-op must preserve exact sidecar bytes and `metadata.updated_at`. Save only after the row writer succeeds. Phase 3 will turn post-row sidecar failures into pending responses; do not invent a response model here.
  - **Validation:** `V-3`, `V-4`, `V-5`: no-op byte equality, entry-only creation, correct versions, and failure before row save causing no sidecar write.

**Completion evidence:** One shared apply path consumes the Phase 1 operations, and an unchanged or ineligible save does not touch sidecar bytes.

### Area 4: Wire both ordinary save flows

**Objective:** A successful inline or external fixed-row save persists its eligible mapping changes before returning.

**Affected code:** `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/app/services/entity_values_service.py::EntityValuesService.update_values`; `backend/app/api/v1/endpoints/entities.py::update_entity_values`; inline/external service and route tests.

**Dependencies:** `T2.2`–`T2.5`.

**Tasks**

- [x] `T2.6` **Change:** Keep the inline change set through `save_entity_boundary`, then apply it inside the existing project lock.
  - **Target:** `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/api/v1/test_entities.py`.
  - **Current → required:** Inline updates validate and discard the Phase 1 result → prepare against the lock-held disk snapshot, persist the entity once, get its post-write `compute_entity_etag`, and apply the exact affected keys before returning.
  - **Implementation:** Keep existing ETag conflict check, rename handling, persistence strategy, and `SchemaValidationError` conversion in their current order. Use the same project lock already held; only the ordinary non-rename inline fixed-values path runs save-time sync. If the boundary save fails, do not write mappings.
  - **Constraints:** Preserve `EntityResponse` and warnings contract in Phase 2. Do not synchronize non-fixed or `@load:` entity-config edits here.
  - **Validation:** `V-4`: authorized API and service cases for add, edit, clear, remove, key change, unchanged/older/blank saved ID, non-fixed entity, and an ineligible non-materialized fixed entity; ETag conflict and invalid input still prevent writes.

- [x] `T2.7` **Change:** Hold the project lock through the external file save and affected-key sidecar update; remove the route's full rebuild call.
  - **Target:** `backend/app/services/entity_values_service.py::EntityValuesService.update_values`; `backend/app/api/v1/endpoints/entities.py::update_entity_values`; `backend/tests/services/test_entity_values_service.py`; `backend/tests/api/v1/test_entities.py`.
  - **Current → required:** External values are written without the project lock and the route then rebuilds all manual links → perform `If-Match`, old-row read, disk sidecar snapshot, Phase 1 comparison, file write, new file ETag, and shared affected-key apply in one lock scope.
  - **Implementation:** Reuse existing CSV/parquet normalization and stored-row read. Let the service perform sync so direct callers, including external materialization, follow the same rule. Remove only the automatic `sync_materialized_entity_mappings(..., require_materialized=False)` call from the values route; retain the separate administrative endpoint. Preserve the existing valid-input response fields.
  - **Constraints:** Keep HTTP 409 for stale `If-Match`, HTTP 422 for pre-write mapping validation, and no file creation on invalid rows. Do not acquire the project lock again through the administrative rebuild.
  - **Validation:** `V-5`: authorized route and service cases for the same affected-key transitions, initial missing entry, non-materialized entry, ineligible/non-fixed saves, legacy column order, CSV/parquet, ETag mismatch, and no-op byte preservation. `V-6` checks existing materialization and mapper behavior.

**Completion evidence:** Both ordinary routes return success with only intended link changes persisted; no route performs a full rebuild after a row save.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH2-AC-1` (`P-AC-7`) | `T2.1`, `T2.2`, `T2.3`, `T2.5`, `T2.6`, `T2.7` | `V-1`, `V-2`, `V-4`, `V-5` | Exact-byte versions, distinct missing token, stale-write rejection, fresh caches, and serialized backend writers. |
| `PH2-AC-2` (`P-AC-1`, `P-AC-2`) | `T2.4`, `T2.5`, `T2.6`, `T2.7` | `V-3`, `V-4`, `V-5` | Both routes persist the expected add/edit/clear/remove/key-change links and respect eligibility. |
| `PH2-AC-3` (`P-AC-4`, `P-AC-6`) | `T2.4`, `T2.5`, `T2.6`, `T2.7` | `V-3`, `V-4`, `V-5`, `V-6` | Unaffected links and metadata match their before-images, matching manual links remain intact, and no-op saves leave sidecar bytes unchanged. |

## Validation And Testing

`V-1` and `V-2` complete `VM-3`; `V-3`–`V-5` complete `VM-4`. Protected route tests use `authorized_client` and create projects through `POST /api/v1/projects` before writing extra sidecar or values files.

The following focused regression command ran all test files listed in `V-1`–`V-6` together; it passed:

```bash
.venv/bin/pytest tests/reconciliation/test_mapping_sidecar.py tests/reconciliation/test_fixed_entity_mapping_changes.py backend/tests/services/test_mapping_write_coordination.py backend/tests/services/test_fixed_entity_mapping_sync_service.py backend/tests/api/v1/test_mapping.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/services/test_materialization_service.py backend/tests/services/project/test_entity_operations_boundary.py backend/tests/services/project/test_entity_operations_optimistic_locking.py backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py backend/tests/mappers/test_project_mapper_file_path_integration.py --tb=short -q
```

| ID | Check and target | Command or method | Covers | Expected result | Result |
|---|---|---|---|---|---|
| `V-1` | Version, cache, and atomic-write cases in `tests/reconciliation/test_mapping_sidecar.py` | Included in the focused regression command above. | `PH2-AC-1` | Missing token differs from SHA-256; exact-byte edits change the version; stale or failed writes preserve disk; a second manager's save is visible. | Pass. |
| `V-2` | Lock and writer checks in `backend/tests/services/test_mapping_write_coordination.py` **NEW**, `backend/tests/api/v1/test_mapping.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/services/test_materialization_service.py` | Included in the focused regression command above. | `PH2-AC-1` | Competing writers serialize; changes at different keys survive; CRUD/export/rebuild retain present contracts. | Pass. |
| `V-3` | Pure application and service integration in `tests/reconciliation/test_fixed_entity_mapping_changes.py` and `backend/tests/services/test_fixed_entity_mapping_sync_service.py` **NEW** | Included in the focused regression command above. | `PH2-AC-2`, `PH2-AC-3` | Exact operations only, metadata preservation, entry-only creation, and no-op byte identity. | Pass. |
| `V-4` | Inline route and boundary checks in `backend/tests/services/project/test_entity_operations_boundary.py`, `backend/tests/services/project/test_entity_operations_optimistic_locking.py`, and `backend/tests/api/v1/test_entities.py` | Included in the focused regression command above. | `PH2-AC-1`–`PH2-AC-3` | One inline save persists affected links; invalid rows, conflicts, non-fixed, and no-op cases keep their specified behavior. | Pass. |
| `V-5` | External service and route checks in `backend/tests/services/test_entity_values_service.py` and `backend/tests/api/v1/test_entities.py` | Included in the focused regression command above. | `PH2-AC-1`–`PH2-AC-3` | One external save persists affected links; legacy order, file format, ETag, and eligibility cases pass. | Pass. |
| `V-6` | Materialization and mapper preservation in `backend/tests/services/test_materialization_service.py`, `backend/tests/mappers/test_project_mapper_file_path_integration.py`, and `tests/reconciliation/test_mapping_sidecar.py` | Included in the focused regression command above. | `PH2-AC-3` and preserved contracts | Administrative rebuild still has its pre-Phase-4 behavior; sidecar-first validation and mapping schema stay intact. | Pass. |
| `V-7` | Ruff, Black, and isort checks on 22 relevant Python files, including all changed Python files | Commands below. | All phase criteria | All checks pass. | Pass: Ruff passed; Black reported 22 files unchanged; isort passed. |

```bash
phase2_files=(
  src/reconciliation/mapping_manager.py
  src/reconciliation/fixed_entity_mapping_changes.py
  backend/app/services/fixed_entity_mapping_change_service.py
  backend/app/services/fixed_entity_mapping_sync_service.py
  backend/app/services/mapping_service.py
  backend/app/services/reconciliation/service.py
  backend/app/services/materialization_service.py
  backend/app/services/project/entity_operations.py
  backend/app/services/entity_values_service.py
  backend/app/api/v1/endpoints/entities.py
  tests/reconciliation/test_mapping_sidecar.py
  tests/reconciliation/test_fixed_entity_mapping_changes.py
  backend/tests/services/test_mapping_write_coordination.py
  backend/tests/services/test_fixed_entity_mapping_sync_service.py
  backend/tests/api/v1/test_mapping.py
  backend/tests/api/v1/test_reconciliation_export.py
  backend/tests/services/test_materialization_service.py
  backend/tests/services/project/test_entity_operations_boundary.py
  backend/tests/services/project/test_entity_operations_optimistic_locking.py
  backend/tests/services/test_entity_values_service.py
  backend/tests/api/v1/test_entities.py
)
rtk uv run ruff check "${phase2_files[@]}"
rtk uv run black --check "${phase2_files[@]}"
rtk uv run isort --check-only "${phase2_files[@]}"
```

The exact checks above were run against 22 relevant Python files: `.venv/bin/ruff check "${phase2_files[@]}"`, `.venv/bin/black --check "${phase2_files[@]}"`, and `.venv/bin/isort --check-only "${phase2_files[@]}"`. All passed. `.venv/bin/graphify update .` refreshed `graph.json`, `GRAPH_REPORT.md`, labels, and the Shape Shifter call-flow HTML; `graph.html` visualization was skipped because the graph has 21,206 nodes, above its 5,000-node limit. These generated changes were retained. A source/test review confirmed the generated artifacts are the result of the required graph refresh. If current source or tests conflict with this plan, stop and report the specific conflict before changing the design or widening scope.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Versioned sidecar I/O and cache freshness | `src/reconciliation/mapping_manager.py`; `tests/reconciliation/test_mapping_sidecar.py` | `T2.1` | `V-1` passes. |
| Locked mapping CRUD and export | `backend/app/services/mapping_service.py`; `backend/app/services/reconciliation/service.py`; `backend/tests/api/v1/test_mapping.py`; `backend/tests/api/v1/test_reconciliation_export.py` | `T2.2` | `V-2` passes. |
| Locked administrative rebuild | `backend/app/services/materialization_service.py`; `backend/tests/services/test_materialization_service.py` | `T2.3` | `V-2`, `V-6` pass without changing rebuild semantics. |
| Writer coordination tests **NEW** | `backend/tests/services/test_mapping_write_coordination.py` | `T2.2` | Deterministic concurrent-writer assertions pass in `V-2`. |
| Affected-key application | `src/reconciliation/fixed_entity_mapping_changes.py`; `tests/reconciliation/test_fixed_entity_mapping_changes.py` | `T2.4` | `V-3` passes. |
| Shared save-time orchestration **NEW** | `backend/app/services/fixed_entity_mapping_sync_service.py` | `T2.5` | Internal result carries row and sidecar versions; `V-3` passes. |
| Snapshot-aware preparation and orchestration tests | `backend/app/services/fixed_entity_mapping_change_service.py`; `backend/tests/services/test_fixed_entity_mapping_sync_service.py` **NEW** | `T2.5` | `V-3` passes; no-op does not write. |
| Inline save integration | `backend/app/services/project/entity_operations.py`; `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/api/v1/test_entities.py` | `T2.6` | `V-4` passes. |
| External save integration | `backend/app/services/entity_values_service.py`; `backend/app/api/v1/endpoints/entities.py`; `backend/tests/services/test_entity_values_service.py`; `backend/tests/api/v1/test_entities.py` | `T2.7` | `V-5` passes; no automatic full rebuild call remains. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Versioned snapshots | Done | None | `T2.1`; `V-1` passed. |
| Area 2: Backend writers | Done | Area 1 | `T2.2`–`T2.3`; `V-2`, `V-6` passed. |
| Area 3: Affected-key apply | Done | Area 1, Phase 1 output | `T2.4`–`T2.5`; `V-3` passed. |
| Area 4: Ordinary saves | Done | Areas 2–3 | `T2.6`–`T2.7`; `V-4`–`V-5` passed. |

## Definition Of Done

- [x] `PH2-AC-1`–`PH2-AC-3` have passing task and validation results; `VM-3` and `VM-4` are met.
- [x] All four areas and listed deliverables are complete.
- [x] `V-1`–`V-7` pass, including deterministic writer coordination and both authorized save routes.
- [x] Existing ETag checks, pre-write errors, row formats, link provenance, sidecar schema, sidecar-first normalization, and administrative rebuild behavior are regression-tested.
- [x] The internal post-write row version, sidecar content version, and exact change set are available for Phase 3 without recomputing from saved rows.
- [x] The graphify update is run after code changes and generated changes are reviewed.
- [x] Any deviations and Phase 3 follow-up are recorded; no unresolved question affects Phase 2's successful-write path.

## Risks And Open Questions

- **Partial writes remain until Phase 3:** The row and sidecar files do not form one transaction. Phase 2 validates successful sync; a failure after row persistence can still leave links pending. Do not mark the overall proposal complete or change the response contract ad hoc. Phase 3 must return the structured pending result and implement retry before save-time sync is treated as complete.
- **Lock scope:** `ProjectService._get_lock` is a process-local, non-reentrant `threading.Lock`. Keep the shared apply helper lock-free and avoid nested calls to lock-acquiring writers. The disk version check rejects a stale snapshot, but it is not a cross-process file lock; deployment with independently writing processes needs that limitation addressed before claiming cross-process serialization.
- **Validation correction:** Regression testing exposed that the shared row index encoded a single-column key as a one-item list. It now passes the scalar value to the existing key encoder; focused Core and external-save tests cover the corrected key format.
