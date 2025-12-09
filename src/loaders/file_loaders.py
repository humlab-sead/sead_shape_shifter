from pathlib import Path

import pandas as pd

from src.arbodat.config_model import TableConfig
from src.arbodat.loaders.interface import DataLoader
from src.utility import dotget


class FileLoader(DataLoader):
    """Loader for CSV files."""

    def __init__(self, sep: str = ",") -> None:
        self.sep = sep

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        """Load data from a CSV file into a DataFrame."""
        if not self.get_loader_opts(table_cfg):
            raise ValueError(f"TableConfig for entity '{entity_name}' has no source defined")

        filepath: str = self.resolve_filepath(table_cfg)
        if not Path(filepath).is_file():
            raise FileNotFoundError(f"File '{filepath}' for entity '{entity_name}' does not exist")

        return await self.load_file(filepath=filepath, opts=self.get_loader_opts(table_cfg))

    async def load_file(self, filepath: str, opts: dict[str, str]) -> pd.DataFrame:  # type: ignore[unused-argument]
        raise TypeError("Subclasses must implement load_file method")

    def resolve_filepath(self, table_cfg: TableConfig) -> str:
        """Resolve the file path from the TableConfig source."""
        return dotget(self.get_loader_opts(table_cfg), "filepath,path,filename", "")

    def get_loader_opts(self, table_cfg: TableConfig) -> dict[str, str]:
        """Get loader options from the TableConfig source."""
        if isinstance(table_cfg.source, str):
            return {"filename": table_cfg.source}
        if isinstance(table_cfg.source, dict):
            return table_cfg.source
        return {}


class CsvLoader(FileLoader):
    """Loader for CSV/TSV files."""

    def __init__(self, sep: str = ",") -> None:
        self.sep: str = sep

    async def load_file(self, filepath: str, opts: dict[str, str]) -> pd.DataFrame:  # type: ignore[unused-argument]
        """Load data from a CSV file into a DataFrame."""
        df: pd.DataFrame = pd.read_csv(filepath, sep=dotget(opts, "sep,delimiter", self.sep))
        return df
