#!/usr/bin/env python3
"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

Usage:
    python shaper_shifter.py input.csv output.xlsx

"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Literal

import click
from loguru import logger

from src.extract import extract_translation_map
from src.model import ShapeShiftConfig
from src.normalizer import ShapeShifter
from src.specifications import CompositeConfigSpecification
from src.utility import load_shape_file, setup_logging

# pylint: disable=no-value-for-parameter


def resolve_config(config: ShapeShiftConfig | str) -> ShapeShiftConfig:
    if isinstance(config, str):
        return ShapeShiftConfig.from_file(config)
    return config


async def workflow(
    config: ShapeShiftConfig,
    target: str,
    translate: bool,
    mode: str,
    drop_foreign_keys: bool,
    validate_then_exit: bool = False,
    default_entity: str | None = None,
) -> None:

    shapeshifter: ShapeShifter = ShapeShifter(config=config, default_entity=default_entity)

    if validate_configuration(config) and validate_then_exit:
        return

    await shapeshifter.normalize()

    if drop_foreign_keys:
        shapeshifter.drop_foreign_key_columns()

    if translate:
        translations_map: dict[str, str] = extract_translation_map(fields_metadata=config.options.get("translation") or [])
        shapeshifter.translate(translations_map=translations_map)

    shapeshifter.add_system_id_columns()
    shapeshifter.move_keys_to_front()
    shapeshifter.map_to_remote(config.mappings)
    shapeshifter.store(target=target, mode=mode)
    shapeshifter.log_shapes(target=target)

    # if verbose:
    #     click.echo("\nTable Summary:")
    #     for name, table in shapeshifter.table_store.items():
    #         click.echo(f"  - {name}: {len(table)} rows")


def validate_configuration(config: ShapeShiftConfig) -> bool:
    specification = CompositeConfigSpecification()
    errors = specification.is_satisfied_by(config.cfg)
    if errors:
        for error in specification.errors:
            logger.error(f"Configuration error: {error}")
        click.echo("Configuration validation failed with errors.", err=True)
        sys.exit(1)
    logger.info("Configuration validation passed successfully.")
    return True


@click.command()
@click.argument("target")
@click.option("--default-entity", "-de", type=str, help="Default entity name to use as source when none is specified.", default=None)
@click.option("--config-file", "-c", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to configuration file.")
@click.option("--env-file", "-e", type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to environment variables file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.", default=False)
@click.option("--translate", "-t", is_flag=True, help="Enable translation.", default=False)
@click.option("--mode", "-m", type=click.Choice(["xlsx", "csv", "db"]), default="xlsx", show_default=True, help="Output file format.")
@click.option("--drop-foreign-keys", "-d", is_flag=True, help="Drop foreign key columns after linking.", default=False)
@click.option("--log-file", "-l", type=click.Path(), help="Path to log file (optional).")
@click.option("--regression-file", "-r", type=click.Path(), help="Path to regression file (optional).")
@click.option("--validate-then-exit", is_flag=True, help="Validate configuration and exit if invalid.", default=False)
def main(
    target: str,
    default_entity: str,
    config_file: str,
    env_file: str,
    verbose: bool,
    translate: bool,
    mode: str,
    drop_foreign_keys: bool,
    log_file: str | None,
    regression_file: str | None,
    validate_then_exit: bool = False,
) -> None:
    """
    Normalize data from various data sources into structured tables.
    Write them as CSVs or sheets in a single Excel file at TARGET location."""
    if config_file:
        click.echo(f"Using configuration file: {config_file}")

    if not config_file:
        config_file = os.path.join(os.path.dirname(__file__), "config.yml")

    if not config_file or not Path(config_file).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file or 'undefined'}")

    config: ShapeShiftConfig = ShapeShiftConfig.from_file(config_file, env_file=env_file, env_prefix="SEAD_NORMALIZER")

    # Configure logging AFTER setup_config_store to override its logging configuration
    setup_logging(verbose=verbose, log_file=log_file)

    asyncio.run(
        workflow(
            config=config,
            default_entity=default_entity,
            target=target,
            translate=translate,
            mode=mode,
            drop_foreign_keys=drop_foreign_keys,
            validate_then_exit=validate_then_exit,
        )
    )

    click.secho(f"✓ Successfully written normalized workbook to {target}", fg="green")

    validate_entity_shapes(target, mode, regression_file)


def validate_entity_shapes(target: str, mode: str, regression_file: str | None):
    if mode != "csv" or not regression_file:
        return

    truth_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=regression_file)
    new_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=os.path.join(target, "table_shapes.tsv"))

    entities_with_different_shapes = [
        (entity, truth_shapes.get(entity), new_shapes.get(entity))
        for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
        if truth_shapes.get(entity) != new_shapes.get(entity)
    ]
    if len(entities_with_different_shapes) > 0:
        click.secho("✗ Regression check failed: Entities with different shapes:", fg="red")

        print("\n".join(f" {z[0]:>30}: expected {str(z[1]):<15} found {str(z[2]):<20}" for z in entities_with_different_shapes))


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
