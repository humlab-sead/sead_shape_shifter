# State Management Analysis & Fixes

**Date:** February 2026  
**Branch:** `make-state-management-robust`  
**Status:** Phase 0 + Phase 1 implemented, all tests passing

---

## Bug Reports

### Bug 1: Entity Loss on Sequential Creation

**Symptom:** Creating 3 entities sequentially results in only the last entity persisting to disk.

**Root Cause:** Two compounding issues:

1. **Shared mutable reference from cache** — `load_project()` returned the cached `Project` object directly. When two concurrent requests both called `load_project()`, they received the **same Python object**. Each caller mutated it independently (adding their entity), but only the last `save_project()` call persisted, silently overwriting the other's changes.

2. **No serialization of mutations** — `add_entity_by_name()` performed a non-atomic read-modify-write cycle (`load → mutate → save`) with no locking. Under concurrent requests (e.g., rapid UI clicks), interleaved execution caused lost updates.

### Bug 2: Ghost Entities After Delete + Recreate

**Symptom:** Deleting a project and recreating it with the same name shows entities from the deleted project.

**Root Cause:** Incomplete cache invalidation on project deletion:

- `ApplicationState._active_projects` was cleared ✓
- `ShapeShiftCache` (entity DataFrame cache) was **NOT** cleared ✗
- `ShapeShiftProjectCache` (ShapeShiftProject instance cache) was **NOT** cleared ✗
- Frontend `entityStore` was **NOT** reset on project delete/switch ✗

When a new project was created with the same name, stale cached data from the deleted project was served.

---

## State Architecture

The system has **5 state layers**, all keyed by project name:

| Layer | Location | Contents | Scope |
|-------|----------|----------|-------|
| **Disk** | `projects/*.yml` | YAML source of truth | Persistent |
| **ApplicationState** | `_active_projects` dict | `Project` (API model) | Server lifetime |
| **ShapeShiftCache** | `_dataframes` dict | Entity DataFrames (TTL+version+hash) | Server lifetime |
| **ShapeShiftProjectCache** | `_cache` dict | `ShapeShiftProject` (Core model) | Server lifetime |
| **Pinia Stores** | `entityStore`, `projectStore` | Frontend reactive state | Browser session |

### Data Flow

```
Browser (Pinia) → HTTP → FastAPI Endpoint → ProjectService
                                                ↓
                                    ApplicationState (cache)
                                                ↓
                                         YAML file (disk)
```

---

## Phase 0: Diagnostic Logging

### 0.1 Correlation ID Middleware

**Files:** `backend/app/middleware/__init__.py`, `backend/app/middleware/correlation.py`, `backend/app/main.py`

- `ContextVar[str]` stores a short UUID (8 chars) per HTTP request
- Reads `X-Correlation-ID` header or auto-generates
- `get_correlation_id()` helper available to all downstream code
- Response includes `X-Correlation-ID` header for client-side correlation

### 0.2 ProjectService Operation Logging

**File:** `backend/app/services/project_service.py`

Every state-mutating operation logs with structured format:
```
[{corr_id}] {operation}: project='{name}' {details}
```

Operations instrumented:
- `load_project` — source (CACHE vs DISK), entity count, entity names
- `save_project` — entity count, entity names, verification result
- `add_entity_by_name` — BEFORE/AFTER entity count and names
- `update_entity_by_name` — current entities, entity being updated
- `delete_entity_by_name` — BEFORE/AFTER entity count and names
- `delete_project` — lock acquisition, cache invalidation
- `create_project` — defensive cache invalidation

### 0.3 ApplicationStateManager Logging

**File:** `backend/app/core/state_manager.py`

Methods instrumented: `get()`, `update()`, `activate()`, `invalidate()`

Each logs correlation ID, entity count, entity names, and version numbers.

### 0.4 Cache Logging

**File:** `backend/app/utils/caches.py`

- Removed `logger.disable(__name__)` that was blanket-disabling all cache logging
- New `invalidate_project()` methods log correlation ID and entry counts

### 0.5 Frontend Diagnostic Logging

**Files:** `frontend/src/stores/entity.ts`, `frontend/src/stores/project.ts`

`logState()` helper outputs to `console.info` with:
- Action name (before/after pattern)
- Current project name
- Entity count and names
- Timestamp

### 0.6 Serialization Verification

**File:** `backend/app/mappers/project_mapper.py`

