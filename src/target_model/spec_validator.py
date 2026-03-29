from __future__ import annotations

from dataclasses import dataclass

from src.target_model.models import TargetModel


@dataclass(slots=True)
class SpecValidationIssue:
    code: str
    message: str
    entity: str | None = None


class TargetModelSpecValidator:
    def validate(self, target_model: TargetModel) -> list[SpecValidationIssue]:
        issues: list[SpecValidationIssue] = []
        suffix = target_model.naming.public_id_suffix if target_model.naming else None

        for entity_name, entity_spec in target_model.entities.items():
            column_names = set(entity_spec.columns)

            if suffix and entity_spec.public_id and not entity_spec.public_id.endswith(suffix):
                issues.append(
                    SpecValidationIssue(
                        code="INVALID_PUBLIC_ID_SUFFIX",
                        message=(f"Entity '{entity_name}' has public_id '{entity_spec.public_id}' " f"which does not end with '{suffix}'"),
                        entity=entity_name,
                    )
                )

            for foreign_key in entity_spec.foreign_keys:
                if foreign_key.entity not in target_model.entities:
                    issues.append(
                        SpecValidationIssue(
                            code="UNKNOWN_FOREIGN_KEY_ENTITY",
                            message=f"Entity '{entity_name}' references unknown foreign key target '{foreign_key.entity}'",
                            entity=entity_name,
                        )
                    )

            for identity_column in entity_spec.identity_columns:
                if identity_column not in column_names:
                    issues.append(
                        SpecValidationIssue(
                            code="UNKNOWN_IDENTITY_COLUMN",
                            message=f"Entity '{entity_name}' references unknown identity column '{identity_column}'",
                            entity=entity_name,
                        )
                    )

            for unique_set in entity_spec.unique_sets:
                for column_name in unique_set:
                    if column_name not in column_names:
                        issues.append(
                            SpecValidationIssue(
                                code="UNKNOWN_UNIQUE_SET_COLUMN",
                                message=f"Entity '{entity_name}' references unknown unique-set column '{column_name}'",
                                entity=entity_name,
                            )
                        )

        return issues
