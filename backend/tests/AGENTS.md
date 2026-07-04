# `backend/tests/` — Agent Guide

Tests in this directory cover the FastAPI backend (`backend/app/`): endpoints, services, mappers, validators, and integrations.

> Also read the root [`AGENTS.md`](../../AGENTS.md) and [`backend/AGENTS.md`](../AGENTS.md) for cross-cutting architecture and backend-specific rules.

## Run commands

```bash
uv run pytest backend/tests -v                          # full backend suite
uv run pytest backend/tests/services -v                 # one subdirectory
uv run pytest backend/tests/test_data_source_api.py -v  # one file
make test                                               # full suite (Core + backend)
```

## Test patterns

- Use `TestClient` (from `starlette.testclient`) for route and endpoint tests.
- Use `@pytest.mark.asyncio` for async service, orchestrator, and client tests.
- Mock `ProjectService` and `ShapeShifter` in unit tests — do not run the full pipeline in endpoint tests.
- Test each data fetch strategy independently by mocking the underlying service call.
- Mock HTTP clients (`httpx.AsyncClient`, SIMS client, OpenRefine client) at the client class level — do not make real network calls in tests.
- Never import `src.*` test helpers from backend tests if those helpers depend on backend infrastructure.
- Use absolute imports: `from backend.app...`.

## Shared fixtures

- `conftest.py` at this level provides app setup, test project configs, and commonly mocked services.
- `test_data/` holds static JSON, YAML, and CSV files used by multiple tests.
- Prefer inline dicts and small DataFrames over file loading for simple unit tests.

## Directory structure

| Directory / file | What it tests |
|---|---|
| `api/` | Endpoint request/response, routing, and HTTP status codes |
| `integration/` | Cross-layer flows (endpoint → service → Core) with minimal mocking |
| `ingesters/` | Ingester implementations registered in `backend/` |
| `mappers/` | `ProjectMapper` conversions between API and Core models |
| `models/` | Pydantic model validation and serialization |
| `scripts/` | CLI script behaviour |
| `services/` | Service layer logic (validation, materialization, reconciliation, etc.) |
| `specifications/` | Backend-layer specification checks |
| `utils/` | Backend utility helpers |
| `validators/` | Backend validators (`backend/app/validators/`) |
| `test_data_source_api.py` | Data source endpoint |
| `test_env_var_resolution.py` | Directive and env-var resolution in `ProjectMapper` |
| `test_reconciliation_client.py` | OpenRefine reconciliation client |
| `test_state_manager.py` | State manager service |
| `test_suggestions.py` | Suggestion service |

## Key mock boundaries

| Component | How to mock it in tests |
|---|---|
| `ProjectService` | Mock the service instance; inject via FastAPI dependency override |
| `ShapeShifter` | Mock `normalize()` return value; do not run the full pipeline in endpoint tests |
| SIMS client | Mock `backend/app/clients/sims_client.py`; use env var `SHAPE_SHIFTER_SIMS_SERVICE_URL` |
| OpenRefine client | Mock `httpx.AsyncClient` calls on `ReconciliationClient` |
| Data fetch strategies | Mock the `PreviewDataFetchStrategy`, `FullDataFetchStrategy`, and `TableStoreDataFetchStrategy` independently |

## Scope boundaries

- Tests here validate backend (`backend/app/`) logic only.
- Core pipeline unit tests belong in `tests/`.
- Frontend tests belong in `frontend/tests/`.
- Integration tests that require a real database or running service are in `integration/`; mark them clearly so they can be skipped in CI when the service is unavailable.
