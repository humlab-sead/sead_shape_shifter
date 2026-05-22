#!/usr/bin/env python3
"""Run validation workflows for a Shape Shifter project file.

Examples:
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml --workflow structural
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml --workflow conformance
"""

from __future__ import annotations

import abc
import argparse
import asyncio
from email import message
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, Sequence

import click
from loguru import logger
from numpy import str_

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.validation import ValidationError
from backend.app.validators.data_validation_orchestrator import DataValidationOrchestrator, TableStoreDataFetchStrategy
from backend.app.validators.target_model_validator import TargetModelValidator
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications import CompositeProjectSpecification, project
from src.specifications.base import SpecificationIssue
from src.utility import Registry, setup_logging
from src.validators.data_validators import ValidationIssue
from src.issues import CoreIssue


@dataclass
class WorkflowResult:
    """Normalized result for a validation workflow run."""

    name: str
    passed: bool
    issues: list[CoreIssue] = field(default_factory=list)
    skipped: str | None = None

    @staticmethod
    def from_exception(name: str, exc: Exception) -> WorkflowResult:
        """Create a WorkflowResult with a single error issue based on an exception."""
        issue: CoreIssue = CoreIssue(
            severity="error", entity=name, field="workflow", message=f"Workflow failed: {exc}", code="WORKFLOW_FAILED", category="workflow"
        )
        return WorkflowResult(name=name, passed=False, issues=[issue])

    @staticmethod
    def create_skipped(name: str, reason: str) -> WorkflowResult:
        """Create a WorkflowResult representing a skipped workflow."""
        return WorkflowResult(name=name, passed=True, skipped=reason)


class ValidateExecutorRegistry(Registry):
    """Executor for running project validation workflows with consistent error handling and result normalization."""

    items: dict[str, Callable[[ShapeShiftProject], Awaitable[WorkflowResult] | WorkflowResult]] = {}


EXECUTORS = ValidateExecutorRegistry()


class WorkflowExecutor(abc.ABC):
    """Helper for executing validation workflows with consistent error handling and result normalization."""

    def execute(self, project: ShapeShiftProject, ignores: set[str] | None = None) -> WorkflowResult:
        """Execute the workflow for the given project and return a WorkflowResult."""
        try:
            return self._execute(project, ignores or set())
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("{} validation workflow failed", self.get_name())
            return WorkflowResult.from_exception(self.get_name(), exc)

    @abc.abstractmethod
    def _execute(self, project: ShapeShiftProject, ignores: set[str]) -> WorkflowResult:
        """Execute the workflow for the given project and return a WorkflowResult."""
        pass

    def get_name(self) -> str:
        """Return the name/key of this workflow executor."""
        return getattr(self, "key", self.__class__.__name__.lower())


@EXECUTORS.register(key="structural")
class StructuralValidationExecutor(WorkflowExecutor):
    def _execute(self, project: ShapeShiftProject, ignores: set[str]) -> WorkflowResult:
        """Run structural/specification validation."""
        specification = CompositeProjectSpecification(project.cfg)
        is_valid: bool = specification.is_satisfied_by()
        return WorkflowResult(
            name=self.get_name(),
            passed=is_valid,
            issues=[issue for issue in specification.errors + specification.warnings if issue.code not in ignores],
        )


@EXECUTORS.register(key="data")
class DataValidationExecutor(WorkflowExecutor):
    def _execute(self, project: ShapeShiftProject, ignores: set[str]) -> WorkflowResult:
        """Run data validation against the fully normalized in-memory table store."""
        normalizer = ShapeShifter(project)
        asyncio.run(normalizer.normalize())

        orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(normalizer.table_store))
        issues: list[ValidationIssue] = asyncio.run(
            orchestrator.validate_all_entities(
                core_project=project,
                project_name=project.metadata.name or Path(project.filename).stem,
            )
        )

        return WorkflowResult(
            name="data",
            passed=all(issue.severity != "error" for issue in issues),
            issues=[issue for issue in issues if issue.code not in ignores],
        )


@EXECUTORS.register(key="conformance")
class ConformanceValidationExecutor(WorkflowExecutor):
    def _execute(self, project: ShapeShiftProject, ignores: set[str]) -> WorkflowResult:
        """Run target-model conformance validation if the project defines a target model."""

        def map_error_to_issue(error: ValidationError) -> ValidationIssue:
            return ValidationIssue(
                severity="error",
                message=error.message,
                entity=error.entity,
                field=error.field,
                code=error.code,
                category="conformance",
                metadata={"message": error.message},
            )

        target_model_data: dict[str, Any] | None = project.metadata.target_model
        if not target_model_data or not isinstance(target_model_data, dict):
            return WorkflowResult(
                name="conformance",
                passed=True,
                skipped="No resolved target model configured on the project.",
            )

        errors: list[ValidationError] = TargetModelValidator().validate(target_model_data, project)
        return WorkflowResult(
            name="conformance",
            passed=len(errors) == 0,
            issues=[map_error_to_issue(e) for e in errors if e.code not in ignores],
        )


def normalize_workflow_name(value: str) -> str:
    """Normalize CLI workflow choices, including stable aliases."""
    normalized: str = value.strip().lower()
    aliases: dict[str, str] = {
        "all": "all",
        "structural": "structural",
        "data": "data",
        "conformance": "conformance",
        "target-model-conformance": "conformance",
    }
    if normalized not in aliases:
        valid = ", ".join(sorted(aliases))
        raise argparse.ArgumentTypeError(f"Invalid workflow '{value}'. Choose one of: {valid}")
    return aliases[normalized]


