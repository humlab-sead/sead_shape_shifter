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

from jinja2.environment import Template
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


class ExcelGenerator:
    """Helper class to generate Excel documentation."""

    def generate(self, project: ShapeShiftProject | None, target_model: TargetModel) -> bytes:
        """Generate Excel spreadsheet for review and annotation.

        Returns:
            Excel workbook as bytes.

        Raises:
            ImportError: If pandas or openpyxl not installed.
        """

        used_entities: set[str] = set(project.cfg.get("entities", {}).keys()) if project else set()

        sheets: dict[str, pd.DataFrame] = {
            "Entities": pd.DataFrame(
                [
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
                    for entity_name, entity_spec in sorted(target_model.entities.items())
                ]
            ),
            "Columns": pd.DataFrame(
                [
                    {
                        "Entity": entity_name,
                        "Used in Project": "Yes" if entity_name in used_entities else "No",
                        "Column": col_name,
                        "Type": col_spec.type,
                        "Required": "Yes" if col_spec.required else "No",
                        "Nullable": "Yes" if col_spec.nullable else "No",
                        "Description": col_spec.description or "",
                    }
                    for entity_name, entity_spec in sorted(target_model.entities.items())
                    if entity_spec.columns
                    for col_name, col_spec in entity_spec.columns.items()
                ]
            ),
            "Relationships": pd.DataFrame(
                [
                    {
                        "From Entity": entity_name,
                        "Used in Project": "Yes" if entity_name in used_entities else "No",
                        "To Entity": fk.entity,
                        "Via Bridge": fk.via or "",
                        "Required": "Yes" if fk.required else "No",
                    }
                    for entity_name, entity_spec in sorted(target_model.entities.items())
                    if entity_spec.foreign_keys
                    for fk in entity_spec.foreign_keys
                ]
            ),
        }

        # Write to bytes buffer
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            self.auto_resize_columns(writer)

        buffer.seek(0)
        return buffer.read()

    def auto_resize_columns(self, writer: pd.ExcelWriter):
        for sheet_name, worksheet in writer.sheets.items():
            for column in worksheet.columns:
                column_letter = column[0].column_letter
                max_length: int = max(
                    [len(str(cell.value)) for cell in column if cell.value is not None],
                    default=0,
                )
                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)


class TextDocumentGenerator:
    """Base class for text-based documentation generators (Markdown, HTML)."""

    def __init__(self):
        self._template_dir: Path = Path(__file__).parent / "templates"

    def generate(self, target_model: TargetModel, project: ShapeShiftProject | None = None) -> str:
        """Generate documentation content as a string."""
        raise NotImplementedError("Subclasses must implement generate() method")

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

    def _render_template(self, template_name: str, target_model: TargetModel, project: ShapeShiftProject | None = None) -> str:
        env: Environment = self._get_jinja_env()
        template: Template = env.get_template(template_name)
        data: dict[str, Any] = self._prepare_model_data(target_model, project)
        output: str = template.render(**data)
        return output

    def _prepare_model_data(self, target_model: TargetModel, project: ShapeShiftProject | None = None) -> dict[str, Any]:
        """Prepare model data for templates with project context."""
        # Group entities by domain
        by_domain: dict[str, list[dict[str, Any]]] = {}
        used_entities: set[str] = set(project.cfg.get("entities", {}).keys()) if project else set()

        for entity_name, entity_spec in target_model.entities.items():
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
        for domain in by_domain:  # type: ignore ; # pylint disable=consider-using-dict-items
            by_domain[domain].sort(key=lambda x: x["name"])

        # Calculate statistics
        total_entities: int = len(target_model.entities)
        required_entities: int = sum(1 for e in target_model.entities.values() if e.required)
        total_fks: int = sum(len(e.foreign_keys) for e in target_model.entities.values())
        total_columns: int = sum(len(e.columns) for e in target_model.entities.values() if e.columns)

        # Project-specific stats
        used_count: int = len(used_entities) if project else 0
        unused_required: int = 0
        if project:
            unused_required = sum(1 for name, spec in target_model.entities.items() if spec.required and name not in used_entities)

        return {
            "model": target_model.model,
            "entities": target_model.entities,
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
            "project_name": project.metadata.name if project else None,
            "project_version": project.metadata.version if project else None,
            "has_project_context": project is not None,
        }


class MarkdownDocumentGenerator(TextDocumentGenerator):
    """Generate Markdown documentation."""

    def generate(self, target_model: TargetModel, project: ShapeShiftProject | None = None) -> str:
        """Generate Markdown content."""
        return self._render_template("target_model.md.j2", target_model=target_model, project=project)


class HTMLDocumentGenerator(TextDocumentGenerator):
    """Generate interactive HTML documentation."""

    def generate(self, target_model: TargetModel, project: ShapeShiftProject | None = None) -> str:
        """Generate HTML content."""
        return self._render_template("target_model.html.j2", target_model=target_model, project=project)


class TargetModelDocumentGenerator:
    """Generate human-readable documentation from target models with optional project context."""

    def __init__(self, target_model: TargetModel, project: ShapeShiftProject | None = None):
        """
        Initialize documentation generator.

        Args:
            target_model: Target model specification to document.
            project: Optional project for context (entity usage, validation status).
        """
        self.target_model: TargetModel = target_model
        self.project: ShapeShiftProject | None = project
        self._template_dir: Path = Path(__file__).parent / "templates"

    def generate(self, format: DocumentFormat) -> bytes:  # pylint: disable=redefined-builtin
        """Generate documentation in specified format.

        Args:
            format: Output format (HTML, Markdown, or Excel).

        Returns:
            Document content as bytes.
        """

        if format == DocumentFormat.HTML:
            return HTMLDocumentGenerator().generate(self.target_model, self.project).encode("utf-8")

        if format == DocumentFormat.MARKDOWN:
            return MarkdownDocumentGenerator().generate(self.target_model, self.project).encode("utf-8")

        if format == DocumentFormat.EXCEL:
            return ExcelGenerator().generate(self.project, self.target_model)

        raise ValueError(f"Unsupported format: {format}")

    def write_to_file(self, format: DocumentFormat, output_path: Path) -> None:  # pylint: disable=redefined-builtin
        """Generate documentation and write to file.

        Args:
            format: Output format.
            output_path: Path to write output file.
        """
        content: bytes = self.generate(format)
        output_path.write_bytes(content)
