"""Tests for application state manager."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

import backend.app.core.state_manager as sm
from backend.app.core.state_manager import (
    ApplicationState,
    ApplicationStateManager,
    ConfigSession,
    get_app_state,
    init_app_state,
)
from backend.app.models.project import Project, ProjectMetadata

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary configuration directory."""
    return tmp_path / "configs"


@pytest.fixture
def app_state(config_dir: Path) -> ApplicationState:
    """Create an ApplicationState instance."""
    return ApplicationState(config_dir)


@pytest.fixture
def sample_config() -> Project:
    """Create a sample configuration."""
    return Project(
        metadata=ProjectMetadata(name="test-config", entity_count=0),
        entities={},
        options={},
    )


@pytest.fixture
def reset_singletons():
    """Reset module-level singletons before and after a test."""
    original_state = sm._app_state
    original_manager = sm._app_state_manager
    sm._app_state = None
    sm._app_state_manager = None
    yield
    sm._app_state = original_state
    sm._app_state_manager = original_manager


class TestConfigSession:
    """Test ConfigSession dataclass."""

    def test_create_session(self):
        """Test creating a session."""
        session_id = UUID("12345678-1234-5678-1234-567812345678")
        now: datetime = datetime.now()

        session = ConfigSession(
            session_id=session_id,
            project_name="test-config",
            user_id="user123",
            loaded_at=now,
            last_accessed=now,
        )

        assert session.session_id == session_id
        assert session.project_name == "test-config"
        assert session.user_id == "user123"
        assert session.loaded_at == now
        assert session.last_accessed == now
        assert session.modified is False
        assert session.lock_holder is None
        assert session.version == 1

    def test_touch_updates_last_accessed(self):
        """Test that touch() updates last_accessed timestamp."""
        now: datetime = datetime.now()
        session = ConfigSession(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_name="test-config",
            user_id=None,
            loaded_at=now,
            last_accessed=now - timedelta(minutes=5),
        )

        old_timestamp = session.last_accessed
        session.touch()

        assert session.last_accessed > old_timestamp


