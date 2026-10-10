"""
Tests for Database Loaders

Tests the vendor-specific database introspection methods in database loaders.
"""

import pytest

from src.loaders.base_loader import DataLoader, DataLoaders, LoaderType
from src.model import DataSourceConfig

# pylint: disable=redefined-outer-name, unused-argument, protected-access


class TestDataLoader:
    """Tests for SQDataLoader."""

    @pytest.mark.asyncio
    async def test_all_registered_data_loaders_has_a_loader_type(self):
        """Check that all registered loaders have loader_type defined."""
        for key, loader_cls in DataLoaders.items.items():
            loader_type: LoaderType = loader_cls.loader_type()
            assert isinstance(loader_type, LoaderType), f"Loader '{key}' has invalid loader_type '{loader_type}'"
            assert loader_type != LoaderType.BASE, f"Loader '{key}' has base loader_type, should be specific"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "loader_type,expected_keys",
        [
            (LoaderType.SQL, {"postgres", "sqlite", "ucanaccess", "duckdb"}),
            (LoaderType.FILE, {"csv", "xlsx", "openpyxl"}),
            (LoaderType.VALUE, {"fixed"}),
        ],
    )
    async def test_get_loader_keys_by_type(self, loader_type, expected_keys):
        """Check that all registered loaders have loader_type defined."""
        loader_keys: set[str] = DataLoaders.get_loader_keys_by_type(loader_type)
        assert set(loader_keys) == expected_keys, f"{loader_type} loaders do not match expected set. Found: {set(loader_keys)}"


class TestDataLoaderCreateDefault:
    """Tests for the base DataLoader.create() default implementation.

    DuckDbLoader is the only loader that overrides create(). All other loaders
    inherit this default, which instantiates the class directly and ignores
    unused context keyword arguments.
    """

    def test_create_returns_instance_of_loader_class(self):
        loader_cls: type[DataLoader] = DataLoaders.get(key="csv")
        loader: DataLoader = loader_cls.create(data_source=None)
        assert isinstance(loader, loader_cls)

    def test_create_forwards_data_source(self):
        config = DataSourceConfig(cfg={"driver": "csv"}, name="files")
        loader: DataLoader = DataLoaders.get(key="csv").create(data_source=config)
        assert loader.data_source is config

    def test_create_ignores_unused_context_kwargs(self):
        config = DataSourceConfig(cfg={"driver": "csv"}, name="files")
        loader: DataLoader = DataLoaders.get(key="csv").create(
            data_source=config,
            workspace=object(),
            table_store=object(),
        )
        assert loader.data_source is config
