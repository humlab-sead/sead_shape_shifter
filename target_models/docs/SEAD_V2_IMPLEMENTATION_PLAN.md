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

## Proposal Milestone Tracking

The format proposal now defines three delivery milestones in addition to the phase roadmap above.

These milestones are broader than the standalone `target_models/` phases and should be read as proposal-level checkpoints.
That means an earlier phase can be complete in the narrow standalone sense while a later proposal milestone is still incomplete because the current proposal text and the current implementation are not yet fully aligned.

### Milestone 1: Core Shape

Proposal intent:
- Format supports entities, roles, required flag, columns, nullability, identity_columns, unique_sets, domains, foreign_keys, naming, and basic constraints
- SEAD spec covers the first core entity set
- The format is concrete enough to support parser and validator implementation without schema changes

Checklist:
- [x] Parser models exist for the current standalone target-model format
- [x] Spec validation exists for the current standalone target-model format
- [x] Standalone conformance validation exists for project-versus-target checks
- [x] The current standalone format supports entities, roles, required, nullability, identity_columns, unique_sets, domains, foreign_keys, naming, and constraint declarations
- [x] The current standalone SEAD spec covers the Milestone 1 core spine and additional iteration-1 entities in `target_models/specs/sead_v2.yml`
- [x] The proposal now treats `target_models/specs/sead_v2.yml` as the working version until Shape Shifter integration is completed
- [x] Implementation matches the current proposal column contract (mapping-based `columns` with logical `type` metadata)
- [x] Proposal and implementation are aligned tightly enough to claim "without schema changes"

Current status:
- **Milestone 1 is complete.**
- The parser, standalone validators, and working core SEAD spec all exist.
- The proposal now matches the current standalone reality: until integration is completed, the working `sead_v2.yml` remains in `target_models/specs/sead_v2.yml` and uses the implemented mapping-based column contract with logical `type` metadata.

### Milestone 2: Expanded Coverage

Proposal intent:
- Refine the format based on Milestone 1 feedback
- Expand SEAD coverage toward domain-specific entities
- Demonstrate template-generation value from the target model

Checklist:
- [x] Resolve the Milestone 1 proposal-versus-implementation alignment gaps
- [x] Expand the canonical SEAD spec toward the current Milestone 2 backlog: abundance, dating, method/contact, and taxonomy coverage
- [x] Reach the explicit Milestone 2 target of 20-24 total entities in `target_models/specs/sead_v2.yml`
- [x] Reach the preferred planning target of 23 total entities if all currently named Milestone 2 backlog entities remain in scope
- [x] Add a template-generation proof of concept using the target model, optionally filtered by domain/profile
- [x] Validate the expanded model with parser, spec-validation, and conformance tests

Current status:
- **Milestone 2 is complete for the current standalone scope.**
- The abundance, taxonomy, dating, and method/contact packages have now been drafted in the working spec.
- Current baseline: the working spec contains 23 entities, so both the minimum and preferred Milestone 2 entity-count targets are now satisfied.
- The template-generation proof of concept now exists as a standalone generator and CLI in `target_models/`.
- The remaining work moves out of Milestone 2 and into later implementation choices such as backend integration, broader coverage, or a richer generator.

### Milestone 3: Stability

Proposal intent:
- Treat the format as stable for v1
- Expand SEAD coverage toward the most commonly mapped entities
- Hand the format off cleanly to downstream consumers such as target-schema-aware validation

Checklist:
- [ ] Resolve remaining proposal-versus-implementation mismatches
- [ ] Expand the canonical SEAD spec toward roughly 30 commonly mapped entities
- [ ] Freeze the v1 format contract as stable
- [ ] Demonstrate downstream consumption by target-schema-aware validation without further schema redesign
- [ ] Confirm the proposal-level acceptance criteria are satisfied

Current status:
- **Milestone 3 is not complete.**
- The current standalone work is still best understood as pre-integration stabilization rather than full v1 format stabilization.

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

- [x] Run the standalone conformance validator against multiple real project fixtures
- [x] Classify findings into stable errors, warnings, and deferred heuristics
- [x] Record false positives and ambiguous cases in `target_models/docs/`
- [x] Confirm whether `sead_v2.yml` needs refinement based on real project evidence
- [x] Identify the minimal check set safe for eventual backend integration

Deliverables:
- Refined conformance tests
- Notes on noisy versus stable rules in `target_models/docs/TARGET_MODEL_CONFORMANCE_REFINEMENT.md`
- A documented minimal rule set for future backend integration

Current Phase 6 decision:
- Keep `sead_v2.yml` canonical and unchanged for now; the current real-project evidence does not justify alias metadata or weaker conformance semantics.
- Freeze the standalone integration candidate to the conservative checks already documented in `target_models/docs/TARGET_MODEL_CONFORMANCE_REFINEMENT.md`.
- Treat Phase 6 as complete for the current standalone conformance-refinement scope.

Exit criteria:
- The validator behavior is understood well enough that integration can be incremental rather than speculative

### Iteration Notes

- **Iteration 1**: evaluate one project deeply
- **Iteration 2**: compare across multiple project shapes
- **Iteration 3**: freeze a minimum viable conformance rule set and carry only that subset toward backend integration

## Phase 7: Milestone 2 Completion

Goals:
- Complete the Milestone 2 documentation and specification work before any backend-service integration
- Expand `sead_v2.yml` beyond the current core spine toward the next domain-specific entity groups
- Make the target model more useful to downstream consumers by improving coverage and documenting the path to template generation

### Checklist

