# Proposal: Authoritative YAML Schema Reference

**Status:** Draft
**Scope:** Schema generation, Entity Pydantic model, configuration instructions
**Goal:** Provide AI coding agents and tooling with a complete, structured reference for Shape Shifter YAML structure.

---

## Summary

The JSON schemas used by the Monaco editor (`entitySchema.json`, `projectSchema.json`) are generated from Pydantic API models and omit six user-authored YAML fields, the `defer_dependency` FK option, loader-specific options, and directives. This gap is not a problem for human editors but prevents AI coding agents from reliably validating or authoring Shape Shifter YAML. The fix has three parts: add the missing fields to the `Entity` and `ForeignKeyConfig` Pydantic models, generate loader option sub-schemas from `DriverSchema`, and add an entity type contract table to the configuration instructions.

## Problem

`entitySchema.json` is generated from the `Entity` Pydantic model via `model_json_schema()`. The `Entity` model only declares structurally significant fields (identity, FK, columns, filters). Fields that exist in valid project YAML but are not on the model never appear in the schema.

The following fields are missing from the generated schema:

| Missing field                                 | Defined on                                           | Example usage                                   | Gap                                                                                          |
|-----------------------------------------------|------------------------------------------------------|-------------------------------------------------|----------------------------------------------------------------------------------------------|
| `options`                                     | `TableConfig` (raw dict)                             | `openpyxl`, `xlsx`, `csv` entities              | Loader options like `filename`, `sheet_name`, `range` are invisible                          |
| `check_functional_dependency`                 | `TableConfig.check_functional_dependency`            | `sample`, `site`, `site_location`               | Common validation toggle absent                                                              |
| `surrogate_name`                              | `TableConfig.surrogate_name`                         | `sample_description_type`, `site_property_type` | Fixed entity type naming absent                                                              |
| `type_names`                                  | YAML sidecar (raw dict)                              | `sample_description_type`                       | Column list referenced by `@value:` in other entities; absent from schema                    |
| `replacements`                                | `TableConfig.replacements`                           | Data quality transforms                         | Value replacement dict absent from schema                                                    |
| `defer_dependency`                            | `ForeignKeyConfig.defer_dependency`                  | FK cycle-breaking                               | Advanced FK setting absent from `ForeignKeyConfig` API model                                 |
| `materialized`                                | `TableConfig.materialized` / `MaterializationConfig` | `site_type`, `site_type_group`                  | Written by the materialization service, not human authors; schema exposure is lower priority |
| Directives (`@include:`, `@value:`, `@load:`) | `src/configuration/resolve.py`                       | Throughout YAML                                 | Resolved before models see the data; cannot be represented as JSON Schema properties         |

Not all gaps have the same fix. The table below categorizes them:

| Category                            | Fields                                                                                   | Approach                                                                                                                              |
|-------------------------------------|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| **Add to `Entity` model**           | `options`, `check_functional_dependency`, `surrogate_name`, `type_names`, `replacements` | Add Pydantic fields; re-run schema generation                                                                                         |
| **Add to `ForeignKeyConfig` model** | `defer_dependency`                                                                       | Add Pydantic field; re-run schema generation                                                                                          |
| **Deferred — system-managed**       | `materialized`                                                                           | Written by the materialization service after processing; not a user-authored field. Expose in a follow-up if schema consumers need it |
| **Deferred — not representable**    | Directives (`@include:`, `@value:`, `@load:`)                                            | These are string patterns resolved at config load time. JSON Schema cannot validate or document their syntax                          |

Additionally, the schema cannot express conditional requirements such as "if `type` is `openpyxl`, then `options.filename` is required." JSON Schema Draft 7 (the current target) does not support `if/then/else`. This gap requires the entity type contract table in the configuration instructions.

AI coding agents use the JSON schema as a primary reference when analyzing or editing Shape Shifter YAML. Without these fields, an agent cannot know that an `openpyxl` entity requires `options.filename`, that `replacements` is a valid key, or that `defer_dependency` can be set on a foreign key. The SKILL.md skill loads `shapeshifter-configuration.instructions.md`, which contains prose rules for some of these, but prose is not machine-readable and does not cover all cases. The semantic rules instructions in `docs/ai/semantic-rules-agent.md` define a machine-readable YAML rule catalog format that can express these conditional requirements, but no catalog exists yet.

