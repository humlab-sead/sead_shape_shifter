# Proposal Review: Allow Operators To Create Change Request Target Bundles

## Review Basis

| Item | Value |
|---|---|
| Reviewed document | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) |
| Related plan | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) |
| Related task plan | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md) |
| Review date | 2026-10-19 |
| Revision reviewed | Branch `dev`, commit `50a7e5bc`, clean working tree. The read-only target-database relaxation is now committed, and the topic was renamed to `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS`. |
| Supersedes | The 2026-10-18 review of revision `fc539a3f` |
| Method | Read the proposal, phase plan, task plan, and current source, including authorization dependencies, the ingester endpoint, the artifact writer, and the identity adapter. No tests were run and no deployment trust model was verified. |

This record replaces the 2026-10-18 review. It holds review advice only. It is not an approval, and it does not change the proposal, the phase plan, or the task plan.

## Overall Assessment

Three changes since the prior review move this proposal forward:

- The proposal was narrowed: the permission exception now applies only to the composed in-memory path from [Hand Normalized Tables To The Ingester In Memory](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), and the caller-path source route explicitly keeps `application:run_ingesters`. That removes the prior revision's expansion of the unconstrained source read. The previous review's `R3` is downgraded accordingly.
- The target-database rule is now committed. `P-AC-3` permits read-only verification queries and forbids target-row writes and `nextval`, which matches `_verify_provider_row` in `ingesters/sead_change_request/ingester.py`. The prior `F2` blocker stays resolved.
- The proposals index row and the topic folder name now match the decision, and `require_ingester_project(Action.EXECUTE)` is already applied to the `sead_change_request` ingest route. The latter changes the effective authorization subject and is the largest new problem in this revision.

The proposal is not implemented. `backend/app/api/v1/endpoints/ingesters.py` still applies `RUN_INGESTERS` to both routes, `ingesters/sead_change_request/artifact_writer.py` still removes an existing same-name bundle directory, and Phase 1 tasks `T1.1`–`T1.5` are unchecked. No approval is recorded in the proposal's Status section.

Principal remaining concerns: the proposal describes an authorization subject that the shipped project gate does not produce (`R2`); the phase plan declares no dependency although the proposal's only criterion needs an unimplemented proposal (`R10`); the managed output root and run-folder uniqueness are still undefined, and current naming is date-only (`R6`); the Security Hardening Follow-up documents still require no target-database connection (`R11`); `P-AC-5` still does not name the SIMS scope (`R5`); and the UI cannot supply the `run_id` a retry needs (`R4`).

## Prior Findings Status

| Prior finding | Status | Basis |
|---|---|---|
| R2 — authorization subject | Open and now contradicted by shipped code | `require_ingester_project(Action.EXECUTE)` was added to the ingest route after the prior review. See R2. |
| R3 — source read path | Narrowed out of scope | The caller-path route keeps its gate, so this proposal no longer widens that read. The residual exposure is tracked only by a review ID. See R3 and R12. |
| R4 — client `run_id` | Open | No frontend field, no value in the request, no run ID in the rerun instruction. See R4. |
| R5 — `P-AC-5` scope | Partially resolved | The provider-scope proposal is now linked in Proposed Design; the criterion itself is unchanged. See R5. |
| R6 — managed output root | Open | No output-root setting; the writer still deletes an existing bundle. See R6. |
| R7 — stale task-plan findings | Open, plus a new internal contradiction | Still based on `0670d7d7`; the plan is labelled both validated and blocked. See R7 and R10. |
| R8 — fallback identity collision | Open | Unchanged. See R8. |
| R9 — companion documents and alternatives | Partially resolved | Index row and filename fixed; route inventory, Change Request README, Security Hardening, and Alternatives remain. See R9 and R11. |

## Open Findings

### R2 — High — The described authorization subject is not what the route will enforce

