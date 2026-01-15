"""Tests for task service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.task import TaskPriority, TaskStatus
from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.task_service import TaskService
from src.model import ShapeShiftProject, TaskList

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def mock_core_project():
    """Create mock core ShapeShiftProject."""
    project = MagicMock(spec=ShapeShiftProject)
    project.filename = "test-project.yml"
    project.table_names = ["location", "site", "sample"]
    project.has_table.side_effect = lambda name: name in ["location", "site", "sample"]

    # Mock task list
    task_list = MagicMock(spec=TaskList)
    task_list.required_entities = ["location", "site", "sample"]
    task_list.completed = ["location"]
    task_list.ignored = []
    task_list.is_required.side_effect = lambda name: name in ["location", "site", "sample"]
    task_list.is_completed.side_effect = lambda name: name in ["location"]
    task_list.is_ignored.side_effect = lambda name: name in []
    project.task_list = task_list

    # Mock table configs
    def get_table_mock(name):
        table = MagicMock()
        table.depend_on = []
        table.foreign_keys = []
        return table

    project.get_table.side_effect = get_table_mock

    # Add cfg attribute that save_project expects
    project.cfg = {
        "entities": {"location": {}, "site": {}, "sample": {}},
        "options": {"task_list": {"required": ["location", "site", "sample"], "completed": ["location"], "ignored": []}},
    }

    return project


@pytest.fixture
def mock_api_project():
    """Create mock API Project."""
    return MagicMock(spec=Project)


@pytest.fixture
def mock_validation_result():
    """Create mock validation result."""
    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
    )


@pytest.fixture
def task_service():
    """Create TaskService with mocked dependencies."""
    service = TaskService()

    # Replace service dependencies with mocks
    service.project_service = MagicMock()
    service.validation_service = MagicMock()
    service.shapeshift_service = MagicMock()

    yield service


class TestTaskServiceBasic:
    """Tests for basic task service functionality."""

    @pytest.mark.asyncio
    async def test_compute_status_returns_all_entities(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that compute_status returns status for all entities."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()
        
        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert len(result.entities) == 3
            assert "location" in result.entities
            assert "site" in result.entities
            assert "sample" in result.entities

    @pytest.mark.asyncio
    async def test_compute_status_marks_completed_entity_as_done(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that completed entities have done status."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()
        
        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["location"].status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_compute_status_marks_uncompleted_as_todo(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that uncompleted entities have todo status."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()
        
        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].status == TaskStatus.TODO
            assert result.entities["sample"].status == TaskStatus.TODO

    @pytest.mark.asyncio
    async def test_compute_status_calculates_stats(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that completion statistics are calculated correctly."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()
        
        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.completion_stats["total"] == 3
            assert result.completion_stats["done"] == 1
            assert result.completion_stats["todo"] == 2
            assert result.completion_stats["required_total"] == 3
            assert result.completion_stats["required_done"] == 1


class TestTaskServicePriority:
    """Tests for priority determination."""

    @pytest.mark.asyncio
    async def test_required_entity_without_errors_is_ready(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that required entity with no errors has ready priority."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            # Site should be ready (exists, validates, has preview, no blockers)
            assert result.entities["site"].priority == TaskPriority.READY

    @pytest.mark.asyncio
    async def test_required_entity_with_validation_errors_is_critical(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that required entity with validation errors has critical priority."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)

        # Create validation result with errors for site
        validation_result = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    entity="site",
                    message="Missing required column",
                    severity="error",
                )
            ],
            warnings=[],
        )
        task_service.validation_service.validate_project_data = AsyncMock(return_value=validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].priority == TaskPriority.CRITICAL
            assert not result.entities["site"].validation_passed

    @pytest.mark.asyncio
    async def test_ignored_entity_is_optional_priority(self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result):
        """Test that ignored entities have optional priority."""
        # Mark site as ignored
        mock_core_project.task_list.ignored = ["site"]
        mock_core_project.task_list.is_ignored.side_effect = lambda name: name == "site"

        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].status == TaskStatus.IGNORED
            assert result.entities["site"].priority == TaskPriority.OPTIONAL


class TestTaskServiceMarkComplete:
    """Tests for marking entities as complete."""

    @pytest.mark.asyncio
    async def test_mark_complete_validates_entity(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete validates entity before marking done."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=ValidationResult(is_valid=True, errors=[], warnings=[]))
        task_service.shapeshift_service.preview_entity = AsyncMock()
        task_service.project_service.save_project = Mock()  # Not AsyncMock since it's not awaited

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            result = await task_service.mark_complete("test-project", "site")

            assert result["success"] is True
            assert result["status"] == "done"
            task_service.validation_service.validate_project_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_complete_checks_preview_availability(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete checks preview generation."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=ValidationResult(is_valid=True, errors=[], warnings=[]))
        task_service.shapeshift_service.preview_entity = AsyncMock()
        task_service.project_service.save_project = Mock()  # Not AsyncMock since it's not awaited

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            await task_service.mark_complete("test-project", "site")

            task_service.shapeshift_service.preview_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_complete_fails_if_validation_fails(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete raises error if validation fails."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        entity="site",
                        message="Missing column",
                        severity="error",
                    )
                ],
                warnings=[],
            )
        )

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            with pytest.raises(ValueError, match="validation failed"):
                await task_service.mark_complete("test-project", "site")

    @pytest.mark.asyncio
    async def test_mark_complete_fails_if_preview_fails(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete raises error if preview generation fails."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=ValidationResult(is_valid=True, errors=[], warnings=[]))
        task_service.shapeshift_service.preview_entity = AsyncMock(side_effect=Exception("Preview failed"))

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project):
            with pytest.raises(ValueError, match="preview generation failed"):
                await task_service.mark_complete("test-project", "site")

    @pytest.mark.asyncio
    async def test_mark_complete_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete updates task list."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=ValidationResult(is_valid=True, errors=[], warnings=[]))
        task_service.shapeshift_service.preview_entity = AsyncMock()
        task_service.project_service.save_project = Mock()  # Not AsyncMock since it's not awaited

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            await task_service.mark_complete("test-project", "site")

            mock_core_project.task_list.mark_completed.assert_called_once_with("site")


class TestTaskServiceMarkIgnored:
    """Tests for marking entities as ignored."""

    @pytest.mark.asyncio
    async def test_mark_ignored_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_ignored updates task list."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.project_service.save_project = Mock()  # Not AsyncMock

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            result = await task_service.mark_ignored("test-project", "site")

            assert result["success"] is True
            assert result["status"] == "ignored"
            mock_core_project.task_list.mark_ignored.assert_called_once_with("site")

    @pytest.mark.asyncio
    async def test_mark_ignored_saves_project(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_ignored saves project."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.project_service.save_project = Mock()  # Not AsyncMock

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            await task_service.mark_ignored("test-project", "site")

            task_service.project_service.save_project.assert_called_once()


class TestTaskServiceResetStatus:
    """Tests for resetting entity status."""

    @pytest.mark.asyncio
    async def test_reset_status_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that reset_status updates task list."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.project_service.save_project = Mock()  # Not AsyncMock

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            result = await task_service.reset_status("test-project", "location")

            assert result["success"] is True
            assert result["status"] == "todo"
            mock_core_project.task_list.reset_status.assert_called_once_with("location")

    @pytest.mark.asyncio
    async def test_reset_status_saves_project(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that reset_status saves project."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.project_service.save_project = Mock()  # Not AsyncMock

        with patch.object(ProjectMapper, 'to_core', return_value=mock_core_project), \
             patch.object(ProjectMapper, 'to_api_config', return_value=mock_api_project):
            await task_service.reset_status("test-project", "location")

            task_service.project_service.save_project.assert_called_once()
