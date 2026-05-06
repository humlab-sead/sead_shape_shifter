# Shape Shifter - Testing Guide

## Purpose

This guide describes how Shape Shifter is tested: what test levels exist, what each level covers, how to run tests, and what is expected before merging. For local environment setup see [DEVELOPMENT.md](DEVELOPMENT.md). For runtime and deployment see [OPERATIONS.md](OPERATIONS.md).

---

## Audience and Scope

Developers and maintainers who need to understand the testing model, choose the right test level for a new test, run the relevant checks, and interpret failures. The test suite covers the core transformation engine (`src/`), the FastAPI backend (`backend/`), the ingesters (`ingesters/`), and the Vue frontend (`frontend/`).

---

## Testing Goals

- Catch regressions in the transformation pipeline (Extract → Filter → Link → Unnest → Translate → Store).
- Validate that API layer ↔ Core layer boundaries are enforced correctly.
- Ensure configuration validation produces accurate, actionable errors.
- Prevent silent failures in async loaders, foreign key resolution, and merged entity processing.
- Give contributors confidence to change core models and mappers without manual verification for every case.

---

## Test Levels and Responsibilities

### Core tests (`tests/`)

Unit and integration tests for the transformation engine in `src/`. These run without a database or running server.

Covers:
- Configuration loading, resolution, and env var substitution
- Entity model construction, merged entity merging, foreign key linking
- Dispatch and timezone handling
- Specification validation (structural project rules)
- Loader schemas and path resolution
- Constraint validators
- Transformation pipeline correctness (append, unnest, mapping)

Tests in `tests/integration/` cover multi-step pipeline flows using file-based fixtures in `tests/test_data/`.

### Backend tests (`backend/tests/`)

Unit and integration tests for the FastAPI application in `backend/app/`. These run without an external database unless marked `integration` or `manual`.

Covers:
- API endpoint request/response handling
- Service layer logic (validation, preview, project load/save, task state)
- Mapper correctness (API ↔ Core conversion, directive resolution)
- Model validation (Pydantic schemas, env var preservation)
- State manager and cache behaviour
- Error handlers and correlation middleware
- Driver schema class-based configuration
- Data source API contracts

Tests in `backend/tests/integration/` test service interactions end-to-end within the backend layer.

### Ingester tests (`ingesters/sead/tests/`)

Tests for the SEAD ingester covering validation logic, ingestion flow, and fixture-based unit tests. No live database required for the unit tier.

### Frontend tests (`frontend/src/**/__tests__/`)

Vitest unit tests for stores, composables, API client modules, utilities, and selected components. Run in a jsdom environment.

Covers:
- Pinia store actions and state transitions (project, entity, validation, session, data-source, task status)
- API client module contracts (projects, entities, sessions, schema, validation, data-sources)
- Utility functions (graph adapter, task graph, error helpers)
- Component rendering (ValidationPanel, EntityFormDialog)
- Type guards and schema validation helpers

### Frontend E2E tests (`frontend/tests/e2e/`)

Playwright end-to-end tests against a running application. Currently covers:
- Smoke test (`00-smoke.spec.ts`)
- Project management workflow (`01-project-management.spec.ts`)
- Validation workflow (`02-validation-workflow.spec.ts`)
- Entity management (`03-entity-management.spec.ts`)

E2E tests require both the backend and frontend servers to be running.

### Manual testing

Detailed manual test procedures (UI checklists, feature-specific verification steps) are maintained separately:

- [Manual Testing Guide](other/MANUAL_TESTING_GUIDE.md) — UI walkthrough checklists for core application features
- [Merged Entity Manual Test Checklist](testing/MERGED_ENTITY_MANUAL_TEST_CHECKLIST.md) — merged entity setup and verification
- [Target Model Conformance Manual Test Checklist](testing/TARGET_MODEL_CONFORMANCE_MANUAL_TEST_CHECKLIST.md) — conformance validation across fixture types
- [Error Scenario Testing](testing/ERROR_SCENARIO_TESTING.md) — error handling and recovery
- [Non-Functional Testing Guide](testing/NON_FUNCTIONAL_TESTING_GUIDE.md) — browser compatibility and performance
- [Accessibility Testing Guide](testing/ACCESSIBILITY_TESTING_GUIDE.md) — WCAG compliance and keyboard navigation

---

## Test Environment and Prerequisites

- Python tests: `.venv/` must be active (run via `uv run ...`). No live database needed unless the test is marked `integration` or `manual`.
- Frontend unit tests: `pnpm install` in `frontend/`; no running backend needed.
- Frontend E2E tests: backend running on port 8013 and frontend dev server on port 5173 (or a built frontend).
- `asyncio_mode = "auto"` is set in `pyproject.toml`, so `@pytest.mark.asyncio` is still accepted but not required on individual tests.

