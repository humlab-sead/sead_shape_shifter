"""Tests for link troubleshooter orchestration and read-only integration."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import pytest

from backend.app.core.config import Settings
from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.models.link_troubleshooter import LinkExperimentTrialRequest
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_experiment_context_store import (
    LINK_EXPERIMENT_CONTEXT_TTL,
    LinkExperimentContextStore,
    TrialExceptionGroup,
    TrialExceptionGroups,
    TrialExceptionRow,
)
from backend.app.services.link_trial_service import ARowTrialDiagnostic, LinkTrialResult, LinkTrialService
from backend.app.services.link_troubleshooter_service import LinkTroubleshooterService
from src.model import ForeignKeyConfig, ShapeShiftProject


class StubBaselineService:
    """Return one prepared baseline and record its request."""

    def __init__(self, baseline: LinkBaselineResult) -> None:
        self.baseline = baseline
        self.calls: list[dict[str, Any]] = []

    async def build_baseline(self, **kwargs: Any) -> LinkBaselineResult:
        self.calls.append(kwargs)
        return self.baseline


class StubTrialService:
    """Return queued trial results and record each selected key pair."""

    def __init__(self, results: Sequence[LinkTrialResult]) -> None:
        self.results = list(results)
        self.calls: list[tuple[list[str] | None, list[str] | None]] = []
        self.option_calls: list[dict[str, Any]] = []

    def run_trial(
        self,
        baseline: LinkBaselineResult,  # pylint: disable=unused-argument
        *,
        local_keys: Sequence[str] | None,
        remote_keys: Sequence[str] | None,
        **options: Any,
    ) -> LinkTrialResult:
        self.calls.append((list(local_keys) if local_keys is not None else None, list(remote_keys) if remote_keys is not None else None))
        self.option_calls.append(options)
        return self.results.pop(0)


def make_baseline(
    *,
    local_keys: list[str] | None = None,
    remote_keys: list[str] | None = None,
    how: str = "inner",
    status: str = "reproduced",
    include_context: bool = True,
) -> LinkBaselineResult:
    """Build a reproducible baseline for service-level orchestration tests."""
    saved_local_keys = local_keys or ["saved_code"]
    saved_remote_keys = remote_keys or ["saved_value"]
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "columns": ["saved_code", "trial_code"],
                "values": [["A", "X"], ["B", "X"], ["missing", "Z"]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": saved_local_keys,
                        "remote_keys": saved_remote_keys,
                        "how": how,
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "columns": ["saved_value", "trial_value"],
                "values": [["A", "X"], ["B", "X"], ["C", "Y"]],
            },
        }
    }
    saved_project = ShapeShiftProject(cfg=cfg)
    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]
    return LinkBaselineResult(
        status=status,  # type: ignore[arg-type]
        reason="reproduced" if status == "reproduced" else "warning_changed",
        message="The baseline result.",
        entity_name="orders",
        remote_entity="customers",
        fk_index=0,
        link_pass="initial",
        row_count_before=3,
        row_count_after=2,
        local_rows=(
            pd.DataFrame(
                {
                    "system_id": [10, 11, 12],
                    "saved_code": ["A", "B", "missing"],
                    "trial_code": ["X", "X", "Z"],
                }
            )
            if include_context
            else None
        ),
        remote_rows=(
            pd.DataFrame(
                {
                    "system_id": [1, 2, 3],
                    "saved_value": ["A", "B", "C"],
                    "trial_value": ["X", "X", "Y"],
                }
            )
            if include_context
            else None
        ),
        _saved_project=saved_project if include_context else None,
        _foreign_key=fk,
    )


def trial_result(
    *,
    status: str = "complete",
    input_rows: int | None = 3,
    output_rows: int | None = 2,
    unmatched_rows: int | None = 1,
    multiply_matched_rows: int | None = 0,
    rows: tuple[ARowTrialDiagnostic, ...] | None = (),
    reason: str = "complete",
) -> LinkTrialResult:
    """Build a trial result for orchestration tests."""
    return LinkTrialResult(
        status=status,  # type: ignore[arg-type]
        reason=reason,
        message="Trial result.",
        input_a_rows=input_rows,
        output_rows=output_rows,
        unmatched_a_rows=unmatched_rows,
        multiply_matched_a_rows=multiply_matched_rows,
        a_rows=rows,
    )


# ---------------------------------------------------------------------------
# Retained experiment context
# ---------------------------------------------------------------------------


class StubClock:
    """Controllable clock for context expiry tests."""

    def __init__(self) -> None:
        self.current: datetime = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward."""
        self.current += delta


