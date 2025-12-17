"""API models for driver schema metadata."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldMetadataResponse(BaseModel):
    """Response model for field metadata.

    Describes a single configuration field for a data source driver.
    """

    name: str = Field(..., description="Field identifier")
    type: Literal["string", "integer", "boolean", "password", "file_path"] = Field(..., description="Field data type")
    required: bool = Field(..., description="Whether the field is mandatory")
    default: Any = Field(None, description="Default value for the field")
    description: str = Field("", description="Human-readable description")
    min_value: int | None = Field(None, description="Minimum value for integer fields")
    max_value: int | None = Field(None, description="Maximum value for integer fields")
    placeholder: str = Field("", description="Example value to show in UI")


class DriverSchemaResponse(BaseModel):
    """Response model for driver schema.

    Describes the complete configuration schema for a data source driver.
    """

    driver: str = Field(..., description="Driver identifier")
    display_name: str = Field(..., description="Human-readable driver name")
    description: str = Field(..., description="Driver description")
    category: Literal["database", "file"] = Field(..., description="Driver category")
    fields: list[FieldMetadataResponse] = Field(..., description="List of supported configuration fields")
