# Proposal: Target-Schema-Aware Validation

## Status

- Proposed feature
- Scope: Validation system, project configuration
- Goal: Enable semantic validation based on target data model requirements

## Summary

Add optional target-schema-aware validation that reasons about modeling intent and target system requirements, not just YAML structure. The validator would catch semantic mismatches like fact tables using lookup-style IDs or entities missing required relationships. Target models would be defined in reusable specification files and referenced via `@include:`, making Shape Shifter truly generic while providing structure-specific guidance when needed.

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

## Current Behavior

Shape Shifter validates:
- YAML syntax and structure
- Foreign key constraint completeness
- Circular dependency detection
- Column existence in entities
- Topological sort feasibility

Shape Shifter does not validate:
- Entity semantic roles (fact vs lookup vs classifier)
- Target system requirements (required entities, mandatory relationships)
- Naming convention adherence (public ID patterns)
- Source type appropriateness (classifiers should use `fixed` or `sql`)

## Proposed Design

### Target Model Specification Files

Introduce target model specification files that define target system requirements independently from project data mappings.

**File location:** `data/models/<target_system_name>.yml`

**Structure:**
```yaml
# data/models/sead_v2.yml
model:
  name: "SEAD Clearinghouse"
  version: "2.0.0"
  description: "SEAD archaeological data model"
  
  # Entities that MUST exist in conforming projects
  required_entities:
    - location
    - site
    - sample
  
  # Entity specifications
  entities:
    location:
      role: lookup              # Semantic role
      required: true            # Must exist in project
      required_columns:         # Must have these columns
        - location_id
        - location_name
        - location_type_id
      constraints:
        - type: unique_keys
          keys: [location_name]
    
    site:
      role: lookup
      required: true
      required_columns:
        - site_id
        - site_name
        - location_id
      foreign_keys:              # Required relationships
        - entity: location
          required: true
    
    sample:
      role: fact
      required: true
      required_columns:
        - sample_id
        - sample_name
        - site_id
      foreign_keys:
        - entity: site
          required: true
    
    sample_type:
      role: classifier           # Controlled vocabulary
      required: true
      source_options: [fixed, sql]  # Acceptable source types
      required_columns:
        - sample_type_id
        - type_name
  
  # Global constraints
  constraints:
    - type: no_circular_dependencies
    - type: all_lookups_before_facts
    
  # Naming conventions
  naming:
    public_id_suffix: "_id"
    lookup_id_pattern: "^[a-z_]+_id$"
```

### Project Referencing

Projects reference target models using existing `@include:` pattern:

```yaml
metadata:
  type: shapeshifter-project
  name: "Arbodat Dendrochronology Import"
  target_model: "@include: models/sead_v2.yml"
  
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
          required_columns: [artifact_id, name]
```

### Validation Rules

**Phase 1: Basic Conformance**
- Required entities present
- Required columns exist
- Entity roles match (if specified in target model)
- Required foreign keys exist

**Phase 2: Semantic Checks**
- Public ID naming conventions
- Source type appropriateness (classifiers use fixed/sql)
- Fact-to-lookup relationship patterns
- Naming mismatches (e.g., entity named `X_dating` but maps to `X_age_id`)

**Phase 3: Branch-Aware** (after Proposals 4–5)
- Merged parent branch discriminators
- Branch-scoped consumer validity
- Schema-aware append conformance

### Data Model

```python
# backend/app/models/target_model.py
from pydantic import BaseModel
from typing import Literal

class ForeignKeySpec(BaseModel):
    entity: str
    required: bool = False

class EntitySpec(BaseModel):
    role: Literal["fact", "lookup", "classifier", "bridge"] | None = None
    required: bool = False
    required_columns: list[str] = []
    foreign_keys: list[ForeignKeySpec] = []
    source_options: list[str] | None = None  # e.g., ["fixed", "sql"]
    constraints: list[dict] = []

class NamingConventions(BaseModel):
    public_id_suffix: str | None = None
    lookup_id_pattern: str | None = None

class TargetModel(BaseModel):
    name: str
    version: str
    description: str | None = None
    required_entities: list[str] = []
    entities: dict[str, EntitySpec] = {}
    constraints: list[dict] = []
    naming: NamingConventions | None = None
```

### Validator Implementation

