"""Tests for ProjectUtils component."""

from pathlib import Path

import pytest

from backend.app.exceptions import ResourceNotFoundError
from backend.app.services.project.project_utils import ProjectUtils
from backend.app.utils.exceptions import BadRequestError

# pylint: disable=redefined-outer-name


class TestProjectUtils:
    """Test ProjectUtils validation and existence checking."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path: Path) -> Path:
        """Create temporary configurations directory."""
        config_dir = tmp_path / "configurations"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def utils(self, temp_config_dir: Path) -> ProjectUtils:
        """Create ProjectUtils instance with temporary directory."""
        return ProjectUtils(projects_dir=temp_config_dir)

    @pytest.fixture
    def sample_project_dir(self, temp_config_dir: Path) -> Path:
        """Create a sample project directory."""
        project_dir = temp_config_dir / "test_project"
        project_dir.mkdir()

        # Create shapeshifter.yml
        config_content = """
metadata:
  type: shapeshifter-project
  name: test_project
  description: Test project
  version: 1.0.0

entities:
  sample:
    type: entity
    keys: [id]
    columns: [name, value]

options: {}
"""
        (project_dir / "shapeshifter.yml").write_text(config_content)
        return project_dir

    # validate_project_name tests

    def test_validate_project_name_valid_simple(self, utils: ProjectUtils):
        """Test validating a simple project name."""
        assert utils.validate_project_name("test") == "test"

    def test_validate_project_name_valid_nested(self, utils: ProjectUtils):
        """Test validating nested path with colon separator."""
        assert utils.validate_project_name("parent:child") == "parent:child"

    def test_validate_project_name_empty(self, utils: ProjectUtils):
        """Test validating empty name raises error."""
        with pytest.raises(BadRequestError, match="cannot be empty"):
            utils.validate_project_name("")

    def test_validate_project_name_whitespace_only(self, utils: ProjectUtils):
        """Test validating whitespace-only name raises error."""
        with pytest.raises(BadRequestError, match="cannot be empty"):
            utils.validate_project_name("   ")

    def test_validate_project_name_directory_traversal(self, utils: ProjectUtils):
        """Test directory traversal is prevented."""
        with pytest.raises(BadRequestError, match="directory traversal"):
            utils.validate_project_name("parent:..:sibling")

        with pytest.raises(BadRequestError, match="directory traversal"):
            utils.validate_project_name("..:parent")

    def test_validate_project_name_forward_slash(self, utils: ProjectUtils):
        """Test forward slashes are rejected (use colon instead)."""
        with pytest.raises(BadRequestError, match="use ':' for nested projects"):
            utils.validate_project_name("parent/child")

    def test_validate_project_name_absolute_path(self, utils: ProjectUtils):
        """Test absolute paths with slash are rejected."""
        with pytest.raises(BadRequestError, match="use ':' for nested projects"):
            utils.validate_project_name("/absolute/path")
            
    def test_validate_project_name_strips_whitespace(self, utils: ProjectUtils):
        """Test whitespace is stripped."""
        assert utils.validate_project_name("  test  ") == "test"
        assert utils.validate_project_name("  parent:child  ") == "parent:child"

    # ensure_project_exists tests

    def test_ensure_project_exists_valid(self, utils: ProjectUtils, sample_project_dir: Path):  # pylint: disable=unused-argument
        """Test ensuring project exists returns correct path."""
        project_file = utils.ensure_project_exists("test_project")
        assert project_file.exists()
        assert project_file.name == "shapeshifter.yml"
        assert project_file.parent.name == "test_project"

    def test_ensure_project_exists_not_found(self, utils: ProjectUtils):
        """Test ensuring non-existent project raises error."""
        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            utils.ensure_project_exists("nonexistent")

    def test_ensure_project_exists_nested(self, utils: ProjectUtils, temp_config_dir: Path):
        """Test ensuring nested project exists (using colon separator)."""
        # Create nested project
        nested_dir = temp_config_dir / "parent" / "child"
        nested_dir.mkdir(parents=True)
        (nested_dir / "shapeshifter.yml").write_text("metadata:\n  name: child\n")

        # Should succeed with colon separator
        project_file = utils.ensure_project_exists("parent:child")
        assert project_file.exists()
        assert project_file.parent.name == "child"