class RaisingTrialService:
    """Reject every trial with the projected-budget failure."""

    def run_trial(
        self,
        baseline: LinkBaselineResult,  # pylint: disable=unused-argument
        *,
        local_keys: Sequence[str] | None,  # pylint: disable=unused-argument
        remote_keys: Sequence[str] | None,  # pylint: disable=unused-argument
        **options: Any,  # pylint: disable=unused-argument
    ):
        raise ProjectedBudgetExceeded(
            "The projected memory for link trial is 200.0 MiB, above the configured limit of 100.0 MiB.",
            context={"stage": "link trial", "limit_bytes": 100, "projected_bytes": 200},
        )


def context_service(
    *,
    baseline: LinkBaselineResult,
    trials: Sequence[LinkTrialResult] = (),
    trial_service: Any | None = None,
) -> tuple[LinkTroubleshooterService, StubBaselineService, Any, LinkExperimentContextStore, StubClock]:
    """Build a service over a stub clock and a recording baseline service."""
    clock = StubClock()
    store = LinkExperimentContextStore(clock=clock)
    baseline_service = StubBaselineService(baseline)
    service = LinkTroubleshooterService(
        baseline_service=baseline_service,  # type: ignore[arg-type]
        trial_service=trial_service if trial_service is not None else StubTrialService(trials),  # type: ignore[arg-type]
        context_store=store,
    )
    return service, baseline_service, service.trial_service, store, clock


async def open_default_context(service: LinkTroubleshooterService):
    """Open one context for the default test owner and project."""
    return await service.open_context(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        owner_principal_id="alice",
        project_locator="project-a",
    )


@pytest.mark.asyncio
async def test_open_context_retains_a_usable_snapshot() -> None:
    service, baseline_service, trial_service, store, _ = context_service(baseline=make_baseline(), trials=[trial_result()])

    response = await open_default_context(service)

    assert response.status == "reproduced"
    assert response.context_id is not None
    assert response.expires_at is not None
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "complete"
    assert response.baseline.output_rows == 2
    assert response.configured_keys is not None
    assert response.key_options is not None
    assert len(store) == 1
    assert len(baseline_service.calls) == 1
    assert trial_service.calls == [(["saved_code"], ["saved_value"])]


@pytest.mark.asyncio
async def test_open_context_reports_an_incomplete_diagnostic_without_totals() -> None:
    incomplete = trial_result(
        status="incomplete",
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        reason="row_limit_exceeded",
    )
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[incomplete])

    response = await open_default_context(service)

    assert response.context_id is not None
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "incomplete"
    assert response.baseline.diagnostic_reason == "row_limit_exceeded"
    assert response.baseline.input_a_rows is None
    assert response.baseline.output_rows is None
    assert response.baseline.unmatched_a_rows is None
    assert response.baseline.multiply_matched_a_rows is None


@pytest.mark.asyncio
async def test_open_context_keeps_failed_diagnostics_without_totals() -> None:
    failed = trial_result(
        status="failed",
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        reason="invalid_keys",
    )
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[failed])

    response = await open_default_context(service)

    assert response.context_id is not None
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "failed"
    assert response.baseline.input_a_rows is None


@pytest.mark.asyncio
async def test_open_context_treats_a_budget_rejection_as_an_incomplete_baseline() -> None:
    service, _, _, store, _ = context_service(baseline=make_baseline(), trial_service=RaisingTrialService())

    response = await open_default_context(service)

    assert response.context_id is not None
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "incomplete"
    assert response.baseline.diagnostic_reason == "projected_budget_exceeded"
    assert "MiB" in (response.baseline.diagnostic_message or "")
    assert response.baseline.output_rows is None
    assert len(store) == 1


@pytest.mark.asyncio
async def test_open_context_without_reproduction_returns_no_identifier() -> None:
    baseline = make_baseline(status="not_reproduced", include_context=False)
    service, _, trial_service, store, _ = context_service(baseline=baseline)

    response = await open_default_context(service)

    assert response.context_id is None
    assert response.expires_at is None
    assert response.status == "not_reproduced"
    assert response.baseline is None
    assert response.configured_keys is not None
    assert not trial_service.calls
    assert len(store) == 0


