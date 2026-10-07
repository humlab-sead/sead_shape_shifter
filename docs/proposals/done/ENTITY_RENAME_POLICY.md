# Guarded Entity Rename

## Status

- Completed; tracked by [issue #524](https://github.com/humlab-sead/sead_shape_shifter/issues/524)

## Summary

Entity API renames are rejected when another entity refers to the entity being renamed. A rename with no dependents updates the entity key and `metadata.default_entity` when applicable. Project YAML is the required save; moving the entity note in `shapeshifter.tasks.yml` is best-effort.

## Completed Scope

- The reference inventory covers source and explicit dependencies, all foreign keys including deferred ones, append and branch sources, and both filter entity fields. Rename checks also scan configuration strings for `@value: entities.<name>` directives and extract table names from internal SQL queries.
- A rejected rename returns sorted dependent names and does not save the project or sidecar. The editor shows the conflict details and manual next steps.
- A successful rename updates the entity key and applicable default entity. It attempts to move the note without overwriting a note already stored under the new name. A note collision or sidecar error does not undo the project save; the API returns a warning and the note stays under its old key.
- Task statuses, flags, and graph layout positions are not re-keyed. Manual YAML renames require users to update project references and any sidecar keys they want to preserve.

## Validation Performed

- Backend tests cover reference rejection without writes, deferred foreign keys, SQL table extraction, note movement, note collisions, sidecar write failures, and warning responses.
- Frontend tests cover rename submission, conflict details, and successful editor state refresh.
- Focused model tests cover the `TableConfig` reference inventory, including deferred foreign keys and both filter reference fields.

## Remaining Follow-Up

The guard detects the supported configuration references, `@value: entities.<name>` directives, and table names extractable from internal SQL. It cannot guarantee discovery of references created dynamically or encoded in unsupported free-form text. Note migration is not transactional with the project YAML save; a warning identifies when manual note recovery is needed.