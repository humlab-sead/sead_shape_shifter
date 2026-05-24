"""Tests for SEAD change request deploy SQL generation."""

from datetime import datetime

import pandas as pd
import pytest

from ingesters.sead_change_request import (
    COPY_CSV_DEPLOY_ARTIFACT_STRATEGY,
    DEFAULT_DEPLOY_ARTIFACT_STRATEGY,
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    CopyCsvDeployStrategy,
    DeployArtifact,
    SubmissionContext,
    build_deploy_artifact,
    resolve_deploy_artifact_strategy,
)
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

    def test_resolves_named_inline_insert_strategy(self):
        """Named strategy selection should resolve to the default inline-insert renderer."""
        strategy = resolve_deploy_artifact_strategy(DEFAULT_DEPLOY_ARTIFACT_STRATEGY)

        assert strategy.__class__.__name__ == "InlineInsertDeployStrategy"

    def test_rejects_unknown_named_strategy(self):
        """Unknown named strategies should fail loudly at the render boundary."""
        with pytest.raises(ValueError, match="Unsupported deploy strategy"):
            resolve_deploy_artifact_strategy("something_else")

    def test_resolves_copy_csv_strategy_placeholder(self):
        """The CSV deploy strategy name should resolve to its concrete renderer."""
        strategy = resolve_deploy_artifact_strategy(COPY_CSV_DEPLOY_ARTIFACT_STRATEGY)

        assert isinstance(strategy, CopyCsvDeployStrategy)

    def test_builds_copy_csv_artifact_with_sidecar_files(self):
        """CSV deploy rendering should emit \\copy statements plus CSV sidecar files."""
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
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        assert artifact.metadata["deploy_strategy"] == "copy_csv"
        assert artifact.metadata_artifact["deploy_strategy"] == "copy_csv"
        assert artifact.metadata_artifact["bundle_file_count"] == 1
        assert artifact.statements == [
            '\\copy "tbl_sample" ("sample_id", "sample_name", "active") FROM \'payload/tbl_sample.csv\' WITH (FORMAT csv, HEADER true);'
        ]
        assert artifact.bundle_files == {"payload/tbl_sample.csv": "sample_id,sample_name,active\n101,O'Reilly,True\n"}

    def test_delegates_to_injected_strategy(self):
        """Deploy artifact generation should delegate to an injected rendering strategy."""

        class StubStrategy:
            def build_artifact(self, change_package, target_model, submission_context):
                return DeployArtifact(
                    deploy_sql="SELECT 1;",
                    statements=["SELECT 1;"],
                    metadata={"strategy": "stub"},
                    revert_placeholder_sql="ROLLBACK;",
                    verify_placeholder_sql="ROLLBACK;",
                    metadata_artifact={"artifact_type": "stub"},
                    bundle_files={"payload/sample.csv": "sample_id\n101\n"},
                )

        frame = pd.DataFrame({"sample_id": [101]})
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
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy=StubStrategy())

        assert artifact.deploy_sql == "SELECT 1;"
        assert artifact.metadata == {"strategy": "stub"}
        assert artifact.bundle_files == {"payload/sample.csv": "sample_id\n101\n"}

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
        assert artifact.metadata["deploy_strategy"] == "inline_insert"
        assert artifact.metadata["submission_name"] == "test-submission"
        assert "Rollback is not implemented" in artifact.revert_placeholder_sql
        assert "Verification is not implemented" in artifact.verify_placeholder_sql
        assert artifact.metadata_artifact["non_revertible"] is True
        assert artifact.metadata_artifact["verify_placeholder"] is True
        assert artifact.metadata_artifact["deploy_strategy"] == "inline_insert"
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
        assert artifact.metadata_artifact["deploy_strategy"] == "inline_insert"
