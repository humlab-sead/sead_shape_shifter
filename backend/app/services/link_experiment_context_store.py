"""Retain one reproduced foreign-key link snapshot for a limited time.

The store keeps the pre-link A input, the processed B input, and the resolved
link configuration from a reproduced warning. Each use re-links those inputs,
so a settings change recomputes only the join. Expiry is fixed at 15 minutes
and is not extended by requests.

The module also holds the memory estimate used to reject an input or a
projected merge before it is materialized. The estimate is per computation, not
a hard guarantee against simultaneous work.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import pandas as pd
from loguru import logger

from backend.app.exceptions import ProjectedBudgetExceeded
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.specifications.constraints import ForeignKeyRuntimeOptions, ValidationIssue
from src.transforms.link import _resolve_fk_runtime_options
from src.transforms.utility import _NULL_SENTINEL_PREFIX, _coerce_compatible_merge_key_dtypes

if TYPE_CHECKING:
    from backend.app.services.link_baseline_service import LinkBaselineResult
    from backend.app.services.link_trial_service import LinkTrialResult

LINK_EXPERIMENT_CONTEXT_TTL: timedelta = timedelta(minutes=15)
"""Fixed lifetime of one retained snapshot."""

LINK_EXPERIMENT_CLEANUP_INTERVAL_SECONDS: float = 60.0
"""How often the background task removes expired contexts."""

BYTES_PER_MIB: int = 1024 * 1024
"""Bytes in one mebibyte, the unit of the configured memory limit."""

MIN_PROJECTED_COLUMN_BYTES: int = 64
"""Per-row width assumed for a column when the frame has no rows to measure."""

DiagnosticStatus = Literal["complete", "failed", "incomplete", "not_run"]
"""Status of the configured-key diagnostic retained with a snapshot."""

ContextLookupState = Literal["found", "expired", "unavailable"]
"""Outcome of looking up one context for one owner."""

_NULL_KEY = object()


@dataclass(frozen=True)
class LinkExperimentDiagnostics:
    """Configured-key diagnostic status retained with a snapshot.

    The four row counts stay ``None`` unless the diagnostic completed, so an
    incomplete baseline never presents complete totals.
    """

    status: DiagnosticStatus
    reason: str | None = None
    message: str | None = None
    input_a_rows: int | None = None
    output_rows: int | None = None
    unmatched_a_rows: int | None = None
    multiply_matched_a_rows: int | None = None
    issues: tuple[ValidationIssue, ...] = ()

    @classmethod
    def from_trial(cls, trial: LinkTrialResult) -> LinkExperimentDiagnostics:
        """Build diagnostics from one configured-key trial result."""
        if trial.status != "complete":
            return cls(
                status=trial.status,
                reason=trial.reason,
                message=trial.message,
                issues=trial.issues,
            )

        return cls(
            status="complete",
            reason=trial.reason,
            message=trial.message,
            input_a_rows=trial.input_a_rows,
            output_rows=trial.output_rows,
            unmatched_a_rows=trial.unmatched_a_rows,
            multiply_matched_a_rows=trial.multiply_matched_a_rows,
            issues=trial.issues,
        )


@dataclass(frozen=True)
class LinkExperimentSnapshot:
    """Fixed inputs, original configuration, and baseline state for one link."""

    baseline: LinkBaselineResult
    diagnostics: LinkExperimentDiagnostics


@dataclass(frozen=True)
class LinkExperimentContext:
    """One owner-scoped snapshot with a fixed expiry."""

    context_id: str
    owner_principal_id: str
    project_locator: str
    snapshot: LinkExperimentSnapshot
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Return True when ``now`` has reached the fixed expiry."""
        return now >= self.expires_at


