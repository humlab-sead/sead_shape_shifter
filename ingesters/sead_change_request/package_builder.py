"""In-memory change-package assembly for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    IdentityResolutionResult,
    TargetProjectionResult,
)

INSERTABLE_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
}


def build_change_request_package(projection_result: TargetProjectionResult, identity_result: IdentityResolutionResult) -> ChangeRequestPackage:
    """Build the in-memory change package from projected tables."""
    tables: dict[str, ChangeRequestTable] = {}
    infos: list[str] = []

    for entity_name, projected_table in projection_result.tables.items():
        resolved_table = identity_result.tables.get(entity_name)
        if resolved_table is None:
            continue

        insert_mask: pd.Series = resolved_table.row_states.isin(INSERTABLE_ROW_STATES)
        if not bool(insert_mask.any()):
            continue

        package_frame: pd.DataFrame = projected_table.frame.loc[insert_mask].copy()
        package_row_states: pd.Series = resolved_table.row_states.loc[insert_mask].copy()
        tables[entity_name] = ChangeRequestTable(name=entity_name, frame=package_frame, row_states=package_row_states)
        infos.append(f"Prepared change-package table '{entity_name}' with {len(package_frame.index)} insert row(s)")

    infos.append(f"Prepared {len(tables)} change-package table(s)")
    return ChangeRequestPackage(tables=tables, warnings=list(projection_result.diagnostics), infos=infos)
