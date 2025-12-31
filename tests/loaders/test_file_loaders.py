"""Tests for file loaders."""

import tempfile
from types import SimpleNamespace

import pandas as pd
import pytest

from src.loaders.base_loader import ConnectTestResult
from src.loaders.file_loaders import CsvLoader, FileLoader
from src.model import DataSourceConfig


class DummyFileLoader(FileLoader):
    """Minimal subclass to exercise FileLoader logic."""

    async def load_file(self, opts: dict[str, str]) -> pd.DataFrame:
        return pd.DataFrame({"value": [opts.get("value", "")]})

    async def test_connection(self):

        return ConnectTestResult.create_empty(success=True)


@pytest.mark.asyncio
async def test_get_loader_opts_precedence():
    """Data source options take precedence over table options/source."""
    ds = DataSourceConfig(name="ds", cfg={"driver": "csv", "options": {"value": "from_ds"}})
    table_cfg = SimpleNamespace(options={"value": "from_table"}, source={"value": "from_source"})

    loader = DummyFileLoader(data_source=ds)
    result = await loader.load("entity", table_cfg)  # type: ignore

    assert result["value"].iloc[0] == "from_ds"


@pytest.mark.asyncio
async def test_file_loader_load_requires_options():
    """load should raise when no options are available."""
    loader = DummyFileLoader()
    table_cfg = SimpleNamespace(options=None, source=None)

    with pytest.raises(ValueError, match="no load options"):
        await loader.load("e", table_cfg)  # type: ignore


@pytest.mark.asyncio
async def test_csv_loader_load_file_reads_csv():
    """CsvLoader.load_file reads CSV with provided filename."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("id,name\n1,Alice\n")
        path = f.name

    loader = CsvLoader()
    df = await loader.load_file({"filename": path})
    assert df.to_dict("list") == {"id": [1], "name": ["Alice"]}


@pytest.mark.asyncio
async def test_csv_loader_missing_filename_raises():
    """CsvLoader.load_file requires filename in options."""
    loader = CsvLoader()
    with pytest.raises(ValueError, match="Missing 'filename'"):
        await loader.load_file({})
