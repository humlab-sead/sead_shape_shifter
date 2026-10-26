# Change Request Target Bundle Access — Phase 2 Task Plan

## Phase Summary

**Goal:** Make project-only Change Request validation and ingestion read-only against the target database, and keep SIMS identity and the operator's run ID stable across retries.

**Readiness:** Validated. [Phase 2](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md#phase-2-remove-target-sequence-allocation-and-stabilize-retries) is ready after Phase 1; the [Phase 1 task plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md) records its output safeguards complete, and the relevant current tests pass. No implementation decision remains open.

**Sources:** [Proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) (`P-AC-3`, `P-AC-5`) and [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) (`VM-2.1`, `VM-2.2`). Phase 1's exclusive run folder and returned `output_path` are prerequisites. Keep `application:run_ingesters` and `project:execute` on both project-only routes and the direct helper until Phase 3. Preserve the authorized project's provider-schema scope, backend-selected target connection, strict project request, retired file input, and deployment-time sequence synchronization.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-3`): Project-only validation and ingestion use only read-only target verification. Neither writes target rows nor consumes sequence values; unresolved database-sequence IDs fail before allocation.
2. [x] `PH2-AC-2` (from `P-AC-5`): Within the saved provider-schema scope, later runs with the same declared business keys reuse assigned SIMS target IDs; invalid tracked keys fail before identity resolution.
3. [x] `PH2-AC-3` (from `P-AC-5`): The client uses one run ID for validation, ingestion, and retry of an attempt, changes it when submission identity changes or a bundle succeeds, and names the effective ID in pending-confirmation guidance.

## Repository Findings

**Repository basis:** `change-request-target-bundle-access` at `7db7eb86`, planning date 2026-10-20. Uncommitted changes under `TARGET_MODEL_GUIDED_ENTITY_CREATION` were left untouched and did not inform this plan. Graphify was used for navigation; the findings below were checked in source and tests. The proposal's Current Behavior predates completed Phase 1 output work; plan from current source.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `ingesters/sead_change_request/planning.py::plan_table`; `orchestration.py::orchestrate_identity_assignments`; `preparation.py::prepare_change_request` | A missing public ID with `database_sequence` becomes `RESERVE_DATABASE_ID`; orchestration calls `target_id_allocator.reserve_target_id` when one is supplied. Both validation and ingestion share this preparation. Pre-resolved row assignments are skipped. | Block unresolved sequence IDs in the shared path, including when an allocator is present. Preserve pre-resolved IDs and deployment-time child IDs. |
| `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._prepare_resolved_inputs`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` | The ingester passes `target_id_allocator` or `collision_checker` to preparation. The checker has read-only `target_id_exists` and `row_exists`, plus a `reserve_target_id` method that executes `SELECT nextval(...)`. | Remove the allocation path and its runtime method; retain the read checks used for provider confirmation and target collisions. |
| `ingesters/sead_change_request/sql_builder.py::_add_sequence_synchronization`; `inline_staging_sql.py` | Generated deploy SQL synchronizes target sequences after inserts; inline staging can allocate child IDs when that SQL is later executed. | Keep generated SQL behavior. The read-only rule applies while validating or creating the bundle, not when the deployment artifact is executed elsewhere. |
| `backend/app/services/project_data_provider_service.py::build_trusted_context`; `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter` | The backend obtains registered scope and ordered project `safe_keys`; the SIMS adapter serializes declared keys using `business_id_for_row`. On serialization error it currently returns the shared entity name. | Preserve the trusted scope and serialization; remove the shared-value fallback for declared keys. |
| `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._validate_business_keys`; `src/business_keys.py::business_key_errors` | Project table keys are checked before provider lookup and SIMS work for missing declarations, columns, values, and duplicates. | Keep structured validation failures; add a direct adapter guard and later-run reuse tests. |
| `backend/app/models/ingester.py::ProjectSubmissionOptions`; `frontend/src/stores/ingester.ts`; `frontend/src/components/ingester/IngesterForm.vue::buildProjectRequest` | The strict request accepts optional `run_id`, but the form omits it and the Pinia store retains no attempt ID. The server mints a fallback for absent IDs. | Generate and retain an operator run ID in the ingester store; keep server fallback for other API callers. |
| `ingesters/sead_change_request/contracts.py::PendingConfirmationReport.create`; `frontend/src/components/ingester/IngesterForm.vue` | Pending reports have rerun text but omit the run ID. The form renders report guidance for validation and ingestion. | Put the effective run ID in report guidance and display it in both pending states. |

## Scope

**In scope:** Shared Change Request identity preparation, its target database and SIMS adapters, pending-confirmation text, the project-only frontend attempt state, focused tests, and the Change Request package README.

**Out of scope:** Changing route or helper authorization, adding source/output/database fields, changing SIMS scope or business-key encoding, changing the completed run-folder layout, executing deploy SQL, changing other ingesters, and reopening file input.

## Work Breakdown

### Area 1: Stop target sequence allocation during preparation

**Objective:** Both table operations can read the target for verification but cannot consume a target sequence value.

**Affected code:** `ingesters/sead_change_request/ingester.py::_prepare_resolved_inputs`; `preparation.py::prepare_change_request`; `orchestration.py::orchestrate_identity_assignments`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`.

**Dependencies:** Accepted Phase 1 output behavior.

**Tasks:**

* [x] `T2.1` **Change:** Convert unresolved `RESERVE_DATABASE_ID` rows to blocked identity assignments without calling an allocator.
  * **Target:** `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`, `TargetIdAllocatorPort`; `preparation.py::prepare_change_request`; `ingester.py::SeadChangeRequestIngester._prepare_resolved_inputs`.
  * **Current → required:** Shared preparation can reserve an ID from a target sequence. A missing non-SIMS database-sequence public ID must produce an explicit unsupported/unresolved diagnostic in both validation and ingestion, with no SIMS or target allocator call for that row.
  * **Implementation:** Remove the allocator argument and port from the shared call chain. Preserve the `RESERVE_DATABASE_ID` planning action so missing IDs are recognized. Keep fallback/pre-resolved assignments and deployment-time staged child IDs working. Return existing structured validation/ingestion failures through `build_validation_result` and `check_ingestion_preconditions`.
  * **Constraints:** Retain `row_exists`/`target_id_exists` reads and unchanged SQL generation, including sequence synchronization and inline staging's deployment-time allocation.
  * **Validation:** `V-1`, `V-2`, `V-3`; missing ID with an allocator-like fake, pre-resolved ID, both table operations, and all deploy strategies.
* [x] `T2.2` **Change and test:** Remove the now-unused runtime sequence reservation method and replace tests that expect generation-time allocation.
  * **Target:** `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker.reserve_target_id`; `backend/tests/ingesters/test_sead_change_request_orchestration.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py`; `backend/tests/ingesters/test_sead_change_request_inline_staging.py`; `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`.
  * **Current → required:** The checker exposes a `nextval` call, and orchestration tests expect it for non-tracked rows. The runtime collaborator used during bundle creation must expose only verification reads; tests must assert blocked missing IDs and unchanged target sequence state before artifact execution.
  * **Implementation:** Remove obsolete `target_id_allocator` fixtures and assertions, including the direct reservation integration test. Use a recording checker or a fail-on-reserve fake to prove validation and ingestion never call it. In the existing disposable PostgreSQL artifact test, distinguish bundle-generation state from later SQL execution; keep its deployment and rollback assertions. Update `ingesters/sead_change_request/README.md` to describe verification-only target access and explicit unsupported sequence IDs.
  * **Constraints:** Do not weaken provider-row or target-collision checks, or remove generated `setval`/staging `nextval` SQL intended for downstream execution.
  * **Validation:** `V-1`–`V-4`, `V-7`.

**Completion evidence:** `VM-2.1` passes: missing IDs fail without target sequence changes; required reads and generated deployment SQL still work.

### Area 2: Keep SIMS identity and confirmation guidance stable

**Objective:** Declared business keys resolve within the saved provider-schema scope without a shared fallback, and pending guidance identifies the retry key.

**Affected code:** `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter._build_identity_value`; `ingesters/sead_change_request/contracts.py::PendingConfirmationReport.create`.

**Dependencies:** Area 1's shared-path tests can run independently; trusted project context already exists.

**Tasks:**

* [x] `T2.3` **Change and test:** Fail closed when a declared business key cannot be serialized; confirm identity reuse across runs.
  * **Target:** `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter._build_identity_value`; `backend/tests/ingesters/test_sead_change_request_runtime.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`.
  * **Current → required:** A `BusinessKeyError` becomes the common entity name. Keep `business_id_for_row` as the identity value, but propagate a clear failure for invalid declared keys; do not send the shared value to SIMS. Project input validation must still reject missing, blank, unsupported, and duplicate keys before SIMS work.
  * **Implementation:** Add tests using the same saved provider-schema scope, same declared keys, and different run IDs; assert equal serialized identity and reused SIMS target ID with a stateful fake. Add a different-key and different-scope case, plus direct adapter serialization failure and project validation failure with zero SIMS calls. Keep field-based identity for entities without declared keys, including generated submission rows.
  * **Constraints:** Do not change `src/business_keys.py` encoding or accept caller-selected scope.
  * **Validation:** `V-2`, `V-5`.
* [x] `T2.4` **Change and test:** Name the effective run ID in pending-confirmation instructions.
  * **Target:** `ingesters/sead_change_request/contracts.py::PendingConfirmationReport.create`; `backend/tests/ingesters/test_sead_change_request_confirmation.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`.
  * **Current → required:** The rerun instruction names the submission and project but not the retry key. Include the effective raw run ID in the report's rerun guidance for validation and ingestion, and show it in both existing pending alerts.
  * **Implementation:** Use `SubmissionContext.run_id` already set by input resolution. Keep the existing report fields and API response types; test that the ID in guidance equals the SIMS request ID and, after a successful retry, the result/manifest ID.
  * **Constraints:** Never derive the ID from the run folder or expose it as a filesystem component.
  * **Validation:** `V-5`, `V-6`.

**Completion evidence:** `VM-2.2` passes for same-key later runs and invalid keys; pending guidance contains the exact retry ID.

### Area 3: Retain one operator run ID per submission attempt

**Objective:** Validation, ingestion, and a Binding Set retry send one run ID until the submission identity changes or a bundle succeeds.

**Affected code:** `frontend/src/stores/ingester.ts::useIngesterStore`; `frontend/src/components/ingester/IngesterForm.vue::buildProjectRequest`, `resetForm`.

**Dependencies:** The existing optional `ProjectSubmissionOptions.run_id` contract and Phase 1 output success response.

**Tasks:**

* [x] `T2.5` **Change:** Store the current attempt's run ID and attach it to both project requests.
  * **Target:** `frontend/src/stores/ingester.ts::useIngesterStore`, `validateProject`, `ingestProject`; `frontend/src/components/ingester/IngesterForm.vue::buildProjectRequest`, `resetForm`.
  * **Current → required:** Each form request omits `run_id`, so the server mints a different value each time. The store must generate one client UUID for an attempt and send it for validation, ingestion, and pending-confirmation retry, including after leaving and remounting the form while the Pinia store remains alive.
  * **Implementation:** Keep attempt state in the ingester store, keyed by the normalized submission name, route project, timestamp, datatype, and identifier. Prepare a copy of each project request with the current run ID before API dispatch. Reset the ID on any key-field change, explicit new-submission/reset action, and only after `ingestProject` returns `success: true`; retain it for validation results, pending confirmation, failed responses, and transport errors. Keep the non-Change-Request file actions unchanged.
  * **Constraints:** Do not add a request field or persist the ID across page reloads. Keep the backend fallback for callers that omit `run_id`.
  * **Validation:** `V-6`; same-attempt requests, remount, all reset triggers, and failure/retry cases.
* [x] `T2.6` **Test and document:** Verify the complete client retry flow and update the operator-facing explanation.
  * **Target:** `frontend/src/stores/__tests__/ingester.test.ts`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`; `ingesters/sead_change_request/README.md`.
  * **Current → required:** Existing tests check project request forwarding but not run ID reuse. Assert matching IDs for validate → ingest → pending retry, a new ID after changed submission identity or successful bundle, and unchanged ID after a failed/blocked ingest. Explain the store lifetime and server fallback in the README.
  * **Implementation:** Mock `ingesterApi` in store tests and mount the existing form test with its Pinia store mock updated for the new attempt action. Assert the displayed pending guidance contains the effective ID; the successful result and manifest retain it.
  * **Constraints:** Preserve the strict project request and existing route path.
  * **Validation:** `V-6`, `V-7`.

**Completion evidence:** `VM-2.2` passes for one client run ID per attempt, reset rules, and visible pending-confirmation guidance.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-3`) | `T2.1`, `T2.2` | `V-1`–`V-4` | Both table operations use verification reads only; unresolved sequence IDs fail, while generated deployment SQL retains sequence handling. |
| `PH2-AC-2` (from `P-AC-5`) | `T2.3` | `V-2`, `V-5` | Same scope and business key reuse a SIMS target ID; invalid tracked keys produce no SIMS call. |
| `PH2-AC-3` (from `P-AC-5`) | `T2.4`–`T2.6` | `V-5`, `V-6` | One ID spans validation, ingestion, and retry; reset rules and pending guidance are verified. |

## Validation And Testing

Baseline on 2026-10-20: the existing orchestration, ingester, confirmation, and runtime suites passed with three service-dependent skips; SQL builder, inline staging, and project service suites passed with thirteen skips; the disposable PostgreSQL artifact test skipped; both focused frontend suites passed (13 tests). These are current-state results, not Phase 2 acceptance.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Missing and pre-resolved sequence IDs in `backend/tests/ingesters/test_sead_change_request_orchestration.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH2-AC-1` | Validation and ingestion block unresolved IDs without a reserve call; pre-resolved and staged children work. | Pass: existing tests pass, but some still expect reservation and must be replaced. |
| `V-2` | Project preparation and trusted keys in `backend/tests/services/test_project_ingester_service.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/services/test_project_ingester_service.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH2-AC-1`, `PH2-AC-2` | Backend-selected provider row and target collision reads still occur; invalid keys stop before SIMS; app gate remains. | Pass: existing tests pass; new read-only and later-run cases remain. |
| `V-3` | Generated SQL in `backend/tests/ingesters/test_sead_change_request_sql_builder.py`, `backend/tests/ingesters/test_sead_change_request_inline_staging.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_inline_staging.py -q` | `PH2-AC-1` | Sequence synchronization and staged child allocation remain in deploy SQL, not generation-time DB calls. | Pass: existing checks pass; some database cases skip without a disposable service. |
| `V-4` | Runtime checker and disposable PostgreSQL check in `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py -q` | `PH2-AC-1` | No generation-time sequence movement; verification reads work. If the disposable database is available, later artifact execution still performs its intended SQL. | Pass: unit checks pass; service and disposable PostgreSQL cases skipped without local dependencies. |
| `V-5` | SIMS identity and pending report in `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_confirmation.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_confirmation.py -q` | `PH2-AC-2`, `PH2-AC-3` | Same scope/key reuse, invalid key failure, and report ID assertions pass with local fakes. | Pass: existing checks pass; later-run and run-ID guidance cases remain. |
| `V-6` | Store and form retry cases in `frontend/src/stores/__tests__/ingester.test.ts`, `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `rtk pnpm --dir frontend test:run src/stores/__tests__/ingester.test.ts src/components/ingester/__tests__/IngesterForm.test.ts` | `PH2-AC-3` | One ID across requests/retries; changed identity and successful bundle get a new ID; pending alerts display it. | Pass: 13 current tests, without attempt-ID coverage. |
| `V-7` | Formatting, type check, docs, and diff | `rtk .venv/bin/black --check ingesters/sead_change_request/orchestration.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/ingester.py ingesters/sead_change_request/contracts.py backend/app/services/ingester_runtime.py backend/tests/ingesters backend/tests/services/test_project_ingester_service.py`<br>`rtk .venv/bin/isort --check-only ingesters/sead_change_request/orchestration.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/ingester.py ingesters/sead_change_request/contracts.py backend/app/services/ingester_runtime.py backend/tests/ingesters backend/tests/services/test_project_ingester_service.py`<br>`rtk pnpm --dir frontend build`<br>`rtk make check-doc-links`<br>`rtk git diff --check` | Changed code, documentation, and tests | All checks pass. | Not run as a combined gate: planning made no code or README changes. Plan links and diff check pass. |

**Execution evidence (2026-10-20):**

- `V-1`–`V-5`: Focused backend suites passed after implementation.
- `V-3`: Thirteen disposable PostgreSQL inline-staging tests skipped because `SEAD_DISPOSABLE_POSTGRES_*` was not configured.
- `V-4`: The two disposable SIMS tests and two disposable PostgreSQL checks skipped because their service variables were not configured. The live target-sequence state check was therefore not exercised.
- `V-6`: Both frontend suites passed (17 tests).
- `V-7`: Black, isort, `vue-tsc`/production build, documentation links, and whitespace checks passed. Vite reported existing dependency annotation and chunk-size warnings.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Read-only preparation | `ingesters/sead_change_request/orchestration.py`, `ingesters/sead_change_request/preparation.py`, `ingesters/sead_change_request/ingester.py`; `backend/app/services/ingester_runtime.py` | `T2.1`, `T2.2` | No runtime `nextval` path; structured unresolved-ID result. |
| Sequence and read-only regressions | `backend/tests/ingesters/test_sead_change_request_orchestration.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_inline_staging.py`, `backend/tests/ingesters/test_sead_change_request_submission_sims_integration.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `T2.1`, `T2.2` | `VM-2.1` results recorded. |
| SIMS identity and guidance | `backend/app/services/ingester_runtime.py`; `ingesters/sead_change_request/contracts.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_confirmation.py` | `T2.3`, `T2.4` | Stable key resolution and report ID checks pass. |
| Operator attempt state and tests | `frontend/src/stores/ingester.ts`, `frontend/src/components/ingester/IngesterForm.vue`, `frontend/src/stores/__tests__/ingester.test.ts`, `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `T2.4`–`T2.6` | `VM-2.2` client checks pass. |
| Current behavior description | `ingesters/sead_change_request/README.md` | `T2.2`, `T2.6` | README describes read-only generation and retry ID rules. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Stop target sequence allocation | Done | Phase 1 accepted | Both operations block unresolved database-sequence IDs; runtime target access has no reservation method. Deployment SQL regressions pass. |
| Area 2: Keep SIMS identity stable | Done | Trusted project context | Same scope/key reuses identity; invalid keys fail before SIMS work; pending guidance includes the run ID. |
| Area 3: Retain operator run ID | Done | Existing request `run_id` and Phase 1 output | Store keeps the attempt through remounts and failures, resets on identity changes or success, and passes client tests. |

## Definition Of Done

- [x] Before implementation, verified the named repository targets still matched; unrelated working-tree changes were preserved.
- [x] `PH2-AC-1`–`PH2-AC-3` have implementation and focused validation evidence; `VM-2.2` passed, and live PostgreSQL portions of `VM-2.1` were skipped because disposable database variables were unavailable.
- [x] Every listed task and deliverable is complete; `V-1`–`V-7` passed or environment-dependent skips are recorded with their limits.
- [x] Provider-row and target-collision reads, SIMS scope/key serialization, generated sequence SQL, and Phase 1 output behavior are regression-tested.
- [x] Both project-only routes and the direct helper retain `application:run_ingesters` and `project:execute`; file input remains retired.
- [x] The README and pending-confirmation guidance match behavior; the unavailable live database check is recorded.
- [x] No unresolved implementation question remains.

## Risks And Open Questions

- A fake that only checks `reserve_target_id` calls does not prove a real database sequence stayed unchanged. `V-4` checks sequence state with a disposable database when available and reports any skip; unit checks must still block the call path without that service.
- The same SIMS run ID is a retry key for the same payload. The client keeps it through confirmation and failures for an unchanged attempt; changes to the named submission identity fields start a new attempt. A page reload loses Pinia state and starts a new run, as fixed by the proposal.
- No blocking decision remains. Phase 3 alone removes the application action after the Phase 2 results are accepted.
