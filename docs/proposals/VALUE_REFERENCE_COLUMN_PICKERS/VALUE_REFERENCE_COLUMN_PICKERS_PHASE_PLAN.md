# Value Reference Column Pickers — Phase Plan

Source: [Make `@value` References Usable in Column Pickers](VALUE_REFERENCE_COLUMN_PICKERS.md)

## Summary

Deliver reference-safe column editing in five phases: preserve stored values, add scoped backend resolution, report saved-project reference errors, add guided entry and inspection, then add conflict annotations and explicit replacement. Each phase has a result that later work can use without changing how valid references resolve in Core.

## Problem

The entity editor shows a saved `@value` reference as one chip without showing its columns. Some column-list controls lose scalar references on form save, and FK pickers offer untyped project-wide paths. Saved-project validation can lose the original path before reporting an error. These gaps make reference errors hard to find and fix.

## Scope

This plan covers the proposal's in-scope column-list controls, read-only draft-aware reference resolution, saved-project reference validation, guided entry, inspection, and **Replace with columns**. Fixed Entity Columns remain excluded. The plan does not change directive syntax, valid Core resolution, stored YAML formats, or general editing of legacy `+` expressions.

## Current Position

- API and YAML data retain directive text. `ProjectMapper.to_core()` resolves directives for full Core use; the existing draft column-candidate service maps a copied project with the unsaved entity applied.
- Business Keys and non-fixed Columns already load simple scalar references as chips. Deduplication Columns and Drop Empty Rows lose scalar selections, while the unnest editor expects arrays. A literal-first legacy `+` expression can change storage shape on form save.
- FK key pickers still append the project-wide `valid-directives` list. That list includes paths without checking for a list of column names.
- Project validation resolves directives before its normal structural checks. Fixed Entity Columns use a positional schema that does not preserve scalar references through a form save.

## Phase Plan

### Phase 1: Preserve references in the form

**Goal**

Make opening and saving an in-scope entity safe for existing references before adding new editing actions.

**Focus**

- Confirm the in-scope controls and exclude Fixed Entity Columns from the shared interaction.
- Normalize scalar references in the remaining chip inputs and preserve scalar, mixed-list, and legacy `+` expression storage forms. Keep a scalar legacy expression as one raw chip, including the literal-first form.

**Depends On**

- The field scope and storage rules in the source proposal.

**Outputs**

- Form values that retain their reference text and stored shape through an unchanged save.
- A confirmed field set for backend validation and later editor actions.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-6`) An unchanged form save preserves scalar references, mixed lists, manually entered valid paths, and both supported scalar legacy `+` expression forms in every in-scope control.
- `PH1-AC-2` (from `P-AC-1`) Fixed Entity Columns remain outside the new reference interaction and validation field set.

**Validation Milestones**

- `VM-1` Form round-trip checks preserve storage shape and column order for the in-scope forms; the fixed-column exclusion is confirmed (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Use `P-AC-1` and `P-AC-6`. Retain raw directive text, treat legacy expressions as single scalar values when stored that way, and confirm each control's stored contract before changing it.

**Readiness**

Ready for a task plan.

### Phase 2: Resolve requested references from drafts

**Goal**

Provide ordered column results and local failure reasons for one requested reference without resolving unrelated broken references.

**Focus**

- Add the proposal's read-only editor mode to `ProjectMapper.to_core()` using the saved project plus the current entity draft. Resolve only the requested path and its nested dependencies under the existing directive rules.
- Supply independently checked, progressively filtered list-valued property choices and validation of a complete manually entered path. Preserve project read authorization.

**Depends On**

- Phase 1's confirmed field set and storage forms.

**Outputs**

- A backend resolution contract for completion, preview, and independent saved-project checks.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-3`) A requested reference returns ordered strings from the unsaved draft or a local unresolved reason; an unrelated missing or circular reference does not block a valid result.
- `PH2-AC-2` (from `P-AC-2`) Eligible entity properties are checked independently, and a manually entered full path can be checked without relying on the project-wide path list.
- `PH2-AC-3` (from `P-AC-7`) Read requests enforce project authorization and do not persist the draft or alter normal full-project conversion.

**Validation Milestones**

