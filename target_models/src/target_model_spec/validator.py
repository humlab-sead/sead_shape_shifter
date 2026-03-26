from __future__ import annotations

from dataclasses import dataclass

from target_model_spec.models import TargetModel


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    entity: str | None = None


class TargetModelSpecValidator:
    def validate(self, target_model: TargetModel) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        suffix = target_model.naming.public_id_suffix if target_model.naming else None

        for entity_name, entity_spec in target_model.entities.items():
            if suffix and entity_spec.public_id and not entity_spec.public_id.endswith(suffix):
                issues.append(
                    ValidationIssue(
                        code="INVALID_PUBLIC_ID_SUFFIX",
                        message=f"Entity '{entity_name}' has public_id '{entity_spec.public_id}' which does not end with '{suffix}'",
                        entity=entity_name,
                    )
                )

            for foreign_key in entity_spec.foreign_keys:
                if foreign_key.entity not in target_model.entities:
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_FOREIGN_KEY_ENTITY",
                            message=f"Entity '{entity_name}' references unknown foreign key target '{foreign_key.entity}'",
                            entity=entity_name,
                        )
                    )

        return issues