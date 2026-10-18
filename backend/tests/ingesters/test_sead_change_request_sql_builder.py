"""Tests for SEAD change request deploy SQL generation."""

import gzip
from datetime import datetime
from hashlib import sha256

import pandas as pd
import pytest

from ingesters.sead_change_request import (
    COPY_CSV_DEPLOY_ARTIFACT_STRATEGY,
    DEFAULT_DEPLOY_ARTIFACT_STRATEGY,
    INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    CopyCsvDeployStrategy,
    DeployArtifact,
    KnownIdMapping,
    PlannedRowAction,
    SubmissionContext,
    build_deploy_artifact,
    resolve_deploy_artifact_strategy,
)
from ingesters.sead_change_request.contracts import resolve_bundle_name
from ingesters.sead_change_request.inline_staging_sql import _remote_entity_for_column
from ingesters.sead_change_request.sql_builder import InlineStagingDeployStrategy
from src.target_model.models import EntitySpec, TargetModel

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

    def test_inline_insert_omits_generated_bridge_id(self):
        frame = pd.DataFrame({"site_location_id": pd.Series([pd.NA], dtype="Int64"), "site_id": [6489], "location_id": [1]})
        package = ChangeRequestPackage(
            tables={
                "site_location": ChangeRequestTable(
                    name="site_location",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index, name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(
            site_location={
                "role": "bridge",
                "public_id": "site_location_id",
                "target_table": "tbl_site_locations",
                "columns": {
                    "site_location_id": {"required": True, "generated": True, "type": "integer", "nullable": False},
                    "site_id": {"required": True, "type": "integer", "nullable": False},
                    "location_id": {"required": True, "type": "integer", "nullable": False},
                },
            }
        )
        submission_context = SubmissionContext(
            submission_name="site-insert",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements == ['INSERT INTO "tbl_site_locations" ("site_id", "location_id") VALUES (6489, 1);']

    def test_copy_csv_omits_generated_bridge_id(self):
        frame = pd.DataFrame({"site_location_id": pd.Series([pd.NA], dtype="Int64"), "site_id": [6489], "location_id": [1]})
        package = ChangeRequestPackage(
            tables={
                "site_location": ChangeRequestTable(
                    name="site_location",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index, name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(
            site_location={
                "role": "bridge",
                "public_id": "site_location_id",
                "target_table": "tbl_site_locations",
                "columns": {
                    "site_location_id": {"required": True, "generated": True, "type": "integer", "nullable": False},
                    "site_id": {"required": True, "type": "integer", "nullable": False},
                    "location_id": {"required": True, "type": "integer", "nullable": False},
                },
            }
        )
        submission_context = SubmissionContext(
            submission_name="site-insert",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
        )

        artifact = build_deploy_artifact(package, target_model, submission_context, strategy="copy_csv")
        expected_bundle_name = bundle_name(submission_context)
        bundle_path = f"deploy/{expected_bundle_name}/tbl_site_locations.gz"

        assert artifact.bundle_files[bundle_path] == "6489\t1\n"
        assert '("site_id", "location_id")' in artifact.statements[0]

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

    def test_syncs_postgresql_sequence_after_inserting_sims_assigned_id(self):
        """Deploy SQL should keep a target sequence above explicit SIMS IDs."""
        package = ChangeRequestPackage(
            tables={
                "submission": ChangeRequestTable(
                    name="submission",
                    frame=pd.DataFrame({"submission_id": [7], "submission_name": ["Submission A"]}),
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=[0], name="_row_state"),
                )
            }
        )
        target_model = minimal_target_model(
            submission={
                "role": "fact",
                "identity_tracking": "tracked",
                "reconciliation": "allocate",
                "public_id": "submission_id",
                "target_table": "tbl_submissions",
                "synchronize_sequence_after_insert": True,
            }
        )
        submission_context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

        artifact = build_deploy_artifact(package, target_model, submission_context)

        assert artifact.statements[0] == 'LOCK TABLE "tbl_submissions" IN SHARE ROW EXCLUSIVE MODE;'
        assert artifact.statements[1] == 'INSERT INTO "tbl_submissions" ("submission_id", "submission_name") VALUES (7, \'Submission A\');'
        sequence_sync = artifact.statements[2]
        assert "pg_get_serial_sequence(target_table::text, target_column)" in sequence_sync
        assert "setval(target_sequence::regclass, table_max_id, true)" in sequence_sync
        assert "SELECT COALESCE(MAX(%I), 0)" in sequence_sync
        assert artifact.deploy_sql.index("LOCK TABLE") < artifact.deploy_sql.index("INSERT INTO")
        assert artifact.deploy_sql.index("INSERT INTO") < artifact.deploy_sql.index("pg_get_serial_sequence")

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
        assert artifact.metadata_artifact["artifact_type"] == "mvp_delivery_change_package"
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


class TestStrategyParity:
    """Both deploy strategies must emit the same SIMS-issued identity values."""

    def _package_with_resolved_identities(self) -> ChangeRequestPackage:
        frame = pd.DataFrame(
            {
                "system_id": [1, 2],
                "sample_id": [501, 502],
                "sample_name": ["Allocated A", "Allocated B"],
            }
        )
        return ChangeRequestPackage(
            tables={
                "sample": ChangeRequestTable(
                    name="sample",
                    frame=frame,
                    row_states=pd.Series(
                        [ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.NEWLY_ALLOCATED_ENTITY],
                        index=frame.index,
                        name="_row_state",
                    ),
                )
            }
        )

    def _submission_context(self) -> SubmissionContext:
        return SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 23, 0, 0),
            datatype="mal",
            identifier="TEST_SUBMISSION",
        )

    def test_both_strategies_emit_the_same_resolved_identity_values(self):
        """Inline INSERT and copy-CSV must both carry the SIMS-issued target IDs in order."""
        package = self._package_with_resolved_identities()
        target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
        context = self._submission_context()

        inline = build_deploy_artifact(package, target_model, context, strategy="inline_insert")
        copy_csv = build_deploy_artifact(package, target_model, context, strategy="copy_csv")

        # Inline INSERT carries both resolved IDs in its VALUES clauses.
        assert 'INSERT INTO "tbl_sample" ("sample_id", "sample_name") VALUES (501, \'Allocated A\');' in inline.statements
        assert 'INSERT INTO "tbl_sample" ("sample_id", "sample_name") VALUES (502, \'Allocated B\');' in inline.statements

        # copy-CSV carries the same two resolved IDs in its sidecar payload.
        resolved_bundle_name: str = resolve_bundle_name(context)
        payload: str = copy_csv.bundle_files[f"deploy/{resolved_bundle_name}/tbl_sample.gz"]
        assert payload == "501\tAllocated A\n502\tAllocated B\n"

        # Both strategies preserve exactly the same ordered target-ID values.
        inline_ids = [int(statement.split("VALUES (")[1].split(",")[0]) for statement in inline.statements]
        csv_ids = [int(line.split("\t")[0]) for line in payload.rstrip("\n").split("\n")]
        assert inline_ids == csv_ids == [501, 502]


def _staging_submission_context() -> SubmissionContext:
    return SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=datetime(2026, 10, 17, 10, 0, 0),
        datatype="mal",
        identifier="STAGING_CASE",
    )


def _staging_model(**extra_entities: dict) -> TargetModel:
    """Build a dataset -> analysis_entity -> abundance chain for staging tests."""
    entities = {
        "dataset": {
            "role": "lookup",
            "identity_tracking": "tracked",
            "reconciliation": "allocate",
            "public_id": "dataset_id",
            "target_table": "tbl_datasets",
            "synchronize_sequence_after_insert": True,
            "columns": {"dataset_name": {"required": True, "type": "string"}},
        },
        "analysis_entity": {
            "role": "fact",
            "public_id": "analysis_entity_id",
            "target_table": "tbl_analysis_entities",
            "aggregate_parent": "dataset",
            "columns": {"dataset_id": {"required": True, "type": "integer"}},
            "foreign_keys": [{"entity": "dataset", "required": True}],
        },
        "abundance": {
            "role": "fact",
            "public_id": "abundance_id",
            "target_table": "tbl_abundances",
            "aggregate_parent": "analysis_entity",
            "unique_sets": [["analysis_entity_id", "taxon_id"]],
            "columns": {
                "analysis_entity_id": {"required": True, "type": "integer"},
                "taxon_id": {"required": True, "type": "integer"},
            },
            "foreign_keys": [{"entity": "analysis_entity", "required": True}],
        },
    }
    entities.update(extra_entities)
    return TargetModel.model_validate({"model": {"name": "SEAD Test Model", "version": "0.1.0"}, "entities": entities, "constraints": []})


def _staging_package() -> ChangeRequestPackage:
    """Build a staging package with one known root ID and pending children."""
    dataset_frame = pd.DataFrame({"system_id": [10], "dataset_id": [900], "dataset_name": ["D1"]})
    analysis_frame = pd.DataFrame({"system_id": [100], "analysis_entity_id": [None], "dataset_id": [10]})
    abundance_frame = pd.DataFrame(
        {"system_id": [1000, 1001], "abundance_id": [None, None], "analysis_entity_id": [100, 100], "taxon_id": [5, 6]}
    )
    return ChangeRequestPackage(
        tables={
            "analysis_entity": ChangeRequestTable(
                name="analysis_entity",
                frame=analysis_frame,
                row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=analysis_frame.index),
                planned_actions=pd.Series([PlannedRowAction.DEFER_TO_DEPLOYMENT], index=analysis_frame.index),
            ),
            "abundance": ChangeRequestTable(
                name="abundance",
                frame=abundance_frame,
                row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID] * 2, index=abundance_frame.index),
                planned_actions=pd.Series([PlannedRowAction.DEFER_TO_DEPLOYMENT] * 2, index=abundance_frame.index),
            ),
            "dataset": ChangeRequestTable(
                name="dataset",
                frame=dataset_frame,
                row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=dataset_frame.index),
                planned_actions=pd.Series([PlannedRowAction.ALLOCATE], index=dataset_frame.index),
            ),
        },
        known_id_mappings=[KnownIdMapping(entity_name="dataset", system_id=10, target_id=900)],
        target_schema="public",
    )