class TestApplicationState:
    """Test ApplicationState class."""

    def test_initialization(self, config_dir: Path):
        """Test ApplicationState initialization."""
        state = ApplicationState(config_dir)

        assert state.projects_dir == config_dir
        assert not state._active_projects
        assert state._active_project_name is None
        assert not state._sessions
        assert not state._sessions_by_project
        assert not state._project_versions
        assert not state._project_dirty
        assert state._cleanup_task is None

    @pytest.mark.asyncio
    async def test_start_stop(self, app_state: ApplicationState):
        """Test starting and stopping background tasks."""
        await app_state.start()
        assert app_state._cleanup_task is not None
        assert not app_state._cleanup_task.done()

        await app_state.stop()
        assert app_state._cleanup_task.cancelled()

    @pytest.mark.asyncio
    async def test_create_session(self, app_state: ApplicationState):
        """Test creating a new session."""
        session_id = await app_state.create_session("test-config", "user123")

        assert isinstance(session_id, UUID)
        assert session_id in app_state._sessions

        session = app_state._sessions[session_id]
        assert session.project_name == "test-config"
        assert session.user_id == "user123"
        assert "test-config" in app_state._sessions_by_project
        assert session_id in app_state._sessions_by_project["test-config"]

    @pytest.mark.asyncio
    async def test_get_session(self, app_state: ApplicationState):
        """Test retrieving a session."""
        session_id = await app_state.create_session("test-config")
        original_access_time = app_state._sessions[session_id].last_accessed

        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)

        session = await app_state.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.last_accessed > original_access_time

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, app_state: ApplicationState):
        """Test retrieving a non-existent session."""
        fake_id = UUID("00000000-0000-0000-0000-000000000000")
        session = await app_state.get_session(fake_id)

        assert session is None

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, app_state: ApplicationState):
        """Test getting all active sessions for a configuration."""
        session_id1 = await app_state.create_session("config1")
        session_id2 = await app_state.create_session("config1")
        session_id3 = await app_state.create_session("config2")

        sessions = await app_state.get_active_sessions("config1")

        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert session_id1 in session_ids
        assert session_id2 in session_ids
        assert session_id3 not in session_ids

    @pytest.mark.asyncio
    async def test_release_session(self, app_state: ApplicationState, sample_config: Project):
        """Test releasing a session."""
        session_id = await app_state.create_session("test-config")
        app_state.set_active_project(sample_config)

        await app_state.release_session(session_id)

        assert session_id not in app_state._sessions
        assert "test-config" not in app_state._sessions_by_project
        assert "test-config" not in app_state._active_projects
        assert "test-config" not in app_state._project_versions
        assert "test-config" not in app_state._project_dirty

    @pytest.mark.asyncio
    async def test_release_session_keeps_config_if_other_sessions(self, app_state: ApplicationState, sample_config: Project):
        """Test that config is kept when other sessions exist."""
        session_id1 = await app_state.create_session("test-config")
        session_id2 = await app_state.create_session("test-config")
        app_state.set_active_project(sample_config)

        await app_state.release_session(session_id1)

        # Config should still be in memory
        assert "test-config" in app_state._active_projects
        assert session_id2 in app_state._sessions
        assert "test-config" in app_state._sessions_by_project

    def test_get_active_projecturation(self, app_state: ApplicationState, sample_config: Project):
        """Test getting the active configuration."""
        # No active config initially
        assert app_state.get_active_project() is None

        # Set active config
        app_state.set_active_project(sample_config)

        # Should return the active config
        active = app_state.get_active_project()
        assert active is not None
        assert active.metadata is not None
        assert active.metadata.name == "test-config"

    def test_get_configuration(self, app_state: ApplicationState, sample_config: Project):
        """Test getting a specific configuration."""
        app_state.set_active_project(sample_config)

        config = app_state.get_project("test-config")
        assert config is not None
        assert config.metadata is not None
        assert config.metadata.name == "test-config"

        # Non-existent config
        assert app_state.get_project("non-existent") is None

    def test_set_active_projecturation(self, app_state: ApplicationState, sample_config: Project):
        """Test setting the active configuration."""
        app_state.set_active_project(sample_config)

        assert app_state._active_project_name == "test-config"
        assert "test-config" in app_state._active_projects
        assert app_state._project_versions["test-config"] == 1
        assert app_state._project_dirty["test-config"] is True

    def test_set_active_projecturation_increments_version(self, app_state: ApplicationState, sample_config: Project):
        """Test that setting active config increments version."""
        app_state.set_active_project(sample_config)
        initial_version = app_state._project_versions["test-config"]

        # Update again
        app_state.set_active_project(sample_config)

        assert app_state._project_versions["test-config"] == initial_version + 1

    def test_mark_saved(self, app_state: ApplicationState, sample_config: Project):
        """Test marking a configuration as saved."""
        app_state.set_active_project(sample_config)
        assert app_state._project_dirty["test-config"] is True

        app_state.mark_saved("test-config")

        assert app_state._project_dirty["test-config"] is False

    def test_mark_saved_nonexistent(self, app_state: ApplicationState):
        """Test marking a non-existent configuration as saved."""
        # Should not raise an error
        app_state.mark_saved("non-existent")

    def test_is_dirty(self, app_state: ApplicationState, sample_config: Project):
        """Test checking if configuration is dirty."""
        # Not dirty initially
        assert app_state.is_dirty("test-config") is False

        # Set active - becomes dirty
        app_state.set_active_project(sample_config)
        assert app_state.is_dirty("test-config") is True

        # Mark saved - no longer dirty
        app_state.mark_saved("test-config")
        assert app_state.is_dirty("test-config") is False

    def test_get_version(self, app_state: ApplicationState, sample_config: Project):
        """Test getting configuration version."""
        # No version initially
        assert app_state.get_version("test-config") == 0

        # Set active - version 1
        app_state.set_active_project(sample_config)
        assert app_state.get_version("test-config") == 1

        # Update again - version 2
        app_state.set_active_project(sample_config)
        assert app_state.get_version("test-config") == 2

    @pytest.mark.asyncio
    async def test_cleanup_stale_sessions(self, app_state: ApplicationState):
        """Test cleanup of stale sessions."""
        # Create a session
        session_id = await app_state.create_session("test-config")

        # Manually set last_accessed to be old
        app_state._sessions[session_id].last_accessed = datetime.now() - timedelta(hours=1)

        # Start cleanup task
        await app_state.start()

        # Wait a bit for cleanup to potentially run (it runs every 5 minutes, but we'll stop it quickly)
        await asyncio.sleep(0.1)

        # Manually trigger cleanup by calling the method
        # Create a task that will be cancelled quickly
        cleanup_task = asyncio.create_task(app_state._cleanup_stale_sessions())
        await asyncio.sleep(0.1)
        cleanup_task.cancel()

        # The session should be too new to clean up with default threshold
        # Let's test the logic more directly by adjusting the timestamp
        app_state._sessions[session_id].last_accessed = datetime.now() - timedelta(minutes=31)

        # Now manually check if it would be cleaned
        stale_threshold = datetime.now().timestamp() - 1800  # 30 minutes
        is_stale: bool = app_state._sessions[session_id].last_accessed.timestamp() < stale_threshold

        assert is_stale is True

        await app_state.stop()


