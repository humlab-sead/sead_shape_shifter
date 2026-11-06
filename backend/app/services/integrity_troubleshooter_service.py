"""Read-only inspection of unmatched foreign-key values for one saved link.

The service resolves an integrity warning to its saved foreign key, normalizes the
current project in a private run that writes nothing to shared caches, recomputes
the distinct unmatched keys through the production validator comparison, and
returns a bounded value page plus an optional bounded row sample. It never edits
projects, source data, or saved results.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from loguru import logger

from backend.app.exceptions import ConfigurationError, ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.integrity_troubleshooter import (
    FULL_NORMALIZATION_SOURCE,
    IntegrityTroubleshootKeys,
    IntegrityTroubleshootRelationship,
    IntegrityTroubleshootResponse,
    IntegrityTroubleshootRows,
    IntegrityTroubleshootValue,
    IntegrityTroubleshootValuePage,
    decode_key_token,
    encode_key_token,
)
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.table_store import TableStore
from src.transforms.link_resolution import LinkIssueResolution, resolve_integrity_issue
from src.validators.data_validators import (
    ForeignKeyComparison,
    ForeignKeyIntegrityValidator,
    compare_foreign_key_values,
    to_key_scalar,
)

VALUE_PAGE_SIZE = 50
"""Maximum distinct unmatched values returned in one page."""

ROW_SAMPLE_LIMIT = 20
"""Maximum local rows returned for one selected value."""

COLUMN_LIMIT = 20
"""Maximum columns returned for one selected value's rows."""


