# Proposal: Target Model Specification Format

## Status

- Proposed feature
- Scope: Specification format (YAML schema + semantics) and initial SEAD model definition
- Goal: Define a reusable, system-independent format for describing target data model requirements, and produce a concrete SEAD specification as the first consumer

## Summary

Define a declarative YAML format for describing the requirements, structure, and conventions of a target data model. The format is independent of Shape Shifter's processing pipeline — it describes *what a conforming dataset must look like*, not how data flows through the system.

The format and the first concrete specification (SEAD v2) should be developed iteratively in parallel: the format evolves as the SEAD model exposes gaps, and the SEAD model stress-tests the format against real requirements.

Other systems in the SEAD ecosystem (Clearinghouse validation, ingestion pipelines, documentation generators) can consume the same specification files.

## Problem

There is no machine-readable description of what the SEAD data model expects from incoming data. Constraints live in:

- PostgreSQL DDL files (165 tables, FK constraints, column types)
- Tribal knowledge about which entities are lookups vs facts
- Naming conventions that exist only in developers' heads
- Implicit assumptions baked into individual Shape Shifter project files

This means:

1. **Every project re-encodes target knowledge.** Two SEAD projects will independently define the same FK patterns, column expectations, and entity roles. Mistakes in one project don't inform the other.
2. **Validation cannot reason about the target.** Shape Shifter validates YAML structure and topological consistency but cannot say "SEAD requires a location entity" or "this entity's public_id name is wrong for its role."
3. **Other tools cannot reuse the knowledge.** The Clearinghouse ingester, auto-reconciliation scripts, and documentation generators all need target model awareness but have no shared definition to consume.

## Scope

This proposal covers two deliverables developed in parallel:

1. **The format** — A YAML schema defining how to express target model requirements: entities, roles, columns, relationships, naming rules, and constraints.
2. **SEAD v2 specification** — A concrete file (`sead_v2.yml`) that describes the SEAD archaeological database using this format, covering the entities and patterns most commonly used in Shape Shifter projects. Until Shape Shifter integration is completed, the working version lives at `target_models/specs/sead_v2.yml`.

## Non-Goals

- Integration into the Shape Shifter validation pipeline (covered by the [TARGET_SCHEMA_AWARE_VALIDATION](TARGET_SCHEMA_AWARE_VALIDATION.md) proposal)
- A general-purpose schema DSL or type system
- Full coverage of all 165 SEAD tables in v1 (start with the ~30 most commonly mapped)
- Runtime enforcement or processing behavior changes
- Replacing PostgreSQL DDL as the canonical schema definition

## Proposed Format

### Design Principles

1. **Declarative, not procedural.** The spec says "entity X must have column Y" — not how to check it.
2. **Optional and additive.** Every field beyond `name` and `version` is optional. A minimal spec is still useful.
3. **Target-system-agnostic.** The format works for SEAD, museum databases, or any relational target. No SEAD-specific keywords.
4. **Derivable from existing artifacts.** Entity specs should be producible from DDL + domain knowledge, not invented from scratch.
5. **Consumed by multiple tools.** The same file should be usable by validators, template generators, documentation tools, and ingestion pipelines.

### Top-Level Structure

```yaml
# target_models/specs/sead_v2.yml
model:
  name: "SEAD Clearinghouse"
  version: "2.0.0"
  description: "SEAD archaeological research data model"

entities:
  location:
    role: lookup
    required: true
    # ...per-entity spec

naming:
  public_id_suffix: "_id"

constraints:
  - type: no_orphan_facts
```

Three top-level keys: `model` (metadata), `entities` (per-entity specs), and optionally `naming` and `constraints` (global rules).

### Model Metadata

```yaml
model:
  name: string            # Human-readable model name
  version: string         # Semver string
  description: string     # Optional
```

Version is informational in v1. Future work may add compatibility checks.

### Entity Specification

Each key under `entities` is an entity name. The spec describes what a conforming entity must look like.

At a high level, a target-model specification should express facts such as:

1. this entity must exist
2. it should have this `public_id`
3. it needs these columns
4. it must reference these other entities
5. it plays this semantic role
6. it may map to this target table
7. it may belong to one or more semantic domains or profiles
8. it may define canonical identity columns for matching and documentation
9. it may define nullability and uniqueness expectations that matter to conforming data
10. it may participate in global naming and constraint rules

