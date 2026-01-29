# Project Editor - Software Architecture

## 1. Executive Summary

This document defines the software architecture for the Shape Shifter Project Editor, a web-based application for managing data transformation configurations. The architecture supports a phased rollout from basic entity management to advanced data-aware features with intelligent suggestions.

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
│                      Web Browser (Client)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Vue3/TypeScript Frontend                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │ │
│  │  │ Monaco   │  │  Entity  │  │    Validation      │    │ │
│  │  │ Editor   │  │  Tree    │  │    Panel           │    │ │
│  │  └──────────┘  └──────────┘  └────────────────────┘    │ │
│  │  ┌────────────────────────────────────────────────┐    │ │
│  │  │             State Management (Pinia)           │    │ │
│  │  └────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST/JSON API
┌──────────────────────────┴──────────────────────────────────┐
│                    Python Backend (Server)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                FastAPI Application                     │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────┐   │ │
│  │  │ Project│  │  Validation   │  │  Auto-Fix  │   │ │
│  │  │   Service    │  │   Service     │  │  Service   │   │ │
│  │  └──────────────┘  └───────────────┘  └────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Shape Shifter Transformation Engine          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐   │ │
│  │  │     model    │  │specifications│  │  normalizer │   │ │
│  │  │     .py      │  │    .py       │  │     .py     │   │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                      File System                            │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ Project │  │   Backups     │  │      Logs       │  │
│  │   (YAML)      │  │   (YAML)      │  │  (Application)  │  │
│  └───────────────┘  └───────────────┘  └─────────────────┘  │
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
| **Framework** | Vue3 | UI frontend framework (Composition API) |
| **Language** | TypeScript | Type-safe JavaScript |
| **Editor** | Monaco Editor | VS Code's editor for YAML editing |
| **UI Components** | Vuetify | Component library and theming |
| **State Management** | Pinia | Client/UI state management |
| **Build Tool** | Vite | Fast build tool and dev server |
| **Testing** | Vitest + @vue/test-utils | Unit, component, and composable tests |
| **Styling** | SCSS + Vuetify theme tokens | Component styling |

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
| **File Format** | YAML | Project storage |

---

## 4. Frontend Architecture

### 4.1 Directory Structure

```
frontend/
├── src/
│   ├── api/                    # Axios client + per-resource modules
│   ├── components/             # Vue components (common, validation, entities, data sources, etc.)
│   ├── composables/            # Reusable Composition API helpers
│   ├── stores/                 # Pinia stores
│   ├── views/                  # Route-level screens
│   ├── router/                 # Vue Router configuration
│   ├── plugins/                # Vuetify and other plugin setup
│   ├── styles/                 # Global SCSS and theme variables
│   ├── types/                  # Shared TypeScript types
│   ├── App.vue                 # Root component
│   └── main.ts                 # Entry point
├── public/                     # Static assets
├── docs/                       # Frontend-specific notes
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### 4.2 Component Architecture

#### Layout Components

```typescript
// Main layout with panels
<ProjectEditor>
  <EntityTreePanel />      // Left: entity navigation
  <MonacoEditor />         // Center: YAML editor
  <ValidationPanel />      // Right: validation results
  <PropertiesPanel />      // Right: entity properties
</ProjectEditor>
```

#### Component Hierarchy

```
App
├── ProjectEditor (main container)
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

const yamlContent = ref('entity:\n  type: entity')

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

#### Server State

- Fetch via `frontend/src/api` modules (axios client with interceptors).
- Wrap calls in composables (e.g., `useProjects`, `useValidation`) that expose `loading`, `error`, `data`, and `refresh`.
- Cache per-configuration responses in Pinia or composable-level refs; invalidate after save/auto-fix actions.

```typescript
// frontend/src/composables/useValidation.ts
import { ref } from 'vue';
import { getValidation } from '@/api/validation';

export function useValidation() {
  const loading = ref(false);
  const error = ref<string | null>(null);
  const result = ref(null);

  const run = async (configName: string, type: string) => {
    loading.value = true;
    error.value = null;
    try {
      result.value = await getValidation(configName, type);
    } catch (err) {
      error.value = (err as Error).message;
    } finally {
      loading.value = false;
    }
  };

  return { loading, error, result, run };
}
```

#### Client State (Pinia)

```typescript
// frontend/src/stores/configurationStore.ts
import { defineStore } from 'pinia';

export const useProjectStore = defineStore('configuration', {
  state: () => ({
    currentConfig: null as string | null,
    selectedEntity: null as string | null,
    activeTab: 'validation' as 'validation' | 'properties',
  }),
  actions: {
    setCurrentConfig(name: string) {
      this.currentConfig = name;
    },
    setSelectedEntity(entity: string | null) {
      this.selectedEntity = entity;
    },
    setActiveTab(tab: 'validation' | 'properties') {
      this.activeTab = tab;
    },
  },
});
```