class _InspectionStop(Exception):
    """Stop inspection with a named non-reproduction reason."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason: str = reason
        self.message: str = message


class IntegrityTroubleshooterService:
    """Build a read-only inspection for one saved integrity warning."""

    def __init__(self, project_service: ProjectService | None = None) -> None:
        """Initialize the service.

        Args:
            project_service: Loads saved API projects. Defaults to a new service.
        """
        self.project_service: ProjectService = project_service or ProjectService()

    async def inspect(
        self,
        *,
        project_name: str,
        issue_type: str,
        local_entity: str,
        metadata: Mapping[str, Any],
        page: int = 1,
        selected_value_token: str | None = None,
    ) -> IntegrityTroubleshootResponse:
        """Inspect the current unmatched values behind one integrity warning.

        Args:
            project_name: Saved project name as the project service knows it.
            issue_type: Type of the validation issue that offers the action.
            local_entity: Entity the warned foreign key belongs to.
            metadata: Issue metadata recorded by validation.
            page: One-based page of distinct unmatched values.
            selected_value_token: Optional token naming one value to sample.

        Returns:
            IntegrityTroubleshootResponse describing the reproduced warning, its
            current values, and any selected rows.
        """
        try:
            api_project: Project = self.project_service.load_project(project_name)
        except (ResourceNotFoundError, ConfigurationError) as exc:
            return self._response(
                status="not_reproduced",
                reason="project_unavailable",
                message=str(exc),
            )

        if api_project is None:
            return self._response(
                status="not_reproduced",
                reason="project_unavailable",
                message=f"Project '{project_name}' was not loaded",
            )

        api_project = api_project.model_copy(deep=True)

        try:
            saved_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
        except (ConfigurationError, ValueError, KeyError) as exc:
            return self._response(
                status="not_reproduced",
                reason="project_unmappable",
                message=str(exc),
            )

        resolution: LinkIssueResolution = resolve_integrity_issue(
            saved_project,
            issue_type=issue_type,
            local_entity=local_entity,
            metadata=metadata,
        )
        relationship: IntegrityTroubleshootRelationship | None = self._relationship(local_entity, resolution)

        if not resolution.is_eligible or resolution.fk is None:
            return self._response(
                status="ineligible",
                reason=resolution.status,
                message=f"The warning does not resolve to one saved link ({resolution.status})",
                relationship=relationship,
            )

        fk: ForeignKeyConfig = resolution.fk
        configured_keys: IntegrityTroubleshootKeys = IntegrityTroubleshootKeys(local_keys=fk.local_keys, remote_keys=fk.remote_keys)
        recorded_count: int | None = _as_int(metadata.get("orphan_count"))

        if recorded_count is None:
            return self._response(
                status="not_reproduced",
                reason="missing_warning_count",
                message="The warning does not record an integer unmatched-value count.",
                relationship=relationship,
                configured_keys=configured_keys,
            )

        try:
            local_df, remote_df = await self._normalize_frames(saved_project, fk)
        except _InspectionStop as stop:
            return self._response(
                status="not_reproduced",
                reason=stop.reason,
                message=stop.message,
                relationship=relationship,
                configured_keys=configured_keys,
                recorded_orphan_count=recorded_count,
            )

        comparison: ForeignKeyComparison = compare_foreign_key_values(local_df, remote_df, fk.fk_cfg)

        # A supplied token is always answered against the current data, even when the
        # link is clean or the frames are unusable, so a changed value is never shown
        # as a stale row sample.
        selected: IntegrityTroubleshootRows | None = None
        if selected_value_token is not None:
            selected = self._selected_rows(
                token=selected_value_token,
                comparison=comparison,
                local_df=local_df,
                saved_project=saved_project,
                fk=fk,
            )

        if comparison.status == "invalid_input":
            return self._response(
                status="not_reproduced",
                reason="invalid_input",
                message="The saved link's keys or columns cannot be compared in the current data.",
                relationship=relationship,
                configured_keys=configured_keys,
                recorded_orphan_count=recorded_count,
                selected=selected,
            )

        if comparison.status == "remote_empty":
            return self._response(
                status="not_reproduced",
                reason="remote_empty",
                message="The remote key has no values to match against in the current data.",
                relationship=relationship,
                configured_keys=configured_keys,
                recorded_orphan_count=recorded_count,
                selected=selected,
            )

        if comparison.status == "matched":
            return self._response(
                status="not_reproduced",
                reason="no_unmatched_values",
                message="The current data has no unmatched values for this link.",
                relationship=relationship,
                configured_keys=configured_keys,
                recorded_orphan_count=recorded_count,
                current_orphan_count=0,
                values=IntegrityTroubleshootValuePage(
                    page=page,
                    page_size=VALUE_PAGE_SIZE,
                    distinct_value_count=0,
                    returned_value_count=0,
                    has_next=False,
                ),
                selected=selected,
            )

        current_count: int = self._validator_count(local_df, remote_df, fk, comparison)
        status = "reproduced" if current_count == recorded_count else "not_reproduced"
        reason = "reproduced" if status == "reproduced" else "count_changed"
        message = (
            "The current full-data unmatched count matches the warning."
            if status == "reproduced"
            else f"The current full-data unmatched count is {current_count} but the warning recorded {recorded_count}."
        )

        sorted_keys: list[tuple[Any, ...]] = sorted(comparison.unmatched_keys, key=_sort_key)
        row_counts: dict[tuple[Any, ...], int] = self._local_row_counts(local_df, fk)
        values_page: IntegrityTroubleshootValuePage = self._value_page(sorted_keys, row_counts, page)

        return self._response(
            status=status,
            reason=reason,
            message=message,
            relationship=relationship,
            configured_keys=configured_keys,
            recorded_orphan_count=recorded_count,
            current_orphan_count=current_count,
            values=values_page,
            selected=selected,
        )

    async def _normalize_frames(self, saved_project: ShapeShiftProject, fk: ForeignKeyConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Normalize the saved project privately and return the link's two frames.

        The run uses a fresh table store and the saved project clone, never the
        cache-writing service, so it leaves projects, source data, and shared
        caches unchanged.
        """
        if not saved_project.has_table(fk.remote_entity):
            raise _InspectionStop("remote_entity_not_found", f"Remote entity '{fk.remote_entity}' is not in the project")

        try:
            normalizer = ShapeShifter(project=saved_project.clone(), table_store=TableStore())
            await normalizer.normalize()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.info(f"[integrity-troubleshooter]: normalization failed: {exc}")
            raise _InspectionStop("normalization_failed", str(exc)) from exc

        for entity_name in (fk.local_entity, fk.remote_entity):
            if entity_name in normalizer.incomplete_entities:
                raise _InspectionStop(f"{entity_name}_incomplete", normalizer.incomplete_entities[entity_name])
            if entity_name not in normalizer.table_store:
                raise _InspectionStop(f"{entity_name}_missing", f"Full normalization did not produce entity '{entity_name}'")

        return normalizer.table_store[fk.local_entity].copy(), normalizer.table_store[fk.remote_entity].copy()

    @staticmethod
    def _validator_count(
        local_df: pd.DataFrame,
        remote_df: pd.DataFrame,
        fk: ForeignKeyConfig,
        comparison: ForeignKeyComparison,
    ) -> int:
        """Return the current distinct unmatched count from the production validator.

        The shared comparison already proves the validator's null and deduplication
        rules. Calling the validator for the reported count keeps the reproduction
        claim tied to the same code that raises the warning.
        """
        if comparison.status != "unmatched":
            return comparison.orphan_count

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk.fk_cfg, fk.local_entity)
        for issue in issues:
            if issue.code != "FK_DATA_INTEGRITY":
                continue
            count = issue.metadata.get("orphan_count")
            if isinstance(count, int) and not isinstance(count, bool):
                return count

        return comparison.orphan_count

    def _selected_rows(
        self,
        *,
        token: str,
        comparison: ForeignKeyComparison,
        local_df: pd.DataFrame,
        saved_project: ShapeShiftProject,
        fk: ForeignKeyConfig,
    ) -> IntegrityTroubleshootRows:
        """Return bounded local rows for one token-selected unmatched value."""
        try:
            decode_key_token(token)
        except ValueError as exc:
            return IntegrityTroubleshootRows(status="unavailable", reason="invalid_token", message=str(exc))

        unmatched_keys_by_token: dict[str, tuple[Any, ...]] = {
            encode_key_token(candidate): candidate for candidate in comparison.unmatched_keys
        }
        key: tuple[Any, ...] | None = unmatched_keys_by_token.get(token)

        if key is None:
            return IntegrityTroubleshootRows(
                status="unavailable",
                reason="value_no_longer_unmatched",
                message="The selected value no longer appears as an unmatched value in the current data.",
            )

        key_values: list[Any] = [_json_scalar(value) for value in key]
        columns, columns_truncated = self._row_columns(saved_project, fk, local_df)
        matching_rows: pd.DataFrame = _select_rows(local_df, fk, key)
        total_rows: int = len(matching_rows)
        sample: pd.DataFrame = matching_rows.head(ROW_SAMPLE_LIMIT)
        rows: list[dict[str, Any]] = [
            {column: _json_scalar(to_key_scalar(row[column])) for column in columns} for _, row in sample.iterrows()
        ]

        return IntegrityTroubleshootRows(
            status="selected",
            key_values=key_values,
            total_row_count=total_rows,
            returned_row_count=len(rows),
            columns=columns,
            columns_truncated=columns_truncated,
            rows=rows,
        )

    @staticmethod
    def _local_row_counts(local_df: pd.DataFrame, fk: ForeignKeyConfig) -> dict[tuple[Any, ...], int]:
        """Count local rows per unmatched-key tuple with the validator's null rules."""
        local_keys: Sequence[str] = fk.local_keys
        null_keys_equal: bool = bool(fk.constraints.data.get("null_keys_equal", False))

        if not all(key in local_df.columns for key in local_keys):
            return {}

        counts: dict[tuple[Any, ...], int] = {}
        for row in local_df[list(local_keys)].itertuples(index=False, name=None):
            key: tuple[Any, ...] = tuple(to_key_scalar(value) for value in row)
            if not null_keys_equal and any(value is None for value in key):
                continue
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _value_page(
        sorted_keys: list[tuple[Any, ...]],
        row_counts: dict[tuple[Any, ...], int],
        page: int,
    ) -> IntegrityTroubleshootValuePage:
        """Slice the ordered distinct keys into one bounded page."""
        total: int = len(sorted_keys)
        start: int = (page - 1) * VALUE_PAGE_SIZE
        end: int = start + VALUE_PAGE_SIZE
        page_keys: list[tuple[Any, ...]] = sorted_keys[start:end]

        values: list[IntegrityTroubleshootValue] = [
            IntegrityTroubleshootValue(
                key_values=[_json_scalar(value) for value in key],
                local_row_count=row_counts.get(key, 0),
                token=encode_key_token(key),
            )
            for key in page_keys
        ]

        return IntegrityTroubleshootValuePage(
            page=page,
            page_size=VALUE_PAGE_SIZE,
            distinct_value_count=total,
            returned_value_count=len(values),
            has_next=end < total,
            values=values,
        )

    @staticmethod
    def _row_columns(
        saved_project: ShapeShiftProject,
        fk: ForeignKeyConfig,
        local_df: pd.DataFrame,
    ) -> tuple[list[str], bool]:
        """Choose available sample columns: FK keys, business keys, then target-facing columns."""
        available: set[str] = set(local_df.columns)
        table_cfg: TableConfig = saved_project.get_table(fk.local_entity)

        candidates: list[str] = []
        candidates.extend(fk.local_keys)
        candidates.extend(table_cfg.safe_keys)
        candidates.extend(table_cfg.get_target_facing_columns())

        ordered: list[str] = [column for column in dict.fromkeys(candidates) if column in available]
        columns_truncated: bool = len(ordered) > COLUMN_LIMIT
        return ordered[:COLUMN_LIMIT], columns_truncated

    @staticmethod
    def _relationship(
        local_entity: str,
        resolution: LinkIssueResolution,
    ) -> IntegrityTroubleshootRelationship:
        """Build the read-only relationship details available for one resolution."""
        fk: ForeignKeyConfig | None = resolution.fk
        if fk is not None:
            return IntegrityTroubleshootRelationship(
                local_entity=fk.local_entity,
                remote_entity=fk.remote_entity,
                fk_index=fk.fk_index,
                join_type=fk.how or "inner",
                constraints=dict(fk.constraints.data),
            )

        return IntegrityTroubleshootRelationship(
            local_entity=local_entity,
            fk_index=resolution.fk_index,
        )

    @staticmethod
    def _response(
        *,
        status: str,
        reason: str,
        message: str,
        relationship: IntegrityTroubleshootRelationship | None = None,
        configured_keys: IntegrityTroubleshootKeys | None = None,
        recorded_orphan_count: int | None = None,
        current_orphan_count: int | None = None,
        values: IntegrityTroubleshootValuePage | None = None,
        selected: IntegrityTroubleshootRows | None = None,
    ) -> IntegrityTroubleshootResponse:
        """Build one inspection response."""
        return IntegrityTroubleshootResponse(
            status=status,  # type: ignore[arg-type]
            reason=reason,
            message=message,
            source=FULL_NORMALIZATION_SOURCE,
            relationship=relationship,
            configured_keys=configured_keys,
            recorded_orphan_count=recorded_orphan_count,
            current_orphan_count=current_orphan_count,
            values=values,
            selected=selected,
        )


