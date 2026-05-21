#!/usr/bin/env python3
"""Run validation workflows for a Shape Shifter project file.

Examples:
    uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml
    uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml --workflow structural
    uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml --workflow conformance
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Sequence

from loguru import logger

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.validation import ValidationError
from backend.app.validators.data_validation_orchestrator import DataValidationOrchestrator, TableStoreDataFetchStrategy
from backend.app.validators.target_model_validator import TargetModelValidator
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications import CompositeProjectSpecification
from src.specifications.base import SpecificationIssue
from src.utility import setup_logging
from src.validators.data_validators import ValidationIssue

WORKFLOW_LABELS: dict[str, str] = {
    "structural": "Structural",
    "data": "Data",
    "conformance": "Target-model conformance",
}


@dataclass
class WorkflowResult:
    """Normalized result for a validation workflow run."""

    name: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    skipped: str | None = None


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


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run validation workflows against a Shape Shifter project file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflows
---------
  structural               Run configuration/specification validation.
  data                     Run data-aware validation against normalized output.
  conformance              Run target-model conformance validation.
  all                      Run structural, then data, then conformance.

Examples
--------
  uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml
  uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml --workflow structural
  uv run python scripts/run_validation_workflows.py data/projects/example/shapeshifter.yml --workflow target-model-conformance
""",
    )
    parser.add_argument("project", type=Path, help="Path to a project shapeshifter.yml file")
    parser.add_argument(
        "--workflow",
        type=normalize_workflow_name,
        default="all",
        help="Workflow to run: structural, data, conformance, target-model-conformance, or all (default: all)",
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Optional env file for project loading (default: .env)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-level", "-l", type=str, default=None, help="Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--log-file", type=Path, help="Optional log file path")
    return parser


def load_project(project_file: Path, env_file: Path) -> ShapeShiftProject:
    """Load a project file into the resolved core project model."""
    return ShapeShiftProject.from_file(
        filename=str(project_file),
        env_file=str(env_file),
        env_prefix="SHAPE_SHIFTER",
    )


def format_specification_issue(issue: SpecificationIssue) -> str:
    """Format a structural validation issue for CLI output."""
    return str(issue)


def format_data_issue(issue: ValidationIssue) -> str:
    """Format a data validation issue for CLI output."""
    location = issue.entity or "project"
    if issue.field:
        location = f"{location}.{issue.field}"
    return f"[{issue.severity.upper()}] {location}: {issue.message} ({issue.code})"


def format_validation_error(error: ValidationError) -> str:
    """Format a backend validation error for CLI output."""
    location: str = error.entity or "project"
    if error.field:
        location = f"{location}.{error.field}"
    return f"[{error.severity.upper()}] {location}: {error.message} ({error.code or 'UNKNOWN'})"


def run_structural_validation(project: ShapeShiftProject) -> WorkflowResult:
    """Run structural/specification validation."""
    specification = CompositeProjectSpecification(project.cfg)
    is_valid: bool = specification.is_satisfied_by()
    return WorkflowResult(
        name="structural",
        passed=is_valid,
        errors=[format_specification_issue(issue) for issue in specification.errors],
        warnings=[format_specification_issue(issue) for issue in specification.warnings],
    )


async def run_data_validation(project: ShapeShiftProject) -> WorkflowResult:
    """Run data validation against the fully normalized in-memory table store."""
    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(normalizer.table_store))
    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project,
        project_name=project.metadata.name or Path(project.filename).stem,
    )

    return WorkflowResult(
        name="data",
        passed=all(issue.severity != "error" for issue in issues),
        errors=[format_data_issue(issue) for issue in issues if issue.severity == "error"],
        warnings=[format_data_issue(issue) for issue in issues if issue.severity == "warning"],
        info=[format_data_issue(issue) for issue in issues if issue.severity == "info"],
    )


def run_conformance_validation(project: ShapeShiftProject) -> WorkflowResult:
    """Run target-model conformance validation if the project defines a target model."""
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
        errors=[format_validation_error(error) for error in errors],
    )


