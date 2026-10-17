# Deployment-Time Staging — Phase 2 Task Plan

## Phase Summary

**Phase:** 2 — Resolve IDs And FKs Through Inline Staging. **Readiness: Validated for implementation.** The [phase plan](./DEPLOYMENT_TIME_STAGING_PHASE_PLAN.md) requires Phase 1's reviewed child/root inventory and deployed target-ID contract. The [Phase 1 task plan](./DEPLOYMENT_TIME_STAGING_PHASE_1_TASK_PLAN.md) records its work areas, validation, and definition of done as complete; the [target-model review](../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) records the generator, schema, and lock results. Its summary acceptance checkboxes remain unchecked, but the completed work and test results provide the required handoff.

**Goal:** Prove an explicitly selected inline staging artifact that preserves local row IDs and FKs, carries known reference mappings, allocates supported child IDs during deployment, checks complete `unique_sets`, and writes target rows in dependency order. Current direct-to-target rendering remains the default until Phase 3 validates copy-CSV parity and the release path.

**Sources and fixed rules:** [proposal](./DEPLOYMENT_TIME_STAGING.md), [Phase 2 in the phase plan](./DEPLOYMENT_TIME_STAGING_PHASE_PLAN.md#phase-2-resolve-ids-and-fks-through-inline-staging), and Phase 1's review. Use effective identity and `resolve_aggregate_chain`, not entity names or `public_id_generation`, to find children. A tracked root must be inserted in the same submission with a SIMS ID; a reconciled root may be reference-only when its target ID is known. Existing tracked roots cannot gain children in this phase. Use one bundle per submission; existing-row updates, resubmissions, copy-CSV staging, and Sqitch promotion are outside Phase 2.

**Schema choice for this phase:** The deployed database has both `public` and `clearing_house` copies of target table names. Require an explicit `staging_target_schema` in `IngesterConfig.extra` for the opt-in staging strategy, and render schema-qualified target and sequence references. Use `public` for the representative Phase 1 contract and a disposable test schema for integration tests. Reject an absent or mismatched schema before target inserts. This implements the schema-qualification option documented by Phase 1 without changing the direct strategies' current table naming.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-8`): inline staging allocates child IDs only at deployment after locking affected tables, retains local IDs and FKs outside target rows, and maps identical-payload rows correctly regardless of input order. Unsupported sequence cache behavior fails before target inserts.
2. [x] `PH2-AC-2` (from `P-AC-7`, `P-AC-9`, `P-AC-11`): duplicate or conflicting mappings, unresolved required FKs, unsupported generators, cycles, and complete `unique_sets` duplicated among staged rows or matching existing target rows fail before target inserts. Generation-time diagnostics remain available for known IDs and fully resolved derived-bridge sets without rejecting unresolved child IDs.
3. [x] `PH2-AC-3` (from `P-AC-6`, `P-AC-10`): the inline artifact carries reference-only local-to-target mappings without inserting those rows; different local references may resolve to the same existing target row. Children of resolved reconciled roots and newly inserted tracked roots resolve; children of existing tracked roots are rejected. Explicit SIMS IDs retain sequence synchronization.

**Milestones:** `VM-2` executes leaf, multi-row, multi-level, and reconciled-root cases on disposable PostgreSQL, including stale-sequence and competing-writer checks (`PH2-AC-1`, `PH2-AC-3`). `VM-3` proves invalid model, mapping, generator, root-row, and complete `unique_sets` cases fail before target inserts; generation skips only values unavailable until deployment (`PH2-AC-2`, `PH2-AC-3`).

**Validation environment:** `V-4`/`V-5` ran against a disposable loopback PostgreSQL (`127.0.0.1:55433`, PostgreSQL 17.11 in `postgres:17-alpine`) started for this run and removed afterwards. The plan's loopback requirement is met.

## Repository Findings

**Repository basis:** branch `deployment-time-staging` at `f0d76e23`, inspected 2026-10-17. `f0d76e23` amends the `987e28af` basis with documentation-only changes. Graphify located `build_change_request_package` callers; source and tests below were checked directly. Baseline results: 77 focused ingester tests, 54 ingester end-to-end unit tests, and 42 Phase 1 helper tests passed; Ruff passed on the current ingester package and insert-dependency helper. The worktree has no local `.venv`; commands below use the verified virtualenv at `../sead_shape_shifter/.venv`.

| Verified source | Current behavior | Phase 2 consequence |
| --- | --- | --- |
| `src/target_model/effective_identity.py::resolve_aggregate_chain`; `src/target_model/insert_dependencies.py::build_insert_plan` | Phase 1 supplies full child/root chains and a deterministic insert order for selected rows, including optional FK edges and cycle results. | Reuse both results; enforce root rules per submitted row and reject selected cycles before target inserts. |
| `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` sections 11 and 13 | 39 `public` child generators are supported; `value_type_item` has no generator. Unscoped relation names are ambiguous across `public` and `clearing_house`. Supported sequences use increment 1, no cycle, `CACHE 1`, and no enabled insert trigger. | Qualify staged target relations; reject `value_type_item` and runtime schema/generator drift without a fallback. Lock the union of child and SIMS targets in sorted qualified-name order. |
| `ingesters/sead_change_request/planning.py::plan_table`; `orchestration.py::orchestrate_identity_assignments` | `public_id_generation: database_sequence` routes rows to `RESERVE_DATABASE_ID`; orchestration calls the target allocator during preparation. | An opt-in staging action/state must leave the child ID pending and avoid `reserve_target_id`; direct mode keeps current behavior. |
| `ingesters/sead_change_request/preparation.py::prepare_change_request`; `result_builders.py::build_validation_result`; `contracts.py::classify_submission_outcomes` | Validation and ingestion share preparation. Missing assignments are blocked; projection diagnostics fail validation, and only current allocated/derived states count as new data. | Carry pending deployment IDs through validation as intentional, while missing roots/FKs still fail. Both entry points must select the same strategy. |
| `ingesters/sead_change_request/target_projection.py::project_target_ids`; `package_builder.py::build_change_request_package` | Projection replaces local PK/FK values with known target values; package assembly keeps only insert and update rows. Reference-only parents vanish from the artifact. | Build separate staging rows from pre-projection data and mapping-only records from known IDs. Never render those reference rows as target writes. |
| `ingesters/sead_change_request/collision_checks.py::check_projected_collisions` | A pending public ID or derived-bridge set without all values is reported as a generation error; existing target rows are checked, but submitted duplicates are not. | Generation checks only known IDs and complete derived sets. Deployment checks every complete set after FK resolution, for child facts and derived bridges, against staged and target rows. |
| `ingesters/sead_change_request/sql_builder.py::InlineInsertDeployStrategy`, `CopyCsvDeployStrategy`, `_add_sequence_synchronization`, `_render_sequence_synchronization` | Direct insert and copy-CSV are the only named strategies. SIMS sync locks target tables in sorted order but runs after direct data statements. | Add an explicit inline staging strategy. Acquire the union of relevant locks before reading maxima or calling `setval`, then preserve SIMS sync after explicit IDs are inserted. Keep direct output stable. |
| `ingesters/sead_change_request/input_resolution.py::_resolve_deploy_strategy`; `ingester.py::SeadChangeRequestIngester.ingest`; `artifact_writer.py::write_artifact_bundle` | `config.extra` selects the renderer; ingestion runs collision checks, package assembly, rendering, and artifact writing. | Thread staging mode and schema through the existing path; keep one artifact and existing metadata/file conventions. |
| `backend/tests/ingesters/test_sead_change_request_runtime.py::test_target_sequence_reservation_uses_loopback_disposable_postgres` | PostgreSQL integration tests require `SEAD_DISPOSABLE_POSTGRES_*` and a loopback host. | Use this convention for `VM-2` and `VM-3`; the Phase 1 disposable clone has been dropped, so integration validation must run on a new disposable database. |

## Scope

**In scope:** explicit inline staging selection and schema qualification; pending child-ID state and per-row root checks; staging package rows and mapping-only references; generation checks for known values; deployment SQL for temp tables, locked sequence synchronization/allocation, ID/FK mapping, complete `unique_sets`, and ordered target inserts; unit and disposable PostgreSQL tests. Existing and new derived bridges with a generated parent FK must use the same FK map; a bridge's own generated ID need not be preallocated unless another staged row references it.

**Out of scope:** copy-CSV staging, default-strategy promotion, Sqitch release-path changes, existing-row updates/deletes, repeated-import handling, new `value_type` roots, and changing SIMS identity rules. Reject an unsupported staged dependency graph; do not mix direct and staged target writes or fall back to generation-time child reservation.

## Work Breakdown

### Area 1: Select staging and retain pending child identities

**Objective:** Validation and ingestion can prepare eligible child rows without requesting target sequence IDs during generation.

**Affected code:** `ingesters/sead_change_request/input_resolution.py`, `preparation.py`, `planning.py`, `orchestration.py`, `identity_resolution.py`, `target_projection.py`, `result_builders.py`, `contracts.py`, `ingester.py`, `sql_builder.py`; existing tests named below.

**Dependencies:** Completed Phase 1 chain, root-row, generator, and schema contract.

**Tasks**

- [x] `T1.1` **Change:** Add an opt-in inline staging strategy and explicit target schema.
  - **Target:** `sql_builder.py::resolve_deploy_artifact_strategy`, `input_resolution.py::_resolve_deploy_strategy`, `preparation.py::ResolvedInputs`, `ingester.py::SeadChangeRequestIngester._prepare_change_request`, `backend/tests/ingesters/test_sead_change_request_input_resolution.py`, `test_sead_change_request_ingester.py`.
  - **Current → required:** `inline_insert` is the direct default and no schema is selected for staging → `deploy_strategy: inline_staging` requires a nonempty `staging_target_schema`; both `validate()` and `ingest()` use that choice, while omitted/default and `copy_csv` retain current behavior.
  - **Implementation:** Validate the schema identifier in `config.extra`, carry it through `ResolvedInputs`, and select one bundle-level path before planning. Reject updates and a dependency graph mixing staged with direct rows in this isolated strategy. Use no implicit `public` default.
  - **Constraints:** Do not alter the direct strategy or its artifact metadata. An unsupported staged child must fail explicitly.
  - **Validation:** `V-1`, `V-2`, `V-6` cover selection, missing/unsafe schema, unchanged default, and explicit rejection.
- [x] `T1.2` **Change:** Represent child IDs pending deployment and enforce root-row rules.
  - **Target:** `contracts.py::PlannedRowAction`, `ChangeRowState`, `classify_submission_outcomes`; `planning.py::plan_bundle`, `plan_table`; `orchestration.py::orchestrate_identity_assignments`; `identity_resolution.py::resolve_planned_tables`; `target_projection.py::project_target_ids`; `result_builders.py::build_validation_result`; existing planning, orchestration, identity-resolution, and projection tests.
  - **Current → required:** a child with `database_sequence` reserves a target ID or is blocked → an eligible staged child has a distinct pending action/state, a null target public ID, and its original local `system_id` and FKs. Pending values alone do not invalidate staging preparation.
  - **Implementation:** Use `resolve_aggregate_chain` for every staged child. Walk the submitted local FK chain to its root; require a same-submission inserted tracked root with a resolved SIMS target ID, including `dataset` despite its lookup role, or a reconciled root with a resolved ID. Reject an existing tracked root, unresolved root, invalid chain, and a new `value_type` root. Route eligible children to the pending state without calling `reserve_target_id`; keep missing required nonpending values as errors.
  - **Constraints:** Do not use `public_id_generation` as an opt-in or change the direct path's reservation behavior during Phase 2.
  - **Validation:** `V-1`, `V-2`, `V-3`, `V-4`, `V-5` cover tracked/reconciled roots, no allocator call, pending validation, and invalid roots.

**Completion evidence:** An opt-in staging submission reaches package construction with pending child IDs and no allocator call. Direct and copy-CSV submissions still use their existing preparation and rendering paths.

### Area 2: Preserve local rows, reference mappings, and known-value checks

**Objective:** The artifact has every local key and FK needed at deployment, including known parent IDs absent from insert rows.

**Affected code:** `contracts.py::ChangeRequestPackage`, `package_builder.py::build_change_request_package`, `target_projection.py::project_target_ids`, `collision_checks.py::check_projected_collisions`, `ingester.py::SeadChangeRequestIngester.ingest`; existing package, projection, collision, and ingester tests.

**Dependencies:** Area 1 pending state and root checks.

**Tasks**

- [x] `T2.1` **Change:** Add staging rows and mapping-only known IDs to the package.
  - **Target:** `contracts.py::ChangeRequestPackage` and a planned `KnownIdMapping` row type; `package_builder.py` (new `build_staging_package` path); `ingester.py::SeadChangeRequestIngester.ingest`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`, `test_sead_change_request_ingester.py`.
  - **Current → required:** the direct package has projected insert/update rows only → the staging package has insert rows with original `system_id` and local FKs plus a separate list of `(entity, system_id, target ID)` mappings for reference-only parents, reconciled roots, and SIMS-assigned rows. Different local IDs may map to the same existing target ID.
  - **Implementation:** Add staging fields to `ChangeRequestPackage` while preserving `tables` for direct strategies. Build the staging input from `ResolvedIdentityTable.frame` and per-row actions, not projected target FKs. Keep mapping entries as rows until duplicate/conflict checks so a dictionary cannot overwrite them. Include only reference rows needed by staged FKs; never add them to target insert/update rows. Count staged insert rows correctly in ingestion results.
  - **Constraints:** Existing-row updates and resubmissions remain out of scope. Preserve direct-package filtering and one-bundle output.
  - **Validation:** `V-1`, `V-2`, `V-4`, `V-5` cover a new child of a reference-only reconciled parent, two local references to one target, and duplicate local keys.
- [x] `T2.2` **Change:** Limit generation collision checks to resolvable values.
  - **Target:** `collision_checks.py::check_projected_collisions`, `target_projection.py::project_target_ids`, `backend/tests/ingesters/test_sead_change_request_collision_checks.py`, `test_sead_change_request_target_projection.py`.
  - **Current → required:** pending child IDs and incomplete derived-bridge sets block generation → known public IDs and fully resolved derived-bridge `unique_sets` still get read-only target checks, while sets containing pending FK values wait for deployment.
  - **Implementation:** Distinguish pending deployment values from missing required data. A missing `unique_sets` declaration remains a diagnostic for a derived bridge; an incomplete set caused solely by a pending mapped FK is deferred. Do not treat generation checks as duplicate-submission protection; `T3.2` checks staged duplicates after FK resolution.
  - **Constraints:** Preserve actual known-ID and complete-set conflict diagnostics during ingestion; validation must still report missing required projection data.
  - **Validation:** `V-1`, `V-2`, `V-4`, `V-5` cover known collisions, a pending abundance FK in `abundance_ident_level`, and no false generation rejection.

**Completion evidence:** A reference-only parent appears in the artifact's ID-map input and nowhere in target-write rows. Known collisions still fail generation, while pending child IDs and dependent bridge sets do not.

### Area 3: Render one transactional inline staging artifact

**Objective:** Deployment SQL validates schema support, locks and allocates IDs, resolves FKs and complete unique sets, then inserts rows in dependency order.

**Affected code:** `ingesters/sead_change_request/sql_builder.py`, `inline_staging_sql.py` (**NEW**), `sql_rendering.py` (**NEW**); `src/target_model/insert_dependencies.py::build_insert_plan` is consumed without changing it; existing SQL-builder tests.

**Dependencies:** Areas 1–2 and Phase 1's `public` generator/cache contract. Use one transaction and `ON COMMIT DROP` temp tables.

**Tasks**

- [x] `T3.1` **Change:** Qualify target relations and lock supported generators before allocation.
  - **Target:** `sql_builder.py::resolve_deploy_artifact_strategy`, `_add_sequence_synchronization`, `_render_sequence_synchronization`; `inline_staging_sql.py` (**NEW**); `sql_rendering.py` (**NEW**); `backend/tests/ingesters/test_sead_change_request_sql_builder.py`.
  - **Current → required:** direct SQL uses model order and locks only SIMS sync tables → staging SQL uses the explicit schema to resolve one qualified target relation per entity, validates the deployed ID generator, and locks the sorted union of child-allocation and SIMS-sync tables in `SHARE ROW EXCLUSIVE` before any table maximum or `setval` read/write.
  - **Implementation:** Move the existing identifier, relation, string, and value quoting helpers to a shared `sql_rendering.py` module rather than creating a circular import; keep direct SQL text unchanged. At deployment check relation, ID column, sequence/default or identity association, positive noncycling increment, `CACHE 1`, and unsupported insert-trigger behavior against the Phase 1 contract. Synchronize stale sequences above existing IDs, then allocate one `nextval` per pending child row. Hold locks through insertion. Use qualified names for `pg_get_serial_sequence`, locks, checks, and writes.
  - **Constraints:** Do not derive IDs from `MAX(public_id)`; it is only a synchronization bound. Table locks do not control independent `nextval`, so the release no-concurrent-allocation rule still applies. Preserve direct SQL output and SIMS sync behavior.
  - **Validation:** `V-1`, `V-4`, `V-5`, `V-6` cover schema ambiguity, `value_type_item`, cache failure, stale sequence, competing writer, and explicit SIMS IDs.
- [x] `T3.2` **Change:** Build the local ID map, resolve FKs, and check complete `unique_sets` before target inserts.
  - **Target:** `inline_staging_sql.py` (**NEW**), `contracts.py::ChangeRequestPackage`, `backend/tests/ingesters/test_sead_change_request_sql_builder.py`.
  - **Current → required:** static direct inserts depend on already projected FKs → temp staging retains local and target FK columns separately; a deployment-local map is keyed by `(entity, system_id)` and supplies exactly one target ID for every required relationship.
  - **Implementation:** Load inline staging rows and known mappings, reject duplicate keys or conflicting assignments while allowing two local keys to share one target ID, and add newly allocated child IDs to the map. Resolve required, conditional, and present optional FKs before target inserts. For each configured `unique_set` whose columns are present and non-null after resolution, reject duplicates within staged rows and matches in the qualified target table, even if no target constraint exists. Cover child fact `abundance_modification` on `(abundance_id, modification_type_id)` and derived bridge `abundance_ident_level` on `(abundance_id, identification_level_id)` when `abundance_id` is allocated at deployment.
  - **Constraints:** A null optional set is not a complete set; missing required FKs still fail. Do not infer ID mapping from row order or identical payloads.
  - **Validation:** `V-1`, `V-4`, `V-5` cover mapped FKs, shared existing target IDs, missing/ambiguous references, staged duplicates, and target matches.
- [x] `T3.3` **Change:** Insert target rows in dependency order and emit the normal artifact.
  - **Target:** `sql_builder.py::build_deploy_artifact`, a planned `InlineStagingDeployStrategy` in `sql_builder.py`, `inline_staging_sql.py` (**NEW**), `ingester.py::SeadChangeRequestIngester.ingest`, and `backend/tests/ingesters/test_sead_change_request_sql_builder.py`.
  - **Current → required:** direct inline SQL inserts in package order → staging uses `build_insert_plan` for selected insert entities and present optional FK edges, rejects cycles, inserts resolved target values in order, and commits only after checks and inserts succeed.
  - **Implementation:** Omit `system_id` and local FK fields from target columns; explicitly insert allocated child IDs and resolved target FKs, using `OVERRIDING SYSTEM VALUE` for a supported `GENERATED ALWAYS` column. Let leaf derived bridges use their supported target default when their own ID is not referenced; reject a staged dependency requiring an unmapped derived-bridge ID. Preserve the existing deploy/revert/verify wrapper, metadata, and one-bundle file contract. Keep copy-CSV and default direct rendering unchanged.
  - **Constraints:** Database constraints remain the final check; a late failure rolls back rows, while consumed sequence values may leave gaps. Phase 3 owns Sqitch release validation and promotion.
  - **Validation:** `V-1`, `V-2`, `V-4`, `V-5`, `V-6` cover dependency order, generated/explicit IDs, artifact fields, and rollback.

**Completion evidence:** SQL text and executed results show qualified targets, sorted locks, `ON COMMIT DROP` staging, a keyed ID map, pre-insert FK and `unique_sets` checks, ordered inserts, and unchanged direct renderer tests.

### Area 4: Execute disposable PostgreSQL cases

**Objective:** Run `VM-2` and `VM-3` against a disposable loopback database and record actual row, sequence, and lock results.

**Affected tests:** `backend/tests/ingesters/test_sead_change_request_inline_staging.py` (**NEW**); existing ingester, SQL-builder, runtime, and Phase 1 helper tests remain regression targets.

**Dependencies:** Areas 1–3 and a disposable PostgreSQL database. The Phase 1 clone named in the review was dropped and is not a test target.

**Tasks**

- [x] `T4.1` **Change:** Test successful inline deployment cases.
  - **Target:** `backend/tests/ingesters/test_sead_change_request_inline_staging.py` (**NEW**).
  - **Current → required:** no staging integration test exists → a loopback-only fixture creates isolated target schemas/tables and executes the emitted inline artifact.
  - **Implementation:** Cover a leaf child of a newly inserted SIMS root, a child of a reference-only reconciled root, two local references to the same existing target row, identical-payload siblings with permuted input order, and a multi-level chain. Compare local-key-to-target relationships, not numeric sequence equality across runs. Start one sequence behind its table maximum and use two connections to show a competing writer waits on the staging lock. Assert no target table receives `system_id`, and explicit SIMS IDs still advance their sequence.
  - **Constraints:** Require `SEAD_DISPOSABLE_POSTGRES_*` with a loopback host, use only disposable objects, and clean them after the run. A skipped run does not satisfy `VM-2`.
  - **Validation:** `V-4` proves `VM-2` and `PH2-AC-1`/`PH2-AC-3`.
- [x] `T4.2` **Change:** Test pre-insert rejection and transaction rollback.
  - **Target:** `backend/tests/ingesters/test_sead_change_request_inline_staging.py` (**NEW**).
  - **Current → required:** no staging failure test exists → each invalid case has an actionable error and zero committed target rows.
  - **Implementation:** Cover duplicate/conflicting `(entity, system_id)` mappings, missing required and conditional FKs, an existing tracked root, unresolved reconciled root, selected insert cycle, an absent schema when table names occur in two schemas, a mismatched selected schema, missing generator (`value_type_item`), `CACHE > 1`, and complete `unique_sets` duplicated in staged rows or matching target rows under a reconciled parent. Include child fact and derived bridge sets using a newly generated abundance ID. Force a late target constraint error to confirm rollback and temp-table cleanup; allow a sequence gap.
  - **Constraints:** Distinguish cases rejected before any target insert from the late rollback probe. A skipped run does not satisfy `VM-3`.
  - **Validation:** `V-5` proves `VM-3` and `PH2-AC-2`/`PH2-AC-3`.

**Completion evidence:** `V-4` and `V-5` pass without skips against loopback `127.0.0.1:55433` (PostgreSQL 17.11, `postgres:17-alpine`): 13 tests passed and every temporary schema was dropped. The run covered serial target tables, a duplicate-name table in a second schema, a stale sequence, SIMS-assigned IDs, and a two-connection lock result.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-8`) | `T1.1`, `T1.2`, `T2.1`, `T3.1`–`T3.3`, `T4.1` | `V-1`, `V-2`, `V-4`, `V-6` | No generation-time child reservation; locked deployment allocation and local-key FK mapping succeed regardless of payload/order. |
| `PH2-AC-2` (`P-AC-7`, `P-AC-9`, `P-AC-11`) | `T1.2`, `T2.1`, `T2.2`, `T3.1`–`T3.3`, `T4.2` | `V-1`, `V-2`, `V-5` | Invalid mapping, FK, generator, cycle, and complete-set cases stop before target inserts; known generation checks remain. |
| `PH2-AC-3` (`P-AC-6`, `P-AC-10`) | `T1.2`, `T2.1`, `T3.1`–`T3.3`, `T4.1`, `T4.2` | `V-1`–`V-5` | Reference-only and SIMS IDs seed the map; root-row rules hold; no reference-only row is written. |

