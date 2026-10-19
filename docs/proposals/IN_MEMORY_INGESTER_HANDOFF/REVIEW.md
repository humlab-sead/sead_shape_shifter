# Proposal Review: Hand Normalized Tables To The Ingester In Memory

## Review Basis

| Item | Value |
|---|---|
| Reviewed document | [IN_MEMORY_INGESTER_HANDOFF.md](./IN_MEMORY_INGESTER_HANDOFF.md) |
| Related documents | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) and its [REVIEW.md](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/REVIEW.md) |
| Review date | 2026-10-19 |
| Revision reviewed | Working tree on branch `dev`, commit `667181e7` plus the uncommitted `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS` revision |
| Method | Read the proposal and the current source: `src/dispatch.py`, `src/normalizer.py`, `src/workflow.py`, `backend/app/ingesters/protocol.py`, `backend/app/services/execute_service.py`, `backend/app/services/ingester_service.py`, `backend/app/authorization/dependencies.py`, `backend/app/models/ingester.py`, `ingesters/sead_change_request/input_resolution.py`, `ingesters/sead_change_request/ingester.py`. No tests were run and no downstream timezone rendering was verified. |

This record holds review advice only. It is not an approval, and it does not change the proposal.

Finding IDs in this review are local to this document. References to `R3` mean the finding in the sibling [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS review](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/REVIEW.md), not a finding here.

## Overall Assessment

The core decision is sound and well scoped. The fidelity analysis of the Excel round trip matches the code, the design is additive, and the `P-AC-*` set is mostly observable. The rejected alternatives are argued with evidence rather than preference.

Principal concerns:

- The composition helper has no stated consumer and no pinned owner, so its contract is fixed before the caller exists.
- Several "reuse the existing path" claims are too loose to verify, and they are exactly what the acceptance criteria promise to preserve.

`C1` was resolved during this review; see Resolved Findings.

## Resolved Findings

| Finding | Status | Basis |
|---|---|---|
| C1 — permission conflict with the target-bundle proposal | Resolved by decision | `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS` `P-AC-1` now grants the exception only to bundle creation from an authorized saved project with no caller-supplied source path, and keeps `application:run_ingesters` on the upload route. This proposal's `P-AC-8` and Planning Handoff now inherit that decision instead of fixing the permission here. |

## Findings

### High

#### H1 — The composition helper has no consumer

**Location:** Proposed Design §4, `P-AC-5`, `P-AC-7`.

**Issue:** No backend code builds a `SourceTableBundle` today (`rg source_bundle backend/app` returns no matches), and adding a route is a non-goal. `ShapeShiftService` provides preview and batch preview only; `ExecuteService` dispatches and stops. The delivered helper is therefore unexercised outside tests, and its signature is fixed before the route that will call it — including whether it must report progress, return an artifact path, or split validation from ingestion.

**Impact:** The helper's shape cannot be confirmed against its only future caller, and `P-AC-5` and `P-AC-7` become test-only guarantees.

**Recommendation:** Either name the first consumer, even as a `TBD` route modelled on `POST /ingesters/{key}/ingest`, and sketch the call boundary; or state plainly that this is infrastructure-only work validated at service level, with the route as a separate decision. Do not leave it implied.

**Confidence:** High.

#### H2 — "Existing configuration path" is not pinned, so `P-AC-8` can fail silently

**Location:** Proposed Design §4 step 3; `P-AC-8` ("supplies the same trusted project context and runtime dependencies as file input").

**Issue:** `IngesterService` supplies two separate things that must be reused. `_trusted_project_context()` builds the provider-schema scope, fixed provider row, and business keys from the authorized project. `_create_config()` calls `inject_ingester_runtime_dependencies` and `inject_ingester_database_dependencies`. A new helper that builds `IngesterConfig` itself would produce a run that passes validation but silently lacks provider scope or injected dependencies.

**Impact:** This defeats the criterion that makes the table path an acceptable substitute for the file path.

**Recommendation:** Name the owner. Add the table methods to `IngesterService` and reuse `_create_config()` and `_trusted_project_context()`. Add a check that the same config injection and trusted context reach the ingester on both paths.

**Confidence:** High.

#### H3 — The authorization mechanism for a non-route helper is unspecified

**Location:** Proposed Design §4 step 1; `P-AC-8`.

**Issue:** Both gates are FastAPI dependencies. `require_application_action(Action.RUN_INGESTERS)` and `require_ingester_project(Action.EXECUTE)` the latter read `project_name` from the raw request body. Neither is callable from a service. `ExecuteService.execute_workflow` solves this differently: it accepts an `AuthorizedResource` and re-checks action, resource type, and lifecycle state inline.