async def execute_async_workflow(
    name: str, runner: Callable[[ShapeShiftProject], Awaitable[WorkflowResult]], project: ShapeShiftProject
) -> WorkflowResult:
    """Run an async workflow and normalize unexpected failures into CLI output."""
    try:
        result: WorkflowResult = await runner(project)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("{} validation workflow failed", name)
        return WorkflowResult(name=name, passed=False, errors=[f"[{name.upper()}] Workflow failed: {exc}"])

    if not isinstance(result, WorkflowResult):
        raise TypeError(f"Workflow '{name}' did not return WorkflowResult")
    return result


def execute_sync_workflow(name: str, runner: Callable[[ShapeShiftProject], WorkflowResult], project: ShapeShiftProject) -> WorkflowResult:
    """Run a sync workflow and normalize unexpected failures into CLI output."""
    try:
        result: WorkflowResult = runner(project)
        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("{} validation workflow failed", name)
        return WorkflowResult(name=name, passed=False, errors=[f"[{name.upper()}] Workflow failed: {exc}"])


async def run_requested_workflows(project: ShapeShiftProject, workflow: str) -> list[WorkflowResult]:
    """Run the selected validation workflow or workflow set."""
    if workflow == "structural":
        return [execute_sync_workflow("structural", run_structural_validation, project)]

    if workflow == "data":
        return [await execute_async_workflow("data", run_data_validation, project)]

    if workflow == "conformance":
        return [execute_sync_workflow("conformance", run_conformance_validation, project)]

    results: list[WorkflowResult] = []
    structural_result: WorkflowResult = execute_sync_workflow("structural", run_structural_validation, project)
    results.append(structural_result)

    if structural_result.passed:
        results.append(await execute_async_workflow("data", run_data_validation, project))
    else:
        results.append(
            WorkflowResult(
                name="data",
                passed=True,
                skipped="Skipped because structural validation reported errors.",
            )
        )

    results.append(execute_sync_workflow("conformance", run_conformance_validation, project))
    return results


def print_workflow_results(project_file: Path, results: list[WorkflowResult]) -> None:
    """Print workflow-by-workflow validation results."""


    for result in results:
        workflow: str = WORKFLOW_LABELS.get(result.name, result.name)
        for error in result.errors:
            logger.error(error)

    print(f"Validation results for {project_file}")

    for result in results:
        print(f"\n== {WORKFLOW_LABELS[result.name]} ==")
        if result.skipped:
            print(f"SKIPPED: {result.skipped}")
            continue

        status = "PASSED" if result.passed else "FAILED"
        print(f"Status: {status}")

        if not result.errors and not result.warnings and not result.info:
            print("No issues found.")
            continue

        if result.errors:
            print("Errors:")
            for issue in result.errors:
                print(f"  - {issue}")

        if result.warnings:
            print("Warnings:")
            for issue in result.warnings:
                print(f"  - {issue}")

        if result.info:
            print("Info:")
            for issue in result.info:
                print(f"  - {issue}")


def print_summary(results: list[WorkflowResult]) -> None:
    """Print a compact final summary."""
    failed: int = sum(1 for result in results if not result.passed)
    skipped: int = sum(1 for result in results if result.skipped)
    print("\nSummary:")
    for result in results:
        if result.skipped:
            state: str = f"skipped ({result.skipped})"
        else:
            state = "passed" if result.passed else "failed"
        print(f"  - {WORKFLOW_LABELS[result.name]}: {state}")

    print(f"\nCompleted {len(results)} workflow(s): {failed} failed, {skipped} skipped.")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args(argv)

    setup_logging(level=args.log_level.upper() if args.log_level else None, verbose=args.verbose, log_file=str(args.log_file) if args.log_file else None)

    project_file = args.project.resolve()
    if not project_file.exists():
        print(f"Project file not found: {project_file}", file=sys.stderr)
        return 2

    try:
        project: ShapeShiftProject = load_project(project_file, args.env_file)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to load project file {}", project_file)
        print(f"Failed to load project file: {exc}", file=sys.stderr)
        return 1

    results: list[WorkflowResult] = asyncio.run(run_requested_workflows(project, args.workflow))
    print_workflow_results(project_file, results)
    print_summary(results)

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    # main(["data/projects/arbodat/shapeshifter.yml", "--workflow", "all", "--log-level", "WARNING"])
    sys.exit(main())
