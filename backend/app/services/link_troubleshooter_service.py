"""Coordinate the saved-link baseline and requested-key trial."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, cast

import pandas as pd

from backend.app.core.config import Settings, get_settings
from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.mappers.link_troubleshooter_mapper import LinkTroubleshooterMapper
from backend.app.models.link_troubleshooter import (
    LinkExperimentContextResponse,
    LinkExperimentTrialResponse,
    LinkTroubleshootKeyOptions,
    LinkTroubleshootKeys,
    LinkTroubleshootRelationship,
)
from backend.app.services.link_baseline_service import LinkBaselineResult, LinkBaselineService
from backend.app.services.link_experiment_context_store import (
    ContextLookupState,
    LinkExperimentContext,
    LinkExperimentContextStore,
    LinkExperimentDiagnostics,
    LinkExperimentSnapshot,
    get_link_experiment_context_store,
)
from backend.app.services.link_trial_service import LinkTrialResult, LinkTrialService
from src.model import ForeignKeyConfig


@dataclass(frozen=True)
class LinkExperimentContextResult:
    """Outcome of one context read.

    ``unavailable`` covers an unknown identifier and an identifier owned by
    another user or project, so the route cannot reveal either case.
    """

    state: ContextLookupState
    response: LinkExperimentContextResponse | None = None


@dataclass(frozen=True)
class LinkExperimentTrialResult:
    """Outcome of one context trial.

    ``unavailable`` covers an unknown identifier and an identifier owned by
    another user or project, so the route cannot reveal either case.
    """

    state: ContextLookupState
    response: LinkExperimentTrialResponse | None = None


class LinkTroubleshooterService:
    """Build read-only diagnostics for a saved foreign-key link."""

    def __init__(
        self,
        baseline_service: LinkBaselineService | None = None,
        trial_service: LinkTrialService | None = None,
        context_store: LinkExperimentContextStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Create the baseline and trial services used for each request."""
        self.baseline_service: LinkBaselineService = baseline_service or LinkBaselineService()
        self.trial_service: LinkTrialService = trial_service or LinkTrialService()
        self.context_store: LinkExperimentContextStore = context_store if context_store is not None else get_link_experiment_context_store()
        self.settings: Settings = settings if settings is not None else get_settings()

    async def open_context(
        self,
        *,
        project_name: str,
        issue_type: str,
        local_entity: str,
        metadata: Mapping[str, Any],
        owner_principal_id: str,
        project_locator: str,
    ) -> LinkExperimentContextResponse:
        """Reproduce the warning and retain its inputs for later trials.

        A failed, incomplete, or unrun configured-key diagnostic still opens a
        context and is reported as an incomplete baseline. A warning that does
        not reproduce returns no identifier.

        Raises:
            ProjectedBudgetExceeded: If the retained inputs or the projected
                reproduction merge exceed the configured memory limit.
        """
        baseline: LinkBaselineResult = await self.baseline_service.build_baseline(
            project_name=project_name,
            issue_type=issue_type,
            local_entity=local_entity,
            metadata=metadata,
        )
        fk: ForeignKeyConfig | None = baseline._foreign_key

        if (
            not baseline.is_reproduced
            or fk is None
            or baseline.local_rows is None
            or baseline.remote_rows is None
            or baseline._saved_project is None
        ):
            return LinkTroubleshooterMapper.to_context_response(
                context_id=None,
                expires_at=None,
                baseline=baseline,
                diagnostics=None,
                relationship=self._relationship(baseline, fk) if fk is not None else None,
                key_options=None,
                configured_keys=LinkTroubleshootKeys(local_keys=fk.local_keys, remote_keys=fk.remote_keys) if fk is not None else None,
                row_cap=self.settings.LINK_EXPERIMENT_GROUP_ROW_CAP,
            )

        try:
            diagnostics = LinkExperimentDiagnostics.from_trial(self._configured_diagnostics(baseline, fk))
        except ProjectedBudgetExceeded as exc:
            diagnostics = LinkExperimentDiagnostics(
                status="incomplete",
                reason="projected_budget_exceeded",
                message=exc.message,
            )

        context: LinkExperimentContext = await self.context_store.open_context(
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
            snapshot=LinkExperimentSnapshot(baseline=baseline, diagnostics=diagnostics),
        )
        return self._context_response(context)

    async def read_context(
        self,
        *,
        context_id: str,
        owner_principal_id: str,
        project_locator: str,
    ) -> LinkExperimentContextResult:
        """Return one owned context's retained baseline state."""
        lookup = await self.context_store.lookup_context(
            context_id,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
        )
        if lookup.state != "found" or lookup.context is None:
            return LinkExperimentContextResult(state=lookup.state)
        return LinkExperimentContextResult(state="found", response=self._context_response(lookup.context))

    async def run_context_trial(
        self,
        *,
        context_id: str,
        owner_principal_id: str,
        project_locator: str,
        local_keys: Sequence[str],
        remote_keys: Sequence[str],
        how: str | None = None,
        allow_null_keys: bool | None = None,
        null_keys_equal: bool | None = None,
    ) -> LinkExperimentTrialResult:
        """Run one trial against an owned snapshot without reopening it."""
        lookup = await self.context_store.lookup_context(
            context_id,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
        )
        if lookup.state != "found" or lookup.context is None:
            return LinkExperimentTrialResult(state=lookup.state)

        context: LinkExperimentContext = lookup.context
        baseline: LinkBaselineResult = context.snapshot.baseline
        trial: LinkTrialResult = self.trial_service.run_trial(
            baseline,
            local_keys=local_keys,
            remote_keys=remote_keys,
            how=cast(Literal["inner", "left"] | None, how),
            allow_null_keys=allow_null_keys,
            null_keys_equal=null_keys_equal,
        )

        if trial.status == "complete" and trial.input_a_rows != baseline.row_count_before:
            trial = replace(
                trial,
                status="failed",
                reason="baseline_input_mismatch",
                message="The requested-key trial input count did not match the retained baseline.",
                input_a_rows=None,
                output_rows=None,
                unmatched_a_rows=None,
                multiply_matched_a_rows=None,
                a_rows=None,
                exception_groups=None,
            )

        response: LinkExperimentTrialResponse = LinkTroubleshooterMapper.to_context_trial_response(
            context_id=context.context_id,
            expires_at=context.expires_at,
            baseline=baseline,
            diagnostics=context.snapshot.diagnostics,
            trial=trial,
            local_keys=local_keys,
            remote_keys=remote_keys,
            row_cap=self.settings.LINK_EXPERIMENT_GROUP_ROW_CAP,
        )
        return LinkExperimentTrialResult(state="found", response=response)

    async def close_context(
        self,
        *,
        context_id: str,
        owner_principal_id: str,
        project_locator: str,
    ) -> bool:
        """Release one owned context and report whether it existed."""
        return await self.context_store.close_context(
            context_id,
            owner_principal_id=owner_principal_id,
            project_locator=project_locator,
        )

    def _context_response(self, context: LinkExperimentContext) -> LinkExperimentContextResponse:
        """Map one retained context to its baseline response."""
        baseline: LinkBaselineResult = context.snapshot.baseline
        fk: ForeignKeyConfig | None = baseline._foreign_key
        key_options: LinkTroubleshootKeyOptions | None = None
        if fk is not None and baseline.local_rows is not None and baseline.remote_rows is not None:
            key_options = LinkTroubleshootKeyOptions(
                local=self._key_options(baseline.local_rows, fk.local_keys),
                remote=self._key_options(baseline.remote_rows, fk.remote_keys),
            )

        return LinkTroubleshooterMapper.to_context_response(
            context_id=context.context_id,
            expires_at=context.expires_at,
            baseline=baseline,
            diagnostics=context.snapshot.diagnostics,
            relationship=self._relationship(baseline, fk) if fk is not None else None,
            key_options=key_options,
            configured_keys=LinkTroubleshootKeys(local_keys=fk.local_keys, remote_keys=fk.remote_keys) if fk is not None else None,
            row_cap=self.settings.LINK_EXPERIMENT_GROUP_ROW_CAP,
        )

    def _configured_diagnostics(self, baseline: LinkBaselineResult, fk: ForeignKeyConfig) -> LinkTrialResult:
        """Run the configured-key diagnostic and reject a row-count mismatch."""
        trial: LinkTrialResult = self.trial_service.run_trial(
            baseline,
            local_keys=fk.local_keys,
            remote_keys=fk.remote_keys,
            settings_source="saved",
        )
        if trial.status == "complete" and (
            trial.input_a_rows != baseline.row_count_before or trial.output_rows != baseline.row_count_after
        ):
            return replace(
                trial,
                status="failed",
                reason="baseline_counts_mismatch",
                message="Configured-key diagnostics did not match the reproduced baseline row counts.",
                input_a_rows=None,
                output_rows=None,
                unmatched_a_rows=None,
                multiply_matched_a_rows=None,
                a_rows=None,
                exception_groups=None,
            )
        return trial

    @staticmethod
    def _relationship(baseline: LinkBaselineResult, fk: ForeignKeyConfig) -> LinkTroubleshootRelationship:
        """Build the read-only saved foreign-key details."""
        return LinkTroubleshootRelationship(
            local_entity=fk.local_entity,
            remote_entity=fk.remote_entity,
            fk_index=fk.fk_index,
            join_type=fk.how or "inner",
            link_pass=baseline.link_pass,
            constraints=dict(fk.constraints.data),
        )

    @staticmethod
    def _key_options(rows: pd.DataFrame, configured_keys: Sequence[str]) -> list[str]:
        """Keep frame column order while hiding unconfigured system IDs."""
        return list(dict.fromkeys(column for column in rows.columns if column != "system_id" or column in configured_keys))
