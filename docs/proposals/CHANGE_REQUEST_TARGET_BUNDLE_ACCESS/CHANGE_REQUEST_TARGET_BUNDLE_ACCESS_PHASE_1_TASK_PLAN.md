# Phase 1 Task Plan: Allow Authorized Operators to Create Change Request Target Bundles

## Phase Summary

**Goal:** Allow an authenticated principal holding `project:execute` on an authorized saved project to create a Change Request target bundle without changing authorization for other ingester operations.

**Readiness: Blocked on dependency.** The output and ID-allocation decisions are recorded in the source proposal and phase plan. However, every task depends on the composed path from [Hand Normalized Tables To The Ingester In Memory](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), which is still proposed and not implemented. Start implementation only after that proposal's `P-AC-1`, `P-AC-8`, `P-AC-10`, `P-AC-11`, `P-AC-12`, and `P-AC-13` ship; `P-AC-13` blocks invalid project configuration before ingester work.

**Source documents:** [Change Request target-bundle proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) and [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md), Phase 1.

**Constraints and dependencies:** Apply the permission exception only to the composed path's dedicated project-only validation and ingest routes and helper; keep `project:execute` on both routes and the helper's project-resource guard, preserve `application:run_ingesters` on file routes for other ingesters, and keep Change Request file input retired; write each run to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root and fail on collision; limit target-database access in the bundle-creation flow to read-only verification queries; reuse SIMS IDs for stable source identities; reuse one operator run ID per submission attempt; leave quality assurance to the SEAD Release Cycle.

**Acceptance criteria**

- `PH1-AC-1` (from `P-AC-1`): An authenticated principal holding `project:execute` on an authorized saved project can validate and create a Change Request target bundle through the project-only routes without `application:run_ingesters`; the helper accepts the same authorized project without that application action. Unauthenticated callers and principals without `project:execute` are rejected.
- `PH1-AC-2` (from `P-AC-2`): Each run writes to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it. An existing destination fails before any file is written and no existing directory is deleted or replaced; bundle creation does not overwrite or remove unrelated files, and `output_path` returns the written bundle directory.
- `PH1-AC-3` (from `P-AC-3`): Bundle creation limits target-database access to read-only verification queries; it does not modify target rows or consume sequence values.
- `PH1-AC-4` (from `P-AC-4`): Other ingester operations retain their existing authorization requirement.
- `PH1-AC-5` (from `P-AC-5`): Repeating a bundle run for an identity based on the entity's configured business `keys` reuses its SIMS target ID. For one submission attempt the operator client reuses a single run ID across validation, ingestion, and retries, mints a new run ID when the submission identity changes or a bundle has been written, and that run ID appears in the response and the bundle manifest.

## Repository Findings