`to_core_dict()` now verifies entity count survives serialization (input vs output), logging an error on mismatch.

---

## Phase 1: Immediate Fixes

### 1.1 Copy-on-Read (Mutation-Through-Reference Fix)

**File:** `backend/app/services/project_service.py` — `load_project()`

**Before:**
```python
cached_project = self.state.get(name)
if cached_project:
    return cached_project  # Returns SAME object to all callers
```

**After:**
```python
cached_project = self.state.get(name)
if cached_project:
    return cached_project.model_copy(deep=True)  # Each caller gets independent copy
```

Uses Pydantic v2's `model_copy(deep=True)` for proper deep cloning.

### 1.2 Per-Project Mutation Locking

**File:** `backend/app/services/project_service.py`

**Infrastructure:**
```python
class ProjectService:
    _project_locks: dict[str, threading.Lock] = {}  # Class-level
    _locks_lock: threading.Lock = threading.Lock()   # Protects the dict

    @classmethod
    def _get_lock(cls, project_name: str) -> threading.Lock:
        with cls._locks_lock:
            if project_name not in cls._project_locks:
                cls._project_locks[project_name] = threading.Lock()
            return cls._project_locks[project_name]
```

**Design decisions:**
- `threading.Lock` (not `asyncio.Lock`) because service methods are synchronous even though called from async endpoints
- Per-project granularity so different projects don't block each other
- Class-level storage so lock survives across service instantiations

**Methods locked:**
- `add_entity_by_name()` — entire read-modify-write cycle
- `update_entity_by_name()` — entire read-modify-write cycle
- `delete_entity_by_name()` — entire read-modify-write cycle
- `delete_project()` — file deletion + cache invalidation

### 1.3 Complete Cache Invalidation on Delete

**Files:** `backend/app/services/project_service.py`, `backend/app/utils/caches.py`

**New method:** `ProjectService._invalidate_all_caches(project_name, corr)`

Clears ALL three server-side caches:
1. `ApplicationState._active_projects` (via `state.invalidate()`)
2. `ShapeShiftCache._dataframes` + `_metadata` (via new `cache.invalidate_project()`)
3. `ShapeShiftProjectCache._cache` + `_versions` (via new `project_cache.invalidate_project()`)

**Called from:**
- `delete_project()` — after file deletion
- `create_project()` — defensively before creation (handles delete+recreate race)

**New cache methods:**
- `ShapeShiftCache.invalidate_project(name)` — iterates `_metadata` to find all entries matching project name
- `ShapeShiftProjectCache.invalidate_project(name)` — removes from `_cache` and `_versions` dicts

### 1.4 Save Verification (Read-Back)

**File:** `backend/app/services/project_service.py` — `_verify_save()`

After every `save_project()`, reads the YAML file back and compares entity counts/names. Logs error on mismatch. This is a paranoia check to catch silent data loss in the serialization pipeline.

### 1.5 Frontend Store Reset on Project Switch/Delete

**File:** `frontend/src/stores/project.ts`

| Operation | Action |
|-----------|--------|
| `selectProject(name)` | Resets entity store if switching to different project |
| `createProject(data)` | Resets entity store before API call |
| `deleteProject(name)` | Resets entity store before AND after API delete |

This prevents stale frontend state from a previously selected (or deleted) project appearing when a new project is loaded.

**Circular import note:** `entity.ts` already imports `useProjectStore`, and `project.ts` now imports `useEntityStore`. This is safe because Pinia resolves cross-store references lazily inside `defineStore` callbacks.

---

## Test Results

All existing tests pass with zero regressions:

| Suite | Result |
|-------|--------|
| Core (`pytest tests`) | All pass (1 skip) |
| Backend (`pytest backend/tests`) | All pass (4 skips) |
| Frontend (`vitest`) | 542 tests pass |
| TypeScript (`vue-tsc`) | Only pre-existing errors |

---

## Future Phases (Not Yet Implemented)

### Phase 2: Structural Improvements
- Centralized `CacheCoordinator` managing all cache layers
- Event-based state synchronization (publish/subscribe)
- Optimistic concurrency control with version vectors

### Phase 3: Frontend Robustness
- Staleness detection (version polling)
- Operation queue serialization (sequential entity creation)
- Retry with exponential backoff on conflict

### Phase 4: Observability
- Structured JSON logging with correlation IDs
- Metrics (cache hit rate, lock contention, save latency)
- Health check endpoint exposing cache statistics
