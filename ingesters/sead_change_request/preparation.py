"""Shared preparation workflow for the SEAD change request ingester."""

from dataclasses import asdict, dataclass, field
from typing import Any

from ingesters.sead_change_request.capability_preflight import preflight_capabilities
from ingesters.sead_change_request.contracts import (
    CapabilityPreflightResult,
    ChangeRequestPackage,
    IdentityAssignment,
    IdentityResolutionResult,
    IdentityWorkPlan,
    PendingConfirmationReport,
    PlannedTable,
    SourceTableBundle,
    SubmissionContext,
    SubmissionOutcomeSummary,
    TargetProjectionResult,
    TrustedProjectContext,
    classify_submission_outcomes,
)
from ingesters.sead_change_request.direct_fk_validation import validate_direct_foreign_keys
from ingesters.sead_change_request.identity_resolution import resolve_planned_tables
from ingesters.sead_change_request.identity_work import build_identity_work_plan
from ingesters.sead_change_request.orchestration import (
    IdentityOrchestrationResult,
    orchestrate_identity_assignments,
)
from ingesters.sead_change_request.package_builder import build_change_request_package, build_staging_package
from ingesters.sead_change_request.staging_eligibility import (
    PendingDeploymentMap,
    collect_pending_deployment,
    resolve_staged_children,
)
from ingesters.sead_change_request.target_projection import project_target_ids
from src.target_model.models import TargetModel


@dataclass(frozen=True)
class ResolvedInputs:
    """Resolved input values prepared for the shared workflow."""

    bundle: SourceTableBundle
    target_model: TargetModel
    foreign_key_value_sources: dict[str, dict[str, str]]
    submission_context: SubmissionContext
    fallback_assignments: dict[str, dict[object, IdentityAssignment]]
    mutable_fields_by_entity: dict[str, list[str]]
    existing_row_update_entities: set[str] | None
    deploy_strategy: Any | None
    staging_target_schema: str | None = None
    trusted_project_context: TrustedProjectContext | None = None

    @property
    def is_staging(self) -> bool:
        """Return ``True`` when deployment-time staging was selected."""
        return self.staging_target_schema is not None


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
    preflight_result: CapabilityPreflightResult | None = None
    pending_deployment: PendingDeploymentMap = field(default_factory=PendingDeploymentMap)
    change_package: ChangeRequestPackage | None = None
    direct_fk_diagnostics: list[str] = field(default_factory=list)


async def prepare_change_request(
    inputs: ResolvedInputs,
    planned: PlannedBundle,
    *,
    sims_client: Any | None,
    reconciliation_client: Any | None,
    collision_checker: Any | None = None,
) -> PreparationResult:
    """Run the shared preparation workflow after inputs are resolved."""
    preflight_result: CapabilityPreflightResult | None = await _run_capability_preflight(
        planned.tables,
        inputs.target_model,
        sims_client,
    )

    orchestration_result: IdentityOrchestrationResult = await orchestrate_identity_assignments(
        planned.tables,
        inputs.submission_context,
        sims_client=sims_client,
        reconciliation_client=reconciliation_client,
        target_model_entities=inputs.target_model.entities,
        fallback_assignments=inputs.fallback_assignments,
    )
    if orchestration_result.binding_set_uuid and not inputs.submission_context.binding_set_uuid:
        inputs.submission_context.binding_set_uuid = orchestration_result.binding_set_uuid

    if inputs.is_staging:
        staged_children = resolve_staged_children(planned.tables, inputs.target_model, orchestration_result.assignments)
        for entity_name, entity_assignments in staged_children.assignments.items():
            orchestration_result.assignments.setdefault(entity_name, {}).update(entity_assignments)

    resolution_result: IdentityResolutionResult = resolve_planned_tables(
        planned.tables,
        inputs.target_model,
        orchestration_result.assignments,
    )
    pending_deployment = (
        collect_pending_deployment(
            resolution_result,
            inputs.target_model,
            foreign_key_value_sources=inputs.foreign_key_value_sources,
        )
        if inputs.is_staging
        else PendingDeploymentMap()
    )
    projection_result: TargetProjectionResult = project_target_ids(
        resolution_result,
        inputs.target_model,
        planned_tables=planned.tables,
        pending=pending_deployment,
        foreign_key_value_sources=inputs.foreign_key_value_sources,
    )
    change_package = (
        build_staging_package(
            resolution_result,
            planned.tables,
            inputs.target_model,
            str(inputs.staging_target_schema),
            foreign_key_value_sources=inputs.foreign_key_value_sources,
        )
        if inputs.is_staging
        else build_change_request_package(
            projection_result,
            resolution_result,
            planned.tables,
            foreign_key_value_sources=inputs.foreign_key_value_sources,
            target_model=inputs.target_model,
        )
    )
    direct_fk_diagnostics = await validate_direct_foreign_keys(
        change_package,
        inputs.target_model,
        collision_checker,
    )
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
        preflight_result=preflight_result,
        pending_deployment=pending_deployment,
        change_package=change_package,
        direct_fk_diagnostics=direct_fk_diagnostics,
    )


async def _run_capability_preflight(
    planned_tables: list[PlannedTable],
    target_model: TargetModel,
    sims_client: Any | None,
) -> CapabilityPreflightResult | None:
    """Run capability preflight when the SIMS client publishes capabilities.

    Returns None when no SIMS client is present or the client does not expose
    capability discovery, so callers without preflight support keep the existing
    non-SIMS behavior.
    """
    if sims_client is None:
        return None
    get_capabilities = getattr(sims_client, "get_capabilities", None)
    if get_capabilities is None:
        return None
    capabilities = await get_capabilities()
    return preflight_capabilities(planned_tables, target_model, capabilities)


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
