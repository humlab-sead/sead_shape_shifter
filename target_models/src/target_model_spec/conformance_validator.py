from __future__ import annotations

from dataclasses import dataclass

from target_model_spec.models import TargetModel
from target_model_spec.project_models import ProjectEntitySpec, ShapeShifterProject


@dataclass(slots=True)
class ConformanceIssue:
    code: str
    message: str
    entity: str | None = None


class TargetModelConformanceValidator:
    def validate(self, target_model: TargetModel, project: ShapeShifterProject) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []

        for entity_name, entity_spec in target_model.entities.items():
            project_entity = project.entities.get(entity_name)

            if entity_spec.required and project_entity is None:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_ENTITY",
                        message=f"Target model requires entity '{entity_name}'",
                        entity=entity_name,
                    )
                )
                continue

            if project_entity is None:
                continue

            issues.extend(self._validate_public_id(entity_name, entity_spec.public_id, project_entity.public_id))
            issues.extend(self._validate_required_foreign_keys(entity_name, entity_spec.foreign_keys, project_entity))
            issues.extend(self._validate_required_columns(entity_name, entity_spec.columns, project_entity, target_model))

        return issues

    @staticmethod
    def _validate_public_id(entity_name: str, expected_public_id: str | None, project_public_id: str | None) -> list[ConformanceIssue]:
        if expected_public_id is None:
            return []

        if project_public_id is None:
            return [
                ConformanceIssue(
                    code="MISSING_PUBLIC_ID",
                    message=f"Entity '{entity_name}' is missing expected public_id '{expected_public_id}'",
                    entity=entity_name,
                )
            ]

        if project_public_id != expected_public_id:
            return [
                ConformanceIssue(
                    code="UNEXPECTED_PUBLIC_ID",
                    message=(
                        f"Entity '{entity_name}' declares public_id '{project_public_id}' "
                        f"but target model expects '{expected_public_id}'"
                    ),
                    entity=entity_name,
                )
            ]

        return []

    @staticmethod
    def _validate_required_foreign_keys(entity_name: str, target_foreign_keys: list, project_entity: ProjectEntitySpec) -> list[ConformanceIssue]:
        project_foreign_key_entities = {foreign_key.entity for foreign_key in project_entity.foreign_keys}
        issues: list[ConformanceIssue] = []

        for foreign_key in target_foreign_keys:
            if foreign_key.required and foreign_key.entity not in project_foreign_key_entities:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_FOREIGN_KEY_TARGET",
                        message=(
                            f"Entity '{entity_name}' is missing required foreign key target '{foreign_key.entity}'"
                        ),
                        entity=entity_name,
                    )
                )

        return issues

    def _validate_required_columns(
        self,
        entity_name: str,
        target_columns: dict,
        project_entity: ProjectEntitySpec,
        target_model: TargetModel,
    ) -> list[ConformanceIssue]:
        declared_columns = self._declared_project_columns(project_entity, target_model)
        issues: list[ConformanceIssue] = []

        for column_name, column_spec in target_columns.items():
            if column_spec.required and column_name not in declared_columns:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_COLUMN",
                        message=f"Entity '{entity_name}' is missing required target-facing column '{column_name}'",
                        entity=entity_name,
                    )
                )

        return issues

    @staticmethod
    def _declared_project_columns(project_entity: ProjectEntitySpec, target_model: TargetModel) -> set[str]:
        column_names: set[str] = set()

        column_names.update(TargetModelConformanceValidator._literal_names(project_entity.keys))
        column_names.update(TargetModelConformanceValidator._literal_names(project_entity.columns))
        column_names.update(project_entity.extra_columns)

        if project_entity.public_id:
            column_names.add(project_entity.public_id)

        if project_entity.unnest:
            column_names.update(TargetModelConformanceValidator._literal_names(project_entity.unnest.id_vars))
            if project_entity.unnest.var_name:
                column_names.add(project_entity.unnest.var_name)
            if project_entity.unnest.value_name:
                column_names.add(project_entity.unnest.value_name)

        for foreign_key in project_entity.foreign_keys:
            target_entity = target_model.entities.get(foreign_key.entity)
            if target_entity and target_entity.public_id:
                column_names.add(target_entity.public_id)

        return column_names

    @staticmethod
    def _literal_names(value: list[str] | str) -> set[str]:
        if isinstance(value, list):
            return {item for item in value if isinstance(item, str)}
        return set()