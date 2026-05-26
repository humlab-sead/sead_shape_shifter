"""Binding Set confirmation reporting for the SEAD change request ingester."""

from ingesters.sead_change_request.contracts import ChangeRowState, IdentityResolutionResult, PendingConfirmationReport, SubmissionContext


def build_pending_confirmation_report(
    submission_context: SubmissionContext,
    identity_result: IdentityResolutionResult,
    *,
    binding_set_state: str | None,
) -> PendingConfirmationReport:
    """Build the pending-confirmation report for operator action."""
    blocked_entities: list[str] = []
    blocked_rows = 0

    for entity_name, resolved_table in identity_result.tables.items():
        entity_blocked_rows = int((resolved_table.row_states == ChangeRowState.BLOCKED_UNRESOLVED).sum())
        if not entity_blocked_rows:
            continue
        blocked_entities.append(entity_name)
        blocked_rows += entity_blocked_rows

    return PendingConfirmationReport(
        submission_name=submission_context.submission_name,
        project_name=submission_context.project_name,
        binding_set_uuid=submission_context.binding_set_uuid,
        binding_set_state=binding_set_state,
        blocked_entities=blocked_entities,
        blocked_rows=blocked_rows,
        outstanding_step="Confirm the Binding Set before change-package generation can continue",
        operator_action="Confirm the Binding Set in SIMS, then rerun the ingester with the same submission context",
        rerun_instruction=(
            f"Rerun submission '{submission_context.submission_name}' for project '{submission_context.project_name}' "
            "after the Binding Set is confirmed"
        ),
    )
