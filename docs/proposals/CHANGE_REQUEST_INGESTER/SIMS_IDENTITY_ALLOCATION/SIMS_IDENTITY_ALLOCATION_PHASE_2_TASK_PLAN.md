# Phase 2 Task Plan: Model-Driven Planning And Capability Preflight

## Phase Summary

**Goal:** Make the SEAD change-request ingester plan identity work from the target model's effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values (the same rules target-model validation and documentation use) and reject unsupported work against SIMS's published capability contract before SIMS resolution or artifact generation.

**Readiness:** Validated. Phase 2 is marked ready in the [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md). Phase 1 has published the [capability contract](../../../../sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md) and a validated configuration model, and `GET /identity/capabilities` is implemented in the Authority Service. The normalized operation mapping and fail-closed behavior are fully specified by the source proposal and phase plan.

**Constraints and dependencies**

- Use one shared effective-identity resolution path; do not add a third copy of the role/default logic.
- Do not equate the four target-model identity modes with SIMS `entity_subtype`. Map target-model operations to SIMS operations (`allocate_new`, `bind_existing`) explicitly.
- Preserve fail-closed behavior: do not silently fall back from `lookup-only` reconciliation to allocation, or from unsupported child/derived handling to parent IDs.
- Keep SEAD reconciliation and per-row match/miss approval in Shape Shifter. Reconciliation is a Shape Shifter decision; a reconciled row may still have a SIMS tracked identity.
- Do not change SIMS behavior. SIMS guarantees uniqueness only within its own identity store. Cutover, bootstrap, deployment, and SEAD database integrity remain out of scope.
- Model name and version are recorded for diagnostics only; a version mismatch is not itself a failure.

**Source documents:** [identity-allocation proposal](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md), [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md), and the Phase 1 [capability contract](../../../../sead_authority_service/docs/proposals/SIMS_IDENTITY_CAPABILITY_CONTRACT.md).

### Phase Acceptance Criteria

- [ ] `PH2-AC-1` (from `P-AC-1`, `P-AC-2`): Planning derives each row's identity work from the target model's effective `identity_tracking`, `reconciliation`, and `aggregate_parent` values, including documented defaults, and matches target-model validation behavior.
- [ ] `PH2-AC-2` (from `P-AC-3`, `P-AC-4`, `P-AC-5`): Preflight compares normalized identity requirements against the versioned SIMS capability response, records the target-model name and version, and blocks unsupported or incomplete operations before artifact generation.

## Repository Findings

