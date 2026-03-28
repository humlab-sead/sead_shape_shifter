# Proposal: Target-Schema-Aware Validation Implementation Sketch

## Status

- Proposed technical sketch
- Scope: implementation approach for [TARGET_SCHEMA_AWARE_VALIDATION.md](TARGET_SCHEMA_AWARE_VALIDATION.md)
- Goal: describe a low-risk path for adding optional target-model validation without hardcoding target-system behavior into the core pipeline

## Summary

This document turns the proposal into an implementation-oriented sketch.

The core recommendations are:

1. keep target-schema-aware validation optional and layered on top of existing structural validation,
2. model target requirements as separate reusable specifications rather than project-local code paths,
3. resolve target model references at the API or mapper boundary, not inside core processing,
4. move semantic conformance logic onto the resolved core Shape Shifter project model rather than maintaining a second lightweight project-side model.

In short:

1. load the project as today,
2. resolve an optional target model reference,
3. run structural validation first,
4. run target-model validation second,
5. return one combined validation response.

## Relationship To Existing Code

The feature spans both the current backend boundary and the core configuration model.

Relevant files:

- [backend/app/services/validation_service.py](../../backend/app/services/validation_service.py)
- [backend/app/mappers/project_mapper.py](../../backend/app/mappers/project_mapper.py)
- [backend/app/models](../../backend/app/models)
- [src/model.py](../../src/model.py)
- [src/configuration/config.py](../../src/configuration/config.py)

The intended relationship is:

- the API layer continues loading editable project models,
- `ProjectMapper.to_core()` continues producing the resolved core project,
- structural validation remains unchanged and runs first,
- target-model loading and include resolution stay at the boundary,
- a core conformance engine validates the parsed target model against the resolved `ShapeShiftProject`,
- backend validation services map conformance findings to the normal `ValidationError` shape used elsewhere.

This keeps target-model file I/O out of the core while still making target-model conformance a genuine Shape Shifter core capability.

## Suggested Data Model

The proposal’s target model should be represented as a small shared schema aligned with the current format proposal.

In the short term, the existing models in `target_models/` can continue to serve as the drafting source. The migration target should not be a backend-only schema, but a shared domain model that can be consumed by backend validation services and, later, other entry points.

```python
# src/target_model/models.py  # illustrative location
from pydantic import BaseModel
from typing import Literal


class ForeignKeySpec(BaseModel):
    entity: str
    required: bool = False


class ColumnSpec(BaseModel):
    required: bool = False
    type: str | None = None
    nullable: bool | None = None
    description: str | None = None


class EntitySpec(BaseModel):
    role: Literal["fact", "lookup", "classifier", "bridge"] | None = None
    required: bool = False
    description: str | None = None
    domains: list[str] = []
    target_table: str | None = None
    public_id: str | None = None
    identity_columns: list[str] = []
    columns: dict[str, ColumnSpec] = {}
    unique_sets: list[list[str]] = []
    foreign_keys: list[ForeignKeySpec] = []


class NamingConventions(BaseModel):
    public_id_suffix: str | None = None


class ModelMetadata(BaseModel):
    name: str
    version: str
    description: str | None = None


class TargetModel(BaseModel):
    model: ModelMetadata
    entities: dict[str, EntitySpec] = {}
    constraints: list[dict] = []
    naming: NamingConventions | None = None
```

This schema should remain declarative. It is enough to support reusable rules without turning the feature into a broader schema DSL.

## Loading And Resolution Model

The lowest-risk implementation keeps target-model file resolution at the backend boundary.

Recommended behavior:

1. allow `metadata.target_model` to be either an inline object or an `@include:` reference,
2. resolve the reference using the same infrastructure already used for included project content,
3. validate the resolved object into `TargetModel`,
4. pass the parsed target model into a core conformance engine.

This avoids leaking unresolved include directives into the semantic validation layer.

It also aligns with the project’s layer-boundary rule: directives live in the YAML or API boundary, resolved values live in the backend or core logic path that consumes them.

## Core Conformance Engine

The dedicated conformance engine should move onto the resolved core project model.

Recommended shape:

```python
# src/validators/target_model_conformance.py
class TargetModelConformanceValidator:
    def __init__(self, target_model: TargetModel):
        self.target_model = target_model

    def validate(self, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues = []
        issues.extend(self._check_required_entities(project))

        for entity_name, entity_spec in self.target_model.entities.items():
            if entity_name not in project.cfg.get("entities", {}):
                continue

            table_cfg = TableConfig(entities_cfg=project.cfg["entities"], entity_name=entity_name)
            issues.extend(self._validate_entity(entity_name, table_cfg, entity_spec, project))

        return issues
```

The key architectural change is that conformance works against `TableConfig`, `ForeignKeyConfig`, append configuration, unnest configuration, resolved `@value:` directives, and other canonical semantics already defined in core.

### Target-Facing Column Contract

The main missing core abstraction is a canonical way to ask:

`Which columns does this entity present to the target model?`

That should become an explicit `TableConfig`-level API rather than remaining implicit across multiple helpers.

Recommended addition:

```python
class TableConfig:
    def get_target_facing_columns(self) -> set[str]:
        """Return the columns a target-model conformance check should treat as present."""
```