### pytest markers

| Marker | Meaning |
|--------|---------|
| `integration` | Hits external services (database, network) — skipped in standard CI |
| `manual` | Requires manual setup (real DB, specific data) — run locally only |
| `debug` | Debugging helpers — run manually |

Run only unmarked (fast) tests:
```bash
uv run pytest tests backend/tests -v -m "not integration and not manual and not debug"
```

---

## Test Data, Fixtures, and Mocking Strategy

- **YAML fixtures**: Core tests use YAML project files under `tests/test_data/`. Backend tests use fixtures under `backend/tests/test_data/`. These fixture projects are the primary test inputs.
- **Python fixtures**: `tests/conftest.py` provides `MockConfigProvider`, mock DB rows, and async mocks. `backend/tests/conftest.py` provides a FastAPI `TestClient`, mock services, and test projects.
- **Ingester fixtures**: `ingesters/sead/tests/fixtures.py` and `builders.py` provide explicit `IngesterConfig` instances with all required fields to avoid `ConfigStore` initialization in tests.
- **Mocking strategy**: Pure domain validators receive DataFrames directly — no mocks needed. Services that call external systems (DB, HTTP) are mocked at the service boundary. Use `AsyncMock` for async service methods.
- **Frontend mocks**: API modules are mocked via `vi.mock()` in Vitest. Pinia stores are used with `createPinia()` and `setActivePinia()` in each test.
- Do not add `print` statements or debug logging to tests; use `pytest -s` locally if needed.

---

## Common Test Commands

```bash
# All tests (core + backend + ingesters)
make test

# Core tests only
uv run pytest tests -v

# Backend tests only
make backend-test
uv run pytest backend/tests -v

# With explicit PYTHONPATH if imports fail
PYTHONPATH=.:backend uv run pytest backend/tests -v

# Ingester tests only
uv run pytest ingesters/sead/tests -v

# Single test or test file
uv run pytest tests/test_mapping.py::test_name -v -s

# Skip slow/external tests
uv run pytest tests backend/tests -m "not integration and not manual"

# Frontend unit tests
make frontend-test

# Frontend unit tests with coverage
make frontend-coverage

# Frontend E2E (requires running app)
cd frontend && pnpm test:e2e
```

---

## Validation Before Merge

Before opening a pull request:

1. Run the full test suite for the changed area:
   ```bash
   make test           # or targeted subset
   make frontend-test
   ```

2. Format and lint:
   ```bash
   make tidy && make lint
   make frontend-lint
   ```

3. If changing the transformation pipeline, mappers, or specification validators, run the full suite — changes in these areas affect cross-layer behaviour.

4. Add or update tests for any bug fixed or feature added. Regression tests should be narrow and tied to the specific broken input.

---

## CI Test Execution

The current CI pipeline (`.github/workflows/release.yml`) runs semantic-release on merges to `main`. It does not currently run the automated test suite as a CI gate — tests are expected to pass locally before merging.

> **Note:** A CI test step is not yet configured. This is a known gap. Until one is added, all tests must pass locally before merge to `dev` or `main`.

---

## Troubleshooting and Common Pitfalls

**Async test failures:** `asyncio_mode = "auto"` is active in `pyproject.toml`. If you see `ScopeMismatch` or `Event loop is closed` errors, check that fixtures using `async` coroutines match the test function's scope. Async tests do not need `@pytest.mark.asyncio` but it is harmless to include.

**Import errors in backend tests:** Always run via `uv run` or set `PYTHONPATH=.:backend` explicitly. The monorepo has no separate backend venv.

**`ConfigStore` / `ConfigValue` in ingester tests:** Pass all config values explicitly via `IngesterConfig(extra={...})` to avoid triggering `ConfigStore` initialization outside an application context.

**YAML fixture not found:** Test data paths are relative to the test file or resolved via `Config.project_dir`. Check the fixture path in `conftest.py` or the test's `@pytest.fixture`.

**Frontend `vi.mock` not hoisted:** Vitest requires `vi.mock(...)` calls to be at the top level of the test file (not inside `beforeEach`). Move mock declarations above any imports that depend on them.

**E2E tests timing out:** Ensure both backend (port 8013) and frontend (port 5173) are running before starting Playwright tests. Use `make backend-run` and `make frontend-run` in separate terminals.

---

## Related Documents

- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, commands, and contributor workflow
- [DESIGN.md](DESIGN.md) — architecture, layer boundaries, pipeline design
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, and CI/CD
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — YAML project configuration reference
- Manual test guides: [other/MANUAL_TESTING_GUIDE.md](other/MANUAL_TESTING_GUIDE.md), [testing/](testing/)