**Repository basis:** Planning date 2026-10-03. Shape Shifter is on `sims-identity-allocation-phase-1` at `7172e415` with a clean working tree. The Authority Service Phase 1 capability work is committed on the same branch in that repository and is the source of the capability contract this phase consumes.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `src/target_model/spec_validator.py::TargetModelSpecValidator._resolve_effective_sims` | Static method derives effective `identity_tracking`/`reconciliation` from role and `aggregate_parent`; returns a tuple. Used by `_validate_identity_rules`. | Extract this into one shared resolver and keep validation behavior unchanged. |
| `src/target_model/documentation.py::SimsDocumentGenerator._resolve_effective_sims` | A second, semantically equivalent copy that returns a dict and adds an explicit `child → reconciliation None` branch. | Consolidate both copies; the explicit child branch is a no-op equivalent of the validator's fall-through. |
| `ingesters/sead_change_request/planning.py::plan_table` | Routes by raw fields and `role`: `is_tracked_allocation` checks raw `identity_tracking`/`reconciliation`; `missing_action = RECONCILE if role == "classifier" else ALLOCATE`; `role == "bridge"` selects `EVALUATE_BRIDGE`. | Replace role routing with the shared effective resolver. This is the core `PH2-AC-1` change. |
| `ingesters/sead_change_request/collision_checks.py::check_projected_collisions` | Duplicates the same `is_tracked_allocation` + `role == "bridge"` routing at line 58. | Update to the shared resolver so collision checks and planning agree. |
| `backend/app/clients/sims_client.py::SimsClient` | Mirrors the six `/identity` endpoints but has no capability-discovery call. | Add `get_capabilities()`; it is the client-side entry point for preflight. |
| `backend/app/models/sims.py` | Client DTOs stop at `ResolveResponse`; there is no `CapabilitiesResponse`/`EntityCapabilityResponse`. | Add capability DTOs matching the Authority Service response schema. |
| `sead_authority_service/src/api/identity_router.py::CapabilitiesResponse` | `GET /identity/capabilities` returns `{version: str, entities: [{entity_type, entity_subtype, bind_existing, allocate_new, auto_confirm, accept_uuid}]}`; `version` is `CAPABILITY_VERSION = "1.0"`. | The preflight comparison targets these fields and does not require an exact version match. |
| `src/target_model/models.py::ModelMetadata` | `name`, `version`, and `format_version` live on `TargetModel.model`. | Preflight records `TargetModel.model.name` and `.model.version` for diagnostics. |
| `ingesters/sead_change_request/preparation.py::prepare_change_request` | The shared workflow entry; it has the full `inputs.target_model` but `plan_bundle` is handed only `inputs.target_model.entities`. | Wire preflight here, before `orchestrate_identity_assignments`, so blocking happens before SIMS calls and artifact work. |
| `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter` | Per-row resolve seam (`allocate_entity`, `bind_existing_entity`) wrapping `SimsClient`. | Expose capability discovery through this seam so the ingester can preflight without a second client. |
| `resources/target_models/sead_superset_model.yml` | `analysis_entity` is `role: bridge` with `identity_tracking: tracked`/`reconciliation: allocate`; `sample_dimension` is `role: fact` with `aggregate_parent: sample`; `site` is `role: lookup` with no identity fields. | These are the conflicting role/mode regression examples; `analysis_entity` must still allocate, `sample_dimension` must inherit, `site` must reconcile. |
| `backend/tests/ingesters/test_sead_change_request_planning.py`, `test_sead_change_request_orchestration.py`, `test_sead_change_request_contracts.py`, `test_sead_change_request_identity_work.py`, `tests/target_model/test_spec_validator.py` | Existing unit suites cover role-based planning, orchestration, and validator combos. | Extend these; add a new preflight test and a shared-resolver parity test. |

**Baseline checks on the current Shape Shifter checkout**

- `.venv/bin/pytest tests/target_model/test_spec_validator.py backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_contracts.py backend/tests/ingesters/test_sead_change_request_identity_work.py -q` — Pass (exit 0; 55 tests).
- `.venv/bin/ruff check` over the Phase 2 target files — Not run during planning; recorded as a planned validation with a Not-run baseline.

## Scope

**In scope**

- One shared effective-identity resolver used by target-model validation, documentation generation, and ingester planning.
- Model-driven row planning: `tracked` → allocate, `reconciled` → reconcile/lookup, `derived` → bridge derivation, `child` → aggregate-parent inheritance.
- A client-side SIMS capability model and `get_capabilities()` call.
- A fail-closed preflight step that normalizes planned operations, compares them with SIMS capabilities, records target-model name and version, and blocks unsupported or incomplete operations before artifact generation.
- Diagnostics that name the entity and the unsupported requirement.

**Out of scope**

- Single-batch orchestration, run IDs, and artifact-strategy parity (Phase 3).
- SIMS-owned capability/allocator behavior (Authority Service; Phase 1 is complete).
- Defining the insertion contracts for child/derived rows that need their own relational keys; such rows fail closed until a contract is defined (recorded limitation).
- Manual Binding Set confirmation, existing-data migration, bootstrap, deployment, and cutover.

**Affected components:** `src/target_model/` (validator, documentation, new resolver), `ingesters/sead_change_request/` (planning, collision checks, contracts, identity work, new preflight, preparation), `backend/app/clients/sims_client.py`, `backend/app/models/sims.py`, and the corresponding tests.

