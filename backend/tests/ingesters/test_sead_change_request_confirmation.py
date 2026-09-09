"""Tests for SEAD change request pending-confirmation reporting."""

from datetime import datetime

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, SubmissionContext
from ingesters.sead_change_request.contracts import IdentityResolutionResult, PendingConfirmationReport, ResolvedIdentityTable


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

        report = PendingConfirmationReport.create(
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
