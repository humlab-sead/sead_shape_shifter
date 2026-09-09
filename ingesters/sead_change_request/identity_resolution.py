"""Pure identity resolution for the SEAD change request ingester."""

from collections.abc import Hashable
from typing import cast

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRowState,
    IdentityAssignment,
    IdentityResolutionResult,
    PlannedRowAction,
    PlannedTable,
    ResolvedIdentityTable,
)
from src.target_model.models import EntitySpec, TargetModel


def resolve_planned_tables(
    planned_tables: list[PlannedTable],
    target_model: TargetModel,
    assignments: dict[str, dict[object, IdentityAssignment]] | None = None,
) -> IdentityResolutionResult:
    """Resolve planned rows into row states and target IDs."""
    assignments = assignments or {}
    resolved_tables: dict[str, ResolvedIdentityTable] = {}
    diagnostics: list[str] = []

    for planned_table in planned_tables:
        entity_spec: EntitySpec = target_model.entities[planned_table.entity_name]
        resolved_table: ResolvedIdentityTable = _resolve_table(
            planned_table, entity_spec.public_id, assignments.get(planned_table.entity_name, {})
        )
        resolved_tables[planned_table.entity_name] = resolved_table
        diagnostics.extend(resolved_table.diagnostics)

    return IdentityResolutionResult(tables=resolved_tables, diagnostics=diagnostics)


def _resolve_table(
    planned_table: PlannedTable,
    public_id_column: str | None,
    table_assignments: dict[object, IdentityAssignment],
) -> ResolvedIdentityTable:
    """Resolve a single planned table into row states and target IDs."""
    row_states: pd.Series = pd.Series(index=planned_table.frame.index, dtype="object", name="_row_state")
    resolved_target_ids: pd.Series = pd.Series(index=planned_table.frame.index, dtype="Int64", name="_target_id")
    diagnostics: list[str] = []

    for row_index, planned_action in planned_table.planned_actions.items():
        row_key: Hashable = cast(Hashable, row_index)

        if planned_action in {PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE}:
            row_states.at[row_key] = ChangeRowState.EXISTING_ENTITY
            if public_id_column is None:
                diagnostics.append(f"Entity '{planned_table.entity_name}' cannot resolve existing rows without public_id metadata")
                row_states.at[row_key] = ChangeRowState.BLOCKED_UNRESOLVED
                continue
            resolved_target_ids.at[row_key] = planned_table.frame.at[row_key, public_id_column]
            continue

        assignment: IdentityAssignment | None = table_assignments.get(row_index)
        if assignment is None:
            row_states.at[row_key] = ChangeRowState.BLOCKED_UNRESOLVED
            diagnostics.append(
                f"Entity '{planned_table.entity_name}' row '{row_index}' is missing an identity "
                f"assignment for planned action '{planned_action}'"
            )
            continue

        row_states.at[row_key] = assignment.state
        if assignment.target_id is not None:
            resolved_target_ids.at[row_key] = assignment.target_id
        if assignment.note:
            diagnostics.append(f"Entity '{planned_table.entity_name}' row '{row_index}': {assignment.note}")

    return ResolvedIdentityTable(
        entity_name=planned_table.entity_name,
        frame=planned_table.frame.copy(),
        row_states=row_states,
        resolved_target_ids=resolved_target_ids,
        diagnostics=diagnostics,
    )