## Work Breakdown

### Area 1: Consolidate Effective Identity Resolution

**Objective:** One shared resolver computes effective `identity_tracking`, `reconciliation`, and `aggregate_parent`, and validator, documentation, and planner all use it.

**Affected code:** `src/target_model/effective_identity.py` (NEW); `src/target_model/spec_validator.py`; `src/target_model/documentation.py`; `tests/target_model/test_effective_identity.py` (NEW).

**Dependencies:** None. Precedes Areas 2 and 3, which call the shared resolver.

**Tasks:**

* [x] `T1.1` **Change:** Add a shared effective-identity resolver.
  * **Target:** `src/target_model/effective_identity.py` (NEW).
  * **Current → required:** The default rules exist as two private copies (`spec_validator._resolve_effective_sims` and `documentation._resolve_effective_sims`). There is no single importable resolver.
  * **Implementation:** Define `EffectiveIdentity` (fields `identity_tracking`, `reconciliation`, `aggregate_parent`, all `str | None`) and `resolve_effective_identity(spec: EntitySpec) -> EffectiveIdentity`. Implement the exact defaults: `aggregate_parent` implies `child`; otherwise `fact` → `tracked`, `lookup`/`classifier` → `reconciled`, `bridge` → `derived`; `tracked` → `allocate`, `lookup` → `reconcile-exact`, `classifier` → `lookup-only`, `derived` → `derive`, `child` → no reconciliation.
  * **Constraints:** Preserve the documented defaults in [TARGET_MODEL_GUIDE.md](../../TARGET_MODEL_GUIDE.md) verbatim. Do not change validation outcomes. No `backend` imports; this is a `src/` module.
  * **Validation:** `V-1`; `tests/target_model/test_effective_identity.py` proves defaults and explicit overrides.
* [x] `T1.2` **Change:** Delegate both private resolvers to the shared one.
  * **Target:** `src/target_model/spec_validator.py::TargetModelSpecValidator._resolve_effective_sims`; `src/target_model/documentation.py::SimsDocumentGenerator._resolve_effective_sims`.
  * **Current → required:** Two copies that must stay in lock-step.
  * **Implementation:** Replace each body with a call to `resolve_effective_identity(spec)`, preserving each caller's return shape (tuple vs dict). Remove the now-dead private logic.
  * **Constraints:** No change to validator issue codes or generated SIMS register output.
  * **Validation:** `V-1`, `V-4`; existing validator and documentation tests must stay green.
* [x] `T1.3` **Change:** Add a parity test locking validator, documentation, and resolver together.
  * **Target:** `tests/target_model/test_effective_identity.py` (NEW); `tests/target_model/test_spec_validator.py` (read for fixtures).
  * **Current → required:** No test asserts that validation and documentation agree on effective values.
  * **Implementation:** Build `EntitySpec` fixtures for `site` (lookup), `analysis_entity` (bridge + tracked/allocate), `sample_dimension` (fact + aggregate_parent), and a plain `fact`; assert `resolve_effective_identity`, the validator's resolution, and `SimsDocumentGenerator._resolve_effective_sims` all return the same effective values.
  * **Constraints:** Use the documented defaults; no network or DB.
  * **Validation:** `V-1`.

**Completion evidence:** One importable resolver exists; validator and documentation delegate to it; the parity test proves all three agree.

### Area 2: Route Planning By Effective Identity Mode

**Objective:** `plan_table` and collision checks select actions from effective identity metadata, not `role`.

**Affected code:** `ingesters/sead_change_request/planning.py`; `ingesters/sead_change_request/contracts.py`; `ingesters/sead_change_request/identity_work.py`; `ingesters/sead_change_request/collision_checks.py`; `backend/tests/ingesters/test_sead_change_request_planning.py`; `test_sead_change_request_identity_work.py`.

**Dependencies:** Area 1 (shared resolver).

