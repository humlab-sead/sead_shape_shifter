---
applyTo: "backend/app/services/materialization*,backend/app/api/v1/endpoints/materialization*,src/specifications/materialize.py,backend/tests/specifications/test_materialization*,tests/specifications/test_materialize.py"
---

# Materialization – AI Coding Instructions

## What Materialization Does

Materialization replaces a dynamic entity with a saved `type: fixed` snapshot of its rows.

After materialization, the entity config in YAML has:
- `type: fixed`, with `public_id`, `keys`, `columns` (data columns only) and `column_types` when needed.
- `values`: inline rows, or an `@load:` reference to a sidecar file (CSV or Parquet).
- `materialized` with `enabled: true`, `source_state` (the previous entity config) and `materialized_at`.

`TableConfig.is_materialized` is `True`. Use it to tell a materialized snapshot apart from a hand-written fixed entity.

## Materialization Lifecycle (`MaterializationService.materialize_entity()`)

1. `CanMaterializeSpecification.is_satisfied_by(entity=...)` must pass.
2. `ShapeShifter(project=..., target_entities={entity}).normalize()` runs.
3. `_prepare_materialized_values()` sanitizes the data, normalizes it to the fixed-entity column order, infers column types and serializes the rows.
4. Storage: rows are stored inline when the caller asks for `inline` or the row count is below `MATERIALIZATION_INLINE_THRESHOLD`. Otherwise `values` becomes `@load:materialized/{entity}.{csv|parquet}` and `EntityValuesService.update_values()` writes the file.
5. `_create_materialized_entity()` builds the new config and the project is saved. With external storage the project is saved before the data file is written.

## Unmaterialization (`unmaterialize_entity()`)

- Fails if the entity is not materialized.
- Fails if other materialized entities depend on it, unless `cascade=True`, which unmaterializes the dependents first.
- Replaces the entity config with `materialized.source_state` and saves the project.
- Does not delete the sidecar data file.

## Sidecar Files

- Path: `materialized/{entity_name}.{extension}` relative to the project folder, built by `_get_materialized_file_path()`.
- The path is recorded only in the `values: "@load:..."` reference.

## Cascading Dependencies

Before materializing an entity, check all its FK dependencies and `depends_on` entries:
- Dependency must be `type: fixed` OR already `is_materialized` — enforced by `CanMaterializeSpecification`.
- Do not short-circuit this check even for simple entities.

## `_sanitize_materialized_dataframe()`

Always call before persisting. Removes:
- Columns starting with `_merge_indicator_` (merge join helper columns).
- Duplicate column labels (keeps first occurrence). It does not remove duplicate rows.

## Common Mistakes

- Skipping `CanMaterializeSpecification` before running the pipeline.
- Not calling `_sanitize_materialized_dataframe()` — merge indicators will corrupt the fixed entity.
- Hard-coding the sidecar path instead of using `_get_materialized_file_path()`.
- Using `type == "fixed"` to detect a materialized entity. Check `is_materialized`.
- Dropping or editing `materialized.source_state`; unmaterialization restores the entity from it.

## Testing Expectations

- Mock `ProjectService` and `ShapeShifter` — do not run a full pipeline in unit tests.
- Test `CanMaterializeSpecification` pre-conditions: fixed entity (fail), already-materialized (fail), non-materialized dep (fail).
- Test `_sanitize_materialized_dataframe()` with merge indicator columns and duplicate labels.
- Test unmaterialization: the config is restored from `source_state` and the `materialized` block is gone.
- Use `pytest.mark.asyncio` for all async service tests.
