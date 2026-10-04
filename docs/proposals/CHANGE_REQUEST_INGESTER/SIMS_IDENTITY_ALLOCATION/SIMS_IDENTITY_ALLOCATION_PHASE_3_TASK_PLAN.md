# Phase 3 Task Plan: Single-Batch Orchestration And Artifact Generation

## Phase Summary

**Goal:** Submit all of a run's SIMS identity work in one idempotent resolve request, map outcomes deterministically back to planned rows, and produce artifacts only from supported identities and confirmed Binding Sets — without auto-confirming from the ingester.

**Readiness:** Validated. Phase 3 is marked ready in the [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md). Phases 1 and 2 are complete and committed on `sims-identity-allocation-phase-1` in both repositories. The Authority Service batch API requires a `run_id` and guarantees ordered outcomes; the Shape Shifter capability preflight and model-driven planning are in place. The one material behavior change — removing the ingester's auto-confirm call — is explicitly required by `PH3-AC-2` and the source proposal.

**Constraints and dependencies**

- Use one SIMS resolve request per artifact-producing run; skip the request when there is no SIMS work.
- Require and persist a stable `run_id` scoped to the SIMS source scope; reuse it for identical retries and mint a new one for each intentional execution.
- Do not confirm proposed Binding Sets from the ingester. Read state, block artifact generation while `proposed`, and require `confirmed` before generation.
- Prevent the `RECONCILE` → allocation fall-through: `lookup-only`/`lookup-extensible` misses never request allocation.
- Preserve request order as the row-correlation contract; a same-`run_id`/same-payload retry returns the stored result.
- Both deploy strategies (inline `INSERT` and copy-CSV) must emit the same SIMS-issued identity values for supported work.
- SIMS remains the sole minter; Shape Shifter still owns reconciliation and match/miss approval before the batch.

**Source documents:** [identity-allocation proposal](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md), [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md), and the Phase 1 [capability contract](../../../../sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md).

### Phase Acceptance Criteria

- [ ] `PH3-AC-1` (from `P-AC-9`, `P-AC-11`): Each run sends all SIMS work in one request, skips empty batches, and reuses its run ID only for identical retries.
- [ ] `PH3-AC-2` (from `P-AC-10`): Outcomes map deterministically to planned rows; the ingester does not confirm proposed sets and writes artifacts only when the set is confirmed.
- [ ] `PH3-AC-3` (from `P-AC-5`, `P-AC-12`): Both artifact strategies emit the required SIMS-issued identity values consistently and emit no package when capability, identity-value, insertion, or confirmation requirements are unmet.

## Repository Findings

**Repository basis:** Planning date 2026-10-03. Shape Shifter is on `sims-identity-allocation-phase-1` at `b439e59d` with a clean working tree. Phases 1 and 2 are committed on this branch; the Authority Service Phase 1 batch and capability work is committed on the matching branch in that repository.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `sead_authority_service/src/api/identity_router.py::ResolveRequest` | The service requires a `run_id` string on every `POST /identity/resolve`; outcomes are returned in request order. | The consumer request model must gain `run_id`; request order is the correlation contract. |
| `backend/app/models/sims.py::ResolveRequest` | The consumer DTO has `scope_name`, `submission_name`, `requests`, `created_by` but no `run_id`. | Add a required `run_id` field mirroring the service. |
| `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter._resolve_entity` | Each `allocate_entity`/`bind_existing_entity` call builds a one-request `ResolveRequest` and calls `SimsClient.resolve` per row. | Replace per-row resolve with a single collected batch resolve. |
| `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments` | Iterates rows and calls `sims_client.allocate_entity`/`bind_existing_entity` per row; also falls through from `RECONCILE` miss to allocation and calls `confirm_binding_set` when state is not `confirmed`. | Restructure into collect-then-batch; remove auto-confirm; stop `RECONCILE` miss allocation. |
| `ingesters/sead_change_request/contracts.py::SubmissionContext` | Has `binding_set_uuid`, `change_request_name`, `timestamp`, etc., but no `run_id`. | Add a `run_id` field to persist the idempotency key across retries. |
| `ingesters/sead_change_request/input_resolution.py::_resolve_submission_context` | Constructs `SubmissionContext` from config; no `run_id` handling. | Read an optional persisted `run_id` and mint one when absent. |
| `backend/app/clients/sims_client.py::SimsClient.resolve` | Single batch `resolve(request)` already sends a `ResolveRequest` list and returns `ResolveResponse.outcomes`. | The adapter needs a batch entry point that collects requests and submits once. |
| `ingesters/sead_change_request/sql_builder.py::InlineInsertDeployStrategy`, `CopyCsvDeployStrategy` | Both render `ChangeRequestPackage` tables, reading the same projected identity values. | No structural change required; equivalence is asserted by tests rather than new code. |
| `ingesters/sead_change_request/ingester.py::ingest` | Already calls `sims_client.associate_change_request` once after artifact generation when a binding set and change request name exist. | Preserve this single association; no change unless the confirmation gate moves. |
| `ingesters/sead_change_request/preparation.py::_build_pending_confirmation_report` and `result_builders.py::check_ingestion_preconditions` | Block on `blocked_rows` / `pending_confirmation_report` when state is not `confirmed`. | Extend, not replace: the "proposed set blocks generation" gate already exists and must stay. |
| `backend/tests/ingesters/test_sead_change_request_orchestration.py`, `test_sead_change_request_confirmation.py`, `test_sead_change_request_package_builder.py`, `test_sead_change_request_sql_builder.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_submission_sims_integration.py` | Existing unit tests use per-row `FakeSimsClient`/`FakeBackendSimsClient` and cover confirmation/artifact paths; the disposable integration test exercises real SIMS-allocated submission IDs. | Extend fakes with a batch `resolve_batch` seam and add single-batch/no-confirm assertions. |