## Scope

This proposal covers:

- Adding the six missing fields to the `Entity` and `ForeignKeyConfig` Pydantic models.
- Extending `generate_schemas.py` to generate loader option sub-schemas from `DriverSchema`.
- Adding an entity type contract table to `shapeshifter-configuration.instructions.md`.
- Creating an initial semantic rules catalog in `docs/rules/semantic_rules.yml` that encodes the entity type contracts as machine-readable conditional rules.

It does not cover the `materialized` field, directives, Monaco editor UX, Pydantic validation of `options` contents, or replacing the existing schema generation pipeline.

## Non-Goals

- This proposal does not replace the Pydantic `Entity` model with a complete YAML schema.
- This proposal does not upgrade to JSON Schema Draft 9+ for conditional logic.
- This proposal does not create a separate YAML schema file.
- This proposal does not address Monaco editor validation — the schemas remain autocomplete-only.
- This proposal does not add the `materialized` field (system-managed, not user-authored).
- This proposal does not represent directives (`@include:`, `@value:`, `@load:`) in JSON Schema (not representable).

## Current Behavior

### Schema generation

`scripts/generate_schemas.py` calls `Entity.model_json_schema()` and writes the result to `frontend/src/schemas/entitySchema.json`. The `Entity` model in `backend/app/models/entity.py` has no `options` field.

### Project model

`Project.entities` is typed as `dict[str, dict[str, Any]]` — raw dicts. The `Project` model does not validate entity contents against the `Entity` Pydantic model. Entities flow through as raw YAML, and the `ProjectMapper` bridges API and Core layers.

### Core model

`TableConfig` in `src/model.py` reads `options` directly from the underlying YAML dict via a property. The core model is a thin wrapper, not a schema.

### Loader schemas

Each loader declares its accepted options as a `DriverSchema` class variable on the loader class. `DriverSchemaRegistry` (in `src/loaders/driver_metadata.py`) collects these from all registered loader classes and exposes them via `DriverSchemaRegistry.all()`. These schemas are used by the frontend for data source configuration but are not connected to entity schema generation.

## Proposed Design

### 1. Add missing fields to the `Entity` and `ForeignKeyConfig` Pydantic models

Add the following fields to `backend/app/models/entity.py`:

```python
options: dict[str, Any] = Field(
    default_factory=dict,
    description="Loader-specific options (filename, sheet_name, range, etc.). Required keys depend on entity type."
)
check_functional_dependency: bool = Field(
    default=True,
    description="Whether to check functional dependency when dropping duplicates. Default True."
)
surrogate_name: str | None = Field(
    default=None,
    description="Fixed entity type name used when the entity represents a controlled vocabulary type."
)
type_names: list[str] = Field(
    default_factory=list,
    description="Column name list for unnest type columns, referenced by @value: in other entities."
)
replacements: dict[str, Any] = Field(
    default_factory=dict,
    description="Value replacement rules applied during data extraction."
)
```

Add `defer_dependency` to `ForeignKeyConfig` in the same file:

```python
defer_dependency: bool = Field(
    default=False,
    description="Break a dependency cycle by deferring the FK link to a final pass. Use only when circular references are unavoidable."
)
```

These additions surface all user-authored YAML fields in the generated schema. None of them change validation behaviour — they widen what the schema describes, not what the backend accepts.

### 2. Generate loader option sub-schemas from `DriverSchema`

Extend `scripts/generate_schemas.py` to call `DriverSchemaRegistry.all()` (imported from `src.loaders.driver_metadata`) and convert each loader's `DriverSchema` into a JSON Schema fragment. For each loader, `FieldMetadata` entries map to JSON Schema properties: `name` → property key, `type` → JSON Schema type (`file_path` → `string`), `required` fields go into the `required` array, and `description` and `default` pass through directly. The resulting fragments are added to the `options` property in `entitySchema.json` as a `oneOf` array.

The generated structure would be:

