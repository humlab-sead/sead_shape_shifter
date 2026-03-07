"""Tests for LayoutSidecarManager service."""

import tempfile
from pathlib import Path

import pytest

from backend.app.services.layout_sidecar_manager import LayoutSidecarManager
from backend.app.services.yaml_service import YamlService


class TestLayoutSidecarManager:
    """Tests for LayoutSidecarManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "my_project"
            project_dir.mkdir(parents=True, exist_ok=True)
            yield project_dir

    @pytest.fixture
    def yaml_service(self):
        """Create YamlService instance."""
        return YamlService()

    @pytest.fixture
    def sidecar_manager(self, yaml_service):
        """Create LayoutSidecarManager instance."""
        return LayoutSidecarManager(yaml_service)

    @pytest.fixture
    def project_file(self, temp_dir):
        """Create project file path."""
        return temp_dir / "shapeshifter.yml"

    def test_get_sidecar_path_returns_correct_path(self, project_file, sidecar_manager):
        """Test get_sidecar_path returns correct sidecar path."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)

        assert sidecar_path.parent == project_file.parent
        assert sidecar_path.name == "shapeshifter.layout.yml"

    def test_sidecar_exists_returns_false_when_not_exists(self, project_file, sidecar_manager):
        """Test sidecar_exists returns False when sidecar doesn't exist."""
        assert sidecar_manager.sidecar_exists(project_file) is False

    def test_save_and_load_layout_roundtrip(self, project_file, sidecar_manager):
        """Test save and load roundtrip preserves layout coordinates."""
        layout = {
            "entity_a": {"x": 10.5, "y": 20.25},
            "entity_b": {"x": -3.0, "y": 99.9},
        }

        sidecar_manager.save_layout(project_file, layout)
        loaded = sidecar_manager.load_layout(project_file)

        assert loaded == layout

    def test_load_layout_returns_empty_when_missing(self, project_file, sidecar_manager):
        """Test load_layout returns empty dict when sidecar is missing."""
        assert sidecar_manager.load_layout(project_file) == {}

    def test_load_layout_supports_root_format(self, project_file, sidecar_manager, yaml_service):
        """Test load_layout supports legacy root-level mapping format."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        yaml_service.save({"entity_a": {"x": 1, "y": 2}}, sidecar_path)

        loaded = sidecar_manager.load_layout(project_file)

        assert loaded == {"entity_a": {"x": 1.0, "y": 2.0}}

    def test_migrate_from_project_options_creates_sidecar(self, project_file, sidecar_manager):
        """Test migration writes options.layout.custom to sidecar when needed."""
        options = {
            "layout": {
                "custom": {
                    "entity_a": {"x": 123, "y": 456},
                }
            }
        }

        migrated = sidecar_manager.migrate_from_project_options(project_file, options)
        loaded = sidecar_manager.load_layout(project_file)

        assert migrated == {"entity_a": {"x": 123, "y": 456}}
        assert loaded == {"entity_a": {"x": 123.0, "y": 456.0}}

    def test_migrate_from_project_options_skips_if_sidecar_exists(self, project_file, sidecar_manager):
        """Test migration does not overwrite existing sidecar."""
        sidecar_manager.save_layout(project_file, {"existing": {"x": 1, "y": 2}})

        options = {
            "layout": {
                "custom": {
                    "new": {"x": 3, "y": 4},
                }
            }
        }

        migrated = sidecar_manager.migrate_from_project_options(project_file, options)

        assert migrated == {"existing": {"x": 1.0, "y": 2.0}}

    def test_delete_sidecar_removes_file(self, project_file, sidecar_manager):
        """Test delete_sidecar removes sidecar file."""
        sidecar_manager.save_layout(project_file, {"entity": {"x": 1, "y": 2}})
        assert sidecar_manager.sidecar_exists(project_file)

        deleted = sidecar_manager.delete_sidecar(project_file)

        assert deleted is True
        assert not sidecar_manager.sidecar_exists(project_file)
