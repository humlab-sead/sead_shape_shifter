"""Validation for target IDs supplied in declared foreign-key columns."""

from decimal import Decimal, InvalidOperation
from numbers import Integral, Real
from typing import Protocol

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRowState,
    DirectForeignKey,
    PlannedRowAction,
)
from ingesters.sead_change_request.sql_builder import _update_assignment_columns
from src.target_model.models import EntitySpec, ForeignKeySpec, TargetModel

INTEGER_COLUMN_TYPES = frozenset({"smallint", "integer", "bigint", "int2", "int4", "int8"})
INSERT_ROW_STATES = frozenset(
    {
        ChangeRowState.NEWLY_ALLOCATED_ENTITY,
        ChangeRowState.DERIVED_BRIDGE_ROW,
        ChangeRowState.PENDING_DEPLOYMENT_ID,
    }
)


class DirectForeignKeyChecker(Protocol):
    """Read-only target database methods needed to check supplied IDs."""

    async def target_id_column_type(self, table_name: str, public_id_column: str) -> str | None: ...

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool: ...


async def validate_direct_foreign_keys(
    change_package: ChangeRequestPackage,
    target_model: TargetModel,
    checker: DirectForeignKeyChecker | None,
) -> list[str]:
    """Check selected direct-ID values and replace valid values with integers."""
    diagnostics: list[str] = []
    for direct_fk in change_package.direct_foreign_keys:
        package_table = change_package.tables.get(direct_fk.source_entity)
        source_spec = target_model.entities.get(direct_fk.source_entity)
        target_spec = target_model.entities.get(direct_fk.target_entity)
        if package_table is None or source_spec is None or target_spec is None or not target_spec.target_table:
            continue
        foreign_key = _find_foreign_key(source_spec, direct_fk.target_entity)
        if foreign_key is None:
            continue

        values: dict[int, list[tuple[object, object]]] = {}
        column_spec = source_spec.columns.get(direct_fk.column_name)
        required_on_insert = foreign_key.required or (
            foreign_key.required_when is not None and foreign_key.required_when.has_new_rows == direct_fk.source_entity
        )
        non_nullable = column_spec is not None and column_spec.nullable is False
        generated = column_spec.generated if column_spec is not None else False
        if direct_fk.column_name in package_table.frame.columns:
            package_table.frame[direct_fk.column_name] = package_table.frame[direct_fk.column_name].astype(object)

        for row_index, row in package_table.frame.iterrows():
            state = package_table.row_states.loc[row_index]
            is_insert = state in INSERT_ROW_STATES
            is_update = (
                package_table.planned_actions is not None
                and package_table.planned_actions.loc[row_index] == PlannedRowAction.UPDATE_EXISTING_CANDIDATE
            )
            if is_insert and generated:
                continue
            if is_update and not _is_assigned_update_column(
                row, direct_fk.column_name, source_spec.public_id, package_table.mutable_fields
            ):
                continue
            if not is_insert and not is_update:
                continue

            value = row.get(direct_fk.column_name) if direct_fk.column_name in row.index else None
            if _is_missing(value):
                if (is_insert and (required_on_insert or non_nullable)) or (is_update and non_nullable):
                    diagnostics.append(
                        f"Entity '{direct_fk.source_entity}' row '{row_index}' is missing direct FK value "
                        f"for column '{direct_fk.column_name}'"
                    )
                continue

            target_id = _parse_integer_id(value)
            if target_id is None:
                diagnostics.append(
                    f"Entity '{direct_fk.source_entity}' row '{row_index}' column '{direct_fk.column_name}' "
                    f"has invalid direct target ID value {value!r}; expected an integer"
                )
                continue

            package_table.frame.at[row_index, direct_fk.column_name] = target_id
            values.setdefault(target_id, []).append((row_index, value))

        if not values:
            continue
        diagnostics.extend(
            await _check_target_values(
                direct_fk,
                target_spec.target_table,
                values,
                checker,
            )
        )

    return diagnostics


async def _check_target_values(
    direct_fk: DirectForeignKey,
    table_name: str,
    values: dict[int, list[tuple[object, object]]],
    checker: DirectForeignKeyChecker | None,
) -> list[str]:
    """Check the target column type and each distinct supplied ID."""
    diagnostics: list[str] = []
    if checker is None:
        return _value_diagnostics(direct_fk, values, "target database lookup is unavailable")

    type_lookup = getattr(checker, "target_id_column_type", None)
    exists_lookup = getattr(checker, "target_id_exists", None)
    if not callable(type_lookup) or not callable(exists_lookup):
        return _value_diagnostics(direct_fk, values, "target database lookup cannot verify the ID column and value")

    try:
        column_type = await type_lookup(table_name, direct_fk.column_name)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _value_diagnostics(
            direct_fk,
            values,
            f"target database could not read the column type ({exc})",
        )

    normalized_type = column_type.strip().lower() if isinstance(column_type, str) else None
    if normalized_type is None:
        return _value_diagnostics(direct_fk, values, f"target column '{table_name}.{direct_fk.column_name}' does not exist")
    if normalized_type not in INTEGER_COLUMN_TYPES:
        return _value_diagnostics(
            direct_fk,
            values,
            f"target column '{table_name}.{direct_fk.column_name}' has non-integer type '{column_type}'",
        )

    for target_id, occurrences in values.items():
        try:
            exists = await exists_lookup(table_name, direct_fk.column_name, target_id)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            reason = f"target database could not check the ID ({exc})"
        else:
            reason = "" if exists else f"target ID is absent from '{table_name}.{direct_fk.column_name}'"
        if reason:
            for row_index, supplied_value in occurrences:
                diagnostics.append(
                    f"Entity '{direct_fk.source_entity}' row '{row_index}' column '{direct_fk.column_name}' "
                    f"has unverifiable direct target ID value {supplied_value!r}: {reason}"
                )
    return diagnostics


def _value_diagnostics(
    direct_fk: DirectForeignKey,
    values: dict[int, list[tuple[object, object]]],
    reason: str,
) -> list[str]:
    """Return one contextual database-check error for each supplied value."""
    return [
        f"Entity '{direct_fk.source_entity}' row '{row_index}' column '{direct_fk.column_name}' "
        f"has unverifiable direct target ID value {supplied_value!r}: {reason}"
        for occurrences in values.values()
        for row_index, supplied_value in occurrences
    ]


def _find_foreign_key(entity_spec: EntitySpec, target_entity: str) -> ForeignKeySpec | None:
    """Return the direct target-model FK for one target entity."""
    return next((item for item in entity_spec.foreign_keys if item.entity == target_entity and item.via is None), None)


def _is_assigned_update_column(
    row: pd.Series,
    column_name: str,
    public_id_column: str | None,
    mutable_fields: list[str] | None,
) -> bool:
    """Use the deploy renderer's rules to decide whether an update writes a column."""
    return column_name in _update_assignment_columns(row, public_id_column or "", mutable_fields)


def _parse_integer_id(value: object) -> int | None:
    """Return an exact integer value, rejecting booleans and fractional values."""
    if isinstance(value, bool) or not isinstance(value, (Integral, Real, Decimal, str)):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number != number.to_integral_value():
        return None
    try:
        return int(number)
    except (OverflowError, ValueError):
        return None


def _is_missing(value: object) -> bool:
    """Return whether one DataFrame scalar is null."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
