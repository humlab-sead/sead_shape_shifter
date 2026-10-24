"""Request and response models for draft-aware column references."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ColumnReferenceFailureCode(str, Enum):
    """Stable reason codes returned when a requested reference cannot be used."""

    MALFORMED_INPUT = "malformed_input"
    MISSING_PATH = "missing_path"
    CIRCULAR_REFERENCE = "circular_reference"
    DEPENDENCY_FAILURE = "dependency_failure"
    WRONG_RESULT_TYPE = "wrong_result_type"


class ColumnReferenceResolveRequest(BaseModel):
    """Request resolution of one directive against an unsaved entity draft."""

    entity_draft: dict[str, Any] = Field(description="Current unsaved entity values")
    directive: str = Field(description="Complete simple @value directive to check")


class ColumnReferenceResolveResponse(BaseModel):
    """Resolved columns or one local reason that the directive could not be used."""

    directive: str
    path: str | None
    status: Literal["resolved", "unresolved"]
    columns: list[str] | None = None
    reason_code: ColumnReferenceFailureCode | None = None
    reason: str | None = None


class ColumnReferenceCompleteRequest(BaseModel):
    """Request filtered @value candidates for an unsaved entity draft."""

    entity_draft: dict[str, Any] = Field(description="Current unsaved entity values")
    prefix: str = Field(description="Typed @value prefix")
    edited_field_path: str | None = Field(default=None, description="Path of the field being edited")
    preferred_entity: str | None = Field(default=None, description="Entity to show first for a related FK field")


class ColumnReferenceCompleteResponse(BaseModel):
    """Full reference directive strings that match the typed prefix."""

    candidates: list[str]
