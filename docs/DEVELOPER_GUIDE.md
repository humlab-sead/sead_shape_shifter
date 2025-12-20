# Shape Shifter Configuration Editor - Developer Guide

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

Shape Shifter Configuration Editor is a full-stack web application for managing data transformation configurations. The system uses:
- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React 18 + TypeScript
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
- [Configuration Guide](CONFIGURATION_GUIDE.md) - YAML syntax
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

# Run tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run type-check

# Build for production
npm run build
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
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── api/                # API client
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   ├── stores/             # State management
│   │   ├── types/              # TypeScript types
│   │   └── App.tsx             # Main component
│   ├── tests/                  # Frontend tests
│   └── package.json            # Dependencies
├── docs/                       # Documentation
├── input/                      # Sample configurations
├── tests/                      # Shape Shifter core tests
└── src/                        # Shape Shifter core library
```

---

## 3. System Architecture

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
                           │ HTTP/REST
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
│          Shape Shifter Transformation Engine            │
│  ┌──────────────┬──────────────┬─────────────────────┐ │
│  │ config_model │specifications│     normalizer      │ │
│  └──────────────┴──────────────┴─────────────────────┘ │
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
- **FastAPI** - Async web framework
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **Uvicorn** - ASGI server
- **uv** - Package manager

**Frontend:**
- **React 18** - UI library
- **TypeScript** - Type safety
- **Monaco Editor** - Code editor
- **Material-UI** - Component library
- **React Query** - Server state
- **Zustand** - Client state
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
        config_name: str,
        validation_type: ValidationType
    ) -> ValidationResult:
        """Validate configuration with caching."""
        # Check cache
        cache_key = self._make_cache_key(config_name, validation_type)
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached
        
        # Load configuration (API entity with raw ${ENV_VARS})
        config = await self.yaml_service.load_configuration(config_name)
        
        # Run validation
        issues = await self._run_validation(config, validation_type)
        
        # Cache results
        result = ValidationResult(
            config_name=config_name,
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
    """Maps between API and Core data source configurations.
    
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
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    async def load_configuration(self, name: str) -> dict:
        """Load configuration from file."""
        path = self.config_dir / f"{name}.yml"
        
        if not path.exists():
            raise ConfigurationNotFoundError(name)
        
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
    
    def save_configuration(self, name: str, data: dict) -> None:
        """Save configuration to file."""
        path = self.config_dir / f"{name}.yml"
        
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
    config_dir = Path("input")
    return YAMLService(config_dir)

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
        request.config_name,
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
                message="Configuration missing 'entities' section"
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
        config_name: str,
        validation_type: ValidationType
    ) -> str:
        """Generate cache key."""
        return f"validation:{config_name}:{validation_type.value}"
    
    async def validate_configuration(
        self,
        config_name: str,
        validation_type: ValidationType
    ) -> ValidationResult:
        """Validate with caching."""
        cache_key = self._make_cache_key(config_name, validation_type)
        
        # Try cache
        cached = self.cache_service.get(cache_key)
        if cached:
            cached.cache_hit = True
            return cached
        
        # Run validation
        result = await self._run_validation(config_name, validation_type)
        
        # Cache result
        self.cache_service.set(cache_key, result)
        result.cache_hit = False
        
        return result
```

#### Cache Invalidation