**Tasks:**

* [x] `T2.1` **Change:** Drive `plan_table` actions from effective identity.
  * **Target:** `ingesters/sead_change_request/planning.py::plan_table`.
  * **Current → required:** Action selection uses raw `identity_tracking`/`reconciliation` and `role`. `sample_dimension` (child) and `site` (lookup) misroute to `ALLOCATE`.
  * **Implementation:** Compute `EffectiveIdentity` once via `resolve_effective_identity`. Map the missing-public-ID action by effective mode: `tracked` → `ALLOCATE`; `reconciled` → `RECONCILE`; `derived` → `EVALUATE_BRIDGE`; `child` → a new `INHERIT_AGGREGATE` action. Preserve `REFERENCE_EXISTING`/`UPDATE_EXISTING_CANDIDATE` for rows with a public-ID value and the `database_sequence` path. Keep the `bridge` branch as `identity_tracking == "derived"` (so `analysis_entity`, which is `tracked`, still allocates).
  * **Constraints:** Preserve the `database_sequence` non-tracked guard and the existing mutable-field update routing. Do not change `RECONCILE` semantics for classifier lookup entities.
  * **Validation:** `V-2`, `V-4`; extend `test_sead_change_request_planning.py` with `analysis_entity`, `sample_dimension`, and `site` cases.
* [x] `T2.2` **Change:** Introduce a child action and its identity-work bucket.
  * **Target:** `ingesters/sead_change_request/contracts.py::PlannedRowAction`; `ingesters/sead_change_request/identity_work.py::build_identity_work_plan`.
  * **Current → required:** No planned action distinguishes child rows from allocation candidates; `IdentityWorkPlan` has no child bucket.
  * **Implementation:** Add `PlannedRowAction.INHERIT_AGGREGATE` and an `inherit_rows` dict on `IdentityWorkPlan`, populated in `build_identity_work_plan`. Child rows inherit identity through `aggregate_parent`; their own `public_id` source is resolved later and fails closed when no insertion contract is defined.
  * **Constraints:** Do not silently fall back from child handling to parent IDs or to allocation. Keep the new action out of `INSERTABLE_ROW_STATES` until projection resolves an insertion contract.
  * **Validation:** `V-2`, `V-4`; extend `test_sead_change_request_identity_work.py`.
* [x] `T2.3` **Change:** Unify collision-check routing with effective identity.
  * **Target:** `ingesters/sead_change_request/collision_checks.py::check_projected_collisions`.
  * **Current → required:** The file re-derives `is_tracked_allocation` + `role == "bridge"` instead of using effective metadata.
  * **Implementation:** Replace the local raw-field routing with `resolve_effective_identity(spec)` so bridge handling is selected by `identity_tracking == "derived"` and allocation by `tracked`, matching `plan_table`.
  * **Constraints:** Preserve `_check_bridge_collisions` and `_check_target_id_collisions` behavior for their respective row sets.
  * **Validation:** `V-4`; existing `test_sead_change_request_collision_checks.py` stays green.

**Completion evidence:** `plan_table` and `check_projected_collisions` produce the same action for a given effective mode; conflicting role/mode examples (`analysis_entity`, `sample_dimension`, `site`) route correctly and tests assert it.

### Area 3: Fail-Closed SIMS Capability Preflight

**Objective:** Before orchestration, normalize planned operations and compare them with `GET /identity/capabilities`, recording model name/version and blocking unsupported work.

**Affected code:** `backend/app/models/sims.py`; `backend/app/clients/sims_client.py`; `ingesters/sead_change_request/capability_preflight.py` (NEW); `ingesters/sead_change_request/preparation.py`; `ingesters/sead_change_request/contracts.py`; `backend/app/services/ingester_runtime.py`; `backend/tests/ingesters/test_sead_change_request_preflight.py` (NEW).

**Dependencies:** Areas 1 and 2 (effective mode determines the normalized operation).

**Tasks:**

