"""Row planning for the SEAD change request ingester."""

import math

import pandas as pd
from pandas import Series

from ingesters.sead_change_request.contracts import PlannedRowAction, PlannedTable, SourceTableBundle
from ingesters.sead_change_request.preparation import PlannedBundle
from src.target_model.models import EntitySpec


def _has_public_id_value(value: object) -> bool:
    """Return True when a public_id value should count as present."""
    if value is None or value is pd.NA or value is pd.NaT:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, int | float):
        return not math.isnan(value)
    return True


def plan_table(entity_name: str, frame: pd.DataFrame, entity_spec: EntitySpec) -> PlannedTable:
    """Plan row actions for one entity table in a deterministic way."""
    diagnostics: list[str] = []

    if entity_spec.role == "bridge":
        if not entity_spec.unique_sets:
            diagnostics.append(f"Bridge entity '{entity_name}' has no unique_sets metadata; Delivery 1 uniqueness checks will be blocked")
        planned_actions = pd.Series([PlannedRowAction.EVALUATE_BRIDGE] * len(frame.index), index=frame.index, name="_planned_action")
        return PlannedTable(entity_name=entity_name, frame=frame, planned_actions=planned_actions, diagnostics=diagnostics)

    public_id = entity_spec.public_id
    if not public_id:
        raise ValueError(f"Entity '{entity_name}' is missing target-model public_id metadata")
    if public_id not in frame.columns:
        raise ValueError(f"Entity '{entity_name}' is missing public_id column '{public_id}' in the source DataFrame")

    existing_mask = frame[public_id].map(_has_public_id_value)
    missing_action = PlannedRowAction.RECONCILE if entity_spec.role == "classifier" else PlannedRowAction.ALLOCATE
    planned_actions = pd.Series(missing_action, index=frame.index, name="_planned_action")
    planned_actions.loc[existing_mask] = PlannedRowAction.REFERENCE_EXISTING

    return PlannedTable(entity_name=entity_name, frame=frame, planned_actions=planned_actions, diagnostics=diagnostics)


def plan_bundle(bundle: SourceTableBundle, target_model_entities: dict[str, EntitySpec]) -> PlannedBundle:
    """Plan all source tables against the target model and collect diagnostics."""
    planned_tables: list[PlannedTable] = []
    errors: list[str] = []
    warnings: list[str] = list(bundle.warnings)
    infos: list[str] = []

    for entity_name, frame in bundle.tables.items():
        entity_spec = target_model_entities.get(entity_name)
        if entity_spec is None:
            errors.append(f"Source table '{entity_name}' is not present in the target model")
            continue

        try:
            planned_table = plan_table(entity_name, frame, entity_spec)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        planned_tables.append(planned_table)
        warnings.extend(planned_table.diagnostics)

        action_counts: Series = planned_table.planned_actions.value_counts(sort=False)
        action_summary = ", ".join(f"{int(count)} {action}" for action, count in action_counts.items())
        infos.append(f"Planned '{entity_name}': {action_summary}")

    return PlannedBundle(tables=planned_tables, errors=errors, warnings=warnings, infos=infos)
