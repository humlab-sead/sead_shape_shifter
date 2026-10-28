"""Tests for project-load issue collector registration and aggregation."""

from typing import Any

from backend.app.mappers.project_load_issue_collector import ProjectLoadIssueCollectorRegistry, ProjectLoadIssues
from backend.app.models.validation import ValidationError


class StaticProjectLoadIssueCollector:
    """Return fixed load issues for registry tests."""

    def __init__(self, result: ProjectLoadIssues) -> None:
        self.result = result

    def collect(
        self,
        cfg_dict: dict[str, Any],  # pylint: disable=unused-argument
        project_name: str,  # pylint: disable=unused-argument
        filename: str | None = None,  # pylint: disable=unused-argument
    ) -> ProjectLoadIssues:
        return self.result


def test_registry_aggregates_registered_collector_results() -> None:
    registry = ProjectLoadIssueCollectorRegistry()
    registry.register("first", StaticProjectLoadIssueCollector(ProjectLoadIssues(warnings=["first warning"])))
    issue = ValidationError(severity="error", message="second error")
    registry.register("second", StaticProjectLoadIssueCollector(ProjectLoadIssues(errors=[issue])))

    result = registry.collect({"entities": {}}, "test-project")

    assert result.warnings == ["first warning"]
    assert result.errors == [issue]
