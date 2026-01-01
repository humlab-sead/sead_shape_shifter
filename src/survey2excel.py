#!/usr/bin/env python3
"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

Usage:
    python shaper_shifter.py input.csv output.xlsx

"""

import asyncio
from pathlib import Path

import click

from src.utility import setup_logging
from src.workflow import workflow

# pylint: disable=no-value-for-parameter



@click.command()
@click.argument("target")
@click.option("--default-entity", "-de", type=str, help="Default entity name to use as source when none is specified.", default=None)
@click.option("--project", "-p", "project_filename",  type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to project file.")
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
    if project_filename or not Path(project_filename or "").exists():
        raise FileNotFoundError(f"Project file not found: {project_filename or 'undefined'}")

    click.echo(f"Using project file: {project_filename}")
    setup_logging(verbose=verbose, log_file=log_file)

    asyncio.run(
        workflow(
            project=project_filename,
            default_entity=default_entity,
            target=target,
            translate=translate,
            mode=mode,
            drop_foreign_keys=drop_foreign_keys,
            validate_then_exit=validate_then_exit,
            env_file=env_file,
        )
    )

    click.secho(f"✓ Successfully written normalized workbook to {target}", fg="green")


if __name__ == "__main__":
    main()

    # PYTHONPATH=. python src/arbodat/survey2excel.py  --sep ";" --translate --config-file
    # src/arbodat/config.yml src/arbodat/arbodat_mal_elena_input.csv output.xlsx

    # from click.testing import CliRunner

    # runner = CliRunner()
    # result = runner.invoke(
    #     main,
    #     [
    #         "--sep",
    #         ";",
    #         "--translate",
    #         "--config-file",
    #         "src/arbodat/config.yml",
    #         "src/arbodat/arbodat_mal_elena_input.csv",
    #         "output.xlsx",
    #     ],
    # )

    # print(result.output)
