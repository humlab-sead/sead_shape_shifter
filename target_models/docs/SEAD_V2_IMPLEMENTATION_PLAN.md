# SEAD v2 Implementation Plan

## Purpose

This document tracks the implementation phases for the first SEAD target-model specification.

It complements, but does not replace:

- `docs/proposals/TARGET_MODEL_SPECIFICATION_FORMAT.md` for the format contract and semantics
- `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION.md` for how Shape Shifter consumes target models during validation

The goal here is practical sequencing: what must be decided before drafting, what will be delivered in the first iterations, and what is explicitly deferred.

## Phase 0: Pre-Draft Decisions

Phase 0 locks the minimum decisions needed before writing the first SEAD model draft.

### Checklist

- [x] Canonical top-level file shape chosen
- [x] Canonical spec location chosen
- [x] Iteration-1 entity set frozen
- [x] Canonical iteration-1 naming decided
- [x] Minimum column contract decided
- [x] Logical type vocabulary decided
- [x] Meaning of `required` decided
- [x] Meaning of `unique_sets` decided
- [x] Meaning of `identity_columns` decided
- [x] Minimal iteration-1 domain tags decided
- [x] Iteration-1 role usage constrained
- [x] `sample_group` and required `sample_type` semantics decided

### 0.1 Canonical file shape

Iteration 1 uses this top-level shape:

```yaml
model:
  name: string
  version: string
  description: string

entities: {}

naming: {}

constraints: []
```

Decision:
- Use top-level `model`, `entities`, `naming`, and `constraints`
- Do not use a nested `model.entities` shape
- Do not use a redundant top-level `required_entities` list; entity required-ness lives on each entity spec via `required: true`

### 0.2 Canonical spec location

Decision:
- During format iteration, the SEAD spec lives at `target_models/specs/sead_v2.yml`
- Phase documents and implementation notes live under `target_models/docs/`

### 0.3 Iteration-1 entity set

Decision:
- Freeze the first draft to these entities:
  - `location`
  - `location_type`
  - `site`
  - `sample_group`
  - `sample`
  - `sample_type`
  - `method`
  - `dataset`
  - `analysis_entity`

This is the smallest useful set that captures the common SEAD spine without leaving required foreign-key targets undefined.

The intended core hierarchy is:

- `location -> site -> sample_group -> sample -> analysis_entity`
- `sample -> sample_type`
- `dataset -> method`

### 0.4 Canonical iteration-1 naming

Decision:
- Use semantic Shape Shifter-facing entity keys in the spec
- Use explicit `target_table` and `public_id` fields to map to SEAD naming where needed
- In particular:
  - `sample` remains the entity key in the target-model spec
  - `sample.target_table` is `tbl_physical_samples`
  - `sample.public_id` is `physical_sample_id`

Rationale:
- Existing Shape Shifter projects overwhelmingly use `sample` as the entity name
- SEAD table and identifier naming can still be expressed precisely through `target_table` and `public_id`

### 0.5 Minimum column contract

Decision:
- Iteration 1 column metadata is limited to:
  - `name`
  - `required`
  - `type`
  - `nullable`
  - `description`

No richer column contract is introduced in iteration 1.

### 0.6 Logical type vocabulary

Decision:
- Iteration 1 uses a small, system-agnostic logical type vocabulary:
  - `string`
  - `integer`
  - `decimal`
  - `boolean`
  - `date`
  - `datetime`
  - `enum`

These are logical data expectations, not DBMS-native storage declarations.

### 0.7 Meaning of `required`

Decision:
- For entities, `required: true` means the entity must exist in a conforming project
- For columns, `required: true` means the column must exist in a conforming entity definition
- `required` does not imply minimum row counts or non-null source data beyond separately declared `nullable: false`

### 0.8 Meaning of `unique_sets`

Decision:
- `unique_sets` expresses logical dataset-level uniqueness expectations relevant to conformance
- It is not a dump of physical database indexes or named constraints

### 0.9 Meaning of `identity_columns`

Decision:
- `identity_columns` describes canonical target-model identity columns for matching, documentation, and reasoning
- It does not force a one-to-one mapping to Shape Shifter project-level `keys`

### 0.10 Domain tags for iteration 1

Decision:
- Keep domains minimal in the first draft
- Use only `core` and `spatial` in iteration 1

### 0.11 Role usage in iteration 1

Decision:
- Roles are required target-model semantics, but the first consumer should apply them conservatively
- Iteration-1 validation uses roles for light semantic checks and global constraints only
- Do not build a large role-specific rule engine in iteration 1

