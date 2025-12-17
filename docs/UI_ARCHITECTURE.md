# Configuration Editor - Software Architecture

## 1. Executive Summary

This document defines the software architecture for the Shape Shifter Configuration Editor, a web-based application for managing data transformation configurations. The architecture supports a phased rollout from basic entity management to advanced data-aware features with intelligent suggestions.

**Architecture Goals**:
- Leverage existing Python transformation engine
- Modern, responsive web UI with professional UX
- Extensible for future enhancements
- Simple deployment and maintenance
- 90%+ test coverage

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser (Client)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          React/TypeScript Frontend                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │ │
│  │  │ Monaco   │  │  Entity  │  │    Validation      │   │ │
│  │  │ Editor   │  │  Tree    │  │    Panel           │   │ │
│  │  └──────────┘  └──────────┘  └────────────────────┘   │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │         State Management (React Query + Zustand)   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/JSON API
┌──────────────────────────┴──────────────────────────────────┐
│                    Python Backend (Server)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                FastAPI Application                      │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │ │
│  │  │ Configuration│  │  Validation   │  │  Auto-Fix  │  │ │
│  │  │   Service    │  │   Service     │  │  Service   │  │ │
│  │  └──────────────┘  └───────────────┘  └────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Shape Shifter Transformation Engine           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ config_model │  │specifications│  │  normalizer │  │ │
│  │  │   .py        │  │    .py       │  │     .py     │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                      File System                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Configurations│  │   Backups    │  │      Logs       │  │
│  │   (YAML)     │  │  (Timestamped)│  │  (Application)  │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Architecture Principles

1. **Separation of Concerns**: Clear boundaries between UI, API, and business logic
2. **Service Layer Pattern**: Business logic encapsulated in services
3. **Dependency Injection**: Testable, flexible component composition
4. **Type Safety**: TypeScript (frontend) and Pydantic (backend)
5. **API-First**: Well-defined REST API with OpenAPI documentation
6. **Stateless Backend**: All state managed client-side or in persistent storage
7. **Caching Strategy**: Reduce API calls and improve performance
8. **Error Handling**: Comprehensive error handling at all layers

---

## 3. Technology Stack

### 3.1 Frontend

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | React 18 | UI library with hooks and concurrent features |
| **Language** | TypeScript | Type-safe JavaScript |
| **Editor** | Monaco Editor | VS Code's editor for YAML editing |
| **UI Components** | Material-UI (MUI) | Pre-built component library |
| **State Management** | React Query + Zustand | Server and client state |
| **Build Tool** | Vite | Fast build tool and dev server |
| **Testing** | Vitest + React Testing Library | Unit and component tests |
| **Styling** | Emotion (CSS-in-JS) | Component styling |

### 3.2 Backend

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | FastAPI | Modern async Python web framework |
| **Language** | Python 3.11+ | Backend logic |
| **Validation** | Pydantic | Data validation and settings |
| **ASGI Server** | Uvicorn | Production ASGI server |
| **Testing** | pytest + pytest-asyncio | Unit and integration tests |
| **Linting** | Ruff | Fast Python linter |
| **Package Manager** | uv | Fast Python package manager |

### 3.3 Integration

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API Protocol** | REST/JSON | Client-server communication |
| **API Documentation** | OpenAPI/Swagger | Auto-generated API docs |
| **CORS** | FastAPI middleware | Cross-origin requests |
| **File Format** | YAML | Configuration storage |

---

## 4. Frontend Architecture

### 4.1 Directory Structure

```
frontend/
├── src/
│   ├── api/                    # API client layer
│   │   ├── client.ts           # Axios configuration
│   │   ├── configurations.ts   # Config API calls
│   │   ├── validation.ts       # Validation API calls
│   │   └── autoFix.ts          # Auto-fix API calls
│   ├── components/             # React components
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
│   ├── hooks/                  # Custom React hooks
│   │   ├── useConfiguration.ts
│   │   ├── useValidation.ts
│   │   ├── useDebounce.ts
│   │   └── useCache.ts
│   ├── stores/                 # Zustand stores
│   │   └── configStore.ts
│   ├── types/                  # TypeScript types
│   │   ├── configuration.ts
│   │   ├── validation.ts
│   │   └── autoFix.ts
│   ├── utils/                  # Utility functions
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── App.tsx                 # Main application
│   └── main.tsx                # Entry point
├── tests/                      # Test files
│   ├── unit/
│   ├── integration/
│   └── setup.ts
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### 4.2 Component Architecture

#### Layout Components

```typescript
// Main layout with panels
<ConfigurationEditor>
  <EntityTreePanel />      // Left: entity navigation
  <MonacoEditor />         // Center: YAML editor
  <ValidationPanel />      // Right: validation results
  <PropertiesPanel />      // Right: entity properties
