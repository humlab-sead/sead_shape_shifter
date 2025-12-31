"""Session management endpoints."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from backend.app.api.dependencies import require_session
from backend.app.core.state_manager import ApplicationState, ProjectSession, get_app_state

router = APIRouter(prefix="/sessions")


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    project_name: str
    user_id: str | None = None


class SessionResponse(BaseModel):
    """Session information."""

    session_id: UUID
    project_name: str
    user_id: str | None
    loaded_at: str
    last_accessed: str
    modified: bool
    version: int
    concurrent_sessions: int  # How many others editing same file


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: SessionCreateRequest,
    response: Response,
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
) -> SessionResponse:
    """
    Create a new editing session for a configuration file.

    A session must be created before editing a configuration. The session ID
    is returned in the response and set as a cookie for convenience.

    Multiple users can have sessions for the same project, but
    optimistic concurrency control is used to prevent conflicts when saving.
    """

    # Verify project file exists
    project_path: Path = app_state.projects_dir / f"{request.project_name}.yml"
    if not project_path.exists():
        raise HTTPException(404, f"Project '{request.project_name}' not found")

    # Create session
    session_id: UUID = await app_state.create_session(request.project_name, request.user_id)
    session: ProjectSession | None = await app_state.get_session(session_id)

    if not session:
        raise HTTPException(500, "Failed to create session")

    # Load config into store (lazy loading)
    app_state.get_project(request.project_name)

    # Get concurrent session count
    active_sessions = await app_state.get_active_sessions(request.project_name)

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=str(session_id),
        httponly=True,
        samesite="lax",
        max_age=1800,  # 30 minutes
    )

    return SessionResponse(
        session_id=session.session_id,
        project_name=session.project_name,
        user_id=session.user_id,
        loaded_at=session.loaded_at.isoformat(),
        last_accessed=session.last_accessed.isoformat(),
        modified=session.modified,
        version=session.version,
        concurrent_sessions=len(active_sessions),
    )


@router.get("/current", response_model=SessionResponse)
async def get_current_session_info(
    session: Annotated[ProjectSession, Depends(require_session)],
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
) -> SessionResponse:
    """Get information about current session."""
    active_sessions = await app_state.get_active_sessions(session.project_name)

    return SessionResponse(
        session_id=session.session_id,
        project_name=session.project_name,
        user_id=session.user_id,
        loaded_at=session.loaded_at.isoformat(),
        last_accessed=session.last_accessed.isoformat(),
        modified=session.modified,
        version=session.version,
        concurrent_sessions=len(active_sessions),
    )


@router.delete("/current", status_code=204)
async def close_session(
    session: Annotated[ProjectSession, Depends(require_session)],
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
) -> None:
    """
    Close current editing session.

    This will release the session and unload the configuration from memory
    if no other active sessions exist for the same configuration file.
    """
    await app_state.release_session(session.session_id)


@router.get("/{project_name}/active", response_model=list[SessionResponse])
async def list_active_sessions(
    project_name: str,
    app_state: Annotated[ApplicationState, Depends(get_app_state)],
) -> list[SessionResponse]:
    """
    List all active sessions for a configuration file.

    Useful for detecting concurrent editing and coordinating between users.
    """
    sessions = await app_state.get_active_sessions(project_name)

    return [
        SessionResponse(
            session_id=s.session_id,
            project_name=s.project_name,
            user_id=s.user_id,
            loaded_at=s.loaded_at.isoformat(),
            last_accessed=s.last_accessed.isoformat(),
            modified=s.modified,
            version=s.version,
            concurrent_sessions=len(sessions),
        )
        for s in sessions
    ]
