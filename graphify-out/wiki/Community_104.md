# Community 104

> 18 nodes · cohesion 0.12

## Key Concepts

- **get_app_state()** (17 connections) — `backend/app/core/state_manager.py`
- **.get()** (13 connections) — `backend/app/core/state_manager.py`
- **.is_dirty()** (6 connections) — `backend/app/core/state_manager.py`
- **.increment_version()** (5 connections) — `backend/app/core/state_manager.py`
- **.get_active_sessions()** (4 connections) — `backend/app/core/state_manager.py`
- **.get_project()** (4 connections) — `backend/app/core/state_manager.py`
- **.update_version()** (4 connections) — `backend/app/core/state_manager.py`
- **.get_version()** (3 connections) — `backend/app/core/state_manager.py`
- **Get the application state singleton.** (2 connections) — `backend/app/core/state_manager.py`
- **Get all active sessions for a project file.** (1 connections) — `backend/app/core/state_manager.py`
- **Get a specific project from active editing sessions.** (1 connections) — `backend/app/core/state_manager.py`
- **Check if project has unsaved changes.** (1 connections) — `backend/app/core/state_manager.py`
- **Get project version for cache invalidation.** (1 connections) — `backend/app/core/state_manager.py`
- **Increment and return the version number for a project.** (1 connections) — `backend/app/core/state_manager.py`
- **Get ApplicationState, raising error if not initialized.** (1 connections) — `backend/app/core/state_manager.py`
- **Load active project from ApplicationState if available.** (1 connections) — `backend/app/core/state_manager.py`
- **Update version tracking for a project (for cache invalidation).** (1 connections) — `backend/app/core/state_manager.py`
- **Check if project is dirty in ApplicationState if initialized.** (1 connections) — `backend/app/core/state_manager.py`

## Relationships

- [[Community 68]] (7 shared connections)
- [[Community 119]] (7 shared connections)
- [[Community 1]] (7 shared connections)
- [[Community 52]] (3 shared connections)
- [[Community 112]] (2 shared connections)
- [[Community 45]] (1 shared connections)
- [[Community 11]] (1 shared connections)
- [[Community 15]] (1 shared connections)

## Source Files

- `backend/app/core/state_manager.py`

## Audit Trail

- EXTRACTED: 67 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*