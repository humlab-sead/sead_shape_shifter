"""Tests for the retained link experiment context store and its budget rule."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import pytest

from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_experiment_context_store import (
    LINK_EXPERIMENT_CONTEXT_TTL,
    MIN_PROJECTED_COLUMN_BYTES,
    JoinTypeSetting,
    LinkExperimentContext,
    LinkExperimentContextStore,
    LinkExperimentDiagnostics,
    LinkExperimentSnapshot,
    RequestedSetting,
    ResolvedNullPolicy,
    TrialExceptionGroup,
    TrialExceptionGroups,
    TrialExceptionRow,
    TrialSettingsReport,
    ensure_projected_budget,
    ensure_retained_input_budget,
    estimate_output_rows,
    frame_bytes,
    prepare_link_merge_keys,
    projected_merge_bytes,
    retained_input_bytes,
)
from backend.app.services.link_trial_service import LinkTrialResult
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.specifications.constraints import ForeignKeyRuntimeOptions

OWNER = "alice"
PROJECT = "project-a"


class StubClock:
    """Controllable UTC clock for expiry tests."""

    def __init__(self) -> None:
        self.current: datetime = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward."""
        self.current += delta


def make_snapshot(*, diagnostic_status: str = "complete") -> LinkExperimentSnapshot:
    """Build one retained snapshot with fixed frames."""
    baseline = LinkBaselineResult(
        status="reproduced",
        reason="reproduced",
        message="The replayed link raised the opened warning",
        entity_name="orders",
        remote_entity="customers",
        fk_index=0,
        link_pass="initial",
        row_count_before=2,
        row_count_after=1,
        local_rows=pd.DataFrame({"system_id": [10, 11], "customer_code": ["A", "missing"]}),
        remote_rows=pd.DataFrame({"system_id": [1], "code": ["A"]}),
    )
    return LinkExperimentSnapshot(
        baseline=baseline,
        diagnostics=LinkExperimentDiagnostics(
            status=diagnostic_status,  # type: ignore[arg-type]
            reason="complete" if diagnostic_status == "complete" else "invalid_keys",
            input_a_rows=2 if diagnostic_status == "complete" else None,
            output_rows=1 if diagnostic_status == "complete" else None,
        ),
    )


def store_with_clock(*, cleanup_interval_seconds: float = 60.0) -> tuple[LinkExperimentContextStore, StubClock]:
    """Build a store controlled by a stub clock."""
    clock = StubClock()
    return LinkExperimentContextStore(clock=clock, cleanup_interval_seconds=cleanup_interval_seconds), clock


async def opened_context(
    store: LinkExperimentContextStore,
    *,
    owner: str = OWNER,
    project: str = PROJECT,
    diagnostic_status: str = "complete",
) -> LinkExperimentContext:
    """Retain one snapshot for the default owner."""
    return await store.open_context(
        owner_principal_id=owner,
        project_locator=project,
        snapshot=make_snapshot(diagnostic_status=diagnostic_status),
    )


def test_context_lifetime_is_fifteen_minutes() -> None:
    """The retention window is fixed at fifteen minutes."""
    assert LINK_EXPERIMENT_CONTEXT_TTL == timedelta(minutes=15)
    assert LINK_EXPERIMENT_CONTEXT_TTL.total_seconds() == 900


@pytest.mark.asyncio
async def test_open_context_keeps_inputs_fixed_before_expiry() -> None:
    """A context returns the same snapshot for the whole retention window."""
    store, clock = store_with_clock()
    snapshot = make_snapshot()

    context = await store.open_context(owner_principal_id=OWNER, project_locator=PROJECT, snapshot=snapshot)
    clock.advance(LINK_EXPERIMENT_CONTEXT_TTL - timedelta(seconds=1))
    lookup = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)

    assert lookup.state == "found"
    assert lookup.context is not None
    assert lookup.context.snapshot is snapshot
    assert lookup.context.snapshot.baseline.local_rows is snapshot.baseline.local_rows
    assert context.expires_at - context.created_at == LINK_EXPERIMENT_CONTEXT_TTL


