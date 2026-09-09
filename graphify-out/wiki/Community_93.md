# Community 93

> 22 nodes · cohesion 0.12

## Key Concepts

- **.get_dataframe()** (10 connections) — `backend/app/utils/caches.py`
- **TableConfig** (10 connections) — `backend/app/utils/caches.py`
- **TableStore** (9 connections) — `backend/app/utils/caches.py`
- **ShapeShiftProject** (9 connections) — `backend/app/utils/caches.py`
- **.get_dependencies()** (7 connections) — `backend/app/utils/caches.py`
- **.__init__()** (6 connections) — `backend/app/utils/caches.py`
- **.fetch_cached_entity_data()** (6 connections) — `backend/app/utils/caches.py`
- **.set_table_store()** (5 connections) — `backend/app/utils/caches.py`
- **.get_project()** (5 connections) — `backend/app/utils/caches.py`
- **._store_file_meta()** (4 connections) — `backend/app/utils/caches.py`
- **._generate_key()** (3 connections) — `backend/app/utils/caches.py`
- **._current_file_mtime()** (3 connections) — `backend/app/utils/caches.py`
- **Initialize cache with TTL in seconds (default 5 minutes).** (1 connections) — `backend/app/utils/caches.py`
- **Generate cache key from config and entity name.** (1 connections) — `backend/app/utils/caches.py`
- **Get cached DataFrame for entity with 3-tier validation.          Validation orde** (1 connections) — `backend/app/utils/caches.py`
- **Cache DataFrame for entity with metadata including entity hash.          Args:** (1 connections) — `backend/app/utils/caches.py`
- **Cache all entities from table_store individually with entity hashes.          Ar** (1 connections) — `backend/app/utils/caches.py`
- **Gather all cached dependencies for an entity with hash validation.          Args** (1 connections) — `backend/app/utils/caches.py`
- **Initialize ShapeShiftProject cache.** (1 connections) — `backend/app/utils/caches.py`
- **Return the on-disk mtime of a cached project's YAML file, or None if unavailable** (1 connections) — `backend/app/utils/caches.py`
- **Record file path and mtime from a freshly loaded API project.** (1 connections) — `backend/app/utils/caches.py`
- **Get ShapeShiftProject with caching and version tracking.          Uses Applicati** (1 connections) — `backend/app/utils/caches.py`

## Relationships

- [[Community 33]] (10 shared connections)
- [[Community 14]] (6 shared connections)
- [[Community 11]] (5 shared connections)
- [[Community 1]] (3 shared connections)
- [[Community 5]] (3 shared connections)
- [[Community 4]] (3 shared connections)
- [[Community 8]] (3 shared connections)

## Source Files

- `backend/app/utils/caches.py`

## Audit Trail

- EXTRACTED: 69 (79%)
- INFERRED: 18 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*