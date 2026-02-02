# Shape Shifter – Agent Guide

## Architecture Awareness
- Treat the repo as a mono-repo with Core (`src/`), Backend (`backend/app/`), and Frontend (`frontend/`).
- Use the unified Python virtual environment at `.venv/` for every Python command.
- Preserve the core pipeline order: Extract ➜ Filter ➜ Link ➜ Unnest ➜ Translate ➜ Store; orchestrate via `ShapeShifter` (`src/normalizer.py`) using `ProcessState`.
- Keep backend layering clear: routers in `api/v1/endpoints/`, services in `services/`, Pydantic v2 models in `models/`, and shared settings in `core/`.
- Build frontend features with Vue 3 `<script setup>` components, Pinia stores, composables, Axios API layer, and Monaco-based YAML editing.

## Workflow Commands
- Run `make install` for full setup; use `uv pip install -e ".[api]"` for Core+API or `uv pip install -e .` for Core only.
- Start local services with `make backend-run` (FastAPI on :8012) and `make frontend-run` (Vue on :5173).
- Execute tests with `make test` for full coverage, `uv run pytest tests -v` for Core, or `uv run pytest backend/tests -v` (add `PYTHONPATH=.:backend` if imports fail).
- Test frontend with `make frontend-test` or get coverage with `make frontend-coverage`.
- Enforce formatting and linting with `make lint` (backend) and `make frontend-lint` (frontend); run `make tidy` (Black + isort) before committing.
- When you execute a shell command, launch shell with login:false flag.

## Critical Patterns & Constraints
- Register extensible validators/loaders/filters through the registry pattern (`@Validators.register(...)`).
- Await every async data loader in `src/loaders/`; check backend service signatures before mixing sync/async logic.
- Decorate async tests with `@pytest.mark.asyncio` (Core) and use FastAPI `TestClient` for backend routes.
- Import backend usages of Core with absolute paths only (e.g., `from src.model import ShapeShiftProject`).

### Layer Boundary Architecture (Awesome Rule) ⭐

**Critical: Services must convert between API and Core layers using ProjectMapper.**

**Why awesome:** Domain logic (`TaskList`, business rules) lives in Core (framework-independent), not API DTOs. This enables CLI/script usage, cleaner tests, and prevents tight coupling.

**Correct pattern:**
```python
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from src.model import ShapeShiftProject

# Load API model
api_project: Project = project_service.load_project(name)

# Convert to Core for domain logic
project: ShapeShiftProject = ProjectMapper.to_core(api_project)

# Business logic (task_list only on Core)
project.task_list.mark_completed(entity)

# Convert back to API
updated: Project = ProjectMapper.to_api_config(project.cfg, name)

# Save
project_service.save_project(updated)
```

