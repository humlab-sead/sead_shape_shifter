---
description: "Create and maintain semantic validation rules for Shape Shifter project YAML files."
applyTo: "docs/rules/**/*.yml, docs/rules/**/*.md, backend/app/**/rules/**/*.yml, backend/app/**/validation/**/*.py"
---

# Semantic Rules Agent Instructions

Shape Shifter uses YAML project files to describe transformations between source relational models and target relational models. The generated JSON Schema supports editor autocomplete and basic structural validation, but many important rules are semantic, contextual, or cross-model and cannot be fully expressed in JSON Schema.

Create and maintain semantic rule files that describe those rules in a stable, AI-readable format.

## Source priority

Inspect any available sources in this priority order:

1. Existing Shape Shifter project YAML files, especially large real examples with many entities.
2. The entity type contract table in `shapeshifter-configuration.instructions.md` — a verified, high-confidence summary of required and optional fields per entity type.
3. Generated JSON Schema.
4. Pydantic API models.
5. API-to-core mapping layer.
6. Core/domain layer with business rules.
7. Graphify knowledge graph, if available.

Prefer implemented behavior over documentation when they disagree.

## Goal

Extract rules that help validate, explain, debug, and improve Shape Shifter project YAML files.

Focus on rules that:

- depend on discriminator fields such as `type`, `kind`, `source`, or `target`
- require fields only in specific contexts
- refer to existing files, sheets, tables, columns, entities, mappings, joins, lookups, or expressions
- express business rules not captured by JSON Schema
- prevent common user mistakes
- can produce actionable diagnostics and repair suggestions

Do not duplicate trivial JSON Schema rules unless they are useful for explanation or repair.

## Recommended files

For the first version, prefer:

```text
docs/rules/semantic_rules.yml
docs/rules/README.md
```

If the catalog grows, split by area:

```text
docs/rules/entities.yml
docs/rules/sources.yml
docs/rules/mappings.yml
docs/rules/targets.yml
docs/rules/expressions.yml
```

## Rule format

Use this YAML structure:

```yaml
version: 1

rules:
  - id: entity.xlsx.requires_filename
    title: xlsx entities require options.filename
    severity: error
    category: conditional
    applies_to: entities.*
    when:
      type: xlsx
    require:
      - options.filename
    message: xlsx entities must define options.filename.
    fix: Add options.filename pointing to the .xlsx or .xls file.
```

Use stable rule IDs:

```text
<area>.<context>.<rule_name>
```

Examples:

```text
entity.xlsx.requires_filename
entity.xlsx.sheet_name_must_exist
entity.openpyxl.requires_filename
entity.openpyxl.sheet_name_must_exist
mapping.target_column_must_exist
reference.entity_must_exist
expression.value_reference_must_resolve
```

## Rule fields

Use these fields where applicable:

```yaml
id: stable.machine_readable.id
title: Short human-readable title
severity: error | warning | info
category: structural | conditional | project_resource | source_model | target_model | transformation | consistency
applies_to: YAML path pattern
when: condition for the rule
require: list of required fields
check: semantic check descriptor
message: diagnostic message
fix: suggested repair
confidence: high | medium | low
agent_guidance: optional deeper guidance for AI repair
examples: optional valid/invalid examples
source: optional code/model/schema references used to infer the rule
```

## Categories

Use one or more of these categories:

```yaml
structural: Basic shape rules that are important for explanation.
conditional: Rules depending on discriminator values such as type: excel.
project_resource: Files, paths, Excel sheets, CSV headers, encodings, delimiters, or external resources.
source_model: Source tables, source columns, source datatypes, joins, and lookup sources.
target_model: Target tables, target columns, constraints, keys, and relationships.
transformation: Expressions, mappings, constants, references, lookups, casts, and value transformations.
consistency: Rules involving several parts of the same project file.
```

## Check kinds

Reuse these check kinds before inventing new ones:

```yaml
exists
not_empty
one_of
matches_regex
unique_within_scope
reference_resolves
project_file_exists
project_file_has_extension
excel_sheet_exists
csv_column_exists
source_table_exists
source_column_exists
target_table_exists
target_column_exists
expression_parses
expression_reference_resolves
type_compatible
join_key_exists
lookup_key_exists
```

Example:

```yaml
- id: entity.xlsx.sheet_name_must_exist
  title: Sheet must exist in workbook
  severity: error
  category: project_resource
  applies_to: entities.*
  when:
    type: xlsx
  check:
    kind: excel_sheet_exists
    file: options.filename
    sheet: options.sheet_name
  message: Sheet '{{ options.sheet_name }}' does not exist in '{{ options.filename }}'.
  fix: Choose one of the sheets available in the referenced workbook.
```

