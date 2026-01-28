"""
Tests for Database Loaders

Tests the vendor-specific database introspection methods in database loaders.
"""

import pytest

from src.loaders.base_loader import DataLoaders, LoaderType

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
            (LoaderType.SQL, {"postgres", "sqlite", "ucanaccess"}),
            (LoaderType.FILE, {"csv", "xlsx", "openpyxl"}),
            (LoaderType.VALUE, {"fixed"}),
        ],
    )
    async def test_get_loader_keys_by_type(self, loader_type, expected_keys):
        """Check that all registered loaders have loader_type defined."""
        loader_keys: set[str] = DataLoaders.get_loader_keys_by_type(loader_type)
        assert set(loader_keys) == expected_keys, f"{loader_type} loaders do not match expected set. Found: {set(loader_keys)}"
