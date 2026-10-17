# Shape Shifter - Developer Guide

## Purpose

This guide covers setting up, running, modifying, and validating the codebase day-to-day. Architecture and design: [DESIGN.md](DESIGN.md). Deployment and operations: [OPERATIONS.md](OPERATIONS.md).

---

## Prerequisites

**Required:**
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and [pnpm](https://pnpm.io/)
- Git

**Optional:**
- Podman and `podman-compose` (for containerized runs; see [deployment/container/README.md](../deployment/container/README.md))
- Java JRE (`default-jre-headless`) — required to query MS Access sources via UCanAccess
- PostgreSQL — required when using SQL data sources

---

## Local Setup

```bash
# Clone and bootstrap (installs core + API + dev dependencies into .venv)
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter
make install

# Install frontend dependencies
make frontend-install
```

`make install` creates `.venv/` and runs `uv pip install -e ".[all]"`. The virtual environment is shared across the whole monorepo; there is no separate backend venv.

---

## Local Configuration

The backend reads configuration from environment variables prefixed with `SHAPE_SHIFTER_` and loads them from `.env` in the working directory. Copy `.env.example` and set any values that differ from defaults:

```ini
SHAPE_SHIFTER_PROJECTS_DIR=./projects
SHAPE_SHIFTER_LOG_LEVEL=DEBUG
SHAPE_SHIFTER_ENVIRONMENT=development
```

`SHAPE_SHIFTER_ENV_FILE` points the loader at a different file. See `backend/app/core/config.py` for all settings and their defaults. For production variables and secrets layout see [OPERATIONS.md](OPERATIONS.md).

For PostgreSQL access, configure `~/.pgpass` rather than putting passwords in environment variables.

### Markdown link updates when moving files

Enable `markdown.updateLinksOnFileMove.enabled: "always"` and `markdown.validate.enabled: true` to let VS Code rewrite links into and out of a moved file or directory. It fires only for moves VS Code performs, so a terminal `git mv` updates nothing, and it rewrites link syntax only, leaving prose and table paths to a manual search. External `http(s)` links are never checked; run `make check-doc-links` after any move.

---

## Project Structure

```
sead_shape_shifter/
├── src/                     # Core transformation engine (framework-independent)
│   ├── normalizer.py        # ShapeShifter orchestrator
│   ├── model.py             # Domain models
│   ├── dispatch.py          # Output format handlers
│   ├── extract.py           # Source extraction
│   ├── workflow.py          # Pipeline stage sequencing
│   ├── loaders/             # DataLoader implementations
│   ├── validators/          # Constraint validators
│   ├── transforms/          # Filter, link, unnest, translate steps
│   ├── specifications/      # Project-level structural validation
│   ├── target_model/        # Target model parsing and conformance
│   ├── reconciliation/      # Reconciliation support
│   ├── sidecars/            # Mapping and value sidecars
│   ├── configuration/       # Config provider
│   └── types/               # Shared type definitions
├── backend/
│   └── app/
│       ├── api/v1/endpoints/ # FastAPI routers (one module per resource)
│       ├── services/         # Business logic
│       ├── mappers/          # API ↔ Core translation + env var resolution
│       ├── models/           # Pydantic v2 request/response schemas
│       ├── authorization/    # Principals, resources, grants, dependencies
│       ├── validators/       # API-layer validators
│       ├── clients/          # httpx clients (SIMS, reconciliation)
│       ├── core/             # Config, logging, state manager
│       ├── ingesters/        # Ingester adapters
│       ├── utils/            # Shared helpers
│       ├── scripts/          # Admin CLI commands
│       └── middleware/       # Request middleware
├── frontend/src/
│   ├── api/                # Axios client modules (one per resource)
│   ├── stores/             # Pinia stores
│   ├── composables/        # Reusable composition functions
│   ├── components/         # Vue components
│   ├── views/              # Route-level screens
│   ├── router/             # Route definitions
│   ├── config/             # Runtime configuration
│   ├── schemas/            # Generated JSON schemas
│   ├── plugins/            # Vuetify and app plugins
│   ├── styles/             # Shared styles and assets
│   ├── utils/              # Shared frontend helpers
│   └── types/              # TypeScript types
├── ingesters/              # Pluggable ingesters (top-level, auto-discovered)
├── tests/                  # Core tests
├── backend/tests/          # Backend API tests
├── docs/                   # Documentation
├── deployment/             # container release bundle and host deployment tooling
├── scripts/                # Developer and admin scripts
├── pyproject.toml          # Python dependencies and tool config
└── Makefile                # All supported development commands
```

---

## Common Development Commands

All supported commands are defined in `Makefile`. The most common:

### Running locally

```bash
make backend-run          # Start backend on http://localhost:8013
make frontend-run         # Start frontend on http://localhost:5173
make br                   # Kill + restart backend only
make fr                   # Kill + restart frontend only
make br+fr                # Kill + restart both
```

API docs: `/api/v1/docs` on the same port.

### Testing

```bash
make test                              # All suites
make backend-test                      # Backend tests only
uv run pytest tests -v                 # Core tests only

# Run a single test
uv run pytest tests/test_mapping.py::test_name -v -s
```

Frontend tests and documentation:

```bash
make frontend-test        # Run Vitest tests
make frontend-coverage    # Run with coverage report
make check-doc-links      # Check links in active Markdown documentation
```

### Code quality

```bash
make tidy                 # Format: isort + black
make ruff                 # Lint + auto-fix with ruff
make pylint               # Pylint check
make lint                 # tidy + ruff + pylint (full pass)
make frontend-lint        # ESLint for frontend
```

---

## Code Conventions

### Python

- Python 3.13+; always run Python via `uv run` to ensure `.venv/` is active.
- Absolute imports only: `from src.model import ...`, `from backend.app.services import ...`
- Line length: 140 characters (configured in `pyproject.toml`).
- Logging: `from loguru import logger` — do not use `print` or stdlib `logging`.
- Type hints required on all function signatures.
- Naming: `snake_case` for entities; `_id` suffix for public ID columns; `/api/v1/{resource}` (plural) for endpoints.

### Layer boundary rules (critical)

- **API models** (`backend/app/models/`): hold raw `${ENV_VARS}` and `@directives` — never resolve them here.
- **Mappers** (`backend/app/mappers/`): the only place that calls `resolve_config_env_vars()` and converts between API and Core types.
- **Core** (`src/`): always receives fully resolved values; has no dependency on FastAPI or Pydantic API models.

See [DESIGN.md](DESIGN.md) for the full layer boundary and identity system design.

### Authorization for protected work

Use the centralized authorization dependencies for every protected endpoint; do not duplicate role checks in a route or service. The project path parameter must be named `name` or `project_name` so `require_project()` can resolve it. Use `require_shared_data_source(Action.READ)` for a named shared source and `require_application_action(action)` for deployment-wide permissions. Each dependency adds `authorization_requirement` metadata used by [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md).

```python
from typing import Annotated

from fastapi import Depends

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource

project_reader = require_project(Action.READ)


@router.get("/projects/{name}/example")
async def read_example(
   name: str,
   authorized_project: Annotated[AuthorizedResource, Depends(project_reader)],
) -> dict:
   return await service.read_example(authorized_project)
```

Sensitive service methods must accept an `AuthorizedResource` or repeat the central check before reading data. Use `authorized_resource.resource.locator` only after the dependency resolved it; never accept a client-supplied resource name or path as proof of authorization.

For a long-running operation, record the initiating principal and project resource UUID when creating it:

```python
operation_id = operation_manager.create_operation(
   operation_type="example",
   owner_principal_id=authorized_project.principal.principal_id,
   project_resource_id=str(authorized_project.resource.resource_id),
)
```

Use `require_operation(Action.READ)` or `require_operation(Action.EDIT)` for progress, stream, result, and cancellation routes. An operation or session ID is not authorization, and a background task must reauthorize against the recorded project.

### Local authorization debug setup

The `FastAPI Backend (Debug)` launch profile uses the `local-developer` principal, disables trusted-proxy authentication, binds the API to localhost, and writes to `state/authorization-dev.sqlite3`. Initialize it with:

```bash
SHAPE_SHIFTER_ENVIRONMENT=development \
SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false \
SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer \
SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-dev.sqlite3 \
uv run sead-authorization dev-bootstrap
```

The debug launch logs this command when the database lacks the local admin or resource records. The command refuses non-development environments, trusted-proxy authentication, or any other path, and is safe to rerun, so rerun it after adding project or shared data source files outside the API.

When adding or changing protected work:

1. Select the resource and action from `backend.app.authorization.models.Action`.
2. Add the matching dependency and use its returned authorized resource.
3. Record every required resource; project access does not grant shared-source access.
4. Add the route to [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md).
5. Add allowed, denied, and concealed-resource tests, including service and background entry points.

See [AUTHORIZATION.md](AUTHORIZATION.md) for policy and response behavior.

### Frontend

- `<script setup lang="ts">` with `defineProps<T>()` and `defineEmits<T>()`.
- API calls only in `frontend/src/api/` — never directly in components.
- State in Pinia stores; use `storeToRefs()` in components.
- See `.github/instructions/frontend.instructions.md` for detailed conventions.

---

## Development Workflow

1. **Branch from `dev`:** `git checkout -b feature/my-feature`

2. **Make changes**, running the relevant server locally to verify behavior.

3. **Test** the changed area; run broader tests when the change crosses layers.

4. **Format and lint** before committing:
   ```bash
   make tidy && make lint
   ```

5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(scope): ...` — new feature (minor release)
   - `fix(scope): ...` — bug fix (patch release)
   - `docs`, `refactor`, `test`, `chore` — no release
   - Append `!` or use `BREAKING CHANGE:` footer for major releases.

6. **Open a pull request** against `dev`. Semantic-release runs on merges to `main` and generates version tags and `CHANGELOG.md` automatically.

---

## Extending the System

- **New data loader**: subclass `DataLoader` in `src/loaders/`, register with `@DataLoaders.register(key="...")`, define `schema: ClassVar[DriverSchema]`.
- **New validator**: subclass `ConstraintValidator` in `src/validators/`, register with `@Validators.register(key="...", stage="pre-merge|post-merge")`.
- **New ingester**: create `ingesters/<name>/ingester.py`, implement the `Ingester` protocol, register with `@Ingesters.register(key="...")`. See `.github/instructions/ingesters.instructions.md`.
- **New API endpoint**: add router in `backend/app/api/v1/endpoints/`, register in `backend/app/api/v1/api.py`, define Pydantic models in `backend/app/models/`, implement service in `backend/app/services/`.

---

## Debugging and Troubleshooting

**Backend won't start:**
```bash
which python            # Should point to .venv/bin/python
make install            # Reinstall if environment is wrong
lsof -i :8013          # Check if port is in use
```

**Import errors:** run Python through `uv run`, which sets `PYTHONPATH=.`. If imports still fail, set it explicitly: `PYTHONPATH=.:backend uv run pytest backend/tests -v`.

**Async test failures:** ensure `@pytest.mark.asyncio` is on the test function and `pytest-asyncio` is installed.

**Frontend dev server issues:**
```bash
make frontend-clear     # Clear Vite cache and dist
make frontend-install   # Reinstall pnpm dependencies
lsof -i :5173          # Check if port is in use
```

**MS Access / JVM errors:** install Java (`sudo apt install default-jre-headless`) and run `scripts/install-uncanccess.sh` for the UCanAccess JAR. The JVM initializes once at backend startup, so restart the backend if initialization fails.

**Log output:** `logs/backend.log` when running via `make backend-run-log`; add `-s` to pytest for debug output.

---

## AI-Friendly Development

AI-assisted work is limited less by file count than by ambiguity, duplication, and search noise. Multiple implementations of one behavior, stale docs, and archived code that looks authoritative all degrade results, as do generated output, logs, and build artifacts in normal search paths.

Keep architectural boundaries enforced, docs current, naming consistent across entities and layers, feature logic locally coherent, and changes small and scoped. Add regression tests for bug-prone workflows.

When asking for AI help, include the affected workflow, expected and actual behavior, likely files, and related proposal, phase-plan, or task-plan paths. Use `.venv/bin/graphify query` before broad code searches when exploring relationships, and verify its results in current source and tests.

---

## Related Documents

- [TESTING.md](TESTING.md) — test strategy, levels, and repository-specific testing guidance
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) — durable lifecycle policy for provider-submitted data changes through `sead_change_request`
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — complete YAML project configuration reference
- [USER_GUIDE.md](USER_GUIDE.md) — end-user documentation for the editor UI
- `.github/instructions/` — task-specific AI coding guidance (frontend, ingesters, validators, YAML config, etc.)