**Location:** Status, Summary, Problem, Scope, Non-Goals, `P-AC-1`. Verified in `backend/app/api/v1/endpoints/ingesters.py`, `backend/app/authorization/dependencies.py`, `backend/app/authorization/policy.py`.

**Issue and impact:** The ingest route now carries `require_ingester_project(Action.EXECUTE)` (`ingesters.py:20,72`). That dependency reads the top-level `project_name`, authorizes `project:execute`, and raises 404 when the principal has no matching grant (`dependencies.py:176-207`). `policy.py:26` gives the `operator` deployment role only `READ_ALL_SHARED_SOURCES`, `MANAGE_SHARED_SOURCES`, and `RUN_INGESTERS`; `project:execute` comes from the `executor` or `owner` project role, the `project_maintainer` deployment role, or `admin`.

So after the proposed change the effective subject is "an authenticated principal holding `project:execute` on the named saved project", not "any authenticated operator". An `operator` who holds only `RUN_INGESTERS` would still be denied. The title, Summary, and `P-AC-1` also treat project authorization as out of scope, but it is already enforced for this key. `PH1-AC-1` repeats the claim without the saved-project qualifier.

**Recommendation:** State the subject as it will be enforced and decide explicitly whether the project gate stays. If it stays, reword the title, Summary, and `P-AC-1` to "authenticated principal with `project:execute` on the authorized saved project". If "any authenticated principal" is genuinely intended, that requires changing or bypassing `require_ingester_project` for this key, which is a separate design with its own risk section.

**Confidence:** High.

### R10 — High — The phase plan declares no dependency, but the only criterion needs an unimplemented proposal

**Location:** Proposal Status and `P-AC-1`; phase plan "Depends On" and `PH1-AC-1`; task plan Readiness and Validation.

**Issue and impact:** `P-AC-1` is scoped to the composed in-memory path from [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), which is still "Proposed feature". `ingesters/sead_change_request/ingester.py:209` still defines `ingest(self, excel_file: Path | str, ...)`, and no composed normalization-to-ingester helper exists under `backend/app/`. The phase plan says "Depends On: None; this is a single-phase change", and `PH1-AC-1` drops the "no caller-supplied source path" qualifier, so the phase claims more than the proposal. The task plan simultaneously says "Readiness: Validated … ready for implementation handoff" and "No baseline tests were run: the phase is blocked".

An implementer following the phase plan cannot satisfy `PH1-AC-1`; removing `RUN_INGESTERS` from the existing route would satisfy the criterion only by widening the caller-path route the proposal excludes.

**Recommendation:** Record the handoff feature as a blocking dependency with its own readiness state, or deliberately bring the caller-path route into scope. Restore the qualifier in `PH1-AC-1`. Remove the contradictory validated/blocked labels from the task plan.

**Confidence:** High.

### R3 — Medium — The source read exposure is out of scope but has no owner outside this review

**Location:** Problem, Scope, Non-Goals, Risks And Tradeoffs. Verified in `ingesters/sead_change_request/input_resolution.py::_load_source_bundle_from_path` and `IngestRequest.source`.

**Issue and impact:** The revision keeps bundle creation from a caller-supplied path behind `application:run_ingesters`, so this proposal no longer widens that read. That is the correct containment of scope and shipped behavior is unchanged.

What remains is ownership. The unconstrained read is still present: `_load_source_bundle_from_path` checks existence and an `.xlsx`/`.xls` suffix only. The proposal references it as "the read exposure recorded as `R3` in [REVIEW.md](./REVIEW.md)". A review finding is advice, not a tracked decision, and its meaning changes whenever the review is replaced — as this record replaces the previous one. `IN_MEMORY_INGESTER_HANDOFF` uses the same reference.

**Recommendation:** State the condition in the proposal ("the caller-path read stays unconstrained until source resolution is contained") and point at an issue or decision document for the work. See R12.

**Confidence:** High. The severity of the exposure itself is unchanged; this finding is about where the open decision lives.

