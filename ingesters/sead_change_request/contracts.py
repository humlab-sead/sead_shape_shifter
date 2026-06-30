"""Internal data structures for the SEAD change request ingester.

These types describe the data shapes used inside this package. The public
ingester protocol still accepts source files and config values, and the code
converts those inputs into this DataFrame-based workflow.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
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


class LifecycleVersionState(StrEnum):
    """Lifecycle states for versioned logical records."""

    LIVE = "live"
    SUPERSEDED = "superseded"
    PENDING_REVIEW = "pending_review"
    BLOCKED = "blocked"


class SubmissionOutcome(StrEnum):
    """Outcome classes used by phase-2 submission planning."""

    NEW_DATA = "new_data"
    NO_OP = "no_op"
    ALLOWED_UPDATE = "allowed_update"
    PENDING_REVIEW = "pending_review"
    BLOCKED = "blocked"


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
class LogicalRecordVersion:
    """Version metadata for one logical record entry."""

    logical_record_key: str
    version_key: str
    lifecycle_state: LifecycleVersionState
    supersedes_version_key: str | None = None
    submitted_at: datetime | None = None


@dataclass(slots=True)
class SubmissionOutcomeSummary:
    """Row-count summary for phase-2 outcome classification."""

    new_data_rows: int = 0
    no_op_rows: int = 0
    allowed_update_rows: int = 0
    pending_review_rows: int = 0
    blocked_rows: int = 0
    diagnostics: list[str] = field(default_factory=list)


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
class ProjectedTable:
    """Output-ready table with target-facing PK/FK values projected."""

    entity_name: str
    frame: pd.DataFrame
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TargetProjectionResult:
    """Projected target-facing tables and diagnostics."""

    tables: dict[str, ProjectedTable] = field(default_factory=dict)
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

    @staticmethod
    def create(
        submission_context: SubmissionContext, identity_result: IdentityResolutionResult, *, binding_set_state: str | None
    ) -> "PendingConfirmationReport":
        """Build the pending-confirmation report for operator action."""
        blocked_entities: list[str] = []
        blocked_rows: int = 0

        for entity_name, resolved_table in identity_result.tables.items():
            entity_blocked_rows: int = int((resolved_table.row_states == ChangeRowState.BLOCKED_UNRESOLVED).sum())
            if not entity_blocked_rows:
                continue
            blocked_entities.append(entity_name)
            blocked_rows += entity_blocked_rows

        return PendingConfirmationReport(
            submission_name=submission_context.submission_name,
            project_name=submission_context.project_name,
            binding_set_uuid=submission_context.binding_set_uuid,
            binding_set_state=binding_set_state,
            blocked_entities=blocked_entities,
            blocked_rows=blocked_rows,
            outstanding_step="Confirm the Binding Set before change-package generation can continue",
            operator_action="Confirm the Binding Set in SIMS, then rerun the ingester with the same submission context",
            rerun_instruction=(
                f"Rerun submission '{submission_context.submission_name}' for project '{submission_context.project_name}' "
                "after the Binding Set is confirmed"
            ),
        )


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
    revert_sql: str = ""
    verify_sql: str = ""
    metadata_artifact: dict[str, Any] = field(default_factory=dict)
    bundle_files: dict[str, str] = field(default_factory=dict)


def validate_one_live_version(records: list[LogicalRecordVersion]) -> list[str]:
    """Return invariant violations when a logical record has multiple live versions."""
    live_counts: dict[str, int] = {}
    violations: list[str] = []

    for record in records:
        if record.lifecycle_state != LifecycleVersionState.LIVE:
            continue
        live_counts[record.logical_record_key] = live_counts.get(record.logical_record_key, 0) + 1

    for logical_record_key, count in live_counts.items():
        if count <= 1:
            continue
        violations.append(f"Logical record '{logical_record_key}' has {count} live versions; expected at most one live version")

    return violations


def classify_submission_outcomes(
    planned_tables: list[PlannedTable],
    identity_result: IdentityResolutionResult,
    *,
    has_pending_review: bool,
) -> SubmissionOutcomeSummary:
    """Classify rows into phase-2 outcomes and return a summary."""
    reference_existing_rows = 0
    no_op_rows = 0
    compared_reference_rows = 0

    for planned_table in planned_tables:
        reference_mask = planned_table.planned_actions == PlannedRowAction.REFERENCE_EXISTING
        reference_existing_rows += int(reference_mask.sum())

        baseline_pairs = _baseline_column_pairs(planned_table.frame)
        if not baseline_pairs:
            continue

        for row_key in planned_table.frame.index[reference_mask]:
            compared_reference_rows += 1
            if _is_no_op_row(planned_table.frame, row_key, baseline_pairs):
                no_op_rows += 1

    allowed_update_rows = max(reference_existing_rows - no_op_rows, 0)

    new_data_rows = 0
    blocked_rows = 0
    for resolved_table in identity_result.tables.values():
        row_states = resolved_table.row_states
        new_data_rows += int(
            (
                (row_states == ChangeRowState.NEWLY_ALLOCATED_ENTITY)
                | (row_states == ChangeRowState.RECONCILED_CLASSIFIER)
                | (row_states == ChangeRowState.DERIVED_BRIDGE_ROW)
            ).sum()
        )
        blocked_rows += int((row_states == ChangeRowState.BLOCKED_UNRESOLVED).sum())

    pending_review_rows = blocked_rows if has_pending_review else 0
    blocked_rows = max(blocked_rows - pending_review_rows, 0)

    diagnostics = [
        (
            "Outcome classification: "
            f"{new_data_rows} {SubmissionOutcome.NEW_DATA.value}, "
            f"{no_op_rows} {SubmissionOutcome.NO_OP.value}, "
            f"{allowed_update_rows} {SubmissionOutcome.ALLOWED_UPDATE.value}, "
            f"{pending_review_rows} {SubmissionOutcome.PENDING_REVIEW.value}, "
            f"{blocked_rows} {SubmissionOutcome.BLOCKED.value}"
        )
    ]

    if compared_reference_rows == 0:
        diagnostics.append("No existing-row references detected; no-op comparison skipped")
    elif no_op_rows == 0:
        diagnostics.append("No no-op rows detected from mutable-field comparison")

    if reference_existing_rows and compared_reference_rows == 0:
        diagnostics.append(
            "No mutable baseline columns were provided for existing-row comparison; treated all existing references as allowed_update"
        )

    return SubmissionOutcomeSummary(
        new_data_rows=new_data_rows,
        no_op_rows=no_op_rows,
        allowed_update_rows=allowed_update_rows,
        pending_review_rows=pending_review_rows,
        blocked_rows=blocked_rows,
        diagnostics=diagnostics,
    )


def _baseline_column_pairs(frame: pd.DataFrame) -> list[tuple[str, str]]:
    """Return (current, baseline) column pairs using the '<field>__existing' convention."""
    pairs: list[tuple[str, str]] = []
    for baseline_column in frame.columns:
        if not baseline_column.endswith("__existing"):
            continue
        current_column = baseline_column[: -len("__existing")]
        if not current_column or current_column.startswith("_"):
            continue
        if current_column not in frame.columns:
            continue
        pairs.append((current_column, baseline_column))
    return pairs


def _is_no_op_row(frame: pd.DataFrame, row_key: object, baseline_pairs: list[tuple[str, str]]) -> bool:
    """Return True when all mutable fields match their baseline values for one row."""
    for current_column, baseline_column in baseline_pairs:
        current_value = frame.at[row_key, current_column]
        baseline_value = frame.at[row_key, baseline_column]
        if not _values_equal_for_outcome_comparison(current_value, baseline_value):
            return False
    return True


def _values_equal_for_outcome_comparison(left: Any, right: Any) -> bool:
    """Compare mutable-field values for no-op outcome detection."""
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return left == right


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
