# Handoff: Change Request Ingester State And Remaining Tasks

## Purpose

Provide one operational status view for the `CHANGE_REQUEST_INGESTER` proposal set.

This document consolidates what is complete, what is still draft or candidate, and what tasks remain open.

## Current State

- Delivery 1 baseline is closed and archived under `archive/closed_delivery_1/`.
- Delivery 1 follow-up issue slices are resolved or implemented on the current branch.
- Frontend UX integration CR is implemented, with one deferred metadata-defaults follow-up.
- Provider-update lifecycle policy gate is accepted through [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md).
- Lifecycle rules are promoted to durable docs at [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md).
- Lifecycle Phase 1 and Phase 2 prerequisites are implemented on the current branch, including outcome classification diagnostics and integration coverage.
- Existing-row update handling remains a candidate and is still downstream of lifecycle acceptance.
- Next-delivery capability list remains undecided and is not a committed delivery scope.

## Completed Work

- Delivery 1 implementation and hardening documents are closed artifacts.
- Delivery 1 follow-up issue slices are marked resolved or implemented in [archive/DELIVERY_1_FOLLOWUP_ISSUES.md](./archive/DELIVERY_1_FOLLOWUP_ISSUES.md).
- Frontend workflow integration is implemented in `FRONTEND_UX_INTEGRATION_CR.md` and tracked issue-by-issue in `FRONTEND_UX_INTEGRATION_ISSUES.md`.
- Ingester readability refactor plan is complete and explicitly stopped at a stable boundary.

## Key References

- Decision proposal: [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md)
- Durable lifecycle rules: [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)
- Proposal-era lifecycle baseline record: [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md)
- Lifecycle sequencing plan: [DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md)
- Lifecycle phase issue drafts: [LIFECYCLE_PHASE_1_2_ISSUES.md](./LIFECYCLE_PHASE_1_2_ISSUES.md)
- Lifecycle phase 3 issue draft: [LIFECYCLE_PHASE_3_ISSUE.md](./LIFECYCLE_PHASE_3_ISSUE.md)
- Existing-row update proposal: [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md)
- Candidate backlog scope: [NEXT_DELIVERY_CANDIDATES.md](./NEXT_DELIVERY_CANDIDATES.md)

## Next Actions

1. Record and carry forward lifecycle policy acceptance.
- Acceptance decision is complete for `DATA_PROVIDER_UPDATE_SCOPING_CR.md`.
- Durable lifecycle doc created: [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md).
- Promotion note completed: [LIFECYCLE_SPEC_PROMOTION_NOTE.md](./LIFECYCLE_SPEC_PROMOTION_NOTE.md).
- Lifecycle baseline promotion is complete; keep [LIFECYCLE_SPEC_PROMOTION_NOTE.md](./LIFECYCLE_SPEC_PROMOTION_NOTE.md) as the handoff record.

2. Complete lifecycle Phase 1 and Phase 2 implementation prerequisites.
- Track issue-ready work items in [LIFECYCLE_PHASE_1_2_ISSUES.md](./LIFECYCLE_PHASE_1_2_ISSUES.md).
- Phase 1 contracts are implemented: lifecycle metadata plus one-live-version invariant checks.
- Phase 2 contracts are implemented: outcome classification for `new_data`, `no_op`, `allowed_update`, `pending_review`, and `blocked`.
- Integration-level validation info now includes outcome-count diagnostics, with mutable-field scope coverage.

3. Prepare existing-row implementation slice after lifecycle prerequisites are complete.
- Track issue-ready scope in [LIFECYCLE_PHASE_3_ISSUE.md](./LIFECYCLE_PHASE_3_ISSUE.md).
- Confirm first entity set for mutable-field comparison.
- Confirm no-op rerun behavior and supersession rules in implementation tests.
- Keep ambiguous existing-row changes blocked or review-routed.

4. Define shared-data review ownership and path.
- Confirm authority owner for new shared-term requests.
- Confirm owner for corrections to existing shared terms.
- Confirm boundary between provider-owned reference updates and shared-row governance changes.

5. Close deferred frontend follow-up.
- Decide whether stable `sead_change_request` submission defaults should be stored in project metadata.

6. Re-prioritize undecided next-delivery candidates.
- Rollback support.
- Stronger idempotency and resubmission behavior.
- Change detection.
- More precise ordering if deferred constraints are insufficient.
- Verification semantics beyond placeholders.

## Recommended Execution Order (Risk And Dependency)

Use this as the short execution checklist for the six open tasks.

- [x] 1. Decide lifecycle policy acceptance boundary.
Reason: completed on 2026-06-30 and promoted to durable docs; this removed the highest ambiguity for downstream update behavior.

- [x] 2. Complete lifecycle Phase 1 and Phase 2 prerequisites.
Reason: completed on branch; metadata and classification contracts are now in code and tests.

- [ ] 3. Define shared-data review ownership and path.
Reason: closes governance risk early and prevents provider-owned and shared-data paths from blending.

- [ ] 4. Prepare and scope the first existing-row implementation slice.
Reason: depends on steps 1-3; safest point to lock mutable-field boundaries and no-op/supersession behavior.

- [ ] 5. Close the deferred frontend metadata-defaults follow-up.
Reason: lower data-integrity risk than lifecycle/governance items; can proceed once outcome contracts are stable.

- [ ] 6. Re-prioritize and select one next-delivery candidate slice.
Reason: portfolio-level planning step that should happen after lifecycle foundation and immediate follow-ups are settled.

Dependency guardrails:

- Do not start step 4 before steps 2-3 are complete.
- Do not lock the next accepted candidate (step 6) until steps 1-4 are resolved.

## Risks

- Existing-row update implementation may drift into SQL-first behavior if lifecycle acceptance and classification are not completed first.
- Shared-data governance may remain ambiguous if ownership and review routing are not assigned explicitly.
- Operator-facing outcomes may become inconsistent across backend and frontend if outcome contracts remain implicit.
- Candidate backlog can become accidental scope unless accepted slices are explicitly selected.

## Open Decisions

- Which team owns reviewed shared-data requests and approvals?
- Which existing-row entity families are first in scope for mutable-field update behavior?
- Should project YAML carry stable `sead_change_request` submission defaults?
- Which single candidate from `NEXT_DELIVERY_CANDIDATES.md` should become the next accepted proposal slice?

## Suggested Follow-Up Documents

- Keep lifecycle sequencing updates in `DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`.
- Keep issue-level execution details in dedicated issue docs or GitHub issues.
- Use [LIFECYCLE_SPEC_PROMOTION_NOTE.md](./LIFECYCLE_SPEC_PROMOTION_NOTE.md) as the promotion handoff for moving lifecycle rules into durable docs.
- Use [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) as the active lifecycle policy reference.
