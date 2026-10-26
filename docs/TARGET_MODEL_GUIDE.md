# Target Model Specification Guide

## Overview

A **target model specification** is a YAML file that describes what a destination system, such as the SEAD Clearinghouse, expects a Shape Shifter project to provide. It lists the kinds of records (entities) a project may or must include, their columns, how they link to one another, and any naming rules.

The accepted fields and values are defined by the Pydantic models in `src/target_model/models.py`. Use this guide for an overview and [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md) for the complete field-by-field reference, including defaults.

When a project refers to a target model, Shape Shifter can check whether the project's entity definitions include the required record types, fields, and links. This is called **conformance validation**. It can catch configuration problems before the project processes or sends data.

Target models are optional. Projects without a `target_model` reference continue to work as before.

---

## Quick Start

1. Choose a target model file or create one. Shape Shifter includes `resources/target_models/sead_standard_model.yml` as a starting point.
2. In your project YAML, add a `target_model` entry under `metadata`:

```yaml
metadata:
  type: 'shapeshifter-project'
  name: "Dendrochronology Import"
  target_model: "@load: resources/target_models/sead_standard_model.yml"
```

3. Open the project in the editor. On the **Validate** tab, select **Check Conformance**.
4. Open the **Conformance** panel to see any issues.

---

## File Location

The bundled SEAD model is at `resources/target_models/sead_standard_model.yml`. You can store custom models elsewhere. Refer to them with a path relative to the project file or with the full file path.

Recommended layout for project-specific specs:

```
target_models/
  specs/
    sead_standard_model.yml           ← bundled SEAD superset spec
    my_museum.yml         ← custom target model
```

---

## Referencing a Target Model from a Project

Use the `metadata.target_model` field. The value may be either a file reference or an inline definition.

**File reference (recommended):**
```yaml
metadata:
  type: 'shapeshifter-project'
  target_model: "@load: resources/target_models/sead_standard_model.yml"
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

The project workspace's Metadata Editor shows a **Target Model** dropdown with uploaded YAML files in `@load:` format. You can also enter a path directly.

---

## Target Model File Format

Shape Shifter checks each target model file against a defined schema. It reports unknown fields instead of silently ignoring them.

For the full generated reference of accepted sections, keys, defaults, and enum values, see [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md).

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

Each key is an entity name and must match an entity in the project. The value is an **entity spec**: the requirements for that entity.

```yaml
entities:
  site:
    role: lookup
    required: true
    description: "Archaeological site"
    domains: [core, spatial]
    target_table: tbl_sites
    public_id: site_id
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

| Field                    | Required | Default | Description                                                                                                       |
|--------------------------|----------|---------|-------------------------------------------------------------------------------------------------------------------|
| `role`                   | No       | `null`  | Semantic role: `fact`, `lookup`, `classifier`, or `bridge`.                                                       |
| `required`               | No       | `false` | `true` means the project must include this entity.                                                                |
| `description`            | No       | `null`  | Human-readable description for tooling and documentation.                                                         |
| `domains`                | No       | `[]`    | Domain tags used to filter entities when generating project templates.                                            |
| `target_table`           | No       | `null`  | Physical table name in the target system (informational, e.g. `tbl_sites`).                                       |
| `public_id`              | No       | `null`  | Expected `public_id` value in the project entity.                                                                 |
| `public_id_generation`   | No       | `null`  | `database_sequence` reserves an ID from the target database for an explicitly non-tracked entity.                 |
| `synchronize_sequence_after_insert` | No       | `false` | Advance the target column's PostgreSQL sequence after inserting rows with SIMS-assigned IDs.                      |
| `columns`                | No       | `{}`    | Map of column name to column spec; conformance checks these against the project.                                  |
| `unique_sets`            | No       | `[]`    | Groups of columns declared unique for the target entity; each group is a separate uniqueness rule.               |
| `foreign_keys`           | No       | `[]`    | List of foreign-key specs.                                                                                        |
| `identity_tracking`      | No       | `null`  | Identity mode. When omitted, its effective value can be inferred from `role` or `aggregate_parent`.               |
| `reconciliation`         | No       | `null`  | Matching or allocation mode. When omitted, its effective value can be inferred from identity settings and `role`. |
| `aggregate_parent`       | No       | `null`  | Immediate parent entity name (the entity this one points to with a foreign key) when this entity inherits aggregate identity.                                                   |

