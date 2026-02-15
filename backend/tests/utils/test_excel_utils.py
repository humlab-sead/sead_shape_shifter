"""Tests for backend.app.utils.excel_utils module."""

from pathlib import Path

import pandas as pd
import pytest

from backend.app.utils.excel_utils import _parse_cell_range_max_column, get_excel_metadata
from backend.app.utils.exceptions import BadRequestError


class TestParseCellRangeMaxColumn:
    """Test _parse_cell_range_max_column helper function."""

    def test_parse_simple_range(self):
        """Test parsing simple A1:H30 format."""
        result = _parse_cell_range_max_column("A1:H30")
        assert result == 7  # H is the 8th column (0-indexed = 7)

    def test_parse_column_only_range(self):
        """Test parsing A:Z format."""
        result = _parse_cell_range_max_column("A:Z")
        assert result == 25  # Z is the 26th column (0-indexed = 25)

    def test_parse_double_letter_column(self):
        """Test parsing ranges with AA, AB, etc."""
        result = _parse_cell_range_max_column("A1:AA10")
        assert result == 26  # AA is the 27th column (0-indexed = 26)

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        result1 = _parse_cell_range_max_column("a1:h30")
        result2 = _parse_cell_range_max_column("A1:H30")
        assert result1 == result2 == 7

    def test_parse_single_column_A(self):
        """Test parsing for column A."""
        result = _parse_cell_range_max_column("A1:A10")
        assert result == 0  # A is the 1st column (0-indexed = 0)

    def test_parse_triple_letter_column(self):
        """Test parsing AAA column."""
        result = _parse_cell_range_max_column("A1:AAA100")
        # AAA = 26*26 + 26 + 1 = 703 (1-indexed) = 702 (0-indexed)
        assert result == 702

    def test_parse_no_colon_returns_zero(self):
        """Test that missing colon returns 0."""
        result = _parse_cell_range_max_column("A1")
        assert result == 0


class TestGetExcelMetadata:
    """Test get_excel_metadata function."""

    @pytest.fixture
    def temp_excel_file(self, tmp_path: Path) -> Path:
        """Create a temporary Excel file for testing."""
        file_path = tmp_path / "test.xlsx"

        # Create test data with multiple sheets
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df1 = pd.DataFrame(
                {
                    "Column A": [1, 2, 3],
                    "Column B": [4, 5, 6],
                    "Column C": [7, 8, 9],
                    "Column D": [10, 11, 12],
                }
            )
            df2 = pd.DataFrame(
                {
                    "Name": ["Alice", "Bob"],
                    "Age": [30, 25],
                }
            )
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

        return file_path

    def test_get_sheets_and_columns_default(self, temp_excel_file: Path):
        """Test getting sheets and columns from first sheet."""
        sheets, columns = get_excel_metadata(temp_excel_file)

        assert sheets == ["Sheet1", "Sheet2"]
        assert columns == ["column_a", "column_b", "column_c", "column_d"]  # Sanitized

    def test_get_columns_from_specific_sheet(self, temp_excel_file: Path):
        """Test getting columns from specific sheet."""
        sheets, columns = get_excel_metadata(temp_excel_file, sheet_name="Sheet2")

        assert sheets == ["Sheet1", "Sheet2"]
        assert columns == ["name", "age"]  # Sanitized

    def test_get_columns_with_range(self, temp_excel_file: Path):
        """Test limiting columns with cell range."""
        sheets, columns = get_excel_metadata(temp_excel_file, cell_range="A1:B10")

        assert sheets == ["Sheet1", "Sheet2"]
        assert columns == ["column_a", "column_b"]  # Only first 2 columns

    def test_unsupported_file_format(self, tmp_path: Path):
        """Test that non-Excel files raise error."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\\n1,2\\n")

        with pytest.raises(BadRequestError, match="Only .xlsx and .xls files"):
            get_excel_metadata(csv_file)

    def test_sheet_not_found(self, temp_excel_file: Path):
        """Test error when specified sheet doesn't exist."""
        with pytest.raises(BadRequestError, match="Sheet 'NonExistent' not found"):
            get_excel_metadata(temp_excel_file, sheet_name="NonExistent")

    def test_file_not_found(self, tmp_path: Path):
        """Test error when file doesn't exist."""
        missing_file = tmp_path / "missing.xlsx"

        with pytest.raises(BadRequestError, match="Failed to read Excel metadata"):
            get_excel_metadata(missing_file)

    def test_workbook_with_empty_sheet(self, tmp_path: Path):
        """Test handling workbook with empty sheet (no data)."""
        file_path = tmp_path / "empty.xlsx"

        # Create sheet with no data rows (only headers)
        df = pd.DataFrame()
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="EmptySheet", index=False)

        sheets, columns = get_excel_metadata(file_path)

        assert sheets == ["EmptySheet"]
        assert columns == []  # No columns in empty DataFrame

    def test_column_sanitization(self, tmp_path: Path):
        """Test that column names are properly sanitized."""
        file_path = tmp_path / "test_sanitize.xlsx"

        # Create DataFrame with problematic column names
        df = pd.DataFrame(
            {
                "Column With Spaces": [1, 2],
                "Column-With-Dashes": [3, 4],
                "Column.With.Dots": [5, 6],
                "UPPERCASE": [7, 8],
            }
        )

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)

        sheets, columns = get_excel_metadata(file_path)

        # Verify sanitization rules:
        # - Spaces → underscores
        # - Dashes → removed
        # - Dots → removed
        # - Uppercase → lowercase
        assert "column_with_spaces" in columns
        assert "columnwithdashes" in columns  # Dashes removed, not replaced
        assert "columnwithdots" in columns  # Dots removed, not replaced
        assert "uppercase" in columns

    def test_range_with_triple_letter_column(self, tmp_path: Path):
        """Test range parsing with many columns."""
        file_path = tmp_path / "wide.xlsx"

        # Create DataFrame with many columns (more than 26)
        data = {f"Col_{i}": [1, 2] for i in range(30)}
        df = pd.DataFrame(data)

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)

        # Request only first 10 columns
        sheets, columns = get_excel_metadata(file_path, cell_range="A1:J100")

        assert len(columns) == 10  # A-J = 10 columns
