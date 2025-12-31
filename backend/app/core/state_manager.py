"""Application-level state management for multi-user configuration editing."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger

from backend.app.models.project import Project, ProjectMetadata


@dataclass
class ConfigSession:
    """Represents an active editing session for a configuration file."""

    session_id: UUID
    project_name: str
    user_id: str | None  # Future: actual user identification
    loaded_at: datetime
    last_accessed: datetime
    modified: bool = False
    lock_holder: UUID | None = None  # Pessimistic lock (optional, not used yet)
    version: int = 1  # Optimistic concurrency control

    def touch(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now()


class ApplicationState:
    """
    Application-level singleton state (lifespan scope).

    Manages active editing sessions with Configuration objects (API model).
    This replaces ConfigStore usage for editing state management.
    """

    def __init__(self, config_dir: Path):
        self.projects_dir: Path = config_dir

        # Active configurations (editing state)
        self._active_projects: dict[str, Project] = {}
        self._active_project_name: str | None = None

        # Session management
        self._sessions: dict[UUID, ConfigSession] = {}
        self._sessions_by_project: dict[str, set[UUID]] = {}
        self._session_lock = asyncio.Lock()

        # Cache invalidation tracking
        self._project_versions: dict[str, int] = {}
        self._project_dirty: dict[str, bool] = {}

        # Cleanup task
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_sessions())
        logger.info("Application state manager started")

    async def stop(self) -> None:
        """Stop background tasks and cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Application state manager stopped")

    async def create_session(self, project_name: str, user_id: str | None = None) -> UUID:
        """Create a new editing session for a project file."""
        async with self._session_lock:
            session_id: UUID = uuid4()
            session = ConfigSession(
                session_id=session_id,
                project_name=project_name,
                user_id=user_id,
                loaded_at=datetime.now(),
                last_accessed=datetime.now(),
            )

            self._sessions[session_id] = session
            self._sessions_by_project.setdefault(project_name, set()).add(session_id)

            logger.info(f"Created session {session_id} for project '{project_name}'")
            return session_id

    async def get_session(self, session_id: UUID) -> ConfigSession | None:
        """Retrieve and touch a session."""
        async with self._session_lock:
            if session := self._sessions.get(session_id):
                session.touch()
                return session
            return None

    async def get_active_sessions(self, project_name: str) -> list[ConfigSession]:
        """Get all active sessions for a project file."""
        async with self._session_lock:
            session_ids = self._sessions_by_project.get(project_name, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    async def release_session(self, session_id: UUID) -> None:
        """Release a session and clear project if no other sessions."""
        async with self._session_lock:
            if session := self._sessions.pop(session_id, None):
                project_name: str = session.project_name

                # Remove from project index
                if project_name in self._sessions_by_project:
                    self._sessions_by_project[project_name].discard(session_id)

                    # Clear project from memory if no active sessions
                    if not self._sessions_by_project[project_name]:
                        del self._sessions_by_project[project_name]
                        self._active_projects.pop(project_name, None)
                        self._project_versions.pop(project_name, None)
                        self._project_dirty.pop(project_name, None)
                        logger.info(f"Cleared project '{project_name}' from memory (no active sessions)")

                logger.info(f"Released session {session_id}")

    def get_active_project(self) -> Project | None:
        """Get the currently active configuration being edited."""
        if self._active_project_name:
            return self._active_projects.get(self._active_project_name)
        return None

    def get_project(self, name: str) -> Project | None:
        """Get a specific configuration from active editing sessions."""
        return self._active_projects.get(name)

    def set_active_project(self, project: Project) -> None:
        """
        Set/update the active project.

        Args:
            project: Project to set as active
        """
        assert project.metadata, "Project metadata missing"

        name: str = project.metadata.name
        self._active_projects[name] = project
        self._active_project_name = name
        self._project_versions[name] = self._project_versions.get(name, 0) + 1
        self._project_dirty[name] = True
        logger.debug(f"Set active project: {name} (version {self._project_versions[name]})")

    def mark_saved(self, name: str) -> None:
        """Mark a project as saved (no unsaved changes)."""
        if name in self._project_dirty:
            self._project_dirty[name] = False
            logger.debug(f"Marked project '{name}' as saved")

    def is_dirty(self, name: str) -> bool:
        """Check if project has unsaved changes."""
        return self._project_dirty.get(name, False)

    def get_version(self, name: str) -> int:
        """Get project version for cache invalidation."""
        return self._project_versions.get(name, 0)

    async def _cleanup_stale_sessions(self) -> None:
        """Periodically cleanup inactive sessions (30min timeout)."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                stale_threshold: float = datetime.now().timestamp() - 1800  # 30 minutes
                stale_sessions = []

                async with self._session_lock:
                    for session_id, session in self._sessions.items():
                        if session.last_accessed.timestamp() < stale_threshold:
                            stale_sessions.append(session_id)

                for session_id in stale_sessions:
                    await self.release_session(session_id)
                    logger.info(f"Cleaned up stale session {session_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Error in session cleanup: {e}")


# Global instance (initialized in lifespan)
_app_state: ApplicationState | None = None  # pylint: disable=invalid-name


def get_app_state() -> ApplicationState:
    """Get the application state singleton."""
    if _app_state is None:
        raise RuntimeError("Application state not initialized. Call init_app_state() first.")
    return _app_state


def init_app_state(projects_dir: Path) -> ApplicationState:
    """Initialize application state (called in lifespan)."""
    global _app_state  # pylint: disable=global-statement
    _app_state = ApplicationState(projects_dir)
    return _app_state


class ApplicationStateManager:
    """Helper methods for accessing possibly uninitialized ApplicationState."""

    def get_app_state(self) -> ApplicationState:
        """Get ApplicationState, raising error if not initialized."""
        app_state: ApplicationState = get_app_state()
        return app_state

    def get(self, name: str) -> Project | None:
        """Load active project from ApplicationState if available."""
        with contextlib.suppress(RuntimeError):
            if not get_app_state():
                return None
            project: Project | None = get_app_state().get_project(name)
            if project:
                logger.debug(f"Loading active project '{name}' from ApplicationState")
                return project
        return None

    def get_active(self) -> Project | None:
        with contextlib.suppress(RuntimeError):

            if get_app_state():
                return get_app_state().get_active_project()

        return None

    def update(self, project: Project) -> None:
        """Update active project in ApplicationState if initialized."""
        with contextlib.suppress(RuntimeError):

            if not project.metadata:
                return

            if not get_app_state():
                return

            app_state: ApplicationState = get_app_state()

            if app_state.get_project(project.metadata.name):
                app_state.set_active_project(project)
                app_state.mark_saved(project.metadata.name)
                logger.debug(f"Updated ApplicationState for '{project.metadata.name}'")

    def activate(self, project: Project, name: str | None = None) -> None:
        """Set active project in ApplicationState if initialized."""
        name = name or (project.metadata.name if project.metadata else None)
        if not name:
            raise ValueError("Project name is required to activate project.")
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            app_state.set_active_project(project)
            app_state.mark_saved(name)  # Freshly loaded is not dirty
            logger.info(f"Activated project '{name}' for editing")

    def get_active_metadata(self) -> ProjectMetadata:
        with contextlib.suppress(RuntimeError):

            active_project: Project | None = self.get_active()

            if active_project and active_project.metadata:
                return active_project.metadata

        return ProjectMetadata(
            name="", description="", created_at=0, modified_at=0, entity_count=0, version=None, file_path=None, is_valid=True
        )

    @staticmethod
    def is_dirty(name: str) -> bool:
        """Check if project is dirty in ApplicationState if initialized."""
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            return app_state.is_dirty(name)
        return False


_app_state_manager: ApplicationStateManager | None = None  # pylint: disable=invalid-name


def get_app_state_manager() -> ApplicationStateManager:
    """Get the application state singleton."""
    global _app_state_manager  # pylint: disable=global-statement
    if _app_state_manager is None:
        _app_state_manager = ApplicationStateManager()
    return _app_state_manager
