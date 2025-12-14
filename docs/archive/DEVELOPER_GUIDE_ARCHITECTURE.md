# Developer Guide: Architecture

## Overview

Shape Shifter Configuration Editor is a full-stack application with a FastAPI backend and React/TypeScript frontend. This guide covers the architectural decisions, patterns, and design principles used throughout the system.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │  Editor  │  Panels  │  Config  │  Validation      │ │
│  │  Monaco  │  MUI     │  State   │  UI Components   │ │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │           API Client (axios, React Query)          │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                     │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │  Routes  │  Models  │ Services │  Validation      │ │
│  │  /api/v1 │ Pydantic │ Business │  Engine          │ │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │        Core Systems (Config, YAML, Cache)          │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    File System                           │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │  Configs │  Backups │  Logs    │  Test Data       │ │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **FastAPI** - Modern async Python web framework
- **Pydantic** - Data validation and settings management
- **pytest** - Testing framework with async support
- **uvicorn** - ASGI server for production

**Frontend:**
- **React 18** - UI library with hooks and concurrent features
- **TypeScript** - Type-safe JavaScript
- **Monaco Editor** - VS Code's editor for YAML editing
- **Material-UI** - Component library
- **React Query** - Server state management
- **Vite** - Build tool and dev server

**Development:**
- **uv** - Fast Python package manager
- **npm** - Node package manager
- **pytest-asyncio** - Async test support
- **Ruff** - Python linter and formatter

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── configurations.py    # Config CRUD
│   │       │   ├── validation.py        # Validation endpoints
│   │       │   ├── auto_fix.py          # Auto-fix endpoints
│   │       │   └── test_runs.py         # Test execution
│   │       └── router.py                # Route registration
│   ├── core/
│   │   ├── config.py                    # Settings management
│   │   ├── cache.py                     # Caching service
│   │   └── errors.py                    # Exception handlers
│   ├── models/
│   │   ├── configuration.py             # Config models
│   │   ├── validation.py                # Validation models
│   │   ├── auto_fix.py                  # Auto-fix models
│   │   └── test_run.py                  # Test execution models
│   ├── services/
│   │   ├── yaml_service.py              # YAML file operations
│   │   ├── validation_service.py        # Validation orchestration
│   │   ├── auto_fix_service.py          # Auto-fix logic
│   │   └── test_runner.py               # Test execution
│   └── main.py                          # Application entry point
└── tests/
    ├── test_configurations.py
    ├── test_validation.py
    ├── test_auto_fix_service.py
    └── test_integration.py
```

### Key Design Patterns

#### 1. Service Layer Pattern

Services encapsulate business logic and dependencies:

```python
# app/services/validation_service.py
class ValidationService:
    def __init__(
        self,
        yaml_service: YAMLService,
        cache_service: CacheService
    ):
        self.yaml_service = yaml_service
        self.cache_service = cache_service
    
    async def validate_configuration(
        self,
        config_name: str,
        validation_type: ValidationType
    ) -> ValidationResult:
        # Business logic here
        pass
```

**Benefits:**
- Testable (dependency injection)
- Reusable across endpoints
- Clear separation of concerns
- Easy to mock for tests

#### 2. Repository Pattern

YAML service acts as data access layer:

```python
# app/services/yaml_service.py
class YAMLService:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    async def load_configuration(self, name: str) -> dict:
        # File I/O abstraction
        pass
    
    def save_configuration(self, name: str, data: dict) -> None:
        # File I/O abstraction
        pass
```

**Benefits:**
- Abstracts file system operations
- Easy to swap implementations (file, DB, S3)
- Centralized error handling
- Testable with mocks

#### 3. Dependency Injection

FastAPI's dependency system for services:

```python
# app/api/v1/endpoints/validation.py
def get_validation_service() -> ValidationService:
    yaml_service = get_yaml_service()
    cache_service = get_cache_service()
    return ValidationService(yaml_service, cache_service)

@router.post("/validate")
async def validate_configuration(
    request: ValidationRequest,
    service: ValidationService = Depends(get_validation_service)
):
    return await service.validate_configuration(
        request.config_name,
        request.validation_type
    )
```

**Benefits:**
- Clean endpoint code
- Easy to test (override dependencies)
- Flexible service composition
- Lifecycle management

#### 4. Model-View-Controller (MVC)

Clear separation of concerns:

```python
# Model - Data structure and validation
class ConfigurationModel(BaseModel):
    name: str
    entities: dict[str, EntityConfig]
    
    @validator("name")
    def validate_name(cls, v):
        return v

# Service (Controller) - Business logic
class ConfigurationService:
    def create_configuration(self, model: ConfigurationModel):
        # Business logic
        pass

# Endpoint (View) - HTTP interface
@router.post("/configurations")
async def create_configuration(config: ConfigurationModel):
    return service.create_configuration(config)
```

#### 5. Strategy Pattern

Different validators for different types:

```python
# app/services/validation_service.py
class ValidationStrategy(ABC):
    @abstractmethod
    async def validate(self, config: dict) -> list[ValidationIssue]:
        pass

