# Sync Mapping Links After Fixed Entity Saves — Phase 3 Task Plan

## Phase Summary

**Goal:** Return a clear pending result when fixed rows are saved but mapping links are not, and let the client retry the exact changes safely.

**Readiness:** Validated. [Phase 3](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md#phase-3-return-pending-saves-and-support-retry) is marked ready after Phase 2. The [Phase 2 task plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_2_TASK_PLAN.md) records `VM-3` and `VM-4` as complete; its save, lock, version, and affected-key code is present and passes the focused baseline below.

**Sources:** [Proposal](./MATERIALIZED_ENTITY_MAPPING_SYNC.md) and [phase plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md). This phase covers `P-AC-6` through `P-AC-8` and completes `VM-5` and `VM-6`.

**Constraints:** Preserve Phase 1 comparison rules and Phase 2 successful saves. Keep the current mapping file schema, atomic replacement, per-project lock, existing entity/value ETags, and sidecar-first normalization. The retry operation must use the supplied changes, not compare current rows against a new before-image. The materialized rebuild remains a separate administrative operation; Phase 4 changes its default.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-6`, `P-AC-8`): A sidecar failure or affected-key conflict after either row save returns HTTP 200 with the ordinary save fields and the same structured pending `mapping_sync` result, including `rows_saved: true`. The client reports a partial save.
2. [x] `PH3-AC-2` (from `P-AC-7`, `P-AC-8`): Retry applies the supplied changes without recomputing them. Unrelated file edits do not block it; changed affected keys return HTTP 409 with those keys; repeated application does not write the sidecar again.
3. [x] `PH3-AC-3` (from `P-AC-8`): The client can submit the pending result to the distinct retry endpoint and shows changed-key conflicts for review.

## Repository Findings

**Repository basis:** Branch `materialized-entity-mapping-sync`, commit `8ff9532e`, planning date 2026-10-16. The worktree was clean before this plan was written. Current source and tests, rather than Graphify output, establish the findings below.

| Source | Verified behavior | Planning implication |
|---|---|---|
| `src/reconciliation/fixed_entity_mapping_changes.py::FixedRowChangeSet`, `LinkUpsert`, `LinkDelete` | The prepared change set contains exact affected keys, prior saved IDs, new saved IDs, prior links, and optional entry creation. `apply_fixed_row_change_set` already preserves matching manual-link metadata. | Serialize this prepared work and record the saved post-write state; retry must not call `compute_fixed_row_change_set`. Normalize missing/NumPy values before JSON output. |
| `src/reconciliation/mapping_manager.py::MappingManager.load_snapshot`, `save` | A fresh snapshot hashes exact disk bytes; `save` checks `expected_version`, atomically replaces the file, and refreshes its cache. The missing-file token is `missing`. | Re-read under the lock at retry; use the version as a fast check, with affected-key comparisons deciding conflicts. |
| `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name` and `backend/app/services/project_service.py::ProjectService.update_entity_by_name` | Inline saves hold `ProjectService._get_lock`, prepare changes before persistence, then call `apply_change_set`. They currently return only warnings and propagate a post-save mapping failure. | Carry the pending result through the service return value without turning a pre-write failure into a partial success. Keep rename behavior and existing ETag rejection. |
| `backend/app/services/entity_values_service.py::EntityValuesService._update_values_locked`, `EntityValuesData` | External saves hold the same project lock, write CSV/parquet, compute an mtime-and-size ETag, then apply mapping changes. The response data has no mapping status. | Return the external file's new ETag and the pending result together. Its ETag is a hint, not proof that affected rows are unchanged. Reuse the stored fixed-row normalization for retry. |
| `backend/app/services/fixed_entity_mapping_sync_service.py::FixedEntityMappingSyncService.apply_change_set` | The service receives the exact change set and row/sidecar versions but has only a success result. | Capture link and entry preconditions before application mutates the snapshot; report only post-row mapping write/version conflicts as pending. |
| `backend/app/api/v1/endpoints/entities.py::EntityResponse`, `EntityValuesResponse`; `backend/app/api/v1/endpoints/mapping.py::router` | Both save routes use separate response models. The mapping router already has project authorization and is registered in `backend/app/api/v1/api.py`. | Add one shared pending model to both responses and add the retry route to the existing router; no router registration edit is needed. |
| `backend/app/utils/error_handlers.py::handle_endpoint_errors`, `backend/app/exceptions.py::ResourceConflictError` | A resource conflict becomes HTTP 409 with structured `detail.context`. | Return changed keys in a stable context field for the retry client. |
| `frontend/src/api/entities.ts`, `frontend/src/stores/entity.ts`, `frontend/src/components/entities/EntityFormDialog.vue` | The API types lack `mapping_sync`. The store caches inline update results. Save and Save & Close separately call the external values API and show complete success after HTTP 200. | Type the shared payload, retain it per project/entity, and handle pending and retry in both buttons without showing full success or resubmitting rows. |

## Scope

**In scope:** A shared pending save contract, saved-row/link preconditions, partial-save responses from both fixed-row paths, a protected fixed-entity retry endpoint, affected-key conflict checks, client retry and review messages, focused tests, and user guidance for partial saves.

**Out of scope:** Recomputing links from all saved rows, changing `from-materialized` rebuild behavior, non-fixed save synchronization, mapping configuration migration, a separate mapping editor, and cross-process file locking.

**Affected parts:** Core retry comparisons in `src/reconciliation/`; backend models, mapper, services, and routes; Vue API/store/editor; authorized API tests, service tests, frontend tests, and `docs/USER_GUIDE.md`.

## Work Breakdown

### Area 1: Define the pending payload and affected-key checks

**Objective:** A JSON-safe payload records the exact operations and enough post-save row and pre-write link state to retry without guessing user intent.

**Affected code:** `src/reconciliation/fixed_entity_mapping_changes.py`, `backend/app/mappers/project_mapper.py`; `src/reconciliation/fixed_entity_mapping_retry.py` **NEW**; `backend/app/models/mapping_sync.py` **NEW**.

**Dependencies:** Phase 2 change set, disk snapshots, and row versions.

**Tasks**

- [x] `T3.1` **Define:** Add a typed pending `mapping_sync` model and convert prepared Core changes to and from it through `ProjectMapper`.
  - **Target:** `backend/app/models/mapping_sync.py` **NEW**; `backend/app/mappers/project_mapper.py::ProjectMapper`; `src/reconciliation/fixed_entity_mapping_changes.py::FixedRowChangeSet` and operation types.
  - **Current → required:** Internal dataclasses and prior links stay in memory → one serializable pending object has `status: "pending"`, `rows_saved: true`, project/entity identity, storage kind (`inline` or `external`), stored `local_key`/`public_id`, exact upsert/delete operations and optional proposed entry, expected saved-row version, expected sidecar content version, and each affected key's expected post-write row presence/ID and pre-write link (including metadata). Include the prior entry state for entry creation.
  - **Implementation:** Use explicit Pydantic request/response fields and JSON-safe integer-or-null saved IDs. Represent row absence separately from a present row with a missing ID. Reject duplicate keys, incompatible operation fields, and malformed entry configuration. Record a full prior link, so a metadata edit at an affected key is detected. Do not put raw pandas/NumPy values or a file path in the API payload; resolve project files from the authorized project. Preserve exact key strings and operation order. Keep the sidecar schema unchanged.
  - **Validation:** `V-1`: round-trip add/edit/clear/remove/key-change, missing ID, zero ID, entry-only creation, and prior reconciliation/import link; assert JSON contains no NaN and malformed payloads fail validation.

- [x] `T3.2` **Check:** Add pure retry comparison for affected saved rows, sidecar links, and entry configuration.
  - **Target:** `src/reconciliation/fixed_entity_mapping_retry.py` **NEW**; `src/reconciliation/fixed_entity_mapping_changes.py` row-index helper if sharing its current encoded-key and missing-value rules requires extraction.
  - **Current → required:** A sidecar version mismatch can only fail the write → retry uses versions as fast checks and compares each affected key's actual state with its recorded post-save row state and prior or already-applied link state.
  - **Implementation:** Return changed keys for row or link differences. Allow unrelated row/sidecar edits; accept per-key links already at the requested manual target or already deleted. If every requested change is already present, return no-op. For mixed already-applied and unapplied keys, apply only the remaining operations when their prior states still match. Require a matching stored mapping configuration; for entry creation, accept an equivalent already-created entry and report incompatible entry changes for review. Share the existing key encoder and missing-value rule; never infer a new change set from current rows.
  - **Validation:** `V-2`: unchanged, unrelated-edit, affected-row-edit, affected-link-metadata-edit, already-applied, mixed, entry-only, missing-row, and compound-key cases; assert exact conflict keys and no modification of input snapshots.

**Completion evidence:** The pending payload survives JSON round-trip and the pure checker distinguishes unrelated edits, affected-key conflicts, and already-applied operations.

### Area 2: Return pending results from both save paths

**Objective:** Once rows are committed, a mapping write failure becomes an HTTP 200 partial-save result with the ordinary save fields intact.

**Affected code:** `backend/app/services/fixed_entity_mapping_sync_service.py`, `backend/app/services/project/entity_operations.py`, `backend/app/services/project_service.py`, `backend/app/services/entity_values_service.py`, `backend/app/api/v1/endpoints/entities.py`.

**Dependencies:** Area 1.

**Tasks**

- [x] `T3.3` **Update:** Return pending mapping status from the inline entity save.
  - **Target:** `backend/app/services/project/entity_operations.py::EntityOperations.update_entity_by_name`; `backend/app/services/project_service.py::ProjectService.update_entity_by_name`; `backend/app/services/fixed_entity_mapping_sync_service.py::FixedEntityMappingSyncService.apply_change_set`; `backend/app/api/v1/endpoints/entities.py::update_entity`, `EntityResponse`.
  - **Current → required:** A post-row sidecar failure propagates as a failed request → the route returns HTTP 200 with normal entity fields, warnings, new ETag, and the shared pending object. Successful/no-op saves have no pending object.
  - **Implementation:** Retain the prepared change set and a copy of pre-write link/entry state before applying it. Compute the post-save entity ETag from the persisted entity. Return a typed service result containing warnings and optional pending status; preserve rename and non-fixed return behavior. Catch `MappingVersionConflictError` and sidecar I/O failures only after row persistence, log the cause, and build pending from the original change set. Do not catch row write, pre-write validation, or ordinary If-Match failures as pending.
  - **Validation:** `V-3`: inject sidecar save failure and stale affected-key write after an inline row save; assert HTTP 200, `rows_saved`, exact operations/versions/preconditions, persisted rows, unchanged or competing sidecar, and ordinary response fields. Assert pre-write and row-write failures keep their existing HTTP behavior.

- [x] `T3.4` **Update:** Return the same pending shape from the external values save.
  - **Target:** `backend/app/services/entity_values_service.py::EntityValuesService._update_values_locked`, `EntityValuesData`; `backend/app/api/v1/endpoints/entities.py::update_entity_values`, `EntityValuesResponse`.
  - **Current → required:** A post-file sidecar failure propagates → the route returns HTTP 200 with normal columns, values, format, count, new ETag, and the same pending model.
  - **Implementation:** Carry the pre-write sidecar snapshot and exact prepared change set through the file write; use the newly written file ETag as `expected_row_version`. Report only post-row sidecar failures as pending. Preserve CSV/parquet, fixed-column normalization, If-Match, and non-fixed behavior; do not call the administrative rebuild.
  - **Validation:** `V-3`: repeat failure and conflict cases through the external route for CSV and parquet, and compare the pending field's schema with the inline result. Verify persisted rows and ETag; verify invalid columns/IDs and stale If-Match remain failures before a row write.

**Completion evidence:** `VM-5` passes: both routes return the same typed pending field with `rows_saved: true` after a post-row mapping failure, and neither reports full success.

### Area 3: Add the distinct retry operation

**Objective:** A protected retry either completes only recorded changes, reports changed affected keys, or confirms that the work was already applied.

**Affected code:** `backend/app/services/fixed_entity_mapping_retry_service.py` **NEW**; `backend/app/api/v1/endpoints/mapping.py`; `backend/app/models/mapping_sync.py` **NEW**; `backend/app/services/entity_values_service.py` and `backend/app/services/project_service.py` for existing read helpers.

**Dependencies:** Areas 1–2.

**Tasks**

- [x] `T3.5` **Implement:** Apply an exact pending request under the existing project lock.
  - **Target:** `backend/app/services/fixed_entity_mapping_retry_service.py` **NEW**; `src/reconciliation/fixed_entity_mapping_retry.py` **NEW**; `backend/app/mappers/project_mapper.py::ProjectMapper`.
  - **Current → required:** No retry service exists → one operation reads current saved rows and a fresh disk sidecar snapshot, checks affected keys, and applies only safe remaining changes.
  - **Implementation:** Resolve the authorized project and fixed entity, then acquire `ProjectService._get_lock` once. Read inline values from the saved entity or external values through `EntityValuesService`'s existing normalization without calling a lock-taking update method. Verify request project/entity/storage kind and stored mapping columns. Check saved post-write affected rows first, then already-applied links, then prior link/entry preconditions. Use `MappingManager.save(..., expected_version=...)` for atomic replacement and cache freshness; retry a whole-file version race only by re-reading and rechecking affected keys while still within the defined lock scope. Return a success result with `changed: false` for a complete no-op. Return a conflict with the sorted changed keys and no writes when review is needed. Do not recompute from current rows or fall back to rebuild.
  - **Validation:** `V-2`, `V-4`: service tests for unrelated sidecar/row edits, affected row/link edits, mixed applied/unapplied changes, entry creation, repeated retry byte identity, and one retry after a simulated version race. Include both storage formats and column order.

- [x] `T3.6` **Expose:** Add `PATCH /projects/{project_name}/mapping/retry-fixed-entity/{entity_name}`.
  - **Target:** `backend/app/api/v1/endpoints/mapping.py::router`; `backend/app/models/mapping_sync.py` **NEW**; `backend/app/exceptions.py::ResourceConflictError` usage.
  - **Current → required:** Mapping routes expose CRUD only → an `Action.EDIT` protected route accepts the pending `mapping_sync` object and returns a typed retry result.
  - **Implementation:** Use the existing mapping router registration. Validate body shape and route/body identity before touching files. Return HTTP 409 with `detail.context.changed_keys` for affected-key conflicts, plus a clear entry-configuration conflict indicator when no link key exists. Keep malformed bodies at HTTP 422, missing project/entity at the established not-found status, and successful/repeated retry at HTTP 200. Do not weaken mapping CRUD authorization.
  - **Validation:** `V-4`: authorized route tests for success, no-op, unrelated edits, exact changed keys, body/path mismatch, malformed payload, non-fixed entity, and unauthenticated access.

**Completion evidence:** `VM-6` backend checks pass; an unrelated edit survives retry, an affected edit yields 409 without a write, and a second retry leaves sidecar bytes unchanged.

### Area 4: Show partial saves and support client retry

**Objective:** The editor retains a pending result, offers retry without sending rows again, and shows conflicts for review.

**Affected code:** `frontend/src/api/entities.ts`, `frontend/src/stores/entity.ts`, `frontend/src/components/entities/EntityFormDialog.vue`, `docs/USER_GUIDE.md`.

**Dependencies:** Areas 2–3.

**Tasks**

- [x] `T3.7` **Type and retain:** Add the shared pending/result types and retry API call; store pending work by project and entity.
  - **Target:** `frontend/src/api/entities.ts::EntityResponse`, `EntityValuesResponse`, `entitiesApi`; `frontend/src/stores/entity.ts::useEntityStore`.
  - **Current → required:** HTTP 200 is treated as complete and pending data is discarded → both response types expose the same optional `mapping_sync`; the store retains pending data until retry succeeds or the user explicitly dismisses it for review.
  - **Implementation:** Add `entitiesApi.retryFixedEntityMapping` using `PATCH` and the returned pending object unchanged. Keep pending scoped to its project/entity and clear it on store reset; do not overwrite it with a later entity GET/list response. Store the inline pending result during `updateEntity`; give the external path an action to store its result. A successful retry clears only that pending item. Keep existing entity ETag caching.
  - **Validation:** `V-5`: API method/URL/body and response typing; store tests for inline and external pending state, unrelated refresh, project change/reset, and clear-on-retry.

- [x] `T3.8` **Present:** Handle pending and retry in both editor save actions, then document the recovery steps.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::handleSubmit`, `handleSubmitAndClose`; `docs/USER_GUIDE.md` fixed-entity editing and mapping guidance.
  - **Current → required:** Save shows “Saved successfully” and Save & Close closes on any HTTP 200 → pending shows “Rows saved; mapping changes pending,” offers Retry, and does not show full success or auto-close. A 409 lists changed keys and tells the user to review current rows and mapping links.
  - **Implementation:** Check the inline response and, when used, the external response before the success indicator or close action. Keep the updated ETag and saved state so Retry sends only the pending payload; never resubmit rows. Disable duplicate retries while one is running. On success clear the pending display and show completion; on 409 retain it and show the server's changed keys. Preserve the existing error message for a real external-values write failure. Explain partial save, retry, and conflict review in the user guide.
  - **Validation:** `V-6`: component tests for Save and Save & Close on both paths, visible pending notice and Retry button, no false success/close, one retry call without a second row save, no-op retry, and 409 changed-key display. `V-7` checks the documented steps against the implemented UI.

**Completion evidence:** `VM-6` client checks pass; a user can see that rows were saved, retry only the pending mapping changes, and identify keys that require review.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
|---|---|---|---|
| `PH3-AC-1` (`P-AC-6`, `P-AC-8`) | `T3.1`, `T3.3`, `T3.4`, `T3.7`, `T3.8` | `V-1`, `V-3`, `V-6` | Both HTTP 200 save responses contain the same pending shape and preserved normal fields; editor identifies partial success. |
| `PH3-AC-2` (`P-AC-7`, `P-AC-8`) | `T3.1`, `T3.2`, `T3.5`, `T3.6` | `V-1`, `V-2`, `V-4` | Exact changes apply; unrelated edits pass; affected edits list keys in 409; repeat retry makes no write. |
| `PH3-AC-3` (`P-AC-8`) | `T3.6`, `T3.7`, `T3.8` | `V-4`, `V-5`, `V-6`, `V-7` | Client retries through the distinct protected route and presents conflicts for review. |

## Validation And Testing

`V-3` completes `VM-5`. `V-2`, `V-4`, `V-5`, and `V-6` complete `VM-6`. Use `authorized_client` and create test projects through `POST /api/v1/projects` before placing sidecar or values files. Inject sidecar save failures after a successful row write; assert the saved row file/YAML independently of the HTTP response. Proposed test files are marked **NEW**.

| ID | Check and target | Command or method | Covers | Expected result | Result |
|---|---|---|---|---|---|
| `V-1` | Pending model and conversion tests in `backend/tests/models/test_mapping_sync.py` **NEW** | `rtk uv run pytest backend/tests/models/test_mapping_sync.py -q` | `PH3-AC-1`, `PH3-AC-2` | Exact operations and preconditions round-trip; missing/zero IDs and malformed payloads behave as specified. | Pass: 15 tests, including add/edit/clear/remove/key-change, zero ID, entry-only creation, prior reconciliation/import links, JSON safety, and malformed payloads. |
| `V-2` | Pure retry checks in `tests/reconciliation/test_fixed_entity_mapping_retry.py` **NEW** | `rtk uv run pytest tests/reconciliation/test_fixed_entity_mapping_retry.py -q` | `PH3-AC-2` | Only affected-key changes conflict; already-applied and unrelated edits succeed. | Pass: 21 tests covering unchanged, unrelated-edit, affected-row edit, affected-link metadata edit, already-applied, mixed, entry-only, missing-row, compound-key, and no-input-mutation cases. |
| `V-3` | Partial-save service and authorized route cases in `backend/tests/services/project/test_entity_operations_boundary.py`, `backend/tests/services/test_entity_values_service.py`, `backend/tests/api/v1/test_entities.py` | `rtk uv run pytest backend/tests/services/project/test_entity_operations_boundary.py backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py -q` | `PH3-AC-1` | Both persisted-row/failed-sidecar paths return HTTP 200 pending; pre-write and row-write errors retain existing behavior. | Pass: added boundary, external-service, and API cases; both routes return the pending shape with preserved ordinary fields, and pre-write/row-write failures keep their existing behavior. |
| `V-4` | Retry service and authorized route cases in `backend/tests/services/test_fixed_entity_mapping_retry_service.py` **NEW** and `backend/tests/api/v1/test_mapping.py` | `rtk uv run pytest backend/tests/services/test_fixed_entity_mapping_retry_service.py backend/tests/api/v1/test_mapping.py -q` | `PH3-AC-2`, `PH3-AC-3` | Unrelated edits pass; changed keys produce 409; no-op is byte-identical; malformed/unauthorized requests fail. | Pass: 9 retry-service tests and the new route cases verify apply, no-op, unrelated edits, 409 changed keys, body/path mismatch, malformed payload, non-fixed entity, and unauthenticated access. |
| `V-5` | Client API/store tests in `frontend/src/api/__tests__/entities.test.ts` and `frontend/src/stores/__tests__/entity.test.ts` | From `frontend/`: `pnpm exec vitest run src/api/__tests__/entities.test.ts src/stores/__tests__/entity.test.ts` | `PH3-AC-3` | Typed retry call sends unchanged payload; pending state survives refresh and clears at the right time. | Pass: 51 tests across the two files, including the retry call signature, inline/external pending retention, unrelated refresh, and clear-on-retry. |
| `V-6` | Editor recovery tests in `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | From `frontend/`: `pnpm exec vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH3-AC-1`, `PH3-AC-3` | Both buttons and save paths show partial status, call Retry once, avoid a second row save, and display conflict keys. | Pass: 28 tests, including partial-save notice, single retry without a second row save, conflict keys, and Save & Close staying open. |
| `V-7` | User guidance | Read `docs/USER_GUIDE.md` fixed-entity and mapping sections; compare each stated action and message with `EntityFormDialog.vue` and the API route. | `PH3-AC-3` | The guide names retry and review steps exactly as implemented. | Pass: added a **Partial Saves and Mapping Retry** section and the retry endpoint row; wording matches the *Rows saved; mapping changes pending*, **Retry mapping**, and changed-keys messages. |
| `V-8` | Regression and quality checks | Commands below | All criteria and preserved behavior | Existing successful saves, mapping CRUD, formats, ETags, and type/format checks pass. | Pass with one pre-existing failure: backend `2128` tests (`1` pre-existing `arbodat` failure, `19` skipped), core `1843` tests, frontend `726` tests, `vue-tsc` clean, ESLint clean, Ruff/Black/isort clean. |

Planning baseline on commit `8ff9532e`:

```text
rtk uv run pytest backend/tests/services/test_fixed_entity_mapping_sync_service.py backend/tests/api/v1/test_entities.py backend/tests/api/v1/test_mapping.py -q
    Pass.
cd frontend && pnpm exec vitest run src/api/__tests__/entities.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts
    Pass: 39 tests across two files.
rtk uv run pytest backend/tests/services/project/test_entity_operations_boundary.py backend/tests/services/test_entity_values_service.py -q
    Pass.
cd frontend && pnpm exec vitest run src/stores/__tests__/entity.test.ts
    Pass: 27 tests.
cd frontend && pnpm exec vue-tsc --noEmit
    Pass.
```

After implementation, run these regression and quality commands:
```bash
rtk uv run pytest tests/reconciliation/test_fixed_entity_mapping_changes.py tests/reconciliation/test_fixed_entity_mapping_retry.py backend/tests/models/test_mapping_sync.py backend/tests/services/test_fixed_entity_mapping_sync_service.py backend/tests/services/test_fixed_entity_mapping_retry_service.py backend/tests/services/project/test_entity_operations_boundary.py backend/tests/services/project/test_entity_operations_optimistic_locking.py backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py backend/tests/api/v1/test_mapping.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/mappers/test_project_mapper_file_path_integration.py -q
phase3_python_files=(
  src/reconciliation/fixed_entity_mapping_changes.py
  src/reconciliation/fixed_entity_mapping_retry.py
  backend/app/models/mapping_sync.py
  backend/app/mappers/project_mapper.py
  backend/app/services/fixed_entity_mapping_sync_service.py
  backend/app/services/fixed_entity_mapping_retry_service.py
  backend/app/services/project/entity_operations.py
  backend/app/services/project_service.py
  backend/app/services/entity_values_service.py
  backend/app/api/v1/endpoints/entities.py
  backend/app/api/v1/endpoints/mapping.py
  tests/reconciliation/test_fixed_entity_mapping_retry.py
  backend/tests/models/test_mapping_sync.py
  backend/tests/services/test_fixed_entity_mapping_retry_service.py
  backend/tests/services/project/test_entity_operations_boundary.py
  backend/tests/services/test_entity_values_service.py
  backend/tests/api/v1/test_entities.py
  backend/tests/api/v1/test_mapping.py
)
rtk uv run ruff check "${phase3_python_files[@]}"
rtk uv run black --check "${phase3_python_files[@]}"
rtk uv run isort --check-only "${phase3_python_files[@]}"
cd frontend
pnpm exec vitest run src/api/__tests__/entities.test.ts src/stores/__tests__/entity.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts
pnpm exec vue-tsc --noEmit
pnpm exec eslint src/api/entities.ts src/stores/entity.ts src/components/entities/EntityFormDialog.vue src/api/__tests__/entities.test.ts src/stores/__tests__/entity.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts
```

After code changes, run `.venv/bin/graphify update .` and inspect generated changes, as the repository guide requires. If verified source or tests conflict with this plan during implementation, stop and report the conflict before changing the design or scope.

**Validation results:** Every command above was run. The focused backend group passed, the frontend files passed, `vue-tsc`, ESLint, Ruff, Black, and isort reported no issues, and `.venv/bin/graphify update .` refreshed `graph.json`, `GRAPH_REPORT.md`, and the call-flow HTML (the HTML visualization was skipped because the graph exceeds its node limit). The full backend suite is `2128` tests with one pre-existing failure in `backend/tests/data_providers/arbodat/test_validation.py::test_data_validation_orchestrator`; that test also fails with this plan's changes stashed, so it is unrelated to Phase 3. An additional repository check, `backend/tests/authorization/test_route_authentication.py::test_route_inventory_matches_assembled_api_routes`, initially failed for the new route and now passes after `docs/AUTHORIZATION_ROUTE_INVENTORY.md` was updated.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Pending API models **NEW** | `backend/app/models/mapping_sync.py` | `T3.1`, `T3.6` | `V-1`, `V-4` pass. |
| API/Core conversion and payload tests | `backend/app/mappers/project_mapper.py`; `backend/tests/models/test_mapping_sync.py` **NEW** | `T3.1`, `T3.5` | JSON round-trip and validation in `V-1`. |
| Pure retry checks **NEW** | `src/reconciliation/fixed_entity_mapping_retry.py`; `tests/reconciliation/test_fixed_entity_mapping_retry.py` **NEW** | `T3.2`, `T3.5` | Affected-key matrix in `V-2`. |
| Shared row-index rule | `src/reconciliation/fixed_entity_mapping_changes.py` | `T3.2` | Retry uses the same encoded keys and missing rule; `V-2` passes. |
| Inline pending response | `backend/app/services/fixed_entity_mapping_sync_service.py`; `backend/app/services/project/entity_operations.py`; `backend/app/services/project_service.py`; `backend/app/api/v1/endpoints/entities.py`; `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/api/v1/test_entities.py` | `T3.3` | `V-3` verifies row persistence and HTTP 200 pending. |
| External pending response | `backend/app/services/entity_values_service.py`; `backend/app/api/v1/endpoints/entities.py`; `backend/tests/services/test_entity_values_service.py`; `backend/tests/api/v1/test_entities.py` | `T3.4` | `V-3` verifies file persistence, ETag, and matching pending shape. |
| Retry service and route | `backend/app/services/fixed_entity_mapping_retry_service.py` **NEW**; `backend/app/api/v1/endpoints/mapping.py`; `backend/tests/services/test_fixed_entity_mapping_retry_service.py` **NEW**; `backend/tests/api/v1/test_mapping.py` | `T3.5`, `T3.6` | `V-4` verifies safe apply, no-op, 409, and authorization. |
| Client API, state, and editor | `frontend/src/api/entities.ts`; `frontend/src/stores/entity.ts`; `frontend/src/components/entities/EntityFormDialog.vue`; their existing matching test files | `T3.7`, `T3.8` | `V-5`, `V-6`, type check, and ESLint pass. |
| User recovery guidance | `docs/USER_GUIDE.md` | `T3.8` | `V-7` confirms the documented steps. |
| Authorization route inventory | `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T3.6` | `V-4`, `V-8`; the route-authentication inventory test passes. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Payload and checks | Done | Phase 2 output | `T3.1`–`T3.2`; `V-1`, `V-2` passed. |
| Area 2: Pending saves | Done | Area 1 | `T3.3`–`T3.4`; `VM-5` met; `V-3` passed. |
| Area 3: Retry operation | Done | Areas 1–2 | `T3.5`–`T3.6`; backend part of `VM-6`; `V-4` passed. |
| Area 4: Client recovery | Done | Areas 2–3 | `T3.7`–`T3.8`; client part of `VM-6`; `V-5`–`V-7` passed. |

## Definition Of Done

- [x] `PH3-AC-1`–`PH3-AC-3` each have implementation and passing validation results; `VM-5` and `VM-6` are met.
- [x] All work areas and deliverables are complete; the same pending model is returned from both save paths.
- [x] `V-1`–`V-8` pass, including negative, affected-key conflict, already-applied, authorization, and client recovery cases.
- [x] Existing ETag rejection, successful saves, no-op byte preservation, sidecar metadata, CSV/parquet handling, and sidecar-first normalization remain covered by regression tests.
- [x] The protected route, client types, user guidance, the authorization route inventory (`docs/AUTHORIZATION_ROUTE_INVENTORY.md`), and the generated graph are synchronized; deviations and follow-up work are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

- The external values ETag hashes mtime and size, so a matching version cannot by itself prove row identity. The affected-key saved-row check is authoritative, including on a repeated retry.
- `ProjectService._get_lock` is process-local and non-reentrant. Retry must not call another method that acquires it, and this phase must not claim coordination across independent backend processes.
- A sidecar write may fail after replacement has succeeded. The retry's already-applied check must accept that state without rewriting link timestamps or metadata.
