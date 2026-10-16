# Sync Mapping Links After Fixed Entity Saves — Phase 4 Task Plan

## Phase Summary

**Goal:** Make the administrative materialized rebuild additive by default, retain full manual-link replacement behind an explicit request option, and validate the complete fixed-entity mapping flow.

**Readiness:** Validated. [Phase 4](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md#phase-4-make-the-materialized-rebuild-additive) is marked ready after Phases 1–3. Their [Phase 1](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_1_TASK_PLAN.md), [Phase 2](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_2_TASK_PLAN.md), and [Phase 3](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_3_TASK_PLAN.md) task plans record `VM-1`–`VM-6` as complete, and the relevant code and focused tests are present and pass on the repository basis below.

**Sources:** [Proposal](./MATERIALIZED_ENTITY_MAPPING_SYNC.md) and [phase plan](./MATERIALIZED_ENTITY_MAPPING_SYNC_PHASE_PLAN.md). This phase implements `P-AC-5` and `P-AC-9`, completes `VM-7`, and checks `P-AC-1`–`P-AC-9` together for `VM-8`.

**Constraints:** Keep the one-link-per-key sidecar format, sidecar-first normalization, ordered `TableConfig.safe_keys` defaults, stored mapping columns for existing entries, shared per-project lock, disk-read content version, and atomic sidecar save. Administrative rebuild reads all currently saved materialized rows; the Phase 3 retry route applies the supplied pending changes and must remain separate. Do not change mapping configuration or normalization precedence.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `P-AC-9`): A bodyless rebuild creates a missing entry and adds manual links only at absent keys with non-blank saved IDs, preserving all existing links. Full manual-link replacement occurs only with `replace_manual_links: true`.
2. [x] `PH4-AC-2` (from `P-AC-5`, `P-AC-9`): Rebuild entry creation uses the shared ordered `safe_keys` default, and rebuild stays separate from retry's exact pending change set.

## Repository Findings

**Repository basis:** Branch `materialized-entity-mapping-sync`, commit `5a38bfed`, planning date 2026-10-16. Source, tests, and active documentation were inspected. The untracked `docs/TEST_DEPLOYMENT_REFRESH.md` was present before planning and was not used or changed. Graphify was used for navigation; the findings below were verified in the files.

| Source | Verified behavior | Planning implication |
|---|---|---|
| `backend/app/services/materialization_service.py::MaterializationService.sync_materialized_entity_mappings`, `_sync_materialized_entity_mappings_locked` | The public method holds `ProjectService._get_lock`; the locked method reads a fresh `MappingManager.load_snapshot`, ensures an entry, replaces manual links, and saves with `expected_version`. | Retain the lock/version/save sequence. Add an additive default and keep `replace_entity_manual_links` only for an explicit replacement request. Do not save an unchanged existing catalog. |
| `backend/app/services/materialization_service.py::_default_mapping_local_key`, `_ensure_mapping_entity`, `_extract_manual_links_from_rows` | Entry creation already calls shared `default_local_key(table.safe_keys)`. Existing entries supply their stored `local_key`. Extraction checks `pd.isna`, so empty and whitespace-only IDs are not skipped; it builds a new link for every non-null row. | Preserve ordered entry creation and stored columns. Use the Phase 1 missing-ID and key-validation rules before deciding which links to add or replace. |
| `src/reconciliation/fixed_entity_mapping_changes.py::default_local_key`, `build_row_index`; `src/types/fixed_entity_types.py::is_missing_fixed_entity_value` | The shared helper preserves compound-key order; the row index rejects missing columns, unusable or duplicate encoded keys; the missing rule includes `None`, `NaN`, empty, and whitespace-only values but not zero. | Reuse these rules for rebuild input; reject bad saved rows before sidecar mutation. Existing entry columns remain authoritative. |
| `src/reconciliation/mapping_manager.py::MappingManager.load_snapshot`, `save`, `replace_entity_manual_links` | Snapshots hash exact disk bytes. Save uses expected content version, atomic replacement, and cache refresh. Replacement removes old manual links, preserves non-manual links at other keys, and may overwrite a non-manual link at a generated key. | Keep explicit replacement behavior and one-link-per-key precedence; additive mode must skip every occupied key, regardless of source or saved target. |
| `backend/app/api/v1/endpoints/materialization.py::sync_mapping_from_materialized`; `backend/app/models/materialization.py::MaterializedMappingSyncResult` | The protected PATCH route has no request body and returns `manual_links_replaced`. It passes only the authorized project locator and entity name to the service. | Add an optional request model with default `replace_manual_links: false`. Keep bodyless calls valid, preserve the existing response field, and report additive insertions separately. No new route registration is needed. |
| `backend/app/api/v1/endpoints/mapping.py` and `backend/app/services/fixed_entity_mapping_retry_service.py` | The separate protected `retry-fixed-entity` route accepts the pending result and checks affected keys. | Do not call retry from rebuild or recompute retry changes from all saved rows. |
| `backend/tests/services/test_materialization_service.py::TestSyncMaterializedEntityMappings`; `backend/tests/api/v1/test_entities.py::test_patch_from_materialized_replaces_manual_mapping_links` | Both current checks expect a bodyless full replacement. API tests create the project via `POST /api/v1/projects` and then write materialized and sidecar files. | Change these expectations to explicit replacement; add additive, preservation, missing-entry, compound-key, invalid-row, and authorization cases at the same test levels. |
| `docs/USER_GUIDE.md::Materialized Entity Edits`; `docs/DESIGN.md::Mapping Sidecar Design` | Both still say ordinary materialized saves replace all manual links. | Update active guidance to describe affected-key ordinary saves and the administrative rebuild's two modes. Historical proposal files remain historical. |