def _as_int(value: Any) -> int | None:
    """Return an integer warning count, or None when the value is not an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _json_scalar(value: Any) -> Any:
    """Return a JSON-serializable representation of one key scalar."""
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return str(value)


def _sort_key(key: tuple[Any, ...]) -> tuple[Any, ...]:
    """Return a total-order sort key for one mixed-type key tuple."""
    return tuple(_scalar_sort_key(value) for value in key)


def _scalar_sort_key(value: Any) -> tuple[int, float, str]:
    """Order null, bool, int, float, string, and other scalars deterministically."""
    if value is None:
        return (0, 0.0, "")
    if isinstance(value, bool):
        return (1, float(value), "")
    if isinstance(value, int):
        return (2, float(value), "")
    if isinstance(value, float):
        return (3, value, "")
    if isinstance(value, str):
        return (4, 0.0, value)
    return (5, 0.0, str(value))


def _select_rows(local_df: pd.DataFrame, fk: ForeignKeyConfig, key: tuple[Any, ...]) -> pd.DataFrame:
    """Return the local rows whose key matches ``key`` under the link's null rules."""
    local_keys: list[str] = fk.local_keys
    null_keys_equal: bool = bool(fk.constraints.data.get("null_keys_equal", False))

    if not all(column in local_df.columns for column in local_keys):
        return local_df.iloc[0:0]

    matches: list[bool] = []
    for row in local_df[local_keys].itertuples(index=False, name=None):
        normalized: tuple[Any, ...] = tuple(to_key_scalar(value) for value in row)
        if not null_keys_equal and any(value is None for value in normalized):
            matches.append(False)
        else:
            matches.append(normalized == key)

    return local_df[np.array(matches, dtype=bool)]
