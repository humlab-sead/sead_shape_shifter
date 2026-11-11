# Foreign-Key Integrity Troubleshooter Phase Plan

Source: [Foreign-Key Integrity Troubleshooter](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER.md)

## Summary

Deliver the proposed read-only inspection of `FK_DATA_INTEGRITY` warnings in three phases: identify the saved foreign key, inspect current unmatched values and local rows, then expose the result in the existing troubleshooter dialog. Preserve the shipped row-count workflow throughout.

## Problem

The warning reports a count and at most ten example values, but does not identify its saved link or let users inspect the rows behind the unmatched values.

## Scope

This plan covers warning identity, saved-link eligibility, count-based reproduction, authorized and bounded inspection, and the shared dialog. It excludes data or configuration edits, reconciliation, key-pair trials for integrity warnings, and other foreign-key warning kinds. The existing row-count request, response, eligibility, and behavior must not change.

## Current Position

- [`ForeignKeyIntegrityValidator`](../../../../src/validators/data_validators.py) emits `FK_DATA_INTEGRITY` without structured link identity or an `orphan_count` metadata value. The [data validation orchestrator](../../../../backend/app/validators/data_validation_orchestrator.py) is its current production caller and iterates foreign keys without passing their index.
- The [saved-link resolver](../../../../src/transforms/link_resolution.py) handles row-count issues and checks supported join types; the [frontend candidate check](../../../../frontend/src/utils/linkTroubleshooter.ts) likewise accepts only row-count warnings.
- The [existing endpoint](../../../../backend/app/api/v1/endpoints/link_troubleshooter.py) uses project read authorization. No integrity inspection endpoint or result is shipped.

## Phase Plan

### Phase 1: Identify the saved foreign key

**Goal**

Make each new integrity warning attributable to exactly one saved link, without changing row-count eligibility.

**Focus**

- Attach `fk_index`, `fk_signature`, and `orphan_count` to `FK_DATA_INTEGRITY` issues through the validation orchestration path; keep the validator responsible for comparing frames, not fetching data.
- Share saved-FK lookup with the existing resolver, but apply integrity-specific eligibility without a join-type restriction. Refuse missing, out-of-range, or stale identity with named reasons.

**Depends On**

- The proposal's saved-link identity and metadata decisions; no earlier phase.

**Outputs**

- Identifiable integrity issues and an integrity-specific saved-link resolution result for inspection and UI use.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) New integrity issues identify the exact saved link by index and signature, including two links to the same remote entity; missing or stale identity produces a named refusal.
- `PH1-AC-2` (from `P-AC-7`) Row-count eligibility and saved-link resolution remain unchanged.

**Validation Milestones**