```yaml
entities:
  location:
    role: lookup                          # Semantic role
    required: true                        # Must be present in conforming projects
    description: "Geographic location"    # Human-readable, for docs/templates
    domains: [core, spatial]              # Optional domain/profile tags
    target_table: tbl_locations           # Corresponding target DB table
    public_id: location_id               # Expected public_id column name
    identity_columns:                     # Canonical columns that identify this entity
      - location_name
    columns:                              # Columns expected in a conforming dataset
      location_name:
        required: true
        type: string
        nullable: false
      location_type_id:
        required: true
        type: integer
        nullable: false
    unique_sets:                          # Candidate unique sets / alternative keys
      - [location_name]
    foreign_keys:                          # Required FK relationships
      - entity: location_type
        required: true
```

#### Field definitions

| Field                  | Type                                     | Default | Meaning                                          |
|------------------------|------------------------------------------|---------|--------------------------------------------------|
| `role`                 | `lookup \| fact \| classifier \| bridge` | `null`  | Semantic role in the target model                |
| `required`             | `bool`                                   | `false` | Must this entity exist in a conforming project?  |
| `description`          | `string`                                 | `null`  | Human-readable purpose description               |
| `domains`              | `list[string]`                           | `[]`    | Optional domain/profile tags for grouping        |
| `target_table`         | `string`                                 | `null`  | Corresponding table in target database           |
| `public_id`            | `string`                                 | `null`  | Expected `public_id` column name                 |
| `identity_columns`     | `list[string]`                           | `[]`    | Canonical columns used to identify this entity   |
| `columns`              | `dict[string, ColumnSpec]`               | `{}`    | Expected columns keyed by column name            |
| `unique_sets`          | `list[list[string]]`                     | `[]`    | Candidate unique sets / alternative keys         |
| `foreign_keys`         | `list[ForeignKeySpec]`                   | `[]`    | Required FK relationships                        |

#### Column Specification

`columns` is a mapping keyed by column name. This makes the spec easier to scan and keeps the identifier in the same position where `entities` already put it.

```yaml
columns:
  location_name: {}
  location_type_id: {}
```

When richer metadata is useful for validation, templates, or documentation, attach metadata under each column name:

```yaml
columns:
  location_name:
    required: true
    type: string
    nullable: false
    description: Human-readable location label
  location_type_id:
    required: true
    type: integer
    nullable: false
```

Supported `ColumnSpec` fields in v1:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `required` | `bool` | `false` | Must the column exist? |
| `type` | `string \| null` | `null` | Logical target type for validation and docs |
| `nullable` | `bool \| null` | `null` | If set, whether null values are acceptable |
| `description` | `string \| null` | `null` | Human-readable explanation |

Column order is not part of the format contract. YAML parsers commonly preserve mapping insertion order, so authors can still list columns in a preferred reading order, but validators and other consumers should treat `columns` as an unordered mapping.

In v1, this is intentionally minimal. The format needs to distinguish between the full expected column set and the subset that is strictly required, and it should be able to express target-level nullability where it matters.

It should also be able to express logical type constraints where they are important to conforming data. This is not meant to mirror PostgreSQL storage types exactly. The goal is to capture the target-level expectation that a column behaves like an `integer`, `string`, `boolean`, `date`, `datetime`, `decimal`, or `enum`, so validators, template generators, and documentation can reason about it consistently.

The type vocabulary should stay system-agnostic and relatively small in v1. If SEAD uses `integer` and PostgreSQL stores it as `int4`, the target-model spec should say `integer`. If a target system distinguishes more specialized categories later, those can be added deliberately rather than leaking DBMS-specific types into the format.

Examples:

```yaml
columns:
  dataset_id:
    required: true
    type: integer
    nullable: false
  dataset_name:
    required: true
    type: string
    nullable: false
  dating_uncertainty:
    type: decimal
    nullable: true
  method_group:
    type: enum
    nullable: false
```

For `enum`-like values, v1 can either rely on `domains` plus narrative documentation, or later grow a small `allowed_values` feature if a real validator or generator needs it. That should be a separate extension, not assumed by default.