- `VM-2` Backend contract checks cover draft changes, ordered and nested results, wrong types, requested-path failures, unrelated failures, authorization, and unchanged full conversion (`PH2-AC-1` through `PH2-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-2`, `P-AC-3`, and `P-AC-7`. Keep directive interpretation in the mapper. A requested dependency failure returns no partial list; unrelated failures leave valid candidates available.

**Readiness**

Ready for a task plan once Phase 1 establishes the field set.

### Phase 3: Report saved-project reference errors

**Goal**

Show the original path or expression for each invalid saved reference in the existing validation results.

**Focus**

- Check raw scalar and list-item references before resolution removes their text. Check every operand of supported legacy `+` expressions and the final expression result.
- Collect errors independently and combine them with normal validation results. If full-project mapping fails, report collected reference errors and a project-resolution error while skipping checks that need resolved data.

**Depends On**

- Phase 1's field set and Phase 2's independent resolution contract.

**Outputs**

- Saved-project validation results naming each affected entity, field, and original path or expression.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-8`) Missing, unresolved, and wrong-type references in the in-scope fields produce errors with their original location and text, including legacy expression operands and list items that would otherwise become plain strings.
- `PH3-AC-2` (from `P-AC-8`) One invalid reference does not hide others; full-project mapping failure returns collected reference errors plus a project-resolution error, and valid Core resolution is unchanged.
- `PH3-AC-3` (from `P-AC-1`) The new column-list reference check skips Fixed Entity Columns.

**Validation Milestones**

- `VM-3` Saved-project validation checks cover both storage forms, legacy operand and result types, independent error collection, mapping failure, fixed-column exclusion, and unchanged valid resolution (`PH3-AC-1` through `PH3-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-8` and the Fixed Entity Columns exclusion in `P-AC-1`. Preserve raw text until the new checks finish. A scalar operand in a legacy expression remains valid when the complete expression yields a valid string list under existing rules.

**Readiness**

Ready for a task plan once Phase 2 establishes independent resolution.

### Phase 4: Add guided entry and inspection

**Goal**

Let users find suitable references and inspect their current columns from the unsaved draft.

**Focus**

- Add progressive reference entry beside field-specific ordinary column suggestions. Switch FK key pickers from the untyped project-wide path list to this interaction.
- Show ordered columns or a local unresolved reason for a selected simple reference. Discard results made stale by later edits and support keyboard use.

**Depends On**

- Phase 1 form preservation, Phase 2 backend resolution, and Phase 3 saved-project error reporting.

**Outputs**

- Guided reference entry and read-only inspection across the in-scope controls.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-1`) Ordinary suggestions stay field-specific; FK pickers stop appending the project-wide path list, and saved selected references remain visible.
- `PH4-AC-2` (from `P-AC-2`) Typing `@value` narrows entity and list-valued-property choices, while a full manually entered reference remains editable and checkable.
- `PH4-AC-3` (from `P-AC-3`) Inspection shows ordered draft-derived columns or a clear unresolved status without saving or changing the field.
- `PH4-AC-4` (from `P-AC-7`) Keyboard operation, project read authorization, and stale-result handling work for completion and inspection.

**Validation Milestones**

- `VM-4` Editor checks cover progressive entry, FK local and remote context, saved-chip visibility, draft changes, keyboard use, stale results, and preview failure isolation (`PH4-AC-1` through `PH4-AC-4`).

**Task-Plan Handoff**

- Use `P-AC-1` through `P-AC-3` and `P-AC-7`. Preserve manual entry and saved-reference visibility when retiring the FK picker's old suggestion source. Keep legacy expressions as raw chips and Fixed Entity Columns outside the interaction.

**Readiness**

Ready for a task plan once Phases 1–3 supply their contracts.

### Phase 5: Attribute conflicts and replace simple references

**Goal**

Make validated column conflicts understandable and allow an explicit, reversible conversion to literal columns.

**Focus**

- Attribute overlap and non-produced-key findings to expanded columns only when the validation result matches the draft. Label saved-project results as such and treat incomplete source-column candidates as advisory.
- Replace one resolvable simple reference in place, preserve surrounding chip order, explain snapshot behavior, and allow undo before save. Keep replacement unavailable for legacy `+` expressions.

**Depends On**

- Phase 4 inspection and Phase 3 validation results.

**Outputs**

- Conflict annotations, **Replace with columns**, and end-to-end reference editing across the in-scope controls.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-4`) Draft-matched validation identifies the expanded columns behind an unnest overlap or non-produced business key; later edits remove stale annotations, and saved-only findings are labeled.
- `PH5-AC-2` (from `P-AC-5`) Replacing one resolvable simple reference yields ordered literal chips in place, explains the lost link, and can be undone before save; unresolved and legacy expressions cannot be replaced.
- `PH5-AC-3` (from `P-AC-6`) The complete editor preserves untouched scalar, mixed-list, and legacy expression storage forms and leaves valid Core resolution unchanged.

**Validation Milestones**

- `VM-5` End-to-end checks cover conflict attribution and severity, stale findings, incomplete candidates, replacement order and undo, and untouched-reference parity across all in-scope fields (`PH5-AC-1` through `PH5-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-4` through `P-AC-6`. Use existing validators for findings, preserve their severity, and never present saved-project results as current-draft conflicts. Replacement changes only the chosen simple reference.

**Readiness**

Ready for a task plan once Phases 3–4 supply validation and inspection.

## Cross-Phase Rules

- Keep API and YAML directive text raw. Resolution for editor requests stays in `ProjectMapper.to_core()`; normal full-project conversion and valid Core behavior stay unchanged.
- Preserve scalar/list storage shape and legacy `+` expression behavior until an explicit simple-reference replacement. Fixed Entity Columns remain excluded throughout.
- Treat stage-aware column candidates as suggestions when source data is incomplete. Use existing validator results for conflict severity and show whether results describe the draft or saved project.
- Before retiring FK use of the broad path list, confirm that saved references and valid manual entry still work with guided entry.

## Validation Strategy

Validate storage compatibility first (`VM-1`), then isolated backend resolution and authorization (`VM-2`), saved-project errors (`VM-3`), guided editor behavior (`VM-4`), and end-to-end conflict and replacement behavior (`VM-5`). Compare unchanged scalar, mixed-list, and legacy expressions before and after form saves. Check that valid references resolve to the same ordered values as before and that unrelated invalid references do not hide valid editor results or other validation errors. Exact test cases and commands belong in each phase task plan.
