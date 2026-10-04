# Phase 1 Task Plan: SIMS Capability And Batch Guarantees

## Phase Summary

**Goal:** Publish and enforce a configurable, generic SIMS identity contract, mint entity-scoped aggregate identities from configuration rather than entity-specific code, and make each resolve batch atomic and replayable.

**Readiness:** Validated for the agreed architecture. Phase 1 is marked ready in the [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md). SIMS is under development, so the stable run ID is required from the first version of the batch contract; no legacy compatibility path is needed. Capability support is determined by validated entity configuration, not a hard-coded `site`/`sample` allowlist.

**Constraints and dependencies**

- Use the verified `site` and `sample` paths as configuration and regression examples, not as the limit of the generic mechanism or a requirement for entity-specific allocator code.
- Reject missing or invalid entity configuration explicitly. SIMS guarantees uniqueness only within its own identity store.
- Cutover, deployment, existing-data migration, stopping other writers, and SEAD database integrity are outside this development task.
- Keep SEAD reconciliation and per-row match/miss approval in Shape Shifter.
- Use only the helper-owned disposable PostgreSQL database for database-backed validation. Do not run intended-deployment, production, or cutover checks.
- The Authority Service checkout is already modified. Preserve its current uncommitted work and reconcile each planned edit with that source before implementation.

**Source documents:** [identity-allocation proposal](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md), [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md), and [candidate verification](./SIMS_IDENTITY_ALLOCATION_CANDIDATE_VERIFICATION.md).

### Phase Acceptance Criteria

- [x] `PH1-AC-1` (from `P-AC-3`, `P-AC-4`): The capability response describes operations enabled by validated configuration, and unconfigured types or invalid operations receive a stable error rather than default policy behavior.
- [x] `PH1-AC-2` (from `P-AC-5`): Configured allocation returns the same SIMS-issued, entity-scoped aggregate identity value and tracked UUID on retry; artifact generation fails if a required value is absent.
- [x] `PH1-AC-3` (from `P-AC-7`): A later run reuses a confirmed identity, while a distinct run encountering a proposed Binding Set receives a conflict and does not allocate a second identity or target ID.
- [x] `PH1-AC-4` (from `P-AC-9`, `P-AC-11`): A run creates one Submission and one Binding Set; identical retries return the stored result, changed payloads conflict, and failed batches leave no partial result.
- [x] `PH1-AC-5` (from `P-AC-14`): An approved existing aggregate identity binds without minting another identity; a conflicting binding fails, and a configured new-identity request receives its SIMS-issued identity values.
- [x] `PH1-AC-6` (from `P-AC-15`, `P-AC-16`): SIMS stores entity-scoped aggregate identity values, tracked UUIDs, and source keys as distinct roles and enforces uniqueness within its own store without SEAD schema or sequence knowledge.

## Repository Findings

