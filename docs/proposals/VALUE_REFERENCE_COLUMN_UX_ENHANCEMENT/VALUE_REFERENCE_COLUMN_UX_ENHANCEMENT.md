# Improve `@value` Guidance and Preview in Column Pickers

## Status

- Proposed feature
- Scope: Best-effort reference suggestions and column previews in entity column pickers
- Goal: Help users enter and inspect column references without adding a backend resolution or validation workflow
- Related: The broader [Make `@value` References Usable in Column Pickers proposal](../VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS.md) and its `value-reference-column-pickers` implementation branch are retained as prior work and a source of reusable code, not as the design for this change.

## Summary

Add reference suggestions and an explicitly requested, read-only column preview to supported entity column pickers. Resolve references only from cached entity data known to belong to the active project. Keep the stored reference unchanged, and treat expansion as a best-effort display aid: an unavailable preview must not block editing, saving, or project validation.

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

The entity list endpoint returns each entity's configuration in `entity_data`, and the frontend entity store keeps the loaded entities in memory. This gives the editor a local source for suggestions and preview without a new per-reference request. During `fetchEntities()`, the store changes `currentProjectName` before replacing `entities`, so that name alone does not prove the cached list belongs to the active project while a project switch is loading.

Some chip editors normalize a scalar reference into a list for display and emit the normalized list on update. For example, the foreign-key editor converts scalar `local_keys` and `remote_keys` to arrays. An unchanged load and save can therefore change the stored scalar/list representation unless the form adapter preserves it.

The existing `value-reference-column-pickers` branch implements a broader draft-aware backend approach, including mapper-scoped resolution and project-level reference validation. This proposal treats that branch as a prototype. The broader [original proposal](../VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS.md) remains unchanged.

## Proposed Design

Use the loaded entity store as the only source for reference suggestions and previews. Use cached entities only when their completed load is known to belong to the active project. The active project name by itself is not sufficient while a project switch is pending. If cache ownership is unknown or does not match, make suggestions and previews unavailable until the active project's entities have loaded. Do not fall back to a backend resolution request or disk read.

Offer progressive suggestions for references to `entities.<entity>.keys` and `entities.<entity>.columns` when the cached value has a supported column-list shape. Keep ordinary column suggestions scoped to the field being edited; do not add every project reference to those suggestions.

Supported values are a literal list of column-name strings, a scalar complete reference, or a list of column-name strings and complete references. For example:

```yaml
# Literal list
keys: [sample_id, site_id]

# Scalar reference
keys: "@value: entities.site.keys"

# Literal and reference items
keys:
  - sample_id
  - "@value: entities.site.keys"
```

Follow nested references recursively and flatten them in place, preserving order and duplicates. Parse only strings that are themselves complete supported `@value:` references to `entities.<entity>.keys` or `entities.<entity>.columns`. Partial expressions, legacy `+` concatenation expressions, nulls, numbers, dictionaries, and nested lists are unsupported; do not interpret them as column names or expand them.

Provide an explicit preview action for reference items in supported column pickers. Show expanded columns in a read-only popover or equivalent view labeled as based on cached configuration, not the current unsaved form. Never replace or modify the reference chip when showing a preview, and do not change the form value or saved YAML.

Expansion succeeds only if the entire reference tree resolves to supported column-list values. A missing cache, entity, or path, a cycle, or any unsupported nested value makes the complete preview unavailable; never show intermediate or partially expanded columns. Keep the raw reference visible and show a quiet “Preview unavailable” indication. Do not raise a form validation error or prevent saving.

Make only the form-adapter changes needed to preserve the original scalar or list representation when no semantic edit occurred. Internal normalization for chip display must not silently change the stored representation. Reuse suitable frontend code from the prototype branch selectively; do not port its backend resolution, mapper, or project-validation design into this feature.

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
- Compare expansion for supported reference forms with Core's effective `@value` expansion, including nested list-item references, order, and duplicates. Restrict frontend support where semantics differ; do not change Core to match the preview.
- Test that the picker suggests only supported cached `keys` and `columns` references while ordinary suggestions remain field-specific.
- Test that suggestions and previews are unavailable during a project switch until the cache is known to belong to the active project.
- Test that the explicit preview action displays a read-only cached-configuration result and does not change the selected reference or field value.
- Test that failed expansion leaves the raw reference intact and does not block edits or saves.
- Test scalar references, mixed lists, and legacy expressions through form load and save. Confirm that form adapters preserve the original scalar/list representation when no semantic edit occurred.
- Confirm Fixed Entity Columns are unchanged and that project validation behavior is unchanged.

## Acceptance Criteria

- `P-AC-1` Reference suggestions use only a completed entity cache known to belong to the active project and target supported `keys` or `columns` values.
- `P-AC-2` For supported reference forms, the preview matches Core's effective expansion, including nested list-item references, order, and duplicates, without changing the form value or saved YAML.
- `P-AC-3` A missing or mismatched cache, entity, or path, a cycle, or any unsupported value in the reference tree makes the entire preview unavailable. The raw reference remains visible; no partial columns, project validation error, or save block is produced.
- `P-AC-4` Ordinary column suggestions remain field-specific, and Fixed Entity Columns receive no reference suggestions or preview.
- `P-AC-5` Existing scalar references, mixed lists, and legacy `+` expressions retain their original scalar or list representation through an unchanged form load and save, including editors that normalize values internally for display.
- `P-AC-6` The feature adds no backend reference endpoint, mapper resolution mode, or project-level reference validation, and does not change Core directive resolution.
- `P-AC-7` A user explicitly requests a reference preview; it is displayed read-only as based on cached configuration and cannot change the selected reference or the field's stored value.

## Planning Handoff

- Use only a completed cache known to belong to the active project; do not add per-reference disk or backend resolution or merge unsaved edits from the current form into referenced entities.
- Implement the supported reference syntax and all-or-nothing behavior above. Keep the explicit preview read-only, preserve original serialization, and leave Fixed Entity Columns unchanged.
- Reuse suitable frontend code from the prototype branch selectively; do not import its backend, mapper, or project-validation design.
- Decide separately whether the reference-aware provider/schema business-key save guard from the prototype branch should be retained. Do not fold it into this UI change.

## Final Recommendation

Implement this as a frontend-only, cache-backed reference suggestion and preview helper. Keep the broader validation and mapper work on its original branch unless separately approved.
