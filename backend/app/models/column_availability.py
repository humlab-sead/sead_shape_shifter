"""Request and response models for operation-aware column candidates."""

from typing import Any

from pydantic import BaseModel, Field


class ColumnAvailabilityRequest(BaseModel):
    """Entity draft and optional known source columns for candidate resolution."""

    entity_draft: dict[str, Any]
    source_columns: list[str] | None = None


class ForeignKeyColumnCandidates(BaseModel):
    """Column candidates for one configured foreign key."""

    index: int = 0
    entity: str = ""
    local_keys_before_unnest: list[str] = Field(default_factory=list)
    local_keys_after_unnest: list[str] = Field(default_factory=list)
    remote_keys: list[str] = Field(default_factory=list)
    extra_column_sources: list[str] = Field(default_factory=list)


class ExtraColumnCandidates(BaseModel):
    """Available source columns for extra-column expressions."""

    sources: list[str] = Field(default_factory=list)


class UnnestColumnCandidates(BaseModel):
    """Current candidates for unnest identifier and value columns."""

    id_vars: list[str] = Field(default_factory=list)
    value_vars: list[str] = Field(default_factory=list)


class ColumnAvailabilityResponse(BaseModel):
    """Operation-specific and stage-specific column candidates."""

    columns: list[str] = Field(default_factory=list)
    business_keys: list[str] = Field(default_factory=list)
    replacements: list[str] = Field(default_factory=list)
    drop_duplicates: list[str] = Field(default_factory=list)
    drop_empty_rows: list[str] = Field(default_factory=list)
    extra_columns: ExtraColumnCandidates = Field(default_factory=ExtraColumnCandidates)
    filters: dict[str, list[str]] = Field(default_factory=dict)
    foreign_keys: list[ForeignKeyColumnCandidates] = Field(default_factory=list)
    unnest: UnnestColumnCandidates = Field(default_factory=UnnestColumnCandidates)