@pytest.mark.asyncio
async def test_read_context_reuses_the_snapshot_without_replaying() -> None:
    service, baseline_service, trial_service, _, clock = context_service(baseline=make_baseline(), trials=[trial_result()])
    opened = await open_default_context(service)
    clock.advance(timedelta(minutes=14))

    result = await service.read_context(context_id=opened.context_id or "", owner_principal_id="alice", project_locator="project-a")

    assert result.state == "found"
    assert result.response is not None
    assert result.response.context_id == opened.context_id
    assert result.response.expires_at == opened.expires_at
    assert result.response.baseline is not None
    assert result.response.baseline.unmatched_a_rows == 1
    assert len(baseline_service.calls) == 1
    assert trial_service.calls == [(["saved_code"], ["saved_value"])]


@pytest.mark.asyncio
async def test_read_context_reports_expiry_without_running_another_trial() -> None:
    service, baseline_service, trial_service, store, clock = context_service(baseline=make_baseline(), trials=[trial_result()])
    opened = await open_default_context(service)
    clock.advance(LINK_EXPERIMENT_CONTEXT_TTL)

    result = await service.read_context(context_id=opened.context_id or "", owner_principal_id="alice", project_locator="project-a")

    assert result.state == "expired"
    assert result.response is None
    assert len(store) == 0
    assert len(baseline_service.calls) == 1
    assert trial_service.calls == [(["saved_code"], ["saved_value"])]


@pytest.mark.asyncio
async def test_read_and_close_conceal_another_owners_context() -> None:
    service, _, _, store, _ = context_service(baseline=make_baseline(), trials=[trial_result()])
    opened = await open_default_context(service)

    context_id = opened.context_id or ""
    other_user = await service.read_context(context_id=context_id, owner_principal_id="mallory", project_locator="project-a")
    other_project = await service.read_context(context_id=context_id, owner_principal_id="alice", project_locator="project-b")

    assert other_user.state == "unavailable"
    assert other_project.state == "unavailable"
    assert await service.close_context(context_id=context_id, owner_principal_id="mallory", project_locator="project-a") is False
    assert len(store) == 1


@pytest.mark.asyncio
async def test_close_context_releases_the_snapshot() -> None:
    service, _, _, store, _ = context_service(baseline=make_baseline(), trials=[trial_result()])
    opened = await open_default_context(service)

    assert await service.close_context(context_id=opened.context_id or "", owner_principal_id="alice", project_locator="project-a") is True
    assert len(store) == 0

    after_close = await service.read_context(context_id=opened.context_id or "", owner_principal_id="alice", project_locator="project-a")
    assert after_close.state == "unavailable"


# ---------------------------------------------------------------------------
# Context trials
# ---------------------------------------------------------------------------


async def run_context_trial(
    service: LinkTroubleshooterService,
    context_id: str,
    *,
    local_keys: list[str] | None = None,
    remote_keys: list[str] | None = None,
    owner: str = "alice",
    project_locator: str = "project-a",
    **options: Any,
):
    """Run one context trial for the default test owner and project."""
    return await service.run_context_trial(
        context_id=context_id,
        owner_principal_id=owner,
        project_locator=project_locator,
        local_keys=local_keys or ["trial_code"],
        remote_keys=remote_keys or ["trial_value"],
        **options,
    )


@pytest.mark.asyncio
async def test_context_trial_reuses_the_snapshot_without_replaying() -> None:
    service, baseline_service, trial_service, _, _ = context_service(
        baseline=make_baseline(),
        trials=[trial_result(), trial_result(), trial_result()],
    )
    opened = await open_default_context(service)

    first = await run_context_trial(service, opened.context_id or "")
    second = await run_context_trial(service, opened.context_id or "", local_keys=["saved_code"], remote_keys=["saved_value"])

    assert first.state == "found" and first.response is not None
    assert second.state == "found" and second.response is not None
    assert first.response.context_id == opened.context_id
    assert first.response.expires_at == opened.expires_at
    assert second.response.expires_at == opened.expires_at
    assert len(baseline_service.calls) == 1
    assert len(trial_service.calls) == 3


@pytest.mark.asyncio
async def test_context_trial_forwards_only_the_requested_controls() -> None:
    service, _, trial_service, _, _ = context_service(baseline=make_baseline(), trials=[trial_result(), trial_result()])
    opened = await open_default_context(service)

    await run_context_trial(
        service,
        opened.context_id or "",
        how="left",
        allow_null_keys=True,
        null_keys_equal=False,
    )

    assert trial_service.option_calls[-1] == {
        "how": "left",
        "allow_null_keys": True,
        "null_keys_equal": False,
    }


