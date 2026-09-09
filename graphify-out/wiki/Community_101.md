# Community 101

> 19 nodes · cohesion 0.15

## Key Concepts

- **Path** (9 connections) — `backend/app/services/project/file_manager.py`
- **.save_project_file()** (8 connections) — `backend/app/services/project/file_manager.py`
- **.save_data_source_file()** (7 connections) — `backend/app/services/project/file_manager.py`
- **._get_project_upload_dir()** (6 connections) — `backend/app/services/project/file_manager.py`
- **._sanitize_filename()** (6 connections) — `backend/app/services/project/file_manager.py`
- **ProjectFileInfo** (6 connections) — `backend/app/services/project/file_manager.py`
- **.list_project_files()** (5 connections) — `backend/app/services/project/file_manager.py`
- **UploadFile** (4 connections) — `backend/app/services/project/file_manager.py`
- **.list_data_source_files()** (4 connections) — `backend/app/services/project/file_manager.py`
- **.__init__()** (3 connections) — `backend/app/services/project/file_manager.py`
- **._to_public_path()** (3 connections) — `backend/app/services/project/file_manager.py`
- **Initialize file manager.          Args:             projects_root: Base director** (1 connections) — `backend/app/services/project/file_manager.py`
- **Get upload directory for a project.          Returns the project's directory whe** (1 connections) — `backend/app/services/project/file_manager.py`
- **Convert absolute path to public relative path for API responses.          This i** (1 connections) — `backend/app/services/project/file_manager.py`
- **Sanitize uploaded filename to prevent path traversal.          Args:** (1 connections) — `backend/app/services/project/file_manager.py`
- **List files stored under a project's uploads directory.          Args:** (1 connections) — `backend/app/services/project/file_manager.py`
- **Save an uploaded file into the project's uploads directory.          Args:** (1 connections) — `backend/app/services/project/file_manager.py`
- **List files available for data source configuration.          Args:             e** (1 connections) — `backend/app/services/project/file_manager.py`
- **Save an uploaded file into the global data directory (global data source).** (1 connections) — `backend/app/services/project/file_manager.py`

## Relationships

- [[Community 1]] (11 shared connections)
- [[Community 10]] (5 shared connections)
- [[Community 0]] (3 shared connections)

## Source Files

- `backend/app/services/project/file_manager.py`

## Audit Trail

- EXTRACTED: 63 (91%)
- INFERRED: 6 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*