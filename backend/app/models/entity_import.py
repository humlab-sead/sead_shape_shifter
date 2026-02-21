"""
Models for entity import from database tables.
"""

from typing import Optional

from pydantic import BaseModel, Field


class EntityImportRequest(BaseModel):
    """Request to import an entity from a database table."""

    entity_name: Optional[str] = Field(None, description="Optional custom entity name (defaults to table name)")
    include_all_columns: bool = Field(True, description="Include all columns from the table")
    selected_columns: Optional[list[str]] = Field(None, description="Specific columns to include (if not include_all_columns)")


class KeySuggestion(BaseModel):
    """Suggested key column(s) for an entity."""

    columns: list[str] = Field(..., description="Column name(s)")
    reason: str = Field(..., description="Reason for suggestion")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)


class EntityImportResult(BaseModel):
    """Result of importing an entity from a database table."""

    entity_name: str = Field(..., description="Generated entity name")
    type: str = Field(..., description="Entity type (always 'sql')")
    data_source: str = Field(..., description="Data source name")
    query: str = Field(..., description="Generated SQL query")
    columns: list[str] = Field(..., description="Column names")
    public_id_suggestion: Optional[KeySuggestion] = Field(None, description="Suggested public ID column")
    natural_key_suggestions: list[KeySuggestion] = Field(default_factory=list, description="Suggested natural key columns")
    column_types: dict[str, str] = Field(default_factory=dict, description="Column names to data types")