## Scope

**In scope:** Materialized rebuild service behavior, optional PATCH request and accurate result counts, focused service and authorized route tests, active user and design documentation, and grouped regression checks for both save paths, retry, mapping writes, and normalization.

**Out of scope:** Changes to ordinary fixed-row comparison, pending/retry contracts, frontend behavior, sidecar schema, mapping configuration migration, non-fixed synchronization, reconciliation export semantics, and archived proposals.

**Affected components:** Backend materialization service, API model and route, backend tests, existing Core comparison and normalization tests, frontend recovery tests as regression checks, and active documentation. No new files are required beyond this task plan.

## Work Breakdown

### Area 1: Apply saved rows in the requested rebuild mode

**Objective:** A bodyless service call seeds only absent links, while an explicit call performs the existing full manual-link rebuild.

**Affected code:** `backend/app/services/materialization_service.py::MaterializationService._extract_manual_links_from_rows`, `sync_materialized_entity_mappings`, `_sync_materialized_entity_mappings_locked`, `_ensure_mapping_entity`; `src/reconciliation/fixed_entity_mapping_changes.py::build_row_index` as an existing helper, not a planned edit.

**Dependencies:** Phase 1 ordered keys and missing-value rules; Phase 2 project lock and versioned sidecar save.

**Tasks**

- [x] `T4.1` **Validate:** Build candidate manual links from currently saved rows using the shared fixed-row rules.
  - **Target:** `backend/app/services/materialization_service.py::_extract_manual_links_from_rows` and its call in `_sync_materialized_entity_mappings_locked`.
  - **Current → required:** Extraction skips only `pd.isna` and can silently overwrite duplicate encoded keys → it skips all IDs accepted by `is_missing_fixed_entity_value`, accepts zero, and rejects missing columns, unusable or duplicate keys, and invalid non-blank integer targets before sidecar mutation.
  - **Implementation:** Use the existing entry's `local_key` and `public_id` when present; use `_ensure_mapping_entity`'s ordered `safe_keys` default for a new entry. Reuse `build_row_index` for encoded-key validation and the fixed-entity ID validator before constructing links. Convert validation errors into the service's current unsuccessful result so the route keeps its current 400 error path. Read inline or `@load:` rows through `_load_saved_materialized_rows`; never compare them with a previous snapshot.
  - **Constraints:** Keep `ProjectMapper.to_core` for API-to-Core conversion and preserve the sidecar's one-link-per-key representation. Do not change the Phase 1 save-time comparison.
  - **Validation:** `V-1` in `backend/tests/services/test_materialization_service.py`: `None`, `NaN`, `""`, whitespace, and zero; missing/duplicate key, absent column, and invalid ID; assert no save on invalid rows.

