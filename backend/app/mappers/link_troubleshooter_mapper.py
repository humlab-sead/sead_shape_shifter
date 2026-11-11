"""Map baseline and trial results to the bounded troubleshooter response."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

import pandas as pd

from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.link_troubleshooter import (
    EXCEPTION_ROW_PAGE_SIZE,
    ExceptionGroupName,
    ExceptionRowSide,
    LinkExceptionRowsPage,
    LinkExperimentContextResponse,
    LinkExperimentTrialResponse,
    LinkTroubleshootBaseline,
    LinkTroubleshootComparison,
    LinkTroubleshootDetail,
    LinkTroubleshootExceptionGroup,
    LinkTroubleshootExceptionRow,
    LinkTroubleshootFindings,
    LinkTroubleshootJoinTypeSetting,
    LinkTroubleshootKeyOptions,
    LinkTroubleshootKeys,
    LinkTroubleshootKeyValue,
    LinkTroubleshootRelationship,
    LinkTroubleshootRequestedSetting,
    LinkTroubleshootResolvedNullPolicy,
    LinkTroubleshootTotals,
    LinkTroubleshootTrialSettings,
)
from backend.app.models.validation import ValidationError

if TYPE_CHECKING:
    from datetime import datetime

    from backend.app.services.link_baseline_service import LinkBaselineResult
    from backend.app.services.link_experiment_context_store import (
        LinkExperimentDiagnostics,
        TrialExceptionGroup,
        TrialExceptionGroups,
        TrialExceptionRow,
        TrialSettingsReport,
    )
    from backend.app.services.link_trial_service import LinkTrialResult
    from src.specifications.constraints import ValidationIssue as LinkerValidationIssue

KEY_VALUE_BYTE_LIMIT: int = 256
"""Maximum UTF-8 bytes for one exception key value."""

FINDING_COUNT_LIMIT: int = 50
"""Maximum number of findings returned per side."""

FINDING_MESSAGE_BYTE_LIMIT: int = 512
"""Maximum UTF-8 bytes for one finding message."""

DETAIL_BUDGET_BYTES: int = 256 * 1024
"""Aggregate per-side detail budget in UTF-8 bytes."""


def _truncate_utf8(text: str, limit: int) -> tuple[str, bool]:
    """Cut text at the last whole code point that fits in ``limit`` UTF-8 bytes."""
    encoded: bytes = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore"), True


def _string_form(value: Any) -> str:
    """Return the measured string form of one JSON-safe scalar."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return str(value)


@dataclass
class _DetailBudget:
    """Track the shared per-side detail budget in UTF-8 bytes."""

    remaining: int = DETAIL_BUDGET_BYTES
    exhausted: bool = False

    def charge(self, byte_count: int) -> bool:
        """Consume bytes, returning False when the charge does not fit."""
        if byte_count <= 0:
            return True
        if byte_count > self.remaining:
            self.exhausted = True
            return False
        self.remaining -= byte_count
        return True


