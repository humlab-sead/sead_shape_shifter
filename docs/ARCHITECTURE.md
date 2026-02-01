# Shape Shifter - Architecture

## Overview

Shape Shifter is a data transformation system that harmonizes heterogeneous input data into a target schema through declarative configuration. The system consists of three loosely-coupled components:

1. **Core** - Python-based transformation engine executing declarative pipelines
2. **Backend** - REST API providing configuration management and preview services
3. **Frontend** - Web-based configuration editor with validation and visualization

```
┌──────────────────────────────────────────────────────────┐
│                    Web Browser                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Frontend (Vue 3)                      │  │
│  │   Configuration Editor • Validation • Preview      │  │
│  └────────────────┬───────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────┘
                    │ REST/JSON
┌───────────────────┼──────────────────────────────────────┐
│  ┌────────────────┴───────────────────────────────────┐  │
│  │            Backend (FastAPI)                       │  │
│  │   API Layer • Services • Mappers                   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │              Core (Python)                         │  │
│  │   Pipeline • Loaders • Validators • Dispatchers    │  │
│  └────────────────┬───────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────┘
                    │
              ┌─────┴─────┐
              │ File I/O  │  YAML • CSV • Excel
              │ Database  │  PostgreSQL • SQLite
              └───────────┘
```

---

## Architectural Goals

### Primary Goals

- **Separation of Concerns**: Core transformation logic independent of API/UI
- **Pluggability**: Extension points for loaders, validators, dispatchers, and filters
- **Declarative Configuration**: Behavior defined in YAML, not code
- **Layer Isolation**: Clear boundaries between API (unresolved), Mapper (resolution), and Core (resolved)
- **Testability**: Components testable in isolation

### Non-Goals

- Real-time collaborative editing
- Native mobile applications
- Streaming data processing
- Built-in version control (delegated to file system)

---

## System Components

### Core (Transformation Engine)

**Responsibility**: Execute declarative transformation pipelines from configuration to output.

**Key Abstractions**:
- **Pipeline**: Multi-phase processing (Extract → Filter → Link → Unnest → Translate → Store)
- **Entities**: Logical datasets with identity, relationships, and transformations
- **Loaders**: Pluggable data source connectors (SQL, CSV, Excel, fixed values)
- **Validators**: Constraint checking (cardinality, foreign keys, functional dependencies)
- **Dispatchers**: Output format handlers (Excel, CSV, database)

**Architectural Patterns**:
- **Registry Pattern**: Dynamic discovery of loaders/validators/dispatchers via decorators
- **Topological Sorting**: Dependency-aware entity processing order
- **Immutable Configuration**: Deep copy on read to prevent mutations

**Extension Points**:
```python
# Register custom loader
@DataLoaders.register(key="custom_source")
class CustomLoader(DataLoader):
    async def load(self) -> pd.DataFrame:
        ...

# Register custom validator
@Validators.register(key="custom_check", stage="pre-merge")
class CustomValidator(ConstraintValidator):
    ...
```

**Core Invariants**:
- All entity processing respects dependency order (no cycles)
- Foreign key relationships use local `system_id` values
- Environment variables always resolved before Core execution
- Configuration files are immutable during execution

---

### Backend (API Layer)

**Responsibility**: Expose Core capabilities via REST API, manage project lifecycle, provide editor services.

**Key Abstractions**:
- **Services**: Business logic for validation, auto-fix, entity preview, schema introspection
- **Mappers**: Translate between API models (raw `${ENV_VARS}`) and Core models (resolved)
- **Models**: Pydantic schemas for request/response validation

**Architectural Patterns**:
- **Layer Boundary**: API → Mapper → Core (environment variable resolution at mapper)
- **Service Layer**: Business logic isolated from HTTP concerns
- **Dependency Injection**: Services injected via FastAPI dependencies
- **3-Tier Cache**: TTL → Project Version → Entity Hash (xxhash for invalidation)

**Layer Responsibilities**:
```
API Layer (models/)
  ↓ Raw data with ${ENV_VARS}
Mapper Layer (mappers/)
  ↓ Resolve env vars + directives (@include:, @value:)
Core Layer (src/)
  ↓ Fully resolved entities
```

**Extension Points**:
- Add services for new features
- Register custom validators
- Extend auto-fix suggestion logic

**Backend Invariants**:
- API models never contain resolved environment variables
- Core always receives fully resolved configuration
- Mappers are the only layer performing resolution
- Services remain stateless (state in cache or filesystem)

---

### Frontend (Configuration Editor)

**Responsibility**: Provide intuitive UI for project configuration, validation, and preview.

**Key Abstractions**:
- **Stores (Pinia)**: Client-side state management for projects, entities, validation
- **Composables**: Reusable logic for validation, auto-fix, entity preview
- **Components**: Entity editor, dependency graph, validation panel, Monaco YAML editor

**Architectural Patterns**:
- **Composition API**: Reusable logic via composables, not mixins
- **Unidirectional Data Flow**: User action → API call → State update → UI update
- **Optimistic Updates**: Immediate UI feedback with rollback on failure
- **Debounced Validation**: Reduce API calls during typing (300ms delay)