* [x] `T3.1` **Change:** Add capability DTOs and a client method.
  * **Target:** `backend/app/models/sims.py`; `backend/app/clients/sims_client.py::SimsClient`.
  * **Current → required:** The client cannot discover capabilities; no DTOs exist.
  * **Implementation:** Add `EntityCapabilityResponse` (`entity_type`, `entity_subtype`, `bind_existing`, `allocate_new`, `auto_confirm`, `accept_uuid`) and `CapabilitiesResponse` (`version`, `entities`). Add `SimsClient.get_capabilities() -> CapabilitiesResponse` calling `GET /identity/capabilities`.
  * **Constraints:** Mirror the Authority Service `CapabilitiesResponse` schema exactly; keep `_get`/`_post` behavior.
  * **Validation:** `V-3`, `V-5`; unit test with a mocked httpx response.
* [x] `T3.2` **Change:** Add a normalization + preflight module.
  * **Target:** `ingesters/sead_change_request/capability_preflight.py` (NEW); `ingesters/sead_change_request/contracts.py` (add a `CapabilityPreflightResult` dataclass).
  * **Current → required:** No preflight exists; orchestration calls SIMS per row and blocks only after a missing aggregate ID.
  * **Implementation:** Add `preflight_capabilities(planned, target_model, capabilities) -> CapabilityPreflightResult` that: normalizes each entity's planned operation (`tracked` → `allocate_new`; `reconciled` with an approved match → `bind_existing`; `reconciled` `lookup-only`/`lookup-extensible` → `bind_existing` only, never allocation; `child`/`derived` → no SIMS operation). Compare against capability entries; record `model_name`/`model_version` from `TargetModel.model`; collect a blocking diagnostic naming the entity and unsupported requirement.
  * **Constraints:** A version mismatch is not a failure. Do not infer support from a model entry's presence. Unlisted entity types are unsupported.
  * **Validation:** `V-3`; `test_sead_change_request_preflight.py` proves unsupported allocation blocks, `lookup-only` misses do not fall back to allocation, and model name/version are recorded.
* [x] `T3.3` **Change:** Wire preflight into the preparation workflow before orchestration.
  * **Target:** `ingesters/sead_change_request/preparation.py::prepare_change_request`; `ingesters/sead_change_request/ingester.py::_prepare_change_request`; `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter`.
  * **Current → required:** `prepare_change_request` proceeds straight to `orchestrate_identity_assignments`; no capability gate exists.
  * **Implementation:** Expose `get_capabilities()` through the SIMS adapter seam; call `preflight_capabilities` when a SIMS client is present, before orchestration. When preflight blocks, surface the diagnostics in the `PreparationResult`/validation path so no artifact is generated.
  * **Constraints:** Keep the seam `SimsClientPort`-compatible; when no SIMS client is injected, preserve the existing non-SIMS behavior and record that preflight was skipped.
  * **Validation:** `V-3`, `V-4`; extend `test_sead_change_request_orchestration.py`/ingester tests with a blocked-preflight path that produces no artifact.