## Validation And Testing

Commands run from `/data/roger/source/sead_shape_shifter-deployment-time-staging`. This worktree has no local `.venv`; `../sead_shape_shifter/.venv/bin/python` and its Ruff executable were verified. Set `SEAD_DISPOSABLE_POSTGRES_HOST`, `_PORT`, `_DB`, and `_USER` (and `_PASSWORD` if needed) only for disposable loopback integration runs. The tests must reject a non-loopback host.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Planning, identity, projection, package, collision, SQL, and input-resolution unit tests | `../sead_shape_shifter/.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_identity_resolution.py backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_collision_checks.py backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_input_resolution.py -q` | `PH2-AC-1`–`PH2-AC-3` | Existing behavior remains green; add pending-ID, root-row, mapping-only, complete/incomplete set, schema/generator, SQL ordering, and default-strategy cases to these exact files. | **Pass:** existing and new cases passed on 2026-10-17 (part of a 220-test ingester run). |
| `V-2` | Ingester validation, output contract, and direct-strategy regression | `../sead_shape_shifter/.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH2-AC-1`–`PH2-AC-3`, preserved direct behavior | Assert staging selection and one emitted artifact, no child allocator call, source warnings, failure results, unchanged direct/copy-CSV output and metadata. | **Pass:** direct, copy-CSV, and staged cases passed on 2026-10-17. |
| `V-3` | Phase 1 chain and dependency helper regression | `../sead_shape_shifter/.venv/bin/python -m pytest tests/target_model/test_effective_identity.py tests/target_model/test_insert_dependencies.py -q` | Root and dependency contract used by `PH2-AC-1`–`PH2-AC-3` | Valid tracked/reconciled chains and selected insert order/cycle cases continue to pass. | **Pass:** Phase 1 helper tests passed on 2026-10-17. |
| `V-4` | Disposable PostgreSQL successful deployments, `VM-2` | With the disposable connection variables set: `../sead_shape_shifter/.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_inline_staging.py -q`; inspect the success-case results for `T4.1`. | `PH2-AC-1`, `PH2-AC-3` | Leaf, multi-row, multi-level, reference-only, SIMS, stale-sequence, and competing-writer cases pass; assertions compare FK relationships and target rows. | **Pass:** 13 passed, 0 skipped on 2026-10-17 against loopback `127.0.0.1:55433` (PostgreSQL 17.11). |
| `V-5` | Disposable PostgreSQL failures, `VM-3` | Run the same **NEW** test file and connection as `V-4`; inspect the failure-case results for `T4.2`. | `PH2-AC-2`, `PH2-AC-3` | Each pre-insert error leaves target row counts unchanged; the late constraint probe rolls back target rows and drops temporary tables. Sequence rollback is not required. | **Pass:** the same 13-test run covered every rejection and rollback case; all schemas were dropped afterwards (`leftover schemas: none`). |
| `V-6` | Direct runtime and rendering regression | `../sead_shape_shifter/.venv/bin/python -m pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_sql_builder.py -q` | Direct/copy-CSV, SIMS, artifact contract | Direct and copy-CSV behavior, explicit SIMS sync, and current artifact metadata pass. The existing runtime DB test may skip without disposable variables; `V-4` covers staged DB behavior. | **Pass:** ran as a combined command on 2026-10-17. The existing runtime DB test skipped without disposable variables. |
| `V-7` | Code quality and document links | `../sead_shape_shifter/.venv/bin/ruff check ingesters/sead_change_request src/target_model/insert_dependencies.py backend/tests/ingesters/test_sead_change_request_inline_staging.py`; `../sead_shape_shifter/.venv/bin/black --check ingesters/sead_change_request backend/tests/ingesters/test_sead_change_request_inline_staging.py`; `../sead_shape_shifter/.venv/bin/isort --check-only ingesters/sead_change_request backend/tests/ingesters/test_sead_change_request_inline_staging.py`; `scripts/check_doc_links.sh`; `git diff --check` | Touched code/tests and this plan | Lint, formatting, links, and whitespace checks pass after implementation. | **Ruff pass.** Formatting does not pass on a clean baseline: `ruff format --check` and `black --check` already fail on files untouched by this work, so only the four new modules were formatted. `git diff --check` is clean. |