#### Domain Tags

`domains` allows one target-model file to cover multiple subject areas without forcing every consumer to use the full model at once.

Examples:

```yaml
domains: [core]
domains: [dating]
domains: [abundance, taxonomy]
```

This supports partial coverage, profile-aware template generation, and progress tracking as the SEAD specification expands.

#### Identity Columns

`identity_columns` describes the canonical columns used to identify instances of an entity in a conforming dataset.

This is target-model metadata, not a direct instruction to mirror Shape Shifter's `keys` field exactly. It exists to express how the target entity is typically recognized across projects and by downstream consumers.

#### Unique Sets

`unique_sets` describes candidate unique sets or alternative keys that should be unique within a conforming dataset.

Examples:

```yaml
unique_sets:
  - [location_type]
  - [dataset_name, master_set_id]
```

This is useful target knowledge for validation, documentation, and template generation. It captures meaningful uniqueness rules without turning the format into a full dump of physical database indexes and constraint names.

#### Foreign Key Specification

```yaml
foreign_keys:
  - entity: location_type        # Target entity name
    required: bool               # Must this FK exist? (default: false)
```

This checks only *existence* of a FK to the named entity. It does not validate join columns — that's the project's concern (join strategies vary by data source).

Richer relationship semantics may be added later if a concrete validator or generator needs them, but v1 intentionally stops at existence and required-ness. Join keys, join modes, and operational cardinality remain Shape Shifter concerns rather than target-model concerns.

#### Role Semantics

Roles describe modeling intent (see [ENTITY_SEMANTIC_ROLES](ENTITY_SEMANTIC_ROLES.md) for detailed rationale):

- **`lookup`** — Reference entity with stable identity. Defines reusable domain values (locations, site types, methods). Expected to have `public_id` and `keys`. Referenced by many entities.
- **`fact`** — Observational or transactional entity. Records measurements, samples, events. Depends on lookups and parent entities. Usually sits lower in the dependency graph.
- **`classifier`** — Controlled vocabulary or typology. Curated value sets used for consistent classification and lookup behavior.
- **`bridge`** — Association entity connecting two or more entities in many-to-many relationships. Carries structural meaning rather than independent business meaning.

Role is optional. Omitting it means no role-based validation applies to that entity.

### Naming Conventions

```yaml
naming:
  public_id_suffix: "_id"             # All public_ids must end with this
```

Intentionally minimal in v1. The suffix rule catches the most common naming errors. Pattern-based rules (e.g., "lookup public_ids must match `^[a-z_]+_id$`") can be added later when real need emerges.

### Global Constraints

```yaml
constraints:
  - type: no_orphan_facts             # Facts must FK to at least one lookup
  - type: no_circular_dependencies    # Standard DAG requirement
```

Constraint types are an extensible enum. v1 ships with a small set of well-defined constraint types.

#### v1 Constraint Types

| Type | Meaning |
|---|---|
| `no_orphan_facts` | Every entity with `role: fact` must have at least one FK to a lookup/classifier |
| `no_circular_dependencies` | Entity dependency graph must be a DAG |

Additional constraint types (e.g., `all_lookups_before_facts`, `required_lookup_coverage`) can be added as new proposals or phases.

### What the Format Does NOT Express

- **Database-native storage types or sizes.** The format may say a column is `integer` or `date`, but not that it must be `varchar(100)`, `int4`, or another DBMS-specific physical type.
- **Database defaults and generated values.** Defaults such as sequences, timestamps, or server-side fallback values are usually persistence mechanics, not target-model semantics. If needed later, treat them as advisory metadata rather than normative validation rules.
- **Join strategies.** The format says "entity X must FK to entity Y," not which columns to join on. Join column choice depends on the data source.
- **Source mechanics.** The format does not say whether an entity should be loaded from `sql`, `fixed`, or file-backed inputs. That is project authoring strategy, not target-model semantics.
- **Processing order.** The format describes the target shape, not how to get there.
- **Cardinality constraints on data.** The format does not say "location must have at least 1 row." It describes schema structure, not data content.

## Developing Format and SEAD Spec in Parallel

The format and the SEAD specification should be iterated together:

### Iteration cycle

