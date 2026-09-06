"""Tests for authenticated session ownership."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.app.api.dependencies import get_current_session
from backend.app.core.state_manager import ProjectSession


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
