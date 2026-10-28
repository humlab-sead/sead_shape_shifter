# Scaffold Project Entities From an Associated Target Model

## Status

- Proposed feature
- Scope: Entity creation in the project editor
- Goal: Start a project entity with its target name and public ID while showing the target requirements.

## Summary

Add an optional target-model entity picker to the existing Add Entity form. It lists target-model entities absent from the project. Selecting one fills its exact name and declared `public_id`. The form shows required target columns and links as reference information. The user configures source columns and joins through the existing editors and saves through the normal action.

Target requirements describe output, not source configuration. Selecting an entity must not put target columns or links into project `columns` or `foreign_keys` automatically.

## Problem

The Add Entity form starts blank even when a project has an associated target model. Users must look up the target name, public ID, required columns, and links elsewhere. This makes omissions and wrong ID names easy. The target model cannot tell whether a required output column comes from the source, a transformation, or a foreign key.

## Scope

- Offer missing target-model entities in the existing create form while preserving manual creation.
- Fill the selected target name and declared `public_id`, and show target requirements beside the form.
- Keep source mapping and project changes under the user's control.

## Non-Goals

- Infer a source type, query, file, source column, business key, FK join, fixed value, or data-source setting.
- Copy target `unique_sets` into project `keys`, or create dependencies automatically.
- Change the command-line helper or full project-template generator.
- Edit the associated target model.

## Current Behavior

- **Add Entity** opens `EntityFormDialog` with a blank name and `type: entity`. Its Foreign Keys tab is unavailable until the entity has been created.
- Project metadata may contain an inline target model or a reference. `ProjectMapper.to_core()` resolves references for target-model conformance.
- The existing raw target-model YAML endpoint handles project-local files, but does not serve inline or shared models.
- The full project-template generator emits required target column names into project `columns` and required FK targets as direct `foreign_keys`. Those fields are not always valid source mappings: target columns can be generated or produced by joins, and a target link can use a `via` bridge.

## Proposed Design

### Choose an entity

In create mode, show a clearable **Start from target model** picker when the project's associated model resolves. Offer every target-model entity whose name is absent from the project. Sort required entities first and label each option with its role and required or optional status.

Selecting an option fills the exact entity name and its `public_id`, if declared. While selected, keep the name fixed so the saved entity still matches the target model. If no `public_id` is declared, the user supplies one using the existing form. Clearing the picker removes the target context and makes the name editable; entered form values remain for manual editing. Confirm before selecting an option if that would replace an edited name or `public_id`. Refresh the options after save.

If no model is configured, keep the manual form. If a configured model cannot be loaded or parsed, show a picker error and keep manual creation usable.

### Show requirements without inventing mappings

Show the selected entity's role, description, target table, required non-generated target columns, and required links near the form. Keep this information separate from saved entity data. A column marked `generated` is not a source-column requirement. Do not add any target column to project `columns`: the user chooses source columns or configures the transformation that produces each output.

For a direct required link, show its target entity. For a required link with `via`, show the bridge and final target as a path; do not suggest a direct FK from the selected entity to the final target. Mark any target or bridge in these paths that is absent from the project. The user adds those entities separately from the picker and configures joins in the existing Foreign Keys editor after creating the entity. The create form does not need a new FK editor.

The target model does not specify a Shape Shifter source type. For a selected entity, require an explicit source-type choice; the form's default `entity` value does not count as that choice. For a classifier, allow `fixed` or `sql` and explain the choice. The normal save may leave target requirements unmet; existing structural and conformance validation reports those gaps as the user completes the project.

### Read the associated model on the server

Add a project-scoped, read-authorized API operation that returns the missing options and their target facts. Resolve the model from project metadata through `ProjectMapper.to_core()`; do not accept a model path from the browser. Return target information separately from project entity fields so it cannot be saved by accident.

The dialog submits only the completed entity form through the existing entity-create API. Selecting an option does not write to the project. This feature does not reuse or change the full project-template generator, whose broader scaffolds serve a different workflow.

## Alternatives Considered

- **Copy the full project-template scaffold into the form.** This can mistake target output columns for source columns and turn a bridged link into a direct FK.
- **Enable FK editing during creation.** The existing editor works after save. Showing requirements before save and configuring joins afterward keeps this change smaller.
- **Parse target-model YAML in the browser.** This duplicates resolution and cannot use the current raw-YAML endpoint for inline or shared models.
- **Create required dependencies automatically.** Those entities need their own source settings and an explicit save.

## Risks And Tradeoffs

- Users still choose how to produce each required output column and link. The form makes requirements visible but does not claim that the source contains them.
- The project may fail validation between saving an entity and completing its source and FK configuration. Existing validation reports those gaps.
- Replacing a selected target can discard edits to its name or `public_id`; confirm before doing so.

## Testing And Validation

- Verify missing-entity filtering, required and role labels, name locking, clearing the picker, replacement confirmation, and unchanged manual creation.
- Verify that a selected target entity cannot be saved with only the default `entity` type, and that saving requires an explicit source-type choice.
- Check project authorization and local, shared, inline, absent, missing, and invalid model handling.
- Use target models with a generated required column and a required `via` link. Confirm neither becomes a project source column or direct FK, while the required bridge path remains visible.
- Confirm that only the normal save writes the entity, and that structural and conformance validation reports source or link gaps after an incomplete save.

## Acceptance Criteria

- `P-AC-1`: With a resolvable associated target model, create mode lists every target-model entity absent from the project and labels its role and required status.
- `P-AC-2`: Without a resolvable associated target model, manual entity creation remains usable; a configured model that fails to load produces a clear picker error.
- `P-AC-3`: Selecting a target entity fills its exact name and declared `public_id`. The name stays fixed until the picker is cleared, and changing the selection does not silently replace edited values.
- `P-AC-4`: Selecting an option alone does not populate `columns`, `foreign_keys`, or `keys`. Saving preserves the fields the user configured explicitly.
- `P-AC-5`: Saving a selected classifier requires `type: fixed` or `type: sql`; the form explains that choice.
- `P-AC-6`: Selecting a target entity does not write to the project. Only the normal create save persists form data.
- `P-AC-7`: Existing project entities are not offered, and a newly saved entity is removed from the candidate list.
- `P-AC-8`: The form shows required non-generated target columns and required link paths, including `via` bridges, without turning generated columns or bridged links into direct project mappings.
- `P-AC-9`: For every selected target entity, saving requires an explicitly selected Shape Shifter source type; the default `entity` value alone does not satisfy this requirement.

## Planning Handoff

- Preserve manual Add Entity and the existing save and validation flows.
- Resolve only the project's associated target model on the server with project read authorization. Return target requirements separately from fields submitted on save.
- Fill only the exact name and declared `public_id`. Keep the name fixed while selected; clearing selection restores manual name editing.
- Require an explicit Shape Shifter source-type choice for every selected target entity; the default `entity` value alone is not a choice. For selected classifiers, allow only `fixed` or `sql`.
- Treat required target columns and FK paths as reference information. Do not modify the full template generator, command-line helper, or create-mode FK editor.
- Validate direct and bridged links, generated columns, incomplete saves, and all supported model reference forms. No product decision remains open for planning.

## Final Recommendation

Add the target-model picker and show its requirements in the existing create form. Prefill only the identity fields the target model can state without guessing how project data will produce them.
