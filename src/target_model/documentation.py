"""Target model documentation generator with project context integration.

Generates human-readable documentation from target model specifications in multiple formats:
- HTML: Interactive web documentation with entity cards, search, and visual indicators
- Markdown: Static documentation for GitHub/wikis
- Excel: Spreadsheet format for review and annotation

When provided with a ShapeShiftProject, enhances documentation with:
- Entity usage status (which entities are actually configured in the project)
- Validation status (conformance checking results)
- Project-specific context and statistics
"""

from __future__ import annotations

import io
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from src.target_model.models import TargetModel

if TYPE_CHECKING:
    from src.model import ShapeShiftProject


class DocumentFormat(str, Enum):
    """Supported documentation formats."""

    HTML = "html"
    MARKDOWN = "markdown"
    EXCEL = "excel"


class TargetModelDocumentGenerator:
    """Generate human-readable documentation from target models with optional project context."""

    def __init__(self, target_model: TargetModel, project: ShapeShiftProject | None = None):
        """
        Initialize documentation generator.

        Args:
            target_model: Target model specification to document.
            project: Optional project for context (entity usage, validation status).
        """
        self.target_model = target_model
        self.project = project
        self._template_dir = Path(__file__).parent / "templates"

    def _get_jinja_env(self) -> Environment:
        """Create Jinja2 environment with custom filters."""
        env = Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["pluralize"] = lambda n, singular, plural: singular if n == 1 else plural
        return env

    def _prepare_model_data(self) -> dict[str, Any]:
        """Prepare model data for templates with project context."""
        # Group entities by domain
        by_domain: dict[str, list[dict[str, Any]]] = {}
        used_entities = set(self.project.cfg.get("entities", {}).keys()) if self.project else set()

        for entity_name, entity_spec in self.target_model.entities.items():
            entity_data = {
                "name": entity_name,
                "spec": entity_spec,
                "used": entity_name in used_entities,  # Project context
            }

            for domain in entity_spec.domains or ["general"]:
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(entity_data)

        # Sort entities within each domain
        for domain in by_domain:  # type: ignore
            by_domain[domain].sort(key=lambda x: x["name"])

        # Calculate statistics
        total_entities = len(self.target_model.entities)
        required_entities = sum(1 for e in self.target_model.entities.values() if e.required)
        total_fks = sum(len(e.foreign_keys) for e in self.target_model.entities.values())
        total_columns = sum(len(e.columns) for e in self.target_model.entities.values() if e.columns)

        # Project-specific stats
        used_count = len(used_entities) if self.project else 0
        unused_required = 0
        if self.project:
            unused_required = sum(1 for name, spec in self.target_model.entities.items() if spec.required and name not in used_entities)

        return {
            "model": self.target_model.model,
            "entities": self.target_model.entities,
            "by_domain": by_domain,
            "stats": {
                "total_entities": total_entities,
                "required_entities": required_entities,
                "optional_entities": total_entities - required_entities,
                "total_fks": total_fks,
                "total_columns": total_columns,
                "domain_count": len(by_domain),
                "used_count": used_count,
                "unused_required": unused_required,
            },
            "project_name": self.project.metadata.name if self.project else None,
            "project_version": self.project.metadata.version if self.project else None,
            "has_project_context": self.project is not None,
        }

    def generate_html(self) -> bytes:
        """Generate interactive HTML documentation.

        Returns:
            HTML content as UTF-8 encoded bytes.
        """
        env = self._get_jinja_env()
        template = env.get_template("target_model.html.j2")
        data = self._prepare_model_data()
        html = template.render(**data)
        return html.encode("utf-8")

    def generate_markdown(self) -> bytes:
        """Generate Markdown documentation.

        Returns:
            Markdown content as UTF-8 encoded bytes.
        """
        env = self._get_jinja_env()
        template = env.get_template("target_model.md.j2")
        data = self._prepare_model_data()
        md = template.render(**data)
        return md.encode("utf-8")

    def generate_excel(self) -> bytes:
        """Generate Excel spreadsheet for review and annotation.

        Returns:
            Excel workbook as bytes.

        Raises:
            ImportError: If pandas or openpyxl not installed.
        """

        used_entities = set(self.project.cfg.get("entities", {}).keys()) if self.project else set()

        # Entities sheet
        entities_data = []
        for entity_name, entity_spec in sorted(self.target_model.entities.items()):
            entities_data.append(
                {
                    "Entity": entity_name,
                    "Used in Project": "Yes" if entity_name in used_entities else "No",
                    "Target Table": entity_spec.target_table or f"tbl_{entity_name}",
                    "Required": "Yes" if entity_spec.required else "No",
                    "Role": entity_spec.role or "",
                    "Public ID": entity_spec.public_id or "",
                    "Domains": ", ".join(entity_spec.domains) if entity_spec.domains else "",
                    "Column Count": len(entity_spec.columns) if entity_spec.columns else 0,
                    "FK Count": len(entity_spec.foreign_keys) if entity_spec.foreign_keys else 0,
                    "Description": entity_spec.description or "",
                }
            )

        entities_df = pd.DataFrame(entities_data)

        # Columns sheet
        columns_data = []
        for entity_name, entity_spec in sorted(self.target_model.entities.items()):
            if entity_spec.columns:
                for col_name, col_spec in entity_spec.columns.items():
                    columns_data.append(
                        {
                            "Entity": entity_name,
                            "Used in Project": "Yes" if entity_name in used_entities else "No",
                            "Column": col_name,
                            "Type": col_spec.type,
                            "Required": "Yes" if col_spec.required else "No",
                            "Nullable": "Yes" if col_spec.nullable else "No",
                            "Description": col_spec.description or "",
                        }
                    )

        columns_df = pd.DataFrame(columns_data)

        # Foreign keys sheet
        fks_data = []
        for entity_name, entity_spec in sorted(self.target_model.entities.items()):
            if entity_spec.foreign_keys:
                for fk in entity_spec.foreign_keys:
                    fks_data.append(
                        {
                            "From Entity": entity_name,
                            "Used in Project": "Yes" if entity_name in used_entities else "No",
                            "To Entity": fk.entity,
                            "Via Bridge": fk.via or "",
                            "Required": "Yes" if fk.required else "No",
                        }
                    )

        fks_df = pd.DataFrame(fks_data)

        # Write to bytes buffer
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            entities_df.to_excel(writer, sheet_name="Entities", index=False)
            columns_df.to_excel(writer, sheet_name="Columns", index=False)
            fks_df.to_excel(writer, sheet_name="Relationships", index=False)

            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            max_length = max(max_length, len(str(cell.value)))
                        except:  # noqa: E722 ; # pylint: disable=bare-except
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        buffer.seek(0)
        return buffer.read()

    def generate(self, format: DocumentFormat) -> bytes:  # pylint: disable=redefined-builtin
        """Generate documentation in specified format.

        Args:
            format: Output format (HTML, Markdown, or Excel).

        Returns:
            Document content as bytes.
        """
        if format == DocumentFormat.HTML:
            return self.generate_html()
        if format == DocumentFormat.MARKDOWN:
            return self.generate_markdown()
        if format == DocumentFormat.EXCEL:
            return self.generate_excel()
        raise ValueError(f"Unsupported format: {format}")

    def write_to_file(self, format: DocumentFormat, output_path: Path) -> None:  # pylint: disable=redefined-builtin
        """Generate documentation and write to file.

        Args:
            format: Output format.
            output_path: Path to write output file.
        """
        content: bytes = self.generate(format)
        output_path.write_bytes(content)
