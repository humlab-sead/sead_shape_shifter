#!/usr/bin/env python3
"""Re-order Shape Shifter entity keys the way a full project save does.

The editor writes each entity's keys in a fixed order (``type``, ``source``,
``system_id``, ``public_id``, ``keys``, ``columns``, ``values``, and so on). Two
copies of the same project that were written by different code paths, or edited by
hand, can therefore differ only in key order. This script applies the same ordering
pass as ``YamlService.save`` so those differences disappear and real changes stand
out in a diff.

The script reformats only. It writes the file directly and runs no project
validation.

Examples:
    uv run python scripts/sort_project_yaml.py data/projects/example/shapeshifter.yml > sorted.yml
    uv run python scripts/sort_project_yaml.py --inplace data/projects/example/shapeshifter.yml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, YamlService


def configure_logging() -> None:
    """Show warnings and errors only; hide the DEBUG and INFO chatter from YamlService."""
    logger.remove()
    logger.add(sys.stderr, level="WARNING", format="{level}: {message}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Re-order Shape Shifter entity keys the way a full project save does.",
    )
    parser.add_argument("project_file", type=Path, help="Path to a shapeshifter.yml project file")
    parser.add_argument(
        "-i",
        "--inplace",
        action="store_true",
        help="Rewrite the input file instead of printing the result to stdout",
    )
    return parser


def main() -> int:
    """Print the sorted project file, or rewrite it with --inplace."""
    args = build_parser().parse_args()
    configure_logging()
    service = YamlService()

    try:
        data: dict[str, Any] = service.load(args.project_file)
    except YamlLoadError as exc:
        print(f"Could not read '{args.project_file}': {exc}", file=sys.stderr)
        return 1

    if args.inplace:
        try:
            # A timestamped backup next to the project would pollute the project folder,
            # so the caller is expected to keep its own copy (typically a git revision).
            service.save(data, args.project_file, create_backup=False)
        except YamlSaveError as exc:
            print(f"Could not write '{args.project_file}': {exc}", file=sys.stderr)
            return 1
        return 0

    sys.stdout.write(service.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
