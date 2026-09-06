"""Tests for SEAD change request deploy SQL generation."""

import gzip
from datetime import datetime
from hashlib import sha256

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
    PlannedRowAction,
    SubmissionContext,
    build_deploy_artifact,
    resolve_deploy_artifact_strategy,
)
from ingesters.sead_change_request.contracts import resolve_bundle_name
from src.target_model.models import TargetModel

# pylint: disable=unused-argument, line-too-long


def minimal_target_model(**extra_entities: dict) -> TargetModel:
    """Build a minimal TargetModel for SQL builder tests."""
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": extra_entities,
            "constraints": [],
        }
    )


def bundle_name(submission_context: SubmissionContext) -> str:
    """Build the expected CR bundle name for tests."""
    return resolve_bundle_name(submission_context)


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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        expected_bundle_name = bundle_name(submission_context)

        assert artifact.metadata["deploy_strategy"] == "copy_csv"
        assert artifact.metadata_artifact["deploy_strategy"] == "copy_csv"
        assert artifact.metadata_artifact["bundle_file_count"] == 1
        assert artifact.metadata_artifact["contract_version"] == 1
        assert artifact.metadata_artifact["cr_name"] == expected_bundle_name
        assert artifact.metadata_artifact["datatype"] == "mal"
        assert artifact.metadata_artifact["payload_format"] == "csv"
        assert artifact.metadata_artifact["payload_delimiter"] == "\t"
        assert artifact.metadata_artifact["payload_compression"] == "gzip"
        assert artifact.metadata_artifact["header_row"] is False
        assert artifact.metadata_artifact["payload_null_rule"] == "unquoted_empty_field"
        assert artifact.metadata_artifact["payload_empty_string_rule"] == "quoted_empty_field"
        assert artifact.metadata_artifact["sccs_runtime_assumption"] == "psql+zcat"
        assert artifact.metadata_artifact["files"] == [f"deploy/{expected_bundle_name}/tbl_sample.gz"]
        assert artifact.metadata_artifact["checksums"] == {
            f"deploy/{expected_bundle_name}/tbl_sample.gz": sha256(gzip.compress(b"101\tO'Reilly\ttrue\n", mtime=0)).hexdigest()
        }
        assert artifact.metadata_artifact["table_order"] == ["tbl_sample"]
        assert artifact.metadata_artifact["row_counts"] == {"tbl_sample": 1}
        assert f"-- deploy mal: {expected_bundle_name}" in artifact.deploy_sql
        assert artifact.statements == [
            f'\\copy "tbl_sample" ("sample_id", "sample_name", "active") FROM program \'zcat -qac {expected_bundle_name}/tbl_sample.gz\' WITH (FORMAT csv, DELIMITER E\'\\t\', ENCODING \'utf-8\');'  # NOQA
        ]
        assert artifact.bundle_files == {f"deploy/{expected_bundle_name}/tbl_sample.gz": "101\tO'Reilly\ttrue\n"}

    def test_copy_csv_distinguishes_null_and_empty_string(self):
        """CSV-mode payloads should distinguish null from empty string."""
        frame = pd.DataFrame({"sample_id": [101], "sample_name": [""], "sample_note": [None]})
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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        assert artifact.bundle_files[f"deploy/{bundle_name(submission_context)}/tbl_sample.gz"] == '101\t""\t\n'

    def test_copy_csv_escapes_tabs_quotes_backslashes_and_multiline_text(self):
        """CSV-mode payloads should preserve PostgreSQL-compatible escaping for special text content."""
        frame = pd.DataFrame(
            {
                "sample_id": [101],
                "sample_note": ['tab\tquote"slash\\line\nend'],
                "sample_comment": ["prefix\rsuffix"],
            }
        )
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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        assert artifact.bundle_files[f"deploy/{bundle_name(submission_context)}/tbl_sample.gz"] == (
            '101\t"tab\tquote""slash\\line\nend"\t"prefix\rsuffix"\n'
        )

    def test_copy_csv_preserves_precise_real_values_without_scientific_notation(self):
        """CSV-mode payloads should preserve precise real values without rounding them to zero."""
        precise_value = 0.1234567890123456
        frame = pd.DataFrame({"sample_id": [101], "small_value": [1e-7], "precise_value": [precise_value]})
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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        rendered_payload = artifact.bundle_files[f"deploy/{bundle_name(submission_context)}/tbl_sample.gz"]
        rendered_fields = rendered_payload.rstrip("\n").split("\t")

        assert rendered_fields == ["101", "0.0000001", str(precise_value)]
        assert "e" not in rendered_fields[1].lower()

    def test_copy_csv_renders_date_only_timestamps_without_time_component(self):
        """CSV-mode payloads should render date-only pandas timestamps as YYYY-MM-DD."""
        frame = pd.DataFrame({"sample_id": [101], "sample_date": [pd.Timestamp("2026-05-23")]})
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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        assert artifact.bundle_files[f"deploy/{bundle_name(submission_context)}/tbl_sample.gz"] == "101\t2026-05-23\n"

    def test_copy_csv_manifest_uses_emission_order_and_real_row_counts(self):
        """Manifest metadata should preserve emitted table order and row counts even with multiline payload text."""
        alpha_frame = pd.DataFrame({"alpha_id": [101], "alpha_note": ["line one\nline two"]})
        beta_frame = pd.DataFrame({"beta_id": [201], "beta_name": ["B"], "beta_flag": [True]})
        package = ChangeRequestPackage(
            tables={
                "beta": ChangeRequestTable(
                    name="beta",
                    frame=beta_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=beta_frame.index, name="_row_state"),
                ),
                "alpha": ChangeRequestTable(
                    name="alpha",
                    frame=alpha_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=alpha_frame.index, name="_row_state"),
                ),
            }
        )
        target_model = minimal_target_model(
            beta={"role": "fact", "public_id": "beta_id", "target_table": "tbl_beta"},
            alpha={"role": "fact", "public_id": "alpha_id", "target_table": "tbl_alpha"},
        )
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        assert artifact.metadata_artifact["table_order"] == ["tbl_beta", "tbl_alpha"]
        assert artifact.metadata_artifact["row_counts"] == {"tbl_beta": 1, "tbl_alpha": 1}

    def test_copy_csv_rejects_unsafe_target_table_name_for_bundle_path(self):
        """CSV deploy rendering should reject target table names that are unsafe in bundle paths."""
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
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "../tbl_sample"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        with pytest.raises(ValueError, match="Unsafe table name '../tbl_sample'"):
            build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

    def test_copy_csv_rejects_unsafe_entity_name_when_target_table_missing(self):
        """CSV deploy rendering should validate fallback entity names before using them in bundle paths."""
        frame = pd.DataFrame({"site_id": [501]})
        package = ChangeRequestPackage(
            tables={
                "../site": ChangeRequestTable(
                    name="../site",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(**{"../site": {"role": "lookup", "public_id": "site_id"}})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        with pytest.raises(ValueError, match="Unsafe table name '../site'"):
            build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

    def test_delegates_to_injected_strategy(self):
        """Deploy artifact generation should delegate to an injected rendering strategy."""

        class StubStrategy:
            def build_artifact(self, change_package, target_model, submission_context):
                return DeployArtifact(
                    deploy_sql="SELECT 1;",
                    statements=["SELECT 1;"],
                    metadata={"strategy": "stub"},
                    revert_sql="ROLLBACK;",
                    verify_sql="ROLLBACK;",
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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        expected_bundle_name = bundle_name(submission_context)

        assert artifact.statements == [
            'INSERT INTO "tbl_sample" ("sample_id", "sample_name", "active") VALUES (101, \'O\'\'Reilly\', TRUE);'
        ]
        assert artifact.deploy_sql.startswith(f"-- deploy mal: {expected_bundle_name}\n/")
        assert "BEGIN;\nSET CONSTRAINTS ALL DEFERRED;\nINSERT INTO" in artifact.deploy_sql
        assert artifact.deploy_sql.endswith("\nCOMMIT;")
        assert artifact.metadata["non_revertible"] is True
        assert artifact.metadata["verify_placeholder"] is True
        assert artifact.metadata["deploy_strategy"] == "inline_insert"
        assert artifact.metadata["submission_name"] == "test-submission"
        assert "Rollback is not implemented" in artifact.revert_sql
        assert "Verification is not implemented" in artifact.verify_sql
        assert f"-- revert mal: {expected_bundle_name}" in artifact.revert_sql
        assert f"-- verify mal: {expected_bundle_name}" in artifact.verify_sql
        assert artifact.metadata_artifact["non_revertible"] is True
        assert artifact.metadata_artifact["verify_placeholder"] is True
        assert artifact.metadata_artifact["deploy_strategy"] == "inline_insert"
        assert artifact.metadata_artifact["deploy_statement_count"] == 1
        assert artifact.metadata_artifact["contract_version"] == 1

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
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == ['INSERT INTO "site" ("site_id") VALUES (501);']
        assert artifact.metadata_artifact["artifact_type"] == "delivery_1_change_package"
        assert artifact.metadata_artifact["deploy_strategy"] == "inline_insert"

    def test_builds_update_statement_for_accepted_existing_row(self):
        """Deploy SQL should render accepted existing-row updates as UPDATE statements."""
        frame = pd.DataFrame(
            {
                "system_id": [1],
                "sample_id": [101],
                "sample_name": ["changed"],
                "sample_name__existing": ["old"],
            }
        )
        package = ChangeRequestPackage(
            tables={
                "sample": ChangeRequestTable(
                    name="sample",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=frame.index, name="_row_state"),
                    planned_actions=pd.Series([PlannedRowAction.UPDATE_EXISTING_CANDIDATE], index=frame.index, name="_planned_action"),
                )
            }
        )
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == ['UPDATE "tbl_sample" SET "sample_name" = \'changed\' WHERE "sample_id" = 101;']
        assert 'UPDATE "tbl_sample" SET "sample_name" = \'changed\' WHERE "sample_id" = 101;' in artifact.deploy_sql

    def test_builds_update_statement_using_only_configured_mutable_fields(self):
        """Deploy SQL should keep UPDATE statements inside the configured mutable-field boundary."""
        frame = pd.DataFrame(
            {
                "system_id": [1],
                "sample_id": [101],
                "sample_name": ["changed"],
                "sample_name__existing": ["old"],
                "sample_note": ["note changed"],
                "sample_note__existing": ["note old"],
            }
        )
        package = ChangeRequestPackage(
            tables={
                "sample": ChangeRequestTable(
                    name="sample",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=frame.index, name="_row_state"),
                    planned_actions=pd.Series([PlannedRowAction.UPDATE_EXISTING_CANDIDATE], index=frame.index, name="_planned_action"),
                    mutable_fields=["sample_name"],
                )
            }
        )
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == ['UPDATE "tbl_sample" SET "sample_name" = \'changed\' WHERE "sample_id" = 101;']

    def test_copy_csv_renders_update_statements_inline_for_existing_rows(self):
        """CSV deploy rendering should keep insert sidecars and emit accepted existing-row updates inline."""
        frame = pd.DataFrame(
            {
                "system_id": [1, 2],
                "sample_id": [101, 102],
                "sample_name": ["new row", "changed row"],
                "sample_name__existing": ["new row", "old row"],
            }
        )
        package = ChangeRequestPackage(
            tables={
                "sample": ChangeRequestTable(
                    name="sample",
                    frame=frame,
                    row_states=pd.Series(
                        [ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.EXISTING_ENTITY],
                        index=frame.index,
                        name="_row_state",
                    ),
                    planned_actions=pd.Series(
                        [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE],
                        index=frame.index,
                        name="_planned_action",
                    ),
                )
            }
        )
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")

        expected_bundle_name = bundle_name(submission_context)
        assert artifact.metadata_artifact["bundle_file_count"] == 1
        assert artifact.metadata_artifact["row_counts"] == {"tbl_sample": 1}
        assert artifact.bundle_files == {f"deploy/{expected_bundle_name}/tbl_sample.gz": "101\tnew row\n"}
        assert artifact.statements == [
            f'\\copy "tbl_sample" ("sample_id", "sample_name") '
            f"FROM program 'zcat -qac {expected_bundle_name}/tbl_sample.gz' WITH (FORMAT csv, DELIMITER E'\\t', ENCODING 'utf-8');",
            'UPDATE "tbl_sample" SET "sample_name" = \'changed row\' WHERE "sample_id" = 102;',
        ]
