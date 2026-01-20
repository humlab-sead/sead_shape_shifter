# Shape Shifter Project Editor - Developer Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [System Architecture](#3-system-architecture)
4. [Backend Development](#4-backend-development)
5. [Frontend Development](#5-frontend-development)
6. [Testing Strategy](#6-testing-strategy)
7. [API Development](#7-api-development)
8. [Best Practices](#8-best-practices)
9. [Troubleshooting](#9-troubleshooting)
10. [Contributing](#10-contributing)

---

## 1. Introduction

### Project Overview

Shape Shifter Project Editor is a full-stack web application for managing data transformation configurations. The system uses:
- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** Vue3 + TypeScript
- **Testing:** pytest + Vitest
- **Deployment:** Docker + Uvicorn

### Target Audience

This guide is for developers who are:
- Contributing to the project
- Extending features
- Fixing bugs
- Understanding architecture
- Writing tests

### Related Documentation

- [UI Architecture](UI_ARCHITECTURE.md) - Detailed architecture
- [User Guide](USER_GUIDE.md) - End-user documentation
- [Project Guide](CONFIGURATION_GUIDE.md) - YAML syntax
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures

---

## 2. Getting Started

### Prerequisites

**Required:**
- Python 3.13 or higher
- Node.js 18 or higher
- Git
- uv (Python package manager)
- npm

**Optional:**
- Docker & Docker Compose
- PostgreSQL (future)
- Redis (future)

### Installation

#### Clone Repository

```bash
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter
```

#### Backend Setup

```bash
cd backend

# Create virtual environment
uv venv

# Install dependencies (including dev tools)
uv pip install -e ".[dev]"

# Verify installation
uv run pytest --version
uv run ruff --version
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Verify installation
npm run --version
```

### Running Development Servers

#### Start Backend

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`  
API docs at: `http://localhost:8000/docs`

#### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend available at: `http://localhost:5173`

### Development Tools

#### Backend Tools

```bash
# Run tests
cd backend
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=app --cov-report=html

# Lint code
uv run ruff check app/ tests/

# Format code
uv run ruff format app/ tests/

# Type checking (if using mypy)
uv run mypy app/
```

#### Frontend Tools

```bash
cd frontend

# Start dev server
npm run dev

# Lint code
npm run lint

# Format code
npm run format

# Build for production (includes vue-tsc type-check)
npm run build

# Preview production build
npm run preview
```

### Project Structure

```
sead_shape_shifter/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Core functionality
│   │   ├── models/             # Pydantic models
│   │   ├── services/           # Business logic
│   │   └── main.py             # Application entry
│   ├── tests/                  # Backend tests
│   └── pyproject.toml          # Dependencies
├── frontend/                   # Vue3 frontend
│   ├── src/
│   │   ├── api/                # Axios client + per-resource modules
│   │   ├── components/         # Reusable Vue components
│   │   ├── composables/        # Reusable composition functions
│   │   ├── stores/             # Pinia state management
│   │   ├── views/              # Route-level views
│   │   ├── router/             # Vue Router configuration
│   │   ├── plugins/            # Vuetify + other plugins
│   │   ├── styles/             # Global styles and variables
│   │   ├── types/              # TypeScript types
│   │   ├── App.vue             # Root component
│   │   └── main.ts             # App bootstrap
│   └── package.json            # Dependencies
├── docs/                       # Documentation
├── projects/                   # Sample projects
├── tests/                      # Shape Shifter core tests
└── src/                        # Shape Shifter core library
```

---

## 3. System Architecture

### Layer Boundary Architecture (Awesome Principles) ⭐

**Shape Shifter follows a strict layer separation pattern that is both awesome and essential for maintainability.**

#### The Three Layers

```
┌─────────────────────────────────────────┐
│  API Layer (backend/app/models/)        │  ← HTTP interface
│  - Pydantic models for request/response │
│  - Data validation & serialization      │
│  - Raw environment variables (${VAR})   │
└─────────────────────────────────────────┘
              ↕ ProjectMapper
┌─────────────────────────────────────────┐
│  Core Layer (src/model.py)              │  ← Domain logic
│  - ShapeShiftProject business logic     │
│  - TaskList state manipulation          │
│  - Resolved configuration data          │
│  - Framework-independent                │
└─────────────────────────────────────────┘
              ↕ ConfigStore
┌─────────────────────────────────────────┐
│  Persistence (YAML files)               │  ← Source of truth
│  - Project configuration                │
│  - Task list state                      │
└─────────────────────────────────────────┘
```

#### Why This Architecture is Awesome

**1. Domain-Driven Design**
- Business logic (like `TaskList`) belongs in the domain (Core), not the API
- Domain state is persisted in YAML, making Core the natural owner
- API layer is just for HTTP concerns - validation, serialization, routing

**2. Separation of Concerns**
- **Core** = Pure business logic, zero framework dependencies
- **API** = HTTP/REST interface, Pydantic validation
- **Mappers** = Translation between layers
- Mixing these creates "smart DTOs" (anti-pattern) and tight coupling

**3. Reusability**
```python
# Core can be used independently of FastAPI
from src.model import ShapeShiftProject

# CLI tools
project = ShapeShiftProject.load("project.yml")
project.task_list.mark_completed("site")
project.save()

# Scripts, ingesters, batch processors - all use same core
```

**4. Framework Independence**
- Swap FastAPI for Flask/Django without touching domain logic
- Core has zero dependency on Pydantic/FastAPI
- Better long-term maintainability and testability

**5. Testing Benefits**
- Test domain logic without HTTP mocking
- Pure business logic tests are faster and clearer
- API tests focus on HTTP concerns only

#### The Mapper Pattern (Critical)

**Never bypass the mapper.** Services must convert between layers explicitly:

```python
# ✅ CORRECT: Service uses mapper for layer conversion
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from src.model import ShapeShiftProject

class TaskService:
    async def mark_complete(self, project_name: str, entity_name: str):
        # 1. Load from API layer
        api_project: Project = self.project_service.load_project(project_name)
        
        # 2. Convert to core layer for business logic
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)
        
        # 3. Execute domain logic
        project.task_list.mark_completed(entity_name)
        
        # 4. Convert back to API layer
        updated_api_project: Project = ProjectMapper.to_api_config(
            project.cfg, project_name
        )
        
        # 5. Save via API layer
        self.project_service.save_project(updated_api_project)
```

```python
# ❌ WRONG: Type confusion, bypassing mapper
class TaskService:
    async def mark_complete(self, project_name: str, entity_name: str):
        # This returns API Project, not ShapeShiftProject!
        project: ShapeShiftProject = self.project_service.load_project(project_name)
        project.task_list.mark_completed(entity_name)  # AttributeError!
```

#### Mapper Responsibilities

**Data Source Mapper** (`backend/app/mappers/data_source_mapper.py`):
- Converts API models ↔ Core configuration
- **Resolves environment variables at API→Core boundary**
- Never resolve in services - always in mapper

**Project Mapper** (`backend/app/mappers/project_mapper.py`):
- Converts `Project` (API) ↔ `ShapeShiftProject` (Core)
- Handles entity dict transformations
- Preserves sparse YAML structure

**Environment Variable Resolution:**
```python
# ✅ CORRECT: Mapper resolves variables
class DataSourceMapper:
    @staticmethod
    def to_core_config(api_config):
        api_config = api_config.resolve_config_env_vars()  # HERE!
        return CoreDataSourceConfig(...)

# ❌ WRONG: Service resolving variables
class SomeService:
    def do_something(self, config):
        config = config.resolve_config_env_vars()  # NO! Mapper's job
```

#### Layer Communication Rules

1. **Services** work with API models, call mapper when needing Core
2. **Mappers** are the ONLY place for layer translation
3. **Core** knows nothing about API models or HTTP
4. **API models** are DTOs - no business logic
5. **Environment variables** resolved in mapper, never in services

#### When to Use Each Layer

**Use Core (ShapeShiftProject) when:**
- Manipulating domain state (task_list, entities)
- Business logic that should work in CLI/scripts
- Need access to framework-independent logic

**Use API (Project) when:**
- Receiving HTTP requests
- Validating user input with Pydantic
- Serializing responses
- Storing in ApplicationState

**Use Mapper when:**
- Converting between API ↔ Core
- Resolving environment variables
- Translating data structures between layers

#### Performance Note

The mapper "cost" (object construction) is negligible:
- One-time per request (not in loops)
- No I/O overhead
- Enforces contracts and prevents bugs
- Architectural benefits far outweigh minimal conversion cost

**This pattern is awesome because it saves you from pain later.** 🎉

## 3. System Architecture (Continued)

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Vue3)                     │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │  Editor  │  Panels  │  Config  │  Validation      │  │
│  │  Monaco  │ Vuetify  │  State   │  UI Components   │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  API Client (axios)                │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                    │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │  Routes  │  Models  │ Services │  Validation      │  │
│  │  /api/v1 │ Pydantic │ Business │  Engine          │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
│  ┌────────────────────────────────────────────────────┐ │
│  │        Core Systems (Config, YAML, Cache)          │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          Shape Shifter Transformation Engine            │
│  ┌──────────────┬──────────────┬─────────────────────┐  │
│  │     model    │specifications│     normalizer      │  │
│  └──────────────┴──────────────┴─────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    File System                          │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │  Configs │  Backups │  Logs    │  Test Data       │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **FastAPI** - Async web framework
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **Uvicorn** - ASGI server
- **uv** - Package manager

**Frontend:**
- **Vue3** - UI library
- **TypeScript** - Type safety
- **Monaco Editor** - Code editor
- **Material-UI** - Component library
- **Pinia** - Client state
- **Vite** - Build tool

### Design Principles

1. **Separation of Concerns** - Clear layer boundaries
2. **Dependency Injection** - Testable components
3. **Type Safety** - TypeScript + Pydantic
4. **API-First** - Well-defined REST API
5. **Cache Strategy** - Performance optimization
6. **Error Handling** - Comprehensive error management

---

## 4. Backend Development

### Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── configurations.py
│   │       │   ├── validation.py
│   │       │   ├── auto_fix.py
│   │       │   └── test_runs.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py          # Settings
│   │   ├── cache.py           # Caching
│   │   └── errors.py          # Exceptions
│   ├── models/
│   │   ├── configuration.py
│   │   ├── validation.py
│   │   ├── auto_fix.py
│   │   └── test_run.py
│   ├── services/
│   │   ├── yaml_service.py
│   │   ├── validation_service.py
│   │   ├── auto_fix_service.py
│   │   └── test_runner.py
│   └── main.py
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    └── conftest.py
```

### Key Design Patterns

#### 1. Service Layer Pattern

Encapsulate business logic in services. **Important:** Services work with API-layer entities (Pydantic models) which may contain unresolved environment variables.

```python
# app/services/validation_service.py
class ValidationService:
    """Orchestrates configuration validation."""
    
    def __init__(
        self,
        yaml_service: YAMLService,
        cache_service: CacheService
    ):
        self.yaml_service = yaml_service
        self.cache_service = cache_service
    
    async def validate_configuration(
        self,
        project_name: str,
        validation_type: ValidationType
    ) -> ValidationResult:
        """Validate configuration with caching."""
        # Check cache
        cache_key = self._make_cache_key(project_name, validation_type)
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached
        
        # Load configuration (API entity with raw ${ENV_VARS})
        config = await self.yaml_service.load_project(project_name)
        
        # Run validation
        issues = await self._run_validation(config, validation_type)
        
        # Cache results
        result = ValidationResult(
            project_name=project_name,
            validation_type=validation_type,
            issues=issues,
            timestamp=datetime.now()
        )
        self.cache_service.set(cache_key, result)
        
        return result
```

**Benefits:**
- Testable (mock dependencies)
- Reusable across endpoints
- Clear separation of concerns
- Easy to maintain

#### 1a. Mapper Pattern for Layer Boundaries

Mappers handle conversion between API and Core layers and **resolve environment variables** at this boundary:

```python
# app/mappers/data_source_mapper.py
class DataSourceMapper:
    """Maps between API and Core data sources.
    
    IMPORTANT: Environment variable resolution happens here,
    at the boundary between API and Core layers.
    """
    
    @staticmethod
    def to_core_config(api_config: ApiDataSourceConfig) -> CoreDataSourceConfig:
        """Convert API config to Core config.
        
        Resolves environment variables during mapping.
        API entities remain raw (${VAR}), core entities are resolved.
        """
        # Resolution at the layer boundary
        api_config = api_config.resolve_config_env_vars()
        
        # Map to core format
        return CoreDataSourceConfig(
            name=api_config.name,
            cfg={
                "driver": api_config.driver,
                "options": {...}  # Fully resolved
            }
        )
```

**Layer Responsibilities:**

| Layer | Entity Type | Env Vars | Where |
|-------|------------|----------|-------|
| API | Pydantic models | Raw `${VAR}` | `backend/app/models/` |
| Mapper | Translation | **Resolves** | `backend/app/mappers/` |
| Core | Domain objects | Resolved | `src/` |

**Benefits:**
- Single point of resolution (DRY)
- Services never need to remember to resolve
- Clear separation: API = raw, Core = resolved
- Type-safe boundaries

#### 2. Repository Pattern

Abstract data access:

```python
# app/services/yaml_service.py
class YAMLService:
    """Handles YAML file operations."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
    
    async def load_project(self, name: str) -> dict:
        """Load configuration from file."""
        path = self.project_dir / f"{name}.yml"
        
        if not path.exists():
            raise ProjectNotFoundError(name)
        
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
    
    def save_project(self, name: str, data: dict) -> None:
        """Save configuration to file."""
        path = self.project_dir / f"{name}.yml"
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
```

**Benefits:**
- Abstracts file system
- Easy to swap implementations
- Centralized error handling
- Testable with mocks

#### 3. Dependency Injection

FastAPI's dependency system:

```python
# app/api/v1/endpoints/validation.py
from fastapi import Depends

def get_yaml_service() -> YAMLService:
    """Get YAML service instance."""
    project_dir = Path("projects")
    return YAMLService(project_dir)

def get_cache_service() -> CacheService:
    """Get cache service instance."""
    return CacheService(ttl=300)

def get_validation_service(
    yaml_service: YAMLService = Depends(get_yaml_service),
    cache_service: CacheService = Depends(get_cache_service)
) -> ValidationService:
    """Get validation service with dependencies."""
    return ValidationService(yaml_service, cache_service)

@router.post("/validate")
async def validate_configuration(
    request: ValidationRequest,
    service: ValidationService = Depends(get_validation_service)
):
    """Validate configuration endpoint."""
    return await service.validate_configuration(
        request.project_name,
        request.validation_type
    )
```

**Benefits:**
- Clean endpoint code
- Easy to test (override dependencies)
- Flexible composition
- Lifecycle management

#### 4. Strategy Pattern

Different validation strategies:

```python
# app/services/validation_service.py
from abc import ABC, abstractmethod

class ValidationStrategy(ABC):
    """Base validation strategy."""
    
    @abstractmethod
    async def validate(self, config: dict) -> list[ValidationIssue]:
        """Run validation and return issues."""
        pass

class StructuralValidator(ValidationStrategy):
    """Validate YAML structure and syntax."""
    
    async def validate(self, config: dict) -> list[ValidationIssue]:
        issues = []
        
        # Check entity definitions
        if "entities" not in config:
            issues.append(ValidationIssue(
                code="MISSING_ENTITIES",
                severity="error",
                message="Project missing 'entities' section"
            ))
        
        # More structural checks...
        return issues

class DataValidator(ValidationStrategy):
    """Validate against actual data sources."""
    
    async def validate(self, config: dict) -> list[ValidationIssue]:
        issues = []
        
        # Check columns exist in data
        for entity_name, entity in config.get("entities", {}).items():
            for column in entity.get("columns", []):
                if not await self._column_exists(entity_name, column):
                    issues.append(ValidationIssue(
                        code="COLUMN_NOT_FOUND",
                        severity="error",
                        entity=entity_name,
                        message=f"Column '{column}' not found"
                    ))
        
        return issues
```

### Caching Architecture

#### Cache Service Implementation

```python
# app/core/cache.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    value: Any
    expires_at: datetime
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now() > self.expires_at

class CacheService:
    """In-memory cache with TTL."""
    
    def __init__(self, ttl: int = 300):
        """Initialize cache with TTL in seconds."""
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        entry = self._cache.get(key)
        
        if entry is None:
            return None
        
        if entry.is_expired():
            self._cache.pop(key)
            return None
        
        return entry.value
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=datetime.now() + timedelta(seconds=self._ttl)
        )
    
    def invalidate(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        keys_to_remove = [
            k for k in self._cache.keys()
            if k.startswith(pattern)
        ]
        for key in keys_to_remove:
            self._cache.pop(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
```

#### Cache Usage

```python
# In service
class ValidationService:
    def _make_cache_key(
        self,
        project_name: str,
        validation_type: ValidationType
    ) -> str:
        """Generate cache key."""
        return f"validation:{project_name}:{validation_type.value}"
    
    async def validate_configuration(
        self,
        project_name: str,
        validation_type: ValidationType
    ) -> ValidationResult:
        """Validate with caching."""
        cache_key = self._make_cache_key(project_name, validation_type)
        
        # Try cache
        cached = self.cache_service.get(cache_key)
        if cached:
            cached.cache_hit = True
            return cached
        
        # Run validation
        result = await self._run_validation(project_name, validation_type)
        
        # Cache result
        self.cache_service.set(cache_key, result)
        result.cache_hit = False
        
        return result
```

#### Cache Invalidation

```python
# On configuration update
@router.put("/projects/{name}")
async def update_configuration(
    name: str,
    config: dict,
    cache: CacheService = Depends(get_cache_service)
):
    """Update configuration and invalidate cache."""
    # Save configuration
    yaml_service.save_project(name, config)
    
    # Invalidate all caches for this config
    cache.invalidate(f"validation:{name}:")
    
    return {"message": "Project updated"}
```

### Error Handling

#### Custom Exceptions

```python
# app/core/errors.py
class BaseAPIException(Exception):
    """Base exception for all API errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ProjectNotFoundError(BaseAPIException):
    """Project file not found."""
    
    def __init__(self, project_name: str):
        super().__init__(
            f"Project '{project_name}' not found",
            status_code=404
        )

class ValidationError(BaseAPIException):
    """Validation failed."""
    
    def __init__(self, errors: list[str]):
        super().__init__(
            f"Validation failed: {'; '.join(errors)}",
            status_code=400
        )

class AutoFixError(BaseAPIException):
    """Auto-fix operation failed."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Auto-fix failed: {reason}",
            status_code=500
        )
```

#### Exception Handlers

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "type": exc.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "InternalServerError",
            "timestamp": datetime.now().isoformat()
        }
    )
```

---

## 5. Frontend Development

### Directory Structure

```
frontend/src/
├── api/                        # API client layer (axios + per-resource modules)
├── components/                 # Vue components (layout, panels, shared UI)
│   ├── common/                 # Reusable pieces (YamlEditor/Monaco wrapper, alerts, skeletons)
│   ├── projects/
│   ├── validation/
│   └── ...
├── composables/                # Reusable composition functions (loading/error guards, etc.)
├── stores/                     # Pinia stores (configuration, validation, UI)
├── views/                      # Route-level screens
├── router/                     # Vue Router configuration
├── plugins/                    # Vuetify and other plugin setup
├── styles/                     # Global styles and variables
├── types/                      # TypeScript types
├── App.vue                     # Root component
└── main.ts                     # App bootstrap
```

### State Management

- **Server state:** Fetch via `frontend/src/api` using axios; keep request/response handling in composables (e.g., `useApiRequest`) to centralize loading/error logic.
- **Pinia for UI state:** Keep configuration data, validation results, and editor UI flags in stores under `frontend/src/stores`; derive refs with `storeToRefs()` inside components.

### Component Patterns

- Use `<script setup lang="ts">` with `defineProps`/`defineEmits` for typing.
- Prefer composables over ad-hoc helpers for shared behavior (debounce, error handling, router guards).
- Build UI with Vuetify components and encapsulate Monaco usage inside dedicated editor components.
- Keep route views thin: orchestrate stores/composables and delegate UI rendering to child components.

#### Composition Pattern

- Use `computed` for derived state and `watch`/`watchEffect` for side effects.
- Leverage VueUse utilities (e.g., `useDebounceFn`) for timers and throttling.
- Co-locate API calls with related Pinia actions or composables rather than directly in templates.



---

## 6. Testing Strategy

### Testing Pyramid

```
        ┌──────────────────┐
        │   E2E Tests      │  ~10% (Manual + Automated)
        └──────────────────┘
      ┌────────────────────────┐
      │   Integration Tests    │  ~20% (API + Service)
      └────────────────────────┘
    ┌──────────────────────────────┐
    │      Unit Tests              │  ~70% (Functions + Classes)
    └──────────────────────────────┘
```

**Distribution:**
- **70% Unit Tests** - Fast, isolated, many
- **20% Integration Tests** - Medium speed, verify interactions
- **10% E2E Tests** - Slow, expensive, critical paths only

### Backend Testing

#### Unit Test Example

```python
# backend/tests/unit/test_validation_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from backend.app.services.validation_service import ValidationService

@pytest.fixture
def mock_yaml_service():
    """Mock YAML service."""
    service = Mock()
    service.load_project = AsyncMock()
    return service

@pytest.fixture
def mock_cache_service():
    """Mock cache service."""
    service = Mock()
    service.get = Mock(return_value=None)
    service.set = Mock()
    return service

@pytest.fixture
def validation_service(mock_yaml_service, mock_cache_service):
    """Create validation service with mocks."""
    return ValidationService(mock_yaml_service, mock_cache_service)

@pytest.mark.asyncio
async def test_validate_configuration_success(
    validation_service,
    mock_yaml_service
):
    """Test successful validation."""
    # Arrange
    mock_yaml_service.load_project.return_value = {
        "entities": {
            "test_entity": {
                "columns": ["id", "name"],
                "keys": ["id"]
            }
        }
    }
    
    # Act
    result = await validation_service.validate_configuration(
        "test_config",
        "all"
    )
    
    # Assert
    assert result.project_name == "test_config"
    assert isinstance(result.issues, list)
    mock_yaml_service.load_project.assert_called_once_with("test_config")

@pytest.mark.asyncio
async def test_validate_uses_cache(validation_service, mock_cache_service):
    """Test that validation uses cache."""
    # Arrange
    cached_result = ValidationResult(
        project_name="test",
        issues=[],
        cache_hit=True
    )
    mock_cache_service.get.return_value = cached_result
    
    # Act
    result = await validation_service.validate_configuration("test", "all")
    
    # Assert
    assert result.cache_hit is True
    mock_cache_service.get.assert_called_once()
```

#### Integration Test Example

```python
# backend/tests/integration/test_api_validation.py
import pytest
from httpx import AsyncClient
from backend.app.main import app

@pytest.mark.asyncio
async def test_validate_endpoint():
    """Test validation endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/validate",
            json={
                "project_name": "test_config",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "project_name" in data
    assert "issues" in data
    assert "summary" in data
    assert isinstance(data["issues"], list)

@pytest.mark.asyncio
async def test_validate_nonexistent_config():
    """Test validating non-existent config returns 404."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/validate",
            json={
                "project_name": "nonexistent",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()
```

### Frontend Testing

Use Vitest with `@vue/test-utils`. Place unit specs under `frontend/tests/unit` and run with `npx vitest`.

#### Component Test Example

```typescript
// frontend/tests/unit/components/ValidationPanel.spec.ts
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import ValidationPanel from '@/components/panels/ValidationPanel.vue';

describe('ValidationPanel', () => {
  it('renders validation issues', () => {
    const issues = [
      {
        id: '1',
        code: 'COLUMN_NOT_FOUND',
        severity: 'error',
        entity: 'test_entity',
        message: 'Column "missing" not found'
      }
    ];

    const wrapper = mount(ValidationPanel, { props: { issues } });

    expect(wrapper.text()).toContain('Column "missing" not found');
    expect(wrapper.text()).toContain('test_entity');
  });

  it('emits apply-fix when button clicked', async () => {
    const issues = [
      {
        id: '1',
        code: 'COLUMN_NOT_FOUND',
        severity: 'error',
        auto_fixable: true,
        message: 'Column "missing" not found'
      }
    ];

    const wrapper = mount(ValidationPanel, { props: { issues } });

    await wrapper.get('[data-testid="apply-fix"]').trigger('click');

    expect(wrapper.emitted('apply-fix')).toHaveLength(1);
  });
});
```

#### Composable Test Example

```typescript
// frontend/tests/unit/composables/useDebouncedSearch.spec.ts
import { describe, it, expect, vi } from 'vitest';
import { ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';

const useDebouncedSearch = (search: (term: string) => Promise<void>) => {
  const term = ref('');
  const loading = ref(false);

  const run = useDebounceFn(async (value: string) => {
    loading.value = true;
    await search(value);
    loading.value = false;
  }, 300);

  const update = (value: string) => {
    term.value = value;
    run(value);
  };

  return { term, loading, update };
};

describe('useDebouncedSearch', () => {
  it('debounces value changes', async () => {
    vi.useFakeTimers();

    const search = vi.fn().mockResolvedValue(undefined);
    const { update, loading } = useDebouncedSearch(search);

    update('config');
    update('configu'); // rapid change

    expect(loading.value).toBe(false);

    vi.advanceTimersByTime(300);

    expect(search).toHaveBeenCalledTimes(1);
    expect(loading.value).toBe(false);

    vi.useRealTimers();
  });
});
```

### Test Coverage

#### Running Coverage

```bash
# Backend coverage
cd backend
uv run pytest tests/ --cov=app --cov-report=html --cov-report=term

# Frontend coverage
cd frontend
npx vitest run --coverage
```

#### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Backend Services | 90%+ | 94% |
| Backend API | 85%+ | 88% |
| Backend Models | 100% | 100% |
| Frontend Components | 85%+ | 88% |
| Frontend Composables | 90%+ | 92% |
| **Overall** | **90%+** | **91%** |

---

## 7. API Development

### RESTful Endpoints

```
# Projects
GET    /api/v1/projects           # List all
GET    /api/v1/projects/{name}    # Get one
POST   /api/v1/projects           # Create
PUT    /api/v1/projects/{name}    # Update
DELETE /api/v1/projects/{name}    # Delete

# Validation
POST   /api/v1/validate                 # Validate
GET    /api/v1/validate/{name}/results  # Get cached

# Auto-Fix
POST   /api/v1/auto-fix/preview         # Preview
POST   /api/v1/auto-fix/apply           # Apply
POST   /api/v1/auto-fix/rollback        # Rollback

# Test Execution
POST   /api/v1/test-runs                # Start
GET    /api/v1/test-runs/{id}           # Status
GET    /api/v1/test-runs/{id}/results   # Results
```

### Adding New Endpoints

#### 1. Define Models

```python
# app/models/my_feature.py
from pydantic import BaseModel
from datetime import datetime

class MyFeatureRequest(BaseModel):
    """Request model."""
    project_name: str
    param1: str
    param2: int = 10

class MyFeatureResponse(BaseModel):
    """Response model."""
    status: str
    data: dict
    timestamp: datetime
```

#### 2. Create Service

```python
# app/services/my_feature_service.py
class MyFeatureService:
    """Business logic for my feature."""
    
    def __init__(self, yaml_service: YAMLService):
        self.yaml_service = yaml_service
    
    async def process(self, request: MyFeatureRequest) -> MyFeatureResponse:
        """Process feature request."""
        # Business logic here
        config = await self.yaml_service.load_project(request.project_name)
        
        # Do something...
        result = {"key": "value"}
        
        return MyFeatureResponse(
            status="success",
            data=result,
            timestamp=datetime.now()
        )
```

#### 3. Create Endpoint

```python
# app/api/v1/endpoints/my_feature.py
from fastapi import APIRouter, Depends
from backend.app.models.my_feature import MyFeatureRequest, MyFeatureResponse
from backend.app.services.my_feature_service import MyFeatureService

router = APIRouter()

def get_my_feature_service() -> MyFeatureService:
    """Get service instance."""
    yaml_service = get_yaml_service()
    return MyFeatureService(yaml_service)

@router.post("/my-feature", response_model=MyFeatureResponse)
async def my_feature_endpoint(
    request: MyFeatureRequest,
    service: MyFeatureService = Depends(get_my_feature_service)
):
    """Process my feature request."""
    return await service.process(request)
```

#### 4. Register Router

```python
# app/api/v1/router.py
from fastapi import APIRouter
from backend.app.api.v1.endpoints import my_feature

api_router = APIRouter()
api_router.include_router(my_feature.router, tags=["my-feature"])
```

#### 5. Write Tests

```python
# tests/unit/test_my_feature_service.py
import pytest
from backend.app.services.my_feature_service import MyFeatureService

@pytest.mark.asyncio
async def test_my_feature_process():
    """Test feature processing."""
    service = MyFeatureService(mock_yaml_service)
    
    request = MyFeatureRequest(
        project_name="test",
        param1="value",
        param2=20
    )
    
    result = await service.process(request)
    
    assert result.status == "success"
    assert result.data is not None
```

---

## 8. Best Practices

### Code Style

#### Python (Backend)

```python
# Good - Clear function names
async def validate_configuration_structure(config: dict) -> list[Issue]:
    """Validate configuration structure and return issues."""
    pass

# Bad - Generic name
async def check(config: dict):
    pass

# Good - Type hints
def get_entities(config: dict) -> dict[str, EntityConfig]:
    return config.get("entities", {})

# Bad - No type hints
def get_entities(config):
    return config.get("entities", {})

# Good - Docstrings
def create_backup(project_name: str) -> Path:
    """
    Create timestamped backup of configuration.
    
    Args:
        project_name: Name of configuration to backup
        
    Returns:
        Path to backup file
        
    Raises:
        ProjectNotFoundError: If config doesn't exist
    """
    pass
```

#### TypeScript (Frontend)

```vue
<!-- Good - Explicit types and typed props -->
<script setup lang="ts">
import ValidationIssueList from '@/components/panels/ValidationIssueList.vue';

interface ValidationIssue {
  id: string;
  code: string;
  severity: 'error' | 'warning' | 'info';
  entity?: string;
  message: string;
}

const props = defineProps<{ issues: ValidationIssue[] }>();
</script>

<template>
  <ValidationIssueList :issues="props.issues" />
</template>

<!-- Bad - Any types and untyped props -->
<script setup>
defineProps(['issues']);
</script>

<template>
  <ValidationIssueList :issues="issues" />
</template>
```

### Error Handling

```python
# Good - Specific exceptions
try:
    config = await yaml_service.load_project(name)
except FileNotFoundError:
    raise ProjectNotFoundError(name)
except yaml.YAMLError as e:
    raise ValidationError(f"Invalid YAML: {e}")

# Bad - Catch all
try:
    config = await yaml_service.load_project(name)
except Exception as e:
    raise Exception(f"Error: {e}")
```

### Testing Best Practices

```python
# Good - Descriptive test names
def test_apply_fix_removes_missing_column_from_entity():
    """Test that auto-fix correctly removes non-existent columns."""
    pass

# Bad - Generic names
def test_fix():
    pass

# Good - Arrange-Act-Assert
def test_validation_caching():
    # Arrange
    service = ValidationService(mock_yaml, mock_cache)
    mock_cache.get.return_value = None
    
    # Act
    result = await service.validate("test", "all")
    
    # Assert
    assert result.cache_hit is False
    mock_cache.set.assert_called_once()

# Good - One assertion focus per test
def test_validation_returns_issues():
    result = await service.validate("test", "all")
    assert isinstance(result.issues, list)

def test_validation_includes_project_name():
    result = await service.validate("test", "all")
    assert result.project_name == "test"

# Bad - Multiple unrelated assertions
def test_validation():
    result = await service.validate("test", "all")
    assert result.project_name == "test"
    assert len(result.issues) > 0
    assert result.cache_hit is False
    assert result.timestamp is not None
```

### Performance

```typescript
// Good - Derived data via computed
const sortedIssues = computed(() => [...issues.value].sort((a, b) => a.severity.localeCompare(b.severity)));

// Bad - Recompute imperatively on every render
const sortedIssues = ref([]);
watchEffect(() => {
  sortedIssues.value = [...issues.value].sort((a, b) => a.severity.localeCompare(b.severity));
});

// Good - Debounce user input
const debouncedSearch = useDebounceFn(() => performSearch(searchTerm.value), 500);
watch(searchTerm, () => debouncedSearch());

// Bad - Trigger on every keystroke
watch(searchTerm, (value) => {
  performSearch(value);
});
```

---

## 9. Troubleshooting

### Common Development Issues

#### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check virtual environment
which python  # Should be in venv

# Reinstall dependencies
cd backend
uv pip install -e ".[dev]" --force-reinstall

# Check port availability
lsof -i :8000
```

#### Frontend Won't Start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check port availability
lsof -i :5173
```

#### Tests Failing

```bash
# Backend - Run single test with verbose output
cd backend
uv run pytest tests/test_file.py::test_function -v -s

# Frontend - Run single test
cd frontend
npx vitest ValidationPanel.spec.ts

# Check for async issues
# Ensure @pytest.mark.asyncio decorator present
```

#### Import Errors

```bash
# Backend - Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify package installed
uv pip list | grep shape-shifter

# Reinstall in editable mode
cd backend
uv pip install -e .
```

### Debugging

#### Backend Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

#### Frontend Debugging

```typescript
// Browser DevTools
console.log('Debug:', variable);
debugger;  // Breakpoint

```

---

## 10. Contributing

### Workflow

1. **Create Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes**
   - Write code
   - Write tests
   - Update documentation

3. **Run Tests**
   ```bash
   # Backend
   cd backend
   uv run pytest tests/ -v
   
   # Frontend
   cd frontend
   npm run test
   ```

4. **Lint Code**
   ```bash
   # Backend
   cd backend
   uv run ruff check app/ tests/
   
   # Frontend
   cd frontend
   npm run lint
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(feature-area): add my feature"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

### Commit Convention

This project uses **[Conventional Commits](https://www.conventionalcommits.org/)** with **semantic-release** for automated versioning and changelog generation.

#### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Commit Types and Release Impact

- **feat**: New feature (→ **MINOR** release, e.g., 1.1.0)
- **fix**: Bug fix (→ **PATCH** release, e.g., 1.0.1)
- **docs**: Documentation changes (→ **PATCH** if scope is README)
- **refactor**: Code refactoring (→ **PATCH** release)
- **perf**: Performance improvements (→ **PATCH** release)
- **style**: Code style changes (→ **PATCH** release)
- **test**: Adding or updating tests (no release)
- **build**: Build system changes (no release)
- **ci**: CI/CD configuration (no release)
- **chore**: Other maintenance tasks (no release)
- **revert**: Revert a previous commit (no release)

#### Common Scopes

- `core`: Core processing pipeline
- `backend`: Backend API
- `frontend`: Frontend application
- `config`: Project handling
- `validation`: Validation services
- `cache`: Caching functionality
- `loaders`: Data loaders
- `api`: API endpoints
- `deps`: Dependencies

#### Examples

```bash
# Features (MINOR release)
git commit -m "feat(cache): implement 3-tier cache validation"
git commit -m "feat(frontend): add entity preview with auto-refresh"

# Bug fixes (PATCH release)
git commit -m "fix(validation): prevent mutation in resolve_references"
git commit -m "fix(frontend): resolve dark mode text color issue"

# Documentation (PATCH if scope is README)
git commit -m "docs(README): add installation instructions"
git commit -m "docs(api): update endpoint examples"

# Refactoring (PATCH release)
git commit -m "refactor(services): extract validation logic"

# Tests (no release)
git commit -m "test(loaders): add UCanAccessSqlLoader tests"

# Chores (no release)
git commit -m "chore(deps): bump pydantic to 2.5.0"
git commit -m "chore: update pre-commit hooks"
```

#### Breaking Changes (MAJOR release)

Use `!` or `BREAKING CHANGE:` footer to trigger a **MAJOR** release (e.g., 2.0.0):

```bash
# With ! notation
git commit -m "feat(api)!: change validation response format"

# With footer
git commit -m "feat(api): change validation response format

BREAKING CHANGE: validation errors now return array instead of object.
Update API clients to handle the new format."
```

#### Multi-line Commits

Use the body for detailed explanations:

```bash
git commit -m "feat(cache): implement hash-based invalidation

Add xxhash-based entity hashing to detect changes
beyond version numbers. Implements 3-tier validation:
1. TTL check (300s)
2. Config version comparison  
3. Entity hash validation

This prevents serving stale cached data when entity
changes without version bump.

Closes #123"
```

#### Best Practices

- **Keep subject line under 72 characters**
- **Use imperative mood**: "add" not "added" or "adds"
- **Don't capitalize** the first letter
- **Don't end** with a period
- **Reference issues**: Use `Closes #123`, `Fixes #456` in footer
- **Explain why**: Use body to explain **what** and **why**, not **how**
- **Skip CI when needed**: Add `[skip ci]` to skip CI builds
- **Add co-authors**: `Co-authored-by: Name <email@example.com>`

#### Common Mistakes

❌ **Avoid**:
```bash
git commit -m "Fixed bug"           # No type
git commit -m "feat: Added feature." # Capitalized + period
git commit -m "WIP"                 # Not descriptive
```

✅ **Prefer**:
```bash
git commit -m "fix(validation): prevent null pointer in entity resolution"
git commit -m "feat(api): add batch validation endpoint"
git commit -m "refactor(core): simplify dependency resolution"
```

#### Automated Releases

Semantic-release automatically:
- Analyzes commits on `main` branch
- Determines next version number
- Generates `CHANGELOG.md`
- Updates version in `pyproject.toml`
- Creates git tags

See `.releaserc.json` for full configuration.

For complete details, see the **Conventional Commit Messages** section in [TODO.md](../TODO.md).

---

## Related Documentation

- [UI Architecture](UI_ARCHITECTURE.md) - Detailed architecture
- [User Guide](USER_GUIDE.md) - End-user documentation
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures
- [Project Guide](CONFIGURATION_GUIDE.md) - YAML syntax
- [API Reference](API_REFERENCE.md) - API documentation

---

**Document Version**: 1.1  
**Last Updated**: December 30, 2025  
**For**: Shape Shifter Project Editor v0.1.0
