"""Command-line administration for the authorization database."""

from pathlib import Path

import click

from backend.app.authorization.operations import (
    apply_manifest,
    backup_database,
    initialize_database,
    inspect_manifest,
    integrity_check,
    reconcile_manifest,
    restore_database,
)
from backend.app.core.config import settings


@click.group()
def cli() -> None:
    """Manage Shape Shifter authorization storage."""


@cli.command("migrate")
@click.option("--database", type=click.Path(path_type=Path), default=None)
@click.option("--manifest", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--dry-run", is_flag=True)
def migrate(database: Path | None, manifest: Path | None, dry_run: bool) -> None:
    """Initialize the schema and optionally inspect a migration manifest."""
    path = database or settings.AUTHORIZATION_DATABASE_PATH
    if manifest:
        summary = inspect_manifest(manifest)
        click.echo(f"Manifest: {summary['resources']} resources, {summary['administrators']} administrators")
    if dry_run:
        click.echo("Dry run: no database changes made")
        return
    if manifest:
        applied = apply_manifest(manifest, path)
        click.echo(f"Applied: {applied['resources']} resources, {applied['administrators']} administrators, {applied['grants']} grants")
    else:
        initialize_database(path)
    click.echo(f"Authorization database ready: {path}")


@cli.command("integrity-check")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
def check_integrity(database: Path | None) -> None:
    """Check SQLite integrity and exit non-zero when it fails."""
    path = database or settings.AUTHORIZATION_DATABASE_PATH
    if not integrity_check(path):
        raise click.ClickException("Authorization database failed integrity check")
    click.echo("Authorization database integrity check passed")


@cli.command("backup")
@click.argument("destination", type=click.Path(path_type=Path))
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
def backup(destination: Path, database: Path | None) -> None:
    """Create a consistent backup of the authorization database."""
    backup_database(database or settings.AUTHORIZATION_DATABASE_PATH, destination)
    click.echo(f"Authorization database backup written: {destination}")


@cli.command("restore")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("--database", type=click.Path(path_type=Path), default=None)
def restore(source: Path, database: Path | None) -> None:
    """Restore an integrity-checked authorization database backup."""
    restore_database(source, database or settings.AUTHORIZATION_DATABASE_PATH)
    click.echo(f"Authorization database restored: {database or settings.AUTHORIZATION_DATABASE_PATH}")


@cli.command("reconcile")
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
def reconcile(manifest: Path, database: Path | None) -> None:
    """Report reviewed manifest records missing from authorization storage."""
    result = reconcile_manifest(manifest, database or settings.AUTHORIZATION_DATABASE_PATH)
    summary = (
        "Missing: "
        f"{result['missing_resources']} resources, "
        f"{result['missing_administrators']} administrators, "
        f"{result['missing_grants']} grants"
    )
    click.echo(summary)
    if any(result.values()):
        raise click.ClickException(f"{summary}\nAuthorization resources do not match the reviewed manifest")


if __name__ == "__main__":
    cli()
