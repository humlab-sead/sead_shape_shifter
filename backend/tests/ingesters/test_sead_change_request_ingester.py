"""Tests for the SEAD change request ingester scaffold behavior."""

from typing import Any, cast

import pandas as pd
import pytest

from backend.app.ingesters import IngesterConfig
from backend.app.services.ingester_runtime import SeadChangeRequestSimsAdapter
from ingesters.sead_change_request import ChangeRowState, DeployArtifact, SourceTableBundle
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester


class FakeReconciliationClient:
    """Simple fake reconciliation client for ingester tests."""

    def __init__(self, target_id: int | None) -> None:
        self.target_id = target_id

    async def reconcile_entity(self, entity_name: str, row: dict) -> int | None:
        return self.target_id


class FakeSimsClient:
    """Simple fake SIMS client for ingester tests."""

    def __init__(
        self,
        *,
        binding_set_uuid: str = "binding-123",
        binding_set_state: str = "confirmed",
        confirmed_binding_set_state: str | None = None,
        target_id: int | None = 501,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.binding_set_state = binding_set_state
        self.confirmed_binding_set_state = confirmed_binding_set_state or binding_set_state
        self.target_id = target_id
        self.associated_change_requests: list[tuple[str, str]] = []

    async def allocate_entity(self, entity_name: str, row: dict, submission_context) -> dict:
        return {
            "target_id": self.target_id,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Allocated {entity_name}",
        }

    async def derive_bridge_row(self, entity_name: str, row: dict, submission_context) -> dict:
        return {
            "state": ChangeRowState.DERIVED_BRIDGE_ROW.value,
            "target_id": None,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Derived {entity_name}",
        }

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        return self.binding_set_state

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        self.binding_set_state = self.confirmed_binding_set_state
        return self.binding_set_state

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        self.associated_change_requests.append((binding_set_uuid, change_request_name))


class FakeBackendSimsClient:
    """Minimal fake backend SIMS client for adapter-backed ingester tests."""

    def __init__(
        self,
        binding_set_uuid: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        lifecycle_state: str = "confirmed",
        *,
        target_id: int | None = None,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.lifecycle_state = lifecycle_state
        self.target_id = target_id
        self.associated_change_requests: list[tuple[str, str]] = []

    async def resolve(self, request: object):
        return cast(
            Any,
            type(
                "ResolveResponse",
                (),
                {
                    "binding_set": type(
                        "BindingSetResponse",
                        (),
                        {
                            "binding_set_uuid": self.binding_set_uuid,
                            "lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})(),
                        },
                    )(),
                    "outcomes": [
                        type(
                            "Outcome",
                            (),
                            {"tracked_identity_uuid": None, "target_id": self.target_id},
                        )()
                    ],
                },
            )(),
        )

    async def get_binding_set(self, binding_set_uuid):
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )

    async def confirm_binding_set(self, binding_set_uuid):
        self.lifecycle_state = "confirmed"
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )

    async def associate_change_request(self, binding_set_uuid, change_request_name: str):
        self.associated_change_requests.append((str(binding_set_uuid), change_request_name))
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )


class FakeCollisionChecker:
    """Simple fake target collision checker for ingester tests."""

    def __init__(
        self, *, target_ids: set[tuple[str, str, int]] | None = None, rows: set[tuple[str, tuple[tuple[str, object], ...]]] | None = None
    ) -> None:
        self.target_ids = target_ids or set()
        self.rows = rows or set()

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool:
        return (table_name, public_id_column, target_id) in self.target_ids

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        return (table_name, tuple(sorted(filters.items()))) in self.rows


class StubBundleFileDeployStrategy:
    """Test strategy that emits an extra sidecar file in the artifact bundle."""

    def build_artifact(self, change_package, target_model, submission_context):
        return DeployArtifact(
            deploy_sql="SELECT 1;",
            statements=["SELECT 1;"],
            metadata={"deploy_strategy": "stub_bundle_file"},
            revert_placeholder_sql="ROLLBACK;",
            verify_placeholder_sql="ROLLBACK;",
            metadata_artifact={"artifact_type": "stub", "deploy_strategy": "stub_bundle_file"},
            bundle_files={"payload/sample.csv": "sample_id\n501\n"},
        )


def minimal_target_model(**extra_entities: dict) -> dict:
    """Build a minimal target model payload for ingester tests."""
    return {
        "model": {"name": "SEAD Test Model", "version": "0.1.0"},
        "entities": extra_entities,
        "constraints": [],
    }