def run_workflows(project: ShapeShiftProject, workflow: str, ignores: set[str]) -> dict[str, WorkflowResult]:
    """Run the selected validation workflow or workflow set."""

    workflows: list[str] = [workflow] if workflow != "all" else list(EXECUTORS.items.keys())
    workflows = ["structural"] + [w for w in workflows if w != "structural"]  # Always run structural first

    results: dict[str, WorkflowResult] = {}

    for wf in workflows:

        if "structural" in results and not results["structural"].passed:
            reason = "Skipped because structural validation reported errors."
            logger.warning(f"Skipping {wf} validation: {reason}")
            results[wf] = WorkflowResult.create_skipped(name=wf, reason=reason)
            continue

        executor_cls: type[WorkflowExecutor] = EXECUTORS.get(wf)
        result: WorkflowResult = executor_cls().execute(project, ignores=ignores)  # type: ignore[call-arg]
        results[wf] = result

    return results


def print_workflow_results(project_file: Path, results: dict[str, WorkflowResult], format: str = "csv") -> None:
    """Print workflow-by-workflow validation results."""

    def csv_header() -> str:
        return "workflow;severity;entity;field;column;code;message"

    def to_csv(issue: CoreIssue) -> str:
        """Return a list of issue attributes suitable for CSV output."""
        return f"{issue.severity};{issue.entity};{issue.field};{issue.column};{issue.code};{issue.message}"

    if format == "csv":
        print(csv_header())
        for result in results.values():
            for issue in result.issues:
                print(f"{result.name};{to_csv(issue)}")
        return

    # print(f"Validation results for {project_file}")

    # for result in results.values():
    #     for result in results.values():
    #         print(f"\n== {WORKFLOW_LABELS[result.name]} ==")
    #         if result.skipped:
    #             print(f"SKIPPED: {result.skipped}")
    #             continue

    #         status = "PASSED" if result.passed else "FAILED"
    #         print(f"Status: {status}")

    #         if not result.issues:
    #             print("No issues found.")
    #             continue

    #         if result.errors:
    #             print("Errors:")
    #             for issue in result.errors:
    #                 print(f"  - {issue}")

    #         if result.warnings:
    #             print("Warnings:")
    #             for issue in result.warnings:
    #                 print(f"  - {issue}")

    #         if result.info:
    #             print("Info:")
    #             for issue in result.info:
    #                 print(f"  - {issue}")
    # print_summary(results)


def print_summary(results: dict[str, WorkflowResult]) -> None:
    """Print a compact final summary."""
    failed: int = sum(1 for result in results.values() if not result.passed)
    skipped: int = sum(1 for result in results.values() if result.skipped)
    print("\nSummary:")
    for result in results.values():
        if result.skipped:
            state: str = f"skipped ({result.skipped})"
        else:
            state = "passed" if result.passed else "failed"
        print(f"  - {result.name}: {state}")

    print(f"\nCompleted {len(results)} workflow(s): {failed} failed, {skipped} skipped.")


@click.command()
@click.argument("project_name")
@click.option(
    "--workflow",
    type=normalize_workflow_name,
    default="all",
    help="Workflow to run: structural, data, conformance, target-model-conformance, or all (default: all)",
)
@click.option("--env-file", type=Path, default=Path(".env"), help="Optional env file for project loading (default: .env)")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose loggingEnable verbose logging")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR)"
)
@click.option("--log-file", type=Path, default=None, help="Optional log file path")
@click.option(
    "--ignore",
    type=str,
    default=None,
    help="Codes to ignore, separated by commas (e.g., 'MISSING_COLUMN,INVALID_FOREIGN_KEY') ",
    show_default=True,
)
def main(project_name: str, workflow: str, env_file: Path, verbose: bool, log_level: str, log_file: Path, ignore: str) -> int:
    """
    Workflows
    ---------
    structural               Run configuration/specification validation.
    data                     Run data-aware validation against normalized output.
    conformance              Run target-model conformance validation.
    all                      Run structural, then data, then conformance.

    Examples
    --------
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml --workflow structural
    uv run python scripts/validate_project.py data/projects/example/shapeshifter.yml --workflow target-model-conformance
    """
    setup_logging(level=log_level.upper() if log_level else None, verbose=verbose, log_file=str(log_file) if log_file else None)

    ignores: set[str] = set(code.strip() for code in ignore.split(",")) if ignore else set()

    project_file = Path(project_name).resolve()
    if not project_file.exists():
        click.echo(f"Project file not found: {project_file}", err=True)
        return 2

    try:
        project: ShapeShiftProject = ShapeShiftProject.from_file(
            filename=str(project_file), env_file=str(env_file), env_prefix="SHAPE_SHIFTER"
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to load project file {}", project_file)
        click.echo(f"Failed to load project file: {exc}", err=True)
        return 1

    results: dict[str, WorkflowResult] = run_workflows(project, workflow, ignores=ignores)
    print_workflow_results(project_file, results)

    return 0 if all(result.passed for result in results.values()) else 1


if __name__ == "__main__":
    # main(["data/projects/arbodat/shapeshifter.yml", "--workflow", "all", "--log-level", "WARNING"])
    main()
