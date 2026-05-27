# Shape Shifter - AI Coding Instructions

This file should stay small and always-on. Put task-specific guidance in `.github/instructions/*.instructions.md` so it loads only when relevant.

## Documentation scope

- Use current documentation in `docs/`.
- Ignore `docs/archive/`.
- Treat `docs/features/` as future backlog, not authoritative implementation guidance, unless the user asks about roadmap or planned features.
- Start with `docs/DESIGN.md`, `docs/CONFIGURATION_GUIDE.md`, `docs/DEVELOPMENT.md`, `docs/USER_GUIDE.md`, `docs/REQUIREMENTS.md`, `docs/TESTING.md`, `docs/OPERATIONS.md`, and `.github/instructions/shapeshifter-configuration.instructions.md`.
- For proposal work, follow `.github/instructions/proposal-writing-guide.instructions.md` and use `docs/templates/PROPOSAL_TEMPLATE.md` unless asked otherwise.

## Documentation vocabulary

- Use plain, concrete language in generated code, comments, docstrings, PR text, and documentation.
- Prefer words that name the actual thing, action, rule, input, output, or result directly.
- Do not treat any word as forbidden, but use abstract or overloaded terms carefully. If a technical term is necessary, define it nearby or pair it with a plain-language explanation.
- Use these terms carefully unless they are established project vocabulary: `evidence`, `boundary`, `framing`, `canonical`, `surface`, `facing`, `slice`, `signal`.
- Prefer explicit wording such as `data`, `result`, `source`, `check`, `validation result`, `limit`, `responsibility`, `allowed range`, `rule`, `purpose`, `reason`, `background`, `request details`, `standard`, `preferred`, `normalized`, `official`, `interface`, `page`, `endpoint`, `entry point`, `used by`, `shown to`, `exposed to`, `part`, `section`, `subset`, `step`, `indicator`, `warning`, `metric`, `status`, `input`, `output`, `error`, and `side effect`.
- Write for a mixed audience: junior developers, maintainers, testers, data managers, researchers, and non-technical stakeholders.
- The closer text is to code or user-visible behavior, the more concrete the vocabulary should be.
- Comments and docstrings should explain behavior, responsibility, assumptions, inputs, outputs, and side effects. Avoid metaphorical or fashion-driven wording when a simpler phrase is equally accurate.
- Write docstrings using concrete behavior-first wording. Prefer direct statements such as `Reads sample rows from a CSV file.`, `Returns validation errors for missing required fields.`, `Uses the site ID to find matching sample groups.`, and `Does not write changes to the database.` Avoid vague wording such as `Ingests artifacts across the import boundary.`, `Resolves canonical entities for downstream consumers.`, and `Emits signals for the review surface.`

## Repository structure

Shape Shifter is a monorepo with these main components:

- `src/`: core Python transformation engine
- `backend/app/`: FastAPI backend
- `frontend/`: Vue 3 + Vuetify frontend
- `ingesters/`: pluggable ingester implementations

Python uses the root `.venv/`.

Core pipeline order matters: Extract → Filter → Link → Unnest → Translate → Store. The orchestrator is `ShapeShifter` in `src/normalizer.py` using `ProcessState`.

## Always-on architecture rules

### API and Core separation

- Keep API models in `backend/app/models/` and domain logic in `src/`.
- Convert API ↔ Core with mappers.
- Resolve environment variables and directives only at the mapper boundary.
- Do not put business logic in API DTOs.
- Do not import API-layer models into `src/`.

### Circular dependencies

- Prefer constructor injection or factory functions when services depend on each other.
- Use `TYPE_CHECKING` imports for type hints.
- Do not treat lazy imports inside methods as the long-term fix.

### Pure domain validators

- Validators in `src/validators/` must receive data and config; they do not fetch data.
- Return domain validation issues, not API DTOs.
- Backend orchestrators may fetch preview/full data and map domain issues to API models.

### Identity and configuration rules

- All relationships use local `system_id` values.
- `keys` are business keys for matching and deduplication.
- `public_id` names target/export identity columns and should end with `_id`.
- Do not use external IDs as internal foreign-key values.
- Directives such as `@include:` and `@value:` belong in YAML and API-layer models; core models should receive resolved values.

### Core implementation patterns

- Use the registry pattern for validators, loaders, filters, and ingesters.
- Loader schemas belong on loader classes as `schema: ClassVar[DriverSchema]`.
- Use absolute imports only: `from src...` and `from backend.app...`.
- Await loaders and check sync/async service boundaries carefully.

## Workflow expectations

- Use the unified environment at `.venv/` for Python work.
- Common commands:
  - `make install`
  - `make backend-run`
  - `make frontend-run`
  - `make test`
  - `uv run pytest tests -v`
  - `uv run pytest backend/tests -v`
  - `PYTHONPATH=.:backend uv run pytest backend/tests -v`
  - `make lint`
  - `make tidy`
- Run targeted tests for the changed area before finishing.
- Run broader tests when a change crosses layers.
- When touching project YAML, validate against `.github/instructions/shapeshifter-configuration.instructions.md`.

## Code conventions

- Use absolute imports.
- Keep line length at 140.
- Use Black and isort via `make tidy`.
- Use `loguru.logger` for logging.
- Add type hints to all functions.

Naming:

- Entity names: `snake_case`
- Public IDs must end with `_id`
- API endpoints use `/api/v1/{resource}` with plural nouns

## Task-specific instructions

Use the targeted files under `.github/instructions/` for detailed guidance instead of expanding this file again:

- `python.instructions.md`: Python architecture, loaders, validators, and test patterns
- `frontend.instructions.md`: Vue, Pinia, and frontend API conventions
- `project-config.instructions.md`: `shapeshifter.yml` and configuration validation
- `shapeshifter-configuration.instructions.md`: full YAML validation rules, entity types, identity system, FK patterns, and common errors
- `github-workflow.instructions.md`: issue + commit workflow and commit hygiene
- `ingesters.instructions.md`: ingester structure, discovery, config, and testing
- `diagrams.instructions.md`: Mermaid diagram style and conventions
- `operations.instructions.md`: rules for writing and maintaining `docs/OPERATIONS.md`
- `user-guide.instructions.md`: rules for writing and maintaining `docs/USER_GUIDE.md`
