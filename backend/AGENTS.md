# Shape Shifter – Backend (`backend/`) Agent Rules

Rules here apply when working in `backend/`. Also read the root `AGENTS.md` for cross-cutting rules.

## Layer Boundary

- API models live in `backend/app/models/`. Domain logic lives in `src/`. Never import `backend.*` from `src/`.
- All API↔Core conversions go through `ProjectMapper.to_core()` — never bypass it.
- Directives (`@include:`, `@value:`, `${ENV_VAR}`) are resolved **only** in `ProjectMapper.to_core()`. The API and YAML layers receive raw strings.
- `ValidationService` owns loading, resolving, and delegating — it never constructs `TargetModel` or domain objects directly.

## Dependency Injection

- Break circular imports with constructor injection or `TYPE_CHECKING` guards — never by restructuring import order.
- Pass the `DataFetchStrategy` to `DataValidationOrchestrator` via its constructor — never hard-code which strategy to use.
- Three fetch strategies: `PreviewDataFetchStrategy`, `FullDataFetchStrategy`, `TableStoreDataFetchStrategy` — choose based on context (preview → sample rows, full → complete run, table store → in-memory).

## Validation Orchestrator (`backend/app/validators/`)

- `DataValidationOrchestrator` lives in the backend — it is the only component that may call infrastructure (HTTP, file I/O).
- Pure domain validators (`src/validators/`) receive DataFrames; the orchestrator fetches and passes them.
- Returns `list[ValidationIssue]`; caller converts to API errors.
- Run structural and constraint validation before data validation — structural errors may prevent data loading.

## Materialization

- Lifecycle: `CanMaterializeSpecification` → `ShapeShifter.normalize()` → `_sanitize_materialized_dataframe()` → persist → update YAML.
- Always call `_sanitize_materialized_dataframe()` before persisting — removes `_merge_indicator_*` columns and duplicate labels.
- Entity `type` does not change after materialization — check `is_materialized`, not `type`.
- Unmaterialization: delete sidecar file (best-effort — log warning if missing, do not raise), clear `materialized` block from YAML.
- Sidecar path: `materialized/{entity_name}.{extension}` relative to project folder — always use `_get_materialized_file_path()`.

## Reconciliation

- `src/reconciliation/` is pure domain — no HTTP, no DB. Backend orchestration goes in `backend/app/services/reconciliation*`.
- Use `determine_strategy()` to pick `TARGET_ENTITY`, `ANOTHER_ENTITY`, or `SQL_QUERY` — never hard-code strategy selection.
- `auto_accept_threshold` ≥ `review_threshold` — use `update_thresholds()` to change both atomically.
- OpenRefine client is a shared async singleton — do not create a new `httpx.AsyncClient` per request.

## Target Model Conformance

- `TargetModelValidator` is the only component that converts `ConformanceIssue` → `ValidationError` and touches `ValidationCategory.CONFORMANCE`.
- New conformance validators: decorate with `@CONFORMANCE_VALIDATORS.register(key="...")` and extend `ConformanceValidator`.
- A project without `metadata.target_model` is not an error — return an empty valid `ValidationResult`.

## Backend Feature Checklist

When adding a new backend feature, update all four layers:
1. Endpoint function in `backend/app/api/v1/endpoints/`
2. Request/response models in `backend/app/models/`
3. Business logic in `backend/app/services/`
4. Router registration in `backend/app/api/v1/api.py`

## Testing

- `TestClient` for route/endpoint tests; mock `ProjectService` and `ShapeShifter` in unit tests.
- `@pytest.mark.asyncio` for all async service and orchestrator tests.
- Test each fetch strategy independently (mock the underlying service).
- Test `CanMaterializeSpecification` preconditions: fixed entity (fail), already-materialized (fail), non-materialized dep (fail).
- SIMS client: `backend/app/clients/sims_client.py` — env var `SHAPE_SHIFTER_SIMS_SERVICE_URL`.
