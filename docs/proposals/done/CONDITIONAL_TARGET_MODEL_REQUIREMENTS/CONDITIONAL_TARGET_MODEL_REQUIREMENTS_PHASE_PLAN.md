# Conditional Target Model Requirements — Phase Plan

Source: [Conditional Target Model Requirements](CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md).

## Summary

Deliver the new FK condition in two steps: accept and report it in the target-model format, then enforce it using reconciled insert decisions. Schema tooling and guidance are part of feature delivery.

## Problem

Static entity, column, and FK requirements can reject a submission whose locations all resolve to existing rows. The proposed `has_new_rows` rule must wait for reconciliation so provisional new rows do not trigger false errors.

## Scope

This plan covers the target-model format, project-only conformance result, change-request validation, schema tooling, and feature guidance. It excludes a general condition language, changes to unrelated required fields, and activation of the rule in the SEAD superset model. The source proposal's `P-AC-5` also requires that activation; this CR covers only its tooling and guidance portion.

## Current Position

- The strict target-model schema has boolean `required` fields and no live `required_when` field. The superset YAML contains only a commented example.
- Project conformance evaluates configuration without reconciled row states. Target projection checks required FK data before package assembly; the package builder later selects rows for insertion from resolved row states.
- The [proposal](CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md) fixes the rule to an FK's own source entity. The target must declare `public_id`; the conditional FK supplies its column requirement, while static `required` behavior stays unchanged.

## Phase Plan

### Phase 1: Format and project-only result

**Goal**

Accept the conditional FK syntax and represent its status accurately before reconciliation.

**Focus**

- Validate `required_when: {has_new_rows: <source entity>}` and reject conflicting or unresolvable declarations.
- Report the condition as awaiting reconciliation in project-only conformance, without issuing conditional missing-entity, link, or column errors.
- Make the accepted syntax available in the generated schema reference and editor schema.

**Depends On**

- The source proposal's condition and compatibility rules.

**Outputs**

- A validated target-model contract, matching schema tooling, and a project-only result that distinguishes deferred checks from passed checks.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Valid conditional FKs parse; unknown or non-owning sources, targets without `public_id`, and mixed `required`/`required_when` declarations are rejected.
- `PH1-AC-2` (from `P-AC-2`) Project-only conformance reports the condition as awaiting reconciliation and emits no error caused solely by that condition.
- `PH1-AC-3` (from `P-AC-6`) Existing static entity, column, and FK requirement results are unchanged.
- `PH1-AC-4` (from `P-AC-5`, tooling portion) The generated schema reference and editor schema accept and describe the new condition.

**Validation Milestones**

- `VM-1` (`PH1-AC-1`–`PH1-AC-4`): schema and project-conformance cases show accepted, rejected, deferred, and unchanged static results; generated schemas match the accepted format.

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-2`, the tooling portion of `P-AC-5`, and `P-AC-6`; preserve current static checks. No blocking design decision remains.

**Readiness**

Ready for a task plan.

### Phase 2: Reconciled change-request enforcement

**Goal**

Apply conditional requirements only to rows selected for insertion after reconciliation.

**Focus**

- Use final insert decisions to activate the lookup, project link, and FK column/value checks.
- Prevent provisional and matched rows from triggering conditional errors while preserving projection of FK values used by inserted or updated rows.
- Explain the rule's reconciliation timing and FK-column behavior in the target-model guide.

**Depends On**

- Phase 1's parsed condition and deferred project-only result.

**Outputs**

- Change-request validation that accepts matched-only submissions and rejects incomplete new rows before package acceptance, with matching feature guidance.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-3`) Zero reconciled `location` inserts cause no error from this condition, including when provisional rows match existing locations.
- `PH2-AC-2` (from `P-AC-4`) A reconciled `location` insert fails with a clear error if the lookup, project link, or FK column is missing, or the FK value is null or unresolved.
- `PH2-AC-3` (from `P-AC-6`) Static requirement validation matches its pre-change results.
- `PH2-AC-4` (from `P-AC-5`, guidance portion) The target-model guide explains that `has_new_rows` uses reconciled insert decisions and that the conditional FK requires its column on inserted rows.

**Validation Milestones**

- `VM-2` (`PH2-AC-1`–`PH2-AC-4`): matched-only, insert, update, and static-rule cases produce the expected validation results; the guide matches those results.

**Task-Plan Handoff**

- Use `P-AC-3`, `P-AC-4`, the guidance portion of `P-AC-5`, and `P-AC-6`; final reconciled insert decisions are authoritative. Active SEAD superset rules remain outside this CR.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Count only rows selected for insertion after reconciliation; the older pre-reconciliation `has_new_rows()` check does not satisfy this rule.
- Keep unconditional `required` results stable throughout the change. Compare them with current behavior when validating each phase.
- Keep the active SEAD superset rules unchanged in this CR. Their adoption remains a separate decision and validation step.

## Validation Strategy

Validate the format and project-only result first, then exercise reconciled zero-insert and insert cases using a conditional target-model fixture. Compare static requirement results before and after each change. The phase task plans should choose exact fixtures and commands.
