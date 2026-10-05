"""Row planning for the SEAD change request ingester."""

from typing import Any

import pandas as pd
from pandas import Series

from ingesters.sead_change_request.contracts import PlannedRowAction, PlannedTable, SourceTableBundle
from ingesters.sead_change_request.preparation import PlannedBundle
from src.target_model.effective_identity import EffectiveIdentity, resolve_effective_identity
from src.target_model.models import EntitySpec


def _has_public_id_value(value: Any) -> bool:
    """Return True when a public_id value should count as present."""
    if isinstance(value, str):
        return bool(value.strip())
    return not bool(pd.isna(value))


def _values_equal_for_existing_row_planning(left: Any, right: Any) -> bool:
    """Compare mutable-field values while routing existing-row updates."""
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return left == right


def _missing_action_for(effective: EffectiveIdentity) -> PlannedRowAction:
    """Return the planned action for rows whose public ID is unresolved."""
    if effective.identity_tracking == "tracked":
        return PlannedRowAction.ALLOCATE
    if effective.identity_tracking == "reconciled":
        return PlannedRowAction.RECONCILE
    if effective.identity_tracking == "child":
        return PlannedRowAction.INHERIT_AGGREGATE
    raise ValueError(f"Effective identity_tracking '{effective.identity_tracking}' cannot plan a missing-public-ID action")


def plan_table(
    entity_name: str,
    frame: pd.DataFrame,
    entity_spec: EntitySpec,
    *,
    mutable_fields: list[str] | None = None,
    existing_row_update_entities: set[str] | None = None,
) -> PlannedTable:
    """Plan row actions for one entity table in a deterministic way."""
    diagnostics: list[str] = []
    effective = resolve_effective_identity(entity_spec)

    if entity_spec.public_id_generation == "database_sequence":
        if not entity_spec.target_table:
            raise ValueError(f"Entity '{entity_name}' uses database_sequence public ID generation but has no target_table")
        if entity_spec.identity_tracking is None or entity_spec.identity_tracking == "tracked":
            raise ValueError(
                f"Entity '{entity_name}' uses database_sequence public ID generation but must explicitly declare "
                "a non-tracked identity_tracking value; tracked identities must be allocated by SIMS"
            )
        missing_action = PlannedRowAction.RESERVE_DATABASE_ID
    elif effective.identity_tracking == "derived":
        if not entity_spec.unique_sets:
            diagnostics.append(f"Bridge entity '{entity_name}' has no unique_sets metadata; Delivery 1 uniqueness checks will be blocked")
        planned_actions = pd.Series([PlannedRowAction.EVALUATE_BRIDGE] * len(frame.index), index=frame.index, name="_planned_action")
        return PlannedTable(entity_name=entity_name, frame=frame, planned_actions=planned_actions, diagnostics=diagnostics)
    else:
        missing_action = _missing_action_for(effective)

    public_id = entity_spec.public_id
    if not public_id:
        raise ValueError(f"Entity '{entity_name}' is missing target-model public_id metadata")
    if public_id not in frame.columns:
        raise ValueError(f"Entity '{entity_name}' is missing public_id column '{public_id}' in the source DataFrame")

    existing_mask = frame[public_id].map(_has_public_id_value)
    planned_actions = pd.Series(missing_action, index=frame.index, name="_planned_action")
    planned_actions.loc[existing_mask] = PlannedRowAction.REFERENCE_EXISTING

    if mutable_fields is not None and bool(existing_mask.any()):
        missing_requirements = _missing_mutable_field_requirements(frame, mutable_fields)
        if missing_requirements:
            planned_actions.loc[existing_mask] = PlannedRowAction.BLOCK_EXISTING_UPDATE
            diagnostics.append(
                "Entity "
                f"'{entity_name}' blocked existing-row update planning because mutable-field requirements are missing: "
                + ", ".join(missing_requirements)
            )
            return PlannedTable(
                entity_name=entity_name,
                frame=frame,
                planned_actions=planned_actions,
                mutable_fields=mutable_fields,
                diagnostics=diagnostics,
            )

        baseline_pairs = [(field_name, f"{field_name}__existing") for field_name in mutable_fields if field_name]
        update_candidate_rows: list[object] = []
        for row_index in frame.index[existing_mask]:
            is_no_op = True
            for current_column, baseline_column in baseline_pairs:
                if not _values_equal_for_existing_row_planning(
                    frame.at[row_index, current_column],
                    frame.at[row_index, baseline_column],
                ):
                    is_no_op = False
                    break

            if not is_no_op:
                update_candidate_rows.append(row_index)

        if existing_row_update_entities is not None and entity_name not in existing_row_update_entities:
            if update_candidate_rows:
                for row_index in update_candidate_rows:
                    planned_actions.at[row_index] = PlannedRowAction.BLOCK_EXISTING_UPDATE
                diagnostics.append(
                    f"Entity '{entity_name}' is outside the first existing-row update slice; existing-row updates are blocked"
                )
        else:
            for row_index in update_candidate_rows:
                planned_actions.at[row_index] = PlannedRowAction.UPDATE_EXISTING_CANDIDATE

    return PlannedTable(
        entity_name=entity_name,
        frame=frame,
        planned_actions=planned_actions,
        mutable_fields=mutable_fields,
        diagnostics=diagnostics,
    )


def plan_bundle(
    bundle: SourceTableBundle,
    target_model_entities: dict[str, EntitySpec],
    *,
    mutable_fields_by_entity: dict[str, list[str]] | None = None,
    existing_row_update_entities: set[str] | None = None,
) -> PlannedBundle:
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
            planned_table = plan_table(
                entity_name,
                frame,
                entity_spec,
                mutable_fields=(mutable_fields_by_entity or {}).get(entity_name),
                existing_row_update_entities=existing_row_update_entities,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue

        planned_tables.append(planned_table)
        warnings.extend(planned_table.diagnostics)

        action_counts: Series = planned_table.planned_actions.value_counts(sort=False)
        action_summary = ", ".join(f"{int(count)} {action}" for action, count in action_counts.items())
        infos.append(f"Planned '{entity_name}': {action_summary}")

    return PlannedBundle(tables=planned_tables, errors=errors, warnings=warnings, infos=infos)


def _missing_mutable_field_requirements(frame: pd.DataFrame, mutable_fields: list[str]) -> list[str]:
    """Return missing mutable-field requirements needed for existing-row update routing."""
    missing: list[str] = []
    for field_name in mutable_fields:
        current_column = field_name.strip() if isinstance(field_name, str) else ""
        if not current_column:
            continue
        baseline_column = f"{current_column}__existing"
        if current_column not in frame.columns:
            missing.append(current_column)
            continue
        if baseline_column not in frame.columns:
            missing.append(baseline_column)
    return missing
