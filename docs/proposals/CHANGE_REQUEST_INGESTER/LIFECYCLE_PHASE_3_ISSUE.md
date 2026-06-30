# Lifecycle Phase 3 Issue Draft

This document turns lifecycle implementation plan phase 3 into an issue-ready draft.

The issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 3

Status:

`Ready after shared-data governance owner and first-entity scope decision`

Title:

`feat(sead_change_request): implement existing-row provider update path with mutable-field boundaries and supersession`

Problem:

Phase 1 and Phase 2 lifecycle prerequisites are now implemented, but the existing-row provider update path is still missing.

Without this phase-3 slice, submissions that include provider-owned changes to existing rows cannot move from classification outcomes into a controlled update path with deterministic no-op behavior and safe mutation boundaries.

Solution:

Implement the narrow existing-row update path defined in the lifecycle phase plan and the existing-row update proposal.

Use explicit mutable-field boundaries for supported entities, treat unchanged reruns as no-op, supersede prior live versions only for accepted updates, and block ambiguous or disallowed updates with clear diagnostics.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/UPDATE_HANDLING_FOR_EXISTING_ROWS.md`
- `ingesters/sead_change_request/planning.py`
- `ingesters/sead_change_request/preparation.py`
- `ingesters/sead_change_request/orchestration.py`
- `ingesters/sead_change_request/sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_planning.py`
- `backend/tests/ingesters/test_sead_change_request_orchestration.py`
- `backend/tests/ingesters/test_sead_change_request_sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`
