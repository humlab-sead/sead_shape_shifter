# Make `@value` References Usable in Column Pickers

## Status

- Proposed feature
- Scope: Entity editor fields that accept column lists and `@value` references
- Goal: Keep references convenient while making their columns visible and editable
- Related: Supersedes the UI phases of the archived [Value Directive UX Plan](../done/VALUE_DIRECTIVE_UX_PLAN.md). Its list-flattening and scalar-shorthand work has shipped; its context-aware `/valid-directives` phase is replaced by the guided entry below, and its dangling-reference validation phase is folded into this proposal.

## Summary

Add guided reference entry, an ordered column preview, and an explicit **Replace with columns** action to the entity editor. Keep ordinary column suggestions short and relevant to each field. This addresses the difficulty of finding a reference and fixing a column validation error without giving up the benefit of a reference that follows later changes to its source.

## Problem

A saved `@value: entities.site.keys` chip hides the columns it currently represents. When validation reports overlapping unnest variables or a business key that the entity does not produce, the editor does not show which referenced columns caused the problem. Users must inspect another entity or the YAML to work it out. Removing references from ordinary column suggestions has shortened those lists, but it has also made references harder to discover and enter in some fields.

## Scope

- Column-list inputs in the entity editor that already support `@value`, including Business Keys, Columns, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows. The last two load a scalar reference as an empty selection today and need the same normalization.
- Simple references to entity properties that resolve to lists of column names. Keep manually entered references to other supported paths editable.
- Read-only inspection of resolved columns and an explicit conversion to literal column names.
- Project-level validation that reports dangling or wrong-type `@value` references in these fields through the existing validation pipeline.

## Non-Goals

- Change `@value` syntax, resolution order, existing validation rules, or stored YAML formats. Adding the new dangling-reference check is in scope; altering how valid references resolve is not.
- Automatically expand references on load or save, or migrate existing projects.
- Turn column suggestions into a guarantee that a source or query will produce every suggested column.
- Build a general editor for legacy `+` reference expressions or scalar references outside column-list fields.

## Current Behavior

The API and YAML preserve directives; `ProjectMapper.to_core()` resolves them for Core use. A lone reference can be stored as a scalar string, while references mixed with literal columns can be stored as list items and flattened during resolution. Business Keys and Columns load scalar references as chips and write a lone reference back as a scalar. A scalar Deduplication Columns reference currently loads as an empty column selection in the form. The unnest editor expects arrays for `id_vars` and `value_vars` and does not normalize scalar references for its chip inputs.

Business Keys and Columns receive field-specific column candidates from a service that evaluates an unsaved entity draft. Those candidate lists do not include a project-wide set of references. FK key pickers still append paths from the project-wide `valid-directives` endpoint when focused. That endpoint lists paths without checking whether each result is a column list. The existing directive validation endpoint checks saved project data and does not return resolved values to the UI. Core already checks overlapping `id_vars`/`value_vars` and business keys that are not produced; the editor does not connect those errors to the columns inside a reference.

## Proposed Design

### Guided entry without a long dropdown

Keep ordinary column suggestions scoped to the edited field. When the user types `@value` or chooses a small **Insert reference** action, offer completion in steps: `@value: entities.`, matching entity names as the name is typed, then list-valued properties of the chosen entity such as `keys` and `columns`. Show only paths whose current value resolves to a list of strings; do not suggest a reference to the field being edited. For FK fields, put the relevant local or target entity first, while allowing other valid entities.

The user can still paste or type a full supported reference. Check it when committed and show a useful error for a missing path, wrong result type, or resolution failure. An invalid saved reference remains visible and editable. Do not put every possible reference back into the ordinary dropdown.

FK key pickers switch to this guided entry and stop appending the project-wide `valid-directives` path list when focused. That endpoint returns untyped paths — including scalar paths such as `public_id` — so it is not a suitable column-list source; completion is served from draft-aware resolution instead.

Normalize saved scalar references for each in-scope chip input and serialize a lone reference back to the same scalar form. The form must preserve existing references when a user opens and saves an entity without changing them.

### Inspect and replace a reference

Give each reference chip a compact inspection action. Its detail view shows the current ordered column names, including columns from nested references, or an explicit reason why they cannot be resolved. Show the reference path alongside the result so users can see where the columns come from. For the edited field, identify definite conflicts using existing validators: for example, columns shared by expanded `id_vars` and `value_vars`, or a business key reported as not produced. Attribute a conflict to the current form only when its validation result matches the current draft. Discard that annotation after later edits. If only saved-project results are available, identify them as saved-project results rather than current-draft conflicts. Treat missing stage-aware candidates as advisory when source columns are incomplete.

Offer **Replace with columns** from that detail view for a simple reference that resolves to a list of strings. Replace only the chosen reference chip, in place, preserving column order and any surrounding literal chips. Show that the new names are a snapshot and will no longer follow changes to the referenced property. The edit remains in the form until the user saves; the user can undo it before saving. Disable replacement if resolution fails or returns a different type. Keep legacy expressions intact unless a safe, exact expansion is available.