- [x] `T4.2` **Implement:** Make additive seeding the default and retain explicit replacement.
  - **Target:** `backend/app/services/materialization_service.py::MaterializationService.sync_materialized_entity_mappings`, `_sync_materialized_entity_mappings_locked`.
  - **Current → required:** Every eligible call invokes `MappingManager.replace_entity_manual_links` → default calls add candidates only where the encoded key is absent; only `replace_manual_links=True` invokes full manual-link replacement.
  - **Implementation:** Thread a `replace_manual_links: bool = False` option through both service methods. For default calls, leave all occupied keys untouched, including manual, reconciliation, and import links with blank, older, or different saved IDs. Save only when a link was added or a missing entry was created; a repeated additive call with no changes leaves sidecar bytes and link metadata unchanged. For explicit replacement, retain the current removal of stale manual links, preservation of non-manual links at other keys, and generated manual links overwriting any source at their keys. Save under the existing lock with the snapshot's `expected_version`.
  - **Constraints:** Do not invoke `compute_fixed_row_change_set`, `FixedEntityMappingRetryService`, or the pending retry route. Keep non-materialized rejection on the administrative route.
  - **Validation:** `V-1` and `V-2`: missing entry, additive no-op, occupied-key preservation, explicit replacement, ordered compound keys, and one-link-per-key behavior.

**Completion evidence:** `V-1` passes; additive calls preserve exact existing link data and repeated no-op calls do not write, while explicit replacement retains the former full-rebuild result.

### Area 2: Expose the explicit option without breaking bodyless requests

**Objective:** The existing protected PATCH route accepts an optional replacement request and returns counts that identify what happened.

**Affected code:** `backend/app/models/materialization.py::MaterializedMappingSyncResult`; `backend/app/api/v1/endpoints/materialization.py::sync_mapping_from_materialized`.

**Dependencies:** Area 1.

**Tasks**

- [x] `T4.3` **Update:** Add and pass the rebuild request option and distinguish added from replaced links in the response.
  - **Target:** `backend/app/models/materialization.py` (`MaterializedMappingSyncRequest` **NEW class** in the existing file, `MaterializedMappingSyncResult`); `backend/app/api/v1/endpoints/materialization.py::sync_mapping_from_materialized`.
  - **Current → required:** The route has no body and always requests replacement → a missing body or `{}` requests additive seeding; `{"replace_manual_links": true}` requests full replacement; malformed bodies get FastAPI/Pydantic validation errors.
  - **Implementation:** Define the request with `replace_manual_links: bool = False` and make the route body optional. Pass the value to the service. Add `manual_links_added: int = 0` to the response for additive insertions; retain `manual_links_replaced` for the explicit replacement mode (the existing count of manual links after replacement), returning zero for it in additive mode. Keep `success`, `entity_name`, and existing error handling.
  - **Constraints:** Keep `require_project(Action.EDIT)` and the current URL; do not route through `retry-fixed-entity`. Do not change the authorized project locator behavior.
  - **Validation:** `V-2` in `backend/tests/api/v1/test_entities.py`: bodyless, `{}`, `false`, `true`, malformed body, non-materialized entity, and unauthenticated request; assert response counts and saved sidecar data.

**Completion evidence:** `V-2` passes; bodyless clients can seed links, and full replacement requires an explicit true option.

### Area 3: Lock in behavior and update active guidance

**Objective:** Existing save, retry, normalization, and administrative flows all satisfy the proposal together, and active documentation describes the shipped behavior.

**Affected code and documents:** `backend/tests/services/test_materialization_service.py`; `backend/tests/api/v1/test_entities.py`; `docs/USER_GUIDE.md`; `docs/DESIGN.md`. Existing tests named in `V-3` and `V-4` are regression targets, not planned edits unless a real failure exposes a Phase 4 defect.

**Dependencies:** Areas 1–2.

**Tasks**

