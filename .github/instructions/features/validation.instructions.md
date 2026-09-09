---
applyTo: "src/validators/**,backend/app/validators/**,backend/app/services/validation*,tests/test_constraints*,backend/tests/test_validation*"
---

# Validation – AI Coding Instructions

## Three-Tier Validation Model

| Tier | Location | Responsibility |
|------|----------|---------------|
| Structural | `src/specifications/` | Config structure, FK integrity, dependency graph |
| Constraint | `src/validators/`, `src/constraints.py` | Business rules, cardinality, keys, data types |
| Data | `src/validators/data_validators.py` + backend orchestrator | Row-level data checks against actual DataFrames |

Run structural and constraint validation before data validation — structural errors may prevent data from loading.

## Pure Domain Validators (`src/validators/`)

- Validators receive `pd.DataFrame` and config — they **never fetch data**.
- Return `list[ValidationIssue]` — not API DTOs, not exceptions.
- `ValidationIssue` carries: `entity_name`, `column_name` (optional), `message`, `severity` (`error` / `warning`).
- Validators are pure functions — no side effects, no I/O.
- Current validators: `ColumnExistsValidator`, `DataTypeCompatibilityValidator`, `ForeignKeyDataValidator`, `ForeignKeyIntegrityValidator`, `NaturalKeyUniquenessValidator`, `NonEmptyResultValidator`, `UnresolvedExtraColumnsValidator`.

## Constraint Validators (`src/constraints.py`)

- Registered with `@CONFORMANCE_VALIDATORS.register(key="...")` or `@Validators.register(key=..., stage=...)`.
- Receive `data` and `config` — no DB, no HTTP.
- Return domain issues; the caller converts to API responses.

## Data Validation Orchestrator (`backend/app/validators/data_validation_orchestrator.py`)

- Lives in backend — has access to infrastructure (HTTP, DB, file I/O).
- Uses injected `DataFetchStrategy` — three implementations:
  - `PreviewDataFetchStrategy` — sample rows via `ShapeShiftService.preview_entity()`
  - `FullDataFetchStrategy` — complete normalized run via `ShapeShifter`
  - `TableStoreDataFetchStrategy` — reads from an in-memory `table_store`
- Calls pure domain validators with fetched DataFrames.
- Returns `list[ValidationIssue]` — consumer converts to API errors.
- Inject the strategy via constructor — never hard-code which strategy to use.

## Layer Boundary Rules

- `src/validators/` must not import `backend.*` — ever.
- `backend/app/validators/` may import `src/validators/` for domain validators.
- `ValidationService` loads the project, converts via `ProjectMapper.to_core()`, then creates orchestrator and strategy — all in the backend layer.
- Never put data fetching logic inside a `src/validators/` class.

## Common Mistakes

- Importing `backend.*` from inside `src/validators/` — hard layer violation.
- Returning API error models from a domain validator instead of `ValidationIssue`.
- Fetching data inside a validator — pass the DataFrame in.
- Creating `DataValidationOrchestrator` without injecting a strategy — always inject explicitly.
- Skipping structural validation and running data validation on an invalid config.
- Using the wrong strategy for the context: preview strategy for full-dataset rules produces false negatives.

## Testing Expectations

- Unit-test domain validators with inline DataFrames — no project file, no backend.
- Test each strategy independently (mock the underlying service).
- Test the orchestrator with a `TableStoreDataFetchStrategy` backed by in-memory DataFrames.
- Use `pytest.mark.asyncio` for orchestrator tests (fetch strategies are async).
- Structural validators (`src/specifications/`) take a `project_cfg` dict — no DB or HTTP needed.
