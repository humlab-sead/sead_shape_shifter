"""Run a read-only alternative-key trial for one reproduced foreign-key link."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, cast

import pandas as pd

from backend.app.core.config import Settings, get_settings
from backend.app.services.link_baseline_service import LinkBaselineResult
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.specifications.constraints import ForeignKeyConstraintViolation, ForeignKeyRuntimeOptions, ValidationIssue
from src.table_store import TableStore
from src.transforms.link import ForeignKeyLinker, LinkPass, _resolve_fk_runtime_options
from src.transforms.utility import _NULL_SENTINEL_PREFIX, _coerce_compatible_merge_key_dtypes, merge_with_nonmatching_null_keys

TrialStatus = Literal["complete", "failed", "incomplete"]
"""Outcome of one alternative-key trial."""

_NULL_KEY = object()


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
        trial_fk: ForeignKeyConfig = ForeignKeyConfig(
            local_entity=saved_fk.local_entity,
            fk_cfg=trial_fk_data,
            fk_index=saved_fk.fk_index,
        )
        join_type: str = trial_fk.how or "inner"

        if join_type not in ("inner", "left"):
            return self._failed("unsupported_join", f"Trials do not support the '{join_type}' join type.")

        try:
            local_key_frame, remote_key_frame, mapped_remote_keys = self._prepare_key_frames(
                saved_project,
                trial_fk,
                local_rows,
                remote_rows,
            )
            remote_config = saved_project.get_table(trial_fk.remote_entity)
            runtime_options: ForeignKeyRuntimeOptions = _resolve_fk_runtime_options(trial_fk, remote_config)
            estimated_link_rows, estimated_diagnostic_rows = self._estimate_output_rows(
                local_key_frame,
                remote_key_frame,
                trial_fk.local_keys,
                mapped_remote_keys,
                runtime_options,
                join_type,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("invalid_keys", str(exc))

        output_limit: int = self.settings.LINK_TRIAL_MAX_OUTPUT_ROWS
        if max(estimated_link_rows, estimated_diagnostic_rows) > output_limit:
            return LinkTrialResult(
                status="incomplete",
                reason="row_limit_exceeded",
                message=f"The estimated join output exceeds the configured limit of {output_limit} rows.",
            )

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
            return self._failed("constraint_violation", str(exc))
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("link_failed", str(exc))

        if not linker.validators:
            return self._failed("link_failed", "The production linker did not validate the selected link.")

        if len(linked_rows) != estimated_link_rows:
            return self._failed("preflight_mismatch", "The preflight row estimate did not match the production link.")

        output_rows: int = len(linked_rows)
        issues: tuple[ValidationIssue, ...] = tuple(linker.validators[-1].issues)
        del linked_rows

        try:
            a_rows, diagnostic_join_rows = self._diagnose_a_rows(
                local_rows,
                remote_key_frame,
                trial_fk,
                mapped_remote_keys,
                runtime_options,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return self._failed("diagnostic_failed", str(exc))

        if diagnostic_join_rows != estimated_diagnostic_rows:
            return self._failed("preflight_mismatch", "The preflight row estimate did not match the diagnostic join.")

        if sum(row.output_row_contribution for row in a_rows) != output_rows:
            return self._failed("diagnostic_mismatch", "A-row contributions did not match the production link output.")

        return LinkTrialResult(
            status="complete",
            reason="complete",
            message="The alternative-key trial completed.",
            input_a_rows=len(local_rows),
            output_rows=output_rows,
            unmatched_a_rows=sum(not row.matched for row in a_rows),
            multiply_matched_a_rows=sum(row.remote_match_count > 1 for row in a_rows),
            a_rows=a_rows,
            issues=issues,
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
    def _prepare_key_frames(
        project: ShapeShiftProject,
        fk: ForeignKeyConfig,
        local_rows: pd.DataFrame,
        remote_rows: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        """Return the actual local and renamed remote merge-key columns."""
        if not local_rows.columns.is_unique or not remote_rows.columns.is_unique:
            raise ValueError("Link inputs must not contain duplicate column names.")

        remote_config = project.get_table(fk.remote_entity)
        if list(remote_rows.columns).count(remote_config.system_id) != 1:
            raise KeyError(f"The remote link input must contain one '{remote_config.system_id}' column.")
        setup = fk.generate_link_setup(remote_rows.columns.tolist(), remote_config)
        remote_columns_to_select: list[str] = [remote_config.system_id]
        remote_columns_to_select.extend(column for column in setup.remote_columns if column != remote_config.system_id)
        output_columns: list[str] = [setup.rename_map.get(column, column) for column in remote_columns_to_select]
        if len(set(output_columns)) != len(output_columns):
            raise ValueError("The remote key setup produces duplicate link columns.")

        source_by_output: dict[str, str] = dict(zip(output_columns, remote_columns_to_select))
        mapped_remote_keys: list[str] = [setup.rename_map.get(key, key) for key in fk.remote_keys]
        if len(set(mapped_remote_keys)) != len(mapped_remote_keys):
            raise ValueError("The selected remote keys resolve to duplicate link columns.")

        missing_outputs: list[str] = [key for key in mapped_remote_keys if key not in source_by_output]
        if missing_outputs:
            raise KeyError(f"Remote link keys are unavailable after production column mapping: {missing_outputs}")

        local_key_frame: pd.DataFrame = local_rows.loc[:, fk.local_keys].copy()
        remote_sources: list[str] = [source_by_output[key] for key in mapped_remote_keys]
        remote_key_frame: pd.DataFrame = remote_rows.loc[:, remote_sources].copy()
        remote_key_frame.columns = mapped_remote_keys
        return local_key_frame, remote_key_frame, mapped_remote_keys

    @staticmethod
    def _estimate_output_rows(
        local_key_frame: pd.DataFrame,
        remote_key_frame: pd.DataFrame,
        local_keys: list[str],
        remote_keys: list[str],
        runtime_options: ForeignKeyRuntimeOptions,
        how: str,
    ) -> tuple[int, int]:
        """Estimate production and diagnostic output sizes without expanding matches."""
        estimate_local, estimate_remote = _coerce_compatible_merge_key_dtypes(
            local_key_frame.copy(),
            remote_key_frame.copy(),
            local_keys,
            remote_keys,
        )
        local_counts: dict[tuple[Any, ...], int] = LinkTrialService._key_frequencies(
            estimate_local,
            local_keys,
            null_side="left",
            prevent_null_key_matches=runtime_options.prevent_null_key_matches,
        )
        remote_counts: dict[tuple[Any, ...], int] = LinkTrialService._key_frequencies(
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

    @staticmethod
    def _key_frequencies(
        frame: pd.DataFrame,
        keys: list[str],
        *,
        null_side: Literal["left", "right"],
        prevent_null_key_matches: bool,
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

    @staticmethod
    def _failed(reason: str, message: str) -> LinkTrialResult:
        """Return a named failure without partial counts or rows."""
        return LinkTrialResult(status="failed", reason=reason, message=message)
