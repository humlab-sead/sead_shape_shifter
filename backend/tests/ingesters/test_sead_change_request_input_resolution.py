"""Tests for SEAD change request input resolution of the run ID."""

from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from backend.app.ingesters import IngesterConfig
from ingesters.sead_change_request.contracts import (
    CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE,
    SourceTableBundle,
    SubmissionContext,
)
from ingesters.sead_change_request.input_resolution import (
    DeployStrategyError,
    SourceBundleError,
    _build_source_bundle,
    _resolve_deploy_strategy,
    _resolve_run_id,
    _resolve_source_bundle,
    _resolve_staging_target_schema,
    _resolve_submission_context,
)
from ingesters.sead_change_request.sql_builder import (
    COPY_CSV_DEPLOY_ARTIFACT_STRATEGY,
    INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY,
    CopyCsvDeployStrategy,
    InlineInsertDeployStrategy,
    InlineStagingDeployStrategy,
)


def _config_with_context(context_data: dict) -> IngesterConfig:
    return IngesterConfig(
        host="localhost",
        port=5432,
        dbname="test_db",
        user="test_user",
        submission_name="test_submission",
        data_types="test",
        extra={"submission_context": context_data},
    )


class TestResolveRunId:
    """Tests for run-ID persistence and minting."""

    def test_persisted_run_id_is_preserved(self):
        run_id = _resolve_run_id({"run_id": "run-123"})

        assert run_id == "run-123"

    def test_missing_run_id_mints_a_uuid(self):
        run_id = _resolve_run_id({})

        assert run_id is not None
        assert run_id != ""

    def test_submission_context_preserves_supplied_run_id(self):
        context = _resolve_submission_context(
            _config_with_context(
                {
                    "submission_name": "test-submission",
                    "project_name": "test-project",
                    "timestamp": "2026-05-23T22:00:00",
                    "datatype": "mal",
                    "identifier": "TEST_SUBMISSION",
                    "run_id": "run-456",
                }
            )
        )

        assert context.run_id == "run-456"

    def test_submission_context_mints_run_id_when_absent(self):
        context = _resolve_submission_context(
            _config_with_context(
                {
                    "submission_name": "test-submission",
                    "project_name": "test-project",
                    "timestamp": "2026-05-23T22:00:00",
                    "datatype": "mal",
                    "identifier": "TEST_SUBMISSION",
                }
            )
        )

        assert context.run_id is not None
        assert context.run_id != ""

    def test_submission_context_instance_mints_run_id_when_absent(self):
        existing = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime(2026, 5, 23, 22, 0, 0),
        )
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            submission_name="test_submission",
            data_types="test",
            extra={"submission_context": existing},
        )

        context = _resolve_submission_context(config)

        assert context.run_id is not None
        assert context.run_id != ""


class TestResolveDeployStrategy:
    """Tests for selecting a deploy strategy and its required staging schema."""

    def test_absent_strategy_keeps_the_direct_default(self):
        config = _config_with_context({})

        strategy = _resolve_deploy_strategy(config)

        assert isinstance(strategy, InlineInsertDeployStrategy)
        assert _resolve_staging_target_schema(config) is None

    def test_copy_csv_stays_available_without_a_staging_schema(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"deploy_strategy": COPY_CSV_DEPLOY_ARTIFACT_STRATEGY},
        )

        strategy = _resolve_deploy_strategy(config)

        assert isinstance(strategy, CopyCsvDeployStrategy)

    def test_inline_staging_uses_the_explicit_schema(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"deploy_strategy": INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY, "staging_target_schema": "public"},
        )

        strategy = _resolve_deploy_strategy(config, _resolve_staging_target_schema(config))

        assert isinstance(strategy, InlineStagingDeployStrategy)
        assert strategy.target_schema == "public"

    def test_inline_staging_requires_a_schema(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"deploy_strategy": INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY},
        )

        with pytest.raises(DeployStrategyError, match="requires a non-empty 'staging_target_schema'"):
            _resolve_deploy_strategy(config)

    @pytest.mark.parametrize("unsafe_schema", ["public; DROP TABLE x", "1public", "pub lic", ""])
    def test_inline_staging_rejects_an_unsafe_schema(self, unsafe_schema: str):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"deploy_strategy": INLINE_STAGING_DEPLOY_ARTIFACT_STRATEGY, "staging_target_schema": unsafe_schema},
        )

        with pytest.raises(DeployStrategyError):
            _resolve_deploy_strategy(config, _resolve_staging_target_schema(config))

    def test_non_string_staging_schema_is_rejected(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"staging_target_schema": 7},
        )

        with pytest.raises(DeployStrategyError, match="must be a string"):
            _resolve_staging_target_schema(config)

    def test_direct_strategy_rejects_a_staging_schema(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"staging_target_schema": "public"},
        )

        with pytest.raises(DeployStrategyError, match="does not accept 'staging_target_schema'"):
            _resolve_deploy_strategy(config, _resolve_staging_target_schema(config))


