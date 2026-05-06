# Shape Shifter - Developer Guide

## Purpose

This guide covers everything a developer needs to set up, run, modify, and validate the Shape Shifter codebase day-to-day. For architecture and design decisions see [DESIGN.md](DESIGN.md). For deployment and operations see [OPERATIONS.md](OPERATIONS.md).

---

## Prerequisites

**Required:**
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and [pnpm](https://pnpm.io/)
- Git

**Optional:**
- Docker and Docker Compose (for containerized runs)
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

The backend reads configuration from environment variables prefixed with `SHAPE_SHIFTER_`. For local development, create `backend.env` (not committed) and set any values that differ from defaults:

```ini
SHAPE_SHIFTER_PROJECTS_DIR=./projects
SHAPE_SHIFTER_LOG_LEVEL=DEBUG
SHAPE_SHIFTER_ENVIRONMENT=development
```

See `backend/app/core/config.py` for all available settings and their defaults. For production environment variables and secrets layout see [OPERATIONS.md](OPERATIONS.md).

For PostgreSQL access, configure `~/.pgpass` rather than putting passwords in environment variables.

---

## Project Structure

```
sead_shape_shifter/
├── src/                    # Core transformation engine (framework-independent)
│   ├── normalizer.py       # ShapeShifter orchestrator
│   ├── model.py            # Domain models
│   ├── loaders/            # DataLoader implementations (sql, csv, xlsx, fixed)
│   ├── validators/         # Constraint validators
│   ├── dispatchers/        # Output format handlers
│   └── specifications/     # Project-level structural validation
├── backend/
│   └── app/
│       ├── api/v1/endpoints/ # FastAPI routers (one module per resource)
│       ├── services/         # Business logic
│       ├── mappers/          # API ↔ Core translation + env var resolution
│       ├── models/           # Pydantic v2 request/response schemas
│       ├── clients/          # httpx clients (SIMS, reconciliation)
│       └── core/             # Config, logging, state manager
├── frontend/src/
│   ├── api/                # Axios client modules (one per resource)
│   ├── stores/             # Pinia stores
│   ├── composables/        # Reusable composition functions
│   ├── components/         # Vue components
│   └── views/              # Route-level screens
├── ingesters/              # Pluggable ingesters (top-level, auto-discovered)
├── tests/                  # Core tests
├── backend/tests/          # Backend API tests
├── docs/                   # Documentation
├── docker/                 # Container build and deploy scripts
├── scripts/                # Developer and admin scripts
├── pyproject.toml          # Python dependencies and tool config
└── Makefile                # All supported development commands
```

The core layer (`src/`) has no dependency on FastAPI or Pydantic API models. See [DESIGN.md](DESIGN.md) for the layer boundary architecture.

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

API docs are available at `http://localhost:8013/api/v1/docs` when the backend is running.

### Testing

```bash
make test                              # All tests (core + backend + ingesters)
make backend-test                      # Backend tests only
uv run pytest tests -v                 # Core tests only
uv run pytest backend/tests -v         # Backend tests only

# Run a single test
uv run pytest tests/test_mapping.py::test_name -v -s

# With explicit PYTHONPATH when import resolution fails
PYTHONPATH=.:backend uv run pytest backend/tests -v
```

Frontend tests:

```bash
make frontend-test        # Run Vitest tests
make frontend-coverage    # Run with coverage report
```

### Code quality

```bash
make tidy                 # Format: isort + black
make ruff                 # Lint + auto-fix with ruff
make pylint               # Pylint check
make lint                 # tidy + ruff + pylint (full pass)
make frontend-lint        # ESLint for frontend
```

Run `make tidy && make lint` before opening a pull request.

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

### Frontend

- `<script setup lang="ts">` with `defineProps<T>()` and `defineEmits<T>()`.
- API calls only in `frontend/src/api/` — never directly in components.
- State in Pinia stores; use `storeToRefs()` in components.
- See `.github/instructions/frontend.instructions.md` for detailed conventions.

---

## Development Workflow

1. **Create a branch** from `dev`:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes.** Run the relevant server locally to verify behavior.

3. **Run targeted tests** for the changed area. Run broader tests when the change crosses layers.

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

**Import errors:** Always run Python commands through `uv run`, which sets `PYTHONPATH=.` automatically. If still failing:
```bash
PYTHONPATH=.:backend uv run pytest backend/tests -v
```

**Async test failures:** ensure `@pytest.mark.asyncio` is on the test function and `pytest-asyncio` is installed.

**Frontend dev server issues:**
```bash
make frontend-clear     # Clear Vite cache and dist
make frontend-install   # Reinstall pnpm dependencies
lsof -i :5173          # Check if port is in use
```

**MS Access / JVM errors:** Java JRE must be installed (`sudo apt install default-jre-headless`). Run `scripts/install-ucanaccess.sh` to install the UCanAccess JAR. The JVM initializes once at backend startup; restart the backend if initialization fails.

**Log output:** logs go to `logs/backend.log` when running via `make backend-run-log`. For pytest debug output, add `-s`.

---

## AI-Friendly Development

As this project grows, AI-assisted code work is affected less by raw file count and more by how much ambiguity, duplication, and noise exists in the workspace.

**What degrades AI performance:**
- Multiple competing implementations of the same behavior
- Stale or conflicting documentation
- Generated files, coverage output, logs, and build artifacts mixed into normal search paths
- Deprecated or archived code that looks authoritative
- Features spread across many unrelated files with no clear owner

**What helps most:**
1. Keep architectural boundaries clear and enforced.
2. Maintain concise, current docs — especially architecture and workflow guidance.
3. Use strong, consistent naming across entities, stores, services, endpoints, and config.
4. Keep feature logic locally coherent rather than scattered across layers.
5. Keep commits and pull requests small and scoped.
6. Add focused regression tests for bug-prone workflows.
7. When asking for AI help, include: affected workflow, expected behavior, actual behavior, and likely files.

The biggest performance cost for AI in a large repository is not size — it is uncertainty. Reducing ambiguity, duplication, and search noise usually improves AI effectiveness more than reducing line count.

---

## Related Documents

- [DESIGN.md](DESIGN.md) — architecture, component responsibilities, key flows, design decisions
- [TESTING.md](TESTING.md) — test strategy, levels, and repository-specific testing guidance
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, CI/CD, rollback, and observability
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — complete YAML project configuration reference
- [USER_GUIDE.md](USER_GUIDE.md) — end-user documentation for the editor UI
- `.github/instructions/` — task-specific AI coding guidance (frontend, ingesters, validators, YAML config, etc.)
- API reference: `http://localhost:8013/api/v1/docs` when running locally
