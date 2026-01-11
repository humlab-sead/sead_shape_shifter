#!/usr/bin/env python3
"""CLI tool for data ingestion using registered ingesters.

This script provides command-line access to Shape Shifter's ingester system,
allowing validation and ingestion of data from external sources.

Examples:
    # List available ingesters
    python -m backend.app.scripts.ingest list

    # Validate a SEAD Excel file
    python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx \\
        --config config.json

    # Ingest SEAD data
    python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \\
        --submission-name "dendro_2026_01" \\
        --data-types "dendro" \\
        --database-host localhost \\
        --database-port 5432 \\
        --database-name sead_staging \\
        --database-user sead_user \\
        --register \\
        --explode

    # Ingest with config file
    python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \\
        --config ingest_config.json
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
from loguru import logger

from backend.app.ingesters.protocol import IngesterConfig
from backend.app.models.ingester import IngestRequest, ValidateRequest
from backend.app.services.ingester_service import IngesterService


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<level>{level: <8}</level> | <level>{message}</level>")


def load_config_file(config_path: str) -> dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        sys.exit(1)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Shape Shifter Data Ingestion CLI.
    
    Manage data ingestion from external sources using registered ingesters.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_logging(verbose)


@cli.command()
def list_ingesters() -> None:
    """List all available data ingesters."""
    logger.info("Fetching available ingesters...")
    
    ingesters = IngesterService.list_ingesters()
    
    if not ingesters:
        logger.warning("No ingesters available")
        return
    
    click.echo("\nAvailable Ingesters:")
    click.echo("=" * 80)
    
    for ingester in ingesters:
        click.echo(f"\n  Key:         {ingester.key}")
        click.echo(f"  Name:        {ingester.name}")
        click.echo(f"  Description: {ingester.description}")
        click.echo(f"  Version:     {ingester.version}")
        click.echo(f"  Formats:     {', '.join(ingester.supported_formats)}")
    
    click.echo("\n" + "=" * 80)
    logger.info(f"Found {len(ingesters)} ingester(s)")


@cli.command()
@click.argument('ingester_key')
@click.argument('source', type=click.Path(exists=True))
@click.option('--config', '-c', 'config_file', type=click.Path(exists=True), help='JSON config file')
@click.option('--ignore-columns', multiple=True, help='Column patterns to ignore (can specify multiple times)')
@click.pass_context
def validate(
    ctx: click.Context,
    ingester_key: str,
    source: str,
    config_file: str | None,
    ignore_columns: tuple[str, ...]
) -> None:
    """Validate data file before ingestion.
    
    INGESTER_KEY: Key of the ingester to use (e.g., 'sead')
    SOURCE: Path to the data file to validate
    """
    logger.info(f"Validating {source} using {ingester_key} ingester...")
    
    # Build config
    config: dict[str, Any] = {}
    if config_file:
        config = load_config_file(config_file)
    
    if ignore_columns:
        config['ignore_columns'] = list(ignore_columns)
    
    # Create request
    request = ValidateRequest(source=str(source), config=config)
    
    # Run validation
    async def run_validation():
        return await IngesterService.validate(ingester_key, request)
    
    try:
        result = asyncio.run(run_validation())
    except ValueError as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during validation: {e}")
        sys.exit(1)
    
    # Display results
    click.echo("\nValidation Results:")
    click.echo("=" * 80)
    
    if result.is_valid:
        click.echo(click.style("✓ VALIDATION PASSED", fg='green', bold=True))
    else:
        click.echo(click.style("✗ VALIDATION FAILED", fg='red', bold=True))
    
    if result.errors:
        click.echo(f"\n{click.style('Errors:', fg='red', bold=True)}")
        for error in result.errors:
            click.echo(f"  • {error}")
    
    if result.warnings:
        click.echo(f"\n{click.style('Warnings:', fg='yellow', bold=True)}")
        for warning in result.warnings:
            click.echo(f"  • {warning}")
    
    click.echo("\n" + "=" * 80)
    
    sys.exit(0 if result.is_valid else 1)


@cli.command()
@click.argument('ingester_key')
@click.argument('source', type=click.Path(exists=True))
@click.option('--config', '-c', 'config_file', type=click.Path(exists=True), help='JSON config file')
@click.option('--submission-name', '-n', required=True, help='Name for this submission')
@click.option('--data-types', '-t', required=True, help='Type of data (e.g., dendro, ceramics)')
@click.option('--output-folder', '-o', default='output', help='Output folder for generated files')
@click.option('--database-host', help='Database host')
@click.option('--database-port', type=int, default=5432, help='Database port')
@click.option('--database-name', help='Database name')
@click.option('--database-user', help='Database user')
@click.option('--ignore-columns', multiple=True, help='Column patterns to ignore')
@click.option('--register/--no-register', default=False, help='Register submission in database')
@click.option('--explode/--no-explode', default=False, help='Explode submission into public tables')
@click.pass_context
def ingest(
    ctx: click.Context,
    ingester_key: str,
    source: str,
    config_file: str | None,
    submission_name: str,
    data_types: str,
    output_folder: str,
    database_host: str | None,
    database_port: int,
    database_name: str | None,
    database_user: str | None,
    ignore_columns: tuple[str, ...],
    register: bool,
    explode: bool
) -> None:
    """Ingest data into the system.
    
    INGESTER_KEY: Key of the ingester to use (e.g., 'sead')
    SOURCE: Path to the data file to ingest
    """
    logger.info(f"Ingesting {source} using {ingester_key} ingester...")
    
    # Build config
    config: dict[str, Any] = {}
    if config_file:
        config = load_config_file(config_file)
    
    # Override with CLI options
    if database_host or database_name or database_user:
        config['database'] = config.get('database', {})
        if database_host:
            config['database']['host'] = database_host
        if database_port:
            config['database']['port'] = database_port
        if database_name:
            config['database']['dbname'] = database_name
        if database_user:
            config['database']['user'] = database_user
    
    if ignore_columns:
        config['ignore_columns'] = list(ignore_columns)
    
    # Create request
    request = IngestRequest(
        source=str(source),
        config=config,
        submission_name=submission_name,
        data_types=data_types,
        output_folder=output_folder,
        do_register=register,
        explode=explode
    )
    
    # Run ingestion
    async def run_ingestion():
        return await IngesterService.ingest(ingester_key, request)
    
    try:
        result = asyncio.run(run_ingestion())
    except ValueError as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during ingestion: {e}")
        sys.exit(1)
    
    # Display results
    click.echo("\nIngestion Results:")
    click.echo("=" * 80)
    
    if result.success:
        click.echo(click.style("✓ INGESTION SUCCESSFUL", fg='green', bold=True))
        click.echo(f"\n  Message:           {result.message}")
        click.echo(f"  Records Processed: {result.records_processed}")
        if result.submission_id:
            click.echo(f"  Submission ID:     {result.submission_id}")
        if result.output_path:
            click.echo(f"  Output Path:       {result.output_path}")
    else:
        click.echo(click.style("✗ INGESTION FAILED", fg='red', bold=True))
        click.echo(f"\n  Message: {result.message}")
    
    click.echo("\n" + "=" * 80)
    
    sys.exit(0 if result.success else 1)


if __name__ == '__main__':
    cli(obj={})
