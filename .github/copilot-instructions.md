# Shape Shifter - AI Coding Agent Instructions

## Project Architecture

**Shape Shifter** is a mono-repo with three components:
1. **Core** (`src/`) - Declarative data transformation engine (Python)
2. **Backend** (`backend/app/`) - FastAPI REST API for configuration editing
3. **Frontend** (`frontend/`) - Vue 3 + Vuetify web editor

All Python code shares a **unified virtual environment** at root `.venv/`.

### Core Processing Pipeline
1. **Extract** (`src/extract.py`) - Load data from sources (CSV, SQL, fixed values)
2. **Filter** (`src/filter.py`) - Apply post-load filters (e.g., `exists_in`)
3. **Link** (`src/link.py`) - Resolve foreign key relationships with constraint validation
4. **Unnest** (`src/unnest.py`) - Transform wide to long format (melt operations)
5. **Translate** (`src/mapping.py`) - Map column names to target schema
6. **Store** - Output to CSV, Excel, or database

The orchestrator is `ShapeShifter` in `src/normalizer.py` which uses `ProcessState` for topological sorting.

### Backend Architecture (`backend/app/`)
- **API Layer** (`api/v1/endpoints/`) - FastAPI routers for each feature
- **Services** (`services/`) - Business logic (validation, auto-fix, query execution)
- **Models** (`models/`) - Pydantic v2 schemas for request/response (raw `${ENV_VARS}`)
- **Mappers** (`mappers/`) - Layer boundary translators (resolve env vars here)
- **Core** (`core/`) - Settings and configuration

Key services:
- `validation_service.py` - Multi-type validation (structural, data, entity-specific)
- `auto_fix_service.py` - Automated fix suggestions with backup/rollback
- `query_service.py` - SQL query execution against configured data sources
- `schema_service.py` - Database schema introspection
- `shapeshift_service.py` - Entity preview with intelligent 3-tier cache (TTL, version, hash)

Key mappers:
- `data_source_mapper.py` - API ↔ Core translation + environment variable resolution
- `table_schema_mapper.py` - Schema metadata translation

### Frontend Architecture (`frontend/src/`)
- **Vue 3 Composition API** with `<script setup>` syntax
- **Pinia stores** (`stores/`) - State management for config, validation, entities
- **Composables** (`composables/`) - Reusable logic (useValidation, useAutoFix)
- **API layer** (`api/`) - Axios-based API clients with interceptors
- **Monaco Editor** integration for YAML editing

Key stores:
- `configuration.ts` - Config file CRUD operations
- `validation.ts` - Validation state and entity-level results
- `entity.ts` - Entity selection and editing state
- `data-source.ts` - Database connection management

Key composables:
- `useValidation()` - Validation with auto-validate and change tracking
- `useAutoFix()` - Automated fix suggestions and application

## Development Workflow

### Setup (Unified Environment)
```bash
make install              # Full setup: core + api + dev tools
# Or selective:
uv pip install -e ".[api]"  # Core + API only
uv pip install -e .         # Core only
```

### Running
```bash
make backend-run          # Start FastAPI at http://localhost:8012
make frontend-run         # Start Vue dev server at http://localhost:5173
```

### Testing
```bash
make test                 # All tests (core + backend)
uv run pytest tests -v    # Core tests only
uv run pytest backend/tests -v  # Backend tests only
PYTHONPATH=.:backend uv run pytest backend/tests -v  # If import issues
```

### Linting
```bash
make lint                 # Full lint (tidy + pylint + check-imports)
make tidy                 # Format with black + isort
```

## Critical Patterns

### Registry Pattern (Core)
Used for extensible validators, loaders, filters:
```python
@Validators.register(key="cardinality", stage="pre-merge")
class CardinalityValidator(ConstraintValidator):
    pass
```

### Driver Schema Pattern (Loaders)
**Critical**: Driver configuration schemas are defined directly in loader classes using `ClassVar`:
```python
from typing import ClassVar
from src.loaders.driver_metadata import DriverSchema, FieldMetadata

@DataLoaders.register(key="postgresql")
class PostgresSqlLoader(DataLoader):
    schema: ClassVar[DriverSchema] = DriverSchema(
        driver="postgresql",
        display_name="PostgreSQL",
        description="Connect to PostgreSQL database",
        category="database",
        fields=[
            FieldMetadata(name="host", type="string", required=True, ...),
            FieldMetadata(name="port", type="number", required=False, ...),
            # ...
        ]
    )
```

**Pattern responsibilities:**
- Loader classes (`src/loaders/`) - Define `schema` as `ClassVar[DriverSchema]`
- DriverSchemaRegistry (`src/loaders/driver_metadata.py`) - Introspects `DataLoaders.items` for schemas
- Backend endpoint (`backend/app/api/v1/endpoints/data_sources.py`) - Uses `DriverSchemaRegistry.all()`