</ConfigurationEditor>
```

#### Component Hierarchy

```
App
├── ConfigurationEditor (main container)
│   ├── Header
│   │   ├── ConfigSelector
│   │   ├── SaveButton
│   │   └── ValidateButton
│   ├── Layout (3-panel)
│   │   ├── EntityTreePanel
│   │   │   ├── EntityTree
│   │   │   ├── EntitySearch
│   │   │   └── EntityFilter
│   │   ├── EditorPanel
│   │   │   ├── MonacoEditor
│   │   │   └── EditorToolbar
│   │   └── RightPanel (tabbed)
│   │       ├── ValidationPanel
│   │       │   ├── ValidationTabs
│   │       │   ├── IssueList
│   │       │   └── AutoFixSuggestions
│   │       └── PropertiesPanel
│   │           ├── PropertyForm
│   │           └── ForeignKeyEditor
│   └── Dialogs
│       ├── PreviewDialog
│       ├── ConfirmDialog
│       ├── ErrorDialog
│       └── EntityFormDialog (with YAML editor)
```

#### YAML Editor Component

The **YamlEditor** component provides a dual-mode editing experience for entities, similar to VS Code's settings editor:

**Location:** `frontend/src/components/common/YamlEditor.vue`

**Features:**
- Monaco Editor integration for professional code editing
- Real-time YAML syntax validation
- Error display with line numbers
- Configurable height and read-only mode
- Auto-completion and syntax highlighting

**Props:**
```typescript
interface YamlEditorProps {
  modelValue: string;           // YAML content to edit
  height?: string;              // Editor height (default: '400px')
  readonly?: boolean;           // Read-only mode (default: false)
  validateOnChange?: boolean;   // Validate as user types (default: true)
}
```

**Events:**
```typescript
interface YamlEditorEvents {
  'update:modelValue': (value: string) => void;  // Content changed
  'validate': (result: ValidationResult) => void; // Validation result
  'change': (value: string) => void;             // Content changed (alias)
}

interface ValidationResult {
  valid: boolean;
  error: string | null;
}
```

**Usage Example:**
```vue
<template>
  <YamlEditor
    v-model="yamlContent"
    height="500px"
    :readonly="false"
    @validate="handleValidation"
  />
</template>

<script setup lang="ts">
import YamlEditor from '@/components/common/YamlEditor.vue'
import { ref } from 'vue'

const yamlContent = ref('entity:\n  type: data')

function handleValidation(result: { valid: boolean; error: string | null }) {
  if (!result.valid) {
    console.error('YAML Error:', result.error)
  }
}
</script>
```

#### EntityFormDialog Component

The **EntityFormDialog** has been enhanced with a tabbed interface for dual-mode editing:

**Location:** `frontend/src/components/entities/EntityFormDialog.vue`

**Tabs:**
1. **Form Tab** - Visual form editor with input fields
2. **YAML Tab** - Raw YAML editor with syntax highlighting

**Bidirectional Synchronization:**
```typescript
// Form → YAML conversion
function formDataToYaml(): string {
  const entityData = {
    [entityName.value]: {
      type: entityType.value,
      keys: naturalKeys.value?.split(',').map(k => k.trim()) || [],
      surrogate_id: surrogateId.value || undefined,
      // ... other fields
    }
  }
  return yaml.dump(entityData, { indent: 2, lineWidth: 100 })
}

// YAML → Form conversion
function yamlToFormData(yamlString: string): void {
  try {
    const parsed = yaml.load(yamlString)
    const entityKey = Object.keys(parsed)[0]
    const entity = parsed[entityKey]
    
    entityName.value = entityKey
    entityType.value = entity.type
    naturalKeys.value = entity.keys?.join(', ') || ''
    // ... update other fields
  } catch (error) {
    yamlError.value = error.message
  }
}
```

**Tab Switching Behavior:**
```typescript
// Watch for tab changes to sync data
watch(activeTab, (newTab, oldTab) => {
  if (newTab === 'yaml' && oldTab !== 'yaml') {
    // Switching TO yaml tab - convert form to YAML
    yamlContent.value = formDataToYaml()
    yamlError.value = null
  } else if (oldTab === 'yaml' && newTab !== 'yaml') {
    // Switching FROM yaml tab - validate and sync to form
    if (yamlValid.value) {
      yamlToFormData(yamlContent.value)
    }
  }
})
```

**Validation Rules:**
- YAML syntax must be valid before switching from YAML tab
- Form validation occurs on Save/OK button click
- Invalid YAML shows error banner with details
- Cannot save entity until all validation passes

**Dependencies:**
```json
{
  "dependencies": {
    "monaco-editor": "^0.52.0",
    "@guolao/vue-monaco-editor": "^1.5.6",
    "js-yaml": "^4.1.0"
  },
  "devDependencies": {
    "@types/js-yaml": "^4.0.9"
  }
}
```

### 4.3 State Management

#### Server State (React Query)

```typescript
// Fetch and cache server data
const { data, isLoading, error } = useQuery({
  queryKey: ['configuration', configName],
  queryFn: () => fetchConfiguration(configName),
  staleTime: 5 * 60 * 1000,  // 5 minutes
});

