"""Validation service for configuration validation."""

from typing import Any
import sys
from pathlib import Path

from loguru import logger

from app.models.validation import ValidationError, ValidationResult
from app.services.config_service import get_config_service
from app.services.preview_service import PreviewService
from app.validators.data_validators import DataValidationService


class ValidationService:
    """Service for validating configurations using existing specifications."""

    def __init__(self) -> None:
        """Initialize validation service."""
        # Import here to avoid circular dependencies and ensure src is in path

        # Get the project root (backend parent is project root)
        project_root = Path(__file__).parent.parent.parent.parent

        # Add both project root and src to path (for src.* imports within specifications.py)
        project_root_str = str(project_root)
        src_path = str(project_root / "src")

        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Import after path is set
        from specifications import CompositeConfigSpecification

        self.validator = CompositeConfigSpecification()

    async def validate_configuration_data(self, config_name: str, entity_names: list[str] | None = None) -> ValidationResult:
        """
        Run data-aware validation on configuration.

        Args:
            config_name: Configuration name
            entity_names: Optional list of entity names to validate (None = all)

        Returns:
            ValidationResult with data validation errors and warnings
        """

        logger.debug(f"Running data validation for configuration: {config_name}")

        config_service = get_config_service()
        preview_service = PreviewService(config_service)
        data_validator = DataValidationService(preview_service)

        # Run data validators
        errors_list = await data_validator.validate_configuration(config_name, entity_names)

        # Separate by severity
        errors = [e for e in errors_list if e.severity == "error"]
        warnings = [e for e in errors_list if e.severity == "warning"]
        info = [e for e in errors_list if e.severity == "info"]

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            error_count=len(errors),
            warning_count=len(warnings),
        )

        logger.info(f"Data validation completed: {result.error_count} errors, " f"{result.warning_count} warnings")

        return result

    def validate_configuration(self, config_data: dict[str, Any]) -> ValidationResult:
        """
        Validate configuration using CompositeConfigSpecification.

        Args:
            config_data: Configuration dictionary with entities and options

        Returns:
            ValidationResult with errors and warnings
        """
        logger.debug("Validating configuration")

        # Run validation
        is_valid = self.validator.is_satisfied_by(config_data)

        # Convert specification errors/warnings to ValidationError objects
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        # Parse errors
        for error_msg in self.validator.errors:
            validation_error = self._parse_error_message(error_msg, severity="error")
            errors.append(validation_error)

        # Parse warnings
        for warning_msg in self.validator.warnings:
            validation_warning = self._parse_error_message(warning_msg, severity="warning")
            warnings.append(validation_warning)

        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            error_count=len(errors),
            warning_count=len(warnings),
        )

        if is_valid:
            logger.info("Configuration validation passed")
        else:
            logger.warning(f"Configuration validation failed with {len(errors)} error(s)")

        return result

    def _parse_error_message(self, message: str, severity: str = "error") -> ValidationError:
        """
        Parse error message to extract entity and field information.

        Error messages typically follow patterns like:
        - "Entity 'sample': references non-existent entity 'missing' in foreign key"
        - "Configuration must contain 'entities' section"
        - "Entity 'sample': field 'surrogate_id' must end with '_id'"

        Args:
            message: Error message from specification
            severity: Severity level (error, warning, info)

        Returns:
            ValidationError object
        """
        entity = None
        field = None
        code = None

        # Try to extract entity name (pattern: Entity 'name':)
        if "Entity '" in message:
            start = message.find("Entity '") + 8
            end = message.find("'", start)
            if end > start:
                entity = message[start:end]

        # Try to extract field name (pattern: field 'name')
        if "field '" in message:
            start = message.find("field '") + 7
            end = message.find("'", start)
            if end > start:
                field = message[start:end]

        # Determine error code based on message content
        if "non-existent" in message:
            code = "missing_reference"
        elif "circular" in message.lower():
            code = "circular_dependency"
        elif "required" in message.lower() or "must contain" in message:
            code = "required_field"
        elif "foreign key" in message.lower():
            code = "foreign_key_error"
        elif "data source" in message.lower():
            code = "data_source_error"
        elif "duplicate" in message.lower():
            code = "duplicate_error"
        else:
            code = "validation_error"

        return ValidationError(severity=severity, entity=entity, field=field, message=message, code=code)

    def validate_entity(self, config: Any, entity_name: str) -> ValidationResult:
        """
        Validate a single entity within a configuration.

        Args:
            config: Configuration object (will be converted to dict)
            entity_name: Name of entity to validate

        Returns:
            ValidationResult with errors and warnings for this entity
        """
        # Convert Configuration to dict if needed
        if hasattr(config, "model_dump"):
            config_data = config.model_dump(exclude_none=True, mode="json")
        elif isinstance(config, dict):
            config_data = config
        else:
            config_data = {"entities": config.entities, "options": config.options}

        # Validate full configuration
        result = self.validate_configuration(config_data)

        # Filter to only errors/warnings for this entity
        entity_errors = [e for e in result.errors if e.entity == entity_name or e.entity is None]
        entity_warnings = [w for w in result.warnings if w.entity == entity_name or w.entity is None]

        return ValidationResult(is_valid=len(entity_errors) == 0, errors=entity_errors, warnings=entity_warnings)


# Singleton instance
_validation_service: ValidationService | None = None


def get_validation_service() -> ValidationService:
    """Get singleton ValidationService instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