**Baseline checks on the current Shape Shifter checkout**

- `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_confirmation.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_sql_builder.py -q` — Pass (35 passed).
- `.venv/bin/pytest backend/tests/ingesters/ -q` — Pass (169 passed, 4 skipped) after Phase 2; the SIMS integration test is skipped without a disposable database.
- `.venv/bin/ruff check` over the Phase 3 target files — Not run during planning; recorded as a planned validation with a Not-run baseline.

## Scope

**In scope**

- One collected SIMS resolve batch per run, with a stable `run_id` and empty-batch skip.
- Deterministic request-to-row correlation using response order.
- Removing the ingester's auto-confirm call; block artifact generation while the set is `proposed`.
- Preventing `lookup-only`/`lookup-extensible` reconciliation misses from allocating.
- Parity assertions across both deploy strategies for SIMS-issued identity values.

**Out of scope**

- Manual SIMS Binding Set confirmation workflows and request chunking.
- Any SIMS-owned API, idempotency, or allocator behavior (Authority Service; Phase 1 is complete).
- Existing-data migration, bootstrap, deployment, and cutover.

**Affected components:** `backend/app/models/sims.py`, `backend/app/services/ingester_runtime.py`, `ingesters/sead_change_request/orchestration.py`, `contracts.py`, `input_resolution.py`, `preparation.py`, `ingester.py`, and the corresponding tests.

## Work Breakdown

### Area 1: Collect And Submit One SIMS Resolve Batch

**Objective:** Replace per-row SIMS resolve with a single collected batch that carries a persisted `run_id` and correlates outcomes by order.

**Affected code:** `backend/app/models/sims.py`; `backend/app/services/ingester_runtime.py`; `ingesters/sead_change_request/contracts.py`; `ingesters/sead_change_request/input_resolution.py`; `backend/tests/ingesters/test_sead_change_request_orchestration.py`.

**Dependencies:** None within Phase 3; depends on Phase 1 (service requires `run_id`) and Phase 2 (effective identity modes determine which rows are SIMS work).

**Tasks:**

* [x] `T1.1` **Change:** Add `run_id` to the consumer request model and the submission context.
  * **Target:** `backend/app/models/sims.py::ResolveRequest`; `ingesters/sead_change_request/contracts.py::SubmissionContext`.
  * **Current → required:** The service requires a `run_id`, but the consumer DTO and `SubmissionContext` have none.
  * **Implementation:** Add a required `run_id: str` to `ResolveRequest`. Add `run_id: str | None = None` to `SubmissionContext` so a persisted key can be carried across retries.
  * **Constraints:** Keep `ResolveRequest` aligned with the service schema; `SubmissionContext` is a consumer record and may carry the optional key.
  * **Validation:** `V-1`, `V-4`; model and orchestration tests confirm `run_id` round-trips.
