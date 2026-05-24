"""Identity work partitioning for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import IdentityWorkPlan, PlannedRowAction, PlannedTable


def build_identity_work_plan(planned_tables: list[PlannedTable]) -> IdentityWorkPlan:
    """Partition planned rows into the Delivery 1 identity work queues."""
    work_plan = IdentityWorkPlan()

    for planned_table in planned_tables:
        for action, target in (
            (PlannedRowAction.REFERENCE_EXISTING, work_plan.existing_rows),
            (PlannedRowAction.ALLOCATE, work_plan.allocation_rows),
            (PlannedRowAction.RECONCILE, work_plan.reconciliation_rows),
            (PlannedRowAction.EVALUATE_BRIDGE, work_plan.bridge_rows),
        ):
            action_rows = _select_action_rows(planned_table, action)
            if action_rows is not None:
                target[planned_table.entity_name] = action_rows

    return work_plan


def _select_action_rows(planned_table: PlannedTable, action: PlannedRowAction) -> pd.DataFrame | None:
    """Return the subset of rows assigned to a specific planned action."""
    action_mask = planned_table.planned_actions == action
    if not bool(action_mask.any()):
        return None
    return planned_table.frame.loc[action_mask].copy()
