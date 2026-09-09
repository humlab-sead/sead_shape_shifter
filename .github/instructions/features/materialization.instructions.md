---
applyTo: "backend/app/services/materialization*,backend/app/api/v1/endpoints/materialization*,src/specifications/materialize.py,backend/tests/test_materialization*"
---

# Materialization – AI Coding Instructions

## What Materialization Does

Materialization freezes a dynamic entity (type `entity`, `sql`, or `merged`) into a `type: fixed` snapshot stored as a file (Parquet or CSV) alongside the project.

After materialization:
- Entity `type` remains the same in YAML, but `materialized.enabled: true` is set with a `source_state` block.
- The entity is loaded from the materialized file during normalization instead of re-running its pipeline.
- `entity.is_materialized` returns `True` on `TableConfig`.

## Materialization Lifecycle

```
1. CanMaterializeSpecification.is_satisfied_by(entity=...) → must pass
2. ShapeShifter(core_project).normalize() → full pipeline run
3. _sanitize_materialized_dataframe() → strip _merge_indicator_* columns, drop duplicates
4. _normalize_materialized_dataframe() → align to fixed-entity canonical columns (system_id, keys, public_id)
5. EntityPersistenceStrategyRegistry.get_strategy_for_type("fixed").save()
6. Update YAML: set materialized.enabled=true, source_state, file path
7. Save project
```

## Unmaterialization

Reverses step 6: removes `materialized` block from YAML, deletes sidecar file.

- Must verify entity is materialized before attempting (`is_materialized == True`).
- Sidecar file deletion is best-effort — log warning if file missing, do not raise.

## Sidecar File Management

- Files saved to `materialized/{entity_name}.{extension}` relative to the project folder.
- Path is tracked in `materialized.path` in YAML.
- On unmaterialization: delete the sidecar file, clear the `materialized` block.
- On re-materialization: overwrite existing sidecar file.

## Cascading Dependencies

Before materializing an entity, check all its FK dependencies and `depends_on` entries:
- Dependency must be `type: fixed` OR already `is_materialized` — enforced by `CanMaterializeSpecification`.
- Do not short-circuit this check even for simple entities.

## `_sanitize_materialized_dataframe()`

Always call before persisting. Removes:
- Columns starting with `_merge_indicator_` (merge join helper columns).
- Duplicate column labels (keeps first occurrence).

## Common Mistakes

- Skipping `CanMaterializeSpecification` before running the pipeline.
- Not calling `_sanitize_materialized_dataframe()` — merge indicators will corrupt the fixed entity.
- Hard-coding the sidecar path instead of using `_get_materialized_file_path()`.
- Raising on missing sidecar during unmaterialization — log warning and continue.
- Assuming entity type changes to `"fixed"` after materialization — it does not. Check `is_materialized`.

## Testing Expectations

- Mock `ProjectService` and `ShapeShifter` — do not run a full pipeline in unit tests.
- Test `CanMaterializeSpecification` pre-conditions: fixed entity (fail), already-materialized (fail), non-materialized dep (fail).
- Test `_sanitize_materialized_dataframe()` with merge indicator columns and duplicate labels.
- Test unmaterialization: YAML block cleared, sidecar deleted.
- Use `pytest.mark.asyncio` for all service tests.