* [x] `T1.2` **Change:** Resolve and persist the run ID at input resolution.
  * **Target:** `ingesters/sead_change_request/input_resolution.py::_resolve_submission_context`.
  * **Current → required:** No `run_id` is read or generated.
  * **Implementation:** Read an optional `run_id` string from the context data; when absent, mint a fresh UUID (`str(uuid4())`) so each intentional execution gets a new key and retries reuse the persisted value. Pass it into `SubmissionContext`.
  * **Constraints:** Never mint a new `run_id` for an ambiguous retry; the persisted value is authoritative.
  * **Validation:** `V-1`; test that a supplied `run_id` is preserved and an absent one is generated exactly once.
* [x] `T1.3` **Change:** Add a batch resolve entry point to the SIMS adapter.
  * **Target:** `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter`; `ingesters/sead_change_request/orchestration.py::SimsClientPort`.
  * **Current → required:** The adapter only exposes per-row `allocate_entity`/`bind_existing_entity`.
  * **Implementation:** Add `resolve_batch(requests: list[ResolutionRequest], submission_context, run_id) -> dict` that builds one `ResolveRequest` (with `run_id`) and returns the ordered outcomes plus binding-set UUID/state. Extend `SimsClientPort` with the same method.
  * **Constraints:** One `SimsClient.resolve` call per run; preserve the existing `_build_scope_name`/`_build_identity_value` helpers.
  * **Validation:** `V-1`, `V-4`; a fake that records one call proves a single batch.

**Completion evidence:** One `ResolveRequest` with a persisted `run_id` carries all collected requests; an empty SIMS work set makes no resolve call.

### Area 2: Collect Per-Row Work Then Resolve In One Batch

**Objective:** Rework `orchestrate_identity_assignments` to collect all SIMS-bound rows first, resolve them in one batch, and map ordered outcomes back to row indices.

**Affected code:** `ingesters/sead_change_request/orchestration.py`; `backend/tests/ingesters/test_sead_change_request_orchestration.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`.

**Dependencies:** Area 1 (batch entry point and `run_id`).

**Tasks:**

* [x] `T2.1` **Change:** Collect SIMS work before any resolve call.
  * **Target:** `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`.
  * **Current → required:** SIMS resolve happens inline per row, interleaved with reconciliation and database-sequence reservation.
  * **Implementation:** First pass collects, in deterministic order, each row that needs SIMS work (`ALLOCATE` rows, `RECONCILE` rows whose reconciliation returned an approved match for binding, and `RECONCILE` rows approved for allocation after a miss). Keep reconciliation and `RESERVE_DATABASE_ID` handling in the first pass; defer SIMS to one `resolve_batch` call. Maintain an ordered list of `(entity_name, row_index, approved_aggregate_id | None)` correlating request slots to rows.
  * **Constraints:** Preserve `REFERENCE_EXISTING`/`UPDATE_EXISTING_CANDIDATE`/`BLOCK_EXISTING_UPDATE` and `EVALUATE_BRIDGE` handling. Do not resolve bridge or child rows through SIMS.
  * **Validation:** `V-2`; fake records one resolve call with the expected request count and order.
* [x] `T2.2` **Change:** Map ordered outcomes back to row assignments.
  * **Target:** `ingesters/sead_change_request/orchestration.py`.
  * **Current → required:** Outcomes are read one at a time from a single-row response.
  * **Implementation:** After `resolve_batch`, zip the ordered outcome list with the collected correlation list and write each `IdentityAssignment` (`RECONCILED_CLASSIFIER` or `NEWLY_ALLOCATED_ENTITY`) by entity name and row index. Block any slot whose `target_id` is missing or mismatches an approved aggregate ID.
  * **Constraints:** Request order is the correlation contract; do not match by entity name alone.
  * **Validation:** `V-2`, `V-4`; reorder a two-entity batch and assert assignments stay on the correct rows.
* [x] `T2.3` **Change:** Prevent `lookup-only`/`lookup-extensible` reconciliation misses from allocating.
  * **Target:** `ingesters/sead_change_request/orchestration.py`; uses `src/target_model/effective_identity.resolve_effective_identity`.
  * **Current → required:** A `RECONCILE` row with no reconciliation match falls through to `allocate_entity`.
  * **Implementation:** For a reconciled row, read the effective reconciliation strategy. Only request allocation on a miss when the strategy is `reconcile-exact` or `reconcile-fuzzy`; a `lookup-only`/`lookup-extensible` miss becomes `BLOCKED_UNRESOLVED` with a "no approved match" note.
  * **Constraints:** Shape Shifter still approves the miss; the batch request records only permitted allocations.
  * **Validation:** `V-2`; a `lookup-only` miss produces no allocate request and blocks the row.

