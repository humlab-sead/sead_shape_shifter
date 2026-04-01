# Proposal: Target-Schema-Aware Validation

## Status

- **Core engine: implemented** — `src/target_model/` package contains the domain model, conformance validator, spec validator, and template generator
- **Backend integration: implemented** — `metadata.target_model` support, `@include:` resolution, `ValidationService.validate_target_model()`, and REST endpoint are all wired
- **Frontend adoption: implemented** — Check Conformance button, Conformance panel, and target_model field in Metadata Editor are all wired
- Scope: Validation system, project configuration
- Goal: Enable semantic validation based on target data model requirements

## Implementation Progress

### Completed

- `src/target_model/models.py` — Pydantic domain model: `TargetModel`, `EntitySpec`, `ColumnSpec`, `ForeignKeySpec`, `NamingConventions`, `GlobalConstraint`
- `src/target_model/conformance.py` — Registry-based conformance engine with four built-in validators: `RequiredEntityConformanceValidator`, `PublicIdConformanceValidator`, `ForeignKeyConformanceValidator`, `RequiredColumnsConformanceValidator`; extensible via `CONFORMANCE_VALIDATORS` registry
- `src/target_model/spec_validator.py` — `TargetModelSpecValidator` checks the target model spec itself (public_id suffix adherence, unknown FK targets, unknown identity/unique-set columns)
- `src/target_model/template_generator.py` — Generates starter project scaffolds from a target model with domain and entity filters; includes CLI (`python -m src.target_model.template_generator --spec ...`)
- `src/model.py` — `TableConfig.get_target_facing_columns()` and `TableConfig.get_target_facing_foreign_key_targets()` provide the column-contract API for conformance
- `tests/model/test_target_model_conformance.py` — 11 tests, 98% branch coverage
- `backend/app/models/project.py` — `ProjectMetadata.target_model` field (`str | dict | None`) added to the API model
- `backend/app/mappers/project_mapper.py` — `@include:` directives resolved at the API→Core boundary; inline dicts preserved as-is
- `backend/app/validators/target_model_validator.py` — `TargetModelValidator` bridges core conformance engine and backend; wraps `TargetModelConformanceValidator` and converts `ConformanceIssue` → `ValidationError`
- `backend/app/services/validation_service.py` — `ValidationService.validate_target_model()` loads and resolves the project, extracts the resolved `target_model` dict, and delegates to `TargetModelValidator`
- `backend/app/models/validation.py` — `ValidationCategory.CONFORMANCE = "conformance"` added; conformance issues now have their own category (no longer grouped with structural)
- `backend/app/mappers/validation_mapper.py` — `ValidationMapper.from_conformance_issue()` uses `ValidationCategory.CONFORMANCE`
- `backend/app/api/v1/endpoints/validation.py` — `POST /projects/{name}/validate/target-model` endpoint
- `backend/app/api/v1/endpoints/projects.py` — `MetadataUpdateRequest.target_model` field added; endpoint passes it to service with presence detection via `model_fields_set`
- `backend/app/services/project_service.py` and `project_operations.py` — `update_metadata()` accepts `target_model` + `target_model_provided`; empty string or explicit `null` clears the field
- `frontend/src/types/config.ts` — `ProjectMetadata.target_model?: string | null` added
- `frontend/src/types/validation.ts` — `ValidationCategory` extended with `'conformance'`
- `frontend/src/api/projects.ts` — `MetadataUpdateRequest.target_model?: string | null` added
- `frontend/src/api/validation.ts` — `validationApi.validateTargetModel()` added
- `frontend/src/composables/useConformanceValidation.ts` — New composable following the `useDataValidation` pattern
- `frontend/src/components/validation/ValidationPanel.vue` — **Check Conformance** button (deep-purple, `mdi-check-decagram-outline`), `conformanceValidationLoading` prop, `validate-target-model` emit, `conformanceIssues`/`conformanceErrors` computed properties, and a **Conformance** expansion panel in the By Category tab
- `frontend/src/views/ProjectDetailView.vue` — `useConformanceValidation` imported and wired; `handleConformanceValidate()` handler added; `mergedValidationResult` extended to include conformance results alongside structural and data results
- `frontend/src/components/MetadataEditor.vue` — **Target Model** combobox added; lists project YAML files as `@include: <file>` suggestions; allows free-text entry; clearable; included in save payload

