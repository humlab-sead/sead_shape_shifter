"""Test for debugging the @include directive bug in ShapeShiftService.

This test reproduces the error:
AttributeError: 'DoubleQuotedScalarString' object has no attribute 'get'

ROOT CAUSE:
-----------
The error occurs when a YAML configuration file contains an @include directive that
hasn't been resolved/processed before being used. The ruamel.yaml library preserves
the string "@include: filename.yml" as a DoubleQuotedScalarString object instead of
loading and merging the referenced file's contents.

When the code tries to access properties of what should be a dictionary (e.g.,
data_source.driver), it fails because it's actually trying to call .get() on a string.

EXAMPLE BUGGY YAML:
-------------------
options:
  data_sources:
    lookup_db: "@include: arbodat-lookup-options.yml"  # BUG: String, not dict!

EXPECTED YAML (after @include resolution):
-------------------------------------------
options:
  data_sources:
    lookup_db:  # Properly resolved dictionary
      driver: postgresql
      options:
        host: localhost
        ...

HOW TO FIX:
-----------
1. Ensure @include directives are processed BEFORE the config is converted to ShapeShiftProject
2. Check the configuration loading code (likely in backend/app/services/project_service.py
   or backend/app/mappers/config_mapper.py) to ensure includes are resolved
3. Add validation to detect unresolved @include directives (see test_detect_unresolved_includes_in_config)
4. The configuration provider/loader should handle @include processing, not the consumers

DEBUGGING STRATEGY:
-------------------
1. Run test_data_source_config_with_include_string to confirm the bug
2. Run test_detect_unresolved_includes_in_config to scan configs for this issue
3. Trace back through the config loading chain to find where @include should be resolved
4. Add proper @include processing to the YAML loading mechanism
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, ScalarString

from backend.app.services.shapeshift_service import ShapeShiftService
from src.model import DataSourceConfig, ShapeShiftProject


class TestShapeShiftServiceIncludeBug:
    """Test to reproduce and debug the @include directive bug."""

    @pytest.fixture
    def mock_config_service(self) -> MagicMock:
        """Create mock ProjectService."""
        service = MagicMock()
        service.load_project = MagicMock()
        return service

    @pytest.fixture
    def service(self, mock_config_service: MagicMock) -> ShapeShiftService:
        """Create ShapeShiftService instance."""
        return ShapeShiftService(project_service=mock_config_service)

    @pytest.mark.asyncio
    async def test_preview_entity_with_unresolved_include_directive(self):
        """
        Test that reproduces the error when @include directive is not resolved.

        The error occurs when:
        1. A configuration has a data source with @include directive
        2. The @include is not resolved to actual dictionary values
        3. DataSourceConfig tries to call .get() on a DoubleQuotedScalarString object

        Expected behavior: The configuration should be properly resolved before use
        Actual behavior: Crashes with AttributeError
        """
        # Create a configuration dict with an UNRESOLVED @include directive
        # This simulates what happens when YAML includes aren't processed
        unresolved_include = DoubleQuotedScalarString("@include: arbodat-lookup-options.yml")

        config_dict = {
            "entities": {
                "feature": {
                    "type": "csv",  # Use CSV type instead of data source to avoid dependencies
                    "source": "test_file.csv",
                    "columns": ["feature_id", "feature_name"],
                    "keys": ["feature_id"],
                    # Don't use data_source to avoid get_dependencies
                }
            },
            "options": {"data_sources": {"lookup_db": unresolved_include}},  # BUG: This should be a dict, not a string!
        }

        # Mock the config cache to return this buggy config
        mock_shapeshift_config = ShapeShiftProject(cfg=config_dict, filename="test-config.yml")

        # Now let's directly test that getting the data source fails
        with pytest.raises(AttributeError, match="'DoubleQuotedScalarString' object has no attribute 'get'"):
            ds = mock_shapeshift_config.get_data_source("lookup_db")
            _ = ds.driver  # This triggers the error

    @pytest.mark.asyncio
    async def test_data_source_config_with_include_string(self):
        """
        Direct test of DataSourceConfig with an @include string.

        This demonstrates the root cause: DataSourceConfig expects a dict but receives a string.
        """

        # Simulate what happens when @include isn't resolved
        unresolved_include = DoubleQuotedScalarString("@include: arbodat-lookup-options.yml")

        # This will fail when trying to access .driver property
        with pytest.raises(AttributeError, match="'DoubleQuotedScalarString' object has no attribute 'get'"):
            data_source = DataSourceConfig(cfg=unresolved_include, name="lookup_db")  # type: ignore
            _ = data_source.driver  # This line triggers the error

    @pytest.mark.asyncio
    async def test_shapeshift_config_with_unresolved_include(self):
        """
        Test ShapeShiftProject.get_data_source with unresolved @include.

        This shows where the error propagates through the config system.
        """
        unresolved_include = DoubleQuotedScalarString("@include: arbodat-lookup-options.yml")

        config_dict = {
            "entities": {
                "test_entity": {
                    "source": "test_table",
                    "columns": ["id"],
                    "keys": ["id"],
                    "data_source": "test_source",
                }
            },
            "options": {"data_sources": {"test_source": unresolved_include}},
        }

        config = ShapeShiftProject(cfg=config_dict, filename="test-config.yml")

        # Attempting to get the data source will fail
        with pytest.raises(AttributeError, match="'DoubleQuotedScalarString' object has no attribute 'get'"):
            data_source = config.get_data_source("test_source")
            _ = data_source.driver

    @pytest.mark.asyncio
    async def test_preview_entity_with_properly_resolved_include(self, service: ShapeShiftService):
        """
        Test that preview works correctly when @include IS properly resolved.

        This demonstrates what the config should look like after includes are resolved.
        """
        # This is what the config SHOULD look like after includes are resolved
        config_dict = {
            "entities": {
                "feature": {
                    "type": "values",  # Use simple values type
                    "values": [{"feature_id": 1, "feature_name": "Feature 1"}, {"feature_id": 2, "feature_name": "Feature 2"}],
                    "columns": ["feature_id", "feature_name"],
                    "keys": ["feature_id"],
                }
            },
            "options": {
                "data_sources": {
                    "lookup_db": {  # CORRECT: This is now a dict
                        "driver": "postgresql",
                        "options": {
                            "host": "localhost",
                            "port": 5432,
                            "database": "test_db",
                            "user": "test_user",
                            "password": "test_password",
                        },
                    }
                }
            },
        }

        mock_shapeshift_config = ShapeShiftProject(cfg=config_dict, filename="test-config.yml")

        # Mock the ShapeShifter to return test data
        mock_normalizer = MagicMock()
        test_df = pd.DataFrame({"feature_id": [1, 2], "feature_name": ["Feature 1", "Feature 2"]})
        mock_normalizer.table_store = {"feature": test_df}
        mock_normalizer.normalize = AsyncMock()

        with (
            patch.object(service.config_cache, "get_config", return_value=mock_shapeshift_config),
            patch.object(service, "get_config_version", return_value=1),
            patch("backend.app.services.shapeshift_service.ShapeShifter", return_value=mock_normalizer),
        ):
            # This should work without errors
            result = await service.preview_entity("test_project", "feature", limit=10)

            assert result.entity_name == "feature"
            assert result.total_rows_in_preview == 2
            assert len(result.rows) == 2

            # Verify the data source config is properly accessible as a dict
            ds = mock_shapeshift_config.get_data_source("lookup_db")
            assert ds.driver == "postgresql"
            assert ds.options["host"] == "localhost"


class TestConfigurationResolution:
    """Tests for debugging configuration resolution issues."""

    def test_detect_unresolved_includes_in_config(self):
        """
        Test to detect unresolved @include directives in configuration.

        This can be used as a validation step before using a config.
        """

        unresolved_include = DoubleQuotedScalarString("@include: some-file.yml")

        config_dict = {
            "entities": {"test": {"source": "table"}},
            "options": {"data_sources": {"db": unresolved_include}},
        }

        # Function to detect unresolved includes
        def has_unresolved_includes(obj, path=""):
            """Recursively check for DoubleQuotedScalarString objects that look like @include."""
            if isinstance(obj, ScalarString):
                if obj.startswith("@include:"):
                    return True, path
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    found, found_path = has_unresolved_includes(value, f"{path}.{key}")
                    if found:
                        return found, found_path
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    found, found_path = has_unresolved_includes(item, f"{path}[{i}]")
                    if found:
                        return found, found_path
            return False, ""

        found, path = has_unresolved_includes(config_dict)
        assert found is True
        assert "data_sources.db" in path

    def test_valid_config_has_no_unresolved_includes(self):
        """Test that a properly resolved config doesn't have string data sources."""
        config_dict = {
            "entities": {"test": {"source": "table"}},
            "options": {
                "data_sources": {
                    "db": {  # This is a proper dict
                        "driver": "postgresql",
                        "options": {"host": "localhost"},
                    }
                }
            },
        }

        def has_unresolved_includes(obj, path=""):
            if isinstance(obj, ScalarString):
                if obj.startswith("@include:"):
                    return True, path
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    found, found_path = has_unresolved_includes(value, f"{path}.{key}")
                    if found:
                        return found, found_path
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    found, found_path = has_unresolved_includes(item, f"{path}[{i}]")
                    if found:
                        return found, found_path
            return False, ""

        found, _ = has_unresolved_includes(config_dict)
        assert found is False
