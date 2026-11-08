"""Retain read-only foreign-key inspection snapshots for bounded paging."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

import pandas as pd
from loguru import logger

from backend.app.models.integrity_troubleshooter import (
    IntegrityStatus,
    IntegrityTroubleshootKeys,
    IntegrityTroubleshootRelationship,
)
from src.model import ForeignKeyConfig

INTEGRITY_TROUBLESHOOTER_CONTEXT_TTL: timedelta = timedelta(minutes=15)
"""Fixed lifetime of one retained integrity inspection."""

INTEGRITY_TROUBLESHOOTER_CLEANUP_INTERVAL_SECONDS: float = 60.0
"""How often the background task removes expired inspections."""

ContextLookupState = Literal["found", "expired", "unavailable"]
"""Outcome of looking up one inspection for one owner."""


@dataclass(frozen=True)
class IntegrityTroubleshooterSnapshot:
    """Data needed to page one read-only integrity inspection."""

    status: IntegrityStatus
    reason: str
    message: str
    relationship: IntegrityTroubleshootRelationship
    configured_keys: IntegrityTroubleshootKeys
    recorded_orphan_count: int
    current_orphan_count: int
    local_rows: pd.DataFrame
    foreign_key: ForeignKeyConfig
    unmatched_keys: frozenset[tuple[Any, ...]]
    sorted_keys: tuple[tuple[Any, ...], ...]
    row_counts: dict[tuple[Any, ...], int]
    columns: tuple[str, ...]
    columns_truncated: bool


@dataclass(frozen=True)
class IntegrityTroubleshooterContext:
    """One owner-scoped inspection snapshot with a fixed expiry."""

    context_id: str
    owner_principal_id: str
    project_locator: str
    snapshot: IntegrityTroubleshooterSnapshot
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Return True when ``now`` has reached the fixed expiry."""
        return now >= self.expires_at


@dataclass(frozen=True)
class IntegrityTroubleshooterContextLookup:
    """Result of looking up an inspection for one owner."""

    state: ContextLookupState
    context: IntegrityTroubleshooterContext | None = None


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class IntegrityTroubleshooterContextStore:
    """Hold temporary integrity inspection snapshots for one application process."""

    def __init__(
        self,
        *,
        ttl: timedelta = INTEGRITY_TROUBLESHOOTER_CONTEXT_TTL,
        clock: Callable[[], datetime] | None = None,
        cleanup_interval_seconds: float = INTEGRITY_TROUBLESHOOTER_CLEANUP_INTERVAL_SECONDS,
    ) -> None:
        """Configure the snapshot lifetime, clock, and cleanup interval."""
        self._ttl: timedelta = ttl
        self._clock: Callable[[], datetime] = clock if clock is not None else _utc_now
        self._cleanup_interval_seconds: float = cleanup_interval_seconds
        self._contexts: dict[str, IntegrityTroubleshooterContext] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    @property
    def ttl(self) -> timedelta:
        """Return the fixed snapshot lifetime."""
        return self._ttl

    async def start(self) -> None:
        """Start the background task that removes expired inspections."""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._remove_expired_periodically())
        logger.info("Integrity troubleshooter context store started")

    async def stop(self) -> None:
        """Stop background cleanup and release every retained inspection."""
        cleanup_task: asyncio.Task[None] | None = self._cleanup_task
        self._cleanup_task = None
        if cleanup_task is not None:
            cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cleanup_task

        async with self._lock:
            self._contexts.clear()
        logger.info("Integrity troubleshooter context store stopped")

    async def open_context(
        self,
        *,
        owner_principal_id: str,
        project_locator: str,
        snapshot: IntegrityTroubleshooterSnapshot,
    ) -> IntegrityTroubleshooterContext:
        """Retain one snapshot and return its opaque identifier."""
        now: datetime = self._clock()
        context = IntegrityTroubleshooterContext(
            context_id=uuid4().hex,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
            snapshot=snapshot,
            created_at=now,
            expires_at=now + self._ttl,
        )
        async with self._lock:
            self._contexts[context.context_id] = context
        return context

    async def lookup_context(
        self,
        context_id: str,
        *,
        owner_principal_id: str,
        project_locator: str,
    ) -> IntegrityTroubleshooterContextLookup:
        """Return one owned snapshot, or explain why it cannot be used."""
        async with self._lock:
            context: IntegrityTroubleshooterContext | None = self._contexts.get(context_id)
            if context is None:
                return IntegrityTroubleshooterContextLookup(state="unavailable")
            if context.owner_principal_id != owner_principal_id or context.project_locator != project_locator:
                return IntegrityTroubleshooterContextLookup(state="unavailable")
            if context.is_expired(self._clock()):
                del self._contexts[context_id]
                return IntegrityTroubleshooterContextLookup(state="expired")
            return IntegrityTroubleshooterContextLookup(state="found", context=context)

    async def close_context(
        self,
        context_id: str,
        *,
        owner_principal_id: str,
        project_locator: str,
    ) -> bool:
        """Remove one owned snapshot and report whether it existed."""
        async with self._lock:
            context: IntegrityTroubleshooterContext | None = self._contexts.get(context_id)
            if context is None:
                return False
            if context.owner_principal_id != owner_principal_id or context.project_locator != project_locator:
                return False
            del self._contexts[context_id]
        return True

    async def sweep(self) -> int:
        """Remove every expired inspection and return how many were removed."""
        now: datetime = self._clock()
        async with self._lock:
            expired_ids: list[str] = [context_id for context_id, context in self._contexts.items() if context.is_expired(now)]
            for context_id in expired_ids:
                del self._contexts[context_id]
        return len(expired_ids)

    async def _remove_expired_periodically(self) -> None:
        """Remove abandoned inspections until the application stops."""
        while True:
            await asyncio.sleep(self._cleanup_interval_seconds)
            removed: int = await self.sweep()
            if removed:
                logger.info(f"Removed {removed} expired integrity troubleshooter context(s)")


_store: IntegrityTroubleshooterContextStore | None = None


def get_integrity_troubleshooter_context_store() -> IntegrityTroubleshooterContextStore:
    """Return the shared inspection store, creating one when needed."""
    global _store  # pylint: disable=global-statement
    if _store is None:
        _store = IntegrityTroubleshooterContextStore()
    return _store


def init_integrity_troubleshooter_context_store(
    store: IntegrityTroubleshooterContextStore | None = None,
) -> IntegrityTroubleshooterContextStore:
    """Replace the shared store during application startup."""
    global _store  # pylint: disable=global-statement
    _store = store if store is not None else IntegrityTroubleshooterContextStore()
    return _store
