#!/usr/bin/env python3
"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

Usage:
    python shaper_shifter.py input.csv output.xlsx

"""

import asyncio
import json
import sys
from pathlib import Path

import click

from src.output_expectations import OutputExpectationEvaluation
from src.utility import setup_logging
from src.workflow import validate_project, workflow

# pylint: disable=no-value-for-parameter


@click.command()
@click.argument("target")
@click.option("--default-entity", "-de", type=str, help="Default entity name to use as source when none is specified.", default=None)
@click.option(
    "--project", "-p", "project_filename", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to project file."
)
@click.option("--env-file", "-e", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to environment variables file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.", default=False)
@click.option("--translate", "-t", is_flag=True, help="Enable translation.", default=False)
@click.option("--mode", "-m", type=click.Choice(["xlsx", "csv", "db"]), default="xlsx", show_default=True, help="Output file format.")
@click.option("--drop-foreign-keys", "-d", is_flag=True, help="Drop foreign key columns after linking.", default=False)
@click.option("--log-file", "-l", type=click.Path(), help="Path to log file (optional).")
# @click.option("--regression-file", "-r", type=click.Path(), help="Path to regression file (optional).")
@click.option("--validate-then-exit", is_flag=True, help="Validate configuration and exit if invalid.", default=False)
def main(
    target: str,
    default_entity: str,
    project_filename: str,
    env_file: str,
    verbose: bool,
    translate: bool,
    mode: str,
    drop_foreign_keys: bool,
    log_file: str | None,
    # regression_file: str | None,
    validate_then_exit: bool = False,
) -> None:
    """
    Normalize data from various data sources into structured tables.
    Write them as CSVs or sheets in a single Excel file at TARGET location."""
    if not project_filename or not Path(project_filename).exists():
        raise FileNotFoundError(f"Project file not found: {project_filename or 'undefined'}")

    click.echo(f"Using project file: {project_filename}")
    setup_logging(verbose=verbose, log_file=log_file)

    if validate_then_exit:
        click.echo("Validating project configuration and exiting if invalid.")
        is_valid: bool = validate_project(project_filename)
        sys.exit(0 if is_valid else 1)

    evaluation = asyncio.run(
        workflow(
            project=project_filename,
            default_entity=default_entity,
            target=target,
            translate=translate,
            target_type=mode,
            drop_foreign_keys=drop_foreign_keys,
            env_file=env_file,
        )
    )

    if evaluation is not None:
        _report_output_expectation_results(evaluation)
        if not evaluation.passed:
            raise click.ClickException("Output expectation checks failed; no output was written.")

    click.secho(f"✓ Successfully written normalized workbook to {target}", fg="green")


def _report_output_expectation_results(evaluation: OutputExpectationEvaluation) -> None:
    """Print every output expectation result in the order it was evaluated."""
    click.echo("\nOutput expectation results:")
    for result in evaluation.results:
        label = f"{result.name} ({result.entity}, {result.metric}"
        if result.metric == "grouped_row_count":
            label += f", group={json.dumps(result.group_value)}"
        label += ")"
        click.echo(f"  [{result.status.upper()}] {label}")
        click.echo(f"    measured: {result.measured_value if result.measured_value is not None else 'not available'}")
        click.echo(f"    expected: {json.dumps(result.expected_limit, sort_keys=True)}")
        if result.failure_reason:
            click.echo(f"    reason: {result.failure_reason}")


if __name__ == "__main__":
    main()
