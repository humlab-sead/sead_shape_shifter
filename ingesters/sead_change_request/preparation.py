"""Shared preparation workflow for the SEAD change request ingester."""

from dataclasses import asdict, dataclass, field
from typing import Any

from ingesters.sead_change_request.contracts import (
    IdentityAssignment,
    IdentityResolutionResult,
    IdentityWorkPlan,
    PendingConfirmationReport,
    PlannedTable,
    SourceTableBundle,
    SubmissionContext,
    SubmissionOutcomeSummary,
    TargetProjectionResult,
    classify_submission_outcomes,
)
from ingesters.sead_change_request.identity_resolution import resolve_planned_tables
from ingesters.sead_change_request.identity_work import build_identity_work_plan
from ingesters.sead_change_request.orchestration import IdentityOrchestrationResult, orchestrate_identity_assignments
from ingesters.sead_change_request.target_projection import project_target_ids
from src.target_model.models import TargetModel


@dataclass(frozen=True)
class ResolvedInputs:
    """Resolved input values prepared for the shared workflow."""

    bundle: SourceTableBundle
    target_model: TargetModel
    submission_context: SubmissionContext
    fallback_assignments: dict[str, dict[object, IdentityAssignment]]
    mutable_fields_by_entity: dict[str, list[str]]
    existing_row_update_entities: set[str] | None
    deploy_strategy: Any | None


@dataclass(frozen=True)
class PlannedBundle:
    """Planning output plus diagnostics."""

    tables: list[PlannedTable]
    errors: list[str]
    warnings: list[str]
    infos: list[str]
    work_plan: IdentityWorkPlan = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_plan", build_identity_work_plan(self.tables))


@dataclass(frozen=True)
class PreparationResult:
    """Shared preparation pipeline output for validation and ingestion."""

    inputs: ResolvedInputs
    planned: PlannedBundle
    orchestration_result: IdentityOrchestrationResult
    resolution_result: IdentityResolutionResult
    projection_result: TargetProjectionResult
    outcome_summary: SubmissionOutcomeSummary
    pending_confirmation_report: dict[str, Any] | None = None


async def prepare_change_request(
    inputs: ResolvedInputs,
    planned: PlannedBundle,
    *,
    sims_client: Any | None,
    reconciliation_client: Any | None,
) -> PreparationResult:
    """Run the shared preparation workflow after inputs are resolved."""
    orchestration_result: IdentityOrchestrationResult = await orchestrate_identity_assignments(
        planned.tables,
        inputs.submission_context,
        sims_client=sims_client,
        reconciliation_client=reconciliation_client,
        fallback_assignments=inputs.fallback_assignments,
    )
    if orchestration_result.binding_set_uuid and not inputs.submission_context.binding_set_uuid:
        inputs.submission_context.binding_set_uuid = orchestration_result.binding_set_uuid

    resolution_result: IdentityResolutionResult = resolve_planned_tables(
        planned.tables,
        inputs.target_model,
        orchestration_result.assignments,
    )
    projection_result: TargetProjectionResult = project_target_ids(resolution_result, inputs.target_model)
    pending_confirmation_report = _build_pending_confirmation_report(
        inputs.submission_context,
        orchestration_result,
        resolution_result,
    )
    outcome_summary = classify_submission_outcomes(
        planned.tables,
        resolution_result,
        has_pending_review=pending_confirmation_report is not None,
        mutable_fields_by_entity=inputs.mutable_fields_by_entity,
    )

    return PreparationResult(
        inputs=inputs,
        planned=planned,
        orchestration_result=orchestration_result,
        resolution_result=resolution_result,
        projection_result=projection_result,
        outcome_summary=outcome_summary,
        pending_confirmation_report=pending_confirmation_report,
    )


def _build_pending_confirmation_report(
    submission_context: SubmissionContext,
    orchestration_result: IdentityOrchestrationResult,
    resolution_result: IdentityResolutionResult,
) -> dict[str, Any] | None:
    """Build the pending confirmation payload when identity work remains blocked."""
    if (
        not orchestration_result.binding_set_state
        or orchestration_result.binding_set_state == "confirmed"
        or not resolution_result.blocked_rows
    ):
        return None

    return asdict(
        PendingConfirmationReport.create(
            submission_context,
            resolution_result,
            binding_set_state=orchestration_result.binding_set_state,
        )
    )
