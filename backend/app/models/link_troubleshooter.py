"""API models for the foreign-key link troubleshooter."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.models.validation import ValidationError

LinkTroubleshootRowFilter = Literal["all", "unmatched", "multiply_matched"]


class LinkTroubleshootRequest(BaseModel):
    """Request a baseline comparison or a trial with selected key pairs."""

    issue_type: str
    local_entity: str
    metadata: dict[str, Any]
    local_keys: list[str] | None = None
    remote_keys: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    row_filter: LinkTroubleshootRowFilter = "all"


class LinkTroubleshootKeys(BaseModel):
    """Ordered local and remote trial keys."""

    local_keys: list[str]
    remote_keys: list[str]


class LinkTroubleshootRelationship(BaseModel):
    """Saved relationship details shown as read-only values."""

    local_entity: str
    remote_entity: str | None = None
    fk_index: int | None = None
    join_type: str | None = None
    link_pass: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class LinkTroubleshootKeyOptions(BaseModel):
    """Columns available for trial key selection."""

    local: list[str]
    remote: list[str]


class LinkTroubleshootTotals(BaseModel):
    """Complete totals for one saved-key or requested-key trial."""

    input_a_rows: int
    output_rows: int
    unmatched_a_rows: int
    multiply_matched_a_rows: int


class LinkTroubleshootBaseline(BaseModel):
    """Saved-link counts and diagnostics from the configured-key trial."""

    input_a_rows: int | None = None
    output_rows: int | None = None
    unmatched_a_rows: int | None = None
    multiply_matched_a_rows: int | None = None
    diagnostic_status: Literal["complete", "failed", "incomplete", "not_run"]
    diagnostic_reason: str | None = None
    diagnostic_message: str | None = None
    issues: list[ValidationError] = Field(default_factory=list)


class LinkTroubleshootRow(BaseModel):
    """One bounded A-row diagnostic."""

    input_position: int
    key_values: list[Any]
    matched: bool
    remote_match_count: int
    output_row_contribution: int


class LinkTroubleshootPagination(BaseModel):
    """Counts for the filtered page of A-row diagnostics."""

    page: int
    page_size: int
    filtered_row_count: int
    returned_row_count: int
    has_next: bool


class LinkTroubleshootTrial(BaseModel):
    """Requested trial status, totals, findings, and bounded rows."""

    status: Literal["complete", "failed", "incomplete"]
    reason: str
    message: str
    local_keys: list[str]
    remote_keys: list[str]
    totals: LinkTroubleshootTotals | None = None
    issues: list[ValidationError] = Field(default_factory=list)
    rows: list[LinkTroubleshootRow] = Field(default_factory=list)
    pagination: LinkTroubleshootPagination | None = None


class LinkTroubleshootResponse(BaseModel):
    """Baseline and requested-trial results for one saved foreign key."""

    status: Literal["reproduced", "not_reproduced", "ineligible"]
    reason: str
    message: str
    relationship: LinkTroubleshootRelationship | None = None
    key_options: LinkTroubleshootKeyOptions | None = None
    configured_keys: LinkTroubleshootKeys | None = None
    baseline: LinkTroubleshootBaseline | None = None
    trial: LinkTroubleshootTrial | None = None
