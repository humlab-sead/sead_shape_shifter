# Shape Shifter - AI Coding Agent Instructions

## Documentation Scope

When referencing project documentation, **ignore all files in `docs/archive/`**. These are historical implementation notes and deprecated documentation. Refer only to current documentation in the main `docs/` directory:

- **CONFIGURATION_GUIDE.md** - Complete YAML configuration reference
- **ARCHITECTURE.md** - System architecture and component overview
- **DEVELOPER_GUIDE.md** - Development setup and contribution guidelines
- **USER_GUIDE.md** - End-user documentation
- **REQUIREMENTS.md** - Feature specifications
- **TESTING_GUIDE.md** - Concise functional testing procedures (core workflows only)
- **testing/** - Testing resources subfolder:
  - **ERROR_SCENARIO_TESTING.md** - Error handling and recovery tests
  - **TEST_RESULTS_TEMPLATE.md** - Templates and quick test checklists
  - **APPENDIX.md** - Shortcuts, troubleshooting, tools
  - **NON_FUNCTIONAL_TESTING_GUIDE.md** - Browser compatibility, performance
  - **ACCESSIBILITY_TESTING_GUIDE.md** - WCAG compliance testing

## Project Architecture

**Shape Shifter** is a mono-repo with three components:
1. **Core** (`src/`) - Declarative data transformation engine (Python)
2. **Backend** (`backend/app/`) - FastAPI REST API for project editing
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
- **Services** (`services/`) - Business logic (validation, auto-fix, query execution, dependency analysis)
- **Models** (`models/`) - Pydantic v2 schemas for request/response (raw `${ENV_VARS}`)
- **Mappers** (`mappers/`) - Layer boundary translators (resolve env vars here)
- **Utils** (`utils/`) - Reusable utilities (graph algorithms, SQL parsing)
- **Core** (`core/`) - Settings and configuration

Key services:
- `validation_service.py` - Multi-type validation (structural, data, entity-specific)
- `auto_fix_service.py` - Automated fix suggestions with backup/rollback
- `query_service.py` - SQL query execution against configured data sources
- `schema_service.py` - Database schema introspection
- `shapeshift_service.py` - Entity preview with intelligent 3-tier cache (TTL, version, hash)
- `dependency_service.py` - Entity dependency analysis with cycle detection and topological sorting

Key mappers:
- `data_source_mapper.py` - API ↔ Core translation + environment variable resolution
- `table_schema_mapper.py` - Schema metadata translation

Key utilities:
- `graph.py` - Graph algorithms (cycle detection, topological sort, depth calculation)
- `sql.py` - SQL parsing utilities (table extraction using sqlparse)

### Frontend Architecture (`frontend/src/`)
- **Vue 3 Composition API** with `<script setup>` syntax
- **Pinia stores** (`stores/`) - State management for config, validation, entities
- **Composables** (`composables/`) - Reusable logic (useValidation, useAutoFix)
- **API layer** (`api/`) - Axios-based API clients with interceptors
- **Monaco Editor** integration for YAML editing

Key stores:
- `project.ts` - Project file CRUD operations
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

### Linting & Testing
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
from src.model import ShapeShiftProject  # Core models
from src.configuration.provider import ConfigStore  # Config singleton
from backend.app.services.validation_service import ValidationService  # Backend
```

### Dependency Injection for Circular Imports (Critical Pattern) ⭐

**When services depend on each other, use dependency injection via factory functions instead of lazy imports.**

**Problem - Circular Import:**
```python
# ❌ WRONG: Module-level import causes circular dependency
from backend.app.validators.data_validators import DataValidationService

class ValidationService:
    def validate_data(self):
        validator = DataValidationService()  # DataValidationService also imports ValidationService!
```

**Solution - Dependency Injection:**
```python
# ✅ CORRECT: Inject factory function via constructor
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.validators.data_validators import DataValidationService

class ValidationService:
    def __init__(self, data_validator_factory: Callable[[], "DataValidationService"] | None = None):
        """Inject factory to avoid circular import."""
        self._data_validator_factory = data_validator_factory
    
    def validate_data(self):
        if self._data_validator_factory:
            validator = self._data_validator_factory()
        else:
            # Default factory with lazy import (backward compatible)
            from backend.app.validators.data_validators import DataValidationService
            validator = DataValidationService()
```

**Benefits:**
- **Explicit dependencies**: Constructor signature shows what service needs
- **Testability**: Easy to inject mocks in tests
- **No circular imports**: Factory is just a callable, not a module import
- **Flexibility**: Different contexts can provide different implementations
- **Backward compatible**: Optional parameter with default factory

**Usage:**
```python
# Production (default factory)
service = ValidationService()

# Testing (inject mock)
mock_factory = lambda: mock_validator
service = ValidationService(data_validator_factory=mock_factory)
```

**When to use:**
- Services that depend on each other (validation ↔ data validation)
- Any circular dependency between backend modules
- When you need different implementations in different contexts

**Never:**
- Use lazy imports at method level as permanent solution (use DI instead)
- Import services at module level if they might cause circular dependencies
- Skip TYPE_CHECKING imports (they prevent circular imports at runtime)

### Layer Boundary Architecture (Awesome Pattern) ⭐

**Critical architectural principle: Strict separation between API and Core layers.**

#### Three-Layer Model

```
API Layer (backend/app/models/)    ← HTTP interface, Pydantic validation
      ↕ ProjectMapper
Core Layer (src/model.py)          ← Domain logic, business rules
      ↕ ConfigStore  
YAML Files                         ← Persistence, source of truth
```

**Why awesome:**
- Domain logic (`TaskList`, entity processing) lives in Core (framework-independent)
- API layer is pure interface (no business logic in DTOs)
- Mappers enforce boundaries and prevent layer confusion
- Core can be used in CLI, scripts, ingesters without API dependency
- Testing is cleaner (domain tests don't need HTTP mocking)

#### Mapper Pattern Rules

**1. Environment Variable Resolution** 
Happens ONLY in mapper layer:
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
- API Models (`backend/app/models/`) - Raw `${ENV_VARS}` and directives (@include:, @value:) preserved
- Services (`backend/app/services/`) - Work with raw API entities
- Mappers (`backend/app/mappers/`) - **Resolve env vars + directives at API → Core boundary**
- Core (`src/`) - Always fully resolved (no directives)

**Directive resolution strategy:**
- `ProjectMapper.to_core()`: Resolves @include: and @value: directives (API → Core)
- `ProjectMapper.to_api_config()`: Preserves directives (YAML → API for editing)
- `ProjectMapper.to_core_dict()`: Preserves directives (API → YAML for saving)
- Principle: **Directives live in YAML/API layer, resolved values in Core layer**
- Core layer needs concrete values for processing; API layer keeps references for editing

**2. Domain State Manipulation**
Always use mapper when working with domain state:
```python
# ✅ CORRECT: Service converts API → Core → API
class TaskService:
    async def mark_complete(self, project_name: str, entity: str):
        # Load API model
        api_project: Project = self.project_service.load_project(project_name)
        
        # Convert to Core for business logic
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)
        
        # Domain logic (task_list only exists on Core)
        project.task_list.mark_completed(entity)
        
        # Convert back to API
        updated: Project = ProjectMapper.to_api_config(project.cfg, project_name)
        
        # Save via API layer
        self.project_service.save_project(updated)

# ❌ WRONG: Type confusion
api_project: ShapeShiftProject = load_project(name)  # Returns Project, not ShapeShiftProject!
api_project.task_list.mark_completed(entity)  # AttributeError!
```

**Never:**
- Call `resolve_config_env_vars()` in services - mapper's job
- Assign API `Project` to `ShapeShiftProject` variable - type confusion
- Put business logic in API models - keep them as DTOs
- Skip mapper when needing domain logic - always convert properly

### Pure Domain Validators (Awesome Pattern) ⭐

**Critical: Validators are pure domain logic - they receive data, not fetch it.**

**Why awesome:**
- Validators are testable without mocking infrastructure (just pass DataFrames)
- Can validate preview samples OR full normalized datasets
- Reusable across Core, Backend, CLI, scripts without coupling
- Single Responsibility: only validation logic, no data fetching
- Backend orchestrator handles infrastructure concerns (data loading, API conversion)

#### Architecture

```
Domain Layer (src/validators/)      ← Pure validation logic, no dependencies
      ↓ ValidationIssue (domain)
Backend Orchestrator (backend/app/validators/data_validation_orchestrator.py)
      ↓ Fetch data (preview or full)
      ↓ Call domain validators
      ↓ Convert ValidationIssue → ValidationError (domain → API)
Validation Service (backend/app/services/validation_service.py)
      ↓ Coordinate validation types
API Endpoints (backend/app/api/v1/endpoints/)
```

#### Domain Validator Pattern

**Pure validators** - no infrastructure dependencies:
```python
# src/validators/data_validators.py
from dataclasses import dataclass
import pandas as pd

@dataclass
class ValidationIssue:
    """Domain representation of a validation issue."""
    severity: str  # "error", "warning", "info"
    entity: str | None
    field: str | None
    message: str
    code: str
    suggestion: str | None = None

class ColumnExistsValidator:
    """Pure domain validator - receives data, returns issues."""
    
    @staticmethod
    def validate(df: pd.DataFrame, configured_columns: list[str], entity_name: str) -> list[ValidationIssue]:
        """Check configured columns exist - no external dependencies."""
        missing = set(configured_columns) - set(df.columns)
        return [
            ValidationIssue(
                severity="error",
                entity=entity_name,
                field="columns",
                message=f"Column '{col}' not found in data",
                code="COLUMN_NOT_FOUND",
            )
            for col in sorted(missing)
        ]
```

**Backend orchestrator** - handles infrastructure:
```python
# backend/app/validators/data_validation_orchestrator.py
class DataValidationOrchestrator:
    """Orchestrates data fetching and validation."""
    
    def __init__(self, preview_service: ShapeShiftService, project_service: ProjectService):
        """Inject infrastructure services."""
        self.preview_service = preview_service
        self.project_service = project_service
    
    async def validate_all_entities(
        self,
        project_name: str,
        entity_names: list[str] | None = None,
        use_full_data: bool = False,  # ⭐ Preview OR full dataset
    ) -> list[api.ValidationError]:
        """Fetch data and call pure validators."""
        # 1. Load project and resolve directives
        project = self.preview_service.project_service.load_project(project_name)
        core_project = ProjectMapper.to_core(project)
        
        # 2. Fetch data (preview samples OR full normalized)
        if use_full_data:
            df = await self._fetch_full_data(project_name, entity_name)
        else:
            df = await self._fetch_preview_data(project_name, entity_name)
        
        # 3. Call pure domain validator
        issues = ColumnExistsValidator.validate(df, columns, entity_name)
        
        # 4. Convert domain → API
        return [self._to_api_error(issue) for issue in issues]
```

#### Key Principles

**✅ Domain validators:**
- Static methods receiving DataFrames + config
- Return `ValidationIssue` (domain model)
- No async (pure functions)
- No service dependencies
- Testable with mock DataFrames

**❌ Never in domain validators:**
- ShapeShiftService or preview service injection
- Async data fetching
- API model imports (ValidationError)
- Environment variable resolution

**✅ Backend orchestrator:**
- Inject ShapeShiftService for data fetching
- Support `use_full_data` parameter
- Convert ValidationIssue → ValidationError
- Handle exceptions and infrastructure errors

**Testing pattern:**
```python
# Domain validator test - no mocking needed
def test_column_exists_validator():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    issues = ColumnExistsValidator.validate(df, ["a", "b", "missing"], "test")
    assert len(issues) == 1
    assert issues[0].code == "COLUMN_NOT_FOUND"

# Orchestrator test - mock services
@pytest.mark.asyncio
async def test_orchestrator(mock_preview_service):
    orchestrator = DataValidationOrchestrator(mock_preview_service, mock_project)
    errors = await orchestrator.validate_all_entities("project", use_full_data=False)
    # Verify data fetching and API conversion
```

**Benefits:**
- Full dataset validation: Set `use_full_data=True` for post-normalization checks
- Fast tests: Domain validators are synchronous, pure functions
- Reusable: Use validators in CLI scripts, ingesters, backend
- Clear SRP: Validators validate, orchestrators orchestrate

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
service = ProjectService()
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
- Public IDs: Must end with `_id` (e.g., `sample_type_id`)
- API endpoints: `/api/v1/{resource}` (plural nouns)

### Three-Tier Identity System ⭐

**Critical architectural principle: All relationships use local `system_id` values.**

**The Three Tiers:**

1. **`system_id`** (Local Sequential Identity)
   - **Always present**: Auto-generated, column name standardized to `"system_id"`
   - **Local sequential values**: 1, 2, 3... (reset per entity)
   - **Used for ALL relationships**: FK values ALWAYS reference parent's `system_id`
   - Never external IDs - purely local domain

2. **`keys`** (Business Keys)
   - **Optional**: List of column names used for deduplication and matching
   - Examples: `["specimen_id", "lab_code"]`, `["location_name"]`
   - Used by reconciliation to match local data → SEAD entities
   - Applied in `drop_duplicates` and FK joins

3. **`public_id`** (Target Schema Identity)
   - **Dual purpose column**:
     - **Column name**: Matches target system's PK column (e.g., `"location_id"`)
     - **Column values**: Holds mapped SEAD IDs from `mappings.yml`
   - **Required for**: Fixed entities, entities with FK children, entities in mappings
   - **FK column naming**: Child FK column = parent's `public_id` (avoids `system_id` collision)

**Example Workflow:**

```yaml
# Parent entity
location:
  system_id: "system_id"        # Always standardized
  public_id: "location_id"      # Target schema column
  keys: ["location_name"]       # Business key
  
# Child entity  
site:
  system_id: "system_id"
  public_id: "site_id"
  keys: ["site_name"]
  foreign_keys:
    - entity: location
      local_keys: ["location_name"]   # Join on business keys
      remote_keys: ["location_name"]
```

**Processing Result:**

```python
# location table after map_to_remote()
system_id | location_name | location_id  # ← public_id column
    1     | Norway        | 162          # ← SEAD ID from mappings.yml
    2     | Sweden        | 205

# site table after FK link
system_id | site_name | location_name | location_id  # ← FK column
    1     | Site A    | Norway        | 1            # ← Parent's system_id!
    2     | Site B    | Sweden        | 2
```

**Key Principles:**
- ✅ All FK values are `system_id` references (local domain integrity)
- ✅ `public_id` defines FK column names (avoids `system_id` collision in child)
- ✅ SEAD IDs are decoration applied via `map_to_remote()` (separate from FK logic)
- ✅ Export gets proper column names + mapped external IDs

**Validation Rules:**
- Fixed entities → `public_id` REQUIRED
- Entities with FK children → `public_id` REQUIRED (for FK column naming)
- Entities in `mappings.yml` → `public_id` SHOULD match `mapping.remote_key`

## Git Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) with **semantic-release** for automated versioning. AI agents making commits must follow this format:

```
<type>[optional scope]: <description>
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
- `ingesters`: Data ingester plugins (`ingesters/`)
- `config`: Project handling
- `validation`: Validation services
- `cache`: Caching functionality
- `loaders`: Data loaders (SQL, CSV, fixed)
- `api`: API endpoints and routes
- `services`: Backend service layer
- `mappers`: Data mappers
- `tests`: Test-specific changes
- `deps`: Dependency updates

### Breaking Changes
Add `!` after type/scope or `BREAKING CHANGE:` in footer → **MAJOR** release (2.0.0):
```bash
feat(api)!: change response format for validation errors
```

### Examples
```bash
feat(cache): implement hash-based cache invalidation
fix(validation): prevent null pointer in entity resolution
refactor(core): simplify dependency resolution logic
docs(README): update installation instructions
test(loaders): add comprehensive UCanAccessSqlLoader tests
```

**Rules**: Use imperative mood, lowercase description, no trailing period, keep under 72 chars.

### Release Automation

This project uses **semantic-release** configured in `.releaserc.json`:

- Commits are analyzed using the Angular preset
- Version numbers are automatically determined based on commit types
- `CHANGELOG.md` is automatically generated
- Version in `pyproject.toml` is automatically updated
- Git tags are created automatically on the `main` branch

**Important**: Only commits on the `main` branch trigger releases.

### Tips

- **Keep the subject line under 72 characters**
- **Use imperative mood** ("add" not "added" or "adds")
- **Don't capitalize** the first letter of the description
- **Don't end** the description with a period
- **Reference issues/PRs** in the footer when applicable (e.g., `Closes #123`, `Fixes #456`)
- **Use the body** to explain **what** and **why**, not **how**
- **Use `[skip ci]`** in commit message to skip CI builds when appropriate
- **Check release impact**: `feat` = minor, `fix`/`refactor`/`style` = patch, breaking = major

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

### Adding Project Validation
1. Create class in `src/specifications.py` inheriting `ConfigSpecification`
2. Implement `is_satisfied_by()` returning bool
3. Add to `CompositeConfigSpecification.__init__()` list

### Adding a Data Ingester
1. Create directory `ingesters/<name>/` with `__init__.py` and `ingester.py`
2. Implement `Ingester` protocol in `ingester.py` with `get_metadata()`, `validate()`, and `ingest()` methods
3. Register with `@Ingesters.register(key="<name>")` decorator
4. Ingester will be auto-discovered at application startup from `ingesters/` directory
5. Add tests in `backend/tests/ingesters/test_<name>.py`
6. See `ingesters/sead/` for reference implementation and `backend/app/ingesters/README.md` for protocol details

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
- `src/specifications.py` - Project validation rules
- `src/configuration/config.py` - Project loading and resolution (immutable operations)
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/services/validation_service.py` - Multi-type validation
- `backend/app/services/shapeshift_service.py` - Entity preview with 3-tier cache
- `backend/app/ingesters/protocol.py` - Ingester interface definition
- `backend/app/ingesters/registry.py` - Dynamic ingester discovery system
- `ingesters/sead/` - SEAD Clearinghouse ingester implementation
- `frontend/src/stores/` - Pinia state management

## Ingester System

Shape Shifter includes a plugin-based ingester system for importing data from external sources.

### Architecture
- **Protocol-based**: All ingesters implement the `Ingester` protocol from `backend/app/ingesters/protocol.py`
- **Dynamic discovery**: Ingesters are discovered at startup from `ingesters/` directory via `IngesterRegistry.discover()`
- **Separation of concerns**: Ingesters live in top-level `ingesters/` directory, not in `backend/`
- **Configuration**: `INGESTER_PATHS` and `ENABLED_INGESTERS` settings in `backend/app/core/config.py`

### Key Components
- `backend/app/ingesters/protocol.py` - `Ingester` interface, `IngesterConfig`, result types
- `backend/app/ingesters/registry.py` - `IngesterRegistry` with `discover()` method for dynamic loading
- `ingesters/<name>/ingester.py` - Each ingester implementation with `@Ingesters.register(key="<name>")`

### Discovery Mechanism
Ingesters are discovered at three entry points:
1. Application startup: `backend/app/main.py` calls `Ingesters.discover()` in lifespan
2. Test sessions: `backend/tests/conftest.py` has session-scoped `discover_ingesters` fixture
3. CLI scripts: `backend/app/scripts/ingest.py` calls `Ingesters.discover()` at module level

### Creating New Ingesters
See `ingesters/README.md` for detailed guide. Basic steps:
1. Create `ingesters/<name>/` directory with `__init__.py` and `ingester.py`
2. Implement `Ingester` protocol with `get_metadata()`, `validate()`, and `ingest()` methods
3. Decorate class with `@Ingesters.register(key="<name>")`
4. No manual imports needed - discovery is automatic
5. Test with explicit `IngesterConfig` parameters to avoid ConfigValue dependencies

## Recent Improvements (Dec 2024 - Jan 2026)

### Ingester System Relocation (Jan 2026)
- **Relocated**: Ingester implementations moved from `backend/app/ingesters/<name>/` to top-level `ingesters/<name>/`
- **Dynamic Discovery**: Added `IngesterRegistry.discover()` for automatic ingester loading at startup
- **Configuration**: Added `INGESTER_PATHS` and `ENABLED_INGESTERS` settings for flexible ingester management
- **Benefits**: Cleaner separation of concerns, improved reusability, no manual import registration required
- **Breaking Change**: Import paths changed from `backend.app.ingesters.<name>` to `ingesters.<name>`

### Class-Based Driver Schemas
- **Schema location**: Defined in loader classes as `ClassVar[DriverSchema]`
- **Introspection**: `DriverSchemaRegistry` loads schemas from registered loader classes
- **Benefits**: Single source of truth, impossible to forget updating, type safety
- **Implementation**: All loaders (PostgreSQL, SQLite, MS Access, CSV, Excel) have embedded schemas

### Cache System (shapeshift_service.py)
- **3-tier validation**: TTL (300s) → Project version → Entity hash (xxhash)
- **CacheMetadata**: Tracks timestamp, project_name, entity_name, project_version, entity_hash
- **Hash-based invalidation**: Detects entity changes via xxhash.xxh64
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
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Concise functional testing procedures
- [docs/testing/](docs/testing/) - Testing resources (error scenarios, templates, non-functional, accessibility)

## External Dependencies
- **UCanAccess**: MS Access via JDBC (install: `scripts/install-uncanccess.sh`)
- **Java JRE**: Required for UCanAccess
- **pnpm**: Frontend package manager
