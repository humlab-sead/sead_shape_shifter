---
name: shapeshifter-configuration
description: 'Validate, review, repair, or author Shape Shifter project YAML such as shapeshifter.yml and data/projects/*.yml. Use for entity configuration, fixed/sql/csv/xlsx/entity/merged entities, identity rules, foreign keys, extra_columns, dependency cycles, directives, materialized entities, and project validation errors.'
argument-hint: 'Path to shapeshifter.yml or describe the configuration problem'
---

# Shape Shifter Configuration

Use this skill for deep analysis, repair, and authoring of Shape Shifter project YAML files.

Before making validation decisions, load [`references/shapeshifter-configuration.instructions.md`](references/shapeshifter-configuration.instructions.md). Treat that file as authoritative. Use project docs only to clarify local intent, naming patterns, and workflow-specific conventions.

Expected input: a path to `shapeshifter.yml`, a `data/projects/*.yml` or `data/projects/*.yaml` file, or a description of a configuration problem.

## Scope

Use this skill after it has been selected to:

* validate, review, create, or repair Shape Shifter project YAML
* troubleshoot entity dependencies, foreign keys, identity fields, loaders, data sources, directives, or materialized entities
* explain project validation errors
* turn a rough entity description into valid configuration
* review an existing project for correctness, maintainability, and migration risk before running imports
* diagnose pipeline failures caused by config shape, linkage, dependency, or identity assumptions

Do not use it for Python validator implementation, backend API changes, frontend YAML editor work, or BugsCEP reconciliation-policy YAML unless the task also edits a Shape Shifter project config.

## Expert Mindset

Analyze configuration in this order:

1. Structural validity: top-level shape, required fields, and YAML parseability.
2. Entity semantics: each entity type satisfies its required contract.
3. Identity integrity: `system_id`, `keys`, and `public_id` follow the three-tier identity model.
4. Relationship correctness: FK joins, key columns, and dependency order align.
5. Runtime behavior risk: transforms, duplicate handling, directives, and materialized state behave as intended.

Prefer deterministic, minimal fixes. Avoid broad rewrites when a local change solves the issue.

## Workflow

1. Identify the config file and intended workflow.
2. Load `references/shapeshifter-configuration.instructions.md`.
3. Load nearby project docs only when they clarify local intent or patterns.
4. Parse YAML structurally before reasoning about business intent.
5. Validate top-level requirements: `metadata.name`, `metadata.type: shapeshifter-project`, and `entities`.
6. Validate each entity against type-specific rules from the reference file.
7. Validate the identity model:

   * `system_id` is internal and auto-managed except explicit fixed-entity cases
   * `keys` are business keys for matching and deduplication
   * `public_id` names exported identity and FK target columns and must end with `_id`
8. Validate foreign keys and dependencies:

   * referenced entity exists
   * `local_keys` and `remote_keys` exist at the correct stage
   * no self-reference
   * dependency graph is acyclic unless the specific cycle edge uses `defer_dependency: true`
9. Validate transforms and shaping behavior:

   * `extra_columns` constants, copies, interpolation, and formulas are coherent
   * columns used by FKs may be produced by `extra_columns`
   * `unnest`, `append`, and duplicate/drop rules are intentional and key-safe
10. Preserve directives such as `@include:`, `@load:`, `@value:`, and `${ENV_VAR}`. Do not inline or pre-resolve them during config review or editing.
11. Treat materialized entities as frozen snapshots. Do not re-validate snapshot data as if it were raw source extraction.
12. Edit only when asked. Preserve ordering, comments, and local style where practical.
13. Never invent unknown data-source names, table names, sheet names, source columns, or target columns.
14. Run project validation after changes when the repository and validation command are available.

## High-Value Checks

Prioritize checks that catch common project failures:

* Fixed entity `columns` width must match every row in `values`.
* Explicit-identity fixed entities include both `system_id` and `public_id` in `columns`.
* Fixed entities without `system_id` in `columns` are valid; it will be auto-generated.
* Non-fixed entities must not manually declare `system_id` in `columns`.
* SQL entities must have `data_source` and `query`.
* SQL `data_source` must exist in `options.data_sources`.
* `xlsx` and `openpyxl` entities must define `filename` and `sheet_name`, directly or through `options`.
* `entity` entities must reference an existing `source`.
* FK target entities must exist.
* FK `local_keys` must exist in the child entity at the correct stage.
* FK `remote_keys` must exist in the target entity.
* Child FK values are local parent `system_id` values, not external business IDs.
* `surrogate_id` is legacy — prefer `public_id` in new edits, but do not reject legacy configs solely for using `surrogate_id`.
* When a child already has external parent IDs, keep those as business-key columns and let FK linking add the local-ID FK column separately.
* If an FK depends on an `extra_columns` value, keep the produced column and FK config consistent in the same entity.
* For dependency cycles, prefer `defer_dependency: true` on the specific FK edge that creates the cycle.

## Valid Advanced Patterns

Do not auto-flag these as errors:

* `extra_columns` values used in FK joins.
* Empty `keys: []` when intentional for lookup, bridge, or workflow-specific entities.
* `source:` set to null or empty when valid for the entity type and workflow.
* Materialized fixed entities with historical shape that differs from non-materialized authoring style.
* Left joins or permissive constraints used for sparse or optional relationships.
* Deferred `extra_columns` when referenced columns are not available until a later stage.

If uncertain, state the assumption and ask one focused question instead of proposing speculative edits.

## Review Output Contract

For reviews, always return:

1. Findings ordered by severity: `Critical`, `High`, `Medium`, `Low`.
2. For each finding:

   * entity path
   * exact rule violated
   * impact
   * smallest safe fix
3. Validation status and command evidence.
4. Remaining risks, assumptions, or open questions.

When no issues are found, explicitly say so and still call out residual risk areas such as runtime SQL shape drift, unresolved environment variables, source-file drift, or project-specific assumptions not visible in YAML.

## Edit Output Contract

For edits, return:

1. Edited path.
2. Short change summary.
3. Validation performed.
4. Remaining risks or decisions.

Keep fixes minimal. Preserve comments, ordering, and local formatting where practical.

## Validation Commands

Use repository commands only when validation is requested or after making config changes.

Prefer `rtk` when available:

```bash
rtk uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow all --log-level ERROR
```

If `rtk` is unavailable or fails for wrapper-related reasons, retry without it:

```bash
uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow all --log-level ERROR
```

Do not claim validation passed unless the command completed successfully or VS Code diagnostics report no errors for the edited file.

Optionally run targeted workflow slices if available in the repository, but report exactly what was and was not run.
