# Direct Target-ID Conditional FK Conformance Phase Plan

Source: [Direct Target-ID Conditional FK Conformance](DIRECT_TARGET_ID_CONDITIONAL_FK_CONFORMANCE.md) (proposed change request).

## Summary

Deliver the conformance correction in one phase. Suppress the reconciliation-pending result only for a valid conditional direct target-ID FK, while retaining direct-ID checks and all other entity requirements.

## Problem

Project-only conformance currently reports an unresolved conditional FK dependency even when that relationship uses an existing target ID and needs no project lookup entity or Core link.

## Scope

This plan covers the conditional conformance result and regression validation. It does not change `required_when` syntax, ingestion, target-ID checks, or the entity editor.

## Current Position

- The source proposal is proposed, not implemented.
- Conformance reports `CONDITIONAL_FK_AWAITING_RECONCILIATION` for every conditional FK on a present source; it already distinguishes valid direct-ID declarations and reports `DIRECT_FK_TARGET_CHECK_PENDING`.
- Change-request validation already checks required direct-ID values on selected inserts and verifies supplied target IDs.

## Phase Plan

### Phase 1: Correct conditional conformance

**Goal**

Report reconciliation as pending only for conditional relationships that still need it.

**Focus**

- Apply the existing valid direct-ID check per conditional FK when deciding whether to report awaiting reconciliation.
- Preserve declaration errors, independent target requirements, and direct-ID pending checks.
- Verify conformance cases and existing change-request behavior.

**Depends On**

- Approval of the source proposal before implementation.

**Outputs**

- Corrected project-only conditional FK results with regression coverage.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) A valid conditional direct-ID FK retains the target-check status but has no reconciliation-pending status or lookup requirement from that relationship.
- `PH1-AC-2` (from `P-AC-2`) Local/default conditional FKs still await reconciliation, and invalid direct-ID declarations retain their errors.
- `PH1-AC-3` (from `P-AC-3`) A second FK to the same target retains its own conditional status, and globally required target entities remain required.
- `PH1-AC-4` (from `P-AC-4`) Selected inserts still require conditional direct-ID values and reject IDs absent from the target database.

**Validation Milestones**

- `VM-1` Focused conformance checks demonstrate `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-3`.
- `VM-2` Change-request regression checks demonstrate `PH1-AC-4` without changing current direct-ID validation.

**Task-Plan Handoff**

- Use `P-AC-1` through `P-AC-4` and the existing valid direct-ID contract. Keep the exception per FK; do not infer mode from an absent lookup or change insert-based validation. No technical decision is outstanding.

**Readiness**

Requires approval of the source proposal before implementation planning.

## Validation Strategy

Check the conformance result for valid, local/default, invalid, and mixed-source relationships. Confirm that independent target requirements and change-request direct-ID validation remain unchanged.
