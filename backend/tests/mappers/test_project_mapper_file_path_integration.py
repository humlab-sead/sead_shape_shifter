"""Integration tests for ProjectMapper with FilePathResolver."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.config import Settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata


class TestProjectMapperFilePathIntegration:
    """Integration tests for ProjectMapper file path resolution."""

    @pytest.fixture
    def mock_settings(self, tmp_path: Path) -> Settings:
        """Create mock Settings with temporary directories."""
        settings = MagicMock(spec=Settings)
        settings.GLOBAL_DATA_DIR = tmp_path / "shared" / "shared-data"
        settings.global_data_dir = settings.GLOBAL_DATA_DIR  # For property access
        settings.PROJECTS_DIR = tmp_path / "projects"
        settings.projects_root = settings.PROJECTS_DIR  # For property access
        settings.env_prefix = "SHAPE_SHIFTER_"
        settings.env_file = ".env"

        # Create directories
        settings.global_data_dir.mkdir(parents=True, exist_ok=True)
        settings.projects_root.mkdir(parents=True, exist_ok=True)

        # Create test files
        (settings.global_data_dir / "global_data.csv").write_text("test")
        project_dir = settings.projects_root / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "local_data.csv").write_text("test")

        return settings

    def test_to_core_resolves_global_file_path(self, mock_settings: Settings) -> None:
        """Test that to_core() resolves global file paths to absolute paths."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            api_project = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    file_path="test_project",
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=1,
                ),
                entities={
                    "entity1": {
                        "name": "entity1",
                        "type": "csv",
                        "options": {"filename": "global_data.csv", "location": "global"},
                    }
                },
            )

            core_project = ProjectMapper.to_core(api_project)

            # Verify absolute path resolution
            entity_options = core_project.cfg["entities"]["entity1"]["options"]
            expected_path = str(mock_settings.global_data_dir / "global_data.csv")
            assert entity_options["filename"] == expected_path
            # Location should be removed from Core
            assert "location" not in entity_options

    def test_to_core_resolves_local_file_path(self, mock_settings: Settings) -> None:
        """Test that to_core() resolves local file paths to absolute paths."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            api_project = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    file_path="test_project",
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=1,
                ),
                entities={
                    "entity1": {
                        "name": "entity1",
                        "type": "csv",
                        "options": {"filename": "local_data.csv", "location": "local"},
                    }
                },
            )

            core_project = ProjectMapper.to_core(api_project)

            # Verify absolute path resolution
            entity_options = core_project.cfg["entities"]["entity1"]["options"]
            expected_path = str(mock_settings.projects_root / "test_project" / "local_data.csv")
            assert entity_options["filename"] == expected_path
            # Location should be removed from Core
            assert "location" not in entity_options

    def test_to_core_supports_legacy_format(self, mock_settings: Settings) -> None:
        """Test that to_core() handles legacy ${GLOBAL_DATA_DIR}/ format."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            api_project = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=1,
                    file_path="test_project",
                ),
                entities={
                    "entity1": {
                        "name": "entity1",
                        "type": "csv",
                        "options": {"filename": "${GLOBAL_DATA_DIR}/global_data.csv"},
                        # No location field - should extract from legacy format
                    }
                },
            )

            core_project = ProjectMapper.to_core(api_project)

            # Verify absolute path resolution
            entity_options = core_project.cfg["entities"]["entity1"]["options"]
            expected_path = str(mock_settings.global_data_dir / "global_data.csv")
            assert entity_options["filename"] == expected_path

    def test_to_core_resolves_project_local_target_model_include(self, mock_settings: Settings) -> None:
        """Test that to_core() resolves a project-local target model include to a dict."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            project_dir = mock_settings.projects_root / "test_project"
            project_file = project_dir / "shapeshifter.yml"
            project_file.write_text("metadata:\n  name: test_project\nentities: {}\n", encoding="utf-8")
            target_model_path = project_dir / "target-model.yml"
            target_model_path.write_text(
                "model:\n  name: Test Model\n  format_version: '1'\n  version: '1.0.0'\nentities: {}\n",
                encoding="utf-8",
            )

            api_project = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    file_path=str(project_file),
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=0,
                    target_model="@include: target-model.yml",
                ),
                entities={},
                options={},
            )

            core_project = ProjectMapper.to_core(api_project)

            assert isinstance(core_project.metadata.target_model, dict)
            assert core_project.metadata.target_model["model"] == {
                "name": "Test Model",
                "format_version": "1",
                "version": "1.0.0",
            }
            assert core_project.metadata.target_model["entities"] == {}

    def test_to_core_raises_file_not_found_for_missing_target_model_include(self, mock_settings: Settings) -> None:
        """Test that to_core() raises a clear FileNotFoundError for missing target model includes."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            project_dir = mock_settings.projects_root / "test_project"
            project_file = project_dir / "shapeshifter.yml"
            project_file.write_text("metadata:\n  name: test_project\nentities: {}\n", encoding="utf-8")
            api_project = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    file_path=str(project_file),
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=0,
                    target_model="@include: missing-target-model.yml",
                ),
                entities={},
                options={},
            )

            with pytest.raises(FileNotFoundError, match="missing-target-model.yml"):
                ProjectMapper.to_core(api_project)

    def test_to_api_config_restores_location_for_global_file(self, mock_settings: Settings) -> None:
        """Test that to_api_config() decomposes absolute paths back to location + filename."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            core_dict = {
                "metadata": {
                    "name": "test_project",
                    "type": "shapeshifter-project",
                    "description": "Test",
                    "version": "1.0.0",
                },
                "entities": {
                    "entity1": {
                        "type": "csv",
                        "options": {"filename": str(mock_settings.global_data_dir / "global_data.csv")},
                    }
                },
                "options": {},
            }

            api_project = ProjectMapper.to_api_config(core_dict, "test_project")

            # Verify location restoration
            entity_options = api_project.entities["entity1"]["options"]
            assert entity_options["filename"] == "global_data.csv"
            assert entity_options["location"] == "global"

    def test_to_api_config_restores_location_for_local_file(self, mock_settings: Settings) -> None:
        """Test that to_api_config() correctly identifies local files."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            core_dict = {
                "metadata": {
                    "name": "test_project",
                    "type": "shapeshifter-project",
                    "description": "Test",
                    "version": "1.0.0",
                },
                "entities": {
                    "entity1": {
                        "type": "csv",
                        "options": {"filename": str(mock_settings.projects_root / "test_project" / "local_data.csv")},
                    }
                },
                "options": {},
            }

            api_project = ProjectMapper.to_api_config(core_dict, "test_project")

            # Verify location restoration
            entity_options = api_project.entities["entity1"]["options"]
            assert entity_options["filename"] == "local_data.csv"
            assert entity_options["location"] == "local"

    def test_roundtrip_api_to_core_to_api(self, mock_settings: Settings) -> None:
        """Test full round-trip: API → Core → API preserves location semantics."""
        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            original_api = Project(
                metadata=ProjectMetadata(
                    name="test_project",
                    type="shapeshifter-project",
                    description="Test project",
                    version="1.0.0",
                    entity_count=2,
                    file_path="test_project",
                ),
                entities={
                    "global_entity": {
                        "name": "global_entity",
                        "type": "csv",
                        "options": {"filename": "global_data.csv", "location": "global"},
                    },
                    "local_entity": {
                        "name": "local_entity",
                        "type": "csv",
                        "options": {"filename": "local_data.csv", "location": "local"},
                    },
                },
            )

            # API → Core
            core_project = ProjectMapper.to_core(original_api)

            # Verify Core has absolute paths
            global_options = core_project.cfg["entities"]["global_entity"]["options"]
            local_options = core_project.cfg["entities"]["local_entity"]["options"]
            assert global_options["filename"] == str(mock_settings.global_data_dir / "global_data.csv")
            assert local_options["filename"] == str(mock_settings.projects_root / "test_project" / "local_data.csv")

            # Core → API
            restored_api = ProjectMapper.to_api_config(core_project.cfg, "test_project")

            # Verify API has location semantics restored
            global_restored = restored_api.entities["global_entity"]["options"]
            local_restored = restored_api.entities["local_entity"]["options"]
            assert global_restored["filename"] == "global_data.csv"
            assert global_restored["location"] == "global"
            assert local_restored["filename"] == "local_data.csv"
            assert local_restored["location"] == "local"

    def test_to_api_config_preserves_absolute_paths_outside_managed_dirs(self, mock_settings: Settings, tmp_path: Path) -> None:
        """Test that absolute paths outside managed directories are preserved."""
        external_file = tmp_path / "external" / "data.csv"
        external_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("backend.app.mappers.project_mapper.settings", mock_settings):
            core_dict = {
                "metadata": {
                    "name": "test_project",
                    "type": "shapeshifter-project",
                    "description": "Test",
                    "version": "1.0.0",
                },
                "entities": {
                    "entity1": {
                        "options": {"filename": str(external_file)},
                    }
                },
                "options": {},
            }

            api_project = ProjectMapper.to_api_config(core_dict, "test_project")

            # Verify absolute path is preserved (no location field added)
            entity_options = api_project.entities["entity1"]["options"]
            assert entity_options["filename"] == str(external_file)
            # No location field should be added for external paths
            assert "location" not in entity_options