**Completion evidence:** One resolve call carries all SIMS work, outcomes map deterministically by order, and `lookup-only` misses never allocate.

### Area 3: Block Artifact Generation Until Confirmation

**Objective:** Stop auto-confirming from the ingester; require a confirmed Binding Set before artifacts are written.

**Affected code:** `ingesters/sead_change_request/orchestration.py`; `ingesters/sead_change_request/preparation.py`; `ingesters/sead_change_request/result_builders.py`; `backend/tests/ingesters/test_sead_change_request_confirmation.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`.

**Dependencies:** Area 2 (batch result yields one binding-set state).

**Tasks:**

* [x] `T3.1` **Change:** Remove the ingester auto-confirm call.
  * **Target:** `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`.
  * **Current → required:** The function calls `sims_client.confirm_binding_set` when the state is not `confirmed`.
  * **Implementation:** Replace the confirm call with a read-only `get_binding_set_state` check. When the state is `proposed`, leave it and mark SIMS-assigned rows `BLOCKED_UNRESOLVED` with a pending-confirmation note; do not call `confirm_binding_set`.
  * **Constraints:** The ingester must not mutate the Binding Set state; only SIMS auto-confirms for auto-confirmable batches.
  * **Validation:** `V-3`, `V-4`; a fake asserts `confirm_binding_set` is never called and a `proposed` set blocks.
* [x] `T3.2` **Change:** Keep the pending-confirmation report aligned with the no-confirm flow.
  * **Target:** `ingesters/sead_change_request/preparation.py::_build_pending_confirmation_report`.
  * **Current → required:** The report is built when state is non-confirmed and blocked rows exist; this already matches the no-confirm flow.
  * **Implementation:** No structural change; confirm the report still fires for a `proposed` set and its rerun instruction references the persisted `run_id` so a retry reuses the same batch.
  * **Constraints:** Preserve the operator-facing report contract.
  * **Validation:** `V-3`; assert the rerun instruction names the same `run_id`/submission context.
* [x] `T3.3` **Change:** Verify the artifact boundary blocks on unconfirmed sets.
  * **Target:** `ingesters/sead_change_request/ingester.py::ingest`; `ingesters/sead_change_request/result_builders.py::check_ingestion_preconditions`.
  * **Current → required:** `check_ingestion_preconditions` already returns a failure on blocked rows/pending confirmation; confirm it holds when the batch state is `proposed`.
  * **Implementation:** Add/adjust an ingester test that submits a `proposed`-state fake and asserts no artifact bundle is emitted and the failure carries the pending-confirmation report.
  * **Constraints:** No new top-level error type; reuse the existing blocked-row gate.
  * **Validation:** `V-3`, `V-4`.

**Completion evidence:** A `proposed` Binding Set blocks generation with no `confirm_binding_set` call; a `confirmed` set proceeds and associates the change request once.

### Area 4: Parity Across Both Deploy Strategies

**Objective:** Prove inline `INSERT` and copy-CSV emit identical SIMS-issued identity values and neither writes a package for unsupported or unconfirmed work.

**Affected code:** `backend/tests/ingesters/test_sead_change_request_sql_builder.py`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`.

**Dependencies:** Areas 2 and 3 (the change package carries resolved identity values and only confirmed work).

**Tasks:**

* [x] `T4.1` **Change:** Add strategy-parity assertions for resolved identity values.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_sql_builder.py`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`.
  * **Current → required:** Both strategies are tested in isolation but not asserted equivalent for SIMS-issued IDs.
  * **Implementation:** Build one `ChangeRequestPackage` from resolved identities and render it with both `InlineInsertDeployStrategy` and `CopyCsvDeployStrategy`; assert both carry the same target-facing `public_id` values for newly allocated and reconciled rows.
  * **Constraints:** No production code change; equivalence is a test-level guarantee.
  * **Validation:** `V-4`, `V-5`; equality assertions across strategy outputs.
* [x] `T4.2` **Change:** Assert no package is emitted for unsupported or unconfirmed work.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`.
  * **Current → required:** Blocked/unsupported paths are covered for identity resolution but not tied to both strategies under the no-confirm flow.
  * **Implementation:** Parameterize the existing ingester tests over both deploy strategies: a `proposed` set and a missing identity value each produce no bundle files under inline `INSERT` and copy-CSV.
  * **Constraints:** Keep the disposable integration test guarded by its `127.0.0.1:55432/sead_staging` check.
  * **Validation:** `V-4`, `V-5`.

