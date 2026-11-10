# Direct Target-ID Foreign Key UX

## Status

- Proposed feature
- Scope: Entity-editor support for `foreign_key_value_sources`
- Goal: Let project authors select eligible direct target-ID relationships without editing YAML.

## Summary

Add a small multi-select to the entity editor for direct target-model foreign keys. Populate it with every relationship supported by direct-ID mode, whether or not the source currently produces the target ID column. Let structural validation report missing output columns. Preserve the complete `foreign_key_value_sources` map across form, YAML, and save operations.

This keeps the UI separate from project `foreign_keys` links, which create Core links using local `system_id` values. It adds a visual way to configure the existing feature without changing its behavior or YAML contract.

## Problem

The [direct target-ID feature](../done/DIRECT_TARGET_ID_FOREIGN_KEYS/DIRECT_TARGET_ID_FOREIGN_KEYS.md) is supported in project YAML, but authors must enter `foreign_key_value_sources` manually. The entity dialog has Basic and Foreign Keys sections but no control for this setting. Its YAML and saved-entity loaders also rebuild form data without this map, so adding a control without round-trip handling could lose existing values.

The existing target-model entity picker is not a suitable metadata source: it lists only target entities absent from the project and reports required-link summaries. The selector needs all direct relationships for the current target-model entity, including optional targets and targets already configured in the project.

## Scope

- Add a target-ID selector to the entity editor.
- Add a read-only contract that supplies resolved direct-FK metadata for the current entity.
- Offer every target-model direct FK supported by direct-ID mode; rely on structural validation for output-column requirements.
- Preserve and update the complete `foreign_key_value_sources` map.
- Preserve existing direct-ID and project-FK behavior.

## Non-Goals

- Changing target-model relationships, project validation, or change-request packaging.
- Changing how Core project FK links work.
- Replacing or removing YAML editing or its existing schema completions.
- Supporting target IDs that are not declared by a direct target-model FK.
- Changing the existing target-model entity picker's missing-entity behavior.

## Current Behavior

- A project entity can declare `foreign_key_value_sources` in YAML. `public_id` applies to change-request package values; absent entries retain the `system_id` default.
- The target model must be selected for this declaration, and the target entity must define a direct FK relationship, `public_id`, and `target_table`.
- Core structural validation checks the target entity's `public_id` against [`get_target_facing_columns()`](../../../src/model.py#L968), which includes computed columns and accounts for columns removed by unnesting. It reports a missing output column without requiring the selector to duplicate that check.
- The target-model entity picker excludes entities already present in the project and returns required-link summaries, not all FK relationships for an existing entity.
- The current entity dialog exposes basic entity settings and project FK links, but has no visual control for this map.
- The form parser and saved-entity loader construct explicit field lists without `foreign_key_value_sources`.

## Proposed Design

### Relationship metadata and selector state

Add a read-only backend contract for the selector. For the project entity's corresponding target-model entity, it returns all direct target-model FKs supported by direct-ID mode, including optional relationships and targets already present in the project. Include the target entity name, `public_id`, and `target_table`. Do not filter targets based on whether the source currently produces the ID column. Do not change the existing missing-entity picker.

The result distinguishes an unconfigured target model, a model that failed to resolve, and a resolved model. With no model, show a disabled selector and prompt the user to select one. On resolution failure, show an error instead of an empty list. With a resolved model, show a multi-select labeled **Direct target IDs** near the entity's produced columns in the Basic section.

### Selectable targets, validation, and map updates

- Offer direct relationships without `via` whose target defines both `public_id` and `target_table`, even when the ID column is not currently produced by the source entity.
- Display each choice by target entity and ID column, such as `location_type (location_type_id)`.
- If a project `foreign_keys` link to the same target exists, disable that choice and explain that the conflicting link must be removed first.
- Selecting a target sets `foreign_key_value_sources.<target>` to `public_id`. Clearing a selected public-ID target removes only that entry. Do not create a project `foreign_keys` link or dependency.
- If the target ID column is not produced, rely on normal structural validation to report the existing missing-column issue. Show the project entity and exact column, and provide a direct way to open that entity's column settings with guidance to add the column or remove the direct-ID selection.

### Preserve the complete map

Carry the full `foreign_key_value_sources` map through YAML parsing, form state, YAML/form switching, saved-entity loading, and saving. Show an eligible existing `public_id` entry as selected. Do not show an explicit `system_id` entry as selected, but preserve it unchanged. Keep stale or otherwise ineligible entries visible with an explanation and preserve them unless the user explicitly changes or removes them. Editing one target must not alter other map entries.

## Alternatives Considered

- **Add a “Direct model ID” checkbox to each project FK editor.** This is more contextual, but it couples a target-model value-source setting to a project FK editor and requires special behavior for key selection. The multi-select uses target-model relationships without changing the meaning of project FK links.
- **Reuse the existing missing-entity picker.** Its options omit entities already in the project and do not provide the current entity's complete relationship list. Changing it would risk altering a separate workflow.
- **Keep YAML-only configuration.** This requires the least work, but leaves the requested visual workflow unavailable.

## Risks And Tradeoffs

- The selector needs a small read-only backend contract for resolved target-model relationships. Output-column validity remains the responsibility of structural validation.
- A model or entity change can make a stored selection invalid. The UI must report that state without silently dropping the declaration.
- The selector can confirm that a suitable ID column is configured, but it cannot confirm that source values refer to the intended rows. Existing change-request validation remains responsible for checking that IDs exist in the target database.

## Testing And Validation

- Verify that the metadata contract distinguishes no target model, resolution failure, and a resolved model. A resolved model returns optional and already-configured direct relationships; the existing missing-entity picker remains unchanged.
- Verify that the selector offers direct-ID-compatible relationships even if their target ID columns are not currently produced.
- Verify that structural validation reports a missing target ID column using Core's output-column rules, and that the issue identifies the entity and column and opens the relevant column settings.
- Round-trip a mixed map containing `public_id`, explicit `system_id`, and stale entries through YAML/form switching, save, and reload. Confirm only eligible `public_id` entries appear selected and untouched entries remain unchanged.
- Verify that selecting or clearing one target updates only its map entry and that conflicts with project `foreign_keys` links are explained.
- Confirm that existing local `system_id` links and change-request validation retain their current behavior.

## Acceptance Criteria

- `P-AC-1` The selector cannot add a direct-ID setting unless a target model is selected and resolved.
- `P-AC-2` The metadata contract returns all direct target-model FKs for the current entity, including optional targets and targets already present in the project, without changing the existing missing-entity picker.
- `P-AC-3` The selector offers every direct-ID-compatible target-model FK regardless of whether its target ID column is currently produced.
- `P-AC-4` Structural validation reports a missing target ID column using Core's target-facing column rules. The result identifies the project entity and missing column and provides a direct path to fix the output or remove the selection.
- `P-AC-5` Selecting a target sets its `public_id` value-source entry; clearing it changes only that entry and creates no project FK link or dependency.
- `P-AC-6` The complete value-source map survives YAML/form switching, saved-entity loading, saving, and reload. Only eligible `public_id` entries appear selected; untouched explicit `system_id` and stale entries remain unchanged.
- `P-AC-7` Missing, unresolved, and resolved target-model states have distinct UI behavior, and conflicts with project FK links are actionable.
- `P-AC-8` Existing YAML editing, default `system_id` behavior, Core links, and change-request validation remain unchanged.

## Final Recommendation

Use the entity-level multi-select. It is the smallest visual addition that configures the existing setting while keeping direct target IDs separate from project FK links.
