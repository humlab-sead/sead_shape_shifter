"""Tests for CSV file loader."""

import tempfile
from pathlib import Path

import pytest

from src.config_model import DataSourceConfig
from src.loaders.file_loaders import CsvLoader


class TestCsvLoader:
    """Tests for CSV loader."""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Should successfully test connection to existing CSV file."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name,value\n")
            f.write("1,Alice,100\n")
            f.write("2,Bob,200\n")
            temp_path = f.name

        try:
            config = DataSourceConfig(
                name="test_csv",
                cfg={
                    "driver": "csv",
                    "options": {
                        "filename": temp_path,
                    },
                },
            )

            loader = CsvLoader(data_source=config)
            result = await loader.test_connection()

            assert result.success
            assert "accessible" in result.message.lower()
            assert result.connection_time_ms >= 0
            assert result.metadata["column_count"] == 3
            assert result.metadata["columns"] == ["id", "name", "value"]
            assert "file_size_bytes" in result.metadata

        finally:
            # Clean up
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_connection_file_not_found(self):
        """Should fail when CSV file doesn't exist."""
        config = DataSourceConfig(
            name="test_csv",
            cfg={
                "driver": "csv",
                "options": {
                    "filename": "/nonexistent/path/file.csv",
                },
            },
        )

        loader = CsvLoader(data_source=config)
        result = await loader.test_connection()

        assert not result.success
        assert "not found" in result.message.lower() or "failed" in result.message.lower()
        assert result.connection_time_ms >= 0

    @pytest.mark.asyncio
    async def test_connection_missing_filename(self):
        """Should fail when filename is not provided."""
        config = DataSourceConfig(
            name="test_csv",
            cfg={
                "driver": "csv",
                "options": {},
            },
        )

        loader = CsvLoader(data_source=config)
        result = await loader.test_connection()

        assert not result.success
        assert "filename" in result.message.lower()
        assert result.connection_time_ms >= 0

    @pytest.mark.asyncio
    async def test_connection_with_custom_separator(self):
        """Should test connection with custom CSV separator."""
        # Create a temporary CSV file with semicolon separator
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id;name;value\n")
            f.write("1;Alice;100\n")
            f.write("2;Bob;200\n")
            temp_path = f.name

        try:
            config = DataSourceConfig(
                name="test_csv",
                cfg={
                    "driver": "csv",
                    "options": {
                        "filename": temp_path,
                        "sep": ";",
                    },
                },
            )

            loader = CsvLoader(data_source=config)
            result = await loader.test_connection()

            assert result.success
            assert result.metadata["column_count"] == 3

        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_connection_invalid_csv_format(self):
        """Should handle invalid CSV format gracefully."""
        # Create a file with invalid CSV content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("This is not a valid CSV\n")
            f.write("Just some random text\n")
            temp_path = f.name

        try:
            config = DataSourceConfig(
                name="test_csv",
                cfg={
                    "driver": "csv",
                    "options": {
                        "filename": temp_path,
                    },
                },
            )

            loader = CsvLoader(data_source=config)
            result = await loader.test_connection()

            # Should still succeed - pandas can read this as a 1-column CSV
            assert result.success

        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_connection_empty_file(self):
        """Should handle empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Write nothing
            temp_path = f.name

        try:
            config = DataSourceConfig(
                name="test_csv",
                cfg={
                    "driver": "csv",
                    "options": {
                        "filename": temp_path,
                    },
                },
            )

            loader = CsvLoader(data_source=config)
            result = await loader.test_connection()

            # pandas will throw an error for empty file
            assert not result.success

        finally:
            Path(temp_path).unlink()
