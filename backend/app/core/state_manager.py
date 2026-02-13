"""Application-level state management for multi-user configuration editing."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger

from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.project import Project, ProjectMetadata


@dataclass
class ProjectSession:
    """Represents an active editing session for a project."""

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

    Manages active editing sessions with Project objects (API model).
    This replaces ConfigStore usage for editing state management.
    """

    def __init__(self, projects_dir: Path):
        self.projects_dir: Path = projects_dir

        # Active projects (editing state)
        self._active_projects: dict[str, Project] = {}
        self._active_project_name: str | None = None

        # Session management
        self._sessions: dict[UUID, ProjectSession] = {}
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
        """
        Create a new editing session for a project file.

        If a session already exists for the same user/project combination,
        reuses the existing session instead of creating a new one to prevent
        orphaned sessions on page refresh.
        """
        async with self._session_lock:
            # Check if there's already an active session for this user/project
            existing_session = await self._find_existing_session(project_name, user_id)
            if existing_session:
                logger.info(
                    f"Reusing existing session {existing_session.session_id} for project '{project_name}' "
                    f"(user: {user_id or 'anonymous'})"
                )
                existing_session.touch()
                return existing_session.session_id

            session_id: UUID = uuid4()
            session = ProjectSession(
                session_id=session_id,
                project_name=project_name,
                user_id=user_id,
                loaded_at=datetime.now(),
                last_accessed=datetime.now(),
            )

            self._sessions[session_id] = session
            self._sessions_by_project.setdefault(project_name, set()).add(session_id)

            logger.info(f"Created new session {session_id} for project '{project_name}' (user: {user_id or 'anonymous'})")
            return session_id

    async def _find_existing_session(self, project_name: str, user_id: str | None) -> ProjectSession | None:
        """Find an existing active session for the given project and user."""
        project_sessions = self._sessions_by_project.get(project_name, set())

        for session_id in project_sessions:
            session = self._sessions.get(session_id)
            if session and session.user_id == user_id:
                return session

        return None

    async def get_session(self, session_id: UUID) -> ProjectSession | None:
        """Retrieve and touch a session."""
        async with self._session_lock:
            if session := self._sessions.get(session_id):
                session.touch()
                return session
            return None

    async def get_active_sessions(self, project_name: str) -> list[ProjectSession]:
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
        """Get the currently active project being edited."""
        if self._active_project_name:
            return self._active_projects.get(self._active_project_name)
        return None

    def get_project(self, name: str) -> Project | None:
        """Get a specific project from active editing sessions."""
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

    def increment_version(self, name: str) -> int:
        """Increment and return the version number for a project."""
        self._project_versions[name] = self._project_versions.get(name, 0) + 1
        logger.debug(f"Incremented version for '{name}' to {self._project_versions[name]}")
        return self._project_versions[name]

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
        corr = get_correlation_id()
        with contextlib.suppress(RuntimeError):
            if not get_app_state():
                return None
            project: Project | None = get_app_state().get_project(name)
            if project:
                entity_count = len(project.entities or {})
                entity_names = sorted((project.entities or {}).keys())
                logger.info(
                    "[{}] state.get: project='{}' HIT entities={} names={}",
                    corr,
                    name,
                    entity_count,
                    entity_names,
                )
                return project
            else:
                logger.debug("[{}] state.get: project='{}' MISS", corr, name)
        return None

    def get_active(self) -> Project | None:
        with contextlib.suppress(RuntimeError):

            if get_app_state():
                return get_app_state().get_active_project()

        return None

    def update(self, project: Project) -> None:
        """Update project if it's already known, otherwise ignore."""
        corr = get_correlation_id()
        with contextlib.suppress(RuntimeError):

            if not project.metadata:
                return

            if not get_app_state():
                return

            app_state: ApplicationState = get_app_state()
            name = project.metadata.name

            # Only update if the project is already in memory
            if name in app_state._active_projects:
                entity_count: int = len(project.entities or {})
                entity_names: list[str] = sorted((project.entities or {}).keys())
                app_state._active_projects[name] = project
                new_version: int = app_state.increment_version(name)
                app_state.mark_saved(name)
                logger.info(
                    "[{}] state.update: project='{}' version={} entities={} names={}",
                    corr,
                    name,
                    new_version,
                    entity_count,
                    entity_names,
                )
            else:
                logger.warning(
                    "[{}] state.update: project='{}' NOT in active_projects, skipping cache update",
                    corr,
                    name,
                )

    def update_version(self, name: str) -> None:
        """Update version tracking for a project (for cache invalidation)."""
        with contextlib.suppress(RuntimeError):
            if get_app_state():
                get_app_state().increment_version(name)

    def activate(self, project: Project, name: str | None = None) -> None:
        """Set active project in ApplicationState if initialized."""
        name = name or (project.metadata.name if project.metadata else None)
        if not name:
            raise ValueError("Project name is required to activate project.")
        corr = get_correlation_id()
        entity_count = len(project.entities or {})
        entity_names = sorted((project.entities or {}).keys())
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            app_state.set_active_project(project)
            app_state.mark_saved(name)  # Freshly loaded is not dirty
            logger.info(
                "[{}] state.activate: project='{}' entities={} names={}",
                corr,
                name,
                entity_count,
                entity_names,
            )

    def invalidate(self, name: str) -> None:
        """
        Invalidate (clear) a project from cache.

        Forces the next load_project() call to reload from disk.
        Useful when the YAML file has been modified externally.

        Args:
            name: Project name to invalidate
        """
        corr = get_correlation_id()
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            removed_project = app_state._active_projects.pop(name, None)
            old_version = app_state._project_versions.pop(name, None)
            app_state._project_dirty.pop(name, None)

            old_entities = sorted((removed_project.entities or {}).keys()) if removed_project else []
            logger.info(
                "[{}] state.invalidate: project='{}' was_cached={} old_version={} old_entities={}",
                corr,
                name,
                removed_project is not None,
                old_version,
                old_entities,
            )

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