// Mutations with optimistic updates
const mutation = useMutation({
  mutationFn: saveConfiguration,
  onSuccess: () => {
    queryClient.invalidateQueries(['configuration']);
  },
});
```

**Benefits**:
- Automatic caching and refetching
- Loading and error states
- Optimistic updates
- Background synchronization

#### Client State (Zustand)

```typescript
// UI state store
interface ConfigStore {
  currentConfig: string | null;
  selectedEntity: string | null;
  activeTab: 'validation' | 'properties';
  setCurrentConfig: (name: string) => void;
  setSelectedEntity: (entity: string | null) => void;
  setActiveTab: (tab: string) => void;
}

const useConfigStore = create<ConfigStore>((set) => ({
  currentConfig: null,
  selectedEntity: null,
  activeTab: 'validation',
  setCurrentConfig: (name) => set({ currentConfig: name }),
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),
  setActiveTab: (tab) => set({ activeTab: tab as any }),
}));
```

**Benefits**:
- Simple API
- No boilerplate
- TypeScript support
- DevTools integration

### 4.4 Custom Hooks

#### useDebounce

```typescript
// Debounce rapidly changing values
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}
```

#### useValidation

```typescript
// Validation with caching
export function useValidation(configName: string, type: string) {
  return useQuery({
    queryKey: ['validation', configName, type],
    queryFn: () => validateConfiguration(configName, type),
    staleTime: 5 * 60 * 1000,
    enabled: !!configName,
  });
}
```

### 4.5 Performance Optimizations

#### Code Splitting

```typescript
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
```

#### Memoization

```typescript
// Prevent unnecessary re-renders
const sortedIssues = useMemo(() => {
  return [...issues].sort((a, b) => 
    a.severity.localeCompare(b.severity)
  );
}, [issues]);
```

#### Virtual Scrolling

```typescript
// Render only visible items
import { FixedSizeList } from 'react-window';

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
```

---

## 5. Backend Architecture

### 5.1 Directory Structure

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
│   │   ├── config.py          # Settings management
│   │   ├── cache.py           # Caching service
│   │   └── errors.py          # Custom exceptions
│   ├── models/
│   │   ├── configuration.py   # Pydantic models
│   │   ├── validation.py
│   │   ├── auto_fix.py
│   │   └── test_run.py
│   ├── services/
│   │   ├── yaml_service.py
│   │   ├── validation_service.py
│   │   ├── auto_fix_service.py
│   │   └── test_runner.py
│   └── main.py                # FastAPI app
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### 5.2 Design Patterns

#### Service Layer Pattern

```python
# Business logic in services
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

#### Dependency Injection

```python
# FastAPI dependencies
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

#### Strategy Pattern

```python
# Different validation strategies
class ValidationStrategy(ABC):
    @abstractmethod
    async def validate(self, config: dict) -> list[ValidationIssue]:
        pass

class StructuralValidator(ValidationStrategy):
    async def validate(self, config: dict) -> list[ValidationIssue]:
        # Structural validation
        pass

class DataValidator(ValidationStrategy):
    async def validate(self, config: dict) -> list[ValidationIssue]:
        # Data validation
        pass
```

#### Repository Pattern

```python
# Data access abstraction
class YAMLRepository:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    async def load(self, name: str) -> dict:
        # File I/O
        pass
    
    def save(self, name: str, data: dict) -> None:
        # File I/O
        pass
```

### 5.3 Caching Architecture

#### Cache Service

```python
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
        keys = [k for k in self._cache if k.startswith(pattern)]
        for key in keys:
            self._cache.pop(key)
```

#### Cache Keys

```python
def make_cache_key(config_name: str, type: str) -> str:
    return f"validation:{config_name}:{type}"
```

**Examples**:
- `validation:arbodat:all`
- `validation:arbodat:structural`
- `validation:sample_entity:entity`

### 5.4 Error Handling

```python
# Custom exceptions
class BaseAPIException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class ConfigurationNotFoundError(BaseAPIException):
    def __init__(self, config_name: str):
        super().__init__(
            f"Configuration '{config_name}' not found",
            status_code=404
        )

