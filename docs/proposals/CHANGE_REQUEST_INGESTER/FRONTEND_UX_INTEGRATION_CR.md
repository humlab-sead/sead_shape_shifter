# Proposal: Sead Change Request Frontend UX Integration

## Status

- Implemented in the `dev` working tree and awaiting commit/review
- Scope: frontend workflow integration for `sead_change_request`
- Goal: give operators a usable frontend flow for the user interaction that this ingester requires

## Current Delivery Status

The current uncommitted `dev` branch work covers the main frontend workflow in this change request.

Implemented in the current working tree:

- explicit `sead_change_request` workflow selection and operator-facing workflow copy
- focused submission-context form inputs and deploy-strategy selection
- distinct pending-confirmation state and rerun guidance during validation and ingestion
- operator-facing deploy artifact summary and handoff guidance

Still deferred:

- persisting stable `sead_change_request` submission defaults in project metadata

## Summary

The `sead_change_request` ingester is not just a backend output format.

It requires user-supplied submission metadata, clear handling of blocked confirmation states, and understandable operator feedback around artifact generation and reruns. That means it needs a dedicated frontend workflow rather than being treated as a drop-in replacement for the older fire-and-forget SEAD path.

This proposal covers the frontend-facing integration work needed to make the ingester usable in practice.

## Problem

Delivery 1 closed the backend ingester baseline, but it did not define the full user-facing workflow.

That gap matters because this ingester may require the user to:

- choose the new ingester explicitly
- supply submission metadata and change-request context
- understand when a run is blocked on manual confirmation
- inspect diagnostics and rerun instructions
- review the produced artifact bundle and related metadata
- understand how to hand off or execute the generated bundle without relying on hidden operator knowledge

Without a dedicated frontend UX, those states are either hidden, awkward, or pushed into ad hoc operator knowledge.

## Scope

This proposal covers:

- selecting `sead_change_request` in the frontend ingestion workflow
- collecting the submission context and related operator inputs required by the ingester
- presenting preflight, blocked, failed, and success states clearly
- presenting pending-confirmation results and rerun guidance clearly
- showing the generated artifact summary and key output metadata
- surfacing the operator guidance needed to interpret or hand off the generated bundle

## Non-Goals

- redefining ingester core logic
- implementing rollback, update handling, or other later-delivery backend capabilities
- reproducing SCCS internals in the frontend
- turning the frontend into the place where identity or SQL logic is decided
- persisting stable `sead_change_request` submission defaults in project metadata; treat that as a later change request once the first frontend workflow lands

## Proposed Design

### 1. Add an explicit ingester workflow branch

The frontend should treat `sead_change_request` as its own workflow branch, not just as another label in a generic ingester selector.

The UI should make clear that this path produces a change-request bundle and may require additional operator input.

### 2. Collect submission context explicitly

The frontend should provide a focused form for the operator inputs that the ingester needs, such as:

- submission name
- project name or target context where applicable
- datatype
- identifier
- description
- issue number when available
- deploy-strategy choice if multiple strategies remain operator-selectable

The goal is to make this data explicit and reviewable before the run starts.

### 3. Expose a clear run-state model

The workflow should expose at least these states:

- ready to run
- validation or preparation failed
- blocked pending confirmation
- artifact bundle generated

The frontend should not collapse blocked pending confirmation into a generic failure state.

### 4. Show rerun guidance for confirmation blocks

When confirmation is still pending, the UI should show:

- that no artifact bundle was generated
- the relevant Binding Set identifiers or status summary
- the operator action needed before rerun
- that rerun starts from the beginning rather than resuming in place

### 5. Show artifact outcomes in operator terms

On success, the UI should show the operator enough information to understand what was produced:

- the resolved change-request or bundle name
- deploy strategy used
- whether the package is non-revertible
- key file outputs and manifest metadata
- any important warnings or operator notes
- the execution or handoff guidance needed for the selected deploy strategy, including any runtime assumptions the operator must know

## Risks And Tradeoffs

- a separate frontend branch adds UI scope, but the alternative is hiding important operator behavior in backend-only details
- exposing too much low-level detail would make the UI noisy, so the frontend should summarize state rather than mirror the full internal planning model
- if the backend response shape is not yet stable enough for these states, this CR may need a small backend API follow-up

## Future Follow-Up

A later change request should evaluate which stable `sead_change_request` submission defaults belong in project YAML rather than being entered for each run.

That follow-up should likely persist project-scoped defaults under an ingester-specific metadata section rather than flattening workflow-specific fields into the generic project metadata editor.

## Validation And Acceptance Criteria

- operators can select `sead_change_request` through an explicit frontend workflow
- required submission context can be entered and reviewed before execution
- blocked pending-confirmation results are shown distinctly from generic failures
- success results show the generated artifact summary in operator-facing terms
- success results include the execution or handoff guidance the operator needs for the generated bundle
- the frontend does not need hidden operator knowledge to explain what the ingester expects next

## Final Recommendation

Treat frontend integration as a separate change request.

The new ingester requires real user interaction, and that user interaction should be designed intentionally in the frontend rather than left as an implied backend detail.