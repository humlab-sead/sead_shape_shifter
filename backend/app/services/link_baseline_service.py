"""Read-only baseline for one saved foreign-key link.

The service loads a saved project, resolves a linking warning to its saved
foreign key, replays the production pipeline on a temporary entity
configuration, and links the selected foreign key with the production linker.
It returns counts and findings in memory and never writes project data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, cast

import pandas as pd
from loguru import logger

from backend.app.core.config import Settings, get_settings
from backend.app.exceptions import ConfigurationError, ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.link_experiment_context_store import (
    BYTES_PER_MIB,
    ensure_projected_budget,
    ensure_retained_input_budget,
    estimate_output_rows,
    prepare_link_merge_keys,
    projected_merge_bytes,
    retained_input_bytes,
)
from backend.app.services.project_service import ProjectService
from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.specifications import ForeignKeyDataSpecification
from src.specifications.constraints import ForeignKeyConstraintViolation, ValidationIssue
from src.table_store import TableStore
from src.transforms.filter import normalize_filter_stage
from src.transforms.link import ForeignKeyLinker, LinkPass
from src.transforms.link_resolution import LinkIssueResolution, resolve_row_count_issue

BaselineStatus = Literal["reproduced", "not_reproduced", "ineligible"]
"""Outcome of building one link baseline."""

LINK_PASSES: tuple[str, ...] = ("initial", "after_unnest", "deferred_retry")
"""Linking passes the replay can reproduce."""

_REMOVED_FILTER_STAGES: dict[str, frozenset[str]] = {
    "initial": frozenset({"after_link", "after_unnest"}),
    "after_unnest": frozenset({"after_unnest"}),
    "deferred_retry": frozenset(),
}
"""Filter stages removed from the temporary entity config for each linking pass."""


@dataclass(frozen=True)
class LinkBaselineResult:
    """Baseline for one saved foreign-key link.

    Attributes:
        status: Whether the warning reproduced, could not reproduce, or was ineligible.
        reason: Machine-readable cause; ``"reproduced"`` when the warning reproduced.
        message: Human-readable explanation of ``reason``.
        entity_name: Local entity the link belongs to.
        remote_entity: Remote entity of the selected link, when known.
        fk_index: Position of the selected foreign key in the saved list.
        link_pass: Linking pass recorded in the warning.
        row_count_before: Observed local row count before the link.
        row_count_after: Observed row count after the link.
        issues: Validation issues raised by the selected link in this replay.
        local_rows: Replay input of the local entity, only when reproduction is proven.
        remote_rows: Replay input of the remote entity, only when reproduction is proven.
        _saved_project: Resolved project retained in memory for internal trial execution.
        _foreign_key: Saved foreign key retained in memory for internal trial execution.
    """

    status: BaselineStatus
    reason: str
    message: str
    entity_name: str
    remote_entity: str | None = None
    fk_index: int | None = None
    link_pass: str | None = None
    row_count_before: int | None = None
    row_count_after: int | None = None
    issues: tuple[ValidationIssue, ...] = ()
    local_rows: pd.DataFrame | None = field(default=None, repr=False, compare=False)
    remote_rows: pd.DataFrame | None = field(default=None, repr=False, compare=False)
    _saved_project: ShapeShiftProject | None = field(default=None, repr=False, compare=False)
    _foreign_key: ForeignKeyConfig | None = field(default=None, repr=False, compare=False)

    @property
    def is_reproduced(self) -> bool:
        """Return True only when the replayed warning matches the opened warning."""
        return self.status == "reproduced"


class _BaselineStop(Exception):
    """Stops baseline construction with a named non-reproduced reason."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason: str = reason
        self.message: str = message


