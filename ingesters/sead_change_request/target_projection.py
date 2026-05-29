"""PK/FK target projection for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import IdentityResolutionResult, ProjectedTable, TargetProjectionResult
from src.target_model.models import EntitySpec, TargetModel


def project_target_ids(identity_result: IdentityResolutionResult, target_model: TargetModel) -> TargetProjectionResult:
    """Replace local identity values with target-facing PK/FK values."""
    tables: dict[str, ProjectedTable] = {}
    diagnostics: list[str] = []

    for entity_name, resolved_table in identity_result.tables.items():
        entity_spec: EntitySpec = target_model.entities[entity_name]
        frame: pd.DataFrame = resolved_table.frame.copy()
        table_diagnostics: list[str] = []

        if entity_spec.public_id:
            frame[entity_spec.public_id] = resolved_table.resolved_target_ids.astype("Int64")
            unresolved_pk_count = int(frame[entity_spec.public_id].isna().sum())
            if unresolved_pk_count:
                table_diagnostics.append(
                    f"Entity '{entity_name}' has {unresolved_pk_count} row(s) without a resolved target ID for '{entity_spec.public_id}'"
                )

        for foreign_key in entity_spec.foreign_keys:
            remote_entity = foreign_key.entity
            remote_spec = target_model.entities.get(remote_entity)
            if remote_spec is None or not remote_spec.public_id:
                table_diagnostics.append(
                    f"Entity '{entity_name}' cannot project foreign key to '{remote_entity}' because the target public_id is undefined"
                )
                continue

            fk_column = remote_spec.public_id
            if fk_column not in frame.columns:
                continue

            remote_table = identity_result.tables.get(remote_entity)
            if remote_table is None:
                table_diagnostics.append(
                    f"Entity '{entity_name}' cannot project foreign key '{fk_column}' because "
                    f"resolved table '{remote_entity}' is missing"
                )
                continue

            if "system_id" not in remote_table.frame.columns:
                table_diagnostics.append(
                    f"Entity '{entity_name}' cannot project foreign key '{fk_column}' "
                    f"because resolved table '{remote_entity}' has no system_id column"
                )
                continue

            remote_mapping = _build_remote_id_mapping(remote_table.frame["system_id"], remote_table.resolved_target_ids)
            projected_fk = frame[fk_column].map(remote_mapping).astype("Int64")
            unresolved_fk_count = int(frame[fk_column].notna().sum() - projected_fk.notna().sum())
            frame[fk_column] = projected_fk
            if unresolved_fk_count:
                table_diagnostics.append(f"Entity '{entity_name}' has {unresolved_fk_count} unresolved FK value(s) for '{fk_column}'")

        tables[entity_name] = ProjectedTable(entity_name=entity_name, frame=frame, diagnostics=table_diagnostics)
        diagnostics.extend(table_diagnostics)

    return TargetProjectionResult(tables=tables, diagnostics=diagnostics)


def _build_remote_id_mapping(system_ids: pd.Series, resolved_target_ids: pd.Series) -> dict[object, int]:
    """Create a mapping from local system_id values to resolved target IDs."""
    mapping: dict[object, int] = {}
    for row_index in system_ids.index:
        system_id = system_ids.loc[row_index]
        target_id = resolved_target_ids.loc[row_index]
        if pd.isna(system_id) or pd.isna(target_id):
            continue
        mapping[system_id] = int(target_id)
    return mapping