The initial implementation should derive this from already-resolved core semantics, including:

- declared `columns`
- generated `public_id`
- `extra_columns`
- FK-added target-facing columns (`public_id` plus FK extra columns)
- unnest outputs (`var_name`, `value_name`)
- append-derived output columns

Later iterations can decide whether target-facing columns should also include richer materialized/source-state derivations or other projected outputs that do not appear literally in the raw entity config.

### Why This Belongs In Core

The current standalone validator in `target_models/` depends on a reduced project model that only sees literal `columns`, `keys`, a shallow `foreign_keys` list, and top-level `extra_columns`.

That is enough for exploratory validation, but it is not the right permanent abstraction because it cannot reliably answer target-model questions for real Shape Shifter projects that depend on:

- resolved `@value:` expressions,
- append inheritance,
- FK-driven target columns,
- materialized state,
- generated target-facing columns.

Keeping a second lightweight project model for conformance would duplicate core semantics and violate DRY.

```python
# backend/app/validators/target_model_validator.py
class TargetModelValidator:
    def __init__(self, target_model: TargetModel):
        self.target_model = target_model

    def validate(self, project: ShapeShiftProject) -> list[ValidationError]:
        conformance_issues = CoreTargetModelConformanceValidator(self.target_model).validate(project)
        return [ValidationMapper.from_conformance_issue(issue) for issue in conformance_issues]
```

The backend-facing validator should remain a thin adapter. It should not duplicate conformance semantics already available in core.

## Validation Service Integration

The integration point is the existing validation service.

```python
# backend/app/services/validation_service.py
class ValidationService:
    async def validate_project(
        self,
        project_name: str,
        use_target_model: bool = True,
    ) -> ValidationResponse:
        api_project = self.project_service.load_project(project_name)
        core_project = ProjectMapper.to_core(api_project)

        errors = []

        errors.extend(self._validate_structure(core_project))

        if use_target_model and api_project.metadata.target_model:
            target_model = self._load_target_model(api_project.metadata.target_model)
            validator = TargetModelValidator(target_model)
            errors.extend(validator.validate(core_project))

        return ValidationResponse(errors=errors)
```

Key points:

- structural validation stays first,
- target-model validation is additive and optional,
- the core project passed into validation is already resolved,
- response formatting stays unchanged.

## Delivery Order

### Phase 1: Shared TargetModel And Core Hook Points

1. Move or duplicate the target-model schema into a shared domain location that is not backend-only.
2. Keep `metadata.target_model` support at the editable project/API boundary.
3. Implement target-model loading and `@include:` resolution at the boundary.
4. Add a core-facing validator entry point that accepts `TargetModel` plus resolved `ShapeShiftProject`.
5. Ship the shared validator in parallel with the existing standalone one during transition.

### Phase 2: Target-Facing Column Semantics In Core

1. Add `TableConfig.get_target_facing_columns()` or equivalent.
2. Define exactly which generated columns count as present for conformance.
3. Add required-column validation using the new core abstraction.
4. Add required foreign-key validation using `ForeignKeyConfig` rather than raw dicts.
5. Add naming convention checks and semantic mismatch detection such as entity-name versus `public_id` conflicts.

This phase is where DRY is recovered: conformance stops re-implementing project semantics and instead uses the existing core configuration wrappers.

### Phase 3: Migration And Backend Adoption

1. Replace the standalone lightweight project model in `target_models/` with tests that run against the core validator.
2. Keep `target_models/` for specifications, fixtures, and exploratory docs only.
3. Use backend validation services as adapters that load target models and map conformance issues to API errors.
4. Retire duplicated standalone conformance logic once parity is reached.

### Phase 4: Advanced Semantic Rules

1. Add schema-aware append conformance.
2. Add branch-aware or merged-parent rules when those proposals are concrete enough.
3. Add richer heuristics only after the core target-facing-column contract has proven stable.

### Future Enhancements

- project template generation from target models
- target model diff tooling for upgrades
- remote target-model references
- a curated registry of shared target models

Current phase sequencing and deferred issues are tracked in [target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md](../../target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md).

## Testing Strategy

Primary coverage should shift toward core conformance behavior, with backend tests covering loading and adapter integration.

Important test areas:

- parsing valid and invalid target model definitions,
- resolving inline versus `@include:` target model declarations,
- validating projects with and without `metadata.target_model`,
- verifying required entity, required column, and required foreign-key errors against resolved core projects,
- verifying warning versus error severity for semantic checks,
- handling missing target model files gracefully.

Relevant areas for tests:

- [src/model.py](../../src/model.py)
- a new core conformance validator module under [src](../../src)
- [backend/app/services/validation_service.py](../../backend/app/services/validation_service.py)

## Open Technical Questions

1. Should target model loading live directly in `ValidationService` or in a small dedicated loader service?
2. What exactly should `TableConfig.get_target_facing_columns()` include in v1: only explicit outputs, or also materialized/source-state derived outputs?
3. Should target-model-specific validation codes be grouped under a naming convention such as `TARGET_*` for easier filtering?
4. What is the cleanest way to support future rule disabling such as `options.validation.disabled_rules` without coupling the validator to frontend concerns?