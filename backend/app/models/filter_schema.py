"""Filter schema models for API responses."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FilterFieldMetadataResponse(BaseModel):
    """Filter field metadata for API response."""

    name: str = Field(..., description="Field name")
    type: Literal["string", "boolean", "entity", "column"] = Field(..., description="Field type")
    required: bool = Field(False, description="Whether field is required")
    default: Any = Field(None, description="Default value")
    description: str = Field("", description="Field description")
    placeholder: str = Field("", description="Placeholder text")
    options_source: Literal["entities", "columns"] | None = Field(None, description="Source for autocomplete options")


class FilterSchemaResponse(BaseModel):
    """Filter schema for API response."""

    key: str = Field(..., description="Filter identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Filter description")
    fields: list[FilterFieldMetadataResponse] = Field(..., description="Configuration fields")
