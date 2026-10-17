"""Root-row eligibility and pending-ID bookkeeping for deployment-time staging.

A staged aggregate child receives its target ID during deployment, so the
identity work that normally assigns a target ID at generation time cannot run.
This module decides, per submitted row, whether the row's aggregate chain ends at
a root that may own a new child:

- a tracked root must be inserted by the same submission with a SIMS-assigned ID;
- a reconciled root must have a resolved target ID and may already exist;
- an existing tracked root, an unresolved root, an invalid chain, and a new
  ``value_type`` root are rejected.

Ownership comes from ``resolve_aggregate_chain``; no entity allowlist or role
shortcut is used. The same pass records which rows are pending and which foreign
key values point at pending rows, so projection and collision checks can defer
those values instead of reporting them as missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral, Real

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRowState,
    IdentityAssignment,
    IdentityResolutionResult,
    PlannedRowAction,
    PlannedTable,
)
from src.target_model.effective_identity import AggregateChain, resolve_aggregate_chain
from src.target_model.models import EntitySpec, TargetModel

LOCAL_ID_COLUMN = "system_id"
VALUE_TYPE_ROOT_ENTITY = "value_type"
"""Root that this phase must not create. Children of an existing type stay eligible."""

INSERTED_ROOT_STATES: frozenset[ChangeRowState] = frozenset({ChangeRowState.NEWLY_ALLOCATED_ENTITY})
KNOWN_ROOT_STATES: frozenset[ChangeRowState] = frozenset(
    {ChangeRowState.EXISTING_ENTITY, ChangeRowState.RECONCILED_CLASSIFIER, ChangeRowState.NEWLY_ALLOCATED_ENTITY}
)


@dataclass(slots=True)
class PendingDeploymentMap:
    """Rows whose target IDs are pending, and foreign keys that point at them.

    ``pending_row_mask`` marks rows whose ID is allocated at deployment.
    ``deferred_public_id_mask`` also covers leaf rows whose own ID is left to the
    target default, such as a derived bridge with no incoming reference. Both are
    intentional, so projection does not report them as missing.
    """

    pending_row_mask: dict[str, pd.Series] = field(default_factory=dict)
    pending_fk_mask: dict[str, dict[str, pd.Series]] = field(default_factory=dict)
    deferred_public_id_mask: dict[str, pd.Series] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when no row depends on a deployment-time value."""
        masks = [*self.pending_row_mask.values(), *self.deferred_public_id_mask.values()]
        if any(bool(mask.any()) for mask in masks):
            return False
        return not any(bool(mask.any()) for masks in self.pending_fk_mask.values() for mask in masks.values())

    def is_pending_row(self, entity_name: str, row_index: object) -> bool:
        """Return ``True`` when one row's target ID is allocated at deployment."""
        return _mask_value(self.pending_row_mask, entity_name, row_index)

    def is_deferred_public_id(self, entity_name: str, row_index: object) -> bool:
        """Return ``True`` when one row's target ID is not available during generation."""
        if self.is_pending_row(entity_name, row_index):
            return True
        return _mask_value(self.deferred_public_id_mask, entity_name, row_index)

    def is_pending_foreign_key(self, entity_name: str, column_name: str, row_index: object) -> bool:
        """Return ``True`` when one row's foreign key value is pending deployment."""
        mask = self.pending_fk_mask.get(entity_name, {}).get(column_name)
        if mask is None or row_index not in mask.index:
            return False
        return bool(mask.loc[row_index])


def _mask_value(masks: dict[str, pd.Series], entity_name: str, row_index: object) -> bool:
    """Return one row's value from a per-entity boolean mask."""
    mask = masks.get(entity_name)
    if mask is None or row_index not in mask.index:
        return False
    return bool(mask.loc[row_index])


@dataclass(slots=True)
class StagedChildResolution:
    """Assignments for deferred child rows plus their diagnostics."""

    assignments: dict[str, dict[object, IdentityAssignment]] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


def resolve_staged_children(
    planned_tables: list[PlannedTable],
    target_model: TargetModel,
    assignments: dict[str, dict[object, IdentityAssignment]],
) -> StagedChildResolution:
    """Assign pending or blocked states to rows planned for deployment-time IDs.

    Only rows with ``PlannedRowAction.DEFER_TO_DEPLOYMENT`` are decided here; all
    other rows keep the assignments produced by orchestration.
    """
    result = StagedChildResolution()
    planned_lookup: dict[str, PlannedTable] = {planned.entity_name: planned for planned in planned_tables}

    for planned_table in planned_tables:
        defer_mask: pd.Series = planned_table.planned_actions == PlannedRowAction.DEFER_TO_DEPLOYMENT
        if not bool(defer_mask.any()):
            continue

        chain = resolve_aggregate_chain(target_model, planned_table.entity_name)
        entity_assignments: dict[object, IdentityAssignment] = result.assignments.setdefault(planned_table.entity_name, {})

        for row_index in planned_table.frame.index[defer_mask]:
            assignment = _resolve_staged_row(
                planned_table,
                row_index,
                chain,
                target_model,
                planned_lookup,
                assignments,
            )
            entity_assignments[row_index] = assignment
            if assignment.note:
                result.diagnostics.append(f"Entity '{planned_table.entity_name}' row '{row_index}': {assignment.note}")

    return result