**Never:**
- Skip mapper (causes type confusion: `Project` ≠ `ShapeShiftProject`)
- Put business logic in API models (they're DTOs)
- Resolve env vars in services (mapper's job)

**Directive Resolution at Layer Boundaries:**

The mapper enforces a critical architectural principle:

- **API → Core (`to_core`)**: **Always resolves** @include: and @value: directives
  - Core layer needs concrete values for processing (loaders, validators, normalization)
  - Resolution is conditional (only if `not project.is_resolved()`)
  - Processing is one-way; no Core → API roundtrip that would lose directives

- **YAML → API (`to_api_config`)**: **Preserves** directives
  - API layer is the editing/persistence boundary
  - Directives (@include:, @value:) are kept for editing and saving
  
- **API → YAML (`to_core_dict`)**: **Preserves** directives
  - Saving back to YAML maintains original structure
  - Prevents verbose files from expanded includes

**Principle: Directives live in YAML/API layer, resolved values in Core layer.**

**Environment variable resolution**: Happens ONLY in mapper layer (`backend/app/mappers/`). API entities stay raw (`${VAR}`), core entities are always resolved. Never call `resolve_config_env_vars()` in services.

## Code Conventions
- Keep line length ≤ 140 characters and rely on Black + isort formatting.
- Use `loguru.logger` for logging and provide type hints for all functions (including Pydantic models).
- Follow naming rules: snake_case entities, `_id` suffix for public IDs, `/api/v1/{resource}` (plural) for endpoints.

## Three-Tier Identity System
**Critical: All relationships use local `system_id` values.**

1. **`system_id`** - Local sequential (1, 2, 3...), always present, used for ALL FK relationships
2. **`keys`** - Business keys for deduplication and matching (optional)
3. **`public_id`** - Target schema column name + holds SEAD IDs from mappings.yml (dual purpose)

**FK Resolution:** Child FK column = parent's `public_id` name, FK values = parent's `system_id` values.
**Mapping:** `map_to_remote()` decorates `public_id` column with SEAD IDs (separate from FK logic).

See `.github/copilot-instructions.md` for detailed examples.

## Common Implementation Tasks
- **Backend endpoint**: add router (`backend/app/api/v1/endpoints/`), define Pydantic models (`backend/app/models/`), implement service (`backend/app/services/`), and register in `backend/app/api/v1/api.py`.
- **Constraint validator**: create class in `src/constraints.py`, decorate with `@Validators.register(key=..., stage=...)`, and add tests in `tests/test_constraints.py`.
- **Project validation**: subclass `ProjectSpecification` in `src/specifications.py`, implement `is_satisfied_by()`, and include it inside `CompositeProjectSpecification.__init__()`.
- **Data ingester**: create directory under `backend/app/ingesters/<name>/`, implement `Ingester` protocol in `ingester.py`, decorate with `@Ingesters.register(key="<name>")`, import in `backend/app/ingesters/__init__.py` to trigger registration, and add tests in `backend/tests/ingesters/`.

## Ingester Development Pattern
Ingesters provide a standardized interface for importing data into Shape Shifter from external systems. Each ingester is self-contained and registered via a global registry.

### Ingester Protocol
All ingesters must implement the `Ingester` protocol from `backend/app/ingesters/protocol.py`:
```python
from backend.app.ingesters.protocol import Ingester, IngesterConfig, IngesterMetadata, ValidationResult, IngestionResult
from backend.app.ingesters.registry import Ingesters

@Ingesters.register(key="my_ingester")
class MyIngester(Ingester):
    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="my_ingester",
            name="My Data Ingester",
            description="Imports data from MySystem",
            version="1.0.0",
            supported_formats=["xlsx", "csv"],
        )

    def __init__(self, config: IngesterConfig):
        self.config = config
        # Initialize your ingester

    def validate(self, source: str) -> ValidationResult:
        # Validate source data without making changes
        errors = []
        warnings = []
        # ... validation logic ...
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def ingest(self, source: str) -> IngestionResult:
        # Perform the actual data ingestion
        # ... ingestion logic ...
        return IngestionResult(success=True, records_processed=count, message="Import completed")
```

### Registration & Discovery
- Ingesters auto-register via the `@Ingesters.register(key="...")` decorator
- The key must be unique and is used to identify the ingester in API calls
- Ingesters are dynamically discovered at application startup from `ingesters/` directory
- Create ingester in `ingesters/<name>/` directory with `ingester.py` containing main class
- Access registered ingesters: `Ingesters.items`, `Ingesters.get(key)`, `Ingesters.get_metadata_list()`

### Configuration Pattern
- Use `IngesterConfig` dataclass with `extra: dict[str, Any]` for custom parameters
- Database credentials: `host`, `port`, `dbname`, `user` (standard fields)
- Ingester-specific settings go in `extra` dict (e.g., `extra={"ignore_columns": [], "batch_size": 1000}`)
- Pass explicit values to avoid ConfigValue lookups in tests:
  ```python
  config = IngesterConfig(
      host="localhost",
      port=5432,
      dbname="test_db",
      user="test_user",
      submission_name="test",
      data_types="test_data",
      extra={"ignore_columns": []},  # Explicit config avoids ConfigValue
  )
  ```

### Testing Pattern
- Create test file in `backend/tests/ingesters/test_<ingester_name>.py`
- Test metadata retrieval, validation logic, and successful ingestion
- Use explicit `extra` config values to avoid ConfigStore initialization issues
- Example test structure:
  ```python
  class TestMyIngester:
      def test_metadata(self):
          metadata = MyIngester.get_metadata()
          assert metadata.key == "my_ingester"
          assert metadata.version == "1.0.0"

      def test_validation(self):
          config = IngesterConfig(..., extra={"param": "value"})
          ingester = MyIngester(config)
          result = ingester.validate("path/to/source")
          assert result.is_valid

      def test_ingestion(self, mock_db):
          # ... test ingestion with mocked dependencies
  ```

### File Organization
```
backend/app/ingesters/
├── __init__.py           # Protocol and registry imports only
├── protocol.py           # Ingester interface and result types
├── registry.py           # IngesterRegistry with dynamic discovery
└── README.md             # Guide to ingester system
ingesters/                # Top-level ingesters directory
├── __init__.py           # Package marker
├── README.md             # Guide for creating new ingesters
└── <ingester_name>/      # Each ingester in its own directory
    ├── __init__.py
    ├── ingester.py       # Main ingester class implementing protocol
    └── ...               # Supporting modules (loaders, validators, etc.)
```

### Key Considerations
- **ConfigValue Isolation**: If your ingester uses Shape Shifter's `ConfigValue`, ensure it can accept explicit parameters to avoid config context issues in tests. Use pattern: `if param is not None: use_param else: ConfigValue().resolve()`
- **Validation-First**: Always implement thorough validation in `validate()` before attempting `ingest()`
- **Error Handling**: Return structured errors/warnings in `ValidationResult` and `IngestionResult`
- **Database Connections**: Use connection context managers and handle timeouts
- **Testing**: Provide explicit config values via `extra` dict to avoid ConfigStore dependencies

## CLI Tool Usage

The ingester system includes a CLI tool for command-line operations:

### List Available Ingesters
```bash
python -m backend.app.scripts.ingest list-ingesters
```

### Validate Data Source
```bash
# Basic validation
python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx

# With configuration file
python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx \
  --config ingest_config.json

# With ignore patterns
python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx \
  --ignore-columns "date_updated" --ignore-columns "*_uuid"
```

### Ingest Data
```bash
# Basic ingestion
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "dendro_2026_01" \
  --data-types "dendro" \
  --database-host localhost \
  --database-port 5432 \
  --database-name sead_staging \
  --database-user sead_user

# With registration and explosion
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "dendro_2026_01" \
  --data-types "dendro" \
  --config ingest_config.json \
  --register \
  --explode

# Full example with all options
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "ceramics_batch_001" \
  --data-types "ceramics" \
  --output-folder /output/ceramics \
  --database-host db.example.com \
  --database-port 5433 \
  --database-name sead_prod \
  --database-user import_user \
  --ignore-columns "temp_*" \
  --register \
  --explode \
  --verbose
```

### Configuration File Format
Create a JSON config file (`ingest_config.json`):
```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "dbname": "sead_staging",
    "user": "sead_user"
  },
  "ignore_columns": [
    "date_updated",
    "*_uuid",
    "(*"
  ]
}
```

Then use with `--config ingest_config.json`. CLI options override config file values.

## Frontend Practices
- Always use `<script setup lang="ts">`, composables over mixins, and `defineProps<T>()` / `defineEmits<T>()` for typing.
- Derive store refs with `storeToRefs()` and manage state in Pinia stores under `frontend/src/stores/` (e.g., project, validation, entity, data-source stores).
- Implement API interactions through `frontend/src/api/` with Axios interceptors; call endpoints under `/api/v1` using `apiClient` and `VITE_API_BASE_URL` (default `http://localhost:8012`).
- Follow the documented Pinia pattern (loading/error refs with guarded async calls) and enforce strict null checks, preferring `type` for unions and `interface` for objects.

## Key References
- Use `src/model.py`, `src/constraints.py`, and `src/specifications.py` for Core models, constraints, and config rules.
- Touch backend behavior via `backend/app/main.py` and `backend/app/services/validation_service.py`.
- Manage frontend state under `frontend/src/stores/` and related composables.
- Consult docs: `docs/CONFIGURATION_GUIDE.md`, `docs/SYSTEM_DOCUMENTATION.md`, `docs/BACKEND_API.md`, `docs/DEVELOPMENT_GUIDE.md` before major changes.
- For testing: `docs/TESTING_GUIDE.md` (concise functional testing), `docs/testing/` subfolder (error scenarios, templates, non-functional, accessibility).

## External Dependencies
- Install UCanAccess via `scripts/install-uncanccess.sh` when Access support is required.
- Ensure Java JRE is available for UCanAccess integrations.
- Use `pnpm` as the frontend package manager whenever Node dependencies are involved.
