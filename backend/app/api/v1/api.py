"""API v1 router configuration."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    data_sources,
    entities,
    execute,
    health,
    ingesters,
    logs,
    materialization,
    preview,
    projects,
    query,
    reconciliation,
    schema,
    sessions,
    suggestions,
    tasks,
    validation,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(entities.router, tags=["entities"])
api_router.include_router(validation.router, tags=["validation"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(data_sources.router, tags=["data-sources"])
api_router.include_router(schema.router, tags=["schema"])
api_router.include_router(query.router, tags=["query"])
api_router.include_router(suggestions.router, tags=["suggestions"])
api_router.include_router(preview.router, tags=["preview"])
api_router.include_router(reconciliation.router, tags=["reconciliation"])
api_router.include_router(execute.router, tags=["execute"])
api_router.include_router(materialization.router, tags=["materialization"])
api_router.include_router(ingesters.router, prefix="/ingesters", tags=["ingesters"])
api_router.include_router(logs.router, tags=["logs"])