@pytest.mark.asyncio
async def test_lookup_at_expiry_reports_expired_and_releases_the_snapshot() -> None:
    """Reaching the fixed expiry removes the context and later lookups cannot use it."""
    store, clock = store_with_clock()
    context = await opened_context(store)

    clock.advance(LINK_EXPERIMENT_CONTEXT_TTL)
    expired = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)

    assert expired.state == "expired"
    assert expired.context is None
    assert len(store) == 0

    repeated = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
    assert repeated.state == "unavailable"


@pytest.mark.asyncio
async def test_lookup_does_not_extend_the_snapshot_lifetime() -> None:
    """Repeated access inside the window never moves the expiry."""
    store, clock = store_with_clock()
    context = await opened_context(store)

    for _ in range(3):
        clock.advance(timedelta(minutes=4))
        lookup = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
        assert lookup.state == "found"
        assert lookup.context is not None
        assert lookup.context.expires_at == context.expires_at

    clock.advance(timedelta(minutes=3))
    expired = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
    assert expired.state == "expired"


@pytest.mark.asyncio
async def test_close_context_releases_an_owned_context_once() -> None:
    """Close removes the context, and a repeated Close reports it is gone."""
    store, _ = store_with_clock()
    context = await opened_context(store)

    assert await store.close_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT) is True
    assert len(store) == 0
    assert await store.close_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT) is False


