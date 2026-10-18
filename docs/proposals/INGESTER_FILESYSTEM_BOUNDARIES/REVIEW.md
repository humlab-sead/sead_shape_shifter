# Proposal Review: Allow Operators To Create Change Request Target Bundles

## Review Basis

| Item | Value |
|---|---|
| Reviewed document | [INGESTER_FILESYSTEM_BOUNDARIES.md](./INGESTER_FILESYSTEM_BOUNDARIES.md) |
| Related plan | [INGESTER_FILESYSTEM_BOUNDARIES_PHASE_PLAN.md](./INGESTER_FILESYSTEM_BOUNDARIES_PHASE_PLAN.md) |
| Related task plan | [INGESTER_FILESYSTEM_BOUNDARIES_PHASE_1_TASK_PLAN.md](./INGESTER_FILESYSTEM_BOUNDARIES_PHASE_1_TASK_PLAN.md) |
| Review date | 2026-10-17 |
| Revision reviewed | Commit `fc539a3f` (rescope to a narrow permission exception) |
| Method | Read the proposal, phase plan, task plan, and current source. No tests were run and no deployment trust model was verified. |

This record holds review advice only. It is not an approval, and it does not change the proposal, the phase plan, or the task plan.

## Overall Assessment

The rescope is coherent. Treating Change Request target-bundle creation as file generation rather than a database operation is a defensible boundary, and keeping `application:run_ingesters` on validation and other ingesters limits the exposure. The managed-output and no-target-database rules are the right kind of constraint for a narrow exception.

Status observed:

- The rescope is committed (`fc539a3f`) and has a phase plan plus a task plan marked validated.
- It is not implemented. `backend/app/api/v1/endpoints/ingesters.py` still applies `RUN_INGESTERS` to both routes, `ingesters/sead_change_request/artifact_writer.py` still removes an existing bundle directory, and Phase 1 tasks `T1.1`–`T1.5` are unchecked.
- No approval is recorded in the proposal's Status section.

Principal concerns: `P-AC-5` claims an identity guarantee without naming the SIMS scope that makes a business key stable, and the current request and response contract cannot carry the `run_id` a retry needs; the design does not say how target-database dependencies are removed or that target-side collision checks are lost; the managed output location is undefined; and the source read path remains unconstrained without recording that tradeoff.

## Findings

### F1a — High — Business keys are provider-scoped evidence, and `P-AC-5` does not name the scope that makes them stable

**Location:** `P-AC-5`, Planning Handoff. Verified in `backend/app/services/ingester_runtime.py::_build_identity_value`, `_build_scope_name`; `ingesters/sead_change_request/input_resolution.py`; `src/model.py::EntityConfig.keys`; and, in the authority service, `src/identity/repository.py::SourceIdentityRepository.create_or_get`, `find_by_key`, `schema/sql/identity/003b_source_identity_keys.sql`, and `config/identity_policy.yml`.

**Issue and impact:** SIMS already scopes business keys correctly. A Source Identity is unique per `(scope_uuid, entity_type, key_type, key_value)`, and `SourceScope` is documented as an external namespace such as `provider://gbif`. `EntityConfig.keys` are source-local business keys, so using them as `business_key` signals is the right shape **only when the scope identifies the data provider**. Three consequences follow.

1. The CR ingester derives the scope from the project: `sead-change-request:{project_name}`. Identity stability is therefore per project, not per provider. The same provider submitting the same logical record under two projects creates two Source Identities and, for `provider_owned` entities (`sample_group`, `sample`, `analysis_entity`, `dataset`, `submission`; `bind_existing: false`), two allocated aggregates.
2. Two providers describing the same real-world shared entity with different business keys create two Source Identities by design. They converge only when Shape Shifter supplies `approved_aggregate_id` from reconciliation, which requires `bind_existing: true` (`site`, `taxa_tree_master`, `method`, `data_type`, `unit`, `feature_type`). Where reconciliation misses and allocation is permitted (`site`), two providers can allocate two rows for one real entity. No choice of `EntityConfig.keys` fixes this; it is inherent to provider-supplied keys.
3. `P-AC-5` says "the same stable SIMS source identity" without naming the scope. Within one project the claim is testable; across projects it fails; across providers it is only as good as reconciliation. Read as written, the criterion promises a global identity guarantee that the design does not provide.

Key construction carries the same risk. `create_or_get` returns the first identity matching **any** supplied key, and `source_identity_keys` allows one value per `key_type`, so a composite key must be serialized into one canonical string and adding or removing a key changes merge behaviour. `_build_identity_value` currently serializes every non-missing row field sorted by name, so a changed non-key column produces a new source identity, weak or descriptive columns act as identity evidence within a scope, and the serialization is an undeclared contract whose format changes silently re-identify records.

The declared keys are also unavailable to the ingester. `EntityConfig.keys` are project configuration, `IngestRequest` carries no entity keys, `_resolve_submission_context` reads only `submission_context`, and the target model offers `unique_sets` but no business-key declaration.

**Recommendation:**

