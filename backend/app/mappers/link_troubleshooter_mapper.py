"""Map baseline and trial results to the bounded troubleshooter response."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

import pandas as pd

from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.link_troubleshooter import (
    LinkTroubleshootBaseline,
    LinkTroubleshootKeyOptions,
    LinkTroubleshootKeys,
    LinkTroubleshootPagination,
    LinkTroubleshootRelationship,
    LinkTroubleshootResponse,
    LinkTroubleshootRow,
    LinkTroubleshootTotals,
    LinkTroubleshootTrial,
)
from backend.app.models.validation import ValidationError

if TYPE_CHECKING:
    from backend.app.services.link_baseline_service import LinkBaselineResult
    from backend.app.services.link_trial_service import LinkTrialResult
    from src.specifications.constraints import ValidationIssue as LinkerValidationIssue


class LinkTroubleshooterMapper:
    """Serialize baseline and trial results without exposing project data or frames."""

    @staticmethod
    def to_response(
        *,
        baseline: LinkBaselineResult,
        baseline_trial: LinkTrialResult | None,
        trial: LinkTrialResult | None,
        relationship: LinkTroubleshootRelationship | None,
        key_options: LinkTroubleshootKeyOptions | None,
        configured_keys: LinkTroubleshootKeys | None,
        trial_local_keys: Sequence[str],
        trial_remote_keys: Sequence[str],
        page: int,
        page_size: int,
        row_filter: Literal["all", "unmatched", "multiply_matched"],
    ) -> LinkTroubleshootResponse:
        """Build the public response and page only requested-trial row details."""
        baseline_result: LinkTroubleshootBaseline | None = None
        if not (baseline.status == "ineligible" and baseline.row_count_before is None and baseline.row_count_after is None):
            baseline_result = LinkTroubleshooterMapper._map_baseline(baseline, baseline_trial)

        trial_result: LinkTroubleshootTrial | None = None
        if trial is not None:
            trial_result = LinkTroubleshooterMapper._map_trial(
                trial,
                trial_local_keys=trial_local_keys,
                trial_remote_keys=trial_remote_keys,
                page=page,
                page_size=page_size,
                row_filter=row_filter,
            )

        return LinkTroubleshootResponse(
            status=baseline.status,
            reason=baseline.reason,
            message=baseline.message,
            relationship=relationship,
            key_options=key_options,
            configured_keys=configured_keys,
            baseline=baseline_result,
            trial=trial_result,
        )

    @staticmethod
    def _map_baseline(
        baseline: LinkBaselineResult,
        baseline_trial: LinkTrialResult | None,
    ) -> LinkTroubleshootBaseline:
        """Map saved-link counts and only configured-key diagnostics."""
        diagnostic_status: Literal["complete", "failed", "incomplete", "not_run"] = (
            baseline_trial.status if baseline_trial is not None else "not_run"
        )

        return LinkTroubleshootBaseline(
            input_a_rows=baseline.row_count_before,
            output_rows=baseline.row_count_after,
            unmatched_a_rows=(
                baseline_trial.unmatched_a_rows if baseline_trial is not None and baseline_trial.status == "complete" else None
            ),
            multiply_matched_a_rows=(
                baseline_trial.multiply_matched_a_rows if baseline_trial is not None and baseline_trial.status == "complete" else None
            ),
            diagnostic_status=diagnostic_status,
            diagnostic_reason=baseline_trial.reason if baseline_trial is not None else None,
            diagnostic_message=baseline_trial.message if baseline_trial is not None else None,
            issues=LinkTroubleshooterMapper._map_issues(baseline.issues),
        )

    @staticmethod
    def _map_trial(
        trial: LinkTrialResult,
        *,
        trial_local_keys: Sequence[str],
        trial_remote_keys: Sequence[str],
        page: int,
        page_size: int,
        row_filter: Literal["all", "unmatched", "multiply_matched"],
    ) -> LinkTroubleshootTrial:
        """Map requested-trial results and keep incomplete output out of the response."""
        if trial.status != "complete":
            return LinkTroubleshootTrial(
                status=trial.status,
                reason=trial.reason,
                message=trial.message,
                local_keys=list(trial_local_keys),
                remote_keys=list(trial_remote_keys),
                issues=LinkTroubleshooterMapper._map_issues(trial.issues),
            )

        totals = LinkTroubleshooterMapper._complete_totals(trial)
        all_rows = list(trial.a_rows or ())
        if row_filter == "unmatched":
            filtered_rows = [row for row in all_rows if not row.matched]
        elif row_filter == "multiply_matched":
            filtered_rows = [row for row in all_rows if row.remote_match_count > 1]
        else:
            filtered_rows = all_rows

        page_start: int = (page - 1) * page_size
        page_rows: list[LinkTroubleshootRow] = [
            LinkTroubleshootRow(
                input_position=row.input_position,
                key_values=[LinkTroubleshooterMapper._json_safe_scalar(value) for value in row.key_values],
                matched=row.matched,
                remote_match_count=row.remote_match_count,
                output_row_contribution=row.output_row_contribution,
            )
            for row in filtered_rows[page_start : page_start + page_size]
        ]
        pagination = LinkTroubleshootPagination(
            page=page,
            page_size=page_size,
            filtered_row_count=len(filtered_rows),
            returned_row_count=len(page_rows),
            has_next=page * page_size < len(filtered_rows),
        )

        return LinkTroubleshootTrial(
            status="complete",
            reason=trial.reason,
            message=trial.message,
            local_keys=list(trial_local_keys),
            remote_keys=list(trial_remote_keys),
            totals=totals,
            issues=LinkTroubleshooterMapper._map_issues(trial.issues),
            rows=page_rows,
            pagination=pagination,
        )

    @staticmethod
    def _complete_totals(trial: LinkTrialResult) -> LinkTroubleshootTotals:
        """Return totals only when a complete trial contains every required count."""
        input_a_rows = trial.input_a_rows
        output_rows = trial.output_rows
        unmatched_a_rows = trial.unmatched_a_rows
        multiply_matched_a_rows = trial.multiply_matched_a_rows
        if input_a_rows is None or output_rows is None or unmatched_a_rows is None or multiply_matched_a_rows is None:
            raise ValueError("A complete link trial must include all four totals.")

        return LinkTroubleshootTotals(
            input_a_rows=input_a_rows,
            output_rows=output_rows,
            unmatched_a_rows=unmatched_a_rows,
            multiply_matched_a_rows=multiply_matched_a_rows,
        )

    @staticmethod
    def _map_issues(issues: Sequence[LinkerValidationIssue]) -> list[ValidationError]:
        """Map core linker issues through the shared validation mapper."""
        return [ValidationMapper.to_api_error(ValidationMapper.from_linker_issue(issue)) for issue in issues]

    @staticmethod
    def _json_safe_scalar(value: Any) -> Any:
        """Convert missing and non-JSON scalar values to safe response values."""
        if value is None or value is pd.NA:
            return None

        if isinstance(value, (list, dict)):
            try:
                json.dumps(value, allow_nan=False)
            except (TypeError, ValueError):
                return str(value)
            return value

        item = getattr(value, "item", None)
        if callable(item):
            try:
                value = item()
            except (TypeError, ValueError):
                pass

        if value is None or value is pd.NA:
            return None

        if pd.api.types.is_scalar(value) and bool(pd.isna(value)):
            return None

        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError):
            return str(value)
        return value
