#!/usr/bin/env python
"""CLI script for running auto-reconciliation workflow."""

import asyncio
import sys
from pathlib import Path

import click
from loguru import logger

# pylint: disable=wrong-import-position, no-value-for-parameter
# no-value-for-parameter is a false positive: click fills the decorated arguments.
from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import AutoReconcileResult
from backend.app.services.reconciliation import ReconciliationService
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.reconciliation import model as core


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    logger.remove()  # Remove default handler

    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG" if verbose else "INFO",
    )


def resolve_resolution_set(
    service: ReconciliationService,
    project_name: str,
    entity_name: str,
    target_field: str | None,
) -> tuple[str, core.EntityResolutionSet]:
    """Return the target field and its resolution set for one entity.

    The catalog stores one resolution set per entity and target field. When the
    caller does not name a field, the entity's only field is used. An entity with
    several fields is reported instead of guessing which one to reconcile,
    because a run writes decisions for the field it resolves.
    """
    catalog: core.EntityResolutionCatalog = service.catalog_manager.load_catalog(project_name)
    fields: dict[str, core.EntityResolutionSet] = catalog.entities.get(entity_name, {})

    if not fields:
        raise NotFoundError(f"No reconciliation specification for entity '{entity_name}'")

    available: str = ", ".join(sorted(fields))

    if target_field is None:
        if len(fields) > 1:
            raise BadRequestError(
                f"Entity '{entity_name}' has several reconciliation target fields ({available}). " "Pass --target-field to choose one."
            )
        target_field = next(iter(fields))

    resolution_set: core.EntityResolutionSet | None = fields.get(target_field)
    if resolution_set is None:
        raise NotFoundError(
            f"No reconciliation specification for entity '{entity_name}' target field '{target_field}'. "
            f"Available target fields: {available}"
        )

    return target_field, resolution_set


async def run_reconciliation(
    project_name: str,
    entity_name: str,
    target_field: str | None,
    threshold: float | None,
    review_threshold: float | None,
    service_url: str,
    max_candidates: int,
    project_dir: Path | None = None,
) -> tuple[str, AutoReconcileResult]:
    """Execute the reconciliation workflow and return the field used with its result."""
    logger.info(f"Connecting to reconciliation service: {service_url}")
    recon_client = ReconciliationClient(base_url=service_url)
    config_dir: Path = project_dir if project_dir else settings.PROJECTS_DIR
    service = ReconciliationService(config_dir=config_dir, reconciliation_client=recon_client)

    try:
        # Resolve the specification before contacting the service, so a wrong
        # entity or target field is reported without needing a reachable service.
        logger.info(f"Loading reconciliation catalog for project: {project_name}")
        resolved_field, resolution_set = resolve_resolution_set(service, project_name, entity_name, target_field)

        # An omitted threshold keeps the value saved in the specification.
        resolution_set.metadata.update_thresholds(
            threshold=threshold if threshold is not None else resolution_set.metadata.auto_accept_threshold,
            review_threshold=review_threshold,
        )

        health = await recon_client.check_health()
        if health.get("status") != "online":
            logger.error(f"Reconciliation service is offline: {health.get('error')}")
            raise RuntimeError("Reconciliation service is not available")

        logger.info(f"Service online: {health.get('service_name')}")

        logger.info(f"Starting auto-reconciliation for entity: {entity_name}")
        logger.info(f" Target field: {resolved_field}")
        logger.info(f" Auto-accept threshold: {resolution_set.metadata.auto_accept_threshold}")
        logger.info(f" Review threshold: {resolution_set.metadata.review_threshold}")
        logger.info(f" Max candidates per query: {max_candidates}")

        result = await service.auto_reconcile_entity(
            project_name=project_name,
            entity_name=entity_name,
            target_field=resolved_field,
            entity_mapping=resolution_set,
            max_candidates=max_candidates,
        )

        return resolved_field, result

    finally:
        # Cleanup
        await recon_client.close()


def print_results(target_field: str, result: AutoReconcileResult, verbose: bool) -> None:
    """Print reconciliation results in a formatted way."""

    click.echo()
    click.secho("=== Reconciliation Results ===", fg="cyan", bold=True)
    click.echo()

    click.echo(f"  Target field:        {target_field}")
    click.echo(f"  Total rows:          {result.total}")
    click.secho(f"  Decisions proposed:  {result.proposed}", fg="green")
    click.secho(f"  Unmatched:           {result.unmatched}", fg="red")
    click.echo()

    if result.total > 0:
        proposal_rate = result.proposed / result.total * 100
        click.secho(f"  Proposal rate:       {proposal_rate:.1f}%", fg="green")

    if result.errors:
        click.secho(f"\n  Rows not reconciled: {len(result.errors)}", fg="yellow")
        for error in result.errors[:5]:
            click.echo(f"    row {error.row_index}: {error.message}")
        if len(result.errors) > 5:
            click.echo(f"    ... and {len(result.errors) - 5} more")

    if verbose and result.candidates:
        click.echo()
        click.secho("=== Top Candidates Sample ===", fg="cyan", bold=True)
        click.echo()

        # Show first 5 candidates
        for _, (key, candidates) in enumerate(list(result.candidates.items())[:5]):
            click.echo(f"  Query: {key}")
            if candidates:
                for candidate in candidates[:3]:  # Top 3 per query
                    score: float = candidate.score if candidate.score is not None else 0.0
                    match_symbol = "✓" if candidate.match else "○"
                    score_color = "green" if score >= 0.95 else "yellow" if score >= 0.8 else "white"
                    click.echo(f"    {match_symbol} ", nl=False)
                    click.secho(f"{candidate.name}", fg=score_color, nl=False)
                    click.echo(f" (score: {score:.2f})")
            else:
                click.secho("    No candidates found", fg="red")
            click.echo()


