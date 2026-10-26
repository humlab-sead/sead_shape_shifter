"""Helpers for deriving authoritative fixed-entity schemas."""

from __future__ import annotations

from typing import Any, TypedDict

from src.types.fixed_entity_types import build_fixed_entity_full_columns, build_fixed_entity_legacy_columns


class FixedSchema(TypedDict):
    """Authoritative fixed-schema metadata for editor clients."""

    full_columns: list[str]
    editable_columns: list[str]
    identity_columns: list[str]
    key_columns: list[str]
    order_source: str


def build_fixed_full_columns(columns: list[str], public_id: str | None) -> list[str]:
    """Build canonical fixed-entity column order.

    Delegates to the core ordering rule so the backend and project validation
    share one definition of the authoritative fixed-entity column order.
    """
    trimmed_public_id: str | None = public_id.strip() if public_id else None
    return build_fixed_entity_full_columns(columns, trimmed_public_id or None)


def build_legacy_fixed_full_columns(entity_data: dict[str, Any]) -> list[str]:
    """Rebuild the historical identity/keys/data order from stored entity data.

    Used only to recognize legacy fixed-values requests during the compatibility
    period; the authoritative order comes from :func:`derive_fixed_schema`.
    """
    fixed_schema = derive_fixed_schema(entity_data)
    if not fixed_schema:
        return []

    identity_columns: list[str] = fixed_schema["identity_columns"]
    public_id: str | None = identity_columns[1] if len(identity_columns) > 1 else None
    identity_set: set[str] = set(identity_columns)
    data_columns: list[str] = [column for column in fixed_schema["full_columns"] if column not in identity_set]
    return build_fixed_entity_legacy_columns(data_columns, fixed_schema["key_columns"], public_id)


def format_missing_fixed_keys_message(entity_name: str, missing_keys: list[str], full_columns: list[str]) -> str:
    """Explain missing fixed business keys and show the expected positional order."""
    return (
        f"Fixed data entity '{entity_name}' uses business key(s) {sorted(missing_keys)} that it does not produce. "
        "'keys' do not create output columns. Add the missing fields to 'columns' or configure the producer that creates them. "
        f"Expected positional column order: {full_columns}"
    )


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

    full_columns: list[str] = build_fixed_full_columns(raw_columns, public_id or None)
    order_source = "stored" if raw_columns == full_columns else "derived"

    editable_columns: list[str] = [column for column in full_columns if column not in hidden_columns]

    return {
        "full_columns": full_columns,
        "editable_columns": editable_columns,
        "identity_columns": identity_columns,
        "key_columns": key_columns,
        "order_source": order_source,
    }


def normalize_fixed_entity(entity_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize fixed-entity columns to produced data fields for persistence.

    Managed identity columns are not stored in ``columns``; the authoritative
    positional order is rebuilt from identity plus data on read.
    """
    fixed_schema = derive_fixed_schema(entity_data)
    if not fixed_schema:
        return entity_data

    identity_columns: set[str] = set(fixed_schema["identity_columns"])
    normalized_entity = dict(entity_data)
    normalized_entity["columns"] = [column for column in fixed_schema["full_columns"] if column not in identity_columns]
    return normalized_entity
