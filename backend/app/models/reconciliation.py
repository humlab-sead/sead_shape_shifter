"""Reconciliation models for entity matching against SEAD database."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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

    local_key_value: str = Field(..., min_length=1, description="Encoded ordered business key")
    source_value: Any = Field(..., description="Search label (not row identity)")
    status: Literal["proposed", "accepted", "rejected", "local-only"] = "proposed"
    target_id: int | None = Field(default=None, description="Selected target ID for an accepted decision")
    candidate_id: str | None = Field(default=None, description="Exact selected candidate URI")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Mapping confidence (0-1)")
    notes: str | None = Field(default=None, description="Operator notes")
    candidates: list["ReconciliationCandidate"] = Field(default_factory=list)
    created_at: str | None = Field(default=None, description="ISO timestamp")
    created_by: str | None = Field(default=None, description="User who created mapping")
    last_modified: str | None = Field(default=None, description="Last modification timestamp")

    # This model also reads legacy version 3.0 catalogs, so it deliberately does not
    # enforce the accepted/target/candidate relationship on load. Write paths run the
    # shared reference validator before saving a decision.


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
        description="Legacy score threshold (retained for compatibility; matching never auto-accepts)",
    )
    review_threshold: float = Field(
        0.70,
        ge=0.0,
        le=1.0,
        description="Score threshold for flagging review needed (default 70%)",
    )
    mapping: list[ResolvedEntityPair] = Field(default_factory=list, description="Manual and auto-generated mappings")

    @model_validator(mode="after")
    def validate_unique_keys(self) -> "EntityResolutionSet":
        keys = [decision.local_key_value for decision in self.mapping]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate reconciliation decision local_key_value")
        return self


class EntityResolutionCatalog(BaseModel):
    """Complete entity resolution catalog for all entities."""

    version: str = Field("3.0", description="Reconciliation format version")
    service_url: str = Field(..., description="Base URL of OpenRefine reconciliation service")
    entities: dict[str, dict[str, EntityResolutionSet]] = Field(
        default_factory=dict, description="Entity name -> target field -> mapping spec"
    )


class EntityResolutionCatalogDeleteResult(EntityResolutionCatalog):
    """Updated reconciliation catalog and counts of removed owned sidecar entries."""

    removed_owned_links: int = Field(..., ge=0, description="Count of owned mapping links removed with the specification.")
    removed_owned_approvals: int = Field(0, ge=0, description="Count of owned local-only approvals removed with the specification.")


class EntityResolutionListItem(BaseModel):
    """Flattened specification for list view."""

    entity_name: str = Field(..., description="Entity name")
    has_business_keys: bool = Field(..., description="Whether the entity has at least one configured business key")
    target_field: str = Field(..., description="Target field name")
    source: str | ReconciliationSource | None = Field(default=None, description="Data source specification")
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

    source: str | ReconciliationSource | None = Field(default=None, description="Data source specification")
    property_mappings: dict[str, str] = Field(default_factory=dict, description="Property mappings")
    remote: ReconciliationRemote = Field(..., description="Remote entity configuration")
    auto_accept_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Auto-accept threshold")
    review_threshold: float = Field(0.70, ge=0.0, le=1.0, description="Review threshold")


# OpenRefine API response models


class ReconciliationCandidate(BaseModel):
    """Candidate entity returned by reconciliation service."""

    id: str = Field(..., description="Unique identifier URI")
    name: str = Field(..., description="Display name")
    score: float | None = Field(default=None, description="Match confidence score (0-100)")
    match: bool | None = Field(default=None, description="High-confidence match flag")
    type: list[dict[str, str]] = Field(default_factory=list, description="Entity type info")
    distance_km: float | None = Field(default=None, description="Geographic distance (for sites)")
    description: str | None = Field(default=None, description="Additional context")


class ReconciliationPreviewRow(BaseModel):
    """Preview row combining local data with reconciliation status."""

    # Dynamic fields for keys and columns
    # Plus reconciliation status fields
    target_id: int | None = None
    confidence: float | None = None
    notes: str | None = None
    candidates: list[ReconciliationCandidate] | None = None
    match_status: str | None = None


class AutoReconcileResult(BaseModel):
    """Results for all normalized rows considered by a matching operation."""

    proposed: int = Field(..., description="Count of proposed decisions updated")
    unmatched: int = Field(..., description="Count of keyed rows without candidates")
    total: int = Field(..., description="Total normalized rows considered")
    candidates: dict[str, list[ReconciliationCandidate]] = Field(default_factory=dict, description="Encoded key -> candidates")
    errors: list["ReconciliationRowError"] = Field(default_factory=list)


class ReconciliationRowError(BaseModel):
    """One row that cannot be safely reconciled."""

    row_index: int
    local_key_value: str | None = None
    message: str


class DecisionUpdateRequest(BaseModel):
    """Operator action addressed by the encoded business key."""

    local_key_value: str = Field(..., min_length=1)
    status: Literal["accepted", "rejected", "local-only"]
    target_id: int | None = None
    candidate_id: str | None = Field(default=None)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "DecisionUpdateRequest":
        if (self.status == "accepted") != (self.target_id is not None):
            raise ValueError("Only accepted decisions may specify a target_id, and accepted decisions require one")
        if self.status == "accepted" and (self.candidate_id is None or not self.candidate_id.strip()):  # pylint: disable=no-member
            raise ValueError("An accepted decision requires a non-empty candidate_id")
        if self.status != "accepted" and self.candidate_id is not None:
            raise ValueError("Only accepted decisions may specify a candidate_id")
        return self


class CandidateVerificationRequestItem(BaseModel):
    """One exact candidate URI sent to the Authority Service."""

    type: str = Field(..., min_length=1)
    id: str = Field(..., min_length=1)


class CandidateVerificationResult(BaseModel):
    """Authority Service result for one candidate URI."""

    type: str
    id: str
    outcome: Literal["exists", "not_found", "invalid_candidate", "unsupported_type"]
    entity_type: str | None = None
    aggregate_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_aggregate_id(self) -> "CandidateVerificationResult":
        if (self.outcome == "exists") != (self.aggregate_id is not None):
            raise ValueError("Only an existing candidate may include an aggregate_id")
        return self


class CandidateVerificationResponse(BaseModel):
    """Ordered candidate-check results returned by the Authority Service."""

    results: list[CandidateVerificationResult]


class ExportToMappingOutcome(BaseModel):
    """Export result for one encoded business key."""

    local_key_value: str = Field(..., min_length=1)
    outcome: Literal["verified", "not_found", "invalid_candidate", "unverified"]
    reason: str | None = None


class ExportToMappingResult(BaseModel):
    """Result of exporting reconciliation links and local-only approvals into the mapping sidecar."""

    exported: int = Field(..., description="Count of reconciliation links written to the mapping sidecar.")
    removed: int = Field(..., description="Count of stale owned links removed from the mapping sidecar.")
    exported_local_only_approvals: int = Field(0, description="Count of local-only approvals written to the mapping sidecar.")
    removed_local_only_approvals: int = Field(0, description="Count of stale owned local-only approvals removed from the mapping sidecar.")
    skipped_manual: int = Field(..., description="Count of reconciliation links skipped because a manual mapping already exists.")
    entity: str = Field(..., description="Entity name whose links were exported.")
    field: str = Field(..., description="Reconciliation field used as the source key during export.")
    outcomes: list[ExportToMappingOutcome] = Field(default_factory=list, description="Verification outcome for each checked business key.")


class ReconciliationIssue(BaseModel):
    """One row-specific problem reported with a rejected reconciliation write."""

    row_index: int | None = Field(default=None, description="Server index in the resolved source rows")
    local_key_value: str | None = Field(default=None, description="Encoded business key of the affected row")
    field: str | None = Field(default=None, description="Column name when one column caused the issue")
    code: str = Field(..., min_length=1, description="Stable issue code")
    message: str = Field(..., min_length=1, description="Human-readable issue description")


class DecisionDraft(BaseModel):
    """One first-time or replacement decision submitted in a batch."""

    # The service validates the key so a malformed draft produces a row issue
    # instead of a request-model rejection.
    local_key_value: str = Field(..., description="Encoded ordered business key")
    displayed_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Columns the operator saw; used only for change detection and never written as source data",
    )
    status: Literal["accepted", "local-only"] = Field(..., description="Decision to store for this row")
    target_id: int | None = Field(default=None, description="Selected target ID for an accepted decision")
    candidate_id: str | None = Field(default=None, description="Exact selected candidate URI for an accepted decision")
    notes: str | None = Field(default=None, description="Operator notes")


class DecisionBatchRequest(BaseModel):
    """Batch of decisions saved in one catalog write."""

    drafts: list[DecisionDraft] = Field(default_factory=list, description="Decisions to store; each key appears at most once")


class SavedDecision(BaseModel):
    """One decision stored by a batch save, echoed in request order."""

    local_key_value: str = Field(..., min_length=1)
    status: Literal["accepted", "local-only"]
    target_id: int | None = None
    candidate_id: str | None = None
    notes: str | None = None
    last_modified: str | None = None


class SpecificationDecisionCounts(BaseModel):
    """Post-save decision totals for one reconciliation specification."""

    accepted: int = Field(..., ge=0)
    local_only: int = Field(..., ge=0)
    proposed: int = Field(..., ge=0)
    rejected: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class DecisionBatchCounts(BaseModel):
    """Counts for the stored batch and the resulting specification."""

    saved: int = Field(..., ge=0)
    accepted: int = Field(..., ge=0)
    local_only: int = Field(..., ge=0)
    specification: SpecificationDecisionCounts


class DecisionBatchResult(BaseModel):
    """Result of a batch decision save."""

    saved: list[SavedDecision] = Field(default_factory=list)
    counts: DecisionBatchCounts


# Record selection models: capabilities, ranked search, and complete browse lists.


class RecordDisplayFieldDescriptor(BaseModel):
    """One ordered display field advertised for a record-selection type."""

    name: str = Field(..., min_length=1)
    source: Literal["record", "fields"]
    label: str = Field(..., min_length=1)
    value_type: Literal["string", "integer", "number", "boolean"]
    display: bool


class RecordFieldFilterDescriptor(BaseModel):
    """One client-side field filter advertised for a record-selection type."""

    field: str = Field(..., min_length=1)
    operator: Literal["contains_ci", "equals"]


class RecordSelectionTypeCapabilities(BaseModel):
    """Capabilities, limits, and declared fields for one configured record type."""

    type: str = Field(..., min_length=1)
    search_supported: bool
    identifier_search_supported: bool
    browse_supported: bool
    details_supported: bool
    export_verification_supported: bool
    id_base: str | None = None
    id_path: str = Field(..., min_length=1)
    browse_max_rows: int | None = Field(default=None, gt=0)
    browse_max_bytes: int | None = Field(default=None, gt=0)
    interactive_search_max_results: int | None = Field(default=None, gt=0)
    display_fields: list[RecordDisplayFieldDescriptor] = Field(default_factory=list)
    text_filter_fields: list[str] = Field(default_factory=list)
    sort_fields: list[str] = Field(default_factory=list)
    field_filters: list[RecordFieldFilterDescriptor] = Field(default_factory=list)


class RecordSelectionCapabilities(BaseModel):
    """Versioned record-selection capabilities for the specification's own type."""

    version: int = Field(..., ge=1)
    type: RecordSelectionTypeCapabilities


