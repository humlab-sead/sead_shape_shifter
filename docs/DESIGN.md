# Shape Shifter - Design

## Purpose

This document describes the architecture and design of Shape Shifter: how the system is structured, how its major components interact, which design decisions shape the code, and what constraints and tradeoffs operators and contributors need to understand. It is the primary entry point for anyone working on the codebase.

## Audience and Scope

Written for developers and maintainers who need to understand how the system is organized, how to extend it, and what boundaries must not be crossed. Local setup and contributor workflow belong in [DEVELOPMENT.md](DEVELOPMENT.md). Deployment procedures belong in [OPERATIONS.md](OPERATIONS.md).

---

## System Context and Boundaries

Shape Shifter is a data transformation system that harmonizes heterogeneous input data into a target schema through declarative YAML configuration. It is used primarily to prepare archaeological research data for import into the SEAD Clearinghouse.

**In scope:** project configuration management, data extraction, transformation pipeline, validation, output dispatch, and the editor UI.

**Out of scope:** the SEAD Clearinghouse itself, the SIMS identity management service, the OpenRefine reconciliation service, and the source databases. These are external systems that Shape Shifter integrates with but does not own.

**External integrations:**

| System | Direction | Protocol | Purpose |
|--------|-----------|----------|---------|
| SEAD databases (PostgreSQL / MS Access) | Inbound | SQL | Source data for extraction |
| CSV / Excel files | Inbound | File I/O | Source data for extraction |
| SIMS (`sead_authority_service`) | Outbound | HTTP | Identity resolution and change detection |
| OpenRefine reconciliation service | Outbound | HTTP | FK candidate suggestions |
| Output files (Excel, CSV) or DB | Outbound | File I/O / SQL | Dispatch results |

---

## High-Level Architecture

Shape Shifter is a monorepo with three loosely-coupled layers served as a single container in production:

```
┌────────────────────────────────────────────────┐
│              Web Browser                       │
│  Frontend (Vue 3 + Vuetify + Pinia)            │
│  Configuration editor • Validation • Preview   │
└─────────────────────┬──────────────────────────┘
                      │ REST/JSON (/api/v1)
┌─────────────────────┴──────────────────────────┐
│  Backend (FastAPI)                             │
│  API Layer • Services • Mappers                │
├────────────────────────────────────────────────┤
│  Core (src/)                                   │
│  Pipeline • Loaders • Validators • Dispatchers │
└─────────────────────┬──────────────────────────┘
                      │
          ┌───────────┴──────────┐
          │ File system          │  YAML projects, logs, output, backups
          │ Source databases     │  PostgreSQL, SQLite, MS Access
          └──────────────────────┘
```

The backend serves the built Vue frontend as static files, so the deployed artifact is a single container on port 8012.

---

## Components and Responsibilities

### Core (`src/`)

Owns the transformation pipeline. Takes a resolved project configuration and produces processed entity DataFrames.

- **Pipeline phases** (in order): Extract → Filter → Link → Unnest → Translate → Store
- **Orchestrator**: `ShapeShifter` in `src/normalizer.py` using `ProcessState`
- **Entity types**: `sql`, `csv`, `xlsx`, `fixed`, `merged`
- **Loaders** (`src/loaders/`): pluggable async data source connectors registered via `@DataLoaders.register`
- **Validators** (`src/validators/`): constraint checks (cardinality, FK integrity, functional dependencies) registered via `@Validators.register`
- **Dispatchers** (`src/dispatch.py`): output format handlers registered via `@Dispatchers.register`
- **Specifications** (`src/specifications/`): project-level structural validation (DAG, references, identity)

Core has no dependency on FastAPI or Pydantic API models. It operates entirely on resolved Python data structures.

### Backend (`backend/app/`)

Exposes Core capabilities as a REST API and manages the project editing lifecycle.

- **Routers** (`api/v1/endpoints/`): thin HTTP layer; one module per resource
- **Services** (`services/`): business logic — project CRUD, validation orchestration, preview, schema introspection, task management
- **Mappers** (`mappers/`): translate between API models and Core models; the only layer that resolves environment variables and directives
- **Models** (`models/`): Pydantic v2 schemas for request/response validation; always hold raw `${ENV_VARS}` and `@directives`
- **Clients** (`clients/`): async `httpx` wrappers for SIMS and reconciliation services
- **`ApplicationState`** (`core/state_manager.py`): lifespan-scoped singleton managing active editing sessions (project objects in memory)

### Frontend (`frontend/src/`)

A Vue 3 SPA built with Vuetify and Pinia.

- **Stores** (`stores/`): Pinia state for projects, entities, validation, sessions
- **Composables** (`composables/`): reusable logic for validation, entity preview, debouncing
- **API layer** (`api/`): Axios client modules per resource; no API calls in components
- **Key UI components**: Monaco-based YAML editor, entity form editor, dependency graph, validation panel, schema explorer

---

## Key Flows and Interactions

See [DIAGRAMS.md](DIAGRAMS.md) for detailed sequence and state diagrams for each flow.

