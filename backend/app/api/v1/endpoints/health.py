"""Health check endpoint."""

from datetime import UTC, datetime

from app.core.config import settings
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    timestamp: datetime
    configurations_dir: str
    backups_dir: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns application status and configuration information.
    """
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(UTC),
        configurations_dir=str(settings.CONFIGURATIONS_DIR),
        backups_dir=str(settings.BACKUPS_DIR),
    )