- [x] `T4.4` **Test:** Replace the old bodyless-replacement expectations and add the administrative test matrix.
  - **Target:** `backend/tests/services/test_materialization_service.py::TestSyncMaterializedEntityMappings`; `backend/tests/api/v1/test_entities.py::test_patch_from_materialized_replaces_manual_mapping_links` and adjacent materialized-route tests.
  - **Current → required:** Existing checks assert bodyless replacement → they assert additive preservation; the former replacement assertions run with `replace_manual_links: true`.
  - **Implementation:** Use small inline rows and sidecar entries for the service cases. For route cases, create the project with `POST /api/v1/projects`, then place inline or parquet rows and sidecar data. Check absent key insertions, existing manual/reconciliation/import links retaining their full serialized metadata and targets, blank/older saved IDs, zero ID, a missing entry with ordered compound keys, repeated bodyless no-op with identical bytes, explicit removal of old manual links and replacement at occupied keys, malformed request and invalid saved-row 400/422 paths, and unauthorized access.
  - **Validation:** `V-1`, `V-2`, `V-3`; assert exact keys, sources, targets, metadata, count fields, and sidecar bytes where no write is expected.

- [x] `T4.5` **Document:** Correct the active descriptions of ordinary saves and administrative rebuilds.
  - **Target:** `docs/USER_GUIDE.md::Materialized Entity Edits`, `Mapping Sidecar Management`; `docs/DESIGN.md::Mapping Sidecar Design` write paths.
  - **Current → required:** Active docs say a materialized save replaces every manual link → they describe affected-key ordinary save sync, bodyless additive administrative seeding, and explicit `replace_manual_links: true` replacement. The user guide must also distinguish rebuild from pending-result retry.
  - **Implementation:** Keep the endpoint names exact. State that an existing link is preserved by additive rebuild even if saved rows contain an older or blank ID, and that explicit replacement may remove stale manual links or overwrite a link at a generated key. Keep the existing partial-save instructions consistent with the Phase 3 client.
  - **Validation:** `V-5`: manually compare both sections with the service, route, request model, and test results; check relative document links.

- [x] `T4.6` **Validate:** Run grouped checks for `P-AC-1`–`P-AC-9` and stop if prior-phase behavior changes.
  - **Target:** Test files and commands in `V-3`, `V-4`, and `V-6`.
  - **Current → required:** Phases 1–3 pass the planning baseline; Phase 4 must preserve those results while adding administrative coverage.
  - **Implementation:** Run the grouped Python and frontend checks after implementation, then Ruff, Black, and isort checks on changed Python files. Run `.venv/bin/graphify update .` after code changes as required by the repository guide. If verified source or tests conflict with this plan, stop and report the conflict rather than redesigning or broadening the phase.
  - **Validation:** `V-3`, `V-4`, `V-6`.

**Completion evidence:** `VM-7` is met by `V-1`–`V-2`; `VM-8` is met by `V-3`–`V-6`, with the `P-AC-1`–`P-AC-9` checks below passing and active documentation matching the implementation.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
|---|---|---|---|
| `PH4-AC-1` (`P-AC-9`) | `T4.1`, `T4.2`, `T4.3`, `T4.4`, `T4.5` | `V-1`, `V-2`, `V-3`, `V-5` | Bodyless seeding changes only absent keys; explicit true retains full replacement; response and guidance distinguish the modes. |
| `PH4-AC-2` (`P-AC-5`, `P-AC-9`) | `T4.1`, `T4.2`, `T4.4`, `T4.6` | `V-1`, `V-2`, `V-3` | New entries encode compound keys in declared order; existing entries retain stored columns; rebuild and retry remain distinct. |

**`VM-8` proposal coverage:** `P-AC-1`, `P-AC-2`, and `P-AC-6` use the inline/external save cases in `backend/tests/api/v1/test_entities.py`, `backend/tests/services/test_entity_values_service.py`, and `backend/tests/services/project/test_entity_operations_boundary.py`; `P-AC-3` and `P-AC-4` use `tests/reconciliation/test_fixed_entity_mapping_changes.py` and the save-route cases. `P-AC-5` uses the ordered-key cases in the Core change tests, service tests, and new rebuild cases. `P-AC-7` uses `tests/reconciliation/test_mapping_sidecar.py`, `backend/tests/services/test_mapping_write_coordination.py`, and retry checks. `P-AC-8` uses backend pending/retry and frontend recovery cases. `P-AC-9` uses the new `V-1`–`V-2` cases. `tests/process/test_shapeshifter.py` checks sidecar-first normalization across the change.