**Repository basis:** Planning date 2026-10-02. The Authority Service is on `sims-resume-work-autumn-2026` at `cb29605` and retains uncommitted changes; findings below use that working tree and must preserve its changes. The Shape Shifter SIMS integration work this plan depends on has since been committed on `dev`.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `sead_authority_service/src/api/identity_router.py::ResolveRequest`, `resolve()` | `POST /identity/resolve` has no run ID. The endpoint creates a scope and Submission, resolves each request, then calls `bind`; the resolve steps are not wrapped in one outer transaction. | Add a required stable run ID in the first batch contract version and route the endpoint through one batch service operation. |
| `sead_authority_service/src/identity/policy.py::IdentityPolicy.get_entity_policy()` | Unlisted types inherit defaults; `known_entity_types()` reports configured names but no supported operations. | Make resolve behavior derive from validated, explicit configuration and reject missing configuration; do not use defaults to infer capability. |
| `sead_authority_service/config/identity_policy.yml` | Entity-specific legacy subtype/allocation settings exist; proposed site operation keys are comments and are not parsed. | Define generic entity configuration consumed by shared allocator and resolver code. Keep `site` and `sample` as examples, not hard-coded operation cases. |
| `sead_authority_service/src/identity/service.py::resolve_identity()`, `bind()` | Approved target-ID binding, confirmed-binding reuse, proposed-binding conflicts, and binding-stage row locking already exist. `bind()` owns a transaction only for the binding stage. | Preserve those behaviors while moving the complete HTTP batch into one transaction and adding operation-specific rejection. |
| `sead_authority_service/src/identity/repository.py::SourceIdentityRepository.create_or_get()`, `lock_for_binding()`, `TrackedIdentityRepository.mint()` | Source-key advisory locks and binding row locks exist. `mint()` uses entity-specific allocator rows for some types; a missing allocator row fails. | Replace entity-specific mint branches with the generic configured allocator and enforce uniqueness within the SIMS store. |
| `sead_authority_service/src/configuration/setup.py::get_connection()` | Nested calls reuse the active connection; the outer context commits on success and rolls back on error. | The batch service can use the existing transaction boundary if every repository call remains inside its outer context. |
| `sead_authority_service/schema/sql/identity/009_site_id_allocator.sql` | The current working tree contains the site/sample allocator schema as migration 009. | Add the request-idempotency schema as an additive next identity SQL file; apply it only to the helper-owned disposable database for validation. |
| `sead_authority_service/tests/identity/test_policy.py`, `test_api.py`, `test_service.py`, `test_repository.py`, `test_service_integration.py` | Unit tests cover policy fallback, API conflicts, approved target IDs, allocator behavior, source locking, and pending Binding Sets. Integration tests already provide a `disposable_service` fixture that checks for `127.0.0.1:55432/sead_staging`. | Extend these tests for strict capabilities and batch replay; new database-backed tests must use the guarded disposable fixture. |
| `sead_authority_service/src/identity/README.md` | Documents current identity endpoints and the existing test commands. | Update the endpoint and test guidance when adding capability publication and batch idempotency. |
| Shape Shifter `backend/app/models/sims.py::ResolveRequest`, `backend/app/services/ingester_runtime.py`, `backend/app/clients/sims_client.py::SIMSClient.resolve()` | The current consumer request has no run ID; the runtime calls SIMS for individual entity resolutions. | Require a run ID in the initial contract and update the consumer before enabling these operations; Phase 2/3 own the consumer batching changes. |

**Baseline checks on the current Authority Service checkout**

- `uv run pytest tests/identity/ -q` — Pass; database integration tests were skipped because `SIMS_INTEGRATION_DB` was not enabled.
- `uv run ruff check src/identity tests/identity` — Fail: 12 findings in the current working tree (five line-length findings in `src/identity/models.py`, plus import-order/import-position findings in `tests/identity/test_policy.py`).
- `uv run ruff check src/api/identity_router.py src/identity/policy.py src/identity/service.py src/identity/repository.py tests/identity/test_api.py tests/identity/test_service.py tests/identity/test_repository.py tests/identity/test_service_integration.py` — Pass.

## Scope

**In scope**

- Define and publish a versioned SIMS capability and identity contract driven by validated entity configuration.
- Implement generic entity-scoped aggregate identity allocation and binding without entity-specific allocator branches.
- Return SIMS-issued aggregate identity values and tracked UUIDs for configured allocations and approved existing-identity bindings.
- Prove that adding a configured entity type uses the same allocator implementation and that missing or invalid configuration is rejected.
- Add a scoped run ID, payload fingerprint, persistent replay result, database serialization, and one transaction for the entire resolve batch.
- Verify behavior with unit tests and the helper-owned disposable database.

**Out of scope**

- Shape Shifter model-driven planning, consumer batching, and artifact generation; these belong to later phases.
- Bootstrap, competing-writer retirement, deployment, rollout, and cutover checks.
- Production or intended-deployment validation.
- Manual SIMS Binding Set confirmation, target-system insertion behavior, and SEAD database-integrity checks.

## Work Breakdown

### Area 1: Define And Enforce Generic Entity Configuration

**Objective:** Publish a versioned contract for generic configured operations and make the resolve endpoint reject missing or invalid entity configuration before creating records.

