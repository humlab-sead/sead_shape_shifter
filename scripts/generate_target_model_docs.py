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

    parser = argparse.ArgumentParser(
        description="Generate human-readable documentation from a target model YAML specification.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output formats
--------------
  html      Interactive web page with entity cards, live search, domain groupings,
            and relationship arrows. Recommended for stakeholder presentations and
            reference documentation. Opens in any browser; no software required.

  excel     Excel workbook with three sheets (Entities, Columns, Relationships).
            Sortable and filterable. Best for review workshops, gap analysis, and
            collecting structured feedback. Add review columns ("Complete?",
            "Priority", "Comments") and distribute to domain experts.

  markdown  Plain-text Markdown grouped by domain. Renders on GitHub/GitLab.
            Version-controlled and can be converted to PDF or Word.

  all       Generates all three formats in one pass (default).

Output files
------------
  Files are written to --output-dir (default: docs/generated/) using the input
  file stem as the base name, e.g.:
    docs/generated/sead_standard_model.html
    docs/generated/sead_standard_model.md
    docs/generated/sead_standard_model.xlsx

Understanding entity cards (HTML)
----------------------------------
  ┌─────────────────────────────────────┐
  │ sample_group                        │  ← entity name
  │ → tbl_sample_groups                 │  ← target table
  │ [Required] [data]                   │  ← status / role badges
  │ Collection of related samples       │  ← description
  │ 📊 6 column(s)                      │  ← metadata
  │ sample_group → site (required)      │  ← relationships
  └─────────────────────────────────────┘

  Badges:
    Required (red)   – must be included in every project
    Optional (green) – can be omitted if not needed
    Role (blue): data | classifier | bridge | lookup

  Relationship arrows:
    entity_a → entity_b                  entity_a references entity_b
    entity_a → entity_b (required)       the relationship is mandatory
    entity_a → entity_b via bridge_tbl   relationship goes through a bridge entity

Examples
--------
  # Generate all formats from the bundled SEAD spec
  python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml

  # HTML only (recommended for stakeholder review)
  python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format html

  # Excel for gap-analysis workshop
  python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format excel

  # Custom output directory
  python scripts/generate_target_model_docs.py my_model.yml --format all --output-dir /tmp/model-docs
""",
    )
    parser.add_argument("input", type=Path, help="Input YAML file (e.g., resources/target_models/sead_standard_model.yml)")
    parser.add_argument(
        "--format",
        choices=["html", "markdown", "excel", "all"],
        default="all",
        help="Output format: html (interactive), markdown (plain text), excel (spreadsheet), all (default)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/generated"), help="Output directory (default: docs/generated)")

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