**Repository basis:** branch `ingester-filesystem-boundaries`, commit `0670d7d7`, planning date `2026-10-13`. Uncommitted proposal and phase-plan changes, plus target-model changes, are present and were treated as existing work; no implementation changes were made for this plan. Graphify did not return a useful target-bundle trace, so the findings below were verified against current source, tests, and package documentation.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/ingesters.py::ingester_operator_dependency`, `ingester_project_dependency`, `validate_data`, `ingest_data` | Both validation and ingestion routes use the `RUN_INGESTERS` dependency. For the `sead_change_request` key, `ingest_data` also requires `project:execute` on the top-level saved project. | The handoff retires Change Request file input and adds distinct project-only routes with a direct-call guard in their helper. Remove the application gate only from those project-only routes and helper; preserve their project checks and the file-route gates for other ingesters. |
| `backend/app/services/ingester_service.py::ingest` | The file-input service copies `request.output_folder` into ingester configuration and returns it as the output path. | The handoff retires that Change Request file-input call. Its project-only path selects a backend-owned output root; this phase adds per-run output below that root and returns the written bundle directory. |
| `ingesters/sead_change_request/contracts.py::resolve_bundle_name` | The bundle name is `<date>_DML_<datatype>_<identifier>` and is also the manifest `cr_name`, the SQL file names, and the paths inside generated `\copy` statements. | Add the timestamped run folder above the bundle directory so none of those paths change. |
| `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle` | The writer uses the supplied folder as its root and calls `shutil.rmtree` on an existing same-name bundle directory before writing. | Use an exclusive `mkdir` under the timestamped run folder and delete the `rmtree` branch; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks future review of retention. |
| `backend/app/core/config.py` | Managed directories are declared as settings and resolved under `APPLICATION_ROOT` in `resolve_paths()`, and each is created and protected there. The current code has no `INGEST_OUTPUT_DIR`. | The handoff adds `INGEST_OUTPUT_DIR` as a backend-owned root; `T1.2` reuses it and adds exclusive per-run output behavior. |
| `frontend/src/api/ingester.ts`, `frontend/src/types/ingester.ts::SubmissionContextInput`, `frontend/src/components/ingester/IngesterForm.vue::buildSubmissionContext` | The client currently uses file routes and sends no `run_id`, so every browser run mints a fresh UUID on the server. `IngestResponse.run_id` is already displayed. | The handoff first adds project-only client requests; `T1.6` adds the retry field, holds the attempt value in the store, and sends it on project validation, ingestion, and retry. |
| `backend/app/services/ingester_service.py::_create_config`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` | Caller database configuration can inject a PostgreSQL checker today. The checker can query target rows and calls `nextval` to reserve target IDs. | The handoff selects a backend-owned target connection for project-only runs before injecting this checker. This phase keeps its read-only queries and removes sequence consumption from bundle generation. |
| `ingesters/sead_change_request/ingester.py::_verify_provider_row` | Provider-row confirmation requires the injected `collision_checker` client and runs a read-only `row_exists` query against the fixed `data_provider` row before any SIMS request; it raises `SubmissionContextError` when no target connection is available. | Read-only target access is already required by the shipped provider-scope cutover. `T1.3` must preserve this verification while removing generation-time sequence consumption. |
| `ingesters/sead_change_request/planning.py::plan_table`; `ingesters/sead_change_request/orchestration.py`; `ingesters/sead_change_request/input_resolution.py` | SIMS-tracked entities cannot use database-sequence generation; non-tracked sequence entities can reserve IDs with `nextval`; absent run IDs may be generated for a new invocation. | `T0.2` decides the sequence-entity question: pre-resolved IDs or rejection, with no `nextval` during generation. `T0.3` fixes stable SIMS identity inputs and retry keys. |
| `backend/tests/api/test_ingesters.py::client` | The fixture overrides `ingester_operator_dependency` with an authenticated principal. A route test using only this fixture does not exercise the real action check. | Add or use a test setup that verifies project-only access without the application action, Change Request file-input rejection, and unchanged gates for other ingesters. |
| `backend/tests/api/test_ingesters.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py` | Existing API, ingester, and runtime tests cover the affected areas. The package README documents the focused ingester test command. | Extend these tests for access and database behavior. Add a focused artifact-writer test if needed. |

## Scope

**In scope**

- Narrow permission access for `sead_change_request` bundle creation.
- Use a managed output root with a UTC-timestamped run folder for each run; fail on collision and protect all existing files.
- Limit bundle creation's target-database access to read-only verification queries; no target-row writes and no sequence allocation.
- Preserve stable SIMS target IDs for repeated source identities and retries.
- Reuse one operator run ID per submission attempt so a browser retry replays the same batch.
- Regression coverage for retired Change Request file input and unchanged authorization for other ingesters.

**Out of scope**

- Per-source authorization or a new permission specific to Change Request bundle creation.
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

**Objective:** Implement the five phase acceptance criteria after Area 1 and the in-memory handoff are complete.

**Affected code:** `backend/app/api/v1/endpoints/ingesters.py`, `backend/app/services/ingester_service.py`, `backend/app/services/ingester_runtime.py`, `ingesters/sead_change_request/ingester.py`, `ingesters/sead_change_request/artifact_writer.py`, `ingesters/sead_change_request/contracts.py`, `frontend/src/types/ingester.ts`, `frontend/src/stores/ingester.ts`, and `frontend/src/components/ingester/IngesterForm.vue`.

