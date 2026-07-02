# Frontend UX Integration Issue Drafts

This document turns the frontend UX integration CR into GitHub-ready issue drafts.

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 1

Status:

`Implemented in PR #456`

Title:

`feat(frontend): add explicit sead_change_request ingestion workflow`

Problem:

The frontend currently treats ingester selection too generically for `sead_change_request`.

That hides an important product difference: this ingester produces a change-request bundle and may require more operator input and clearer run-state handling than the legacy SEAD path.

Solution:

Add an explicit frontend workflow branch for `sead_change_request`.

The UI should make clear that this flow is a change-request workflow rather than a fire-and-forget export path.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_ISSUES.md`
- `frontend/src/**`

## Issue 2

Status:

`Implemented in PR #456`

Title:

`feat(frontend): collect submission context for sead_change_request`

Problem:

The ingester needs explicit submission metadata such as datatype, identifier, description, and related change-request context.

Without a focused form, those values are either hidden, implicit, or too easy to enter inconsistently.

Solution:

Add a focused submission-context form for `sead_change_request`.

The form should make the required operator inputs explicit, reviewable, and clearly separated from generic ingestion controls.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_ISSUES.md`
- `frontend/src/**`

## Issue 3

Status:

`Implemented in PR #456`

Title:

`feat(frontend): show blocked confirmation state and rerun guidance`

Problem:

`sead_change_request` can stop in a pending-confirmation state where no artifact bundle is generated.

If the frontend collapses that into a generic failure, the operator does not know whether to fix input data, wait for confirmation, or rerun after an external action.

Solution:

Add a distinct blocked pending-confirmation state in the frontend.

Show the confirmation summary, the fact that no bundle was generated, and the rerun guidance required by the ingester workflow.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_ISSUES.md`
- `frontend/src/**`

## Issue 4

Status:

`Implemented in PR #456`

Title:

`feat(frontend): present sead_change_request artifact outcomes`

Problem:

On success, operators need to understand what the ingester produced without reading raw backend payloads or inspecting files directly.

That includes the bundle name, deploy strategy, non-revertible status, the main artifact outputs, and any execution or handoff guidance tied to the selected deploy strategy.

Solution:

Add an operator-facing success summary for `sead_change_request` results.

The summary should present the key artifact outcomes, relevant warnings, and the execution or handoff guidance the operator needs in a compact, understandable frontend view.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_ISSUES.md`
- `frontend/src/**`

## Issue 5

Status:

`Future`

Title:

`feat(project-metadata): persist stable sead_change_request submission defaults`

Problem:

Some `sead_change_request` operator inputs are stable project defaults rather than true per-run decisions.

If those values stay transient in the run form, reruns can drift and operators must keep re-entering context that belongs with the project configuration.

Solution:

Add a follow-up change request that evaluates which `sead_change_request` submission defaults should be stored in project YAML.

Prefer an ingester-specific metadata subsection over adding flat workflow-specific fields to the generic metadata editor.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/done/FRONTEND_UX_INTEGRATION_ISSUES.md`
- `frontend/src/components/MetadataEditor.vue`
- `backend/app/models/project.py`
- `backend/app/api/v1/endpoints/projects.py`