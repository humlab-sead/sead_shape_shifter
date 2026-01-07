# Shape Shifter Backend API

REST API for managing Shape Shifter YAML project files and entity configurations.

## Overview

The Shape Shifter backend provides a FastAPI-based REST API that enables:
- Project file management (CRUD, backups, versioning)
- Entity configuration editing
- Real-time validation (structural, data, foreign keys)
- Data source management and schema introspection
- Entity data preview with transformations
- Dependency graph analysis
- Foreign key relationship testing
- Reconciliation workflows

## Installation

The backend is part of the unified Shape Shifter package. Install from the project root:

```bash
# From project root (recommended)
cd /path/to/sead_shape_shifter

# Full installation with all dependencies
make install

# Or manually with uv
uv pip install -e ".[api]"
```

## Quick Start

### Running the Server

```bash
# Using make (recommended)
make backend-run

# Or directly with uvicorn
cd /path/to/sead_shape_shifter
PYTHONPATH=.:backend uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8012
```

### API Documentation

Once running, access interactive documentation:

- **Swagger UI**: http://localhost:8012/api/v1/docs
- **ReDoc**: http://localhost:8012/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8012/api/v1/openapi.json

## Technology Stack

- **FastAPI 0.115+**: Modern async web framework
- **Pydantic v2**: Data validation with type safety
- **ruamel.yaml**: YAML parsing with format/comment preservation
- **NetworkX**: Dependency graph algorithms
- **Pandas**: Data transformation and preview
- **uvicorn**: ASGI server
- **JayDeBeApi**: JDBC connectivity (MS Access, PostgreSQL)

## Architecture

### Layered Structure

```
backend/app/
├── api/v1/endpoints/     # REST endpoint handlers
├── services/             # Business logic layer
├── models/               # Pydantic request/response schemas
├── mappers/              # Layer boundary translation
├── core/                 # Configuration and state
├── validators/           # Data validation logic
└── utils/                # Error handlers, exceptions
```

### Key Architectural Patterns

#### 1. Layer Separation
- **API Layer**: Handles HTTP, serialization, error responses
- **Service Layer**: Business logic, orchestration
- **Mapper Layer**: Translates between API and Core models
- **Core Integration**: Direct use of `src/` components

#### 2. State Management
- **ApplicationState**: In-memory active project editing sessions
- **ApplicationStateManager**: Safe access wrapper with fallbacks
- **Optimistic Locking**: Version-based concurrent edit detection

#### 3. Environment Variable Resolution
**Critical**: Environment variables are resolved ONLY in the mapper layer:
- API models contain raw `${ENV_VAR}` placeholders
- Services work with raw entities
- **Mappers resolve vars** at API/Core boundary
- Core always receives fully resolved values

```python
# backend/app/mappers/data_source_mapper.py
class DataSourceMapper:
    @staticmethod
    def to_core_config(api_config: ApiDataSourceConfig) -> CoreDataSourceConfig:
        # Resolution happens here at the boundary
        api_config = api_config.resolve_config_env_vars()
        return CoreDataSourceConfig(...)
```

#### 4. Preview Caching
Entity preview uses intelligent 3-tier cache validation:
1. **TTL check** (300 seconds)
2. **Project version comparison**
3. **Entity hash validation** (xxhash-based)

Dependencies are also cached and validated by hash.

## API Endpoints

