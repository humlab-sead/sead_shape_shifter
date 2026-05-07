---
applyTo: "src/specifications/**,tests/test_constraints*,tests/project/**"
---

# Specifications – AI Coding Instructions

## Architecture

Specifications live in `src/specifications/` — pure Core with no backend imports.

| File | Purpose |
|------|---------|
| `base.py` | `Specification`, `ProjectSpecification`, `SpecificationIssue` base classes |
| `entity.py` | Per-entity field validators; `ENTITY_SPECIFICATION` and `ENTITY_TYPE_SPECIFICATION` registries |
| `project.py` | Cross-entity specs: circular dependencies, data source existence, FK consistency |
| `fields.py` | Field-level checks used by entity specs (type, presence, membership) |
| `constraints.py` | Constraint validation rules |
| `foreign_key.py` | FK configuration integrity |
| `materialize.py` | `CanMaterializeSpecification` — pre-flight check before materialization |
| `fd.py` | Functional dependency checks |

## Base Classes

- `Specification` — abstract; `is_satisfied_by(**kwargs) -> bool`; accumulates `errors` and `warnings` as `list[SpecificationIssue]`.
- `ProjectSpecification(Specification)` — takes `project_cfg: dict[str, Any]` in constructor; helpers: `get_entity_cfg()`, `get_entity()`, `entity_exists()`.
- `SpecificationIssue` — carry `severity` (`"error"` / `"warning"`), `message`, optional `entity`, `field`, `column`.

## Composable Pattern

- `CompositeProjectSpecification` aggregates all individual specs in its `__init__()`.
- To add a new project-level check: subclass `ProjectSpecification`, implement `is_satisfied_by()`, add to `CompositeProjectSpecification.__init__()`.
- Merge results from sub-specs with `self.merge(sub_spec)`.

## Entity Type Registries

- `@ENTITY_TYPE_SPECIFICATION.register(key="entity")` — runs for `type: entity` entities.
- `@ENTITY_TYPE_SPECIFICATION.register(key="other")` — base rules applied when no type-specific spec is registered.
- Add a new entity type validator by registering with the appropriate key.

## `CanMaterializeSpecification`

Three preconditions that must all pass before materialization:
1. Entity must not be `type: fixed`.
2. Entity must not already be `is_materialized`.
3. All dependencies (FKs + `depends_on`) must be either `type: fixed` or already materialized.

Call this spec in the backend service before writing the materialized snapshot; never skip it.

## Common Mistakes

- Importing `backend.*` inside any `src/specifications/` file — these are pure Core.
- Raising exceptions from `is_satisfied_by()` instead of calling `add_error()` and returning `False`.
- Calling `is_satisfied_by()` without calling `clear()` first when reusing a spec instance — always call `clear()` at the top of `is_satisfied_by()`.
- Adding a new entity type without registering it in `ENTITY_TYPE_SPECIFICATION`.
- Skipping `CanMaterializeSpecification` before materializing an entity.

## Testing Expectations

- Pass a plain `dict` as `project_cfg` — no file loading needed.
- Test each spec's `errors` and `warnings` lists directly after `is_satisfied_by()`.
- Test error cases: missing fields, wrong types, circular deps, duplicate keys.
- Test `CanMaterializeSpecification` with `type: fixed` (should fail), already-materialized (should fail), non-materialized dep (should fail).
