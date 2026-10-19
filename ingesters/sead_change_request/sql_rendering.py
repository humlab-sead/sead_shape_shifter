"""Shared PostgreSQL rendering helpers for change-request artifacts.

Both the direct deploy strategies and the inline staging renderer quote
identifiers, relations, strings, and literals. Keeping the helpers here avoids a
circular import between ``sql_builder`` and ``inline_staging_sql`` and keeps one
definition of each quoting rule.
"""

from __future__ import annotations

import gzip
from collections.abc import Container, Mapping
from datetime import datetime
from numbers import Integral, Real
from typing import Any, cast

import pandas as pd

TIMEZONE_AWARE_TYPE_NAMES = frozenset({"timestamptz", "timetz"})
"""PostgreSQL type names that carry an explicit timezone."""


def normalize_column_type(column_type: str | None) -> str:
    """Return a lower-case, single-spaced descriptor for a target column type."""
    if not column_type:
        return ""
    return " ".join(str(column_type).strip().lower().split())


def is_timezone_aware_type(column_type: str | None) -> bool:
    """Return whether a target column type explicitly stores a timezone."""
    normalized = normalize_column_type(column_type)
    if not normalized:
        return False
    return normalized in TIMEZONE_AWARE_TYPE_NAMES or "with time zone" in normalized


def is_date_type(column_type: str | None) -> bool:
    """Return whether a target column type stores only a calendar date."""
    return normalize_column_type(column_type) == "date"


def is_timestamp_type(column_type: str | None) -> bool:
    """Return whether a target column type stores a date and a clock time."""
    normalized = normalize_column_type(column_type)
    return normalized.startswith("timestamp") or normalized == "datetime"


def drop_timezone(value: datetime | pd.Timestamp) -> datetime | pd.Timestamp:
    """Remove timezone metadata without changing the calendar or clock fields."""
    if isinstance(value, pd.Timestamp):
        return value.tz_localize(None) if value.tzinfo is not None else value
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def is_midnight(value: datetime | pd.Timestamp) -> bool:
    """Return whether a timezone-naive value falls exactly on midnight."""
    return value.hour == 0 and value.minute == 0 and value.second == 0 and value.microsecond == 0 and getattr(value, "nanosecond", 0) == 0


def timezone_aware_target_message(column_type: str | None) -> str:
    """Return a clear rejection message for a timezone-aware target column."""
    return f"Target column type '{column_type}' is timezone-aware; normalized values must target " "a timezone-naive column"


def validate_target_temporal_types(
    entity_name: str,
    column_names: Container[str],
    column_types: Mapping[str, str | None],
) -> None:
    """Reject explicitly timezone-aware target columns before artifact rendering."""
    for column_name in column_names:
        declared_type = column_types.get(column_name)
        if is_timezone_aware_type(declared_type):
            raise ValueError(
                f"Target column '{entity_name}.{column_name}' declares timezone-aware type '{declared_type}'; "
                "normalized values require a timezone-naive column"
            )


def render_temporal_text(value: datetime | pd.Timestamp, column_type: str | None) -> str:
    """Render a temporal value from its target column type without converting zones."""
    if is_timezone_aware_type(column_type):
        raise ValueError(timezone_aware_target_message(column_type))
    if is_date_type(column_type):
        return value.date().isoformat()
    return drop_timezone(value).isoformat()


def quote_identifier(identifier: str) -> str:
    """Quote one PostgreSQL identifier."""
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def quote_relation(relation_name: str) -> str:
    """Quote each part of a possibly schema-qualified PostgreSQL relation name."""
    return ".".join(quote_identifier(part) for part in relation_name.split("."))


def quote_qualified_relation(schema_name: str, relation_name: str) -> str:
    """Return a quoted ``schema.relation`` name."""
    return f"{quote_identifier(schema_name)}.{quote_identifier(relation_name)}"


def quote_string(value: str) -> str:
    """Quote one PostgreSQL string literal."""
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def render_literal(value: object, column_type: str | None = None) -> str:
    """Render one Python value as a PostgreSQL literal."""

    scalar_value = cast(Any, value)
    if value is None or pd.isna(scalar_value):
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Integral):
        return str(value)
    if isinstance(value, Real):
        return repr(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return quote_string(render_temporal_text(value, column_type))
    return quote_string(str(value))


def renderable_columns(row_like: pd.Series | pd.DataFrame, excluded_columns: set[str] | None = None) -> list[str]:
    """Return non-internal column names in stable order for artifact rendering."""
    excluded = excluded_columns or set()
    if isinstance(row_like, pd.DataFrame):
        return [str(column) for column in row_like.columns if _is_renderable_column(str(column), excluded)]
    return [str(column) for column in row_like.index if _is_renderable_column(str(column), excluded)]


def _is_renderable_column(column_name: str, excluded: set[str]) -> bool:
    """Return whether one column should be written to a target table."""
    return (
        column_name not in excluded
        and not column_name.startswith("_")
        and not column_name.endswith("__existing")
        and column_name != "system_id"
    )


def encode_bundle_file_content(relative_path: str, content: str) -> bytes:
    """Encode bundle content exactly as it will be written to disk."""
    encoded = content.encode("utf-8")
    if relative_path.endswith(".gz"):
        return gzip.compress(encoded, mtime=0)
    return encoded