# Exception handler
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

---

## 6. API Design

### 6.1 RESTful Endpoints

```
# Configurations
GET    /api/v1/configurations           # List all configs
GET    /api/v1/configurations/{name}    # Get specific config
POST   /api/v1/configurations           # Create config
PUT    /api/v1/configurations/{name}    # Update config
DELETE /api/v1/configurations/{name}    # Delete config

# Validation
POST   /api/v1/validate                 # Validate config
GET    /api/v1/validate/{name}/results  # Get cached results

# Auto-Fix
POST   /api/v1/auto-fix/preview         # Preview fixes
POST   /api/v1/auto-fix/apply           # Apply fixes
POST   /api/v1/auto-fix/rollback        # Rollback changes

# Test Execution
POST   /api/v1/test-runs                # Start test run
GET    /api/v1/test-runs/{id}           # Get test status
GET    /api/v1/test-runs/{id}/results   # Get test results
```

### 6.2 Request/Response Models

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

### 6.3 Error Responses

```json
{
  "error": "Configuration 'invalid' not found",
  "type": "ConfigurationNotFoundError",
  "timestamp": "2025-12-14T10:30:00Z",
  "path": "/api/v1/configurations/invalid",
  "method": "GET"
}
```

---

## 7. Data Flow

### 7.1 Configuration Load Flow

```
User clicks "Open Config"
  ↓
Frontend: Send GET /api/v1/configurations/{name}
  ↓
Backend: YAMLService.load_configuration()
  ↓
Backend: Parse YAML, validate structure
  ↓
Backend: Return configuration JSON
  ↓
Frontend: Display in Monaco Editor
  ↓
Frontend: Populate entity tree
```

### 7.2 Validation Flow

```
User clicks "Validate All"
  ↓
Frontend: Check cache (5-min TTL)
  ↓
Cache hit? → Display cached results
  ↓
Cache miss: Send POST /api/v1/validate
  ↓
Backend: Check cache
  ↓
Cache miss: Run validation
  ↓
Backend: Return validation results
  ↓
Backend: Cache results (5 min)
  ↓
Frontend: Display in validation panel
  ↓
Frontend: Cache results (5 min)
```

### 7.3 Auto-Fix Flow

```
User clicks "Apply Fix"
  ↓
Frontend: Send POST /api/v1/auto-fix/preview
  ↓
Backend: Generate fix preview
  ↓
Frontend: Display before/after comparison
  ↓
User confirms
  ↓
Frontend: Send POST /api/v1/auto-fix/apply
  ↓
Backend: Create backup
  ↓
Backend: Apply fix to config
  ↓
Backend: Save configuration
  ↓
Backend: Revalidate
  ↓
Frontend: Update editor
  ↓
Frontend: Show success message
  ↓
Frontend: Invalidate validation cache
```

---

## 8. Security

### 8.1 Input Validation

- All inputs validated with Pydantic models
- YAML parsing with safe loaders only
- File path validation (prevent traversal)
- Content type validation

### 8.2 CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.3 Future Security (Phase 3)

- Authentication (JWT tokens)
- Authorization (RBAC)
- Rate limiting
- Audit logging
- HTTPS enforcement

---

## 9. Deployment

### 9.1 Development

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

### 9.2 Production (Future)

```bash
# Docker Compose
docker-compose up -d

# Services:
# - Backend: Gunicorn + Uvicorn workers
# - Frontend: Nginx serving static files
# - Database: PostgreSQL (future)
# - Cache: Redis (future)
```

---

## 10. Testing Strategy

### 10.1 Frontend Testing

- **Unit Tests**: Components, hooks, utilities (Vitest)
- **Integration Tests**: User workflows (React Testing Library)
- **E2E Tests**: Critical paths (Playwright, future)

### 10.2 Backend Testing

- **Unit Tests**: Services, models (pytest)
- **Integration Tests**: API endpoints (pytest + httpx)
- **E2E Tests**: Full workflows (pytest)

### 10.3 Coverage Targets

- Backend: 90%+ (achieved: 91%)
- Frontend: 85%+ (achieved: 88%)
- Overall: 90%+ (achieved: 90%)

---

## 11. Related Documentation

- [UI Requirements](UI_REQUIREMENTS.md) - Functional requirements
- [User Guide](USER_GUIDE.md) - User documentation
- [Developer Guide](DEVELOPER_GUIDE.md) - Development guide
- [Testing Guide](TESTING_GUIDE.md) - Testing documentation
- [Configuration Guide](CONFIGURATION_GUIDE.md) - Config syntax

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**Status**: Implemented and Deployed
