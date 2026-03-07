"""Tests for TaskListSidecarManager service."""

import tempfile
from pathlib import Path

import pytest

from backend.app.services.task_list_sidecar_manager import TaskListSidecarManager
from backend.app.services.yaml_service import YamlService
from src.model import TaskList


class TestTaskListSidecarManager:
    """Tests for TaskListSidecarManager class."""

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
        """Create TaskListSidecarManager instance."""
        return TaskListSidecarManager(yaml_service)

    @pytest.fixture
    def project_file(self, temp_dir):
        """Create project file path."""
        return temp_dir / "shapeshifter.yml"

    def test_get_sidecar_path_returns_correct_path(self, project_file, sidecar_manager):
        """Test get_sidecar_path returns correct sidecar path."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)

        assert sidecar_path.parent == project_file.parent
        assert sidecar_path.name == "shapeshifter.tasks.yml"

    def test_sidecar_exists_returns_false_when_not_exists(self, project_file, sidecar_manager):
        """Test sidecar_exists returns False when sidecar doesn't exist."""
        assert sidecar_manager.sidecar_exists(project_file) is False

    def test_sidecar_exists_returns_true_when_exists(self, project_file, sidecar_manager):
        """Test sidecar_exists returns True when sidecar exists."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.touch()

        assert sidecar_manager.sidecar_exists(project_file) is True

    def test_load_task_list_returns_empty_dict_when_not_exists(self, project_file, sidecar_manager):
        """Test load_task_list returns {} when sidecar doesn't exist."""
        result = sidecar_manager.load_task_list(project_file)

        assert result == {}

    def test_load_task_list_returns_task_list_when_exists(self, project_file, sidecar_manager, yaml_service):
        """Test load_task_list returns task_list when sidecar exists."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        # Create sidecar file with task_list data
        task_list_data = {
            "required": ["entity1", "entity2"],
            "completed": ["entity1"],
        }
        yaml_service.save({"task_list": task_list_data}, sidecar_path)

        result = sidecar_manager.load_task_list(project_file)

        assert result == task_list_data

    def test_load_task_list_handles_missing_task_list_key(self, project_file, sidecar_manager, yaml_service):
        """Test load_task_list returns full data when sidecar has no explicit task_list key."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        # Create sidecar file without explicit task_list key (treat root as task_list)
        sidecar_content = {"completed": ["entity1"], "ongoing": ["entity2"]}
        yaml_service.save(sidecar_content, sidecar_path)

        result = sidecar_manager.load_task_list(project_file)

        # Should return the content as-is since there's no explicit task_list key
        assert result == sidecar_content

    def test_save_task_list_creates_sidecar_file(self, project_file, sidecar_manager):
        """Test save_task_list creates sidecar file."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        task_list = TaskList({"required": ["entity1"], "completed": []})

        sidecar_manager.save_task_list(project_file, task_list)

        assert sidecar_path.exists()

    def test_save_task_list_saves_correct_format(self, project_file, sidecar_manager, yaml_service):
        """Test save_task_list saves correct format."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        task_list = TaskList(
            {
                "required_entities": ["entity1", "entity2"],
                "completed": ["entity1"],
            }
        )

        sidecar_manager.save_task_list(project_file, task_list)

        # Load file directly to verify format
        loaded_data = yaml_service.load(sidecar_path)

        assert "task_list" in loaded_data
        assert "required_entities" in loaded_data["task_list"]
        assert "entity1" in loaded_data["task_list"]["required_entities"]

    def test_save_task_list_creates_parent_directory(self, temp_dir, sidecar_manager):
        """Test save_task_list creates parent directory if needed."""
        project_file = temp_dir / "nested" / "dir" / "shapeshifter.yml"
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)

        task_list = TaskList({"required_entities": ["entity1"], "completed": []})

        sidecar_manager.save_task_list(project_file, task_list)

        assert sidecar_path.parent.exists()
        assert sidecar_path.exists()

    def test_migrate_task_list_copies_from_main_to_sidecar(self, project_file, sidecar_manager, yaml_service):
        """Test migrate_task_list copies task_list from main to sidecar."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        project_data = {
            "entities": {"entity1": {}},
            "task_list": {
                "required_entities": ["entity1"],
                "completed": [],
            },
        }

        result = sidecar_manager.migrate_task_list(project_file, project_data)

        # Verify sidecar was created
        assert sidecar_path.exists()

        # Verify sidecar contains task_list
        sidecar_data = yaml_service.load(sidecar_path)
        assert "task_list" in sidecar_data
        assert sidecar_data["task_list"] == project_data["task_list"]

        # Verify task_list was removed from returned data
        assert "task_list" not in result
        assert "entities" in result

    def test_migrate_task_list_skips_if_sidecar_exists(self, project_file, sidecar_manager, yaml_service):
        """Test migrate_task_list skips if sidecar already exists."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        # Create existing sidecar
        yaml_service.save({"task_list": {"existing": "data"}}, sidecar_path)

        project_data = {
            "entities": {"entity1": {}},
            "task_list": {"new": "data"},
        }

        result = sidecar_manager.migrate_task_list(project_file, project_data)

        # Verify sidecar was not overwritten
        sidecar_data = yaml_service.load(sidecar_path)
        assert sidecar_data["task_list"] == {"existing": "data"}

        # Verify project_data returned unchanged (no migration needed)
        assert result == project_data

    def test_migrate_task_list_skips_if_no_task_list_in_main(self, project_file, sidecar_manager):
        """Test migrate_task_list skips if no task_list in main file."""
        project_data = {
            "entities": {"entity1": {}},
        }

        result = sidecar_manager.migrate_task_list(project_file, project_data)

        # Verify sidecar was not created
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        assert not sidecar_path.exists()

        # Verify project_data returned unchanged
        assert result == project_data

    def test_migrate_task_list_returns_copy_not_reference(self, project_file, sidecar_manager):
        """Test migrate_task_list returns copy of data, not reference."""
        project_data = {
            "entities": {"entity1": {}},
            "task_list": {"required": ["entity1"]},
        }

        result = sidecar_manager.migrate_task_list(project_file, project_data)

        # Verify returned data is different from input
        assert result is not project_data
        assert "task_list" not in result
        assert "task_list" in project_data  # Original unchanged

    def test_delete_sidecar_removes_file(self, project_file, sidecar_manager, yaml_service):
        """Test delete_sidecar removes sidecar file."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        # Create sidecar file
        yaml_service.save({"task_list": {"test": "data"}}, sidecar_path)
        assert sidecar_path.exists()

        sidecar_manager.delete_sidecar(project_file)

        assert not sidecar_path.exists()

    def test_delete_sidecar_handles_missing_file_gracefully(self, project_file, sidecar_manager):
        """Test delete_sidecar handles missing file gracefully."""
        # Should not raise exception even if file doesn't exist
        sidecar_manager.delete_sidecar(project_file)

    def test_roundtrip_save_and_load(self, project_file, sidecar_manager):
        """Test save and load roundtrip preserves data."""
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        original_task_list = TaskList(
            {
                "required_entities": ["entity1", "entity2"],
                "completed": ["entity1"],
                "ignored": ["entity2"],
            }
        )

        sidecar_manager.save_task_list(project_file, original_task_list)
        loaded_data = sidecar_manager.load_task_list(project_file)

        assert "required_entities" in loaded_data
        assert "entity1" in loaded_data["required_entities"]
        assert "entity1" in loaded_data.get("completed", [])

    def test_multiple_projects_have_separate_sidecars(self, temp_dir, sidecar_manager):
        """Test multiple projects have separate sidecar files."""
        project1_dir = temp_dir / "project1"
        project2_dir = temp_dir / "project2"
        project1_dir.mkdir()
        project2_dir.mkdir()

        project1_file = project1_dir / "shapeshifter.yml"
        project2_file = project2_dir / "shapeshifter.yml"

        sidecar1 = sidecar_manager.get_sidecar_path(project1_file)
        sidecar2 = sidecar_manager.get_sidecar_path(project2_file)

        assert sidecar1 != sidecar2
        assert sidecar1.parent == project1_dir
        assert sidecar2.parent == project2_dir

    def test_sidecar_path_matches_project_file_location(self, temp_dir, sidecar_manager):
        """Test sidecar path is in same directory as project file."""
        project_file = temp_dir / "deeply" / "nested" / "dir" / "shapeshifter.yml"
        sidecar_path = sidecar_manager.get_sidecar_path(project_file)

        assert sidecar_path.parent == project_file.parent
        assert sidecar_path.parent == temp_dir / "deeply" / "nested" / "dir"