@dataclass(frozen=True)
class LinkExperimentContextLookup:
    """Result of looking up a context for one owner.

    ``unavailable`` covers an unknown identifier and an identifier owned by
    another user or project, so a response cannot reveal either case.
    """

    state: ContextLookupState
    context: LinkExperimentContext | None = None


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class LinkExperimentContextStore:
    """Hold temporary link snapshots for one application process."""

    def __init__(
        self,
        *,
        ttl: timedelta = LINK_EXPERIMENT_CONTEXT_TTL,
        clock: Callable[[], datetime] | None = None,
        cleanup_interval_seconds: float = LINK_EXPERIMENT_CLEANUP_INTERVAL_SECONDS,
    ) -> None:
        """Configure the lifetime, clock, and cleanup interval.

        Args:
            ttl: Fixed lifetime of each context; it is never extended.
            clock: Current-time source. Tests replace it with a controllable clock.
            cleanup_interval_seconds: Delay between background expiry sweeps.
        """
        self._ttl: timedelta = ttl
        self._clock: Callable[[], datetime] = clock if clock is not None else _utc_now
        self._cleanup_interval_seconds: float = cleanup_interval_seconds
        self._contexts: dict[str, LinkExperimentContext] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    @property
    def ttl(self) -> timedelta:
        """Return the fixed context lifetime."""
        return self._ttl

    def __len__(self) -> int:
        """Return how many contexts the store currently holds."""
        return len(self._contexts)

    async def start(self) -> None:
        """Start the background task that removes expired contexts."""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._remove_expired_periodically())
        logger.info("Link experiment context store started")

    async def stop(self) -> None:
        """Stop background cleanup and release every retained snapshot."""
        cleanup_task: asyncio.Task[None] | None = self._cleanup_task
        self._cleanup_task = None
        if cleanup_task is not None:
            cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cleanup_task

        async with self._lock:
            self._contexts.clear()
        logger.info("Link experiment context store stopped")

    async def open_context(
        self,
        *,
        owner_principal_id: str,
        project_locator: str,
        snapshot: LinkExperimentSnapshot,
    ) -> LinkExperimentContext:
        """Retain one snapshot and return its opaque identifier record."""
        now: datetime = self._clock()
        context = LinkExperimentContext(
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
    ) -> LinkExperimentContextLookup:
        """Return one owned context, or explain why it cannot be used.

        An expired context is removed on access so its frames are released.
        """
        async with self._lock:
            context: LinkExperimentContext | None = self._contexts.get(context_id)
            if context is None:
                return LinkExperimentContextLookup(state="unavailable")
            if context.owner_principal_id != owner_principal_id or context.project_locator != project_locator:
                return LinkExperimentContextLookup(state="unavailable")
            if context.is_expired(self._clock()):
                del self._contexts[context_id]
                return LinkExperimentContextLookup(state="expired")
            return LinkExperimentContextLookup(state="found", context=context)

    async def close_context(
        self,
        context_id: str,
        *,
        owner_principal_id: str,
        project_locator: str,
    ) -> bool:
        """Remove one owned context and report whether it existed.

        Removing a context drops the store's reference. A computation that
        already holds the record may still finish with its own reference.
        """
        async with self._lock:
            context: LinkExperimentContext | None = self._contexts.get(context_id)
            if context is None:
                return False
            if context.owner_principal_id != owner_principal_id or context.project_locator != project_locator:
                return False
            del self._contexts[context_id]
        return True

    async def sweep(self) -> int:
        """Remove every expired context and return how many were removed."""
        now: datetime = self._clock()
        async with self._lock:
            expired_ids: list[str] = [context_id for context_id, context in self._contexts.items() if context.is_expired(now)]
            for context_id in expired_ids:
                del self._contexts[context_id]
        return len(expired_ids)

    async def _remove_expired_periodically(self) -> None:
        """Remove abandoned contexts until the application stops the store."""
        while True:
            await asyncio.sleep(self._cleanup_interval_seconds)
            removed: int = await self.sweep()
            if removed:
                logger.info(f"Removed {removed} expired link experiment context(s)")


_store: LinkExperimentContextStore | None = None  # pylint: disable=invalid-name


def get_link_experiment_context_store() -> LinkExperimentContextStore:
    """Return the shared context store, creating a default one when needed."""
    global _store  # pylint: disable=global-statement
    if _store is None:
        _store = LinkExperimentContextStore()
    return _store


def init_link_experiment_context_store(store: LinkExperimentContextStore | None = None) -> LinkExperimentContextStore:
    """Replace the shared store during application startup."""
    global _store  # pylint: disable=global-statement
    _store = store if store is not None else LinkExperimentContextStore()
    return _store


@dataclass(frozen=True)
class LinkMergeKeys:
    """Prepared merge keys and selected remote columns for one foreign key."""

    local_key_frame: pd.DataFrame
    remote_key_frame: pd.DataFrame
    mapped_remote_keys: list[str]
    remote_output_columns: list[str]
    remote_source_by_output: dict[str, str]
    runtime_options: ForeignKeyRuntimeOptions
    join_type: str


