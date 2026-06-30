# Lifecycle Phase 1 and 2 Issue Drafts

This document turns lifecycle implementation plan phases 1 and 2 into issue-ready drafts.

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 1

Status:

`Implemented on branch cr-ingester-final-work`

Title:

`feat(sead_change_request): add lifecycle metadata contracts and one-live-version invariant checks`

Problem:

The lifecycle policy is accepted, but the ingester contracts do not yet expose explicit lifecycle metadata structures for logical-record versions.

Without a contract-level invariant check, later implementation work can accidentally allow multiple live versions for the same logical record.

Solution:

Add lifecycle metadata contracts in the `sead_change_request` package and include a one-live-version invariant check utility at the contract layer.

Use this issue to establish stable building blocks for later planner and orchestration integration.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `ingesters/sead_change_request/contracts.py`
- `backend/tests/ingesters/test_sead_change_request_contracts.py`

## Issue 2

Status:

`Implemented on branch cr-ingester-final-work`

Title:

`feat(sead_change_request): classify submission outcomes for new/no-op/allowed/review/blocked paths`

Problem:

The implementation plan requires classification outcomes before SQL artifact generation, but outcome classes are not yet represented as an explicit ingester-facing contract.

Without this classification layer, blocked and pending-review scenarios are harder to trace and operator diagnostics remain inconsistent.

Solution:

Introduce explicit phase-2 outcome classification contracts and diagnostics payload shapes in the planning/preparation path.

Require tests for at least: new data, no-op, allowed update, pending review, and blocked outcomes.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `ingesters/sead_change_request/planning.py`
- `ingesters/sead_change_request/preparation.py`
- `ingesters/sead_change_request/result_builders.py`
- `backend/tests/ingesters/test_sead_change_request_planning.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`
