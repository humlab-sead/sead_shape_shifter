"""
API Dependencies

Provides dependency injection functions for FastAPI endpoints.
"""

from typing import Annotated, Generator
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request

from backend.app import services
from backend.app.core.config import settings
from backend.app.core.state_manager import ApplicationState, ProjectSession, get_app_state
from backend.app.services.project_service import get_project_service


def get_data_source_service() -> Generator[services.DataSourceService, None, None]:
    """
    Get DataSourceService instance.

    Creates service for managing global data source files.
    Used as FastAPI dependency for data source endpoints.
    """
    service = services.DataSourceService(settings.global_data_source_dir)
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
    service = services.SchemaIntrospectionService(settings.GLOBAL_DATA_SOURCE_DIR)
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


async def get_authenticated_user(request: Request) -> str | None:
    """Return the identity asserted by the trusted proxy, when proxy authentication is enabled."""
    return getattr(request.state, "authenticated_user", None)


async def get_current_session(
    session_id: Annotated[UUID | None, Depends(get_session_id)],
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
    authenticated_user: Annotated[str | None, Depends(get_authenticated_user)],
) -> ProjectSession | None:
    """Get current editing session (optional)."""
    if session_id:
        session: ProjectSession | None = await app_state.get_session(session_id)
        if not session:
            raise HTTPException(404, f"Session {session_id} not found or expired")
        if authenticated_user is not None and session.user_id != authenticated_user:
            raise HTTPException(403, "Session does not belong to the authenticated user")
        return session
    return None


async def require_session(
    session: Annotated[ProjectSession | None, Depends(get_current_session)],
) -> ProjectSession:
    """Require an active session."""
    if not session:
        raise HTTPException(401, "No active session. Call POST /api/v1/sessions first.")
    return session


# ============================================================================
# Active Project Dependencies
# ============================================================================


def get_active_project_locator() -> str | None:
    """Return the locator of the active project, or None when no project is loaded.

    The active project is application state rather than request input, so authorization for
    routes that act on it resolves the locator here instead of from a path or query parameter.
    """
    return get_project_service().get_active_project_metadata().name or None
