"""Tests for authenticated session ownership."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from backend.app.api.dependencies import get_current_session
from backend.app.api.v1.endpoints.sessions import SessionCreateRequest, create_session
from backend.app.authorization.dependencies import require_authorized_session
from backend.app.authorization.models import Action, Grant, Principal, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.state_manager import ApplicationState, ProjectSession


def _session(user_id: str) -> ProjectSession:
    """Create a session for dependency tests."""
    now = datetime.now()
    return ProjectSession(
        session_id=uuid4(),
        project_name="project",
        user_id=user_id,
        loaded_at=now,
        last_accessed=now,
    )


def _principal(principal_id: str = "alice") -> Principal:
    """Create a principal for dependency tests."""
    return Principal(principal_id, "test", datetime.now(UTC))


@pytest.mark.asyncio
async def test_session_belongs_to_authenticated_user() -> None:
    """An authenticated user can use that user's session."""
    session = _session("alice")
    app_state = AsyncMock()
    app_state.get_session.return_value = session

    result = await get_current_session(session.session_id, app_state, "alice")

    assert result is session


@pytest.mark.asyncio
async def test_session_for_another_authenticated_user_is_rejected() -> None:
    """An authenticated user cannot use another user's session."""
    session = _session("alice")
    app_state = AsyncMock()
    app_state.get_session.return_value = session

    with pytest.raises(HTTPException) as exc_info:
        await get_current_session(session.session_id, app_state, "bob")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_session_requires_project_edit_access_and_records_principal(tmp_path) -> None:
    """Creating an editing session checks project edit access and stores the principal ID."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "shapeshifter.yml").write_text("metadata:\n  type: shapeshifter-project\nentities: {}\n", encoding="utf-8")
    app_state = ApplicationState(tmp_path)
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "editor", datetime.now(UTC), "admin"))

    result = await create_session(
        SessionCreateRequest(project_name="project", user_id="spoofed"),
        Response(),
        app_state,
        _principal(),
        AuthorizationService(repository),
    )

    assert result.project_name == "project"
    assert result.user_id == "alice"
    repository.close()


@pytest.mark.asyncio
async def test_authorized_session_requires_current_project_access(tmp_path) -> None:
    """A matching session owner still needs current project access."""
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project")
    repository.create_resource(resource)
    dependency = require_authorized_session(Action.EDIT)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(_session("alice"), _principal(), AuthorizationService(repository))

    assert exc_info.value.status_code == 404
    repository.close()
