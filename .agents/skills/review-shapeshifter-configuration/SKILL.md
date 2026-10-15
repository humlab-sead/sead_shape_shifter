---
name: review-shapeshifter-configuration
description: Review, validate, repair, or author Shape Shifter project YAML. Use for entity configuration, identity and foreign keys, directives, dependencies, materialized entities, and project validation errors.
---

# Shape Shifter project configuration

Use this skill for Shape Shifter project YAML, including `shapeshifter.yml` and files under `data/projects/`. The requested work may be a review, a repair, a new entity, or an explanation of a validation failure. A target-model specification is a separate format; inspect it only when the project configuration references it or the user asks about it.

Read [the configuration instructions](../../../.github/instructions/shapeshifter-configuration.instructions.md) before judging or editing a project. They give detailed review rules and examples for common configuration forms. Check the current models, specifications, loaders, and mapper when a rule matters to the task or conflicts with an existing project; those implementations determine current behavior. Use `docs/CONFIGURATION_GUIDE.md` for examples and background, and report any discrepancy with the implementation.

## Review or edit

1. Identify the project file, the user's intended workflow, and whether they want findings, an edit, or both. Inspect the raw YAML and relevant nearby files. Preserve directives as written in the project file.
2. Check project shape and each entity's actual loader contract. Then trace identity fields, the columns produced at each pipeline stage, foreign keys, and processing dependencies.
3. Check the behavior of filters, `extra_columns`, append, unnest, and materialized state only where the entity uses them. Treat source names, columns, and business keys as project data; do not invent replacements for unknown values.
4. Apply a focused change when the user asks for a repair or new configuration. Preserve comments, ordering, and local style where practical. For a review request, give findings without rewriting the file.
5. Validate at the level the task needs and inspect the reported issue severities, even if the command exits with status 0. Report the exact command and result. Separate confirmed errors from assumptions that depend on files, database schemas, or environment variables unavailable locally.

## Rules that change review decisions

- `system_id` holds local IDs used in foreign-key values. The parent `public_id` names the child FK column; it is not the value stored in that column. `keys` identify business rows and do not create output columns.
- Persisted fixed-entity `columns` contain produced data fields. Fixed `values` may contain data-only rows or full positional rows ordered as `system_id`, `public_id`, then data fields. Older configurations can include identity names in `columns`; persistence removes them from that list without dropping their row values.
- A dependency may come from `source`, a non-deferred FK, an append source, a merged branch, a filter, or explicit `depends_on`. Use `defer_dependency: true` only on an FK that genuinely needs a final linking pass.
- API and YAML editing preserve `@include:`, `@load:`, `@value:`, and `${ENV_VAR}` strings. The API's `ProjectMapper.to_core()` resolves them for processing. Do not inline or replace directives during a review unless the user requests that change.
- Materialization saves a fixed snapshot with `materialized.enabled` and `materialized.source_state`, which records the original configuration for restoration. Inspect the saved values or sidecar as snapshot data.

## Validation and reporting

For a changed project, or when validation is requested, start with the structural workflow if the project and its referenced files are available:

```bash
rtk uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow structural --log-level ERROR
```

Use `--workflow data`, `--workflow target-model-conformance`, or `--workflow all` when the request needs those checks and their data sources are available. These workflows can read external data and run normalization. If `rtk` fails because of its wrapper, retry the same command without `rtk`. The current CLI can print error rows while exiting with status 0; determine success from the reported severities. Never report a validation pass that did not complete.

For findings, give the entity or YAML path, the violated rule, the effect, and the smallest safe fix, ordered by impact. For edits, name the changed file and summarize the change and validation result. State remaining uncertainty only when it affects the user's decision.
