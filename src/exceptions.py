"""Core exception types for Shape Shifter domain/runtime errors.

These exceptions live in `src/` so core logic can raise typed errors
without depending on backend API/domain exception classes.
"""

from typing import Any


class ShapeShifterCoreError(Exception):
    """Base class for core-layer runtime/validation errors."""


class FunctionalDependencyError(ValueError, ShapeShifterCoreError):
    """Raised when functional dependency validation fails."""

    def __init__(
        self,
        message: str,
        *,
        entity_name: str | None = None,
        determinant_columns: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.entity_name = entity_name
        self.determinant_columns = determinant_columns or []
        self.details = details or {}