class StructuralValidator(ValidationStrategy):
    async def validate(self, config: dict) -> list[ValidationIssue]:
        # Structural validation logic
        pass

class DataValidator(ValidationStrategy):
    async def validate(self, config: dict) -> list[ValidationIssue]:
        # Data validation logic
        pass
```

### Caching Architecture

#### Cache Service Design

```python
# app/core/cache.py
class CacheService:
    def __init__(self, ttl: int = 300):  # 5 minutes
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.value
        self._cache.pop(key, None)
        return None
    
    def set(self, key: str, value: Any) -> None:
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=datetime.now() + timedelta(seconds=self._ttl)
        )
    
    def invalidate(self, pattern: str) -> None:
        keys_to_remove = [
            k for k in self._cache.keys()
            if k.startswith(pattern)
        ]
        for key in keys_to_remove:
            self._cache.pop(key)
```

#### Cache Key Strategy

```python
def _make_cache_key(
    config_name: str,
    validation_type: ValidationType
) -> str:
    """Generate unique cache key."""
    return f"validation:{config_name}:{validation_type.value}"
```

**Key format:** `validation:<config_name>:<type>`

**Examples:**
- `validation:arbodat:all`
- `validation:arbodat:structural`
- `validation:sample_entity:entity`

#### Cache Invalidation

Automatic invalidation on:

```python
# When configuration changes
@router.put("/configurations/{name}")
async def update_configuration(
    name: str,
    cache: CacheService = Depends(get_cache_service)
):
    # Update config...
    cache.invalidate(f"validation:{name}:")  # Clear all validation caches
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

class ConfigurationNotFoundError(BaseAPIException):
    """Raised when configuration file doesn't exist."""
    def __init__(self, config_name: str):
        super().__init__(
            f"Configuration '{config_name}' not found",
            status_code=404
        )

class ValidationError(BaseAPIException):
    """Raised when validation fails."""
    def __init__(self, errors: list[str]):
        super().__init__(
            f"Validation failed: {'; '.join(errors)}",
            status_code=400
        )
```

#### Exception Handlers

```python
# app/main.py
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "type": exc.__class__.__name__,
            "timestamp": datetime.now().isoformat()
        }
    )
```

### Testing Architecture

#### Test Structure

```python
# tests/test_auto_fix_service.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_yaml_service():
    """Mock YAML service for tests."""
    service = Mock()
    service.load_configuration = AsyncMock()
    service.save_configuration = Mock()
    return service

@pytest.fixture
def auto_fix_service(mock_yaml_service, mock_config_service):
    """Create auto-fix service with mocked dependencies."""
    return AutoFixService(mock_yaml_service, mock_config_service)

@pytest.mark.asyncio
async def test_apply_fix_removes_column(auto_fix_service, mock_yaml_service):
    """Test that apply_fix correctly removes a column."""
    # Arrange
    mock_yaml_service.load_configuration.return_value = {
        "entities": {
            "test_entity": {
                "columns": ["col1", "col2", "missing_column"]
            }
        }
    }
    
    suggestion = FixSuggestion(
        issue_code="COLUMN_NOT_FOUND",
        entity="test_entity",
        suggestion="Remove missing_column",
        actions=[
            FixAction(
                type=FixActionType.REMOVE_COLUMN,
                entity="test_entity",
                field="columns",
                old_value="missing_column"
            )
        ],
        auto_fixable=True,
        warnings=[]
    )
    
    # Act
    result = await auto_fix_service.apply_fixes("test_config", [suggestion])
    
    # Assert
    assert result.applied_count == 1
    assert result.failed_count == 0
```

#### Test Organization

- **Unit Tests:** Test individual functions/methods
- **Integration Tests:** Test service interactions
- **End-to-End Tests:** Test full API workflows

## Frontend Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts                # Axios configuration
│   │   ├── configurations.ts        # Config API calls
│   │   ├── validation.ts            # Validation API calls
│   │   └── autoFix.ts               # Auto-fix API calls
│   ├── components/
│   │   ├── editor/
│   │   │   ├── ConfigurationEditor.tsx
│   │   │   └── MonacoEditor.tsx
│   │   ├── panels/
│   │   │   ├── ValidationPanel.tsx
│   │   │   ├── EntityTreePanel.tsx
│   │   │   └── PropertiesPanel.tsx
│   │   └── common/
│   │       ├── LoadingSkeleton.tsx
│   │       ├── SuccessSnackbar.tsx
│   │       └── Tooltip.tsx
│   ├── hooks/
│   │   ├── useConfiguration.ts      # Config state
│   │   ├── useValidation.ts         # Validation logic
│   │   ├── useDebounce.ts           # Debouncing
│   │   └── useCache.ts              # Client-side cache
│   ├── stores/
│   │   └── configStore.ts           # Zustand store
│   ├── types/
│   │   ├── configuration.ts
│   │   ├── validation.ts
│   │   └── autoFix.ts
│   └── App.tsx
└── package.json
```

