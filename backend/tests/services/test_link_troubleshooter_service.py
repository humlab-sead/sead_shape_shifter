"""Tests for link troubleshooter orchestration and read-only integration."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app.core.config import Settings
from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.services.link_baseline_service import LinkBaselineResult, LinkBaselineService
from backend.app.services.link_experiment_context_store import LINK_EXPERIMENT_CONTEXT_TTL, LinkExperimentContextStore
from backend.app.services.link_trial_service import ARowTrialDiagnostic, LinkTrialResult, LinkTrialService
from backend.app.services.link_troubleshooter_service import LinkTroubleshooterService
from backend.app.utils.caches import ShapeShiftCache, ShapeShiftProjectCache
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


class StubProjectService:
    """Return one in-memory API project to the baseline service."""

    def __init__(self, api_project) -> None:
        self.api_project = api_project

    def load_project(self, project_name: str, force_reload: bool = False):  # pylint: disable=unused-argument
        return self.api_project.model_copy(deep=True)


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


def service_for(baseline: LinkBaselineResult, trials: Sequence[LinkTrialResult]) -> tuple[LinkTroubleshooterService, StubTrialService]:
    """Build a service with recorded baseline and trial dependencies."""
    trial_service = StubTrialService(trials)
    service = LinkTroubleshooterService(
        baseline_service=StubBaselineService(baseline),  # type: ignore[arg-type]
        trial_service=trial_service,  # type: ignore[arg-type]
    )
    return service, trial_service


@pytest.mark.asyncio
async def test_configured_keys_run_once_and_reuse_diagnostics_for_requested_trial() -> None:
    baseline = make_baseline()
    trial = trial_result()
    service, trial_service = service_for(baseline, [trial])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={"fk_index": 0},
    )

    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "complete"
    assert response.baseline.unmatched_a_rows == 1
    assert response.trial is not None
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 2
    assert trial_service.calls == [(["saved_code"], ["saved_value"])]


@pytest.mark.asyncio
async def test_alternative_keys_keep_configured_diagnostics_and_allow_different_output_count() -> None:
    service, trial_service = service_for(make_baseline(), [trial_result(), trial_result(output_rows=4)])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
    )

    assert response.baseline is not None
    assert response.baseline.output_rows == 2
    assert response.baseline.diagnostic_status == "complete"
    assert response.trial is not None
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 4
    assert trial_service.calls == [(["saved_code"], ["saved_value"]), (["trial_code"], ["trial_value"])]


@pytest.mark.asyncio
async def test_one_missing_key_list_returns_invalid_keys_without_hiding_baseline_diagnostics() -> None:
    service, _ = service_for(make_baseline(), [trial_result(), trial_result(status="failed", reason="invalid_keys")])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        local_keys=["trial_code"],
    )

    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "complete"
    assert response.baseline.unmatched_a_rows == 1
    assert response.trial is not None
    assert response.trial.status == "failed"
    assert response.trial.reason == "invalid_keys"
    assert response.trial.totals is None
    assert response.trial.rows == []
    assert response.trial.pagination is None


@pytest.mark.asyncio
async def test_non_reproduced_baseline_keeps_fk_details_and_skips_trials() -> None:
    baseline = make_baseline(status="not_reproduced", include_context=False)
    service, trial_service = service_for(baseline, [])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
    )

    assert response.status == "not_reproduced"
    assert response.relationship is not None
    assert response.relationship.remote_entity == "customers"
    assert response.configured_keys is not None
    assert response.configured_keys.local_keys == ["saved_code"]
    assert response.key_options is None
    assert response.trial is None
    assert not trial_service.calls


@pytest.mark.asyncio
async def test_reproduced_baseline_with_missing_context_is_downgraded_without_trial() -> None:
    baseline = make_baseline(include_context=False)
    service, trial_service = service_for(baseline, [])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
    )

    assert response.status == "not_reproduced"
    assert response.reason == "baseline_context_missing"
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "not_run"
    assert response.trial is None
    assert not trial_service.calls


@pytest.mark.asyncio
async def test_baseline_count_mismatch_disables_only_baseline_trial_totals() -> None:
    service, trial_service = service_for(make_baseline(), [trial_result(output_rows=3)])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
    )

    assert response.baseline is not None
    assert response.baseline.output_rows == 2
    assert response.baseline.diagnostic_status == "failed"
    assert response.baseline.diagnostic_reason == "baseline_counts_mismatch"
    assert response.baseline.unmatched_a_rows is None
    assert response.trial is not None
    assert response.trial.status == "failed"
    assert response.trial.reason == "baseline_counts_mismatch"
    assert response.trial.totals is None
    assert response.trial.rows == []
    assert trial_service.calls == [(["saved_code"], ["saved_value"])]


@pytest.mark.asyncio
async def test_requested_trial_input_mismatch_removes_trial_totals_and_rows() -> None:
    service, _ = service_for(make_baseline(), [trial_result(), trial_result(input_rows=2, output_rows=4)])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
    )

    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "complete"
    assert response.trial is not None
    assert response.trial.status == "failed"
    assert response.trial.reason == "baseline_input_mismatch"
    assert response.trial.totals is None
    assert response.trial.rows == []
    assert response.trial.pagination is None


@pytest.mark.asyncio
async def test_incomplete_configured_trial_does_not_hide_complete_alternative_trial() -> None:
    service, _ = service_for(
        make_baseline(),
        [
            trial_result(status="incomplete", input_rows=None, output_rows=None, rows=None, reason="row_limit_exceeded"),
            trial_result(output_rows=4),
        ],
    )

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
    )

    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "incomplete"
    assert response.baseline.diagnostic_reason == "row_limit_exceeded"
    assert response.baseline.unmatched_a_rows is None
    assert response.trial is not None
    assert response.trial.status == "complete"
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 4


@pytest.mark.asyncio
async def test_key_options_hide_unconfigured_system_ids_but_keep_configured_ids() -> None:
    baseline = make_baseline(remote_keys=["system_id"])
    service, trial_service = service_for(baseline, [trial_result()])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
    )

    assert response.key_options is not None
    assert "system_id" not in response.key_options.local
    assert "system_id" in response.key_options.remote
    assert trial_service.calls == [(["saved_code"], ["system_id"])]


@pytest.mark.asyncio
async def test_pagination_filters_rows_without_changing_trial_totals_or_serializing_frames() -> None:
    rows = (
        ARowTrialDiagnostic(0, ("A",), True, 1, 1),
        ARowTrialDiagnostic(1, ("missing-1",), False, 0, 0),
        ARowTrialDiagnostic(2, ("missing-2",), False, 0, 0),
    )
    service, _ = service_for(make_baseline(), [trial_result(rows=rows)])

    response = await service.run(
        project_name="project-a",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata={},
        page=1,
        page_size=1,
        row_filter="unmatched",
    )

    assert response.trial is not None
    assert response.trial.totals is not None
    assert response.trial.totals.input_a_rows == 3
    assert response.trial.pagination is not None
    assert response.trial.pagination.filtered_row_count == 2
    assert response.trial.pagination.returned_row_count == 1
    assert response.trial.pagination.has_next is True
    assert response.trial.rows[0].input_position == 1
    payload = response.model_dump()
    assert "local_rows" not in payload
    assert "_saved_project" not in payload
    assert "_foreign_key" not in payload


def fixed_project_config(
    *,
    how: str = "inner",
    local_values: list[list[Any]] | None = None,
    remote_values: list[list[Any]] | None = None,
    local_keys: list[str] | None = None,
    remote_keys: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the small fixed-entity project used for real baseline and trial tests."""
    local_columns = ["order_code", "saved_code", "alternate_code"]
    remote_columns = ["saved_value", "alternate_value"]
    fk: dict[str, Any] = {
        "entity": "customers",
        "local_keys": local_keys or ["saved_code"],
        "remote_keys": remote_keys or ["saved_value"],
        "how": how,
        "constraints": constraints or {"allow_row_decrease": True},
    }
    return {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": local_columns,
                "values": local_values or [["O1", "A", "X"], ["O2", "B", "Y"], ["O3", "missing", "Z"]],
                "foreign_keys": [fk],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["saved_value"],
                "columns": remote_columns,
                "values": remote_values or [["A", "X"], ["B", "X"], ["C", "Y"]],
            },
        }
    }