**Completion evidence:** Unsupported or incomplete operations are reported and blocked before any SIMS resolve call or artifact write; diagnostics name the entity and requirement and carry the model name and version.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-1`, `P-AC-2`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2`, `T2.3` | `V-1`, `V-2`, `V-4` | `analysis_entity` still allocates, `sample_dimension` inherits, `site` reconciles; validator, documentation, and planner agree on effective values. |
| `PH2-AC-2` (`P-AC-3`, `P-AC-4`, `P-AC-5`) | `T3.1`, `T3.2`, `T3.3` | `V-3`, `V-4` | Preflight compares normalized operations with capabilities, records model name/version, and blocks unsupported or incomplete operations before artifact generation. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Shared-resolver parity | `cd /data/roger/source/sead_shape_shifter && .venv/bin/pytest tests/target_model/test_effective_identity.py -q` | `PH2-AC-1` | Resolver, validator, and documentation return identical effective values for `site`, `analysis_entity`, `sample_dimension`, and a plain `fact`. | Pass (2026-10-03): 13 passed; parity across resolver, validator, and documentation. |
| `V-2` | Planner unit tests | `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_identity_work.py -q` | `PH2-AC-1` | Conflicting role/mode examples route by effective mode; child rows land in the inherit bucket, not allocation. | Pass (2026-10-03): 26 passed; `site` → RECONCILE, `sample_dimension` → INHERIT_AGGREGATE, `analysis_entity` → ALLOCATE. |
| `V-3` | Capability preflight contract tests | `.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_preflight.py -q` | `PH2-AC-2` | Unsupported allocation blocks; `lookup-only` misses do not fall back to allocation; model name/version recorded; unlisted types are unsupported. | Pass (2026-10-03): 13 passed. |
| `V-4` | Regression suite | `.venv/bin/pytest tests/target_model/test_spec_validator.py backend/tests/ingesters/ -q` | `PH2-AC-1`, `PH2-AC-2` | Existing validator, planning, orchestration, contracts, identity-work, and collision checks stay green; `test_sead_change_request_submission_sims_integration.py` still passes when a SIMS/disposable DB is available. | Pass (2026-10-03): full ingester suite 169 passed, 4 skipped (SIMS integration); target-model validator suite green. One unrelated, pre-existing failure in `backend/tests/services/test_reconciliation_service.py` (env-dependent `host.docker.internal` vs `localhost`) is outside this phase's scope. |
| `V-5` | Lint and format | `.venv/bin/ruff check src/target_model/effective_identity.py src/target_model/spec_validator.py src/target_model/documentation.py ingesters/sead_change_request/planning.py ingesters/sead_change_request/collision_checks.py ingesters/sead_change_request/contracts.py ingesters/sead_change_request/identity_work.py ingesters/sead_change_request/capability_preflight.py ingesters/sead_change_request/preparation.py backend/app/clients/sims_client.py backend/app/models/sims.py` then `make tidy` | `PH2-AC-1`, `PH2-AC-2` | No Ruff findings; Black + isort clean. | Pass (2026-10-03): Areas 1–3 source/test files clean, including `capability_preflight.py`, `preparation.py`, `result_builders.py`, `sims.py`, `sims_client.py`, `ingester_runtime.py`, and `test_sead_change_request_preflight.py`. |

The `VM-5` parity milestone (document every changed identity route) is satisfied by `V-2`/`V-4` together with the `analysis_entity`/`sample_dimension`/`site` cases named above; a short parity note is recorded in the change's commit/PR text rather than as a separate artifact.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared resolver | `src/target_model/effective_identity.py` (NEW) | `T1.1` | One importable `resolve_effective_identity` with the documented defaults. |
| Validator/documentation delegation | `src/target_model/spec_validator.py`, `src/target_model/documentation.py` | `T1.2` | Both delegate to the shared resolver; no behavior change. |
| Model-driven planning | `ingesters/sead_change_request/planning.py`, `collision_checks.py`, `contracts.py`, `identity_work.py` | `T2.1`, `T2.2`, `T2.3` | Actions derive from effective identity; child rows bucket separately; collision checks agree with planning. |
| Capability client + DTOs | `backend/app/models/sims.py`, `backend/app/clients/sims_client.py` | `T3.1` | `get_capabilities()` returns the capability schema. |
| Preflight module | `ingesters/sead_change_request/capability_preflight.py` (NEW) | `T3.2` | `preflight_capabilities` normalizes and compares, recording model name/version. |
| Workflow wiring | `ingesters/sead_change_request/preparation.py`, `ingester.py`, `backend/app/services/ingester_runtime.py` | `T3.3` | Preflight runs before orchestration; blocked runs produce no artifact. |
| Tests | `tests/target_model/test_effective_identity.py` (NEW), `backend/tests/ingesters/test_sead_change_request_preflight.py` (NEW), plus edits to `test_sead_change_request_planning.py`, `test_sead_change_request_identity_work.py`, `test_sead_change_request_ingester.py`, `test_sead_change_request_orchestration.py` | `T1.3`, `T2.1`, `T2.2`, `T3.2`, `T3.3` | New and extended tests cover the criteria in the coverage table. |
| Phase 2 task plan | `docs/proposals/CHANGE_REQUEST_INGESTER/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_2_TASK_PLAN.md` (NEW) | — | This plan records the repository basis, criteria mapping, and validation commands. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Consolidate effective identity resolution | Done | None | `src/target_model/effective_identity.py` added; validator and documentation delegate; 13 parity/default tests pass. |
| Area 2: Route planning by effective identity mode | Done | Area 1 | `plan_table`/collision checks use effective mode; `INHERIT_AGGREGATE` action + bucket added; 26 planner/identity-work tests pass. |
| Area 3: Fail-closed SIMS capability preflight | Done | Areas 1 and 2 | `CapabilitiesResponse` DTOs, `SimsClient.get_capabilities`, `capability_preflight.py`, and workflow wiring added; 13 preflight tests pass; preflight surfaced in validation and preconditions. |