## Validation And Testing

Use `authorized_client` for protected route cases and register test projects through the project API. `V-1`–`V-2` complete `VM-7`; `V-3`–`V-6` complete `VM-8`.

| ID | Check and target | Command or method | Covers | Expected result | Planning baseline |
|---|---|---|---|---|---|
| `V-1` | Service behavior in `backend/tests/services/test_materialization_service.py::TestSyncMaterializedEntityMappings` | `rtk uv run pytest backend/tests/services/test_materialization_service.py -q` | `PH4-AC-1`, `PH4-AC-2`, `P-AC-9` | Additive/no-op, explicit replacement, blank/zero/invalid IDs, ordered/duplicate keys, and no-write failures pass. | Pass: existing file passes; new Phase 4 cases not run because they are not written. |
| `V-2` | Protected PATCH contract in `backend/tests/api/v1/test_entities.py` | `rtk uv run pytest backend/tests/api/v1/test_entities.py -q` | `PH4-AC-1`, `PH4-AC-2`, `P-AC-9` | Bodyless and false are additive; true replaces; counts, invalid input, materialization guard, and authorization are correct. | Pass: existing file passes with old bodyless-replacement assertion; new contract cases not run because they are not written. |
| `V-3` | Grouped Core/backend regression, including both save paths, retry, mapping writers, rebuild, and normalization | Command below | `P-AC-1`–`P-AC-9`; `PH4-AC-1`, `PH4-AC-2` | All cases pass, including new administrative cases and preservation of prior-phase behavior. | Pass: exact command below passed on `5a38bfed` before Phase 4 edits; current tests still expect bodyless replacement. |
| `V-4` | Client pending/retry regression in three existing Vitest files | From `frontend/`: `pnpm exec vitest run src/api/__tests__/entities.test.ts src/stores/__tests__/entity.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts` | `P-AC-8`; `VM-8` | Existing retry and partial-save behavior remains intact. | Pass: 3 files, 79 tests. |
| `V-5` | Active user/design guidance | Read `docs/USER_GUIDE.md` sections **Materialized Entity Edits** and **Mapping Sidecar Management**, and `docs/DESIGN.md` section **Mapping Sidecar Design**; compare claims with `MaterializationService`, `sync_mapping_from_materialized`, request model, and `V-1`–`V-2`. | `PH4-AC-1`; `VM-8` | Ordinary save, rebuild modes, and retry are described accurately. | Fail: both documents currently say ordinary materialized saves replace all manual links. |
| `V-6` | Python quality and repository graph | Commands below; inspect resulting graph changes | All changed Python files; `VM-8` | Ruff, Black, and isort pass; graph reflects code changes. | Not run: Phase 4 code has not been edited. |

`V-3` command from the repository root:

```bash
rtk uv run pytest tests/reconciliation/test_fixed_entity_mapping_changes.py tests/reconciliation/test_fixed_entity_mapping_retry.py tests/reconciliation/test_mapping_sidecar.py tests/process/test_shapeshifter.py backend/tests/services/test_materialization_service.py backend/tests/services/test_fixed_entity_mapping_sync_service.py backend/tests/services/test_fixed_entity_mapping_retry_service.py backend/tests/services/test_mapping_write_coordination.py backend/tests/services/test_entity_values_service.py backend/tests/services/project/test_entity_operations_boundary.py backend/tests/api/v1/test_entities.py backend/tests/api/v1/test_mapping.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/mappers/test_project_mapper_file_path_integration.py -q
```

`V-6` commands from the repository root after code changes:

```bash
rtk uv run ruff check backend/app/services/materialization_service.py backend/app/models/materialization.py backend/app/api/v1/endpoints/materialization.py backend/tests/services/test_materialization_service.py backend/tests/api/v1/test_entities.py
rtk uv run black --check backend/app/services/materialization_service.py backend/app/models/materialization.py backend/app/api/v1/endpoints/materialization.py backend/tests/services/test_materialization_service.py backend/tests/api/v1/test_entities.py
rtk uv run isort --check-only backend/app/services/materialization_service.py backend/app/models/materialization.py backend/app/api/v1/endpoints/materialization.py backend/tests/services/test_materialization_service.py backend/tests/api/v1/test_entities.py
.venv/bin/graphify update .
```