Disposable execution evidence recorded on 2026-10-17 from the loopback database (`127.0.0.1:55433`, PostgreSQL 17.11); 13 of 13 tests passed with no skips:

| Scenario | Result |
| --- | --- |
| Multi-level chain: dataset root from SIMS, `analysis_entity` and two `abundance` rows allocated at deployment | Passed; child FKs resolve to the allocated parents and the allocator port was never called. |
| Reference-only reconciled root (`site`) | Passed; the existing site ID seeds the map and no site row is written. |
| Identical payloads in permuted input order | Passed; taxon-to-dataset relationships match for both orders and allocated IDs are consistent per dataset. |
| Stale `abundance` sequence reset to 1 before a second deployment | Passed; the next allocated ID exceeded the previous maximum. |
| SIMS-assigned ID followed by sequence synchronization | Passed; the target sequence advanced past the explicit ID. |
| Duplicate `unique_sets` within staged rows | Rejected with `duplicate unique_set`; no row committed. |
| Complete `unique_sets` matching an existing target row | Rejected with `match an existing target row`; no row committed. |
| Child of an existing tracked root | Rejected at validation with `existing tracked root`. |
| Unresolved reconciled root (`lookup-only`, no match) | Rejected before inserts; the unresolved `site_id` blocked the dependent row. |
| Selected schema absent | Rejected with `does not exist` before any insert. |
| No staging schema supplied | Rejected as a validation failure before rendering. |
| Late primary-key conflict on two staged roots | Rolled back; no dataset or analysis row committed and sequence gaps were left. |
| Competing writer during staging | Timed out with `LockNotAvailable` while staging held `SHARE ROW EXCLUSIVE`. |

