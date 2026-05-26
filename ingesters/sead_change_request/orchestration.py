"""Thin client orchestration for SEAD change request identity resolution."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from ingesters.sead_change_request.contracts import ChangeRowState, IdentityAssignment, PlannedRowAction, PlannedTable, SubmissionContext

SIMS_TARGET_ID_CAPABILITY_NOTE = (
    "SIMS allocation could not complete target projection because no target-facing integer ID was returned"
)


@dataclass(slots=True)
class IdentityOrchestrationResult:
    """Assignments and Binding Set state produced by client orchestration."""

    assignments: dict[str, dict[object, IdentityAssignment]] = field(default_factory=dict)
    binding_set_uuid: str | None = None
    binding_set_state: str | None = None


class SimsClientPort(Protocol):
    """Thin SIMS client seam used by the ingester orchestration layer."""

    async def allocate_entity(self, entity_name: str, row: dict[str, Any], submission_context: SubmissionContext) -> dict[str, Any]: ...

    async def derive_bridge_row(self, entity_name: str, row: dict[str, Any], submission_context: SubmissionContext) -> dict[str, Any]: ...

    async def get_binding_set_state(self, binding_set_uuid: str) -> str: ...

    async def confirm_binding_set(self, binding_set_uuid: str) -> str: ...

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None: ...


class ReconciliationClientPort(Protocol):
    """Thin reconciliation client seam used by the ingester orchestration layer."""

    async def reconcile_entity(self, entity_name: str, row: dict[str, Any]) -> int | None: ...


async def orchestrate_identity_assignments(
    planned_tables: list[PlannedTable],
    submission_context: SubmissionContext,
    *,
    sims_client: SimsClientPort | None = None,
    reconciliation_client: ReconciliationClientPort | None = None,
    fallback_assignments: dict[str, dict[object, IdentityAssignment]] | None = None,
) -> IdentityOrchestrationResult:
    """Build identity assignments using injected SIMS and reconciliation clients."""
    assignments: dict[str, dict[object, IdentityAssignment]] = {
        entity_name: dict(entity_assignments) for entity_name, entity_assignments in (fallback_assignments or {}).items()
    }
    sims_assigned_rows: list[tuple[str, object]] = []
    binding_set_uuid: str | None = submission_context.binding_set_uuid
    binding_set_state: str | None = None

    for planned_table in planned_tables:
        entity_assignments: dict[object, IdentityAssignment] = assignments.setdefault(planned_table.entity_name, {})
        for row_index, planned_action in planned_table.planned_actions.items():
            if planned_action == PlannedRowAction.REFERENCE_EXISTING:
                continue
            if row_index in entity_assignments:
                continue

            row_payload = {str(column_name): value for column_name, value in planned_table.frame.loc[[row_index]].iloc[0].to_dict().items()}

            if planned_action == PlannedRowAction.RECONCILE and reconciliation_client is not None:
                reconciled_target_id = await reconciliation_client.reconcile_entity(planned_table.entity_name, row_payload)
                if reconciled_target_id is not None:
                    entity_assignments[row_index] = IdentityAssignment(
                        state=ChangeRowState.RECONCILED_CLASSIFIER,
                        target_id=reconciled_target_id,
                    )
                    continue

            if planned_action in {PlannedRowAction.ALLOCATE, PlannedRowAction.RECONCILE} and sims_client is not None:
                allocation = await sims_client.allocate_entity(planned_table.entity_name, row_payload, submission_context)
                target_id = allocation.get("target_id")
                note = allocation.get("note")
                if target_id is None:
                    blocking_note = SIMS_TARGET_ID_CAPABILITY_NOTE
                    if note:
                        blocking_note = f"{blocking_note}: {note}"
                    entity_assignments[row_index] = IdentityAssignment(
                        state=ChangeRowState.BLOCKED_UNRESOLVED,
                        note=blocking_note,
                    )
                else:
                    entity_assignments[row_index] = IdentityAssignment(
                        state=ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                        target_id=target_id,
                        note=note,
                    )
                binding_set_uuid = allocation.get("binding_set_uuid") or binding_set_uuid
                binding_set_state = allocation.get("binding_set_state") or binding_set_state
                if target_id is not None:
                    sims_assigned_rows.append((planned_table.entity_name, row_index))
                continue

            if planned_action == PlannedRowAction.EVALUATE_BRIDGE and sims_client is not None:
                bridge = await sims_client.derive_bridge_row(planned_table.entity_name, row_payload, submission_context)
                bridge_state = bridge.get("state")
                note = bridge.get("note")
                if bridge_state == ChangeRowState.DERIVED_BRIDGE_ROW.value:
                    entity_assignments[row_index] = IdentityAssignment(
                        state=ChangeRowState.DERIVED_BRIDGE_ROW,
                        note=note,
                    )
                else:
                    blocking_note = f"Bridge derivation for '{planned_table.entity_name}' could not determine whether the row is insertable"
                    if note:
                        blocking_note = f"{blocking_note}: {note}"
                    entity_assignments[row_index] = IdentityAssignment(
                        state=ChangeRowState.BLOCKED_UNRESOLVED,
                        note=blocking_note,
                    )
                binding_set_uuid = bridge.get("binding_set_uuid") or binding_set_uuid
                binding_set_state = bridge.get("binding_set_state") or binding_set_state
                if bridge.get("target_id") is not None:
                    sims_assigned_rows.append((planned_table.entity_name, row_index))

    if sims_client is not None and binding_set_uuid:
        binding_set_state = binding_set_state or await sims_client.get_binding_set_state(binding_set_uuid)
        if binding_set_state != "confirmed":
            binding_set_state = await sims_client.confirm_binding_set(binding_set_uuid)

        if binding_set_state != "confirmed":
            for entity_name, row_index in sims_assigned_rows:
                assignments.setdefault(entity_name, {})[row_index] = IdentityAssignment(
                    state=ChangeRowState.BLOCKED_UNRESOLVED,
                    note=(f"Binding Set '{binding_set_uuid}' is in state '{binding_set_state}' and must be confirmed before generation"),
                )

    return IdentityOrchestrationResult(
        assignments=assignments,
        binding_set_uuid=binding_set_uuid,
        binding_set_state=binding_set_state,
    )