### Projects
- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{name}` - Get project configuration
- `POST /api/v1/projects` - Create new project
- `PUT /api/v1/projects/{name}` - Update project
- `DELETE /api/v1/projects/{name}` - Delete project
- `POST /api/v1/projects/{name}/activate` - Load into ApplicationState
- `GET /api/v1/projects/active` - Get active project name
- `GET /api/v1/projects/{name}/raw-yaml` - Get raw YAML content
- `PUT /api/v1/projects/{name}/raw-yaml` - Update raw YAML

### Entities
- `GET /api/v1/projects/{name}/entities` - List entities
- `GET /api/v1/projects/{name}/entities/{entity_name}` - Get entity
- `POST /api/v1/projects/{name}/entities` - Create entity
- `PUT /api/v1/projects/{name}/entities/{entity_name}` - Update entity
- `DELETE /api/v1/projects/{name}/entities/{entity_name}` - Delete entity

### Validation
- `POST /api/v1/projects/{name}/validate` - Structural validation
- `POST /api/v1/projects/{name}/validate/data` - Data validation
- `GET /api/v1/projects/{name}/auto-fixes` - Get fix suggestions
- `POST /api/v1/projects/{name}/auto-fixes/preview` - Preview fixes
- `POST /api/v1/projects/{name}/auto-fixes/apply` - Apply fixes

### Preview & Testing
- `POST /api/v1/projects/{name}/entities/{entity_name}/preview` - Preview entity data
- `POST /api/v1/projects/{name}/entities/{entity_name}/sample` - Get data sample
- `DELETE /api/v1/projects/{name}/preview-cache` - Clear cache
- `POST /api/v1/projects/{name}/entities/{entity_name}/foreign-keys/{fk_index}/test` - Test FK join

### Dependencies
- `GET /api/v1/projects/{name}/dependencies` - Get dependency graph
- `POST /api/v1/projects/{name}/dependencies/validate` - Check circular dependencies

### Data Sources
- `GET /api/v1/data-sources/drivers` - List available drivers
- `POST /api/v1/data-sources/{name}/test` - Test connection
- `GET /api/v1/data-sources/{name}/schema` - Get database schema
- `GET /api/v1/data-sources/{name}/tables` - List tables
- `GET /api/v1/data-sources/{name}/tables/{table}/preview` - Preview table data
- `POST /api/v1/data-sources/query` - Execute SQL query

### Reconciliation
- `GET /api/v1/projects/{name}/entities/{entity_name}/reconciliation` - Get reconciliation config
- `POST /api/v1/projects/{name}/entities/{entity_name}/reconciliation/preview` - Preview reconciliation
- `POST /api/v1/projects/{name}/entities/{entity_name}/reconciliation/apply` - Apply reconciliation

### Backups
- `GET /api/v1/projects/{name}/backups` - List backups
- `POST /api/v1/projects/{name}/backups/restore` - Restore from backup

### Metadata
- `GET /api/v1/projects/{name}/metadata` - Get project metadata
- `PUT /api/v1/projects/{name}/metadata` - Update metadata

### Health
- `GET /api/v1/health` - API health check

## Configuration

### Environment Variables

Create `.env` in the project root:

```bash
# API Settings
ENVIRONMENT=development
API_PORT=8012
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Directories
PROJECTS_DIR=./projects
BACKUPS_DIR=./backups

# Database (for Authority database - optional)
SEAD_AUTHORITY_DB_HOST=localhost
SEAD_AUTHORITY_DB_PORT=5432
SEAD_AUTHORITY_DB_NAME=sead_authority
SEAD_AUTHORITY_DB_USER=sead
SEAD_AUTHORITY_DB_PASSWORD=secret
```

### Settings Class

Configuration managed via `backend/app/core/config.py`:

```python
from backend.app.core.config import settings

# Access configuration
projects_dir = settings.PROJECTS_DIR
backups_dir = settings.BACKUPS_DIR
allowed_origins = settings.ALLOWED_ORIGINS
```

## Testing

### Run All Tests

```bash
# From project root
make test

# Or directly
uv run pytest backend/tests -v
```

### Run Specific Tests

```bash
# Single test file
uv run pytest backend/tests/api/v1/test_projects_endpoints.py -v

# Single test
uv run pytest backend/tests/services/test_validation_service.py::test_validate_project -v

# With coverage
uv run pytest backend/tests --cov=backend.app --cov-report=html
```

### Test Patterns

```python
# API endpoint tests - use TestClient
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
response = client.get("/api/v1/health")
assert response.status_code == 200

# Service tests - mock ApplicationState
from unittest.mock import MagicMock