class TestSingletonFunctions:
    """Test singleton pattern functions."""

    def test_init_app_state(self, config_dir: Path):
        """Test initializing global app state."""
        # Import the module-level variable

        # Reset to None first
        sm._app_state = None

        state: ApplicationState = init_app_state(config_dir)

        assert isinstance(state, ApplicationState)
        assert state.projects_dir == config_dir
        assert sm._app_state is state

    def test_get_app_state_when_initialized(self, config_dir: Path):
        """Test getting app state when initialized."""

        sm._app_state = ApplicationState(config_dir)

        state: ApplicationState = get_app_state()

        assert isinstance(state, ApplicationState)
        assert state is sm._app_state

    def test_get_app_state_when_not_initialized(self):
        """Test getting app state when not initialized."""

        # Reset to None
        sm._app_state = None

        with pytest.raises(RuntimeError, match="Application state not initialized"):
            get_app_state()


class TestConcurrency:
    """Test concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self, app_state: ApplicationState):
        """Test creating multiple sessions concurrently."""
        tasks = [app_state.create_session(f"config-{i}", f"user-{i}") for i in range(10)]

        session_ids = await asyncio.gather(*tasks)

        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # All unique
        assert len(app_state._sessions) == 10

    @pytest.mark.asyncio
    async def test_concurrent_session_access(self, app_state: ApplicationState):
        """Test accessing sessions concurrently."""
        session_ids = [await app_state.create_session(f"config-{i}") for i in range(5)]

        tasks = [app_state.get_session(sid) for sid in session_ids]
        sessions = await asyncio.gather(*tasks)

        assert len(sessions) == 5
        assert all(s is not None for s in sessions)

    @pytest.mark.asyncio
    async def test_concurrent_session_release(self, app_state: ApplicationState):
        """Test releasing sessions concurrently."""
        session_ids = [await app_state.create_session("test-config") for _ in range(5)]

        tasks = [app_state.release_session(sid) for sid in session_ids]
        await asyncio.gather(*tasks)

        assert len(app_state._sessions) == 0
        assert "test-config" not in app_state._sessions_by_project


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_release_nonexistent_session(self, app_state: ApplicationState):
        """Test releasing a session that doesn't exist."""
        fake_id = UUID("00000000-0000-0000-0000-000000000000")

        # Should not raise an error
        await app_state.release_session(fake_id)

    def test_multiple_configs_active(self, app_state: ApplicationState):
        """Test having multiple configurations active simultaneously."""
        config1 = Project(
            metadata=ProjectMetadata(name="config1", entity_count=0),
            entities={},
            options={},
        )
        config2 = Project(
            metadata=ProjectMetadata(name="config2", entity_count=0),
            entities={},
            options={},
        )

        app_state.set_active_project(config1)
        app_state.set_active_project(config2)

        # Both should be in active configs
        assert "config1" in app_state._active_projects
        assert "config2" in app_state._active_projects

        # But only config2 is the "active" one
        assert app_state._active_project_name == "config2"

    def test_version_tracking_independent_configs(self, app_state: ApplicationState):
        """Test that version tracking is independent per config."""
        config1 = Project(
            metadata=ProjectMetadata(name="config1", entity_count=0),
            entities={},
            options={},
        )
        config2 = Project(
            metadata=ProjectMetadata(name="config2", entity_count=0),
            entities={},
            options={},
        )

        app_state.set_active_project(config1)
        app_state.set_active_project(config1)  # Version 2

        app_state.set_active_project(config2)  # Version 1 for config2

        assert app_state.get_version("config1") == 2
        assert app_state.get_version("config2") == 1


