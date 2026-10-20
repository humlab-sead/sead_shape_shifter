"""Validate and preserve provider-schema assignments in project metadata."""

from collections.abc import Mapping
from typing import Any

from loguru import logger

from backend.app.core.config import settings
from backend.app.exceptions import ConfigurationError
from backend.app.models.validation import ValidationError
from backend.app.services.data_provider_service import DataProviderRegistryError, DataProviderService

PROVIDER_CODE_FIELD = "metadata.data_provider_code"
PROVIDER_SCHEMA_FIELD = "metadata.provider_schema"


class ProjectProviderBindingError(ConfigurationError):
    """Raised when a project write would create or change an invalid provider pair."""

    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = errors
        super().__init__(
            message="; ".join(f"{error.field}: {error.message}" for error in errors),
            specification="ProjectProviderBindingSpecification",
        )


class ProjectProviderRegistryUnavailable(RuntimeError):
    """Raised when the local provider registry cannot be read safely."""


class ProjectProviderBindingService:
    """Check project provider pairs against the local reviewed registry."""

    def __init__(self, provider_service: DataProviderService | None = None) -> None:
        self.provider_service = provider_service or DataProviderService(settings.global_data_provider_dir)

    def validation_errors(self, metadata: object) -> list[ValidationError]:
        """Return field-specific errors when metadata does not contain a registered pair."""
        values = metadata if isinstance(metadata, Mapping) else {}
        provider_code = values.get("data_provider_code")
        provider_schema = values.get("provider_schema")

        errors: list[ValidationError] = []
        self._append_text_error(errors, provider_code, PROVIDER_CODE_FIELD, "data provider code")
        self._append_text_error(errors, provider_schema, PROVIDER_SCHEMA_FIELD, "provider schema")
        if errors:
            return errors

        assert isinstance(provider_code, str)
        assert isinstance(provider_schema, str)
        try:
            registered = self.provider_service.get_scope(provider_code, provider_schema)
        except DataProviderRegistryError as exc:
            logger.error("Project provider registry is unavailable: {}", exc)
            raise ProjectProviderRegistryUnavailable("Data provider registry is unavailable") from exc

        if registered is None:
            message = f"Provider-schema pair '{provider_code}' / '{provider_schema}' is not registered."
            return [
                self._field_error(PROVIDER_CODE_FIELD, message),
                self._field_error(PROVIDER_SCHEMA_FIELD, message),
            ]
        return []

    def require_registered_pair(self, metadata: object) -> tuple[str, str]:
        """Return the registered pair or raise an error suitable for a rejected write."""
        errors = self.validation_errors(metadata)
        if errors:
            raise ProjectProviderBindingError(errors)
        values = metadata
        assert isinstance(values, Mapping)
        provider_code = values["data_provider_code"]
        provider_schema = values["provider_schema"]
        assert isinstance(provider_code, str)
        assert isinstance(provider_schema, str)
        return provider_code, provider_schema

    def validate_write(self, current_metadata: object | None, candidate_metadata: object) -> None:
        """Reject writes that alter a binding or introduce an incomplete initial pair."""
        current = current_metadata if isinstance(current_metadata, Mapping) else {}
        candidate = candidate_metadata if isinstance(candidate_metadata, Mapping) else {}
        current_pair = (current.get("data_provider_code"), current.get("provider_schema"))
        candidate_pair = (candidate.get("data_provider_code"), candidate.get("provider_schema"))

        if current_metadata is None:
            self.require_registered_pair(candidate)
            return

        current_is_bound = self._is_complete_pair(current_pair)
        candidate_is_bound = self._is_complete_pair(candidate_pair)

        if current_is_bound:
            current_errors = self.validation_errors(current)
            if current_errors:
                raise ProjectProviderBindingError(current_errors)
            if candidate_pair != current_pair:
                errors = [
                    self._field_error(
                        field,
                        f"An assigned provider-schema pair cannot be changed or removed; keep '{current_pair[index]}'.",
                    )
                    for index, field in enumerate((PROVIDER_CODE_FIELD, PROVIDER_SCHEMA_FIELD))
                    if candidate_pair[index] != current_pair[index]
                ]
                raise ProjectProviderBindingError(errors)
            return

        if candidate_pair == current_pair:
            return
        if candidate_is_bound:
            self.require_registered_pair(candidate)
            return

        errors: list[ValidationError] = []
        self._append_text_error(errors, candidate_pair[0], PROVIDER_CODE_FIELD, "data provider code")
        self._append_text_error(errors, candidate_pair[1], PROVIDER_SCHEMA_FIELD, "provider schema")
        if not errors:
            errors = [
                self._field_error(PROVIDER_CODE_FIELD, "Assign both a registered data provider code and provider schema together."),
                self._field_error(PROVIDER_SCHEMA_FIELD, "Assign both a registered data provider code and provider schema together."),
            ]
        raise ProjectProviderBindingError(errors)

    @staticmethod
    def _is_complete_pair(pair: tuple[Any, Any]) -> bool:
        """Return whether both pair values are nonblank strings."""
        return all(isinstance(value, str) and bool(value.strip()) for value in pair)

    @classmethod
    def _append_text_error(
        cls,
        errors: list[ValidationError],
        value: Any,
        field: str,
        label: str,
    ) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append(cls._field_error(field, f"A nonblank {label} is required."))

    @staticmethod
    def _field_error(field: str, message: str) -> ValidationError:
        return ValidationError(
            severity="error",
            entity=None,
            field=field,
            message=message,
            code="PROJECT_PROVIDER_BINDING_INVALID",
        )
