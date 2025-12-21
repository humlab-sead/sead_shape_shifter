# Shape Shifter Configuration Editor - Backend

REST API for editing Shape Shifter YAML configuration files.

## Unified Installation (Recommended)

The backend is now part of the unified Shape Shifter package. Install from the project root:

```bash
# From project root (recommended)
cd /path/to/sead_shape_shifter

# Install with all dependencies (core + API + dev tools)
uv venv
uv pip install -e ".[all]"

# Run the backend
make backend-run
```

### Alternative Installation Options

```bash
# Install core + API only (no dev tools)
uv pip install -e ".[api]"

# Install core only (no backend dependencies)
uv pip install -e .
```

## Technology Stack

- **FastAPI**: Modern async Python web framework
- **Pydantic v2**: Data validation and serialization
- **ruamel.yaml**: YAML parsing with format preservation
- **NetworkX**: Graph algorithms for dependency analysis
- **uvicorn**: ASGI server

## Quick Start

### Running the Server

```bash
# From project root with make (recommended)
make backend-run

# Or manually with PYTHONPATH
PYTHONPATH=.:backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8012
```

### Access API Documentation

- **Swagger UI**: http://localhost:8012/api/v1/docs
- **ReDoc**: http://localhost:8012/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8012/api/v1/openapi.json

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── api.py          # Router configuration
│   │       └── endpoints/
│   │           ├── health.py   # Health check
│   │           ├── configuration.py  # (Coming in Sprint 3.1)
│   │           ├── entities.py       # (Coming in Sprint 3.2)
│   │           ├── validation.py     # (Coming in Sprint 3.3)
│   │           └── dependencies.py   # (Coming in Sprint 3.3)
│   ├── core/
│   │   ├── config.py           # Application settings
│   │   └── exceptions.py       # (Coming in Sprint 2.1)
│   ├── models/
│   │   ├── entity.py           # (Coming in Sprint 1.3)
│   │   ├── config.py           # (Coming in Sprint 1.3)
│   │   └── validation.py       # (Coming in Sprint 1.3)
│   ├── services/
│   │   ├── yaml_service.py     # (Coming in Sprint 2.1)
│   │   ├── config_service.py   # (Coming in Sprint 2.2)
│   │   ├── validation_service.py  # (Coming in Sprint 2.3)
│   │   └── dependency_service.py  # (Coming in Sprint 3.3)
│   └── integrations/
│       └── specifications.py   # (Coming in Sprint 2.3)
├── tests/
│   └── api/
│       └── v1/
│           └── test_health.py
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Health Check
- `GET /api/v1/health` - Application health and status

### Configurations (Sprint 3.1)
- `GET /api/v1/configurations` - List available configs
- `GET /api/v1/configurations/{name}` - Get configuration
- `POST /api/v1/configurations` - Create new configuration
- `PUT /api/v1/configurations/{name}` - Update configuration
- `DELETE /api/v1/configurations/{name}` - Delete configuration
- `POST /api/v1/configurations/{name}/load` - Load from file
- `POST /api/v1/configurations/{name}/save` - Save to file

### Entities (Sprint 3.2)
- `GET /api/v1/configurations/{name}/entities` - List entities
- `GET /api/v1/configurations/{name}/entities/{id}` - Get entity
- `POST /api/v1/configurations/{name}/entities` - Create entity
- `PUT /api/v1/configurations/{name}/entities/{id}` - Update entity
- `DELETE /api/v1/configurations/{name}/entities/{id}` - Delete entity

### Validation (Sprint 3.3)
- `POST /api/v1/configurations/{name}/validate` - Validate configuration

### Dependencies (Sprint 3.3)
- `GET /api/v1/configurations/{name}/dependencies` - Get dependency graph
- `POST /api/v1/configurations/{name}/dependencies/check` - Check circular dependencies

## Configuration

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

Key settings:
- `ENVIRONMENT`: `development` | `production` | `test`
- `ALLOWED_ORIGINS`: Frontend URLs for CORS
- `CONFIGURATIONS_DIR`: Where YAML files are stored (default: `../input`)
- `BACKUPS_DIR`: Where backups are stored (default: `../backups`)

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=html

# Run specific test
uv run pytest tests/api/v1/test_health.py -v
```

## Integration with Shape Shifter Core

The backend directly imports and uses existing Shape Shifter components:

```python
from src.model import ShapeShiftConfig, EntityConfig
from src.specifications import CompositeConfigSpecification
from src.normalizer import ArbodatSurveyNormalizer
```

This ensures:
- ✅ No code duplication
- ✅ Validation stays in sync
- ✅ Single source of truth for business logic

## Development Workflow

1. **Start backend server** (terminal 1):
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. **Start frontend dev server** (terminal 2):
   ```bash
   cd frontend
   pnpm dev
   ```

3. **Make changes** - both servers auto-reload

4. **Test API** via Swagger UI or frontend

## Next Steps (Sprint 1.3)

- [ ] Create Pydantic models matching `src/model.py`
- [ ] Create TypeScript types for frontend
- [ ] Ensure type compatibility between backend and frontend

## Sprint Status

- ✅ **Sprint 1.1**: Project Scaffolding (COMPLETE)
  - FastAPI application with CORS
  - Health check endpoint
  - Project structure
  - Requirements and configuration
- ⏳ **Sprint 1.2**: Frontend Setup (NEXT)
- ⏳ **Sprint 1.3**: Pydantic Models & Types