### Project load  →  [sequence diagram](DIAGRAMS.md#15-project-load--sequence)

```
User selects project
  ↓
Frontend: GET /api/v1/projects/{name}
  ↓
Backend: ProjectMapper.to_api_config()
  ├─ Read YAML from disk
  ├─ Preserve ${ENV_VARS} and @directives unchanged
  └─ Return API model (unresolved)
  ↓
Frontend: Store in Pinia (projectStore)
  ↓
Frontend: Render entity list and editor
```

### Entity preview  →  [sequence diagram](DIAGRAMS.md#16-entity-preview--sequence)

```
User edits entity in Monaco
  ↓
Frontend: Debounced 300 ms
  ↓
Backend: POST /api/v1/preview
  ├─ Check 3-tier cache (TTL / project version / entity xxhash)
  ├─ [MISS] ProjectMapper.to_core()  ←  resolve env vars + directives
  ├─ [MISS] Core: ShapeShifter.preview(entity, limit)
  └─ Return preview rows
  ↓
Frontend: Update split-view grid
```

### Validation  →  [sequence diagram](DIAGRAMS.md#17-validation--sequence)

```
User clicks "Check Project"
  ↓
Backend: POST /api/v1/validate → ValidationService
  ├─ Structural validation
  │   ├─ YAML schema, required fields
  │   ├─ Entity references (no missing deps)
  │   └─ DAG cycle detection
  ├─ Constraint validation
  │   ├─ FK definitions and cardinality
  │   └─ Functional dependencies
  └─ Data validation (optional, sample rows)
      └─ Column existence, FK values
  ↓
Frontend: ValidationResult grouped by severity (error / warning / info)
```

### Execution  →  [sequence diagram](DIAGRAMS.md#18-execution--sequence)

```
User clicks "Execute"
  ↓
Backend: POST /api/v1/execute
  ↓
ProjectMapper.to_core()  ←  full env var + directive resolution
  ↓
Core: ShapeShifter.normalize()
  ├─ ProcessState: Topological sort (DAG → ordered list)
  └─ For each entity (dependency order):
      ├─ If type == "merged":
      │   ├─ Collect branch DataFrames (already processed)
      │   ├─ Inject {entity}_branch discriminator column
      │   ├─ Propagate sparse FK columns ({source}_id → system_id, pd.NA for others)
      │   ├─ Concatenate (union of columns, null-fill branch-only columns)
      │   └─ Apply post-merge: extra_columns, foreign_keys, drop_duplicates, columns
      └─ Otherwise (standard entity):
          Extract → Filter → Link → Unnest → Translate
  ↓
Store via Dispatcher (Excel / CSV / database)
  ↓
Frontend: Show completion status
```

### Project save  →  [sequence diagram](DIAGRAMS.md#19-project-save--sequence)

```
User saves
  ↓
Backend: PUT /api/v1/projects/{name}
  ├─ Check session version (optimistic concurrency)
  ├─ [CONFLICT] Return 409 → user must refresh
  ├─ ProjectMapper.to_core_dict()  ←  preserve @directives, ${ENV_VARS}
  ├─ Write timestamped backup to BACKUPS_DIR
  └─ Write project YAML to PROJECTS_DIR
  ↓
Frontend: Project saved
```

---

## Data and Persistence Design

**Project files**: all project state is stored as YAML files in the configured `PROJECTS_DIR`. There is no database for project metadata. The file system is the source of truth.

**Editing state**: `ApplicationState` holds active `Project` objects (API-layer models) in memory during editing. On save the mapper serializes back to YAML, preserving directives. A timestamped backup is written to `BACKUPS_DIR` before every save.

**Shared reference data**: `GLOBAL_DATA_DIR` and `GLOBAL_DATA_SOURCE_DIR` hold shared files that multiple projects can reference via `@include:` or `@load:` directives.

**No cross-request database**: there is no Redis, no relational store for sessions, and no persistent cache. Cache state is per-process and lost on restart.

**Output**: execution results are written to `OUTPUT_DIR`. These are ephemeral; no retention policy is applied automatically.

---

## Cross-Cutting Concerns

### Layer boundary and environment variable resolution

The three-layer boundary (API → Mapper → Core) is the central architectural constraint. API models always carry raw `${ENV_VARS}` and `@directives`. Mappers are the only code that calls `resolve_config_env_vars()`. Core models always receive fully resolved values. Violating this boundary causes silent credential leaks in API responses or unresolved placeholders reaching the pipeline.

### Three-tier identity system

All FK relationships use local `system_id` values (sequential integers assigned during pipeline processing), not external IDs. `keys` are business keys for deduplication. `public_id` is the target schema column name and also carries mapped external IDs after reconciliation. Child FK column name = parent's `public_id`; FK values = parent's `system_id` values.

### Caching

The backend uses a three-tier in-process cache for entity previews: TTL (300 s), project file modification time, and xxhash of entity configuration. Cache is invalidated on entity edit, project save, or TTL expiry. Because the cache is in-process, the backend must run with a single Uvicorn worker.

### Logging

