# Improve `@value` Guidance and Preview in Column Pickers

## Status

- Proposed feature
- Scope: Best-effort reference suggestions and column previews in entity column pickers
- Goal: Help users enter and inspect column references without adding a backend resolution or validation workflow
- Related: The broader [Make `@value` References Usable in Column Pickers proposal](../VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS.md) and its `value-reference-column-pickers` implementation branch are retained as prior work and a source of reusable code, not as the design for this change.

## Summary

Add reference suggestions and an on-demand expanded-column preview to supported entity column pickers. Resolve references from the entity data already held in the frontend store. Keep the stored reference unchanged, and treat expansion as a best-effort display aid: an unavailable preview must not block editing, saving, or project validation.

This narrows the broader implementation, which adds backend reference endpoints, scoped mapper resolution, and project-level reference validation. Those mechanisms are not required for this editor-only helper.

## Problem

A column picker can contain an `@value` reference without showing the column names it represents. Users may also have difficulty discovering which references they can enter. The editor should make supported references easier to find and inspect, but failures in this convenience feature should not create project errors or interrupt editing.

## Scope

- Offer guided `@value` suggestions in column-list fields that support references: Business Keys, Columns for non-fixed entities, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows.
- Use the current project's in-memory entity list to suggest references to `keys` and `columns`.
- Let a user inspect the ordered columns produced by a supported reference, including nested list-item references.
- Keep the reference in the form and saved YAML. Expansion is display-only.
- Preserve the existing field-specific ordinary column suggestions.
- Keep Fixed Entity Columns outside this interaction.

## Non-Goals

- Add backend completion or resolution endpoints, mapper modes, or a general-purpose directive resolver for the editor.
- Add project-level validation for missing, invalid, or wrong-type references.
- Change Core `@value` resolution, project save behavior, or existing validation behavior.
- Expand references automatically on load or save, or add a **Replace with columns** action.
- Guarantee that a referenced column is produced by a source or transformation.
- Resolve unsaved draft edits against other entities. A preview may reflect the last entity data loaded into the frontend store.
- Resolve `@include`, `@load`, environment variables, or legacy `+` expressions. Preserve unsupported or legacy directive text without interpreting it.
- Add this behavior to Fixed Entity Columns.

## Current Behavior

The entity list endpoint returns each entity's configuration in `entity_data`, and the frontend entity store keeps the loaded entities in memory. This gives the editor a local source for suggestions and preview without a new per-reference request.

The existing `value-reference-column-pickers` branch implements a broader draft-aware backend approach, including mapper-scoped resolution and project-level reference validation. This proposal treats that branch as a prototype. The broader [original proposal](../VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS.md) remains unchanged.

## Proposed Design

Use the loaded entity store as the only source for reference suggestions and previews. Do not fall back to a backend resolution request or disk read if the relevant entity data is unavailable.

Offer progressive suggestions for references to `entities.<entity>.keys` and `entities.<entity>.columns` when the cached value has a supported column-list shape. Keep ordinary column suggestions scoped to the field being edited; do not add every project reference to those suggestions.

When the user asks to inspect a reference, follow its path through the cached entity data. Expand nested references in list items in order, preserving literal column order. Keep the operation read-only: do not change the form value or saved YAML.

If the project cache is unavailable, the path is missing, a cycle is found, or a value has an unsupported shape, leave the raw reference visible and show a quiet “Preview unavailable” indication. Do not return partial columns, raise a form validation error, or prevent saving. Do not parse legacy `+` expressions; show them as raw text.

## Alternatives Considered

- **Keep the broader backend implementation:** It can provide draft-aware resolution and project-level errors, but those guarantees add backend, mapper, and validation code that this non-critical preview does not need.
- **Restore all references to ordinary dropdowns:** This is simpler than guided entry but can make field suggestions long and include paths that are not column lists.
- **Require users to inspect YAML:** This avoids new UI behavior but leaves reference entry and inspection inconvenient.

## Risks And Tradeoffs

- Previews may be stale when an entity has unsaved changes or cached data has not refreshed. This is an accepted limitation of the best-effort helper.
- A preview only reports the columns declared by the referenced property. It does not prove that a source or later pipeline stage produces them.
- Unsupported references remain editable but cannot be inspected through this helper.

## Testing And Validation

- Test the in-memory expansion helper with literal lists, nested references, order preservation, missing paths, cycles, and unsupported values.
- Test that the picker suggests only supported cached `keys` and `columns` references while ordinary suggestions remain field-specific.
- Test that failed expansion leaves the raw reference intact and does not block edits or saves.
- Test scalar references, mixed literal/reference lists, and legacy expressions through form load and save to confirm their stored shape is preserved.
- Confirm Fixed Entity Columns are unchanged and that project validation behavior is unchanged.

## Acceptance Criteria

- `P-AC-1` Reference suggestions use only the current project's loaded entity data and target supported `keys` or `columns` properties with column-list values.
- `P-AC-2` A supported reference preview shows its ordered columns, including nested list-item references, without changing the form value or saved YAML.
- `P-AC-3` A missing cache entry, path, cycle, or unsupported value leaves the raw reference visible and shows a non-blocking unavailable state; it does not add a project validation error or prevent saving.
- `P-AC-4` Ordinary column suggestions remain field-specific, and Fixed Entity Columns receive no reference suggestions or preview.
- `P-AC-5` Existing scalar references, mixed lists, and legacy `+` expressions retain their stored form through an unchanged form load and save.
- `P-AC-6` The feature adds no backend reference endpoint, mapper resolution mode, or project-level reference validation, and does not change Core directive resolution.

## Planning Handoff

- Use the frontend entity store for reference lookup; do not add per-reference disk or backend resolution.
- Keep preview read-only and best-effort. Do not merge unsaved edits from the current form into referenced entities.
- Support only `entities.<entity>.keys` and `entities.<entity>.columns` values with supported column-list shapes. Preserve unsupported references as raw text.
- Preserve stored directive text and scalar/list form. Keep Fixed Entity Columns excluded.
- Validate that expansion order is stable and failures do not block editing, saving, or project validation.
- Decide separately whether the reference-aware provider/schema business-key save guard from the prototype branch should be retained. Do not fold it into this UI change.

## Final Recommendation

Implement this as a frontend-only, cache-backed reference suggestion and preview helper. Keep the broader validation and mapper work on its original branch unless separately approved.
