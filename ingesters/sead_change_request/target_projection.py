"""PK/FK target projection for the SEAD change request ingester."""

import pandas as pd

from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    PlannedRowAction,
    PlannedTable,
    ProjectedTable,
    ResolvedIdentityTable,
    TargetProjectionResult,
)
from ingesters.sead_change_request.package_builder import INSERTABLE_ROW_STATES
from src.target_model.models import EntitySpec, ForeignKeySpec, TargetModel


def project_target_ids(
    identity_result: IdentityResolutionResult,
    target_model: TargetModel,
    planned_tables: list[PlannedTable] | None = None,
) -> TargetProjectionResult:
    """Replace local identity values with target-facing PK/FK values.

    Conditional foreign keys are evaluated from the final reconciled row states, so
    ``planned_tables`` carries the planned row actions that distinguish an accepted
    existing-row update from a reference-only match.
    """
    tables: dict[str, ProjectedTable] = {}
    diagnostics: list[str] = []
    planned_table_lookup: dict[str, PlannedTable] = {planned_table.entity_name: planned_table for planned_table in planned_tables or []}

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

        required_fk_columns = {
            remote_spec.public_id
            for foreign_key in entity_spec.foreign_keys
            if foreign_key.required and (remote_spec := target_model.entities.get(foreign_key.entity)) is not None and remote_spec.public_id
        }
        for column_name, column_spec in entity_spec.columns.items():
            if (
                frame.empty  # pylint: disable=too-many-boolean-expressions
                or not column_spec.required
                or column_spec.nullable is True
                or column_spec.generated
                or column_name == entity_spec.public_id
                or column_name in required_fk_columns
            ):
                continue
            if column_name not in frame.columns:
                table_diagnostics.append(f"Entity '{entity_name}' is missing required target column '{column_name}'")
                continue
            missing_value_count = int(frame[column_name].isna().sum())
            if missing_value_count:
                table_diagnostics.append(
                    f"Entity '{entity_name}' has {missing_value_count} null value(s) in required target column '{column_name}'"
                )

        for foreign_key in entity_spec.foreign_keys:
            if foreign_key.required_when is not None:
                table_diagnostics.extend(
                    _project_conditional_foreign_key(
                        entity_name,
                        foreign_key,
                        resolved_table,
                        frame,
                        target_model,
                        identity_result,
                        planned_table_lookup.get(entity_name),
                    )
                )
                continue

            remote_entity = foreign_key.entity
            remote_spec = target_model.entities.get(remote_entity)
            if remote_spec is None or not remote_spec.public_id:
                table_diagnostics.append(
                    f"Entity '{entity_name}' cannot project foreign key to '{remote_entity}' because the target public_id is undefined"
                )
                continue

            fk_column = remote_spec.public_id
            if fk_column not in frame.columns:
                if foreign_key.required and not frame.empty:
                    table_diagnostics.append(f"Entity '{entity_name}' is missing required FK column '{fk_column}' for '{remote_entity}'")
                continue
            missing_required_fk_count = int(frame[fk_column].isna().sum())
            if foreign_key.required and missing_required_fk_count:
                table_diagnostics.append(
                    f"Entity '{entity_name}' has {missing_required_fk_count} missing required FK value(s) for '{fk_column}'"
                )
            if not bool(frame[fk_column].notna().any()):
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


def _project_conditional_foreign_key(
    entity_name: str,
    foreign_key: ForeignKeySpec,
    resolved_table: ResolvedIdentityTable,
    frame: pd.DataFrame,
    target_model: TargetModel,
    identity_result: IdentityResolutionResult,
    planned_table: PlannedTable | None,
) -> list[str]:
    """Project one conditional foreign key and report only the rows that need a value.

    The condition applies only to rows finally selected for insertion. Accepted
    existing-row updates keep their projected foreign key value, and matched rows
    that stay out of the package are not evaluated.
    """
    diagnostics: list[str] = []
    insert_mask: pd.Series = resolved_table.row_states.isin(INSERTABLE_ROW_STATES)
    update_mask: pd.Series = _build_packaged_update_mask(planned_table, resolved_table)
    packaged_mask: pd.Series = insert_mask | update_mask
    has_insert_rows = bool(insert_mask.any())

    remote_entity: str = foreign_key.entity
    remote_spec: EntitySpec | None = target_model.entities.get(remote_entity)
    if remote_spec is None or not remote_spec.public_id:
        if has_insert_rows:
            diagnostics.append(
                f"Entity '{entity_name}' cannot project conditional foreign key to '{remote_entity}' "
                "because the target public_id is undefined"
            )
        return diagnostics

    fk_column: str = remote_spec.public_id
    if fk_column not in frame.columns:
        if has_insert_rows:
            diagnostics.append(f"Entity '{entity_name}' is missing conditional FK column '{fk_column}' for '{remote_entity}'")
        return diagnostics

    if not bool(packaged_mask.any()):
        return diagnostics

    missing_conditional_fk_count = int(frame.loc[insert_mask, fk_column].isna().sum())
    if missing_conditional_fk_count:
        diagnostics.append(f"Entity '{entity_name}' has {missing_conditional_fk_count} missing conditional FK value(s) for '{fk_column}'")

    values_needing_projection: pd.Series = frame.loc[packaged_mask, fk_column]
    if not bool(values_needing_projection.notna().any()):
        return diagnostics

    remote_table = identity_result.tables.get(remote_entity)
    if remote_table is None:
        diagnostics.append(
            f"Entity '{entity_name}' cannot project conditional foreign key '{fk_column}' because "
            f"resolved table '{remote_entity}' is missing"
        )
        return diagnostics

    if "system_id" not in remote_table.frame.columns:
        diagnostics.append(
            f"Entity '{entity_name}' cannot project conditional foreign key '{fk_column}' "
            f"because resolved table '{remote_entity}' has no system_id column"
        )
        return diagnostics

    remote_mapping = _build_remote_id_mapping(remote_table.frame["system_id"], remote_table.resolved_target_ids)
    projected_fk: pd.Series = frame[fk_column].map(remote_mapping).astype("Int64")
    unresolved_conditional_fk_count = int(values_needing_projection.notna().sum() - projected_fk.loc[packaged_mask].notna().sum())
    frame[fk_column] = projected_fk
    if unresolved_conditional_fk_count:
        diagnostics.append(
            f"Entity '{entity_name}' has {unresolved_conditional_fk_count} unresolved conditional FK value(s) for '{fk_column}'"
        )

    return diagnostics


def _build_packaged_update_mask(planned_table: PlannedTable | None, resolved_table: ResolvedIdentityTable) -> pd.Series:
    """Return the accepted existing-row update candidates among the resolved rows."""
    if planned_table is None:
        return pd.Series(False, index=resolved_table.frame.index)

    return planned_table.planned_actions.reindex(resolved_table.frame.index) == PlannedRowAction.UPDATE_EXISTING_CANDIDATE


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