Loguru is used throughout. All modules import `from loguru import logger`. The backend configures log file rotation (10 MB), retention (30 days), and compression at startup via `Settings`. Correlation IDs (set by `CorrelationMiddleware` from the `X-Correlation-ID` request header or generated as a UUID prefix) are propagated via a `ContextVar` so all log messages for a single request share the same ID.

### Error handling

Domain exceptions in `backend/app/exceptions.py` carry a human-readable message, contextual tips (`error_tips.py`), and a `recoverable` flag. The exception hierarchy (`DomainException → DataIntegrityError / DependencyError / ValidationError / ResourceError`) is mapped to HTTP status codes at the API boundary. Core exceptions flow upward and are caught at the service or router level. The frontend receives structured JSON error responses for consistent display.

### Authentication and authorization

There is currently no authentication or user identity model. The API is assumed to be accessible only within a trusted network or behind a reverse proxy. `ApplicationState` has a placeholder `user_id` field for future use. Sessions track a `lock_holder` UUID for optimistic concurrency at the entity level, but no user identity is enforced.

### Security

- YAML is parsed with safe loaders (no arbitrary code execution).
- Database credentials are resolved from environment variables at the mapper boundary; they are never logged or included in API responses.
- PostgreSQL passwords use `.pgpass` rather than environment variables where possible.
- CORS is restricted by origin allowlist (`ALLOWED_ORIGINS`) and a regex for DevTunnels/GitHub preview environments. Production deployments should narrow `ALLOWED_ORIGINS`.
- File uploads are accepted up to 100 MB (multipart limit).

### Asynchronous execution

Data loaders are async (database I/O). Backend services mix sync and async; check signatures before adding `await`. Tests use `@pytest.mark.asyncio`. The JVM (for UCanAccess MS Access support) is initialized once at startup; JPype does not allow JVM restart.

---

## Constraints and Assumptions

- **Single Uvicorn worker**: mandatory while ApplicationState and the preview cache are in-process singletons. Multiple workers require shared external state (Redis or database) first.
- **No built-in TLS**: TLS termination is expected upstream.
- **No real-time collaboration**: projects are not locked on open; concurrent edits by multiple users on the same project will produce last-write-wins behavior.
- **Memory-bound processing**: all entity DataFrames are loaded into memory. Very large source datasets may exhaust available RAM.
- **Java required at runtime**: MS Access support requires `default-jre-headless` (included in the production Docker image).
- **File system access**: the backend requires read/write access to `PROJECTS_DIR`, `BACKUPS_DIR`, `OUTPUT_DIR`, and `LOG_DIR`.

---

## Design Decisions and Tradeoffs

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| Mapper-only resolution | Prevents env vars from leaking into API responses or persisted YAML | All API→Core paths must go through the mapper; skipping it is a silent bug |
| In-memory ApplicationState | Simple, no external dependencies | Single-worker constraint; state lost on restart |
| YAML as sole project store | Human-readable, version-control-friendly, no DB required | No concurrent write safety; large projects can be slow to parse |
| Registry pattern for loaders/validators/dispatchers | Runtime extensibility without modifying the orchestrator | Registration must happen at import time; missed imports cause silent omissions |
| `system_id` as the universal FK value | Stable local key unaffected by source-system IDs | External IDs must be mapped separately via `public_id` and reconciliation |
| Single container (frontend + backend) | Simplified deployment; no separate static asset server | Frontend rebuild required to change any Vite build-time variable |
| Merged entity sparse FK columns | Gives downstream consumers typed paths to each branch without synthetic keys | Sparse `pd.NA` columns appear in all merged rows for branches that don't apply |

---

## Known Limitations and Technical Debt

- **No concurrent write safety**: simultaneous saves to the same project from multiple browser tabs or users will silently overwrite each other. Optimistic locking at the entity level is partially designed but not fully enforced.
- **No streaming or incremental processing**: the full entity DataFrame is materialized in memory before any downstream step runs.
- **Validation does not sample full data by default**: data validators run on preview-row counts unless explicitly configured otherwise; large datasets may have issues that only appear at full scale.
- **No automated cleanup of output and backup directories**: these grow unbounded; operators must prune manually.
- **CORS allowlist includes hardcoded DevTunnels hostnames**: these should be moved to runtime configuration.
- **FK suggestions are disabled by default** (`ENABLE_FK_SUGGESTIONS: false`): the reconciliation service integration is experimental.

---

## Related Documents

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) — complete YAML project configuration reference
- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, contributor workflow, and common commands
- [TESTING.md](TESTING.md) — test strategy, levels, and repository-specific testing guidance
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, CI/CD, rollback, and observability
- [DIAGRAMS.md](DIAGRAMS.md) — component architecture, sequence diagrams (project load, preview, validation, execution, save), state diagrams (entity editing, cache, validation result), and other visual design artifacts
- [USER_GUIDE.md](USER_GUIDE.md) — end-user documentation for the editor UI
- API reference: `http://localhost:8012/api/v1/docs` (Swagger) or `/api/v1/redoc` when running locally
