# Proposal Review: Allow Operators To Create Change Request Target Bundles

## Review Basis

| Item | Value |
|---|---|
| Reviewed document | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) |
| Related plan | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) |
| Related task plan | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md) |
| Review date | 2026-10-18 |
| Revision reviewed | Working tree on branch `dev`: uncommitted read-only target-database relaxation; proposal body otherwise commit `fc539a3f` |
| Method | Read the proposal, phase plan, task plan, and current source, including the implemented provider-scope code. No tests were run and no deployment trust model was verified. |

This record replaces the 2026-10-17 review of revision `fc539a3f`. It holds review advice only. It is not an approval, and it does not change the proposal, the phase plan, or the task plan.

## Overall Assessment

Two changes since the prior review move this proposal forward:

- [Bind Each Project To One Curated Provider Scope](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md) is Implemented (Phases 1–4), and its code is on the current branch. It defines the SIMS scope (`provider://<provider-code>/<provider-schema>`, required, no project-name fallback), the business-key source (`EntityConfig.keys` through `business_id_for_row` in `src/business_keys.py`), a versioned key serialization, pre-SIMS key validation, and the effective `run_id` and `scope_name` in the response and deploy-artifact metadata. The prior review's identity blockers (F1a, and the response half of F1b) are resolved in code, not just on paper.
- The target-database rule was relaxed on 2026-10-18 (uncommitted) from "does not connect" to "read-only verification queries only; no target-row writes and no `nextval`." This matches shipped behavior — `_verify_provider_row` in `ingesters/sead_change_request/ingester.py` already requires a read-only target query to confirm the fixed `data_provider` row — and resolves the prior F2 blocker by naming the mechanism and retaining collision checks instead of losing them.

The proposal is not implemented. `backend/app/api/v1/endpoints/ingesters.py` still applies `RUN_INGESTERS` to both routes, `ingesters/sead_change_request/artifact_writer.py` still removes an existing same-name bundle directory, and Phase 1 tasks `T1.1`–`T1.5` are unchecked. No approval is recorded in the proposal's Status section.

Principal remaining concerns: the authorization subject is still ambiguous, the source read path is still unconstrained and unrecorded, the managed output root is still undefined, `P-AC-5` still does not name the SIMS scope it depends on, and the UI cannot supply the `run_id` a retry needs.

## Prior Findings Status

| Prior finding | Status | Basis |
|---|---|---|
| F1a — business-key scope and serialization | Resolved in code | Provider-scope proposal: scope from the saved project pair, declared `keys` via `business_id_for_row`, versioned serialization, pre-SIMS validation. Proposal text still not updated (see R5). |
| F1b — client-minted `run_id` | Partially resolved | `IngestResponse` returns the effective `run_id`, `sql_builder.py` records it in artifact metadata, and the UI displays it. The UI still cannot send one (see R4). |
| F2 — target-database mechanism and lost collision checks | Resolved in working tree | The read-only relaxation names the mechanism (injected checker, read-only queries allowed, `nextval` removed from generation), keeps target-row collision checks, and records the new target-availability dependency in Risks. Needs commit. |
| F3 — authorization subject | Open | See R2. |
| F4 — source read path | Open | See R3. |
| F5 — managed output root | Open | See R6. |
| F6 — companion documents | Open | See R9. |
| F7 — alternatives not recorded | Open | See R9. |
| F8 — filename mismatch | Open | See R9. |

## Open Findings

### R2 — High — "Any authenticated operator" is ambiguous and broader than the current permission

**Location:** Status, Summary, `P-AC-1`. Verified in `backend/app/authorization/policy.py`.

**Issue and impact:** `RUN_INGESTERS` is held only by `operator` (and `admin`). Authorization has no implicit allow for authenticated principals. Removing the action grants bundle creation to any authenticated principal, including users with no deployment or project role. The document never says whether that is intended, so the security change is larger than "operators" implies.

**Recommendation:** State the exact subject ("any authenticated principal" or a named role) and whether any project access is required. Align the title, summary, and the Security Hardening follow-up wording.

**Confidence:** High.

### R3 — High — The source read path remains unconstrained and the exposure is unstated

