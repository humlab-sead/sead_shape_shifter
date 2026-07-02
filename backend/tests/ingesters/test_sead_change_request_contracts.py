"""Tests for the SEAD change request internal contracts."""

from datetime import datetime

import pandas as pd

from ingesters.sead_change_request import ChangeRequestPackage, ChangeRequestTable, ChangeRowState, SourceTableBundle, SubmissionContext
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    LifecycleVersionState,
    LogicalRecordVersion,
    PendingConfirmationReport,
    ResolvedIdentityTable,
    validate_one_live_version,
)


class TestChangeRowState:
    """Tests for Delivery 1 row-state definitions."""

    def test_row_state_values(self):
        """Row-state enum should match the accepted Delivery 1 design names."""
        assert ChangeRowState.EXISTING_ENTITY == "existing_entity"
        assert ChangeRowState.NEWLY_ALLOCATED_ENTITY == "newly_allocated_entity"
        assert ChangeRowState.RECONCILED_CLASSIFIER == "reconciled_classifier"
        assert ChangeRowState.DERIVED_BRIDGE_ROW == "derived_bridge_row"
        assert ChangeRowState.BLOCKED_UNRESOLVED == "blocked_unresolved"


class TestSourceTableBundle:
    """Tests for the DataFrame-first source handoff."""

    def test_bundle_preserves_tables_and_defaults(self):
        """Source bundle should carry tables plus optional metadata."""
        sample = pd.DataFrame({"sample_id": [1, 2]})

        bundle = SourceTableBundle(tables={"sample": sample})

        assert bundle.tables["sample"].equals(sample)
        assert bundle.source_name == ""
        assert not bundle.warnings


class TestChangeRequestPackage:
    """Tests for the generated change-request payload contract."""

    def test_package_defaults(self):
        """Package should start empty with no messages."""
        package = ChangeRequestPackage()

        assert not package.tables
        assert not package.warnings
        assert not package.infos

    def test_change_request_table_carries_row_states(self):
        """Prepared tables should keep DataFrame content and row-state annotations together."""
        frame = pd.DataFrame({"sample_id": [1]})
        row_states = pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], name="_row_state")

        table = ChangeRequestTable(name="sample", frame=frame, row_states=row_states)

        assert table.name == "sample"
        assert table.frame.equals(frame)
        assert table.row_states.equals(row_states)


class TestSubmissionContext:
    """Tests for submission-scoped Delivery 1 metadata."""

    def test_submission_context_preserves_fields(self):
        """Submission context should keep the traceability fields needed by Delivery 1."""
        timestamp = datetime(2026, 5, 23, 22, 0, 0)

        context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=timestamp,
            binding_set_uuid="binding-123",
            change_request_name="CR-2026-001",
        )

        assert context.submission_name == "test-submission"
        assert context.project_name == "test-project"
        assert context.timestamp == timestamp
        assert context.binding_set_uuid == "binding-123"
        assert context.change_request_name == "CR-2026-001"


class TestBuildPendingConfirmationReport:
    """Tests for the operator-facing Binding Set confirmation report."""

    def test_report_collects_blocked_entities_and_rerun_instruction(self):
        """Pending confirmation reports should identify blocked entities and the rerun action."""
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=pd.DataFrame({"system_id": [1]}),
                    row_states=pd.Series([ChangeRowState.BLOCKED_UNRESOLVED], name="_row_state"),
                    resolved_target_ids=pd.Series([pd.NA], dtype="Int64", name="_target_id"),
                ),
                "site": ResolvedIdentityTable(
                    entity_name="site",
                    frame=pd.DataFrame({"system_id": [2]}),
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], name="_row_state"),
                    resolved_target_ids=pd.Series([101], dtype="Int64", name="_target_id"),
                ),
            }
        )
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 22, 30, 0),
            binding_set_uuid="binding-123",
            change_request_name="CR-2026-001",
        )

        report: PendingConfirmationReport = PendingConfirmationReport.create(
            submission_context,
            identity_result,
            binding_set_state="proposed",
        )

        assert report.submission_name == "test-submission"
        assert report.project_name == "test-project"
        assert report.binding_set_uuid == "binding-123"
        assert report.binding_set_state == "proposed"
        assert report.blocked_entities == ["sample"]
        assert report.blocked_rows == 1
        assert report.outstanding_step == "Confirm the Binding Set before change-package generation can continue"
        assert report.operator_action == "Confirm the Binding Set in SIMS, then rerun the ingester with the same submission context"
        assert "test-submission" in report.rerun_instruction


class TestLifecycleVersionContracts:
    """Tests for phase-1 lifecycle metadata and invariant checks."""

    def test_lifecycle_version_state_values(self):
        """Lifecycle version state names should match the accepted lifecycle policy terms."""
        assert LifecycleVersionState.LIVE == "live"
        assert LifecycleVersionState.SUPERSEDED == "superseded"
        assert LifecycleVersionState.PENDING_REVIEW == "pending_review"
        assert LifecycleVersionState.BLOCKED == "blocked"

    def test_one_live_version_check_passes_when_each_logical_record_has_at_most_one_live_version(self):
        """Invariant check should pass when logical records have zero or one live version."""
        records = [
            LogicalRecordVersion(logical_record_key="sample:1", version_key="v1", lifecycle_state=LifecycleVersionState.LIVE),
            LogicalRecordVersion(
                logical_record_key="sample:1",
                version_key="v0",
                lifecycle_state=LifecycleVersionState.SUPERSEDED,
                supersedes_version_key=None,
            ),
            LogicalRecordVersion(logical_record_key="sample:2", version_key="v1", lifecycle_state=LifecycleVersionState.PENDING_REVIEW),
        ]

        assert validate_one_live_version(records) == []

    def test_one_live_version_check_reports_violation_when_logical_record_has_multiple_live_versions(self):
        """Invariant check should report a violation when one logical record has multiple live versions."""
        records = [
            LogicalRecordVersion(logical_record_key="sample:1", version_key="v1", lifecycle_state=LifecycleVersionState.LIVE),
            LogicalRecordVersion(logical_record_key="sample:1", version_key="v2", lifecycle_state=LifecycleVersionState.LIVE),
        ]

        violations = validate_one_live_version(records)

        assert len(violations) == 1
        assert "sample:1" in violations[0]
        assert "2 live versions" in violations[0]
