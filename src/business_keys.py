"""Stable business-key serialization for SIMS identity values.

A project declares its source business keys once, in ``EntityConfig.keys``. This module
turns one row's declared key values into a deterministic ``business_id`` string and
checks a complete source table for missing, blank, or duplicate key values.

The serialized form is compact JSON shaped ``[1, [[column, type, value], ...]]``:

- format version ``1`` identifies the current encoding;
- the inner list preserves the declared key order;
- each entry carries the column name, a type tag, and normalized text.

Type tags are ``string``, ``number``, ``boolean``, ``date``, and ``datetime``. Strings keep
their case and contents, numbers become decimal text, dates become ISO text, and
timezone-aware datetimes become UTC ISO text.

This module does not read project files, call SIMS, or write output. Callers pass the
declared key columns and the row values, so the same encoding is used in validation and
in identity work.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from numbers import Integral, Real
from typing import Any

import pandas as pd

BUSINESS_ID_FORMAT_VERSION = 1
"""Version marker used as the first element of every serialized business ID."""

STRING_TYPE = "string"
NUMBER_TYPE = "number"
BOOLEAN_TYPE = "boolean"
DATE_TYPE = "date"
DATETIME_TYPE = "datetime"
SUPPORTED_TYPE_TAGS: tuple[str, ...] = (STRING_TYPE, NUMBER_TYPE, BOOLEAN_TYPE, DATE_TYPE, DATETIME_TYPE)

MANAGED_IDENTIFIER_COLUMN = "system_id"
"""Local identifier column that cannot be declared as a business key."""


class BusinessKeyError(ValueError):
    """Raised when one row's declared business-key values cannot be serialized."""

    def __init__(self, column: str, reason: str) -> None:
        self.column = column
        self.reason = reason
        super().__init__(f"Business key column '{column}': {reason}")


@dataclass(frozen=True, slots=True)
class BusinessKeyPart:
    """One column, type tag, and normalized text inside a serialized business ID."""

    column: str
    type_tag: str
    value: str

    def as_list(self) -> list[str]:
        """Return the JSON-array form of this part."""
        return [self.column, self.type_tag, self.value]


def serialize_business_key(parts: Sequence[BusinessKeyPart]) -> str:
    """Return the compact JSON business ID for ordered key parts."""
    payload: list[Any] = [BUSINESS_ID_FORMAT_VERSION, [part.as_list() for part in parts]]
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def encode_business_key(keys: Sequence[str], row: Mapping[str, Any]) -> list[BusinessKeyPart]:
    """Return normalized key parts for one row, in declared key order.

    Raises:
        BusinessKeyError: A declared key is missing, blank, or holds a value that cannot
            be normalized to a supported type.
    """
    if not keys:
        raise BusinessKeyError("<none>", "at least one business key column is required")

    parts: list[BusinessKeyPart] = []
    for column in keys:
        if column not in row:
            raise BusinessKeyError(column, "the row does not contain this column")
        parts.append(_part_for(column, row[column]))
    return parts


def business_id_for_row(keys: Sequence[str], row: Mapping[str, Any]) -> str:
    """Return the serialized business ID for one row."""
    return serialize_business_key(encode_business_key(keys, row))


def business_key_errors(
    entity_name: str,
    keys: Sequence[str],
    frame: pd.DataFrame,
    *,
    public_id: str | None = None,
    system_id_column: str = MANAGED_IDENTIFIER_COLUMN,
) -> list[str]:
    """Return validation messages for one entity table's declared business keys.

    Checks the declaration itself (nonempty, unique, no managed identifiers), the key
    columns (present in the frame), every row value (present and normalizable), and the
    computed values (unique within this table).

    Returns an empty list when the table passes. Never raises for bad data.
    """
    messages = _declaration_errors(entity_name, keys, public_id=public_id, system_id_column=system_id_column)
    if messages:
        return messages

    missing_columns = [column for column in keys if column not in frame.columns]
    if missing_columns:
        return [
            f"Tracked entity '{entity_name}' is missing declared business key column(s) "
            + ", ".join(f"'{column}'" for column in missing_columns)
            + " in the transformed delivery"
        ]

    first_row_by_business_id: dict[str, object] = {}
    seen_duplicates: set[str] = set()
    for row_index in frame.index:
        row = {column: frame.at[row_index, column] for column in keys}
        try:
            business_id = business_id_for_row(keys, row)
        except BusinessKeyError as exc:
            return [f"Tracked entity '{entity_name}' row '{row_index}': {exc}"]

        previous_row = first_row_by_business_id.get(business_id)
        if previous_row is not None:
            if business_id not in seen_duplicates:
                seen_duplicates.add(business_id)
                messages.append(
                    f"Tracked entity '{entity_name}' rows '{previous_row}' and '{row_index}' share one business key value; "
                    "the transformed delivery must identify each row uniquely"
                )
            continue
        first_row_by_business_id[business_id] = row_index

    return messages


