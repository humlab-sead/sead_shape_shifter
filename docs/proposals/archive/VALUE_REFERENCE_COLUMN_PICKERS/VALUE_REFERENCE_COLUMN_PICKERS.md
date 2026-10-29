# Make `@value` References Usable in Column Pickers

## Status

- Archived; superseded by [Improve `@value` Guidance and Preview in Column Pickers](../../done/VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT/VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT.md). This proposal will not be completed. Associated [PR #605](https://github.com/humlab-sead/sead_shape_shifter/pull/605) will not be merged.
- Scope: Entity editor fields that accept column lists and `@value` references, except Fixed Entity Columns
- Goal: Keep references convenient while making their columns visible and editable
- Related: Supersedes the UI phases of the archived [Value Directive UX Plan](../../done/VALUE_DIRECTIVE_UX_PLAN.md). Its list-flattening and scalar-shorthand work has shipped; its context-aware `/valid-directives` phase is replaced by the guided entry below, and its dangling-reference validation phase is folded into this proposal.

## Summary

Add guided reference entry, an ordered column preview, and an explicit **Replace with columns** action to the entity editor. Keep ordinary column suggestions short and relevant to each field. This addresses the difficulty of finding a reference and fixing a column validation error without giving up the benefit of a reference that follows later changes to its source.

## Problem

A saved `@value: entities.site.keys` chip hides the columns it currently represents. When validation reports overlapping unnest variables or a business key that the entity does not produce, the editor does not show which referenced columns caused the problem. Users must inspect another entity or the YAML to work it out. Removing references from ordinary column suggestions has shortened those lists, but it has also made references harder to discover and enter in some fields.

## Scope

- Column-list inputs in the entity editor that support `@value`: Business Keys, Columns for non-fixed entities, FK Local/Remote Keys, unnest ID/Value Variables, Deduplication Columns, and Drop Empty Rows. The last two load a scalar reference as an empty selection today and need the same normalization.
- Simple references to entity properties that resolve to lists of column names. Keep manually entered references to other supported paths editable.
- Read-only inspection of resolved columns and an explicit conversion to literal column names.
- Project-level validation that reports dangling or wrong-type `@value` references in these fields through the existing validation pipeline.

## Non-Goals

- Change `@value` syntax, resolution order, existing validation rules, or stored YAML formats. Adding the new dangling-reference check is in scope; altering how valid references resolve is not.
- Automatically expand references on load or save, or migrate existing projects.
- Turn column suggestions into a guarantee that a source or query will produce every suggested column.
- Add guided entry, preview, replacement, or the new column-list reference check to Fixed Entity Columns. Their positional values and stored column order need a separate design.
- Build a general editor for legacy `+` reference expressions or scalar references outside column-list fields. Preserve and validate legacy expressions already present in in-scope fields.

## Current Behavior

The API and YAML preserve directives; `ProjectMapper.to_core()` resolves them for Core use. A lone reference can be stored as a scalar string, while references mixed with literal columns can be stored as list items and flattened during resolution. Business Keys and Columns load scalar references as chips and write a lone reference back as a scalar. A scalar Deduplication Columns reference currently loads as an empty column selection in the form. The unnest editor expects arrays for `id_vars` and `value_vars` and does not normalize scalar references for its chip inputs. Fixed Entity Columns use a positional schema that does not preserve scalar references through a form save. A legacy `+` expression beginning with a literal list can also be changed from a scalar into a list item on form save, changing its resolved shape.

Business Keys and Columns receive field-specific column candidates from a service that evaluates an unsaved entity draft. Those candidate lists do not include a project-wide set of references. FK key pickers still append paths from the project-wide `valid-directives` endpoint when focused. That endpoint lists paths without checking whether each result is a column list. The existing directive validation endpoint checks saved project data and does not return resolved values to the UI. Core already checks overlapping `id_vars`/`value_vars` and business keys that are not produced; the editor does not connect those errors to the columns inside a reference.

## Proposed Design

### Guided entry without a long dropdown

Keep ordinary column suggestions scoped to the edited field. When the user types `@value` or chooses a small **Insert reference** action, offer completion in steps: `@value: entities.`, matching entity names as the name is typed, then list-valued properties of the chosen entity such as `keys` and `columns`. Show only paths whose current value resolves to a list of strings; do not suggest a reference to the field being edited. For FK fields, put the relevant local or target entity first, while allowing other valid entities.

The user can still paste or type a full supported reference. Check it when committed and show a useful error for a missing path, wrong result type, or resolution failure. An invalid saved reference remains visible and editable. Do not put every possible reference back into the ordinary dropdown.

FK key pickers switch to this guided entry and stop appending the project-wide `valid-directives` path list when focused. That endpoint returns untyped paths — including scalar paths such as `public_id` — so it is not a suitable column-list source; completion is served from draft-aware resolution instead.

Normalize saved scalar references for each in-scope chip input and serialize a lone reference back to the same scalar form. The form must preserve existing references when a user opens and saves an entity without changing them. Keep a supported legacy `+` expression stored as a scalar in that scalar form, including expressions that begin with a literal list. Display it as one raw expression chip. Do not offer **Replace with columns** for legacy expressions in this proposal.

### Inspect and replace a reference

Give each reference chip a compact inspection action. Its detail view shows the current ordered column names, including columns from nested references, or an explicit reason why they cannot be resolved. Show the reference path alongside the result so users can see where the columns come from. For the edited field, identify definite conflicts using existing validators: for example, columns shared by expanded `id_vars` and `value_vars`, or a business key reported as not produced. Attribute a conflict to the current form only when its validation result matches the current draft. Discard that annotation after later edits. If only saved-project results are available, identify them as saved-project results rather than current-draft conflicts. Treat missing stage-aware candidates as advisory when source columns are incomplete.

Offer **Replace with columns** from that detail view for a simple reference that resolves to a list of strings. Replace only the chosen reference chip, in place, preserving column order and any surrounding literal chips. Show that the new names are a snapshot and will no longer follow changes to the referenced property. The edit remains in the form until the user saves; the user can undo it before saving. Disable replacement if resolution fails or returns a different type.

Where validation results are used to annotate the draft, they must match that draft; if only saved-project results are available, label them accordingly and do not present them as current-draft conflicts. Ignore preview, completion, and validation results made stale by later edits. Preserve project authorization for any new read request.

### Resolve each requested reference independently

Reference completion and preview use the current unsaved entity draft together with the saved project. Extend `ProjectMapper.to_core()` with a read-only editor mode that resolves only the requested reference and its nested dependencies under the same directive, file, and environment rules as full Core conversion. Full-project conversion keeps its current behavior. A failure in the requested reference or one of its dependencies produces a local unresolved reason, never a partial column list. A failure in an unrelated field does not prevent valid property completions or previews. Resolve completion candidates independently after filtering by the typed entity and property prefix; do not interpret directives in the frontend.

### Validate dangling references

Add a project-level check for `@value` references in the in-scope column-list fields, including scalar and list-item forms. Run it while the raw directive text is still available, before the normal validation path discards that text during resolution. Check each simple reference independently for a missing path, failed resolution, or a result other than a list of strings. For a supported legacy `+` expression, check every `@value` operand and require the complete expression to resolve to a list of strings under existing rules; an operand that resolves to a scalar remains valid when those rules produce a valid list. Report a missing operand even when the current expression parser would skip it.

Retain the original entity, field, and path or expression in each error. Combine independent reference errors with normal validation results. If full-project mapping fails, return the collected reference errors and a project-resolution error; skip checks that require a resolved project. Do not change how valid references resolve in Core. This replaces the deferred dangling-reference phase of the archived plan. When an unresolved reference is saved, the project validation panel reports it instead of leaving a silent gap.

## Alternatives Considered

- **Restore every reference to each dropdown:** quick to implement, but recreates long lists and offers unsuitable paths in column fields.
- **Always display or store expanded columns:** makes names visible, but silently removes the dynamic link and creates large chip lists.
- **Require YAML editing for references:** preserves syntax flexibility, but leaves common fixes difficult in the form editor.

## Risks And Tradeoffs

Scoped resolution adds mapper complexity but keeps an unrelated broken reference from blocking the current edit. A circular or unresolved dependency of the selected reference still produces a local error and leaves its raw chip intact; never substitute guessed columns. A literal replacement can become stale when the referenced entity changes, so the action must explain the snapshot behavior. Resolving on each keystroke may be costly; completion should narrow candidates as the user types, and preview should run when requested or after a selected reference changes.

## Testing And Validation

Verify completion, preview, and replacement for a scalar reference, a reference mixed with literals, nested references, and an invalid path. Check FK local and remote context, draft edits before save, stale preview and validation results, keyboard use, and the existing YAML round trip. Confirm that an unrelated missing or circular reference does not block valid completion or preview, while a broken dependency of the requested path returns an unresolved reason. Confirm that Fixed Entity Columns do not gain this interaction. Confirm that overlap and non-produced-key errors can be traced to the expanded columns without changing the underlying validators.

For the new reference check, cover a missing path, paths that resolve to a scalar or another non-list type, valid references, and both scalar and list-item storage forms. Include a wrong-type list-item reference that would otherwise become an ordinary string after resolution. Check both `@value`-first and literal-first legacy `+` expressions for unchanged scalar form saves, missing operands, valid scalar operands, and valid ordered results. Confirm each error reports the original path or expression and that a full-project mapping failure returns collected reference errors plus a project-resolution error.

## Acceptance Criteria

- `P-AC-1` Ordinary column suggestions remain field-specific and do not include the project-wide reference list; existing saved references still appear as selected values. Fixed Entity Columns do not gain reference completion, preview, replacement, or the new column-list reference check.
- `P-AC-2` Typing `@value` offers progressively filtered entity and list-valued-property completions, including `keys` and `columns`; a full manually entered reference can still be validated. An unrelated broken reference does not hide valid completions.
- `P-AC-3` A selected reference can show its ordered resolved column names from the current draft, or a clear unresolved status for a broken dependency, without saving or changing the field. An unrelated broken reference does not block its preview.
- `P-AC-4` When validation results match the current draft, the editor shows which expanded columns cause an unnest overlap or non-produced business-key error; it discards annotations made stale by later edits. Incomplete candidate lists do not produce a false hard error.
- `P-AC-5` **Replace with columns** changes only the selected resolvable simple reference into ordered literal chips, explains that the link is lost, and can be undone before save. The action is unavailable for legacy `+` expressions.
- `P-AC-6` In-scope fields preserve saved scalar references, mixed lists, manually entered valid paths, and legacy `+` expressions through a form save. A legacy expression stored as a scalar remains a scalar, including one beginning with a literal list. Core resolution behavior remains unchanged unless the user explicitly replaces a simple reference.
- `P-AC-7` Completion and preview work with keyboard input, respect project read authorization, and discard preview, completion, or validation results made stale by later edits.
- `P-AC-8` Before resolution removes the original reference text, validation checks scalar and list-item `@value` references in in-scope fields, including every operand of supported legacy `+` expressions. A missing path, failed resolution, wrong-type simple reference, or expression that does not yield a list of strings produces an error naming the entity, field, and original path or expression. One failure does not hide errors for other references; if full-project mapping fails, collected reference errors and a project-resolution error are returned. Valid references resolve exactly as before.

## Planning Handoff

- Preserve directive text in API and YAML data and resolve it through `ProjectMapper.to_core()` for Core behavior. Its read-only editor mode resolves only a requested reference and its nested dependencies; default full-project conversion stays unchanged. Keep stage-aware column candidates separate from reference completion. Exclude Fixed Entity Columns from the shared interaction and new column-list check.
- Use the existing validators for hard errors. Treat column candidates as advisory when source data is incomplete.
- Preserve the raw directive tree long enough to validate reference paths and result types. Check each path independently and aggregate its errors with normal validation results before the raw reference text is lost. Include list-item references whose scalar result would otherwise look like an ordinary column name. Parse supported legacy `+` expressions to check every operand without changing their resolution, and preserve scalar expressions as scalars on form save.
- Validate the outcomes in `P-AC-1` through `P-AC-8` against saved projects and unsaved drafts. During the first phase, confirm the exact column-list controls that accept `@value` so the shared interaction is applied only where the stored contract permits it; Fixed Entity Columns remain excluded.
- Reference completion replaces the archived plan's context-aware `/valid-directives` extension; do not re-plan that phase. The existing `DirectiveValidator` looks up a raw path value; it does not expand nested directives, and its endpoint does not return that value. Use mapper-owned scoped resolution on a read-only copy with the current draft applied for preview and completion. Return an unresolved status instead of a partial list when a requested dependency remains unresolved or has a non-string item; unrelated failures must not suppress valid results.
- Use validation results for conflict annotations only when they match the current draft. If the editor has only saved-project results, label them as such and do not attribute their conflicts to the unsaved form.

## Final Recommendation

Add progressive reference entry, on-demand resolved-column inspection, and explicit replacement to the entity editor's `@value`-capable column pickers.
