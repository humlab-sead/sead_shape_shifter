"""Reconciliation models for entity matching against SEAD database."""

from typing import Any

from pydantic import BaseModel, Field


class ReconciliationSource(BaseModel):
    """Custom data source for reconciliation (alternative to entity preview data)."""

    data_source: str = Field(..., description="Data source name from main config")
    type: str = Field("sql", description="Query type (currently only 'sql' supported)")
    query: str = Field(..., description="SQL query to fetch reconciliation data")


class ReconciliationRemote(BaseModel):
    """Remote SEAD entity specification for reconciliation."""

    data_source: str = Field(..., description="Data source name (e.g., 'sead')")
    entity: str = Field(..., description="Remote table name (e.g., 'tbl_sites')")
    key: str = Field(..., description="Remote key column (e.g., 'site_id')")
    service_type: str | None = Field(
        None, description="Reconciliation service entity type (e.g., 'Site', 'Taxon'). If None, reconciliation is disabled."
    )
    columns: list[str] = Field(default_factory=list, description="Additional columns for display/matching")


class ReconciliationMapping(BaseModel):
    """Single reconciliation mapping entry linking source keys to SEAD ID."""

    source_values: list[Any] = Field(..., description="Source key values")
    sead_id: int = Field(..., description="SEAD entity ID")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Mapping confidence (0-1)")
    notes: str | None = Field(None, description="Manual notes or auto-match info")
    created_at: str | None = Field(None, description="ISO timestamp")
    created_by: str | None = Field(None, description="User who created mapping")


class EntityReconciliationSpec(BaseModel):
    """Reconciliation specification for a single entity type."""

    source: str | ReconciliationSource | None = Field(
        None, description="Data source: None (entity preview), entity name (string), or custom query (ReconciliationSource)"
    )
    keys: list[str] = Field(..., description="Local key fields for matching")
    columns: list[str] = Field(default_factory=list, description="Additional columns for context/matching")
    property_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Service property ID -> source column name mapping (e.g., {'latitude': 'lat', 'longitude': 'lon'})",
    )
    remote: ReconciliationRemote = Field(..., description="Remote SEAD entity specification")
    auto_accept_threshold: float = Field(
        0.95,
        ge=0.0,
        le=1.0,
        description="Score threshold for auto-accepting matches (default 95%)",
    )
    review_threshold: float = Field(
        0.70,
        ge=0.0,
        le=1.0,
        description="Score threshold for flagging review needed (default 70%)",
    )
    mapping: list[ReconciliationMapping] = Field(default_factory=list, description="Manual and auto-generated mappings")


class ReconciliationConfig(BaseModel):
    """Complete reconciliation configuration for all entities."""

    service_url: str = Field(..., description="Base URL of OpenRefine reconciliation service")
    entities: dict[str, EntityReconciliationSpec] = Field(default_factory=dict, description="Entity name -> reconciliation spec")


# OpenRefine API response models


class ReconciliationCandidate(BaseModel):
    """Candidate entity returned by reconciliation service."""

    id: str = Field(..., description="Unique identifier URI")
    name: str = Field(..., description="Display name")
    score: float | None = Field(None, description="Match confidence score (0-100)")
    match: bool | None = Field(None, description="High-confidence match flag")
    type: list[dict[str, str]] = Field(default_factory=list, description="Entity type info")
    distance_km: float | None = Field(None, description="Geographic distance (for sites)")
    description: str | None = Field(None, description="Additional context")


class ReconciliationPreviewRow(BaseModel):
    """Preview row combining local data with reconciliation status."""

    # Dynamic fields for keys and columns
    # Plus reconciliation status fields
    sead_id: int | None = None
    confidence: float | None = None
    notes: str | None = None
    candidates: list[ReconciliationCandidate] | None = None
    match_status: str | None = None  # "auto-matched", "needs-review", "unmatched"


class AutoReconcileResult(BaseModel):
    """Result of auto-reconciliation operation."""

    auto_accepted: int = Field(..., description="Count of auto-accepted matches")
    needs_review: int = Field(..., description="Count of uncertain matches")
    unmatched: int = Field(..., description="Count with no good matches")
    total: int = Field(..., description="Total entities processed")
    candidates: dict[str, list[ReconciliationCandidate]] = Field(default_factory=dict, description="Source key -> candidates mapping")