1. **Draft format** — Define the schema with enough structure to express basic SEAD patterns (entities, roles, required columns, FKs).
2. **Apply to SEAD** — Write specs for 5-10 core SEAD entities (location, site, sample, dataset, etc.) using the draft format.
3. **Find gaps** — Identify where the format is insufficient, ambiguous, or verbose for real SEAD requirements.
4. **Refine format** — Adjust schema to close gaps. Add fields only when SEAD (or another real consumer) needs them.
5. **Expand SEAD coverage** — Add more entities using the refined format.
6. **Repeat** — Until the format is stable and covers ~30 common SEAD entities.

### Why parallel, not sequential

- Designing the format in isolation risks overengineering (inventing fields no real model needs) or underspecifying (missing patterns that only emerge when writing concrete specs).
- The SEAD spec is the format's first acceptance test. If the format cannot cleanly express SEAD requirements, it needs revision.
- Feedback loops are tighter: each format change is immediately validated against real content.

### Delivery milestones

**Milestone 1: Core shape**
- Format supports: entities, roles, required flag, columns, logical types, nullability, identity_columns, unique_sets, domains, foreign_keys, naming, basic constraints
- SEAD spec covers: location, site, sample, dataset, analysis_entity, physical_sample (~6 core entities)
- The format is concrete enough to support parser and validator implementation without schema changes

**Milestone 2: Expanded coverage**
- Format refined based on M1 feedback
- SEAD spec covers a concrete Milestone 2 package of abundance, dating, method/contact, and taxonomy entities
- Milestone 2 is considered complete when the working SEAD spec reaches 20-24 total entities
- Preferred planning target: 23 total entities, corresponding to the current 9 core entities plus the 14 currently named Milestone 2 additions
- Template-generation proof of concept is implemented as a standalone generator that produces a non-runnable `shapeshifter.yml` starter scaffold from the target model, optionally filtered by domain/profile, including entity stubs, `public_id`, required target-facing columns, and required FK dependency closure without guessing loaders, SQL queries, or project-specific joins

After that initial Milestone 2 package is complete, the same standalone pre-integration track can continue with a follow-on expansion phase. That follow-on work can resolve remaining proposal-versus-implementation drift and draft the next most commonly mapped entities before the format is treated as Milestone 3 stable.

Milestone 2 should be completed as far as practical before backend-service integration becomes the primary focus.
That means expanding the working `target_models/specs/sead_v2.yml`, tightening the documentation around the expanded scope, and documenting the expected template-generation outcome before shifting effort toward backend wiring.

**Milestone 3: Stability**
- Format considered stable for v1
- SEAD spec covers ~30 most commonly mapped entities
- Validator integration ready (hand off to TARGET_SCHEMA_AWARE_VALIDATION)

Reaching ~30 entities is necessary but not sufficient for Milestone 3. Stability still requires a frozen v1 contract and downstream consumer validation.

## SEAD Specification Sketch

Initial entity groupings based on the SEAD schema (165 tables) and existing Shape Shifter projects:

### Core entities (Milestone 1)

These appear in virtually every SEAD project:

```yaml
entities:
  location:
    role: lookup
    required: true
    domains: [core, spatial]
    target_table: tbl_locations
    public_id: location_id
    identity_columns: [location_name]
    columns:
      location_name:
        required: true
        type: string
        nullable: false
      location_type_id:
        required: true
        type: integer
        nullable: false
    unique_sets:
      - [location_name]
    foreign_keys:
      - entity: location_type
        required: true

  location_type:
    role: classifier
    required: false
    domains: [core, spatial]
    target_table: tbl_location_types
    public_id: location_type_id
    identity_columns: [location_type]
    columns:
      location_type:
        required: true
        type: string
        nullable: false
    unique_sets:
      - [location_type]

  site:
    role: lookup
    required: true
    domains: [core, spatial]
    target_table: tbl_sites
    public_id: site_id
    identity_columns: [site_name]
    columns:
      site_name:
        required: true
        type: string
        nullable: false
    foreign_keys:
      - entity: location
        required: true

  sample:
    role: fact
    required: true
    domains: [core]
    target_table: tbl_physical_samples
    public_id: physical_sample_id
    foreign_keys:
      - entity: site
        required: true
      - entity: sample_type
        required: false

  sample_type:
    role: classifier
    domains: [core]
    target_table: tbl_sample_types
    public_id: sample_type_id
    identity_columns: [type_name]
    columns:
      type_name:
        required: true
        type: string
        nullable: false
    unique_sets:
      - [type_name]

  dataset:
    role: lookup
    required: true
    domains: [core]
    target_table: tbl_datasets
    public_id: dataset_id
    foreign_keys:
      - entity: method
        required: true

  analysis_entity:
    role: bridge
    required: true
    domains: [core]
    target_table: tbl_analysis_entities
    public_id: analysis_entity_id
    foreign_keys:
      - entity: sample
        required: true
      - entity: dataset
        required: true
```

