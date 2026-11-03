"""Tests for the bounded foreign-key troubleshooter response mapper."""

from typing import Any

import numpy as np
import pandas as pd
import pytest

from backend.app.mappers.link_troubleshooter_mapper import LinkTroubleshooterMapper
from backend.app.models.link_troubleshooter import (
    LinkTroubleshootKeyOptions,
    LinkTroubleshootKeys,
    LinkTroubleshootRelationship,
)
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_trial_service import ARowTrialDiagnostic, LinkTrialResult
from src.specifications.constraints import ValidationIssue


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
    )


def map_response(
    baseline: LinkBaselineResult,
    *,
    baseline_trial: LinkTrialResult | None = None,
    trial: LinkTrialResult | None = None,
    page: int = 1,
    page_size: int = 50,
    row_filter: str = "all",
):
    """Map one test result with the configured relationship details."""
    return LinkTroubleshooterMapper.to_response(
        baseline=baseline,
        baseline_trial=baseline_trial,
        trial=trial,
        relationship=LinkTroubleshootRelationship(
            local_entity="orders",
            remote_entity="customers",
            fk_index=0,
            join_type="inner",
            link_pass="initial",
        ),
        key_options=LinkTroubleshootKeyOptions(local=["code"], remote=["code"]),
        configured_keys=LinkTroubleshootKeys(local_keys=["code"], remote_keys=["code"]),
        trial_local_keys=["trial_code"],
        trial_remote_keys=["trial_code"],
        page=page,
        page_size=page_size,
        row_filter=row_filter,  # type: ignore[arg-type]
    )


def test_maps_configured_baseline_diagnostics_separately_from_requested_trial() -> None:
    baseline_diagnostics = trial_result(
        input_rows=3,
        output_rows=2,
        unmatched_rows=1,
        multiply_matched_rows=1,
        a_rows=(),
    )
    requested_rows = (
        ARowTrialDiagnostic(0, ("A",), True, 1, 1),
        ARowTrialDiagnostic(1, ("missing",), False, 0, 0),
        ARowTrialDiagnostic(2, ("duplicate",), True, 2, 2),
    )
    requested_trial = trial_result(
        input_rows=3,
        output_rows=3,
        unmatched_rows=1,
        multiply_matched_rows=1,
        a_rows=requested_rows,
    )

    response = map_response(reproduced_baseline(), baseline_trial=baseline_diagnostics, trial=requested_trial)

    assert response.baseline is not None
    assert response.baseline.input_a_rows == 3
    assert response.baseline.output_rows == 2
    assert response.baseline.unmatched_a_rows == 1
    assert response.baseline.multiply_matched_a_rows == 1
    assert response.baseline.diagnostic_status == "complete"
    assert response.trial is not None
    assert response.trial.totals is not None
    assert response.trial.totals.output_rows == 3
    assert response.trial.rows[0].key_values == ["A"]
    assert response.trial.local_keys == ["trial_code"]


@pytest.mark.parametrize("diagnostic_status", ["incomplete", "failed"])
def test_incomplete_or_failed_baseline_diagnostics_do_not_hide_complete_trial(diagnostic_status: str) -> None:
    baseline_diagnostics = trial_result(
        status=diagnostic_status,
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        a_rows=None,
        reason="row_limit_exceeded" if diagnostic_status == "incomplete" else "constraint_violation",
        message="Configured-key diagnostics are unavailable.",
    )
    requested_trial = trial_result(a_rows=(ARowTrialDiagnostic(0, ("A",), True, 1, 1),))

    response = map_response(reproduced_baseline(), baseline_trial=baseline_diagnostics, trial=requested_trial)

    assert response.baseline is not None
    assert response.baseline.unmatched_a_rows is None
    assert response.baseline.multiply_matched_a_rows is None
    assert response.baseline.diagnostic_status == diagnostic_status
    assert response.baseline.diagnostic_reason == baseline_diagnostics.reason
    assert response.trial is not None
    assert response.trial.status == "complete"
    assert response.trial.totals is not None