**Location:** Problem, Scope, Risks And Tradeoffs. Verified in `ingesters/sead_change_request/input_resolution.py::_load_source_bundle_from_path` and `IngestRequest.source`.

**Issue and impact:** The source is a caller-supplied path checked only for existence and `.xlsx`/`.xls` suffix. There is no containment. The previous revision made source containment a core requirement; this revision covers output only. `docs/proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md` exempts this operation from source constraints, but this proposal does not record that tradeoff. Any authenticated user can cause server-side reads of accessible Excel files and receive path or parser errors.

This finding is scoped to the caller-path input route. The composed in-memory path in [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) reads no caller-supplied path, which is why the proposal's `P-AC-1` now grants its permission exception only to that composed path and keeps `application:run_ingesters` on this route.

**Recommendation:** Either keep source containment under an approved root or uploaded reference, reusing `src/path_resolution`, or add the read exposure and the trust assumption to Risks And Tradeoffs.

**Confidence:** Medium. The severity depends on the deployment trust model and on whether other authenticated routes already expose equivalent reads.

### R4 — Medium — F1b downgraded: the response and manifest side is done; the client retry key is still missing

**Location:** `P-AC-5`; `frontend/src/types/ingester.ts::SubmissionContextInput`; `frontend/src/components/ingester/IngesterForm.vue::buildSubmissionContext`; `ingesters/sead_change_request/contracts.py::PendingConfirmationReport`.

**Issue and impact:** The prior finding's four contract points are now half-done: `IngestResponse` returns the effective `run_id` and `scope_name`, `sql_builder.py` records `run_id` in deploy-artifact metadata, and the UI displays it. Still open:

- `SubmissionContextInput` has no `run_id`, and `buildSubmissionContext` never sends one. The backend accepts `submission_context` as a free-form dict and `input_resolution.py::_resolve_run_id` honors a supplied `run_id`, so an API caller can retry today — but the UI cannot. Each UI rerun mints a fresh `uuid4()`.
- `PendingConfirmationReport.rerun_instruction` still says only "rerun with the same submission context" without naming the run ID.

So `P-AC-5`'s retry claim is satisfiable via the API but not through the product's own UI.

**Recommendation:** Add optional `run_id` to the frontend context type, mint it once per submission attempt and persist it with the form state, and name the run ID in the rerun instruction.

**Confidence:** High.

### R5 — Medium — F1a mostly resolved by the completed provider-scope proposal; the proposal text was not updated to match

**Location:** `P-AC-5`, Planning Handoff, Risks And Tradeoffs.

**Issue and impact:** The scope, key source, serialization, and fail-closed validation are implemented under [PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md). But this proposal still:

- writes `P-AC-5` without naming the scope ("the same stable SIMS source identity"); the scope is now `provider://<provider-code>/<provider-schema>` from the saved project pair;
- never links the completed proposal that defines the mechanism its Planning Handoff and `P-AC-5` depend on;
- does not record the residual cross-provider duplicate risk that the provider-scope proposal itself lists in its Risks.

**Recommendation:** Link the completed proposal, reword `P-AC-5` to "within one provider-schema SIMS scope, repeated bundle generation for the same declared business key reuses the assigned target ID," and note the reconciliation dependency.

**Confidence:** High.

### R6 — Medium — Managed output location, `output_folder`, and `output_path` semantics are undefined

**Location:** Proposed Design, `P-AC-2`. Verified in `backend/app/core/config.py`, `backend/app/services/ingester_service.py::ingest`, and `ingesters/sead_change_request/artifact_writer.py`.

**Issue and impact:** There is no ingester output-root setting. The only managed output pattern is project-scoped execution output (`backend/app/services/execute_service.py::resolve_output_target`). `IngestRequest.output_folder` is still accepted, and `IngestResponse.output_path` echoes it even though the ingester writes to `output_folder/bundle_name`. The proposal does not say whether `output_folder` is ignored, rejected, or treated as a subpath. Implementers can choose an arbitrary root, callers will not know where a timestamped bundle was written, and collision uniqueness and concurrent-run behavior are unspecified.

**Recommendation:** Name the managed root and its configuration setting, define `output_folder` handling, return the actual bundle directory, and require atomic exclusive directory creation with clear timestamp uniqueness.

