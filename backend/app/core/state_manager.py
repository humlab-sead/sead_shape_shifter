"""Application-level state management for multi-user configuration editing."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import A
from uuid import UUID, uuid4

from loguru import logger

import app
from backend.app.models.config import ConfigMetadata, Configuration


@dataclass
class ConfigSession:
    """Represents an active editing session for a configuration file."""

    session_id: UUID
    config_name: str
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
        self.config_dir: Path = config_dir

        # Active configurations (editing state)
        self._active_configs: dict[str, Configuration] = {}
        self._active_config_name: str | None = None

        # Session management
        self._sessions: dict[UUID, ConfigSession] = {}
        self._sessions_by_config: dict[str, set[UUID]] = {}
        self._session_lock = asyncio.Lock()

        # Cache invalidation tracking
        self._config_versions: dict[str, int] = {}
        self._config_dirty: dict[str, bool] = {}

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

    async def create_session(self, config_name: str, user_id: str | None = None) -> UUID:
        """Create a new editing session for a config file."""
        async with self._session_lock:
            session_id: UUID = uuid4()
            session = ConfigSession(
                session_id=session_id,
                config_name=config_name,
                user_id=user_id,
                loaded_at=datetime.now(),
                last_accessed=datetime.now(),
            )

            self._sessions[session_id] = session
            self._sessions_by_config.setdefault(config_name, set()).add(session_id)

            logger.info(f"Created session {session_id} for config '{config_name}'")
            return session_id

    async def get_session(self, session_id: UUID) -> ConfigSession | None:
        """Retrieve and touch a session."""
        async with self._session_lock:
            if session := self._sessions.get(session_id):
                session.touch()
                return session
            return None

    async def get_active_sessions(self, config_name: str) -> list[ConfigSession]:
        """Get all active sessions for a config file."""
        async with self._session_lock:
            session_ids = self._sessions_by_config.get(config_name, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    async def release_session(self, session_id: UUID) -> None:
        """Release a session and clear config if no other sessions."""
        async with self._session_lock:
            if session := self._sessions.pop(session_id, None):
                config_name: str = session.config_name

                # Remove from config index
                if config_name in self._sessions_by_config:
                    self._sessions_by_config[config_name].discard(session_id)

                    # Clear config from memory if no active sessions
                    if not self._sessions_by_config[config_name]:
                        del self._sessions_by_config[config_name]
                        self._active_configs.pop(config_name, None)
                        self._config_versions.pop(config_name, None)
                        self._config_dirty.pop(config_name, None)
                        logger.info(f"Cleared config '{config_name}' from memory (no active sessions)")

                logger.info(f"Released session {session_id}")

    def get_active_configuration(self) -> Configuration | None:
        """Get the currently active configuration being edited."""
        if self._active_config_name:
            return self._active_configs.get(self._active_config_name)
        return None

    def get_configuration(self, name: str) -> Configuration | None:
        """Get a specific configuration from active editing sessions."""
        return self._active_configs.get(name)

    def set_active_configuration(self, config: Configuration) -> None:
        """
        Set/update the active configuration.

        Args:
            config: Configuration to set as active
        """
        assert config.metadata, "Configuration metadata missing"

        name: str = config.metadata.name
        self._active_configs[name] = config
        self._active_config_name = name
        self._config_versions[name] = self._config_versions.get(name, 0) + 1
        self._config_dirty[name] = True
        logger.debug(f"Set active configuration: {name} (version {self._config_versions[name]})")

    def mark_saved(self, name: str) -> None:
        """Mark a configuration as saved (no unsaved changes)."""
        if name in self._config_dirty:
            self._config_dirty[name] = False
            logger.debug(f"Marked configuration '{name}' as saved")

    def is_dirty(self, name: str) -> bool:
        """Check if configuration has unsaved changes."""
        return self._config_dirty.get(name, False)

    def get_version(self, name: str) -> int:
        """Get configuration version for cache invalidation."""
        return self._config_versions.get(name, 0)

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


def init_app_state(config_dir: Path) -> ApplicationState:
    """Initialize application state (called in lifespan)."""
    global _app_state  # pylint: disable=global-statement
    _app_state = ApplicationState(config_dir)
    return _app_state


class ApplicationStateManager:
    """Helper methods for accessing possibly uninitialized ApplicationState."""

    def get(self, name: str) -> Configuration | None:
        """Load active configuration from ApplicationState if available."""
        try:
            if not get_app_state():
                return None
            config: Configuration | None = get_app_state().get_configuration(name)
            if config:
                logger.debug(f"Loading active configuration '{name}' from ApplicationState")
                return config
        except RuntimeError:
            # ApplicationState not initialized (e.g., in tests)
            return None

    def get_active(self) -> Configuration | None:
        with contextlib.suppress(RuntimeError):

            if get_app_state():
                return get_app_state().get_active_configuration()

        return None

    def update(self, config: Configuration) -> None:
        """Update active configuration in ApplicationState if initialized."""
        with contextlib.suppress(RuntimeError):

            if not config.metadata:
                return None

            if not get_app_state():
                return None

            app_state: ApplicationState = get_app_state()

            if app_state.get_configuration(config.metadata.name):
                app_state.set_active_configuration(config)
                app_state.mark_saved(config.metadata.name)
                logger.debug(f"Updated ApplicationState for '{config.metadata.name}'")

    def activate(self, config: Configuration, name: str | None = None) -> None:
        """Set active configuration in ApplicationState if initialized."""
        name = name or (config.metadata.name if config.metadata else None)
        if not name:
            raise ValueError("Configuration name is required to activate configuration.")
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            app_state.set_active_configuration(config)
            app_state.mark_saved(name)  # Freshly loaded is not dirty
            logger.info(f"Activated configuration '{name}' for editing")

    def get_active_metadata(self) -> ConfigMetadata:
        with contextlib.suppress(RuntimeError):

            active_config: Configuration | None = self.get_active()

            if active_config and active_config.metadata:
                return active_config.metadata

        return ConfigMetadata(
            name="", description="", created_at=0, modified_at=0, entity_count=0, version=None, file_path=None, is_valid=True
        )

    @staticmethod
    def is_dirty(name: str) -> bool:
        """Check if configuration is dirty in ApplicationState if initialized."""
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            return app_state.is_dirty(name)
        return False


_app_state_manager: ApplicationStateManager | None = None  # pylint: disable=invalid-name


def get_app_state_manager() -> ApplicationStateManager:
    """Get the application state singleton."""
    global _app_state_manager
    if _app_state_manager is None:
        _app_state_manager = ApplicationStateManager()
    return _app_state_manager