### Domain-specific entities (Milestone 2)

These vary by data type (botanical, dating, ceramics, etc.):

The current Milestone 2 backlog is intentionally concrete rather than open-ended. The abundance, taxonomy, dating, and method/contact packages were the initial Milestone 2 package, which brought the working SEAD spec to 23 entities.

The next standalone follow-on expansion then added a first common-mapped-entity package, bringing the working SEAD spec to 31 entities. That package currently includes:

- `project`
- `feature_type`
- `feature`
- `modification_type`
- `sample_description_type`
- `sample_description`
- `site_type_group`
- `site_type`

The following follow-on package then extended the working SEAD spec to 35 entities with provenance and bridge coverage:

- `citation`
- `master_dataset`
- `dataset_contact`
- `sample_feature`

For Milestone 2, template generation should be understood narrowly: it is not a promise to auto-generate runnable project files. The implemented proof of concept is a deterministic starter scaffold generated from the target model, optionally filtered by domain/profile, that includes entity stubs, `public_id`, required target-facing columns, and required FK dependency closure while leaving source-specific extraction details to a human author.

The same specification file can tag these with `domains` such as `dating`, `abundance`, `taxonomy`, `contacts`, or `spatial` so consumers can work with focused subsets without splitting the model into many separate files too early.

- **Abundance chain:** `abundance`, `abundance_element`, `abundance_element_group`, `abundance_modification`, `abundance_property`, `modification_type` (drafted)
- **Dating:** `relative_ages`, `relative_dating`, `geochronology`, `dating_lab` (drafted). In Arbodat terms, archaeological dating facts map to `relative_dating`, while chronology or laboratory dating facts map to canonical SEAD `geochronology`.
- **Methods, provenance, and contacts:** `method`, `method_group`, `contact`, `contact_type`, `project`, `master_dataset`, `citation`, `dataset_contact` (drafted)
- **Taxonomy:** `taxa_tree_master`, `taxa_common_names` (drafted)
- **Excavation and site vocabulary:** `feature_type`, `feature`, `site_type_group`, `site_type` (drafted)
- **Sample metadata and bridges:** `sample_description_type`, `sample_description`, `sample_feature` (drafted)

These will be specified as the format stabilizes during M1→M2 iteration.

## Alternatives Considered

### Express the model in PostgreSQL DDL directly

Could parse `01_tables.sql` and `05_constraints.sql` to extract entity specs automatically.

Rejected because DDL describes physical schema, not modeling intent. It cannot express roles, required-ness for import projects, naming conventions, or which of 165 tables matter for a given data type. DDL is a useful *input* for generating specs, not a replacement.

### JSON Schema

Could define the target model format as a JSON Schema document.

Rejected because it optimizes for generic structural validation rather than domain-specific semantic constraints. The format needs concepts like "role" and "required FK to entity X" that JSON Schema would express awkwardly. YAML + Pydantic is more natural for this project.

### Embed in project files

Could put target model requirements inline in each `shapeshifter.yml`.

Rejected because it defeats reusability. The whole point is that target model requirements are defined once and consumed by many projects and tools.

## Risks and Tradeoffs

**Under-specification risk.** The format may not cover all SEAD patterns. Mitigation: iterate format and SEAD spec in parallel; add fields when real need emerges, not speculatively.

**Over-specification risk.** The format may accumulate fields that only SEAD uses, making it less generic. Mitigation: only add fields that would make sense for a non-SEAD target model. SEAD-specific semantics go in the *content* of `sead_v2.yml`, not in the *format*.

