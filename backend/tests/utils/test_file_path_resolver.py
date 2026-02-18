"""Tests for centralized file path resolution."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.core.config import Settings
from backend.app.utils.file_path_resolver import FilePathResolver


class TestFilePathResolver:
    """Test suite for FilePathResolver utility class."""

    @pytest.fixture
    def mock_settings(self, tmp_path: Path) -> Settings:
        """Create mock Settings with temporary directories."""
        settings = MagicMock(spec=Settings)
        settings.GLOBAL_DATA_DIR = tmp_path / "shared" / "shared-data"
        settings.global_data_dir = settings.GLOBAL_DATA_DIR  # For property access
        settings.PROJECTS_DIR = tmp_path / "projects"
        settings.projects_root = settings.PROJECTS_DIR  # For property access
        settings.APPLICATION_ROOT = tmp_path
        settings.application_root = settings.APPLICATION_ROOT  # For property access

        # Create directories
        settings.global_data_dir.mkdir(parents=True, exist_ok=True)
        settings.projects_root.mkdir(parents=True, exist_ok=True)

        return settings

    @pytest.fixture
    def resolver(self, mock_settings: Settings) -> FilePathResolver:
        """Create FilePathResolver instance with mock settings."""
        return FilePathResolver(mock_settings)

    # Test: resolve()

    def test_resolve_global_file(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving global file path."""
        result = resolver.resolve("specimens.csv", "global")
        expected = mock_settings.global_data_dir / "specimens.csv"
        assert result == expected

    def test_resolve_global_file_with_subdirectory(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving global file with subdirectory."""
        result = resolver.resolve("data/specimens.csv", "global")
        expected = mock_settings.global_data_dir / "data" / "specimens.csv"
        assert result == expected

    def test_resolve_local_file(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving local (project-specific) file path."""
        result = resolver.resolve("sites.xlsx", "local", "dendro:sites")
        expected = mock_settings.projects_root / "dendro" / "sites" / "sites.xlsx"
        assert result == expected

    def test_resolve_local_file_with_subdirectory(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving local file with subdirectory."""
        result = resolver.resolve("data/sites.xlsx", "local", "dendro:sites")
        expected = mock_settings.projects_root / "dendro" / "sites" / "data" / "sites.xlsx"
        assert result == expected

    def test_resolve_local_file_without_project_name_raises(self, resolver: FilePathResolver) -> None:
        """Test that resolving local file without project_name raises ValueError."""
        with pytest.raises(ValueError, match="project_name required"):
            resolver.resolve("sites.xlsx", "local")

    def test_resolve_invalid_location_raises(self, resolver: FilePathResolver) -> None:
        """Test that invalid location raises ValueError."""
        with pytest.raises(ValueError, match="Invalid location"):
            resolver.resolve("file.csv", "invalid")  # type: ignore

    # Test: decompose()

    def test_decompose_global_file(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test decomposing global file path."""
        absolute_path = mock_settings.global_data_dir / "specimens.csv"
        result = resolver.decompose(absolute_path)
        assert result == ("specimens.csv", "global")

    def test_decompose_global_file_with_subdirectory(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test decomposing global file with subdirectory."""
        absolute_path = mock_settings.global_data_dir / "data" / "specimens.csv"
        result = resolver.decompose(absolute_path)
        assert result == ("data/specimens.csv", "global")

    def test_decompose_local_file(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test decomposing local (project-specific) file path."""
        absolute_path = mock_settings.projects_root / "dendro" / "sites" / "sites.xlsx"
        result = resolver.decompose(absolute_path, "dendro:sites")
        assert result == ("sites.xlsx", "local")

    def test_decompose_local_file_with_subdirectory(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test decomposing local file with subdirectory."""
        absolute_path = mock_settings.projects_root / "dendro" / "sites" / "data" / "sites.xlsx"
        result = resolver.decompose(absolute_path, "dendro:sites")
        assert result == ("data/sites.xlsx", "local")

    def test_decompose_file_outside_managed_directories(self, resolver: FilePathResolver, tmp_path: Path) -> None:
        """Test decomposing file outside managed directories returns None."""
        external_path = tmp_path / "external" / "file.csv"
        result = resolver.decompose(external_path)
        assert result is None

    def test_decompose_without_project_name_prefers_global(
        self, resolver: FilePathResolver, mock_settings: Settings
    ) -> None:
        """Test that decompose without project_name cannot detect local files."""
        absolute_path = mock_settings.projects_root / "dendro" / "sites" / "sites.xlsx"
        result = resolver.decompose(absolute_path)  # No project_name
        # Without project_name, we can't determine it's local, returns None
        assert result is None

    # Test: extract_location()

    def test_extract_location_from_legacy_global_format(self, resolver: FilePathResolver) -> None:
        """Test extracting location from legacy ${GLOBAL_DATA_DIR}/ format."""
        filename, location = resolver.extract_location("${GLOBAL_DATA_DIR}/specimens.csv")
        assert filename == "specimens.csv"
        assert location == "global"

    def test_extract_location_from_plain_filename(self, resolver: FilePathResolver) -> None:
        """Test extracting location from plain filename (defaults to local)."""
        filename, location = resolver.extract_location("specimens.csv")
        assert filename == "specimens.csv"
        assert location == "local"

    def test_extract_location_with_subdirectory(self, resolver: FilePathResolver) -> None:
        """Test extracting location with subdirectory in legacy format."""
        filename, location = resolver.extract_location("${GLOBAL_DATA_DIR}/data/specimens.csv")
        assert filename == "data/specimens.csv"
        assert location == "global"

    # Test: to_legacy_format()

    def test_to_legacy_format_global(self, resolver: FilePathResolver) -> None:
        """Test converting to legacy format for global file."""
        result = resolver.to_legacy_format("specimens.csv", "global")
        assert result == "${GLOBAL_DATA_DIR}/specimens.csv"

    def test_to_legacy_format_local(self, resolver: FilePathResolver) -> None:
        """Test converting to legacy format for local file."""
        result = resolver.to_legacy_format("sites.xlsx", "local")
        assert result == "sites.xlsx"

    # Test: Round-trip conversions

    def test_roundtrip_global_via_resolve_and_decompose(
        self, resolver: FilePathResolver, mock_settings: Settings
    ) -> None:
        """Test round-trip conversion: (filename, location) → absolute → (filename, location)."""
        original_filename = "specimens.csv"
        original_location = "global"

        # API → Core (resolve)
        absolute_path = resolver.resolve(original_filename, original_location)

        # Core → API (decompose)
        filename, location = resolver.decompose(absolute_path)  # type: ignore

        assert filename == original_filename
        assert location == original_location

    def test_roundtrip_local_via_resolve_and_decompose(
        self, resolver: FilePathResolver, mock_settings: Settings
    ) -> None:
        """Test round-trip conversion for local file."""
        original_filename = "data/sites.xlsx"
        original_location = "local"
        project_name = "dendro:sites"

        # API → Core (resolve)
        absolute_path = resolver.resolve(original_filename, original_location, project_name)

        # Core → API (decompose)
        filename, location = resolver.decompose(absolute_path, project_name)  # type: ignore

        assert filename == original_filename
        assert location == original_location

    def test_roundtrip_legacy_format(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test round-trip with legacy format extraction."""
        legacy_filename = "${GLOBAL_DATA_DIR}/specimens.csv"

        # Extract location from legacy format
        filename, location = resolver.extract_location(legacy_filename)

        # Resolve to absolute path
        absolute_path = resolver.resolve(filename, location)

        # Decompose back
        decomposed_filename, decomposed_location = resolver.decompose(absolute_path)  # type: ignore

        assert decomposed_filename == "specimens.csv"
        assert decomposed_location == "global"

        # Convert back to legacy format
        legacy_result = resolver.to_legacy_format(decomposed_filename, decomposed_location)
        assert legacy_result == legacy_filename

    # Test: Edge cases

    def test_resolve_empty_filename(self, resolver: FilePathResolver) -> None:
        """Test resolving empty filename still returns valid path."""
        result = resolver.resolve("", "global")
        assert result == resolver.settings.global_data_dir

    def test_decompose_directory_path(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test decomposing directory (not file) path."""
        dir_path = mock_settings.global_data_dir / "data"
        result = resolver.decompose(dir_path)
        assert result == ("data", "global")

    def test_project_name_with_multiple_colons(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test project name with multiple colons converts to nested path."""
        result = resolver.resolve("file.csv", "local", "parent:child:grandchild")
        expected = mock_settings.projects_root / "parent" / "child" / "grandchild" / "file.csv"
        assert result == expected

    # Test: resolve_in_entity_config()

    def test_resolve_in_entity_config_global(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving file paths in entity config dictionary for global file."""
        config = {
            "options": {
                "filename": "data.csv",
                "location": "global"
            }
        }
        
        resolver.resolve_in_entity_config(config, "test_project")
        
        expected_path = str(mock_settings.global_data_dir / "data.csv")
        assert config["options"]["filename"] == expected_path
        # Location should be removed for Core
        assert "location" not in config["options"]

    def test_resolve_in_entity_config_local(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving file paths in entity config dictionary for local file."""
        config = {
            "options": {
                "filename": "data.csv",
                "location": "local"
            }
        }
        
        resolver.resolve_in_entity_config(config, "my:project")
        
        expected_path = str(mock_settings.projects_root / "my" / "project" / "data.csv")
        assert config["options"]["filename"] == expected_path
        assert "location" not in config["options"]

    def test_resolve_in_entity_config_legacy_format(self, resolver: FilePathResolver, mock_settings: Settings) -> None:
        """Test resolving file paths in entity config with legacy format."""
        config = {
            "options": {
                "filename": "${GLOBAL_DATA_DIR}/legacy_data.csv"
                # No location field - should be extracted
            }
        }
        
        resolver.resolve_in_entity_config(config, "test_project")
        
        expected_path = str(mock_settings.global_data_dir / "legacy_data.csv")
        assert config["options"]["filename"] == expected_path
        assert "location" not in config["options"]

    def test_resolve_in_entity_config_no_options(self, resolver: FilePathResolver) -> None:
        """Test resolve_in_entity_config with config missing options."""
        config: dict[str, Any] = {"other_field": "value"}
        
        # Should not raise error, just return early
        resolver.resolve_in_entity_config(config, "test_project")
        
        assert config == {"other_field": "value"}

    def test_resolve_in_entity_config_no_filename(self, resolver: FilePathResolver) -> None:
        """Test resolve_in_entity_config with options but no filename."""
        config = {
            "options": {
                "other_option": "value"
            }
        }
        
        resolver.resolve_in_entity_config(config, "test_project")
        
        assert config["options"] == {"other_option": "value"}

    def test_resolve_in_entity_config_invalid_location_defaults_to_global(
        self, resolver: FilePathResolver, mock_settings: Settings
    ) -> None:
        """Test that invalid location defaults to global."""
        config = {
            "options": {
                "filename": "data.csv",
                "location": "invalid_location"
            }
        }
        
        resolver.resolve_in_entity_config(config, "test_project")
        
        # Should use global as fallback
        expected_path = str(mock_settings.global_data_dir / "data.csv")
        assert config["options"]["filename"] == expected_path
