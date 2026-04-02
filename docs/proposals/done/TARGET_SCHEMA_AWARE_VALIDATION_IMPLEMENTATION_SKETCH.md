# Proposal: Target-Schema-Aware Validation Implementation Sketch

## Status

- **Milestones 1–3: complete** — core engine, backend integration, frontend wiring all done
- **Remaining backlog:** see [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md)
- Scope: implementation approach for [TARGET_SCHEMA_AWARE_VALIDATION.md](TARGET_SCHEMA_AWARE_VALIDATION.md)

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


## Domain Model

**Implemented as `src/target_model/models.py`.** The schema matches the original proposal and has been extended with `domains`, `target_table`, and `identity_columns` on `EntitySpec` to support the full SEAD spec. `GlobalConstraint` was added for top-level constraint declarations. `Field(default_factory=...)` is used throughout in preference to mutable default class attributes.

See `src/target_model/models.py` for the current source of truth.

## Loading And Resolution Model

Not yet implemented at the backend boundary. The intended behaviour is unchanged from the original sketch:

1. allow `metadata.target_model` to be either an inline object or an `@include:` reference,
2. resolve the reference using the same infrastructure already used for included project content,
3. validate the resolved object into `TargetModel`,
4. pass the parsed target model into the core conformance engine.

This avoids leaking unresolved include directives into the semantic validation layer and aligns with the project's layer-boundary rule: directives live in the YAML or API boundary, resolved values live in the backend or core logic path that consumes them.

## Core Conformance Engine

**Implemented as `src/target_model/conformance.py`.**

The engine uses a registry pattern rather than a single monolithic class. This allows new validators to be added without touching the orchestrator:

```python
# src/target_model/conformance.py  — actual design

class ConformanceValidatorRegistry(Registry[type[ConformanceValidator]]):
    items: dict[str, type[ConformanceValidator]] = {}

CONFORMANCE_VALIDATORS = ConformanceValidatorRegistry()


class EntityConformanceValidator(ConformanceValidator):
    """Base for validators that operate entity-by-entity.
    Subclasses implement validate_entity(); the base handles iteration and guard."""

    def guard(self, target_model, project, entity_name) -> bool:
        return project.has_table(entity_name)   # skip entities not in project

    def validate(self, target_model, project) -> list[ConformanceIssue]:
        issues = []
        for entity_name, entity_spec in target_model.entities.items():
            if not self.guard(target_model, project, entity_name):
                continue
            table_cfg = project.get_table(entity_name)
            issues.extend(self.validate_entity(entity_name, entity_spec, table_cfg))
        return issues


@CONFORMANCE_VALIDATORS.register(key="required_entity")
class RequiredEntityConformanceValidator(ConformanceValidator):
    """Reports MISSING_REQUIRED_ENTITY for entities absent from the project."""

@CONFORMANCE_VALIDATORS.register(key="public_id")
class PublicIdConformanceValidator(EntityConformanceValidator):
    """Reports MISSING_PUBLIC_ID / UNEXPECTED_PUBLIC_ID."""

@CONFORMANCE_VALIDATORS.register(key="foreign_key")
class ForeignKeyConformanceValidator(EntityConformanceValidator):
    """Reports MISSING_REQUIRED_FOREIGN_KEY_TARGET."""

@CONFORMANCE_VALIDATORS.register(key="required_columns")
class RequiredColumnsConformanceValidator(EntityConformanceValidator):
    """Reports MISSING_REQUIRED_COLUMN using TableConfig.get_target_facing_columns()."""


class TargetModelConformanceValidator(ConformanceValidator):
    """Orchestrator: runs all registered validators and aggregates issues."""

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues = []
        for validator_cls in CONFORMANCE_VALIDATORS.items.values():
            issues.extend(validator_cls().validate(target_model, project))
        return issues
```

**Key design decisions vs. the original sketch:**

- Both `target_model` and `project` are passed to `validate()` at call time, not at construction time. This makes `TargetModelConformanceValidator` stateless and reusable across multiple project/model combinations without reinstantiation.
- Validators live in `src/target_model/`, not `src/validators/`, since they form a cohesive target-model package.
- `RequiredEntityConformanceValidator` extends `ConformanceValidator` directly (not `EntityConformanceValidator`) because it operates on entities that are absent from the project and therefore has no `TableConfig` to work with.

### Target-Facing Column Contract

**Implemented in `src/model.py`.**

```python
class TableConfig:
    def get_target_facing_columns(self) -> list[str]: ...
    def get_target_facing_foreign_key_targets(self) -> set[str]: ...
```

