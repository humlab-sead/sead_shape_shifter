# Scaffold Project Entities From an Associated Target Model

## Status

- Proposed feature
- Scope: Entity creation in the project editor
- Goal: Prefill a new project entity from an entity in the project's associated target model.

## Summary

Add an optional target-model entity picker to the existing Add Entity flow. The picker lists target-model entities that are not yet in the project. Selecting one preloads a Shape Shifter entity draft with the target name, `public_id`, required columns, and required foreign-key targets. The user still chooses how to load and join the source data, reviews the draft, and saves it through the normal entity form.

Use the same project-scaffold generator for the editor and command-line output. The target model describes the destination schema; it does not provide source queries, files, business keys, or data values.

## Problem

When a project has an associated target model, users can validate project entities against it, but the Add Entity dialog starts blank. Users must copy target names, IDs, required columns, and links by hand. This makes it easy to omit a required field or use the wrong target ID name.

## Scope

- Offer missing target-model entities in the existing create form while keeping manual entity naming available.
- Generate a project entity draft from the selected target-model specification.
- Show target role and missing required target entities as context.
- Keep the draft unsaved until the user uses the existing save action.
- Share the scaffold-generation behavior between the UI and command-line tooling.

## Non-Goals

- Guess the source loader, SQL, filename, source columns, project `keys`, FK join columns, fixed values, or data-source settings.
- Turn target `unique_sets` into project `keys`; they describe different rules.
- Add the selected entity or its dependencies to the project without an explicit user save.
- Edit the associated target model or create a new target-model entity.

## Current Behavior

- The Entities page opens `EntityFormDialog` in create mode from **Add Entity**. The form starts with a blank name and defaults to `type: entity`.
- Project metadata can associate a target model by reference or inline configuration. `ProjectMapper.to_core()` resolves configured directives, and target-model conformance uses the resolved model.
- The existing target-model YAML endpoint serves project-local files only. It rejects inline models and shared model files, so the browser cannot use that endpoint to support every configured model.
- `src/target_model/template_generator.py` already creates project scaffolds. For an entity, it emits `type: TODO`, `public_id`, required target columns, and required FK entity names. The current command-line script `scripts/print_target_model_entity.py` prints the target-model specification stanza, not this project entity scaffold.

## Proposed Design

### Select a target-model entity

When a project has a target model that resolves successfully, show a clearable **Start from target model** picker beside the editable entity name in create mode. Include every target-model entity whose name is not already present in the project. Sort required entities first and label each option with its role and required or optional status. Keep ordinary manual entry available.

Selecting an option fills the entity name and applies its generated project scaffold to the create form. The name remains editable. If the user has already changed the form, ask before replacing those changes. After the entity is saved, refresh the candidate list so the new entity is no longer offered.

If the project has no target model, or the associated model cannot be resolved, keep the existing manual create flow available. Show a clear picker error when a configured model cannot be loaded; do not block manual entry.

### Prefill only target-model facts

Use the existing project-template rules to prefill:

- `public_id`, when declared by the target model
- Required target column names
- Required FK target entity names

Show the target role, description, and table as reference information; they are not project entity fields. Leave optional target columns out of the initial `columns` list because the target model cannot establish that the source contains them. Do not copy target `unique_sets` into `keys`.

The target model does not declare a Shape Shifter loader type. Do not save or display `type: TODO`, and do not silently keep the create form's `entity` default when it conflicts with the selected role. Require a valid source type choice for a target-model scaffold. For a classifier, guide the user to choose `fixed` or `sql`. Keep source settings, business keys, FK join columns, and data values for the user to supply.

Required FK targets can be shown in the form before their project entities exist. List any required target entities that are still missing so the user can add them from the same picker. Do not create a dependency closure in the background.

### Resolve the model on the server

Add a project-scoped, read-authorized API operation that returns the missing entity options and their project scaffolds. Resolve the model from the project's own metadata using the same resolver used by conformance validation; do not accept an arbitrary path from the browser. Return the target labels separately from the project entity YAML so the form can show context without persisting target-model-only fields.

Move or expose the per-entity scaffold generation as a shared function used by this API, the full project-template generator, and the command-line helper. Make the command-line helper print the same Shape Shifter entity snippet used by the form. Keep target-model parsing and source-specific decisions out of the frontend.

The create dialog submits the completed form through the existing entity-create API. The project remains unchanged until the user saves.

## Alternatives Considered

- **Keep template generation separate from the editor.** This avoids changing the entity form but leaves users to copy generated YAML into the project themselves.
- **Parse the target-model file in the browser.** This duplicates target-model resolution and cannot consistently handle inline and shared model references through the current raw-YAML endpoint.
- **Automatically add the selected entity and all required dependencies.** This hides multiple project changes behind one selection and may create incomplete entities with no source configuration.

## Risks And Tradeoffs

- A target model cannot provide project-specific source settings or FK join columns, so the scaffold is intentionally incomplete. The form must make those remaining choices clear.
- Replacing the form draft after the user has started editing can lose work. Protect dirty drafts with a confirmation.
- Shared and inline model references need the same project-scoped authorization and resolution rules as other project operations.
- Required FK entity names do not identify source-side join columns. The UI must not imply that a target link is fully configured just because its target name is prefilled.

## Testing And Validation

- Frontend tests should cover absent and configured target models, candidate filtering, required/optional labels, prefill behavior, dirty-form replacement, and unchanged manual creation.
- Backend tests should cover project authorization, missing and invalid models, project-local, shared, and inline model resolution, and candidate exclusion for existing entities.
- Verify that a selected scaffold is submitted only after the normal save action and contains the generated `public_id`, required columns, and required FK targets.
- Run the existing structural and target-model conformance workflows on a saved example. Confirm that source-specific gaps remain visible until the user supplies those settings.

## Acceptance Criteria

- `P-AC-1`: With a resolvable associated target model, create mode lists all target-model entities absent from the project and labels required entities and roles.
- `P-AC-2`: The picker is absent or unavailable without a resolvable associated target model, while manual entity creation remains usable.
- `P-AC-3`: Selecting an entity fills its name, declared `public_id`, required target columns, and required FK target names from the shared project-scaffold generator.
- `P-AC-4`: The form does not infer source queries, files, data-source settings, business keys, FK join columns, fixed values, or project `keys` from target-model metadata.
- `P-AC-5`: A selected classifier cannot be saved with an incompatible `type: entity`; the form guides the user to choose `fixed` or `sql`.
- `P-AC-6`: Selecting a target-model entity does not write to the project. Only the normal create save persists the draft.
- `P-AC-7`: Existing project entities are not offered, and a newly saved entity is removed from the candidate list.
- `P-AC-8`: The UI and command-line helper use the same project-scaffold generator and print or submit the same entity fields.

## Planning Handoff

- Preserve the manual Add Entity path and normal save behavior.
- Resolve the target model from project metadata on the server; do not accept a client-supplied model path.
- Reuse the scaffold rules already used by project-template generation. Leave source-specific mapping to the user.
- Validate local, shared, and inline target models; confirm that missing target entities are filtered by project entity names and that saved drafts pass through existing structural and conformance validation.
- No product decision remains open for planning: include all missing target-model entities, mark required ones, and add dependencies only through explicit user actions.

## Final Recommendation

Add the target-model picker to the existing Add Entity create form and back it with a project-scoped API that returns missing entities and their shared-generator scaffolds. This removes repetitive target-schema entry while keeping source configuration and project changes under the user's control.
