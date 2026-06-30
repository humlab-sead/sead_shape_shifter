# Phase Plan: Data Provider Submission Lifecycle Implementation

## Summary

This plan sequences lifecycle implementation work for provider-owned data changes in `sead_change_request`.

It is an execution plan, not a policy document. Lifecycle policy comes from [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md) and [DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_SPECIFICATION.md).

## Problem

The repository has draft lifecycle rules but no completed implementation path that enforces those rules end to end.

Without phased delivery, existing-row update handling risks becoming SQL-first and bypassing ownership classification, one-live-version invariants, and review routing for restricted changes.

## Scope

This plan covers lifecycle implementation sequencing for:

- lifecycle metadata and invariants
- submission planning and classification outcomes
- existing-row provider-owned update handling
- restricted shared-data review routing
- artifact and operator outcome behavior

This plan does not redefine policy, frontend IA, release scheduling, or staffing.

## Current Position

- lifecycle policy scope decision is accepted through [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md)
- delivery order exists, but implementation tracking is split across multiple proposal documents
- existing-row update handling remains proposed and should stay downstream of lifecycle rule enforcement
- shared-data governance boundaries are documented at proposal level but not yet implemented as a review path contract

## Phase Entry Status

| Phase | Entry status | Note |
|-------|--------------|------|
| Phase 1: Lifecycle Metadata And Invariants | ready to start | lifecycle policy gate is complete |
| Phase 2: Submission Planning And Classification | ready after Phase 1 core model contracts land | depends on Phase 1 identity and state model choices |
| Phase 3: Existing-Row Provider Update Path | blocked | remains downstream of Phase 1 and Phase 2 outcomes |
| Phase 4: Shared-Data Review And Operator Contract | ready to scope, implementation after Phase 2 outcome contract | governance boundaries are accepted at policy level but delivery path is not yet implemented |

## Phase Plan

### Phase 1: Lifecycle Metadata And Invariants

**Goal**

Define and implement the minimum state and metadata model that can enforce lifecycle invariants.

**Focus**

- define logical-record identity versus record-version identity
- implement live and superseded state handling with traceability fields
- ensure one-live-version enforcement is represented in the implementation model

**Acceptance Criteria**

- logical record and record-version identities are explicit in implementation contracts
- one-live-version behavior is enforceable by the model, not only by documentation
- accepted, no-op, pending-review, and blocked outcomes are represented consistently in lifecycle state handling

### Phase 2: Submission Planning And Classification

**Goal**

Classify incoming provider submissions before SQL artifact generation.

**Focus**

- classify requested changes as provider-owned, shared-reference, or system-managed
- classify outcomes as new data, no-op, allowed update, pending review, or blocked
- produce operator-facing diagnostics for blocked and review-required outcomes

**Acceptance Criteria**

- planning distinguishes all required outcome classes for provider-submitted changes
- no-op outcomes are explicit and do not create duplicate live versions
- diagnostics describe why changes were blocked or routed to review

### Phase 3: Existing-Row Provider Update Path

**Goal**

Implement the narrow accepted existing-row update path for provider-owned data.

**Focus**

- align mutable-field comparison boundaries with [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md)
- apply supersession when a new accepted version replaces the current live version
- block ambiguous or unsupported updates instead of applying speculative mutation

**Acceptance Criteria**

- accepted existing-row changes produce a new live version and supersede the prior live version
- unchanged reruns are no-op and do not create duplicate live versions
- ambiguous or disallowed existing-row changes do not mutate current live records silently

### Phase 4: Shared-Data Review And Operator Contract

**Goal**

Implement restricted shared-data handling and operator-visible lifecycle outcomes.

**Focus**

- define reviewed request flow for new or corrected shared terms
- keep provider-owned reference updates separate from shared-row mutation
- align artifact and frontend outcome reporting for accepted, no-op, blocked, and pending-review paths

**Acceptance Criteria**

- shared-data changes are routed to a defined reviewed path instead of default provider update execution
- provider-owned reference changes are handled separately from shared-row governance actions
- operator-visible results distinguish accepted, no-op, blocked, and review-required outcomes

## Cross-Phase Rules

- do not implement existing-row update mutation before lifecycle metadata and classification rules are in place
- preserve one-live-version behavior in every accepted provider-owned update path
- treat ambiguous changes as blocked or pending review, never as implicit acceptance
- keep shared-data governance outside default provider-owned update execution
- keep plan state in this file and move issue-level tracking to dedicated issue documents

## Validation Strategy

- validate lifecycle state transitions and one-live-version behavior with focused unit tests in ingester and planning modules
- validate classification behavior with scenario tests for new, no-op, allowed, pending-review, and blocked outcomes
- validate existing-row update behavior with explicit mutable-field boundary tests and rerun-idempotency checks
- validate operator-facing outcome payloads used by frontend states for blocked, pending-review, no-op, and accepted paths
- update this plan only when acceptance criteria are actually met in code and tests

## Final Recommendation

Use this phase plan as the only lifecycle sequencing document.

Track cross-document status and remaining tasks in [CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](./CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md), then keep issue-level execution details outside this phase plan.