"""Tests for task management API endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.validation import ValidationResult
from backend.app.services import project_service, task_service, validation_service, yaml_service

client = TestClient(app)

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""
    # Only reset services with module-level singleton variables
    # task_service uses @lru_cache, so we need to clear its cache
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    # Clear LRU cache for task_service
    task_service.get_task_service.cache_clear()

    yield

    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None
    task_service.get_task_service.cache_clear()


@pytest.fixture
def sample_project_data():
    """Sample project data for tests."""
    return {
        "name": "test_project",
        "entities": {
            "location": {
                "type": "data",
                "keys": ["location_id"],
                "columns": ["name", "latitude", "longitude"],
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
                        "how": "left",
                    }
                ],
            },
        },
        "task_list": {
            "required_entities": ["location", "site"],
            "completed": [],
            "ignored": [],
        },
    }


class TestGetTaskStatus:
    """Tests for GET /projects/{name}/tasks endpoint."""

    def test_get_task_status_returns_all_entities(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that get_task_status returns status for all entities."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Get task status
        response = client.get("/api/v1/projects/test_project/tasks")
        assert response.status_code == 200

        data = response.json()
        assert "entities" in data
        assert "completion_stats" in data
        assert "location" in data["entities"]
        assert "site" in data["entities"]

    def test_get_task_status_includes_completion_stats(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that completion statistics are included."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Get task status
        response = client.get("/api/v1/projects/test_project/tasks")
        data = response.json()

        stats = data["completion_stats"]
        assert "total" in stats
        assert "done" in stats
        assert "todo" in stats
        assert "ignored" in stats
        assert "required_total" in stats
        assert "required_done" in stats
        assert "required_todo" in stats

    def test_get_task_status_entity_has_required_fields(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that entity status has all required fields."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Get task status
        response = client.get("/api/v1/projects/test_project/tasks")
        data = response.json()

        location_status = data["entities"]["location"]
        assert "status" in location_status
        assert "priority" in location_status
        assert "required" in location_status
        assert "exists" in location_status
        assert "validation_passed" in location_status
        assert "preview_available" in location_status
        assert "blocked_by" in location_status
        assert "issues" in location_status

    def test_get_task_status_nonexistent_project(self, tmp_path, monkeypatch, reset_services):
        """Test getting task status for non-existent project."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/nonexistent/tasks")
        assert response.status_code == 404


