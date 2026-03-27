# SEAD v2 Implementation Plan

## Purpose

This document tracks the implementation phases for the first SEAD target-model specification.

It complements, but does not replace:

- `docs/proposals/TARGET_MODEL_SPECIFICATION_FORMAT.md` for the format contract and semantics
- `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION.md` for how Shape Shifter consumes target models during validation

The goal here is practical sequencing: what must be decided before drafting, what will be delivered in the first iterations, and what is explicitly deferred.

## Terminology

The words `phase` and `iteration` mean different things in this document.

- **Phase** = a broad stage of work with a distinct goal and exit criteria.
- **Iteration** = one pass within a phase where we refine the output using real examples, feedback, or tests.

In practice:

- We are currently using **phases** to describe the roadmap.
- We use **iterations** to describe refinement loops within a phase.

Examples:

- Phase 3 is "author the first SEAD draft".
- Iteration 1 within that phase is the first narrow draft of `sead_v2.yml`.
- A later iteration in the same phase could tighten columns or identity rules after testing against another real project.

For the next stretch of work, the important distinction is:

- we can add new **phases** for standalone conformance-validation work inside `target_models/`
- and still expect multiple **iterations** within those phases before any backend integration is justified

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
- Iteration 1 stores columns as a mapping keyed by column name
- Iteration 1 column metadata is limited to:
  - `required`
  - `type`
  - `nullable`
  - `description`
- Column order is not semantically significant in the format contract, even if authors preserve a preferred reading order in YAML

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
- [x] Required columns reviewed for all iteration-1 entities
- [x] Identity columns reviewed for all iteration-1 entities
- [x] Unique sets reviewed for all iteration-1 entities
- [x] Draft cross-checked against SEAD source schema and a real Shape Shifter project

Deliverables:
- `target_models/specs/sead_v2.yml`

Iteration-1 content rules:
- Prefer minimal but correct metadata over broad but speculative coverage
- Include `role`, `required`, `domains`, `target_table`, `public_id`, `identity_columns`, `columns`, `unique_sets`, and `foreign_keys` only where there is confidence
- Avoid adding specialized fields until a concrete validator or second consumer requires them

Exit criteria:
- The SEAD spec is internally consistent and usable as the first acceptance test of the format

Cross-check basis:
- `docs/sead/01_tables.sql`
- `tests/test_data/projects/arbodat/shapeshifter.yml`

## Phase 4: Standalone Project Corpus

Goals:
- Collect a small set of real `shapeshifter.yml` files inside `target_models/` for isolated experimentation
- Keep target-model conformance work independent from backend integration
- Make the next validator phase testable using real project examples rather than synthetic payloads only

### Checklist

- [x] Create a `target_models/examples/` area for standalone project fixtures
- [x] Add at least one real SEAD-oriented project fixture
- [x] Add at least one intentionally non-conforming or partially conforming fixture
- [x] Document fixture provenance and any simplifications made for standalone testing
- [x] Add tests that load the fixture projects independently of backend services

Deliverables:
- `target_models/examples/`
- Standalone project fixtures derived from real `shapeshifter.yml` files
- Fixture-loading tests under `target_models/tests/`

Exit criteria:
- Real project configurations can be loaded and exercised from within `target_models/` alone

### Iteration Notes

- **Iteration 1**: start with one real SEAD-style project and one intentionally broken fixture
- **Iteration 2**: add a second real project only if the first validator pass exposes ambiguity in the target model

## Phase 5: Initial TargetModelConformanceValidator

Goals:
- Introduce a validator that checks whether a Shape Shifter project conforms to a target model
- Keep it standalone inside `target_models/` before wiring anything into Shape Shifter validation services
- Focus on low-noise checks driven directly by the target model contract

### Checklist

- [x] Define a lightweight project-side model for the subset of `shapeshifter.yml` needed for conformance checks
- [x] Add a `TargetModelConformanceValidator` alongside the spec validator
- [x] Validate required entities declared in the target model
- [x] Validate expected `public_id` values where the target model declares them
- [x] Validate required foreign-key targets by entity name
- [x] Validate required target-facing columns where the project declares column output explicitly enough to compare
- [x] Return standalone conformance issues without depending on backend `ValidationError`
- [x] Cover the validator with tests against real fixture projects

Deliverables:
- `target_models/src/target_model_spec/conformance_validator.py` or equivalent
- A lightweight project model or adapter for standalone `shapeshifter.yml` validation
- Conformance tests under `target_models/tests/`

Exit criteria:
- A standalone conformance validator can detect obvious project-versus-target mismatches using real project fixtures

### Iteration Notes

- **Iteration 1**: required entities, `public_id`, foreign-key entity presence, and required columns only
- **Iteration 2**: tighten comparisons where project files express enough information to check them reliably
- **Iteration 3**: decide which checks are too noisy for the first integrated version

## Phase 6: Standalone Conformance Refinement

Goals:
- Iterate on validator behavior using real projects before integrating with Shape Shifter services
- Separate stable, low-noise checks from speculative or brittle checks
- Use this phase to decide what deserves backend integration and what should remain experimental

### Checklist

- [ ] Run the standalone conformance validator against multiple real project fixtures
- [ ] Classify findings into stable errors, warnings, and deferred heuristics
- [ ] Record false positives and ambiguous cases in `target_models/docs/`
- [ ] Refine `sead_v2.yml` only where real project evidence shows the target model is underspecified or misleading
- [ ] Identify the minimal check set safe for eventual backend integration

Deliverables:
- Refined conformance tests
- Notes on noisy versus stable rules
- A documented minimal rule set for future backend integration

Exit criteria:
- The validator behavior is understood well enough that integration can be incremental rather than speculative

### Iteration Notes

- **Iteration 1**: evaluate one project deeply
- **Iteration 2**: compare across multiple project shapes
- **Iteration 3**: freeze a minimum viable conformance rule set

## Phase 7: Optional Backend Integration

Goals:
- Integrate only the proven subset of conformance checks into Shape Shifter validation services
- Reuse the standalone work rather than redesigning it inside the backend

### Checklist

- [ ] Decide whether target-model loading should stay in a dedicated loader or move into existing services
- [ ] Map standalone conformance issues to backend validation error shapes
- [ ] Integrate target-model conformance as an additive validation pass
- [ ] Keep non-integrated experimental rules outside the backend path

Deliverables:
- Backend integration work described in `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md`

Exit criteria:
- Target-model-aware validation in the backend uses only rules that have already been stabilized in `target_models/`

## Future Phase: Deferred Issues

These are intentionally deferred so the standalone validator and the first target-model iterations stay small and coherent.

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
- Value-level checks that require executing the Shape Shifter pipeline rather than inspecting project configuration

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
4. Build a standalone project corpus in Phase 4.
5. Implement and iterate on `TargetModelConformanceValidator` in Phases 5 and 6.
6. Revisit backend integration only after the standalone validator has stabilized.