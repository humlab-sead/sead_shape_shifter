"""Measure configured output expectations against normalized tables."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from src.model import ShapeShiftProject


@dataclass(frozen=True)
class OutputExpectationResult:
    """Store the measured value and comparison result for one expectation."""

    name: str
    entity: str
    metric: str
    group_value: Any | None
    measured_value: int | None
    expected_limit: dict[str, int]
    status: Literal["pass", "fail"]
    failure_reason: str | None = None


@dataclass(frozen=True)
class OutputExpectationEvaluation:
    """Store all results and the combined pass/fail status."""

    results: list[OutputExpectationResult]
    passed: bool


def evaluate_output_expectations(
    project: ShapeShiftProject,
    tables: Mapping[str, pd.DataFrame],
    incomplete_entities: Mapping[str, str],
) -> OutputExpectationEvaluation:
    """Measure configured expectations from completed in-memory entity tables."""
    results: list[OutputExpectationResult] = []

    for expectation in project.options.get("output_expectations", []):
        name: str = expectation["name"]
        entity: str = expectation["entity"]
        metric: str = expectation["metric"]
        entity_reason = _entity_failure_reason(entity, tables, incomplete_entities)

        if metric == "grouped_row_count":
            column: str = expectation["column"]
            for group_value, limits in expectation["groups"].items():
                expected_limit = _expected_limit(limits)
                if entity_reason is not None:
                    results.append(
                        _failed_result(
                            name=name,
                            entity=entity,
                            metric=metric,
                            group_value=group_value,
                            expected_limit=expected_limit,
                            reason=entity_reason,
                        )
                    )
                    continue

                table = tables[entity]
                if column not in table.columns:
                    results.append(
                        _failed_result(
                            name=name,
                            entity=entity,
                            metric=metric,
                            group_value=group_value,
                            expected_limit=expected_limit,
                            reason=f"Grouping column '{column}' is missing from entity '{entity}'.",
                        )
                    )
                    continue

                group_values = table[column]
                matches = group_values.isna() if group_value is None else group_values.eq(group_value).fillna(False)
                measured_value = int(matches.sum())
                results.append(
                    _compared_result(
                        name=name,
                        entity=entity,
                        metric=metric,
                        group_value=group_value,
                        measured_value=measured_value,
                        expected_limit=expected_limit,
                    )
                )
            continue

        expected_limit = _expected_limit(expectation)
        if entity_reason is not None:
            results.append(
                _failed_result(
                    name=name,
                    entity=entity,
                    metric=metric,
                    group_value=None,
                    expected_limit=expected_limit,
                    reason=entity_reason,
                )
            )
            continue

        table = tables[entity]
        if metric == "row_count":
            measured_value = len(table)
        else:
            key_columns = project.get_table(entity).safe_keys
            missing_columns = [column for column in key_columns if column not in table.columns]
            if missing_columns:
                results.append(
                    _failed_result(
                        name=name,
                        entity=entity,
                        metric=metric,
                        group_value=None,
                        expected_limit=expected_limit,
                        reason=f"Business key columns are missing from entity '{entity}': {', '.join(missing_columns)}.",
                    )
                )
                continue

            key_values = table.loc[:, key_columns]
            complete_keys = key_values.loc[key_values.notna().all(axis=1)]
            measured_value = int(len(complete_keys.drop_duplicates()))

        results.append(
            _compared_result(
                name=name,
                entity=entity,
                metric=metric,
                group_value=None,
                measured_value=measured_value,
                expected_limit=expected_limit,
            )
        )

    return OutputExpectationEvaluation(
        results=results,
        passed=all(result.status == "pass" for result in results),
    )


def _entity_failure_reason(
    entity: str,
    tables: Mapping[str, pd.DataFrame],
    incomplete_entities: Mapping[str, str],
) -> str | None:
    """Return why an expected entity has no complete table."""
    if entity in incomplete_entities:
        return f"Expected entity '{entity}' is incomplete: {incomplete_entities[entity]}"
    if entity not in tables:
        return f"Expected entity '{entity}' is missing from completed output."
    return None


def _expected_limit(comparison: Mapping[str, int]) -> dict[str, int]:
    """Copy the configured comparison limits for one result."""
    return {key: comparison[key] for key in ("equals", "min", "max") if key in comparison}


def _compared_result(
    *,
    name: str,
    entity: str,
    metric: str,
    group_value: Any | None,
    measured_value: int,
    expected_limit: dict[str, int],
) -> OutputExpectationResult:
    """Return a result with the configured comparison applied."""
    if _meets_limit(measured_value, expected_limit):
        return OutputExpectationResult(
            name=name,
            entity=entity,
            metric=metric,
            group_value=group_value,
            measured_value=measured_value,
            expected_limit=expected_limit,
            status="pass",
        )

    return _failed_result(
        name=name,
        entity=entity,
        metric=metric,
        group_value=group_value,
        expected_limit=expected_limit,
        measured_value=measured_value,
        reason=f"Measured value {measured_value} does not satisfy {_limit_description(expected_limit)}.",
    )


def _failed_result(
    *,
    name: str,
    entity: str,
    metric: str,
    group_value: Any | None,
    expected_limit: dict[str, int],
    reason: str,
    measured_value: int | None = None,
) -> OutputExpectationResult:
    """Return a failed result with its reason and optional measured value."""
    return OutputExpectationResult(
        name=name,
        entity=entity,
        metric=metric,
        group_value=group_value,
        measured_value=measured_value,
        expected_limit=expected_limit,
        status="fail",
        failure_reason=reason,
    )


def _meets_limit(value: int, expected_limit: Mapping[str, int]) -> bool:
    """Check an exact value or inclusive minimum and maximum."""
    if "equals" in expected_limit:
        return value == expected_limit["equals"]
    return ("min" not in expected_limit or value >= expected_limit["min"]) and (
        "max" not in expected_limit or value <= expected_limit["max"]
    )


def _limit_description(expected_limit: Mapping[str, int]) -> str:
    """Describe the configured exact value or inclusive range."""
    if "equals" in expected_limit:
        return f"the expected value {expected_limit['equals']}"
    if "min" in expected_limit and "max" in expected_limit:
        return f"the inclusive range {expected_limit['min']} through {expected_limit['max']}"
    if "min" in expected_limit:
        return f"the minimum {expected_limit['min']}"
    return f"the maximum {expected_limit['max']}"