**Affected code:** `sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md` (NEW); `sead_authority_service/src/api/identity_router.py`; `sead_authority_service/src/identity/policy.py`; `sead_authority_service/config/identity_policy.yml`; `sead_authority_service/src/identity/README.md`; `sead_authority_service/tests/identity/test_api.py`; `sead_authority_service/tests/identity/test_capabilities.py` (NEW).

**Dependencies:** The request-key and enabled-operation questions in [Risks And Open Questions](#risks-and-open-questions) must be decided and recorded in the companion contract before API behavior is changed.

**Tasks:**

* [x] `T1.1` **Change:** Write the companion Authority Service proposal and settle the capability and request contract before implementation.
  * **Target:** `sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md` (NEW); review Shape Shifter `backend/app/models/sims.py::ResolveRequest` and `backend/app/clients/sims_client.py::SIMSClient.resolve()`.
  * **Current → required:** The phase handoff requires a versioned `GET /identity/capabilities` response, but the exact response schema belongs in a companion Authority Service proposal. The existing downstream request has no stable run ID.
  * **Implementation:** Specify the response version, generic entity-scoped configuration, accepted source-key semantics, confirmation behavior, and identity-value result. A provider-supplied UUID is a source identity value only; it must never replace the SIMS-minted tracked identity UUID or aggregate identity value. Use `site` and `sample` as examples only. Define stable errors for missing or invalid configuration, require a stable run ID and payload fingerprint from the first batch contract version, and document how clients learn configured capabilities. Keep Shape Shifter's reconciliation and match/miss approval outside SIMS.
  * **Constraints:** Configuration selects generic behavior; it must not require entity-specific allocator code. SIMS guarantees uniqueness only within its own identity store and does not map identity values to SEAD tables or columns. Do not include cutover or production enablement in this development task.
  * **Validation:** `V-1`; contract review against the agreed generic identity ownership model, phase plan, and current consumer request model.
* [x] `T1.2` **Change:** Replace implicit policy fallback with explicit operation checks and publish the versioned capability response.
  * **Target:** `sead_authority_service/src/identity/policy.py::IdentityPolicy`; `sead_authority_service/config/identity_policy.yml`; `sead_authority_service/src/api/identity_router.py`.
  * **Current → required:** Unknown types receive default policy, the policy has no enforced operation field, and no capability endpoint exists.
  * **Implementation:** Parse and validate generic entity configuration defined by `T1.1`; add `GET /identity/capabilities`; derive supported operations from configuration and require a valid configured operation on `POST /identity/resolve` before scope, Submission, or identity writes. Return the contract's stable client error when configuration is missing or invalid.
  * **Constraints:** Preserve `get_entity_policy()` fallback for existing non-capability callers; the resolve endpoint must use validated generic configuration and must not mistake that fallback for support. New entity types must use the same allocator implementation.
  * **Validation:** `V-2`; policy tests for listed/unlisted types and operation combinations; API tests for capability version/content, stable rejection, and rejection before writes.
* [x] `T1.3` **Change:** Document the new endpoint and enforceable operation scope in the identity module guide.
  * **Target:** `sead_authority_service/src/identity/README.md`.
  * **Current → required:** The endpoint list and test instructions do not include capability discovery or batch replay.
  * **Implementation:** Document the capability endpoint, configuration-driven operations, missing/invalid configuration behavior, and the documented disposable integration-test command.
  * **Constraints:** State clearly that disposable validation is not deployment or cutover approval.
  * **Validation:** `V-1`; verify documentation matches the companion contract and implemented API.

**Completion evidence:** The companion contract is recorded, capability discovery reflects validated configuration, the same allocator supports multiple configured entity types, and API tests prove that missing or invalid configuration fails before writes.

### Area 2: Make Resolve Batches Atomic And Replayable

**Objective:** Store a scoped run key and completed result with all batch writes in one transaction; replay identical requests and reject key reuse with a changed payload.

**Affected code:** `sead_authority_service/src/api/identity_router.py::ResolveRequest`, `resolve()`; `sead_authority_service/src/identity/service.py::IdentityService`; `sead_authority_service/src/identity/repository.py`; `sead_authority_service/schema/sql/identity/011_resolve_batch_idempotency.sql` (NEW); `sead_authority_service/tests/identity/test_repository.py`; `sead_authority_service/tests/identity/test_service.py`.

**Dependencies:** `T1.1` defines the required run ID and capability/enablement contract. The additive migration must be applied to the helper-owned database before `V-5`.

**Tasks:**

* [x] `T2.1` **Change:** Add persistent storage for scoped run keys, request fingerprints, and completed resolve responses.
  * **Target:** `sead_authority_service/schema/sql/identity/011_resolve_batch_idempotency.sql` (NEW); `sead_authority_service/src/identity/repository.py`.
  * **Current → required:** The database has no resolve-batch idempotency record or unique scope/run-key constraint.
  * **Implementation:** Add an additive identity-schema migration and repository operations to look up and persist one completed batch result per scoped key, including the canonical request fingerprint and response needed for exact replay.
  * **Constraints:** Insert the idempotency record and result in the same transaction as the Submission and identity changes. Never release or recycle a target ID. Do not edit generated schema artifacts or deploy the migration outside the disposable database during this phase.
  * **Validation:** `V-3`, `V-5`; repository unit tests for lookup, insert, uniqueness, and fingerprint mismatch; disposable schema inspection after migration.
* [x] `T2.2` **Change:** Route one resolve request through a service method that owns the complete transaction.
  * **Target:** `sead_authority_service/src/api/identity_router.py::ResolveRequest`, `resolve()`; `sead_authority_service/src/identity/service.py::IdentityService`.
  * **Current → required:** The router creates the scope and Submission, resolves rows, then binds them in separate transaction contexts.
  * **Implementation:** Require the contract's stable run ID from the first supported batch request and delegate scope resolution/creation, replay lookup, Submission creation, all source-identity resolution, one Binding Set, target-ID allocation, and result persistence to one outer `get_connection()` transaction. Return the saved result for same-key/same-payload retries; return the contract's conflict for same-key/different-payload requests; preserve request order in outcomes.
  * **Constraints:** A failure at any point rolls back the scope created for the batch, Submission, source keys, tracked identities, bindings, Binding Set, and replay result. Use the existing nested `get_connection()` behavior rather than opening independent transaction scopes.
  * **Validation:** `V-2`, `V-4`, `V-5`; unit tests for response ordering and rollback propagation, plus disposable batch replay and failure tests.
* [x] `T2.3` **Change:** Serialize duplicate run keys and preserve source-identity binding rules during batch retries.
  * **Target:** `sead_authority_service/src/identity/service.py::IdentityService`; `sead_authority_service/src/identity/repository.py::SourceIdentityRepository`.
  * **Current → required:** Source-key and binding locks exist, but no lock or unique key serializes concurrent calls for one run ID.
  * **Implementation:** Acquire a database transaction lock for the scoped run key before creating batch records, enforce uniqueness in the schema, reuse confirmed bindings, and retain the existing proposed-binding conflict for a distinct run. Ensure an approved existing `site` ID binds to the existing materialized identity without minting and that new `site`/`sample` operations return their SIMS-allocated target IDs.
  * **Constraints:** Preserve source keys, tracked UUIDs, and aggregate identity values as separate values. Do not use SEAD sequences. A failed batch must not leave a successful replay record or partial allocation.
  * **Validation:** `V-3`, `V-4`, `V-5`; repository/service unit tests and database-backed concurrent replay, changed-payload conflict, confirmed retry, proposed-binding conflict, and allocator-state rollback scenarios.

**Completion evidence:** Database-backed requests demonstrate one Submission/Binding Set per successful run, exact replay without duplicate allocations, a conflict for changed payloads, and no partial database state after a failed batch.

### Area 3: Verify The Approved Operations In The Disposable Database

**Objective:** Prove the operation and transaction contracts against the guarded helper database without running deployment or cutover checks.

**Affected code:** `sead_authority_service/tests/identity/test_service_integration.py`; `sead_authority_service/tests/identity/test_api.py`; `sead_authority_service/tests/identity/test_service.py`; `sead_authority_service/tests/identity/test_repository.py`.

**Dependencies:** Areas 1 and 2; apply the new additive migration to the helper-owned database before integration tests.

**Tasks:**

* [x] `T3.1` **Change:** Add unit and API regression cases for the closed operation set and target-ID outcomes.
  * **Target:** `sead_authority_service/tests/identity/test_capabilities.py` (NEW); `test_api.py`; `test_service.py`; `test_repository.py`.
  * **Current → required:** Existing tests cover generic policy fallback and approved target IDs but do not exercise capability discovery or the approved operation matrix. Keep generic fallback behavior for non-capability callers while proving it cannot authorize resolve operations.
  * **Implementation:** Test that the capability response reflects validated configuration, that `site` and `sample` use the shared allocation mechanism through configuration, and that a new configured test entity does not require an allocator branch. Verify missing or invalid configuration is rejected. Test approved binding reuse, binding conflicts, and allocation failure when required SIMS-owned allocator state is unavailable.
  * **Constraints:** Do not add entity-specific allocator branches or production/cutover behavior. Keep manual Binding Set confirmation out of scope.
  * **Validation:** `V-2`, `V-3`.
* [x] `T3.2` **Change:** Extend the guarded disposable integration suite with whole-batch and concurrency checks.
  * **Target:** `sead_authority_service/tests/identity/test_service_integration.py`, using the existing `disposable_service` fixture and its `127.0.0.1:55432/sead_staging` guard.
  * **Current → required:** Existing integration tests cover individual site/sample allocation, concurrent identity operations, approved target IDs, and proposed-binding conflicts, but not an idempotent atomic resolve batch.
  * **Implementation:** Add database-backed scenarios for same-key/same-payload replay, concurrent duplicate run requests, same-key/changed-payload conflict, request-order preservation, distinct-run proposed-binding conflict, and rollback after an earlier batch item has written. Query the SIMS database to confirm source keys, tracked UUIDs, and configured aggregate identity values remain distinct and linked, and that allocator state is not advanced by a failed batch.
  * **Constraints:** Every new database test must use the guarded disposable fixture. Check the host, port, and database before applying SQL or running tests. Do not connect to an intended deployment or run bootstrap/cutover checks; those belong to the [operational proposal](../../CUTOVER_AND_DEPLOYMENT/SIMS_SEAD_TRUST_CONTRACT_ADOPTION_PROPOSAL.md).
  * **Validation:** `V-4`, `V-5`.
* [x] `T3.3` **Change:** Rerun the focused identity suite and targeted lint after implementation.
  * **Target:** The identity API, policy, service, repository, and integration test files listed in this plan.
  * **Current → required:** The current unit suite passes, but the full identity-tree Ruff check has recorded baseline findings.
  * **Implementation:** Run the focused unit suite and Ruff over changed source/test files. Keep unrelated existing `src/identity/models.py` lint findings out of the change; do not claim the broad baseline Ruff check is clean unless separately repaired within scope.
  * **Constraints:** Do not use the repository's `make ruff-lint` target for this check because it invokes Ruff with `--fix`.
  * **Validation:** `V-2`, `V-3`.

**Completion evidence:** Focused unit/API tests and the database-backed batch scenarios pass against the helper database; no deployment or cutover check has been run.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (`P-AC-3`, `P-AC-4`) | `T1.1`, `T1.2`, `T3.1` | `V-1`, `V-2` | Versioned capability response reflects validated configuration; missing or invalid configuration receives the stable documented error. |
| `PH1-AC-2` (`P-AC-5`) | `T1.1`, `T1.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-4`, `V-5` | Shared configured allocation returns SIMS-issued identity values; artifact integration rejects a missing required value. |
| `PH1-AC-3` (`P-AC-7`) | `T2.3`, `T3.2` | `V-4`, `V-5` | Confirmed identities are reused; a distinct run meeting a proposed binding conflicts without a second identity or ID. |
| `PH1-AC-4` (`P-AC-9`, `P-AC-11`) | `T2.1`, `T2.2`, `T2.3`, `T3.2` | `V-3`, `V-4`, `V-5` | A batch creates one Submission and Binding Set; identical retries replay the stored response; changed payloads conflict; failures leave no partial state. |
| `PH1-AC-5` (`P-AC-14`) | `T2.3`, `T3.1`, `T3.2` | `V-2`, `V-4`, `V-5` | Approved existing identities bind without minting; conflicts fail; configured allocations return SIMS-issued identity values and UUIDs. |
| `PH1-AC-6` (`P-AC-15`, `P-AC-16`) | `T2.1`, `T2.3`, `T3.2` | `V-4`, `V-5` | SIMS stores distinct source keys, tracked UUIDs, and entity-scoped aggregate identity values, and enforces uniqueness within its own store. No SEAD database or cutover checks are performed. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Companion contract review | Compare `sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md` with the generic identity ownership model, Phase 1 handoff, and current Shape Shifter request model/client. | `PH1-AC-1`, `PH1-AC-2` | Configuration schema, generic operation semantics, stable errors, run-key behavior, and capability reporting are explicit and consistent before service code changes. | Pass (2026-10-03): companion contract written, reviewed, and implemented. |
| `V-2` | Identity unit and API suite | `cd /data/roger/source/sead_authority_service && uv run pytest tests/identity/ -q` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-5` | Tests pass for validated configuration, generic capability response, approved binding, missing/invalid configuration, and explicit allocation failures. | Pass (2026-10-03): 214 passed, 1 skipped against the disposable DB with `SIMS_INTEGRATION_DB=1`; 182 passed, 27 skipped with integration disabled. |
| `V-3` | Focused lint | `cd /data/roger/source/sead_authority_service && uv run ruff check src/api/identity_router.py src/identity/policy.py src/identity/service.py src/identity/repository.py tests/identity/test_api.py tests/identity/test_capabilities.py tests/identity/test_service.py tests/identity/test_repository.py tests/identity/test_service_integration.py` | `PH1-AC-1`, `PH1-AC-4`, `PH1-AC-5` | No Ruff findings in the Phase 1 source and test targets. | Pass (2026-10-03): all Phase 1 source and test targets clean, including `test_capabilities.py`. |
| `V-4` | Batch contract integration tests | After confirming the configured host/port/database are exactly the helper-owned `127.0.0.1:55432/sead_staging`: `cd /data/roger/source/sead_authority_service && SIMS_INTEGRATION_DB=1 ENV_FILE=tests/.env uv run pytest tests/identity/test_service_integration.py -k batch -v` | `PH1-AC-3`, `PH1-AC-4`, `PH1-AC-5`, `PH1-AC-6` | Guarded tests prove replay, concurrent duplicate serialization, changed-payload conflict, pending-binding conflict, request order, and rollback without duplicate or partial SIMS identities. | Pass (2026-10-03): 7 selected, 7 passed against `127.0.0.1:55432/sead_staging`. |
| `V-5` | Additive migration and allocator checks | Apply `schema/sql/identity/011_resolve_batch_idempotency.sql` only after confirming `SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=127.0.0.1`, `SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=55432`, and `SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging`; inspect the new constraint/table and run `V-4`. | `PH1-AC-2`, `PH1-AC-3`, `PH1-AC-4`, `PH1-AC-5`, `PH1-AC-6` | Migration creates the batch-key constraint on the helper database; failed batches do not advance SIMS allocator state; configured identity values remain unique in the SIMS store. | Pass (2026-10-03): migrations `010` (rename) and `011` applied to the disposable DB; `resolve_batches` PK `(scope_name, run_id)` verified; failed batch leaves no allocator advance or replay record. |

The documented disposable check does not validate real reconciliation decisions, intended deployment settings, writer retirement, bootstrap coverage, or cutover. Those remain outside this phase's verification scope.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Capability contract proposal | `sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md` (NEW) | `T1.1` | Reviewed contract defines the approved operations, response version, error behavior, and required run-ID/fingerprint fields. |
| Capability API and explicit policy | `sead_authority_service/src/api/identity_router.py`, `src/identity/policy.py`, `config/identity_policy.yml` | `T1.2` | API returns the versioned capability data and rejects unsupported operations before writes. |
| Identity documentation | `sead_authority_service/src/identity/README.md` | `T1.3` | Endpoint, validated capability configuration, and disposable-test guidance match implementation. |
| Resolve idempotency migration | `sead_authority_service/schema/sql/identity/011_resolve_batch_idempotency.sql` (NEW) | `T2.1` | Additive schema stores scoped run key, fingerprint, and completed response with a uniqueness constraint. |
| Atomic batch orchestration | `sead_authority_service/src/api/identity_router.py`, `src/identity/service.py`, `src/identity/repository.py` | `T2.1`, `T2.2`, `T2.3` | Whole resolve batch commits or rolls back together and exact retries replay the saved result. |
| Regression and disposable tests | `sead_authority_service/tests/identity/test_capabilities.py` (NEW), `test_api.py`, `test_service.py`, `test_repository.py`, `test_service_integration.py` | `T1.2`, `T1.3`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2` | Unit and guarded database tests prove the criteria in the coverage table. |
| Phase 1 task plan | `docs/proposals/CHANGE_REQUEST_INGESTER/done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_1_TASK_PLAN.md` | — | This plan records the repository basis, checks, criteria mapping, and open contract decisions. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Define and enforce capability contract | Done | `T1.1` contract deliverable | Capability contract, operations config, `GET /identity/capabilities`, and resolve operation checks implemented and tested. |
| Area 2: Make resolve batches atomic and replayable | Done | Area 1; additive migration | `resolve_batch`, run-key advisory lock, fingerprint replay/conflict, and `011_resolve_batch_idempotency.sql` implemented; unit/API tests pass. Disposable DB-backed `V-4`/`V-5` evidence is Area 3. |
| Area 3: Verify approved operations in disposable database | Done | Areas 1 and 2; apply migration to helper database | Six batch idempotency integration tests added and passing against `127.0.0.1:55432/sead_staging`; migrations `010`/`011` applied; allocator rollback verified. No intended-deployment or cutover validation. |

## Definition Of Done

- [x] Every `PH1-AC-*` criterion has implementation and validation evidence mapped above.
- [x] The capability contract reports each configured entity's supported operations from validated configuration; operations beyond the disposable-verified set are recorded as configuration, not as deployment approval.
- [x] Unsupported entity types and operations fail before creating partial records.
- [x] Same-key/same-payload retries return the stored result; changed payloads conflict.
- [x] Resolve batch writes, target IDs, and replay results commit or roll back in one transaction.
- [x] Confirmed identities are reused; proposed bindings block a distinct run without duplicate allocation.
- [x] Approved site binding does not mint an identity; permitted site/sample allocation returns both the tracked UUID and target ID.
- [x] Focused unit, API, lint, migration, and helper-database checks pass.
- [x] Existing behavior, contracts, migrations, and documentation touched by the change are regression-tested and synchronized.
- [x] No intended-deployment, bootstrap, competing-writer retirement, or cutover check has been run as part of this phase.
- [x] The first supported batch contract requires a stable run ID; no legacy request path is provided.
- [x] Capability support derives from validated configuration, and no intended-deployment, bootstrap, or cutover enablement is performed in this phase; cutover gating and existing-data adoption are tracked in the [operational cutover and deployment proposal](../../CUTOVER_AND_DEPLOYMENT/SIMS_SEAD_TRUST_CONTRACT_ADOPTION_PROPOSAL.md).

## Risks And Open Questions

**Open decisions:** None blocking. Capability support and runtime enforcement both derive from the same validated `operations` configuration; there is no separate runtime-enablement toggle. The disposable-verified operations are `site` bind plus `site`/`sample` allocate; the remaining configured operations are forward-looking configuration, not deployment approval. Cutover gating and existing-data adoption are tracked in the [operational cutover and deployment proposal](../../CUTOVER_AND_DEPLOYMENT/SIMS_SEAD_TRUST_CONTRACT_ADOPTION_PROPOSAL.md). The required run ID is part of the initial contract, not a migration path.

**Implementation risk:** None outstanding for Phase 1. All Phase 1 work is committed on `sims-identity-allocation-phase-1` in both repositories. Phases 2 and 3 are complete; their task plans record implementation and validation evidence.
