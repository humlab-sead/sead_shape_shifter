"""Command-line administration for the authorization database."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click

from backend.app.authorization.membership import HttpGroupMembershipResolver, MembershipLookupStatus
from backend.app.authorization.models import ApplicationRole, Grant, GrantSubjectType, ResourceType
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
        summary = inspect_manifest(manifest, allow_authenticated_everyone=settings.AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE)
        click.echo(f"Manifest: {summary['resources']} resources, {summary['administrators']} administrators")
    if dry_run:
        click.echo("Dry run: no database changes made")
        return
    if manifest:
        applied = apply_manifest(manifest, path, allow_authenticated_everyone=settings.AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE)
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
    result = reconcile_manifest(
        manifest,
        database or settings.AUTHORIZATION_DATABASE_PATH,
        allow_authenticated_everyone=settings.AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE,
    )
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
        if typed_subject == GrantSubjectType.EVERYONE and not settings.AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE:
            raise click.ClickException("Authenticated everyone grants are disabled by deployment configuration")
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
@click.option("--yes", is_flag=True, help="Confirm the destructive operation.")
@click.option("--non-interactive", is_flag=True, help="Skip confirmation for controlled automation.")
def revoke(
    database: Path | None,
    resource_type: str,
    locator: str,
    subject_type: str,
    subject_id: str,
    role: str,
    actor: str,
    dry_run: bool,
    yes: bool,
    non_interactive: bool,
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
        _confirm_destructive(
            f"Revoke {role} from {subject_type}:{subject_id} on {resource_type}:{locator}?",
            yes,
            non_interactive,
        )
        try:
            repository.remove_grant(subject_id, resource.resource_id, role, actor, typed_subject)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Revoked {role} from {subject_type}:{subject_id} on {resource_type}:{locator}")
    finally:
        repository.close()


@cli.command("list-grants")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--effective", is_flag=True, help="Expand group grants through the trusted membership provider.")
@click.option("--membership-url", default=None, help="URL template containing {group_id} for trusted membership lookup.")
@click.option("--membership-provider", default=None, help="Name of the trusted membership provider.")
@click.option("--actor", default=None, help="Principal performing an effective membership review.")
@click.option("--strict", is_flag=True, help="Exit with an error when a group membership lookup is unavailable.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def list_grants(
    database: Path | None,
    effective: bool,
    membership_url: str | None,
    membership_provider: str | None,
    actor: str | None,
    strict: bool,
    as_json: bool,
) -> None:
    """List typed resource grants for operator review."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        grants = repository.list_all_grants()
        group_ids = {grant.subject_id for grant in grants if grant.subject_type == GrantSubjectType.GROUP}
        resolver = None
        snapshots = {}
        if effective and group_ids:
            if not actor:
                raise click.ClickException("Effective group review requires --actor for audit logging")
            lookup_url = membership_url or settings.AUTHORIZATION_MEMBERSHIP_LOOKUP_URL
            if not lookup_url:
                raise click.ClickException("Effective group review requires AUTHORIZATION_MEMBERSHIP_LOOKUP_URL or --membership-url")
            try:
                resolver = HttpGroupMembershipResolver(
                    lookup_url,
                    membership_provider or settings.AUTHORIZATION_MEMBERSHIP_PROVIDER,
                    settings.AUTHORIZATION_MEMBERSHIP_LOOKUP_TIMEOUT_SECONDS,
                )
            except ValueError as error:
                raise click.ClickException(str(error)) from error
            snapshots = {group_id: resolver.resolve_members(group_id) for group_id in group_ids}
            for snapshot in snapshots.values():
                repository.record_membership_lookup(actor, snapshot)

        records = []
        for grant_record in grants:
            record = {
                "subject_type": grant_record.subject_type.value,
                "subject_id": grant_record.subject_id,
                "role": grant_record.role,
                "resource_id": str(grant_record.resource_id),
            }
            snapshot = snapshots.get(grant_record.subject_id)
            if grant_record.subject_type == GrantSubjectType.GROUP and effective and snapshot:
                record["membership"] = {
                    "provider": snapshot.provider,
                    "status": snapshot.status.value,
                    "principal_ids": sorted(snapshot.principal_ids),
                    "fetched_at": snapshot.fetched_at.isoformat(),
                    "error": snapshot.error,
                }
            records.append(record)

        if as_json:
            click.echo(json.dumps(records, indent=2, sort_keys=True))
        else:
            for record in records:
                click.echo(f"{record['subject_type']}:{record['subject_id']} {record['role']} {record['resource_id']}")
                membership = record.get("membership")
                if membership:
                    members = ", ".join(membership["principal_ids"]) or "none"
                    click.echo(f"  effective principals: {members}")
                    click.echo(f"  membership: {membership['status']} via {membership['provider']} at {membership['fetched_at']}")
                    if membership["error"]:
                        click.echo(f"  lookup error: {membership['error']}")

        if strict and any(snapshot.status != MembershipLookupStatus.RESOLVED for snapshot in snapshots.values()):
            raise click.ClickException("One or more group membership lookups did not resolve")
    finally:
        repository.close()