def minimal_submission_context(**overrides: object) -> dict:
    """Build a minimal submission context payload for ingester tests."""
    payload: dict[str, object] = {
        "submission_name": "test-submission",
        "project_name": "test-project",
        "timestamp": "2026-05-23T22:00:00",
    }
    payload.update(overrides)
    return payload


class TestSeadChangeRequestIngesterValidation:
    """Tests for DataFrame-first validation handoff."""

    @pytest.mark.asyncio
    async def test_validate_accepts_tables_from_config_extra(self):
        """Validation should accept the Delivery 1 in-memory table bundle from config.extra."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1, 2]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is True
        assert result.errors == []
        assert any("1 table" in info for info in result.infos)
        assert any("2 row" in info for info in result.infos)
        assert any("Validated submission context for 'test-submission' in project 'test-project'" in info for info in result.infos)
        assert any("Planned 'sample': 2 reference_existing" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_accepts_source_bundle_argument(self):
        """Validation should accept an already-built source bundle directly."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )
        bundle = SourceTableBundle(
            tables={"sample": pd.DataFrame({"sample_id": [1]})},
            source_name="normalized submission",
            warnings=["sample warning"],
        )

        result = await ingester.validate(bundle)

        assert result.is_valid is True
        assert result.warnings == ["sample warning"]
        assert any("normalized submission" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_accepts_excel_path_source(self, tmp_path):
        """Validation should load a workbook path into the source bundle contract."""
        workbook_path = tmp_path / "submission.xlsx"
        with pd.ExcelWriter(workbook_path) as writer:
            pd.DataFrame({"Sample ID": [1, 2]}).to_excel(writer, sheet_name="sample", index=False)
            pd.DataFrame({"ignored": [1]}).to_excel(writer, sheet_name="data_table_index", index=False)

        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                submission_name="test-submission",
                output_folder=str(tmp_path),
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate(workbook_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["Ignored sheet 'data_table_index' from Excel source bundle"]
        assert any(f"Source bundle name: {workbook_path}" in info for info in result.infos)
        assert any("Planned 'sample': 2 reference_existing" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_fails_for_unsupported_path_source_extension(self, tmp_path):
        """Validation should reject non-Excel path sources at the boundary."""
        source_path = tmp_path / "submission.csv"
        source_path.write_text("sample_id\n1\n", encoding="utf-8")

        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate(source_path)

        assert result.is_valid is False
        assert result.errors == ["Unsupported source file format '.csv'; expected .xlsx or .xls"]

    @pytest.mark.asyncio
    async def test_validate_fails_for_non_dataframe_table_values(self):
        """Validation should reject malformed table mappings at the handoff boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": [{"sample_id": 1}]},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Source table 'sample' must be a pandas DataFrame"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_target_model_missing(self):
        """Validation should require target-model metadata before planning rows."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={"tables": {"sample": pd.DataFrame({"sample_id": [1]})}},
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Target model is required; provide config.extra['target_model'] as a dict or TargetModel"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_missing(self):
        """Validation should require explicit submission context metadata."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Submission context is required; provide config.extra['submission_context']"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_timestamp_invalid(self):
        """Validation should reject invalid submission timestamps at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(timestamp="not-a-timestamp"),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Submission context timestamp must be a valid ISO-8601 datetime string"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_identity_assignments_malformed(self):
        """Validation should reject malformed identity-assignment payloads at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {"sample": {0: {"state": "not-a-state"}}},
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Identity assignment for 'sample' row '0' has invalid state 'not-a-state'"]

    @pytest.mark.asyncio
    async def test_validate_fails_for_unknown_target_model_table(self):
        """Validation should fail when the bundle includes a table not declared in the target model."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(site={"role": "fact", "public_id": "site_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == ["Source table 'sample' is not present in the target model"]

    @pytest.mark.asyncio
    async def test_validate_surfaces_bridge_planning_diagnostics_as_warnings(self):
        """Validation should surface early bridge-planning blockers as warnings for now."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample_taxon": pd.DataFrame({"sample_id": [1], "taxon_id": [2]})},
                    "target_model": minimal_target_model(sample_taxon={"role": "bridge"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample_taxon": {
                            0: {
                                "state": ChangeRowState.DERIVED_BRIDGE_ROW,
                                "target_id": 5001,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is True
        assert result.warnings == ["Bridge entity 'sample_taxon' has no unique_sets metadata; Delivery 1 uniqueness checks will be blocked"]
        assert any("1 evaluate_bridge" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_reports_blocked_rows_after_identity_resolution(self):
        """Validation should fail when planned work lacks required identity assignments."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert any("Blocked rows after identity resolution: 1" in info for info in result.infos)
        assert result.errors == [
            "Entity 'sample' has 1 row(s) without a resolved target ID for 'sample_id'",
            "Entity 'sample' row '0' is missing an identity assignment for planned action 'allocate'",
        ]

    @pytest.mark.asyncio
    async def test_validate_accepts_identity_assignments(self):
        """Validation should summarize zero blocked rows when identity assignments are provided."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                                "note": "Allocated by test harness",
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is True
        assert any("Blocked rows after identity resolution: 0" in info for info in result.infos)
        assert result.warnings == ["Entity 'sample' row '0': Allocated by test harness"]

    @pytest.mark.asyncio
    async def test_validate_accepts_client_orchestrated_assignments(self):
        """Validation should accept assignments produced by the thin client orchestration layer."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": FakeSimsClient(binding_set_state="confirmed", target_id=501),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is True
        assert result.pending_confirmation_report is None
        assert any("Binding Set UUID: binding-123" in info for info in result.infos)
        assert result.warnings == ["Entity 'sample' row '0': Allocated sample"]

    @pytest.mark.asyncio
    async def test_validate_returns_pending_confirmation_report_for_proposed_binding_set(self):
        """Validation should surface a pending confirmation report when SIMS returns a proposed Binding Set."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": FakeSimsClient(binding_set_state="proposed", target_id=501),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.pending_confirmation_report is not None
        assert result.pending_confirmation_report["binding_set_uuid"] == "binding-123"
        assert result.pending_confirmation_report["binding_set_state"] == "proposed"


class TestSeadChangeRequestIngesterIngest:
    """Tests for scaffold ingest behavior."""

    @pytest.mark.asyncio
    async def test_ingest_emits_empty_artifact_bundle_for_valid_reference_only_bundle(self, tmp_path):
        """Ingest should emit an artifact bundle even when no rows enter the Delivery 1 insert package."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1, 2]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert result.tables_processed == 0
        assert result.records_inserted == 0
        assert result.error_details is None
        assert (tmp_path / "test-submission" / "deploy.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_returns_validation_failure_for_invalid_bundle(self):
        """Ingest should stop at the validation boundary when the input contract is not met."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is False
        assert result.message == "Validation failed"
        assert result.error_details == "Source file does not exist: submission.xlsx"

    @pytest.mark.asyncio
    async def test_ingest_returns_invalid_submission_context_error(self):
        """Ingest should stop at the submission-context boundary when the context is malformed."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(timestamp="invalid"),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Invalid submission context"
        assert result.error_details == "Submission context timestamp must be a valid ISO-8601 datetime string"

    @pytest.mark.asyncio
    async def test_ingest_blocks_when_identity_resolution_incomplete(self):
        """Ingest should stop before generation when identity work remains unresolved."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Identity resolution incomplete"
        assert result.error_details == "Entity 'sample' row '0' is missing an identity assignment for planned action 'allocate'"

    @pytest.mark.asyncio
    async def test_ingest_accepts_resolved_identity_assignments(self, tmp_path):
        """Ingest should emit the Delivery 1 artifact bundle when assignments are present."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert result.tables_processed == 1
        assert result.records_inserted == 1
        assert result.error_details is None
        assert result.deploy_artifact is not None
        assert "Rollback is not implemented" in result.deploy_artifact["revert_placeholder_sql"]
        assert "Verification is not implemented" in result.deploy_artifact["verify_placeholder_sql"]
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["non_revertible"] is True
        assert result.deploy_artifact["metadata_artifact"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["verify_placeholder"] is True
        assert (tmp_path / "test-submission" / "deploy.sql").exists()
        assert (tmp_path / "test-submission" / "revert.sql").exists()
        assert (tmp_path / "test-submission" / "verify.sql").exists()
        assert (tmp_path / "test-submission" / "metadata.json").exists()

    @pytest.mark.asyncio
    async def test_ingest_accepts_named_deploy_strategy(self, tmp_path):
        """Ingest should accept the default named deploy strategy from config.extra."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "inline_insert",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert 'INSERT INTO "tbl_sample" ("sample_id") VALUES (501);' in result.deploy_artifact["deploy_sql"]

    @pytest.mark.asyncio
    async def test_ingest_emits_strategy_sidecar_files(self, tmp_path):
        """Ingest should write additional files emitted by a deploy strategy into the artifact bundle."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": StubBundleFileDeployStrategy(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["bundle_files"] == {"payload/sample.csv": "sample_id\n501\n"}
        assert (tmp_path / "test-submission" / "payload" / "sample.csv").read_text(encoding="utf-8") == "sample_id\n501\n"

    @pytest.mark.asyncio
    async def test_ingest_rejects_unknown_named_deploy_strategy(self):
        """Ingest should fail cleanly when config.extra requests an unsupported deploy strategy."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "unknown_strategy",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Invalid deploy strategy"
        assert result.error_details == "Unsupported deploy strategy 'unknown_strategy'; expected 'inline_insert' or 'copy_csv'"

    @pytest.mark.asyncio
    async def test_ingest_accepts_copy_csv_deploy_strategy(self, tmp_path):
        """Ingest should emit a CSV-backed artifact bundle for the copy_csv strategy."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "copy_csv"
        assert result.deploy_artifact["metadata_artifact"]["bundle_file_count"] == 1
        assert "\\copy \"sample\" (\"sample_id\") FROM 'payload/sample.csv' WITH (FORMAT csv, HEADER true);" in result.deploy_artifact["deploy_sql"]
        assert result.deploy_artifact["bundle_files"] == {"payload/sample.csv": "sample_id\n501\n"}
        assert (tmp_path / "test-submission" / "payload" / "sample.csv").read_text(encoding="utf-8") == "sample_id\n501\n"

    @pytest.mark.asyncio
    async def test_ingest_stops_when_target_id_collision_detected(self):
        """Ingest should stop before package generation when a target ID collision is detected."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
                    "submission_context": minimal_submission_context(),
                    "collision_checker": FakeCollisionChecker(target_ids={("tbl_sample", "sample_id", 501)}),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Target collision checks failed"
        assert result.error_details == "Entity 'sample' row '0' collides with existing target ID 501 in 'tbl_sample.sample_id'"

    @pytest.mark.asyncio
    async def test_ingest_stops_when_bridge_uniqueness_metadata_missing_at_collision_check(self):
        """Ingest should fail before package generation when insertable bridge rows lack usable uniqueness metadata."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample_taxon": pd.DataFrame({"sample_id": [101], "taxon_id": [9001]})},
                    "target_model": minimal_target_model(sample_taxon={"role": "bridge"}),
                    "submission_context": minimal_submission_context(),
                    "collision_checker": FakeCollisionChecker(),
                    "identity_assignments": {
                        "sample_taxon": {
                            0: {
                                "state": ChangeRowState.DERIVED_BRIDGE_ROW,
                                "target_id": 5001,
                            }
                        }
                    },
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Target collision checks failed"
        assert result.error_details == "Bridge entity 'sample_taxon' cannot run collision checks because unique_sets metadata is missing"

    @pytest.mark.asyncio
    async def test_ingest_returns_pending_confirmation_report_for_proposed_binding_set(self):
        """Ingest should return the structured pending confirmation report when SIMS blocks finalization."""
        sims_client = FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="proposed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "Binding Set confirmation incomplete"
        assert result.pending_confirmation_report is not None
        assert result.pending_confirmation_report["binding_set_uuid"] == "binding-123"
        assert result.deploy_artifact is None

    @pytest.mark.asyncio
    async def test_ingest_returns_explicit_capability_gap_when_sims_has_no_target_id(self):
        """Ingest should surface the current Delivery 1 SIMS capability gap explicitly."""
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=None)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is False
        assert result.message == "SIMS target ID allocation capability incomplete"
        assert result.error_details is not None
        assert "Delivery 1 materialization" in result.error_details
        assert "target-facing integer ID" in result.error_details

    @pytest.mark.asyncio
    async def test_ingest_runs_mixed_pilot_bundle(self, tmp_path):
        """Ingest should handle a mixed pilot bundle with existing, allocated, reconciled, and bridge rows."""
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "system_id": [1, 2],
                                "sample_id": [101, None],
                                "sample_name": ["Existing Sample", "New Sample"],
                            }
                        ),
                        "taxon": pd.DataFrame(
                            {
                                "system_id": [10, 11],
                                "taxon_id": [9001, None],
                                "taxon_name": ["Existing Taxon", "Reconciled Taxon"],
                            }
                        ),
                        "sample_taxon": pd.DataFrame(
                            {
                                "sample_id": [2],
                                "taxon_id": [11],
                                "abundance": [3],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"},
                        taxon={"role": "classifier", "public_id": "taxon_id", "target_table": "tbl_taxon"},
                        sample_taxon={
                            "role": "bridge",
                            "target_table": "tbl_sample_taxon",
                            "unique_sets": [["sample_id", "taxon_id"]],
                            "foreign_keys": [{"entity": "sample"}, {"entity": "taxon"}],
                        },
                    ),
                    "submission_context": minimal_submission_context(change_request_name="deploy/mixed-pilot"),
                    "sims_client": sims_client,
                    "reconciliation_client": FakeReconciliationClient(target_id=9200),
                    "collision_checker": FakeCollisionChecker(),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is True
        assert result.message.startswith("Deploy artifact emitted to '")
        assert result.tables_processed == 2
        assert result.records_inserted == 2
        assert result.error_details is None
        assert sims_client.associated_change_requests == [("binding-123", "deploy/mixed-pilot")]
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["binding_set_uuid"] == "binding-123"
        assert result.deploy_artifact["metadata"]["change_request_name"] == "deploy/mixed-pilot"
        assert result.deploy_artifact["metadata"]["change_request_associated"] is True
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata"]["verify_placeholder"] is True
        assert result.deploy_artifact["metadata_artifact"]["deploy_statement_count"] == 2
        assert result.deploy_artifact["metadata_artifact"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["verify_placeholder"] is True
        assert 'INSERT INTO "tbl_sample" ("system_id", "sample_id", "sample_name") VALUES (2, 501, ' in result.deploy_artifact["deploy_sql"]
        assert (
            'INSERT INTO "tbl_sample_taxon" ("sample_id", "taxon_id", "abundance") VALUES (501, 9200, 3);'
            in result.deploy_artifact["deploy_sql"]
        )
        assert "tbl_taxon" not in result.deploy_artifact["deploy_sql"]
        assert "Existing Sample" not in result.deploy_artifact["deploy_sql"]
        assert (tmp_path / "deploy_mixed-pilot" / "deploy.sql").exists()
        assert (tmp_path / "deploy_mixed-pilot" / "verify.sql").exists()
        assert (tmp_path / "deploy_mixed-pilot" / "metadata.json").exists()

    @pytest.mark.asyncio
    async def test_ingest_runs_mixed_pilot_bundle_with_backend_bridge_adapter(self, tmp_path):
        """Ingest should handle bridge rows through the real backend adapter seam."""
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)))
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "system_id": [1, 2],
                                "sample_id": [101, None],
                                "sample_name": ["Existing Sample", "New Sample"],
                            }
                        ),
                        "taxon": pd.DataFrame(
                            {
                                "system_id": [10, 11],
                                "taxon_id": [9001, None],
                                "taxon_name": ["Existing Taxon", "Reconciled Taxon"],
                            }
                        ),
                        "sample_taxon": pd.DataFrame(
                            {
                                "sample_id": [2],
                                "taxon_id": [11],
                                "abundance": [3],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"},
                        taxon={"role": "classifier", "public_id": "taxon_id", "target_table": "tbl_taxon"},
                        sample_taxon={
                            "role": "bridge",
                            "target_table": "tbl_sample_taxon",
                            "unique_sets": [["sample_id", "taxon_id"]],
                            "foreign_keys": [{"entity": "sample"}, {"entity": "taxon"}],
                        },
                    ),
                    "submission_context": minimal_submission_context(change_request_name="deploy/backend-bridge"),
                    "sims_client": adapter,
                    "reconciliation_client": FakeReconciliationClient(target_id=9200),
                    "collision_checker": FakeCollisionChecker(),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is True
        assert result.records_inserted == 2
        assert result.deploy_artifact is not None
        assert (
            'INSERT INTO "tbl_sample_taxon" ("sample_id", "taxon_id", "abundance") VALUES (501, 9200, 3);'
            in result.deploy_artifact["deploy_sql"]
        )
        assert (tmp_path / "deploy_backend-bridge" / "deploy.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_associates_change_request_after_confirmation(self, tmp_path):
        """Ingest should associate the requested CR name after Binding Set confirmation succeeds."""
        sims_client = FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="confirmed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(change_request_name="deploy/test-change"),
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingester.ingest("submission.xlsx", validate_first=False)

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert sims_client.associated_change_requests == [("binding-123", "deploy/test-change")]
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["change_request_associated"] is True
        assert (tmp_path / "deploy_test-change" / "deploy.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_returns_validation_failure_for_unknown_target_model_table(self):
        """Ingest should stop when the source bundle and target model do not align."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(site={"role": "fact", "public_id": "site_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is False
        assert result.message == "Validation failed"
        assert result.error_details == "Source table 'sample' is not present in the target model"
