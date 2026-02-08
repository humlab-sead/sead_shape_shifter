"""Reconciliation models for entity matching against SEAD database."""

from typing import Any

from pydantic import BaseModel, Field


class ReconciliationSource(BaseModel):
    """Custom data source for entity resolution (alternative to entity preview data)."""

    data_source: str = Field(..., description="Data source name from main config")
    type: str = Field("sql", description="Query type (currently only 'sql' supported)")
    query: str = Field(..., description="SQL query to fetch reconciliation data")


class ReconciliationRemote(BaseModel):
    """Specification for target system for entity resolution."""

    service_type: str | None = Field(
        None, description="Entity resolution service entity type (e.g., 'Site', 'Taxon'). If None, entity resolution is disabled."
    )
    columns: list[str] = Field(default_factory=list, description="Additional columns for display/matching")


class ResolvedEntityPair(BaseModel):
    """Single entity resolution entry linking source identity to target identity."""

    source_value: Any = Field(..., description="Source field value")
    target_id: int | None = Field(None, description="Target entity ID (None if unmatched)")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Mapping confidence (0-1)")
    notes: str | None = Field(None, description="Manual notes or auto-match info")
    will_not_match: bool = Field(False, description="User marked as will not match (local-only identifier)")
    created_at: str | None = Field(None, description="ISO timestamp")
    created_by: str | None = Field(None, description="User who created mapping")
    last_modified: str | None = Field(None, description="Last modification timestamp")


class EntityResolutionSet(BaseModel):
    """Entity resolution specification and mappings for a single target field within a project.
    - `source` is the data used for entity resolution (either entity preview or custom query),
    - `property_mappings` define how to map remote (OpenRefine) service properties to columns in `source`
    - `remote` specifies the OpenRefine entity type and additional columns, and mapping contains the individual resolved items.
    """

    source: str | ReconciliationSource | None = Field(
        None, description="Data source: None (entity preview), entity name (string), or custom query (ReconciliationSource)"
    )
    property_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Service property ID -> source column name mapping (e.g., {'latitude': 'lat', 'longitude': 'lon'})",
    )
    remote: ReconciliationRemote = Field(..., description="Remote OpenRefine entity specification")
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
    mapping: list[ResolvedEntityPair] = Field(default_factory=list, description="Manual and auto-generated mappings")


class EntityResolutionCatalog(BaseModel):
    """Complete entity resolution catalog for all entities."""

    version: str = Field("2.0", description="Reconciliation format version")
    service_url: str = Field(..., description="Base URL of OpenRefine reconciliation service")
    entities: dict[str, dict[str, EntityResolutionSet]] = Field(
        default_factory=dict, description="Entity name -> target field -> mapping spec"
    )


class EntityResolutionListItem(BaseModel):
    """Flattened specification for list view."""

    entity_name: str = Field(..., description="Entity name")
    target_field: str = Field(..., description="Target field name")
    source: str | ReconciliationSource | None = Field(None, description="Data source specification")
    property_mappings: dict[str, str] = Field(default_factory=dict, description="Property mappings")
    remote: ReconciliationRemote = Field(..., description="Remote entity configuration")
    auto_accept_threshold: float = Field(..., description="Auto-accept threshold")
    review_threshold: float = Field(..., description="Review threshold")
    mapping_count: int = Field(..., description="Number of mappings")
    property_mapping_count: int = Field(..., description="Number of property mappings")


class EntityResolutionCatalogCreateRequest(BaseModel):
    """Request to create new resolution catalog entry."""

    entity_name: str = Field(..., description="Entity name (must exist in project)")
    target_field: str = Field(..., description="Target field name")
    spec: EntityResolutionSet = Field(..., description="Entity resolution specification")


class EntityResolutionCatalogUpdateRequest(BaseModel):
    """Request to update resolution catalog entry (excludes entity/target/mapping)."""

    source: str | ReconciliationSource | None = Field(None, description="Data source specification")
    property_mappings: dict[str, str] = Field(default_factory=dict, description="Property mappings")
    remote: ReconciliationRemote = Field(..., description="Remote entity configuration")
    auto_accept_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Auto-accept threshold")
    review_threshold: float = Field(0.70, ge=0.0, le=1.0, description="Review threshold")


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
    target_id: int | None = None
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
