# Target Model Specification Guide

## Overview

A **target model specification** is a YAML file that describes what an external destination system — such as the SEAD Clearinghouse — expects from a Shape Shifter project. It defines which entities are required, what columns and foreign-key relationships they must have, and what naming conventions apply.

The field-level schema authority lives in the Pydantic models in `src/target_model/models.py`. Use `TARGET_MODEL_GUIDE.md` as the narrative guide and `TARGET_MODEL_SCHEMA_REFERENCE.md` as the generated key-by-key reference derived from that schema.

When a project references a target model, Shape Shifter can perform **conformance validation**: checking whether the project entities actually satisfy the requirements described in the spec. This catches semantic modeling errors at configuration time, before you run the pipeline or attempt a dispatch.

Target model specs are optional. Existing projects without a `target_model` reference continue to work without any changes.

---

## Quick Start

1. Pick or create a spec file — e.g., `resources/target_models/sead_superset_model.yml` (the current bundled SEAD superset spec ships with Shape Shifter).
2. Add a `target_model` reference to your project's `metadata` section:

```yaml
metadata:
  type: 'shapeshifter-project'
  name: "Dendrochronology Import"
  target_model: "@include: resources/target_models/sead_superset_model.yml"
```

3. Open your project in the editor, go to the **Validate** tab, and click **Check Conformance**.
4. Review any issues in the **Conformance** expansion panel.

---

## File Location

The current bundled SEAD spec lives at `resources/target_models/sead_superset_model.yml`. Custom or project-specific specs can live anywhere; reference them with a path relative to the project file or an absolute path.

Recommended layout for project-specific specs:

```
target_models/
  specs/
    sead_superset_model.yml           ← bundled SEAD superset spec
    my_museum.yml         ← custom target model
```

---

## Referencing a Target Model from a Project

Use the `metadata.target_model` field. The value may be either a file reference or an inline definition.

**File reference (recommended):**
```yaml
metadata:
  type: 'shapeshifter-project'
  target_model: "@include: resources/target_models/sead_superset_model.yml"
```

**Inline definition (for small custom models):**
```yaml
metadata:
  type: 'shapeshifter-project'
  target_model:
    model:
      name: "Custom Museum"
      version: "1.0.0"
    entities:
      artifact:
        role: fact
        required: true
        public_id: artifact_id
        columns:
          accession_number:
            required: true
            type: string
            nullable: false
    naming:
      public_id_suffix: "_id"
```

The Metadata Editor in the project workspace surfaces this as a **Target Model** combobox that lists uploaded YAML files in `@include:` format. You can also type a path directly.

---

## Target Model File Format

Target model files are parsed with strict Pydantic models. Unknown keys in these blocks are rejected during load instead of being silently ignored.

For the full generated reference of accepted sections, keys, defaults, and enum values, see [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md).

### Top-Level Structure

```yaml
model:
  name: string          # Human-readable model name (required)
  format_version: "1"   # Optional format version; defaults to "1"
  version: string       # Semantic version, e.g. "2.0.0" (required)
  description: string   # Optional description

entities:               # Map of entity name → entity spec
  <entity_name>:
    ...

naming:                 # Optional naming convention rules
  public_id_suffix: string

constraints:            # Optional global constraint list
  - type: string
    required: true | strict
```

---

### `model` Block

```yaml
model:
  name: "SEAD Clearinghouse"
  format_version: "1"
  version: "2.0.0"
  description: "SEAD archaeological research data model"
```

| Field         | Required | Description                                       |
|---------------|----------|---------------------------------------------------|
| `name`        | Yes      | Display name of the target system                 |
| `format_version` | No    | Target-model format version. Defaults to `"1"`  |
| `version`     | Yes      | Version of *this spec file* (semantic versioning) |
| `description` | No       | Free-text description shown in tooling            |

---

### `entities` Block

Each key is an entity name that must match the project entity name. Each value is an **entity spec**.

```yaml
entities:
  site:
    role: lookup
    required: true
    description: "Archaeological site"
    domains: [core, spatial]
    target_table: tbl_sites
    public_id: site_id
    identity_columns: [site_name]
    identity_tracking: reconciled
    reconciliation: reconcile-fuzzy
    columns:
      site_name:
        required: true
        type: string
        nullable: false
    unique_sets:
      - [site_name]
    foreign_keys:
      - entity: location
        required: true
        via: site_location
```