```python
# On configuration update
@router.put("/configurations/{name}")
async def update_configuration(
    name: str,
    config: dict,
    cache: CacheService = Depends(get_cache_service)
):
    """Update configuration and invalidate cache."""
    # Save configuration
    yaml_service.save_configuration(name, config)
    
    # Invalidate all caches for this config
    cache.invalidate(f"validation:{name}:")
    
    return {"message": "Configuration updated"}
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
    """Configuration file not found."""
    
    def __init__(self, config_name: str):
        super().__init__(
            f"Configuration '{config_name}' not found",
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
├── api/                        # API client layer
│   ├── client.ts               # Axios config
│   ├── configurations.ts
│   ├── validation.ts
│   └── autoFix.ts
├── components/                 # React components
│   ├── editor/
│   │   ├── ConfigurationEditor.tsx
│   │   └── MonacoEditor.tsx
│   ├── panels/
│   │   ├── ValidationPanel.tsx
│   │   ├── EntityTreePanel.tsx
│   │   └── PropertiesPanel.tsx
│   └── common/
│       ├── LoadingSkeleton.tsx
│       └── SuccessSnackbar.tsx
├── hooks/                      # Custom hooks
│   ├── useConfiguration.ts
│   ├── useValidation.ts
│   ├── useDebounce.ts
│   └── useCache.ts
├── stores/                     # State management
│   └── configStore.ts
├── types/                      # TypeScript types
│   ├── configuration.ts
│   ├── validation.ts
│   └── autoFix.ts
├── utils/                      # Utilities
│   ├── formatters.ts
│   └── validators.ts
└── App.tsx
```

### State Management

#### React Query for Server State

```typescript
// src/hooks/useValidation.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { validateConfiguration } from '../api/validation';

export function useValidation(configName: string, validationType: string) {
  return useQuery({
    queryKey: ['validation', configName, validationType],
    queryFn: () => validateConfiguration(configName, validationType),
    staleTime: 5 * 60 * 1000,     // 5 minutes
    cacheTime: 10 * 60 * 1000,    // 10 minutes
    refetchOnWindowFocus: false,
    enabled: !!configName,
  });
}

export function useValidationMutation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ configName, validationType }) => 
      validateConfiguration(configName, validationType),
    onSuccess: (data, variables) => {
      // Update cache
      queryClient.setQueryData(
        ['validation', variables.configName, variables.validationType],
        data
      );
    },
  });
}
```

#### Zustand for UI State

```typescript
// src/stores/configStore.ts
import create from 'zustand';
import { devtools } from 'zustand/middleware';

interface ConfigStore {
  // State
  currentConfig: string | null;
  selectedEntity: string | null;
  activeTab: 'validation' | 'properties';
  
  // Actions
  setCurrentConfig: (name: string) => void;
  setSelectedEntity: (entity: string | null) => void;
  setActiveTab: (tab: 'validation' | 'properties') => void;
  reset: () => void;
}

export const useConfigStore = create<ConfigStore>()(
  devtools((set) => ({
    // Initial state
    currentConfig: null,
    selectedEntity: null,
    activeTab: 'validation',
    
    // Actions
    setCurrentConfig: (name) => set({ currentConfig: name }),
    setSelectedEntity: (entity) => set({ selectedEntity: entity }),
    setActiveTab: (tab) => set({ activeTab: tab }),
    reset: () => set({
      currentConfig: null,
      selectedEntity: null,
      activeTab: 'validation',
    }),
  }), { name: 'ConfigStore' })
);
```

### Custom Hooks

#### useDebounce

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

// Usage
function SearchComponent() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebounce(searchTerm, 500);
  
  useEffect(() => {
    if (debouncedSearch) {
      performSearch(debouncedSearch);
    }
  }, [debouncedSearch]);
  
  return <input onChange={(e) => setSearchTerm(e.target.value)} />;
}
```

#### useCache

```typescript
// src/hooks/useCache.ts
import { useState, useEffect } from 'react';

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = 300000  // 5 minutes
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    async function fetchData() {
      try {
        // Check localStorage cache
        const cached = localStorage.getItem(key);
        if (cached) {
          const entry: CacheEntry<T> = JSON.parse(cached);
          if (Date.now() < entry.expiresAt) {
            setData(entry.value);
            setLoading(false);
            return;
          }
        }
        
        // Fetch fresh data
        const result = await fetcher();
        
        // Cache result
        const entry: CacheEntry<T> = {
          value: result,
          expiresAt: Date.now() + ttl,
        };
        localStorage.setItem(key, JSON.stringify(entry));
        
        setData(result);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [key, ttl]);
  
  return { data, loading, error };
}
```

### Component Patterns

#### Composition Pattern

```typescript
// src/components/editor/ConfigurationEditor.tsx
import { Box } from '@mui/material';
import EntityTreePanel from '../panels/EntityTreePanel';
import MonacoEditor from './MonacoEditor';
import ValidationPanel from '../panels/ValidationPanel';

