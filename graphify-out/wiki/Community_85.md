# Community 85

> 25 nodes · cohesion 0.10

## Key Concepts

- **FastAPI** (30 connections) — `backend/app/main.py`
- **api.py** (23 connections) — `backend/app/api/v1/api.py`
- **columns.py** (7 connections) — `backend/app/api/v1/endpoints/columns.py`
- **directives.py** (7 connections) — `backend/app/api/v1/endpoints/directives.py`
- **health.py** (6 connections) — `backend/app/api/v1/endpoints/health.py`
- **logs.py** (6 connections) — `backend/app/api/v1/endpoints/logs.py`
- **download_logs()** (5 connections) — `backend/app/api/v1/endpoints/logs.py`
- **HealthResponse** (4 connections) — `backend/app/api/v1/endpoints/health.py`
- **help_docs.py** (4 connections) — `backend/app/api/v1/endpoints/help_docs.py`
- **get_logs()** (4 connections) — `backend/app/api/v1/endpoints/logs.py`
- **health_check()** (3 connections) — `backend/app/api/v1/endpoints/health.py`
- **get_help_doc()** (3 connections) — `backend/app/api/v1/endpoints/help_docs.py`
- **LogType** (2 connections) — `backend/app/api/v1/endpoints/logs.py`
- **API v1 router configuration.** (1 connections) — `backend/app/api/v1/api.py`
- **API endpoints for column introspection.** (1 connections) — `backend/app/api/v1/endpoints/columns.py`
- **API endpoints for @value directive validation.** (1 connections) — `backend/app/api/v1/endpoints/directives.py`
- **Health check endpoint.** (1 connections) — `backend/app/api/v1/endpoints/health.py`
- **Health check response model.** (1 connections) — `backend/app/api/v1/endpoints/health.py`
- **Health check endpoint.      Returns application status and configuration informa** (1 connections) — `backend/app/api/v1/endpoints/health.py`
- **PlainTextResponse** (1 connections) — `backend/app/api/v1/endpoints/help_docs.py`
- **API endpoints for markdown help documents used by the frontend.** (1 connections) — `backend/app/api/v1/endpoints/help_docs.py`
- **Return a markdown document used by the Help view.** (1 connections) — `backend/app/api/v1/endpoints/help_docs.py`
- **API endpoints for application logs.** (1 connections) — `backend/app/api/v1/endpoints/logs.py`
- **Fetch application logs.      Args:         log_type: Type of log file ('app' or** (1 connections) — `backend/app/api/v1/endpoints/logs.py`
- **Get download path for log file.      Args:         log_type: Type of log file ('** (1 connections) — `backend/app/api/v1/endpoints/logs.py`

## Relationships

- [[Community 13]] (5 shared connections)
- [[Community 68]] (4 shared connections)
- [[Community 52]] (3 shared connections)
- [[Community 89]] (3 shared connections)
- [[Community 1]] (3 shared connections)
- [[Community 3]] (2 shared connections)
- [[Community 75]] (2 shared connections)
- [[Community 15]] (2 shared connections)
- [[Community 39]] (2 shared connections)
- [[Community 37]] (2 shared connections)
- [[Community 79]] (2 shared connections)
- [[Community 45]] (2 shared connections)

## Source Files

- `backend/app/api/v1/api.py`
- `backend/app/api/v1/endpoints/columns.py`
- `backend/app/api/v1/endpoints/directives.py`
- `backend/app/api/v1/endpoints/health.py`
- `backend/app/api/v1/endpoints/help_docs.py`
- `backend/app/api/v1/endpoints/logs.py`
- `backend/app/main.py`

## Audit Trail

- EXTRACTED: 114 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*