import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

from src.loaders.driver_metadata import DriverSchema, FieldMetadata

from .base_loader import ConnectTestResult, DataLoader, DataLoaders, LoaderType

if TYPE_CHECKING:
    from src.model import DataSourceConfig, TableConfig


class FileLoader(DataLoader):
    """Loader for CSV files."""

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        super().__init__(data_source=data_source)

    @classmethod
    def loader_type(cls) -> LoaderType:
        """Get the loader type."""
        return LoaderType.FILE

    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        """Load data from a CSV file into a DataFrame."""
        options: dict[str, str] = self.get_loader_opts(table_cfg)
        if not options:
            raise ValueError(f"TableConfig for entity '{entity_name}' has no load options defined")
        return await self.load_file(opts=options)

    async def load_file(self, opts: dict[str, str]) -> pd.DataFrame:  # type: ignore[unused-argument]
        raise TypeError("Subclasses must implement load_file method")

    def get_loader_opts(self, table_cfg: "TableConfig") -> dict[str, str]:
        """Get loader options from the TableConfig source."""
        if self.data_source and self.data_source.options:
            return self.data_source.options
        if table_cfg.options:
            return table_cfg.options
        if isinstance(table_cfg.source, str):
            return {"filename": table_cfg.source}
        if isinstance(table_cfg.source, dict):
            return table_cfg.source
        return {}


@DataLoaders.register(key=["csv", "tsv"])
class CsvLoader(FileLoader):
    """Loader for CSV/TSV files."""

    schema: ClassVar["DriverSchema | None"] = DriverSchema(
        driver="csv",
        display_name="CSV File",
        description="Comma-separated values file",
        category="file",
        fields=[
            FieldMetadata(
                name="filename",
                type="file_path",
                required=True,
                description="Path to .csv file",
                placeholder="./data/file.csv",
                aliases=["file", "filepath", "path"],
            ),
            FieldMetadata(
                name="encoding", type="string", required=False, default="utf-8", description="File encoding", placeholder="utf-8"
            ),
            FieldMetadata(
                name="delimiter",
                type="string",
                required=False,
                default=",",
                description="Field delimiter",
                placeholder=",",
                aliases=["sep", "separator"],
            ),
        ],
    )

    async def load_file(self, opts: dict[str, Any]) -> pd.DataFrame:  # type: ignore[unused-argument]
        """Load data from a delimited text file into a DataFrame."""
        clean_opts: dict[str, Any] = dict(opts)
        try:
            filename: str = clean_opts.pop("filename")
        except KeyError as exc:
            raise ValueError("Missing 'filename' in options for CSV loader") from exc
        df: pd.DataFrame = pd.read_csv(filename, **clean_opts)
        return df

    async def test_connection(self) -> ConnectTestResult:
        """Test file-based connection (CSV).

        Args:
            config: CSV data source configuration

        Returns:
            Test result
        """
        start_time: float = time.time()

        assert self.data_source is not None

        try:
            file_path: str | None = self.data_source.options.get("filename") if self.data_source.options else None
            if not file_path:
                raise ValueError("CSV source requires 'filename' or 'file_path'")

            path: Path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Try to read first few rows
            read_opts: dict[str, Any] = dict(self.data_source.options or {})
            read_opts.pop("filename", None)  # Remove filename to avoid passing it twice
            df: pd.DataFrame = pd.read_csv(file_path, nrows=5, **read_opts)

            elapsed_ms: int = int((time.time() - start_time) * 1000)

            metadata: dict[str, Any] = {
                "file_size_bytes": path.stat().st_size,
                "columns": list(df.columns),
                "column_count": len(df.columns),
            }

            return ConnectTestResult(
                success=True,
                message=f"File accessible ({len(df.columns)} columns detected)",
                connection_time_ms=elapsed_ms,
                metadata=metadata,
            )

        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ConnectTestResult(success=False, message=f"File access failed: {str(e)}", connection_time_ms=elapsed_ms, metadata={})
