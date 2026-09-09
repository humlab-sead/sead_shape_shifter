# Shape Shifter – Core (`src/`) Agent Rules

Rules here apply when working in `src/`. Also read the root `AGENTS.md` for cross-cutting rules.

## Pipeline

- Immutable stage order: **Extract → Filter → Link → Unnest → Translate → Store**.
- `ShapeShifter.normalize()` is async — never call with `asyncio.run()`.
- `ProcessState.get_next_entity_to_process()` may return `None` when circular deps remain — always handle `None`.
- Never modify `table_store` from outside `ShapeShifter` during a run.
- Loaders are resolved per-entity via `resolve_loader()` — never pre-load all entities upfront.

## Entity System

- Three identity tiers: `system_id` (FK values), `keys` (dedup), `public_id` (target column name, must end `_id`).
- FK child column name = parent's `public_id` name; FK values = parent's `system_id` — never external IDs.
- Entity types: `entity` (row-extract), `fixed` (inline lookup), `sql` (query), `merged` (multi-branch). Classifiers must use `fixed` or `sql`, not `entity`.
- Merged entities: each branch gets a `{entity}_branch` discriminator column and sparse nullable `Int64` FK columns for all other branches.
- `defer_dependency: true` breaks circular FK chains; it is not a general ordering tool — only use for genuine cycles.
- Always use `table_cfg.get_target_facing_columns()` and `table_cfg.get_target_facing_foreign_key_targets()` — never access `table_cfg.columns` directly.

## Transforms

- **Filter**: runs on raw source DataFrame — FK-added columns are not yet available. Never reference post-link columns.
- **Extra columns**: four modes in order: DSL formula (`=`), column copy, interpolated string (`{col}`), constant. If a referenced column doesn't exist, defer — do not raise.
- **Replace**: three forms: advanced rule list, mapping, legacy scalar/list. Never mix forms per column. `ffill` applies only to the legacy form.
- **Unnest**: `id_vars` and `value_vars` must exist at unnest time — raises `ValueError` if missing. Skips silently if `value_name` already exists as a column.
- DSL functions allowlist: `concat`, `upper`, `lower`, `trim`, `substr`, `coalesce` — no others.

## Specifications (`src/specifications/`)

- Pure Core — zero `backend.*` imports permitted.
- Subclass `ProjectSpecification`, implement `is_satisfied_by()` calling `add_error()` / `add_warning()` — never raise exceptions.
- Call `clear()` at the top of `is_satisfied_by()` when reusing an instance.
- Add new project-level specs to `CompositeProjectSpecification.__init__()` and merge results with `self.merge(sub_spec)`.
- `CanMaterializeSpecification` must pass before any materialization — never skip it.

## Validators (`src/validators/`)

- Pure functions: accept `pd.DataFrame` and config, return `list[ValidationIssue]` — no I/O, no side effects.
- Never import `backend.*` from `src/validators/`.
- `ValidationIssue` carries: `entity_name`, `column_name` (optional), `message`, `severity` (`error` / `warning`).

## Data Loaders (`src/loaders/`)

- Every loader must implement `async def load(...)` and `async def test_connection()` — never synchronous.
- Schema declared as `ClassVar[DriverSchema]` on the class — not an instance attribute.
- Register with `@DataLoaders.register(key="<driver_key>")` — key must match the YAML `driver` name exactly.
- `test_connection()` must always return `ConnectTestResult` — never raise on failure.
- UCanAccess: call `init_jvm_for_ucanaccess()` once at startup — never inside `load()`.

## Target Model (`src/target_model/`)

- Pure Core — zero `backend.*` imports.
- Conformance validators receive already-resolved `TargetModel` + `ShapeShiftProject`. They never fetch data or files.
- `@include:` in `metadata.target_model` is resolved by `ProjectMapper.to_core()` — Core always receives an expanded `dict`.
- A project without `metadata.target_model` is not an error — return an empty valid result.

## Testing

- Construct `ShapeShiftProject(cfg={...})` directly from dicts — no file loading, no backend.
- `@pytest.mark.asyncio` for all async Core tests.
- Test domain validators with inline DataFrames — no project file, no DB.
- Test `test_connection()` for both success and failure paths.
