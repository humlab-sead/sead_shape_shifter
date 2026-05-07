---
description: "Use when validating or editing shapeshifter.yml, project YAML, entity configuration, mappings, or foreign-key configuration. Covers identity rules, directives, and common valid patterns."
applyTo: "**/shapeshifter.yml,data/projects/**/*.yml,data/projects/**/*.yaml"
---
# Project Config Validation

- Validate project YAML against `.github/instructions/shapeshifter-configuration.instructions.md` before declaring a configuration invalid.
- Not every unusual pattern is an error; examples that can be valid include `extra_columns` with FK references, business-key joins, and hierarchical fixed entities.
- Keep directives such as `@include:` and `@value:` in YAML and API-layer models; resolve them only when mapping into core models.
- All internal relationships use local `system_id` values.
- `keys` are business keys for reconciliation and deduplication.
- `public_id` names exported and FK target columns, should end with `_id`, and is required for fixed entities and entities with FK children.
- When transforming config data in code, avoid mutating the input; use deep copies where needed.
