# Target Model Specification Guide

## Overview

A **target model specification** is a YAML file that describes what an external destination system — such as the SEAD Clearinghouse — expects from a Shape Shifter project. It defines which entities are required, what columns and foreign-key relationships they must have, and what naming conventions apply.

When a project references a target model, Shape Shifter can perform **conformance validation**: checking whether the project entities actually satisfy the requirements described in the spec. This catches semantic modeling errors at configuration time, before you run the pipeline or attempt a dispatch.

Target model specs are optional. Existing projects without a `target_model` reference continue to work without any changes.

---

## Quick Start

1. Pick or create a spec file — e.g., `resources/target_models/sead_standard_model.yml` (the SEAD Clearinghouse spec ships with Shape Shifter).
2. Add a `target_model` reference to your project's `metadata` section:

```yaml
metadata:
  type: 'shapeshifter-project'
  name: "Dendrochronology Import"
  target_model: "@include: resources/target_models/sead_standard_model.yml"
```

3. Open your project in the editor, go to the **Validate** tab, and click **Check Conformance**.
4. Review any issues in the **Conformance** expansion panel.

---

## File Location

The built-in SEAD spec lives at `resources/target_models/sead_standard_model.yml`. Custom or project-specific specs can live anywhere; reference them with a path relative to the project file or an absolute path.

Recommended layout for project-specific specs:

```
target_models/
  specs/
    sead_standard_model.yml           ← bundled SEAD clearinghouse spec
    my_museum.yml         ← custom target model
```

---

## Referencing a Target Model from a Project

Use the `metadata.target_model` field. The value may be either a file reference or an inline definition.

**File reference (recommended):**
```yaml
metadata:
  type: 'shapeshifter-project'
  target_model: "@include: resources/target_models/sead_standard_model.yml"
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

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name of the target system |
| `version` | Yes | Version of *this spec file* (semantic versioning) |
| `description` | No | Free-text description shown in tooling |

---

### `entities` Block

Each key is an entity name that must match the project entity name. Each value is an **entity spec**.

```yaml
entities:
  location:
    role: lookup
    required: true
    description: "Geographic location"
    domains: [core, spatial]
    target_table: tbl_locations
    public_id: location_id
    identity_columns: [location_type_id, location_name]
    columns:
      location_name:
        required: true
        type: string
        nullable: false
    unique_sets:
      - [location_type_id, location_name]
    foreign_keys:
      - entity: location_type
        required: true
```

#### Entity Spec Fields

| Field | Required | Description |
|-------|----------|-------------|
| `role` | No | Semantic role: `fact`, `lookup`, `classifier`, or `bridge` |
| `required` | No | `true` means the project must include this entity (default: `false`) |
| `description` | No | Human-readable description for tooling and documentation |
| `domains` | No | List of domain tags; used to filter entities when generating project templates |
| `target_table` | No | Physical table name in the target system (informational, e.g. `tbl_sites`) |
| `public_id` | No | Expected `public_id` value in the project entity |
| `identity_columns` | No | Columns that form the natural key in the target system |
| `columns` | No | Map of column name → column spec; conformance checks these against the project |
| `unique_sets` | No | List of unique-set column groups |
| `foreign_keys` | No | List of foreign key specs |

---

### Semantic Roles

The `role` field describes the meaning of an entity in the target model. Roles are informational in v1 and help humans understand the model; future validators will use them for advanced semantic checks.

| Role | Meaning |
|------|---------|
| `fact` | A primary observational or transactional record (e.g., a sample, an analysis result). Usually depends on surrounding lookups and classifiers. |
| `lookup` | Reference data providing stable parent context (e.g., locations, sites, methods). Commonly referenced by many facts. |
| `classifier` | A controlled vocabulary or typology entity (e.g., site types, sample types). Best loaded from `fixed` or `sql` sources. |
| `bridge` | An association entity connecting two or more entities in a many-to-many relationship. |

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

| Field | Required | Description |
|-------|----------|-------------|
| `required` | No | `true` means the project entity must expose this column |
| `type` | No | Hint type: `string`, `integer`, `decimal`, `boolean` (informational; no hard type enforcement in v1) |
| `nullable` | No | Whether the column is expected to allow null values (informational) |

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
  - entity: site_type
    required: false
```

| Field | Required | Description |
|-------|----------|-------------|
| `entity` | Yes | Name of the target entity this FK must point to |
| `required` | No | `true` means the project entity must declare a FK to this entity (default: `false`) |

