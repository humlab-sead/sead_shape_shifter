# DuckDB Internal SQL Loader

## Status

- Proposed feature / change request (implemented on branch `add-duckdb-loader`)
- Scope: `src/loaders/duckdb_loader/`, `src/normalizer.py`, `src/loaders/base_loader.py`, `src/table_store.py`
- Goal: Enable entities to be defined using SQL queries over already-resolved entities

## Summary

Add a DuckDB-backed loader that exposes Shape Shifter's in-memory entity store as a SQL-queryable workspace. This allows an entity to be derived from one or more previously processed entities using a plain SQL query, without requiring an external database.

A supporting change — a `DataLoader.create()` factory classmethod — decouples loader instantiation from `ShapeShifter`, so no loader-specific branching is needed in the orchestrator.

## Problem

Currently, an entity's source must be a single upstream entity or an external data source. There is no way to express a derived entity that joins, aggregates, or filters across multiple already-processed entities using SQL. The only workaround is to push this logic into `extra_columns` expressions or into the ingester, both of which scale poorly for non-trivial cross-entity logic.

## Scope

- A new `DuckDbLoader` (`type: duckdb`) that executes a SQL query over the current table store.
- A `DuckDbWorkspace` that wraps a persistent in-memory DuckDB connection and registers entity DataFrames as views.
- Hook wiring in `TableStore` so DuckDB views stay in sync automatically as entities are added.
- A `DataLoader.create()` factory classmethod so loaders that need runtime context can receive it without burdening `ShapeShifter` with loader-specific logic.

## Non-Goals

- Persistent DuckDB file storage (in-memory only for now).
- Replacing existing loaders or the standard `source:` mechanism.
- Exposing DuckDB queries to the frontend or API surface.
- Query optimisation or caching across entities.

## Current Behavior

`ShapeShifter.resolve_loader()` calls `DataLoaders.get(key=...) (data_source=...)` uniformly. All loaders are constructed with just a `DataSourceConfig`. Loaders that need runtime state (e.g., a live connection or shared workspace) have no standard way to receive it.

`TableStore` is a plain `dict[str, pd.DataFrame]`; nothing is notified when an entity is stored.

## Proposed Design

### TableStore hooks

`TableStore` is now a `dict` subclass with `add_on_set_hook` and `add_on_delete_hook`. Hooks fire whenever an entity is assigned or deleted. `ShapeShifter` registers `DuckDbWorkspace.register_entity` as an on-set hook (with `replay=True` so existing entries are registered immediately). DuckDB views therefore stay current without any manual sync step.

### DuckDbWorkspace

A thin wrapper around a `duckdb.DuckDBPyConnection`. DataFrames are registered as zero-copy views (not copied into DuckDB storage). A per-entity object-id cache avoids redundant re-registration when the same DataFrame object is stored again.

### DuckDbLoader

Registered under keys `duckdb`, `internal`, and `shape_store`. An entity configured with `type: duckdb` and a `query:` field is loaded by executing that query against the workspace. The full column detection and validation pipeline from `SqlLoader` is reused.

Example entity configuration:

```yaml
derived_summary:
  type: duckdb
  depends_on: [site, sample]
  query: |
    SELECT s.site_name, COUNT(sa.sample_id) AS sample_count
    FROM site s
    JOIN sample sa ON sa.site_id = s.system_id
    GROUP BY s.site_name
  columns: [site_name, sample_count]
  keys: [site_name]
```

### DataLoader.create() factory

`DataLoader` gains a classmethod:

```python
@classmethod
def create(cls, data_source: DataSourceConfig | None, **context: Any) -> "DataLoader":
    return cls(data_source=data_source)
```

`DuckDbLoader` overrides it:

```python
@classmethod
def create(cls, data_source: DataSourceConfig | None, **context: Any) -> "DuckDbLoader":
    return cls(data_source=data_source, workspace=context["workspace"], table_store=context["table_store"])
```

`ShapeShifter.resolve_loader()` now reads:

```python
context = {"workspace": self.duckdb_workspace, "table_store": self.table_store}

if table_cfg.data_source:
    data_source = self.project.get_data_source(table_cfg.data_source)
    return DataLoaders.get(key=data_source.driver).create(data_source=data_source, **context)

if table_cfg.type and table_cfg.type in DataLoaders.items:
    return DataLoaders.get(key=table_cfg.type).create(data_source=None, **context)
```

No `issubclass` check, no `DuckDbLoader` import in the orchestrator. All loaders receive the same `context`; each picks what it needs.

## Risks And Tradeoffs

**DuckDB blocks the event loop.** `duckdb`'s Python API is synchronous. `DuckDbLoader.read_sql` is `async` for API conformance but does not yield. For large queries over large DataFrames this will stall the event loop. Mitigation: wrap with `asyncio.to_thread` if this becomes a problem in practice.

**`context` is untyped at the call site.** A loader that overrides `create` and requests a missing key will raise `KeyError` at runtime, not at type-check time. This is acceptable given the small number of loaders, but would need attention if the pattern spreads widely.

**`depends_on` is required for correctness.** The DuckDB workspace is kept in sync by hooks, but if a query references an entity not yet processed, it will see an empty or missing view. The user must declare `depends_on` correctly; there is no automatic validation that query references match declared dependencies.

**In-memory only.** Large projects with many large entities will accumulate all DataFrames in memory simultaneously (as views, not copies). This was already true of the table store itself, so no regression, but it limits scalability.

## Testing And Validation

- Unit tests for `DuckDbWorkspace`: register, re-register, unregister, query.
- Unit tests for `DuckDbLoader.load()`: correct query execution, column detection, `system_id` injection.
- Unit tests for `DataLoader.create()` default and the override in `DuckDbLoader`.
- Integration test: a project with a `type: duckdb` entity that joins two upstream entities and produces correct output end-to-end through `normalize()`.

## Acceptance Criteria

- An entity with `type: duckdb` and a valid SQL `query:` loads correctly during `normalize()`.
- Entities not yet processed are absent from the workspace; the query fails with a clear error if `depends_on` is missing.
- `ShapeShifter.resolve_loader()` contains no loader-specific branching.
- All existing tests pass unchanged.

## Open Questions

- Should `depends_on` be validated against query references (e.g., via `EXPLAIN`) to catch missing declarations early?
- Should the workspace support a file-backed DuckDB path for projects where in-memory size is a constraint?

## Final Recommendation

Proceed. The DuckDB loader fills a genuine gap (cross-entity SQL derivation) with low coupling. The `create()` factory is a small, reversible pattern improvement that pays for itself immediately and leaves the orchestrator clean for future loaders.