def collect_pending_deployment(
    identity_result: IdentityResolutionResult,
    target_model: TargetModel,
) -> PendingDeploymentMap:
    """Return the pending rows and the foreign keys that reference them.

    A foreign key row is pending when its local value matches a pending row of the
    referenced entity, so that projection and collision checks can defer the value
    instead of reporting it as missing.
    """
    pending_keys: dict[str, set[int]] = {}
    pending_row_mask: dict[str, pd.Series] = {}
    deferred_public_id_mask: dict[str, pd.Series] = {}

    for entity_name, resolved_table in identity_result.tables.items():
        mask: pd.Series = resolved_table.row_states == ChangeRowState.PENDING_DEPLOYMENT_ID
        pending_row_mask[entity_name] = mask
        default_generated = (resolved_table.row_states == ChangeRowState.DERIVED_BRIDGE_ROW) & resolved_table.resolved_target_ids.isna()
        deferred_public_id_mask[entity_name] = mask | default_generated.fillna(False).astype(bool)
        if not bool(mask.any()):
            continue
        pending_keys[entity_name] = _local_keys(resolved_table.frame.loc[mask])

    pending_fk_mask: dict[str, dict[str, pd.Series]] = {}
    for entity_name, resolved_table in identity_result.tables.items():
        entity_spec = target_model.entities.get(entity_name)
        if entity_spec is None:
            continue
        column_masks: dict[str, pd.Series] = {}
        for foreign_key in entity_spec.foreign_keys:
            remote_keys = pending_keys.get(foreign_key.entity)
            remote_spec = target_model.entities.get(foreign_key.entity)
            if not remote_keys or remote_spec is None or not remote_spec.public_id:
                continue
            if remote_spec.public_id not in resolved_table.frame.columns:
                continue
            column_values = resolved_table.frame[remote_spec.public_id]
            column_masks[remote_spec.public_id] = column_values.map(lambda value: _as_int(value) in remote_keys).fillna(False).astype(bool)
        if column_masks:
            pending_fk_mask[entity_name] = column_masks

    return PendingDeploymentMap(
        pending_row_mask=pending_row_mask,
        pending_fk_mask=pending_fk_mask,
        deferred_public_id_mask=deferred_public_id_mask,
    )


def _resolve_staged_row(
    planned_table: PlannedTable,
    row_index: object,
    chain: AggregateChain,
    target_model: TargetModel,
    planned_lookup: dict[str, PlannedTable],
    assignments: dict[str, dict[object, IdentityAssignment]],
) -> IdentityAssignment:
    """Return the pending or blocked assignment for one deferred child row."""
    entity_name = planned_table.entity_name

    if not chain.is_valid:
        codes = ", ".join(issue.code for issue in chain.issues)
        return _blocked(f"Aggregate chain for '{entity_name}' is invalid: {codes}")

    failure_note = _walk_parent_chain(planned_table, row_index, chain, target_model, planned_lookup, assignments)
    if failure_note is not None:
        return _blocked(failure_note)

    return IdentityAssignment(
        state=ChangeRowState.PENDING_DEPLOYMENT_ID,
        target_id=None,
        note=(f"'{entity_name}' target ID is allocated at deployment from '{chain.root_entity}' aggregate ownership"),
    )


def _walk_parent_chain(
    planned_table: PlannedTable,
    row_index: object,
    chain: AggregateChain,
    target_model: TargetModel,
    planned_lookup: dict[str, PlannedTable],
    assignments: dict[str, dict[object, IdentityAssignment]],
) -> str | None:
    """Walk the local parent references to the root and return a failure note.

    Returns ``None`` when the row may receive a deployment-time ID.
    """
    current_table = planned_table
    current_row = row_index

    for parent_name in chain.parent_chain:
        parent_spec: EntitySpec | None = target_model.entities.get(parent_name)
        if parent_spec is None or not parent_spec.public_id:
            return f"Aggregate parent '{parent_name}' is missing public_id metadata"
        if parent_spec.public_id not in current_table.frame.columns:
            return (
                f"Entity '{current_table.entity_name}' has no local foreign key column '{parent_spec.public_id}' "
                f"for aggregate parent '{parent_name}'"
            )

        local_value = current_table.frame.at[current_row, parent_spec.public_id]
        if pd.isna(local_value):
            return f"Entity '{current_table.entity_name}' row '{current_row}' has no local reference to aggregate parent '{parent_name}'"

        parent_table = planned_lookup.get(parent_name)
        if parent_table is None:
            return f"Aggregate parent '{parent_name}' is not part of the submitted tables"

        parent_row = _find_row_by_local_key(parent_table, local_value)
        if parent_row is None:
            return (
                f"Entity '{current_table.entity_name}' row '{current_row}' references {LOCAL_ID_COLUMN} "
                f"'{local_value}' in '{parent_name}' which is not part of the submission"
            )

        parent_state, _ = _row_state_and_target_id(parent_table, parent_row, parent_spec.public_id, assignments)
        if parent_state == ChangeRowState.BLOCKED_UNRESOLVED:
            return f"Aggregate parent '{parent_name}' row '{parent_row}' is blocked"

        current_table = parent_table
        current_row = parent_row

    root_public_id = target_model.entities[chain.root_entity].public_id if chain.root_entity else None
    return _validate_root(current_table, current_row, chain, root_public_id, assignments)