def build_replay_project(saved_project: ShapeShiftProject, resolution: LinkIssueResolution) -> ShapeShiftProject:
    """Return a copy of the saved project configured for one linking pass.

    The local entity keeps only the foreign keys saved before the selected one,
    preserves the selected link's local keys in its columns, loses its business
    keys, and keeps the pipeline stages that run before the recorded linking pass.

    Args:
        saved_project: Resolved project that raised the warning.
        resolution: Resolved warning carrying the saved foreign key and linking pass.

    Returns:
        Independent project whose local entity reaches the selected linking pass.

    Raises:
        ValueError: If the resolution has no foreign key, index, or linking pass.
    """
    fk: ForeignKeyConfig | None = resolution.fk
    if fk is None or resolution.fk_index is None or resolution.link_pass is None:
        raise ValueError("A resolved foreign key with an index and a linking pass is required")

    saved_cfg: TableConfig = saved_project.get_table(fk.local_entity)
    unnest_dependent_dedup: bool = saved_cfg.is_drop_duplicate_dependent_on_unnesting()

    replay: ShapeShiftProject = saved_project.clone()
    entity_cfg: dict[str, Any] = replay.entities[fk.local_entity]

    columns: list[str] = list(entity_cfg.get("columns") or [])
    required_columns: list[str] = [key for key in fk.local_keys if key not in columns and key not in saved_cfg.unnest_columns]
    entity_cfg["columns"] = columns + required_columns
    entity_cfg["foreign_keys"] = list(entity_cfg.get("foreign_keys") or [])[: resolution.fk_index]
    entity_cfg["keys"] = []

    link_pass: str = resolution.link_pass

    if link_pass == "initial":
        entity_cfg.pop("unnest", None)
        entity_cfg.pop("drop_empty_rows", None)

    if unnest_dependent_dedup and link_pass in ("initial", "after_unnest"):
        entity_cfg.pop("drop_duplicates", None)

    removed_stages: frozenset[str] = _REMOVED_FILTER_STAGES[link_pass]
    if removed_stages:
        remaining: list[dict[str, Any]] = [
            filter_cfg for filter_cfg in entity_cfg.get("filters") or [] if normalize_filter_stage(filter_cfg) not in removed_stages
        ]
        if remaining:
            entity_cfg["filters"] = remaining
        else:
            entity_cfg.pop("filters", None)

    return replay