```json
"options": {
  "type": "object",
  "description": "Loader-specific options. Required keys depend on entity type.",
  "oneOf": [
    {
      "description": "Options for type: openpyxl",
      "properties": {
        "filename": { "type": "string", "description": "Path to .xlsx file" },
        "sheet_name": { "type": "string", "description": "Sheet name to load" },
        "range": { "type": "string", "description": "Cell range to load (e.g., A1:D10)" },
        "sanitize_header": { "type": "boolean", "description": "Whether to sanitize column headers", "default": true }
      },
      "required": ["filename"]
    },
    {
      "description": "Options for type: xlsx",
      "properties": {
        "filename": { "type": "string", "description": "Path to .xlsx or .xls file" },
        "sheet_name": { "type": "string", "description": "Sheet name to load" },
        "sanitize_header": { "type": "boolean", "description": "Whether to sanitize column headers", "default": true }
      },
      "required": ["filename"]
    }
  ]
}
```

This gives AI agents structured, loader-specific option information. The `oneOf` is a hint, not a conditional constraint — Monaco autocomplete may not use it perfectly, but it provides the information.

### 3. Add entity type contract table to configuration instructions

Add a structured table to `.github/instructions/shapeshifter-configuration.instructions.md` that explicitly lists required and optional fields per entity type. This is the authoritative reference for AI agents loading the SKILL.md skill:

```markdown
## Entity Type Contracts

Required and optional fields per entity type. `options.*` fields are loader-specific; see loader schemas for detail.

| Type         | Required fields                       | Required options   | Optional fields                                                  | Notes                                                                                                                                  |
|--------------|---------------------------------------|--------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `entity`     | none (default when `type` is omitted) | none               | `source`, `columns`, `foreign_keys`, `depends_on`                | `source` names a parent entity to derive from; omit `source` to load from the project default data source                              |
| `sql`        | `data_source`, `query`                | none               | `columns`, `keys`, `public_id`, `depends_on`                     | `data_source` must match an entry in `options.data_sources`; `data_source: "@internal"` is exempt and requires no `data_sources` entry |
| `fixed`      | `columns`, `values`                   | none               | `public_id`, `keys`, `column_types`, `extra_columns`             | Row width must match `columns` length                                                                                                  |
| `csv`, `tsv` | —                                     | `options.filename` | `options.delimiter`, `options.encoding`                          | File loader; `csv` and `tsv` use the same loader class                                                                                 |
| `xlsx`       | —                                     | `options.filename` | `options.sheet_name`, `options.sanitize_header`                  | File loader, pandas engine                                                                                                             |
| `openpyxl`   | —                                     | `options.filename` | `options.sheet_name`, `options.range`, `options.sanitize_header` | File loader, openpyxl engine with range support                                                                                        |
| `merged`     | `branches`, `public_id`               | none               | `keys`, `foreign_keys`                                           | Each branch needs `name` + `source`                                                                                                    |
| `duckdb`     | `query`, `depends_on`                 | none               | `columns`, `keys`, `public_id`                                   | No `data_source`                                                                                                                       |
```

This table is parseable by AI agents and provides the conditional logic that JSON Schema cannot express.

### 4. Create initial semantic rules catalog

Create `docs/rules/semantic_rules.yml` following `docs/ai/semantic-rules-agent.md`. The entity type contract table in step 3 provides the verified source for the initial rule set. Each row maps to one or more rules:

- A `conditional` rule for required `options` fields per file-loader type (e.g., `xlsx` and `openpyxl` require `options.filename`).
- A `structural` rule for required top-level fields per type (e.g., `sql` requires `data_source` and `query`).
- A `project_resource` rule where the resource can be verified at runtime (e.g., `options.filename` must point to an existing file).

This gives AI agents a machine-readable rule catalog that complements the prose instructions in `shapeshifter-configuration.instructions.md` and the `SKILL.md` skill. The `SKILL.md` workflow loads this file when present, making it the primary reference for programmatic and AI-assisted semantic validation.

## Alternatives Considered

### Add all missing fields to `Entity` as hand-curated Pydantic fields

Add every YAML field, including `materialized`, `type_names`, `replacements`, and similar fields, by hand to `Entity`. This proposal already adds the six straightforward fields. The distinction here is "hand-curate all fields including ambiguous ones" — the risk is that fields like `materialized` (system-managed) or arbitrary sidecar fields (e.g., project-specific cross-reference keys) would appear as first-class model fields without clear semantics. The proposal draws the line at fields that have a defined role and are user-authored.

