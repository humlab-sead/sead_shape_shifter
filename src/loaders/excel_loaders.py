from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import openpyxl
import pandas as pd

from src.loaders.driver_metadata import DriverSchema, FieldMetadata
from src.loaders.file_loaders import FileLoader

from .base_loader import ConnectTestResult, DataLoaders, LoaderType

if TYPE_CHECKING:
    from src.model import TableConfig


class ExcelLoader(FileLoader):
    """Loader for Excel files."""

    @classmethod
    def loader_type(cls) -> LoaderType:
        """Get the loader type."""
        return LoaderType.FILE

    def get_loader_opts(self, table_cfg: "TableConfig") -> dict[str, str]:
        """Get loader options from the TableConfig or data source.

        Base FileLoader already handles filename/options on the table config or data source.
        We extend it to also respect a shorthand sheet name when provided as `source`.
        """
        opts: dict[str, str] = super().get_loader_opts(table_cfg)

        # If the sheet is specified via `source: <sheet>` keep the filename from options
        # and just add sheet_name instead of replacing the whole options dict.
        if isinstance(table_cfg.source, str) and table_cfg.source:
            opts.setdefault("sheet_name", table_cfg.source)

        return opts


@DataLoaders.register(key=["xlsx", "xls"])
class PandasLoader(ExcelLoader):
    """Loader for Excel files using pandas."""

    schema: ClassVar["DriverSchema | None"] = DriverSchema(
        driver="xlsx",
        display_name="Excel File (pandas)",
        description="Excel file loader using pandas",
        category="file",
        fields=[
            FieldMetadata(
                name="filename",
                type="file_path",
                required=True,
                description="Path to .xlsx or .xls file",
                placeholder="./data/file.xlsx",
                aliases=["file", "filepath", "path"],
                extensions=["xlsx", "xls"],
            ),
            FieldMetadata(
                name="sheet_name",
                type="string",
                required=False,
                description="Sheet name to load",
                placeholder="Sheet1",
            ),
        ],
    )

    async def load_file(self, opts: dict[str, Any]) -> pd.DataFrame:  # type: ignore[unused-argument]
        """Load data from a sheet in an Excel file into a DataFrame."""
        clean_opts: dict[str, Any] = dict(opts)
        filename: str = clean_opts.pop("filename")
        sheet_name: str | None = clean_opts.pop("sheet_name", None)
        file_path = Path(filename)
        df: pd.DataFrame | dict[str, pd.DataFrame] = pd.read_excel(file_path, sheet_name=sheet_name, **clean_opts)
        if not isinstance(df, pd.DataFrame):
            raise ValueError("ExcelLoader currently supports loading a single sheet only.")
        
        # Clean up column names: ensure all are strings to avoid NaN/float column names
        df.columns = [str(col) if isinstance(col, str) else f"Unnamed_{i}" for i, col in enumerate(df.columns)]
        
        return df

    async def test_connection(self) -> ConnectTestResult:
        """Test file-based connection (Excel)."""
        return ConnectTestResult(success=True, message="No test performed", connection_time_ms=0, metadata={})


@DataLoaders.register(key=["openpyxl"])
class OpenPyxlLoader(ExcelLoader):
    """Loader for Excel files using openpyxl."""

    schema: ClassVar["DriverSchema | None"] = DriverSchema(
        driver="openpyxl",
        display_name="Excel File (openpyxl)",
        description="Excel file loader using openpyxl with range support",
        category="file",
        fields=[
            FieldMetadata(
                name="filename",
                type="file_path",
                required=True,
                description="Path to .xlsx file",
                placeholder="./data/file.xlsx",
                aliases=["file", "filepath", "path"],
                extensions=["xlsx", "xls"],
            ),
            FieldMetadata(
                name="sheet_name",
                type="string",
                required=False,
                description="Sheet name to load",
                placeholder="Sheet1",
            ),
            FieldMetadata(
                name="range",
                type="string",
                required=False,
                description="Cell range to load (e.g., A1:D10)",
                placeholder="A1:D10",
            ),
        ],
    )

    async def load_file(self, opts: dict[str, Any]) -> pd.DataFrame:  # type: ignore[unused-argument]
        """Load data from a sheet in an Excel file into a DataFrame."""
        filename: str | None = opts.get("filename")
        if not filename:
            raise ValueError("Missing 'filename' in options for Excel loader")

        file_path = Path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        sheet_name: str | None = opts.get("sheet_name", None)

        workbook: openpyxl.Workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

        worksheet: Any = workbook.active if sheet_name is None else workbook[sheet_name]

        if worksheet is None:
            raise ValueError(f"Sheet '{sheet_name}' not found in Excel file '{filename}'")

        cell_range: str | None = opts.get("range", None)

        if cell_range is None:
            data = worksheet.values
        else:
            data = ([cell.value for cell in row] for row in worksheet[cell_range])

        header: bool = opts.get("header", True)

        columns = next(data) if header else None
        
        # Clean up column names: convert None/NaN to string to avoid issues downstream
        if columns is not None:
            columns = [str(col) if col is not None else f"Unnamed_{i}" for i, col in enumerate(columns)]
        
        df = pd.DataFrame(data, columns=columns)
        if isinstance(header, list):
            if len(header) != len(df.columns):
                raise ValueError("Length of provided header does not match number of columns in data")
            df.columns = header
        elif not header:
            df.columns = [f"C_{i+1}" for i in range(len(df.columns))]

        return df

    async def test_connection(self) -> ConnectTestResult:
        """Test file-based connection (Excel)."""
        return ConnectTestResult(success=True, message="No test performed", connection_time_ms=0, metadata={})