**Extension Points**:
- Register custom entity types in form builder
- Add visualization components to graph
- Extend validation display with custom renderers

**Frontend Invariants**:
- State managed in Pinia stores, not component state
- API calls isolated in `api/` layer, never in components
- Validation state synchronized with backend
- Monaco Editor used for all YAML editing

---

## Data Flow

### Configuration Loading

```
User selects project
  ↓
Frontend: GET /api/v1/projects/{name}
  ↓
Backend: ProjectMapper.to_api_config()
  ├─ Load YAML from filesystem
  ├─ Preserve ${ENV_VARS} and @directives
  └─ Return API model (unresolved)
  ↓
Frontend: Store in Pinia (projectStore)
  ↓
Frontend: Render entities in editor
```

### Entity Preview

```
User edits entity in Monaco
  ↓
Frontend: Debounced preview (300ms)
  ↓
Backend: POST /api/v1/preview
  ├─ Check 3-tier cache (TTL/version/hash)
  ├─ ProjectMapper.to_core() [resolve env vars]
  ├─ Core: ShapeShifter.preview(entity, limit)
  └─ Return preview data
  ↓
Frontend: Display in split-view grid
```

### Validation Flow

```
User clicks "Check Project"
  ↓
Frontend: POST /api/v1/validate
  ↓
Backend: ValidationService.validate()
  ├─ Structural validation (schema, refs)
  ├─ Constraint validation (FKs, cycles)
  ├─ Optional: Data validation (sample rows)
  └─ Return ValidationResult
  ↓
Frontend: Display in validation panel
  ├─ Group by severity (error/warning/info)
  └─ Show entity badges in list
```

### Execution Flow

```
User clicks "Execute"
  ↓
Frontend: POST /api/v1/execute
  ↓
Backend: ProjectMapper.to_core() [resolve]
  ↓
Core: ShapeShifter.normalize()
  ├─ ProcessState: Topological sort
  ├─ For each entity (dependency order):
  │   ├─ Extract (via DataLoader)
  │   ├─ Filter (post-load filters)
  │   ├─ Link (FK relationships)
  │   ├─ Unnest (wide → long)
  │   └─ Translate (column mapping)
  └─ Store (via Dispatcher)
  ↓
Backend: Return execution result
  ↓
Frontend: Show completion status
```

---

## Control Flow

### Dependency Resolution

Entities form a directed acyclic graph (DAG). Processing order determined by:

1. **Explicit**: `depends_on: [parent_entity]`
2. **Implicit**: Foreign key references (`entity: parent`)
3. **Source**: `source: parent_entity` (data type entities)

**Topological Sort**:
```
1. Build dependency graph
2. Detect cycles (error if found)
3. Compute depths (distance from roots)
4. Sort by depth (parents before children)
5. Process in sorted order
```

### Environment Variable Resolution

**Two-Phase Strategy**:

1. **API → Core (Mapper)**:
   - Resolve `${ENV_VARS}` to actual values
   - Resolve `@include:` directives to embedded content
   - Resolve `@value:` directives to runtime values
   - Result: Fully resolved configuration for Core

2. **API → YAML (Save)**:
   - Preserve `${ENV_VARS}` and directives
   - Maintain original structure for editing
   - Result: Unchanged configuration file

**Principle**: Directives live in YAML/API layer, resolved values in Core layer.

---

## Extension and Customization

### Adding Data Sources

1. Create loader class inheriting `DataLoader`
2. Define schema using `ClassVar[DriverSchema]`
3. Register with `@DataLoaders.register(key="driver_name")`
4. Implement `async load() -> DataFrame`

**Schema introspection**: `DriverSchemaRegistry` loads schemas from registered loaders.

### Adding Validators

1. Create validator inheriting `ConstraintValidator`
2. Register with `@Validators.register(key="name", stage="pre-merge|post-merge")`
3. Implement `validate(entity) -> ConstraintViolation | None`

**Stages**:
- `pre-merge`: Before combining with parent data
- `post-merge`: After foreign key joins

### Adding Output Formats

1. Create dispatcher inheriting `Dispatcher`
2. Register with `@Dispatchers.register(key="format")`
3. Implement `dispatch(entities) -> None`

### Adding Ingesters

1. Create directory `ingesters/<name>/`
2. Implement `Ingester` protocol with `validate()` and `ingest()`
3. Register with `@Ingesters.register(key="<name>")`
4. Auto-discovered at startup via `IngesterRegistry.discover()`

---

## Architectural Constraints

### Three-Tier Identity System

**Critical Principle**: All relationships use local `system_id` values.

1. **`system_id`** - Local sequential identity (1, 2, 3...)
   - Always present, standardized column name
   - Used for ALL foreign key relationships
   
2. **`keys`** - Business keys for deduplication
   - Optional list of column names
   - Used in reconciliation and FK joins
   