class TestResolveSourceBundle:
    """The retired file input must fail before config extras or file access."""

    @pytest.mark.parametrize("source", ["submission.xlsx", Path("submission.xlsx")])
    def test_string_and_path_sources_are_rejected(self, source: str | Path):
        config = IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user")

        with pytest.raises(SourceBundleError, match=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE):
            _resolve_source_bundle(config, source)

    @pytest.mark.parametrize(
        "extras",
        [
            {},
            {"source_bundle": SourceTableBundle(tables={"sample": pd.DataFrame({"sample_id": [1]})})},
            {"tables": {"sample": pd.DataFrame({"sample_id": [1]})}},
        ],
    )
    @pytest.mark.parametrize("source", ["submission.xlsx", Path("submission.xlsx")])
    def test_path_shaped_sources_cannot_select_extras(self, source: str | Path, extras: dict):
        config = IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user", extra=extras)

        with pytest.raises(SourceBundleError, match=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE):
            _resolve_source_bundle(config, source)

    def test_path_source_is_rejected_without_reading_the_file(self, tmp_path: Path):
        source_path = tmp_path / "submission.xlsx"
        source_path.write_bytes(b"not a workbook")
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"tables": {"sample": pd.DataFrame({"sample_id": [1]})}},
        )

        with pytest.raises(SourceBundleError, match=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE):
            _resolve_source_bundle(config, source_path)

    def test_source_bundle_argument_is_accepted(self):
        bundle = SourceTableBundle(tables={"sample": pd.DataFrame({"sample_id": [1]})})
        config = IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user")

        assert _resolve_source_bundle(config, bundle) is bundle

    def test_configured_source_bundle_is_accepted(self):
        bundle = SourceTableBundle(tables={"sample": pd.DataFrame({"sample_id": [1]})})
        config = IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user", extra={"source_bundle": bundle})

        assert _resolve_source_bundle(config, None) is bundle

    def test_configured_tables_are_built_into_a_bundle(self):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            extra={"tables": {"sample": pd.DataFrame({"sample_id": [1]})}},
        )

        bundle = _resolve_source_bundle(config, None)

        assert list(bundle.tables) == ["sample"]

    def test_non_dataframe_table_values_are_rejected_when_building_the_bundle(self):
        with pytest.raises(SourceBundleError, match="must be a pandas DataFrame"):
            _build_source_bundle({"sample": [{"sample_id": 1}]})

    def test_empty_table_mappings_are_rejected_when_building_the_bundle(self):
        with pytest.raises(SourceBundleError, match="No source tables were provided"):
            _build_source_bundle({})


class TestBuildSourceBundle:
    """The adapter copies caller frames and sanitizes only the copied columns."""

    def test_preserves_entity_names_values_dtypes_and_timezones(self):
        source_frame = pd.DataFrame(
            {
                "Sample ID": [1, 2],
                "Collected At": pd.Series(pd.to_datetime(["2026-05-23 10:15:00+02:00", "2026-05-24 11:30:00+02:00"])).dt.tz_convert(
                    "Europe/Stockholm"
                ),
            }
        )
        original_columns = source_frame.columns.tolist()

        bundle = _build_source_bundle({"sample": source_frame}, source_name="normalized submission")

        expected_frame = source_frame.copy()
        expected_frame.columns = ["sample_id", "collected_at"]
        copied_frame = bundle.tables["sample"]

        assert bundle.source_name == "normalized submission"
        assert list(bundle.tables) == ["sample"]
        assert copied_frame is not source_frame
        assert source_frame.columns.tolist() == original_columns
        assert_frame_equal(copied_frame, expected_frame)
        assert str(copied_frame["collected_at"].dt.tz) == "Europe/Stockholm"

    def test_sanitized_duplicate_columns_remain_unique(self):
        source_frame = pd.DataFrame([[1, 2]], columns=["Sample ID", "Sample ID"])

        bundle = _build_source_bundle({"sample": source_frame})

        assert bundle.tables["sample"].columns.tolist() == ["sample_id", "sample_id_1"]

    def test_internal_workflow_columns_keep_their_labels(self):
        source_frame = pd.DataFrame(
            {
                "Sample Name": ["new name"],
                "sample_name__existing": ["old name"],
                "_row_state": ["existing_entity"],
            }
        )

        bundle = _build_source_bundle({"sample": source_frame})

        assert bundle.tables["sample"].columns.tolist() == ["sample_name", "sample_name__existing", "_row_state"]

    def test_mapping_instances_are_accepted_by_source_resolution(self):
        config = IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user")
        source = MappingProxyType({"sample": pd.DataFrame({"sample_id": [1]})})

        bundle = _resolve_source_bundle(config, source)

        assert list(bundle.tables) == ["sample"]
        assert bundle.tables["sample"]["sample_id"].tolist() == [1]

    def test_blank_table_names_are_rejected(self):
        with pytest.raises(SourceBundleError, match="must be non-empty strings"):
            _build_source_bundle({"   ": pd.DataFrame({"sample_id": [1]})})

    def test_non_string_table_names_are_rejected(self):
        with pytest.raises(SourceBundleError, match="must be non-empty strings"):
            _build_source_bundle({1: pd.DataFrame({"sample_id": [1]})})  # type: ignore[dict-item]