@pytest.mark.asyncio
async def test_another_owner_cannot_read_or_close_the_context() -> None:
    """An identifier alone grants no access, and a foreign Close keeps the context."""
    store, _ = store_with_clock()
    context = await opened_context(store)

    other_user = await store.lookup_context(context.context_id, owner_principal_id="mallory", project_locator=PROJECT)
    other_project = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator="project-b")

    assert other_user.state == "unavailable"
    assert other_project.state == "unavailable"
    assert await store.close_context(context.context_id, owner_principal_id="mallory", project_locator=PROJECT) is False
    assert len(store) == 1

    owned = await store.lookup_context(context.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
    assert owned.state == "found"


@pytest.mark.asyncio
async def test_unknown_identifier_is_unavailable() -> None:
    """An identifier that was never issued cannot be read or closed."""
    store, _ = store_with_clock()

    lookup = await store.lookup_context("missing", owner_principal_id=OWNER, project_locator=PROJECT)

    assert lookup.state == "unavailable"
    assert lookup.context is None
    assert await store.close_context("missing", owner_principal_id=OWNER, project_locator=PROJECT) is False


@pytest.mark.asyncio
async def test_sweep_removes_only_expired_contexts() -> None:
    """Periodic cleanup releases abandoned contexts and keeps live ones."""
    store, clock = store_with_clock()
    abandoned = await opened_context(store)
    clock.advance(timedelta(minutes=10))
    live = await opened_context(store)

    clock.advance(timedelta(minutes=6))
    removed = await store.sweep()

    assert removed == 1
    assert len(store) == 1
    gone = await store.lookup_context(abandoned.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
    kept = await store.lookup_context(live.context_id, owner_principal_id=OWNER, project_locator=PROJECT)
    assert gone.state == "unavailable"
    assert kept.state == "found"


@pytest.mark.asyncio
async def test_periodic_cleanup_removes_an_abandoned_context() -> None:
    """The background task expires a dialog the user never returns to."""
    store, clock = store_with_clock(cleanup_interval_seconds=0.01)
    await store.start()
    try:
        await opened_context(store)
        clock.advance(LINK_EXPERIMENT_CONTEXT_TTL)

        for _ in range(200):
            if len(store) == 0:
                break
            await asyncio.sleep(0.01)

        assert len(store) == 0
    finally:
        await store.stop()


@pytest.mark.asyncio
async def test_stop_releases_retained_contexts_and_is_idempotent() -> None:
    """Shutdown clears the store and starting twice keeps one cleanup task."""
    store, _ = store_with_clock()
    await store.start()
    await store.start()
    await opened_context(store)

    assert len(store) == 1
    await store.stop()
    await store.stop()

    assert len(store) == 0


def test_frame_bytes_measures_column_memory() -> None:
    """Frame size covers every column and ignores the index."""
    frame = pd.DataFrame({"code": ["value"] * 100})

    assert frame_bytes(frame) > 0
    assert retained_input_bytes(frame, frame) == 2 * frame_bytes(frame)


def test_retained_input_budget_allows_the_exact_limit() -> None:
    """Equality with the configured limit is accepted."""
    ensure_retained_input_budget(1024, 1024, stage="link reproduction")


@pytest.mark.parametrize("projected", [1025])
def test_retained_input_budget_rejects_one_byte_over_the_limit(projected: int) -> None:
    """One byte above the limit is rejected with no row values in the message."""
    with pytest.raises(ProjectedBudgetExceeded) as raised:
        ensure_retained_input_budget(projected, 1024, stage="link reproduction")

    assert "MiB" in raised.value.message
    assert raised.value.context["limit_bytes"] == 1024
    assert raised.value.context["projected_bytes"] == projected
    assert raised.value.context["stage"] == "link reproduction"


def test_projected_budget_rejects_only_above_the_limit() -> None:
    """Projected merges allow equality and reject a larger projection."""
    ensure_projected_budget(2048, 2048, stage="link trial")

    with pytest.raises(ProjectedBudgetExceeded) as raised:
        ensure_projected_budget(2049, 2048, stage="link trial")

    assert raised.value.code == "PROJECTED_BUDGET_EXCEEDED"
    assert raised.value.context["limit_bytes"] == 2048


def test_estimate_output_rows_expands_duplicate_remote_keys() -> None:
    """Duplicate remote matches expand production and diagnostic row counts."""
    local = pd.DataFrame({"code": ["duplicate", "missing"]})
    remote = pd.DataFrame({"code": ["duplicate", "duplicate"]})
    runtime = ForeignKeyRuntimeOptions(prevent_null_key_matches=False)

    inner_rows, inner_diagnostic = estimate_output_rows(local, remote, ["code"], ["code"], runtime, "inner")
    left_rows, left_diagnostic = estimate_output_rows(local, remote, ["code"], ["code"], runtime, "left")

    assert (inner_rows, inner_diagnostic) == (2, 3)
    assert (left_rows, left_diagnostic) == (3, 3)


def test_estimate_output_rows_prevents_null_key_matches() -> None:
    """Forbidden null matches do not join the two sides."""
    local = pd.DataFrame({"code": ["A", None]})
    remote = pd.DataFrame({"code": ["A", None]})

    allowed_rows, allowed_diagnostic = estimate_output_rows(
        local,
        remote,
        ["code"],
        ["code"],
        ForeignKeyRuntimeOptions(prevent_null_key_matches=False),
        "inner",
    )
    prevented_rows, prevented_diagnostic = estimate_output_rows(
        local,
        remote,
        ["code"],
        ["code"],
        ForeignKeyRuntimeOptions(prevent_null_key_matches=True),
        "inner",
    )

    assert (allowed_rows, allowed_diagnostic) == (2, 2)
    assert (prevented_rows, prevented_diagnostic) == (1, 2)


def test_projected_merge_counts_both_key_sides_when_names_differ() -> None:
    """A renamed remote key adds its own output column."""
    local = pd.DataFrame({"code": ["value"]})
    shared_remote = pd.DataFrame({"code": ["value"]})
    renamed_remote = pd.DataFrame({"other": ["value"]})

    shared = projected_merge_bytes(
        retained_bytes=0,
        input_bytes=0,
        local_rows=local,
        remote_rows=shared_remote,
        local_keys=["code"],
        remote_output_columns=["code"],
        remote_source_by_output={"code": "code"},
        mapped_remote_keys=["code"],
        estimated_output_rows=1,
    )
    renamed = projected_merge_bytes(
        retained_bytes=0,
        input_bytes=0,
        local_rows=local,
        remote_rows=renamed_remote,
        local_keys=["code"],
        remote_output_columns=["other"],
        remote_source_by_output={"other": "other"},
        mapped_remote_keys=["other"],
        estimated_output_rows=1,
    )

    assert shared > 0
    assert renamed == 2 * shared


def test_projected_merge_uses_a_column_width_for_empty_frames() -> None:
    """Empty frames fall back to a fixed per-column width instead of dividing by zero."""
    empty_local = pd.DataFrame({"code": pd.Series([], dtype="object")})
    empty_remote = pd.DataFrame({"code": pd.Series([], dtype="object")})

    projected = projected_merge_bytes(
        retained_bytes=0,
        input_bytes=0,
        local_rows=empty_local,
        remote_rows=empty_remote,
        local_keys=["code"],
        remote_output_columns=["code"],
        remote_source_by_output={"code": "code"},
        mapped_remote_keys=["code"],
        estimated_output_rows=1,
    )

    assert projected == 3 * MIN_PROJECTED_COLUMN_BYTES


def test_projected_merge_adds_indicator_position_and_null_key_columns() -> None:
    """Temporary merge columns increase the projected width."""
    local = pd.DataFrame({"code": ["value"]})
    remote = pd.DataFrame({"code": ["value"]})
    base: dict[str, Any] = {
        "retained_bytes": 0,
        "input_bytes": 0,
        "local_rows": local,
        "remote_rows": remote,
        "local_keys": ["code"],
        "remote_output_columns": ["code"],
        "remote_source_by_output": {"code": "code"},
        "mapped_remote_keys": ["code"],
        "estimated_output_rows": 1,
    }

    plain = projected_merge_bytes(**base)
    with_indicator = projected_merge_bytes(**base, include_merge_indicator=True)
    with_positions = projected_merge_bytes(**base, position_columns=2)
    with_nulls = projected_merge_bytes(**base, null_key_temporaries=True)

    assert with_indicator == plain + 3 * MIN_PROJECTED_COLUMN_BYTES
    assert with_positions == plain + 6 * MIN_PROJECTED_COLUMN_BYTES
    assert with_nulls == plain + 6 * MIN_PROJECTED_COLUMN_BYTES


def test_projected_merge_retains_inputs_and_copy_headroom() -> None:
    """The rule adds retained inputs, four input copies, and three output copies."""
    local = pd.DataFrame({"code": ["value"]})
    remote = pd.DataFrame({"code": ["value"]})
    base: dict[str, Any] = {
        "retained_bytes": 0,
        "input_bytes": 0,
        "local_rows": local,
        "remote_rows": remote,
        "local_keys": ["code"],
        "remote_output_columns": ["code"],
        "remote_source_by_output": {"code": "code"},
        "mapped_remote_keys": ["code"],
        "estimated_output_rows": 1,
    }
    output_bytes = projected_merge_bytes(**base)

    projected = projected_merge_bytes(**(base | {"retained_bytes": 1_000, "input_bytes": 100}))  # pyright: ignore[reportArgumentType]

    assert projected == 1_000 + 4 * 100 + output_bytes


def merge_project() -> tuple[ShapeShiftProject, ForeignKeyConfig, pd.DataFrame, pd.DataFrame]:
    """Build a saved project whose remote key keeps its own name."""
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "orders": {
                    "type": "fixed",
                    "public_id": "order_id",
                    "columns": ["customer_code"],
                    "values": [["A"]],
                    "foreign_keys": [{"entity": "customers", "local_keys": ["customer_code"], "remote_keys": ["code"]}],
                },
                "customers": {
                    "type": "fixed",
                    "public_id": "customer_id",
                    "columns": ["code"],
                    "values": [["A"]],
                },
            }
        }
    )
    fk: ForeignKeyConfig = project.get_table("orders").foreign_keys[0]
    local_rows = pd.DataFrame({"system_id": [1], "customer_code": ["A"]})
    remote_rows = pd.DataFrame({"system_id": [1], "code": ["A"]})
    return project, fk, local_rows, remote_rows