The disposable tests must build their own small serial and identity target tables in an isolated schema, plus a duplicate-name table in a second schema to prove qualification. They must not use the representative `sead_staging` database for writes. A generated SQL snapshot, a skipped integration run, or a test that omits the competing writer does not satisfy `VM-2`/`VM-3`.

## Deliverables

| Deliverable | Exact target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Explicit staging selection and schema | `ingesters/sead_change_request/input_resolution.py`, `preparation.py`, `ingester.py`, `sql_builder.py` | `T1.1`, `T3.3` | Staging requires a schema; `V-1`, `V-2` pass while direct default stays stable. |
| Pending identity and root-row checks | `ingesters/sead_change_request/contracts.py`, `planning.py`, `orchestration.py`, `identity_resolution.py`, `target_projection.py`, `result_builders.py` | `T1.2` | No child sequence call during generation; valid/invalid root cases pass. |
| Staging package and generation checks | `ingesters/sead_change_request/contracts.py`, `package_builder.py`, `target_projection.py`, `collision_checks.py` | `T2.1`, `T2.2` | Local values and mapping-only rows survive; known collisions remain. |
| Inline staging SQL and shared quoting | `ingesters/sead_change_request/inline_staging_sql.py` (**NEW**), `sql_rendering.py` (**NEW**), `sql_builder.py` | `T3.1`–`T3.3` | Qualified, locked, validated, ordered SQL passes `V-1`, `V-4`, `V-5`. |
| Existing unit and regression tests | `backend/tests/ingesters/test_sead_change_request_planning.py`, `test_sead_change_request_identity_resolution.py`, `test_sead_change_request_target_projection.py`, `test_sead_change_request_package_builder.py`, `test_sead_change_request_collision_checks.py`, `test_sead_change_request_sql_builder.py`, `test_sead_change_request_input_resolution.py`, `test_sead_change_request_ingester.py` | `T1.1`–`T3.3` | `V-1`, `V-2`, `V-6` pass. |
| Disposable inline deployment tests | `backend/tests/ingesters/test_sead_change_request_inline_staging.py` (**NEW**) | `T4.1`, `T4.2` | `V-4` and `V-5` pass without skips. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Staging selection and pending IDs | Done | Phase 1 completed contract | `inline_staging` requires `staging_target_schema`; children plan `DEFER_TO_DEPLOYMENT`; root rules implemented in `staging_eligibility.py`; `V-1`, `V-2`, `V-3` pass. |
| Area 2: Local rows and known-value checks | Done | Area 1 | `build_staging_package` keeps local values and emits `KnownIdMapping` rows; projection and collision checks defer pending values only. |
| Area 3: Transactional inline SQL | Done | Areas 1–2; Phase 1 generator/cache rules | `render_inline_staging_deploy` emits one statement per artifact entry: support check, sorted union locks, temp staging, id map, allocation, FK resolution, unique-set checks, ordered inserts, SIMS sync. |
| Area 4: Disposable deployment cases | Done | Areas 1–3; loopback PostgreSQL | 13 tests passed with no skips against loopback `127.0.0.1:55433` (PostgreSQL 17.11); the fixture created and dropped its own schemas. |

