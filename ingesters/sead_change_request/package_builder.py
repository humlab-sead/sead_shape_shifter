"""In-memory change-package assembly for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    DirectForeignKey,
    IdentityResolutionResult,
    KnownIdMapping,
    PlannedRowAction,
    PlannedTable,
    ResolvedIdentityTable,
    TargetProjectionResult,
)
from src.target_model.models import TargetModel

INSERTABLE_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
}

STAGING_INSERT_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
    ChangeRowState.PENDING_DEPLOYMENT_ID,
}

REFERENCE_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.EXISTING_ENTITY,
    ChangeRowState.RECONCILED_CLASSIFIER,
}


def build_change_request_package(
    projection_result: TargetProjectionResult,
    identity_result: IdentityResolutionResult,
    planned_tables: list[PlannedTable] | None = None,
    foreign_key_value_sources: dict[str, dict[str, str]] | None = None,
    target_model: TargetModel | None = None,
) -> ChangeRequestPackage:
    """Build the in-memory change package from projected tables."""
    if target_model is None and any(
        value_source == "public_id"
        for entity_sources in (foreign_key_value_sources or {}).values()
        for value_source in entity_sources.values()
    ):
        raise ValueError("Target model is required to identify direct foreign-key columns in a change package")

    tables: dict[str, ChangeRequestTable] = {}
    infos: list[str] = []
    planned_table_lookup: dict[str, PlannedTable] = {planned_table.entity_name: planned_table for planned_table in planned_tables or []}

    for entity_name, projected_table in projection_result.tables.items():
        resolved_table: ResolvedIdentityTable | None = identity_result.tables.get(entity_name)
        planned_table: PlannedTable | None = planned_table_lookup.get(entity_name)
        if planned_table is None:
            infos.append(f"Skipping change-package table '{entity_name}' because no planned table was found")
            continue
        if resolved_table is None:
            infos.append(f"Skipping change-package table '{entity_name}' because no resolved table was found")
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
            mutable_fields=planned_table.mutable_fields,
        )

        insert_row_count = int(insert_mask.loc[package_mask].sum())
        update_row_count = int(update_mask.loc[package_mask].sum())
        infos.append(
            f"Prepared change-package table '{entity_name}' with {insert_row_count} insert row(s) and {update_row_count} update row(s)"
        )

    infos.append(f"Prepared {len(tables)} change-package table(s)")
    return ChangeRequestPackage(
        tables=tables,
        warnings=list(projection_result.diagnostics),
        infos=infos,
        direct_foreign_keys=_select_direct_foreign_keys(tables, foreign_key_value_sources, target_model),
    )


def _build_update_mask(planned_table: PlannedTable | None, resolved_table: ResolvedIdentityTable) -> pd.Series:
    """Return rows that should be rendered as existing-row updates."""
    if planned_table is None:
        return pd.Series(False, index=resolved_table.frame.index)

    return planned_table.planned_actions == PlannedRowAction.UPDATE_EXISTING_CANDIDATE


def build_staging_package(
    identity_result: IdentityResolutionResult,
    planned_tables: list[PlannedTable],
    target_model: TargetModel,
    target_schema: str,
    foreign_key_value_sources: dict[str, dict[str, str]] | None = None,
) -> ChangeRequestPackage:
    """Build the inline-staging package from pre-projection resolved rows.

    Staging rows keep their local ``system_id`` and local foreign-key values, so
    deployment can still see the local relationships after target IDs are
    allocated. Parent rows that must not be written are carried separately as
    ``(entity, system_id, target ID)`` mappings.

    Only rows referenced by a staged foreign key are mapped, so a large
    reference table does not inflate the artifact.
    """
    infos: list[str] = []
    tables: dict[str, ChangeRequestTable] = {}

    for planned_table in planned_tables:
        resolved_table = identity_result.tables.get(planned_table.entity_name)
        if resolved_table is None:
            continue
        insert_mask: pd.Series = resolved_table.row_states.isin(STAGING_INSERT_ROW_STATES)
        if not bool(insert_mask.any()):
            continue

        staged_frame = resolved_table.frame.loc[insert_mask].copy()
        entity_spec = target_model.entities.get(planned_table.entity_name)
        if entity_spec is not None and entity_spec.public_id:
            staged_frame[entity_spec.public_id] = resolved_table.resolved_target_ids.loc[insert_mask].astype("Int64")

        tables[planned_table.entity_name] = ChangeRequestTable(
            name=planned_table.entity_name,
            frame=staged_frame,
            row_states=resolved_table.row_states.loc[insert_mask].copy(),
            planned_actions=planned_table.planned_actions.loc[insert_mask].copy(),
        )
        infos.append(f"Staged {int(insert_mask.sum())} row(s) for '{planned_table.entity_name}'")

    direct_foreign_keys = _select_direct_foreign_keys(tables, foreign_key_value_sources, target_model)
    known_id_mappings = _collect_known_id_mappings(tables, identity_result, target_model, direct_foreign_keys)
    infos.append(f"Staged {len(known_id_mappings)} known target-ID mapping(s)")
    return ChangeRequestPackage(
        tables=tables,
        infos=infos,
        known_id_mappings=known_id_mappings,
        direct_foreign_keys=direct_foreign_keys,
        target_schema=target_schema,
    )


def _collect_known_id_mappings(
    staged_tables: dict[str, ChangeRequestTable],
    identity_result: IdentityResolutionResult,
    target_model: TargetModel,
    direct_foreign_keys: list[DirectForeignKey] | None = None,
) -> list[KnownIdMapping]:
    """Return mappings for every local reference used by a staged foreign key."""
    needed: dict[str, set[object]] = {}
    direct_pairs = {(item.source_entity, item.target_entity) for item in direct_foreign_keys or []}
    for entity_name, staged_table in staged_tables.items():
        entity_spec = target_model.entities.get(entity_name)
        if entity_spec is None:
            continue
        for foreign_key in entity_spec.foreign_keys:
            if (entity_name, foreign_key.entity) in direct_pairs:
                continue
            remote_spec = target_model.entities.get(foreign_key.entity)
            if remote_spec is None or not remote_spec.public_id:
                continue
            if remote_spec.public_id not in staged_table.frame.columns:
                continue
            needed.setdefault(foreign_key.entity, set()).update(staged_table.frame[remote_spec.public_id].dropna())

    mappings: list[KnownIdMapping] = []
    for entity_name in sorted(needed):
        resolved_table = identity_result.tables.get(entity_name)
        if resolved_table is None:
            continue
        local_keys = _local_key_series(resolved_table.frame)
        frame = resolved_table.frame
        for row_index in frame.index:
            local_value = local_keys.loc[row_index]
            if pd.isna(local_value) or local_value not in needed[entity_name]:
                continue
            if resolved_table.row_states.loc[row_index] not in REFERENCE_ROW_STATES | STAGING_INSERT_ROW_STATES:
                continue
            target_id = resolved_table.resolved_target_ids.loc[row_index]
            if pd.isna(target_id):
                continue
            mappings.append(KnownIdMapping(entity_name=entity_name, system_id=int(local_value), target_id=int(target_id)))

    return mappings


def _select_direct_foreign_keys(
    package_tables: dict[str, ChangeRequestTable],
    foreign_key_value_sources: dict[str, dict[str, str]] | None,
    target_model: TargetModel | None = None,
) -> list[DirectForeignKey]:
    """Return declared direct FKs for source tables selected into the package."""
    direct_foreign_keys: list[DirectForeignKey] = []
    for source_entity, target_sources in (foreign_key_value_sources or {}).items():
        if source_entity not in package_tables:
            continue
        for target_entity, value_source in target_sources.items():
            if value_source != "public_id":
                continue
            column_name = None
            if target_model is not None:
                target_spec = target_model.entities.get(target_entity)
                column_name = target_spec.public_id if target_spec is not None else None
            if not column_name:
                continue
            direct_foreign_keys.append(DirectForeignKey(source_entity=source_entity, target_entity=target_entity, column_name=column_name))
    return sorted(direct_foreign_keys, key=lambda item: (item.source_entity, item.target_entity, item.column_name))


def _local_key_series(frame: pd.DataFrame) -> pd.Series:
    """Return the local row identity, using ``system_id`` or the index labels."""
    if "system_id" in frame.columns:
        return frame["system_id"]
    return pd.Series(frame.index, index=frame.index)
