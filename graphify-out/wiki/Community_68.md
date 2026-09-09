# Community 68

> 33 nodes · cohesion 0.08

## Key Concepts

- **ApplicationState** (56 connections) — `backend/app/core/state_manager.py`
- **Exception** (14 connections) — `backend/app/main.py`
- **state_manager.py** (12 connections) — `backend/app/core/state_manager.py`
- **main.py** (11 connections) — `backend/app/main.py`
- **CorrelationMiddleware** (9 connections) — `backend/app/middleware/correlation.py`
- **init_app_state()** (6 connections) — `backend/app/core/state_manager.py`
- **lifespan()** (6 connections) — `backend/app/main.py`
- **global_exception_handler()** (5 connections) — `backend/app/main.py`
- **Path** (4 connections) — `backend/app/core/state_manager.py`
- **ShapeShifterCoreError** (4 connections) — `src/exceptions.py`
- **Request** (3 connections) — `backend/app/main.py`
- **JSONResponse** (3 connections) — `backend/app/main.py`
- **serve_spa()** (3 connections) — `backend/app/main.py`
- **correlation.py** (3 connections) — `backend/app/middleware/correlation.py`
- **.dispatch()** (3 connections) — `backend/app/middleware/correlation.py`
- **.__init__()** (2 connections) — `backend/app/core/state_manager.py`
- **.stop()** (2 connections) — `backend/app/core/state_manager.py`
- **root()** (2 connections) — `backend/app/main.py`
- **Application-level state management for multi-user configuration editing.** (1 connections) — `backend/app/core/state_manager.py`
- **Application-level singleton state (lifespan scope).      Manages active editing** (1 connections) — `backend/app/core/state_manager.py`
- **Stop background tasks and cleanup.** (1 connections) — `backend/app/core/state_manager.py`
- **Initialize application state (called in lifespan).** (1 connections) — `backend/app/core/state_manager.py`
- **FastAPI application entry point.** (1 connections) — `backend/app/main.py`
- **Application lifespan events.** (1 connections) — `backend/app/main.py`
- **Catch all unhandled exceptions and log with full traceback.      This is a last-** (1 connections) — `backend/app/main.py`
- *... and 8 more nodes in this community*

## Relationships

- [[Community 52]] (19 shared connections)
- [[Community 33]] (9 shared connections)
- [[Community 1]] (8 shared connections)
- [[Community 112]] (7 shared connections)
- [[Community 104]] (7 shared connections)
- [[Community 85]] (4 shared connections)
- [[Community 5]] (3 shared connections)
- [[Community 45]] (3 shared connections)
- [[Community 119]] (2 shared connections)
- [[Community 137]] (2 shared connections)
- [[Community 34]] (2 shared connections)
- [[Community 25]] (2 shared connections)

## Source Files

- `backend/app/core/state_manager.py`
- `backend/app/main.py`
- `backend/app/middleware/correlation.py`
- `src/exceptions.py`

## Audit Trail

- EXTRACTED: 117 (72%)
- INFERRED: 46 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*