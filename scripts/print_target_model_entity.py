#!/usr/bin/env python3
"""Print one entity specification from a target model YAML file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.target_model.models import TargetModel


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Print one entity specification from a target model YAML file.")
    parser.add_argument("--spec", "--target-model", dest="spec", type=Path, required=True, help="Path to the target model YAML file")
    parser.add_argument("--entity", required=True, help="Entity name to print")
    return parser


def main() -> int:
    """Load a target model and print the selected entity specification as YAML."""
    args = build_parser().parse_args()

    try:
        target_model_data = yaml.safe_load(args.spec.read_text(encoding="utf-8"))
        target_model = TargetModel.model_validate(target_model_data)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        print(f"Could not load target model '{args.spec}': {exc}", file=sys.stderr)
        return 1

    if args.entity not in target_model.entities:
        entity_names = ", ".join(target_model.entities)
        print(f"Unknown entity '{args.entity}' in '{args.spec}'. Available entities: {entity_names}", file=sys.stderr)
        return 1

    entity_config = target_model_data["entities"][args.entity]
    rendered = yaml.safe_dump({args.entity: entity_config}, sort_keys=False, allow_unicode=True)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
