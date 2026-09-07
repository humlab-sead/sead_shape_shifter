"""Command-line administration for the authorization database."""

from datetime import UTC, datetime
from pathlib import Path

import click

from backend.app.authorization.models import Grant, GrantSubjectType, ResourceType
from backend.app.authorization.operations import (
    apply_manifest,
    backup_database,
    initialize_database,
    inspect_manifest,
    integrity_check,
    reconcile_manifest,
    restore_database,
)
from backend.app.authorization.repository import SQLiteAuthorizationRepository
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


@cli.command("grant")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--resource-type", required=True, type=click.Choice([resource_type.value for resource_type in ResourceType]))
@click.option("--locator", required=True)
@click.option("--subject-type", required=True, type=click.Choice([subject_type.value for subject_type in GrantSubjectType]))
@click.option("--subject-id", required=True)
@click.option("--role", required=True)
@click.option("--actor", required=True)
@click.option("--dry-run", is_flag=True)
def grant(
    database: Path | None,
    resource_type: str,
    locator: str,
    subject_type: str,
    subject_id: str,
    role: str,
    actor: str,
    dry_run: bool,
) -> None:
    """Add a typed resource grant with an auditable actor."""
    path = database or settings.AUTHORIZATION_DATABASE_PATH
    repository = SQLiteAuthorizationRepository(path)
    try:
        resource = repository.get_resource_by_locator(ResourceType(resource_type), locator)
        if resource is None:
            raise click.ClickException("Active authorization resource not found")
        typed_subject = GrantSubjectType(subject_type)
        if repository.grant_exists(typed_subject, subject_id, resource.resource_id, role):
            click.echo("Grant already exists")
            return
        if dry_run:
            click.echo(f"Dry run: would grant {role} to {subject_type}:{subject_id} on {resource_type}:{locator}")
            return
        repository.add_grant(Grant(subject_id, resource.resource_id, role, datetime.now(UTC), actor, typed_subject))
        click.echo(f"Granted {role} to {subject_type}:{subject_id} on {resource_type}:{locator}")
    finally:
        repository.close()


@cli.command("revoke")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--resource-type", required=True, type=click.Choice([resource_type.value for resource_type in ResourceType]))
@click.option("--locator", required=True)
@click.option("--subject-type", required=True, type=click.Choice([subject_type.value for subject_type in GrantSubjectType]))
@click.option("--subject-id", required=True)
@click.option("--role", required=True)
@click.option("--actor", required=True)
@click.option("--dry-run", is_flag=True)
def revoke(
    database: Path | None,
    resource_type: str,
    locator: str,
    subject_type: str,
    subject_id: str,
    role: str,
    actor: str,
    dry_run: bool,
) -> None:
    """Revoke a typed resource grant with final-owner protection."""
    path = database or settings.AUTHORIZATION_DATABASE_PATH
    repository = SQLiteAuthorizationRepository(path)
    try:
        resource = repository.get_resource_by_locator(ResourceType(resource_type), locator)
        if resource is None:
            raise click.ClickException("Active authorization resource not found")
        typed_subject = GrantSubjectType(subject_type)
        if not repository.grant_exists(typed_subject, subject_id, resource.resource_id, role):
            raise click.ClickException("Grant does not exist")
        if dry_run:
            click.echo(f"Dry run: would revoke {role} from {subject_type}:{subject_id} on {resource_type}:{locator}")
            return
        repository.remove_grant(subject_id, resource.resource_id, role, actor, typed_subject)
        click.echo(f"Revoked {role} from {subject_type}:{subject_id} on {resource_type}:{locator}")
    finally:
        repository.close()


@cli.command("list-grants")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
def list_grants(database: Path | None) -> None:
    """List typed resource grants for operator review."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        for grant_record in repository.list_all_grants():
            click.echo(f"{grant_record.subject_type.value}:{grant_record.subject_id} {grant_record.role} {grant_record.resource_id}")
    finally:
        repository.close()


if __name__ == "__main__":
    cli()
