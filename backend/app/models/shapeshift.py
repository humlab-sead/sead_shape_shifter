"""Models for entity data preview functionality."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    """Request model for entity preview."""

    entity_name: str = Field(..., description="Name of the entity to preview")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum number of rows to preview")
    include_metadata: bool = Field(default=True, description="Include column metadata in response")


class ColumnInfo(BaseModel):
    """Information about a column in the preview."""

    name: str
    data_type: str
    nullable: bool = True
    is_key: bool = False  # True if part of keys or surrogate_id


class PreviewResult(BaseModel):
    """Result of an entity preview operation."""

    entity_name: str
    rows: list[dict[str, Any]]
    columns: list[ColumnInfo]
    total_rows_in_preview: int
    estimated_total_rows: Optional[int] = None  # Actual row count if available
    execution_time_ms: int
    has_dependencies: bool = False
    dependencies_loaded: list[str] = []
    cache_hit: bool = False
    row_count: int = 0


class EntityPreviewError(BaseModel):
    """Error information for preview failures."""

    entity_name: str
    error_type: str
    message: str
    details: Optional[dict[str, Any]] = None
