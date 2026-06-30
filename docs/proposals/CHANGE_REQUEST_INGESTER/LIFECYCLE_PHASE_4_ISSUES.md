# Lifecycle Phase 4 Issue Drafts

This document turns lifecycle implementation plan phase 4 into an issue-ready draft.

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 4

Status:

`Draft`

Title:

`feat(sead_change_request): define shared-data review ownership and operator routing for non-provider existing-row scenarios`

Problem:

Phase 3 existing-row provider update handling is implemented, but the shared-data path is still not defined as an explicit operator workflow.

Without a separate review and ownership contract, requests that affect shared terms can blur into provider-owned update handling and create inconsistent routing for new shared terms or corrections to existing ones.

Solution:

Define the shared-data review ownership and routing contract as a separate lifecycle path from provider-owned existing-row updates.

Make the operator-facing outcome explicit for shared-term requests, including where they are reviewed, how they are classified, and which requests remain out of scope for direct provider updates.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_UPDATE_SCOPING_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/UPDATE_HANDLING_FOR_EXISTING_ROWS.md`
- `ingesters/sead_change_request/orchestration.py`
- `ingesters/sead_change_request/result_builders.py`
- `backend/tests/ingesters/test_sead_change_request_orchestration.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`