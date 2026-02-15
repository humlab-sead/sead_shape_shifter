"""Excel file utilities for metadata extraction and inspection."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.utils.exceptions import BadRequestError
from src.utility import sanitize_columns


def get_excel_metadata(file_path: Path, sheet_name: str | None = None, cell_range: str | None = None) -> tuple[list[str], list[str]]:
    """Extract sheet names and column headers from an Excel file.

    Args:
        file_path: Path to the Excel file (.xlsx or .xls)
        sheet_name: Optional sheet to inspect for columns. If None, uses first sheet.
        cell_range: Optional cell range (e.g., 'A1:H30') to limit columns

    Returns:
        Tuple of (sheet_names, column_names)
        - sheet_names: List of all sheet names in the workbook
        - column_names: List of sanitized column names from the specified/first sheet

    Raises:
        BadRequestError: If file is unsupported format, sheet not found, or read fails

    Examples:
        >>> sheets, columns = get_excel_metadata(Path("data.xlsx"))
        >>> sheets, columns = get_excel_metadata(Path("data.xlsx"), sheet_name="Sheet1")
        >>> sheets, columns = get_excel_metadata(Path("data.xlsx"), cell_range="A1:H30")
    """
    if file_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise BadRequestError("Only .xlsx and .xls files are supported for metadata probing")

    try:
        # Parse cell range to extract maximum column index
        max_col_index: int | None = None
        if cell_range:
            max_col_index = _parse_cell_range_max_column(cell_range)

        with pd.ExcelFile(file_path) as xls:
            sheets: list[str] = list(xls.sheet_names)  # type: ignore

            target_sheet = sheet_name or (sheets[0] if sheets else None)
            columns: list[str] = []

            if target_sheet:
                if target_sheet not in sheets:
                    raise BadRequestError(f"Sheet '{target_sheet}' not found in {file_path.name}")

                # Read only the header row (nrows=0)
                df = pd.read_excel(xls, sheet_name=target_sheet, nrows=0)

                # Sanitize column names to match what the loader will produce
                all_columns = sanitize_columns(list(df.columns))

                # Limit to columns within specified range
                if max_col_index is not None:
                    columns = all_columns[: max_col_index + 1]
                else:
                    columns = all_columns

            return sheets, columns

    except BadRequestError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Failed to read Excel metadata for {file_path}: {exc}")
        raise BadRequestError(f"Failed to read Excel metadata: {exc}") from exc


def _parse_cell_range_max_column(cell_range: str) -> int:
    """Parse Excel cell range to extract maximum column index.

    Supports formats like:
    - "A1:H30" -> extracts "H" -> returns 7 (0-based)
    - "A:H" -> extracts "H" -> returns 7
    - "B5:Z100" -> extracts "Z" -> returns 25

    Args:
        cell_range: Excel cell range string

    Returns:
        Zero-based column index (A=0, B=1, ..., Z=25, AA=26, etc.)

    Examples:
        >>> _parse_cell_range_max_column("A1:H30")
        7
        >>> _parse_cell_range_max_column("A:Z")
        25
        >>> _parse_cell_range_max_column("A1:AA10")
        26
    """
    # Match patterns like "A1:H30" or "A:H" to extract ending column letter
    match = re.search(r":([A-Z]+)", cell_range.upper())
    if not match:
        return 0

    col_letter: str | Any = match.group(1)

    # Convert column letter to 0-based index (A=0, B=1, ..., Z=25, AA=26, etc.)
    max_col_index = 0
    for char in col_letter:
        max_col_index = max_col_index * 26 + (ord(char) - ord("A") + 1)

    return max_col_index - 1  # Convert to 0-based
