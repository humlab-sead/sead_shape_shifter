"""Read and check a project's fixed SEAD data provider row.

A project bound to a provider-schema pair declares one fixed ``data_provider`` entity.
That row carries the operator-reconciled SEAD ``data_provider_id`` and the project's
``data_provider_code``. The value cannot come from the registry, the request, or the
submitted workbook, because it identifies one existing SEAD provider row.

This service has two entry points:

- ``fixed_row_errors`` checks a resolved project configuration dictionary and returns
  field-specific validation errors without reading the target database;
- ``require_fixed_row`` returns the checked row from a mapped project, and
  ``build_trusted_context`` combines the registered scope, the fixed row, and the ordered
  business keys into the backend-owned context used by Change Request ingestion.

It never writes project files, never creates provider rows, and never queries SEAD.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.app.exceptions import ConfigurationError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.validation import ValidationError
from backend.app.services.data_provider_service import DataProviderRegistryError, DataProviderService
from backend.app.services.project_provider_binding_service import ProjectProviderBindingService
from ingesters.sead_change_request.contracts import TrustedProjectContext
from src.model import ShapeShiftProject, TableConfig
from src.types.fixed_entity_types import build_fixed_entity_full_columns

FIXED_PROVIDER_ENTITY = "data_provider"
FIXED_PROVIDER_PUBLIC_ID = "data_provider_id"
FIXED_PROVIDER_KEY = "data_provider_code"
FIXED_PROVIDER_FIELD_PREFIX = f"entities.{FIXED_PROVIDER_ENTITY}"

_PROVIDER_BINDING_FIELD = "metadata.data_provider_code"


class ProjectDataProviderError(ConfigurationError):
    """Raised when a project's fixed data provider row cannot supply a usable ID."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, specification="ProjectDataProviderSpecification")


@dataclass(frozen=True, slots=True)
class FixedProviderRow:
    """The operator-reconciled SEAD provider row declared by one project."""

    data_provider_id: int
    data_provider_code: str