The `Default` column shows what the schema uses when a field is omitted. The ingester may infer effective values for `identity_tracking` and `reconciliation` from `role` and `aggregate_parent`; see [Identity And Reconciliation Fields](#identity-and-reconciliation-fields). The target model's `unique_sets` declares target-side column groups that are expected to be unique. This is separate from a project's `keys`, which describe source-side business keys. A unique set does not direct SIMS or the ingester to match source records. A database sequence is an automatic counter that issues IDs. SIMS is the SEAD Identity Management System.

---

### Semantic Roles

The `role` field says what an entity represents. If identity settings are omitted, the SEAD Change Request Ingester uses the role to choose defaults. Any explicit `identity_tracking`, `reconciliation`, or `aggregate_parent` value takes precedence.

| Role         | Meaning                                                                                                                                       |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `fact`       | A record that captures an observation, measurement, or event (for example, a sample or analysis result). Often linked to lookups or classifiers. |
| `lookup`     | A reference entity whose records provide reusable domain or contextual information to other entities (e.g., sites, locations, or methods). Records may be curated and controlled. |
| `classifier` | A reference entity whose records provide categories used to classify other entities (e.g., site types or sample types), often as a controlled vocabulary.                     |
| `bridge`     | An association entity connecting two or more entities in a many-to-many relationship.                                                         |

All four roles describe entities. They differ in what their records represent and how other entities use them. Controlledness alone does not determine the role: site records can be curated and still be lookups because they represent places; site types are classifiers because they categorize sites. If identity settings are omitted, the ingester defaults lookups to `reconcile-exact` (which may assign a new ID when no exact match is found) and classifiers to `lookup-only` (which uses existing matches only). Set `reconciliation` explicitly if that default does not match the target's policy.

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
| `required` | No       | If `true`, the project entity must provide this column.                                               |
| `type`     | No       | A hint such as `string`, `integer`, `decimal`, `boolean`, or `date`; not checked in v1.                |
| `nullable` | No       | Whether the destination column may contain `null` (no value); not checked in v1.                      |
| `description` | No    | Note shown to reviewers and in generated documentation or editor help.                               |

Each group in `unique_sets` is a separate target-side uniqueness declaration. A group can contain one column, including a UUID column, or several columns. The structural validator checks that each listed column is declared. Membership in `unique_sets` does not set the column's `required` flag. The Change Request Ingester uses complete, non-null groups for bridge collision checks; the target-model validator does not prove that values are unique in the database or use these groups to match provider records. The `required` setting controls whether a project must declare a column, while `nullable` describes whether the target column may contain null.

Shape Shifter treats a column as present if the project defines it directly or a relationship or transformation adds it. For example, a column is present when it appears as:
- an explicit entry in `columns` or `keys`
- an entry in `extra_columns`
- the `public_id` value
  - a column added by a foreign key (the related entity's `public_id`)
  - a column kept or created by an `unnest` transformation (`id_vars`, `var_name`, or `value_name`)

---

### Foreign Key Specs

A foreign key (FK) is a link from one entity to another.

```yaml
foreign_keys:
  - entity: location
    required: true
    via: site_location
  - entity: site_type
    required: false
```

| Field           | Required | Description                                                                             |
|-----------------|----------|-----------------------------------------------------------------------------------------|
| `entity`        | Yes      | Name of the entity this link points to                                                   |
| `required`      | No       | If `true`, the project must declare this link (default: `false`).                        |
| `via`           | No       | Bridge entity used for a many-to-many link, such as `site -> site_location -> location`. |
| `required_when` | No       | Requires this link only after reconciliation selects rows for insertion; see below.      |

Conformance checks that the project entity declares a link to each required target entity.

When `via` is present, conformance checks both parts of the path: the source entity must link to the bridge, and the bridge must link to the final target.

#### Conditional Foreign Keys

Use `required_when` when a link is needed only if the source entity receives new rows:

```yaml
entities:
  location:
    columns:
      location_type_id:
        type: integer
        nullable: false
    foreign_keys:
      - entity: location_type
        required_when:
          has_new_rows: location
  location_type:
    required: false
    public_id: location_type_id
```

`has_new_rows` must name the entity that declares the foreign key. The condition becomes true only when the final reconciliation result selects at least one row of that entity for insertion. Rows matched to existing records, rows accepted as updates, and blocked rows do not activate it. A submission whose locations all match existing locations therefore needs no `location_type_id` value, even when those rows looked new before reconciliation.

Project conformance cannot evaluate this rule, because it does not reconcile rows. It reports the rule as awaiting reconciliation instead of failing the project.

The SEAD Change Request Ingester evaluates the rule after reconciliation. When at least one row of the named entity is inserted:

- the project must contain the `location_type` entity and declare the link to it
- the FK column name comes from the target's `public_id`, so `location_type_id` above is `location_type.public_id`
- every inserted row needs a non-null `location_type_id` that resolves to a target ID; the ingester rejects the submission before it builds the change package

Because the column requirement applies only to inserted rows, omit unconditional `required: true` on both the lookup entity and the FK column when you use this rule. Keep `nullable: false` on the column to describe the destination constraint, and set the lookup entity to `required: false`; otherwise that entity stays required in every conforming project.

A conditional FK must be a direct link: it cannot also declare `required`, and it cannot use `via`.

#### Inserted-Row Link Errors

When the condition is active, each inserted row's link value must be translated before the row reaches the change request: the source value is replaced by the target system's ID for the record it points to. The messages call this translation *projection*.

Projection needs three things. Each missing one produces a different message.

| Need | Where it comes from |
|------|---------------------|
| A column to hold the target ID | The linked entity's `public_id` |
| The linked rows, present in the same submission | The linked entity's normalized table |
| A key that joins the two sides | The submission's own row numbering (`system_id`) |

The messages below use a `location` row that links to `location_type` through `location_type_id`.

| Message | Meaning | Where to look |
|---------|---------|---------------|
| `Entity 'location' cannot project conditional foreign key to 'location_type' because the target public_id is undefined` | The target model does not name the column that holds the location type ID, so there is no place to write the value. | The `location_type` entity is missing from the target model, or it declares no `public_id`. |
| `Entity 'location' is missing conditional FK column 'location_type_id' for 'location_type'` | The location rows have no `location_type_id` column. | The project does not link `location` to `location_type`, so the column is never produced. |
| `Entity 'location' has 1 missing conditional FK value(s) for 'location_type_id'` | A new location row has an empty link value. | A cell in the source data is blank. |
| `Entity 'location' cannot project conditional foreign key 'location_type_id' because resolved table 'location_type' is missing` | Location type rows were not part of this submission, so there is nothing to translate the values against. | The linked entity's table is absent from the submitted bundle. |
| `Entity 'location' cannot project conditional foreign key 'location_type_id' because resolved table 'location_type' has no system_id column` | The location type rows carry no row numbering, so they cannot be joined to the locations that point at them. | The linked table was not produced with Shape Shifter's row identity column. |
| `Entity 'location' has 1 unresolved conditional FK value(s) for 'location_type_id'` | A location points at a location type that is not among the submitted location type rows. | The value does not match any linked row, or the linked row is missing from the submission. |

These messages appear only while the condition is active. A submission whose locations all match existing records inserts nothing, so it receives none of them, even when the location type data is absent or incomplete.

An FK declared with `required: true` produces the same family of messages, with `required` in place of `conditional`. The difference is reach: `required` checks every row submitted for the entity, before reconciliation decides its outcome, while the conditional form checks only the rows that will be inserted. That difference is why the conditional rule is preferred when link values are needed only for new rows.

---

### Identity And Reconciliation Fields

These fields describe how records are identified: whether the ingester should match an existing record, assign a new ID, or use an ID inherited from a parent. SIMS performs identity operations according to its own entity configuration; the target model does not configure SIMS directly.

The SEAD Change Request Ingester uses the resolved `identity_tracking`, `reconciliation`, and `aggregate_parent` values to plan this work. Before it creates the change package, it checks whether SIMS supports the needed operations.

#### Pointing `aggregate_parent` At The Immediate Parent

`aggregate_parent` names the entity's **immediate** parent, that is, the entity it declares a foreign key to. It does not name the aggregate root.

The aggregate root is found by following the `aggregate_parent` links from child to parent until an entity with effective `identity_tracking: tracked` is reached. A tracked root does not set `aggregate_parent` itself.

For example, `analysis_boolean_value` sets `aggregate_parent: analysis_value`, and `analysis_value` sets `aggregate_parent: analysis_entity` (a tracked root). If `aggregate_parent` named the root directly, `analysis_boolean_value` would point at `analysis_entity` and the intermediate link through `analysis_value` would be lost.

To set the field: use the entity this entity's foreign key points to, and leave `aggregate_parent` unset on the tracked root. Validation reports `MISSING_AGGREGATE_PARENT_FOREIGN_KEY` when the named parent is not also a declared foreign-key target.

When it loads a target model, Shape Shifter checks that these settings work together:

- If omitted, a `fact` entity defaults to `identity_tracking: tracked` and `reconciliation: allocate`.
- `aggregate_parent` must name another entity in the same model.
- An entity with `aggregate_parent` must also declare a foreign key to that parent; this is what makes the named entity its immediate parent.
- `identity_tracking: child` requires an `aggregate_parent`.
- A `tracked` entity uses `reconciliation: allocate`.
- `public_id_generation: database_sequence` requires an explicit, non-tracked `identity_tracking` value. SIMS assigns IDs to tracked entities.
- A `derived` entity uses `reconciliation: derive`.
- A `child` entity must not declare a reconciliation strategy.
- A `reconciled` entity must use `reconcile-exact`, `reconcile-fuzzy`, `lookup-only`, or `lookup-extensible`.

| Field | Allowed values | Description |
|-------|----------------|-------------|
| `identity_tracking` | `tracked`, `reconciled`, `derived`, `child` | Says whether the entity gets its own tracked identity, is matched using business fields, takes an ID from related records, or inherits its parent's identity. |
| `reconciliation` | `allocate`, `reconcile-exact`, `reconcile-fuzzy`, `lookup-only`, `lookup-extensible`, `derive` | Says how incoming records are matched or how new IDs are assigned. |
| `aggregate_parent` | Entity name | Names the immediate parent entity (the entity this one has a foreign key to) whose identity this entity inherits. Follow the `aggregate_parent` links to reach the tracked root. |
| `public_id_generation` | `database_sequence` | Gets an ID from the target database when `identity_tracking` is explicitly set to a non-tracked value. |

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

Constraints are named rules that apply to the whole target model. To add new settings for a constraint, first add them to the Pydantic schema.

When a target model declares `no_orphan_facts`, conformance checks that each fact entity in the project is linked, through foreign keys, to at least one lookup or classifier.

---

## Conformance Validation

### How It Works

When you select **Check Conformance** in the editor, Shape Shifter:

1. Loads the project and opens the referenced target model file, including when the reference uses `@load:`.
2. Reads the target model into the format used for checks.
3. Checks the model for mistakes, such as links to unknown entities or incompatible identity settings.
4. Checks the project against the target model's requirements.
5. Reports each issue with a code, an explanation, the affected entity and field, and a suggested fix.

Results appear in the **Conformance** panel on the **Validate** tab, separately from checks of project structure and data.

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

Five validators run in order. All run by default; version 1 does not let a project turn them off individually.

| Validator key       | What it checks                                                                                    |
|---------------------|---------------------------------------------------------------------------------------------------|
| `required_entity`   | Checks that the project includes every entity marked `required: true` in the target model.         |
| `public_id`         | Checks whether project entities have the expected `public_id` values and flags unexpected ones.   |
| `foreign_key`       | Checks that the project declares every required link to another entity.                            |
| `required_columns`  | Checks that the project entity provides every required column.                                     |
| `naming_convention` | Checks that each `public_id` ends with the configured `naming.public_id_suffix`.                   |

### Checking Conformance Without the UI

You can also check conformance from a terminal, without opening the editor:

```bash
python -m src.target_model.conformance \
  --spec resources/target_models/sead_standard_model.yml \
  --project data/projects/my_project/shapeshifter.yml
```

## Change Request Ingester MVP Field Usage

The SEAD Change Request Ingester uses some target-model fields to decide how to match records, assign IDs, link related records, check for duplicates, and build change-request files. Other Shape Shifter tools, such as conformance checks and project scaffold generation, may use fields differently.

| Field(s)                                                        | Effect in Change Request Ingester MVP                                                                                                                                                  |
|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `identity_tracking`<br>`reconciliation`<br>`aggregate_parent`   | Drive identity planning and SIMS capability checks.                                                                                                                                    |
| `role`                                                          | Supplies defaults when explicit identity settings are absent.                                                                                                                          |
| `public_id_generation`<br>`target_table`<br>`public_id`         | Affect target ID reservation, key projection, collision checks, and emitted SQL.                                                                                                       |
| `foreign_keys`                                                  | Affect FK projection and required-FK checks. A `required_when` link is checked after reconciliation against inserted rows only. The ingester does not directly read `via`; bridge entities are handled as their own entities. |
| `columns.required`<br>`columns.nullable`<br>`columns.generated` | Required and nullable settings affect target-row checks; `generated` controls omission of generated values from inserts. Column `type` and `description` are not used by the ingester. |
| `unique_sets`                                                   | Support collision checks for derived/bridge rows.                                                                                                                                      |
| Entity-level `required`                                         | Affects conformance, not ingester planning.                                                                                                                                            |
| `description`<br>`domains`                                     | Have no direct ingester effect. `domains` can still affect generated project scaffolds.                                                                                                |

---

## Reviewing the SEAD Superset Model

Use this checklist to review `resources/target_models/sead_standard_model.yml` beyond the Change Request Ingester MVP. Focus on these questions and record unrelated concerns separately.

1. **Entity roles:** Check whether each `role` (`fact`, `lookup`, `classifier`, or `bridge`) fits what the entity represents and how it relates to other entities. Recommend a role and explain why. If identity settings are omitted, the role can affect the ingester's defaults; explicit settings take precedence.
2. **Tables not used by the MVP:** Check whether each table exists in the target database and whether current projects or import workflows use it. A table's absence from the MVP does not mean it is obsolete. Recommend keeping it optional, requiring it in conforming projects, or postponing/removing it, and explain why. `required: true` means every conforming project must include the entity; it does not describe whether a database column allows empty values.
3. **Required links:** For each `foreign_keys` entry, ask whether every conforming project must declare the link. Check the target entity and any `via` bridge path. Set `required: true` only when every valid project must have the link; use `false` when valid projects may omit it. Conformance checks the link declared in the project, not a database constraint. The ingester also checks that required link columns and values are present in output rows.

For each recommendation, record the entity or table, its current and proposed settings, the reason or source, and any open domain question. Mark uncertain points as questions instead of guessing from names. Do not change the model until the decision is recorded.

## Generating a Project Scaffold from a Target Model

The template generator creates a starter project YAML file with the entities and columns listed in a target model:

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

The generated file includes the identity fields and foreign keys from the target model. Add the source settings (`type`, `source`, `data_source`, and others) for each entity.

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

- Start with only the entities and columns you need to check. An entity may be absent from the project without causing an error unless the target model marks it `required: true`.
- Use `required: false` (or omit `required`) for optional/conditional entities that only appear in some project shapes.
- Set a column's `required: true` only when the project must provide it.
- In version 1, conformance records the column's `type` and `nullable` settings but does not check them.
- Use `domains` tags to group entities so you can generate partial project scaffolds.

---

## SEAD Superset Spec (`sead_standard_model.yml`)

The bundled SEAD superset model at `resources/target_models/sead_standard_model.yml` currently defines 102 entities. It aims to cover nearly all shared SEAD tables; each Shape Shifter project can select the subset it needs.

Coverage is incomplete. In the filtered snapshot of the live database, 136 tables are in scope and 42 do not yet have a matching target-model entity. Work to decide and verify coverage is tracked in [Define And Verify The SEAD Target Model Coverage Boundary](proposals/SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md) and [#532](https://github.com/humlab-sead/sead_shape_shifter/issues/532).

| Domain       | Entities                                                                                                                                                                |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `core` | Shared context such as locations, sites, sample groups, samples, methods, datasets, analysis entities, and provenance lookups |
| `analysis` | Analysis results and related value types, notes, identifiers, categories, numbers, ranges, taxon counts, and dimensions linked to analysis entities |
| `spatial` | Locations, site-location links, dimensions, site properties, grid references, and coordinates for sites, samples, and sample groups |
| `sample-metadata` | Descriptions and related details for samples and sample groups, such as sampling context, horizons, notes, colours, dimensions, qualifiers, and references |
| `abundance` | Abundance records, shared property types, and related categories |
| `taxonomy` | Taxonomy records and related common names, synonyms, measured attributes, Red Data Book entries, and supporting tables |
| `dating` | Relative dating, chronology, dating labs, and uncertainty records |
| `provenance` | Projects, datasets, citations, contacts, and dataset-contact records |

The model uses `naming.public_id_suffix: "_id"`. It also enables `no_orphan_facts`, which checks that each fact entity in a project links to at least one lookup or classifier.

---

## Generating Documentation from a Target Model

Use `scripts/generate_target_model_docs.py` to create readable documentation from a target model YAML file. It supports four output formats:

| Format     | Best for                              | Output file   |
|------------|---------------------------------------|---------------|
| `html`     | Sharing or presenting the model       | `<stem>.html` |
| `excel`    | Reviewing the model or finding gaps   | `<stem>.xlsx` |
| `markdown` | Wikis and version-controlled guides   | `<stem>.md`   |
| `sims`     | Target-model reference for SIMS documentation; not a list of SIMS capabilities | `<stem>.sims.md` |

```bash
# Generate all formats (default)
python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml

# HTML only — recommended for sharing with archaeologists and data managers
python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format html

# Excel for gap-analysis workshops
python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format excel

# Target-model reference for Authority Service docs
python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format sims

# Custom output directory
python scripts/generate_target_model_docs.py my_model.yml --format all --output-dir /tmp/model-docs
```

Files are saved to `docs/generated/` by default. Run `python scripts/generate_target_model_docs.py --help` to see all options and format details.

---

## Related Documentation

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — full project YAML reference, including the `metadata.target_model` field
- [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md) — generated field-by-field schema reference derived from the Pydantic models
- [USER_GUIDE.md](USER_GUIDE.md) — editor UI guide, including the Check Conformance button and Conformance panel
- [docs/proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md) — closed consolidation record for the delivered conformance backlog and deferred follow-up