async def run_live_troubleshooter(
    cfg: dict[str, Any],
    *,
    tmp_path,
    row_count_before: int = 3,
    row_count_after: int,
    local_keys: list[str] | None = None,
    remote_keys: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
    row_filter: str = "all",
    trial_limit: int = 100,
) -> tuple[Any, Any]:
    """Run orchestration with the production baseline and trial services."""
    api_project = ProjectMapper.to_api_config(cfg, name="link-troubleshooter-test")
    saved_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]
    baseline_service = LinkBaselineService(project_service=StubProjectService(api_project))  # type: ignore[arg-type]
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path, LINK_TRIAL_MAX_OUTPUT_ROWS=trial_limit)
    service = LinkTroubleshooterService(baseline_service=baseline_service, trial_service=LinkTrialService(settings=settings))
    metadata = {
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
        "link_pass": "initial",
        "join_type": fk.how or "inner",
        "row_count_before": row_count_before,
        "row_count_after": row_count_after,
    }
    response = await service.run(
        project_name="link-troubleshooter-test",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=metadata,
        local_keys=local_keys,
        remote_keys=remote_keys,
        page=page,
        page_size=page_size,
        row_filter=row_filter,
    )
    return response, api_project


@pytest.mark.asyncio
async def test_real_inner_and_left_links_reproduce_and_complete_configured_trials(tmp_path) -> None:
    inner, _ = await run_live_troubleshooter(fixed_project_config(), tmp_path=tmp_path, row_count_after=2)
    assert inner.status == "reproduced"
    assert inner.baseline is not None
    assert inner.baseline.diagnostic_status == "complete"
    assert inner.trial is not None
    assert inner.trial.status == "complete"
    assert inner.trial.totals is not None
    assert inner.trial.totals.output_rows == 2

    left, _ = await run_live_troubleshooter(
        fixed_project_config(
            how="left",
            local_values=[["O1", "A", "X"], ["O2", "missing", "Z"]],
            remote_values=[["A", "X"], ["A", "X"]],
            constraints={"allow_row_decrease": True, "allow_unmatched_left": True},
        ),
        tmp_path=tmp_path,
        row_count_before=2,
        row_count_after=3,
    )
    assert left.status == "reproduced"
    assert left.baseline is not None
    assert left.baseline.diagnostic_status == "complete"
    assert left.trial is not None
    assert left.trial.status == "complete"
    assert left.trial.totals is not None
    assert left.trial.totals.output_rows == 3


