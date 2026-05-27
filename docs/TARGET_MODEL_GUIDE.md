# Target Model Specification Guide

## Overview

A **target model specification** is a YAML file that describes what an external destination system — such as the SEAD Clearinghouse — expects from a Shape Shifter project. It defines which entities are required, what columns and foreign-key relationships they must have, and what naming conventions apply.

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

### Top-Level Structure

```yaml
model:
  name: string          # Human-readable model name (required)
  version: string       # Semantic version, e.g. "2.0.0" (required)
  description: string   # Optional description

entities:               # Map of entity name → entity spec
  <entity_name>:
    ...

naming:                 # Optional naming convention rules
  public_id_suffix: string

constraints:            # Optional global constraint list
  - type: string
```

---

### `model` Block

```yaml
model:
  name: "SEAD Clearinghouse"
  version: "2.0.0"
  description: "SEAD archaeological research data model"
```

| Field         | Required | Description                                       |
|---------------|----------|---------------------------------------------------|
| `name`        | Yes      | Display name of the target system                 |
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

The `role` field describes the meaning of an entity in the target model. Roles are informational in v1 and help humans understand the model; future validators will use them for advanced semantic checks.

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
    nullable: true
```

| Field      | Required | Description                                                                                          |
|------------|----------|------------------------------------------------------------------------------------------------------|
| `required` | No       | `true` means the project entity must expose this column                                              |
| `type`     | No       | Hint type such as `string`, `integer`, `decimal`, `boolean`, or `date` (informational in v1)       |
| `nullable` | No       | Whether the column is expected to allow null values (informational)                                  |
| `description` | No    | Human-readable note for reviewers, generated docs, and editor help                                   |

Shape Shifter counts a column as present in a project entity when it appears as:
- an explicit entry in `columns` or `keys`
- an entry in `extra_columns`
- the `public_id` value
- a column contributed by a foreign key (parent's `public_id`)
- a column that survives an `unnest` transformation (`id_vars`, `var_name`, `value_name`)

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
  - type: no_circular_dependencies
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Global rule name applied to the whole target model |

Current constraints are modeled as simple typed entries. Add new constraint-specific keys only after extending the Pydantic schema.

Global constraints are planned for future validation phases. `no_orphan_facts` is declared in the SEAD spec but not yet enforced by the conformance engine. It records the intended rule that every fact entity must be reachable from at least one required lookup.

---

## Conformance Validation

### How It Works

When you click **Check Conformance** in the editor, Shape Shifter:

1. Loads the project and resolves the `target_model` reference (expanding `@include:` if needed).
2. Parses the target model spec into a `TargetModel` domain object.
3. Runs the target-model spec validator to check self-consistency, including unknown FK targets, invalid aggregate-parent relationships, and invalid identity-tracking or reconciliation combinations.
4. Runs the built-in conformance validators against the resolved project.
5. Returns a list of `ConformanceIssue` objects, each including a code, message, affected entity and field, and a suggestion.

Conformance results appear in their own **Conformance** panel in the Validate tab, separate from structural and data validation results.

### Issue Codes

| Code                                  | Severity | What It Means                                                                          |
|---------------------------------------|----------|----------------------------------------------------------------------------------------|
| `MISSING_REQUIRED_ENTITY`             | error    | An entity marked `required: true` in the target model is absent from the project       |
| `MISSING_PUBLIC_ID`                   | error    | The target model declares a `public_id` for an entity, but the project entity has none |
| `UNEXPECTED_PUBLIC_ID`                | warning  | The project entity has a `public_id` that the target model does not expect             |
| `MISSING_REQUIRED_FOREIGN_KEY_TARGET` | error    | A required FK target is not declared on the project entity                             |
| `MISSING_REQUIRED_COLUMN`             | error    | A required column is not present in the project entity's target-facing columns         |
| `PUBLIC_ID_NAMING_VIOLATION`          | warning  | A `public_id` value does not end with the `naming.public_id_suffix`                    |

### Validators

Five validators run in sequence. All are enabled by default; there is no per-project override mechanism in v1.

| Validator key       | What it checks                                                                                    |
|---------------------|---------------------------------------------------------------------------------------------------|
| `required_entity`   | Checks that every entity with `required: true` exists in the project                              |
| `public_id`         | Checks that each project entity has (or doesn't have) the `public_id` declared in the target spec |
| `foreign_key`       | Checks that each required FK target is declared on the project entity                             |
| `required_columns`  | Checks that each required column is in the project entity's target-facing column set              |
| `naming_convention` | Checks that all `public_id` values end with `naming.public_id_suffix`                             |

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
  --entities location,site,sample \
  --output minimal.yml
```

The generated scaffold has the correct identity fields and foreign keys pre-filled; you only need to add source configuration (`type`, `source`, `data_source`, etc.) for each entity.

---

## Writing a Custom Target Model

### Minimal Example

```yaml
model:
  name: "My Museum System"
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
- The `type` and `nullable` column fields are informational in v1 — they are recorded in the spec but not enforced by the conformance validators.
- Use `domains` tags to group entities so you can generate partial project scaffolds.

---

## SEAD Superset Spec (`sead_superset_model.yml`)

The bundled SEAD superset spec at `resources/target_models/sead_superset_model.yml` currently covers 51 entities. It is intended to be the near-complete shared SEAD model from which individual Shape Shifter projects can select curated subsets.

| Domain       | Entities                                                                                                                                                                |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `core` | Core context entities such as `location`, `site`, `sample_group`, `sample`, `method`, `dataset`, `analysis_entity`, and provenance lookups |
| `spatial` | Spatial context and coordinate-related entities such as `location`, `site_location`, `dimension`, and site or sample-group spatial extensions |
| `sample-metadata` | Sample descriptions, notes, dimensions, and other sample-attached metadata entities |
| `abundance` | Abundance observations, abundance property entities, and related classifiers |
| `taxonomy` | Taxonomy entities such as `taxa_tree_master`, `taxa_common_names`, and taxonomy support lookups |
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
- [USER_GUIDE.md](USER_GUIDE.md) — editor UI guide, including the Check Conformance button and Conformance panel
- [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md) — deferred and future work backlog
