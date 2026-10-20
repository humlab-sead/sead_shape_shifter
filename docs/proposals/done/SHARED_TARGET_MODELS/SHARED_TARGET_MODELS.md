# Share Target Models Across Projects

## Status

- Proposed feature / change request
- Tracking issue: [#548: Share target models across projects](https://github.com/humlab-sead/sead_shape_shifter/issues/548)
- Scope: Shared storage and project metadata selection for target model YAML files
- Goal: Let projects use a managed target model without copying it into each project

## Summary

Add `shared/target-models` and include its YAML files in the project metadata target model picker. Configure this directory as an allowed `@load:` root so a selected shared model can be resolved when the project is loaded.

## Problem

The target model picker lists only YAML files in the current project. Copying one target model into several projects creates duplicate files that can drift. Adding a shared folder alone is insufficient: target model references are currently resolved from the project directory, `shared/shared-data`, and `shared/data-sources`.

## Scope

- Add a configured shared target model directory at `shared/target-models`.
- Let project metadata select either project-local or shared target model files.
- Resolve selected shared files through the existing `@load:` mechanism.
- Keep shared model files read-only in the project editor; project-local files remain editable.

## Non-Goals

- Adding upload, edit, or delete controls for shared target models.
- Defining a target model versioning or release process.

## Current Behavior

The metadata picker requests `.yml` and `.yaml` files from the project file list and turns each filename into an `@load:` value. `ProjectMapper` resolves target model directives only under the project directory and the two configured shared data directories. The project detail view does not show its target model editor for references containing a path.

## Proposed Design

Add a `GLOBAL_TARGET_MODEL_DIR` setting defaulting to `shared/target-models`. Add this directory to the allowed roots used to resolve project directives and to the resolver's permitted path variables. Shared choices should save a portable reference such as `@load: ${GLOBAL_TARGET_MODEL_DIR}/model.yml`; local choices should keep their current project-relative references.

Extend the metadata picker’s file options to include `.yml` and `.yaml` files from both locations. Label each choice as project-local or shared, and retain the full reference as its value so files with the same name remain distinguishable. Manage shared files through deployment or the server filesystem; the project editor should not write to the shared directory.

## Risks And Tradeoffs

Changes to a shared model affect every project that references it. Shared files therefore need stable paths, and maintainers should review changes with their consuming projects in mind. Keeping project-local models editable allows a project to use a customized copy.

## Testing And Validation

Verify that local and shared references resolve through normal project loading and target model validation, that the picker presents both sources with distinct values, and that paths outside configured roots remain rejected. Confirm that existing local references and their editing behavior still work.

## Acceptance Criteria

- `P-AC-1`: The configured `shared/target-models` directory is an allowed target model resolution root, and paths outside approved roots remain rejected.
- `P-AC-2`: The metadata picker lists project-local and shared target model YAML files and saves a valid location-specific `@load:` reference for either choice.
- `P-AC-3`: Shared target models can be used for validation without copying them into a project, while existing project-local models remain editable and usable.

## Final Recommendation

Implement this as one tracking issue using the acceptance criteria above. The change spans file discovery, reference resolution, and the metadata picker, but it is a bounded additive feature and does not need a phase plan. This is sufficient while shared files remain deployment-managed and read-only in the editor; adding a shared model management interface or versioning policy would require a separate scope decision.