def _declaration_errors(
    entity_name: str,
    keys: Sequence[str],
    *,
    public_id: str | None,
    system_id_column: str,
) -> list[str]:
    """Return validation messages for a declared key list itself."""
    messages: list[str] = []
    if not keys:
        return [f"Tracked entity '{entity_name}' declares no business keys; declare ordered 'keys' in the project entity configuration"]

    blank_keys = [column for column in keys if not isinstance(column, str) or not column.strip()]
    if blank_keys:
        messages.append(f"Tracked entity '{entity_name}' declares a blank business key column")

    trimmed = [column.strip() for column in keys if isinstance(column, str) and column.strip()]
    duplicates = sorted({column for column in trimmed if trimmed.count(column) > 1})
    if duplicates:
        messages.append(f"Tracked entity '{entity_name}' declares duplicate business key column(s): " + ", ".join(duplicates))

    managed = [column for column in trimmed if column == system_id_column or (public_id and column == public_id)]
    if managed:
        messages.append(f"Tracked entity '{entity_name}' cannot use managed identifier column(s) as business keys: " + ", ".join(managed))
    return messages


def _part_for(column: str, raw_value: Any) -> BusinessKeyPart:
    """Return the normalized type tag and text for one raw value."""
    if raw_value is None or raw_value is pd.NaT or raw_value is pd.NA:
        raise BusinessKeyError(column, "value is missing")

    value = raw_value.item() if hasattr(raw_value, "item") and not isinstance(raw_value, (date, datetime)) else raw_value

    if isinstance(value, bool):
        return BusinessKeyPart(column, BOOLEAN_TYPE, "true" if value else "false")

    if isinstance(value, Decimal):
        return BusinessKeyPart(column, NUMBER_TYPE, _decimal_text(_finite_decimal(value, column), column))

    if isinstance(value, Integral):
        return BusinessKeyPart(column, NUMBER_TYPE, _decimal_text(Decimal(int(value)), column))

    if isinstance(value, Real):
        return BusinessKeyPart(column, NUMBER_TYPE, _decimal_text(_finite_decimal(value, column), column))

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise BusinessKeyError(column, "naive datetimes are ambiguous; provide a timezone-aware value")
        return BusinessKeyPart(column, DATETIME_TYPE, value.astimezone(timezone.utc).isoformat())

    if isinstance(value, date):
        return BusinessKeyPart(column, DATE_TYPE, value.isoformat())

    if isinstance(value, str):
        if not value.strip():
            raise BusinessKeyError(column, "value is blank")
        return BusinessKeyPart(column, STRING_TYPE, value)

    raise BusinessKeyError(column, f"unsupported value type '{type(value).__name__}'")


def _finite_decimal(value: Real | Decimal, column: str) -> Decimal:
    """Convert a real number to a finite decimal."""
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise BusinessKeyError(column, "value is not a finite number") from exc
    if not number.is_finite():
        raise BusinessKeyError(column, "value is not a finite number")
    return number


def _decimal_text(number: Decimal, column: str) -> str:
    """Return decimal text without exponent notation."""
    try:
        return format(number.normalize(), "f")
    except (ValueError, InvalidOperation) as exc:  # pragma: no cover - defensive
        raise BusinessKeyError(column, "value is not a finite number") from exc
