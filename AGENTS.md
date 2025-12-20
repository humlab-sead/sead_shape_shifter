# Shape Shifter – Agent Guide

## Architecture Awareness
- Treat the repo as a mono-repo with Core (`src/`), Backend (`backend/app/`), and Frontend (`frontend/`).
- Use the unified Python virtual environment at `.venv/` for every Python command.
- Preserve the core pipeline order: Extract ➜ Filter ➜ Link ➜ Unnest ➜ Translate ➜ Store; orchestrate via `ArbodatSurveyNormalizer` (`src/normalizer.py`) using `ProcessState`.
- Keep backend layering clear: routers in `api/v1/endpoints/`, services in `services/`, Pydantic v2 models in `models/`, and shared settings in `core/`.
- Build frontend features with Vue 3 `<script setup>` components, Pinia stores, composables, Axios API layer, and Monaco-based YAML editing.

## Workflow Commands
- Run `make install` for full setup; use `uv pip install -e ".[api]"` for Core+API or `uv pip install -e .` for Core only.
- Start local services with `make backend-run` (FastAPI on :8012) and `make frontend-run` (Vue on :5173).
- Execute tests with `make test` for full coverage, `uv run pytest tests -v` for Core, or `uv run pytest backend/tests -v` (add `PYTHONPATH=.:backend` if imports fail).
- Enforce formatting and linting with `make lint`; run `make tidy` (Black + isort) before committing.

## Critical Patterns & Constraints
- Register extensible validators/loaders/filters through the registry pattern (`@Validators.register(...)`).
- Await every async data loader in `src/loaders/`; check backend service signatures before mixing sync/async logic.
- Decorate async tests with `@pytest.mark.asyncio` (Core) and use FastAPI `TestClient` for backend routes.
- Import backend usages of Core with absolute paths only (e.g., `from src.model import TablesConfig`).
- **Environment variable resolution**: Happens ONLY in mapper layer (`backend/app/mappers/`). API entities stay raw (`${VAR}`), core entities are always resolved. Never call `resolve_config_env_vars()` in services.

## Code Conventions
- Keep line length ≤ 140 characters and rely on Black + isort formatting.
- Use `loguru.logger` for logging and provide type hints for all functions (including Pydantic models).
- Follow naming rules: snake_case entities, `_id` suffix for surrogate keys, `/api/v1/{resource}` (plural) for endpoints.

## Common Implementation Tasks
- **Backend endpoint**: add router (`backend/app/api/v1/endpoints/`), define Pydantic models (`backend/app/models/`), implement service (`backend/app/services/`), and register in `backend/app/api/v1/api.py`.
- **Constraint validator**: create class in `src/constraints.py`, decorate with `@Validators.register(key=..., stage=...)`, and add tests in `tests/test_constraints.py`.
- **Configuration validation**: subclass `ConfigSpecification` in `src/specifications.py`, implement `is_satisfied_by()`, and include it inside `CompositeConfigSpecification.__init__()`.

## Frontend Practices
- Always use `<script setup lang="ts">`, composables over mixins, and `defineProps<T>()` / `defineEmits<T>()` for typing.
- Derive store refs with `storeToRefs()` and manage state in Pinia stores under `frontend/src/stores/` (e.g., configuration, validation, entity, data-source stores).
- Implement API interactions through `frontend/src/api/` with Axios interceptors; call endpoints under `/api/v1` using `apiClient` and `VITE_API_BASE_URL` (default `http://localhost:8012`).
- Follow the documented Pinia pattern (loading/error refs with guarded async calls) and enforce strict null checks, preferring `type` for unions and `interface` for objects.

## Key References
- Use `src/model.py`, `src/constraints.py`, and `src/specifications.py` for Core models, constraints, and config rules.
- Touch backend behavior via `backend/app/main.py` and `backend/app/services/validation_service.py`.
- Manage frontend state under `frontend/src/stores/` and related composables.
- Consult docs: `docs/CONFIGURATION_GUIDE.md`, `docs/SYSTEM_DOCUMENTATION.md`, `docs/BACKEND_API.md`, `docs/DEVELOPMENT_GUIDE.md` before major changes.

## External Dependencies
- Install UCanAccess via `scripts/install-uncanccess.sh` when Access support is required.
- Ensure Java JRE is available for UCanAccess integrations.
- Use `pnpm` as the frontend package manager whenever Node dependencies are involved.
