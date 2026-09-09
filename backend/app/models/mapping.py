"""API models for mapping sidecar CRUD endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class MappingLinkUpsertRequest(BaseModel):
    """Request body for creating or updating a manual mapping link."""

    target_id: int = Field(..., description="Resolved public_id value to assign to this local key.")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Optional confidence score for the manual link.")
    notes: str | None = Field(default=None, description="Optional notes stored with the mapping link.")


class MappingLinkResponse(BaseModel):
    """API representation of a single mapping link."""

    target_id: int | None = None
    source: str
    confidence: float | None = None
    created_at: datetime
    committed_at: datetime | None = None
    notes: str | None = None
    created_by: str
    reviewed_by: str | None = None


class MappingEntityResponse(BaseModel):
    """API response for all mapping links and metadata for one entity."""

    entity_name: str
    local_key: str | list[str]
    public_id: str
    entity_type: str
    description: str | None = None
    links: dict[str, MappingLinkResponse] = Field(default_factory=dict)


class MappingLinkRecordResponse(BaseModel):
    """API response for a single mapping link lookup."""

    entity_name: str
    local_key_value: str
    local_key: str | list[str]
    public_id: str
    link: MappingLinkResponse


class MappingDeleteResponse(BaseModel):
    """API response for deleting a mapping link."""

    entity_name: str
    local_key_value: str
    deleted: bool
