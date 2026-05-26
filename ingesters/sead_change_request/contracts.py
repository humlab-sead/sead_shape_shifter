"""Internal data structures for the SEAD change request ingester.

These types describe the data shapes used inside this package. The public
ingester protocol still accepts source files and config values, and the code
converts those inputs into this DataFrame-based workflow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import re
from typing import Any

import pandas as pd


APPROVED_DATATYPES: frozenset[str] = frozenset(
    {
        "mal",
        "archaeobotany",
        "dendrochronology",
        "adna",
        "bugs",
        "isotope",
        "ceramics",
        "radiocarbon",
    }
)


class ChangeRowState(StrEnum):
    """Resolved row states used when building a change request."""

    EXISTING_ENTITY = "existing_entity"
    NEWLY_ALLOCATED_ENTITY = "newly_allocated_entity"
    RECONCILED_CLASSIFIER = "reconciled_classifier"
    DERIVED_BRIDGE_ROW = "derived_bridge_row"
    BLOCKED_UNRESOLVED = "blocked_unresolved"


class PlannedRowAction(StrEnum):
    """Planned row actions before identity work is carried out."""

    REFERENCE_EXISTING = "reference_existing"
    ALLOCATE = "allocate"
    RECONCILE = "reconcile"
    EVALUATE_BRIDGE = "evaluate_bridge"


@dataclass(slots=True)
class SourceTableBundle:
    """Normalized table bundle handed to the ingester core."""

    tables: dict[str, pd.DataFrame]
    source_name: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SubmissionContext:
    """Submission metadata used to build change-package output."""

    submission_name: str
    project_name: str
    timestamp: datetime
    binding_set_uuid: str | None = None
    change_request_name: str | None = None
    datatype: str | None = None
    identifier: str | None = None
    description: str | None = None
    issue_number: str | None = None
    author: str | None = None


@dataclass(slots=True)
class PlannedTable:
    """Per-table work plan derived from the target model."""

    entity_name: str
    frame: pd.DataFrame
    planned_actions: pd.Series
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IdentityWorkPlan:
    """Groups of planned rows organized by the identity work they need."""

    existing_rows: dict[str, pd.DataFrame] = field(default_factory=dict)
    allocation_rows: dict[str, pd.DataFrame] = field(default_factory=dict)
    reconciliation_rows: dict[str, pd.DataFrame] = field(default_factory=dict)
    bridge_rows: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def total_existing_rows(self) -> int:
        return sum(len(frame.index) for frame in self.existing_rows.values())

    @property
    def total_allocation_rows(self) -> int:
        return sum(len(frame.index) for frame in self.allocation_rows.values())

    @property
    def total_reconciliation_rows(self) -> int:
        return sum(len(frame.index) for frame in self.reconciliation_rows.values())

    @property
    def total_bridge_rows(self) -> int:
        return sum(len(frame.index) for frame in self.bridge_rows.values())


@dataclass(slots=True)
class IdentityAssignment:
    """Resolved identity decision for a single planned row."""

    state: ChangeRowState
    target_id: int | None = None
    note: str | None = None


@dataclass(slots=True)
class ResolvedIdentityTable:
    """Per-table resolved identity state after orchestration."""

    entity_name: str
    frame: pd.DataFrame
    row_states: pd.Series
    resolved_target_ids: pd.Series
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IdentityResolutionResult:
    """Resolved identity state across all planned tables."""

    tables: dict[str, ResolvedIdentityTable] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    @property
    def blocked_rows(self) -> int:
        return sum(int((table.row_states == ChangeRowState.BLOCKED_UNRESOLVED).sum()) for table in self.tables.values())


@dataclass(slots=True)
class MaterializedTable:
    """Output-ready table with target-facing PK/FK values materialized."""

    entity_name: str
    frame: pd.DataFrame
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MaterializationResult:
    """Materialized target-facing tables and diagnostics."""

    tables: dict[str, MaterializedTable] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PendingConfirmationReport:
    """Operator-facing report for blocked Binding Set confirmation."""

    submission_name: str
    project_name: str
    binding_set_uuid: str | None
    binding_set_state: str | None
    blocked_entities: list[str] = field(default_factory=list)
    blocked_rows: int = 0
    outstanding_step: str = ""
    operator_action: str = ""
    rerun_instruction: str = ""


@dataclass(slots=True)
class ChangeRequestTable:
    """Prepared table plus per-row state annotations."""

    name: str
    frame: pd.DataFrame
    row_states: pd.Series


@dataclass(slots=True)
class ChangeRequestPackage:
    """Generated change-request payload before artifact rendering."""

    tables: dict[str, ChangeRequestTable] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DeployArtifact:
    """In-memory deploy artifact plus its metadata."""

    deploy_sql: str
    statements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    revert_placeholder_sql: str = ""
    verify_placeholder_sql: str = ""
    metadata_artifact: dict[str, Any] = field(default_factory=dict)
    bundle_files: dict[str, str] = field(default_factory=dict)


def normalize_submission_identifier(identifier: str) -> str:
    """Normalize the change-request identifier for bundle naming."""
    return identifier.strip().upper()


def is_valid_submission_identifier(identifier: str) -> bool:
    """Return whether an identifier matches the bundle naming rules."""
    return bool(re.fullmatch(r"[A-Z0-9_]+", identifier)) and len(identifier) < 40


def resolve_bundle_name(submission_context: SubmissionContext) -> str:
    """Build the standard bundle name for a submission."""
    date_component = submission_context.timestamp.strftime("%Y%m%d")
    datatype_component = (submission_context.datatype or submission_context.project_name).strip()
    identifier_component = normalize_submission_identifier(submission_context.identifier or submission_context.submission_name)
    return f"{date_component}_DML_{datatype_component}_{identifier_component}"