### R6 — Medium — Managed output root is undefined, and current naming cannot produce a unique run folder

**Location:** Proposed Design, `P-AC-2`. Verified in `backend/app/services/ingester_service.py::ingest`, `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`, and `ingesters/sead_change_request/contracts.py::resolve_bundle_name`.

**Issue and impact:** There is no ingester output-root setting. The only managed output pattern is project-scoped execution output (`backend/app/services/execute_service.py::resolve_output_target`). `ingest` still passes `request.output_folder` into the ingester config and echoes it as `output_path` (`ingester_service.py:157,179`).

Current bundle naming also cannot meet `P-AC-2`. `resolve_bundle_name` returns `<YYYYMMDD>_DML_<datatype>_<identifier>` (`contracts.py:565`) — a date, not a UTC timestamp with a time component — and the writer calls `shutil.rmtree` on an existing directory before writing (`artifact_writer.py:19-24`). Two runs of the same submission on one day therefore collide by construction, and the current behavior deletes the earlier bundle, which is exactly what `P-AC-2` forbids.

**Recommendation:** Name the managed root and its configuration setting, define whether `output_folder` is ignored, rejected, or a subpath, make the run folder unique per run (UTC timestamp with time, or the effective run ID), require exclusive creation with no deletion (`exist_ok=False`), and return the actual bundle directory in `output_path`.

**Confidence:** High.

### R11 — Medium — The Security Hardening Follow-up still requires no target-database connection

**Location:** [Security Hardening Follow-up phase plan](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) Phase 4 focus, `PH4-AC-3`, and cross-phase rules; [Security Hardening Follow-up](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md) `P-AC-2`; this proposal's `P-AC-3` and Planning Handoff.

**Issue and impact:** The Security Hardening documents state that Change Request target-bundle creation "makes no target-database connection or write". `P-AC-3` now permits read-only verification queries and the provider-scope cutover requires them. Two documents that both govern this operation specify opposite behavior, and the proposal's handoff only asks for later alignment.

**Recommendation:** Update the Security Hardening phase plan and proposal in the same change, or state here that their Phase 4 wording is superseded by `P-AC-3`.

**Confidence:** High.

### R5 — Medium — The completed provider-scope proposal is now linked, but `P-AC-5` is unchanged

**Location:** `P-AC-5`, Planning Handoff, Risks And Tradeoffs.

**Issue and impact:** Proposed Design now links [PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md), which resolves the missing-link part of this finding. Still open:

- `P-AC-5` says "the same stable SIMS source identity" without naming the scope; the scope is `provider://<provider-code>/<provider-schema>` from the saved project pair.
- The residual cross-provider duplicate risk listed in the provider-scope proposal's Risks is not recorded here.

**Recommendation:** Rewrite `P-AC-5` using the wording in the section below and note the reconciliation dependency.

**Confidence:** High.

### R4 — Medium — The client retry key is still missing from the UI

**Location:** `P-AC-5`; `frontend/src/types/ingester.ts:15-25` (`SubmissionContextInput`); `frontend/src/components/ingester/IngesterForm.vue:897-913` (`buildSubmissionContext`); `ingesters/sead_change_request/contracts.py:315` (`PendingConfirmationReport.rerun_instruction`).

**Issue and impact:** `SubmissionContext` accepts `run_id` (`contracts.py:95`) and `IngestResponse` returns it (`types/ingester.ts:82`), so an API caller can retry with a stable run ID today. The product UI cannot: `SubmissionContextInput` has no `run_id` field and `buildSubmissionContext` never sends one, so each rerun mints a fresh `uuid4()`. `rerun_instruction` also names only the submission and project, not the run ID.

So `P-AC-5`'s retry claim is satisfiable via the API but not through the product's own UI.

**Recommendation:** Add optional `run_id` to `SubmissionContextInput`, mint it once per submission attempt and persist it with the form state, and name the run ID in the rerun instruction.

**Confidence:** High.