service = ProjectService()
mock_state = MagicMock()
service.state = mock_state  # Inject mock

# Async tests - use pytest-asyncio
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Development Workflow

### Starting Development Servers

```bash
# Terminal 1: Backend (auto-reload)
make backend-run

# Terminal 2: Frontend (auto-reload)
make frontend-run
```

### Code Quality

```bash
# Format code
make tidy

# Full lint check
make lint

# Type checking (if using mypy)
uv run mypy backend/app
```

## Integration with Core

The backend directly imports Shape Shifter core components:

```python
from src.model import ShapeShiftProject, TableConfig
from src.specifications import CompositeProjectSpecification
from src.normalizer import ShapeShifter
from src.loaders import DataLoaders
from src.constraints import Validators
```

**Benefits:**
- ✅ No code duplication
- ✅ Validation logic stays synchronized
- ✅ Single source of truth for business rules
- ✅ Core improvements automatically available in API

## Key Services

### ProjectService
Manages project CRUD operations, file I/O, backups:
- File-based storage with `.yml` extension
- Automatic backup creation on save
- Optimistic locking via version tracking
- Integration with ApplicationState

### ValidationService
Provides multi-type validation:
- **Structural**: Configuration schema validation
- **Entity**: Per-entity validation rules
- **Data**: Runtime data quality checks
- Auto-fix suggestion generation

### ShapeShiftService
Entity data preview with caching:
- Loads entity and dependencies
- Applies transformations (filters, unnest, joins)
- 3-tier cache validation (TTL, version, hash)
- Supports unlimited row preview

### ValidateForeignKeyService
Foreign key relationship testing:
- Performs test joins with sample data
- Validates cardinality constraints
- Detects unmatched rows
- Identifies duplicate matches

### SchemaService
Database schema introspection:
- Multi-driver support (PostgreSQL, SQLite, MS Access)
- Table/column metadata retrieval
- Data type mapping
- Sample data preview

### ReconciliationService
Entity reconciliation workflows:
- Compare entity data with reference sources
- Generate reconciliation suggestions
- Apply bulk updates

## Error Handling

Consistent error responses using custom exceptions:

```python
from backend.app.utils.exceptions import (
    NotFoundError,
    BadRequestError,
    ConflictError,
    ValidationError
)

# Raises appropriate HTTP status codes
raise NotFoundError("Project not found: my-project")  # 404
raise BadRequestError("Invalid entity configuration")  # 400
raise ConflictError("Version conflict detected")       # 409
```

All endpoints wrapped with `@handle_endpoint_errors` for consistent error formatting.

## Logging

Structured logging via loguru:

```python
from loguru import logger

logger.info("Project loaded: {}", project_name)
logger.warning("Cache miss for entity: {}", entity_name)
logger.error("Validation failed: {}", error_details)
```

## Common Issues

### Import Errors

If you see `ModuleNotFoundError`, ensure `PYTHONPATH` includes both root and backend:

```bash
export PYTHONPATH=.:backend
uv run uvicorn backend.app.main:app --reload
```

### Port Already in Use

Backend runs on port 8012. If occupied:

```bash
# Kill process using port
lsof -ti:8012 | xargs kill -9

# Or change port in .env
API_PORT=8013
```

### CORS Issues

Update `ALLOWED_ORIGINS` in `.env` to include your frontend URL:

```bash
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Contributing

1. Follow existing code patterns (see `.github/copilot-instructions.md`)
2. Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)
3. Add tests for new features
4. Run `make lint` before committing
5. Update API documentation if adding endpoints

## Related Documentation

- [Main Project README](../README.md) - Overall project documentation
- [Configuration Guide](../docs/CONFIGURATION_GUIDE.md) - YAML configuration reference
- [Development Guide](../docs/DEVELOPMENT_GUIDE.md) - Development setup and workflows
- [Copilot Instructions](../.github/copilot-instructions.md) - AI coding agent guidelines

## License

Same as main Shape Shifter project.