def test_prepare_link_merge_keys_maps_remote_columns() -> None:
    """Merge keys keep the local names and resolve the renamed remote payload."""
    project, fk, local_rows, remote_rows = merge_project()

    keys = prepare_link_merge_keys(project, fk, local_rows, remote_rows)

    assert keys.local_key_frame.columns.tolist() == ["customer_code"]
    assert keys.remote_key_frame.columns.tolist() == ["code"]
    assert keys.mapped_remote_keys == ["code"]
    assert "customer_id" in keys.remote_source_by_output
    assert keys.join_type == "inner"


def test_prepare_link_merge_keys_rejects_a_missing_remote_system_id() -> None:
    """Production requires exactly one remote system ID column."""
    project, fk, local_rows, remote_rows = merge_project()

    with pytest.raises(KeyError):
        prepare_link_merge_keys(project, fk, local_rows, remote_rows.drop(columns=["system_id"]))


def sample_settings() -> TrialSettingsReport:
    """Build one resolved settings report."""
    return TrialSettingsReport(
        join_type=JoinTypeSetting(requested=None, source="inherited", effective="inner"),
        allow_null_keys=RequestedSetting(requested=None, source="inherited"),
        null_keys_equal=RequestedSetting(requested=None, source="inherited"),
        resolved_null_policy=ResolvedNullPolicy(enforce_strict_null_keys=True, prevent_null_key_matches=False),
    )


