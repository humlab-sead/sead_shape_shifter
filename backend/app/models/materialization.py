"""Models for entity materialization functionality."""

from typing import Literal

from pydantic import BaseModel, Field


class MaterializeRequest(BaseModel):
    """Request model for materializing an entity."""

    storage_format: Literal["csv", "parquet", "inline"] = Field(default="parquet", description="Storage format for materialized data")
    user_email: str | None = Field(default=None, description="Email of user performing materialization")


class MaterializationResult(BaseModel):
    """Result of entity materialization operation."""

    success: bool
    entity_name: str | None = None
    rows_materialized: int | None = None
    storage_file: str | None = None
    storage_format: str | None = None
    errors: list[str] = []


class UnmaterializeRequest(BaseModel):
    """Request model for unmaterializing an entity."""

    cascade: bool = Field(default=False, description="Also unmaterialize dependent materialized entities")


class UnmaterializationResult(BaseModel):
    """Result of entity unmaterialization operation."""

    success: bool
    entity_name: str | None = None
    unmaterialized_entities: list[str] = []
    errors: list[str] = []
    requires_cascade: bool = False
    affected_entities: list[str] = []


class CanMaterializeResponse(BaseModel):
    """Response for can-materialize check."""

    can_materialize: bool
    errors: list[str] = []