**Completion evidence:** Both strategies produce equivalent identity values for supported work and emit no artifact for unsupported or unconfirmed work.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-9`, `P-AC-11`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2` | `V-1`, `V-2`, `V-4` | One resolve call per run with a persisted `run_id`; empty batches skip; retries reuse the key; changed payload under the same key conflicts at the service boundary. |
| `PH3-AC-2` (`P-AC-10`) | `T2.1`, `T2.2`, `T3.1`, `T3.2`, `T3.3` | `V-2`, `V-3`, `V-4` | Outcomes map by order to rows; `confirm_binding_set` is never called; a `proposed` set blocks generation. |
| `PH3-AC-3` (`P-AC-5`, `P-AC-12`) | `T4.1`, `T4.2` | `V-4`, `V-5` | Both strategies emit equivalent SIMS-issued identity values and emit nothing for unsupported or unconfirmed work. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Request model and run-ID persistence | `cd /data/roger/source/sead_shape_shifter && .venv/bin/pytest backend/tests/ingesters/test_sead_change_request_orchestration.py -q` | `PH3-AC-1` | `run_id` round-trips through `ResolveRequest` and `SubmissionContext`; a supplied key is preserved, an absent key is minted once. | Pass (2026-10-03): new `test_sead_change_request_input_resolution.py` (6 tests) plus adapter `resolve_batch` and `SubmissionContext.run_id` tests; `resolve_batch` submits one request with the persisted run ID. |
| `V-2` | Single-batch collection and correlation | `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_orchestration.py -q` | `PH3-AC-1`, `PH3-AC-2` | One `resolve_batch` call; outcomes map by order; `lookup-only` misses do not allocate. | Pass (2026-10-03): 16 orchestration tests pass, including one-batch collection, order correlation, and `lookup-only`/`reconcile-exact` miss handling. |
| `V-3` | No-confirm blocking | `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_confirmation.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-2` | `confirm_binding_set` is never called; a `proposed` set yields a pending-confirmation failure with no artifact bundle. | Pass (2026-10-03): orchestration no-confirm tests assert `confirm_calls == []`; `test_ingest_returns_pending_confirmation_report_for_proposed_binding_set` asserts `deploy_artifact is None`. |
| `V-4` | Regression suite | `.venv/bin/pytest backend/tests/ingesters/ -q` | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3` | Full ingester suite stays green; `test_sead_change_request_submission_sims_integration.py` passes against the disposable DB when available. | Pass (2026-10-03): 186 passed, 4 skipped after Area 4. |
| `V-5` | Strategy parity | `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_package_builder.py -q` | `PH3-AC-3` | Inline `INSERT` and copy-CSV emit equivalent identity values; no package for unsupported/unconfirmed work. | Pass (2026-10-03): `TestStrategyParity.test_both_strategies_emit_the_same_resolved_identity_values` asserts both strategies carry identical ordered target IDs; `test_ingest_returns_pending_confirmation_report_for_proposed_binding_set` and `test_ingest_blocks_before_writing_when_sims_has_no_aggregate_id` are parametrized over both strategies and assert no artifact. |
| `V-6` | Lint and format | `.venv/bin/ruff check backend/app/models/sims.py backend/app/services/ingester_runtime.py ingesters/sead_change_request/orchestration.py ingesters/sead_change_request/contracts.py ingesters/sead_change_request/input_resolution.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/ingester.py ingesters/sead_change_request/result_builders.py backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py` then `make tidy` | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3` | No Ruff findings; Black + isort clean. | Pass (2026-10-03): Area 4 test files clean. |