@pytest.mark.parametrize("trial_status", ["failed", "incomplete"])
def test_failed_or_incomplete_requested_trial_has_no_totals_rows_or_pagination(trial_status: str) -> None:
    trial = trial_result(
        status=trial_status,
        input_rows=None,
        output_rows=None,
        unmatched_rows=None,
        multiply_matched_rows=None,
        a_rows=None,
        reason="invalid_keys" if trial_status == "failed" else "row_limit_exceeded",
        message="The requested trial is unavailable.",
    )

    response = map_response(reproduced_baseline(), trial=trial)

    assert response.trial is not None
    assert response.trial.status == trial_status
    assert response.trial.reason == trial.reason
    assert response.trial.message == trial.message
    assert response.trial.totals is None
    assert response.trial.rows == []
    assert response.trial.pagination is None


def test_not_reproduced_baseline_keeps_counts_and_current_findings_without_trial() -> None:
    issue = linker_issue("The current link still has a row-count warning.")
    baseline = LinkBaselineResult(
        status="not_reproduced",
        reason="warning_changed",
        message="The current warning differs.",
        entity_name="orders",
        row_count_before=4,
        row_count_after=3,
        issues=(issue,),
    )

    response = map_response(baseline)

    assert response.status == "not_reproduced"
    assert response.baseline is not None
    assert response.baseline.input_a_rows == 4
    assert response.baseline.output_rows == 3
    assert response.baseline.diagnostic_status == "not_run"
    assert response.baseline.issues[0].message == issue.message
    assert response.trial is None


def test_ineligible_baseline_without_counts_has_no_baseline_payload() -> None:
    baseline = LinkBaselineResult(
        status="ineligible",
        reason="stale_signature",
        message="The warning no longer identifies a saved link.",
        entity_name="orders",
    )

    response = map_response(baseline)

    assert response.status == "ineligible"
    assert response.baseline is None
    assert response.trial is None


@pytest.mark.parametrize(
    ("row_filter", "expected_positions"),
    [
        ("all", [0, 1, 2]),
        ("unmatched", [1]),
        ("multiply_matched", [2]),
    ],
)
def test_filters_and_pages_rows_without_changing_complete_totals(row_filter: str, expected_positions: list[int]) -> None:
    rows = (
        ARowTrialDiagnostic(0, ("A",), True, 1, 1),
        ARowTrialDiagnostic(1, ("B",), False, 0, 0),
        ARowTrialDiagnostic(2, ("C",), True, 2, 2),
    )
    trial = trial_result(a_rows=rows)

    first_page = map_response(reproduced_baseline(), trial=trial, page=1, page_size=2, row_filter=row_filter)

    assert first_page.trial is not None
    assert [row.input_position for row in first_page.trial.rows] == expected_positions[:2]
    assert first_page.trial.pagination is not None
    assert first_page.trial.pagination.filtered_row_count == len(expected_positions)
    assert first_page.trial.pagination.returned_row_count == min(2, len(expected_positions))
    assert first_page.trial.totals is not None
    assert first_page.trial.totals.output_rows == trial.output_rows

    beyond_last = map_response(reproduced_baseline(), trial=trial, page=10, page_size=2, row_filter=row_filter)

    assert beyond_last.trial is not None
    assert beyond_last.trial.rows == []
    assert beyond_last.trial.pagination is not None
    assert beyond_last.trial.pagination.has_next is False
    assert beyond_last.trial.totals == first_page.trial.totals


def test_key_values_are_json_safe_for_pandas_and_numpy_scalars() -> None:
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
    trial = trial_result(a_rows=(ARowTrialDiagnostic(0, values, True, 1, 1),))

    response = map_response(reproduced_baseline(), trial=trial)

    assert response.trial is not None
    assert response.trial.rows[0].key_values == [12, 3.5, True, None, None, None, ["nested", 1], {"nested": True}]
    response.model_dump_json()


def test_serialized_response_has_no_frames_project_or_foreign_key_context() -> None:
    baseline = reproduced_baseline()
    trial = trial_result(a_rows=(ARowTrialDiagnostic(0, ("A",), True, 1, 1),))

    payload = map_response(baseline, baseline_trial=trial, trial=trial).model_dump(mode="json")
    serialized = str(payload)

    assert "DataFrame" not in serialized
    assert "_saved_project" not in serialized
    assert "_foreign_key" not in serialized
    assert "local_rows" not in serialized
    assert "remote_rows" not in serialized
