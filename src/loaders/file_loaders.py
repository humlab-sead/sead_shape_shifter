from typing import TYPE_CHECKING, Any

import pandas as pd

from src.utility import dotget

from .base_loader import DataLoader, DataLoaders

if TYPE_CHECKING:
    from src.config_model import DataSourceConfig, TableConfig


class FileLoader(DataLoader):
    """Loader for CSV files."""

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        super().__init__(data_source=data_source)

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


@DataLoaders.register(key="csv")
class CsvLoader(FileLoader):
    """Loader for CSV/TSV files."""

    async def load_file(self, opts: dict[str, Any]) -> pd.DataFrame:  # type: ignore[unused-argument]
        """Load data from a delimited text file into a DataFrame."""
        clean_opts: dict[str, Any] = dict(opts)
        try:
            filename: str = clean_opts.pop('filename')
        except KeyError:
            raise ValueError(f"Missing 'filename' in options for CSV loader")    
        df: pd.DataFrame = pd.read_csv(filename, **clean_opts)
        return df