def sample_groups(cap: int = 2) -> TrialExceptionGroups:
    """Build groups whose retained rows are already capped."""
    unmatched = tuple(TrialExceptionRow(position, ("missing",), 0, 0) for position in range(cap))
    multiply = tuple(TrialExceptionRow(position, ("duplicate",), 2, 2) for position in range(cap))
    return TrialExceptionGroups(
        unmatched=TrialExceptionGroup(total_count=5, rows=unmatched),
        multiply_matched=TrialExceptionGroup(total_count=4, rows=multiply),
    )


def test_diagnostics_from_a_complete_trial_retain_capped_groups_and_settings() -> None:
    groups = sample_groups()
    settings = sample_settings()

    diagnostics = LinkExperimentDiagnostics.from_trial(
        LinkTrialResult(
            status="complete",
            reason="complete",
            message="The trial completed.",
            input_a_rows=9,
            output_rows=4,
            unmatched_a_rows=5,
            multiply_matched_a_rows=4,
            a_rows=(),
            exception_groups=groups,
            settings=settings,
        )
    )

    assert diagnostics.status == "complete"
    assert diagnostics.input_a_rows == 9
    assert diagnostics.output_rows == 4
    assert diagnostics.unmatched_a_rows == 5
    assert diagnostics.multiply_matched_a_rows == 4
    assert diagnostics.exception_groups == groups
    assert diagnostics.exception_groups is not None
    assert diagnostics.exception_groups.unmatched.total_count == 5
    assert len(diagnostics.exception_groups.unmatched.rows) == 2
    assert diagnostics.settings == settings


@pytest.mark.parametrize("status", ["failed", "incomplete"])
def test_diagnostics_from_a_non_complete_trial_drop_counts_and_groups(status: str) -> None:
    settings = sample_settings()

    diagnostics = LinkExperimentDiagnostics.from_trial(
        LinkTrialResult(
            status=status,  # type: ignore[arg-type]
            reason="invalid_keys" if status == "failed" else "row_limit_exceeded",
            message="The trial is unavailable.",
            input_a_rows=9,
            output_rows=4,
            unmatched_a_rows=5,
            multiply_matched_a_rows=4,
            exception_groups=sample_groups(),
            settings=settings,
        )
    )

    assert diagnostics.status == status
    assert diagnostics.input_a_rows is None
    assert diagnostics.output_rows is None
    assert diagnostics.unmatched_a_rows is None
    assert diagnostics.multiply_matched_a_rows is None
    assert diagnostics.exception_groups is None
    assert diagnostics.settings == settings