### 0.12 Required sample semantics

Decision:
- SEAD places `sample_group` between `site` and `sample`
- `sample` must belong to a `sample_group`
- `sample_type` is a required property of `sample`, so the `sample -> sample_type` relationship is required in iteration 1
- `sample_type` therefore remains part of the iteration-1 required core rather than a deferred classifier

## Phase 1: Align Documentation

Goals:
- Align proposal documents around the canonical top-level target-model shape
- Remove execution sequencing and rollout details from the format proposal
- Point implementation planning to this document

### Checklist

- [x] Format proposal points to the implementation plan
- [x] Format proposal no longer carries phased rollout content
- [x] Validation proposal uses the canonical top-level target-model shape
- [x] Validation proposal points to `target_models/specs/sead_v2.yml`
- [x] Implementation sketch is aligned with the current format
- [x] All phase-related cross-references are consistent

Deliverables:
- `docs/proposals/TARGET_MODEL_SPECIFICATION_FORMAT.md`
- `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION.md`
- `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md`

Exit criteria:
- The docs no longer disagree on structure, location, or iteration-1 scope

## Phase 2: Freeze Iteration-1 SEAD Core

Goals:
- Freeze the entity list and canonical naming for the first SEAD draft
- Keep iteration 1 intentionally narrow and low-risk

### Checklist

- [x] Core entity list frozen
- [x] `sample` retained as the semantic entity key
- [x] `sample` mapped to `tbl_physical_samples` / `physical_sample_id`
- [x] `sample_group` inserted between `site` and `sample`
- [x] `sample_type` marked as a required sample dependency
- [x] Core hierarchy written down explicitly

Deliverables:
- Stable iteration-1 entity list
- Stable mapping from semantic entity names to SEAD tables and public IDs

Exit criteria:
- The first SEAD draft can be written without further naming decisions

## Phase 3: Author First SEAD Draft

Goals:
- Produce the first usable `target_models/specs/sead_v2.yml`
- Cover only the iteration-1 core entities with minimal metadata

### Checklist

- [x] `target_models/specs/sead_v2.yml` created
- [x] Iteration-1 core entities present in the draft
- [x] `target_table` mappings added for iteration-1 entities
- [x] `public_id` mappings added for iteration-1 entities
- [x] Core foreign-key relationships expressed
- [x] Global constraints included
- [ ] Required columns reviewed for all iteration-1 entities
- [ ] Identity columns reviewed for all iteration-1 entities
- [ ] Unique sets reviewed for all iteration-1 entities
- [ ] Draft cross-checked against SEAD source schema and a real Shape Shifter project

Deliverables:
- `target_models/specs/sead_v2.yml`

Iteration-1 content rules:
- Prefer minimal but correct metadata over broad but speculative coverage
- Include `role`, `required`, `domains`, `target_table`, `public_id`, `identity_columns`, `columns`, `unique_sets`, and `foreign_keys` only where there is confidence
- Avoid adding specialized fields until a concrete validator or second consumer requires them

Exit criteria:
- The SEAD spec is internally consistent and usable as the first acceptance test of the format

## Future Phase: Deferred Issues

These are intentionally deferred so iteration 1 stays small and coherent.

### Checklist

- [ ] Revisit deferred format issues after iteration-1 feedback
- [ ] Revisit deferred validation issues after the first validator pass
- [ ] Expand beyond the core SEAD spine only after the first draft stabilizes

### Deferred format issues

- Join-column semantics for foreign keys
- Schema-qualified `target_table` names
- `allowed_values` or richer enum support
- Advisory metadata for database defaults or generated values
- Inheritance, mixins, or reusable entity templates
- Physical storage details such as lengths or DBMS-native types

### Deferred validation issues

- Source-type appropriateness rules such as classifier-prefer-fixed-or-sql
- Advanced naming-pattern checks beyond suffix validation
- Entity-name versus `public_id` semantic mismatch heuristics beyond clear, low-noise cases
- Type-aware validation against real preview or normalized data
- Branch-aware semantic validation
- Severity overrides or per-rule suppression mechanisms

### Deferred SEAD coverage issues

- Abundance chain entities
- Dating entities
- Method-group and contact entities
- Taxonomy-focused entities
- Lower-frequency SEAD tables that appear only in specialized project types

## Near-Term Order

1. Complete Phase 1.
2. Confirm Phase 2 decisions in the first draft.
3. Produce Phase 3 output.
4. Revisit deferred issues only after the first draft exposes real gaps.