### Upgrade to JSON Schema Draft 9+ with `if/then/else`

This would allow conditional constraints like "if `type` is `openpyxl`, then `options.filename` is required." The Monaco YAML language server supports Draft 2020-12, but the conditional logic would still need a source of truth for what each type requires. This is a surface improvement on top of the structural gap.

### Create a separate YAML schema file

A dedicated schema file, not derived from Pydantic, could be the authoritative YAML reference. This is the most complete approach. The maintenance burden is prohibitive: a hand-curated schema would diverge from the Pydantic models over time, and the Pydantic-derived schema would still be required for Monaco. Any new entity field or loader option would need two updates.

## Risks And Tradeoffs

- **`oneOf` in Monaco autocomplete:** Monaco's YAML language server may not use `oneOf` for autocomplete effectively. The loader option sub-schemas are primarily for AI agent consumption, not editor UX.
- **Schema drift:** If a loader adds or removes `FieldMetadata`, the generated schema will change on next run. This is acceptable — the schema should track the loaders.
- **`options` as `dict[str, Any]`:** Adding this to `Entity` means the Pydantic model no longer validates `options` contents. This is consistent with current behavior — `options` validation happens at the loader boundary.
- **Instruction table maintenance:** The type contract table needs updates when new entity types or required fields are added. This is a documentation maintenance cost, but it is the same cost as updating the prose rules.

## Testing And Validation

- Run `python scripts/generate_schemas.py` and verify `entitySchema.json` now includes `options` with loader sub-schemas.
- Verify `make lint` passes (Black + isort).
- Verify existing tests pass (`make test`).
- Manually verify Monaco editor loads the updated schema without errors in the frontend.
- Verify the SKILL.md skill loads the updated instructions file successfully.

## Acceptance Criteria

- `entitySchema.json` includes `options`, `check_functional_dependency`, `surrogate_name`, `type_names`, and `replacements` as properties on entity definitions.
- `entitySchema.json` includes `defer_dependency` as a property on foreign key definitions.
- `entitySchema.json` includes loader-specific option sub-schemas for `openpyxl`, `xlsx`, and `csv` loaders.
- `shapeshifter-configuration.instructions.md` includes an entity type contract table.
- Schema generation is driven by `DriverSchema` from the loader registry, not hardcoded.
- Existing tests pass.
- Monaco editor loads the updated schema without errors.
- `docs/rules/semantic_rules.yml` exists with conditional rules covering required and optional `options` fields for each entity type, following the format in `docs/ai/semantic-rules-agent.md`.

## Recommended Delivery Order

1. Add `options`, `check_functional_dependency`, `surrogate_name`, `type_names`, `replacements` to `Entity` in `backend/app/models/entity.py`.
2. Add `defer_dependency` to `ForeignKeyConfig` in the same file.
3. Extend `generate_schemas.py` to generate loader option sub-schemas from `DriverSchema`.
4. Add entity type contract table to `shapeshifter-configuration.instructions.md`.
5. Create `docs/rules/semantic_rules.yml` from the entity type contracts using `docs/ai/semantic-rules-agent.md`.
6. Run schema generation and validate output.
7. Run full test suite.

## Final Recommendation

Implement the three-part fix. The changes are small and self-contained; the maintenance cost is bounded by the loader registry and the instruction table.

---

## Task Plan

### Work Breakdown

#### Area 1 — Pydantic model fields

Objective: surface all user-authored YAML fields in the generated schema by adding them to the API models.

- [x] Open `backend/app/models/entity.py` and locate the `Entity` model.
- [x] Add `options: dict[str, Any]` field with description.
- [x] Add `check_functional_dependency: bool` field with `default=True` and description.
- [x] Add `surrogate_name: str | None` field with `default=None` and description.
- [x] Add `type_names: list[str]` field with `default_factory=list` and description.
- [x] Add `replacements: dict[str, Any]` field with `default_factory=dict` and description.
- [x] Locate `ForeignKeyConfig` in the same file and add `defer_dependency: bool` with `default=False` and description.
- [x] Verify `from __future__ import annotations` and `Any` import are present.
- [x] Run `make lint` and confirm no type errors on the model file.

