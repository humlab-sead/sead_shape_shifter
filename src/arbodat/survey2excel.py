#!/usr/bin/env python3
"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx

"""

import asyncio
import os
from pathlib import Path
from typing import Literal

import click

from src.configuration.setup import setup_config_store
from src.arbodat.workflow import workflow


@click.command()
@click.argument("input_csv")  # type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("target")  # type=click.Path(dir_okay=False, writable=True))
@click.option("--sep", "-s", default=";", show_default=True, help='Field separator character. Use "," for comma-separated files.')
@click.option("--config-file", "-c", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to configuration file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--translate", "-t", is_flag=True, help="Enable translation.")
@click.option("--mode", "-m", type=click.Choice(["xlsx", "csv"]), default="xlsx", show_default=True, help="Output file format.")
@click.option("--drop-foreign-keys", "-d", is_flag=True, help="Drop foreign key columns after linking.")
def main(
    input_csv: str,
    target: str,
    sep: str,
    config_file: str,
    verbose: bool,
    translate: bool,
    mode: Literal["xlsx", "csv"],
    drop_foreign_keys: bool,
) -> None:
    """
    Normalize an Arbodat "Data Survey" CSV export into several tables.

    Reads INPUT_CSV and writes normalized data as multiple sheets to TARGET.

    The input CSV should contain one row per Sample × Taxon combination, with
    columns identifying projects, sites, features, samples, and taxa.
    """
    if verbose:
        click.echo(f"Reading Arbodat CSV from: {input_csv}")
        click.echo(f"Using separator: {repr(sep)}")

    if config_file:
        click.echo(f"Using configuration file: {config_file}")

    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__), "config.yml")

    if not config_file or not Path(config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file or 'undefined'}")

    asyncio.run(setup_config_store(config_file))

    workflow(
        input_csv=input_csv,
        target=target,
        sep=sep,
        verbose=verbose,
        translate=translate,
        mode=mode,
        drop_foreign_keys=drop_foreign_keys,
    )

    click.secho(f"✓ Successfully written normalized workbook to {target}", fg="green")


if __name__ == "__main__":
    main()

    # PYTHONPATH=. python src/arbodat/survey2excel.py  --sep ";" --translate --config-file src/arbodat/config.yml src/arbodat/arbodat_mal_elena_input.csv output.xlsx

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
