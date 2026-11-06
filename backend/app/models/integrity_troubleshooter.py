"""API models for the read-only foreign-key integrity troubleshooter.

The inspection result is separate from the row-count troubleshooter: integrity
warnings describe values that have no remote match, not a merge that changed the
row count. The request carries an optional type-preserving token so a selected
value can be addressed without depending on its position in a value page.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Literal, Sequence

from pydantic import BaseModel, Field, field_validator

IntegrityStatus = Literal["reproduced", "not_reproduced", "ineligible"]
"""Outcome of inspecting one saved integrity warning."""

IntegritySelectionStatus = Literal["selected", "unavailable"]
"""Whether the requested value still names a current unmatched key."""

_TOKEN_TYPES: frozenset[str] = frozenset({"null", "bool", "int", "float", "str"})
"""Scalar type tags a value token may carry."""

FULL_NORMALIZATION_SOURCE = "current full normalization"
"""Data source stated in every inspection response."""


def _encode_scalar(value: Any) -> dict[str, Any]:
    """Return a tagged JSON form for one key scalar."""
    if value is None:
        return {"t": "null", "v": None}
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "int", "v": value}
    if isinstance(value, float):
        return {"t": "float", "v": value}
    return {"t": "str", "v": str(value)}


def _decode_scalar(payload: Any) -> Any:
    """Return the Python scalar for one tagged token value, raising ValueError when malformed."""
    if not isinstance(payload, dict):
        raise ValueError("Token value is not an object")

    kind: Any = payload.get("t")
    value: Any = payload.get("v")

    if kind not in _TOKEN_TYPES:
        raise ValueError("Token value has an unknown type")

    if kind == "null":
        return None
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError("Token bool value is not a bool")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Token int value is not an int")
        return value
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Token float value is not a number")
        return float(value)
    if not isinstance(value, str):
        raise ValueError("Token str value is not a string")
    return value


def encode_key_token(key_values: Sequence[Any]) -> str:
    """Encode an ordered key tuple into a stateless, type-preserving token.

    Args:
        key_values: Python scalar key values in configured key order.

    Returns:
        A URL-safe base64 token that can be decoded without server state.
    """
    payload = [_encode_scalar(value) for value in key_values]
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_key_token(token: str) -> tuple[Any, ...]:
    """Decode a key token into its ordered Python scalar values.

    Args:
        token: Token produced by :func:`encode_key_token`.

    Returns:
        The key tuple that the token names.

    Raises:
        ValueError: If the token is not valid base64, JSON, or a typed key list.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise ValueError("Token is not valid base64") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Token is not valid JSON") from exc

    if not isinstance(payload, list) or not payload:
        raise ValueError("Token must contain an ordered list of key values")

    return tuple(_decode_scalar(item) for item in payload)


class IntegrityTroubleshootRequest(BaseModel):
    """Request one value page and optionally one selected value's local rows."""

    issue_type: str
    local_entity: str
    metadata: dict[str, Any]
    page: int = Field(default=1, ge=1)
    selected_value_token: str | None = None

    @field_validator("selected_value_token")
    @classmethod
    def _validate_selected_value_token(cls, value: str | None) -> str | None:
        """Reject a malformed token before the endpoint runs the service."""
        if value is None:
            return None
        decode_key_token(value)
        return value


class IntegrityTroubleshootKeys(BaseModel):
    """Ordered local and remote keys of the saved link."""

    local_keys: list[str]
    remote_keys: list[str]


class IntegrityTroubleshootRelationship(BaseModel):
    """Read-only saved relationship details."""

    local_entity: str
    remote_entity: str | None = None
    fk_index: int | None = None
    join_type: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class IntegrityTroubleshootValue(BaseModel):
    """One distinct unmatched key and the local rows that carry it."""

    key_values: list[Any]
    local_row_count: int
    token: str


class IntegrityTroubleshootValuePage(BaseModel):
    """One bounded page of distinct unmatched keys."""

    page: int
    page_size: int
    distinct_value_count: int
    returned_value_count: int
    has_next: bool
    values: list[IntegrityTroubleshootValue] = Field(default_factory=list)


class IntegrityTroubleshootRows(BaseModel):
    """Bounded local rows for one selected unmatched value."""

    status: IntegritySelectionStatus
    reason: str | None = None
    message: str | None = None
    key_values: list[Any] | None = None
    total_row_count: int | None = None
    returned_row_count: int | None = None
    columns: list[str] = Field(default_factory=list)
    columns_truncated: bool = False
    rows: list[dict[str, Any]] = Field(default_factory=list)


class IntegrityTroubleshootResponse(BaseModel):
    """Read-only integrity result for one saved foreign key."""

    status: IntegrityStatus
    reason: str
    message: str
    source: str = FULL_NORMALIZATION_SOURCE
    relationship: IntegrityTroubleshootRelationship | None = None
    configured_keys: IntegrityTroubleshootKeys | None = None
    recorded_orphan_count: int | None = None
    current_orphan_count: int | None = None
    values: IntegrityTroubleshootValuePage | None = None
    selected: IntegrityTroubleshootRows | None = None
