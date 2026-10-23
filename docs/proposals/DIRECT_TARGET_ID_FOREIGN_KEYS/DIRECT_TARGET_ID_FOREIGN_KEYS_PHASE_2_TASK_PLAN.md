# Direct Target-Id Foreign Keys — Phase 2 Task Plan

## Phase Summary

**Phase:** [Phase 2: Ingester validation and projection](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md#phase-2-ingester-validation-and-projection).
**Goal:** Validate direct integer target IDs and carry them unchanged into change-request packages made from normalized tables.
**Readiness:** Validated. Phase 2 is marked ready; the Phase 1 declaration and conformance work is recorded as complete in its [task plan](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_1_TASK_PLAN.md). The code targets and test commands below were verified.
**Sources:** [Proposal](DIRECT_TARGET_ID_FOREIGN_KEYS.md) and [phase plan](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md).
**Dependency:** Phase 1's `foreign_key_value_sources` declaration. `VM-2` covers this plan. Phase 3 owns saved-project map derivation, guidance, the disposable PostgreSQL run, and the representative pilot.

Phase 2 acceptance criteria:

1. [x] `PH2-AC-1` (from `P-AC-4`): A declared target ID reaches the packaged FK column unchanged and is never passed through a local `system_id` map.
2. [x] `PH2-AC-2` (from `P-AC-5`): `validate_tables()` and `ingest_tables()` reject malformed, nonexistent, or unverifiable packaged IDs with the source entity, column, and supplied value; a standalone caller can provide the map.
3. [x] `PH2-AC-3` (from `P-AC-6`): Selected inserts enforce `required`, `required_when`, and `nullable: false`; an explicit null update to a non-nullable FK fails, while an untouched FK update or excluded row needs no value.
4. [x] `PH2-AC-4` (from `P-AC-7`): Integer IDs are checked against the referenced target table without a local entity; a non-integer target public-ID database column fails direct-mode validation.
5. [x] `PH2-AC-5` (from `P-AC-10`): The manifest identifies direct-ID FKs, and supplied FK values create no artificial reconciliation or staging ID-map entries.
6. [x] `PH2-AC-6` (from `P-AC-8`): Omitted and explicit `system_id` sources keep their current package values and diagnostics.

## Repository Findings

**Repository basis:** Branch `direct-target-id-foreign-keys`, commit `74f30ead`, 2026-10-23. The working tree also contains changes in `backend/tests/authorization/test_state_snapshot.py` and `backend/tests/services/test_file_manager.py`; these were not used as a basis or modified. Graphify located the ingester and protocol; source and tests below establish the behavior.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `src/model.py::TableConfig.foreign_key_value_sources`, `backend/app/models/entity.py::Entity` | Phase 1 stores a per-entity map; an absent entry means `system_id`. | Read the same map from `IngesterConfig.extra` for standalone calls; do not infer mode from table presence. Saved-project extraction stays in Phase 3. |
| `ingesters/sead_change_request/input_resolution.py::resolve_inputs`, `preparation.py::ResolvedInputs` | Inputs resolve target model, submission context, assignments, and strategy before planning. No value-source map is carried. | Resolve and check the supplied map against direct target-model FKs, then carry it through preparation. Preserve the no-map path. |
| `ingesters/sead_change_request/ingester.py::validate_tables`, `ingest_tables`, `_ingest_resolved` | Both table methods use the shared preparation flow. `validate_tables()` does not run the optional ingestion collision check; `ingest_tables(validate_first=False)` still checks preparation preconditions. | Put the mandatory direct-ID check in shared preparation and fail ingestion even when `validate_first=False`. Keep domain failures in structured results. |
| `ingesters/sead_change_request/planning.py::plan_table`, `package_builder.py::build_change_request_package`, `build_staging_package`, `sql_builder.py::_update_assignment_columns` | Planned actions and resolved row states select inserts, updates, and excluded rows. An update writes only selected mutable fields that have `__existing` baselines. Inline staging has no update support. | Use these exact selections for direct-ID checks; an untouched FK on an update is not checked or required. Do not validate excluded rows. |
| `ingesters/sead_change_request/target_projection.py::project_target_ids`, `_project_conditional_foreign_key` | FK values are mapped through a referenced resolved table; unconditional required-FK checks currently inspect all rows, while conditional checks inspect selected inserts. | Bypass local mapping only for declared `public_id` FKs and apply direct-mode null rules to packaged rows without changing default diagnostics. |
| `ingesters/sead_change_request/staging_eligibility.py::collect_pending_deployment`, `package_builder.py::_collect_known_id_mappings`, `inline_staging_sql.py::_foreign_key_columns`, `_render_resolve_foreign_keys` | Staging treats every FK column as a local parent key and can mistake a numeric value for a pending local ID. | Keep direct columns out of pending-local-FK masks, staging ID-map entries, and local-FK SQL; load their validated target IDs as target columns. |
| `ingesters/sead_change_request/collision_checks.py::TargetCollisionChecker`, `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` | The injected read-only PostgreSQL adapter provides `target_id_exists()` and `row_exists()`, but no column-type lookup. Injection is optional when database config is absent. | Add a read-only type query to the adapter and require the checker only when packaged direct values need lookup. Report missing checker, query failure, missing column, or non-integer type as validation failure. |
| `ingesters/sead_change_request/contracts.py::ChangeRequestPackage`, `sql_builder.py::build_deploy_artifact`, `artifact_writer.py::write_artifact_bundle` | Package data reaches each deploy strategy; `metadata_artifact` becomes `manifest.json`. Staging `known_id_mappings` is its deployment-local map, while project reconciliation sidecars are managed outside this ingester. | Carry direct-FK metadata into the package and add it to the manifest for used FKs. Do not write supplied IDs to either map. |

## Scope

**In scope:** `IngesterConfig.extra` input resolution for standalone table callers; direct-ID row selection, integer normalization, null rules, read-only database type and existence checks, all three deploy strategies (`inline_insert`, `copy_csv`, `inline_staging`), manifest metadata, and focused/default-path tests.

**Out of scope:** Saved-project service and route handoff, API request changes, Core FK links, target-model schema changes, configuration and agent guides, a real PostgreSQL pilot, and non-integer or `via` FK support. Phase 3 handles saved-project and real database verification.

**Affected contracts:** `ResolvedInputs`, `PreparationResult`, `ChangeRequestPackage`, the injected checker, structured `ValidationResult`/`IngestionResult`, deploy artifacts, and `manifest.json`. No project mapping sidecar write is part of this flow.

## Work Breakdown

### Area 1: Carry the declaration and preserve direct FK values

**Objective:** A standalone table caller can select `public_id` for an eligible FK, and target projection keeps that column's supplied value without requiring a referenced source table.

**Affected code:** `ingesters/sead_change_request/input_resolution.py::resolve_inputs`; `preparation.py::ResolvedInputs`, `prepare_change_request`; `target_projection.py::project_target_ids`, `_project_conditional_foreign_key`; `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `test_sead_change_request_target_projection.py`.

**Dependencies:** Phase 1 declaration.

**Tasks:**

* [x] `T1.1` **Resolve the standalone value-source map.**
  * **Target:** `ingesters/sead_change_request/input_resolution.py::resolve_inputs` and `preparation.py::ResolvedInputs`.
  * **Current → required:** Only the target model is resolved → `extra["foreign_key_value_sources"]` carries a per-source-entity map into preparation; absence is empty/default.
  * **Implementation:** Check map shape and `system_id`/`public_id` values. For direct entries, verify the source and target entities, direct FK without `via`, target `public_id`, and `target_table` in the resolved target model. Use `InputResolutionError`-style failures; keep project/Core link checks in Phase 1. Pass an explicit copy of the checked map through `ResolvedInputs`.
  * **Constraints:** Do not derive the map from a saved project here, accept inference from a missing referenced table, or alter the protocol/config dataclass.
  * **Validation:** `V-1`: `test_sead_change_request_input_resolution.py` with `NEW` cases for valid/empty/explicit `system_id` and malformed or ineligible maps.
* [x] `T1.2` **Keep direct values out of local-ID projection.**
  * **Target:** `ingesters/sead_change_request/target_projection.py::project_target_ids`, `_project_conditional_foreign_key`; `preparation.py::prepare_change_request`.
  * **Current → required:** Every FK passes through a referenced resolved table → a declared direct FK retains its value and needs no such table; other FKs keep present behavior.
  * **Implementation:** Pass the checked map into projection. Branch before required/conditional local mapping for direct entries; leave unselected values alone so malformed excluded rows do not fail. Normalize only packaged direct values in Area 2. Keep source-row `system_id` values and target-model FK definitions unchanged.
  * **Validation:** `V-1`: `test_sead_change_request_target_projection.py` with `NEW` direct required/conditional cases, a source bundle lacking the referenced project table, and default diagnostic parity.

**Completion evidence:** The projector retains a supplied direct FK without a remote resolved table, while existing local-ID projection cases still pass.

### Area 2: Check packaged IDs against the target database

**Objective:** Both table methods reject invalid direct values before a package can be accepted, including when ingestion skips its optional validation pass.

**Affected code:** `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`; `ingesters/sead_change_request/preparation.py::PreparationResult`, `prepare_change_request`; `result_builders.py::build_validation_result`, `check_ingestion_preconditions`; `ingester.py::_ingest_resolved`; `ingesters/sead_change_request/direct_fk_validation.py` **NEW**; `backend/tests/ingesters/test_sead_change_request_runtime.py`, `test_sead_change_request_ingester.py`.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.1` **Add a read-only target public-ID type lookup.**
  * **Target:** `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`; `ingesters/sead_change_request/direct_fk_validation.py` **NEW** (checker protocol); `backend/tests/ingesters/test_sead_change_request_runtime.py`.
  * **Current → required:** The checker can test ID existence but cannot verify database column type → direct mode checks the real PostgreSQL public-ID column before querying values.
  * **Implementation:** Add a parameterized/read-only catalog query using the adapter's existing schema handling and safe identifier rules; accept PostgreSQL integer column types and report missing/non-integer columns. Reuse `target_id_exists()` for existence. Make an unavailable checker or failed query a validation error, not a fallback to `system_id`.
  * **Validation:** `V-2`: `NEW` mocked adapter cases for qualified/default schema, integer, text, missing column, and query error. The real database check remains `VM-3` in Phase 3.
* [x] `T2.2` **Validate exactly the values that will be written.**
  * **Target:** `ingesters/sead_change_request/direct_fk_validation.py` **NEW**; `package_builder.py::build_change_request_package`, `build_staging_package` (share row-selection rules as needed); `preparation.py::prepare_change_request`, `PreparationResult`.
  * **Current → required:** No target existence lookup runs during validation → selected direct-ID inserts and assigned update columns receive type, integer, null, and existence checks after final identity actions.
  * **Implementation:** Use insert states from the package builders (`PENDING_DEPLOYMENT_ID` only for staging), and `UPDATE_EXISTING_CANDIDATE` with the renderer's actual assignment rules. For inserts, fail missing values when FK `required`, its `required_when` applies, or the FK column has `nullable: false`. For updates, fail explicit null only when the non-nullable FK is assigned; preserve `required_when` insert timing. Parse integer values without truncation or accepting booleans, normalize checked values to integer payloads, and check each distinct non-null value against the target table/public-ID column. Skip lookup for excluded rows or when no direct value is packaged. Produce entity/column/value diagnostics for bad supplied values; name the entity and column for missing values.
  * **Constraints:** No database write, no local-ID remapping, no check of an absent referenced project table. Preserve the existing default-path required-FK diagnostics.
  * **Validation:** `V-3`: `NEW` `test_sead_change_request_ingester.py` cases for accepted ID, malformed/fractional/boolean value, absent row, unavailable checker, lookup exception, required/conditional/non-nullable insert, zero-insert bundle, explicit null update, untouched update, and excluded malformed row. Assert zero calls for rows outside the package.
* [x] `T2.3` **Return the direct check through both public table methods.**
  * **Target:** `ingesters/sead_change_request/result_builders.py::build_validation_result`, `check_ingestion_preconditions`; `ingester.py::_ingest_resolved`.
  * **Current → required:** Direct lookup errors cannot affect validation and `validate_first=False` can emit after preparation → both paths fail with structured diagnostics and no completed bundle.
  * **Implementation:** Add direct-check diagnostics to `PreparationResult`; include them in `ValidationResult.errors` and ingestion preconditions. Ensure any run folder reserved by failed ingestion is removed by the existing cleanup path, and no deploy artifact is written. Keep normal collision checks optional for default projects.
  * **Validation:** `V-3`: exercise `validate_tables()` and `ingest_tables()` with both `validate_first` values; assert error details and no emitted bundle on failure.

**Completion evidence:** An accepted direct ID passes both methods; every invalid/unverifiable packaged value fails before artifact acceptance, including ingestion with `validate_first=False`.

### Area 3: Render direct IDs and identify their source

**Objective:** Each deploy strategy writes validated target IDs unchanged, and the manifest lists only direct FKs used by the package.

**Affected code:** `ingesters/sead_change_request/contracts.py::ChangeRequestPackage`; `package_builder.py::build_change_request_package`, `build_staging_package`, `_collect_known_id_mappings`; `staging_eligibility.py::collect_pending_deployment`; `inline_staging_sql.py::_foreign_key_columns`, `_render_resolve_foreign_keys`; `sql_builder.py::build_deploy_artifact`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`, `test_sead_change_request_sql_builder.py`, `test_sead_change_request_ingester.py`.

**Dependencies:** Areas 1–2.

**Tasks:**

* [x] `T3.1` **Prevent staging from treating direct values as local IDs.**
  * **Target:** `ingesters/sead_change_request/contracts.py::ChangeRequestPackage`; `package_builder.py::build_staging_package`, `_collect_known_id_mappings`; `staging_eligibility.py::collect_pending_deployment`; `inline_staging_sql.py::_foreign_key_columns`, `_render_resolve_foreign_keys`.
  * **Current → required:** A direct value may match a pending local key, enter `known_id_mappings`, or be rewritten by staging SQL → direct columns remain target columns and never seed or use the deployment-local ID map.
  * **Implementation:** Carry the selected direct-FK set with the package; exclude those columns from pending-local-FK detection, known mappings, `_local_` FK staging columns, and FK-resolution statements. Keep them in staged loaded/inserted target columns. Leave ordinary staging relationships and insert ordering intact.
  * **Validation:** `V-4`: `NEW` package/SQL cases with a direct integer equal to a local parent key, no referenced project table, no artificial known mapping, direct value in staging `INSERT`, and unchanged ordinary local FK mapping.
* [x] `T3.2` **Record used direct FKs in the manifest.**
  * **Target:** `ingesters/sead_change_request/contracts.py::ChangeRequestPackage`; `package_builder.py::build_change_request_package`, `build_staging_package`; `sql_builder.py::build_deploy_artifact` (shared artifact metadata); `backend/tests/ingesters/test_sead_change_request_ingester.py`, `test_sead_change_request_sql_builder.py`.
  * **Current → required:** `manifest.json` has no FK value-source list → it identifies each source entity, target entity, and FK column that supplied a direct ID in packaged data.
  * **Implementation:** Derive a sorted list from the checked map for FKs with a non-null value in selected package rows; put it in `metadata_artifact` for all strategies, so `artifact_writer.py::write_artifact_bundle` persists it. Preserve existing manifest shape when no direct FK is used. Do not add a project reconciliation sidecar entry or a staging `KnownIdMapping` for supplied IDs.
  * **Validation:** `V-4`: `NEW` inline-insert, copy-CSV, and inline-staging cases assert payload ID and metadata; read emitted `manifest.json` and assert the list and absence of artificial mappings.

**Completion evidence:** All strategies retain the same validated direct value in target FK data, the manifest identifies its FK, and staging has no local map entry for it.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-4`) | `T1.2`, `T2.2`, `T3.1` | `V-1`, `V-3`, `V-4` | Supplied integer appears unchanged in direct, CSV, and staging target columns. |
| `PH2-AC-2` (`P-AC-5`) | `T1.1`, `T2.1`, `T2.2`, `T2.3` | `V-1`, `V-2`, `V-3` | Both table methods fail on bad, missing, or unverifiable supplied IDs with contextual errors. |
| `PH2-AC-3` (`P-AC-6`) | `T2.2`, `T2.3` | `V-3` | Only selected insert/update values receive the stated null rules. |
| `PH2-AC-4` (`P-AC-7`) | `T1.2`, `T2.1`, `T2.2` | `V-2`, `V-3` | Integer database column and existing ID pass without a local parent; text column fails. |
| `PH2-AC-5` (`P-AC-10`) | `T3.1`, `T3.2` | `V-4` | Manifest lists used direct FKs; supplied values create no map entry. |
| `PH2-AC-6` (`P-AC-8`) | `T1.1`, `T1.2`, `T2.3`, `T3.1`, `T3.2` | `V-1`, `V-3`, `V-4`, `V-5` | No-map and explicit `system_id` results and diagnostics match the baseline. |

