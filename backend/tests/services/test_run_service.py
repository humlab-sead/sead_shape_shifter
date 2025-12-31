"""Tests for TestRunService covering happy path and error handling."""

from unittest.mock import MagicMock

import pytest

from backend.app.models.project import Project
from backend.app.models.test_run import OutputFormat, TestRunOptions, TestRunStatus
from backend.app.services.test_run_service import TestRunService

# pylint: disable=redefined-outer-name


@pytest.fixture
def project_service() -> MagicMock:
    """Mock configuration service."""
    return MagicMock()


@pytest.mark.asyncio
async def test_execute_test_run_success_fixed_entity(project_service: MagicMock) -> None:
    """Run completes with fixed entity values and preview rows."""
    project_service.load_project.return_value = Project(
        entities={
            "users": {
                "name": "users",
                "type": "fixed",
                "columns": ["id", "name"],
                "values": [[1, "Alice"], [2, "Bob"]],
            }
        }
    )

    service = TestRunService(project_service=project_service)
    options = TestRunOptions(output_format=OutputFormat.PREVIEW, **{})
    result = service.init_test_run("test_cfg", options)

    await service.execute_test_run(result.run_id)

    stored = service.get_test_result(result.run_id)
    assert stored is not None
    assert stored.status == TestRunStatus.COMPLETED
    assert stored.entities_total == 1
    assert stored.entities_succeeded == 1
    assert stored.entities_failed == 0
    assert stored.entities_processed[0].preview_rows == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@pytest.mark.asyncio
async def test_execute_test_run_invalid_entity_fails(project_service: MagicMock) -> None:
    """Invalid entity selection marks run as failed."""
    project_service.load_project.return_value = Project(
        entities={
            "orders": {"name": "orders", "type": "fixed", "columns": ["id"], "values": [[1]]},
        }
    )

    service = TestRunService(project_service=project_service)
    options = TestRunOptions(entities=["orders", "missing"], **{})
    result = service.init_test_run("test_cfg", options)

    await service.execute_test_run(result.run_id)

    stored = service.get_test_result(result.run_id)
    assert stored is not None
    assert stored.status == TestRunStatus.FAILED
    assert "Invalid entities" in (stored.error_message or "")
    assert stored.entities_failed == 0  # failure occurs before processing


@pytest.mark.asyncio
async def test_process_entity_adds_validation_issue(project_service: MagicMock) -> None:
    """Foreign key validation creates a validation issue when remote entity missing."""
    service = TestRunService(project_service=project_service)
    options = TestRunOptions(validate_foreign_keys=True, **{})
    entity_config = {
        "type": "fixed",
        "columns": ["id"],
        "values": [[1], [2]],
        "foreign_keys": [{"local_keys": ["id"]}],  # missing 'entity'
    }

    result = await service._process_entity("orders", entity_config, options)  # pylint: disable=protected-access

    assert result.status == "success"
    assert len(result.validation_issues) == 1
    issue = result.validation_issues[0]
    assert issue.entity_name == "orders"
    assert "Foreign key missing remote entity name" in issue.message
