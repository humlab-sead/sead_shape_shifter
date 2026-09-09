# Community 112

> 15 nodes · cohesion 0.14

## Key Concepts

- **.create_session()** (6 connections) — `backend/app/core/state_manager.py`
- **UUID** (6 connections) — `backend/app/core/state_manager.py`
- **.get_session()** (6 connections) — `backend/app/core/state_manager.py`
- **._find_existing_session()** (5 connections) — `backend/app/core/state_manager.py`
- **.touch()** (4 connections) — `backend/app/core/state_manager.py`
- **.release_session()** (4 connections) — `backend/app/core/state_manager.py`
- **._cleanup_stale_sessions()** (4 connections) — `backend/app/core/state_manager.py`
- **.start()** (3 connections) — `backend/app/core/state_manager.py`
- **Update last accessed timestamp.** (1 connections) — `backend/app/core/state_manager.py`
- **Start background tasks.** (1 connections) — `backend/app/core/state_manager.py`
- **Create a new editing session for a project file.          If a session already e** (1 connections) — `backend/app/core/state_manager.py`
- **Find an existing active session for the given project and user.** (1 connections) — `backend/app/core/state_manager.py`
- **Retrieve and touch a session.** (1 connections) — `backend/app/core/state_manager.py`
- **Release a session and clear project if no other sessions.** (1 connections) — `backend/app/core/state_manager.py`
- **Periodically cleanup inactive sessions (30min timeout).** (1 connections) — `backend/app/core/state_manager.py`

## Relationships

- [[Community 68]] (7 shared connections)
- [[Community 52]] (4 shared connections)
- [[Community 104]] (2 shared connections)
- [[Community 5]] (1 shared connections)
- [[Community 1]] (1 shared connections)

## Source Files

- `backend/app/core/state_manager.py`

## Audit Trail

- EXTRACTED: 43 (96%)
- INFERRED: 2 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*