@pytest.mark.asyncio
async def test_context_trial_rejects_expired_and_foreign_contexts() -> None:
    service, baseline_service, trial_service, store, clock = context_service(
        baseline=make_baseline(),
        trials=[trial_result(), trial_result()],
    )
    opened = await open_default_context(service)

    other_user = await run_context_trial(service, opened.context_id or "", owner="mallory")
    other_project = await run_context_trial(service, opened.context_id or "", project_locator="project-b")

    assert other_user.state == "unavailable"
    assert other_project.state == "unavailable"
    assert len(trial_service.calls) == 1

    clock.advance(LINK_EXPERIMENT_CONTEXT_TTL)
    expired = await run_context_trial(service, opened.context_id or "")

    assert expired.state == "expired"
    assert expired.response is None
    assert len(store) == 0
    assert len(baseline_service.calls) == 1
    assert len(trial_service.calls) == 1


@pytest.mark.asyncio
async def test_context_trial_keeps_an_incomplete_baseline_without_totals() -> None:
    incomplete = trial_result(
        status="incomplete",
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        reason="row_limit_exceeded",
    )
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[incomplete, trial_result()])
    opened = await open_default_context(service)

    result = await run_context_trial(service, opened.context_id or "")

    assert result.state == "found" and result.response is not None
    assert result.response.baseline is not None
    assert result.response.baseline.diagnostic_status == "incomplete"
    assert result.response.baseline.output_rows is None
    assert result.response.trial.totals is not None
    assert result.response.trial.detail is not None


@pytest.mark.asyncio
async def test_context_trial_does_not_mutate_frames_or_saved_project(tmp_path) -> None:
    baseline = make_baseline()

    assert baseline.local_rows is not None
    assert baseline.remote_rows is not None

    local_before = baseline.local_rows.copy(deep=True)
    remote_before = baseline.remote_rows.copy(deep=True)
    saved_fk = baseline._foreign_key
    assert saved_fk is not None
    saved_fk_data = deepcopy(saved_fk.fk_cfg)

    service, _, trial_service, _, _ = context_service(baseline=baseline)
    service.trial_service = LinkTrialService(
        settings=Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]
    )
    opened = await open_default_context(service)

    result = await run_context_trial(service, opened.context_id or "", local_keys=["trial_code"], remote_keys=["trial_value"])

    assert result.state == "found" and result.response is not None
    assert result.response.trial.status == "complete"
    pd.testing.assert_frame_equal(baseline.local_rows, local_before)
    pd.testing.assert_frame_equal(baseline.remote_rows, remote_before)
    assert saved_fk.fk_cfg == saved_fk_data
    assert trial_service is not service.trial_service


# ---------------------------------------------------------------------------
# Affected-row browsing
# ---------------------------------------------------------------------------


def retained_exception_groups(*, unmatched_total: int, retained_rows: int) -> TrialExceptionGroups:
    """Build retained exception groups with a full count and up to the browse cap of rows."""
    rows = tuple(
        TrialExceptionRow(
            input_position=index,
            key_values=("missing",),
            remote_match_count=0,
            output_row_contribution=0,
        )
        for index in range(retained_rows)
    )
    return TrialExceptionGroups(
        unmatched=TrialExceptionGroup(total_count=unmatched_total, rows=rows),
        multiply_matched=TrialExceptionGroup(total_count=0, rows=()),
    )


def trial_with_groups(groups: TrialExceptionGroups | None) -> LinkTrialResult:
    """Build one complete trial that carries the given exception groups."""
    return LinkTrialResult(
        status="complete",
        reason="complete",
        message="Trial result.",
        input_a_rows=3,
        output_rows=2,
        unmatched_a_rows=groups.unmatched.total_count if groups is not None else None,
        multiply_matched_a_rows=groups.multiply_matched.total_count if groups is not None else None,
        exception_groups=groups,
    )


@pytest.mark.asyncio
async def test_read_exception_rows_slices_the_retained_baseline_page() -> None:
    """A baseline page is sliced from the retained rows and keeps the full count."""
    groups = retained_exception_groups(unmatched_total=150, retained_rows=150)
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[trial_with_groups(groups)])
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="baseline",
        group="unmatched",
        offset=100,
        limit=100,
    )

    assert result.state == "found"
    assert result.page is not None
    assert result.page.status == "available"
    assert result.page.total_count == 150
    assert result.page.browse_cap == 25_000
    assert result.page.browse_cap_reached is False
    assert result.page.returned_count == 50
    assert [row.input_position for row in result.page.rows] == list(range(100, 150))


