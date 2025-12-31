"""
API Dependencies

Provides dependency injection functions for FastAPI endpoints.
"""

from typing import Annotated, Generator
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException

from backend.app import services
from backend.app.core.config import settings
from backend.app.core.state_manager import ApplicationState, ConfigSession, get_app_state


def get_data_source_service() -> Generator[services.DataSourceService, None, None]:
    """
    Get DataSourceService instance.

    Creates service for managing global data source files.
    Used as FastAPI dependency for data source endpoints.
    """
    service = services.DataSourceService(settings.PROJECTS_DIR)
    try:
        yield service
    finally:
        # Cleanup if needed (connection pool cleanup in future)
        pass


def get_schema_service() -> Generator[services.SchemaIntrospectionService, None, None]:
    """
    Get SchemaIntrospectionService instance.

    Creates service with current configuration.
    Used as FastAPI dependency for schema introspection endpoints.
    """
    service = services.SchemaIntrospectionService(settings.PROJECTS_DIR)
    try:
        yield service
    finally:
        # Cleanup if needed (cache cleanup in future)
        pass


# ============================================================================
# Session Management Dependencies
# ============================================================================


async def get_session_id(
    x_session_id: Annotated[str | None, Header()] = None,
    session_id: Annotated[str | None, Cookie()] = None,
) -> UUID | None:
    """Extract session ID from header or cookie."""
    session_str: str | None = x_session_id or session_id
    if session_str:
        try:
            return UUID(session_str)
        except ValueError as exc:
            raise HTTPException(400, "Invalid session ID format") from exc
    return None


async def get_current_session(
    session_id: Annotated[UUID | None, Depends(get_session_id)],
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
) -> ConfigSession | None:
    """Get current editing session (optional)."""
    if session_id:
        session: ConfigSession | None = await app_state.get_session(session_id)
        if not session:
            raise HTTPException(404, f"Session {session_id} not found or expired")
        return session
    return None


async def require_session(
    session: Annotated[ConfigSession | None, Depends(get_current_session)],
) -> ConfigSession:
    """Require an active session."""
    if not session:
        raise HTTPException(401, "No active session. Call POST /api/v1/sessions first.")
    return session