## Deriving rules

### From project YAML files

Look for repeated patterns across real entities. Compare entities with the same `type` and identify required options, optional options, naming conventions, references, source fields, target fields, and common transformation structures.

If a rule is inferred only from repeated examples, add `confidence: medium`. Do not create hard `error` rules from weak conventions.

### From JSON Schema

Use the schema to identify allowed values, object structure, required fields, discriminated unions, descriptions, aliases, defaults, and examples.

Do not copy the whole schema into semantic rules. Extract only rules that help diagnostics, explanation, repair, or contextual validation.

### From Pydantic API models

Inspect model fields, validators, discriminators, default values, descriptions, aliases, and enums.

Rules inferred from validators are usually high confidence. When a field is optional in the API model but required later by core logic in a specific context, create a semantic rule.

### From API-to-core mapping

Look for fields that are transformed, renamed, normalized, defaulted, expanded, or dropped.

Create rules when the mapping layer assumes that a field exists, a string matches a known name, a reference resolves, or a source field maps to a target field.

### From core/business logic

Prioritize core-layer checks, exceptions, guard clauses, validation functions, and runtime assumptions.

Good signals include:

```text
raise ValueError(...)
raise ValidationError(...)
assert ...
if missing:
if not found:
if type == ...
if source.kind == ...
```

Create rules for conditions that would otherwise fail at runtime.

### From graphify

Use graphify to find related symbols and code paths. Useful searches include:

```text
entity model
excel source
sheetname
filename
validator
mapping
target column
source column
reference
transformation expression
```

Follow edges from API models to mappers, validators, services, and core transformation logic. Prefer rules confirmed by multiple connected sources.

## Confidence

Add `confidence` when a rule is inferred rather than explicit.

Use:

```yaml
confidence: high
```

when confirmed by code, schema, or explicit validation.

Use:

```yaml
confidence: medium
```

when inferred from repeated project examples and consistent naming.

Use:

```yaml
confidence: low
```

only for candidate rules that need human review.

Do not create hard `error` rules from low-confidence inference.

## Source references

Include source references where useful:

```yaml
source:
  - kind: pydantic_model
    path: backend/app/api/models/project.py
    symbol: ExcelEntityOptions
  - kind: core_validator
    path: backend/app/core/project/validation.py
    symbol: validate_excel_entity
  - kind: example_project
    path: examples/large_project.yml
    note: All Excel entities define options.filename and options.sheetname.
```

Source references help maintainers and AI agents. They do not need to be perfect, but they should be useful.

## Agent guidance

Add `agent_guidance` when repair requires reasoning:

```yaml
agent_guidance:
  explanation: >
    Excel-backed entities must refer to an existing workbook and sheet. JSON Schema
    can require the fields, but it cannot know which files or sheets exist in the
    project workspace.
  repair_strategy:
    - Inspect options.filename.
    - Check whether the file exists relative to the project file.
    - If the workbook exists, list available sheet names.
    - Suggest the closest matching sheet name when there is an obvious typo.
    - Do not change the sheet name automatically unless the match is unambiguous.
  safe_autofix: false
```

## Good first rule families

Start with a small high-confidence catalog. Prefer 10-30 useful rules over a large noisy file.

Good first families:

```text
entity.<type>.requires_options
entity.<type>.required_option_fields
entity.<type>.resource_must_exist
entity.<type>.source_columns_must_exist
mapping.target_table_must_exist
mapping.target_column_must_exist
mapping.source_column_must_exist
reference.entity_must_exist
expression.references_must_resolve
lookup.keys_must_exist
target.required_fields_must_be_mapped
```

## Diagnostic quality

Every rule should help produce diagnostics like:

```text
Error entity.excel.sheetname_must_exist at entities.abc.options.sheetname:
Sheet 'Sheet1' does not exist in 'somefile.xlsx'.

Suggested fix:
Choose one of the sheets available in the referenced workbook.
```

Prefer diagnostics that identify the exact YAML location, failed rule ID, invalid value, expected value or available alternatives, and safe repair suggestion.

## Avoid

Do not:

- replace the generated JSON Schema
- duplicate every schema property as a semantic rule
- invent rules not supported by examples, schema, models, mapping code, core code, or graphify
- make low-confidence inferred conventions into hard errors
- create a complex expression language unless existing fields are insufficient
- hide uncertainty
- write vague messages such as "invalid configuration"
- propose unsafe autofixes for ambiguous source or target mappings