@pytest.mark.asyncio
async def test_read_exception_rows_reports_when_the_browse_cap_is_reached() -> None:
    """The browse cap is reported even though only the capped rows are retained."""
    groups = retained_exception_groups(unmatched_total=30_000, retained_rows=5)
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[trial_with_groups(groups)])
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="baseline",
        group="unmatched",
        offset=0,
        limit=100,
    )

    assert result.page is not None
    assert result.page.total_count == 30_000
    assert result.page.browse_cap_reached is True
    assert result.page.returned_count == 5


@pytest.mark.asyncio
async def test_read_exception_rows_requires_trial_controls_for_the_trial_side() -> None:
    """Trial rows are recomputed, so browsing them requires the trial controls."""
    groups = retained_exception_groups(unmatched_total=5, retained_rows=5)
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[trial_with_groups(groups)])
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="trial",
        group="unmatched",
        offset=0,
        limit=100,
    )

    assert result.state == "found"
    assert result.page is not None
    assert result.page.status == "unavailable"
    assert result.page.reason == "trial_required"


@pytest.mark.asyncio
async def test_read_exception_rows_recomputes_the_trial_side() -> None:
    """A trial page recomputes the trial from retained inputs and pages its rows."""
    baseline_groups = retained_exception_groups(unmatched_total=3, retained_rows=3)
    trial_groups = retained_exception_groups(unmatched_total=140, retained_rows=140)
    service, _, trial_service, _, _ = context_service(
        baseline=make_baseline(),
        trials=[trial_with_groups(baseline_groups), trial_with_groups(trial_groups)],
    )
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="trial",
        group="unmatched",
        offset=0,
        limit=100,
        trial_request=LinkExperimentTrialRequest(local_keys=["trial_code"], remote_keys=["trial_value"]),
    )

    assert result.page is not None
    assert result.page.status == "available"
    assert result.page.total_count == 140
    assert result.page.returned_count == 100
    assert trial_service.calls[-1] == (["trial_code"], ["trial_value"])


@pytest.mark.asyncio
async def test_read_exception_rows_stops_at_the_default_browse_cap() -> None:
    """A large affected set keeps its full count but only the browse cap is browsable."""
    cap = 25_000
    groups = retained_exception_groups(unmatched_total=30_000, retained_rows=cap)
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[trial_with_groups(groups)])
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="baseline",
        group="unmatched",
        offset=24_800,
        limit=500,
    )

    assert result.page is not None
    assert result.page.total_count == 30_000
    assert result.page.browse_cap == cap
    assert result.page.browse_cap_reached is True
    assert result.page.returned_count == 200
    assert [row.input_position for row in result.page.rows] == list(range(24_800, cap))


@pytest.mark.asyncio
async def test_read_exception_rows_reports_an_incomplete_diagnostic() -> None:
    """An incomplete configured-key diagnostic has no affected rows to browse."""
    service, _, _, _, _ = context_service(
        baseline=make_baseline(),
        trials=[
            trial_result(
                status="incomplete",
                input_rows=None,
                output_rows=None,
                unmatched_rows=None,
                multiply_matched_rows=None,
                reason="row_limit_exceeded",
            )
        ],
    )
    opened = await open_default_context(service)

    result = await service.read_exception_rows(
        context_id=opened.context_id or "",
        owner_principal_id="alice",
        project_locator="project-a",
        side="baseline",
        group="unmatched",
        offset=0,
        limit=100,
    )

    assert result.page is not None
    assert result.page.status == "unavailable"
    assert result.page.reason == "diagnostic_incomplete"


@pytest.mark.asyncio
async def test_read_exception_rows_conceals_an_unavailable_context() -> None:
    """An unknown identifier returns the unavailable state without a page."""
    service, _, _, _, _ = context_service(baseline=make_baseline(), trials=[trial_with_groups(None)])

    result = await service.read_exception_rows(
        context_id="unknown",
        owner_principal_id="alice",
        project_locator="project-a",
        side="baseline",
        group="unmatched",
        offset=0,
        limit=100,
    )

    assert result.state == "unavailable"
    assert result.page is None