Execution note: HEAD was `f0d76e23` (branch `deployment-time-staging`) when implementation started, an amend of the `987e28af` basis named in Repository Findings with documentation-only changes. The uncommitted phase-plan edit and the untracked Phase 2 task plan were preserved. `V-7` formatting could not pass on the existing tree: `ruff format --check` and `black --check` already fail on files untouched by this work (for example `orchestration.py` and `target_projection.py` at HEAD), so only the four new modules were formatted.

## Definition Of Done

- [x] `PH2-AC-1`–`PH2-AC-3` have the mapped task results and `V-1`–`V-3`, `V-6` validation results.
- [x] `VM-2` and `VM-3` pass under the loopback fixture (`V-4`, `V-5`; 13 tests, no skips).
- [x] All areas and deliverables are complete. `V-7` formatting matches the existing baseline rather than passing cleanly, because `ruff format --check` and `black --check` already fail on files untouched by this work.
- [x] Reference-only mappings, same-target references, tracked/reconciled root rules, child fact and derived-bridge complete sets, and SIMS sequence sync have regression coverage.
- [x] Generated SQL contains no numeric public IDs for pending children and never writes `system_id` or local FK values to target columns; local keys live in `_local_*` staging columns.
- [x] Runtime generator/cache checks and qualified relations agree with the Phase 1 contract; `value_type_item` remains unsupported until a deployed generator exists, and a new `value_type` root is rejected.
- [x] The artifact contract and this plan record any implementation deviation; Phase 3 can reuse the mapping, locking, and unique-set rules without changing Phase 2 outcomes. If verified schema or source behavior conflicts with this plan, stop and report the exact conflict rather than broadening scope or inventing another design.

## Risks And Open Questions

- **Deployed schema drift:** Phase 1 inspected `public` on 2026-10-17. Deployment must verify the chosen qualified relation, generator, cache setting, and trigger disposition again. A changed or missing mechanism is an explicit failure, not permission to reserve IDs during generation.
- **Sequence visibility:** `setval` and `nextval` are not rolled back with failed target inserts. Gaps are acceptable; target row atomicity is required. Sorted table locks prevent competing inserts but do not serialize independent `nextval`, which the supported release workflow excludes.
- **Derived bridge IDs:** `abundance_ident_level` has a generated own ID and a generated-parent FK. Its FK and `unique_sets` must resolve before insertion; a later staged row requiring its own target ID is unsupported unless the mapping contract is extended deliberately.
