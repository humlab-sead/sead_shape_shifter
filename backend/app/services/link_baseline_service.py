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

from backend.app.exceptions import ConfigurationError, ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
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
    loses its business keys, and keeps the pipeline stages that run before the
    recorded linking pass.

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

    def __init__(self, project_service: ProjectService | None = None) -> None:
        """Initialize the service.

        Args:
            project_service: Loads saved API projects. Defaults to a new service.
        """
        self.project_service: ProjectService = project_service or ProjectService()

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
            )

        fk: ForeignKeyConfig = cast(ForeignKeyConfig, resolution.fk)
        remote_entity: str = fk.remote_entity

        if not saved_project.has_table(remote_entity):
            return self._stop(
                "remote_entity_not_found", f"Remote entity '{remote_entity}' is not in the project", local_entity, fk, resolution
            )

        if resolution.link_pass is None:
            return self._stop("missing_link_pass", "The warning does not record a linking pass", local_entity, fk, resolution)

        if resolution.link_pass not in LINK_PASSES:
            return self._stop(
                "unknown_link_pass",
                f"Linking pass '{resolution.link_pass}' is not one of {LINK_PASSES}",
                local_entity,
                fk,
                resolution,
            )

        expected_before: int | None = _as_int(metadata.get("row_count_before"))
        expected_after: int | None = _as_int(metadata.get("row_count_after"))
        expected_join: str = str(metadata.get("join_type") or fk.how or "inner")

        if expected_before is None or expected_after is None:
            return self._stop("missing_warning_counts", "The warning does not record both row counts", local_entity, fk, resolution)

        if expected_join != (fk.how or "inner"):
            return self._stop(
                "warning_join_mismatch",
                f"The warning records join type '{expected_join}' but the saved link uses '{fk.how or 'inner'}'",
                local_entity,
                fk,
                resolution,
            )

        replay_project: ShapeShiftProject = build_replay_project(saved_project, resolution)

        try:
            replay_store: TableStore = await self._replay(replay_project, local_entity, remote_entity)
            return self._link(replay_store, saved_project, replay_project, fk, resolution, expected_before, expected_after)
        except _BaselineStop as stop:
            return self._stop(stop.reason, stop.message, local_entity, fk, resolution)

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

        local_rows: pd.DataFrame = replay_store[fk.local_entity].copy()
        remote_rows: pd.DataFrame = replay_store[fk.remote_entity].copy()

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
        )

    def _stop(
        self,
        reason: str,
        message: str,
        local_entity: str,
        fk: ForeignKeyConfig | None = None,
        resolution: LinkIssueResolution | None = None,
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
        )


def _as_int(value: Any) -> int | None:
    """Return an integer warning count, or None when the value is not an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