**Benefits:**
- Single source of truth (schema lives with implementation)
- Impossible to forget updating schema when adding new loader
- Type safety with Pydantic validation
- Follows existing registry pattern
- No separate YAML file to maintain

### Async/Await
- **Data loaders** (`src/loaders/`) are async - always `await loader.load()`
- **Backend services** mix sync/async - check method signatures carefully
- **Tests**: Use `@pytest.mark.asyncio` + `async def` for async tests

### Backend Imports
Backend imports from core using absolute paths:
```python
from src.model import ShapeShiftConfig  # Core models
from src.configuration.provider import ConfigStore  # Config singleton
from backend.app.services.validation_service import ValidationService  # Backend
```

### Mapper Pattern (Environment Variables)
**Critical**: Environment variable resolution happens ONLY in the mapper layer:
```python
# backend/app/mappers/data_source_mapper.py
class DataSourceMapper:
    @staticmethod
    def to_core_config(api_config: ApiDataSourceConfig) -> CoreDataSourceConfig:
        # Resolution at the API/Core boundary
        api_config = api_config.resolve_config_env_vars()
        return CoreDataSourceConfig(...)  # Fully resolved
```

**Layer responsibilities:**
- API Models (`backend/app/models/`) - Raw `${ENV_VARS}` (unresolved)
- Services (`backend/app/services/`) - Work with raw API entities
- Mappers (`backend/app/mappers/`) - **Resolve env vars here**
- Core (`src/`) - Always fully resolved

**Never** call `resolve_config_env_vars()` in services - let the mapper handle it.

### Test Patterns
```python
# Core tests - use decorator for config setup
@pytest.mark.asyncio
@with_test_config
async def test_something(self, test_provider):
    result = await normalizer.normalize()

# Backend tests - use TestClient
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/api/v1/health")

# Backend service tests - mock state via instance attribute
service = ConfigurationService()
mock_state = MagicMock()
service.state = mock_state  # Correct pattern
# NOT: patch('src.configuration.provider.get_application_state')

# Database loader tests - mock connection and internal methods
with patch.object(loader, "connection"):
    with patch.object(loader, "_get_tables", return_value=mock_tables):
        tables = await loader.get_tables()

# Dispatcher tests - mock class constructor, not lambda
mock_dispatcher = Mock()
mock_dispatcher_cls = Mock(return_value=mock_dispatcher)
with patch("src.normalizer.Dispatchers.get", return_value=mock_dispatcher_cls):
    normalizer.store(target="output.xlsx", mode="xlsx")
    mock_dispatcher_cls.assert_called_once_with(config)
```

### Immutability Pattern
Functions that process configuration data should use deep copy to prevent mutations:
```python
def resolve_references(data: dict) -> dict:
    """Resolve references without mutating input."""
    data = copy.deepcopy(data)  # Protect against mutations
    # ... process data
    return data
```

## Code Conventions

- **Imports**: Absolute only (`from src.module import X`, never relative)
- **Line length**: 140 characters
- **Formatting**: Black + isort (run `make tidy`)
- **Logging**: Use `loguru.logger` (pre-configured)
- **Type hints**: Required for all functions (Pydantic v2 for models)

### Naming
- Entity names: `snake_case` (e.g., `sample_type`)
- Surrogate IDs: Must end with `_id` (e.g., `sample_type_id`)
- API endpoints: `/api/v1/{resource}` (plural nouns)

## Conventional Commit Messages

