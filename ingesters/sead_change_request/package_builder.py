"""In-memory change-package assembly for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    IdentityResolutionResult,
    PlannedRowAction,
    PlannedTable,
    ResolvedIdentityTable,
    TargetProjectionResult,
)

INSERTABLE_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
}


def build_change_request_package(
    projection_result: TargetProjectionResult,
    identity_result: IdentityResolutionResult,
    planned_tables: list[PlannedTable] | None = None,
) -> ChangeRequestPackage:
    """Build the in-memory change package from projected tables."""
    tables: dict[str, ChangeRequestTable] = {}
    infos: list[str] = []
    planned_table_lookup: dict[str, PlannedTable] = {planned_table.entity_name: planned_table for planned_table in planned_tables or []}

    for entity_name, projected_table in projection_result.tables.items():
        resolved_table = identity_result.tables.get(entity_name)
        planned_table = planned_table_lookup.get(entity_name)
        if resolved_table is None:
            continue

        insert_mask: pd.Series = resolved_table.row_states.isin(INSERTABLE_ROW_STATES)
        update_mask: pd.Series = _build_update_mask(planned_table, resolved_table)
        package_mask: pd.Series = insert_mask | update_mask
        if not bool(package_mask.any()):
            continue

        package_frame: pd.DataFrame = projected_table.frame.loc[package_mask].copy()
        package_row_states: pd.Series = resolved_table.row_states.loc[package_mask].copy()
        package_planned_actions: pd.Series | None = None
        if planned_table is not None:
            package_planned_actions = planned_table.planned_actions.loc[package_mask].copy()

        tables[entity_name] = ChangeRequestTable(
            name=entity_name,
            frame=package_frame,
            row_states=package_row_states,
            planned_actions=package_planned_actions,
        )

        insert_row_count = int(insert_mask.loc[package_mask].sum())
        update_row_count = int(update_mask.loc[package_mask].sum())
        infos.append(
            f"Prepared change-package table '{entity_name}' with {insert_row_count} insert row(s) and {update_row_count} update row(s)"
        )

    infos.append(f"Prepared {len(tables)} change-package table(s)")
    return ChangeRequestPackage(tables=tables, warnings=list(projection_result.diagnostics), infos=infos)


def _build_update_mask(planned_table: PlannedTable | None, resolved_table: ResolvedIdentityTable) -> pd.Series:
    """Return rows that should be rendered as existing-row updates."""
    if planned_table is None:
        return pd.Series(False, index=resolved_table.frame.index)

    return planned_table.planned_actions == PlannedRowAction.UPDATE_EXISTING_CANDIDATE