**Confidence:** High.

### R7 — Medium — Task-plan Repository Findings are stale relative to the implemented provider-scope work

**Location:** `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md`, Repository Findings and `T0.3`.

**Issue and impact:** The task plan's basis is commit `0670d7d7` (2026-10-13), before provider-scope Phases 3–4. Its findings table still says the ingester "currently builds its primary signal from row fields" and leaves the sequence/identity questions open; `T0.3`'s "Current → required" row is likewise outdated. The task decomposition itself (`T1.1`–`T1.5`) still matches current code, and `T1.5`'s "same keys, changed non-key data" test is now feasible because `business_id` uses only declared keys.

**Recommendation:** Refresh the findings table and cite the provider-scope implementation so the implementer does not re-derive resolved facts.

**Confidence:** High.

### R8 — Low — Fallback identity paths can silently collide

**Location:** `backend/app/services/ingester_runtime.py::_build_identity_value`.

**Issue and impact:** `_build_identity_value` keeps the all-fields serialization for entities without declared keys, and on `BusinessKeyError` returns the bare `entity_name` — every row of that entity would share one identity value. The pre-SIMS key validator should make this unreachable for tracked entities, but the adapter fallback is a silent-collision shape.

**Recommendation:** Add a guard or an explicit fail within `T1.3`/`T1.5` scope.

**Confidence:** Medium. The validator ordering that would make this unreachable was not executed for this review.

### R9 — Low — Companion documents, alternatives, and filename are unchanged (prior F6/F7/F8)

**Location:** `docs/proposals/README.md`, `docs/proposals/CHANGE_REQUEST_INGESTER/README.md`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`; missing Alternatives Considered section; filename.

**Issue and impact:** The index row is still titled "Secure Ingester Filesystem And Destination Access" with a containment summary; the Change Request README still says "not ready to enable … Keep operations unavailable until required checks are enforced"; the route inventory still assigns containment to this proposal. No Alternatives section weighs a dedicated `create_change_request_bundle` action, a separate route, or a broader `operator` grant. The filename implied broad filesystem boundaries while the document is a narrow permission exception.

**Filename part resolved:** the topic was renamed to `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS` (folder and all three named documents) and every inbound reference was updated, so the path now matches the decision. The index row text, the Change Request README wording, the route inventory, and the missing Alternatives section remain open.

**Recommendation:** Update the index row and both references in the same change; add two or three sentences on why authentication-only is preferred.

**Confidence:** High.

## Suggested `P-AC-5` Rewrite

Current wording assigns a target ID to "the same stable SIMS source identity" without defining that identity. Now that the provider-scope proposal is implemented, the scope and key source are decided facts, so the criterion can name them:

> `P-AC-5` Within one provider-schema SIMS source scope (`provider://<provider-code>/<provider-schema>` from the project's bound provider pair), repeated bundle generation for the same declared business key reuses the assigned target ID. A caller-supplied `run_id` is reused for retries and is recorded in the response and the bundle manifest.

This keeps the testable part of the current criterion, removes the implied cross-provider guarantee, and points at the implemented mechanism instead of restating it.

## Planning Readiness

**Ready with minor revisions.** The prior review's blocking identity items (`P-AC-5` scope, key source, serialization, response traceability) are resolved by the completed provider-scope implementation, and the read-only target-database relaxation resolves the prior F2 blocker. What must change in the proposal before approval is now a smaller, mostly local set: the authorization subject (R2), the source-read decision (R3), the managed output root (R6), and the `P-AC-5` rewording with the provider-scope link (R5). The UI retry key (R4), the stale task-plan findings (R7), and the silent-collision guard (R8) should ride along in the same revision. Commit the uncommitted read-only relaxation. None of these reopens the design.

## Not Verified

- Runtime behaviour of SIMS batch replay when a run key is reused with a different payload. The conflict path exists in `resolve_identity_batch`, but it was not executed for this review.
- Whether the pre-SIMS key-validator ordering makes the R8 fallback unreachable.
- Whether existing projects map one-to-one to data providers, which determines how often the residual cross-provider duplicate risk actually occurs.
- The deployment trust model that determines the severity of R3.
- Any runtime behavior; no tests or live checks were run for this review.
