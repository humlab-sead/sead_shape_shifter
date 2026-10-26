---
name: review-shapeshifter-configuration
description: Review, validate, repair, or author Shape Shifter project YAML, including entity data flow, identities, transformations, provider bindings, and target-model references.
---

# Shape Shifter project configuration

Use this skill for project configuration such as `shapeshifter.yml`. A target-model specification is a separate format; inspect it when the project references it or the user asks about it.

Read the [configuration instructions](../../../.github/instructions/shapeshifter-configuration.instructions.md) first. For an upgrade, also use the [project configuration upgrade guide](../../../docs/PROJECT_CONFIGURATION_UPGRADE_GUIDE.md). The [configuration guide](../../../docs/CONFIGURATION_GUIDE.md) has examples, but check current code when behavior or documentation disagrees.

## Review workflow

1. Identify the exact project file and whether the user wants findings, an edit, or both. If the user means a file open in the editor, use editor context when available. Do not guess from modification time; ask for the path if it is not available and the file is ambiguous.
2. Read the raw YAML and relevant local files. Preserve `@include:`, `@load:`, `@value:`, and `${ENV_VAR}` as written. Check the actual loader and current model or specification when a rule is unclear.
3. Trace each affected entity from extraction through filtering, linking, unnesting, translation, and storage. Check produced columns, identity fields, foreign keys, dependencies, and only the transforms the entity uses.
4. Check project metadata and runtime state where relevant:
   - Verify `data_provider_code` and `provider_schema` as a pair in the deployment's curated registry. Existing bound projects cannot change the pair or their established business keys through normal project saves.
   - Confirm a target-model reference resolves before reporting conformance as passed. Prefer a shared model when projects use the same target schema.
   - Inspect materialized snapshots and the mapping sidecar when the question concerns saved rows or assigned public IDs.
5. Validate only the workflows needed and available:
   - Start with `rtk uv run python scripts/validate_project.py <path> --workflow structural --log-level ERROR` for Core structural checks. This CLI does not check provider-registry bindings or the fixed `data_provider` row.
   - Backend YAML Validation also checks provider metadata and the fixed provider row.
   - Use `--workflow data` when source files and connections are available. It normalizes the project and may read external sources.
   - Use `--workflow conformance` when a target model is configured and resolved. `target-model-conformance` is an accepted alias. Confirm the model loaded; the editor can skip conformance when a referenced file is missing.
   - Read the reported issue severities and workflow statuses. The CLI can exit 0 while printing error-severity findings; exit status alone does not prove validation passed.
6. For a review, report findings without changing the project. For a requested repair, make the smallest safe edit and validate it. Report exact commands, issue severities, and limits caused by unavailable files or services.

## Identity and directives

- `system_id` values are local foreign-key values. The parent's `public_id` names the child FK column; it is not the FK value. `keys` identify business rows and do not create output columns.
- Preserve directives in saved YAML. The backend mapper resolves them for Core processing. In the editor, environment variables are limited by deployment settings and loaded paths are limited to approved project/shared roots.
- Materialized entities keep their original configuration in `materialized.source_state`. The mapping sidecar can supply public-ID links that are not visible in raw YAML; Core structural validation does not use them, while CLI data validation applies committed links during normalization.

## High-risk checks

- Trace each `keys`, FK `local_keys`, and unnest `id_vars` field to a real producer at the stage where it is used.
- Compare FK key values and types on both entities. An inner join can remove unmatched rows; the child FK stores the parent's local `system_id`.
- Check whether an `extra_columns` string is a literal or a copy. A plain string copies a column only when that column exists; do not redefine identity or unnest output columns.
- Check fixed row order and strict ID types. For a non-fixed `system_id` from a file, inspect the actual values and dependent joins before keeping or removing it.
- Resolve unnest directives before checking `id_vars` and `value_vars` for overlap. A FK key produced by unnest can link in the post-unnest pass without `defer_dependency: true`.