`get_target_facing_columns()` derives the column contract from already-resolved core semantics:

- business keys (`keys`) and explicit `columns`
- `extra_columns` names
- `public_id`
- FK-added columns: remote entity `public_id` plus FK `extra_columns`
- unnest survivors: `id_vars`, `var_name`, `value_name` (columns that survive the melt boundary)
- unnest-aware FK pruning: FK-generated columns only count if their `local_keys` survive unnest

`system_id` is intentionally excluded unless it surfaces through one of the above mechanisms.

### Why This Belongs In Core

The standalone validator in `target_models/` was a useful prototype but depended on a reduced project model with only literal `columns`, `keys`, a shallow `foreign_keys` list, and `extra_columns`. That model cannot answer conformance questions for projects that use append inheritance, materialized state, unnest transformations, or FK-generated columns. Moving conformance onto `TableConfig` recovers DRY and makes the column contract authoritative.

### Backend Adapter (Pending)

When backend integration is implemented, the adapter should remain thin:

```python
# backend/app/validators/target_model_validator.py  — not yet written
class TargetModelValidator:
    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ValidationError]:
        from src.target_model.conformance import TargetModelConformanceValidator
        from backend.app.mappers.validation_mapper import ValidationMapper
        issues = TargetModelConformanceValidator().validate(target_model, project)
        return [ValidationMapper.to_api_error(issue) for issue in issues]
```

## Validation Service Integration (Pending)

The integration point will be the existing `ValidationService`:

```python
# backend/app/services/validation_service.py  — not yet modified
async def validate_project(self, project_name: str, use_target_model: bool = True) -> ValidationResponse:
    api_project = self.project_service.load_project(project_name)
    core_project = ProjectMapper.to_core(api_project)
    errors = list(self._validate_structure(core_project))

    if use_target_model and api_project.metadata.get("target_model"):
        target_model = self._load_target_model(api_project.metadata["target_model"])
        errors.extend(TargetModelValidator().validate(target_model, core_project))

    return ValidationResponse(errors=errors)
```

Key constraints remain: structural validation stays first; target-model validation is additive and optional; the core project is already resolved before conformance runs.

## Delivery Order

### Phase 1: Shared TargetModel And Core Hook Points

- [x] Move target-model schema to `src/target_model/models.py` (shared domain location, not backend-only)
- [x] Add core-facing conformance engine: `TargetModelConformanceValidator.validate(target_model, project)`
- [x] Add `TargetModelSpecValidator` for spec self-consistency checks
- [x] Add `metadata.target_model` field to the API project model
- [x] Implement `@include:` resolution for `target_model` at the backend boundary
- [x] Ship validation in parallel with existing standalone example tests during transition

### Phase 2: Target-Facing Column Semantics In Core

- [x] `TableConfig.get_target_facing_columns()` — covers keys, columns, extra_columns, public_id, FK columns, unnest survivors
- [x] `TableConfig.get_target_facing_foreign_key_targets()` — unnest-aware FK target set
- [x] Required-column validation using the core abstraction (`RequiredColumnsConformanceValidator`)
- [x] Required foreign-key validation (`ForeignKeyConformanceValidator`)
- [x] Required entity validation (`RequiredEntityConformanceValidator`)
- [x] Public ID conformance (`PublicIdConformanceValidator`)
- [ ] Naming convention checks in conformance validator — `public_id_suffix` is validated in `TargetModelSpecValidator` against the spec file; not yet checked against project entities in conformance
- [ ] Semantic mismatch detection (entity-name vs. public_id style divergence)

### Phase 3: Migration And Backend Adoption

- [x] Add `metadata.target_model` support to API project/mapper layer
- [x] Implement target-model loading and `@include:` resolution at backend boundary
- [x] Add `TargetModelValidator` backend adapter (`backend/app/validators/`)
- [x] Wire into `ValidationService.validate_target_model()`
- [x] Migrate standalone `target_models/` example tests to use the core conformance engine
- [x] Retire duplicated standalone conformance logic once parity is confirmed

### Phase 4 and Future Enhancements

Phase 4 advanced semantic rules, future enhancements, and remaining deferred items are tracked in [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Testing Strategy

### Current coverage

- `tests/model/test_target_model_conformance.py` — 11 tests, 98% branch coverage of `src/target_model/conformance.py`
- ~~`target_models/tests/` — standalone spec and example-project tests (still using the pre-core-integration path)~~

### Remaining test areas

Test coverage gaps are tracked in [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Open Technical Questions

Open technical questions (target model loading location, validation code naming, rule disabling) are tracked in [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).