@cli.command("list-resources")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def list_resources(database: Path | None, as_json: bool) -> None:
    """List all authorization resources and lifecycle generations."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        resources = repository.list_resources()
        records = [
            {
                "resource_id": str(resource.resource_id),
                "resource_type": resource.resource_type.value,
                "locator": resource.locator,
                "lifecycle_state": resource.lifecycle_state,
                "parent_resource_id": str(resource.parent_resource_id) if resource.parent_resource_id else None,
            }
            for resource in resources
        ]
        if as_json:
            click.echo(json.dumps(records, indent=2, sort_keys=True))
        else:
            for record in records:
                click.echo(f"{record['resource_type']}:{record['locator']} " f"{record['lifecycle_state']} {record['resource_id']}")
    finally:
        repository.close()


@cli.command("list-application-roles")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def list_application_roles(database: Path | None, as_json: bool) -> None:
    """List deployment-wide application role assignments."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        assignments = repository.list_all_application_roles()
        records = [
            {
                "principal_id": assignment.principal_id,
                "role": assignment.role.value,
                "created_at": assignment.created_at.isoformat(),
                "created_by": assignment.created_by,
            }
            for assignment in assignments
        ]
        if as_json:
            click.echo(json.dumps(records, indent=2, sort_keys=True))
        else:
            for record in records:
                click.echo(f"{record['principal_id']} {record['role']} {record['created_at']} by {record['created_by']}")
    finally:
        repository.close()


@cli.command("list-audit-events")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def list_audit_events(database: Path | None, as_json: bool) -> None:
    """List authorization audit events in occurrence order."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        events = repository.list_audit_events()
        records = [
            {
                "event_id": str(event.event_id),
                "occurred_at": event.occurred_at.isoformat(),
                "actor_principal_id": event.actor_principal_id,
                "event_type": event.event_type,
                "resource_id": str(event.resource_id) if event.resource_id else None,
                "action": event.action,
                "outcome": event.outcome,
                "correlation_id": event.correlation_id,
                "subject_type": event.subject_type.value if event.subject_type else None,
                "subject_id": event.subject_id,
                "provider": event.provider,
                "details": event.details,
            }
            for event in events
        ]
        if as_json:
            click.echo(json.dumps(records, indent=2, sort_keys=True))
        else:
            for record in records:
                click.echo(f"{record['occurred_at']} {record['event_type']} " f"{record['outcome']} actor={record['actor_principal_id']}")
    finally:
        repository.close()


@cli.command("grant-application-role")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--principal-id", required=True)
@click.option("--role", required=True, type=click.Choice([role.value for role in ApplicationRole]))
@click.option("--actor", required=True)
@click.option("--dry-run", is_flag=True)
def grant_application_role(database: Path | None, principal_id: str, role: str, actor: str, dry_run: bool) -> None:
    """Assign a deployment-wide application role."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        if role in repository.list_application_roles(principal_id):
            click.echo("Application role already exists")
            return
        if dry_run:
            click.echo(f"Dry run: would grant {role} to {principal_id}")
            return
        repository.add_application_role(principal_id, role, actor)
        click.echo(f"Granted application role {role} to {principal_id}")
    finally:
        repository.close()


@cli.command("revoke-application-role")
@click.option("--database", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--principal-id", required=True)
@click.option("--role", required=True, type=click.Choice([role.value for role in ApplicationRole]))
@click.option("--actor", required=True)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", is_flag=True, help="Confirm the destructive operation.")
@click.option("--non-interactive", is_flag=True, help="Skip confirmation for controlled automation.")
def revoke_application_role(
    database: Path | None,
    principal_id: str,
    role: str,
    actor: str,
    dry_run: bool,
    yes: bool,
    non_interactive: bool,
) -> None:
    """Revoke a deployment-wide application role with final-admin protection."""
    repository = SQLiteAuthorizationRepository(database or settings.AUTHORIZATION_DATABASE_PATH)
    try:
        if role not in repository.list_application_roles(principal_id):
            raise click.ClickException("Application role does not exist")
        if dry_run:
            click.echo(f"Dry run: would revoke {role} from {principal_id}")
            return
        _confirm_destructive(f"Revoke application role {role} from {principal_id}?", yes, non_interactive)
        try:
            repository.remove_application_role(principal_id, role, actor)
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Revoked application role {role} from {principal_id}")
    finally:
        repository.close()


def _confirm_destructive(message: str, yes: bool, non_interactive: bool) -> None:
    if yes or non_interactive:
        return
    if not click.confirm(message):
        raise click.Abort()


if __name__ == "__main__":
    cli()