# pylint: disable=too-many-lines
class TestStagingStrategyResolution:
    """Schema and strategy selection rules."""

    def test_inline_staging_requires_a_schema(self):
        with pytest.raises(ValueError, match="requires a non-empty 'staging_target_schema'"):
            resolve_deploy_artifact_strategy(INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY)

    def test_inline_staging_accepts_a_safe_schema(self):
        strategy = resolve_deploy_artifact_strategy(INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY, staging_target_schema="public")

        assert isinstance(strategy, InlineStagingDeployStrategy)
        assert strategy.target_schema == "public"

    @pytest.mark.parametrize("unsafe_schema", ["public; DROP TABLE x", "1public", "pub lic"])
    def test_inline_staging_rejects_an_unsafe_schema(self, unsafe_schema: str):
        with pytest.raises(ValueError, match="Unsafe 'staging_target_schema'"):
            resolve_deploy_artifact_strategy(INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY, staging_target_schema=unsafe_schema)

    def test_direct_strategy_rejects_a_staging_schema(self):
        with pytest.raises(ValueError, match="does not accept 'staging_target_schema'"):
            resolve_deploy_artifact_strategy("inline_insert", staging_target_schema="public")

    def test_mismatched_package_schema_is_rejected(self):
        package = _staging_package()
        strategy = InlineStagingDeployStrategy(target_schema="clearing_house")

        with pytest.raises(ValueError, match="but the deployment schema is 'clearing_house'"):
            strategy.build_artifact(package, _staging_model(), _staging_submission_context())