## Definition Of Done

- [x] Every `PH2-AC-*` criterion has implementation and validation evidence mapped above.
- [x] One shared resolver is the single source of effective identity defaults, used by validator, documentation, and planner.
- [x] `analysis_entity` still allocates, `sample_dimension` inherits, and `site` reconciles; explicit mode settings override conflicting roles and omitted settings use documented defaults.
- [x] Preflight normalizes planned operations against SIMS capabilities, records target-model name and version, and blocks unsupported or incomplete operations before artifact generation.
- [x] Preflight normalization derives `bind_existing`-only (never `allocate_new`) for `lookup-only`/`lookup-extensible` entities, and child/derived rows never silently inherit a parent ID without a defined insertion contract.
- [x] Required tests (`V-1` through `V-4`) and quality checks (`V-5`) pass.
- [x] Existing behavior identified for preservation (validation outcomes, generated SIMS register output, mutable-field update routing, database-sequence path) is regression-tested.
- [x] Deviations and follow-up work (child insertion contracts, manual confirmation, batch orchestration, orchestration-side `lookup-only` fall-through prevention) are documented.
- [x] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

**Known limitation (not blocking):** Child/derived rows that need their own relational `public_id` without a defined insertion contract are rejected at preflight. Defining those contracts (for example `sample_dimension_id`) is a separate follow-up; this phase routes them to inheritance and fails closed rather than allocating. This matches the source proposal's `Blockers And Known Limitations`.

**Open implementation choices (resolved by repo convention, recorded for the coding agent):**

- The new child planned-action enum value is `INHERIT_AGGREGATE`; the exact name may be adjusted to match existing naming in `contracts.py`, but the semantics (inherit via `aggregate_parent`, never allocate) are fixed by `PH2-AC-1`.
- Preflight is wired in `prepare_change_request` (which holds the full `TargetModel`) rather than in `orchestrate_identity_assignments`; the capability fetch is exposed through the existing SIMS adapter seam.

**Open question (resolved):** Preflight records a blocking diagnostic (`CapabilityPreflightResult.diagnostics`) that both the validation and ingestion-precondition paths already surface, so `PH2-AC-2` is enforced at the artifact boundary without a new top-level error type. `V-4` confirms the full ingester suite stays green.

**Deferred (Phase 3/4):** Single-batch orchestration and run IDs; SIMS-side manual confirmation; existing-data migration, deployment, and cutover; orchestration-side prevention of the `RECONCILE` → allocation fall-through for `lookup-only` entities (Phase 2 preflight already normalizes these as `bind_existing`-only, but the per-row orchestration fall-through is restructured in Phase 3's single-batch collection). None of these affect the planning and preflight scope of this phase.
