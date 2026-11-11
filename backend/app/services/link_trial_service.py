"""Run a read-only alternative-key trial for one reproduced foreign-key link."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, cast

import pandas as pd

from backend.app.core.config import Settings, get_settings
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_experiment_context_store import (
    BYTES_PER_MIB,
    JoinTypeSetting,
    LinkMergeKeys,
    RequestedSetting,
    ResolvedNullPolicy,
    SourceKind,
    TrialExceptionGroup,
    TrialExceptionGroups,
    TrialExceptionRow,
    TrialSettingsReport,
    ensure_projected_budget,
    ensure_retained_input_budget,
    estimate_output_rows,
    prepare_link_merge_keys,
    projected_merge_bytes,
    retained_input_bytes,
)
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.specifications.constraints import ForeignKeyConstraintViolation, ForeignKeyRuntimeOptions, ValidationIssue
from src.table_store import TableStore
from src.transforms.link import ForeignKeyLinker, LinkPass
from src.transforms.utility import merge_with_nonmatching_null_keys

TrialStatus = Literal["complete", "failed", "incomplete"]
"""Outcome of one alternative-key trial."""

SettingsSourceMode = Literal["saved", "request"]
"""Whether a settings report describes the saved configuration or a request."""


@dataclass(frozen=True)
class ARowTrialDiagnostic:
    """Match details and output contribution for one input A row."""

    input_position: int
    key_values: tuple[Any, ...]
    matched: bool
    remote_match_count: int
    output_row_contribution: int


@dataclass(frozen=True)
class LinkTrialResult:
    """Complete trial data, or a failure/incomplete reason without partial data."""

    status: TrialStatus
    reason: str
    message: str
    input_a_rows: int | None = None
    output_rows: int | None = None
    unmatched_a_rows: int | None = None
    multiply_matched_a_rows: int | None = None
    a_rows: tuple[ARowTrialDiagnostic, ...] | None = None
    issues: tuple[ValidationIssue, ...] = ()
    exception_groups: TrialExceptionGroups | None = None
    settings: TrialSettingsReport | None = None


class LinkTrialService:
    """Compare alternative key pairs on the full inputs of a reproduced link."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        """Use backend settings to bound materialized join results."""
        self.settings: Settings = settings if settings is not None else get_settings()

    def run_trial(
        self,
        baseline: LinkBaselineResult,
        *,
        local_keys: Sequence[str] | None,
        remote_keys: Sequence[str] | None,
        how: Literal["inner", "left"] | None = None,
        allow_null_keys: bool | None = None,
        null_keys_equal: bool | None = None,
        settings_source: SettingsSourceMode = "request",
    ) -> LinkTrialResult:
        """Run one read-only trial and return complete counts only when all checks finish."""
        saved_project: ShapeShiftProject | None = baseline._saved_project
        saved_fk: ForeignKeyConfig | None = baseline._foreign_key
        local_rows: pd.DataFrame | None = baseline.local_rows
        remote_rows: pd.DataFrame | None = baseline.remote_rows

        if not baseline.is_reproduced or saved_project is None or saved_fk is None or local_rows is None or remote_rows is None:
            return self._failed(
                "baseline_not_reproduced",
                "A trial requires the full inputs and resolved link context from a reproduced baseline.",
            )

        if baseline.link_pass not in ("initial", "after_unnest", "deferred_retry"):
            return self._failed("baseline_context_invalid", "The reproduced baseline has no supported linking pass.")

        selection_error: str | None = self._validate_key_selection(local_rows, remote_rows, local_keys, remote_keys)
        if selection_error is not None:
            return self._failed("invalid_keys", selection_error)

        selected_local_keys: list[str] = list(cast(Sequence[str], local_keys))
        selected_remote_keys: list[str] = list(cast(Sequence[str], remote_keys))
        trial_fk_data: dict[str, Any] = deepcopy(saved_fk.fk_cfg)
        trial_fk_data["local_keys"] = selected_local_keys
        trial_fk_data["remote_keys"] = selected_remote_keys
        if how is not None:
            trial_fk_data["how"] = how
        if allow_null_keys is not None or null_keys_equal is not None:
            constraints: dict[str, Any] = dict(trial_fk_data.get("constraints") or {})
            if allow_null_keys is not None:
                constraints["allow_null_keys"] = allow_null_keys
            if null_keys_equal is not None:
                constraints["null_keys_equal"] = null_keys_equal
            trial_fk_data["constraints"] = constraints
        trial_fk: ForeignKeyConfig = ForeignKeyConfig(
            local_entity=saved_fk.local_entity,
            fk_cfg=trial_fk_data,
            fk_index=saved_fk.fk_index,
        )
        join_type: str = trial_fk.how or "inner"

        if join_type not in ("inner", "left"):
            return self._failed("unsupported_join", f"Trials do not support the '{join_type}' join type.")

        try:
            merge_keys: LinkMergeKeys = prepare_link_merge_keys(saved_project, trial_fk, local_rows, remote_rows)
            estimated_link_rows, estimated_diagnostic_rows = estimate_output_rows(
                merge_keys.local_key_frame,
                merge_keys.remote_key_frame,
                trial_fk.local_keys,
                merge_keys.mapped_remote_keys,
                merge_keys.runtime_options,
                join_type,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("invalid_keys", str(exc))

        settings_report: TrialSettingsReport = self._build_settings_report(
            saved_fk,
            merge_keys,
            how_override=how,
            allow_null_keys_override=allow_null_keys,
            null_keys_equal_override=null_keys_equal,
            settings_source=settings_source,
        )

        limit_bytes: int = self.settings.LINK_EXPERIMENT_MAX_MEMORY_MB * BYTES_PER_MIB
        input_bytes: int = retained_input_bytes(local_rows, remote_rows)
        ensure_retained_input_budget(input_bytes, limit_bytes, stage="link trial")

        output_limit: int = self.settings.LINK_TRIAL_MAX_OUTPUT_ROWS
        if max(estimated_link_rows, estimated_diagnostic_rows) > output_limit:
            return LinkTrialResult(
                status="incomplete",
                reason="row_limit_exceeded",
                message=f"The estimated join output exceeds the configured limit of {output_limit} rows.",
                settings=settings_report,
            )

        null_key_temporaries: bool = bool(merge_keys.runtime_options.prevent_null_key_matches)
        link_projection: int = projected_merge_bytes(
            retained_bytes=input_bytes,
            input_bytes=input_bytes,
            local_rows=local_rows,
            remote_rows=remote_rows,
            local_keys=trial_fk.local_keys,
            remote_output_columns=merge_keys.remote_output_columns,
            remote_source_by_output=merge_keys.remote_source_by_output,
            mapped_remote_keys=merge_keys.mapped_remote_keys,
            estimated_output_rows=estimated_link_rows,
            include_merge_indicator=True,
            null_key_temporaries=null_key_temporaries,
        )
        diagnostic_projection: int = projected_merge_bytes(
            retained_bytes=input_bytes,
            input_bytes=input_bytes,
            local_rows=merge_keys.local_key_frame,
            remote_rows=merge_keys.remote_key_frame,
            local_keys=trial_fk.local_keys,
            remote_output_columns=merge_keys.mapped_remote_keys,
            remote_source_by_output={key: key for key in merge_keys.mapped_remote_keys},
            mapped_remote_keys=merge_keys.mapped_remote_keys,
            estimated_output_rows=estimated_diagnostic_rows,
            position_columns=2,
            null_key_temporaries=null_key_temporaries,
        )
        ensure_projected_budget(max(link_projection, diagnostic_projection), limit_bytes, stage="link trial")

        link_local_rows: pd.DataFrame = local_rows.copy(deep=True)
        link_remote_rows: pd.DataFrame = remote_rows.copy(deep=True)
        linker: ForeignKeyLinker = ForeignKeyLinker(
            project=saved_project,
            table_store=TableStore({trial_fk.local_entity: link_local_rows, trial_fk.remote_entity: link_remote_rows}),
        )
        linker.link_pass = cast(LinkPass, baseline.link_pass)

        try:
            linked_rows: pd.DataFrame = linker.link_foreign_key(link_local_rows, trial_fk, link_remote_rows)
        except ForeignKeyConstraintViolation as exc:
            return self._failed("constraint_violation", str(exc), settings=settings_report)
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("link_failed", str(exc), settings=settings_report)

        if not linker.validators:
            return self._failed("link_failed", "The production linker did not validate the selected link.", settings=settings_report)

        if len(linked_rows) != estimated_link_rows:
            return self._failed(
                "preflight_mismatch",
                "The preflight row estimate did not match the production link.",
                settings=settings_report,
            )

        output_rows: int = len(linked_rows)
        issues: tuple[ValidationIssue, ...] = tuple(linker.validators[-1].issues)
        del linked_rows

        ensure_projected_budget(diagnostic_projection, limit_bytes, stage="link trial diagnostic join")

        try:
            a_rows, diagnostic_join_rows = self._diagnose_a_rows(
                local_rows,
                merge_keys.remote_key_frame,
                trial_fk,
                merge_keys.mapped_remote_keys,
                merge_keys.runtime_options,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("diagnostic_failed", str(exc), settings=settings_report)

        if diagnostic_join_rows != estimated_diagnostic_rows:
            return self._failed(
                "preflight_mismatch",
                "The preflight row estimate did not match the diagnostic join.",
                settings=settings_report,
            )

        if sum(row.output_row_contribution for row in a_rows) != output_rows:
            return self._failed(
                "diagnostic_mismatch",
                "A-row contributions did not match the production link output.",
                settings=settings_report,
            )

        exception_groups: TrialExceptionGroups = self._exception_groups(a_rows)
        return LinkTrialResult(
            status="complete",
            reason="complete",
            message="The alternative-key trial completed.",
            input_a_rows=len(local_rows),
            output_rows=output_rows,
            unmatched_a_rows=exception_groups.unmatched.total_count,
            multiply_matched_a_rows=exception_groups.multiply_matched.total_count,
            a_rows=a_rows,
            issues=issues,
            exception_groups=exception_groups,
            settings=settings_report,
        )

    @staticmethod
    def _validate_key_selection(
        local_rows: pd.DataFrame,
        remote_rows: pd.DataFrame,
        local_keys: Sequence[str] | None,
        remote_keys: Sequence[str] | None,
    ) -> str | None:
        """Return a reason when the selected ordered keys are not available."""
        if (
            not isinstance(local_keys, Sequence)  # pylint: disable=too-many-boolean-expressions
            or isinstance(local_keys, (str, bytes))
            or not isinstance(remote_keys, Sequence)
            or isinstance(remote_keys, (str, bytes))
            or not local_keys
            or not remote_keys
        ):
            return "Select at least one local key and one remote key."

        if not all(isinstance(key, str) and key for key in (*local_keys, *remote_keys)):
            return "Key selections must contain nonempty column names."
        if len(local_keys) != len(remote_keys):
            return "Local and remote key selections must have the same number of columns."
        if len(set(local_keys)) != len(local_keys) or len(set(remote_keys)) != len(remote_keys):
            return "A key column cannot be selected more than once."

        for side, frame, selected_keys in (
            ("local", local_rows, local_keys),
            ("remote", remote_rows, remote_keys),
        ):
            for key in selected_keys:
                occurrences: int = list(frame.columns).count(key)
                if occurrences == 0:
                    return f"The selected {side} key '{key}' is not available in the link input."
                if occurrences > 1:
                    return f"The selected {side} key '{key}' is ambiguous in the link input."
        return None

    @staticmethod
    def _diagnose_a_rows(
        local_rows: pd.DataFrame,
        remote_rows: pd.DataFrame,
        fk: ForeignKeyConfig,
        mapped_remote_keys: list[str],
        runtime_options: ForeignKeyRuntimeOptions,
    ) -> tuple[tuple[ARowTrialDiagnostic, ...], int]:
        """Return match counts for every A position using the production null policy."""
        local_keys: pd.DataFrame = local_rows.loc[:, fk.local_keys].copy()
        remote_key_frame: pd.DataFrame = remote_rows.copy()
        a_position: str = LinkTrialService._available_position_column(local_keys.columns, "__ss_trial_a_position__")
        b_position: str = LinkTrialService._available_position_column(remote_key_frame.columns, "__ss_trial_b_position__")
        local_keys[a_position] = range(len(local_rows))
        remote_key_frame[b_position] = range(len(remote_rows))

        diagnostic_merge: pd.DataFrame = merge_with_nonmatching_null_keys(
            local_df=local_keys,
            remote_df=remote_key_frame,
            allow_null_keys=fk.constraints.allow_null_keys,
            prevent_null_key_matches=runtime_options.prevent_null_key_matches,
            how="left",
            left_on=fk.local_keys,
            right_on=mapped_remote_keys,
            suffixes=("", f"_{fk.remote_entity}"),
        )
        match_counts = diagnostic_merge.groupby(a_position, sort=False)[b_position].count()

        diagnostics: list[ARowTrialDiagnostic] = []
        is_left_join: bool = fk.how == "left"
        for position in range(len(local_rows)):
            remote_match_count: int = int(match_counts.get(position, 0))
            contribution: int = max(remote_match_count, 1) if is_left_join else remote_match_count
            key_values: tuple[Any, ...] = tuple(local_rows[key].iloc[position] for key in fk.local_keys)
            diagnostics.append(
                ARowTrialDiagnostic(
                    input_position=position,
                    key_values=key_values,
                    matched=remote_match_count > 0,
                    remote_match_count=remote_match_count,
                    output_row_contribution=contribution,
                )
            )
        return tuple(diagnostics), len(diagnostic_merge)

    @staticmethod
    def _available_position_column(columns: pd.Index, base_name: str) -> str:
        """Choose a temporary position column name not used by a join key."""
        name: str = base_name
        while name in columns:
            name = f"{name}_"
        return name

    def _exception_groups(self, a_rows: Sequence[ARowTrialDiagnostic]) -> TrialExceptionGroups:
        """Select the capped exception rows for both groups in input order."""
        group_cap: int = self.settings.LINK_TROUBLESHOOT_BROWSE_ROW_CAP
        unmatched: list[ARowTrialDiagnostic] = [row for row in a_rows if row.remote_match_count == 0]
        multiply_matched: list[ARowTrialDiagnostic] = [row for row in a_rows if row.remote_match_count > 1]

        def capped(rows: list[ARowTrialDiagnostic]) -> TrialExceptionGroup:
            """Keep the lowest input positions up to the configured group cap."""
            return TrialExceptionGroup(
                total_count=len(rows),
                rows=tuple(
                    TrialExceptionRow(
                        input_position=row.input_position,
                        key_values=row.key_values,
                        remote_match_count=row.remote_match_count,
                        output_row_contribution=row.output_row_contribution,
                    )
                    for row in rows[:group_cap]
                ),
            )

        return TrialExceptionGroups(unmatched=capped(unmatched), multiply_matched=capped(multiply_matched))

    @staticmethod
    def _build_settings_report(
        saved_fk: ForeignKeyConfig,
        merge_keys: LinkMergeKeys,
        *,
        how_override: str | None,
        allow_null_keys_override: bool | None,
        null_keys_equal_override: bool | None,
        settings_source: SettingsSourceMode,
    ) -> TrialSettingsReport:
        """Report requested and production-resolved settings for one side."""
        saved_constraints = saved_fk.constraints
        if settings_source == "saved":
            saved_how_present: bool = "how" in saved_fk.fk_cfg
            join_requested: str | None = str(saved_fk.fk_cfg["how"]) if saved_how_present else None
            join_source: SourceKind = "explicit" if saved_how_present else "inherited"
            allow_requested: bool | None = saved_constraints.allow_null_keys if saved_constraints.allow_null_keys_is_explicit else None
            allow_source: SourceKind = "explicit" if saved_constraints.allow_null_keys_is_explicit else "inherited"
            null_equal_requested: bool | None = saved_constraints.null_keys_equal if saved_constraints.null_keys_equal_is_explicit else None
            null_equal_source: SourceKind = "explicit" if saved_constraints.null_keys_equal_is_explicit else "inherited"
        else:
            join_requested = how_override
            join_source = "explicit" if how_override is not None else "inherited"
            allow_requested = allow_null_keys_override
            allow_source = "explicit" if allow_null_keys_override is not None else "inherited"
            null_equal_requested = null_keys_equal_override
            null_equal_source = "explicit" if null_keys_equal_override is not None else "inherited"

        return TrialSettingsReport(
            join_type=JoinTypeSetting(
                requested=join_requested,
                source=join_source,
                effective=merge_keys.join_type,
            ),
            allow_null_keys=RequestedSetting(requested=allow_requested, source=allow_source),
            null_keys_equal=RequestedSetting(requested=null_equal_requested, source=null_equal_source),
            resolved_null_policy=ResolvedNullPolicy(
                enforce_strict_null_keys=merge_keys.runtime_options.enforce_strict_null_keys,
                prevent_null_key_matches=merge_keys.runtime_options.prevent_null_key_matches,
            ),
        )

    @staticmethod
    def _failed(reason: str, message: str, *, settings: TrialSettingsReport | None = None) -> LinkTrialResult:
        """Return a named failure without partial counts or rows."""
        return LinkTrialResult(status="failed", reason=reason, message=message, settings=settings)
