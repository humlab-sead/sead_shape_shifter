from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.model import ShapeShiftProject, TableConfig
from src.target_model.models import TargetModel


@dataclass(slots=True)
class ConformanceIssue:
    code: str
    message: str
    entity: str | None = None


class TargetModelConformanceValidator:
    """Validate a resolved Shape Shifter project against a target model. """

    def __init__(
        self,
        *,
        foreign_key_column_source: Literal["project", "target_model"] = "project",
    ) -> None:
        self.foreign_key_column_source = foreign_key_column_source

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []

        for entity_name, entity_spec in target_model.entities.items():
            if entity_spec.required and not project.has_table(entity_name):
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_ENTITY",
                        message=f"Target model requires entity '{entity_name}'",
                        entity=entity_name,
                    )
                )
                continue

            if not project.has_table(entity_name):
                continue

            table_cfg: TableConfig = project.get_table(entity_name)

            issues.extend(self._validate_public_id(entity_name, entity_spec.public_id, table_cfg.public_id or None))
            issues.extend(self._validate_required_foreign_keys(entity_name, entity_spec.foreign_keys, table_cfg))
            issues.extend(self._validate_required_columns(entity_name, entity_spec.columns, table_cfg, target_model))

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

    def _validate_required_foreign_keys(
        self, entity_name: str, target_foreign_keys: list, table_cfg: TableConfig
    ) -> list[ConformanceIssue]:
        project_targets = table_cfg.get_target_facing_foreign_key_targets()
        issues: list[ConformanceIssue] = []

        for foreign_key in target_foreign_keys:
            if foreign_key.required and foreign_key.entity not in project_targets:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_FOREIGN_KEY_TARGET",
                        message=f"Entity '{entity_name}' is missing required foreign key target '{foreign_key.entity}'",
                        entity=entity_name,
                    )
                )

        return issues

    def _validate_required_columns(
        self,
        entity_name: str,
        target_columns: dict,
        table_cfg: TableConfig,
        target_model: TargetModel,
    ) -> list[ConformanceIssue]:
        declared_columns = set(table_cfg.get_target_facing_columns())

        if self.foreign_key_column_source == "target_model":
            for foreign_key_target in table_cfg.get_target_facing_foreign_key_targets():
                target_entity = target_model.entities.get(foreign_key_target)
                if target_entity and target_entity.public_id:
                    declared_columns.add(target_entity.public_id)

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
