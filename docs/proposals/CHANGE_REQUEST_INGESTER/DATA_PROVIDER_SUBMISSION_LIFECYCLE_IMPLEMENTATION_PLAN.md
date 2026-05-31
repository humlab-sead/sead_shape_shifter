# Plan: Data Provider Submission Lifecycle Implementation

## Status

- Draft implementation plan
- Related proposal: [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md)
- Related specification: [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md)
- Intended role: delivery planning, work sequencing, and progress tracking for accepted lifecycle rules

## Purpose

This document breaks the accepted provider-submission lifecycle work into implementation phases.

It is a delivery document, not a policy document. If this plan conflicts with the proposal or the lifecycle specification, the proposal and specification win.

## Scope

This plan covers:

- recommended delivery order
- implementation workstreams
- readiness checks between phases
- progress checklist placeholders

## Non-Goals

- redefining provider-visible policy rules
- replacing the lifecycle specification as the durable source of truth
- tracking issue-level day-to-day notes in this document

## Planning Assumptions

- provider-owned changes require history-preserving handling
- only one live version may exist for the same logical record at a given point in time
- shared reference data remains outside the default provider update path
- existing-row updates are one scenario inside the broader lifecycle work, not the full lifecycle scope

## Workstreams

### 1. Lifecycle model and metadata

Define the minimum data model and metadata needed to represent logical records, versions, live status, supersession, and review outcomes.

Checklist:

- [ ] define the minimum lifecycle fields needed for provider-owned version tracking
- [ ] define how logical record identity is distinguished from record-version identity
- [ ] define how live and superseded status are represented
- [ ] define the minimum audit and traceability metadata

### 2. Planning and decision engine

Define how incoming submissions are classified as new data, no-op, allowed update, restricted change, or blocked change.

Checklist:

- [ ] classify changes by provider-owned, shared reference, or system-managed data role
- [ ] define no-op comparison rules for provider-owned data
- [ ] define when a change becomes pending review instead of blocked
- [ ] define operator-facing diagnostics for blocked and review-required outcomes

### 3. Existing-row update handling

Implement the narrower existing-row scenario only after lifecycle rules and minimum metadata are in place.

Checklist:

- [ ] align field mutability rules with [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md)
- [ ] define how an accepted new version supersedes the previous live version
- [ ] define how no-op reruns avoid creating duplicate live versions
- [ ] define how ambiguous existing-row changes stop or route to review

### 4. Shared-data review path

Define the path for requested changes that involve shared classifiers or shared lookups.

Checklist:

- [ ] define request flow for new shared terms
- [ ] define review flow for corrections to existing shared terms
- [ ] define how provider-owned reference changes are separated from shared-row changes
- [ ] define the boundary between provider workflow and curator or authority workflow

### 5. Artifact generation and execution contract

Define how accepted outcomes are rendered into change artifacts without weakening lifecycle rules.

Checklist:

- [ ] define artifact behavior for accepted new versions
- [ ] define artifact behavior for no-op outcomes
- [ ] define artifact behavior for blocked and pending-review outcomes
- [ ] confirm that artifact generation preserves the one-live-version rule

### 6. Frontend and operator workflow

Define how the system explains lifecycle outcomes to operators and how review-required work is handled.

Checklist:

- [ ] show whether a submission produced new data, a new live version, a no-op, a blocked result, or a review-required result
- [ ] show which earlier version was superseded when a new version becomes live
- [ ] show why a change was blocked or routed to review
- [ ] define rerun guidance for corrected submissions

## Recommended Delivery Order

### Phase 1. Lifecycle rules and minimum metadata

Finish the minimum lifecycle model, invariants, and traceability requirements needed to support provider-owned history.

Exit criteria:

- [ ] logical record and record-version concepts are defined well enough for implementation
- [ ] the one-live-version rule can be enforced by the planned model
- [ ] accepted, blocked, pending-review, and no-op outcomes are defined clearly enough for downstream work

### Phase 2. Planning behavior and diagnostics

Implement or document the decision path that classifies provider submissions before SQL-oriented handling begins.

Exit criteria:

- [ ] new data, no-op, allowed update, restricted change, and blocked change outcomes are distinguishable
- [ ] operator-facing diagnostics exist for blocked and pending-review outcomes
- [ ] shared-data requests are separated from default provider-owned update handling

### Phase 3. Existing-row update path

Implement the accepted subset of existing-row updates for provider-owned data.

Exit criteria:

- [ ] accepted existing-row changes create a new live version and supersede the older live version
- [ ] no-op reruns do not create duplicate live versions
- [ ] ambiguous changes do not mutate the current live version silently

### Phase 4. Review and governance extensions

Add or refine the reviewed paths for shared-data requests and other restricted changes.

Exit criteria:

- [ ] review-required changes have a defined path
- [ ] shared-data governance actions remain outside the default provider update flow
- [ ] operator workflow makes the distinction between provider-owned changes and shared-data changes clear

## Progress Tracking

Use this section for high-level progress only. Detailed issue tracking should stay in GitHub or other delivery tooling.

### Current status

- [ ] Phase 1 not started
- [ ] Phase 2 not started
- [ ] Phase 3 not started
- [ ] Phase 4 not started

### Open delivery dependencies

- [ ] confirm where lifecycle metadata will live
- [ ] confirm which existing-row entities will support mutable-field comparison first
- [ ] confirm review path ownership for shared-data requests
- [ ] confirm frontend scope for blocked and pending-review results

## Relationship To Other Documents

- [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md) defines the problem and recommendation
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md) defines the durable lifecycle rules and invariants
- [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) narrows the existing-row implementation scenario

## Maintenance Rule

Keep this plan lean.

When a phase is complete, update the checklist or archive the finished planning details instead of turning this document into a historical narrative.