# Phase 1 Task Plan: Allow Operators to Create Change Request Target Bundles

## Phase Summary

**Goal:** Allow any authenticated operator to create a Change Request target bundle without changing authorization for other ingester operations.

**Readiness: Validated.** The output and ID-allocation decisions are recorded in the source proposal and phase plan. The task plan has repository-verified targets and executable validation methods and is ready for implementation handoff.

**Source documents:** [Change Request target-bundle proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) and [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md), Phase 1.

**Constraints and dependencies:** Keep the permission exception limited to `sead_change_request` bundle creation; preserve the `application:run_ingesters` requirement for validation and other ingesters; write each run to its own UTC-timestamped managed folder and fail on collision; limit target-database access in the bundle-creation flow to read-only verification queries; reuse SIMS IDs for stable source identities; leave quality assurance to the SEAD Release Cycle.

**Acceptance criteria**

- `PH1-AC-1` (from `P-AC-1`): Any authenticated operator can create a Change Request target bundle without `application:run_ingesters`; unauthenticated callers cannot.
- `PH1-AC-2` (from `P-AC-2`): Each run writes to a UTC-timestamped folder under its managed output location. A destination collision fails without modifying existing files, and bundle creation does not overwrite or remove unrelated files.
- `PH1-AC-3` (from `P-AC-3`): Bundle creation limits target-database access to read-only verification queries; it does not modify target rows or consume sequence values.
- `PH1-AC-4` (from `P-AC-4`): Other ingester operations retain their existing authorization requirement.
- `PH1-AC-5` (from `P-AC-5`): Repeating a bundle run for an identity based on the entity's configured business `keys` reuses its SIMS target ID; retrying an allocation batch uses the same run ID and payload.

## Repository Findings

**Repository basis:** branch `ingester-filesystem-boundaries`, commit `0670d7d7`, planning date `2026-10-13`. Uncommitted proposal and phase-plan changes, plus target-model changes, are present and were treated as existing work; no implementation changes were made for this plan. Graphify did not return a useful target-bundle trace, so the findings below were verified against current source, tests, and package documentation.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/ingesters.py::ingester_operator_dependency`, `validate_data`, `ingest_data` | Both validation and ingestion routes use the `RUN_INGESTERS` dependency. | Apply any permission exception only to Change Request bundle ingestion; keep validation and other ingester keys protected. |
| `backend/app/services/ingester_service.py::ingest` | The service copies `request.output_folder` into ingester configuration and returns it as the output path. | The Change Request path must use the decided managed output location without changing other ingester output behavior. |
| `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle` | The writer uses the supplied folder as its root and calls `shutil.rmtree` on an existing same-name bundle directory before writing. | Use a UTC-timestamped folder per run and fail on any unexpected destination collision; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks future review of this naming choice. |
| `backend/app/services/ingester_service.py::_create_config`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` | Database configuration can inject a PostgreSQL checker. The checker can query target rows and calls `nextval` to reserve target IDs. | The relaxed rule allows the checker's read-only row queries but still prohibits its `nextval` path. Keep target-row verification and separate any sequence-reservation use from bundle generation. |
| `ingesters/sead_change_request/ingester.py::_verify_provider_row` | Provider-row confirmation requires the injected `collision_checker` client and runs a read-only `row_exists` query against the fixed `data_provider` row before any SIMS request; it raises `SubmissionContextError` when no target connection is available. | Read-only target access is already required by the shipped provider-scope cutover. `T1.3` must preserve this verification while removing generation-time sequence consumption. |
| `ingesters/sead_change_request/planning.py::plan_table`; `ingesters/sead_change_request/orchestration.py`; `ingesters/sead_change_request/input_resolution.py` | SIMS-tracked entities cannot use database-sequence generation; non-tracked sequence entities can reserve IDs with `nextval`; absent run IDs may be generated for a new invocation. | `T0.2` decides the sequence-entity question: pre-resolved IDs or rejection, with no `nextval` during generation. `T0.3` fixes stable SIMS identity inputs and retry keys. |
| `backend/tests/api/test_ingesters.py::client` | The fixture overrides `ingester_operator_dependency` with an authenticated principal. A route test using only this fixture does not exercise the real action check. | Add or use a test setup that verifies the actual permission behavior, including that validation and other ingesters remain gated. |
| `backend/tests/api/test_ingesters.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py` | Existing API, ingester, and runtime tests cover the affected areas. The package README documents the focused ingester test command. | Extend these tests for access and database behavior. Add a focused artifact-writer test if needed. |

