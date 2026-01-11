"""Tests for the ingest CLI tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from backend.app.models.ingester import (
    IngesterMetadataResponse,
    IngestResponse,
    ValidateResponse,
)
from backend.app.scripts.ingest import cli


class TestIngestCLI:
    """Test the ingest CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_list_ingesters(self):
        """Test listing available ingesters."""
        mock_ingesters = [
            IngesterMetadataResponse(
                key="sead",
                name="SEAD Clearinghouse",
                description="Ingest SEAD data",
                version="1.0.0",
                supported_formats=["xlsx"],
            )
        ]

        with patch(
            "backend.app.scripts.ingest.IngesterService.list_ingesters",
            return_value=mock_ingesters,
        ):
            result = self.runner.invoke(cli, ["list-ingesters"])

        assert result.exit_code == 0
        assert "SEAD Clearinghouse" in result.output
        assert "sead" in result.output
        assert "1.0.0" in result.output

    def test_list_ingesters_empty(self):
        """Test listing when no ingesters are available."""
        with patch(
            "backend.app.scripts.ingest.IngesterService.list_ingesters",
            return_value=[],
        ):
            result = self.runner.invoke(cli, ["list-ingesters"])

        assert result.exit_code == 0
        assert "No ingesters available" in result.output

    def test_validate_success(self, tmp_path):
        """Test successful validation."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        mock_response = ValidateResponse(
            is_valid=True, errors=[], warnings=["Warning 1"]
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.validate", new=async_mock
        ):
            result = self.runner.invoke(
                cli, ["validate", "sead", str(test_file)]
            )

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output
        assert "Warning 1" in result.output

    def test_validate_failure(self, tmp_path):
        """Test failed validation."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        mock_response = ValidateResponse(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=[]
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.validate", new=async_mock
        ):
            result = self.runner.invoke(
                cli, ["validate", "sead", str(test_file)]
            )

        assert result.exit_code == 1
        assert "VALIDATION FAILED" in result.output
        assert "Error 1" in result.output
        assert "Error 2" in result.output

    def test_validate_with_config(self, tmp_path):
        """Test validation with config file."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        config_file = tmp_path / "config.json"
        config_file.write_text('{"ignore_columns": ["col1"]}')

        mock_response = ValidateResponse(is_valid=True, errors=[], warnings=[])

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.validate", new=async_mock
        ) as mock_validate:
            result = self.runner.invoke(
                cli, ["validate", "sead", str(test_file), "--config", str(config_file)]
            )

        assert result.exit_code == 0
        # Verify config was passed
        call_args = mock_validate.call_args
        assert call_args[0][1].config["ignore_columns"] == ["col1"]

    def test_ingest_success(self, tmp_path):
        """Test successful ingestion."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        mock_response = IngestResponse(
            success=True,
            records_processed=100,
            message="Ingestion complete",
            submission_id=42,
            output_path="/output/test",
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.ingest", new=async_mock
        ):
            result = self.runner.invoke(
                cli,
                [
                    "ingest",
                    "sead",
                    str(test_file),
                    "--submission-name",
                    "test",
                    "--data-types",
                    "test_data",
                ],
            )

        assert result.exit_code == 0
        assert "INGESTION SUCCESSFUL" in result.output
        assert "100" in result.output
        assert "42" in result.output

    def test_ingest_failure(self, tmp_path):
        """Test failed ingestion."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        mock_response = IngestResponse(
            success=False, records_processed=0, message="Ingestion failed: error"
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.ingest", new=async_mock
        ):
            result = self.runner.invoke(
                cli,
                [
                    "ingest",
                    "sead",
                    str(test_file),
                    "--submission-name",
                    "test",
                    "--data-types",
                    "test_data",
                ],
            )

        assert result.exit_code == 1
        assert "INGESTION FAILED" in result.output
        assert "error" in result.output

    def test_ingest_with_database_options(self, tmp_path):
        """Test ingestion with database options."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        mock_response = IngestResponse(
            success=True, records_processed=50, message="Success"
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.ingest", new=async_mock
        ) as mock_ingest:
            result = self.runner.invoke(
                cli,
                [
                    "ingest",
                    "sead",
                    str(test_file),
                    "--submission-name",
                    "test",
                    "--data-types",
                    "test_data",
                    "--database-host",
                    "testhost",
                    "--database-port",
                    "5433",
                    "--database-name",
                    "testdb",
                    "--database-user",
                    "testuser",
                    "--register",
                    "--explode",
                ],
            )

        assert result.exit_code == 0

        # Verify database config was passed
        call_args = mock_ingest.call_args
        request = call_args[0][1]
        assert request.config["database"]["host"] == "testhost"
        assert request.config["database"]["port"] == 5433
        assert request.config["database"]["dbname"] == "testdb"
        assert request.config["database"]["user"] == "testuser"
        assert request.do_register is True
        assert request.explode is True

    def test_ingest_missing_required_options(self, tmp_path):
        """Test ingestion fails without required options."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        # Missing --submission-name
        result = self.runner.invoke(
            cli, ["ingest", "sead", str(test_file), "--data-types", "test"]
        )
        assert result.exit_code != 0

        # Missing --data-types
        result = self.runner.invoke(
            cli, ["ingest", "sead", str(test_file), "--submission-name", "test"]
        )
        assert result.exit_code != 0

    def test_validate_nonexistent_file(self):
        """Test validation with nonexistent file."""
        result = self.runner.invoke(
            cli, ["validate", "sead", "/nonexistent/file.xlsx"]
        )
        assert result.exit_code != 0

    def test_ingest_with_config_file(self, tmp_path):
        """Test ingestion with config file."""
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("test data")

        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{"database": {"host": "confighost", "port": 5432, "dbname": "configdb", "user": "configuser"}}'
        )

        mock_response = IngestResponse(
            success=True, records_processed=75, message="Success"
        )

        async_mock = AsyncMock(return_value=mock_response)

        with patch(
            "backend.app.scripts.ingest.IngesterService.ingest", new=async_mock
        ) as mock_ingest:
            result = self.runner.invoke(
                cli,
                [
                    "ingest",
                    "sead",
                    str(test_file),
                    "--submission-name",
                    "test",
                    "--data-types",
                    "test_data",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0

        # Verify config file was loaded
        call_args = mock_ingest.call_args
        request = call_args[0][1]
        assert request.config["database"]["host"] == "confighost"
        assert request.config["database"]["dbname"] == "configdb"
