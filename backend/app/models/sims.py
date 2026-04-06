"""Pydantic models mirroring the SIMS (SEAD Identity Management System) API contracts.

These are client-side DTOs for communicating with the sead_authority_service /identity endpoints.
They mirror the models defined in sead_authority_service/src/identity/models.py and
sead_authority_service/src/api/identity_router.py.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class IdentityType(StrEnum):
    """How a Source Identity value was obtained from the provider."""

    UUID = "uuid"
    BUSINESS_KEY = "business_key"
    PROVIDER_KEY = "provider_key"
    AUTHORITY_KEY = "authority_key"


class BindingSetState(StrEnum):
    """Lifecycle state of a Binding Set."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class BindingMethod(StrEnum):
    """How a Binding was established between a Source Identity and a Tracked Identity."""

    EXACT_MATCH = "exact_match"
    BUSINESS_KEY = "business_key"
    UUID_ACCEPTED = "uuid_accepted"
    UUID_MAPPED = "uuid_mapped"
    MANUAL = "manual"
    ALLOCATED = "allocated"


class ChangeOutcome(StrEnum):
    """Result of a content-hash change detection comparison."""

    INSERT = "insert"
    UPDATE = "update"
    SKIP = "skip"


# ---------------------------------------------------------------------------
# Request models (sent to SIMS)
# ---------------------------------------------------------------------------


class IdentitySignal(BaseModel):
    """An identity signal submitted for resolution."""

    identity_type: IdentityType = Field(description="Key type discriminator driving lookup strategy.")
    identity_value: str = Field(description="Serialised key value, e.g. 'site_name=Nordic Site'.")
    signals: dict | None = Field(
        default=None,
        description="Additional evidence: authority keys, alternative identifiers.",
    )


class ResolutionRequest(BaseModel):
    """One domain entity submitted for identity resolution within a scope."""

    entity_type: str = Field(description="SEAD entity type, e.g. 'site', 'taxa_tree_master'.")
    primary_signal: IdentitySignal = Field(description="The main identity key used for idempotency lookup.")
    additional_signals: list[IdentitySignal] = Field(
        default_factory=list,
        description="Optional supplementary keys also stored alongside the primary signal.",
    )


class ResolveRequest(BaseModel):
    """Request body for POST /identity/resolve."""

    scope_name: str = Field(description="Source Scope name, e.g. 'sead://reconciliation' or a provider URI.")
    submission_name: str = Field(description="Human-readable name for this submission batch.")
    requests: list[ResolutionRequest] = Field(
        description="One entry per domain entity to resolve.",
        min_length=1,
    )
    created_by: str | None = Field(default=None, description="Agent or user identifier for audit trail.")


class ChangeDetectionRequest(BaseModel):
    """Request body for POST /identity/detect-change."""

    tracked_identity_uuid: UUID
    content_hash: str = Field(description="Deterministic aggregate content hash computed by the submitting system.")


# ---------------------------------------------------------------------------
# Response models (received from SIMS)
# ---------------------------------------------------------------------------


class SourceScope(BaseModel):
    """External namespace within which Source Identities are unique."""

    scope_uuid: UUID
    scope_name: str
    parent_scope_uuid: UUID | None = None
    description: str | None = None
    created_at: datetime
    created_by: str | None = None


class ResolutionOutcome(BaseModel):
    """Output of a single entity resolution within a POST /identity/resolve call."""

    source_identity_uuid: UUID
    entity_type: str
    outcome: str = Field(description="'matched' or 'new'")
    tracked_identity_uuid: UUID | None = None


class BindingSetResponse(BaseModel):
    """Represents a Binding Set and its current state."""

    binding_set_uuid: UUID
    submission_uuid: UUID | None = None
    lifecycle_state: BindingSetState
    change_request_name: str | None = None
    binding_count: int = Field(description="Number of source↔tracked Binding rows within this set.")
    created_at: datetime
    confirmed_at: datetime | None = None


class ResolveResponse(BaseModel):
    """Response body for POST /identity/resolve."""

    submission_uuid: UUID
    scope_uuid: UUID
    binding_set: BindingSetResponse
    outcomes: list[ResolutionOutcome]


class ChangeDetectionResult(BaseModel):
    """Output of POST /identity/detect-change."""

    tracked_identity_uuid: UUID
    outcome: ChangeOutcome
    previous_hash: str | None = Field(default=None, description="The previously stored hash, if any.")
