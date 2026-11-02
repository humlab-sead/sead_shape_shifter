# `@value` Column Picker UX Phase Plan

Source: [Improve `@value` Guidance and Preview in Column Pickers](./VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT.md)

## Summary

Deliver the proposal in two phases: first make cached references and unchanged form values safe to use, then add suggestions and an explicit preview to the supported pickers. The preview remains a display aid; references stay in the form and saved YAML.

## Problem

Column pickers do not show what an `@value` reference contains or help users find supported references. A helper must remain useful when cached data is available without turning missing or unsupported references into save errors.

## Scope

This plan covers frontend cache ownership, supported reference expansion, form value preservation, and picker suggestions and previews. It excludes backend reference endpoints, mapper changes, project-level reference validation, Core changes, Fixed Entity Columns, and the separate provider/schema business-key save-guard decision.

## Current Position

- The proposal is marked **Proposed feature**; this plan sequences its stated design without changing that status.
- The entity store holds loaded `entity_data`, but `fetchEntities()` sets `currentProjectName` before the requested list replaces the previous cache. The name alone cannot prove cache ownership during a switch.
- Core recursively resolves `@value` references and flattens list-item results. Some form serialization currently collapses a single reference to a scalar, so an unchanged load and save can change its original list form.

## Phase Plan

### Phase 1: Safe cached reference data

**Goal**

Provide a trustworthy local source for reference results and preserve unchanged form values.

**Focus**

- Identify the project of a completed entity-cache load and withhold reference results while cache ownership is unknown or mismatched.
- Expand only complete supported `entities.<entity>.keys` and `.columns` references from that cache. Preserve order and duplicates; reject an entire result if any nested value is unsupported or unavailable.
- Preserve the original scalar or list representation of unchanged reference fields, including editors that use arrays for display.

**Depends On**

- The proposal's supported syntax and cached-data rule; no earlier phase.

**Outputs**

- A frontend cache check, reference expansion result, and form round-trip behavior ready for picker use.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Reference results are available only after a completed cache load for the active project.
- `PH1-AC-2` (from `P-AC-2`) Supported scalar and nested list-item references expand like Core, in the same order and with duplicates retained.
- `PH1-AC-3` (from `P-AC-3`) A missing cache, entity, or path, a cycle, or an unsupported nested value returns no partial columns.
- `PH1-AC-4` (from `P-AC-5`) An unchanged load and save retains scalar references, mixed lists, and legacy `+` expressions in their original scalar or list form.

**Validation Milestones**

- `VM-1` Compare supported expansion with Core and check cache switches, failure cases, and unchanged form round trips (`PH1-AC-1`–`PH1-AC-4`).

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-2`, `P-AC-3`, and `P-AC-5`. The completed cache is the only reference source; unsupported syntax stays raw. Decide the exact frontend changes and tests in the phase task plan. No design question blocks that plan.

**Readiness**

Ready for a task plan.

### Phase 2: Suggestions and explicit preview

**Goal**

Help users find and inspect supported references in column pickers without changing edit or save behavior.

**Focus**

- Add guided reference suggestions to Business Keys, non-fixed Columns, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows while retaining each field's ordinary column suggestions.
- Add an explicit, read-only preview of a reference item, labeled as based on cached configuration. Keep the raw reference visible when preview is unavailable.
- Check the full picker and save flow, including Fixed Entity Columns and existing project validation.

**Depends On**

- Phase 1 cache check, expansion result, and form round-trip behavior.

**Outputs**

- Supported pickers with suggestions and an optional preview, plus regression results for unchanged behavior.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`) Supported pickers suggest only supported `keys` and `columns` references from the active project's completed cache.
- `PH2-AC-2` (from `P-AC-4`) Ordinary column suggestions remain field-specific, and Fixed Entity Columns have no reference suggestions or preview.
- `PH2-AC-3` (from `P-AC-2`, `P-AC-7`) A user-requested preview shows the complete expanded columns as read-only cached configuration without changing the reference, form value, or saved YAML.
- `PH2-AC-4` (from `P-AC-3`) An unavailable preview shows no partial columns or form error and does not block editing or saving.
- `PH2-AC-5` (from `P-AC-6`) No backend reference endpoint, mapper resolution mode, project-level reference validation, or Core directive change is introduced.

**Validation Milestones**

- `VM-2` Check suggestions and preview in each supported field, project switching, unavailable results, unchanged saves, Fixed Entity Columns, and existing validation behavior (`PH2-AC-1`–`PH2-AC-5`).

**Task-Plan Handoff**

- Use `P-AC-1`–`P-AC-7` and the Phase 1 outputs. Reuse prototype frontend code only where it fits this proposal. Keep the provider/schema business-key save guard as a separate decision. No design question blocks this plan.

**Readiness**

Ready for a task plan after Phase 1 delivers its outputs.

## Cross-Phase Rules

- Keep all reference lookup in the completed frontend cache; do not resolve against unsaved edits or make per-reference requests.
- Treat preview failure as an unavailable display result, never as a project error or save condition.

## Validation Strategy

Validate Phase 1's cache, expansion, Core parity, and representation rules before connecting them to pickers. After Phase 2, verify the complete editor flow and the unchanged behavior named in `P-AC-4`–`P-AC-6`. The phase task plans choose exact tests and commands.
