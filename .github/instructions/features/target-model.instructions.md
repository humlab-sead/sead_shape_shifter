---
applyTo: "src/target_model/**,backend/app/validators/target_model_validator.py,backend/app/services/validation_service.py,tests/model/test_target_model*"
---

# Target Model Conformance – AI Coding Instructions

## Architectural Boundaries

- `src/target_model/` is pure Core — zero backend/API imports permitted.
- Conformance validators receive `TargetModel` (Pydantic) + `ShapeShiftProject` (already resolved). They never fetch data or files.
- `@include:` in `metadata.target_model` is resolved by `ProjectMapper.to_core()` at the API→Core boundary. Core always receives an expanded `dict`, never a file path.
- `TargetModelValidator` (backend adapter) is the only component that converts `ConformanceIssue` → `ValidationError` and touches `ValidationCategory.CONFORMANCE`.
- `ValidationService.validate_target_model()` owns loading, resolving, and delegating. It never constructs `TargetModel` objects itself.

## Required Invariants

- Always call `table_cfg.get_target_facing_columns()` and `table_cfg.get_target_facing_foreign_key_targets()` to inspect project output — **never** access `table_cfg.columns` directly. Materialized entities are treated as fixed views and only expose their explicit `columns` list as target-facing.
- Conformance is **additive and optional**: structural validation runs first; conformance adds `ValidationCategory.CONFORMANCE` issues.
- A project without `metadata.target_model` is not an error — return an empty valid `ValidationResult`.
- `guard()` skips entities absent from the project — this is expected, not a bug.
- Only FK specs with `required: true` generate `MISSING_REQUIRED_FOREIGN_KEY_TARGET` issues.
- For bridge FKs (`via:`): check source→bridge FK first; if missing, stop. Then check bridge→ultimate target (advisory, code `BRIDGE_MISSING_TARGET_FK`).
- `TargetModelSpecValidator` validates the spec file itself for self-consistency (e.g. FK references unknown entity, identity column not in columns dict). Run this before conformance in new tooling.

## Registered Conformance Validators

| Key | Class | What it checks |
|-----|-------|----------------|
| `required_entity` | `RequiredEntityConformanceValidator` | All `required: true` entities are present in project |
| `public_id` | `PublicIdConformanceValidator` | `public_id` matches spec (present + correct name) |
| `foreign_key` | `ForeignKeyConformanceValidator` | Required FK targets present; bridge chain intact |
| `required_columns` | `RequiredColumnsConformanceValidator` | Required target-facing columns declared |
| `naming_convention` | `NamingConventionConformanceValidator` | `public_id` ends with `naming.public_id_suffix` |
| `induced_requirements` | `InducedRequirementConformanceValidator` | Entities pulled in by required FKs are also present |
| `source_type_appropriateness` | `SourceTypeAppropriatenessConformanceValidator` | Classifiers use `fixed` or `sql`, not `entity` |

New validators must be decorated `@CONFORMANCE_VALIDATORS.register(key="...")` and extend `ConformanceValidator` or `EntityConformanceValidator`.

## Common Mistakes

- Accessing `table_cfg.columns` directly — skips materialized entity logic.
- Calling `TargetModelConformanceValidator` with an unresolved project (e.g. before `ProjectMapper.to_core()`).
- Importing anything from `backend.app` inside `src/target_model/`.
- Mixing conformance issues into structural or data validation categories.
- Raising exceptions for a missing `target_model` field — always return empty valid result.
- Skipping `TargetModelSpecValidator` when loading a new target model file; malformed specs produce confusing conformance noise.

## Testing Expectations

- Core conformance tests: construct `ShapeShiftProject` and `TargetModel` inline from dicts; no mocks, no DB, no API.
- Use the `issue_pairs(target_model, project) → list[tuple[code, entity]]` pattern for concise assertions.
- Test both clean (zero issues) and each specific issue code.
- Backend adapter tests: test `TargetModelValidator.validate(dict, project)` in isolation; do not spin up `ValidationService`.
- Fixture YAMLs live in `tests/test_data/examples/`; the reference spec is `tests/test_data/specs/sead_standard_model.yml`.

## Forbidden Shortcuts

- Do not fetch files or data inside any `ConformanceValidator`.
- Do not import `backend.app.*` from `src/target_model/`.
- Do not add conformance issues to `ValidationCategory.STRUCTURAL` or `ValidationCategory.DATA`.
- Do not bypass `get_target_facing_*` APIs by reading raw entity config dicts.
- Do not treat a missing target model as a validation failure at any layer.