3. **`public_id`** - Target schema identity
   - Dual purpose: column name + holds mapped external IDs
   - Required for: fixed entities, entities with FK children

**FK Resolution**: Child FK column name = parent's `public_id`, FK values = parent's `system_id`.

### Layer Boundary Rules

1. **API Models**:
   - Raw configuration with `${ENV_VARS}`
   - Never perform resolution
   
2. **Mappers**:
   - Single responsibility: API ↔ Core translation
   - ONLY layer that resolves environment variables
   
3. **Core Models**:
   - Always fully resolved
   - Never see directives or placeholders

### Immutability Requirements

Configuration processing functions must prevent mutations:
```python
def resolve_references(data: dict) -> dict:
    data = copy.deepcopy(data)  # Prevent mutations
    # ... process
    return data
```

**Reason**: Multiple components may hold references to same configuration. Mutations cause unpredictable side effects.

### Asynchronous Constraints

- Data loaders are async (database I/O)
- Backend services mix sync/async (check signatures)
- Tests use `@pytest.mark.asyncio` for async functions

---

## Integration Contracts

### API Layer Contract

**Endpoint Pattern**:
```
GET    /api/v1/{resource}           # List/query
GET    /api/v1/{resource}/{id}      # Get one
POST   /api/v1/{resource}           # Create
PUT    /api/v1/{resource}/{id}      # Update
DELETE /api/v1/{resource}/{id}      # Delete
POST   /api/v1/{resource}/{action}  # Action verb
```

**Response Format**:
```json
{
  "data": {...},          // Success payload
  "error": "message",     // Error message (if failed)
  "meta": {               // Optional metadata
    "timestamp": "...",
    "version": "..."
  }
}
```

### Core Interface Contract

**Configuration Requirements**:
- Valid `metadata.type: 'shapeshifter-project'`
- All entities have defined `type`
- No circular dependencies
- All referenced entities exist

**Execution Contract**:
```python
project = ShapeShiftProject.from_file("config.yml")
normalizer = ShapeShifter(project)
await normalizer.normalize()  # Returns processed entities
normalizer.store(target="output.xlsx", mode="xlsx")
```

### Mapper Resolution Contract

**Environment Variable Resolution**:
- Input: `{"host": "${DB_HOST}"}`
- Output: `{"host": "localhost"}`
- Fallback: Raise error if variable undefined

**Directive Resolution**:
- `@include:path.yml` → Embed file content
- `@value:expression` → Evaluate runtime value
- Applied recursively until no directives remain

---

## Performance Characteristics

### Caching Strategy

**3-Tier Cache Validation**:
1. **TTL Check** (300s): Timestamp comparison
2. **Version Check**: Project file modification time
3. **Hash Check**: xxhash.xxh64 of entity configuration

**Cache Invalidation**:
- Entity edit → Invalidate entity hash
- Project save → Invalidate version
- TTL expiry → Invalidate all

### Dependency Processing

**Topological Sort Complexity**: O(V + E) where V = entities, E = dependencies

**Processing Parallelization**: Not implemented (single-threaded pipeline)

**Memory Footprint**: All entities loaded into memory (pandas DataFrames)

---

## Deployment Considerations

### Single Worker Requirement

**Constraint**: Backend must run with single uvicorn worker.

**Reason**: In-memory state (singletons, caches) incompatible with multi-process workers.

**Production Alternative**: Use Redis/database for shared state if multiple workers needed.

### File System Requirements

- **Projects Directory**: YAML configurations
- **Backups Directory**: Automatic backups before edits
- **Output Directory**: Execution results
- **Logs Directory**: Application logs

### Database Connectivity

**Optional Dependencies**:
- PostgreSQL: Install `psycopg2-binary`
- MS Access: Requires Java JRE + UCanAccess (JDBC)

---

## Security Considerations

### Environment Variable Handling

- Never log resolved values (may contain credentials)
- Use `.pgpass` for PostgreSQL passwords
- Validate resolution before Core execution

### YAML Processing

- No arbitrary code execution (safe YAML parsing)
- Schema validation via Pydantic
- Backup before save (auto-rollback capability)

---

## Evolution and Stability

### Stable Interfaces

- Core pipeline phases (Extract → Filter → Link → Unnest → Translate → Store)
- Registry pattern for extensibility
- Three-tier identity system
- Layer boundary architecture (API → Mapper → Core)

### Planned Enhancements

- Row count estimation in validation
- FK data integrity checks (sample-based)
- Validation summary dashboard
- Incremental validation (debounced)

### Deprecated Patterns

- **Test Run feature**: Removed (redundant with validation + preview)
- **Multiple workers**: Not supported (in-memory state)

---

## References

For implementation details, configuration syntax, and usage instructions, consult:

- **CONFIGURATION_GUIDE.md** - Complete YAML reference
- **DEVELOPER_GUIDE.md** - Development setup and patterns
- **USER_GUIDE.md** - End-user workflows
- **REQUIREMENTS.md** - Feature specifications
- **TESTING_GUIDE.md** - Testing procedures
