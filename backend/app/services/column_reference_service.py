"""Resolve draft-aware @value references and complete list-valued entity properties."""

import copy
import re
from typing import Any

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.column_reference import (
    ColumnReferenceCompleteResponse,
    ColumnReferenceFailureCode,
    ColumnReferenceResolveResponse,
)
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from src.configuration.resolve import RequestedReferenceResolutionError

_SIMPLE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_-]+(?:[.:][A-Za-z0-9_-]+)*$")
_REASON_MESSAGES = {
    ColumnReferenceFailureCode.MALFORMED_INPUT: "Enter a complete simple @value reference path.",
    ColumnReferenceFailureCode.MISSING_PATH: "The referenced path does not exist in the current project draft.",
    ColumnReferenceFailureCode.CIRCULAR_REFERENCE: "The reference depends on a circular @value reference.",
    ColumnReferenceFailureCode.DEPENDENCY_FAILURE: "A file or nested directive required by this reference could not be resolved.",
    ColumnReferenceFailureCode.WRONG_RESULT_TYPE: "The reference must resolve to a list containing only column names.",
}


class ColumnReferenceService:
    """Check one reference or suggest eligible entity properties for a project draft."""

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def resolve_reference(
        self,
        project_name: str,
        entity_name: str,
        entity_draft: dict[str, Any],
        directive: str,
    ) -> ColumnReferenceResolveResponse:
        """Resolve a complete simple directive and return columns or one local reason."""
        path = self._parse_directive(directive)
        if path is None:
            return self._unresolved(directive, None, ColumnReferenceFailureCode.MALFORMED_INPUT)

        project = self._load_draft(project_name, entity_name, entity_draft)
        try:
            value = self._resolve_path(project, path)
        except RequestedReferenceResolutionError as exc:
            reason_code = ColumnReferenceFailureCode(exc.reason_code)
            return self._unresolved(directive, path, reason_code)

        if not self._is_column_list(value):
            return self._unresolved(directive, path, ColumnReferenceFailureCode.WRONG_RESULT_TYPE)

        return ColumnReferenceResolveResponse(
            directive=directive,
            path=path,
            status="resolved",
            columns=value,
        )

    def complete_references(
        self,
        project_name: str,
        entity_name: str,
        entity_draft: dict[str, Any],
        prefix: str,
        edited_field_path: str | None = None,
        preferred_entity: str | None = None,
    ) -> ColumnReferenceCompleteResponse:
        """Return progressively filtered @value candidates for list-valued properties."""
        normalized_prefix = prefix.strip()
        if not normalized_prefix.startswith("@value"):
            return ColumnReferenceCompleteResponse(candidates=[])

        body = normalized_prefix[len("@value") :].strip()
        if body.startswith(":"):
            body = body[1:].strip()
        if not body or "entities".startswith(body):
            return ColumnReferenceCompleteResponse(candidates=["@value: entities."])
        if not body.startswith("entities."):
            return ColumnReferenceCompleteResponse(candidates=[])

        remainder = body[len("entities.") :]
        project = self._load_draft(project_name, entity_name, entity_draft)
        entity_names = self._ordered_entity_names(project, preferred_entity)
        if "." not in remainder:
            candidates = [f"@value: entities.{name}." for name in entity_names if name.startswith(remainder)]
            return ColumnReferenceCompleteResponse(candidates=candidates)

        selected_entity, property_prefix = remainder.split(".", maxsplit=1)
        if selected_entity not in project.entities:
            return ColumnReferenceCompleteResponse(candidates=[])

        edited_path = self._edited_path(edited_field_path)
        entity_value = project.entities[selected_entity]
        if not isinstance(entity_value, dict):
            return ColumnReferenceCompleteResponse(candidates=[])

        candidate_paths: list[str] = []
        for property_name in sorted(entity_value):
            if not property_name.startswith(property_prefix):
                continue
            path = f"entities.{selected_entity}.{property_name}"
            if path == edited_path:
                continue
            # Only text and list properties can resolve to a column list, so skip
            # the mapping and resolution work for the remaining shapes.
            if not isinstance(entity_value[property_name], (str, list)):
                continue
            candidate_paths.append(path)

        resolved_values = ProjectMapper.resolve_reference_values(project, candidate_paths)
        candidates: list[str] = [f"@value: {path}" for path in candidate_paths if self._is_column_list(resolved_values.get(path))]

        return ColumnReferenceCompleteResponse(candidates=candidates)

    @staticmethod
    def _is_column_list(value: Any) -> bool:
        """Return True when the resolved value is a list holding only strings."""
        return isinstance(value, list) and all(isinstance(column, str) for column in value)

    @staticmethod
    def _parse_directive(directive: str) -> str | None:
        """Return a simple path from a complete @value directive."""
        normalized = directive.strip()
        if not normalized.startswith("@value:"):
            return None
        path = normalized[len("@value:") :].strip()
        return path if path and _SIMPLE_PATH_PATTERN.fullmatch(path) else None

    def _load_draft(self, project_name: str, entity_name: str, entity_draft: dict[str, Any]) -> Project:
        """Load an isolated project copy and replace one entity with its unsaved values."""
        project = self.project_service.load_project(project_name).model_copy(deep=True)
        project.entities[entity_name] = copy.deepcopy(entity_draft)
        return project

    @staticmethod
    def _resolve_path(project: Project, path: str) -> Any:
        """Resolve one path through the mapper's editor-only resolution mode."""
        value = ProjectMapper.resolve_reference_values(project, [path])[path]
        if isinstance(value, RequestedReferenceResolutionError):
            raise value
        return value

    @staticmethod
    def _ordered_entity_names(project: Project, preferred_entity: str | None) -> list[str]:
        """Sort entity names and move the preferred entity to the first position."""
        names = sorted(project.entities)
        if preferred_entity in names:
            names.remove(preferred_entity)
            names.insert(0, preferred_entity)
        return names

    @staticmethod
    def _edited_path(edited_field_path: str | None) -> str | None:
        """Normalize an edited path supplied either bare or as a simple directive."""
        if edited_field_path is None:
            return None
        normalized = edited_field_path.strip()
        if normalized.startswith("@value:"):
            return ColumnReferenceService._parse_directive(normalized)
        return normalized

    @staticmethod
    def _unresolved(directive: str, path: str | None, reason_code: ColumnReferenceFailureCode) -> ColumnReferenceResolveResponse:
        """Build a failed result without exposing an exception or partial columns."""
        return ColumnReferenceResolveResponse(
            directive=directive,
            path=path,
            status="unresolved",
            reason_code=reason_code,
            reason=_REASON_MESSAGES[reason_code],
        )