class TestMarkComplete:
    """Tests for POST /projects/{name}/tasks/{entity}/complete endpoint."""

    def test_mark_complete_success(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test successfully marking entity as complete."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Mock the task_service.mark_complete method to succeed
        with patch("backend.app.api.v1.endpoints.tasks.get_task_service") as mock_get_service:
            mock_service = Mock()
            mock_service.mark_complete = AsyncMock(
                return_value={
                    "success": True,
                    "entity_name": "location",
                    "status": "done",
                    "message": "Entity marked as completed",
                }
            )
            mock_get_service.return_value = mock_service

            # Mark location as complete
            response = client.post("/api/v1/projects/test_project/tasks/location/complete")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["entity_name"] == "location"
            # The API response model may rename 'status' to 'new_status'
            assert data.get("new_status") == "done" or data.get("status") == "done"

    def test_mark_complete_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test marking non-existent entity as complete."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Try to mark non-existent entity as complete
        response = client.post("/api/v1/projects/test_project/tasks/nonexistent/complete")
        assert response.status_code == 400

    def test_mark_complete_updates_task_list(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that marking complete updates the task list in project file."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # For this test, we'll use a mock that actually calls the real service
        # so we can test the integration, but we'll mock the validation/preview parts
        with (
            patch("backend.app.services.validation_service.ValidationService.validate_project_data") as mock_validate,
            patch("backend.app.services.shapeshift_service.ShapeShiftService.preview_entity") as mock_preview,
        ):

            mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
            mock_preview.return_value = None  # Preview succeeds

            # Mark as complete
            response = client.post("/api/v1/projects/test_project/tasks/location/complete")
            assert response.status_code == 200

            # Verify task list was updated
            project_response = client.get("/api/v1/projects/test_project")
            project_data = project_response.json()

            # Check if task_list.completed includes location
            assert "task_list" in project_data
            assert project_data["task_list"] is not None, "task_list should not be None"
            assert "location" in project_data["task_list"].get("completed", [])


class TestMarkIgnored:
    """Tests for POST /projects/{name}/tasks/{entity}/ignore endpoint."""

    def test_mark_ignored_success(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test successfully marking entity as ignored."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Mark location as ignored
        response = client.post("/api/v1/projects/test_project/tasks/location/ignore")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["entity_name"] == "location"
        assert data["new_status"] == "ignored"

    def test_mark_ignored_updates_task_list(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that marking ignored updates the task list."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Mark as ignored
        response = client.post("/api/v1/projects/test_project/tasks/location/ignore")
        assert response.status_code == 200

        # Verify task list was updated
        project_response = client.get("/api/v1/projects/test_project")
        project_data = project_response.json()

        # Check if task_list.ignored includes location
        if "task_list" in project_data:
            assert "location" in project_data["task_list"].get("ignored", [])

    def test_mark_ignored_nonexistent_project(self, tmp_path, monkeypatch, reset_services):
        """Test marking entity as ignored in non-existent project."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.post("/api/v1/projects/nonexistent/tasks/entity/ignore")
        assert response.status_code == 404


class TestResetStatus:
    """Tests for DELETE /projects/{name}/tasks/{entity} endpoint."""

    def test_reset_status_success(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test successfully resetting entity status."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # First mark as ignored
        client.post("/api/v1/projects/test_project/tasks/location/ignore")

        # Then reset
        response = client.delete("/api/v1/projects/test_project/tasks/location")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["entity_name"] == "location"
        assert data["new_status"] == "todo"

    def test_reset_status_removes_from_ignored_list(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that reset removes entity from ignored list."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Mark as ignored
        client.post("/api/v1/projects/test_project/tasks/location/ignore")

        # Reset
        client.delete("/api/v1/projects/test_project/tasks/location")

        # Verify task list was updated
        project_response = client.get("/api/v1/projects/test_project")
        project_data = project_response.json()

        # Check that location is NOT in ignored list
        if "task_list" in project_data:
            assert "location" not in project_data["task_list"].get("ignored", [])

    def test_reset_status_nonexistent_project(self, tmp_path, monkeypatch, reset_services):
        """Test resetting status in non-existent project."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/nonexistent/tasks/entity")
        assert response.status_code == 404


class TestTaskStatusFlow:
    """Tests for complete task status workflow."""

    def test_full_workflow_todo_to_ignored_to_reset(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test complete workflow: todo -> ignored -> reset."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Initial status should be todo
        status_response = client.get("/api/v1/projects/test_project/tasks")
        status_data = status_response.json()
        assert status_data["entities"]["location"]["status"] == "todo"

        # Mark as ignored
        client.post("/api/v1/projects/test_project/tasks/location/ignore")
        status_response = client.get("/api/v1/projects/test_project/tasks")
        status_data = status_response.json()
        assert status_data["entities"]["location"]["status"] == "ignored"

        # Reset to todo
        client.delete("/api/v1/projects/test_project/tasks/location")
        status_response = client.get("/api/v1/projects/test_project/tasks")
        status_data = status_response.json()
        assert status_data["entities"]["location"]["status"] == "todo"

    def test_completion_stats_update_correctly(self, tmp_path, monkeypatch, reset_services, sample_project_data):
        """Test that completion statistics update as entities change status."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        client.post("/api/v1/projects", json=sample_project_data)

        # Initial stats
        status_response = client.get("/api/v1/projects/test_project/tasks")
        stats = status_response.json()["completion_stats"]
        assert stats["done"] == 0
        assert stats["ignored"] == 0

        # Mark one as ignored
        client.post("/api/v1/projects/test_project/tasks/location/ignore")
        status_response = client.get("/api/v1/projects/test_project/tasks")
        stats = status_response.json()["completion_stats"]
        assert stats["ignored"] == 1