@pytest.mark.asyncio
async def test_real_alternative_keys_can_change_output_and_stale_signature_is_ineligible(tmp_path) -> None:
    cfg = fixed_project_config()
    response, api_project = await run_live_troubleshooter(
        cfg,
        tmp_path=tmp_path,
        row_count_after=2,
        local_keys=["alternate_code"],
        remote_keys=["alternate_value"],
    )
    assert response.baseline is not None
    assert response.baseline.output_rows == 2
    assert response.trial is not None
    assert response.trial.status == "complete"
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 3

    saved_project = ProjectMapper.to_core(api_project)
    fk = saved_project.get_table("orders").foreign_keys[0]
    stale_metadata = {
        "fk_index": 0,
        "fk_signature": "stale-signature",
        "link_pass": "initial",
        "join_type": "inner",
        "row_count_before": 3,
        "row_count_after": 2,
    }
    baseline_service = LinkBaselineService(project_service=StubProjectService(api_project))  # type: ignore[arg-type]
    stale = await baseline_service.build_baseline(
        project_name="link-troubleshooter-test",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=stale_metadata,
    )
    assert stale.status == "ineligible"
    assert stale.reason == "signature_mismatch"
    assert fk.identity_signature != stale_metadata["fk_signature"]


@pytest.mark.asyncio
async def test_real_configured_system_id_key_is_available_and_runs_as_the_default_pair(tmp_path) -> None:
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_ref"],
                "values": [["O1", 1], ["O2", 2], ["O3", 99]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_ref"],
                        "remote_keys": ["system_id"],
                        "how": "inner",
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["customer_name"],
                "columns": ["customer_name"],
                "values": [["Alpha"], ["Beta"], ["Gamma"]],
            },
        }
    }

    response, _ = await run_live_troubleshooter(cfg, tmp_path=tmp_path, row_count_after=2)

    assert response.status == "reproduced"
    assert response.configured_keys is not None
    assert response.configured_keys.local_keys == ["customer_ref"]
    assert response.configured_keys.remote_keys == ["system_id"]
    assert response.key_options is not None
    assert "system_id" in response.key_options.remote
    assert response.trial is not None
    assert response.trial.status == "complete"
    assert response.trial.local_keys == ["customer_ref"]
    assert response.trial.remote_keys == ["system_id"]
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 2


