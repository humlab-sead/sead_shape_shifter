"""
Models for auto-fix functionality.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FixActionType(str, Enum):
    """Types of fix actions that can be applied."""

    ADD_COLUMN = "add_column"
    REMOVE_COLUMN = "remove_column"
    UPDATE_REFERENCE = "update_reference"
    ADD_CONSTRAINT = "add_constraint"
    REMOVE_CONSTRAINT = "remove_constraint"
    UPDATE_QUERY = "update_query"
    ADD_ENTITY = "add_entity"
    REMOVE_ENTITY = "remove_entity"
    UPDATE_VALUES = "update_values"  # For updating fixed entity values (system_id repair)


class FixAction(BaseModel):
    """A single fix action to apply to project."""

    type: FixActionType
    entity: str
    field: str | None = None
    old_value: Any | None = None
    new_value: Any | None = None
    description: str


class FixSuggestion(BaseModel):
    """A suggested fix for a validation issue."""

    issue_code: str
    entity: str
    field: str | None = None
    suggestion: str
    actions: list[FixAction]
    auto_fixable: bool = True
    requires_confirmation: bool = False
    warnings: list[str] = Field(default_factory=list)


class FixResult(BaseModel):
    """Result of applying fixes."""

    success: bool
    fixes_applied: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    backup_path: str | None = None
    updated_config: dict[str, Any] | None = None
