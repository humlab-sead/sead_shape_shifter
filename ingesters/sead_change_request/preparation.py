"""Shared preparation workflow for the SEAD change request ingester."""

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from ingesters.sead_change_request.capability_preflight import has_sims_identity_operations, preflight_capabilities
from ingesters.sead_change_request.contracts import (
    CapabilityPreflightResult,
    ChangeRequestPackage,
    IdentityAssignment,
    IdentityResolutionResult,
    IdentityWorkPlan,
    LocalOnlyApproval,
    PendingConfirmationReport,
    PlannedRowAction,
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
from src.reconciliation.mapping_model import encode_local_key
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
    local_key_columns_by_entity: dict[str, tuple[str, ...]] = field(default_factory=dict)
    local_only_approvals: dict[str, dict[str, LocalOnlyApproval]] = field(default_factory=dict)

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
    collision_checker: Any | None = None,
) -> PreparationResult:
    """Run the shared preparation workflow after inputs are resolved."""
    approved_existing_target_ids, link_errors = _verified_reconciliation_link_targets(inputs, planned.tables)
    planned.errors.extend(link_errors)
    preflight_result: CapabilityPreflightResult | None = None
    orchestration_result: IdentityOrchestrationResult
    if planned.errors:
        orchestration_result = IdentityOrchestrationResult()
    else:
        preflight_result = await _run_capability_preflight(
            planned.tables,
            inputs.target_model,
            sims_client,
            approved_existing_target_ids=approved_existing_target_ids,
        )
        if preflight_result is not None and preflight_result.has_blockers:
            orchestration_result = IdentityOrchestrationResult(assignments=inputs.fallback_assignments)
        else:
            orchestration_result = await orchestrate_identity_assignments(
                planned.tables,
                inputs.submission_context,
                sims_client=sims_client,
                database_sequence_reserver=collision_checker,
                target_model_entities=inputs.target_model.entities,
                fallback_assignments=inputs.fallback_assignments,
                approved_existing_target_ids=approved_existing_target_ids,
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
        approved_existing_target_ids=approved_existing_target_ids,
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


def _verified_reconciliation_link_targets(
    inputs: ResolvedInputs,
    planned_tables: list[PlannedTable],
) -> tuple[dict[str, dict[object, int]], list[str]]:
    """Match backend-verified accepted links to normalized rows before SIMS binding."""
    trusted_context = inputs.trusted_project_context
    if trusted_context is None:
        return {}, []

    planned_by_entity = {table.entity_name: table for table in planned_tables}
    targets_by_entity: dict[str, dict[object, int]] = {}
    errors: list[str] = []
    for entity_name, verified_links in trusted_context.verified_reconciliation_links.items():
        planned_table = planned_by_entity.get(entity_name)
        if planned_table is None:
            continue

        key_columns = trusted_context.local_key_columns_by_entity.get(entity_name, ())
        if not key_columns or any(column not in planned_table.frame.columns for column in key_columns):
            errors.append(f"Verified reconciliation links for '{entity_name}' require local-key columns in the normalized table")
            continue
        entity_spec = inputs.target_model.entities.get(entity_name)
        if entity_spec is None or not entity_spec.public_id or entity_spec.public_id not in planned_table.frame.columns:
            errors.append(f"Verified reconciliation links for '{entity_name}' require a normalized public-ID column")
            continue

        for row_index in planned_table.frame.index:
            encoded_key = encode_local_key(
                list(key_columns),
                [planned_table.frame.at[row_index, column] for column in key_columns],
            )
            target_id = verified_links.get(encoded_key)
            if target_id is None:
                continue

            planned_action = planned_table.planned_actions.at[row_index]
            if planned_action not in {PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE}:
                errors.append(f"Verified reconciliation link for '{entity_name}' key '{encoded_key}' has no normalized existing target ID")
                continue
            normalized_target_id = planned_table.frame.at[row_index, entity_spec.public_id]
            if pd.isna(normalized_target_id) or normalized_target_id != target_id:
                errors.append(
                    f"Verified reconciliation link for '{entity_name}' key '{encoded_key}' does not match "
                    f"normalized target ID '{entity_spec.public_id}'"
                )
                continue
            targets_by_entity.setdefault(entity_name, {})[row_index] = target_id

    return targets_by_entity, errors


async def _run_capability_preflight(
    planned_tables: list[PlannedTable],
    target_model: TargetModel,
    sims_client: Any | None,
    *,
    approved_existing_target_ids: dict[str, dict[object, int]] | None = None,
) -> CapabilityPreflightResult | None:
    """Run capability preflight when the SIMS client publishes capabilities.

    Returns None when no SIMS client is present or the client does not expose
    capability discovery, so callers without preflight support keep the existing
    non-SIMS behavior.
    """
    if sims_client is None or not has_sims_identity_operations(
        planned_tables,
        target_model,
        approved_existing_target_ids=approved_existing_target_ids,
    ):
        return None
    get_capabilities = getattr(sims_client, "get_capabilities", None)
    if get_capabilities is None:
        return None
    capabilities = await get_capabilities()
    return preflight_capabilities(
        planned_tables,
        target_model,
        capabilities,
        approved_existing_target_ids=approved_existing_target_ids,
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