**Dependencies:** `T0.1` (complete), `T0.2`, and `T0.3`.

**Tasks:**

* [ ] `T1.2` **Change:** Confine Change Request bundle output to the managed root and write each run to its own UTC-timestamped run folder.
  * **Target:** `backend/app/services/ingester_service.py::ingest` and `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`.
  * **Current → required:** The current file request supplies `output_folder`; the writer trusts that folder and recursively removes an existing same-name bundle. The handoff retires Change Request file input and supplies `INGEST_OUTPUT_DIR` for project-only runs, but not the exclusive per-run write rule.
  * **Implementation:** Reuse the handoff's `INGEST_OUTPUT_DIR` setting. Compose `<INGEST_OUTPUT_DIR>/<UTC timestamp>_<run_id>/<bundle_name>`, create it exclusively, and drop the `shutil.rmtree` branch. Keep output paths out of the project-only request and return the written bundle directory in `output_path`.
  * **Constraints:** Keep the bundle name and every path it generates unchanged, and keep other ingester output behavior unchanged.
  * **Validation:** `V-2`.
* [ ] `T1.3` **Change:** Limit the Change Request bundle path to read-only target-database verification.
  * **Target:** `backend/app/services/ingester_service.py::_create_config`, `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`, and `ingesters/sead_change_request/ingester.py`.
  * **Current → required:** The handoff selects the project-only target connection from backend settings and injects a checker. Its read-only `row_exists` query confirms the fixed `data_provider` row before SIMS requests, while its `nextval` path can reserve target sequence values. The relaxed rule keeps read-only queries and removes sequence consumption from generation.
  * **Implementation:** Apply the approved handling for non-SIMS sequence IDs from `T0.2`; do not call `nextval` or write target rows during bundle creation. Keep provider-row confirmation and target-row collision checks running as read-only queries.
  * **Constraints:** Preserve deployment-time sequence synchronization in emitted SQL. It runs when the release process applies the bundle and is distinct from generation-time allocation.
  * **Validation:** `V-3`.
* [ ] `T1.1` **Change:** Allow an authenticated principal holding `project:execute` to validate and create a Change Request bundle through the dedicated project-only routes and helper without `RUN_INGESTERS`.
  * **Target:** `backend/app/api/v1/endpoints/ingesters.py`, project-only `from-project/validate` and `from-project/ingest` routes, and the composition helper delivered by the handoff proposal.
  * **Current → required:** The handoff retires Change Request file input. The project-only routes and helper initially require `RUN_INGESTERS`; only those routes and helper receive the exception after the output and database rules in `T1.2` and `T1.3` apply. Shared file routes retain their gate for other ingesters.
  * **Implementation:** Remove the application check from the project-only routes and helper. Keep authentication and the authorized saved project on both routes, and keep the helper's `AuthorizedResource` action, type, active-state, and locator checks. Leave `ingester_operator_dependency` on `/{key}/validate` and `/{key}/ingest` for every key, including `sead_change_request`.
  * **Constraints:** Do not enable the exception before `T1.2` and `T1.3` are effective; preserve the handoff's `P-AC-11` trusted inputs, `P-AC-12` direct-call project guard, and `P-AC-13` mandatory project validation. Do not accept a caller source path or arbitrary config on those routes.
  * **Validation:** `V-1`, `V-4`.
