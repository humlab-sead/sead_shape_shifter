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
4. keep semantic validation logic isolated in a dedicated validator that reads resolved core project data and produces normal validation errors.

In short:

1. load the project as today,
2. resolve an optional target model reference,
3. run structural validation first,
4. run target-model validation second,
5. return one combined validation response.

## Relationship To Existing Code

The feature fits naturally into the current backend layering.

Relevant files:

- [backend/app/services/validation_service.py](../../backend/app/services/validation_service.py)
- [backend/app/mappers/project_mapper.py](../../backend/app/mappers/project_mapper.py)
- [backend/app/models](../../backend/app/models)
- [src/model.py](../../src/model.py)

The intended relationship is:

- the API layer continues loading editable project models,
- `ProjectMapper.to_core()` continues producing the resolved core project,
- structural validation remains unchanged and runs first,
- a new target-model loader plus validator runs only when `metadata.target_model` is present,
- target-model validation returns the same `ValidationError` shape used elsewhere.

This keeps target-specific semantics out of the core normalization pipeline while still making them actionable during validation.

## Suggested Data Model

The proposal’s target model can be represented as a small backend-side schema aligned with the current format proposal.

```python
# backend/app/models/target_model.py
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

The lowest-risk implementation keeps target-model resolution at the backend boundary.

Recommended behavior:

1. allow `metadata.target_model` to be either an inline object or an `@include:` reference,
2. resolve the reference using the same infrastructure already used for included project content,
3. validate the resolved object into `TargetModel`,
4. pass the parsed target model into a dedicated validator.

This avoids leaking unresolved include directives into the semantic validation layer.

It also aligns with the project’s layer-boundary rule: directives live in the YAML or API boundary, resolved values live in the backend or core logic path that consumes them.

## Validator Shape

The simplest implementation is a dedicated validator class responsible only for target-model conformance.

```python
# backend/app/validators/target_model_validator.py
class TargetModelValidator:
    def __init__(self, target_model: TargetModel):
        self.target_model = target_model

    def validate(self, project: ShapeShiftProject) -> list[ValidationError]:
        errors = []

        errors.extend(self._check_required_entities(project))

        for entity_name, entity_spec in self.target_model.entities.items():
            if entity_name in project.cfg["entities"]:
                errors.extend(
                    self._validate_entity(
                        entity_name,
                        project.cfg["entities"][entity_name],
                        entity_spec,
                    )
                )

        if self.target_model.naming:
            errors.extend(self._check_naming_conventions(project))

        return errors

    def _check_required_entities(self, project: ShapeShiftProject) -> list[ValidationError]:
        required_entities = {
            entity_name
            for entity_name, entity_spec in self.target_model.entities.items()
            if entity_spec.required
        }
        missing = required_entities - set(project.cfg["entities"].keys())
        return [
            ValidationError(
                severity="error",
                code="MISSING_REQUIRED_ENTITY",
                message=f"Target model requires entity '{name}'",
                entity=None,
                field="entities",
                suggestion=f"Add entity '{name}' or choose a different target model",
            )
            for name in missing
        ]

    def _validate_entity(self, name: str, entity_cfg: dict, spec: EntitySpec) -> list[ValidationError]:
        errors = []

        configured_columns = entity_cfg.get("columns", [])
        required_columns = {
            column_name
            for column_name, column in spec.columns.items()
            if column.required
        }
        missing_cols = required_columns - set(configured_columns)
        for col in missing_cols:
            errors.append(
                ValidationError(
                    severity="error",
                    code="MISSING_REQUIRED_COLUMN",
                    message=f"Entity '{name}' missing required column '{col}'",
                    entity=name,
                    field="columns",
                )
            )

        configured_fks = {fk["entity"] for fk in entity_cfg.get("foreign_keys", [])}
        for fk_spec in spec.foreign_keys:
            if fk_spec.required and fk_spec.entity not in configured_fks:
                errors.append(
                    ValidationError(
                        severity="error",
                        code="MISSING_REQUIRED_FK",
                        message=f"Entity '{name}' missing required FK to '{fk_spec.entity}'",
                        entity=name,
                        field="foreign_keys",
                    )
                )

        if spec.public_id and entity_cfg.get("public_id") and entity_cfg["public_id"] != spec.public_id:
            errors.append(
                ValidationError(
                    severity="warning",
                    code="UNEXPECTED_PUBLIC_ID",
                    message=f"Entity '{name}' uses public_id '{entity_cfg['public_id']}' but target model expects '{spec.public_id}'",
                    entity=name,
                    field="public_id",
                    suggestion=f"Use '{spec.public_id}' if this entity is intended to conform to the target model",
                )
            )

        return errors
```

This validator should remain narrowly focused on semantic conformance. It should not fetch data, mutate the project, or own the broader validation orchestration.

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

### Phase 1: Foundation

1. Add the target model Pydantic schema in [backend/app/models](../../backend/app/models).
2. Add support for `metadata.target_model` in the editable project model.
3. Implement target model loading and `@include:` resolution.
4. Add required-entity validation.
5. Add required-column validation.
6. Ship a reference model such as `target_models/specs/sead_v2.yml`.

### Phase 2: Semantic Rules

1. Add required foreign-key validation.
2. Add naming convention checks.
3. Add semantic mismatch detection such as entity-name versus `public_id` conflicts.
4. Consider source-type appropriateness only after the first SEAD draft proves it is worth the noise.

This phase benefits from any parallel work on explicit semantic roles, but it does not require changes to the core normalization engine.

### Phase 3: Branch-Aware Rules

1. Add merged-parent branch discriminator checks.
2. Add branch-scoped consumer validation.
3. Add schema-aware append conformance.

This phase depends on separate branch-modeling proposals becoming concrete enough to validate against.

### Future Enhancements

- project template generation from target models
- target model diff tooling for upgrades
- remote target-model references
- a curated registry of shared target models

Current phase sequencing and deferred issues are tracked in [target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md](../../target_models/docs/SEAD_V2_IMPLEMENTATION_PLAN.md).

## Testing Strategy

Primary coverage should sit around backend validation behavior.

Important test areas:

- parsing valid and invalid target model definitions,
- resolving inline versus `@include:` target model declarations,
- validating projects with and without `metadata.target_model`,
- verifying required entity, required column, and required foreign-key errors,
- verifying warning versus error severity for semantic checks,
- handling missing target model files gracefully.

Relevant areas for tests:

- [backend/app/services/validation_service.py](../../backend/app/services/validation_service.py)
- [backend/app/models](../../backend/app/models)
- a new target-model validator module under [backend/app](../../backend/app)

## Open Technical Questions

1. Should target model loading live directly in `ValidationService` or in a small dedicated loader service?
2. How much of the existing include-resolution machinery can be reused without introducing project-specific assumptions?
3. Should target-model-specific validation codes be grouped under a naming convention such as `TARGET_*` for easier filtering?
4. What is the cleanest way to support future rule disabling such as `options.validation.disabled_rules` without coupling the validator to frontend concerns?