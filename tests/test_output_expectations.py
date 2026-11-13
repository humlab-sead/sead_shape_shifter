from typing import Any

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.output_expectations import evaluate_output_expectations


def project_with(expectations: list[dict[str, Any]]) -> ShapeShiftProject:
    """Build an in-memory project with valid business-key declarations."""
    return ShapeShiftProject(
        cfg={
            "entities": {
                "site": {"keys": ["site_key", "project_key"]},
                "missing": {"keys": ["site_key"]},
                "incomplete": {"keys": ["site_key"]},
            },
            "options": {"output_expectations": expectations},
        }
    )


def test_row_count_includes_rows_with_null_values() -> None:
    project = project_with([{"name": "sites", "entity": "site", "metric": "row_count", "equals": 3}])

    evaluation = evaluate_output_expectations(
        project,
        {"site": pd.DataFrame({"site_key": ["a", "b", None], "project_key": [1, 2, 3]})},
        {},
    )

    assert evaluation.passed is True
    result = evaluation.results[0]
    assert result.name == "sites"
    assert result.entity == "site"
    assert result.metric == "row_count"
    assert result.measured_value == 3
    assert result.expected_limit == {"equals": 3}
    assert result.status == "pass"
    assert result.failure_reason is None


def test_distinct_key_count_excludes_rows_with_any_null_key_component() -> None:
    project = project_with([{"name": "site-identities", "entity": "site", "metric": "distinct_key_count", "equals": 2}])
    table = pd.DataFrame(
        {
            "site_key": ["a", "a", "a", "b", pd.NA],
            "project_key": [1, 1, pd.NA, 2, 3],
        }
    )

    evaluation = evaluate_output_expectations(project, {"site": table}, {})

    assert evaluation.passed is True
    assert evaluation.results[0].measured_value == 2
    assert evaluation.results[0].expected_limit == {"equals": 2}


def test_grouped_count_evaluates_only_configured_groups_including_null() -> None:
    project = project_with(
        [
            {
                "name": "sites-by-project",
                "entity": "site",
                "metric": "grouped_row_count",
                "column": "project",
                "groups": {
                    None: {"equals": 2},
                    "north": {"min": 2},
                    "missing": {"equals": 0},
                },
            }
        ]
    )
    table = pd.DataFrame({"project": [None, pd.NA, "north", "north", "south"]})

    evaluation = evaluate_output_expectations(project, {"site": table}, {})

    assert evaluation.passed is True
    assert evaluation.results[0].name == "sites-by-project"
    assert evaluation.results[0].entity == "site"
    assert evaluation.results[0].metric == "grouped_row_count"
    assert [result.group_value for result in evaluation.results] == [None, "north", "missing"]
    assert [result.measured_value for result in evaluation.results] == [2, 2, 0]
    assert [result.expected_limit for result in evaluation.results] == [
        {"equals": 2},
        {"min": 2},
        {"equals": 0},
    ]
    assert [result.status for result in evaluation.results] == ["pass", "pass", "pass"]


def test_present_empty_table_measures_rows_and_configured_groups_as_zero() -> None:
    project = project_with(
        [
            {"name": "site-total", "entity": "site", "metric": "row_count", "equals": 0},
            {
                "name": "sites-by-project",
                "entity": "site",
                "metric": "grouped_row_count",
                "column": "project",
                "groups": {None: {"equals": 0}, "north": {"equals": 0}},
            },
        ]
    )

    evaluation = evaluate_output_expectations(
        project,
        {"site": pd.DataFrame(columns=["project", "site_key", "project_key"])},
        {},
    )

    assert evaluation.passed is True
    assert [result.measured_value for result in evaluation.results] == [0, 0, 0]


def test_absent_and_incomplete_entities_fail_without_measurements() -> None:
    project = project_with(
        [
            {"name": "missing-site", "entity": "missing", "metric": "row_count", "equals": 0},
            {
                "name": "incomplete-sites",
                "entity": "incomplete",
                "metric": "grouped_row_count",
                "column": "project",
                "groups": {"north": {"min": 0}, None: {"equals": 0}},
            },
        ]
    )

    evaluation = evaluate_output_expectations(
        project,
        {"incomplete": pd.DataFrame({"project": ["north"], "site_key": ["a"]})},
        {"incomplete": "source query failed"},
    )

    assert evaluation.passed is False
    assert len(evaluation.results) == 3
    assert all(result.status == "fail" for result in evaluation.results)
    assert all(result.measured_value is None for result in evaluation.results)
    assert "missing from completed output" in (evaluation.results[0].failure_reason or "")
    assert all("source query failed" in (result.failure_reason or "") for result in evaluation.results[1:])


def test_missing_metric_column_fails_without_a_measurement() -> None:
    project = project_with(
        [
            {
                "name": "sites-by-project",
                "entity": "site",
                "metric": "grouped_row_count",
                "column": "project",
                "groups": {"north": {"equals": 1}},
            }
        ]
    )

    evaluation = evaluate_output_expectations(project, {"site": pd.DataFrame({"site_key": ["a"]})}, {})

    assert evaluation.passed is False
    assert evaluation.results[0].measured_value is None
    assert evaluation.results[0].status == "fail"
    assert "Grouping column 'project' is missing" in (evaluation.results[0].failure_reason or "")


def test_missing_business_key_column_fails_without_a_measurement() -> None:
    project = project_with([{"name": "site-identities", "entity": "site", "metric": "distinct_key_count", "equals": 0}])

    evaluation = evaluate_output_expectations(project, {"site": pd.DataFrame({"site_key": ["a"]})}, {})

    assert evaluation.passed is False
    assert evaluation.results[0].measured_value is None
    assert "Business key columns are missing" in (evaluation.results[0].failure_reason or "")


@pytest.mark.parametrize(
    ("comparison", "passed"),
    [
        ({"equals": 3}, True),
        ({"equals": 2}, False),
        ({"min": 3}, True),
        ({"min": 4}, False),
        ({"max": 3}, True),
        ({"max": 2}, False),
        ({"min": 2, "max": 3}, True),
        ({"min": 4, "max": 5}, False),
    ],
)
def test_comparison_limits_are_applied_inclusively(comparison: dict[str, int], passed: bool) -> None:
    project = project_with([{"name": "sites", "entity": "site", "metric": "row_count", **comparison}])

    evaluation = evaluate_output_expectations(project, {"site": pd.DataFrame(index=range(3))}, {})

    result = evaluation.results[0]
    assert evaluation.passed is passed
    assert result.measured_value == 3
    assert result.expected_limit == comparison
    assert (result.failure_reason is None) is passed
