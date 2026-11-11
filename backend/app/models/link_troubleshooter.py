"""API models for the foreign-key link troubleshooter."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.validation import ValidationError

SettingSource = Literal["inherited", "explicit"]

ExceptionGroupName = Literal["unmatched", "multiply_matched"]
"""The two affected-row categories the troubleshooter can browse."""

ExceptionRowSide = Literal["baseline", "trial"]
"""Which retained result set the browse request addresses."""

EXCEPTION_ROW_PAGE_SIZE: int = 100
"""Rows returned by one exception-row page request."""

EXCEPTION_ROW_PAGE_LIMIT: int = 25_000
"""Largest page a caller may request for exception rows.

This matches the affected-row browse cap, so one request can ask for every
retained row of a group.
"""


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


class LinkTroubleshootJoinTypeSetting(BaseModel):
    """Requested, sourced, and effective join type."""

    requested: Literal["inner", "left"] | None = None
    source: SettingSource
    effective: Literal["inner", "left"]


class LinkTroubleshootRequestedSetting(BaseModel):
    """One requested null-key control and whether it was explicit or inherited."""

    requested: bool | None = None
    source: SettingSource


class LinkTroubleshootResolvedNullPolicy(BaseModel):
    """The production-resolved null-key pair for one link."""

    enforce_strict_null_keys: bool
    prevent_null_key_matches: bool


class LinkTroubleshootTrialSettings(BaseModel):
    """Requested and resolved settings for the baseline or one trial."""

    join_type: LinkTroubleshootJoinTypeSetting
    allow_null_keys: LinkTroubleshootRequestedSetting
    null_keys_equal: LinkTroubleshootRequestedSetting
    resolved_null_policy: LinkTroubleshootResolvedNullPolicy


class LinkTroubleshootKeyValue(BaseModel):
    """One exception key value with its truncation state."""

    value: Any
    truncated: bool = False
    original_length: int | None = None


class LinkTroubleshootExceptionRow(BaseModel):
    """One bounded exception A row."""

    input_position: int
    key_values: list[LinkTroubleshootKeyValue]
    remote_match_count: int
    output_row_contribution: int


class LinkTroubleshootExceptionGroup(BaseModel):
    """One exception group with its full count and the first browse page.

    ``rows`` holds only the first page. ``total_count`` and ``row_cap`` keep
    the full count and the browse cap, so a caller can page the remaining rows
    through the exception-row route without losing the result size.
    """

    total_count: int
    returned_count: int
    row_cap: int
    row_cap_reached: bool
    budget_exhausted: bool
    rows: list[LinkTroubleshootExceptionRow] = Field(default_factory=list)


class LinkTroubleshootFindings(BaseModel):
    """Bounded link findings with their full count."""

    total_count: int
    returned_count: int
    truncated: bool
    issues: list[ValidationError] = Field(default_factory=list)


class LinkTroubleshootDetail(BaseModel):
    """Bounded findings and exception groups for one side of a comparison."""

    detail_truncated: bool
    findings: LinkTroubleshootFindings
    unmatched: LinkTroubleshootExceptionGroup | None = None
    multiply_matched: LinkTroubleshootExceptionGroup | None = None


class LinkTroubleshootBaseline(BaseModel):
    """Saved-link counts, diagnostics, settings, and bounded detail."""

    input_a_rows: int | None = None
    output_rows: int | None = None
    unmatched_a_rows: int | None = None
    multiply_matched_a_rows: int | None = None
    diagnostic_status: Literal["complete", "failed", "incomplete", "not_run"]
    diagnostic_reason: str | None = None
    diagnostic_message: str | None = None
    issues: list[ValidationError] = Field(default_factory=list)
    settings: LinkTroubleshootTrialSettings | None = None
    detail: LinkTroubleshootDetail | None = None


class LinkExperimentContextRequest(BaseModel):
    """Retain the inputs behind one reproduced linking warning.

    Unknown fields are rejected so a caller that still sends stateless paging
    fields learns that the request shape changed instead of silently ignoring
    them.
    """

    model_config = ConfigDict(extra="forbid")

    issue_type: str
    local_entity: str
    metadata: dict[str, Any]


class LinkExperimentContextResponse(BaseModel):
    """Identity and baseline state of one retained snapshot.

    ``context_id`` is ``None`` when the warning did not reproduce, so no snapshot
    was retained. ``expires_at`` is the fixed end of the snapshot lifetime.
    """

    context_id: str | None = None
    status: Literal["reproduced", "not_reproduced", "ineligible"]
    reason: str
    message: str
    expires_at: datetime | None = None
    relationship: LinkTroubleshootRelationship | None = None
    key_options: LinkTroubleshootKeyOptions | None = None
    configured_keys: LinkTroubleshootKeys | None = None
    baseline: LinkTroubleshootBaseline | None = None


class LinkExperimentTrialRequest(BaseModel):
    """Trial controls for one retained snapshot.

    Every field is required except the three controls. An omitted control
    inherits the saved foreign key; an explicit value overrides it.
    """

    model_config = ConfigDict(extra="forbid")

    local_keys: list[str]
    remote_keys: list[str]
    how: Literal["inner", "left"] | None = None
    allow_null_keys: bool | None = None
    null_keys_equal: bool | None = None


class LinkTroubleshootComparison(BaseModel):
    """One trial's status, settings, totals, and bounded detail."""

    status: Literal["complete", "failed", "incomplete"]
    reason: str
    message: str
    settings: LinkTroubleshootTrialSettings | None = None
    totals: LinkTroubleshootTotals | None = None
    detail: LinkTroubleshootDetail | None = None


class LinkExperimentTrialResponse(BaseModel):
    """Retained baseline and one requested trial for the same snapshot."""

    context_id: str
    expires_at: datetime
    local_keys: list[str]
    remote_keys: list[str]
    baseline: LinkTroubleshootBaseline | None = None
    trial: LinkTroubleshootComparison


class LinkExceptionRowsRequest(BaseModel):
    """Request one bounded page of affected source rows.

    A ``trial`` request is required when ``side`` is ``trial`` because trial
    rows are not retained; they are recomputed from the retained inputs with
    the same controls as the accepted trial.
    """

    model_config = ConfigDict(extra="forbid")

    side: ExceptionRowSide = "baseline"
    group: ExceptionGroupName = "unmatched"
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=EXCEPTION_ROW_PAGE_SIZE, ge=1, le=EXCEPTION_ROW_PAGE_LIMIT)
    trial: LinkExperimentTrialRequest | None = None


class LinkExceptionRowsPage(BaseModel):
    """One bounded page of affected source rows for one result set."""

    status: Literal["available", "unavailable"]
    reason: str | None = None
    message: str | None = None
    side: ExceptionRowSide
    group: ExceptionGroupName
    offset: int
    limit: int
    total_count: int = 0
    browse_cap: int = 0
    browse_cap_reached: bool = False
    returned_count: int = 0
    rows: list[LinkTroubleshootExceptionRow] = Field(default_factory=list)