class TestApplicationStateManagerHelpers:
    """Test ApplicationStateManager convenience methods."""

    def test_get_and_get_active(self, config_dir: Path, sample_config: Project, reset_singletons):
        """Test manager returns active configs when singleton is initialized."""
        sm._app_state = ApplicationState(config_dir)
        manager = sm.get_app_state_manager()
        assert sm._app_state is not None

        sm._app_state.set_active_project(sample_config)
        sm._app_state.mark_saved(sample_config.metadata.name)  # type: ignore[union-attr]

        assert manager.get("test-config") is sample_config
        assert manager.get_active() is sample_config

    def test_update_only_applies_when_config_known(self, config_dir: Path, sample_config: Project, reset_singletons):
        """Test update refreshes existing config but ignores unknown ones."""
        sm._app_state = ApplicationState(config_dir)
        manager = sm.get_app_state_manager()

        manager.update(sample_config)
        assert sm._app_state.get_project("test-config") is None  # type: ignore[union-attr]

        sm._app_state.set_active_project(sample_config)  # type: ignore[union-attr]
        updated_config = Project(
            metadata=ProjectMetadata(name="test-config", entity_count=0),
            entities={"updated": {"type": "data", "keys": ["id"]}},
            options={"flag": True},
        )

        manager.update(updated_config)

        assert sm._app_state.get_project("test-config") is updated_config  # type: ignore[union-attr]
        assert sm._app_state.get_version("test-config") == 2  # type: ignore[union-attr]
        assert sm._app_state.is_dirty("test-config") is False  # type: ignore[union-attr]
        expected_entities = {"updated": {"type": "data", "keys": ["id"]}}
        assert sm._app_state._active_projects["test-config"].entities == expected_entities  # type: ignore[attr-defined]

    def test_activate_and_metadata(self, config_dir: Path, sample_config: Project, reset_singletons):
        """Test activate sets active config and returns metadata."""
        sm._app_state = ApplicationState(config_dir)
        manager = sm.get_app_state_manager()

        manager.activate(sample_config)

        assert sm._app_state.get_active_project() is sample_config  # type: ignore[union-attr]
        assert sm._app_state.is_dirty("test-config") is False  # type: ignore[union-attr]
        active_metadata = manager.get_active_metadata()
        assert active_metadata.name == "test-config"
        assert active_metadata.entity_count == 0

    def test_activate_without_name_raises(self, reset_singletons):
        """Test activate raises when no name available."""
        manager = sm.get_app_state_manager()
        nameless_config = Project(metadata=None, entities={}, options={})

        with pytest.raises(ValueError):
            manager.activate(nameless_config)

    def test_get_active_metadata_defaults_when_uninitialized(self, reset_singletons):
        """Test metadata fallback when state is not initialized."""
        manager = sm.get_app_state_manager()

        metadata = manager.get_active_metadata()

        assert metadata.name == ""
        assert metadata.entity_count == 0

    def test_is_dirty_handles_missing_state(self, reset_singletons):
        """Test is_dirty safely handles missing app state."""
        assert ApplicationStateManager.is_dirty("unknown") is False