export default function ConfigurationEditor() {
  return (
    <Box display="flex" height="100vh">
      {/* Left: Entity Tree */}
      <Box width={300} borderRight="1px solid #ddd">
        <EntityTreePanel />
      </Box>
      
      {/* Center: Monaco Editor */}
      <Box flex={1}>
        <MonacoEditor />
      </Box>
      
      {/* Right: Validation Panel */}
      <Box width={400} borderLeft="1px solid #ddd">
        <ValidationPanel />
      </Box>
    </Box>
  );
}
```

#### Performance Optimization

```typescript
// src/components/panels/ValidationPanel.tsx
import { useMemo, memo } from 'react';

interface Props {
  issues: ValidationIssue[];
}

const ValidationPanel = memo(({ issues }: Props) => {
  // Expensive sorting memoized
  const sortedIssues = useMemo(() => {
    return [...issues].sort((a, b) => {
      const severityOrder = { error: 0, warning: 1, info: 2 };
      return severityOrder[a.severity] - severityOrder[b.severity];
    });
  }, [issues]);
  
  return (
    <Box>
      {sortedIssues.map((issue) => (
        <IssueItem key={issue.id} issue={issue} />
      ))}
    </Box>
  );
});

export default ValidationPanel;
```

#### Code Splitting

```typescript
// src/App.tsx
import { lazy, Suspense } from 'react';
import LoadingSkeleton from './components/common/LoadingSkeleton';

// Lazy load heavy components
const ConfigurationEditor = lazy(() => 
  import('./components/editor/ConfigurationEditor')
);

function App() {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <ConfigurationEditor />
    </Suspense>
  );
}

export default App;
```

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
    service.load_configuration = AsyncMock()
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
    mock_yaml_service.load_configuration.return_value = {
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
    assert result.config_name == "test_config"
    assert isinstance(result.issues, list)
    mock_yaml_service.load_configuration.assert_called_once_with("test_config")

@pytest.mark.asyncio
async def test_validate_uses_cache(validation_service, mock_cache_service):
    """Test that validation uses cache."""
    # Arrange
    cached_result = ValidationResult(
        config_name="test",
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
                "config_name": "test_config",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "config_name" in data
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
                "config_name": "nonexistent",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()
```

### Frontend Testing

#### Component Test Example

```typescript
// frontend/tests/unit/components/ValidationPanel.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ValidationPanel from '@/components/panels/ValidationPanel';

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
    
    render(<ValidationPanel issues={issues} />);
    
    expect(screen.getByText(/Column "missing" not found/)).toBeInTheDocument();
    expect(screen.getByText('test_entity')).toBeInTheDocument();
  });
  
  it('calls onApplyFix when button clicked', () => {
    const onApplyFix = vi.fn();
    const issues = [{
      id: '1',
      code: 'COLUMN_NOT_FOUND',
      auto_fixable: true,
      suggestion: { /* ... */ }
    }];
    
    render(<ValidationPanel issues={issues} onApplyFix={onApplyFix} />);
    
    const button = screen.getByRole('button', { name: /apply fix/i });
    fireEvent.click(button);
    
    expect(onApplyFix).toHaveBeenCalledOnce();
  });
  
  it('filters issues by severity', () => {
    const issues = [
      { id: '1', severity: 'error', message: 'Error' },
      { id: '2', severity: 'warning', message: 'Warning' },
    ];
    
    render(<ValidationPanel issues={issues} />);
    
    // Click errors filter
    fireEvent.click(screen.getByText('Errors'));
    
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.queryByText('Warning')).not.toBeInTheDocument();
  });
});
```

#### Hook Test Example

