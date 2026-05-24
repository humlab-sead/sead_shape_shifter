"""Tests for the SEAD change request internal contracts."""

from datetime import datetime

import pandas as pd

from ingesters.sead_change_request import ChangeRequestPackage, ChangeRequestTable, ChangeRowState, SourceTableBundle, SubmissionContext


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
        assert bundle.warnings == []


class TestChangeRequestPackage:
    """Tests for the generated change-request payload contract."""

    def test_package_defaults(self):
        """Package should start empty with no messages."""
        package = ChangeRequestPackage()

        assert package.tables == {}
        assert package.warnings == []
        assert package.infos == []

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
