# Shape Shifter - AI Coding Instructions

This file is always-on. Put task-specific guidance in `.github/instructions/` so it loads only when relevant.

## Repository structure

- `src/`: core Python transformation engine
- `backend/app/`: FastAPI backend
- `frontend/`: Vue 3 + Vuetify frontend
- `ingesters/`: pluggable ingester implementations
- Python environment: `.venv/` at repo root

Core pipeline order: Extract → Filter → Link → Unnest → Translate → Store. Orchestrated by `ShapeShifter` in `src/normalizer.py` via `ProcessState`.

## Architecture invariants

- API models in `backend/app/models/`; domain logic in `src/`. Convert between layers with mappers. Never import API models into `src/`.
- Resolve `@include:`, `@value:`, and `${ENV_VAR}` directives **only** at the mapper boundary (`ProjectMapper.to_core()`). Core always receives resolved values.
- All FK relationships use local `system_id` values. `keys` are business keys for deduplication. `public_id` names the export column and must end with `_id`.
- Use the registry pattern for validators, loaders, filters, and ingesters (`@Validators.register(...)` etc.).
- Use absolute imports only: `from src...` and `from backend.app...`.

## Code conventions

- Line length: 140. Format with `make tidy` (Black + isort).
- Logging: `loguru.logger`. All functions must have type hints.
- Naming: `snake_case` entities, `_id` suffix for public IDs, `/api/v1/{resource}` (plural) for endpoints.

## Workflow

- Install: `make install`. Backend: `make backend-run`. Frontend: `make frontend-run`.
- Test: `make test` or `uv run pytest tests -v` (core) / `uv run pytest backend/tests -v` (backend).
- Lint: `make lint`. Format: `make tidy`.
- Run targeted tests before finishing; broader tests when a change crosses layers.

## Documentation scope

- Use `docs/` (current). Ignore `docs/archive/`. Treat `docs/features/` as future backlog, not authoritative guidance.
- For proposal work: follow `.github/instructions/proposal-writing-guide.instructions.md` and use `docs/templates/PROPOSAL_TEMPLATE.md`.

## Scoped instructions

Most instruction files auto-load via `applyTo:` when a matching file is open — no manual reference needed:

- `python.instructions.md` — all `src/`, `backend/`, `ingesters/`, `tests/` Python files
- `frontend.instructions.md` — `frontend/src/**/*.vue` and `.ts`
- `features/*.instructions.md` — feature-specific paths (entities, transforms, execution, validation, loaders, materialization, reconciliation, graph, ingesters, target-model, specifications)
- `shapeshifter-configuration.instructions.md` and `project-config.instructions.md` — `**/shapeshifter.yml` and project YAML
- `design/development/testing/operations/user-guide.instructions.md` — their respective `docs/` files

Cross-cutting (no path trigger — load when relevant):
- `diagrams.instructions.md`: Mermaid diagram style and conventions
- `github-workflow.instructions.md`: issue creation and commit workflow
