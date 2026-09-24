# Change Request Ingester — Proposal Status Assessment

- Status: Current assessment
- Date: 2026-09-24
- Branch: `dev`
- Scope: `CHANGE_REQUEST_INGESTER` proposal set

## Recommended Overall Status

**Core implementation complete; follow-up proposals remain active.** This directory is a portfolio of related proposals and plans, not one change request with a single completion state. Delivery 1, frontend workflow integration, provider lifecycle work, and persisted submission defaults are implemented. Do not mark the entire portfolio complete: upstream PostgreSQL validation for the submission metadata work remains outstanding, and separate proposals still contain unresolved scope or ownership decisions.

## Status By Area

| Area | Status | Notes |
|---|---|---|
| Delivery 1 baseline and follow-ups | Complete | Closed and archived under `done/CHANGE_REQUEST_INGESTER_DELIVERY_1/`. |
| Frontend workflow integration | Complete | Issues 1–4 shipped in PR #456. Stable defaults were delivered separately in the submission metadata work. |
| Provider submission lifecycle | Complete | Implemented and recorded in the durable lifecycle documentation and archived proposal set. |
| Submission metadata and persisted defaults | Repository implementation complete; PostgreSQL validation pending | Code, focused tests, and target-model updates are recorded in [the proposal](./REFACTOR_SEAD_SUBMISSION_METADATA.md). Execution against the revised upstream schema is still unchecked in its task plan. |
| Shared-data review and operator contract | Draft; decision blocked | Ownership of review and approval, and the split from provider-owned updates, remain unresolved. |
| Ingester filesystem boundaries | Proposed | Separate security work; operations must remain disabled until the required path and authorization checks exist. |
| Stronger idempotency and next-delivery candidates | Candidate; undecided | Do not treat these as accepted delivery scope until a narrower proposal is selected. |

## Remaining Gates

1. **Submission metadata database validation:** apply the revised upstream DDL to a disposable PostgreSQL database, execute both artifact strategies, and verify the migration and generated relationships. Keep the task plan open until these checks have results.
2. **Shared-data ownership:** decide who owns review and approval before accepting the shared-data proposal.
3. **Next-delivery scope:** select and accept one candidate before creating an implementation plan for it.

## References

- Proposal README: [README.md](./README.md)
- Consolidated tracker (archived): [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md)
- Durable lifecycle rules: [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)
- Candidate backlog: [future/NEXT_DELIVERY_CANDIDATES.md](./future/NEXT_DELIVERY_CANDIDATES.md)
- Existing-row update proposal: [future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md)
- Shared-data review: [SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md)