- Name the scope in `P-AC-5`, for example "within one SIMS scope, repeated bundle generation for the same declared business key reuses the assigned target ID". Do not claim cross-provider deduplication.
- Record the source-scope string for this ingester. If the provider owns the identity, `sead-change-request:{project_name}` is the wrong scope; use a provider-scoped name and keep the project as submission metadata. If the project is deliberately the scope, record that provider-owned entities are project-local and cannot be deduplicated across projects.
- Make the business key explicit input: pass declared `keys` per entity, or add a target-model business-key declaration. Fail closed when a tracked or reconciled entity has no declared key, or when a key column is absent from the projected frame. Do not fall back to all columns.
- Define the canonical key serialization (column order, trimming, case, null handling, numeric and date formatting) as a versioned contract, because changing it invalidates every stored Source Identity.
- Record the residual cross-provider risk for shared entities in Risks And Tradeoffs: identity quality depends on reconciliation, and a reconciliation miss plus allocation can create a duplicate row.

**Confidence:** High for the mechanism. Medium for operational impact, which depends on whether projects are aligned with providers and whether duplicate aggregates have already been observed.

The scope half of this finding is now a separate decision: [Bind Each Project To One Curated Data Provider](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md). The business-key source and serialization remain open.

### F1b — High — `run_id` should be client-minted and operator-visible, and four contract points must change

**Location:** `P-AC-5`; `frontend/src/types/ingester.ts::SubmissionContextInput`; `frontend/src/components/ingester/IngesterForm.vue::buildSubmissionContext`; `backend/app/models/ingester.py::IngestResponse`; `ingesters/sead_change_request/input_resolution.py::_resolve_run_id`; `backend/app/services/ingester_runtime.py::_run_id_for`; `ingesters/sead_change_request/contracts.py::PendingConfirmationReport`; `ingesters/sead_change_request/sql_builder.py::_base_deploy_artifact_metadata`.

**Issue and impact:** Client minting fits the SIMS contract. `ResolveRequest.run_id` is a plain string, idempotency is keyed `(scope_name, run_id)`, and a different payload under the same key is rejected with a conflict rather than silently mixed. The current path cannot carry a client value, however: `SubmissionContextInput` has no `run_id`, `IngestResponse` does not return one, input resolution and the adapter both mint a `uuid4()` when absent, the pending-confirmation rerun instruction does not mention the key, and the deploy artifact metadata does not record it. A retry therefore cannot reuse the key, and neither the operator nor the bundle can identify the SIMS batch that produced the result.

**Recommendation:**

- Add optional `run_id` (UUID string) to `SubmissionContextInput` and to server-side submission-context resolution. Keep minting only when the caller omits it, and always return the effective value in `ValidateResponse` and `IngestResponse`.
- Generate the value once per submission attempt in the UI, persist it with the saved form state, display it read-only, and rotate it only on an explicit new run. Minting per render or per click defeats idempotency.
- Include the effective `run_id` in `PendingConfirmationReport.rerun_instruction` and in `_base_deploy_artifact_metadata`, so an operator can retry and the bundle stays traceable to its SIMS batch.
- Use lowercase UUIDv4 as the canonical format. The service stores text, so a UUID works; a required format keeps the scoped key unambiguous.
- Note the scope coupling: a `run_id` is unique only within a scope. With a project-derived scope, the same UUID reused in another project is harmless. With a provider-derived scope, an operator reusing another provider's key receives a payload conflict, not a mixed result.
- Update the task plan so `T0.3` records this contract and `T1.5` asserts the effective `run_id` round-trips through the request, the response, and the manifest.

**Confidence:** High for the contract gap and for client minting being compatible with the service.

### F2 — High — Proposed Design is silent on removing database-backed clients and on losing target collision checks

**Location:** Proposed Design, Risks And Tradeoffs. Verified in `backend/app/services/ingester_service.py::_create_config`, `backend/app/services/ingester_runtime.py::inject_ingester_database_dependencies`, `SeadChangeRequestTargetCollisionChecker`, and `ingesters/sead_change_request/ingester.py`.

**Issue and impact:** With database config present, the service injects a checker that queries target tables and calls `nextval`; the ingester also uses it as the `target_id_allocator`. `P-AC-3` is not achieved by the design as written. Omitting database config silently blocks `RESERVE_DATABASE_ID` rows and removes all target-side collision diagnostics. The proposal states neither the mechanism nor the consequence, so approvers may accept `P-AC-3` without seeing that non-SIMS sequence entities become unsupported and that collision detection moves entirely into the SEAD Release Cycle.

**Recommendation:** Add a design subsection covering no database dependency injection for this key, explicit reject-or-block behavior for `database_sequence` entities, no target-side collision check, and retention of deployment-time sequence synchronization in emitted SQL. Add the lost collision check as a named risk.

**Confidence:** High.

### F3 — High — "Any authenticated operator" is ambiguous and broader than the current permission

**Location:** Status, Summary, `P-AC-1`. Verified in `backend/app/authorization/policy.py`.

**Issue and impact:** `RUN_INGESTERS` is held only by `operator` (and `admin`). Authorization has no implicit allow for authenticated principals. Removing the action grants bundle creation to any authenticated principal, including users with no deployment or project role. The document never says whether that is intended, so the security change is larger than "operators" implies.

