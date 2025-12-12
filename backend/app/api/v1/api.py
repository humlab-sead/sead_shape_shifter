"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import configurations, entities, health, validation

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(configurations.router, tags=["configurations"])
api_router.include_router(entities.router, tags=["entities"])
api_router.include_router(validation.router, tags=["validation"])
