from typing import Any

import pytest

from src.loaders.base_loader import DataLoaders
from src.loaders.file_loaders import FileLoader


@pytest.mark.parametrize("key", ["xlsx", "xls", "openpyxl"])
def test_excel_xlsx_loader_registration(key: str):

    loader_cls = DataLoaders.get(key)
    assert issubclass(loader_cls, FileLoader)


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["xlsx", "xls", "openpyxl"])
async def test_excel_xlsx_load_sheet(key: str):

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "sanitize_header": False,
    }

    loader_cls = DataLoaders.get(key)
    loader = loader_cls()
    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["A", "B", "C"]
    assert len(df) == 4


async def test_excel_openpyxl_load_entire_cell_range():

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "cell_range": "A1:C5",
        "sanitize_header": False,
    }

    loader_cls = DataLoaders.get("openpyxl")
    loader = loader_cls()

    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["A", "B", "C"]
    assert len(df) == 4


async def test_excel_openpyxl_load_two_columns():
    loader_cls = DataLoaders.get("openpyxl")
    loader = loader_cls()

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "range": "B1:C5",
        "sanitize_header": False,
    }
    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["B", "C"]
    assert len(df) == 4


async def test_excel_openpyxl_load_subset_without_header():
    loader_cls = DataLoaders.get("openpyxl")
    loader = loader_cls()

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "range": "A3:C5",
        "header": False,
        "sanitize_header": False,
    }
    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["C_1", "C_2", "C_3"]
    assert len(df) == 3


async def test_excel_openpyxl_load_subset_with_explicit_header():
    loader_cls = DataLoaders.get("openpyxl")
    loader = loader_cls()

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "range": "A3:C5",
        "header": ["X", "Y", "Z"],
        "sanitize_header": False,
    }
    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["X", "Y", "Z"]
    assert len(df) == 2


async def test_excel_openpyxl_load_subset_with_sanitize_header():
    loader_cls = DataLoaders.get("openpyxl")
    loader = loader_cls()

    cfg: dict[str, Any] = {
        "filename": "tests/test_data/excel_test.xlsx",
        "sheet_name": "kalle",
        "range": "A3:C5",
        "header": ["X Y", "Y Z", "Z W"],
        "sanitize_header": True,
    }
    df = await loader.load_file(cfg)
    assert not df.empty
    assert list(df.columns) == ["x_y", "y_z", "z_w"]
    assert len(df) == 2
