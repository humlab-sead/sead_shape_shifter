"""Application-level state management for multi-user configuration editing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger

from src.configuration.provider import ConfigStore


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
    """Application-level singleton state (lifespan scope)."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_store = ConfigStore(config_directory=config_dir)

        # Session management
        self._sessions: dict[UUID, ConfigSession] = {}
        self._sessions_by_config: dict[str, set[UUID]] = {}
        self._session_lock = asyncio.Lock()

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
            session_id = uuid4()
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
        """Release a session and unload config if no other sessions."""
        async with self._session_lock:
            if session := self._sessions.pop(session_id, None):
                config_name = session.config_name

                # Remove from config index
                if config_name in self._sessions_by_config:
                    self._sessions_by_config[config_name].discard(session_id)

                    # Unload config if no active sessions
                    if not self._sessions_by_config[config_name]:
                        del self._sessions_by_config[config_name]
                        self.config_store.unload_config(config_name)
                        logger.info(f"Unloaded config '{config_name}' (no active sessions)")

                logger.info(f"Released session {session_id}")

    async def _cleanup_stale_sessions(self) -> None:
        """Periodically cleanup inactive sessions (30min timeout)."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                stale_threshold = datetime.now().timestamp() - 1800  # 30 minutes
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