Conformance checks whether the project entity has at least one foreign key whose target matches the required entity name.

---

### `naming` Block

```yaml
naming:
  public_id_suffix: "_id"
```

| Field | Description |
|-------|-------------|
| `public_id_suffix` | Every `public_id` value in project entities must end with this string. The SEAD standard is `"_id"`. |

---

### `constraints` Block

```yaml
constraints:
  - type: no_orphan_facts
```

Global constraints are planned for future validation phases. `no_orphan_facts` is declared in the SEAD spec but not yet enforced by the conformance engine. It records the *intent* that every fact entity must be reachable from at least one required lookup.

---

## Conformance Validation

### How It Works

When you click **Check Conformance** in the editor, Shape Shifter:

1. Loads the project and resolves the `target_model` reference (expanding `@include:` if needed).
2. Parses the target model spec into a `TargetModel` domain object.
3. Runs the five built-in conformance validators against the resolved project.
4. Returns a list of `ConformanceIssue` objects, each including a code, message, affected entity and field, and a suggestion.

Conformance results appear in their own **Conformance** panel in the Validate tab, separate from structural and data validation results.

### Issue Codes

| Code | Severity | What It Means |
|------|----------|---------------|
| `MISSING_REQUIRED_ENTITY` | error | An entity marked `required: true` in the target model is absent from the project |
| `MISSING_PUBLIC_ID` | error | The target model declares a `public_id` for an entity, but the project entity has none |
| `UNEXPECTED_PUBLIC_ID` | warning | The project entity has a `public_id` that the target model does not expect |
| `MISSING_REQUIRED_FOREIGN_KEY_TARGET` | error | A required FK target is not declared on the project entity |
| `MISSING_REQUIRED_COLUMN` | error | A required column is not present in the project entity's target-facing columns |
| `PUBLIC_ID_NAMING_VIOLATION` | warning | A `public_id` value does not end with the `naming.public_id_suffix` |

### Validators

Five validators run in sequence. All are enabled by default; there is no per-project override mechanism in v1.

| Validator key | What it checks |
|---------------|---------------|
| `required_entity` | Checks that every entity with `required: true` exists in the project |
| `public_id` | Checks that each project entity has (or doesn't have) the `public_id` declared in the target spec |
| `foreign_key` | Checks that each required FK target is declared on the project entity |
| `required_columns` | Checks that each required column is in the project entity's target-facing column set |
| `naming_convention` | Checks that all `public_id` values end with `naming.public_id_suffix` |

### Checking Conformance Without the UI

The conformance engine can also be used from the CLI for quick checks:

```bash
python -m src.target_model.conformance \
  --spec resources/target_models/sead_standard_model.yml \
  --project data/projects/my_project/shapeshifter.yml
```

---

## Generating a Project Scaffold from a Target Model

The template generator creates a starter project YAML pre-populated with the entities and columns defined in a target model spec:

```bash
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_standard_model.yml \
  --output my_project_scaffold.yml

# Filter to a specific domain
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_standard_model.yml \
  --domain core \
  --output core_entities.yml

# Include only specific entities
python -m src.target_model.template_generator \
  --spec resources/target_models/sead_standard_model.yml \
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

## SEAD Clearinghouse Spec (`sead_standard_model.yml`)

The bundled SEAD spec at `resources/target_models/sead_standard_model.yml` currently covers 35 entities organized across these domains:

| Domain | Entities |
|--------|----------|
| `core` | location, location_type, site, site_type, site_type_group, sample_group, sample, sample_type, method, dataset, master_dataset, project, citation |
| `spatial` | location, location_type, site, site_type |
| `analysis` | dataset, analysis_entity, abundance, abundance_element, abundance_element_group, abundance_modification, modification_type, abundance_property, abundance_element_group |
| `taxa` | taxa_tree_master, taxa_common_names |
| `dating` | relative_ages, relative_dating, geochronology, dating_lab |
| `method` | method, method_group |
| `contact` | contact, contact_type, dataset_contact |
| `excavation` | feature_type, feature, sample_feature |

The SEAD spec uses `naming.public_id_suffix: "_id"` and declares `constraints: [{type: no_orphan_facts}]`.

---

## Related Documentation

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — full project YAML reference, including the `metadata.target_model` field
- [USER_GUIDE.md](USER_GUIDE.md) — editor UI guide, including the Check Conformance button and Conformance panel
- [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md) — deferred and future work backlog
