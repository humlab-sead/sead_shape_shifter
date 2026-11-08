"""Read-only inspection of unmatched foreign-key values for one configured link.

The service resolves an integrity warning to its saved foreign key, normalizes the
current project in a private run that writes nothing to shared caches, recomputes
the distinct unmatched keys through the production validator comparison, and
returns every distinct unmatched key plus every local row of one selected key. It
never edits projects, source data, or saved results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from loguru import logger

from backend.app.exceptions import ConfigurationError, ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.integrity_troubleshooter import (
    FULL_NORMALIZATION_SOURCE,
    IntegrityStatus,
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
from backend.app.services.integrity_troubleshooter_context_store import (
    ContextLookupState,
    IntegrityTroubleshooterContextStore,
    IntegrityTroubleshooterSnapshot,
    get_integrity_troubleshooter_context_store,
)
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

COLUMN_LIMIT = 20
"""Maximum columns returned for one selected value's rows."""


class _InspectionStop(Exception):
    """Stop inspection with a named non-reproduction reason."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason: str = reason
        self.message: str = message


@dataclass(frozen=True)
class IntegrityTroubleshooterContextResult:
    """Outcome of reading one retained integrity inspection."""

    state: ContextLookupState
    response: IntegrityTroubleshootResponse | None = None


class IntegrityTroubleshooterService:
    """Build a read-only inspection for one saved integrity warning."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        context_store: IntegrityTroubleshooterContextStore | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            project_service: Loads saved API projects. Defaults to a new service.
            context_store: Retains normalized data so a later read does not normalize again.
        """
        self.project_service: ProjectService = project_service or ProjectService()
        self.context_store: IntegrityTroubleshooterContextStore = (
            context_store if context_store is not None else get_integrity_troubleshooter_context_store()
        )

    async def inspect(
        self,
        *,
        project_name: str,
        issue_type: str,
        local_entity: str,
        metadata: Mapping[str, Any],
        selected_value_token: str | None = None,
        owner_principal_id: str | None = None,
        project_locator: str | None = None,
    ) -> IntegrityTroubleshootResponse:
        """Inspect the current unmatched values behind one integrity warning.

        Args:
            project_name: Saved project name as the project service knows it.
            issue_type: Type of the validation issue that offers the action.
            local_entity: Entity the warned foreign key belongs to.
            metadata: Issue metadata recorded by validation.
            selected_value_token: Optional token naming one value whose local rows are returned.

        Returns:
            IntegrityTroubleshootResponse describing the reproduced warning, every
            current unmatched value, and the rows of any selected value.
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
                message=f"The warning does not resolve to one configured link ({resolution.status})",
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
        unmatched_keys: frozenset[tuple[Any, ...]] = frozenset(comparison.unmatched_keys)

        # A supplied token is always answered against the current data, even when the
        # link is clean or the frames are unusable, so a changed value is never shown
        # as a stale row sample.
        selected: IntegrityTroubleshootRows | None = None
        columns: list[str] | None = None
        columns_truncated: bool = False
        if selected_value_token is not None:
            columns, columns_truncated = self._row_columns(saved_project, fk, local_df)
            selected = self._selected_rows(
                token=selected_value_token,
                unmatched_keys=unmatched_keys,
                local_df=local_df,
                columns=columns,
                columns_truncated=columns_truncated,
                fk=fk,
            )

        if comparison.status == "invalid_input":
            return self._response(
                status="not_reproduced",
                reason="invalid_input",
                message="The configured link's keys or columns cannot be compared in the current data.",
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
                values=IntegrityTroubleshootValuePage(distinct_value_count=0),
                selected=selected,
            )

        current_count: int = self._validator_count(local_df, remote_df, fk, comparison)
        status: IntegrityStatus = "reproduced" if current_count == recorded_count else "not_reproduced"
        reason = "reproduced" if status == "reproduced" else "count_changed"
        message = (
            "The current full-data unmatched count matches the warning."
            if status == "reproduced"
            else f"The current full-data unmatched count is {current_count} but the warning recorded {recorded_count}."
        )

        sorted_keys: list[tuple[Any, ...]] = sorted(comparison.unmatched_keys, key=_sort_key)
        row_counts: dict[tuple[Any, ...], int] = self._local_row_counts(local_df, fk)
        values_page: IntegrityTroubleshootValuePage = self._values(sorted_keys, row_counts)

        response: IntegrityTroubleshootResponse = self._response(
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
        if owner_principal_id is None or project_locator is None or relationship is None:
            return response

        if columns is None:
            columns, columns_truncated = self._row_columns(saved_project, fk, local_df)
        snapshot: IntegrityTroubleshooterSnapshot = IntegrityTroubleshooterSnapshot(
            status=status,
            reason=reason,
            message=message,
            relationship=relationship,
            configured_keys=configured_keys,
            recorded_orphan_count=recorded_count,
            current_orphan_count=current_count,
            local_rows=local_df.loc[:, columns].copy(),
            foreign_key=fk,
            unmatched_keys=unmatched_keys,
            sorted_keys=tuple(sorted_keys),
            row_counts=row_counts,
            columns=tuple(columns),
            columns_truncated=columns_truncated,
        )
        context = await self.context_store.open_context(
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
            snapshot=snapshot,
        )
        response.context_id = context.context_id
        response.expires_at = context.expires_at
        return response

    async def read_context(
        self,
        *,
        context_id: str,
        owner_principal_id: str,
        project_locator: str,
        selected_value_token: str | None = None,
    ) -> IntegrityTroubleshooterContextResult:
        """Return the complete inspection from an owned snapshot without normalization."""
        lookup = await self.context_store.lookup_context(
            context_id,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
        )
        if lookup.state != "found" or lookup.context is None:
            return IntegrityTroubleshooterContextResult(state=lookup.state)

        context = lookup.context
        snapshot: IntegrityTroubleshooterSnapshot = context.snapshot
        selected: IntegrityTroubleshootRows | None = None
        if selected_value_token is not None:
            selected = self._selected_rows(
                token=selected_value_token,
                unmatched_keys=snapshot.unmatched_keys,
                local_df=snapshot.local_rows,
                columns=list(snapshot.columns),
                columns_truncated=snapshot.columns_truncated,
                fk=snapshot.foreign_key,
            )

        response: IntegrityTroubleshootResponse = self._response(
            status=snapshot.status,
            reason=snapshot.reason,
            message=snapshot.message,
            relationship=snapshot.relationship,
            configured_keys=snapshot.configured_keys,
            recorded_orphan_count=snapshot.recorded_orphan_count,
            current_orphan_count=snapshot.current_orphan_count,
            values=self._values(snapshot.sorted_keys, snapshot.row_counts),
            selected=selected,
            context_id=context.context_id,
            expires_at=context.expires_at,
        )
        return IntegrityTroubleshooterContextResult(state="found", response=response)

    async def close_context(
        self,
        *,
        context_id: str,
        owner_principal_id: str,
        project_locator: str,
    ) -> bool:
        """Release one owned inspection snapshot."""
        return await self.context_store.close_context(
            context_id,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
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
        unmatched_keys: frozenset[tuple[Any, ...]],
        local_df: pd.DataFrame,
        columns: list[str],
        columns_truncated: bool,
        fk: ForeignKeyConfig,
    ) -> IntegrityTroubleshootRows:
        """Return every local row for one token-selected unmatched value."""
        try:
            key: tuple[Any, ...] = decode_key_token(token)
        except ValueError as exc:
            return IntegrityTroubleshootRows(status="unavailable", reason="invalid_token", message=str(exc))

        if key not in unmatched_keys:
            return IntegrityTroubleshootRows(
                status="unavailable",
                reason="value_no_longer_unmatched",
                message="The selected value no longer appears as an unmatched value in the current data.",
            )
        key_values: list[Any] = [_json_scalar(value) for value in key]
        matching_rows: pd.DataFrame = _select_rows(local_df, fk, key)
        rows: list[dict[str, Any]] = [
            {column: _json_scalar(to_key_scalar(row[column])) for column in columns} for _, row in matching_rows.iterrows()
        ]

        return IntegrityTroubleshootRows(
            status="selected",
            key_values=key_values,
            total_row_count=len(matching_rows),
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
    def _values(
        sorted_keys: Sequence[tuple[Any, ...]],
        row_counts: dict[tuple[Any, ...], int],
    ) -> IntegrityTroubleshootValuePage:
        """Return every ordered distinct key with its local row count."""
        values: list[IntegrityTroubleshootValue] = [
            IntegrityTroubleshootValue(
                key_values=[_json_scalar(value) for value in key],
                local_row_count=row_counts.get(key, 0),
                token=encode_key_token(key),
            )
            for key in sorted_keys
        ]

        return IntegrityTroubleshootValuePage(
            distinct_value_count=len(values),
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
        status: IntegrityStatus,
        reason: str,
        message: str,
        relationship: IntegrityTroubleshootRelationship | None = None,
        configured_keys: IntegrityTroubleshootKeys | None = None,
        recorded_orphan_count: int | None = None,
        current_orphan_count: int | None = None,
        values: IntegrityTroubleshootValuePage | None = None,
        selected: IntegrityTroubleshootRows | None = None,
        context_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> IntegrityTroubleshootResponse:
        """Build one inspection response."""
        return IntegrityTroubleshootResponse(
            status=status,
            reason=reason,
            message=message,
            source=FULL_NORMALIZATION_SOURCE,
            context_id=context_id,
            expires_at=expires_at,
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