Completion condition: all six fields appear in the model; `make lint` passes; no existing tests break.

#### Area 2 — Loader option sub-schemas

Objective: make `entitySchema.json` include structured, loader-specific option schemas derived from the loader registry.

- [x] Open `scripts/generate_schemas.py` and review the current schema generation logic.
- [x] Import `DriverSchemaRegistry` from `src.loaders.driver_metadata`.
- [x] Call `DriverSchemaRegistry.all()` to retrieve all registered loader schemas.
- [x] Write a conversion function that maps each `DriverSchema` → JSON Schema fragment:
  - `FieldMetadata.name` → property key
  - `FieldMetadata.type` → JSON Schema type (`file_path` → `string`)
  - `FieldMetadata.required` → `required` array entry
  - `FieldMetadata.description` and `FieldMetadata.default` → pass through
- [x] Build a `oneOf` array from all loader fragments and assign it to the `options` property in the generated schema.
- [x] Run `python scripts/generate_schemas.py` and inspect `frontend/src/schemas/entitySchema.json`.
- [x] Confirm `options.oneOf` contains entries for `openpyxl`, `xlsx`, and `csv` loaders.
- [x] Confirm `filename` appears in `required` for file-loader entries.

Completion condition: `entitySchema.json` contains `options` with a populated `oneOf`; generation is driven by the registry, not hardcoded values.

#### Area 3 — Configuration instructions

Objective: add a machine-parseable entity type contract table to `shapeshifter-configuration.instructions.md` so AI agents loading the SKILL.md skill have complete per-type field requirements.

- [x] Confirm the entity type contract table has been added to `.github/instructions/shapeshifter-configuration.instructions.md` (done as part of proposal alignment — verify it is present and accurate).
- [x] Cross-check each table row against the current loader and mapper behavior:
  - [x] `entity`: no required options; `source` optional.
  - [x] `sql`: `data_source` and `query` required; `"@internal"` exemption documented.
  - [x] `fixed`: `columns` and `values` required; row width rule present.
  - [x] `csv`/`tsv`: `options.filename` required; same loader class noted.
  - [x] `xlsx`: `options.filename` required; `options.sheet_name` optional.
  - [x] `openpyxl`: `options.filename` required; `options.sheet_name` and `options.range` optional.
  - [x] `merged`: `branches` and `public_id` required.
  - [x] `duckdb`: `query` and `depends_on` required; no `data_source`.
- [x] Verify the symlink at `.github/skills/shapeshifter-configuration/references/shapeshifter-configuration.instructions.md` reflects the updated file.

Completion condition: entity type contract table is present, all rows are accurate, and the SKILL.md symlink resolves correctly.

#### Area 4 — Semantic rules catalog

Objective: create `docs/rules/semantic_rules.yml` as a machine-readable rule catalog covering entity type contracts and common error patterns using `docs/ai/semantic-rules-agent.md`.

- [x] Create `docs/rules/semantic_rules.yml` with `version: 1` header.
- [x] Add `conditional` rules for required options per file-loader type:
  - [x] `entity.xlsx.requires_filename` — `options.filename` required when `type: xlsx`.
  - [x] `entity.openpyxl.requires_filename` — `options.filename` required when `type: openpyxl`.
  - [x] `entity.csv.requires_filename` — `options.filename` required when `type: csv`.
  - [x] `entity.tsv.requires_filename` — `options.filename` required when `type: tsv`.
- [x] Add `structural` rules for required top-level fields:
  - [x] `entity.sql.requires_data_source` — `data_source` required when `type: sql` (exempt: `"@internal"`).
  - [x] `entity.sql.requires_query` — `query` required when `type: sql`.
  - [x] `entity.fixed.requires_columns` — `columns` required when `type: fixed`.
  - [x] `entity.fixed.requires_values` — `values` required when `type: fixed`.
  - [x] `entity.merged.requires_branches` — `branches` required when `type: merged`.
  - [x] `entity.merged.requires_public_id` — `public_id` required when `type: merged`.
  - [x] `entity.duckdb.requires_query` — `query` required when `type: duckdb`.
  - [x] `entity.duckdb.requires_depends_on` — `depends_on` required when `type: duckdb`.