def _validate_root(
    root_table: PlannedTable,
    root_row: object,
    chain: AggregateChain,
    root_public_id: str | None,
    assignments: dict[str, dict[object, IdentityAssignment]],
) -> str | None:
    """Return a failure note when the chain root cannot own a new child."""
    root_state, root_target_id = _row_state_and_target_id(root_table, root_row, root_public_id, assignments)
    root_name = chain.root_entity or root_table.entity_name

    if root_state == ChangeRowState.BLOCKED_UNRESOLVED:
        return f"Aggregate root '{root_name}' row '{root_row}' is blocked"

    if chain.root_identity_tracking == "tracked":
        if root_state not in INSERTED_ROOT_STATES:
            return (
                f"Aggregate root '{root_name}' row '{root_row}' is an existing tracked root; "
                "a new child requires a tracked root inserted by this submission"
            )
        if root_target_id is None:
            return f"Aggregate root '{root_name}' row '{root_row}' has no SIMS-assigned target ID"
        return None

    if chain.root_identity_tracking == "reconciled":
        if root_state not in KNOWN_ROOT_STATES or root_target_id is None:
            return f"Aggregate root '{root_name}' row '{root_row}' has no resolved target ID"
        if root_name == VALUE_TYPE_ROOT_ENTITY and root_state not in {ChangeRowState.EXISTING_ENTITY, ChangeRowState.RECONCILED_CLASSIFIER}:
            return "Creating a new 'value_type' root is outside the deployment-time staging scope"
        return None

    return (
        f"Aggregate root '{root_name}' resolves to identity_tracking '{chain.root_identity_tracking}'; "
        "only tracked or reconciled roots can own a new child"
    )


def _row_state_and_target_id(
    planned_table: PlannedTable,
    row_index: object,
    public_id: str | None,
    assignments: dict[str, dict[object, IdentityAssignment]],
) -> tuple[ChangeRowState | None, int | None]:
    """Return the resolved state and target ID for one submitted row."""
    planned_action = planned_table.planned_actions.loc[row_index]
    if planned_action == PlannedRowAction.REFERENCE_EXISTING:
        return ChangeRowState.EXISTING_ENTITY, _known_public_id(planned_table, row_index, public_id)
    if planned_action in {PlannedRowAction.UPDATE_EXISTING_CANDIDATE, PlannedRowAction.BLOCK_EXISTING_UPDATE}:
        return ChangeRowState.BLOCKED_UNRESOLVED, None

    assignment = assignments.get(planned_table.entity_name, {}).get(row_index)
    if assignment is None:
        return None, None
    return assignment.state, assignment.target_id


def _known_public_id(planned_table: PlannedTable, row_index: object, public_id: str | None) -> int | None:
    """Return the public ID supplied by a reference-existing row when it is numeric."""
    if public_id is None or public_id not in planned_table.frame.columns:
        return None
    return _as_int(planned_table.frame.at[row_index, public_id])


def _find_row_by_local_key(planned_table: PlannedTable, local_value: object) -> object | None:
    """Return the row whose local system_id matches ``local_value``."""
    if LOCAL_ID_COLUMN in planned_table.frame.columns:
        matches = planned_table.frame.index[planned_table.frame[LOCAL_ID_COLUMN] == local_value]
    else:
        matches = planned_table.frame.index[planned_table.frame.index == local_value]
    if len(matches) != 1:
        return None
    return matches[0]


def _local_keys(frame: pd.DataFrame) -> set[int]:
    """Return the local keys of a frame, using system_id or the index labels."""
    values = frame[LOCAL_ID_COLUMN] if LOCAL_ID_COLUMN in frame.columns else pd.Series(frame.index, index=frame.index)
    keys: set[int] = set()
    for value in values:
        int_value = _as_int(value)
        if int_value is not None:
            keys.add(int_value)
    return keys


def _as_int(value: object) -> int | None:
    """Return ``value`` as an int when it is an integral number, else ``None``.

    Pandas returns NumPy integers, which are ``numbers.Integral`` but are not
    ``int`` instances, so the check uses the numeric ABCs.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real) and not pd.isna(value) and float(value).is_integer():
        return int(value)
    return None


def _blocked(note: str) -> IdentityAssignment:
    """Return a blocked assignment carrying the failure note."""
    return IdentityAssignment(state=ChangeRowState.BLOCKED_UNRESOLVED, note=note)
