# Lifecycle Phase 3 Issue Drafts

This document turns lifecycle implementation plan phase 3 into issue-ready drafts.

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 3A

Status:

`Ready after shared-data governance owner and first-slice update allowlist decision`

Title:

`feat(sead_change_request): implement phase-3 existing-row update engine path with mutable-field boundaries and supersession planning`

Problem:

Phase 1 and Phase 2 lifecycle prerequisites are now implemented, but the existing-row provider update path is still missing.

Without an engine-level phase-3 slice, submissions that include provider-owned changes to existing rows cannot move from classification outcomes into deterministic decision paths for no-op, accepted update, and blocked outcomes.

The engine also needs an explicit first-slice allowlist so only approved entity families can enter the existing-row update path while the rest stay blocked.

Solution:

Implement the planning and orchestration path for existing-row updates using explicit mutable-field boundaries.

Treat unchanged reruns as no-op, route accepted updates as update candidates, and block ambiguous, disallowed, or out-of-slice updates with clear diagnostics and outcome accounting.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/UPDATE_HANDLING_FOR_EXISTING_ROWS.md`
- `ingesters/sead_change_request/planning.py`
- `ingesters/sead_change_request/preparation.py`
- `ingesters/sead_change_request/orchestration.py`
- `backend/tests/ingesters/test_sead_change_request_planning.py`
- `backend/tests/ingesters/test_sead_change_request_orchestration.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`

## Issue 3B

Status:

`Ready after Issue 3A contracts are stable`

Title:

`feat(sead_change_request): implement phase-3 SQL and artifact rendering for accepted existing-row provider updates`

Problem:

Even with phase-3 engine decisions in place, existing-row provider updates still cannot be delivered end to end until accepted update candidates produce explicit SQL and operator-facing artifacts.

Without a dedicated SQL/artifact slice, update-capable planning outcomes remain internal only and cannot be applied or reviewed consistently.

Solution:

Implement narrow SQL and artifact rendering for accepted existing-row updates, including clear diagnostics for no-op and blocked paths.

Keep the output contract explicit and constrained to accepted mutable-field updates, without broad merge behavior.

Files:

- `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/UPDATE_HANDLING_FOR_EXISTING_ROWS.md`
- `ingesters/sead_change_request/sql_builder.py`
- `ingesters/sead_change_request/package_builder.py`
- `ingesters/sead_change_request/artifact_writer.py`
- `ingesters/sead_change_request/result_builders.py`
- `backend/tests/ingesters/test_sead_change_request_sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_package_builder.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`