def prepare_link_merge_keys(
    project: ShapeShiftProject,
    fk: ForeignKeyConfig,
    local_rows: pd.DataFrame,
    remote_rows: pd.DataFrame,
) -> LinkMergeKeys:
    """Return the key columns and selected remote columns production would merge.

    Args:
        project: Resolved project holding the remote entity configuration.
        fk: Foreign key whose keys are prepared.
        local_rows: Pre-link local input.
        remote_rows: Processed remote input.

    Returns:
        Key frames, mapped remote key names, and the selected remote columns.

    Raises:
        KeyError: If the remote input lacks the remote system ID or a mapped key.
        ValueError: If a frame has duplicate columns or the mapping collides.
    """
    if not local_rows.columns.is_unique or not remote_rows.columns.is_unique:
        raise ValueError("Link inputs must not contain duplicate column names.")

    remote_config = project.get_table(fk.remote_entity)
    if list(remote_rows.columns).count(remote_config.system_id) != 1:
        raise KeyError(f"The remote link input must contain one '{remote_config.system_id}' column.")

    setup = fk.generate_link_setup(remote_rows.columns.tolist(), remote_config)
    remote_sources: list[str] = [remote_config.system_id]
    remote_sources.extend(column for column in setup.remote_columns if column != remote_config.system_id)
    output_columns: list[str] = [setup.rename_map.get(column, column) for column in remote_sources]
    if len(set(output_columns)) != len(output_columns):
        raise ValueError("The remote key setup produces duplicate link columns.")

    source_by_output: dict[str, str] = dict(zip(output_columns, remote_sources))
    mapped_remote_keys: list[str] = [setup.rename_map.get(key, key) for key in fk.remote_keys]
    if len(set(mapped_remote_keys)) != len(mapped_remote_keys):
        raise ValueError("The selected remote keys resolve to duplicate link columns.")

    missing_outputs: list[str] = [key for key in mapped_remote_keys if key not in source_by_output]
    if missing_outputs:
        raise KeyError(f"Remote link keys are unavailable after production column mapping: {missing_outputs}")

    local_key_frame: pd.DataFrame = local_rows.loc[:, fk.local_keys].copy()
    remote_key_frame: pd.DataFrame = remote_rows.loc[:, [source_by_output[key] for key in mapped_remote_keys]].copy()
    remote_key_frame.columns = mapped_remote_keys

    return LinkMergeKeys(
        local_key_frame=local_key_frame,
        remote_key_frame=remote_key_frame,
        mapped_remote_keys=mapped_remote_keys,
        remote_output_columns=output_columns,
        remote_source_by_output=source_by_output,
        runtime_options=_resolve_fk_runtime_options(fk, remote_config),
        join_type=fk.how or "inner",
    )


def estimate_output_rows(
    local_key_frame: pd.DataFrame,
    remote_key_frame: pd.DataFrame,
    local_keys: list[str],
    remote_keys: list[str],
    runtime_options: ForeignKeyRuntimeOptions,
    how: str,
) -> tuple[int, int]:
    """Estimate production and diagnostic output rows without expanding matches.

    Returns:
        The production join row count and the left diagnostic join row count.
    """
    estimate_local, estimate_remote = _coerce_compatible_merge_key_dtypes(
        local_key_frame.copy(),
        remote_key_frame.copy(),
        local_keys,
        remote_keys,
    )
    local_counts: dict[tuple[Any, ...], int] = _key_frequencies(
        estimate_local,
        local_keys,
        null_side="left",
        prevent_null_key_matches=runtime_options.prevent_null_key_matches,
    )
    remote_counts: dict[tuple[Any, ...], int] = _key_frequencies(
        estimate_remote,
        remote_keys,
        null_side="right",
        prevent_null_key_matches=runtime_options.prevent_null_key_matches,
    )

    link_rows: int = 0
    diagnostic_rows: int = 0
    for key, local_count in local_counts.items():
        remote_count: int = remote_counts.get(key, 0)
        diagnostic_rows += local_count * max(remote_count, 1)
        if how == "inner":
            link_rows += local_count * remote_count
        else:
            link_rows += local_count * max(remote_count, 1)
    return link_rows, diagnostic_rows


def _key_frequencies(
    frame: pd.DataFrame,
    keys: list[str],
    *,
    null_side: Literal["left", "right"],
    prevent_null_key_matches: bool | None,
) -> dict[tuple[Any, ...], int]:
    """Count normalized key tuples without joining rows."""
    counts: dict[tuple[Any, ...], int] = {}
    for values in frame.loc[:, keys].itertuples(index=False, name=None):
        normalized: list[Any] = []
        for index, value in enumerate(values):
            if bool(pd.isna(value)):
                if prevent_null_key_matches:
                    normalized.append(f"{_NULL_SENTINEL_PREFIX}_{null_side}_{index}")
                else:
                    normalized.append(_NULL_KEY)
            else:
                normalized.append(value)
        key: tuple[Any, ...] = tuple(normalized)
        counts[key] = counts.get(key, 0) + 1
    return counts


def frame_bytes(frame: pd.DataFrame) -> int:
    """Return the bytes used by one frame's columns."""
    return int(frame.memory_usage(index=False, deep=True).sum())