#### Entity Spec Fields

| Field              | Required | Description                                                                    |
|--------------------|----------|--------------------------------------------------------------------------------|
| `role`             | No       | Semantic role: `fact`, `lookup`, `classifier`, or `bridge`                     |
| `required`         | No       | `true` means the project must include this entity (default: `false`)           |
| `description`      | No       | Human-readable description for tooling and documentation                       |
| `domains`          | No       | List of domain tags; used to filter entities when generating project templates |
| `target_table`     | No       | Physical table name in the target system (informational, e.g. `tbl_sites`)     |
| `public_id`        | No       | Expected `public_id` value in the project entity                               |
| `identity_columns` | No       | Columns that form the natural key in the target system                         |
| `columns`          | No       | Map of column name → column spec; conformance checks these against the project |
| `unique_sets`      | No       | List of unique-set column groups                                               |
| `foreign_keys`     | No       | List of foreign key specs                                                      |
| `identity_tracking`| No       | Identity handling mode: `tracked`, `reconciled`, `derived`, or `child`        |
| `reconciliation`   | No       | Expected matching or allocation mode for this entity                           |
| `aggregate_parent` | No       | Parent entity name when this entity inherits aggregate identity                |

---

### Semantic Roles

The `role` field describes the meaning of an entity in the target model. Roles still help humans read the model, but they also drive implemented conformance rules such as orphan-fact detection and classifier source-type checks.

| Role         | Meaning                                                                                                                                       |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `fact`       | A primary observational or transactional record (e.g., a sample, an analysis result). Usually depends on surrounding lookups and classifiers. |
| `lookup`     | Reference data providing stable parent context (e.g., locations, sites, methods). Commonly referenced by many facts.                          |
| `classifier` | A controlled vocabulary or typology entity (e.g., site types, sample types). Best loaded from `fixed` or `sql` sources.                       |
| `bridge`     | An association entity connecting two or more entities in a many-to-many relationship.                                                         |

---

### Column Specs

```yaml
columns:
  site_name:
    required: true
    type: string
    nullable: false
  latitude_dd:
    type: decimal
    nullable: true
  site_type_id:
    type: integer
    generated: true
    nullable: true
  status:
    type: string
    allowed_values: [draft, final]
```

| Field      | Required | Description                                                                                          |
|------------|----------|------------------------------------------------------------------------------------------------------|
| `required` | No       | `true` means the project entity must expose this column unless it is marked as generated             |
| `generated` | No      | Marks a target column that is produced downstream rather than directly supplied by the project        |
| `allowed_values` | No | Literal allowed values for the column; useful for enums, docs, and downstream tooling                |
| `type`     | No       | Hint type such as `string`, `integer`, `decimal`, `boolean`, or `date`                              |
| `nullable` | No       | Whether the column is expected to allow null values                                                  |
| `description` | No    | Human-readable note for reviewers, generated docs, and editor help                                   |