When committing changes to this repository, use the [Conventional Commits](https://www.conventionalcommits.org/) format to maintain a clear and parseable git history. This project uses **semantic-release** to automatically generate version numbers, changelogs, and releases based on commit messages.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

The project uses the Angular preset with custom release rules:

- **feat**: A new feature (triggers **minor** release)
- **fix**: A bug fix (triggers **patch** release)
- **docs**: Documentation only changes (triggers **patch** release if scope is README)
- **style**: Changes that don't affect code meaning (triggers **patch** release)
- **refactor**: Code change that neither fixes a bug nor adds a feature (triggers **patch** release)
- **perf**: Performance improvement (triggers **patch** release)
- **test**: Adding or correcting tests (no release)
- **build**: Changes to build system or dependencies (no release)
- **ci**: Changes to CI/CD configuration (no release)
- **chore**: Other changes that don't modify src or test files (no release)
- **revert**: Reverts a previous commit (no release)

### Scopes (Optional)

Use scopes to indicate which part of the codebase is affected:
- `core`: Core processing pipeline (`src/`)
- `backend`: Backend API (`backend/app/`)
- `frontend`: Frontend application (`frontend/`)
- `config`: Configuration handling
- `validation`: Validation services
- `cache`: Caching functionality
- `loaders`: Data loaders (SQL, CSV, fixed)
- `api`: API endpoints and routes
- `services`: Backend service layer
- `mappers`: Data mappers
- `tests`: Test-specific changes
- `deps`: Dependency updates

### Examples

```bash
# Feature additions (MINOR release)
git commit -m "feat(cache): implement 3-tier cache validation with hash-based invalidation"
git commit -m "feat(frontend): add entity preview with auto-refresh"
git commit -m "feat(loaders): add UCanAccess support for MS Access databases"

# Bug fixes (PATCH release)
git commit -m "fix(backend): correct mock pattern in service tests"
git commit -m "fix(validation): prevent mutation in resolve_references"
git commit -m "fix(frontend): resolve dark mode text color in preview grid"

# Documentation (PATCH release if scope is README)
git commit -m "docs: update copilot-instructions with recent improvements"
git commit -m "docs(README): add installation instructions for UCanAccess"
git commit -m "docs(api): add examples for reconciliation endpoints"

# Tests (no release)
git commit -m "test(loaders): add comprehensive UCanAccessSqlLoader tests"
git commit -m "test(cache): add hash-based invalidation test cases"

# Refactoring (PATCH release)
git commit -m "refactor(config): use deep copy to prevent mutations"
git commit -m "refactor(services): extract validation logic to separate service"

# Performance (PATCH release)
git commit -m "perf(cache): use xxhash for faster entity hashing"

# Chores (no release)
git commit -m "chore: update dependencies to latest versions"
git commit -m "chore(deps): bump pydantic from 2.0.0 to 2.5.0"

# Build/CI (no release)
git commit -m "build: add support for Python 3.13"
git commit -m "ci: add automated test coverage reporting"
```

### Multi-line Commits

For more complex changes, use the body to explain what and why:

```bash
git commit -m "feat(cache): implement hash-based cache invalidation

Add xxhash-based entity configuration hashing to detect changes
beyond version numbers. Implements 3-tier validation:
1. TTL check (300s)
2. Config version comparison
3. Entity hash validation

This prevents serving stale cached data when entity configuration
changes without version bump.

Closes #123"
```

### Breaking Changes

Indicate breaking changes with a `!` after the type/scope or in the footer. This triggers a **MAJOR** release:

```bash
# Breaking change with ! notation (MAJOR release)
git commit -m "feat(api)!: change response format for validation errors"

# Or in footer (MAJOR release)
git commit -m "feat(api): change response format

BREAKING CHANGE: validation error responses now return array of errors
instead of single error object. Update API clients to handle new format."
```

### Release Automation

This project uses **semantic-release** configured in `.releaserc.json`:

- Commits are analyzed using the Angular preset
- Version numbers are automatically determined based on commit types
- `CHANGELOG.md` is automatically generated
- Version in `pyproject.toml` is automatically updated
- Git tags are created automatically on the `main` branch

**Important**: Only commits on the `main` branch trigger releases.

### Commit Message Validation

The project uses **pre-commit hooks** for code quality:
- Ruff for linting and formatting
- Import consistency checking

To enable commit message validation, you can optionally install commitlint:

```bash
# Install commitizen for interactive commits
pip install commitizen

# Use cz for guided commits
cz commit

# Or install commitlint (requires Node.js)
npm install -g @commitlint/cli @commitlint/config-conventional

# Create commitlint config
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js

# Add to .pre-commit-config.yaml
```

### Tips

- **Keep the subject line under 72 characters**
- **Use imperative mood** ("add" not "added" or "adds")
- **Don't capitalize** the first letter of the description
- **Don't end** the description with a period
- **Reference issues/PRs** in the footer when applicable (e.g., `Closes #123`, `Fixes #456`)
- **Use the body** to explain **what** and **why**, not **how**
- **Add co-authors** when pairing: `Co-authored-by: Name <email@example.com>`
- **Use `[skip ci]`** in commit message to skip CI builds when appropriate
- **Check release impact**: `feat` = minor, `fix`/`refactor`/`style` = patch, breaking = major

### Common Mistakes to Avoid

❌ **Bad**:
```bash
git commit -m "Fixed bug"  # No type
git commit -m "feat: Added new feature."  # Capitalized and period
git commit -m "update docs"  # No type
git commit -m "WIP"  # Not descriptive
```

✅ **Good**:
```bash
git commit -m "fix(validation): prevent null pointer in entity resolution"
git commit -m "feat(api): add batch validation endpoint"
git commit -m "docs(README): update installation instructions"
git commit -m "refactor(core): simplify dependency resolution logic"
```

### Reverting Commits

When reverting a commit, use the `revert` type and reference the original commit:

```bash
git commit -m "revert: feat(cache): implement hash-based invalidation

This reverts commit abc123def456.
Reason: causes performance degradation in production."
```

## Common Tasks

### Adding a Backend Endpoint
1. Create router in `backend/app/api/v1/endpoints/`
2. Add Pydantic models in `backend/app/models/`
3. Implement service in `backend/app/services/`
4. Register router in `backend/app/api/v1/api.py`

### Adding a Data Loader
1. Create class in appropriate file (`sql_loaders.py`, `file_loaders.py`, `exel_loaders.py`)
2. Inherit from `DataLoader` base class
3. Register: `@DataLoaders.register(key="driver_name")`
4. **Define schema**: Add `schema: ClassVar[DriverSchema]` with field definitions
5. Implement async `load()` method
6. Add tests in `tests/loaders/test_*_loaders.py`

### Adding a Constraint Validator
1. Create class in `src/constraints.py` inheriting `ConstraintValidator`
2. Register: `@Validators.register(key="name", stage="pre-merge|post-merge")`
3. Add tests in `tests/test_constraints.py`

### Adding Configuration Validation
1. Create class in `src/specifications.py` inheriting `ConfigSpecification`
2. Implement `is_satisfied_by()` returning bool
3. Add to `CompositeConfigSpecification.__init__()` list

## Frontend Conventions

### Vue 3 Patterns
- Use `<script setup lang="ts">` for all components
- Prefer composables over mixins for shared logic
- Use `defineProps<T>()` and `defineEmits<T>()` for type-safe props/events
- Destructure store state with `storeToRefs()` for reactivity

### API Integration
```typescript
// API clients in frontend/src/api/
import { apiClient } from '@/api/client'

// Base URL: VITE_API_BASE_URL || 'http://localhost:8012'
// All endpoints prefixed with /api/v1
const response = await apiClient.get('/configurations')
```

### Pinia Store Pattern
```typescript
// stores/example.ts
export const useExampleStore = defineStore('example', () => {
  const data = ref<DataType | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchData() {
    loading.value = true
    try {
      data.value = await api.getData()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetchData }
})
```

### TypeScript Conventions
- Define interfaces for API responses in `types/` directory
- Use strict null checks - handle `null | undefined` explicitly
- Prefer `type` for unions, `interface` for objects

## Key Files
- `src/model.py` - Core configuration Pydantic models
- `src/constraints.py` - Foreign key constraint validators
- `src/specifications.py` - Configuration validation rules
- `src/configuration/config.py` - Configuration loading and resolution (immutable operations)
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/services/validation_service.py` - Multi-type validation
- `backend/app/services/shapeshift_service.py` - Entity preview with 3-tier cache
- `frontend/src/stores/` - Pinia state management

## Recent Improvements (Dec 2024)

### Class-Based Driver Schemas
- **Schema location**: Defined in loader classes as `ClassVar[DriverSchema]`
- **Introspection**: `DriverSchemaRegistry` loads schemas from registered loader classes
- **Benefits**: Single source of truth, impossible to forget updating, type safety
- **Implementation**: All loaders (PostgreSQL, SQLite, MS Access, CSV, Excel) have embedded schemas

### Cache System (shapeshift_service.py)
- **3-tier validation**: TTL (300s) → Config version → Entity hash (xxhash)
- **CacheMetadata**: Tracks timestamp, config_name, entity_name, config_version, entity_hash
- **Hash-based invalidation**: Detects entity configuration changes via xxhash.xxh64
- **Smart dependencies**: Validates cached dependency hashes before reuse

### Code Quality Patterns
- **Mutation prevention**: Use `copy.deepcopy()` in config processing functions
- **Mock patterns**: 
  - Service tests: Mock state via instance attribute (`service.state = mock_state`)
  - Database tests: Mock `connection()` and internal methods (`_get_tables`, `_get_columns`)
  - Dispatcher tests: Mock class constructor, not lambda
- **Test coverage**: Comprehensive tests for UCanAccessSqlLoader (MS Access specific behaviors)

## Documentation
- [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md) - Complete YAML configuration reference (2,500+ lines)
- [docs/SYSTEM_DOCUMENTATION.md](docs/SYSTEM_DOCUMENTATION.md) - Architecture and component overview
- [docs/BACKEND_API.md](docs/BACKEND_API.md) - REST API endpoint reference
- [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - Setup and contribution guidelines

## External Dependencies
- **UCanAccess**: MS Access via JDBC (install: `scripts/install-uncanccess.sh`)
- **Java JRE**: Required for UCanAccess
- **pnpm**: Frontend package manager
