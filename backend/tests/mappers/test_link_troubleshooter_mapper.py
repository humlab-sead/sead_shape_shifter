"""Tests for the bounded foreign-key troubleshooter response mapper."""

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import pytest

from backend.app.mappers.link_troubleshooter_mapper import LinkTroubleshooterMapper
from backend.app.models.link_troubleshooter import EXCEPTION_ROW_PAGE_SIZE
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_experiment_context_store import (
    JoinTypeSetting,
    LinkExperimentDiagnostics,
    RequestedSetting,
    ResolvedNullPolicy,
    TrialExceptionGroup,
    TrialExceptionGroups,
    TrialExceptionRow,
    TrialSettingsReport,
)
from backend.app.services.link_trial_service import ARowTrialDiagnostic, LinkTrialResult
from src.specifications.constraints import ValidationIssue

EXPIRES_AT = datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc)


def settings_report(
    *,
    join_requested: str | None = None,
    join_source: str = "inherited",
    join_effective: str = "inner",
    allow_requested: bool | None = None,
    allow_source: str = "inherited",
    null_equal_requested: bool | None = None,
    null_equal_source: str = "inherited",
    strict_null_keys: bool = True,
    prevent_null_matches: bool = False,
) -> TrialSettingsReport:
    """Build one resolved settings report for mapper tests."""
    return TrialSettingsReport(
        join_type=JoinTypeSetting(  # type: ignore[arg-type]
            requested=join_requested,
            source=join_source,
            effective=join_effective,
        ),
        allow_null_keys=RequestedSetting(requested=allow_requested, source=allow_source),  # type: ignore[arg-type]
        null_keys_equal=RequestedSetting(requested=null_equal_requested, source=null_equal_source),  # type: ignore[arg-type]
        resolved_null_policy=ResolvedNullPolicy(
            enforce_strict_null_keys=strict_null_keys,
            prevent_null_key_matches=prevent_null_matches,
        ),
    )


def exception_groups(
    *,
    unmatched_total: int,
    unmatched_rows: tuple[TrialExceptionRow, ...],
    multiply_total: int = 0,
    multiply_rows: tuple[TrialExceptionRow, ...] = (),
) -> TrialExceptionGroups:
    """Build exception groups for mapper tests."""
    return TrialExceptionGroups(
        unmatched=TrialExceptionGroup(total_count=unmatched_total, rows=unmatched_rows),
        multiply_matched=TrialExceptionGroup(total_count=multiply_total, rows=multiply_rows),
    )


def linker_issue(message: str) -> ValidationIssue:
    """Return one warning for mapper tests."""
    return ValidationIssue(
        issue_type="row_count_mismatch",
        severity="warning",
        local_entity="orders",
        remote_entity="customers",
        message=message,
        metadata={"join_type": "inner"},
    )


def reproduced_baseline(
    *,
    row_count_before: int | None = 3,
    row_count_after: int | None = 2,
    issues: tuple[ValidationIssue, ...] = (),
) -> LinkBaselineResult:
    """Build a baseline result without private frame or project context."""
    return LinkBaselineResult(
        status="reproduced",
        reason="reproduced",
        message="The warning was reproduced.",
        entity_name="orders",
        remote_entity="customers",
        fk_index=0,
        link_pass="initial",
        row_count_before=row_count_before,
        row_count_after=row_count_after,
        issues=issues,
    )


