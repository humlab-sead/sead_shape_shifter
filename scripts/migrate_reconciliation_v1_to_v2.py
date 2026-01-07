#!/usr/bin/env python3
"""
Migrate reconciliation.yml files from v1 to v2 format.

This script walks through the projects directory and migrates all reconciliation.yml
files from v1 format (composite keys) to v2 format (single target field).

Usage:
    python scripts/migrate_reconciliation_v1_to_v2.py [--dry-run] [--projects-dir PATH]
"""

import argparse
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.utils.reconciliation_migration import (
    detect_format_version,
    migrate_config_v1_to_v2,
)
from loguru import logger
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.width = 120


def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate a single reconciliation.yml file from v1 to v2.

    Args:
        file_path: Path to reconciliation.yml file
        dry_run: If True, only show what would be changed without writing

    Returns:
        True if migration was successful or not needed, False on error
    """
    try:
        logger.info(f"Processing {file_path}")

        # Load the file
        with open(file_path, "r", encoding="utf-8") as f:
            config_data = yaml.load(f)

        if not config_data:
            logger.warning(f"  Skipping empty file: {file_path}")
            return True

        # Detect format version
        version = detect_format_version(config_data)
        logger.info(f"  Detected format: {version}")

        if version == "2.0":
            logger.info(f"  Already v2 format - skipping")
            return True

        # Migrate to v2
        logger.info(f"  Migrating v1 → v2...")
        migrated_data = migrate_config_v1_to_v2(config_data)

        if dry_run:
            logger.info(f"  [DRY RUN] Would update {file_path}")
            logger.debug(f"  Migrated config:\n{yaml.dump(migrated_data, sys.stdout)}")
        else:
            # Create backup
            backup_path = file_path.with_suffix(f".yml.v1.backup")
            logger.info(f"  Creating backup: {backup_path}")
            with open(backup_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            # Write migrated file
            logger.info(f"  Writing migrated file: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(migrated_data, f)

            logger.success(f"  ✓ Successfully migrated {file_path}")

        return True

    except Exception as e:
        logger.error(f"  ✗ Failed to migrate {file_path}: {e}")
        return False


def find_reconciliation_files(projects_dir: Path) -> list[Path]:
    """
    Find all reconciliation.yml files in the projects directory.

    Args:
        projects_dir: Path to projects directory

    Returns:
        List of paths to reconciliation.yml files
    """
    reconciliation_files = []

    if not projects_dir.exists():
        logger.warning(f"Projects directory does not exist: {projects_dir}")
        return reconciliation_files

    # Search for reconciliation.yml files in all project subdirectories
    for yml_file in projects_dir.rglob("reconciliation.yml"):
        reconciliation_files.append(yml_file)

    return reconciliation_files


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate reconciliation.yml files from v1 to v2 format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing files",
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=Path("projects"),
        help="Path to projects directory (default: projects/)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    logger.info("=" * 80)
    logger.info("Reconciliation Format Migration: v1 → v2")
    logger.info("=" * 80)

    if args.dry_run:
        logger.warning("DRY RUN MODE - No files will be modified")

    # Find all reconciliation.yml files
    projects_dir = args.projects_dir.resolve()
    logger.info(f"Searching for reconciliation.yml files in: {projects_dir}")

    reconciliation_files = find_reconciliation_files(projects_dir)

    if not reconciliation_files:
        logger.warning("No reconciliation.yml files found")
        return 0

    logger.info(f"Found {len(reconciliation_files)} reconciliation.yml file(s)")
    logger.info("")

    # Migrate each file
    success_count = 0
    skip_count = 0
    fail_count = 0

    for file_path in reconciliation_files:
        result = migrate_file(file_path, dry_run=args.dry_run)
        if result:
            success_count += 1
        else:
            fail_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("Migration Summary")
    logger.info("=" * 80)
    logger.info(f"Total files processed: {len(reconciliation_files)}")
    logger.info(f"Successfully migrated: {success_count}")
    logger.info(f"Failed: {fail_count}")

    if args.dry_run:
        logger.info("")
        logger.info("This was a DRY RUN - no files were modified")
        logger.info("Run without --dry-run to apply changes")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
