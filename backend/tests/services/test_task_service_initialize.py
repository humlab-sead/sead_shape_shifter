"""Tests for TaskService initialize_task_list functionality."""

from unittest.mock import Mock, patch

import pytest

from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.task_service import TaskService

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_project():
    """Create a mock project with entities."""
    return Project(
        entities={
            "location": {
                "type": "data",
                "keys": ["location_id"],
                "columns": ["name", "latitude"],
            },
            "site": {
                "type": "data",
                "keys": ["site_id"],
                "columns": ["name", "location_id"],
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": ["location_id"],
                        "remote_keys": ["location_id"],
                    }
                ],
            },
            "sample": {
                "type": "data",
                "keys": ["sample_id"],
                "columns": ["name", "site_id"],
                "foreign_keys": [
                    {
                        "entity": "site",
                        "local_keys": ["site_id"],
                        "remote_keys": ["site_id"],
                    }
                ],
            },
        },
        options={},
        metadata=ProjectMetadata(
            name="test_project",
            description="Test project",
            version="1.0.0",
            file_path="test_project.yml",
            entity_count=3,
            created_at=0,
            modified_at=0,
            is_valid=True,
            type="shapeshifter-project",
        ),
    )


@pytest.mark.asyncio
class TestInitializeTaskList:
    """Tests for initialize_task_list method."""

    async def test_initialize_all_strategy(self, mock_project):
        """Test initializing task list with 'all' strategy."""
        service = TaskService()

        # Mock dependencies
        with (
            patch.object(service.project_service, "load_project", return_value=mock_project),
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_core") as mock_to_core,
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_api_config", return_value=mock_project),
            patch.object(service.project_service, "save_project", return_value=mock_project),
        ):

            # Mock core project
            mock_core_project = Mock()
            mock_core_project.tables = {
                "location": Mock(foreign_keys=[]),
                "site": Mock(foreign_keys=[Mock()]),
                "sample": Mock(foreign_keys=[Mock()]),
            }
            mock_core_project.cfg = {}
            mock_to_core.return_value = mock_core_project

            result = await service.initialize_task_list("test_project", "all")

            # Verify result
            assert result["success"] is True
            assert result["strategy"] == "all"
            assert len(result["required_entities"]) == 3
            assert set(result["required_entities"]) == {"location", "site", "sample"}

            # Verify task_list was created in cfg
            assert "task_list" in mock_core_project.cfg
            assert mock_core_project.cfg["task_list"]["completed"] == []
            assert mock_core_project.cfg["task_list"]["ignored"] == []

    async def test_initialize_required_only_strategy(self, mock_project):
        """Test initializing task list with 'required-only' strategy."""
        service = TaskService()

        with (
            patch.object(service.project_service, "load_project", return_value=mock_project),
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_core") as mock_to_core,
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_api_config", return_value=mock_project),
            patch.object(service.project_service, "save_project", return_value=mock_project),
        ):

            # Mock core project with foreign keys
            mock_core_project = Mock()
            mock_core_project.tables = {
                "location": Mock(foreign_keys=[]),  # No FKs
                "site": Mock(foreign_keys=[Mock()]),  # Has FKs
                "sample": Mock(foreign_keys=[Mock()]),  # Has FKs
            }
            mock_core_project.cfg = {}
            mock_to_core.return_value = mock_core_project

            result = await service.initialize_task_list("test_project", "required-only")

            # Should only include entities with foreign keys
            assert result["success"] is True
            assert len(result["required_entities"]) == 2
            assert set(result["required_entities"]) == {"site", "sample"}

    async def test_initialize_invalid_strategy(self, mock_project):
        """Test that invalid strategy raises ValueError."""
        service = TaskService()

        with patch.object(service.project_service, "load_project", return_value=mock_project):
            with pytest.raises(ValueError, match="Invalid strategy"):
                await service.initialize_task_list("test_project", "invalid-strategy")

    async def test_initialize_dependency_order_strategy(self, mock_project):
        """Test initializing with dependency-order strategy."""
        service = TaskService()

        with (
            patch.object(service.project_service, "load_project", return_value=mock_project),
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_core") as mock_to_core,
            patch("backend.app.mappers.project_mapper.ProjectMapper.to_api_config", return_value=mock_project),
            patch.object(service.project_service, "save_project", return_value=mock_project),
            patch("backend.app.services.task_service.get_dependency_service") as mock_get_dep_service,
        ):

            mock_core_project = Mock()
            mock_core_project.tables = {"location": Mock(), "site": Mock(), "sample": Mock()}
            mock_core_project.cfg = {}
            mock_to_core.return_value = mock_core_project

            # Mock dependency service returning resolved dependency graph
            mock_dep_service = Mock()
            mock_dep_service.analyze_dependencies.return_value = {"topological_order": ["location", "site", "sample"]}
            mock_get_dep_service.return_value = mock_dep_service

            result = await service.initialize_task_list("test_project", "dependency-order")

            assert result["success"] is True
            assert result["strategy"] == "dependency-order"
            assert result["required_entities"] == ["location", "site", "sample"]