```typescript
// frontend/tests/unit/hooks/useDebounce.test.ts
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useDebounce } from '@/hooks/useDebounce';

describe('useDebounce', () => {
  it('debounces value changes', async () => {
    vi.useFakeTimers();
    
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );
    
    expect(result.current).toBe('initial');
    
    // Change value
    rerender({ value: 'changed' });
    expect(result.current).toBe('initial'); // Still old value
    
    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(500);
    });
    
    expect(result.current).toBe('changed'); // Now updated
    
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
npm run test:coverage
```

#### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Backend Services | 90%+ | 94% |
| Backend API | 85%+ | 88% |
| Backend Models | 100% | 100% |
| Frontend Components | 85%+ | 88% |
| Frontend Hooks | 90%+ | 92% |
| **Overall** | **90%+** | **91%** |

---

## 7. API Development

### RESTful Endpoints

```
# Configurations
GET    /api/v1/configurations           # List all
GET    /api/v1/configurations/{name}    # Get one
POST   /api/v1/configurations           # Create
PUT    /api/v1/configurations/{name}    # Update
DELETE /api/v1/configurations/{name}    # Delete

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
    config_name: str
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
        config = await self.yaml_service.load_configuration(request.config_name)
        
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
        config_name="test",
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
def create_backup(config_name: str) -> Path:
    """
    Create timestamped backup of configuration.
    
    Args:
        config_name: Name of configuration to backup
        
    Returns:
        Path to backup file
        
    Raises:
        ConfigurationNotFoundError: If config doesn't exist
    """
    pass
```

#### TypeScript (Frontend)

```typescript
// Good - Explicit types
interface ValidationIssue {
  id: string;
  code: string;
  severity: 'error' | 'warning' | 'info';
  entity?: string;
  message: string;
}

// Bad - Any types
interface ValidationIssue {
  id: any;
  code: any;
  severity: any;
  entity: any;
  message: any;
}

// Good - Descriptive component names
function ValidationIssueList({ issues }: { issues: ValidationIssue[] }) {
  return <>{/* ... */}</>;
}

// Bad - Generic names
function List({ data }: { data: any[] }) {
  return <>{/* ... */}</>;
}
```

### Error Handling

```python
# Good - Specific exceptions
try:
    config = await yaml_service.load_configuration(name)
except FileNotFoundError:
    raise ConfigurationNotFoundError(name)
except yaml.YAMLError as e:
    raise ValidationError(f"Invalid YAML: {e}")

# Bad - Catch all
try:
    config = await yaml_service.load_configuration(name)
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

def test_validation_includes_config_name():
    result = await service.validate("test", "all")
    assert result.config_name == "test"

# Bad - Multiple unrelated assertions
def test_validation():
    result = await service.validate("test", "all")
    assert result.config_name == "test"
    assert len(result.issues) > 0
    assert result.cache_hit is False
    assert result.timestamp is not None
```

### Performance

```typescript
// Good - Memoize expensive computations
const sortedIssues = useMemo(() => {
  return [...issues].sort((a, b) => 
    a.severity.localeCompare(b.severity)
  );
}, [issues]);

// Bad - Compute every render
const sortedIssues = [...issues].sort((a, b) => 
  a.severity.localeCompare(b.severity)
);

// Good - Debounce user input
const debouncedSearch = useDebounce(searchTerm, 500);

// Bad - Trigger on every keystroke
useEffect(() => {
  performSearch(searchTerm);
}, [searchTerm]);
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
npm run test -- ValidationPanel.test.tsx

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

// React DevTools
// Install React DevTools browser extension
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
   git commit -m "feat: add my feature"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

### Commit Convention

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

Examples:
```
feat: add auto-fix for missing columns
fix: resolve validation cache invalidation bug
docs: update developer guide with testing section
test: add integration tests for auto-fix API
refactor: extract validation logic into service
chore: update dependencies
```

---

## Related Documentation

- [UI Architecture](UI_ARCHITECTURE.md) - Detailed architecture
- [User Guide](USER_GUIDE.md) - End-user documentation
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures
- [Configuration Guide](CONFIGURATION_GUIDE.md) - YAML syntax
- [API Reference](API_REFERENCE.md) - API documentation

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**For**: Shape Shifter Configuration Editor v0.1.0