class LinkBaselineService:
    """Build a read-only baseline for one saved foreign-key link."""

    def __init__(self, project_service: ProjectService | None = None, settings: Settings | None = None) -> None:
        """Initialize the service.

        Args:
            project_service: Loads saved API projects. Defaults to a new service.
            settings: Backend settings holding the experiment memory limit.
        """
        self.project_service: ProjectService = project_service or ProjectService()
        self.settings: Settings = settings if settings is not None else get_settings()

    async def build_baseline(
        self,
        *,
        project_name: str,
        issue_type: str,
        local_entity: str,
        metadata: Mapping[str, Any],
    ) -> LinkBaselineResult:
        """Replay the saved link behind one linking warning.

        Args:
            project_name: Saved project name, as the project service knows it.
            issue_type: Type of the validation issue that offers the action.
            local_entity: Entity the warned foreign key belongs to.
            metadata: Issue metadata recorded by the linker.

        Returns:
            LinkBaselineResult describing the reproduced warning or the reason the
            warning does not reproduce.
        """
        api_project: Project | None = None
        try:
            api_project = self.project_service.load_project(project_name)
        except (ResourceNotFoundError, ConfigurationError) as exc:
            return self._stop("project_unavailable", str(exc), local_entity=local_entity)

        if api_project is None:
            return self._stop("project_unavailable", f"Project '{project_name}' was not loaded", local_entity=local_entity)

        api_project = api_project.model_copy(deep=True)

        try:
            saved_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
        except (ConfigurationError, ValueError, KeyError) as exc:
            return self._stop("project_unmappable", str(exc), local_entity=local_entity)

        resolution: LinkIssueResolution = resolve_row_count_issue(
            saved_project,
            issue_type=issue_type,
            local_entity=local_entity,
            metadata=metadata,
        )

        if not resolution.is_eligible:
            return self._result(
                status="ineligible",
                reason=resolution.status,
                message=f"The warning does not resolve to one supported saved link ({resolution.status})",
                local_entity=local_entity,
                remote_entity=resolution.fk.remote_entity if resolution.fk else None,
                fk_index=resolution.fk_index,
                link_pass=resolution.link_pass,
                _saved_project=saved_project if resolution.fk is not None else None,
                _foreign_key=resolution.fk,
            )

        fk: ForeignKeyConfig = cast(ForeignKeyConfig, resolution.fk)
        remote_entity: str = fk.remote_entity

        if not saved_project.has_table(remote_entity):
            return self._stop(
                "remote_entity_not_found",
                f"Remote entity '{remote_entity}' is not in the project",
                local_entity,
                fk,
                resolution,
                saved_project=saved_project,
            )

        if resolution.link_pass is None:
            return self._stop(
                "missing_link_pass",
                "The warning does not record a linking pass",
                local_entity,
                fk,
                resolution,
                saved_project=saved_project,
            )

        if resolution.link_pass not in LINK_PASSES:
            return self._stop(
                "unknown_link_pass",
                f"Linking pass '{resolution.link_pass}' is not one of {LINK_PASSES}",
                local_entity,
                fk,
                resolution,
                saved_project=saved_project,
            )

        expected_before: int | None = _as_int(metadata.get("row_count_before"))
        expected_after: int | None = _as_int(metadata.get("row_count_after"))
        expected_join: str = str(metadata.get("join_type") or fk.how or "inner")

        if expected_before is None or expected_after is None:
            return self._stop(
                "missing_warning_counts",
                "The warning does not record both row counts",
                local_entity,
                fk,
                resolution,
                saved_project=saved_project,
            )

        if expected_join != (fk.how or "inner"):
            return self._stop(
                "warning_join_mismatch",
                f"The warning records join type '{expected_join}' but the saved link uses '{fk.how or 'inner'}'",
                local_entity,
                fk,
                resolution,
                saved_project=saved_project,
            )

        replay_project: ShapeShiftProject = build_replay_project(saved_project, resolution)

        try:
            replay_store: TableStore = await self._replay(replay_project, local_entity, remote_entity)
            return self._link(replay_store, saved_project, replay_project, fk, resolution, expected_before, expected_after)
        except _BaselineStop as stop:
            return self._stop(stop.reason, stop.message, local_entity, fk, resolution, saved_project=saved_project)

    async def _replay(self, replay_project: ShapeShiftProject, local_entity: str, remote_entity: str) -> TableStore:
        """Run the production pipeline on the temporary config and return its tables."""
        try:
            normalizer: ShapeShifter = ShapeShifter(
                project=replay_project,
                default_entity=replay_project.metadata.default_entity,
                table_store=TableStore(),
                target_entities={local_entity, remote_entity},
            )
            await normalizer.normalize()
        except (ValueError, KeyError, FileNotFoundError, OSError) as exc:
            logger.info(f"[link-baseline]: replay failed for '{local_entity}' -> '{remote_entity}': {exc}")
            raise _BaselineStop("replay_failed", str(exc)) from exc

        store: TableStore = normalizer.table_store

        for entity_name in (local_entity, remote_entity):
            if entity_name not in store:
                raise _BaselineStop(f"{entity_name}_missing", f"Replay did not produce entity '{entity_name}'")

            if entity_name in normalizer.incomplete_entities:
                raise _BaselineStop(f"{entity_name}_incomplete", normalizer.incomplete_entities[entity_name])

        return store

    def _link(
        self,
        replay_store: TableStore,
        saved_project: ShapeShiftProject,
        replay_project: ShapeShiftProject,
        fk: ForeignKeyConfig,
        resolution: LinkIssueResolution,
        expected_before: int,
        expected_after: int,
    ) -> LinkBaselineResult:
        """Link the selected foreign key on the replay inputs and compare the warning."""
        specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=replay_project, table_store=replay_store)

        try:
            is_ready: bool = specification.is_satisfied_by(fk_cfg=fk)
        except ValueError as exc:
            raise _BaselineStop("link_not_ready", str(exc)) from exc

        if specification.deferred:
            raise _BaselineStop("link_deferred", specification.get_report())

        if not is_ready:
            raise _BaselineStop("link_not_ready", specification.get_report())

        if specification.is_already_linked(fk_cfg=fk):
            raise _BaselineStop("link_already_linked", f"'{fk.local_entity}' already contains the link for '{fk.remote_entity}'")

        local_input: pd.DataFrame = replay_store[fk.local_entity]
        remote_input: pd.DataFrame = replay_store[fk.remote_entity]
        limit_bytes: int = self.settings.LINK_EXPERIMENT_MAX_MEMORY_MB * BYTES_PER_MIB
        input_bytes: int = retained_input_bytes(local_input, remote_input)

        ensure_retained_input_budget(input_bytes, limit_bytes, stage="link reproduction")

        try:
            merge_keys = prepare_link_merge_keys(saved_project, fk, local_input, remote_input)
            estimated_link_rows, estimated_diagnostic_rows = estimate_output_rows(
                merge_keys.local_key_frame,
                merge_keys.remote_key_frame,
                fk.local_keys,
                merge_keys.mapped_remote_keys,
                merge_keys.runtime_options,
                merge_keys.join_type,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise _BaselineStop("link_not_ready", str(exc)) from exc

        null_key_temporaries: bool = bool(merge_keys.runtime_options.prevent_null_key_matches)
        projected_bytes: int = max(
            projected_merge_bytes(
                retained_bytes=input_bytes,
                input_bytes=input_bytes,
                local_rows=local_input,
                remote_rows=remote_input,
                local_keys=fk.local_keys,
                remote_output_columns=merge_keys.remote_output_columns,
                remote_source_by_output=merge_keys.remote_source_by_output,
                mapped_remote_keys=merge_keys.mapped_remote_keys,
                estimated_output_rows=estimated_link_rows,
                include_merge_indicator=True,
                null_key_temporaries=null_key_temporaries,
            ),
            projected_merge_bytes(
                retained_bytes=input_bytes,
                input_bytes=input_bytes,
                local_rows=merge_keys.local_key_frame,
                remote_rows=merge_keys.remote_key_frame,
                local_keys=fk.local_keys,
                remote_output_columns=merge_keys.mapped_remote_keys,
                remote_source_by_output={key: key for key in merge_keys.mapped_remote_keys},
                mapped_remote_keys=merge_keys.mapped_remote_keys,
                estimated_output_rows=estimated_diagnostic_rows,
                position_columns=2,
                null_key_temporaries=null_key_temporaries,
            ),
        )
        ensure_projected_budget(projected_bytes, limit_bytes, stage="link reproduction")

        local_rows: pd.DataFrame = local_input.copy()
        remote_rows: pd.DataFrame = remote_input.copy()

        linker: ForeignKeyLinker = ForeignKeyLinker(
            project=saved_project,
            table_store=TableStore({fk.local_entity: local_rows.copy(), fk.remote_entity: remote_rows.copy()}),
        )
        linker.link_pass = cast(LinkPass, resolution.link_pass)

        try:
            linker.link_foreign_key(local_rows.copy(), fk, remote_rows.copy())
        except ForeignKeyConstraintViolation as exc:
            raise _BaselineStop("constraint_violation", str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise _BaselineStop("link_failed", str(exc)) from exc

        if not linker.validators:
            raise _BaselineStop("link_failed", "The linker did not validate the selected link")

        issues: tuple[ValidationIssue, ...] = tuple(linker.validators[-1].issues)
        observed_before: int = linker.validators[-1].size_before_merge[0]
        observed_after: int = linker.validators[-1].size_after_merge[0]

        selected: list[ValidationIssue] = [
            issue
            for issue in issues
            if issue.issue_type == "row_count_mismatch"
            and issue.metadata.get("fk_index") == fk.fk_index
            and issue.metadata.get("fk_signature") == fk.identity_signature
            and issue.metadata.get("link_pass") == resolution.link_pass
        ]

        if not selected:
            return self._result(
                status="not_reproduced",
                reason="warning_not_raised",
                message="The replayed link raised no row-count warning",
                local_entity=fk.local_entity,
                remote_entity=fk.remote_entity,
                fk_index=fk.fk_index,
                link_pass=resolution.link_pass,
                row_count_before=observed_before,
                row_count_after=observed_after,
                issues=issues,
                _saved_project=saved_project,
                _foreign_key=fk,
            )

        warning: ValidationIssue = selected[0]
        observed_warning: tuple[Any, Any, Any] = (
            warning.metadata.get("row_count_before"),
            warning.metadata.get("row_count_after"),
            warning.metadata.get("join_type"),
        )

        if observed_warning != (expected_before, expected_after, fk.how or "inner"):
            return self._result(
                status="not_reproduced",
                reason="warning_changed",
                message=(
                    "The replayed warning differs from the opened warning: "
                    f"before={observed_warning[0]}, after={observed_warning[1]}, join={observed_warning[2]}"
                ),
                local_entity=fk.local_entity,
                remote_entity=fk.remote_entity,
                fk_index=fk.fk_index,
                link_pass=resolution.link_pass,
                row_count_before=observed_before,
                row_count_after=observed_after,
                issues=issues,
                _saved_project=saved_project,
                _foreign_key=fk,
            )

        return self._result(
            status="reproduced",
            reason="reproduced",
            message="The replayed link raised the opened warning",
            local_entity=fk.local_entity,
            remote_entity=fk.remote_entity,
            fk_index=fk.fk_index,
            link_pass=resolution.link_pass,
            row_count_before=observed_before,
            row_count_after=observed_after,
            issues=issues,
            local_rows=local_rows,
            remote_rows=remote_rows,
            _saved_project=saved_project,
            _foreign_key=fk,
        )

    def _stop(
        self,
        reason: str,
        message: str,
        local_entity: str,
        fk: ForeignKeyConfig | None = None,
        resolution: LinkIssueResolution | None = None,
        saved_project: ShapeShiftProject | None = None,
    ) -> LinkBaselineResult:
        """Return a non-reproduced result for a named cause."""
        logger.info(f"[link-baseline]: cannot reproduce warning: {reason}: {message}")
        return self._result(
            status="not_reproduced",
            reason=reason,
            message=message,
            local_entity=local_entity,
            remote_entity=fk.remote_entity if fk else None,
            fk_index=fk.fk_index if fk else None,
            link_pass=resolution.link_pass if resolution else None,
            _saved_project=saved_project,
            _foreign_key=fk,
        )

    @staticmethod
    def _result(
        *,
        status: BaselineStatus,
        reason: str,
        message: str,
        local_entity: str,
        remote_entity: str | None = None,
        fk_index: int | None = None,
        link_pass: str | None = None,
        row_count_before: int | None = None,
        row_count_after: int | None = None,
        issues: tuple[ValidationIssue, ...] = (),
        local_rows: pd.DataFrame | None = None,
        remote_rows: pd.DataFrame | None = None,
        _saved_project: ShapeShiftProject | None = None,
        _foreign_key: ForeignKeyConfig | None = None,
    ) -> LinkBaselineResult:
        """Build one baseline result."""
        return LinkBaselineResult(
            status=status,
            reason=reason,
            message=message,
            entity_name=local_entity,
            remote_entity=remote_entity,
            fk_index=fk_index,
            link_pass=link_pass,
            row_count_before=row_count_before,
            row_count_after=row_count_after,
            issues=issues,
            local_rows=local_rows,
            remote_rows=remote_rows,
            _saved_project=_saved_project,
            _foreign_key=_foreign_key,
        )


def _as_int(value: Any) -> int | None:
    """Return an integer warning count, or None when the value is not an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
