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

The orchestrator is `ArbodatSurveyNormalizer` in `src/normalizer.py` which uses `ProcessState` for topological sorting.

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

## Common Tasks

### Adding a Backend Endpoint
1. Create router in `backend/app/api/v1/endpoints/`
2. Add Pydantic models in `backend/app/models/`
3. Implement service in `backend/app/services/`
4. Register router in `backend/app/api/v1/api.py`

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
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/services/validation_service.py` - Multi-type validation
- `frontend/src/stores/` - Pinia state management

## Documentation
- [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md) - Complete YAML configuration reference (2,500+ lines)
- [docs/SYSTEM_DOCUMENTATION.md](docs/SYSTEM_DOCUMENTATION.md) - Architecture and component overview
- [docs/BACKEND_API.md](docs/BACKEND_API.md) - REST API endpoint reference
- [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - Setup and contribution guidelines

## External Dependencies
- **UCanAccess**: MS Access via JDBC (install: `scripts/install-uncanccess.sh`)
- **Java JRE**: Required for UCanAccess
- **pnpm**: Frontend package manager
