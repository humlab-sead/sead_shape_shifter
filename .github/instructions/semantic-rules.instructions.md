---
description: "Create and maintain semantic validation rules for Shape Shifter project YAML files."
applyTo: "docs/rules/**/*.yml, docs/rules/**/*.md, backend/app/**/rules/**/*.yml, backend/app/**/validation/**/*.py"
---

# Shape Shifter semantic rules

When asked to create, initialize, review, or maintain Shape Shifter semantic validation rules, follow the task-specific instruction file:

```text
docs/ai/semantic-rules-agent.md
```

Use generated JSON Schema for editor autocomplete and basic structural validation only. Do not duplicate the full schema as semantic rules.

Semantic rules should capture contextual and cross-model constraints that JSON Schema cannot express well, such as:

- source files that must exist
- Excel sheets that must exist in a workbook
- source tables or columns that must exist
- target tables or columns that must exist
- references between entities, mappings, lookups, and expressions
- business rules implemented in the core layer
- assumptions made by API-to-core mapping code

Prefer implemented behavior over documentation. Use real project YAML examples, JSON Schema, Pydantic API models, API-to-core mapping, core business logic, and graphify when available.

When creating initial conditional rules for entity types, the entity type contract table in `shapeshifter-configuration.instructions.md` provides a verified, high-confidence starting point. It lists required and optional fields per entity type and loader.

Use stable rule IDs such as:

```text
entity.excel.sheetname_must_exist
mapping.target_column_must_exist
reference.entity_must_exist
expression.references_must_resolve
```

Each rule should be actionable, include a severity, point to the relevant YAML path, explain the problem, and suggest a safe repair.