@click.command()
@click.argument("project_name")
@click.argument("entity_name")
@click.option(
    "--target-field",
    "-f",
    type=str,
    default=None,
    help="Reconciliation target field. Default: the entity's only configured field",
)
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=None,
    help="Auto-accept threshold (0.0-1.0). Default: the value saved in the specification",
)
@click.option(
    "--review-threshold",
    "-r",
    type=float,
    default=None,
    help="Review threshold (0.0-1.0). Default: the value saved in the specification",
)
@click.option("--max-candidates", "-m", type=int, default=3, help="Maximum candidates per query. Default: 3", show_default=True)
@click.option("--service-url", "-s", type=str, default=None, help="Reconciliation service URL. Default: from settings")
@click.option(
    "--project-dir",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Project directory. Default: Settings.PROJECTS_DIR",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging (DEBUG level)")
def main(
    project_dir: Path | None,
    project_name: str,
    entity_name: str,
    target_field: str | None,
    threshold: float | None,
    review_threshold: float | None,
    max_candidates: int,
    service_url: str | None,
    verbose: bool,
) -> None:
    """
    Run auto-reconciliation for an entity in a project.

    PROJECT_NAME: Name of the project configuration
    ENTITY_NAME: Name of the entity to reconcile

    Writes proposed decisions to the project's reconciliation catalog. Review them
    in the web interface before exporting them to the mapping.

    Examples:

        # Reconcile 'site' entity with the thresholds saved in the specification
        python scripts/project/auto_reconcile.py my_project site

        # Reconcile one target field when the entity has several
        python scripts/project/auto_reconcile.py my_project site --target-field site_name

        # Reconcile with custom thresholds
        python scripts/project/auto_reconcile.py my_project site --threshold 0.90 --review-threshold 0.40

        # Reconcile with custom service URL
        python scripts/project/auto_reconcile.py my_project site --service-url http://localhost:8000

        # Enable verbose logging
        python scripts/project/auto_reconcile.py my_project site -v
    """

    setup_logging(verbose)

    # Validate thresholds
    for name, value in (("--threshold", threshold), ("--review-threshold", review_threshold)):
        if value is not None and not 0.0 <= value <= 1.0:
            click.secho(f"Error: {name} must be between 0.0 and 1.0", fg="red", err=True)
            sys.exit(1)

    # Use service URL from settings if not provided
    if service_url is None:
        service_url = settings.RECONCILIATION_SERVICE_URL

    logger.info("Auto-reconcile CLI started")
    logger.info(f"Service URL: {service_url}")
    logger.info(f"Project: {project_name}")
    logger.info(f"Entity: {entity_name}")
    if target_field:
        logger.info(f"Target field: {target_field}")

    try:
        # Run async reconciliation
        resolved_field, result = asyncio.run(
            run_reconciliation(
                project_dir=project_dir,
                project_name=project_name,
                entity_name=entity_name,
                target_field=target_field,
                threshold=threshold,
                review_threshold=review_threshold,
                service_url=service_url,
                max_candidates=max_candidates,
            )
        )

        # Print results
        print_results(resolved_field, result, verbose)

        # Exit with status based on results
        if result.total == 0:
            click.secho("\nWarning: No queries were processed", fg="yellow", err=True)
            sys.exit(2)
        elif result.unmatched == result.total:
            click.secho("\nWarning: All queries unmatched", fg="yellow", err=True)
            sys.exit(3)
        else:
            click.secho("\n✓ Reconciliation completed successfully", fg="green")
            sys.exit(0)

    except NotFoundError as e:
        click.secho(f"\nError: {e}", fg="red", err=True)
        sys.exit(4)
    except BadRequestError as e:
        click.secho(f"\nError: {e}", fg="red", err=True)
        sys.exit(5)
    except RuntimeError as e:
        click.secho(f"\nError: {e}", fg="red", err=True)
        sys.exit(6)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Unexpected error during reconciliation")
        click.secho(f"\nUnexpected error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