Reference completion and preview must use the current unsaved entity draft together with the saved project. Backend resolution should use the existing project mapping and directive rules on a read-only copy, rather than a separate frontend interpretation. Where validation results are used to annotate the draft, they must match that draft; if only saved-project results are available, label them accordingly and do not present them as current-draft conflicts. Ignore preview, completion, and validation results made stale by later edits. Preserve project authorization for any new read request.

### Validate dangling references

Add a project-level check for `@value` references in the in-scope column-list fields, including scalar and list-item forms. Run it while the raw directive text is still available, before the normal validation path discards that text during resolution. Use the existing resolution rules on a read-only copy to check that each reference path exists and resolves to a list of strings, while retaining the original entity, field, and path for errors. Combine these errors with the existing validation results so they appear in the validation panel. Do not change how valid references resolve in Core. This replaces the deferred dangling-reference phase of the archived plan and gives the preview an honest unresolved status: a reference the preview cannot expand should also be a saved-project error, not a silent gap.

## Alternatives Considered

- **Restore every reference to each dropdown:** quick to implement, but recreates long lists and offers unsuitable paths in column fields.
- **Always display or store expanded columns:** makes names visible, but silently removes the dynamic link and creates large chip lists.
- **Require YAML editing for references:** preserves syntax flexibility, but leaves common fixes difficult in the form editor.

## Risks And Tradeoffs

Previewing an unsaved draft may fail when another field has an unresolved or circular reference. Show a local preview error and keep the raw chip; never substitute guessed columns. A literal replacement can become stale when the referenced entity changes, so the action must explain the snapshot behavior. Resolving on each keystroke may be costly; completion should narrow candidates as the user types, and preview should run when requested or after a selected reference changes.

## Testing And Validation

Verify completion, preview, and replacement for a scalar reference, a reference mixed with literals, nested references, an invalid path, and a legacy expression. Check FK local and remote context, draft edits before save, stale preview and validation results, keyboard use, and the existing YAML round trip. Confirm that overlap and non-produced-key errors can be traced to the expanded columns without changing the underlying validators. For the new reference check, cover a missing path, paths that resolve to a scalar or another non-list type, valid references, and both scalar and list-item storage forms. Include a wrong-type list-item reference that would otherwise become an ordinary string after resolution, and confirm the check still reports its original path.

## Acceptance Criteria

- `P-AC-1` Ordinary column suggestions remain field-specific and do not include the project-wide reference list; existing saved references still appear as selected values.
- `P-AC-2` Typing `@value` offers progressively filtered entity and list-valued-property completions, including `keys` and `columns`; a full manually entered reference can still be validated.
- `P-AC-3` A selected reference can show its ordered resolved column names from the current draft, or a clear unresolved status, without saving or changing the field.
- `P-AC-4` When validation results match the current draft, the editor shows which expanded columns cause an unnest overlap or non-produced business-key error; it discards annotations made stale by later edits. Incomplete candidate lists do not produce a false hard error.
- `P-AC-5` **Replace with columns** changes only the selected resolvable reference into ordered literal chips, explains that the link is lost, and can be undone before save.
- `P-AC-6` In-scope fields preserve saved scalar references, mixed lists, manually entered valid paths, and legacy expressions through a form save; Core resolution behavior remains unchanged unless the user explicitly replaces a reference.
- `P-AC-7` Completion and preview work with keyboard input, respect project read authorization, and discard preview, completion, or validation results made stale by later edits.
- `P-AC-8` Before resolution removes the original reference text, validation checks scalar and list-item `@value` references in in-scope fields. A missing path or a reference that does not resolve to a list of strings produces an error naming the entity, field, and original path; valid references resolve exactly as before.

## Planning Handoff

- Preserve directive text in API and YAML data and resolve it through `ProjectMapper.to_core()` for Core behavior. Keep stage-aware column candidates separate from reference completion.
- Use the existing validators for hard errors. Treat column candidates as advisory when source data is incomplete.
- Preserve the raw directive tree long enough to validate reference paths and result types. Aggregate these errors with normal validation results before the raw reference text is lost. Include list-item references whose scalar result would otherwise look like an ordinary column name.
- Validate the outcomes in `P-AC-1` through `P-AC-8` against saved projects and unsaved drafts. During the first phase, confirm the exact column-list controls that accept `@value` so the shared interaction is applied only where the stored contract permits it.
- Reference completion replaces the archived plan's context-aware `/valid-directives` extension; do not re-plan that phase. The existing `DirectiveValidator` looks up a raw path value; it does not expand nested directives, and its endpoint does not return that value. Use the existing project mapping and directive resolution on a read-only copy with the current draft applied for preview and completion. Return an unresolved status instead of a partial list when any nested reference remains unresolved or has a non-string item.
- Use validation results for conflict annotations only when they match the current draft. If the editor has only saved-project results, label them as such and do not attribute their conflicts to the unsaved form.

## Final Recommendation

Add progressive reference entry, on-demand resolved-column inspection, and explicit replacement to the entity editor's `@value`-capable column pickers.