### R7 — Medium — Task-plan Repository Findings are stale and internally contradictory

**Location:** `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md`, Repository Findings, `T0.3`, Readiness, and Validation And Testing.

**Issue and impact:** The findings are still based on commit `0670d7d7` (2026-10-13) and state that the ingester "currently builds its primary signal from row fields", although `_build_identity_value` now uses `business_id_for_row` for entities with declared keys (`backend/app/services/ingester_runtime.py:279-295`). The findings also omit `require_ingester_project`, which now gates the route; `T0.3`'s "Current → required" row describes the superseded behavior. The document labels itself validated and blocked at the same time (see R10).

**Recommendation:** Refresh the findings from current source, cite the provider-scope implementation and the project dependency, and resolve the readiness contradiction.

**Confidence:** High.

### R8 — Low — Fallback identity paths can silently collide

**Location:** `backend/app/services/ingester_runtime.py::_build_identity_value` (`ingester_runtime.py:279-295`).

**Issue and impact:** On `BusinessKeyError` the adapter logs a warning and returns the bare `entity_name`, so every row of that entity would share one identity value. Entities without declared keys also keep the all-fields serialization. The pre-SIMS key validator should make the first case unreachable for tracked entities, but the fallback is a silent-collision shape.

**Recommendation:** Add a guard or an explicit fail within `T1.3`/`T1.5` scope.

**Confidence:** Medium. The validator ordering was not executed for this review.

### R9 — Low — Companion documents and alternatives

**Location:** `docs/proposals/CHANGE_REQUEST_INGESTER/README.md:29`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md:226-242`; missing Alternatives Considered section.

**Issue and impact:** The proposals index row and the filename are now correct, so those parts are resolved.

Remaining:

- The Change Request README still says "Proposed; not ready to enable … Keep operations unavailable until required checks are enforced."
- The route inventory still says the ingester routes "accept no project locator" and that a project-scoped run "needs a project locator plus `project:execute`". Both are contradicted by the shipped `require_ingester_project` dependency and the top-level `project_name` in the request bodies.
- The route inventory still assigns containment to this proposal, which now scopes containment out.
- No Alternatives section weighs a dedicated `create_change_request_bundle` action, a separate route, or an `operator`-only grant.

**Recommendation:** Update both references in the same change and add two or three sentences on the rejected alternatives.

**Confidence:** High.

### R12 — Low — The proposal defers a product rule to a review finding ID

**Location:** Non-Goals ("until the read exposure recorded as `R3` in [REVIEW.md](./REVIEW.md) is closed"), Planning Handoff.

**Issue and impact:** Review findings are advisory and are renumbered or reworded whenever a review is replaced; this record already changes the context around `R3`. A proposal should not make a review artifact the source of a gate condition.

**Recommendation:** Restate the condition directly in the proposal and point at an issue or decision document for tracking.

**Confidence:** High.

## Suggested Criterion Rewrites

### `P-AC-1`

The current wording promises a subject the route does not produce. A wording that matches the shipped project gate:

> `P-AC-1` Bundle creation for an authorized saved project through the composed in-memory path requires an authenticated principal holding `project:execute` on that project and does not require `application:run_ingesters`; unauthenticated callers are rejected. Bundle creation from a caller-supplied source path keeps its current `application:run_ingesters` requirement until that read path is constrained.

### `P-AC-5`

Current wording assigns a target ID to "the same stable SIMS source identity" without defining that identity. The provider-scope implementation fixes the scope and key source, so the criterion can name them:

> `P-AC-5` Within one provider-schema SIMS source scope (`provider://<provider-code>/<provider-schema>` from the project's bound provider pair), repeated bundle generation for the same declared business key reuses the assigned target ID. A caller-supplied `run_id` is reused for retries and is recorded in the response and the bundle manifest.

This keeps the testable part of the current criterion, removes the implied cross-provider guarantee, and points at the implemented mechanism instead of restating it.