class ProjectDataProviderService:
    """Check the fixed provider row and build the trusted Change Request context."""

    def __init__(
        self,
        provider_service: DataProviderService | None = None,
        binding_service: ProjectProviderBindingService | None = None,
    ) -> None:
        self.provider_service = provider_service or DataProviderService(_provider_registry_dir())
        self.binding_service = binding_service or ProjectProviderBindingService(self.provider_service)

    # ------------------------------------------------------------------
    # Structural checks (no target-database access)
    # ------------------------------------------------------------------

    def fixed_row_errors(self, project_cfg: Mapping[str, Any] | None) -> list[ValidationError]:
        """Return field-specific errors for a missing or unusable fixed provider row.

        Expects an already resolved configuration dictionary. Returns an empty list when
        the project contains one valid fixed row whose code matches its metadata.
        """
        config = project_cfg if isinstance(project_cfg, Mapping) else {}
        entities = config.get("entities")
        entity = entities.get(FIXED_PROVIDER_ENTITY) if isinstance(entities, Mapping) else None

        if not isinstance(entity, Mapping):
            return [
                self._error(
                    f"Project requires a fixed '{FIXED_PROVIDER_ENTITY}' entity with exactly one row.",
                    field=FIXED_PROVIDER_FIELD_PREFIX,
                )
            ]

        errors = self._declaration_errors(entity)
        if errors:
            return errors

        rows = self._provider_rows(entity)
        if rows is None:
            return [self._error("Fixed 'data_provider' values must be a list of rows.", field=FIXED_PROVIDER_FIELD_PREFIX)]
        if len(rows) != 1:
            return [
                self._error(
                    f"Fixed '{FIXED_PROVIDER_ENTITY}' entity must declare exactly one row; found {len(rows)}.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.values",
                )
            ]

        row = rows[0]
        data_provider_id = _positive_int_or_none(row.get(FIXED_PROVIDER_PUBLIC_ID))
        if data_provider_id is None:
            return [
                self._error(
                    f"Fixed '{FIXED_PROVIDER_ENTITY}' row requires a positive integer '{FIXED_PROVIDER_PUBLIC_ID}'.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.{FIXED_PROVIDER_PUBLIC_ID}",
                )
            ]

        code = row.get(FIXED_PROVIDER_KEY)
        if not isinstance(code, str) or not code.strip():
            return [
                self._error(
                    f"Fixed '{FIXED_PROVIDER_ENTITY}' row requires a nonblank '{FIXED_PROVIDER_KEY}'.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.{FIXED_PROVIDER_KEY}",
                )
            ]

        metadata = config.get("metadata")
        bound_code = metadata.get("data_provider_code") if isinstance(metadata, Mapping) else None
        if not isinstance(bound_code, str) or bound_code.strip() != code.strip():
            return [
                self._error(
                    f"Fixed '{FIXED_PROVIDER_ENTITY}' row code '{code.strip()}' must match the project data provider code "
                    f"'{bound_code if isinstance(bound_code, str) else ''}'.",
                    field=_PROVIDER_BINDING_FIELD,
                )
            ]

        return []

    def _declaration_errors(self, entity: Mapping[str, Any]) -> list[ValidationError]:
        """Return declaration errors for the fixed provider entity shape."""
        errors: list[ValidationError] = []
        if entity.get("type") != "fixed":
            errors.append(
                self._error(
                    f"'{FIXED_PROVIDER_ENTITY}' must declare 'type: fixed'.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.type",
                )
            )
        if entity.get("public_id") != FIXED_PROVIDER_PUBLIC_ID:
            errors.append(
                self._error(
                    f"'{FIXED_PROVIDER_ENTITY}' must declare 'public_id: {FIXED_PROVIDER_PUBLIC_ID}'.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.public_id",
                )
            )
        keys = entity.get("keys")
        if not isinstance(keys, list) or [str(key) for key in keys] != [FIXED_PROVIDER_KEY]:
            errors.append(
                self._error(
                    f"'{FIXED_PROVIDER_ENTITY}' must declare 'keys: [{FIXED_PROVIDER_KEY}]'.",
                    field=f"{FIXED_PROVIDER_FIELD_PREFIX}.keys",
                )
            )
        return errors

    def _provider_rows(self, entity: Mapping[str, Any]) -> list[dict[str, Any]] | None:
        """Return provider rows as mappings, or None when the values shape is unusable."""
        values = entity.get("values")
        if not isinstance(values, list):
            return None

        if values and isinstance(values[0], Mapping):
            return [dict(row) for row in values if isinstance(row, Mapping)]

        columns = _declared_columns(entity)
        if columns is None:
            return None
        return [_row_from_positional_values(row, columns) for row in values]

    # ------------------------------------------------------------------
    # Mapped project reads
    # ------------------------------------------------------------------

    def require_fixed_row(self, project: ShapeShiftProject, expected_code: str) -> FixedProviderRow:
        """Return the project's checked fixed provider row.

        Raises:
            ProjectDataProviderError: The project has no usable single fixed row, or the
                row's code does not match the saved provider code.
        """
        if not project.has_table(FIXED_PROVIDER_ENTITY):
            raise ProjectDataProviderError(f"Project requires a fixed '{FIXED_PROVIDER_ENTITY}' entity with exactly one row.")

        table: TableConfig = project.get_table(FIXED_PROVIDER_ENTITY)
        if table.type != "fixed":
            raise ProjectDataProviderError(f"Entity '{FIXED_PROVIDER_ENTITY}' must declare 'type: fixed'.")
        if table.public_id != FIXED_PROVIDER_PUBLIC_ID:
            raise ProjectDataProviderError(f"Entity '{FIXED_PROVIDER_ENTITY}' must declare 'public_id: {FIXED_PROVIDER_PUBLIC_ID}'.")
        if table.safe_keys != [FIXED_PROVIDER_KEY]:
            raise ProjectDataProviderError(f"Entity '{FIXED_PROVIDER_ENTITY}' must declare 'keys: [{FIXED_PROVIDER_KEY}]'.")

        rows = self._provider_rows(dict(table.entity_cfg))
        if rows is None or len(rows) != 1:
            found = "an unusable" if rows is None else f"{len(rows)}"
            raise ProjectDataProviderError(f"Fixed '{FIXED_PROVIDER_ENTITY}' entity must declare exactly one row; found {found}.")

        row = rows[0]
        data_provider_id = _positive_int_or_none(row.get(FIXED_PROVIDER_PUBLIC_ID))
        if data_provider_id is None:
            raise ProjectDataProviderError(f"Fixed '{FIXED_PROVIDER_ENTITY}' row requires a positive integer '{FIXED_PROVIDER_PUBLIC_ID}'.")

        code = row.get(FIXED_PROVIDER_KEY)
        if not isinstance(code, str) or not code.strip():
            raise ProjectDataProviderError(f"Fixed '{FIXED_PROVIDER_ENTITY}' row requires a nonblank '{FIXED_PROVIDER_KEY}'.")
        if code.strip() != expected_code:
            raise ProjectDataProviderError(
                f"Fixed '{FIXED_PROVIDER_ENTITY}' row code '{code.strip()}' must match the project data provider code "
                f"'{expected_code}'."
            )

        return FixedProviderRow(data_provider_id=data_provider_id, data_provider_code=code.strip())

    # ------------------------------------------------------------------
    # Trusted Change Request context
    # ------------------------------------------------------------------

    def build_trusted_context(self, project: Project) -> TrustedProjectContext:
        """Build the backend-owned Change Request context from one authorized saved project.

        Raises:
            ProjectDataProviderError: The saved pair is missing, unregistered, or has no
                usable fixed provider row.
        """
        if project.metadata is None:
            raise ProjectDataProviderError("Project metadata is required to bind a provider-schema pair.")

        provider_code, provider_schema = self.binding_service.require_registered_pair(
            {
                "data_provider_code": project.metadata.data_provider_code,
                "provider_schema": project.metadata.provider_schema,
            }
        )
        scope_name = self._scope_name(provider_code, provider_schema)

        core_project: ShapeShiftProject = ProjectMapper.to_core(project)
        fixed_row = self.require_fixed_row(core_project, provider_code)
        business_keys = {entity_name: tuple(table.safe_keys) for entity_name, table in core_project.tables.items()}

        return TrustedProjectContext(
            project_name=project.metadata.name,
            provider_code=provider_code,
            provider_schema=provider_schema,
            scope_name=scope_name,
            data_provider_id=fixed_row.data_provider_id,
            business_keys=business_keys,
        )

    def _scope_name(self, provider_code: str, provider_schema: str) -> str:
        """Return the registered scope name for one provider-schema pair."""
        try:
            registered = self.provider_service.get_scope(provider_code, provider_schema)
        except DataProviderRegistryError as exc:
            raise ProjectDataProviderError("Data provider registry is unavailable") from exc
        if registered is None:
            raise ProjectDataProviderError(f"Provider-schema pair '{provider_code}' / '{provider_schema}' is not registered.")
        return registered.scope_name

    @staticmethod
    def _error(message: str, *, field: str) -> ValidationError:
        return ValidationError(
            severity="error",
            entity=FIXED_PROVIDER_ENTITY,
            field=field,
            message=message,
            code="PROJECT_DATA_PROVIDER_INVALID",
        )


def _provider_registry_dir():
    """Return the configured provider registry directory."""
    from backend.app.core.config import settings  # pylint: disable=import-outside-toplevel

    return settings.global_data_provider_dir


def _declared_columns(entity: Mapping[str, Any]) -> list[str] | None:
    """Return the effective positional columns for a fixed entity's list rows."""
    columns = entity.get("columns")
    if not isinstance(columns, list) or not columns:
        return None
    public_id = entity.get("public_id")
    declared = [str(column) for column in columns]
    full_columns = build_fixed_entity_full_columns(declared, str(public_id) if isinstance(public_id, str) else None)
    values = entity.get("values")
    row_length = len(values[0]) if isinstance(values, list) and values and isinstance(values[0], list) else None
    if row_length == len(declared):
        return declared
    return full_columns


def _row_from_positional_values(row: Any, columns: list[str]) -> dict[str, Any]:
    """Map one positional fixed-entity row onto its column names."""
    if not isinstance(row, list):
        return {}
    return {column: row[index] for index, column in enumerate(columns) if index < len(row)}


def _positive_int_or_none(value: Any) -> int | None:
    """Return a positive integer ID or None when the value is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None
