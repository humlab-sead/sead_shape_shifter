"""Tests for SEAD change request deploy SQL generation."""

from datetime import datetime

import pandas as pd

from ingesters.sead_change_request import ChangeRequestPackage, ChangeRequestTable, ChangeRowState, SubmissionContext, build_deploy_artifact
from src.target_model.models import TargetModel


def minimal_target_model(**extra_entities: dict) -> TargetModel:
    """Build a minimal TargetModel for SQL builder tests."""
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": extra_entities,
            "constraints": [],
        }
    )


class TestBuildDeployArtifact:
    """Tests for in-memory deploy SQL generation."""

    def test_builds_insert_only_deploy_sql_in_one_transaction(self):
        """Deploy SQL should wrap insert statements in a single transaction with deferred constraints."""
        frame = pd.DataFrame({"sample_id": [101], "sample_name": ["O'Reilly"], "active": [True]})
        package = ChangeRequestPackage(
            tables={
                "sample": ChangeRequestTable(
                    name="sample",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            binding_set_uuid="binding-123",
            change_request_name="deploy/test.sql",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == [
            'INSERT INTO "tbl_sample" ("sample_id", "sample_name", "active") VALUES (101, \'O\'\'Reilly\', TRUE);'
        ]
        assert artifact.deploy_sql.startswith("BEGIN;\nSET CONSTRAINTS ALL DEFERRED;\nINSERT INTO")
        assert artifact.deploy_sql.endswith("\nCOMMIT;")
        assert artifact.metadata["non_revertible"] is True
        assert artifact.metadata["verify_placeholder"] is True
        assert artifact.metadata["submission_name"] == "test-submission"
        assert "Rollback is not implemented" in artifact.revert_placeholder_sql
        assert "Verification is not implemented" in artifact.verify_placeholder_sql
        assert artifact.metadata_artifact["non_revertible"] is True
        assert artifact.metadata_artifact["verify_placeholder"] is True
        assert artifact.metadata_artifact["deploy_statement_count"] == 1

    def test_uses_entity_name_when_target_table_missing(self):
        """Deploy SQL should fall back to the entity name when target_table is not declared."""
        frame = pd.DataFrame({"site_id": [501]})
        package = ChangeRequestPackage(
            tables={
                "site": ChangeRequestTable(
                    name="site",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(site={"role": "lookup", "public_id": "site_id"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == ['INSERT INTO "site" ("site_id") VALUES (501);']
        assert artifact.metadata_artifact["artifact_type"] == "delivery_1_change_package"