- Derive store refs with `storeToRefs` inside components.
- Keep derived/computed UI-only state inside components; persist long-lived app state in stores.

### 4.4 Composables

#### useDebounceFn

```typescript
// Debounce rapidly changing values (via VueUse)
import { ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';

export function useDebouncedSearch(delay = 300) {
  const term = ref('');
  const run = useDebounceFn((value: string, cb: (value: string) => void) => cb(value), delay);

  const update = (value: string, cb: (value: string) => void) => {
    term.value = value;
    run(value, cb);
  };

  return { term, update };
}
```

#### useValidation

```typescript
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useValidationStore } from '@/stores/validation';

export function useValidationSummary() {
  const store = useValidationStore();
  const { validationResult, loading } = storeToRefs(store);

  const errorCount = computed(() => validationResult.value?.error_count ?? 0);
  const warningCount = computed(() => validationResult.value?.warning_count ?? 0);

  return {
    validationResult,
    loading,
    errorCount,
    warningCount,
    refresh: store.validateProject,
  };
}
```

### 4.5 Performance Optimizations

#### Code Splitting

```vue
<script setup lang="ts">
import { defineAsyncComponent } from 'vue';

const ProjectEditor = defineAsyncComponent(() =>
  import('@/components/projects/ProjectEditor.vue')
);
</script>

<template>
  <Suspense>
    <ProjectEditor />
    <template #fallback>
      <LoadingSkeleton />
    </template>
  </Suspense>
</template>
```

#### Derived State

```typescript
// Prevent unnecessary recomputation
import { computed } from 'vue';

const sortedIssues = computed(() =>
  [...issues.value].sort((a, b) => a.severity.localeCompare(b.severity))
);
```

#### Virtual Scrolling

```vue
<VVirtualScroll
  :items="entities"
  height="600"
  item-height="44"
  v-slot="{ item }"
>
  <EntityNode :entity="item" />
</VVirtualScroll>
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
│   │   ├── configuration.py   # API Pydantic models (raw ${ENV_VARS})
│   │   ├── validation.py
│   │   ├── auto_fix.py
│   │   └── test_run.py
│   ├── mappers/              # Layer boundary translators
│   │   ├── data_source_mapper.py  # Resolves env vars here
│   │   └── table_schema_mapper.py
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

#### Mapper Pattern (Layer Boundary)

```python
# Translates between API and Core layers, resolving env vars
class DataSourceMapper:
    """Maps between API and Core data sources.
    
    Environment variable resolution happens at this layer boundary.
    """
    
    @staticmethod
    def to_core_config(
        api_config: ApiDataSourceConfig
    ) -> CoreDataSourceConfig:
        """Convert API config to Core config.
        
        IMPORTANT: Resolves environment variables during mapping.
        API entities remain raw (${ENV_VAR}), core entities are resolved.
        """
        # Resolution at the boundary
        api_config = api_config.resolve_config_env_vars()
        
        return CoreDataSourceConfig(
            name=api_config.name,
            cfg={...}  # Fully resolved
        )
```

**Layer Responsibilities:**
- **API Models**: Raw data with `${ENV_VARS}` (unresolved)
- **Mappers**: Translation + environment variable resolution
- **Core Models**: Fully resolved, ready for execution

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
        project_name: str,
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
        request.project_name,
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
def make_cache_key(project_name: str, type: str) -> str:
    return f"validation:{project_name}:{type}"
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

class ProjectNotFoundError(BaseAPIException):
    def __init__(self, project_name: str):
        super().__init__(
            f"Project '{project_name}' not found",
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
# Projects
GET    /api/v1/projects           # List all configs
GET    /api/v1/projects/{name}    # Get specific config
POST   /api/v1/projects           # Create config
PUT    /api/v1/projects/{name}    # Update config
DELETE /api/v1/projects/{name}    # Delete config

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
    project_name: str
    validation_type: ValidationType = ValidationType.ALL
    entity_name: Optional[str] = None

# Response
class ValidationResponse(BaseModel):
    project_name: str
    validation_type: ValidationType
    timestamp: datetime
    issues: list[ValidationIssue]
    summary: ValidationSummary
    cache_hit: bool = False
```

### 6.3 Error Responses

```json
{
  "error": "Project 'invalid' not found",
  "type": "ProjectNotFoundError",
  "timestamp": "2025-12-14T10:30:00Z",
  "path": "/api/v1/projects/invalid",
  "method": "GET"
}
```

---

## 7. Data Flow

### 7.1 Project Load Flow

```
User clicks "Open Config"
  ↓
Frontend: Send GET /api/v1/projects/{name}
  ↓
Backend: YAMLService.load_project()
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

### 8.2 CORS Project

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

- **Unit Tests**: Components, composables, utilities (Vitest)
- **Integration Tests**: User workflows
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
- [Project Guide](CONFIGURATION_GUIDE.md) - Config syntax

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**Status**: Implemented and Deployed
