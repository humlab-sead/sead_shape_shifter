#!/usr/bin/env python
"""CLI script for running auto-reconciliation workflow."""

import asyncio
import sys
from pathlib import Path

import click
from loguru import logger

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import AutoReconcileResult
from backend.app.services.reconciliation_service import ReconciliationService
from backend.app.utils.exceptions import BadRequestError, NotFoundError


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    logger.remove()  # Remove default handler
    
    if verbose:
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="DEBUG",
        )
    else:
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="INFO",
        )


async def run_reconciliation(
    project_name: str,
    entity_name: str,
    threshold: float,
    service_url: str,
    max_candidates: int,
) -> AutoReconcileResult:
    """Execute the reconciliation workflow."""
    
    # Initialize services
    logger.info(f"Connecting to reconciliation service: {service_url}")
    recon_client = ReconciliationClient(base_url=service_url)
    
    service = ReconciliationService(
        config_dir=Path(settings.PROJECTS_DIR),
        reconciliation_client=recon_client
    )
    
    try:
        # Check service health
        health = await recon_client.check_health()
        if health.get("status") != "online":
            logger.error(f"Reconciliation service is offline: {health.get('error')}")
            raise RuntimeError("Reconciliation service is not available")
        
        logger.info(f"Service online: {health.get('service_name')}")
        
        # Load reconciliation config
        logger.info(f"Loading reconciliation config for project: {project_name}")
        recon_config = service.load_reconciliation_config(project_name)
        
        if entity_name not in recon_config.entities:
            raise NotFoundError(f"No reconciliation spec for entity '{entity_name}'")
        
        entity_spec = recon_config.entities[entity_name]
        
        # Update threshold if different
        if threshold != entity_spec.auto_accept_threshold:
            logger.info(f"Updating auto-accept threshold from {entity_spec.auto_accept_threshold} to {threshold}")
            entity_spec.auto_accept_threshold = threshold
        
        # Run auto-reconciliation
        logger.info(f"Starting auto-reconciliation for entity: {entity_name}")
        logger.info(f"Auto-accept threshold: {threshold}")
        logger.info(f"Max candidates per query: {max_candidates}")
        
        result = await service.auto_reconcile_entity(
            project_name=project_name,
            entity_name=entity_name,
            entity_spec=entity_spec,
            max_candidates=max_candidates,
        )
        
        return result
        
    finally:
        # Cleanup
        await recon_client.close()


def print_results(result: AutoReconcileResult, verbose: bool) -> None:
    """Print reconciliation results in a formatted way."""
    
    click.echo()
    click.secho("=== Reconciliation Results ===", fg="cyan", bold=True)
    click.echo()
    
    click.echo(f"  Total queries:      {result.total}")
    click.secho(f"  Auto-accepted:      {result.auto_accepted}", fg="green")
    click.secho(f"  Needs review:       {result.needs_review}", fg="yellow")
    click.secho(f"  Unmatched:          {result.unmatched}", fg="red")
    click.echo()
    
    if result.auto_accepted > 0:
        acceptance_rate = (result.auto_accepted / result.total * 100) if result.total > 0 else 0
        click.secho(f"  Acceptance rate:    {acceptance_rate:.1f}%", fg="green")
    
    if verbose and result.candidates:
        click.echo()
        click.secho("=== Top Candidates Sample ===", fg="cyan", bold=True)
        click.echo()
        
        # Show first 5 candidates
        for i, (key, candidates) in enumerate(list(result.candidates.items())[:5]):
            click.echo(f"  Query: {key}")
            if candidates:
                for j, candidate in enumerate(candidates[:3]):  # Top 3 per query
                    match_symbol = "✓" if candidate.match else "○"
                    score_color = "green" if candidate.score >= 0.95 else "yellow" if candidate.score >= 0.8 else "white"
                    click.echo(f"    {match_symbol} ", nl=False)
                    click.secho(f"{candidate.name}", fg=score_color, nl=False)
                    click.echo(f" (score: {candidate.score:.2f})")
            else:
                click.secho("    No candidates found", fg="red")
            click.echo()


@click.command()
@click.argument("project_name")
@click.argument("entity_name")
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=0.95,
    help="Auto-accept threshold (0.0-1.0). Default: 0.95",
    show_default=True,
)
@click.option(
    "--max-candidates",
    "-m",
    type=int,
    default=3,
    help="Maximum candidates per query. Default: 3",
    show_default=True,
)
@click.option(
    "--service-url",
    "-s",
    type=str,
    default=None,
    help="Reconciliation service URL. Default: from settings",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
def main(
    project_name: str,
    entity_name: str,
    threshold: float,
    max_candidates: int,
    service_url: str | None,
    verbose: bool,
) -> None:
    """
    Run auto-reconciliation for an entity in a project.
    
    PROJECT_NAME: Name of the project configuration
    ENTITY_NAME: Name of the entity to reconcile
    
    Examples:
    
        # Reconcile 'site' entity with default settings
        python scripts/auto_reconcile.py my_project site
        
        # Reconcile with custom threshold
        python scripts/auto_reconcile.py my_project site --threshold 0.90
        
        # Reconcile with custom service URL
        python scripts/auto_reconcile.py my_project site --service-url http://localhost:8000
        
        # Enable verbose logging
        python scripts/auto_reconcile.py my_project site -v
    """
    
    setup_logging(verbose)
    
    # Validate threshold
    if not 0.0 <= threshold <= 1.0:
        click.secho("Error: Threshold must be between 0.0 and 1.0", fg="red", err=True)
        sys.exit(1)
    
    # Use service URL from settings if not provided
    if service_url is None:
        service_url = settings.RECONCILIATION_SERVICE_URL
    
    logger.info(f"Auto-reconcile CLI started")
    logger.info(f"Project: {project_name}")
    logger.info(f"Entity: {entity_name}")
    
    try:
        # Run async reconciliation
        result = asyncio.run(
            run_reconciliation(
                project_name=project_name,
                entity_name=entity_name,
                threshold=threshold,
                service_url=service_url,
                max_candidates=max_candidates,
            )
        )
        
        # Print results
        print_results(result, verbose)
        
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
    except Exception as e:
        logger.exception("Unexpected error during reconciliation")
        click.secho(f"\nUnexpected error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
