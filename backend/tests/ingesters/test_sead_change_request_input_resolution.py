"""Tests for SEAD change request input resolution of the run ID."""

from datetime import datetime

from backend.app.ingesters import IngesterConfig
from ingesters.sead_change_request.contracts import SubmissionContext
from ingesters.sead_change_request.input_resolution import _resolve_run_id, _resolve_submission_context


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