**Impact:** "The helper requires both" is not implementable as stated without inventing a third authorization style in the service layer.

**Recommendation:** State the pattern explicitly. The helper receives an already-authorized principal and authorized resource and re-checks them the way `ExecuteService` does, leaving dependency wiring to the future route. This makes `P-AC-8` testable without a route.

**Confidence:** High.

### Medium

#### M1 — `R3` is cited to the wrong document

**Location:** line 32 and the Non-Goals bullet.

**Issue:** The proposal says the `CHANGE_REQUEST_TARGET_BUNDLE_ACCESS` proposal records the source-read exposure as `R3`. That document does not contain `R3`. The identifier is defined in [the sibling review](../CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/REVIEW.md) under "R3 — High — The source read path remains unconstrained and the exposure is unstated", and its `F4` row points there.

**Recommendation:** Cite `REVIEW.md` for `R3` and keep the proposal link for the broader topic.

**Confidence:** High.

#### M2 — The header presents the target state as current

**Location:** lines 3–7.

**Issue:** "Ingestion: backend helper → normalize → tables → ingester → deploy artifact" describes a helper that does not exist. The current operator path is dispatch `xlsx` → download → upload → ingester, which is what the Problem section correctly describes. Current and planned state must be distinguishable.

**Recommendation:** Label the two lines `Current:` and `Target:`, or move the target diagram into Proposed Design.

**Confidence:** High.

#### M3 — `P-AC-4` uses "safe names" while Excel actively rewrites names

**Location:** `P-AC-4`; Testing bullet 2.

**Issue:** `OpenpyxlExcelDispatcher._clean_sheet_name` replaces `:\/?*[]` and truncates to 31 characters, and duplicate cleaned names raise. The `xlsx` dispatcher writes sheet names through unchanged. "Safe names" carries real weight in the criterion but has no stated boundary, so the parity fixture cannot be constructed from the document.

**Recommendation:** Define safe as non-empty, at most 31 characters, free of `:\/?*[]`, and unique after cleaning. Record that names outside this set are an intentional divergence, not a parity failure.

**Confidence:** High.

#### M4 — Project-specification validation is silently dropped

**Location:** Proposed Design §4 step 2.

**Issue:** `ExecuteService.execute_workflow` runs `CompositeProjectSpecification` validation before calling `workflow()` when `request.run_validation` is set. The described helper goes load → `ProjectMapper.to_core()` → normalize. Ingester validation covers the target model, not project configuration. Whether the project check survives on the composed path is unstated.

**Recommendation:** State the decision, either always, on request, or not at all, instead of leaving a gap between the two paths. The current check is optional, so a documented difference may be acceptable as long as it is chosen.

**Confidence:** Medium.

#### M5 — `P-AC-8` combines three independent obligations

**Location:** `P-AC-8`.

**Issue:** Identical post-preparation checks, both permissions, and identical trusted context and dependencies are three separately testable outcomes in one identifier. A partial pass cannot be represented, and phase mapping becomes coarse.

**Recommendation:** Split into separate criteria, for example checks parity, authorization, and configuration parity.

**Confidence:** High.

### Low

#### L1 — A documented divergence contradicts an unqualified equivalence claim

**Location:** handoff table row `data_table_index`; `P-AC-4`.

**Issue:** The adapter deliberately keeps an entity named `data_table_index` that the Excel reader drops. `P-AC-4` states equivalence with no exception.

**Recommendation:** Add "subject to the documented divergences in §3" to `P-AC-4`.

**Confidence:** High.

#### L2 — Timezone rejection needs an owner

**Location:** Risks And Tradeoffs; Open Questions.

**Issue:** "Reject unsupported values clearly" names no mechanism or location. If downstream rendering cannot handle timezone-aware values, the natural place to reject is the adapter or `_build_source_bundle`.

**Recommendation:** Name the rejecting layer so the phase plan does not rediscover the decision.

**Confidence:** Medium.

## Planning Readiness

**Ready with minor revisions.**

`C1` is resolved by decision across both proposals.

H1, H2, and H3 remain as design clarifications, not blockers: the helper's owner, authorization shape, and first consumer must be stated before a task plan is written, but none of them reopens the core decision that the in-memory tables replace the Excel handoff.

M1 through M5 and L1 and L2 are localized text fixes.

The design direction does not need to change.