## Scope

**In scope**

- Narrow permission access for `sead_change_request` bundle creation.
- Use a managed output location with a UTC-timestamped folder for each run; fail on collision and protect all existing files.
- Limit bundle creation's target-database access to read-only verification queries; no target-row writes and no sequence allocation.
- Preserve stable SIMS target IDs for repeated source identities and retries.
- Regression coverage for validation and other ingester authorization.

**Out of scope**

- Per-source or per-project authorization for this operation.
- Authorization changes for other ingesters.
- Applying the generated SQL or performing SEAD Release Cycle review.
- A preview or dry-run mode; any later preview must not allocate IDs, advance sequences, or write bundle files.

## Work Breakdown

### Area 1: Record output decision and resolve ID-allocation behavior

**Objective:** Record the approved output rule and define an idempotent ID-allocation contract that satisfies the read-only target-database rule before implementation.

**Affected code:** None. Decisions must be reflected in the source proposal and phase plan before this task plan can become an implementation handoff.

**Dependencies:** None.

**Tasks:**

* [x] `T0.1` **Record:** Use a UTC-timestamped folder for each run and fail without modification if the destination already exists.
  * **Target:** Decision recorded in the source proposal and phase plan.
  * **Decision:** Preserve prior bundles rather than replacing them. Issue [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks future review of folder naming and retention.
  * **Validation:** `V-0.1`.
* [x] `T0.2` **Decide:** Do not allocate database-sequence IDs during bundle generation.
  * **Target:** Decision recorded in the source proposal and phase plan.
  * **Decision:** Non-SIMS-tracked entities requiring database-sequence IDs must have IDs pre-resolved before bundle generation or be rejected as unsupported. Do not introduce a local sequence allocator without a uniqueness and coordination design.
  * **Constraints:** Do not call `nextval` or otherwise consume sequence values during bundle creation; read-only verification queries remain allowed. Keep generated deployment-time sequence synchronization distinct from generation-time ID allocation.
  * **Validation:** `V-0.2`.
* [x] `T0.3` **Define:** Use configured business `keys` as stable SIMS source identity and preserve the run ID and payload when retrying an allocation batch.
  * **Target:** Decision recorded in the source proposal and phase plan.
  * **Current → required:** SIMS batch replay requires the same scoped `run_id` and payload. The service can reuse a confirmed binding for a stable source identity, but the ingester can generate a new run ID when one is absent and currently builds its primary signal from row fields.
  * **Decision:** Use the entity's configured business `keys`, not all row fields, to construct the SIMS source identity. Reuse the persisted run ID and identical payload for retries; later runs for the same configured keys must resolve to the existing target ID.
  * **Constraints:** Do not use the timestamped output-folder name as an identity or retry key.
  * **Validation:** `V-0.3`.

### Area 2: Implement the approved bundle access and side-effect rules

**Objective:** Implement the four phase acceptance criteria after Area 1 is complete.

**Affected code:** `backend/app/api/v1/endpoints/ingesters.py`, `backend/app/services/ingester_service.py`, `backend/app/services/ingester_runtime.py`, `ingesters/sead_change_request/ingester.py`, and `ingesters/sead_change_request/artifact_writer.py`.

**Dependencies:** `T0.1` (complete), `T0.2`, and `T0.3`.

**Tasks:**

* [ ] `T1.1` **Change:** Allow an authenticated operator to ingest with key `sead_change_request` without `RUN_INGESTERS`.
  * **Target:** `backend/app/api/v1/endpoints/ingesters.py::ingest_data` and `ingester_operator_dependency`.
  * **Current → required:** The shared dependency gates all ingester ingestion; only Change Request target-bundle creation is to receive the exception.
  * **Implementation:** Apply the exception only to that ingestion key. Keep the gate on validation and every other ingester key.
  * **Constraints:** Preserve authentication; do not make the route anonymous.
  * **Validation:** `V-1`, `V-4`.
* [ ] `T1.2` **Change:** Confine Change Request bundle output to its managed location and write each run to a UTC-timestamped folder.
  * **Target:** `backend/app/services/ingester_service.py::ingest` and `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`.
  * **Current → required:** The request supplies `output_folder`; the writer trusts that folder and recursively removes an existing same-name bundle.
  * **Implementation:** Compose a unique run folder under the managed location. If it already exists, fail before deleting or changing any files.
  * **Constraints:** Keep other ingester output behavior unchanged.
  * **Validation:** `V-2`.
* [ ] `T1.3` **Change:** Limit the Change Request bundle path to read-only target-database verification.
  * **Target:** `backend/app/services/ingester_service.py::_create_config`, `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`, and `ingesters/sead_change_request/ingester.py`.
  * **Current → required:** Database configuration injects a checker whose read-only `row_exists` query confirms the fixed `data_provider` row before SIMS requests, and whose `nextval` path reserves target sequence values. The relaxed rule keeps the read-only queries and removes sequence consumption from generation.
  * **Implementation:** Apply the approved handling for non-SIMS sequence IDs from `T0.2`; do not call `nextval` or write target rows during bundle creation. Keep provider-row confirmation and target-row collision checks running as read-only queries.
  * **Constraints:** Preserve deployment-time sequence synchronization in emitted SQL. It runs when the release process applies the bundle and is distinct from generation-time allocation.
  * **Validation:** `V-3`.
* [ ] `T1.4` **Test:** Cover authenticated access, unauthenticated denial, the narrow key exception, output safety, and unchanged authorization for other ingesters.
  * **Target:** `backend/tests/api/test_ingesters.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py`, and `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (`NEW` if no suitable existing writer test is found).
  * **Current → required:** The API test fixture overrides the action dependency; output tests exercise the ingester with a temporary output folder.
  * **Implementation:** Add route coverage that exercises the actual authorization behavior and file tests proving timestamped output, fail-on-collision behavior, and unchanged files.
  * **Constraints:** Use test doubles; do not connect to a real database or external service.
  * **Validation:** `V-1`, `V-2`, and `V-4`.
* [ ] `T1.5` **Test:** Verify SIMS target IDs remain stable across retries and repeated runs for the same configured business keys.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, and relevant unit tests for `ingesters/sead_change_request/input_resolution.py` and `orchestration.py`.
  * **Current → required:** The SIMS service can replay an identical batch for the same scoped run ID and reuse a confirmed binding for a stable source identity. Tests must show the ingester supplies those stable identity and retry values.
  * **Implementation:** Test same-run retry with the persisted run ID and same payload, then test a later run with the same configured business keys and changed non-key data. Verify that the resolved SIMS target ID is unchanged.
  * **Constraints:** Do not make live SIMS requests.
  * **Validation:** `V-5`.

**Completion evidence:** All five phase criteria pass the validations below, with the ID-allocation decisions recorded in the source documents.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.4` | `V-1` | An authenticated operator without the action can create the bundle; an unauthenticated caller cannot. |
| `PH1-AC-2` (from `P-AC-2`) | `T0.1`, `T1.2`, `T1.4` | `V-1`, `V-2` | Each run uses a UTC-timestamped managed folder; collision fails without changing files. |
| `PH1-AC-3` (from `P-AC-3`) | `T0.2`, `T1.3`, `T1.4` | `V-3` | Bundle generation runs only read-only verification queries: no target-row write and no sequence allocation. |
| `PH1-AC-4` (from `P-AC-4`) | `T1.1`, `T1.4` | `V-4` | Validation and other ingester keys continue to require `RUN_INGESTERS`. |
| `PH1-AC-5` (from `P-AC-5`) | `T0.3`, `T1.5` | `V-5` | Retries and later runs for the same stable SIMS source identity reuse the assigned target ID. |

## Validation And Testing

No baseline tests were run: the phase is blocked, and no implementation was changed.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-0.1` | Review the output-folder decision | Confirm the source proposal and phase plan require per-run UTC-timestamped folders and fail-on-collision; issue #550 tracks future review | `T0.1` | The output behavior is unambiguous and matches the user decision | Passed: recorded in source documents |
| `V-0.2` | Review non-SIMS sequence handling | Confirm the source proposal and phase plan prohibit generation-time sequence allocation and require pre-resolved IDs or reject unsupported inputs | `T0.2` | The no-connection rule and supported entity configurations are compatible | Passed: user decision recorded in source documents |
| `V-0.3` | Review SIMS identity and retry contract | Confirm configured business `keys` define source identity and retries preserve the run ID and payload | `T0.3` | Repeated runs do not allocate a new target ID for the same configured keys | Passed: user decision recorded in source documents |
| `V-1` | API access checks in `backend/tests/api/test_ingesters.py` | `uv run pytest backend/tests/api/test_ingesters.py -v` | `PH1-AC-1` | Authenticated operator succeeds; unauthenticated caller is denied | Not run: blocked |
| `V-2` | Bundle output checks in `backend/tests/ingesters/test_sead_change_request_ingester.py` and `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (`NEW` if needed) | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_artifact_writer.py -q` | `PH1-AC-2` | Each run uses a timestamped managed folder; an existing destination fails unchanged; unrelated files remain unchanged | Not run: blocked |
| `V-3` | Runtime checks in `backend/tests/ingesters/test_sead_change_request_runtime.py` and `backend/tests/ingesters/test_sead_change_request_ingester.py` | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-3` | Test doubles confirm only read-only verification queries run: no target-table write and no `nextval` call | Not run: blocked |
| `V-4` | Authorization regression in `backend/tests/api/test_ingesters.py` | `uv run pytest backend/tests/api/test_ingesters.py -v` | `PH1-AC-4` | Validation and non-Change-Request ingestion remain gated | Not run: blocked |
| `V-5` | SIMS ID idempotency checks in `backend/tests/ingesters/test_sead_change_request_runtime.py` and `backend/tests/ingesters/test_sead_change_request_ingester.py` | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-5` | Same-identity reruns and same-run retries reuse the existing SIMS target ID | Not run: blocked |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Decision record | Source proposal and phase plan | `T0.1`–`T0.3` | The output rule is recorded and both ID-allocation questions are resolved. |
| Authorization and output changes | Existing API, service, runtime, and ingester files listed in Area 2 | `T1.1`–`T1.3` | The access, output, and read-only target-database criteria pass. |
| Regression coverage | Existing tests listed in Area 2; artifact-writer test marked `NEW` if needed | `T1.4`, `T1.5` | `V-1`–`V-5` pass. |
| Task plan | `docs/proposals/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md` | This plan | Approved decisions, work, and validation are traceable. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Record output decision and resolve ID-allocation behavior | Done | None | `T0.1`, `T0.2`, and `T0.3` are recorded in the source documents. |
| Area 2: Implement approved bundle access and side-effect rules | Ready | Area 1 | Implementation can begin; preview mode is out of scope. |

## Definition Of Done

- [x] The timestamped-folder and fail-on-collision behavior is approved and documented.
- [x] Non-SIMS sequence IDs are not allocated during generation; unsupported inputs require pre-resolved IDs or are rejected.
- [ ] Stable SIMS source identity and retry-key behavior is specified and tested.
- [ ] Every phase acceptance criterion has implementation and validation evidence.
- [ ] Other ingester authorization behavior is regression-tested.
- [ ] Bundle output cannot overwrite or remove unrelated files.
- [ ] Generated deployment SQL retains the required sequence synchronization behavior.
- [ ] Required tests pass using test doubles, without real database or external-service access.
- [ ] The proposal, phase plan, implementation, and tests describe the same behavior.
- [ ] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

No blocking questions remain. Preview or dry-run behavior is outside this phase; if added later, it must not allocate SIMS IDs, consume PostgreSQL sequence values, or write bundle files.