Shape Shifter counts a column as present in a project entity when it appears as:
- an explicit entry in `columns` or `keys`
- an entry in `extra_columns`
- the `public_id` value
- a column contributed by a foreign key (parent's `public_id`)
- a column that survives an `unnest` transformation (`id_vars`, `var_name`, `value_name`)

Current conformance rules enforce `required` columns. `generated: true` excludes a required column from direct missing-column checks because the value is expected to be added later. `type`, `nullable`, and `allowed_values` remain descriptive metadata for now.

---

### Foreign Key Specs

```yaml
foreign_keys:
  - entity: location
    required: true
    via: site_location
  - entity: site_type
    required: false
```

| Field      | Required | Description                                                                         |
|------------|----------|-------------------------------------------------------------------------------------|
| `entity`   | Yes      | Name of the target entity this FK must point to                                     |
| `required` | No       | `true` means the project entity must declare a FK to this entity (default: `false`) |
| `via`      | No       | Bridge entity name for many-to-many relationships such as `site -> site_location -> location` |

Conformance checks whether the project entity has at least one foreign key whose target matches the required entity name.

When `via` is present, conformance first checks the source entity points to the bridge entity, then checks whether the bridge points to the ultimate target entity.

---

### Identity And Reconciliation Fields

These fields describe how an entity participates in SIMS identity handling and lookup/allocation workflows.

Shape Shifter validates these fields together when a target model loads:

- `aggregate_parent` must name another entity in the same model
- entities with `aggregate_parent` must also declare a foreign key to that parent
- `identity_tracking: child` requires `aggregate_parent`
- `tracked` entities resolve to `allocate`
- `derived` entities resolve to `derive`
- `child` entities must not declare a reconciliation strategy
- `reconciled` entities must resolve to one of `reconcile-exact`, `reconcile-fuzzy`, `lookup-only`, or `lookup-extensible`

| Field | Allowed values | Description |
|-------|----------------|-------------|
| `identity_tracking` | `tracked`, `reconciled`, `derived`, `child` | Declares whether the entity gets its own tracked identity, is matched by business keys, derives identity from related rows, or inherits from an aggregate parent |
| `reconciliation` | `allocate`, `reconcile-exact`, `reconcile-fuzzy`, `lookup-only`, `lookup-extensible`, `derive` | Declares the expected matching or allocation mode for this entity |
| `aggregate_parent` | Entity name | Required when identity is inherited from a parent aggregate such as `analysis_entity` or `sample` |

---

### `naming` Block

```yaml
naming:
  public_id_suffix: "_id"
```

| Field              | Description                                                                                          |
|--------------------|------------------------------------------------------------------------------------------------------|
| `public_id_suffix` | Every `public_id` value in project entities must end with this string. The SEAD standard is `"_id"`. |

---

### `constraints` Block

```yaml
constraints:
  - type: no_orphan_facts
    required: strict
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Global rule name applied to the whole target model |
| `required` | No | Rule strictness for constraints that support it. Use `true` or `strict` for error mode |

Current constraints are modeled as typed entries with optional strictness. Add new constraint-specific keys only after extending the Pydantic schema.

`no_orphan_facts` is enforced by the conformance engine when the target model declares it. The rule checks that each fact entity present in the project reaches at least one lookup or classifier through the target-facing FK graph. When `required` is omitted, the rule emits warnings. When `required: true` or `required: strict` is set, the rule emits errors.

---

## Conformance Validation

### How It Works

When you click **Check Conformance** in the editor, Shape Shifter:

1. Loads the project and resolves the `target_model` reference (expanding `@include:` if needed).
2. Parses the target model spec into a `TargetModel` domain object.
3. Runs the target-model spec validator to check self-consistency, including unknown FK targets, invalid aggregate-parent relationships, and invalid identity-tracking or reconciliation combinations.
4. Runs the built-in conformance validators against the resolved project.
5. Returns `ConformanceIssue` objects grouped as errors, warnings, or info, each including a code, message, affected entity and field, and a suggestion when available.

Conformance results appear in their own **Conformance** panel in the Validate tab, separate from structural and data validation results.

### Issue Codes

Default severities are shown below. Project-level severity overrides can remap individual rules to `error`, `warning`, or `info`.

| Code                                  | Severity | What It Means                                                                          |
|---------------------------------------|----------|----------------------------------------------------------------------------------------|
| `MISSING_REQUIRED_ENTITY`             | error    | An entity marked `required: true` in the target model is absent from the project       |
| `MISSING_PUBLIC_ID`                   | error    | The target model declares a `public_id` for an entity, but the project entity has none |
| `UNEXPECTED_PUBLIC_ID`                | error    | The project entity declares a different `public_id` than the target model expects      |
| `MISSING_REQUIRED_FOREIGN_KEY_TARGET` | error    | A required FK target is not declared on the project entity                             |
| `MISSING_BRIDGE_ENTITY`               | error    | A required bridge entity for a `via:` relationship is missing                          |
| `BRIDGE_MISSING_TARGET_FK`            | error    | The bridge entity does not link to the declared ultimate target                        |
| `MISSING_REQUIRED_COLUMN`             | error    | A required non-generated target column is not present in the entity's target-facing columns |
| `APPEND_MISSING_REQUIRED_COLUMN`      | error    | An append branch does not satisfy the parent entity's required target columns          |
| `PUBLIC_ID_NAMING_VIOLATION`          | error    | A `public_id` value does not end with the `naming.public_id_suffix`                    |
| `MISSING_INDUCED_REQUIRED_ENTITY`     | error    | A non-global entity becomes required because a present entity depends on it            |
| `ORPHAN_FACT_ENTITY`                  | warning  | A fact entity does not reach any lookup or classifier declared in the target model     |
| `CLASSIFIER_WRONG_SOURCE_TYPE`        | warning  | A classifier entity uses a source type other than `fixed` or `sql`                     |
| `UNKNOWN_DISABLED_CONFORMANCE_RULE`   | warning  | The project disables a conformance rule key that does not exist                        |
| `UNKNOWN_CONFORMANCE_SEVERITY_OVERRIDE` | warning | The project overrides severity for an unknown conformance rule key                     |
| `INVALID_CONFORMANCE_SEVERITY_OVERRIDE` | warning | The project uses an unsupported severity override value                                |

### Validators

Nine validators run in sequence. All are enabled by default, and projects can disable or remap specific rules through `options.validation`.

| Validator key       | What it checks                                                                                    |
|---------------------|---------------------------------------------------------------------------------------------------|
| `public_id`         | Checks that each project entity matches the `public_id` declared in the target spec               |
| `foreign_key`       | Checks required FK targets, including bridge-mediated `via:` relationships                        |
| `no_orphan_facts`   | Checks that fact entities can reach at least one lookup or classifier when the constraint is declared |
| `schema_aware_append` | Checks append branches against the parent entity's required target-facing columns               |
| `required_columns`  | Checks that each required non-generated column is in the project entity's target-facing column set |
| `required_entity`   | Checks that every entity with `required: true` exists in the project                              |
| `naming_convention` | Checks that all `public_id` values end with `naming.public_id_suffix`                             |
| `induced_requirements` | Checks transitive required-FK dependencies implied by present optional entities               |
| `source_type_appropriateness` | Warns when classifier entities use source types other than `fixed` or `sql`          |

### Rule Controls

Projects can adjust conformance behavior under `options.validation`:

```yaml
options:
  validation:
    disabled_rules:
      - source_type_appropriateness
    severity_overrides:
      no_orphan_facts: error
      required_columns: warning
```

- `disabled_rules` accepts registered validator keys from the table above.
- `severity_overrides` accepts `error`, `warning`, or `info`.
- Unknown rule keys or invalid severity values do not stop validation, but they do emit warnings.

### Checking Conformance Without the UI

The conformance engine can also be used from the CLI for quick checks:

```bash
python -m src.target_model.conformance \
  --spec resources/target_models/sead_superset_model.yml \
  --project data/projects/my_project/shapeshifter.yml
```

---

## Generating a Project Scaffold from a Target Model

The template generator creates a starter project YAML pre-populated with the entities and columns defined in a target model spec:

```bash
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_superset_model.yml \
  --output my_project_scaffold.yml

# Filter to a specific domain
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_superset_model.yml \
  --domain core \
  --output core_entities.yml

# Include only specific entities
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_superset_model.yml \
  --entity location \
  --entity site \
  --entity sample \
  --output minimal.yml
```

The generated scaffold has the correct identity fields and foreign keys pre-filled; you only need to add source configuration (`type`, `source`, `data_source`, etc.) for each entity.

---

## Writing a Custom Target Model

### Minimal Example

```yaml
model:
  name: "My Museum System"
  format_version: "1"
  version: "1.0.0"

entities:
  artifact:
    role: fact
    required: true
    public_id: artifact_id
    columns:
      accession_number:
        required: true
        type: string
        nullable: false
      collection_date:
        type: string
        nullable: true
      status:
        allowed_values: [draft, final]
    foreign_keys:
      - entity: collection
        required: true

  collection:
    role: lookup
    required: true
    public_id: collection_id
    columns:
      collection_name:
        required: true
        type: string
        nullable: false

naming:
  public_id_suffix: "_id"
```

### Tips

- Start minimal: add only the entities and columns you actually want to enforce. Extra entities in the spec that are absent from the project do not cause errors unless they are marked `required: true`.
- Use `required: false` (or omit `required`) for optional/conditional entities that only appear in some project shapes.
- Set `required: true` on columns only when their absence indicates a genuine configuration error.
- Use `generated: true` for target columns that are added later by database defaults, downstream transforms, or other post-extraction steps.
- Use `allowed_values` when a column is effectively an enum and you want that constraint visible in generated docs and schema-driven tooling.
- The `type`, `nullable`, and `allowed_values` column fields are descriptive metadata in the current validator set; only `required` columns are enforced directly.
- Use `domains` tags to group entities so you can generate partial project scaffolds.

---

## SEAD Superset Spec (`sead_superset_model.yml`)

The bundled SEAD superset spec at `resources/target_models/sead_superset_model.yml` currently covers 98 entities. It is intended to be the near-complete shared SEAD model from which individual Shape Shifter projects can select curated subsets.

| Domain       | Entities                                                                                                                                                                |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `core` | Core context entities such as `location`, `site`, `sample_group`, `sample`, `method`, `dataset`, `analysis_entity`, and provenance lookups |
| `analysis` | Generic analysis values, value-class lookups, notes, identifiers, categorical, boolean, and numeric typed values, range variants, taxon counts, and analysis-value dimensions attached to `analysis_entity` records |
| `spatial` | Spatial context and coordinate-related entities such as `location`, `site_location`, `dimension`, site property and national-grid-reference entities, and site, sample, or sample-group coordinate extensions |
| `sample-metadata` | Sample and sample-group descriptions, sampling-context and horizon lookups, locations, notes, colours, dimensions, qualifier vocabularies, references, and other attached metadata entities |
| `abundance` | Abundance observations, shared property-type vocabularies, abundance property entities, and related classifiers |
| `taxonomy` | Taxonomy entities such as `taxa_tree_master`, `taxa_common_names`, synonyms, measured attributes, Red Data Book lookups, and related taxonomy support tables |
| `dating` | Relative dating, chronology, dating lab, and uncertainty entities |
| `provenance` | Project, dataset, citation, contact, and dataset-contact provenance entities |

The SEAD superset spec uses `naming.public_id_suffix: "_id"` and declares `constraints: [{type: no_orphan_facts}]`.

---

## Generating Documentation from a Target Model

`scripts/generate_target_model_docs.py` produces human-readable output from any target model YAML spec. Four formats are supported:

| Format     | Best for                              | Output file   |
|------------|---------------------------------------|---------------|
| `html`     | Stakeholder presentations, reference  | `<stem>.html` |
| `excel`    | Review workshops, gap analysis        | `<stem>.xlsx` |
| `markdown` | GitHub wikis, version-controlled docs | `<stem>.md`   |
| `sims`     | SIMS entity register and identity review | `<stem>.sims.md` |

```bash
# Generate all formats (default)
python scripts/generate_target_model_docs.py resources/target_models/sead_superset_model.yml

# HTML only — recommended for sharing with archaeologists and data managers
python scripts/generate_target_model_docs.py resources/target_models/sead_superset_model.yml --format html

# Excel for gap-analysis workshops
python scripts/generate_target_model_docs.py resources/target_models/sead_superset_model.yml --format excel

# SIMS entity register for Authority Service docs
python scripts/generate_target_model_docs.py resources/target_models/sead_superset_model.yml --format sims

# Custom output directory
python scripts/generate_target_model_docs.py my_model.yml --format all --output-dir /tmp/model-docs
```

Output files are written to `docs/generated/` by default. Run `python scripts/generate_target_model_docs.py --help` for the full option reference, format descriptions, and badge/relationship-arrow glossary.

---

## Related Documentation

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — full project YAML reference, including the `metadata.target_model` field
- [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md) — generated field-by-field schema reference derived from the Pydantic models
- [USER_GUIDE.md](USER_GUIDE.md) — editor UI guide, including the Check Conformance button and Conformance panel
- [docs/proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md) — closed consolidation record for the delivered conformance backlog and deferred follow-up
