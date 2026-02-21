"""Validation service for project validation."""

from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

from backend.app.core.config import get_settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.project import Project
from backend.app.models.validation import DataValidationMode, ValidationError, ValidationResult
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.shapeshift_service import ShapeShiftService
from src.configuration.config import Config
from src.model import ShapeShiftProject
from src.specifications import CompositeProjectSpecification, SpecificationIssue
from src.validators.data_validators import ValidationIssue

if TYPE_CHECKING:
    from backend.app.validators.data_validation_orchestrator import DataValidationOrchestrator


class ValidationService:
    """Service for validating projects using existing specifications."""

    def __init__(
        self,
        data_orchestrator_factory: Callable[[], "DataValidationOrchestrator"] | None = None,
    ) -> None:
        """
        Initialize validation service.

        Args:
            data_orchestrator_factory: Optional factory function to create DataValidationOrchestrator.
                                      If None, uses default factory (lazy import to avoid circular dependency).
        """
        self._data_orchestrator_factory = data_orchestrator_factory

    async def validate_project_data(
        self,
        project_name: str,
        entity_names: list[str] | None = None,
        validation_mode: DataValidationMode = DataValidationMode.SAMPLE,
    ) -> ValidationResult:
        """
        Run data-aware validation on project.

        Args:
            project_name: Project name
            entity_names: Optional list of entity names to validate (None = all)
            validation_mode: Validation mode (SAMPLE for preview data, COMPLETE for full normalization)

        Returns:
            ValidationResult with data validation errors and warnings
        """
        use_full_data = validation_mode == DataValidationMode.COMPLETE
        logger.debug(f"Running data validation for project: {project_name} (mode={validation_mode.value})")

        # Load and resolve project (convert directives to concrete values)
        project_service: ProjectService = get_project_service()
        api_project: Project = project_service.load_project(project_name)
        core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Use injected factory or default factory
        if self._data_orchestrator_factory:
            orchestrator = self._data_orchestrator_factory()
        else:
            # Default factory - import here to avoid circular dependency
            from backend.app.validators.data_validation_orchestrator import (  # pylint: disable=import-outside-toplevel
                DataValidationOrchestrator,
                FullDataFetchStrategy,
                PreviewDataFetchStrategy,
            )

            shapeshift_service: ShapeShiftService = ShapeShiftService(project_service)

            # Create appropriate strategy based on use_full_data flag
            if use_full_data:
                fetch_strategy = FullDataFetchStrategy(project_service)
            else:
                fetch_strategy = PreviewDataFetchStrategy(shapeshift_service)

            # Inject strategy into orchestrator
            orchestrator = DataValidationOrchestrator(fetch_strategy=fetch_strategy)

        # Orchestrator returns domain issues - convert to API errors
        issues_list: list[ValidationIssue] = await orchestrator.validate_all_entities(
            core_project=core_project,
            project_name=project_name,
            entity_names=entity_names,
        )

        errors_list: list[ValidationError] = [ValidationMapper.to_api_error(issue) for issue in issues_list]

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
            validation_mode=validation_mode,
        )

        logger.info(f"Data validation completed: {result.error_count} errors, {result.warning_count} warnings")

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
            settings = get_settings()

            project_cfg = Config.resolve_references(
                project_cfg,
                source_path=source_path,
                env_prefix=settings.env_prefix,
                try_without_prefix=True,
            )
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
            error_count: int = len(specification.errors)
            warning_count: int = len(specification.warnings)
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

        result: ValidationResult = self.validate_project(core_project.cfg, source_path=project.filename)

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