```python
# backend/app/validators/target_model_validator.py
class TargetModelValidator:
    def __init__(self, target_model: TargetModel):
        self.target_model = target_model
    
    def validate(self, project: ShapeShiftProject) -> list[ValidationError]:
        errors = []
        
        # Check required entities
        errors.extend(self._check_required_entities(project))
        
        # Check entity specs
        for entity_name, entity_spec in self.target_model.entities.items():
            if entity_name in project.cfg["entities"]:
                errors.extend(self._validate_entity(
                    entity_name, 
                    project.cfg["entities"][entity_name],
                    entity_spec
                ))
        
        # Check naming conventions
        if self.target_model.naming:
            errors.extend(self._check_naming_conventions(project))
        
        return errors
    
    def _check_required_entities(self, project: ShapeShiftProject) -> list[ValidationError]:
        missing = set(self.target_model.required_entities) - set(project.cfg["entities"].keys())
        return [
            ValidationError(
                severity="error",
                code="MISSING_REQUIRED_ENTITY",
                message=f"Target model requires entity '{name}'",
                entity=None,
                field="entities",
                suggestion=f"Add entity '{name}' or choose a different target model"
            )
            for name in missing
        ]
    
    def _validate_entity(self, name: str, entity_cfg: dict, spec: EntitySpec) -> list[ValidationError]:
        errors = []
        
        # Check required columns
        configured_columns = entity_cfg.get("columns", [])
        missing_cols = set(spec.required_columns) - set(configured_columns)
        for col in missing_cols:
            errors.append(ValidationError(
                severity="error",
                code="MISSING_REQUIRED_COLUMN",
                message=f"Entity '{name}' missing required column '{col}'",
                entity=name,
                field="columns"
            ))
        
        # Check required foreign keys
        configured_fks = {fk["entity"] for fk in entity_cfg.get("foreign_keys", [])}
        for fk_spec in spec.foreign_keys:
            if fk_spec.required and fk_spec.entity not in configured_fks:
                errors.append(ValidationError(
                    severity="error",
                    code="MISSING_REQUIRED_FK",
                    message=f"Entity '{name}' missing required FK to '{fk_spec.entity}'",
                    entity=name,
                    field="foreign_keys"
                ))
        
        # Check source type (for classifiers)
        if spec.source_options and "type" in entity_cfg:
            if entity_cfg["type"] not in spec.source_options:
                errors.append(ValidationError(
                    severity="warning",
                    code="INVALID_SOURCE_TYPE",
                    message=f"Entity '{name}' has type '{entity_cfg['type']}' but target model expects {spec.source_options}",
                    entity=name,
                    field="type",
                    suggestion=f"Consider using one of: {', '.join(spec.source_options)}"
                ))
        
        return errors
```

### Integration with ValidationService

```python
# backend/app/services/validation_service.py
class ValidationService:
    async def validate_project(
        self, 
        project_name: str,
        use_target_model: bool = True
    ) -> ValidationResponse:
        # Load project
        api_project = self.project_service.load_project(project_name)
        core_project = ProjectMapper.to_core(api_project)
        
        errors = []
        
        # Structural validation (existing)
        errors.extend(self._validate_structure(core_project))
        
        # Target model validation (new)
        if use_target_model and api_project.metadata.target_model:
            target_model = self._load_target_model(api_project.metadata.target_model)
            validator = TargetModelValidator(target_model)
            errors.extend(validator.validate(core_project))
        
        return ValidationResponse(errors=errors)
```

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
target_model: "@include: models/sead_v2.yml"

# Not this:
target_model: "models/sead_v2.yml"
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
required_entities:
  - location
  - site
  - sample
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

### Example 2: Wrong Role for Entity

**Target Model:**
```yaml
entities:
  sample_type:
    role: classifier
    source_options: [fixed, sql]
```

**Project (using wrong source):**
```yaml
entities:
  sample_type:
    type: entity  # Should be 'fixed' or 'sql'
    source: sample
```

**Validation Warning:**
```
WARNING [INVALID_SOURCE_TYPE]: Entity 'sample_type' has type 'entity' but target model expects ['fixed', 'sql']
  Entity: sample_type
  Field: type
  Suggestion: Consider using one of: fixed, sql
```

### Example 3: Semantic Naming Mismatch

**Target Model:**
```yaml
entities:
  relative_dating:
    role: fact
    required_columns: [relative_dating_id]
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
- Semantic naming checks work (Phase 2)
- Projects without target models still validate normally
- Clear, actionable error messages

## Recommended Delivery Order

### Phase 1: Foundation (Low Risk)
1. Target model Pydantic schema (`backend/app/models/target_model.py`)
2. Add `metadata.target_model` field support
3. Target model file loading with `@include:` resolution
4. Basic required entity validation
5. Basic required column validation
6. Ship with `data/models/sead_v2.yml` example

**Dependency:** None, can ship independently

### Phase 2: Semantic Validation
1. Entity role validation (fact/lookup/classifier)
2. Source type appropriateness (classifiers)
3. Required FK validation
4. Naming convention checks
5. Semantic mismatch detection (entity name vs public_id)

**Dependency:** Phase 1 complete, benefits from Proposal 2 (Entity Semantic Roles)

### Phase 3: Branch-Aware (After Proposals 4–5)
1. Merged parent branch discriminator checks
2. Branch-scoped consumer validation
3. Schema-aware append conformance

**Dependency:** Proposals 4 and 5 (branch modeling features)

### Future Enhancements
- Project template generation from target models
- Target model diff tool (for version upgrades)
- Remote target model references (URLs)
- Community target model registry

## Open Questions

1. **Severity defaults:** Should missing required entities be errors or warnings by default?
   - **Recommendation:** Errors for `required: true`, warnings for recommended patterns

2. **Custom validation rules:** Should target models support custom Python validators?
   - **Recommendation:** Defer to Phase 3, start with declarative rules only

3. **Multiple target models:** Can a project conform to multiple target models simultaneously?
   - **Recommendation:** Single target model in v1, multi-model in future if needed

4. **Target model inheritance:** Should target models support extends/inheritance?
   - **Recommendation:** YAGNI for v1, revisit if real need emerges

5. **Validation configuration:** Should projects be able to selectively disable rules?
   - **Recommendation:** Yes, via `options.validation.disabled_rules: [...]`

## Final Recommendation

Implement target-schema-aware validation using separate, reusable target model specification files referenced via `@include:`.

**Start with Phase 1:**
- Define target model schema (entity specs, required entities, constraints)
- Add `metadata.target_model` field
- Implement basic validation (required entities, columns)
- Ship with `data/models/sead_v2.yml` as reference

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
