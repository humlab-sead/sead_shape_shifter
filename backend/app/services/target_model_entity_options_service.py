"""Service for projecting missing target-model entities into read-only options."""

from __future__ import annotations

from typing import Any

import yaml
from loguru import logger

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import (
    Project,
    TargetModelEntityOption,
    TargetModelEntityOptionsResponse,
    TargetModelRequiredLink,
)
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.exceptions import BadRequestError
from src.model import ShapeShiftProject
from src.target_model import EntitySpec, TargetModel, TargetModelSpecValidator


class TargetModelEntityOptionsService:
    """Build read-only target entity options for a project."""

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or get_project_service()

    def get_entity_options(self, project_name: str) -> TargetModelEntityOptionsResponse:
        """Return missing target entities and their declared requirements."""
        api_project: Project = self.project_service.load_project(project_name)
        if api_project.metadata is None or api_project.metadata.target_model is None:
            return TargetModelEntityOptionsResponse(configured=False, entities=[])

        try:
            core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
            target_model_data: Any = core_project.metadata.target_model
            if not isinstance(target_model_data, dict):
                raise ValueError("Resolved target model must be a mapping")

            target_model = TargetModel.model_validate(target_model_data)
            spec_issues = TargetModelSpecValidator().validate(target_model)
        except (FileNotFoundError, OSError, UnicodeError, yaml.YAMLError, ValueError, TypeError) as exc:
            logger.warning("Could not resolve or parse target model for project '{}': {}", project_name, exc)
            raise BadRequestError("The configured target model could not be loaded or is invalid") from exc

        if spec_issues:
            logger.warning(
                "Target model for project '{}' failed specification validation: {}",
                project_name,
                [issue.message for issue in spec_issues],
            )
            raise BadRequestError("The configured target model could not be loaded or is invalid")

        project_entity_names: set[str] = set(api_project.entities)
        options = [
            self._project_entity_option(name, spec, project_entity_names)
            for name, spec in target_model.entities.items()
            if name not in project_entity_names
        ]
        options.sort(key=lambda option: (not option.required, option.name))
        return TargetModelEntityOptionsResponse(configured=True, entities=options)

    @staticmethod
    def _project_entity_option(
        name: str,
        spec: EntitySpec,
        project_entity_names: set[str],
    ) -> TargetModelEntityOption:
        required_links: list[TargetModelRequiredLink] = []
        for foreign_key in spec.foreign_keys:
            if not foreign_key.required and foreign_key.required_when is None:
                continue

            path = [foreign_key.via, foreign_key.entity] if foreign_key.via else [foreign_key.entity]
            required_links.append(
                TargetModelRequiredLink(
                    path=path,
                    missing_entities=[entity_name for entity_name in path if entity_name not in project_entity_names],
                    required_when_has_new_rows=(foreign_key.required_when.has_new_rows if foreign_key.required_when is not None else None),
                )
            )
        required_links.sort(key=lambda link: (link.path, link.required_when_has_new_rows or ""))

        return TargetModelEntityOption(
            name=name,
            role=spec.role,
            required=spec.required,
            description=spec.description,
            target_table=spec.target_table,
            public_id=spec.public_id,
            required_columns=sorted(
                column_name for column_name, column_spec in spec.columns.items() if column_spec.required and not column_spec.generated
            ),
            required_links=required_links,
        )