## Planning Readiness

**Revision required.** The identity questions are closed by the completed provider-scope implementation, and the read-only target-database rule is committed. Before approval, the proposal must resolve four local items and one cross-document conflict:

1. Decide the authorization subject and align the title, Summary, `P-AC-1`, and `PH1-AC-1` with the shipped `project:execute` gate (`R2`).
2. Record the composed in-memory path as a blocking dependency, or bring the caller-path route into scope (`R10`).
3. Name the managed output root and make run-folder naming unique and non-destructive (`R6`).
4. Rewrite `P-AC-5` with the provider-schema scope (`R5`).
5. Reconcile the Security Hardening Follow-up wording that still forbids a target-database connection (`R11`).

The UI retry key (`R4`), the stale task-plan findings (`R7`), the fallback-collision guard (`R8`), the companion-document updates (`R9`), and the review-ID dependency (`R12`) should ride along in the same revision. None of these reopens the core design.

## Revision Applied After This Review

The developer applied part of this advice on 2026-10-19, after the review was recorded. The findings above describe the reviewed revision and are kept unchanged as the record of it.

| Finding | Change applied |
|---|---|
| `R2` | The proposal title, Status, Summary, Problem, Scope, Non-Goals, Current Behavior, Proposed Design, Risks, Testing, `P-AC-1`, and Planning Handoff now name the enforced subject: an authenticated principal holding `project:execute` on the authorized saved project. The phase plan and Phase 1 task plan mirror it. |
| `R10` | The proposal Status names `IN_MEMORY_INGESTER_HANDOFF` as a blocking dependency. The phase plan's "Depends On", `PH1-AC-1`, and readiness, plus the task plan's readiness and `PH1-AC-1`, now record that block and no longer claim the phase is ready. |
| `R11` | The Security Hardening Follow-up `P-AC-2`, its phase plan Current Position, Phase 4 focus, `PH4-AC-3`, `VM-4.3`, and cross-phase rule now permit read-only verification queries and forbid target writes and sequence allocation. |
| `R12` | The proposal and the in-memory handoff now name [Ingester Authorization](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) as the owner of source path containment instead of pointing at review finding `R3`. |
| `R6` | The proposal, phase plan, and task plan now name an `INGEST_OUTPUT_DIR` managed root and a run layout of `<INGEST_OUTPUT_DIR>/<UTC timestamp>_<run_id>/<bundle_name>/...`. The bundle name, `cr_name`, SQL file names, and `\copy` paths are unchanged, so the artifact contract holds. `output_folder` is ignored for this ingester, `output_path` returns the written bundle directory, and creation is exclusive with the `shutil.rmtree` branch removed. |
| `R4` | The proposal adds the operator run-ID rule: one ID per submission attempt, reused for validation, ingestion, and retries, held in the ingester store, and reset when the submission identity changes or a bundle is written. `P-AC-5` states the rule. The task plan adds `T1.6` and `V-6` over `SubmissionContextInput`, the store, `buildSubmissionContext`, and the rerun instruction. |
| `R9` (partial) | The proposals index row now matches the revised title and subject. |

Still open after this revision: `R5`, `R7`, `R8`, and the remaining parts of `R9`.

## Not Verified

- Runtime behaviour of SIMS batch replay when a run key is reused with a different payload. The conflict path exists in `resolve_identity_batch`, but it was not executed for this review.
- Whether the pre-SIMS key-validator ordering makes the `R8` fallback unreachable.
- Whether existing projects map one-to-one to data providers, which determines how often the residual cross-provider duplicate risk actually occurs.
- The deployment value of `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE`. If it is enabled and a project carries an `everyone` grant, an authenticated principal without an individual grant could satisfy `project:execute`, which changes how `R2` should be worded.
- Whether any deployment currently assigns `operator` without a project role, which determines how many existing operators would still be denied after the change.
- Any runtime behavior; no tests or live checks were run for this review.
