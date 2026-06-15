"""Pydantic v2 models for the mapping sidecar schema (`<project>-mapping.yml`).

Defines the full schema for persisting reconciled and manually-assigned
local-key-to-target-ID links alongside entity-level metadata in a project
sidecar file.  Compound local keys are encoded with a pipe separator;
embedded pipes and nulls are escaped for reliable round-tripping.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Compound-key encoding helpers
# ---------------------------------------------------------------------------

_COMPOUND_SEPARATOR = "|"
_COMPOUND_ESCAPE = "\\"
_COMPOUND_NULL_MARKER = "<NULL>"


def encode_local_key(local_key: Union[str, list[str]], values: Any) -> str:
    """Encode one or more local-key column values into a stable string key.

    Single-column keys are returned as the string representation of the
    single value.  Multi-column keys are joined with ``|``.  Embedded pipe
    characters are escaped as ``\\|``, and ``None`` / ``NaN`` values are
    represented by the literal ``<NULL>``.

    Args:
        local_key: Either a single column name (``str``) or an ordered list
            of column names (``list[str]``).
        values: A single value when *local_key* is a string, or an iterable
            of values whose positions correspond to the *local_key* list.

    Returns:
        The encoded string key suitable for use as a dictionary key in
        ``EntityMapping.links``.
    """
    if isinstance(local_key, str):
        return _encode_single(values)

    # Multi-column compound key – pair values with column positions.
    parts: list[str] = [_encode_single(v) for v in values]
    return _COMPOUND_SEPARATOR.join(parts)


def decode_local_key(local_key: Union[str, list[str]], encoded: str) -> list[str]:
    """Decode a string key back into individual component values.

    Reverses the encoding performed by :func:`encode_local_key`.

    Args:
        local_key: The same *local_key* used when encoding.
        encoded: A string previously produced by :func:`encode_local_key`.

    Returns:
        A list of decoded string values whose length matches the number of
        columns in *local_key*.
    """
    if isinstance(local_key, str):
        return [_decode_single(encoded)]

    # Split on unescaped pipes only.
    parts: list[str] = _split_compound(encoded)
    return [_decode_single(p) for p in parts]


def _encode_single(value: Any) -> str:
    """Encode a single value, escaping embedded pipes and normalising null."""
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        return _COMPOUND_NULL_MARKER
    s = str(value)
    return s.replace(_COMPOUND_ESCAPE, _COMPOUND_ESCAPE + _COMPOUND_ESCAPE).replace(
        _COMPOUND_SEPARATOR, _COMPOUND_ESCAPE + _COMPOUND_SEPARATOR
    )


def _decode_single(encoded: str) -> str:
    """Decode a single value: ``<NULL>`` back to empty string, unescape."""
    if encoded == _COMPOUND_NULL_MARKER:
        return ""
    result: list[str] = []
    i = 0
    while i < len(encoded):
        ch = encoded[i]
        if ch == _COMPOUND_ESCAPE and i + 1 < len(encoded):
            result.append(encoded[i + 1])
            i += 2
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def _split_compound(encoded: str) -> list[str]:
    """Split an encoded compound key on unescaped ``|`` characters."""
    parts: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(encoded):
        ch = encoded[i]
        if ch == _COMPOUND_ESCAPE and i + 1 < len(encoded):
            current.append(ch)
            current.append(encoded[i + 1])
            i += 2
        elif ch == _COMPOUND_SEPARATOR:
            parts.append("".join(current))
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    parts.append("".join(current))
    return parts


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LinkSource(str, Enum):
    """Provenance of a mapping link – determines precedence during normalization."""

    MANUAL = "manual"
    RECONCILIATION = "reconciliation"
    IMPORT = "import"


class EntityType(str, Enum):
    """Entity classification used for UI grouping and validation."""

    PRIMARY = "primary"
    LINK_ENTITY = "link_entity"
    DERIVED = "derived"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Link(BaseModel):
    """A single local-key-to-target-ID mapping entry."""

    target_id: Optional[int] = None
    source: LinkSource
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    committed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_by: str
    reviewed_by: Optional[str] = None


class EntityMapping(BaseModel):
    """Mapping configuration and links for a single entity."""

    local_key: Union[str, list[str]]
    public_id: str
    entity_type: EntityType = EntityType.PRIMARY
    description: Optional[str] = None
    links: dict[str, Link] = Field(default_factory=dict)


class Metadata(BaseModel):
    """File-level metadata carried at the top of the sidecar."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project: str


class MappingCatalog(BaseModel):
    """Root container for the mapping sidecar file.

    Holds entity-level mappings and provides helpers for link lookup,
    insertion, and filtering (committed vs. draft).
    """

    version: str = "2.0"
    metadata: Metadata
    entities: dict[str, EntityMapping] = Field(default_factory=dict)

    # -- Link accessors ---------------------------------------------------

    def get_link(self, entity_name: str, local_key_value: str) -> Optional[Link]:
        """Return the link for *entity_name* / *local_key_value*, or ``None``."""
        entity: EntityMapping | None = self.entities.get(entity_name)
        if entity is None:
            return None
        return entity.links.get(local_key_value)

    def set_link(self, entity_name: str, local_key_value: str, link: Link) -> None:
        """Create or replace a link for an entity.

        Raises:
            KeyError: If *entity_name* is not present in the catalog.
        """
        if entity_name not in self.entities:
            raise KeyError(f"Entity '{entity_name}' not found in mapping catalog")
        self.entities[entity_name].links[local_key_value] = link
        self.metadata.updated_at = datetime.now(timezone.utc)

    # -- Bulk link queries ------------------------------------------------

    def committed_links_by_entity(self, entity_name: str) -> dict[str, Link]:
        """Return only links with a non-null ``committed_at`` for *entity_name*."""
        entity: EntityMapping | None = self.entities.get(entity_name)
        if entity is None:
            return {}
        return {k: v for k, v in entity.links.items() if v.committed_at is not None}

    def draft_links_by_entity(self, entity_name: str) -> dict[str, Link]:
        """Return only links whose ``committed_at`` is null for *entity_name*."""
        entity: EntityMapping | None = self.entities.get(entity_name)
        if entity is None:
            return {}
        return {k: v for k, v in entity.links.items() if v.committed_at is None}