- [x] Draft the abundance package in `target_models/specs/sead_v2.yml`: `abundance`, `abundance_element`, `abundance_element_group`, `abundance_modification`, `abundance_property`
- [x] Draft the dating package in `target_models/specs/sead_v2.yml`: `relative_ages`, `relative_dating`, `geochronology`, `dating_lab`
- [x] Draft the method/contact package in `target_models/specs/sead_v2.yml`: `method_group`, `contact`, `contact_type`
- [x] Draft the taxonomy package in `target_models/specs/sead_v2.yml`: `taxa_tree_master`, `taxa_common_names`
- [x] Reach the explicit Milestone 2 target of 20-24 total entities in the working SEAD spec
- [x] Reach the preferred planning target of 23 total entities if all currently named backlog entities remain in scope
- [x] Update `docs/proposals/TARGET_MODEL_SPECIFICATION_FORMAT.md` so its milestone language, examples, and success criteria reflect the expanded-coverage target
- [x] Update `target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md` to track the Milestone 2 completion work and any scope decisions made during expansion
- [x] Decide and document the minimum acceptable template-generation proof of concept for Milestone 2
- [x] Add or update parser, spec-validation, and conformance tests to cover the expanded entity set and any new format decisions
- [x] Reassess whether any newly observed ambiguities belong in deferred format issues versus the Milestone 2 scope

### Milestone 2 Backlog Basis

Current baseline:
- 23 entities now exist in `target_models/specs/sead_v2.yml`

Remaining named expansion backlog:
- 0 additional entities remain in scope for Milestone 2

Planning arithmetic:
- 23 current entities + 0 remaining backlog entities = 23 total entities with the full currently named Milestone 2 backlog drafted
- For planning purposes, treat 20 entities as the minimum acceptable Milestone 2 completion threshold
- Treat 23 entities as the preferred planning target because it corresponds to the full currently named Milestone 2 backlog

Deliverables:
- Expanded `target_models/specs/sead_v2.yml`
- Updated milestone and roadmap documentation in `docs/proposals/` and `target_models/docs/`
- Test coverage proving the expanded target model still loads and validates cleanly
- A working standalone template-generation proof of concept plus its documentation

### Template-Generation Proof of Concept

Purpose:
- Demonstrate that the target model is useful not only for validation but also as an authoring aid for new Shape Shifter projects.

Minimum scope:
- A standalone script or notebook is sufficient; backend integration is not required for Milestone 2.
- Input is the working target model at `target_models/specs/sead_v2.yml` plus an optional domain filter or explicit entity allowlist/profile.
- Output is a non-runnable starter scaffold in `shapeshifter.yml` style that is meant to be completed by a human author.

Required output content:
- Project metadata stub.
- Entity stubs for the selected entities plus any required foreign-key dependency closure.
- `public_id` for each generated entity.
- The target-facing required columns from the target model for each generated entity.
- Required foreign-key entity references, even when the FK join details are still left for a human to complete.

Explicitly out of scope for the proof of concept:
- Inferring loader type (`sql`, `fixed`, `entity`, `xlsx`, etc.) when the target model does not provide that information.
- Generating SQL queries, source-specific keys, data-source names, or environment-variable wiring.
- Producing a ready-to-run project configuration.
- Replacing the need for human decisions about extraction strategy, business keys, or project-specific joins.

Acceptance criteria:
- The prototype can generate at least one deterministic scaffold from the current SEAD target model.
- The prototype supports at least one filtered generation mode, for example `domains=[dating]` or an explicit entity subset.
- The generated scaffold includes dependency closure for required FK targets.
- The generated output is valid YAML and is clearly usable as an authoring starting point, even if incomplete for execution.

Implementation shape:
- The standalone generator lives in `target_models/src/target_model_spec/template_generator.py`.
- The proof-of-concept CLI entrypoint lives in `target_models/scripts/generate_project_template.py`.
- The initial CLI shape is:
  - `--spec PATH`
  - `--domain NAME` (repeatable)
  - `--entity NAME` (repeatable)
  - `--project-name NAME`
  - `--output PATH` (optional; stdout when omitted)

Preferred demonstration target:
- Generate a dating-focused scaffold from the current SEAD target model covering `relative_ages`, `relative_dating`, `geochronology`, `dating_lab`, and any required dependency entities pulled in by the filter.

Current implementation status:
- Implemented in `target_models/src/target_model_spec/template_generator.py` with CLI wrapper `target_models/scripts/generate_project_template.py`.
- Covered by standalone tests in `target_models/tests/test_template_generator.py`.

Exit criteria:
- Milestone 2 is complete or reduced to a clearly bounded remainder with explicit deferred items
- The documentation and standalone target-model artifacts are as complete as practical before backend integration begins

## Phase 8: Optional Backend Integration

Goals:
- Integrate only the proven subset of conformance checks into Shape Shifter validation services
- Reuse the standalone work rather than redesigning it inside the backend

### Checklist

- [ ] Decide whether target-model loading should stay in a dedicated loader or move into existing services
- [ ] Map standalone conformance issues to backend validation error shapes
- [ ] Integrate only the frozen standalone rule set as an additive validation pass
- [ ] Keep non-integrated experimental rules outside the backend path

Deliverables:
- Backend integration work described in `docs/proposals/TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md`

Exit criteria:
- Target-model-aware validation in the backend uses only the frozen conservative rules already stabilized in `target_models/`

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
6. Complete Milestone 2 documentation and target-model expansion work in Phase 7.
7. Revisit backend integration only after the standalone validator and Milestone 2 work have stabilized.