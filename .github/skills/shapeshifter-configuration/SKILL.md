---
name: shapeshifter-configuration
description: 'Validate, review, repair, or author Shape Shifter project YAML such as shapeshifter.yml and data/projects/*.yml. Use for entity configuration, fixed/sql/csv/xlsx/entity/merged entities, identity rules, foreign keys, extra_columns, dependency cycles, directives, materialized entities, and project validation troubleshooting.'
argument-hint: 'Path to shapeshifter.yml or describe the configuration problem'
---

# Shape Shifter Configuration

Use this skill for focused work on Shape Shifter project YAML files. The rule source is [`shapeshifter-configuration.instructions.md`](../../instructions/shapeshifter-configuration.instructions.md); load it before validating, reviewing, or editing project YAML.

## When To Use

Use this skill when the user asks to:

- validate, review, create, or repair `shapeshifter.yml` or `data/projects/*.yml`
- troubleshoot entity dependencies, foreign keys, identity fields, loaders, data sources, directives, or materialized entities
- explain project validation errors or turn a rough entity description into valid config

Do not use it for Python validator implementation, backend API changes, frontend YAML editor work, or BugsCEP reconciliation-policy YAML unless the task also edits a Shape Shifter project config.

## Workflow

1. Identify the config file and intended workflow.
2. Load the rule source and any nearby project docs the user points to.
3. Parse YAML structurally before reasoning about business intent.
4. Check required top-level fields, entity type rules, identity fields, foreign keys, dependencies, loader options, `extra_columns`, directives, and materialization rules.
5. Edit only when the user asked for changes; keep the smallest fix that preserves ordering, comments, and style.
6. Do not invent unknown data-source names, table names, sheet names, or target columns.
7. For circular dependencies, prefer `defer_dependency: true` on the FK that breaks the cycle.
8. For FK columns produced by `extra_columns`, keep the produced value and the FK together.

Preserve directives such as `@include:`, `@value:`, and `${ENV_VAR}` in YAML. Resolution belongs at the API-to-core mapper boundary.

## Validation Commands

Use repository commands only when validation is requested or after making config changes:

```bash
rtk make test-validate
rtk uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow all --log-level ERROR
```

If `rtk` fails, retry without it. Do not claim validation passed unless the command completed successfully or VS Code diagnostics report no errors for the edited file.

## Output Format

For reviews, lead with findings ordered by severity, then concrete fixes, validation, and open questions. For edits, include the edited path, short change summary, validation performed, and remaining risks or decisions.