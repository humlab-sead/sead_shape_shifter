"""Validation service for project validation."""

from typing import Any

from loguru import logger

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.validators.data_validators import DataValidationService
from src.configuration.config import Config
from src.model import ShapeShiftProject
from src.specifications import CompositeProjectSpecification, SpecificationIssue


class ValidationService:
    """Service for validating projects using existing specifications."""

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

    async def validate_project_data(self, project_name: str, entity_names: list[str] | None = None) -> ValidationResult:
        """
        Run data-aware validation on project.

        Args:
            project_name: Project name
            entity_names: Optional list of entity names to validate (None = all)

        Returns:
            ValidationResult with data validation errors and warnings
        """

        logger.debug(f"Running data validation for project: {project_name}")

        project_service: ProjectService = get_project_service()
        shapeshift_service: ShapeShiftService = ShapeShiftService(project_service)
        data_validator: DataValidationService = DataValidationService(shapeshift_service)

        errors_list: list[ValidationError] = await data_validator.validate_project(project_name, entity_names)

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

    def validate_project(self, project_cfg: dict[str, Any], *, source_path: str | None = None) -> ValidationResult:
        """
        Validate project using CompositeConfigSpecification.

        Args:
            project_cfg: Configuration dictionary with entities and options (will be resolved)

        Returns:
            ValidationResult with errors and warnings
        """
        logger.debug("Validating project")

        # Resolve directives before validation (Core layer requirement)
        # Specifications expect fully resolved config

        try:
            project_cfg = Config.resolve_references(project_cfg, source_path=source_path)
        except FileNotFoundError as e:
            # Missing @include file should be reported as a normal validation error,
            # not as a 500 internal server error.
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        severity="error",
                        entity=None,
                        field=None,
                        message=str(e),
                        code="CONFIG_INCLUDE_NOT_FOUND",
                        suggestion="Ensure the referenced include file exists and the path is relative to the project YAML file.",
                    )
                ],
            )

        specification = CompositeProjectSpecification(project_cfg)
        is_valid: bool = specification.is_satisfied_by()

        result = ValidationResult(
            is_valid=is_valid,
            errors=[self._map_issue(error) for error in specification.errors],
            warnings=[self._map_issue(warning) for warning in specification.warnings],
            error_count=len(specification.errors),
            warning_count=len(specification.warnings),
        )

        if is_valid:
            logger.info("Configuration validation passed")
        else:
            error_count = len(specification.errors)
            warning_count = len(specification.warnings)
            parts = []
            if error_count > 0:
                parts.append(f"{error_count} error(s)")
            if warning_count > 0:
                parts.append(f"{warning_count} warning(s)")
            logger.warning(f"Configuration validation failed with {', '.join(parts)}")

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

    def validate_entity(self, project: Project, entity_name: str) -> ValidationResult:
        """
        Validate a single entity within a project.

        Args:
            project: Project object
            entity_name: Name of entity to validate

        Returns:
            ValidationResult with errors and warnings for this entity
        """

        core_project: ShapeShiftProject = ProjectMapper.to_core(project)

        result: ValidationResult = self.validate_project(core_project.cfg)

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