* [ ] `T1.4` **Test:** Cover authenticated access, unauthenticated denial, the project-only route and helper exception, output safety, retired Change Request file input, and unchanged authorization for other file routes.
  * **Target:** `backend/tests/api/test_ingesters.py`, `backend/tests/authorization/test_service_access.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py`, and `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (`NEW` if no suitable existing writer test is found).
  * **Current → required:** The API test fixture overrides the action dependency; output tests exercise the ingester with a temporary output folder.
  * **Implementation:** Add route coverage for project-only validation and ingestion with and without `project:execute` and `RUN_INGESTERS`; verify both reject `source` and arbitrary config. Call the helper directly with valid and invalid `AuthorizedResource` inputs after the application check is removed; denied calls must do no project loading, normalization, database access, or file writing. Test that Change Request file input remains rejected through route, service, and ingester calls and that other file routes remain gated. Add file tests proving timestamped output, fail-on-collision behavior, and unchanged files.
  * **Constraints:** Use test doubles; do not connect to a real database or external service.
  * **Validation:** `V-1`, `V-2`, and `V-4`.
* [ ] `T1.5` **Test:** Verify SIMS target IDs remain stable across retries and repeated runs for the same configured business keys.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, and relevant unit tests for `ingesters/sead_change_request/input_resolution.py` and `orchestration.py`.
  * **Current → required:** The SIMS service can replay an identical batch for the same scoped run ID and reuse a confirmed binding for a stable source identity. Tests must show the ingester supplies those stable identity and retry values.
  * **Implementation:** Test same-run retry with the persisted run ID and same payload, then test a later run with the same configured business keys and changed non-key data. Verify that the resolved SIMS target ID is unchanged.
  * **Constraints:** Do not make live SIMS requests.
  * **Validation:** `V-5`.
* [ ] `T1.6` **Change:** Reuse one operator run ID per submission attempt on the project-only Change Request requests.
  * **Target:** `frontend/src/types/ingester.ts::SubmissionContextInput`, `frontend/src/stores/ingester.ts`, `frontend/src/components/ingester/IngesterForm.vue::buildSubmissionContext`, and `ingesters/sead_change_request/contracts.py::PendingConfirmationReport.create`.
  * **Current → required:** The submission context type has no `run_id` and `buildSubmissionContext` never sends one, so each browser run mints a fresh server-side UUID and a retry cannot replay the earlier batch.
  * **Implementation:** Preserve the handoff's project-only client requests without `source`. Add optional `run_id` to the submission context type, hold the current attempt's value in the ingester store, and send it on project validation, ingestion, and retry. Mint a new value when the submission identity changes (submission name, project, timestamp, datatype, identifier) or after a bundle has been written. Name the run ID in the pending-confirmation rerun instruction.
  * **Constraints:** Do not mint a run ID per request, and do not derive it from the output run folder name. Keep the server's fallback for callers that supply none. Do not send a caller path in a project-only request.
  * **Validation:** `V-6`.

**Completion evidence:** All five phase criteria pass the validations below, with the ID-allocation decisions recorded in the source documents.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.4` | `V-1` | A project executor without the application action can validate and create a bundle through project-only routes and helper; a source path, unauthenticated caller, or invalid project authorization is denied without side effects. |
| `PH1-AC-2` (from `P-AC-2`) | `T0.1`, `T1.2`, `T1.4` | `V-1`, `V-2` | Each run uses a UTC-timestamped run folder under `INGEST_OUTPUT_DIR`; collision fails without changing files; no directory is deleted. |
| `PH1-AC-3` (from `P-AC-3`) | `T0.2`, `T1.3`, `T1.4` | `V-3` | Bundle generation runs only read-only verification queries: no target-row write and no sequence allocation. |
| `PH1-AC-4` (from `P-AC-4`) | `T1.1`, `T1.4` | `V-4` | Change Request file input remains unavailable; file validation and ingestion for other keys continue to require `RUN_INGESTERS`. |
| `PH1-AC-5` (from `P-AC-5`) | `T0.3`, `T1.5`, `T1.6` | `V-5`, `V-6` | Retries and later runs for the same stable SIMS source identity reuse the assigned target ID, and the client reuses one run ID per attempt. |

## Validation And Testing

