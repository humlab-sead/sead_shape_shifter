# Shape Shifter – Agent Guide

> Subsystem-specific rules live in `src/AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, and `ingesters/AGENTS.md`. Read the relevant one when working in that subtree.

## Architecture

- Monorepo: Core (`src/`), Backend (`backend/app/`), Frontend (`frontend/`), Ingesters (`ingesters/`). One `.venv/` at repo root.
- Core pipeline (immutable order): **Extract → Filter → Link → Unnest → Translate → Store** — orchestrated by `ShapeShifter` (`src/normalizer.py`) via `ProcessState`.
- Backend: FastAPI; routers in `api/v1/endpoints/`, services in `services/`, Pydantic v2 models in `models/`.
- Frontend: Vue 3 `<script setup>` + Pinia stores + composables + Axios + Monaco YAML editor.
- Treat `docs/features/` as future-feature backlog — not authoritative.

## Workflow Commands

- `make install` — full setup; `uv pip install -e ".[api]"` for Core+API only.
- `make backend-run` (FastAPI :8012), `make frontend-run` (Vue :5173).
- `make test` — full suite; `uv run pytest tests -v` (Core); `uv run pytest backend/tests -v` (backend).
- `make lint` / `make tidy` (Black + isort) before committing.

## Documentation Vocabulary

- Use plain, concrete language in generated code, comments, docstrings, PR text, and documentation.
- Prefer words that name the actual thing, action, rule, input, output, or result directly.
- Do not treat any word as forbidden, but use abstract or overloaded terms carefully. If a technical term is necessary, define it nearby or pair it with a plain-language explanation.
- Use these terms carefully unless they are established project vocabulary: `evidence`, `boundary`, `framing`, `canonical`, `surface`, `facing`, `slice`, `signal`.
- Prefer explicit wording such as `data`, `result`, `source`, `check`, `validation result`, `limit`, `responsibility`, `allowed range`, `rule`, `purpose`, `reason`, `background`, `request details`, `standard`, `preferred`, `normalized`, `official`, `interface`, `page`, `endpoint`, `entry point`, `used by`, `shown to`, `exposed to`, `part`, `section`, `subset`, `step`, `indicator`, `warning`, `metric`, `status`, `input`, `output`, `error`, and `side effect`.
- Write for a mixed audience: junior developers, maintainers, testers, data managers, researchers, and non-technical stakeholders.
- The closer text is to code or user-visible behavior, the more concrete the vocabulary should be.
- Comments and docstrings should explain behavior, responsibility, assumptions, inputs, outputs, and side effects. Avoid metaphorical or fashion-driven wording when a simpler phrase is equally accurate.
- Write docstrings using concrete behavior-first wording. Prefer direct statements such as `Reads sample rows from a CSV file.`, `Returns validation errors for missing required fields.`, `Uses the site ID to find matching sample groups.`, and `Does not write changes to the database.` Avoid vague wording such as `Ingests artifacts across the import boundary.`, `Resolves canonical entities for downstream consumers.`, and `Emits signals for the review surface.`

## Cross-Cutting Rules

- **Absolute imports only**: `from src...` and `from backend.app...` — never relative across packages.
- **Layer boundary**: API models stay in `backend/app/models/`; domain logic stays in `src/`. Never import `backend.*` from `src/`.
- **Mapper**: all API↔Core conversions go through `ProjectMapper`. Never bypass it.
- **Directives** (`@include:`, `@value:`, `${ENV_VAR}`) are resolved **only** in `ProjectMapper.to_core()` — API and YAML layers preserve them raw.
- **Registries**: use `@Validators.register(...)`, `@DataLoaders.register(...)`, `@Ingesters.register(...)` — never bypass the registry.
- **Circular imports**: use constructor injection or `TYPE_CHECKING` — never restructure imports as a workaround.
- **Async**: `ShapeShifter.normalize()` and all data loaders are async — never call with `asyncio.run()` inside a loader or service.

## Three-Tier Identity System

All FK relationships use local `system_id` values — never external IDs.

| Tier | Field | Purpose | FK values? |
|------|-------|---------|-----------|
| 1 | `system_id` | Local sequential integer | **Yes** |
| 2 | `keys` | Business keys for deduplication | No |
| 3 | `public_id` | Target schema column name; holds SEAD IDs after mapping | No |

- `public_id` must end with `_id`. FK child column name = parent's `public_id`; FK values = parent's `system_id`.

## Code Conventions

- Line length ≤ 140 characters; Black + isort.
- `loguru.logger` for logging; type hints on all functions and Pydantic models.
- Naming: `snake_case` entities, `_id` suffix for public IDs, `/api/v1/{resource}` (plural) for endpoints.
- `@pytest.mark.asyncio` for async Core tests; `TestClient` for backend route tests.

## Common Implementation Tasks

- **Backend endpoint**: router in `backend/app/api/v1/endpoints/`, models in `backend/app/models/`, service in `backend/app/services/`, register in `backend/app/api/v1/api.py`. See `.github/prompts/add-endpoint.prompt.md`.
- **Constraint validator**: `@Validators.register(key=..., stage=...)` in `src/constraints.py`. See `.github/prompts/add-validator.prompt.md`.
- **Data loader**: `@DataLoaders.register(key=...)` in `src/loaders/`, `ClassVar` schema on the class. See `.github/prompts/add-loader.prompt.md`.
- **Specification**: subclass `ProjectSpecification`, implement `is_satisfied_by()`, add to `CompositeProjectSpecification.__init__()`.
- **Ingester**: directory under `ingesters/<name>/`, implement `Ingester` protocol, `@Ingesters.register(key="<name>")`. See `ingesters/AGENTS.md`.

## Key References

- Core models: `src/model.py`, `src/constraints.py`, `src/specifications.py`.
- Backend entry: `backend/app/main.py`; validation: `backend/app/services/validation_service.py`.
- SIMS client: `backend/app/clients/sims_client.py` (env var: `SHAPE_SHIFTER_SIMS_SERVICE_URL`).
- Docs: `docs/DESIGN.md`, `docs/CONFIGURATION_GUIDE.md`, `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`, `docs/TESTING.md`.
- Scoped instructions (VS Code Copilot): `.github/instructions/` — auto-injected by `applyTo` patterns.
- Prompt templates: `.github/prompts/` — invoke via `/` in Copilot Chat.
- UCanAccess setup: `scripts/install-uncanccess.sh` (requires Java JRE).