### State Management

#### React Query for Server State

```typescript
// src/hooks/useValidation.ts
import { useQuery } from '@tanstack/react-query';
import { validateConfiguration } from '../api/validation';

export function useValidation(configName: string, validationType: string) {
  return useQuery({
    queryKey: ['validation', configName, validationType],
    queryFn: () => validateConfiguration(configName, validationType),
    staleTime: 5 * 60 * 1000, // 5 minutes (matches backend cache)
    cacheTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
}
```

**Benefits:**
- Automatic caching
- Background refetching
- Optimistic updates
- Loading/error states

#### Zustand for UI State

```typescript
// src/stores/configStore.ts
import create from 'zustand';

interface ConfigStore {
  currentConfig: string | null;
  selectedEntity: string | null;
  setCurrentConfig: (name: string) => void;
  setSelectedEntity: (entity: string | null) => void;
}

export const useConfigStore = create<ConfigStore>((set) => ({
  currentConfig: null,
  selectedEntity: null,
  setCurrentConfig: (name) => set({ currentConfig: name }),
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),
}));
```

**Benefits:**
- Simple API
- No boilerplate
- TypeScript support
- DevTools integration

### Component Patterns

#### Custom Hooks

```typescript
// src/hooks/useDebounce.ts
import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
```

#### Composition Pattern

```typescript
// src/components/editor/ConfigurationEditor.tsx
export function ConfigurationEditor() {
  return (
    <Box display="flex" height="100vh">
      <EntityTreePanel />
      <Box flex={1}>
        <MonacoEditor />
      </Box>
      <Box width={400}>
        <ValidationPanel />
        <PropertiesPanel />
      </Box>
    </Box>
  );
}
```

### Performance Optimizations

#### 1. Code Splitting

```typescript
// src/App.tsx
import { lazy, Suspense } from 'react';

const ConfigurationEditor = lazy(() => import('./components/editor/ConfigurationEditor'));

function App() {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <ConfigurationEditor />
    </Suspense>
  );
}
```

#### 2. Memoization

```typescript
// src/components/panels/ValidationPanel.tsx
import { useMemo } from 'react';

function ValidationPanel({ issues }) {
  const sortedIssues = useMemo(() => {
    return [...issues].sort((a, b) => 
      a.severity.localeCompare(b.severity)
    );
  }, [issues]);

  return <IssueList issues={sortedIssues} />;
}
```

#### 3. Virtual Lists

```typescript
// src/components/panels/EntityTreePanel.tsx
import { FixedSizeList } from 'react-window';

function EntityTreePanel({ entities }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={entities.length}
      itemSize={35}
    >
      {({ index, style }) => (
        <div style={style}>
          <EntityNode entity={entities[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

## API Design

### RESTful Principles

```
GET    /api/v1/configurations           # List all configs
GET    /api/v1/configurations/{name}    # Get specific config
POST   /api/v1/configurations           # Create config
PUT    /api/v1/configurations/{name}    # Update config
DELETE /api/v1/configurations/{name}    # Delete config

POST   /api/v1/validate                 # Validate config
GET    /api/v1/validate/{name}/results  # Get cached results

POST   /api/v1/auto-fix/preview         # Preview fixes
POST   /api/v1/auto-fix/apply           # Apply fixes
POST   /api/v1/auto-fix/rollback        # Rollback changes
```

### Request/Response Models

```python
# Request
class ValidationRequest(BaseModel):
    config_name: str
    validation_type: ValidationType = ValidationType.ALL
    entity_name: Optional[str] = None

# Response
class ValidationResponse(BaseModel):
    config_name: str
    validation_type: ValidationType
    timestamp: datetime
    issues: list[ValidationIssue]
    summary: ValidationSummary
    cache_hit: bool = False
```

### Error Responses

```json
{
  "error": "Configuration 'invalid' not found",
  "type": "ConfigurationNotFoundError",
  "timestamp": "2025-12-14T10:30:00Z",
  "path": "/api/v1/configurations/invalid",
  "method": "GET"
}
```

## Security Considerations

### Input Validation

- All inputs validated with Pydantic models
- YAML parsing with safe loaders only
- File path validation to prevent traversal
- Content type validation

### CORS Configuration

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting (Future)

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/validate")
@limiter.limit("10/minute")
async def validate_configuration():
    pass
```

## Deployment Architecture

### Development

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

### Production (Future)

```bash
# Docker Compose
docker-compose up -d

# Backend: Gunicorn + Uvicorn workers
# Frontend: Nginx serving static files
# Database: PostgreSQL for persistence
```

## Related Documentation

- [Testing Strategy](DEVELOPER_GUIDE_TESTING.md)
- [API Reference](API_REFERENCE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Performance Tuning](PERFORMANCE.md)

---

**Version:** 1.0  
**Last Updated:** December 14, 2025  
**For:** Shape Shifter Configuration Editor v0.1.0