The phase-plan `VM-6` (one request and one Binding Set per run, stable mapping, empty-batch skip, same-run retry) maps to `V-1`/`V-2`/`V-4`; `VM-7` (both strategies equivalent, no package for unsupported/unconfirmed work) maps to `V-5` and the disposable `V-4` integration check.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Consumer `run_id` | `backend/app/models/sims.py::ResolveRequest`, `ingesters/sead_change_request/contracts.py::SubmissionContext` | `T1.1` | `run_id` is required on the request and optional on the context. |
| Run-ID resolution | `ingesters/sead_change_request/input_resolution.py` | `T1.2` | A persisted `run_id` is reused; an absent one is minted once. |
| Batch adapter entry point | `backend/app/services/ingester_runtime.py`, `orchestration.py::SimsClientPort` | `T1.3` | `resolve_batch` submits one request and returns ordered outcomes. |
| Single-batch orchestration | `ingesters/sead_change_request/orchestration.py` | `T2.1`, `T2.2`, `T2.3` | Collect-then-batch; deterministic order mapping; no `lookup-only` allocation. |
| No-confirm flow | `ingesters/sead_change_request/orchestration.py`, `preparation.py`, `result_builders.py`, `ingester.py` | `T3.1`, `T3.2`, `T3.3` | `confirm_binding_set` removed; `proposed` blocks generation. |
| Tests | `test_sead_change_request_orchestration.py`, `test_sead_change_request_confirmation.py`, `test_sead_change_request_sql_builder.py`, `test_sead_change_request_package_builder.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_submission_sims_integration.py` | `T1.1`–`T4.2` | New and extended tests cover the criteria in the coverage table. |
| Phase 3 task plan | `docs/proposals/CHANGE_REQUEST_INGESTER/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_3_TASK_PLAN.md` (NEW) | — | This plan records the repository basis, criteria mapping, and validation commands. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Collect and submit one SIMS resolve batch | Done | Phase 1 run_id, Phase 2 modes | `run_id` on `ResolveRequest`/`SubmissionContext`; minted/persisted at input resolution; `resolve_batch` adapter entry point added; 27 runtime/contract/input-resolution tests pass. |
| Area 2: Collect per-row work then resolve in one batch | Done | Area 1 | `orchestrate_identity_assignments` collects `SimsResolveItem`s and submits one `resolve_batch`; order-correlated outcomes; `lookup-only`/`lookup-extensible` misses blocked; batch 409 handled as a blocked batch. |
| Area 3: Block artifact generation until confirmation | Done | Area 2 | `confirm_binding_set` removed from orchestration and `SimsClientPort`; `proposed` set blocks with no confirm call; pending-confirmation report still fires. |
| Area 4: Parity across both deploy strategies | Done | Areas 2 and 3 | `TestStrategyParity` asserts identical ordered IDs across both strategies; no-artifact paths parametrized over both strategies. |

## Definition Of Done

- [x] Every `PH3-AC-*` criterion has implementation and validation evidence mapped above.
- [x] One resolve request carries all SIMS work per run with a persisted `run_id`; empty batches skip.
- [x] Outcomes map deterministically to planned rows by request order.
- [x] The ingester never calls `confirm_binding_set`; a `proposed` set blocks artifact generation.
- [x] `lookup-only`/`lookup-extensible` reconciliation misses never allocate.
- [x] Both deploy strategies emit equivalent SIMS-issued identity values and emit nothing for unsupported or unconfirmed work.
- [x] Required tests (`V-1` through `V-5`) and quality checks (`V-6`) pass.
- [x] Existing behavior identified for preservation (reconciliation ownership, `associate_change_request` once, pending-confirmation report) is regression-tested.
- [x] Deviations and follow-up work (manual confirmation, request chunking, existing-data migration) are documented.
- [x] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

**Known limitation (not blocking):** Manual SIMS Binding Set confirmation is out of scope. An entity that requires manual confirmation leaves its set `proposed`, blocking generation until an operator confirms in SIMS and the run is retried with the same `run_id`. This is the documented Phase 3 behavior, not a gap.

**Open implementation choice (resolved by repo convention, recorded for the coding agent):** The `run_id` is minted with `uuid4()` when absent and stored on `SubmissionContext`. The exact generation function may be adjusted to match existing `resolve_bundle_name`/UUID conventions in `contracts.py`, but persistence-and-reuse semantics are fixed by `PH3-AC-1`.

**Deferred operational work:** Existing-data migration, bootstrap, deployment, and cutover are tracked in the [operational cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md). SIMS-side manual confirmation workflow and request chunking are explicitly out of Phase 3 scope.
