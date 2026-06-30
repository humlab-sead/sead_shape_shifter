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

Scenarios:

- A provider submits a row that points to a shared lookup already owned by SEAD. The request should resolve against the existing shared value instead of creating a duplicate shared lookup.
- A provider submits a correction for a shared term that SEAD owns. The request should route to the shared-data review path, not the provider-owned update path.
- A provider cannot find a matching shared value during submission. The request should remain uncommitted until a shared-data review or authority-backed reconciliation step resolves the lookup.
- A third-party authority exists for a shared concept. The workflow should prefer that authority when it is available and appropriate, while SEAD still owns the published shared-data record.

Candidate workflows:

1. Current internal reconciliation workflow.

	Shape Shifter performs reconciliation inside the ingester and routes shared-data cases to SEAD review. This is the current boundary and is not published to data providers.

2. Provider-facing reconciliation service.

	A future provider-facing view or service lets data providers reconcile against shared lookups before data is sent to SEAD. This reduces failed submissions, but it should still respect SEAD ownership and avoid duplicate shared values.

3. Third-party authority-backed lookup workflow.

	For shared concepts with trusted external authorities, the provider can select an authority-backed match before submission. SEAD then records the resolved shared value without duplicating the lookup.

4. Shared-data request workflow.

	When no safe match exists, the provider submits a shared-data request for review. SEAD owns the decision and publication of the shared lookup, and the result can later be reused by providers.

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