# Shape Shifter - AI Coding Instructions

## Documentation scope

Use current documentation in `docs/`.
Ignore `docs/archive/`.
Treat `docs/features/` as future backlog, not authoritative implementation guidance, unless the user asks about roadmap or planned features.

Start with:
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/USER_GUIDE.md`
- `docs/REQUIREMENTS.md`
- `docs/TESTING_GUIDE.md`
- `docs/AI_VALIDATION_GUIDE.md`

For proposal work:
- follow `docs/PROPOSAL_WRITING_GUIDE.md`
- use `docs/templates/PROPOSAL_TEMPLATE.md` unless asked otherwise
- keep proposals concise and decision-oriented

## Repository structure

Shape Shifter is a monorepo with three main components:
- `src/`: core Python transformation engine
- `backend/app/`: FastAPI backend
- `frontend/`: Vue 3 + Vuetify frontend

Python uses the root `.venv/`.

## Critical architectural rules

### API/Core separation

Maintain strict separation between API and Core layers.

- API models live in `backend/app/models/`
- Core domain logic lives in `src/`
- Use mappers for API ↔ Core conversion
- Resolve env vars and directives only in the mapper layer
- Do not put business logic in API DTOs
- Do not import API-layer models into `src/`

### Circular dependencies

Avoid circular imports by using dependency injection or factory functions.

- Prefer constructor injection
- Use `TYPE_CHECKING` imports for type hints
- Do not treat lazy imports inside methods as the long-term solution

### Pure domain validators

Validators in `src/validators/` must be pure domain logic.

- Accept data and config as input
- Return domain validation issues
- Do not fetch data
- Do not depend on backend services
- Do not import API models

Backend orchestrators may fetch data and convert domain issues to API models.

## Core patterns

### Registry pattern

Use the existing registry pattern for validators, loaders, filters, and ingesters.

### Driver schema pattern

Driver configuration schemas belong on loader classes as `ClassVar[DriverSchema]`.

- Define schema on the loader class
- Do not maintain separate schema YAML/files for loaders
- `DriverSchemaRegistry` should discover schemas from registered loaders

### Identity system

All relationships use local `system_id` values.

- `system_id`: local sequential identity used for relationships
- `keys`: business keys for matching and deduplication
- `public_id`: target schema identity / exported FK column name

Do not use external IDs as internal FK values.

## Backend guidance

Use absolute imports:
- core: `from src...`
- backend: `from backend.app...`

Check async/sync boundaries carefully:
- loaders are async and must be awaited
- backend services may be sync or async; check signatures before calling

When adding a backend feature:
1. add or update endpoint in `backend/app/api/v1/endpoints/`
2. add or update Pydantic models in `backend/app/models/`
3. implement logic in `backend/app/services/`
4. register router in `backend/app/api/v1/api.py`

## Frontend guidance

- Use Vue 3 Composition API with `<script setup lang="ts">`
- Prefer composables over mixins
- Use typed props and emits
- Use `storeToRefs()` when destructuring Pinia stores
- Keep API access in `frontend/src/api/`

## Testing and validation

Before finishing:
- run targeted tests for the changed area
- run broader tests when changes cross layers
- preserve architecture boundaries
- validate `shapeshifter.yml` changes against `docs/AI_VALIDATION_GUIDE.md`

Common commands:

```bash
make test
uv run pytest tests -v
uv run pytest backend/tests -v
PYTHONPATH=.:backend uv run pytest backend/tests -v
make lint
make tidy
```

## Code conventions

- Imports: absolute only
- Line length: 140
- Formatting: black + isort via `make tidy`
- Logging: use `loguru.logger`
- Type hints: required for all functions

Naming:
- entity names: `snake_case`
- public IDs must end with `_id`
- API endpoints use `/api/v1/{resource}` with plural nouns

## Common tasks

### Add a data loader

1. create loader class in the appropriate loader module
2. inherit from `DataLoader`
3. register with `@DataLoaders.register(key="driver_name")`
4. define `schema: ClassVar[DriverSchema]`
5. implement async `load()`
6. add tests in `tests/loaders/`

### Add a constraint validator

1. create class in `src/constraints.py`
2. inherit `ConstraintValidator`
3. register with `@Validators.register(...)`
4. add tests

### Add project validation

1. create specification in `src/specifications.py`
2. implement `is_satisfied_by()`
3. register it in `CompositeConfigSpecification`

### Add a data ingester

1. create `ingesters/<name>/`
2. implement the ingester protocol
3. register with `@Ingesters.register(key="<name>")`
4. add backend tests
5. rely on discovery; do not manually wire imports unless required

## Commits

Use Conventional Commits:
`<type>(<scope>): <description>`

Rules:
- imperative mood
- lowercase description
- no trailing period
- subject under 72 chars
- keep commits atomic
- do not stage unrelated files

Common scopes:
- `core`
- `backend`
- `frontend`
- `validation`
- `loaders`
- `services`
- `mappers`
- `tests`
- `deps`
