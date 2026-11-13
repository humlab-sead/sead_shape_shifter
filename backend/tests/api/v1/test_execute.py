"""Route tests for output expectation results in full execution responses."""

from typing import Literal
from unittest.mock import AsyncMock

import pytest

from backend.app.core.config import settings
from backend.app.services import execute_service, project_service, validation_service, yaml_service
from src.output_expectations import OutputExpectationEvaluation, OutputExpectationResult

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""

    def clear() -> None:
        project_service._project_service = None
        validation_service._validation_service = None
        yaml_service._yaml_service = None
        execute_service._execute_service = None

    clear()
    yield
    clear()


def expectation_result(
    name: str,
    *,
    entity: str = "site",
    metric: str = "row_count",
    group_value: object | None = None,
    measured_value: int | None = 1,
    expected_limit: dict[str, int] | None = None,
    status: Literal["pass", "fail"] = "pass",
    failure_reason: str | None = None,
) -> OutputExpectationResult:
    """Build one Core output expectation result for route tests."""
    return OutputExpectationResult(
        name=name,
        entity=entity,
        metric=metric,
        group_value=group_value,
        measured_value=measured_value,
        expected_limit=expected_limit or {"equals": 1},
        status=status,
        failure_reason=failure_reason,
    )


async def create_executable_project(client, name: str) -> None:
    """Create a project and add a valid output expectation declaration."""
    create_response = await client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {
                "site": {
                    "type": "entity",
                    "keys": ["site_key"],
                    "columns": ["site_key"],
                    "depends_on": [],
                }
            },
        },
    )
    assert create_response.status_code in (200, 201), create_response.text

    update_response = await client.put(
        f"/api/v1/projects/{name}",
        json={
            "entities": {},
            "options": {"output_expectations": [{"name": "site-count", "entity": "site", "metric": "row_count", "equals": 1}]},
        },
    )
    assert update_response.status_code == 200, update_response.text


def configure_execution(monkeypatch: pytest.MonkeyPatch, evaluation: OutputExpectationEvaluation) -> AsyncMock:
    """Stub workflow and optional validation while keeping path handling real."""
    workflow = AsyncMock(return_value=evaluation)
    monkeypatch.setattr("backend.app.services.execute_service.workflow", workflow)
    monkeypatch.setattr(execute_service.ExecuteService, "_validate_project", AsyncMock(return_value=(True, [])))
    return workflow


@pytest.mark.asyncio
@pytest.mark.parametrize(("run_validation", "expected_validation"), [(False, None), (True, True)])
async def test_execute_reports_all_results_on_mismatch(
    authorized_client,
    tmp_path,
    monkeypatch,
    reset_services,
    run_validation: bool,
    expected_validation: bool | None,
) -> None:
    """A failed check returns every result and leaves optional validation status unchanged."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    project_name = f"expectation-mismatch-{run_validation}"
    await create_executable_project(authorized_client, project_name)

    evaluation = OutputExpectationEvaluation(
        results=[
            expectation_result(
                "site-count",
                measured_value=0,
                status="fail",
                failure_reason="Measured value 0 does not satisfy the expected value 1.",
            ),
            expectation_result(
                "sites-by-project",
                metric="grouped_row_count",
                group_value="north",
                measured_value=0,
                status="fail",
                failure_reason="Measured value 0 does not satisfy the minimum 1.",
            ),
            expectation_result(
                "sites-without-project",
                metric="grouped_row_count",
                group_value=None,
                measured_value=1,
                status="pass",
            ),
            expectation_result(
                "missing-site-count",
                entity="missing",
                measured_value=None,
                status="fail",
                failure_reason="Expected entity 'missing' is missing from completed output.",
            ),
        ],
        passed=False,
    )
    workflow = configure_execution(monkeypatch, evaluation)

    response = await authorized_client.post(
        f"/api/v1/projects/{project_name}/execute",
        json={"dispatcher_key": "csv", "target": "site.csv", "run_validation": run_validation},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is False
    assert payload["validation_passed"] is expected_validation
    assert payload["download_path"] is None
    assert payload["target"] == ""
    assert [item["name"] for item in payload["output_expectation_results"]] == [
        "site-count",
        "sites-by-project",
        "sites-without-project",
        "missing-site-count",
    ]
    assert payload["output_expectation_results"][0]["status"] == "fail"
    assert payload["output_expectation_results"][0]["measured_value"] == 0
    assert payload["output_expectation_results"][0]["expected_limit"] == {"equals": 1}
    assert "Measured value 0" in (payload["error_details"] or "")
    assert payload["output_expectation_results"][1]["group_value"] == "north"
    assert payload["output_expectation_results"][2]["group_value"] is None
    assert payload["output_expectation_results"][2]["status"] == "pass"
    assert payload["output_expectation_results"][3]["measured_value"] is None
    assert payload["output_expectation_results"][3]["failure_reason"] is not None
    workflow.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_reports_results_on_success(authorized_client, tmp_path, monkeypatch, reset_services) -> None:
    """A passing run returns results with measurements and a download path."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    project_name = "expectation-success"
    await create_executable_project(authorized_client, project_name)

    evaluation = OutputExpectationEvaluation(
        results=[
            expectation_result("site-count", measured_value=4, expected_limit={"min": 1, "max": 5}),
            expectation_result(
                "sites-by-project",
                metric="grouped_row_count",
                group_value="north",
                measured_value=2,
                expected_limit={"equals": 2},
            ),
        ],
        passed=True,
    )
    workflow = configure_execution(monkeypatch, evaluation)

    response = await authorized_client.post(
        f"/api/v1/projects/{project_name}/execute",
        json={"dispatcher_key": "xlsx", "target": "site.xlsx", "run_validation": False},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["validation_passed"] is None
    assert payload["download_path"] is not None
    assert [item["status"] for item in payload["output_expectation_results"]] == ["pass", "pass"]
    assert payload["output_expectation_results"][0]["measured_value"] == 4
    assert payload["output_expectation_results"][0]["expected_limit"] == {"min": 1, "max": 5}
    assert payload["output_expectation_results"][1]["group_value"] == "north"
    workflow.assert_awaited_once()