## Validation And Testing

The `NEW` cases below belong in the named existing test files. Use explicit `IngesterConfig.extra` and fake collaborators for unit tests; no live database is required for `VM-2`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Map resolution and projection: `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `test_sead_change_request_target_projection.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_target_projection.py -q` | `PH2-AC-1`, `PH2-AC-2`, `PH2-AC-6` | New direct and invalid-map cases pass; existing local mapping/conditional diagnostics remain. | Pass: both existing files passed before planning changes. |
| `V-2` | PostgreSQL adapter type lookup: `backend/tests/ingesters/test_sead_change_request_runtime.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_runtime.py -q` | `PH2-AC-2`, `PH2-AC-4` | Mocked integer/text/missing/error and schema-selection cases pass. | Pass: runtime file passed in a focused three-file run; that run had three database-dependent skips. New type cases are not yet present. |
| `V-3` | Both table methods and row-action rules: `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH2-AC-1`–`PH2-AC-4`, `PH2-AC-6` | New accepted/failure/missing/zero-insert/update/excluded cases pass for validation, ingestion, and `validate_first=False`; no failed bundle remains. | Pass: existing file passed before planning changes. |
| `V-4` | Package, SQL strategies, manifest, staging map: `backend/tests/ingesters/test_sead_change_request_package_builder.py`, `test_sead_change_request_sql_builder.py`, `test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH2-AC-1`, `PH2-AC-5`, `PH2-AC-6` | New cases prove direct values and metadata for all strategies, no artificial map entry, and ordinary staging mapping parity. | Pass: all existing files passed before planning changes. |
| `V-5` | Ingester regression suite | `rtk uv run pytest backend/tests/ingesters -q` | `PH2-AC-6`, `VM-2` | Existing ingester tests pass; only tests requiring the optional disposable PostgreSQL environment may skip. | Pass: suite exited 0 before planning changes; database-dependent tests skipped. |
| `V-6` | Code quality and whitespace | `rtk make lint`; `git diff --check` | All changed files | Formatting, lint, and whitespace checks pass; document any unrelated pre-existing lint failure separately. | Not run: no implementation or test files were edited for this plan. |

## Execution Record

**Executed:** 2026-10-23. The focused checks and full ingester suite pass. Optional integration tests that require a disposable PostgreSQL database or SIMS service were skipped because those services were not configured.

| Validation | Result |
| --- | --- |
| `V-1` | Pass: map resolution, direct projection without a parent table, and explicit `system_id` projection parity. |
| `V-2` | Pass: mocked integer, text, missing-column, catalog-error, and qualified/default-schema cases. |
| `V-3` | Pass: both table methods cover accepted, malformed, absent, unavailable, required, conditional, nullable, update, untouched, zero-insert, and excluded-row cases; failed ingestion removes its reserved run folder. |
| `V-4` | Pass: package, SQL, and emitted manifest preserve direct values across inline insert, copy CSV, and inline staging; direct staging values create no local mapping, and ordinary local FK mapping remains. |
| `V-5` | Pass: `rtk uv run pytest backend/tests/ingesters -q`; optional database- and service-dependent tests skipped. |
| `V-6` | Pass: `rtk make lint` and `rtk git diff --check`. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Checked input map | `ingesters/sead_change_request/input_resolution.py::resolve_inputs`; `preparation.py::ResolvedInputs` | `T1.1` | Standalone map is validated and carried; omission retains default. |
| Direct projection | `ingesters/sead_change_request/target_projection.py::project_target_ids`, `_project_conditional_foreign_key`; `preparation.py::prepare_change_request` | `T1.2` | No remote resolved table needed for direct FK. |
| Target checker type method | `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` | `T2.1` | Integer type verified through read-only lookup. |
| Direct value validator **NEW** | `ingesters/sead_change_request/direct_fk_validation.py` | `T2.1`, `T2.2` | Packaged values checked against database with row-aware diagnostics. |
| Structured results | `ingesters/sead_change_request/preparation.py::PreparationResult`; `result_builders.py::build_validation_result`, `check_ingestion_preconditions`; `ingester.py::_ingest_resolved` | `T2.2`, `T2.3` | Both table methods fail closed. |
| Package and staging support | `ingesters/sead_change_request/contracts.py::ChangeRequestPackage`; `package_builder.py::build_change_request_package`, `build_staging_package`, `_collect_known_id_mappings`; `staging_eligibility.py::collect_pending_deployment`; `inline_staging_sql.py::_foreign_key_columns`, `_render_resolve_foreign_keys` | `T2.2`, `T3.1`, `T3.2` | Direct values bypass local mapping in all packages. |
| Manifest metadata | `ingesters/sead_change_request/sql_builder.py::build_deploy_artifact` | `T3.2` | Persisted manifest names used direct FKs. |
| Focused tests | `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `test_sead_change_request_target_projection.py`, `test_sead_change_request_runtime.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_package_builder.py`, `test_sead_change_request_sql_builder.py` | `T1.1`–`T3.2` | `V-1`–`V-4` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: declaration and projection | Done | Phase 1 | Map resolution and direct projection passed `V-1`. |
| Area 2: database validation | Done | Area 1 | Target lookup and both public table methods passed `V-2` and `V-3`. |
| Area 3: package and manifest | Done | Areas 1–2 | Three deploy strategies, staging maps, and manifest output passed `V-4`. |

## Definition Of Done

* [x] `PH2-AC-1`–`PH2-AC-6` each have passing task and validation results recorded in the coverage table.
* [x] All three areas and deliverables are complete; `V-1`–`V-6` pass or a pre-existing quality failure is isolated and recorded.
* [x] A packaged direct ID is typed, confirmed in the target table, and carried unchanged; malformed, missing, non-integer-column, and unavailable-lookup cases fail through both table methods.
* [x] Insert, update, zero-insert, and excluded-row cases enforce only their applicable direct-ID rules; `required_when` remains insert based.
* [x] Manifest, staging SQL, and staging map agree about which FKs used direct IDs; no reconciliation sidecar is written for them.
* [x] Omitted and explicit `system_id` modes retain the baseline package values and diagnostics; no Core FK behavior changed.
* [x] Any deviation or follow-up is recorded, and no unresolved question affects this phase's implementation or checks.

If implementation discovers that a verified file, row-selection rule, or package contract differs from this plan, stop and report the conflicting source and test result before changing the design or scope.
