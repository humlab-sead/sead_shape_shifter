"""Service for generating target model documentation with project context.

Thin wrapper around core TargetModelDocumentGenerator that handles:
- Project loading and resolution
- Target model parsing and validation
- Error handling for API layer
"""

from __future__ import annotations

from loguru import logger

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.model import ShapeShiftProject
from src.target_model import DocumentFormat, TargetModel, TargetModelDocumentGenerator


class DocumentationService:
    """Service for generating target model documentation."""

    def __init__(self, project_service: ProjectService | None = None):
        """
        Initialize documentation service.

        Args:
            project_service: Optional project service (uses singleton if not provided).
        """
        self.project_service = project_service or get_project_service()

    def generate_target_model_docs(self, project_name: str, format: DocumentFormat) -> bytes:
        """
        Generate target model documentation for a project.

        Loads the project, resolves target_model references, and generates documentation
        in the specified format with project context (which entities are used).

        Args:
            project_name: Project name to generate docs for.
            format: Output format (HTML, Markdown, or Excel).

        Returns:
            Documentation content as bytes (ready for download).

        Raises:
            NotFoundError: If project not found or has no target_model configured.
            BadRequestError: If target_model is malformed or unparseable.
        """
        # Load and resolve project
        api_project: Project = self.project_service.load_project(project_name)
        core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Get resolved target model
        target_model_data: dict | None = core_project.metadata.target_model

        if not target_model_data or not isinstance(target_model_data, dict):
            raise NotFoundError(f"Project '{project_name}' has no target_model configured")

        # Parse target model
        try:
            target_model: TargetModel = TargetModel.model_validate(target_model_data)
        except Exception as exc:
            logger.warning(f"Could not parse target model for project '{project_name}': {exc}")
            raise BadRequestError(f"Target model specification is malformed: {exc}") from exc

        # Generate documentation with project context
        generator = TargetModelDocumentGenerator(target_model=target_model, project=core_project)

        try:
            content = generator.generate(format)
            logger.info(f"Generated {format.value} documentation for project '{project_name}' ({len(content)} bytes)")
            return content
        except ImportError as exc:
            raise BadRequestError(f"Missing dependency for {format.value} generation: {exc}") from exc
        except Exception as exc:
            logger.error(f"Error generating {format.value} documentation: {exc}")
            raise BadRequestError(f"Failed to generate documentation: {exc}") from exc


# Singleton instance
_documentation_service: DocumentationService | None = None


def get_documentation_service() -> DocumentationService:
    """Get singleton documentation service instance."""
    global _documentation_service  # noqa: PLW0603
    if _documentation_service is None:
        _documentation_service = DocumentationService()
    return _documentation_service
