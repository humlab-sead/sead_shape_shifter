"""Helpers for deriving authoritative fixed-entity schemas."""

from __future__ import annotations

from typing import Any, TypedDict


class FixedSchema(TypedDict):
    """Authoritative fixed-schema metadata for editor clients."""

    full_columns: list[str]
    editable_columns: list[str]
    identity_columns: list[str]
    key_columns: list[str]
    order_source: str


def _normalize_columns(value: Any) -> list[str]:
    """Normalize a list-like field into ordered, unique string values."""
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        column: str = item.strip()
        if column and column not in normalized:
            normalized.append(column)
    return normalized


def derive_fixed_schema(entity_data: dict[str, Any]) -> FixedSchema | None:
    """Derive authoritative fixed-schema metadata from stored entity data."""
    if entity_data.get("type") != "fixed":
        return None

    raw_columns: list[str] = _normalize_columns(entity_data.get("columns"))
    key_columns: list[str] = _normalize_columns(entity_data.get("keys"))
    public_id: str = ""
    if isinstance(entity_data.get("public_id"), str):
        public_id = entity_data["public_id"].strip()
    elif isinstance(entity_data.get("surrogate_id"), str):
        public_id = entity_data["surrogate_id"].strip()

    identity_columns: list[str] = ["system_id"]
    if public_id:
        identity_columns.append(public_id)

    hidden_columns: list[str] = []
    for column in identity_columns + key_columns:
        if column not in hidden_columns:
            hidden_columns.append(column)

    stored_full_columns: bool = "system_id" in raw_columns

    if stored_full_columns:
        full_columns = raw_columns
        order_source = "stored"
    else:
        full_columns = []
        for column in hidden_columns + raw_columns:
            if column not in full_columns:
                full_columns.append(column)
        order_source = "derived"

    editable_columns: list[str] = [column for column in full_columns if column not in hidden_columns]

    return {
        "full_columns": full_columns,
        "editable_columns": editable_columns,
        "identity_columns": identity_columns,
        "key_columns": key_columns,
        "order_source": order_source,
    }
