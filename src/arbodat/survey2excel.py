#!/usr/bin/env python3
"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx

"""

import asyncio
import os
import sys
from pathlib import Path
from time import time
from typing import Literal

import click
from loguru import logger

from src.arbodat.normalizer import ArbodatSurveyNormalizer
from src.arbodat.utility import extract_translation_map
from src.configuration.resolve import ConfigValue
from src.configuration.setup import setup_config_store


async def workflow(
    input_csv: str,
    target: str,
    sep: str,
    verbose: bool,
    translate: bool,
    mode: Literal["xlsx", "csv", "db"],
    drop_foreign_keys: bool,
) -> None:

    normalizer: ArbodatSurveyNormalizer = ArbodatSurveyNormalizer.load(path=input_csv, sep=sep)

    if verbose:
        click.echo(f"Loaded {len(normalizer.survey)} rows with {len(normalizer.survey.columns)} columns")
        click.echo("Building normalized tables...")

    await normalizer.normalize()

    if drop_foreign_keys:
        normalizer.drop_foreign_key_columns()

    if translate:
        fields_metadata: list[dict[str, str]] = ConfigValue[list[dict[str, str]]]("translation").resolve() or []
        translations_map: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)
        normalizer.translate(translations_map=translations_map)

    normalizer.add_system_id_columns()
    normalizer.move_keys_to_front()
    normalizer.store(target=target, mode=mode)

    if verbose:
        click.echo("\nTable Summary:")
        for name, table in normalizer.data.items():
            click.echo(f"  - {name}: {len(table)} rows")


# Global dictionary to track duplicate log messages
_last_seen_messages: dict[str, float] = {}


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure loguru logging with appropriate handlers and filters.

    Args:
        verbose: If True, set log level to DEBUG and show all messages.
                If False, set to INFO and filter duplicate messages.
        log_file: Optional path to log file. If provided, logs are written to file.
    """
    global _last_seen_messages

    level = "DEBUG" if verbose else "INFO"

    logger.remove()

    # Define filter for duplicate messages (only in non-verbose mode)
    def filter_once_per_message(record) -> bool:
        """Filter to show each unique message only once per second."""
        if verbose:
            return True

        msg = record["message"]
        now = time()
        if msg not in _last_seen_messages or now - _last_seen_messages[msg] > 1.0:
            _last_seen_messages[msg] = now
            return True
        return False

    # Format string for logs
    log_format = (
        (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        if verbose
        else "<level>{message}</level>"
    )

    # Add console handler
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        filter=filter_once_per_message,
        colorize=True,
    )

    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            format=log_format,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )

    if verbose:
        logger.debug("Verbose logging enabled")


@click.command()
@click.argument("input_csv")  # type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("target")  # type=click.Path(dir_okay=False, writable=True))
@click.option("--sep", "-s", show_default=True, help='Field separator character. Use "," for comma-separated files.', default=";")
@click.option("--config-file", "-c", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to configuration file.")
@click.option("--env-file", "-e", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to environment variables file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.", default=False)
@click.option("--translate", "-t", is_flag=True, help="Enable translation.", default=False)
@click.option("--mode", "-m", type=click.Choice(["xlsx", "csv", "db"]), default="xlsx", show_default=True, help="Output file format.")
@click.option("--drop-foreign-keys", "-d", is_flag=True, help="Drop foreign key columns after linking.", default=False)
@click.option("--log-file", "-l", type=click.Path(), help="Path to log file (optional).")
async def main(
    input_csv: str,
    target: str,
    sep: str,
    config_file: str,
    env_file: str,
    verbose: bool,
    translate: bool,
    mode: Literal["xlsx", "csv", "db"],
    drop_foreign_keys: bool,
    log_file: str | None,
) -> None:
    """
    Normalize an Arbodat "Data Survey" CSV export into several tables.

    Reads INPUT_CSV and writes normalized data as multiple sheets to TARGET.

    The input CSV should contain one row per Sample × Taxon combination, with
    columns identifying projects, sites, features, samples, and taxa.
    """
    setup_logging(verbose=verbose, log_file=log_file)

    if verbose:
        logger.info(f"Reading Arbodat CSV from: {input_csv}")
        logger.info(f"Using separator: {repr(sep)}")

    if config_file:
        logger.info(f"Using configuration file: {config_file}")

    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__), "config.yml")

    if not config_file or not Path(config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file or 'undefined'}")

    asyncio.run(setup_config_store(
        config_file,
        env_prefix="SEAD_NORMALIZER",
        env_filename=env_file or os.path.join(os.path.dirname(__file__), "input", ".env"),
        db_opts_path="",
    ))

    await workflow(
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
