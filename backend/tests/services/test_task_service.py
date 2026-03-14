"""Tests for task service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
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

    # Mock task list (using new format)
    task_list = MagicMock(spec=TaskList)
    task_list.required_entities = ["location", "site", "sample"]
    task_list.todo = ["site", "sample"]  # Entities not yet done
    task_list.done = ["location"]  # Done entities
    task_list.ongoing = []
    task_list.ignored = []
    task_list.flagged = {}
    task_list.is_required.side_effect = lambda name: name in ["location", "site", "sample"]
    task_list.is_done.side_effect = lambda name: name in ["location"]
    task_list.is_todo.side_effect = lambda name: name in ["site", "sample"]
    task_list.is_ongoing.side_effect = lambda name: name in []
    task_list.is_ignored.side_effect = lambda name: name in []
    task_list.is_flagged.side_effect = lambda name: False
    task_list.mark_completed = MagicMock()
    task_list.mark_todo = MagicMock()
    task_list.mark_ongoing = MagicMock()
    task_list.mark_ignored = MagicMock()
    task_list.reset_status = MagicMock()
    project.task_list = task_list
    task_list.is_ignored.side_effect = lambda name: name in []
    task_list.is_flagged.side_effect = lambda name: False
    task_list.mark_completed = MagicMock()
    task_list.mark_todo = MagicMock()
    task_list.mark_ongoing = MagicMock()
    task_list.mark_ignored = MagicMock()
    task_list.reset_status = MagicMock()
    project.task_list = task_list

    # Mock table configs
    def get_table_mock(name):
        table = MagicMock()
        table.depend_on = []
        table.foreign_keys = []
        return table

    project.get_table.side_effect = get_table_mock

    # Add cfg attribute that save_project expects (using new format)
    project.cfg = {
        "entities": {"location": {}, "site": {}, "sample": {}},
        "options": {},
        "tasks": {"location": {"status": "done"}, "site": {"status": "todo"}},  # Add tasks for mark_complete/ignore methods
    }

    return project


@pytest.fixture
def mock_api_project():
    """Create mock API Project."""
    project = MagicMock(spec=Project)
    # Add task_list attribute that is accessed in task_service methods (using new format)
    project.task_list = {
        "todo": ["site", "sample"],
        "done": ["location"],
        "ongoing": [],
        "ignored": [],
    }
    return project


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
    async def test_compute_status_returns_all_entities(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that compute_status returns status for all entities."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert len(result.entities) == 3
            assert "location" in result.entities
            assert "site" in result.entities
            assert "sample" in result.entities

    @pytest.mark.asyncio
    async def test_compute_status_marks_done_entity_as_done(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that done entities have done status."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["location"].status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_compute_status_marks_todo_entities_as_todo(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that todo entities have todo status."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].status == TaskStatus.TODO
            assert result.entities["sample"].status == TaskStatus.TODO

    @pytest.mark.asyncio
    async def test_compute_status_includes_ignored_only_entities(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Fresh sidecar task state should include ignored-only entities in task status."""
        mock_core_project.table_names = ["location", "site", "sample"]
        mock_core_project.has_table.side_effect = lambda name: name in ["location", "site", "sample"]
        mock_core_project.task_list.ignored = []
        mock_core_project.task_list.is_ignored.side_effect = lambda name: False
        mock_core_project.task_list.is_required.side_effect = lambda name: name in ["location", "site", "sample"]
        mock_core_project.task_list.is_done.side_effect = lambda name: name in ["location"]
        mock_core_project.task_list.is_todo.side_effect = lambda name: name in ["site", "sample"]
        mock_core_project.task_list.is_ongoing.side_effect = lambda name: False

        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        refreshed_task_list = TaskList(
            {
                "todo": ["site", "sample"],
                "done": ["location"],
                "ignored": ["taxa_persistence"],
            }
        )

        def refresh_task_list(_project_name: str, project: ShapeShiftProject) -> None:
            project.cfg["task_list"] = refreshed_task_list.to_dict()
            project.task_list = refreshed_task_list

        task_service._refresh_project_task_list = Mock(side_effect=refresh_task_list)

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert "taxa_persistence" in result.entities
            assert result.entities["taxa_persistence"].status == TaskStatus.IGNORED

    @pytest.mark.asyncio
    async def test_compute_status_calculates_stats(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that completion statistics are calculated correctly."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        # Mock ProjectMapper.to_core to return our core project
        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.completion_stats["total"] == 3
            assert result.completion_stats["done"] == 1
            assert result.completion_stats["todo"] == 2
            assert result.completion_stats["completion_percentage"] == pytest.approx(33.3333333333)
            assert result.completion_stats["required_total"] == 3
            assert result.completion_stats["required_done"] == 1

    @pytest.mark.asyncio
    async def test_compute_status_marks_entities_with_notes(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Entities with sidecar notes should expose has_note in task status."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()
        task_service.sidecar_manager.load_notes = Mock(return_value={"site": "Need coordinates"})

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].has_note is True
            assert result.entities["location"].has_note is False


class TestTaskServicePriority:
    """Tests for priority determination."""

    @pytest.mark.asyncio
    async def test_required_entity_without_errors_is_ready(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that required entity with no errors has ready priority."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
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

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].priority == TaskPriority.CRITICAL
            assert not result.entities["site"].validation_passed

    @pytest.mark.asyncio
    async def test_ignored_entity_is_optional_priority(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that ignored entities have optional priority."""
        # Mark site as ignored
        mock_core_project.task_list.ignored = ["site"]
        mock_core_project.task_list.is_ignored.side_effect = lambda name: name == "site"

        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.preview_entity = AsyncMock()

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].status == TaskStatus.IGNORED
            assert result.entities["site"].priority == TaskPriority.OPTIONAL


class TestTaskServiceMarkComplete:
    """Tests for marking entities as complete."""

    @pytest.mark.asyncio
    async def test_mark_complete_validates_entity(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete validates entity before marking done."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(
            return_value=ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        task_service.shapeshift_service.preview_entity = AsyncMock()

        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.mark_complete("test-project", "site")

            assert result["success"] is True
            assert result["status"] == "done"
            task_service.validation_service.validate_project_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_complete_checks_preview_availability(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete checks preview generation."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(
            return_value=ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        task_service.shapeshift_service.preview_entity = AsyncMock()

        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            await task_service.mark_complete("test-project", "site")

            task_service.shapeshift_service.preview_entity.assert_called_once()
            task_service.shapeshift_service.preview_entity.assert_called_once_with(
                project_name="test-project",
                entity_name="site",
                limit=1,
            )

    @pytest.mark.asyncio
    async def test_compute_status_uses_project_name_for_cache_lookups(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test that compute_status checks preview cache using request project_name, not project.filename."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)

        # Cache + version checks should use the route project name to match preview endpoint keys
        task_service.shapeshift_service.get_project_version = Mock(return_value=123)
        task_service.shapeshift_service.cache = MagicMock()
        task_service.shapeshift_service.cache.get_dataframe = Mock(return_value=MagicMock(spec=pd.DataFrame))

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            await task_service.compute_status("test-project")

            assert task_service.shapeshift_service.get_project_version.call_count == 3
            task_service.shapeshift_service.get_project_version.assert_called_with("test-project")
            assert task_service.shapeshift_service.cache.get_dataframe.call_count == 3
            for call in task_service.shapeshift_service.cache.get_dataframe.call_args_list:
                assert call.kwargs["project_name"] == "test-project"

    @pytest.mark.asyncio
    async def test_compute_status_falls_back_to_version_only_cache_lookup_when_hash_check_misses(
        self, task_service: TaskService, mock_api_project, mock_core_project, mock_validation_result
    ):
        """Test preview availability fallback when strict entity-hash cache lookup misses."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(return_value=mock_validation_result)
        task_service.shapeshift_service.get_project_version = Mock(return_value=123)
        task_service.shapeshift_service.cache = MagicMock()

        # For entities evaluated for preview, strict lookups miss and fallback lookups hit.
        # Use kwargs-based side effect to avoid dependence on set iteration order.
        def get_dataframe_side_effect(*args, **kwargs):
            entity_name = kwargs.get("entity_name")
            is_strict = "entity_config" in kwargs
            if entity_name in {"site", "sample"}:
                if is_strict:
                    return None
                return MagicMock(spec=pd.DataFrame)
            return MagicMock(spec=pd.DataFrame)

        task_service.shapeshift_service.cache.get_dataframe = Mock(side_effect=get_dataframe_side_effect)

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await task_service.compute_status("test-project")

            assert result.entities["site"].preview_available is True
            assert result.entities["sample"].preview_available is True
            assert task_service.shapeshift_service.cache.get_dataframe.call_count >= 4

            # Every call should use request project name key
            for call in task_service.shapeshift_service.cache.get_dataframe.call_args_list:
                assert call.kwargs["project_name"] == "test-project"

            # For site and sample we should observe both strict and fallback lookups
            site_calls = [
                c.kwargs for c in task_service.shapeshift_service.cache.get_dataframe.call_args_list if c.kwargs["entity_name"] == "site"
            ]
            sample_calls = [
                c.kwargs for c in task_service.shapeshift_service.cache.get_dataframe.call_args_list if c.kwargs["entity_name"] == "sample"
            ]
            assert any("entity_config" in c for c in site_calls)
            assert any("entity_config" not in c for c in site_calls)
            assert any("entity_config" in c for c in sample_calls)
            assert any("entity_config" not in c for c in sample_calls)

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

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with pytest.raises(ValueError, match="validation failed"):
                await task_service.mark_complete("test-project", "site")

    @pytest.mark.asyncio
    async def test_mark_complete_fails_if_preview_fails(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete raises error if preview generation fails."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(
            return_value=ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        task_service.shapeshift_service.preview_entity = AsyncMock(side_effect=Exception("Preview failed"))

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with pytest.raises(ValueError, match="preview generation failed"):
                await task_service.mark_complete("test-project", "site")

    @pytest.mark.asyncio
    async def test_mark_complete_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_complete updates task list."""
        task_service.project_service.load_project = Mock(return_value=mock_api_project)
        task_service.validation_service.validate_project_data = AsyncMock(
            return_value=ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        task_service.shapeshift_service.preview_entity = AsyncMock()

        # Mock sidecar manager operations
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        # Patch to_core for validation checks
        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            await task_service.mark_complete("test-project", "site")

            # Verify sidecar was saved with updated task list
            task_service.sidecar_manager.save_task_list.assert_called_once()
            saved_task_list = task_service.sidecar_manager.save_task_list.call_args[0][1]
            assert "site" in saved_task_list.done


class TestTaskServiceMarkIgnored:
    """Tests for marking entities as ignored."""

    @pytest.mark.asyncio
    async def test_mark_ignored_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_ignored updates task list."""
        # Mock sidecar manager operations
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        result = await task_service.mark_ignored("test-project", "site")

        assert result["success"] is True
        assert result["status"] == "ignored"
        # Verify sidecar was saved with updated task list
        task_service.sidecar_manager.save_task_list.assert_called_once()
        saved_task_list = task_service.sidecar_manager.save_task_list.call_args[0][1]
        assert "site" in saved_task_list.ignored

    @pytest.mark.asyncio
    async def test_mark_ignored_saves_sidecar(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that mark_ignored saves sidecar."""
        # Mock sidecar manager operations
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        await task_service.mark_ignored("test-project", "site")

        task_service.sidecar_manager.save_task_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_ignored_does_not_touch_project_cache(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Task sidecar writes should stay separate from project cache management."""
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()
        task_service.project_service.state.invalidate = Mock()

        await task_service.mark_ignored("test-project", "site")

        task_service.project_service.state.invalidate.assert_not_called()


class TestTaskServiceResetStatus:
    """Tests for resetting entity status."""

    @pytest.mark.asyncio
    async def test_reset_status_updates_task_list(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that reset_status updates task list."""
        # Mock sidecar manager operations
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        result = await task_service.reset_status("test-project", "location")

        assert result["success"] is True
        assert result["status"] == "todo"
        # Verify sidecar was saved with updated task list
        task_service.sidecar_manager.save_task_list.assert_called_once()
        saved_task_list = task_service.sidecar_manager.save_task_list.call_args[0][1]
        assert "location" not in saved_task_list.done

    @pytest.mark.asyncio
    async def test_reset_status_saves_sidecar(self, task_service: TaskService, mock_api_project, mock_core_project):
        """Test that reset_status saves sidecar."""
        # Mock sidecar manager operations
        initial_task_list_data = {
            "required_entities": ["location", "site", "sample"],
            "todo": ["site", "sample"],
            "done": ["location"],
            "ongoing": [],
            "ignored": [],
            "flagged": {},
        }
        task_service.sidecar_manager.load_task_list = Mock(return_value=initial_task_list_data)
        task_service.sidecar_manager.save_task_list = Mock()

        await task_service.reset_status("test-project", "location")

        task_service.sidecar_manager.save_task_list.assert_called_once()


class TestTaskServiceNotes:
    """Tests for entity note operations."""

    @pytest.mark.asyncio
    async def test_get_note_returns_existing_note(self, task_service: TaskService):
        """Existing notes should be returned through the service."""
        task_service.sidecar_manager.get_note = Mock(return_value="Need coordinates")

        result = await task_service.get_note("test-project", "site")

        assert result == {
            "success": True,
            "entity_name": "site",
            "note": "Need coordinates",
            "has_note": True,
            "message": "Entity note loaded",
        }

    @pytest.mark.asyncio
    async def test_set_note_persists_note(self, task_service: TaskService):
        """Setting a note should delegate to the sidecar manager."""
        task_service.sidecar_manager.set_note = Mock(return_value="Need coordinates")

        result = await task_service.set_note("test-project", "site", "Need coordinates")

        task_service.sidecar_manager.set_note.assert_called_once()
        assert result["has_note"] is True
        assert result["note"] == "Need coordinates"

    @pytest.mark.asyncio
    async def test_remove_note_clears_note(self, task_service: TaskService):
        """Removing a note should report a cleared note state."""
        task_service.sidecar_manager.remove_note = Mock(return_value=True)

        result = await task_service.remove_note("test-project", "site")

        task_service.sidecar_manager.remove_note.assert_called_once()
        assert result["has_note"] is False
        assert result["note"] is None
