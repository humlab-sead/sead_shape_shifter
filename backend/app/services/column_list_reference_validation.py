"""Check saved column-list references while their original text is available."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata
from backend.app.models.validation import ValidationCategory, ValidationError
from src.configuration.resolve import RequestedReferenceResolutionError, split_reference_expression
from src.utility import dotget

_VALUE_DIRECTIVE = "@value:"
_RESOLUTION_ERROR_CODES = {
    "missing_path": "COLUMN_REFERENCE_MISSING_PATH",
    "circular_reference": "COLUMN_REFERENCE_CIRCULAR_REFERENCE",
    "dependency_failure": "COLUMN_REFERENCE_DEPENDENCY_FAILURE",
}


@dataclass(frozen=True)
class _ReferenceOccurrence:
    """One raw reference and the field where it was saved."""

    entity: str
    field: str
    text: str
    list_item: bool
    expression: bool


class ColumnListReferenceValidationService:
    """Return located errors for references saved in supported column-list fields."""

    def validate(self, project_cfg: dict[str, Any], *, source_path: str | None = None) -> list[ValidationError]:
        """Check references in raw project data without changing the supplied mapping."""
        occurrences = list(self._collect_occurrences(project_cfg))
        if not occurrences:
            return []

        snapshot = self._make_snapshot(project_cfg, source_path)
        errors: list[ValidationError] = []
        for occurrence in occurrences:
            if occurrence.expression:
                errors.extend(self._validate_expression(snapshot, occurrence, project_cfg, source_path))
            else:
                errors.extend(self._validate_simple_reference(snapshot, occurrence))
        return errors

    def _collect_occurrences(self, project_cfg: dict[str, Any]) -> list[_ReferenceOccurrence]:
        """Visit only saved fields that accept column lists."""
        entities = project_cfg.get("entities")
        if not isinstance(entities, dict):
            return []

        occurrences: list[_ReferenceOccurrence] = []
        for entity_name, entity_cfg in entities.items():
            if not isinstance(entity_name, str) or not isinstance(entity_cfg, dict):
                continue

            entity_type = entity_cfg.get("type")
            self._collect_field(occurrences, entity_name, entity_cfg.get("keys"), "keys")
            if entity_type != "fixed":
                self._collect_field(occurrences, entity_name, entity_cfg.get("columns"), "columns")

            foreign_keys = entity_cfg.get("foreign_keys")
            if isinstance(foreign_keys, list):
                for index, foreign_key in enumerate(foreign_keys):
                    if isinstance(foreign_key, dict):
                        prefix = f"foreign_keys[{index}]"
                        self._collect_field(occurrences, entity_name, foreign_key.get("local_keys"), f"{prefix}.local_keys")
                        self._collect_field(occurrences, entity_name, foreign_key.get("remote_keys"), f"{prefix}.remote_keys")
            elif isinstance(foreign_keys, dict):
                for foreign_key_name, foreign_key in foreign_keys.items():
                    if not isinstance(foreign_key, dict):
                        continue
                    prefix = f"foreign_keys.{foreign_key_name}"
                    self._collect_field(occurrences, entity_name, foreign_key.get("local_keys"), f"{prefix}.local_keys")
                    self._collect_field(occurrences, entity_name, foreign_key.get("remote_keys"), f"{prefix}.remote_keys")

            unnest = entity_cfg.get("unnest")
            if isinstance(unnest, dict):
                self._collect_field(occurrences, entity_name, unnest.get("id_vars"), "unnest.id_vars")
                self._collect_field(occurrences, entity_name, unnest.get("value_vars"), "unnest.value_vars")

            drop_duplicates = entity_cfg.get("drop_duplicates")
            if isinstance(drop_duplicates, dict):
                self._collect_field(occurrences, entity_name, drop_duplicates.get("columns"), "drop_duplicates.columns")
            else:
                self._collect_field(occurrences, entity_name, drop_duplicates, "drop_duplicates")
            self._collect_field(occurrences, entity_name, entity_cfg.get("drop_empty_rows"), "drop_empty_rows")

        return occurrences

    def _collect_field(
        self,
        occurrences: list[_ReferenceOccurrence],
        entity_name: str,
        value: Any,
        field: str,
    ) -> None:
        """Record scalar or list-item references and ignore ordinary values."""
        if isinstance(value, str):
            self._collect_text(occurrences, entity_name, value, field, list_item=False)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str):
                    self._collect_text(occurrences, entity_name, item, f"{field}[{index}]", list_item=True)

    @staticmethod
    def _collect_text(occurrences: list[_ReferenceOccurrence], entity_name: str, text: str, field: str, *, list_item: bool) -> None:
        """Record text only when it contains a reference directive."""
        if _VALUE_DIRECTIVE not in text:
            return

        normalized = text.strip()
        if "+" in normalized:
            tokens = split_reference_expression(normalized)
            if tokens is not None and not any(token.startswith(_VALUE_DIRECTIVE) for token in tokens):
                return
            occurrences.append(_ReferenceOccurrence(entity_name, field, text, list_item, expression=True))
            return

        if normalized.startswith(_VALUE_DIRECTIVE):
            occurrences.append(_ReferenceOccurrence(entity_name, field, text, list_item, expression=False))
        else:
            occurrences.append(_ReferenceOccurrence(entity_name, field, text, list_item, expression=True))

    def _validate_simple_reference(self, snapshot: Project, occurrence: _ReferenceOccurrence) -> list[ValidationError]:
        """Resolve one simple path and require a list containing only strings."""
        path = occurrence.text.strip()[len(_VALUE_DIRECTIVE) :].strip()
        if not path:
            return [self._error(occurrence, "COLUMN_REFERENCE_MISSING_PATH", "the reference path is empty")]

        try:
            value = self._resolve(snapshot, path)
        except RequestedReferenceResolutionError as exc:
            return [self._resolution_error(occurrence, exc)]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return [self._error(occurrence, "COLUMN_REFERENCE_DEPENDENCY_FAILURE", f"the reference could not be checked: {exc}")]

        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return [self._error(occurrence, "COLUMN_REFERENCE_WRONG_TYPE", "the reference must resolve to a list of strings")]
        return []

    def _validate_expression(
        self,
        snapshot: Project,
        occurrence: _ReferenceOccurrence,
        project_cfg: dict[str, Any],
        source_path: str | None,
    ) -> list[ValidationError]:
        """Check each path operand, then check the expression in its saved storage form."""
        tokens = split_reference_expression(occurrence.text.strip())
        if tokens is None:
            return [self._error(occurrence, "COLUMN_REFERENCE_EXPRESSION_INVALID", "the reference expression is malformed or unsupported")]

        operand_errors: list[ValidationError] = []
        for token in tokens:
            if not token.startswith(_VALUE_DIRECTIVE):
                continue
            path = token[len(_VALUE_DIRECTIVE) :].strip()
            try:
                self._resolve(snapshot, path)
            except RequestedReferenceResolutionError as exc:
                operand_errors.append(self._resolution_error(occurrence, exc, path=path))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                operand_errors.append(
                    self._error(
                        occurrence,
                        "COLUMN_REFERENCE_DEPENDENCY_FAILURE",
                        f"operand '{path}' could not be checked: {exc}",
                    )
                )

        if operand_errors:
            return operand_errors

        expression_snapshot, temporary_path = self._expression_snapshot(project_cfg, source_path, occurrence)
        try:
            value = self._resolve(expression_snapshot, temporary_path)
        except RequestedReferenceResolutionError as exc:
            return [self._resolution_error(occurrence, exc)]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return [self._error(occurrence, "COLUMN_REFERENCE_DEPENDENCY_FAILURE", f"the expression could not be checked: {exc}")]

        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return [self._error(occurrence, "COLUMN_REFERENCE_WRONG_TYPE", "the expression must resolve to a list of strings")]
        return []

    @staticmethod
    def _make_snapshot(project_cfg: dict[str, Any], source_path: str | None) -> Project:
        """Copy raw entities and options into a mapper-compatible project model."""
        raw_entities = project_cfg.get("entities")
        entities = (
            {
                entity_name: copy.deepcopy(entity_cfg)
                for entity_name, entity_cfg in raw_entities.items()
                if isinstance(raw_entities, dict) and isinstance(entity_name, str) and isinstance(entity_cfg, dict)
            }
            if isinstance(raw_entities, dict)
            else {}
        )
        for entity_cfg in entities.values():
            foreign_keys = entity_cfg.get("foreign_keys")
            if isinstance(foreign_keys, dict):
                entity_cfg["foreign_keys"] = {
                    foreign_key_name: foreign_key
                    for foreign_key_name, foreign_key in foreign_keys.items()
                    if isinstance(foreign_key, dict) and "entity" in foreign_key
                }

        metadata = project_cfg.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        saved_path = source_path or metadata.get("file_path")
        if not isinstance(saved_path, str):
            saved_path = None
        project_name = metadata.get("name")
        if not isinstance(project_name, str) or not project_name:
            project_name = "column_reference_validation"

        options = project_cfg.get("options")
        options = copy.deepcopy(options) if isinstance(options, dict) else {}
        task_list = project_cfg.get("task_list")
        task_list = copy.deepcopy(task_list) if isinstance(task_list, dict) else None
        return Project(
            metadata=ProjectMetadata(name=project_name, file_path=saved_path, entity_count=len(entities)),
            entities=entities,
            options=options,
            task_list=task_list,
        )

    def _expression_snapshot(
        self, project_cfg: dict[str, Any], source_path: str | None, occurrence: _ReferenceOccurrence
    ) -> tuple[Project, str]:
        """Place one expression under a fresh options key without changing the source project."""
        expression_cfg = copy.deepcopy(project_cfg)
        options = expression_cfg.get("options")
        if not isinstance(options, dict):
            options = {}
            expression_cfg["options"] = options

        key = "__column_reference_expression_check__"
        suffix = 1
        while key in options:
            key = f"__column_reference_expression_check_{suffix}__"
            suffix += 1
        options[key] = [occurrence.text] if occurrence.list_item else occurrence.text
        return self._make_snapshot(expression_cfg, source_path), f"options.{key}"

    @staticmethod
    def _resolve(snapshot: Project, path: str) -> Any:
        """Resolve one path through the mapper's scoped resolution mode."""
        core_project = ProjectMapper.to_core(snapshot, requested_reference_path=path)
        return dotget(core_project.cfg, path)

    @staticmethod
    def _resolution_error(
        occurrence: _ReferenceOccurrence, error: RequestedReferenceResolutionError, *, path: str | None = None
    ) -> ValidationError:
        """Map a scoped mapper failure to the saved-project validation code."""
        code = _RESOLUTION_ERROR_CODES.get(error.reason_code, "COLUMN_REFERENCE_DEPENDENCY_FAILURE")
        details = f"path '{path}' could not be resolved: {error}" if path else str(error)
        return ColumnListReferenceValidationService._error(occurrence, code, details)

    @staticmethod
    def _error(occurrence: _ReferenceOccurrence, code: str, details: str) -> ValidationError:
        """Build a structural error that retains the saved path or expression text."""
        return ValidationError(
            severity="error",
            entity=occurrence.entity,
            field=occurrence.field,
            message=f"Saved reference {occurrence.text!r}: {details.rstrip('.')}.",
            code=code,
            category=ValidationCategory.STRUCTURAL,
        )