class TestInlineStagingArtifact:
    """Rendered statements for a supported staging deployment."""

    def test_artifact_metadata_records_the_staging_contract(self):
        artifact = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        )

        assert artifact.metadata["deploy_strategy"] == INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY
        assert artifact.metadata_artifact["staging_target_schema"] == "public"
        assert artifact.metadata_artifact["staged_table_count"] == 3
        assert artifact.metadata_artifact["known_id_mapping_count"] == 1

    def test_relations_are_schema_qualified_and_locked_in_sorted_order(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert '"public"."tbl_abundances"' in deploy_sql
        lock_lines = [line for line in deploy_sql.splitlines() if line.startswith("LOCK TABLE")]
        assert lock_lines == [
            'LOCK TABLE "public"."tbl_abundances" IN SHARE ROW EXCLUSIVE MODE;',
            'LOCK TABLE "public"."tbl_analysis_entities" IN SHARE ROW EXCLUSIVE MODE;',
            'LOCK TABLE "public"."tbl_datasets" IN SHARE ROW EXCLUSIVE MODE;',
        ]

    def test_support_check_precedes_locks_and_sequence_writes(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert deploy_sql.index("$shape_shifter_staging_support$") < deploy_sql.index("LOCK TABLE")
        assert deploy_sql.index("LOCK TABLE") < deploy_sql.index("nextval(")
        assert "seqcache" in deploy_sql
        assert "tgtype & 4" in deploy_sql

    def test_known_ids_seed_the_map_and_pending_ids_are_allocated(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert "VALUES ('dataset', 10, 900);" in deploy_sql
        assert "SELECT 'abundance', \"_local_system_id\"," in deploy_sql
        assert "nextval(pg_get_serial_sequence('\"public\".\"tbl_abundances\"', 'abundance_id'))" in deploy_sql
        assert "SELECT 'dataset', \"_local_system_id\"," not in deploy_sql

    def test_local_values_are_kept_out_of_target_columns(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert 'INSERT INTO "_shape_shifter_stage_abundance" ("taxon_id", "_local_system_id", "_local_analysis_entity_id")' in deploy_sql
        assert 'INSERT INTO "_shape_shifter_stage_analysis_entity" ("_local_system_id", "_local_dataset_id")' in deploy_sql
        assert 'UPDATE "_shape_shifter_stage_abundance" AS staged SET "analysis_entity_id" = mapped.target_id' in deploy_sql

    def test_unique_set_checks_compare_staged_and_target_rows(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert "$shape_shifter_staging_unique_sets_abundance_0$" in deploy_sql
        assert "HAVING count(*) > 1" in deploy_sql
        assert 'EXISTS (SELECT 1 FROM "public"."tbl_abundances" AS target' in deploy_sql

    def test_inserts_follow_dependency_order(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        dataset_position = deploy_sql.index("$shape_shifter_staging_inserts_dataset$")
        analysis_position = deploy_sql.index("$shape_shifter_staging_inserts_analysis_entity$")
        abundance_position = deploy_sql.index("$shape_shifter_staging_inserts_abundance$")

        assert dataset_position < analysis_position < abundance_position
        assert "OVERRIDING SYSTEM VALUE" in deploy_sql
        assert 'ORDER BY "_local_system_id"' in deploy_sql

    def test_staging_uses_one_transaction(self):
        deploy_sql = build_deploy_artifact(
            _staging_package(),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        ).deploy_sql

        assert deploy_sql.count("\nBEGIN;") == 1
        assert deploy_sql.rstrip().endswith("COMMIT;")
        assert "ON COMMIT DROP" in deploy_sql


class TestInlineStagingRejections:
    """Explicit failures before any target write."""

    def test_ambiguous_foreign_key_column_is_rejected(self):
        model = minimal_target_model(
            dataset={"public_id": "dataset_id"},
            other_dataset={"public_id": "dataset_id"},
        )
        spec = EntitySpec.model_validate({"foreign_keys": [{"entity": "other_dataset"}, {"entity": "dataset"}]})

        with pytest.raises(ValueError, match="dataset_id.*dataset, other_dataset"):
            _remote_entity_for_column(spec, model, "dataset_id")

    def test_selected_insert_cycle_is_rejected(self):
        model = _staging_model(
            cyclic_a={
                "role": "fact",
                "public_id": "cyclic_a_id",
                "target_table": "tbl_cyclic_a",
                "columns": {"cyclic_b_id": {"required": True, "type": "integer"}},
                "foreign_keys": [{"entity": "cyclic_b", "required": True}],
            },
            cyclic_b={
                "role": "fact",
                "public_id": "cyclic_b_id",
                "target_table": "tbl_cyclic_b",
                "columns": {"cyclic_a_id": {"required": True, "type": "integer"}},
                "foreign_keys": [{"entity": "cyclic_a", "required": True}],
            },
        )
        frame_a = pd.DataFrame({"system_id": [1], "cyclic_a_id": [None], "cyclic_b_id": [2]})
        frame_b = pd.DataFrame({"system_id": [2], "cyclic_b_id": [None], "cyclic_a_id": [1]})
        package = ChangeRequestPackage(
            tables={
                "cyclic_a": ChangeRequestTable(
                    name="cyclic_a",
                    frame=frame_a,
                    row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=frame_a.index),
                ),
                "cyclic_b": ChangeRequestTable(
                    name="cyclic_b",
                    frame=frame_b,
                    row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=frame_b.index),
                ),
            },
            target_schema="public",
        )

        with pytest.raises(ValueError, match="Staged insert dependency cycle detected: cyclic_a -> cyclic_b"):
            build_deploy_artifact(package, model, _staging_submission_context(), strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY)

    def test_entity_without_target_metadata_is_rejected(self):
        model = _staging_model(
            missing_target={"role": "fact", "public_id": "missing_target_id"},
        )
        frame = pd.DataFrame({"system_id": [1], "missing_target_id": [None]})
        package = ChangeRequestPackage(
            tables={
                "missing_target": ChangeRequestTable(
                    name="missing_target",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=frame.index),
                )
            },
            target_schema="public",
        )

        with pytest.raises(ValueError, match="needs target_table and public_id metadata for inline staging"):
            build_deploy_artifact(package, model, _staging_submission_context(), strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY)

    def test_empty_package_renders_no_statements(self):
        artifact = build_deploy_artifact(
            ChangeRequestPackage(target_schema="public"),
            _staging_model(),
            _staging_submission_context(),
            strategy=INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
        )

        assert artifact.statements == []


@pytest.mark.parametrize(
    ("deploy_strategy", "target_schema"),
    [("inline_insert", None), ("copy_csv", None), ("inline_staging", "public")],
)
def test_manifest_records_the_effective_scope_and_run_id(deploy_strategy: str, target_schema: str | None):
    """Every deploy strategy carries the same scope and run ID in its runtime and manifest metadata."""
    submission_context = SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=datetime(2026, 5, 23, 23, 0, 0),
        datatype="mal",
        identifier="TEST_SUBMISSION",
        scope_name="provider://mal/archeobotany/arbodat-pilot",
        run_id="run-abc-123",
    )
    target_model = minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"})
    frame = pd.DataFrame({"sample_id": [101]})
    package = ChangeRequestPackage(
        tables={
            "sample": ChangeRequestTable(
                name="sample",
                frame=frame,
                row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
            )
        },
        target_schema=target_schema,
    )

    artifact = build_deploy_artifact(package, target_model, submission_context, strategy=deploy_strategy)

    assert artifact.metadata["scope_name"] == "provider://mal/archeobotany/arbodat-pilot"
    assert artifact.metadata["run_id"] == "run-abc-123"
    assert artifact.metadata_artifact["scope_name"] == "provider://mal/archeobotany/arbodat-pilot"
    assert artifact.metadata_artifact["run_id"] == "run-abc-123"
