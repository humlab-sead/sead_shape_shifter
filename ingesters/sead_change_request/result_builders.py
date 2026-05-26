"""Validation and ingestion result builders for the SEAD change request ingester."""

from loguru import logger

from backend.app.ingesters.protocol import IngestionResult, ValidationResult
from ingesters.sead_change_request.input_resolution import InputResolutionError
from ingesters.sead_change_request.orchestration import SIMS_TARGET_ID_CAPABILITY_NOTE
from ingesters.sead_change_request.preparation import PreparationResult


def build_validation_result(preparation: PreparationResult) -> ValidationResult:
    """Build the protocol validation result from a shared preparation output."""
    validation_errors = preparation.planned.errors + preparation.materialization_result.diagnostics
    warnings = list(preparation.planned.warnings)

    if preparation.resolution_result.blocked_rows:
        validation_errors.extend(preparation.resolution_result.diagnostics)
    else:
        warnings.extend(preparation.resolution_result.diagnostics)

    return ValidationResult(
        is_valid=len(validation_errors) == 0,
        errors=validation_errors,
        warnings=warnings,
        infos=build_validation_infos(preparation),
        pending_confirmation_report=preparation.pending_confirmation_report,
    )


def build_validation_infos(preparation: PreparationResult) -> list[str]:
    """Build the informational validation messages from a shared preparation output."""
    total_rows = sum(len(frame.index) for frame in preparation.inputs.bundle.tables.values())
    infos: list[str] = [
        f"Validated DataFrame-first handoff with {len(preparation.inputs.bundle.tables)} table(s)",
        f"Validated {total_rows} row(s) across the source bundle",
        f"Validated target model with {len(preparation.inputs.target_model.entities)} entity definition(s)",
        (
            f"Validated submission context for '{preparation.inputs.submission_context.submission_name}' "
            f"in project '{preparation.inputs.submission_context.project_name}'"
        ),
    ]

    if preparation.inputs.bundle.source_name:
        infos.append(f"Source bundle name: {preparation.inputs.bundle.source_name}")

    if preparation.inputs.submission_context.datatype:
        infos.append(f"Submission context datatype: {preparation.inputs.submission_context.datatype}")

    infos.extend(
        [f"Submission timestamp: {preparation.inputs.submission_context.timestamp.isoformat()}"]
        + (
            [f"Binding Set UUID: {preparation.inputs.submission_context.binding_set_uuid}"]
            if preparation.inputs.submission_context.binding_set_uuid
            else []
        )
        + (
            [f"Requested CR name: {preparation.inputs.submission_context.change_request_name}"]
            if preparation.inputs.submission_context.change_request_name
            else []
        )
        + preparation.planned.infos
        + summarize_identity_work(preparation)
        + [
            f"Resolved identity tables: {len(preparation.resolution_result.tables)}",
            f"Blocked rows after identity resolution: {preparation.resolution_result.blocked_rows}",
            f"Materialized tables: {len(preparation.materialization_result.tables)}",
        ]
    )
    return infos


def summarize_identity_work(preparation: PreparationResult) -> list[str]:
    """Summarize the planned identity work for validation reporting."""
    work_plan = preparation.planned.work_plan
    return [
        (
            "Identity work queues: "
            f"{work_plan.total_existing_rows} existing, "
            f"{work_plan.total_allocation_rows} allocation, "
            f"{work_plan.total_reconciliation_rows} reconciliation, "
            f"{work_plan.total_bridge_rows} bridge"
        )
    ]


def build_validation_input_failure(exc: InputResolutionError) -> ValidationResult:
    """Build a validation failure result for expected input-resolution errors."""
    logger.warning("SEAD change request validation failed while resolving {} input: {}", exc.scope, exc.user_message)
    return ValidationResult(is_valid=False, errors=[exc.user_message], warnings=list(exc.warnings), infos=[])


def build_ingestion_input_failure(exc: InputResolutionError) -> IngestionResult:
    """Build an ingestion failure result for expected input-resolution errors."""
    logger.warning("SEAD change request ingest failed while resolving {} input: {}", exc.scope, exc.user_message)
    return IngestionResult.create_failed_result(message=exc.ingest_message, details=exc.user_message)


def check_ingestion_preconditions(preparation: PreparationResult) -> IngestionResult | None:
    """Return a failed ingestion result when preparation did not reach a deployable state."""
    if preparation.planned.errors:
        return IngestionResult.create_failed_result(
            message="Validation failed",
            details=failure_details(preparation.planned.errors),
        )

    if preparation.resolution_result.blocked_rows:
        return IngestionResult.create_failed_result(
            message=_identity_resolution_message(
                preparation.resolution_result.diagnostics,
                preparation.pending_confirmation_report,
            ),
            details=failure_details(preparation.resolution_result.diagnostics),
            pending_confirmation_report=preparation.pending_confirmation_report,
        )

    if preparation.materialization_result.diagnostics:
        return IngestionResult.create_failed_result(
            message="PK/FK materialization incomplete",
            details=failure_details(preparation.materialization_result.diagnostics),
        )

    return None


def failure_details(diagnostics: list[str]) -> str:
    """Render diagnostics into the string format expected by IngestionResult."""
    return "\n".join(diagnostics)


def _identity_resolution_message(diagnostics: list[str], pending_confirmation_report: dict[str, object] | None) -> str:
    if pending_confirmation_report is not None:
        return "Binding Set confirmation incomplete"
    if _is_sims_target_id_capability_gap(diagnostics):
        return "SIMS target ID allocation capability incomplete"
    return "Identity resolution incomplete"


def _is_sims_target_id_capability_gap(diagnostics: list[str]) -> bool:
    """Detect the current SIMS limitation where allocation returns no target-facing integer ID."""
    return bool(diagnostics) and all(SIMS_TARGET_ID_CAPABILITY_NOTE in diagnostic for diagnostic in diagnostics)