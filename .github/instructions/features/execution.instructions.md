---
applyTo: "src/normalizer.py,src/process_state.py,src/workflow.py,src/shapeshift.py,tests/process/**,tests/integration/**"
---

# Execution Pipeline – AI Coding Instructions

## Pipeline Order (Immutable)

```
Extract → Filter → Link → Unnest → Translate → Store
```

This order is enforced in `ShapeShifter.normalize()`. Never reorder stages. Each stage receives the output of the previous one.

## Orchestrator: `ShapeShifter`

- Entry point: `ShapeShifter(project).normalize()` — async.
- Holds `table_store: dict[str, pd.DataFrame]` — the mutable output accumulator. An entity is "processed" the moment its DataFrame is added here.
- `ProcessState` is constructed once per run; `table_store` is shared by reference between `ShapeShifter` and `ProcessState`.
- Loaders are resolved per-entity via `resolve_loader()` — never pre-load all entities.

## Topological Sort: `ProcessState`

- `get_next_entity_to_process()` scans `unprocessed_entities` and returns the first one with no unmet dependencies.
- `depends_on` is the authoritative dependency set for an entity — includes FK targets and explicit `depends_on` list.
- If `get_next_entity_to_process()` returns `None` but `unprocessed_entities` is non-empty, the remaining entities have circular dependencies. Check `defer_dependency` flags before raising.
- Never modify `table_store` from outside `ShapeShifter` during a run.

## Deferred Linking: `DeferredLinkingTracker`

- Entities with `defer_dependency: true` on a FK config are registered in `DeferredLinkingTracker`.
- The main loop processes all non-deferred entities first, then `DeferredLinkingTracker.retry()` processes deferred FKs.
- A deferred FK links **after** the target entity is in `table_store` — order is safe.
- Do not use `defer_dependency` as a general workaround for ordering issues; it is for genuine circular dependencies only.

## Merged Entity Branches

- `_process_merged_branch()` is called inside `get_subset()` for `type: merged` entities.
- Each branch gets: discriminator column (`{entity}_branch` = branch name), sparse nullable `Int64` FK columns for all other branches.
- Source `system_id` is dropped from branches.
- Branch DataFrames are concatenated with `pd.concat(..., ignore_index=True)` — columns are unioned, missing values are `pd.NA`.

## Local File Resolution

- `_resolve_project_local_file_options()` rewrites relative `filename` paths when `location: local`.
- This runs at load time, not at config parse time.
- Uses `resolve_managed_file_path()` — do not construct paths manually.

## Common Mistakes

- Awaiting `normalize()` from a synchronous context — it is `async`.
- Checking `table_store` for entity existence before `ShapeShifter` has processed it.
- Assuming `unprocessed_entities` is ordered — it is a set.
- Adding a new pipeline stage by inserting code in the loop instead of adding a dedicated transform function.
- Calling `get_next_entity_to_process()` without checking for `None` — always handle the `None` case.
- Using `defer_dependency` on non-circular FKs — it delays linking and can silently produce nulls.

## Testing Expectations

- Use `ShapeShiftProject(cfg={...})` and pass it directly to `ShapeShifter`.
- Test with minimal configs: one entity with a loader, one with a source reference, one merged.
- Test deferred linking: verify FK columns resolve after the main loop.
- Test topological ordering: entity B depends on A — A must appear in `table_store` before B processes.
- Use `pytest.mark.asyncio` for all tests that call `normalize()`.