**Execution results (2026-10-16):**

- `V-1`: Pass in the grouped run; `backend/tests/services/test_materialization_service.py` covers additive preservation, no-write repeat, explicit replacement, missing values, zero, invalid IDs, duplicate/missing keys, and ordered compound keys.
- `V-2`: Pass in the grouped run; `backend/tests/api/v1/test_entities.py` covers bodyless, empty, false, and true requests, response counts, malformed input, duplicate saved keys, materialization guard, and authentication.
- `V-3`: Pass: the exact grouped Core/backend command above completed successfully after the Phase 4 changes.
- `V-4`: Pass: 3 Vitest files and 79 tests passed.
- `V-5`: Pass: the updated guide and design text matches the route and service. The repository-wide `rtk make check-doc-links` command reports an unrelated broken link in unchanged `docs/SPEC_DRIVEN_PROCESS.md` (`../docs/development/specification-driven-development.md`); the Phase 4 documentation adds no relative document links.
- `V-6`: Pass: Ruff, Black, and isort checks passed. `.venv/bin/graphify update .` refreshed `graph.json`, `GRAPH_REPORT.md`, `.graphify_labels.json`, and the call-flow HTML. Graphify skipped the standalone graph HTML because the graph has 21,537 nodes, above its 5,000-node limit.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Validated saved-row extraction and two rebuild modes | `backend/app/services/materialization_service.py` | `T4.1`, `T4.2` | `V-1` shows additive preservation, no-op, ordered keys, and explicit replacement. |
| Optional request and mode-specific counts | `backend/app/models/materialization.py`; `backend/app/api/v1/endpoints/materialization.py` | `T4.3` | `V-2` proves bodyless compatibility, explicit opt-in, validation, and authorization. |
| Administrative service and route cases | `backend/tests/services/test_materialization_service.py`; `backend/tests/api/v1/test_entities.py` | `T4.4` | `V-1`–`V-3` pass. |
| Current user and design guidance | `docs/USER_GUIDE.md`; `docs/DESIGN.md` | `T4.5` | `V-5` passes. |
| Grouped validation and graph refresh | Existing test files in `V-3`–`V-4`; `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/.graphify_labels.json`, `graphify-out/sead_shape_shifter-callflow.html` | `T4.6` | `V-3`, `V-4`, `V-6` pass; generated changes are inspected. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Rebuild modes | Done | Phases 1–2 | `T4.1`–`T4.2`; `V-1` and grouped `V-3` pass. |
| Area 2: Request and response | Done | Area 1 | `T4.3`; `V-2` and grouped `V-3` pass. |
| Area 3: Tests and guidance | Done | Areas 1–2; Phase 3 | `T4.4`–`T4.6`; `V-3`–`V-6` pass with the documented repository-wide link-check issue. |

## Definition Of Done

- [x] `PH4-AC-1` and `PH4-AC-2` have passing task and validation results; `VM-7` is met.
- [x] `VM-8` checks `P-AC-1`–`P-AC-9` across both save paths, retry, rebuild, and sidecar-first normalization.
- [x] All work areas and deliverables are complete; `V-1`–`V-6` pass or any deviation is explained.
- [x] Bodyless/additive calls preserve existing links and metadata, and no-op calls leave sidecar bytes unchanged.
- [x] Explicit replacement retains the prior full manual-link behavior and remains separate from retry.
- [x] Active documentation and response counts match the implemented modes; quality checks and graph refresh are complete.
- [x] Any verified conflict with this plan is reported before implementation changes the design or scope.

## Risks And Open Questions

- Existing API consumers may read `manual_links_replaced` as an operation count. Preserve the field for explicit replacement, add `manual_links_added` for additive calls, and test both modes so the response is unambiguous. No external decision is needed.
- Historical proposals describe the prior replacement-only endpoint. Leave them as records of the earlier design; update only active documentation listed above.