class LinkTroubleshooterMapper:
    """Serialize baseline and trial results without exposing project data or frames."""

    @staticmethod
    def to_context_response(
        *,
        context_id: str | None,
        expires_at: datetime | None,
        baseline: LinkBaselineResult,
        diagnostics: LinkExperimentDiagnostics | None,
        relationship: LinkTroubleshootRelationship | None,
        key_options: LinkTroubleshootKeyOptions | None,
        configured_keys: LinkTroubleshootKeys | None,
        row_cap: int,
    ) -> LinkExperimentContextResponse:
        """Build the retained-context response for one snapshot.

        A snapshot exists only after reproduction, so an unreproduced baseline
        carries no baseline block and no complete counts.
        """
        return LinkExperimentContextResponse(
            context_id=context_id,
            status=baseline.status,
            reason=baseline.reason,
            message=baseline.message,
            expires_at=expires_at,
            relationship=relationship,
            key_options=key_options,
            configured_keys=configured_keys,
            baseline=(LinkTroubleshooterMapper._map_context_baseline(baseline, diagnostics, row_cap) if context_id is not None else None),
        )

    @staticmethod
    def to_context_trial_response(
        *,
        context_id: str,
        expires_at: datetime,
        baseline: LinkBaselineResult,
        diagnostics: LinkExperimentDiagnostics | None,
        trial: LinkTrialResult,
        local_keys: Sequence[str],
        remote_keys: Sequence[str],
        row_cap: int,
    ) -> LinkExperimentTrialResponse:
        """Map one context trial and its retained baseline to a bounded response."""
        return LinkExperimentTrialResponse(
            context_id=context_id,
            expires_at=expires_at,
            local_keys=list(local_keys),
            remote_keys=list(remote_keys),
            baseline=LinkTroubleshooterMapper._map_context_baseline(baseline, diagnostics, row_cap),
            trial=LinkTroubleshooterMapper._map_comparison(trial, row_cap),
        )

    @staticmethod
    def _map_context_baseline(
        baseline: LinkBaselineResult,
        diagnostics: LinkExperimentDiagnostics | None,
        row_cap: int,
    ) -> LinkTroubleshootBaseline:
        """Map a retained baseline, keeping totals only for complete diagnostics."""
        is_complete: bool = diagnostics is not None and diagnostics.status == "complete"
        findings_issues: Sequence[LinkerValidationIssue] = (
            diagnostics.issues if diagnostics is not None and diagnostics.issues else baseline.issues
        )
        detail: LinkTroubleshootDetail | None = None
        if diagnostics is not None or findings_issues:
            detail = LinkTroubleshooterMapper._build_detail(
                diagnostics.exception_groups if is_complete and diagnostics is not None else None,
                findings_issues,
                row_cap,
            )

        return LinkTroubleshootBaseline(
            input_a_rows=diagnostics.input_a_rows if is_complete and diagnostics is not None else None,
            output_rows=diagnostics.output_rows if is_complete and diagnostics is not None else None,
            unmatched_a_rows=diagnostics.unmatched_a_rows if is_complete and diagnostics is not None else None,
            multiply_matched_a_rows=diagnostics.multiply_matched_a_rows if is_complete and diagnostics is not None else None,
            diagnostic_status=diagnostics.status if diagnostics is not None else "not_run",
            diagnostic_reason=diagnostics.reason if diagnostics is not None else None,
            diagnostic_message=diagnostics.message if diagnostics is not None else None,
            settings=LinkTroubleshooterMapper._map_settings(diagnostics.settings if diagnostics is not None else None),
            detail=detail,
        )

    @staticmethod
    def _map_comparison(trial: LinkTrialResult, row_cap: int) -> LinkTroubleshootComparison:
        """Map one trial, keeping totals and groups only for complete work."""
        settings: LinkTroubleshootTrialSettings | None = LinkTroubleshooterMapper._map_settings(trial.settings)
        if trial.status != "complete":
            return LinkTroubleshootComparison(
                status=trial.status,
                reason=trial.reason,
                message=trial.message,
                settings=settings,
                detail=(LinkTroubleshooterMapper._build_detail(None, trial.issues, row_cap) if trial.issues else None),
            )

        return LinkTroubleshootComparison(
            status="complete",
            reason=trial.reason,
            message=trial.message,
            settings=settings,
            totals=LinkTroubleshooterMapper._complete_totals(trial),
            detail=LinkTroubleshooterMapper._build_detail(trial.exception_groups, trial.issues, row_cap),
        )

    @staticmethod
    def _map_settings(settings: TrialSettingsReport | None) -> LinkTroubleshootTrialSettings | None:
        """Map the resolved settings report to the API model."""
        if settings is None:
            return None
        return LinkTroubleshootTrialSettings(
            join_type=LinkTroubleshootJoinTypeSetting(
                requested=cast(Literal["inner", "left"] | None, settings.join_type.requested),
                source=settings.join_type.source,
                effective=cast(Literal["inner", "left"], settings.join_type.effective),
            ),
            allow_null_keys=LinkTroubleshootRequestedSetting(
                requested=cast(bool | None, settings.allow_null_keys.requested),
                source=settings.allow_null_keys.source,
            ),
            null_keys_equal=LinkTroubleshootRequestedSetting(
                requested=cast(bool | None, settings.null_keys_equal.requested),
                source=settings.null_keys_equal.source,
            ),
            resolved_null_policy=LinkTroubleshootResolvedNullPolicy(
                enforce_strict_null_keys=settings.resolved_null_policy.enforce_strict_null_keys,
                prevent_null_key_matches=settings.resolved_null_policy.prevent_null_key_matches,
            ),
        )

    @staticmethod
    def _build_detail(
        groups: TrialExceptionGroups | None,
        issues: Sequence[LinkerValidationIssue],
        row_cap: int,
    ) -> LinkTroubleshootDetail:
        """Bound findings first, then the unmatched and multiply matched groups."""
        budget = _DetailBudget()
        findings: LinkTroubleshootFindings = LinkTroubleshooterMapper._build_findings(issues, budget)
        detail_truncated: bool = findings.truncated

        unmatched: LinkTroubleshootExceptionGroup | None = None
        multiply_matched: LinkTroubleshootExceptionGroup | None = None
        if groups is not None:
            mapped_unmatched: LinkTroubleshootExceptionGroup = LinkTroubleshooterMapper._build_group(groups.unmatched, row_cap, budget)
            mapped_multiply: LinkTroubleshootExceptionGroup = LinkTroubleshooterMapper._build_group(
                groups.multiply_matched, row_cap, budget
            )
            unmatched = mapped_unmatched
            multiply_matched = mapped_multiply
            detail_truncated = (
                detail_truncated
                or mapped_unmatched.row_cap_reached
                or mapped_unmatched.budget_exhausted
                or mapped_multiply.row_cap_reached
                or mapped_multiply.budget_exhausted
                or any(value.truncated for row in mapped_unmatched.rows for value in row.key_values)
                or any(value.truncated for row in mapped_multiply.rows for value in row.key_values)
            )

        return LinkTroubleshootDetail(
            detail_truncated=detail_truncated,
            findings=findings,
            unmatched=unmatched,
            multiply_matched=multiply_matched,
        )

    @staticmethod
    def _build_findings(issues: Sequence[LinkerValidationIssue], budget: _DetailBudget) -> LinkTroubleshootFindings:
        """Return at most the configured findings with bounded messages."""
        mapped_issues: list[ValidationError] = []
        truncated: bool = False
        for issue in issues:
            if len(mapped_issues) >= FINDING_COUNT_LIMIT:
                truncated = True
                break
            api_issue: ValidationError = LinkTroubleshooterMapper._map_issues([issue])[0]
            message, message_cut = _truncate_utf8(api_issue.message, FINDING_MESSAGE_BYTE_LIMIT)
            if message_cut:
                api_issue = api_issue.model_copy(update={"message": message})
                truncated = True
            if not budget.charge(len(message.encode("utf-8"))):
                truncated = True
                break
            mapped_issues.append(api_issue)

        if len(mapped_issues) < len(issues):
            truncated = True

        return LinkTroubleshootFindings(
            total_count=len(issues),
            returned_count=len(mapped_issues),
            truncated=truncated,
            issues=mapped_issues,
        )

    @staticmethod
    def _build_group(group: TrialExceptionGroup, row_cap: int, budget: _DetailBudget) -> LinkTroubleshootExceptionGroup:
        """Return one group with its first browse page inside the remaining budget.

        The response carries a first page, not the whole browse window. Rows past
        that page are read through the exception-row route, so the baseline
        response stays bounded even when the browse cap is 10,000 rows.
        """
        rows: list[LinkTroubleshootExceptionRow] = []
        budget_exhausted: bool = False
        for row in group.rows[:EXCEPTION_ROW_PAGE_SIZE]:
            key_values: list[LinkTroubleshootKeyValue] = []
            row_bytes: int = 0
            for value in row.key_values:
                bounded, value_bytes = LinkTroubleshooterMapper._bounded_key_value(value)
                key_values.append(bounded)
                row_bytes += value_bytes
            if not budget.charge(row_bytes):
                budget_exhausted = True
                break
            rows.append(
                LinkTroubleshootExceptionRow(
                    input_position=row.input_position,
                    key_values=key_values,
                    remote_match_count=row.remote_match_count,
                    output_row_contribution=row.output_row_contribution,
                )
            )

        return LinkTroubleshootExceptionGroup(
            total_count=group.total_count,
            returned_count=len(rows),
            row_cap=row_cap,
            row_cap_reached=group.total_count > row_cap,
            budget_exhausted=budget_exhausted,
            rows=rows,
        )

    @staticmethod
    def to_exception_rows_page(
        *,
        side: ExceptionRowSide,
        group: ExceptionGroupName,
        offset: int,
        limit: int,
        total_count: int,
        browse_cap: int,
        rows: Sequence[TrialExceptionRow],
    ) -> LinkExceptionRowsPage:
        """Map one already-sliced exception-row window to the browse response."""
        mapped_rows: list[LinkTroubleshootExceptionRow] = []
        for row in rows:
            key_values: list[LinkTroubleshootKeyValue] = [
                LinkTroubleshooterMapper._bounded_key_value(value)[0] for value in row.key_values
            ]
            mapped_rows.append(
                LinkTroubleshootExceptionRow(
                    input_position=row.input_position,
                    key_values=key_values,
                    remote_match_count=row.remote_match_count,
                    output_row_contribution=row.output_row_contribution,
                )
            )

        return LinkExceptionRowsPage(
            status="available",
            side=side,
            group=group,
            offset=offset,
            limit=limit,
            total_count=total_count,
            browse_cap=browse_cap,
            browse_cap_reached=total_count > browse_cap,
            returned_count=len(mapped_rows),
            rows=mapped_rows,
        )

    @staticmethod
    def _bounded_key_value(value: Any) -> tuple[LinkTroubleshootKeyValue, int]:
        """Bound one key value and return it with the bytes it consumes."""
        safe: Any = LinkTroubleshooterMapper._json_safe_scalar(value)
        form: str = _string_form(safe)
        truncated_text, truncated = _truncate_utf8(form, KEY_VALUE_BYTE_LIMIT)
        if not truncated:
            return LinkTroubleshootKeyValue(value=safe), len(form.encode("utf-8"))
        return (
            LinkTroubleshootKeyValue(value=truncated_text, truncated=True, original_length=len(form)),
            len(truncated_text.encode("utf-8")),
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