- [x] Add `project_resource` rules for file existence:
  - [x] `entity.xlsx.filename_must_exist` — `options.filename` must point to an existing file.
  - [x] `entity.openpyxl.filename_must_exist` — `options.filename` must point to an existing file.
  - [x] `entity.csv.filename_must_exist` — `options.filename` must point to an existing file.
- [x] Add `consistency` rules for cross-entity references:
  - [x] `reference.entity_must_exist` — every entity referenced in `source`, `foreign_keys[].entity`, `append[].source`, or `merged.branches[].source` must exist in `entities`.
- [x] Add `source` references for each rule pointing to the relevant Pydantic model, loader, or instruction file.
- [x] Create `docs/rules/README.md` with a short description of the catalog and its intended use.
- [x] Verify YAML parses cleanly (`python -c "import yaml; yaml.safe_load(open('docs/rules/semantic_rules.yml'))"`).

Completion condition: `docs/rules/semantic_rules.yml` parses cleanly; all entity types from the contract table are covered; `docs/rules/README.md` exists.

#### Area 5 — Validation and testing

Objective: confirm the full change set passes all existing checks and produces the expected outputs.

- [x] Run `python scripts/generate_schemas.py` and verify no errors.
- [x] Inspect `frontend/src/schemas/entitySchema.json`:
  - [x] `options` property is present with `oneOf`.
  - [x] `check_functional_dependency`, `surrogate_name`, `type_names`, `replacements` are present as entity properties.
  - [x] `defer_dependency` is present as a foreign key property.
- [x] Run `make lint` (Black + isort) and confirm it passes.
- [x] Run `make test` and confirm all tests pass.
- [x] Load the updated schema in the frontend Monaco editor and verify no console errors.
- [x] Run `uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow all --log-level ERROR` on at least one real project file and confirm validation behavior is unchanged.

Completion condition: all checks pass; schema output matches acceptance criteria; project validation behavior is unchanged.

---

### Progress Tracker

| Area                           | Status      | Notes                                                   |
|--------------------------------|-------------|---------------------------------------------------------|
| 1 — Pydantic model fields      | Complete    | `backend/app/models/entity.py`                          |
| 2 — Loader option sub-schemas  | Complete    | `scripts/generate_schemas.py`                           |
| 3 — Configuration instructions | Complete    | Table verified accurate; symlink confirmed              |
| 4 — Semantic rules catalog     | Complete    | `docs/rules/semantic_rules.yml`, `docs/rules/README.md` |
| 5 — Validation and testing     | Not started | Depends on areas 1–4                                    |

---

### Definition Of Done

- [x] `entitySchema.json` includes `options` (with `oneOf` loader sub-schemas), `check_functional_dependency`, `surrogate_name`, `type_names`, `replacements`, and `defer_dependency`.
- [x] Schema generation reads from `DriverSchemaRegistry`; no loader option values are hardcoded in `generate_schemas.py`.
- [x] Entity type contract table is present and accurate in `shapeshifter-configuration.instructions.md`.
- [x] `docs/rules/semantic_rules.yml` exists, parses cleanly, and covers all entity types in the contract table.
- [x] `docs/rules/README.md` exists with a brief description of the rule catalog.
- [x] `make lint` passes.
- [x] `make test` passes with no regressions.
- [x] Monaco editor loads the updated schema without errors.
- [x] At least one real project file validates without behavior change.

---

### Deliverables

| Deliverable | Description | Status |
|---|---|---|
| `backend/app/models/entity.py` | Add five fields to `Entity`; add `defer_dependency` to `ForeignKeyConfig` | Done |
| `scripts/generate_schemas.py` | Extend to generate loader option sub-schemas from `DriverSchemaRegistry` | Done |
| `frontend/src/schemas/entitySchema.json` | Regenerated output with new fields and `options.oneOf` |Done |
| `.github/instructions/shapeshifter-configuration.instructions.md` | Entity type contract table added | Done |
| `docs/rules/semantic_rules.yml` | Initial semantic rules catalog | Done |
| `docs/rules/README.md` | Brief description and usage guide for the rule catalog | Done |
