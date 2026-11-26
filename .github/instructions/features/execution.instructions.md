---
applyTo: "src/normalizer.py,src/process_state.py,src/workflow.py,src/shapeshift.py,tests/process/**,tests/integration/**"
---

# Execution Pipeline – AI Coding Instructions

## Pipeline Order (Immutable)

```
Extract → Filter → Link → Unnest → Translate → Store
```

Never reorder these stages. `ShapeShifter.normalize()` covers Extract to Unnest for one entity at a time. Translate and Store are separate steps that run on the whole `table_store` after `normalize()` (see `src/workflow.py`).

## Stage Map

| Stage | What it does | Detailed rules |
| --------- | -------------------------------------------------------------------- | ------------------------------------- |
| Extract | Loads source data through the registered loader, selects columns, applies `replacements`, and adds append and merged-branch rows | `features/loaders.instructions.md` |
| Filter | Applies `filters`. Each filter names a stage: `extract` (default), `after_link` or `after_unnest` | `features/transforms.instructions.md` |
| Link | Adds FK columns (parent `public_id` name, parent `system_id` values) | `features/entities.instructions.md` |
| Unnest | Melts `value_vars` into long form via `pd.melt()` | `features/transforms.instructions.md` |
| Translate | Renames columns using the project `translation` option; runs only when translation is requested | this file |
| Store | `ShapeShifter.store()` writes the tables to the output target | this file |

## Order Inside `_process_entity()`

1. Build the entity data (`get_subset()`): load, select columns, apply `replacements`, concatenate append items or merged branches.
2. Evaluate `extra_columns`. Entries with missing inputs are deferred. Extraction also makes a first attempt.
3. Apply `extract` filters, then `drop_duplicates` (delayed when it depends on unnest output).
4. Link foreign keys, retry deferred `extra_columns`, apply `after_link` filters.
5. If the entity has `unnest`: unnest, retry `extra_columns`, link again (`after_unnest` pass), retry `extra_columns`, apply `after_unnest` filters.
6. Run delayed `drop_duplicates`, check duplicate keys, apply `drop_empty_rows` if not already applied.
7. Add `system_id` and the `public_id` column, then apply committed mapping sidecar links.
8. Retry deferred foreign keys, verify `extra_columns`, reorder columns.

## Column Availability

| Point | Available columns |
| ----- | ----------------- |
| `extract` filters | Source columns and the `extra_columns` whose inputs already exist |
| `after_link` filters | The above, plus FK columns (named from parent `public_id`) and `extra_columns` that depend on them |
| `after_unnest` filters | `id_vars`, `var_name`, `value_name`, plus columns added by the later link pass and `extra_columns` retries |
| End of `normalize()` | Final entity columns, including `system_id` and `public_id` |

## Cross-Stage Invariants

- An `extract` filter must not reference FK-added or unnest output columns. Use `after_link` or `after_unnest` for those.
- `extra_columns` may reference columns added by linking or unnest; they are deferred until those columns exist, not an error on the first pass.
- `unnest` `id_vars` and `value_vars` must exist at unnest time — they may be defined as `extra_columns` or FK columns, so do not assume they come from the source.
- `system_id` is assigned per entity and is stable within a run; Core FK values always reference the parent's `system_id`, never external IDs. The change-request package FK declared with `foreign_key_value_sources.<target>: public_id` is the only exception and creates no Core link.

## Orchestrator: `ShapeShifter`

- Entry point: `ShapeShifter(project).normalize()` — async.
- Holds `table_store: TableStore` — the mutable output accumulator, derives from `dict[str, pd.DataFrame]`. An entity is "processed" the moment its DataFrame is added here.
- `ProcessState` is constructed once per run; `table_store` is shared by reference between `ShapeShifter` and `ProcessState`.
- Loaders are resolved per-entity via `resolve_loader()` — never pre-load all entities.

## Topological Sort: `ProcessState`

- `get_next_entity_to_process()` scans `unprocessed_entities` and returns the first one with no unmet dependencies.
- `depends_on` is the authoritative dependency set for an entity — explicit `depends_on`, `source`, non-deferred FK targets, append sources, merged branch sources and filter `other_entity` references.
- If `get_next_entity_to_process()` returns `None` but `unprocessed_entities` is non-empty, the remaining entities have circular dependencies. Check `defer_dependency` flags before raising.
- Never modify `table_store` from outside `ShapeShifter` during a run.

## Deferred Linking: `DeferredLinkingTracker`

- A FK with `defer_dependency: true` is left out of `TableConfig.depends_on`, so it does not affect processing order.
- The linker records entities with unresolved deferred links in `DeferredLinkingTracker.deferred`.
- `ShapeShifter.retry_linking()` retries those entities after each processed entity. `_link_deferred_foreign_keys()` retries again after the main loop (up to 5 passes) and logs a warning if links remain.
- A deferred FK links only when the target entity is in `table_store`.
- Do not use `defer_dependency` as a general workaround for ordering issues; it is for genuine circular dependencies only.

## Merged Entity Branches

- `get_subset()` calls `process_merged_branch()` (`src/transforms/branch.py`) for `type: merged` entities.
- Each branch gets: discriminator column (`{entity}_branch` = branch name) and one nullable `Int64` FK column per branch source. Only the current branch's column has values.
- Source `system_id` is dropped from branches.
- Branch DataFrames are concatenated with `pd.concat(..., ignore_index=True)` — columns are unioned, missing values are `pd.NA`.

## Local File Resolution

- `apply_local_file_options()` in `src/normalizer.py` rewrites relative `filename` paths when `location: local`.
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