class ReconciliationRecord(BaseModel):
    """One selectable target record shared by search and browse results."""

    id: str = Field(..., min_length=1, description="Complete reconciliation URI for the record")
    target_id: int | None = Field(default=None, gt=0, description="Positive numeric target ID when the service supplies one")
    type: str = Field(..., min_length=1, description="Record type the URI was validated against")
    name: str = Field(..., description="Record label; never used as an identifier")
    description: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict, description="Declared display fields")
    score: float | None = Field(
        default=None,
        description="Ranked search score in the OpenRefine 0-100 scale; browse records carry no score",
    )


class RecordSelectionSearchRequest(BaseModel):
    """Operator search text plus optional declared property context."""

    query: str = Field(..., description="Operator text, or 'id: <positive integer>' for an exact lookup")
    limit: int | None = Field(default=None, description="Requested result limit; capped by the advertised maximum")
    context: dict[str, str] = Field(default_factory=dict, description="Declared property IDs used as ranking hints")


class RecordSelectionSearchResult(BaseModel):
    """Ranked search results or the single record for an exact-ID lookup."""

    mode: Literal["ranked", "exact"]
    items: list[ReconciliationRecord] = Field(default_factory=list)


class RecordSelectionBrowseResult(BaseModel):
    """A verified complete record list for the configured type."""

    items: list[ReconciliationRecord] = Field(default_factory=list)
    completeness: Literal["complete"] = "complete"