No baseline tests were run: the phase is blocked, and no implementation was changed.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-0.1` | Review the output-folder decision | Confirm the source proposal and phase plan require per-run UTC-timestamped folders and fail-on-collision; issue #550 tracks future review | `T0.1` | The output behavior is unambiguous and matches the user decision | Passed: recorded in source documents |
| `V-0.2` | Review non-SIMS sequence handling | Confirm the source proposal and phase plan prohibit generation-time sequence allocation and require pre-resolved IDs or reject unsupported inputs | `T0.2` | The no-connection rule and supported entity configurations are compatible | Passed: user decision recorded in source documents |
| `V-0.3` | Review SIMS identity and retry contract | Confirm configured business `keys` define source identity and retries preserve the run ID and payload | `T0.3` | Repeated runs do not allocate a new target ID for the same configured keys | Passed: user decision recorded in source documents |
| `V-1` | API and service access checks in `backend/tests/api/test_ingesters.py` and `backend/tests/authorization/test_service_access.py` | `uv run pytest backend/tests/api/test_ingesters.py backend/tests/authorization/test_service_access.py -v` | `PH1-AC-1` | Project executor without `RUN_INGESTERS` can use project-only routes and helper; missing project grant, unauthenticated calls, `source`, arbitrary config, and invalid direct helper authorizations are rejected before side effects | Not run: blocked |
| `V-2` | Bundle output checks in `backend/tests/ingesters/test_sead_change_request_ingester.py` and `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (`NEW` if needed) | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_artifact_writer.py -q` | `PH1-AC-2` | Each run uses a timestamped run folder under `INGEST_OUTPUT_DIR`; an existing destination fails with nothing written or deleted; unrelated files remain unchanged | Not run: blocked |
| `V-3` | Runtime checks in `backend/tests/ingesters/test_sead_change_request_runtime.py` and `backend/tests/ingesters/test_sead_change_request_ingester.py` | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-3` | Test doubles confirm only read-only verification queries run: no target-table write and no `nextval` call | Not run: blocked |
| `V-4` | Authorization regression in `backend/tests/api/test_ingesters.py` | `uv run pytest backend/tests/api/test_ingesters.py -v` | `PH1-AC-4` | Change Request file input remains unavailable; other file validation and ingestion remain gated | Not run: blocked |
| `V-5` | SIMS ID idempotency checks in `backend/tests/ingesters/test_sead_change_request_runtime.py` and `backend/tests/ingesters/test_sead_change_request_ingester.py` | `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-5` | Same-identity reruns and same-run retries reuse the existing SIMS target ID | Not run: blocked |
| `V-6` | Operator run-ID checks in `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` and `backend/tests/ingesters/test_sead_change_request_contracts.py` | `cd frontend && npx vitest run src/components/ingester/__tests__/IngesterForm.test.ts` and `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_contracts.py -q` | `PH1-AC-5` | Project-only validate, ingest, and retry requests send the same `run_id` without `source`; changing the submission identity or completing a run sends a new one; the rerun instruction names it | Not run: blocked |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Decision record | Source proposal and phase plan | `T0.1`–`T0.3` | The output rule is recorded and both ID-allocation questions are resolved. |
| Authorization and output changes | Existing API, service, runtime, and ingester files listed in Area 2 | `T1.1`–`T1.3` | The access, output, and read-only target-database criteria pass. |
| Regression coverage | Existing tests listed in Area 2; artifact-writer test marked `NEW` if needed | `T1.4`, `T1.5`, `T1.6` | `V-1`–`V-6` pass. |
| Task plan | `docs/proposals/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md` | This plan | Approved decisions, work, and validation are traceable. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Record output decision and resolve ID-allocation behavior | Done | None | `T0.1`, `T0.2`, and `T0.3` are recorded in the source documents. |
| Area 2: Implement approved bundle access and side-effect rules | Blocked | Area 1 and in-memory handoff `P-AC-1`, `P-AC-8`, `P-AC-10`, `P-AC-11`, `P-AC-12`, `P-AC-13` | Begin after the project-only routes, client requests, trusted inputs, service authorization guard, and mandatory project validation ship; preview mode is out of scope. |

## Definition Of Done

- [x] The managed-root, UTC-timestamped run folder, and fail-on-collision behavior is approved and documented.
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
