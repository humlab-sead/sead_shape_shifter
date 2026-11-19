"""API models for mapping sidecar CRUD endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class MappingLinkUpsertRequest(BaseModel):
    """Request body for creating or updating a manual mapping link."""

    target_id: int = Field(..., gt=0, description="Resolved public_id value to assign to this local key.")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Optional confidence score for the manual link.")
    notes: str | None = Field(default=None, description="Optional notes stored with the mapping link.")


class MappingLinkOwner(BaseModel):
    """Specification that owns a reconciliation mapping link."""

    entity_name: str
    target_field: str


class MappingLinkResponse(BaseModel):
    """API representation of a single mapping link."""

    target_id: int | None = None
    source: str
    confidence: float | None = None
    created_at: datetime
    committed_at: datetime | None = None
    owner: MappingLinkOwner | None = None
    verified_at: datetime | None = None
    notes: str | None = None
    created_by: str
    reviewed_by: str | None = None
    protected: bool | None = None


class MappingLocalOnlyApprovalResponse(BaseModel):
    """API representation of an approval to allocate a target ID for a local row."""

    owner: MappingLinkOwner
    committed_at: datetime | None = None
    protected: bool | None = None


class MappingEntityResponse(BaseModel):
    """API response for all mapping links and metadata for one entity."""

    entity_name: str
    local_key: str | list[str]
    public_id: str
    entity_type: str
    description: str | None = None
    links: dict[str, MappingLinkResponse] = Field(default_factory=dict)
    local_only_approvals: dict[str, MappingLocalOnlyApprovalResponse] = Field(default_factory=dict)
    protection_target_field: str | None = None


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


class MappingEntryDeleteResponse(BaseModel):
    """API response for deleting mapping entries for one local key."""

    entity_name: str
    local_key_value: str
    deleted_link: bool
    deleted_local_only_approval: bool
