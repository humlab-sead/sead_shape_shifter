"""Tests for SEAD change request input resolution of the run ID."""

from datetime import datetime

import pytest

from backend.app.ingesters import IngesterConfig
from ingesters.sead_change_request.contracts import SubmissionContext
from ingesters.sead_change_request.input_resolution import (
    DeployStrategyError,
    _resolve_deploy_strategy,
    _resolve_run_id,
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
