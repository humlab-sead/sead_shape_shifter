#!/usr/bin/env python3
"""Generate human-readable documentation from target model YAML specifications.

Supports multiple output formats:
- HTML: Interactive web documentation with entity cards and relationship diagrams
- Markdown: Static documentation for GitHub/wikis
- Excel: Spreadsheet format for review and annotation
"""

import sys
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

#!/usr/bin/env python3
"""Generate human-readable documentation from target model YAML specifications.

Supports multiple output formats:
- HTML: Interactive web documentation with entity cards and relationship diagrams
- Markdown: Static documentation for GitHub/wikis
- Excel: Spreadsheet format for review and annotation

This is a convenience CLI wrapper around src.target_model.TargetModelDocumentGenerator.
"""

import sys
from pathlib import Path

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.target_model import DocumentFormat, TargetModel, TargetModelDocumentGenerator


def load_target_model(path: Path) -> TargetModel:
    """Load and parse target model YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return TargetModel.model_validate(data)


def main():
    """Generate documentation in multiple formats using Core generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate human-readable documentation from target model YAML")
    parser.add_argument("input", type=Path, help="Input YAML file (e.g., sead_v2_extended.yml)")
    parser.add_argument("--format", choices=["html", "markdown", "excel", "all"], default="all", help="Output format")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/generated"), help="Output directory")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Input file not found: {args.input}")
        return 1

    # Load model
    print(f"📖 Loading target model: {args.input}")
    model = load_target_model(args.input)
    print(f"✓ Loaded {model.model.name} v{model.model.version} ({len(model.entities)} entities)")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    base_name = args.input.stem

    # Create generator (without project context for standalone usage)
    generator = TargetModelDocumentGenerator(target_model=model, project=None)

    # Generate requested formats
    formats_to_generate = []
    if args.format == "all":
        formats_to_generate = [DocumentFormat.HTML, DocumentFormat.MARKDOWN, DocumentFormat.EXCEL]
    else:
        formats_to_generate = [DocumentFormat(args.format)]

    for doc_format in formats_to_generate:
        extensions = {
            DocumentFormat.HTML: "html",
            DocumentFormat.MARKDOWN: "md",
            DocumentFormat.EXCEL: "xlsx",
        }
        output_path = args.output_dir / f"{base_name}.{extensions[doc_format]}"

        try:
            generator.write_to_file(doc_format, output_path)
            print(f"✅ Generated {doc_format.value} documentation: {output_path}")
        except ImportError as exc:
            print(f"❌ Missing dependency for {doc_format.value} generation: {exc}")
        except Exception as exc:
            print(f"❌ Error generating {doc_format.value}: {exc}")
            return 1

    print(f"\n✅ Documentation generated in: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
