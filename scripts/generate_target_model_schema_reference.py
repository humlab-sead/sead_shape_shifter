#!/usr/bin/env python3
"""Generate a Markdown reference for the target-model schema from Pydantic models."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "TARGET_MODEL_SCHEMA_REFERENCE.md"

sys.path.insert(0, str(PROJECT_ROOT))

from src.target_model.schema_reference import generate_target_model_schema_reference


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for target-model schema reference generation."""
    parser = argparse.ArgumentParser(
        description="Generate a Markdown reference for the target-model schema from Pydantic models.",
    )
    parser.add_argument("--check", action="store_true", help="Check whether the committed reference file is in sync.")
    parser.add_argument("--print", action="store_true", help="Print the generated reference to stdout instead of writing a file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output file (default: {DEFAULT_OUTPUT_PATH.relative_to(PROJECT_ROOT)})",
    )
    return parser


def main() -> int:
    """Generate the target-model schema reference or check it for drift."""
    parser = build_parser()
    args = parser.parse_args()

    rendered = generate_target_model_schema_reference()

    if args.print:
        print(rendered, end="")
        return 0

    if args.check:
        if not args.output.exists():
            print(f"Reference file not found: {args.output}", file=sys.stderr)
            print("Run: python scripts/generate_target_model_schema_reference.py", file=sys.stderr)
            return 1
        committed = args.output.read_text(encoding="utf-8")
        if committed != rendered:
            print(f"Reference file is out of sync: {args.output}", file=sys.stderr)
            diff = "".join(
                difflib.unified_diff(
                    committed.splitlines(keepends=True),
                    rendered.splitlines(keepends=True),
                    fromfile=str(args.output),
                    tofile="generated",
                )
            )
            if diff:
                print(diff, file=sys.stderr, end="")
            print("Run: python scripts/generate_target_model_schema_reference.py", file=sys.stderr)
            return 1
        print(f"Reference file is in sync: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())