**DDL leakage risk.** Pulling too much from database constraints would turn the format into a lossy copy of physical schema details instead of a useful semantic contract. Mitigation: include only nullability and uniqueness rules that matter to conforming data; keep defaults, generated values, and physical constraint names out of scope.

**Maintenance burden.** The SEAD spec must be kept in sync with the actual SEAD schema. Mitigation: spec covers only commonly-mapped entities (~30 of 165). Consider scripted generation from DDL + annotations in future.

**Premature stability.** Locking the format before enough real-world usage risks revision costs. Mitigation: explicit milestone-based stabilization, v1 scope deliberately narrow.

## Testing and Validation

- **Round-trip:** The working spec at `target_models/specs/sead_v2.yml` loads, serializes, and reloads identically.
- **Coverage:** SEAD spec covers all entities used in at least two existing Shape Shifter projects.
- **Cross-check:** Every `target_table` in the spec exists in `docs/sead/01_tables.sql`.
- **Consumer test:** TARGET_SCHEMA_AWARE_VALIDATION validator can consume the spec and produce correct errors for a known-bad project.

## Acceptance Criteria

1. YAML format is documented with field definitions and semantics.
2. A working `sead_v2.yml` exists and covers core SEAD entities plus the current standalone expansion packages (31 entities at present). Until integration is completed, the working version lives at `target_models/specs/sead_v2.yml`.
3. Required entities are expressed via `required: true` on entity specs (no redundant top-level list).
4. Global constraints use typed objects, not untyped dicts.
5. At least one non-SEAD hypothetical model can be expressed cleanly to verify format generality.
6. Format is consumable by the target-schema-aware validation proposal without modifications.

## Open Questions

1. **Should `target_table` support schema-qualified names?** E.g., `public.tbl_locations` vs `tbl_locations`. Probably not in v1 — single-schema assumption is fine for SEAD.

2. **Should entity specs support inheritance or mixins?** E.g., a "standard_lookup" template that many classifiers share. Likely YAGNI for v1 but worth noting.

3. **How should `identity_columns` relate to project-level `keys`?** They should be conceptually aligned where possible, but `identity_columns` belongs to the target model and should not force a one-to-one mapping to Shape Shifter authoring choices.

4. **How to handle SEAD entities that appear in only one data type?** E.g., `tbl_ceramics` is relevant only for ceramics projects. Options: include all in one spec with `required: false`, tag entities with `domains`, or split into domain-specific spec fragments. Recommend single file plus `domains` for now, revisit if it grows unwieldy.

5. **Should the format version be in the file?** E.g., `format_version: "1.0"` alongside `model.version`. Useful if the format itself evolves. Recommend adding it.

6. **Do we need richer foreign-key semantics later?** Possibly for association-heavy entities and documentation generation, but defer until a concrete consumer needs more than relationship existence and required-ness.

7. **Should database defaults ever appear in the format?** Probably not as normative requirements. If consumers eventually need them, add advisory metadata rather than validation rules.

8. **Relationship to ENTITY_SEMANTIC_ROLES proposal.** That proposal adds `role` to project entity configuration. This proposal uses `role` in the target model spec. They should use the same enum values. Coordination needed but no conflict — one describes what *is*, the other what *should be*.

## Final Recommendation

Create the target model specification format and SEAD v2 spec in parallel, starting with a narrow scope (6 core entities, minimal format) and expanding iteratively.

The format should be opinionated about structure (typed constraints, no redundant fields, roles from the ENTITY_SEMANTIC_ROLES proposal) but minimal in scope. Include column presence, meaningful nullability, and candidate uniqueness where they describe conforming target data. Exclude defaults, processing semantics, and raw physical-schema detail.

The SEAD spec serves as both the primary consumer and the acceptance test for the format. If the format cannot express a real SEAD requirement cleanly, the format is wrong.

Start with Milestone 1. Ship the 6-entity SEAD spec. Then complete as much of Milestone 2 as practical in the standalone target-model work, including follow-on common-entity expansion where it still clarifies the target model, before turning primary attention to backend integration.

For planning purposes, treat 20 total entities as the minimum acceptable Milestone 2 completion threshold and 23 total entities as the preferred target for the initial named backlog. The current standalone spec now stands at 31 entities after the first common-entity follow-on expansion.
