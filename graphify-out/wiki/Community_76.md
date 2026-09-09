# Community 76

> 29 nodes · cohesion 0.12

## Key Concepts

- **Path** (13 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.load_sidecar_data()** (12 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.get_sidecar_path()** (10 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Any** (7 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **._normalize_task_list_data()** (6 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.save_task_list()** (6 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.migrate_task_list()** (6 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.set_note()** (6 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.remove_note()** (6 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.load_task_list()** (5 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.load_notes()** (5 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.sidecar_exists()** (4 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **._normalize_notes_data()** (4 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **TaskList** (4 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.get_note()** (4 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **.delete_sidecar()** (4 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Migrate task list from main project file to sidecar file.      One-time migratio** (2 connections) — `backend/app/api/v1/endpoints/tasks.py`
- **Get the sidecar file path for a project file.          Args:             project** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Check if sidecar file exists for a project.          Args:             project_f** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Normalize task list data to the current server-side schema.          This centra** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Normalize notes data to a canonical entity -> note mapping.** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Load canonical sidecar content from disk.          Returns a dictionary containi** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Load task list from sidecar file if it exists.          Implements backward comp** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Load entity notes from the sidecar file if they exist.** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- **Save task list to sidecar file.          Args:             project_file_path: Pa** (1 connections) — `backend/app/services/task_list_sidecar_manager.py`
- *... and 4 more nodes in this community*

## Relationships

- [[Community 0]] (17 shared connections)
- [[Community 5]] (3 shared connections)

## Source Files

- `backend/app/api/v1/endpoints/tasks.py`
- `backend/app/services/task_list_sidecar_manager.py`

## Audit Trail

- EXTRACTED: 110 (95%)
- INFERRED: 6 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*