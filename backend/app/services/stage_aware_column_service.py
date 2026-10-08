"""Resolve draft-aware column candidates for entity operations."""

from collections.abc import Sequence
from typing import Any

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.column_availability import ColumnAvailabilityResponse
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from src.column_availability import resolve_column_availability
from src.model import ShapeShiftProject, TableConfig


class StageAwareColumnService:
    """Resolve column candidates from an unsaved entity draft and its parents."""

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service: ProjectService = project_service or ProjectService()

    def get_column_availability(
        self,
        project_name: str,
        entity_name: str,
        entity_draft: dict[str, Any],
        source_columns: Sequence[str] | None = None,
    ) -> ColumnAvailabilityResponse:
        """Map a copied project draft and return operation-specific candidates."""
        project: Project = self.project_service.load_project(project_name).model_copy(deep=True)
        project.entities[entity_name] = entity_draft
        core_project: ShapeShiftProject = ProjectMapper.to_core(project)

        table_config: TableConfig = core_project.get_table(entity_name)
        parent_names: set[str] = {foreign_key.remote_entity for foreign_key in table_config.foreign_keys}
        processed_parent_columns: dict[str, list[str]] = {}
        for parent_name in parent_names:
            if core_project.has_table(parent_name):
                parent_result: dict[str, Any] = resolve_column_availability(core_project, parent_name)
                processed_parent_columns[parent_name] = parent_result["drop_empty_rows"]

        result: dict[str, Any] = resolve_column_availability(
            core_project,
            entity_name,
            source_columns=source_columns,
            processed_parent_columns=processed_parent_columns,
        )
        return ColumnAvailabilityResponse.model_validate(result)