- `VM-1` Confirm identity and refusal for valid, duplicate-entity, missing, out-of-range, and stale links, including right and outer joins (`PH1-AC-1`); compare existing row-count resolution and eligibility (`PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-7`. Preserve the saved foreign-key list position and signature, validator purity, and the existing row-count checks. Confirm the production paths that create integrity warnings attach the metadata; older warnings without it remain ineligible. No blocking design decision remains for this phase.

**Readiness**

Ready for a task plan.

### Phase 2: Recompute and inspect unmatched data

**Goal**

Return an authorized, read-only integrity result that distinguishes a reproduced warning from changed or unavailable data.

**Focus**

- Add the separate integrity endpoint and response envelope, using saved-link resolution and current project read authorization on every call.
- Inspect current full-normalization frames in a private, read-only run. Recompute the distinct unmatched count through `ForeignKeyIntegrityValidator`; report `reproduced` when that current full-data count equals the warning's recorded `orphan_count`, even if the warning came from sample validation. This does not claim to replay the original dataset or sample run.
- Return distinct values in deterministic pages of 50 with their local row counts and at most 20 local rows for a selected value; state the source and returned columns.

**Depends On**

- Phase 1's issue metadata and saved-link resolution; D1 and D2 are resolved.

**Outputs**

- An integrity response for the dialog, with relationship details, current values, optional selected rows, counts, status, and named reasons.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`, `P-AC-3`) Reproduction uses the validator's count and null rules; a changed count or unavailable input does not claim reproduction or present an old count as current.
- `PH2-AC-2` (from `P-AC-4`) Distinct unmatched values have correct local row counts, deterministic order and truncation, and separate complete and returned counts.
- `PH2-AC-3` (from `P-AC-5`) Selecting a value returns only bounded local rows, with the inspected data source and returned columns stated.
- `PH2-AC-4` (from `P-AC-6`, `P-AC-7`) Every inspection call requires project read authorization, makes no writes, and leaves the row-count endpoint and response unchanged.

**Validation Milestones**

- `VM-2` Compare recomputed counts with complete validation on matching full-normalization frames, sample-origin warnings, changed inputs, unavailable remote data, and `null_keys_equal` cases (`PH2-AC-1`); verify complete counts, row counts, deterministic paging for unchanged data, selected-row bounds, current-data selection refusal, source and columns (`PH2-AC-2`, `PH2-AC-3`); verify authorization, cross-project refusal, no writes, and row-count response compatibility (`PH2-AC-4`).

**Task-Plan Handoff**

- Source: `P-AC-2` through `P-AC-7`. Inspection uses current full normalization, with frames at the same stage as complete validation, through a private run that does not write projects, source data, or shared caches. State `current full normalization` in the response. Count equality reproduces the warning's numeric claim on current full data, regardless of the warning's original validation mode; it does not prove the original rows or values are unchanged. If full frames are unavailable, report `not_reproduced` with a named reason. Use fixed pages of 50 distinct values and at most 20 rows for one selected value. Include saved local keys, business keys, then available target-facing columns, up to 20 returned columns in all; name the columns and any truncation. One endpoint returns a value page plus optional selected rows, using a type-preserving token for the ordered key tuple. Each call recomputes current data; no snapshot or fingerprint is kept. If the selected value is no longer unmatched, report that explicitly. Paging is deterministic for unchanged data but not guaranteed across source changes.

**Readiness**

Ready for a task plan; D1 and D2 are resolved.

### Phase 3: Present integrity inspection in the shared dialog

**Goal**

Offer one troubleshooter action for eligible integrity warnings and show their read-only result without changing row-count trials.

**Focus**

- Extend the validation-list action and shared dialog shell with an integrity-specific body; keep join trial controls exclusive to row-count warnings.
- Show saved relationship details, status and reason, full versus returned value counts, value row counts, and selected local rows with their source and columns.

**Depends On**

- Phase 2's stable integrity response and decisions on paging and selected-value addressing.

**Outputs**

- An integrity inspection path in the existing UI, with the shipped row-count view intact.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`) Only integrity warnings with resolvable metadata offer an actionable inspection; unsupported or stale warnings explain why they cannot be inspected.
- `PH3-AC-2` (from `P-AC-4`, `P-AC-5`) The dialog distinguishes complete and returned counts, supports selecting a value for bounded local rows, and identifies the inspected source and columns.
- `PH3-AC-3` (from `P-AC-7`) The row-count action, dialog behavior, request, response, and eligibility remain unchanged.

**Validation Milestones**

- `VM-3` Exercise eligible and refused integrity warnings, truncated value lists, and selected-row display (`PH3-AC-1`, `PH3-AC-2`); regress the row-count action and trials against their shipped behavior (`PH3-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-4`, `P-AC-5`, `P-AC-7`. Use Phase 2's finalized response and selection rules. Share the dialog shell and API client plumbing, not the join-trial body; do not introduce edits or auto-fixes.

**Readiness**

Ready for a task plan; Phase 2's response and inspection-shape decisions are resolved.

## Cross-Phase Rules

- Keep unsupported or stale warnings explicitly ineligible; never turn a failed lookup or changed count into a reproduced result.
- Preserve the existing row-count workflow and separate integrity data from join-trial models.
- Keep inspection read-only, authorized for the current project, and bounded, including each follow-up request for selected rows.

## Validation Strategy

Validate saved-link identity before relying on it for inspection (`VM-1`); compare integrity counts and bounded output against the validator, including failure paths (`VM-2`); then verify the dialog and row-count regression together (`VM-3`). Exact test cases, fixtures, and commands belong in the corresponding phase task plans.
