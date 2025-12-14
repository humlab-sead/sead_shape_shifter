"""API v1 router configuration."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    configurations,
    data_sources,
    entities,
    health,
    preview,
    query,
    schema,
    suggestions,
    test_run,
    validation,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(configurations.router, tags=["configurations"])
api_router.include_router(entities.router, tags=["entities"])
api_router.include_router(validation.router, tags=["validation"])
api_router.include_router(data_sources.router, tags=["data-sources"])
api_router.include_router(schema.router, tags=["schema"])
api_router.include_router(query.router, tags=["query"])
api_router.include_router(suggestions.router, tags=["suggestions"])
api_router.include_router(preview.router, tags=["preview"])
api_router.include_router(test_run.router, tags=["test-run"])
