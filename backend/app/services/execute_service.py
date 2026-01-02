"""Service for executing full workflow."""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.state_manager import ApplicationStateManager
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.execute import DispatcherMetadata, ExecuteRequest, ExecuteResult
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from backend.app.services.validation_service import ValidationService
from src.dispatch import Dispatchers
from src.model import ShapeShiftProject
from src.specifications import CompositeProjectSpecification
from src.workflow import workflow


class ExecuteService:
    """Service for executing full Shape Shifter workflow."""

    def __init__(
        self,
        state: ApplicationStateManager | None = None,
        project_service: ProjectService | None = None,
        validation_service: ValidationService | None = None,
    ):
        self.state: ApplicationStateManager = state or ApplicationStateManager()
        self.project_service: ProjectService = project_service or ProjectService()
        self.validation_service: ValidationService = validation_service or ValidationService()

    def get_dispatchers(self) -> list[DispatcherMetadata]:
        """Get list of available dispatchers with metadata."""
        dispatchers = []

        for key, dispatcher_cls in Dispatchers.items.items():
            # Get target_type and description from registry options
            registry_opts: Any | dict[Any, Any] = getattr(dispatcher_cls, "_registry_opts", {})

            dispatchers.append(
                DispatcherMetadata(
                    key=key,
                    target_type=registry_opts.get("target_type", "unknown"),
                    description=registry_opts.get("description", ""),
                )
            )

        return dispatchers

    async def execute_workflow(self, project_name: str, request: ExecuteRequest) -> ExecuteResult:
        """Execute full Shape Shifter workflow.

        Args:
            project_name: Name of project to execute
            request: Execution request parameters

        Returns:
            ExecuteResult with execution details

        Raises:
            ValueError: If dispatcher key is invalid
            Exception: If workflow execution fails
        """
        if request.dispatcher_key not in Dispatchers.items:
            raise ValueError(f"Invalid dispatcher key: {request.dispatcher_key}. " f"Available: {', '.join(Dispatchers.items.keys())}")

        is_satisfied: bool | None = None

        try:
            # Load API project for metadata
            project: Project = self.project_service.load_project(project_name)

            # Load core project using ShapeShiftProject.from_file() to properly resolve @include directives
            if not project.filename:
                raise ValueError(f"Project '{project_name}' has no filename")

            core_project: ShapeShiftProject = ShapeShiftProject.from_file(
                filename=project.filename,
                env_file=".env",  # Config provider handles env file loading
                env_prefix="SEAD_NORMALIZER",
            )

            if request.run_validation:
                is_satisfied = await self._validate_project(core_project)
                if not is_satisfied:
                    return ExecuteResult(
                        success=False,
                        message="Validation failed. Please fix errors before executing workflow.",
                        target=request.target,
                        dispatcher_key=request.dispatcher_key,
                        entity_count=0,
                        validation_passed=False,
                        error_details="Project configuration validation failed",
                    )

            dispatcher_meta: DispatcherMetadata = next(d for d in self.get_dispatchers() if d.key == request.dispatcher_key)
            target = self._resolve_target(request.target, dispatcher_meta.target_type)

            logger.info(f"Executing workflow for project '{project_name}' with dispatcher '{request.dispatcher_key}'")

            await workflow(
                project=core_project,
                target=target,
                translate=request.translate,
                target_type=request.dispatcher_key,
                drop_foreign_keys=request.drop_foreign_keys,
                validate_then_exit=False,
                default_entity=request.default_entity,
                env_file=None,  # Already resolved in project
            )

            entity_count: int = len(core_project.entities)

            logger.info(f"Workflow executed successfully: {entity_count} entities processed")

            return ExecuteResult(
                success=True,
                message=f"Successfully executed workflow with {entity_count} entities",
                target=target,
                dispatcher_key=request.dispatcher_key,
                entity_count=entity_count,
                validation_passed=is_satisfied,
                error_details=None,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Workflow execution failed: {e}")
            return ExecuteResult(
                success=False,
                message=f"Workflow execution failed: {str(e)}",
                target=request.target,
                dispatcher_key=request.dispatcher_key,
                entity_count=0,
                validation_passed=is_satisfied,
                error_details=str(e),
            )

    async def _validate_project(self, project: ShapeShiftProject) -> bool:
        """Run project validation.

        Args:
            project: Project to validate

        Returns:
            True if validation passed, False otherwise
        """
        try:
            specification = CompositeProjectSpecification()
            errors: bool = specification.is_satisfied_by(project.cfg)

            if errors:
                for error in specification.errors:
                    logger.error(f"Configuration error: {error}")
                return False

            logger.info("Configuration validation passed successfully")
            return True

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Validation failed: {e}")
            return False

    def _resolve_target(self, target: str, target_type: str) -> str:
        """Resolve and validate target path.

        Args:
            target: User-provided target path
            target_type: Type of target (file, folder, database)

        Returns:
            Resolved absolute path
        """
        if target_type == "database":
            # Database targets are data source names, return as-is
            return target

        # For file/folder targets, resolve to absolute path
        target_path: Path = Path(target).expanduser().resolve()

        if target_type == "folder":
            # Ensure parent directory exists for folder targets
            target_path.parent.mkdir(parents=True, exist_ok=True)
        elif target_type == "file":
            # Ensure parent directory exists for file targets
            target_path.parent.mkdir(parents=True, exist_ok=True)

        return str(target_path)


_execute_service: ExecuteService | None = None  # pylint: disable=invalid-name


def get_execute_service() -> ExecuteService:
    """Get singleton ExecuteService instance."""
    global _execute_service  # pylint: disable=global-statement
    if _execute_service is None:
        _execute_service = ExecuteService()
    return _execute_service