### Pending

Naming convention conformance and standalone test migration are complete (Milestone 3). Remaining deferred and future items — including semantic mismatch detection, Phase 4 advanced rules, format extensions, and open technical questions — have been consolidated into [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Summary

Add optional target-schema-aware validation that reasons about modeling intent and target system requirements, not just YAML structure. The validator would catch semantic mismatches like fact tables using lookup-style IDs or entities missing required relationships. Target models are defined in reusable specification files and referenced via `@include:`, making Shape Shifter generic while still allowing target-specific guidance when needed.

## Problem

Shape Shifter currently validates YAML structure, constraint syntax, and topological consistency, but cannot catch semantic modeling errors that violate target system requirements.

Real examples of semantic errors that pass current validation:

- Entity named `relative_dating` (fact) mapping to `relative_age_id` (lookup column)
- Fact table using a lookup-style public ID name
- Missing required entities for target system (e.g., SEAD requires `location`, `site`, `sample`)
- Fact tables not linked to required parent entities
- Merged parent entities missing branch discriminators
- Classifier entities using wrong source types (e.g., `type: entity` instead of `type: fixed`)

These errors are not YAML syntax problems. They are semantic mismatches with target model expectations. Users discover them late—at ingestion time or during reconciliation—when fixes are more expensive.

### Why This Matters Now

As Shape Shifter is used for more complex projects:
- Target model requirements become more sophisticated (SEAD Clearinghouse, custom museum systems)
- Projects involve more entities with intricate relationships
- Semantic errors become harder to spot in large configurations
- Need grows for project templates that encode target system structure
- Users need earlier feedback on modeling decisions

Current validation cannot distinguish between "valid YAML that happens to be wrong for SEAD" and "configuration that matches target requirements."

## Scope

This proposal covers:

- Target model specification format (separate YAML files)
- Target model referencing mechanism (`metadata.target_model`)
- Validation rules for semantic conformance
- Initial set of validations (required entities, roles, columns, relationships)
- Project template generation from target models

## Non-Goals

This proposal does not:

- Replace existing structural validation (that stays independent)
- Hardcode SEAD-specific logic into core processing pipeline
- Require target models for all projects (remains optional)
- Add runtime enforcement beyond validation warnings/errors
- Create a type system or schema DSL beyond what's needed

## Current State

### What Shape Shifter validates today

- YAML syntax and structure
- Foreign key constraint completeness
- Circular dependency detection
- Column existence in entities
- Topological sort feasibility

### Core target-model validation (implemented in `src/target_model/`)

- Required entity presence
- Required column presence (via `TableConfig.get_target_facing_columns()`)
- Required foreign key targets (via `TableConfig.get_target_facing_foreign_key_targets()`)
- Public ID conformance (missing, unexpected)
- Spec self-consistency (unknown FK targets, identity columns, unique-set columns, naming conventions)

### Still absent from any validation path

- Entity semantic roles (fact vs lookup vs classifier) — semantic mismatch detection deferred to [TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md)
- Source type appropriateness (classifiers should use `fixed` or `sql`) — deferred
- Backend wiring for Phase 4 checks — deferred

## Proposed Design

The target-model format is defined in [TARGET_MODEL_SPECIFICATION_FORMAT.md](TARGET_MODEL_SPECIFICATION_FORMAT.md). Implementation details and code-level sketches are documented in [TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md](TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md). Phased rollout for the first SEAD model is tracked in [target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md](../../target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md).

### Key Concepts

This proposal uses a small set of semantic concepts to describe modeling intent independently of YAML syntax.

**Semantic role**

A semantic role describes what an entity means in the target model, not how it is loaded. A role helps the validator distinguish between structurally valid configurations that serve different purposes.

- `fact`: A primary observational or transactional entity. Facts usually represent records the project is fundamentally about, such as samples, observations, measurements, or events. They typically depend on surrounding lookup or classifier entities and often sit lower in the dependency graph.
- `lookup`: A reference entity that defines reusable domain values or parent context, such as locations, sites, or categories. Lookup entities are commonly referenced by many facts and usually expose stable identifier columns.
- `classifier`: A controlled-vocabulary or typology entity used to classify other records. In practice these are often best loaded from `fixed` or `sql` sources because they represent curated value sets rather than row-by-row extracted observations.
- `bridge`: An association entity that connects two or more entities, especially in many-to-many relationships. A bridge may carry little business meaning of its own, but it is still semantically important because it expresses relationship structure explicitly.

**Modeling intent**

Modeling intent is the meaning implied by an entity's name, role, columns, and relationships taken together. For example, an entity named `relative_dating` implies a fact-like record, while a public ID such as `relative_age_id` implies a lookup-style identity. Target-schema-aware validation checks for these mismatches.

Aggregates should not be treated as separate semantic roles in v1. An aggregate is usually still a `fact`, but at a different grain or with derived meaning. If aggregate semantics become important, they should be modeled as a separate axis such as `derivation: aggregate` or an explicit grain declaration, rather than by expanding the base role set with variants like `aggregate_fact`.

**Required entity**

A required entity is one the target model expects to be present for the project to be considered conformant. This is not a generic Shape Shifter rule; it is target-model-specific knowledge such as SEAD expecting entities like `location`, `site`, or `sample`.

**Required relationship**

A required relationship is a foreign key or dependency that must exist for an entity to make sense in the target model. For example, a fact entity may be structurally valid on its own but still semantically incomplete if it is not linked to the lookup or parent entity required by the target schema.

**Naming convention**

Naming conventions are target-model rules about identifiers and columns, such as expected public ID suffixes or patterns. These conventions matter because they often encode semantic expectations: fact-like entities should not present themselves using lookup-style identifier names unless that is explicitly intended by the target model.

### Target Model Specification Files

Introduce target model specification files that define target system requirements independently from project data mappings.

**File location during iteration:** `target_models/specs/<target_system_name>.yml`

**Structure:**
```yaml
# target_models/specs/sead_v2.yml
model:
  name: "SEAD Clearinghouse"
  version: "2.0.0"
  description: "SEAD archaeological data model"

entities:
  location:
    role: lookup
    required: true
    public_id: location_id
    columns:
      location_name:
        required: true
        type: string
        nullable: false
      location_type_id:
        required: true
        type: integer
        nullable: false
    foreign_keys:
      - entity: location_type
        required: true

  site:
    role: lookup
    required: true
    public_id: site_id
    columns:
      site_name:
        required: true
        type: string
        nullable: false
    foreign_keys:
      - entity: location
        required: true

naming:
  public_id_suffix: "_id"

constraints:
  - type: no_circular_dependencies
```

### Project Referencing

Projects reference target models using existing `@include:` pattern:

```yaml
metadata:
  type: shapeshifter-project
  name: "Arbodat Dendrochronology Import"
  target_model: "@include: target_models/specs/sead_v2.yml"
  
entities:
  location:
    type: fixed
    public_id: location_id
    # Validator checks this conforms to target_model.entities.location
```

**Alternative (inline for custom models):**
```yaml
metadata:
  type: shapeshifter-project
  name: "Custom Museum Import"
  target_model:
    model:
      name: "Custom"
    entities:
      artifact:
        role: fact
        required: true
        public_id: artifact_id
        columns:
          name:
            required: true
            type: string
            nullable: false
```

### Validation Rules

**Phase 1: Basic Conformance** — implemented in `src/target_model/conformance.py`
- [x] Required entities present via `required: true` on entity specs (`RequiredEntityConformanceValidator`)
- [x] Required columns exist via `columns.<name>.required` (`RequiredColumnsConformanceValidator`)
- [x] Required foreign keys exist (`ForeignKeyConformanceValidator`)
- [x] Expected/unexpected public_id checks (`PublicIdConformanceValidator`)
- [ ] Naming convention checks against project entities — public_id_suffix validated in `TargetModelSpecValidator` only; not yet in conformance

**Phase 2: Semantic Checks** — deferred; see [TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md)
- [ ] Global role-informed checks such as `no_orphan_facts`
- [ ] Semantic naming mismatches where entity key and expected identifier clearly diverge

**Phase 3: Branch-Aware** (after Proposals 4–5) — deferred
- [ ] Merged parent branch discriminators
- [ ] Branch-scoped consumer validity
- [ ] Schema-aware append conformance

Deferred items and open technical questions are tracked in [TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Architecture Decisions

### Why Separate Files vs Inline?

**Separate target model files** (recommended):
- ✅ **Reusability** - Define SEAD model once, use in all SEAD projects
- ✅ **Versioning** - Target model evolves independently (SEAD v1.0 → v2.0)
- ✅ **Maintainability** - Update rules in one place
- ✅ **Clean projects** - Projects stay focused on data mapping
- ✅ **Templates** - Target models can generate project skeletons
- ✅ **Follows existing pattern** - Uses `@include:` like `data_sources` and `mappings`

**Inline specification** (alternative):
- ✅ **Self-contained** - Everything in one file
- ✅ **Custom targets** - Easy per-project tweaking
- ❌ **Duplication** - Every project repeats same constraints
- ❌ **Maintenance burden** - Updates require touching all projects
- ❌ **Cluttered** - Mixes data mapping with schema requirements

**Recommendation:** Use separate files with optional inline override for edge cases.

### Why `@include:` instead of string reference?

```yaml
# This (recommended):
target_model: "@include: target_models/specs/sead_v2.yml"

# Not this:
target_model: "target_models/specs/sead_v2.yml"
```

Reasons:
- Consistent with existing `data_sources` and `mappings` patterns
- Supports both file reference and inline specification seamlessly
- Works with existing YAML resolution infrastructure
- Future-proof for remote references (`@include: https://...`)

## Validation Examples

### Example 1: Missing Required Entity

**Target Model:**
```yaml
entities:
  location:
    required: true
  site:
    required: true
  sample:
    required: true
```

**Project (missing `location`):**
```yaml
entities:
  site:
    type: fixed
  sample:
    type: entity
```

**Validation Error:**
```
ERROR [MISSING_REQUIRED_ENTITY]: Target model 'SEAD v2.0' requires entity 'location'
  Suggestion: Add entity 'location' or choose a different target model
```

### Example 2: Semantic Naming Mismatch

**Target Model:**
```yaml
entities:
  relative_dating:
    role: fact
    public_id: relative_dating_id
```

**Project (wrong column name):**
```yaml
entities:
  relative_dating:
    public_id: relative_age_id  # Fact using lookup-style name
```

**Validation Error:**
```
ERROR [SEMANTIC_NAMING_MISMATCH]: Entity 'relative_dating' (fact) uses public_id 'relative_age_id' which suggests lookup entity
  Entity: relative_dating
  Field: public_id
  Suggestion: Use 'relative_dating_id' to match entity role
```

## Frontend Adoption

The conformance feature is surfaced in two places in the editor UI.

### Validation Panel — Check Conformance button

A **Check Conformance** button sits alongside the existing Run YAML Validation and Run Data Validation buttons. Clicking it calls `POST /projects/{name}/validate/target-model` and displays the results in a dedicated **Conformance** expansion panel under the *By Category* tab. Conformance issues use the `deep-purple` colour and the `mdi-check-decagram-outline` icon to distinguish them visually from structural (grey) and data (blue) issues. Like the other validation runs, conformance results are merged into the unified `mergedValidationResult` so they participate in the tab-level error/warning counts and the copy-to-clipboard export.

If the project has no `target_model` declared, the endpoint returns an empty valid result and the panel does not appear (it is gated on `conformanceIssues.length > 0`). There is no error — the button is always safe to press.

### Metadata Editor — Target Model field

A **Target Model** combobox is added below the Default Entity selector. On mount the editor fetches the project's uploaded YAML files (`GET /projects/{name}/files?ext=yml,yaml`) and presents them as `@include: <filename>` options. Users can also type a path directly, which is the idiomatic way to reference a spec file that lives outside the uploads directory (e.g. `@include: target_models/specs/sead_v2.yml`). The field is clearable; clearing it and saving removes `target_model` from the project metadata entirely. The value is always included in the PATCH payload so the backend can distinguish an intentional clear from a field that was simply not sent.

## Alternatives Considered

### Alternative 1: Hardcode SEAD Rules in Core

**Rejected.** Makes Shape Shifter SEAD-specific instead of generic. Cannot support other target systems without code changes.

### Alternative 2: Runtime Schema Validation Only

**Rejected.** Too late—users need feedback at configuration time, not during ingestion. Also requires target database access.

### Alternative 3: Extend Entity `type` Field

```yaml
entities:
  sample:
    type: sead_fact  # Hardcoded target system
```

**Rejected.** Pollutes entity type space, makes configuration less portable, still requires target-specific logic in core.

### Alternative 4: Validation-Only (No Target Model Files)

**Rejected.** Cannot express reusable requirements, forces duplication of target system knowledge across projects, no template capability.

## Risks And Tradeoffs

**Complexity:**
- Adds new concept (target models) users must understand
- Mitigation: Make optional, ship with clear examples, provide good error messages

**Version compatibility:**
- Projects coupled to target model versions
- Mitigation: Semantic versioning, clear upgrade paths, version pinning support

**False positives:**
- Overly strict validation may reject valid edge cases
- Mitigation: Warning vs error severity, ability to disable specific checks, inline overrides

**Maintenance burden:**
- Target models must be maintained alongside target systems
- Mitigation: Version target models, document update process, make community-contributed

**Migration cost:**
- Existing projects don't have `target_model` reference
- Mitigation: Entirely optional, backward compatible, can be added incrementally

## Testing And Validation

**Unit tests:**
- Target model parsing and validation
- Each validation rule in isolation
- Error message quality

**Integration tests:**
- Load project with target model reference
- Validate against SEAD v2 model
- Handle missing target model gracefully
- Inline vs file reference

**Manual validation:**
- Retrofit Arbodat project with SEAD target model
- Verify relative_dating semantic error is caught
- Test warning/error severity appropriateness
- Validate editor experience

**Acceptance criteria:**
- Target model files parse correctly
- Projects can reference target models via `@include:`
- Required entity checks work
- Required column checks work
- Required FK checks work
- Semantic naming checks work for explicit, low-noise mismatches (Phase 2)
- Projects without target models still validate normally
- Clear, actionable error messages

## Open Questions

Deferred open questions (severity defaults, custom validators, multiple target models, target model inheritance, validation configuration / rule disabling) have been consolidated into [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Final Recommendation

Implement target-schema-aware validation using separate, reusable target model specification files referenced via `@include:`.

**Start with Phase 1:**
- Define target model schema around top-level `model`, `entities`, `naming`, and `constraints`
- Add `metadata.target_model` field
- Implement basic validation (required entities, columns, and foreign keys)
- Ship with `target_models/specs/sead_v2.yml` as reference

**Benefits:**
- Makes Shape Shifter truly generic (no hardcoded SEAD assumptions)
- Catches semantic errors at configuration time
- Enables project templates from target models
- Reusable specifications across projects
- Optional (backward compatible)
- Follows existing `@include:` pattern

**Success metrics:**
- Target model can describe SEAD requirements completely
- Arbodat relative_dating semantic error is caught
- No existing projects break (purely additive)
- Clear, actionable validation messages

This proposal complements other modeling enhancements (entity roles, branch modeling) by providing the validation foundation that makes declarative modeling intent actionable.
