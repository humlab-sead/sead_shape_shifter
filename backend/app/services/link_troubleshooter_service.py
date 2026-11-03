"""Coordinate the saved-link baseline and requested-key trial."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import pandas as pd

from backend.app.mappers.link_troubleshooter_mapper import LinkTroubleshooterMapper
from backend.app.models.link_troubleshooter import (
    LinkTroubleshootKeyOptions,
    LinkTroubleshootKeys,
    LinkTroubleshootRelationship,
    LinkTroubleshootResponse,
    LinkTroubleshootRowFilter,
)
from backend.app.services.link_baseline_service import LinkBaselineResult, LinkBaselineService
from backend.app.services.link_trial_service import LinkTrialResult, LinkTrialService
from src.model import ForeignKeyConfig


class LinkTroubleshooterService:
    """Build read-only diagnostics for a saved foreign-key link."""

    def __init__(
        self,
        baseline_service: LinkBaselineService | None = None,
        trial_service: LinkTrialService | None = None,
    ) -> None:
        """Create the baseline and trial services used for each request."""
        self.baseline_service: LinkBaselineService = baseline_service or LinkBaselineService()
        self.trial_service: LinkTrialService = trial_service or LinkTrialService()

    async def run(
        self,
        *,
        project_name: str,
        issue_type: str,
        local_entity: str,
        metadata: Mapping[str, Any],
        local_keys: Sequence[str] | None = None,
        remote_keys: Sequence[str] | None = None,
        page: int = 1,
        page_size: int = 50,
        row_filter: LinkTroubleshootRowFilter = "all",
    ) -> LinkTroubleshootResponse:
        """Replay the configured link and optionally compare a requested key pair."""
        baseline: LinkBaselineResult = await self.baseline_service.build_baseline(
            project_name=project_name,
            issue_type=issue_type,
            local_entity=local_entity,
            metadata=metadata,
        )
        fk: ForeignKeyConfig | None = baseline._foreign_key

        if not baseline.is_reproduced:
            return self._map_without_trial(
                baseline,
                fk,
                local_keys=local_keys,
                remote_keys=remote_keys,
                page=page,
                page_size=page_size,
                row_filter=row_filter,
            )

        if baseline.local_rows is None or baseline.remote_rows is None or baseline._saved_project is None or fk is None:
            baseline = replace(
                baseline,
                status="not_reproduced",
                reason="baseline_context_missing",
                message="The reproduced baseline is missing the project, foreign key, or input rows required for a trial.",
                local_rows=None,
                remote_rows=None,
            )
            return self._map_without_trial(
                baseline,
                fk,
                local_keys=local_keys,
                remote_keys=remote_keys,
                page=page,
                page_size=page_size,
                row_filter=row_filter,
            )

        configured_keys = LinkTroubleshootKeys(local_keys=fk.local_keys, remote_keys=fk.remote_keys)
        relationship = self._relationship(baseline, fk)
        key_options = LinkTroubleshootKeyOptions(
            local=self._key_options(baseline.local_rows, fk.local_keys),
            remote=self._key_options(baseline.remote_rows, fk.remote_keys),
        )

        baseline_trial: LinkTrialResult = self.trial_service.run_trial(
            baseline,
            local_keys=fk.local_keys,
            remote_keys=fk.remote_keys,
        )
        if baseline_trial.status == "complete" and (
            baseline_trial.input_a_rows != baseline.row_count_before or baseline_trial.output_rows != baseline.row_count_after
        ):
            baseline_trial = replace(
                baseline_trial,
                status="failed",
                reason="baseline_counts_mismatch",
                message="Configured-key diagnostics did not match the reproduced baseline row counts.",
                input_a_rows=None,
                output_rows=None,
                unmatched_a_rows=None,
                multiply_matched_a_rows=None,
                a_rows=None,
            )

        if local_keys is None and remote_keys is None:
            selected_local_keys: list[str] = list(fk.local_keys)
            selected_remote_keys: list[str] = list(fk.remote_keys)
        else:
            selected_local_keys = list(local_keys) if local_keys is not None else []
            selected_remote_keys = list(remote_keys) if remote_keys is not None else []

        if selected_local_keys == fk.local_keys and selected_remote_keys == fk.remote_keys:
            requested_trial: LinkTrialResult = baseline_trial
        else:
            requested_trial = self.trial_service.run_trial(
                baseline,
                local_keys=selected_local_keys,
                remote_keys=selected_remote_keys,
            )

        if requested_trial.status == "complete" and requested_trial.input_a_rows != baseline.row_count_before:
            requested_trial = replace(
                requested_trial,
                status="failed",
                reason="baseline_input_mismatch",
                message="The requested-key trial input count did not match the reproduced baseline.",
                input_a_rows=None,
                output_rows=None,
                unmatched_a_rows=None,
                multiply_matched_a_rows=None,
                a_rows=None,
            )

        return LinkTroubleshooterMapper.to_response(
            baseline=baseline,
            baseline_trial=baseline_trial,
            trial=requested_trial,
            relationship=relationship,
            key_options=key_options,
            configured_keys=configured_keys,
            trial_local_keys=selected_local_keys,
            trial_remote_keys=selected_remote_keys,
            page=page,
            page_size=page_size,
            row_filter=row_filter,
        )

    def _map_without_trial(
        self,
        baseline: LinkBaselineResult,
        fk: ForeignKeyConfig | None,
        *,
        local_keys: Sequence[str] | None,
        remote_keys: Sequence[str] | None,
        page: int,
        page_size: int,
        row_filter: LinkTroubleshootRowFilter,
    ) -> LinkTroubleshootResponse:
        """Map a baseline that cannot support a requested-key trial."""
        configured_keys = LinkTroubleshootKeys(local_keys=fk.local_keys, remote_keys=fk.remote_keys) if fk is not None else None
        selected_local_keys: list[str] = list(local_keys) if local_keys is not None else list(fk.local_keys if fk is not None else ())
        selected_remote_keys: list[str] = list(remote_keys) if remote_keys is not None else list(fk.remote_keys if fk is not None else ())

        return LinkTroubleshooterMapper.to_response(
            baseline=baseline,
            baseline_trial=None,
            trial=None,
            relationship=self._relationship(baseline, fk) if fk is not None else None,
            key_options=None,
            configured_keys=configured_keys,
            trial_local_keys=selected_local_keys,
            trial_remote_keys=selected_remote_keys,
            page=page,
            page_size=page_size,
            row_filter=row_filter,
        )

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