**Recommendation:** State the exact subject ("any authenticated principal" or a named role) and whether any project access is required. Align the title, summary, and the Security Hardening follow-up wording.

**Confidence:** High.

### F4 — High — The source read path remains unconstrained and the exposure is unstated

**Location:** Problem, Scope, Risks And Tradeoffs. Verified in `ingesters/sead_change_request/input_resolution.py::_load_source_bundle_from_path` and `IngestRequest.source`.

**Issue and impact:** The source is a caller-supplied path checked only for existence and `.xlsx`/`.xls` suffix. There is no containment. The previous revision made source containment a core requirement; this revision covers output only. `docs/proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md` exempts this operation from source constraints, but this proposal does not record that tradeoff. Any authenticated user can cause server-side reads of accessible Excel files and receive path or parser errors.

**Recommendation:** Either keep source containment under an approved root or uploaded reference, reusing `src/path_resolution`, or add the read exposure and the trust assumption to Risks And Tradeoffs.

**Confidence:** Medium. The severity depends on the deployment trust model and on whether other authenticated routes already expose equivalent reads.

### F5 — Medium — Managed output location, `output_folder`, and `output_path` semantics are undefined

**Location:** Proposed Design, `P-AC-2`. Verified in `backend/app/core/config.py`, `backend/app/services/ingester_service.py::ingest`, and `ingesters/sead_change_request/artifact_writer.py`.

**Issue and impact:** There is no ingester output-root setting. The only managed output pattern is project-scoped execution output (`backend/app/services/execute_service.py::resolve_output_target`). `IngestRequest.output_folder` is still accepted, and `IngestResponse.output_path` echoes it even though the ingester writes to `output_folder/bundle_name`. The proposal does not say whether `output_folder` is ignored, rejected, or treated as a subpath. Implementers can choose an arbitrary root, callers will not know where a timestamped bundle was written, and collision uniqueness and concurrent-run behavior are unspecified.

**Recommendation:** Name the managed root and its configuration setting, define `output_folder` handling, return the actual bundle directory, and require atomic exclusive directory creation with clear timestamp uniqueness.

**Confidence:** High.

### F6 — Medium — Index and companion documents still describe the old scope

**Location:** `docs/proposals/README.md`, `docs/proposals/CHANGE_REQUEST_INGESTER/README.md`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`.

**Issue and impact:** The index row is still titled "Secure Ingester Filesystem And Destination Access" with a containment summary. The Change Request README says "not ready to enable … Keep operations unavailable until required checks are enforced". The route inventory says containment checks remain owned by this proposal. Readers get contradictory status, and the proposal index no longer states the current decision.

**Recommendation:** Update the index row and both references in the same change, and state that source, destination, and database containment for other ingesters remains owned elsewhere.

**Confidence:** High.

### F7 — Low — No alternatives are recorded for an authorization decision

**Location:** Missing Alternatives Considered section.

**Issue and impact:** A dedicated `create_change_request_bundle` action, a separate route, or granting `operator` more broadly are plausible alternatives that are not weighed.

**Recommendation:** Add two or three sentences explaining why authentication-only is preferred.

**Confidence:** High for the fact; impact is low.

### F8 — Low — The filename no longer matches the topic

**Location:** `INGESTER_FILESYSTEM_BOUNDARIES.md`.

**Issue and impact:** The document is now about a specific permission exception, while its name implies broad filesystem boundaries.

**Recommendation:** Keep the name for link stability and add a one-line note, or rename the file and update the existing links. Do not leave the mismatch unexplained.

**Confidence:** High.

## Suggested `P-AC-5` Rewrite

Current wording assigns a target ID to "the same stable SIMS source identity" without defining that identity. A narrower criterion that matches the contract would be:

> `P-AC-5` Within one SIMS source scope, repeated bundle generation for the same declared business key reuses the assigned target ID. A caller-supplied `run_id` is reused for retries and is recorded in the response and the bundle manifest. The source scope used for Change Request runs is `<decided scope>`, and declared business keys are `<decided source>`.

This keeps the testable part of the current criterion, removes the implied cross-provider guarantee, and makes the scope and key source explicit decisions.

## Planning Readiness

**Revision required.**

The phase plan and task plan structure are sound, but approval should wait until four things are resolved in the proposal: the SIMS scope and business-key contract behind `P-AC-5`, the client-supplied `run_id` contract, the concrete removal of target-database clients plus the resulting collision-check loss, and the managed output root and response-path contract. The source-read exposure should also be either contained or explicitly accepted. After those changes, the remaining findings are editorial and planning can proceed without redesign.

## Not Verified

- Runtime behaviour of SIMS batch replay when a run key is reused with a different payload. The conflict path exists in `resolve_identity_batch`, but it was not executed for this review.
- Whether existing projects map one-to-one to data providers, which determines how often the duplicate-allocation risk in F1a actually occurs.
- Whether target-side collision checks are required by a separate SEAD Release Cycle gate.
- The deployment trust model that determines the severity of F4.
- Any runtime behavior; no tests or live checks were run for this review.
