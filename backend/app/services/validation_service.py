"""Validation service for configuration validation."""

from typing import Any, Literal

from loguru import logger

from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.config_service import ConfigurationService, get_config_service
from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.validators.data_validators import DataValidationService
from src.specifications import CompositeConfigSpecification, SpecificationIssue


class ValidationService:
    """Service for validating configurations using existing specifications."""

    def __init__(self) -> None:
        """Initialize validation service."""
        # Import here to avoid circular dependencies and ensure src is in path

        # Get the project root (backend parent is project root)
        # project_root = Path(__file__).parent.parent.parent.parent

        # # Add both project root and src to path (for src.* imports within specifications.py)
        # project_root_str = str(project_root)
        # src_path = str(project_root / "src")

        # if project_root_str not in sys.path:
        #     sys.path.insert(0, project_root_str)
        # if src_path not in sys.path:
        #     sys.path.insert(0, src_path)

        # Import after path is set

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

        config_service: ConfigurationService = get_config_service()
        shapeshift_service: ShapeShiftService = ShapeShiftService(config_service)
        data_validator: DataValidationService = DataValidationService(shapeshift_service)

        errors_list: list[ValidationError] = await data_validator.validate_configuration(config_name, entity_names)

        errors: list[ValidationError] = [e for e in errors_list if e.severity == "error"]
        warnings: list[ValidationError] = [e for e in errors_list if e.severity == "warning"]
        info: list[ValidationError] = [e for e in errors_list if e.severity == "info"]

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

        is_valid: bool = self.validator.is_satisfied_by(config_data)

        result = ValidationResult(
            is_valid=is_valid,
            errors=[self._map_issue(error) for error in self.validator.errors],
            warnings=[self._map_issue(warning) for warning in self.validator.warnings],
            error_count=len(self.validator.errors),
            warning_count=len(self.validator.warnings),
        )

        if is_valid:
            logger.info("Configuration validation passed")
        else:
            logger.warning(f"Configuration validation failed with {len(self.validator.errors)} error(s)")

        return result

    def _map_issue(self, issue: SpecificationIssue) -> ValidationError:
        """Parse error message to extract entity and field information."""
        return ValidationError(
            severity=issue.severity,  # type: ignore[arg-type]
            entity=issue.entity_name,
            field=issue.entity_field or issue.column_name,
            message=issue.message,
            code=", ".join(str(v) for k, v in issue.kwargs.items()),
        )

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
        result: ValidationResult = self.validate_configuration(config_data)

        # Filter to only errors/warnings for this entity
        entity_errors: list[ValidationError] = [e for e in result.errors if e.entity == entity_name or e.entity is None]
        entity_warnings: list[ValidationError] = [w for w in result.warnings if w.entity == entity_name or w.entity is None]

        return ValidationResult(is_valid=len(entity_errors) == 0, errors=entity_errors, warnings=entity_warnings)


# Singleton instance
_validation_service: ValidationService | None = None  # pylint: disable=invalid-name


def get_validation_service() -> ValidationService:
    """Get singleton ValidationService instance."""
    global _validation_service  # pylint: disable=global-statement
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
