---
applyTo: "src/model.py,src/specifications/**,backend/app/services/entity*,frontend/src/components/entities/**,tests/model/**"
---

# Entity System – AI Coding Instructions

## Three-Tier Identity System

Every entity uses three distinct identity concepts. Never conflate them.

| Tier | Field | Purpose | Used for FKs? |
|------|-------|---------|--------------|
| 1 | `system_id` | Local sequential integer (1, 2, 3…) | **Yes** — all FK values are `system_id` |
| 2 | `keys` | Business keys for deduplication/matching | No |
| 3 | `public_id` | Target schema column name; holds SEAD IDs after mapping | No (naming only) |

- FK child column name = parent's `public_id` name
- FK child column values = parent's `system_id` values
- `public_id` must end with `_id`
- `map_to_remote()` decorates `public_id` with remote SEAD IDs — separate from FK linking

## Entity Types and Roles

- `type: entity` — row-extraction from a data source (default)
- `type: fixed` — pre-loaded lookup; columns declared inline; no data source
- `type: sql` — loaded via SQL query
- `type: merged` — aggregates multiple sub-entity branches; adds discriminator column and sparse FKs

Classifiers should use `type: fixed` or `type: sql` — using `type: entity` for a classifier is a modelling mistake.

## Merged Entities

- Each branch gets a discriminator column (e.g. `analysis_entity_branch`) with the branch name as value.
- Sparse FK columns are added per branch (nullable `Int64`) — all other branches get `pd.NA` for that FK.
- Source `system_id` is dropped from branches before merge.
- Branch lineage column naming: `{parent_entity}_branch`.
- When a fixed entity has `public_id` as a column name, `ForeignKeyMergeSetup` must deduplicate columns — never add `public_id` twice.

## Circular / Deferred Dependencies

- Use `defer_dependency: true` on a FK config to break circular dependency chains.
- `ProcessState.get_next_entity_to_process()` skips entities with unmet dependencies — deferred FKs are retried via `DeferredLinkingTracker` after the main topological pass.
- `CircularDependencySpecification` detects cycles; `defer_dependency` is the sanctioned workaround, not a spec bypass.

## `TableConfig` API

- `table_cfg.get_target_facing_columns()` — columns visible in output (respects materialized/fixed)
- `table_cfg.get_target_facing_foreign_key_targets()` — FK targets visible in output
- `table_cfg.depends_on` — set of entity names this entity depends on (drives topological sort)
- Never read `table_cfg.columns` directly for conformance or validation — always use the `get_target_facing_*` methods

## Common Mistakes

- Using external IDs (SEAD IDs) as FK values — FK values must be `system_id`.
- Setting `public_id` to a value not ending in `_id`.
- Using `type: entity` for a classifier entity.
- Adding a merged branch without a discriminator column — always call `_process_merged_branch()`.
- Assuming `system_id` is stable across runs — it is local and sequential only.
- Forgetting to set `defer_dependency: true` on circular FK references; topological sort will deadlock.

## Testing Expectations

- Construct `ShapeShiftProject(cfg=...)` directly from dicts — no mapper, no DB.
- Test the three-tier identity system with explicit `system_id`, `keys`, and `public_id` fields.
- Test merged entity branch handling: discriminator column present, sparse FK columns nullable.
- Test `defer_dependency` path: circular FKs should not raise; deferred linker resolves them.
