"""Shared Core issue types used across validation and specification layers."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any


@dataclass(slots=True, kw_only=True)
class CoreIssue:
    """Shared domain issue envelope for structural and data validation.

    Attributes:
        severity: Severity level for the issue, typically ``error``, ``warning``, or ``info``.
        message: Human-readable issue description.
        entity: Entity or top-level subject that the issue belongs to.
        field: Configuration field or logical field path associated with the issue.
        column: Concrete data column associated with the issue when a more specific location is needed.
        code: Optional machine-readable issue code for programmatic handling.
        category: Optional issue category such as ``structural`` or ``data``.
        metadata: Additional issue-specific context that does not fit the shared canonical fields.
    """

    severity: str
    message: str
    entity: str | None = None
    field: str | None = None
    column: str | None = None
    code: str | None = None
    category: str | None = None
    metadata: dict[str, Any] = dataclass_field(default_factory=dict, repr=False)

    @property
    def entity_name(self) -> str | None:
        """Backward-compatible alias for ``entity``."""
        return self.entity

    @property
    def entity_field(self) -> str | None:
        """Backward-compatible alias for ``field``."""
        return self.field

    @property
    def column_name(self) -> str | None:
        """Backward-compatible alias for ``column``."""
        return self.column

    @property
    def kwargs(self) -> dict[str, Any]:
        """Backward-compatible alias for arbitrary issue metadata."""
        return self.metadata

    def __str__(self) -> str:
        """Return a concise human-readable issue summary."""
        parts: list[str] = [f"[{self.severity.upper()}]"]
        if self.entity:
            parts.append(f"Entity '{self.entity}':")
        parts.append(self.message)
        if self.field:
            parts.append(f"(field: {self.field})")
        if self.column:
            parts.append(f"(column: {self.column})")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Return the same representation used for user-facing issue text."""
        return self.__str__()
