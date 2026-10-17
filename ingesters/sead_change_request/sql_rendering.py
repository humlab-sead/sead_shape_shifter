"""Shared PostgreSQL rendering helpers for change-request artifacts.

Both the direct deploy strategies and the inline staging renderer quote
identifiers, relations, strings, and literals. Keeping the helpers here avoids a
circular import between ``sql_builder`` and ``inline_staging_sql`` and keeps one
definition of each quoting rule.
"""

from __future__ import annotations

import gzip
from datetime import datetime
from typing import Any, cast

import pandas as pd


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


def render_literal(value: object) -> str:
    """Render one Python value as a PostgreSQL literal."""
    from numbers import Integral, Real

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
        return quote_string(value.isoformat())
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