@pytest.mark.asyncio
async def test_real_over_limit_trial_is_incomplete_and_paged_findings_keep_totals(tmp_path) -> None:
    limited, _ = await run_live_troubleshooter(
        fixed_project_config(),
        tmp_path=tmp_path,
        row_count_after=2,
        trial_limit=1,
    )
    assert limited.status == "reproduced"
    assert limited.baseline is not None
    assert limited.baseline.diagnostic_status == "incomplete"
    assert limited.trial is not None
    assert limited.trial.status == "incomplete"
    assert limited.trial.reason == "row_limit_exceeded"
    assert limited.trial.totals is None
    assert limited.trial.rows == []

    paged, _ = await run_live_troubleshooter(
        fixed_project_config(),
        tmp_path=tmp_path,
        row_count_after=2,
        page_size=1,
        row_filter="unmatched",
    )
    assert paged.trial is not None
    assert paged.trial.totals is not None
    assert paged.trial.totals.input_a_rows == 3
    assert paged.trial.pagination is not None
    assert paged.trial.pagination.filtered_row_count == 1
    assert paged.trial.pagination.returned_row_count == 1


@pytest.mark.asyncio
async def test_real_troubleshooter_does_not_read_or_write_caches_or_mutate_saved_project(tmp_path) -> None:
    cfg = fixed_project_config()
    api_project = ProjectMapper.to_api_config(cfg, name="link-troubleshooter-test")
    before = deepcopy(api_project.model_dump())
    saved_project = ProjectMapper.to_core(api_project)
    fk = saved_project.get_table("orders").foreign_keys[0]
    baseline_service = LinkBaselineService(project_service=StubProjectService(api_project))  # type: ignore[arg-type]
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path, LINK_TRIAL_MAX_OUTPUT_ROWS=100)
    service = LinkTroubleshooterService(baseline_service=baseline_service, trial_service=LinkTrialService(settings=settings))
    metadata = {
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
        "link_pass": "initial",
        "join_type": "inner",
        "row_count_before": 3,
        "row_count_after": 2,
    }

    with (
        patch.object(ShapeShiftCache, "set_dataframe", side_effect=AssertionError("dataframe cache write")),
        patch.object(ShapeShiftCache, "set_table_store", side_effect=AssertionError("table-store cache write")),
        patch.object(ShapeShiftCache, "fetch_cached_entity_data", side_effect=AssertionError("cache read")),
        patch.object(ShapeShiftProjectCache, "get_project", side_effect=AssertionError("project cache read")),
    ):
        response = await service.run(
            project_name="link-troubleshooter-test",
            issue_type="row_count_mismatch",
            local_entity="orders",
            metadata=metadata,
        )

    assert response.status == "reproduced"
    assert api_project.model_dump() == before


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