def trial_result(
    *,
    status: str = "complete",
    input_rows: int | None = 3,
    output_rows: int | None = 4,
    unmatched_rows: int | None = 1,
    multiply_matched_rows: int | None = 1,
    a_rows: tuple[ARowTrialDiagnostic, ...] | None = (),
    reason: str = "complete",
    message: str = "Trial completed.",
    issues: tuple[ValidationIssue, ...] = (),
    groups: TrialExceptionGroups | None = None,
    settings: TrialSettingsReport | None = None,
) -> LinkTrialResult:
    """Build a link trial result for mapper tests."""
    return LinkTrialResult(
        status=status,  # type: ignore[arg-type]
        reason=reason,
        message=message,
        input_a_rows=input_rows,
        output_rows=output_rows,
        unmatched_a_rows=unmatched_rows,
        multiply_matched_a_rows=multiply_matched_rows,
        a_rows=a_rows,
        issues=issues,
        exception_groups=groups,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Retained context comparison
# ---------------------------------------------------------------------------


def context_diagnostics(
    *,
    groups: TrialExceptionGroups | None,
    issues: tuple[ValidationIssue, ...] = (),
    status: str = "complete",
    settings: TrialSettingsReport | None = None,
) -> LinkExperimentDiagnostics:
    """Build retained diagnostics for context mapper tests."""
    is_complete: bool = status == "complete"
    return LinkExperimentDiagnostics(
        status=status,  # type: ignore[arg-type]
        input_a_rows=3 if is_complete else None,
        output_rows=3 if is_complete else None,
        unmatched_a_rows=(groups.unmatched.total_count if is_complete and groups is not None else None),
        multiply_matched_a_rows=(groups.multiply_matched.total_count if is_complete and groups is not None else None),
        issues=issues,
        exception_groups=groups if is_complete else None,
        settings=settings,
    )


def map_context_trial(
    *,
    diagnostics: LinkExperimentDiagnostics,
    trial: LinkTrialResult,
    row_cap: int = 100,
):
    """Map one context trial with a reproduced baseline."""
    return LinkTroubleshooterMapper.to_context_trial_response(
        context_id="context-1",
        expires_at=EXPIRES_AT,
        baseline=reproduced_baseline(),
        diagnostics=diagnostics,
        trial=trial,
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
        row_cap=row_cap,
    )


def exception_row(position: int, value: Any = "missing") -> TrialExceptionRow:
    """Build one exception row for mapper tests."""
    return TrialExceptionRow(
        input_position=position,
        key_values=(value,),
        remote_match_count=0,
        output_row_contribution=0,
    )


def test_context_trial_response_reports_exact_counts_and_bounded_detail() -> None:
    unmatched_rows = tuple(exception_row(position) for position in range(100))
    groups = exception_groups(unmatched_total=150, unmatched_rows=unmatched_rows, multiply_total=4)
    diagnostics = context_diagnostics(groups=groups, settings=settings_report())
    trial = trial_result(
        input_rows=3,
        output_rows=12,
        unmatched_rows=150,
        multiply_matched_rows=4,
        groups=groups,
        settings=settings_report(join_requested="left", join_source="explicit", join_effective="left"),
    )

    response = map_context_trial(diagnostics=diagnostics, trial=trial, row_cap=100)

    assert response.context_id == "context-1"
    assert response.trial.totals is not None
    assert response.trial.totals.unmatched_a_rows == 150
    assert response.trial.detail is not None
    assert response.trial.detail.unmatched is not None
    assert response.trial.detail.unmatched.total_count == 150
    assert response.trial.detail.unmatched.returned_count == 100
    assert response.trial.detail.unmatched.row_cap == 100
    assert response.trial.detail.unmatched.row_cap_reached is True
    assert response.trial.detail.multiply_matched is not None
    assert response.trial.detail.multiply_matched.total_count == 4
    assert response.trial.detail.multiply_matched.returned_count == 0
    assert response.trial.detail.multiply_matched.row_cap_reached is False
    assert [row.input_position for row in response.trial.detail.unmatched.rows] == list(range(100))
    assert response.trial.settings is not None
    assert response.trial.settings.join_type.effective == "left"
    assert response.baseline is not None
    assert response.baseline.settings is not None
    assert response.baseline.detail is not None
    assert response.baseline.detail.unmatched is not None
    assert response.baseline.detail.unmatched.total_count == 150
    response.model_dump_json()


def test_context_detail_key_values_are_json_safe_for_pandas_and_numpy_scalars() -> None:
    values: tuple[Any, ...] = (
        np.int64(12),
        np.float64(3.5),
        np.bool_(True),
        None,
        float("nan"),
        pd.NA,
        ["nested", 1],
        {"nested": True},
    )
    row = TrialExceptionRow(input_position=0, key_values=values, remote_match_count=1, output_row_contribution=1)
    groups = exception_groups(unmatched_total=1, unmatched_rows=(row,))
    trial = trial_result(groups=groups, settings=settings_report())

    response = map_context_trial(diagnostics=context_diagnostics(groups=groups), trial=trial)

    assert response.trial.detail is not None
    assert response.trial.detail.unmatched is not None
    assert [value.value for value in response.trial.detail.unmatched.rows[0].key_values] == [
        12,
        3.5,
        True,
        None,
        None,
        None,
        ["nested", 1],
        {"nested": True},
    ]
    response.model_dump_json()


def test_context_trial_response_limits_findings_and_marks_truncation() -> None:
    issues = tuple(linker_issue(f"warning {index}") for index in range(60))
    trial = trial_result(issues=issues, groups=exception_groups(unmatched_total=0, unmatched_rows=()))

    response = map_context_trial(diagnostics=context_diagnostics(groups=None), trial=trial)

    assert response.trial.detail is not None
    assert response.trial.detail.findings.total_count == 60
    assert response.trial.detail.findings.returned_count == 50
    assert response.trial.detail.findings.truncated is True
    assert response.trial.detail.detail_truncated is True


@pytest.mark.parametrize(
    ("value", "expected_truncated", "expected_length"),
    [
        ("x" * 255, False, None),
        ("x" * 256, False, None),
        ("x" * 257, True, 257),
        ("é" * 128, False, None),
        ("é" * 129, True, 129),
    ],
)
def test_context_trial_response_bounds_key_values_at_whole_code_points(
    value: str,
    expected_truncated: bool,
    expected_length: int | None,
) -> None:
    groups = exception_groups(unmatched_total=1, unmatched_rows=(exception_row(0, value),))
    trial = trial_result(groups=groups)

    response = map_context_trial(diagnostics=context_diagnostics(groups=None), trial=trial)

    assert response.trial.detail is not None
    assert response.trial.detail.unmatched is not None
    key_value = response.trial.detail.unmatched.rows[0].key_values[0]
    assert key_value.truncated is expected_truncated
    assert key_value.original_length == expected_length
    if expected_truncated:
        assert isinstance(key_value.value, str)
        assert len(key_value.value.encode("utf-8")) <= 256
        assert "�" not in key_value.value
    else:
        assert key_value.value == value


def test_context_trial_response_budgets_each_side_independently() -> None:
    def long_row(position: int) -> TrialExceptionRow:
        return TrialExceptionRow(
            input_position=position,
            key_values=tuple("v" * 200 for _ in range(12)),
            remote_match_count=2,
            output_row_contribution=2,
        )

    big_rows = tuple(long_row(position) for position in range(100))
    trial_groups = exception_groups(
        unmatched_total=100,
        unmatched_rows=big_rows,
        multiply_total=100,
        multiply_rows=big_rows,
    )
    baseline_groups = exception_groups(
        unmatched_total=1,
        unmatched_rows=(TrialExceptionRow(0, ("small",), 0, 0),),
    )
    trial = trial_result(groups=trial_groups)

    response = map_context_trial(diagnostics=context_diagnostics(groups=baseline_groups), trial=trial)

    assert response.baseline is not None and response.baseline.detail is not None
    assert response.baseline.detail.unmatched is not None
    assert response.baseline.detail.unmatched.returned_count == 1
    assert response.baseline.detail.unmatched.budget_exhausted is False

    assert response.trial.detail is not None
    assert response.trial.detail.unmatched is not None
    assert response.trial.detail.unmatched.returned_count == 100
    assert response.trial.detail.unmatched.budget_exhausted is False
    assert response.trial.detail.multiply_matched is not None
    assert response.trial.detail.multiply_matched.returned_count < 100
    assert response.trial.detail.multiply_matched.budget_exhausted is True
    assert response.trial.detail.detail_truncated is True


@pytest.mark.parametrize("status", ["failed", "incomplete"])
def test_context_trial_response_keeps_failed_or_incomplete_trials_out_of_success_shape(status: str) -> None:
    trial = trial_result(
        status=status,
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        a_rows=None,
        reason="invalid_keys" if status == "failed" else "row_limit_exceeded",
        message="The requested trial is unavailable.",
        groups=None,
        settings=settings_report(),
    )

    response = map_context_trial(diagnostics=context_diagnostics(groups=None), trial=trial)

    assert response.trial.status == status
    assert response.trial.totals is None
    assert response.trial.detail is None
    assert response.trial.settings is not None
    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "complete"


def test_context_trial_response_keeps_incomplete_baseline_without_totals_or_groups() -> None:
    diagnostics = context_diagnostics(
        groups=None,
        status="incomplete",
        issues=(linker_issue("diagnostics exceeded the row limit"),),
        settings=settings_report(),
    )
    trial = trial_result(groups=exception_groups(unmatched_total=0, unmatched_rows=()))

    response = map_context_trial(diagnostics=diagnostics, trial=trial)

    assert response.baseline is not None
    assert response.baseline.diagnostic_status == "incomplete"
    assert response.baseline.input_a_rows is None
    assert response.baseline.output_rows is None
    assert response.baseline.unmatched_a_rows is None
    assert response.baseline.multiply_matched_a_rows is None
    assert response.baseline.detail is not None
    assert response.baseline.detail.unmatched is None
    assert response.baseline.detail.multiply_matched is None
    assert response.trial.totals is not None


def test_context_detail_carries_only_the_first_browse_page() -> None:
    """A large affected-row window is paged, so the detail keeps one bounded page."""
    unmatched_rows = tuple(exception_row(position) for position in range(250))
    groups = exception_groups(unmatched_total=250, unmatched_rows=unmatched_rows)
    diagnostics = context_diagnostics(groups=groups)

    response = map_context_trial(
        diagnostics=diagnostics,
        trial=trial_result(unmatched_rows=250, groups=groups),
        row_cap=10_000,
    )

    assert response.trial.detail is not None
    assert response.trial.detail.unmatched is not None
    assert response.trial.detail.unmatched.total_count == 250
    assert response.trial.detail.unmatched.returned_count == EXCEPTION_ROW_PAGE_SIZE
    assert response.trial.detail.unmatched.row_cap == 10_000
    assert response.trial.detail.unmatched.row_cap_reached is False
    assert [row.input_position for row in response.trial.detail.unmatched.rows] == list(range(EXCEPTION_ROW_PAGE_SIZE))


def test_exception_rows_page_reports_full_count_and_browse_cap() -> None:
    """A page slice keeps the full affected-row count and the browse cap state."""
    rows = tuple(exception_row(position) for position in range(120))

    page = LinkTroubleshooterMapper.to_exception_rows_page(
        side="baseline",
        group="unmatched",
        offset=100,
        limit=100,
        total_count=250,
        browse_cap=120,
        rows=rows[100:120],
    )

    assert page.status == "available"
    assert page.side == "baseline"
    assert page.group == "unmatched"
    assert page.offset == 100
    assert page.limit == 100
    assert page.total_count == 250
    assert page.browse_cap == 120
    assert page.browse_cap_reached is True
    assert page.returned_count == 20
    assert [row.input_position for row in page.rows] == list(range(100, 120))