def retained_input_bytes(local_rows: pd.DataFrame, remote_rows: pd.DataFrame) -> int:
    """Return the bytes held when both link inputs are retained."""
    return frame_bytes(local_rows) + frame_bytes(remote_rows)


def _column_bytes_per_row(
    frame: pd.DataFrame,
    column: str,
    *,
    fallback: int = MIN_PROJECTED_COLUMN_BYTES,
) -> int:
    """Return bytes per row for one column, or a fallback when no row exists."""
    matching = frame.loc[:, [column]]
    rows: int = len(frame)
    if rows <= 0:
        return fallback
    total: int = int(matching.memory_usage(index=False, deep=True).sum())
    if total <= 0:
        return fallback
    return max((total + rows - 1) // rows, 1)


def projected_merge_bytes(
    *,
    retained_bytes: int,
    input_bytes: int,
    local_rows: pd.DataFrame,
    remote_rows: pd.DataFrame,
    local_keys: Sequence[str],
    remote_output_columns: Sequence[str],
    remote_source_by_output: Mapping[str, str],
    mapped_remote_keys: Sequence[str],
    estimated_output_rows: int,
    include_merge_indicator: bool = False,
    position_columns: int = 0,
    null_key_temporaries: bool = False,
) -> int:
    """Estimate the bytes one merge stage needs.

    The approved rule is retained inputs, plus four copies of the two input
    frames, plus three copies of the projected join output. Widths are measured
    from the actual local frame and the selected remote columns. A column name
    that is a join key on both sides is counted once, because the merge keeps
    one column for it.

    Args:
        retained_bytes: Bytes already held by the retained snapshot.
        input_bytes: Bytes of both input frames.
        local_rows: Local frame entering the merge.
        remote_rows: Remote frame entering the merge.
        local_keys: Local merge keys.
        remote_output_columns: Remote columns present in the merge output.
        remote_source_by_output: Output column name to source column name.
        mapped_remote_keys: Remote merge keys after production renaming.
        estimated_output_rows: Projected output row count for this stage.
        include_merge_indicator: Allow for a merge-indicator column.
        position_columns: Allow for temporary position columns.
        null_key_temporaries: Allow for sentinel key columns that prevent null matches.

    Returns:
        Projected bytes for the stage.
    """
    shared_keys: set[str] = {key for key in local_keys if key in set(mapped_remote_keys)}
    row_width: int = sum(_column_bytes_per_row(local_rows, column) for column in dict.fromkeys(local_rows.columns))
    for output in remote_output_columns:
        if output in shared_keys and output in local_rows.columns:
            continue
        row_width += _column_bytes_per_row(remote_rows, remote_source_by_output.get(output, output))
    if include_merge_indicator:
        row_width += MIN_PROJECTED_COLUMN_BYTES
    if position_columns > 0:
        row_width += position_columns * MIN_PROJECTED_COLUMN_BYTES
    if null_key_temporaries:
        row_width += 2 * len(mapped_remote_keys) * MIN_PROJECTED_COLUMN_BYTES

    output_bytes: int = max(estimated_output_rows, 0) * row_width
    return retained_bytes + 4 * input_bytes + 3 * output_bytes


def ensure_retained_input_budget(retained_bytes: int, limit_bytes: int, *, stage: str) -> None:
    """Reject retained link inputs above the configured memory limit.

    Raises:
        ProjectedBudgetExceeded: If the retained inputs are larger than the limit.
    """
    if retained_bytes > limit_bytes:
        raise ProjectedBudgetExceeded(
            f"Retained link inputs for {stage} need {_format_mib(retained_bytes)} MiB, "
            f"above the configured limit of {_format_mib(limit_bytes)} MiB.",
            context={"stage": stage, "limit_bytes": limit_bytes, "projected_bytes": retained_bytes},
        )


def ensure_projected_budget(projected_bytes: int, limit_bytes: int, *, stage: str) -> None:
    """Reject a merge whose projected memory is above the configured limit.

    Raises:
        ProjectedBudgetExceeded: If the projection is larger than the limit.
    """
    if projected_bytes > limit_bytes:
        raise ProjectedBudgetExceeded(
            f"The projected memory for {stage} is {_format_mib(projected_bytes)} MiB, "
            f"above the configured limit of {_format_mib(limit_bytes)} MiB.",
            context={"stage": stage, "limit_bytes": limit_bytes, "projected_bytes": projected_bytes},
        )


def _format_mib(value: int) -> str:
    """Return a byte count in mebibytes with one decimal place."""
    return f"{value / BYTES_PER_MIB:.1f}"
