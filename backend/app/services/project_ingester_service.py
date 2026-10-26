"""Compose project validation and table-based ingester operations."""

from typing import Any

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from backend.app.authorization.models import Action, AuthorizedResource, ResourceType
from backend.app.core.config import Settings, get_settings
from backend.app.exceptions import ConfigurationError
from backend.app.ingesters.protocol import IngesterConfig, IngestionResult, TableSourceIngester, ValidationResult
from backend.app.ingesters.registry import get_ingester_registry
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.ingester import IngestResponse, ProjectIngesterRequest, ValidateResponse
from backend.app.models.project import Project
from backend.app.services.ingester_runtime import inject_ingester_database_dependencies, inject_ingester_runtime_dependencies
from backend.app.services.project_data_provider_service import ProjectDataProviderError, ProjectDataProviderService
from backend.app.services.project_service import ProjectService, get_project_service
from ingesters.sead_change_request.input_resolution import TRUSTED_PROJECT_CONTEXT_KEY
from src.specifications import CompositeProjectSpecification
from src.target_model.conformance import ConformanceIssue, ForeignKeyValueSourceConformanceValidator
from src.target_model.models import TargetModel
from src.workflow import normalize_project


class ProjectIngesterService:
    """Validate a saved project and pass its normalized tables to a table-capable ingester."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        project_data_provider_service: ProjectDataProviderService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.project_service = project_service or get_project_service()
        self.project_data_provider_service = project_data_provider_service or ProjectDataProviderService()
        self.settings = settings or get_settings()

    async def validate_project_tables(
        self,
        key: str,
        authorized_project: AuthorizedResource,
        request: ProjectIngesterRequest,
    ) -> ValidateResponse:
        """Validate normalized tables from the authorized saved project."""
        project_name = self._guard_project_call(authorized_project, request)
        project, core_project, project_warnings, project_error = self._load_validated_project(project_name)
        if project_error:
            return ValidateResponse(is_valid=False, errors=project_error, warnings=project_warnings)

        ingester_class = self._get_table_ingester(key)
        if isinstance(ingester_class, ValidateResponse):
            return ingester_class

        try:
            config = self._create_trusted_config(key, project, core_project, request)
        except (ConfigurationError, ProjectDataProviderError, PydanticValidationError, ProjectIngesterConfigurationError) as exc:
            return ValidateResponse(is_valid=False, errors=[str(exc)], warnings=project_warnings)

        shapeshifter = await normalize_project(
            core_project,
            translate=request.translate,
            drop_foreign_keys=request.drop_foreign_keys,
            default_entity=request.default_entity,
            env_file=None,
        )
        tables = shapeshifter.table_store
        self._log_table_counts(project_name, tables)
        ingester: TableSourceIngester = ingester_class(config)
        result: ValidationResult = await ingester.validate_tables(tables, source_name=f"project:{project_name}")

        return ValidateResponse(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=project_warnings + result.warnings,
            infos=result.infos,
            pending_confirmation_report=result.pending_confirmation_report,
        )

    async def ingest_project_tables(
        self,
        key: str,
        authorized_project: AuthorizedResource,
        request: ProjectIngesterRequest,
    ) -> IngestResponse:
        """Normalize and ingest tables from the authorized saved project."""
        project_name = self._guard_project_call(authorized_project, request)
        project, core_project, project_warnings, project_error = self._load_validated_project(project_name)
        if project_error:
            return self._ingestion_failure("Project validation failed", project_error)

        ingester_class = self._get_table_ingester(key)
        if isinstance(ingester_class, ValidateResponse):
            return self._ingestion_failure("File input required", ingester_class.errors)

        try:
            config = self._create_trusted_config(key, project, core_project, request)
        except (ConfigurationError, ProjectDataProviderError, PydanticValidationError, ProjectIngesterConfigurationError) as exc:
            return self._ingestion_failure("Ingestion configuration failed", [str(exc)])

        shapeshifter = await normalize_project(
            core_project,
            translate=request.translate,
            drop_foreign_keys=request.drop_foreign_keys,
            default_entity=request.default_entity,
            env_file=None,
        )
        tables = shapeshifter.table_store
        self._log_table_counts(project_name, tables)
        ingester: TableSourceIngester = ingester_class(config)
        result: IngestionResult = await ingester.ingest_tables(
            tables,
            source_name=f"project:{project_name}",
            validate_first=True,
        )
        if project_warnings:
            logger.warning("Project '{}' passed specification checks with warnings: {}", project_name, project_warnings)

        return IngestResponse(
            success=result.success,
            records_processed=result.records_inserted,
            message=result.message,
            submission_id=result.submission_id,
            output_path=result.output_path,
            error_details=result.error_details,
            scope_name=result.scope_name,
            run_id=result.run_id,
            deploy_artifact=result.deploy_artifact,
            pending_confirmation_report=result.pending_confirmation_report,
        )

    def _guard_project_call(self, authorized_project: AuthorizedResource, request: ProjectIngesterRequest) -> str:
        """Reject invalid project authorization before loading project data or settings."""
        if not isinstance(authorized_project, AuthorizedResource):
            raise PermissionError("Project is not authorized for ingester execution")

        resource = authorized_project.resource
        locator = resource.locator
        if (
            authorized_project.action != Action.EXECUTE
            or resource.resource_type != ResourceType.PROJECT
            or resource.lifecycle_state != "active"
            or not isinstance(locator, str)
            or not locator.strip()
        ):
            raise PermissionError("Project is not authorized for ingester execution")

        if not isinstance(request, ProjectIngesterRequest):
            raise TypeError("Project ingester calls require a validated ProjectIngesterRequest")
        if request.project_name != locator:
            raise PermissionError("Requested project does not match the authorized project")

        return locator

    def _load_validated_project(
        self,
        project_name: str,
    ) -> tuple[Project, Any, list[str], list[str]]:
        """Load and validate one saved project before normalization or ingester work."""
        project = self.project_service.load_project(project_name)
        try:
            core_project = ProjectMapper.to_core(project)
            specification = CompositeProjectSpecification(core_project.cfg)
            is_valid = specification.is_satisfied_by()
            errors = [str(error) for error in specification.errors]
            warnings = [str(warning) for warning in specification.warnings]
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Project validation failed for '{}'", project_name)
            return project, None, [], [f"Project configuration validation failed: {exc}"]

        if not is_valid or errors:
            return project, core_project, warnings, errors or ["Project configuration validation failed"]
        return project, core_project, warnings, []

    @staticmethod
    def _get_table_ingester(key: str) -> type[TableSourceIngester] | ValidateResponse:
        """Return the registered table ingester or a clear file-input-required error."""
        ingester_class = get_ingester_registry().get(key)
        if ingester_class is None:
            raise ValueError(f"Ingester '{key}' not found")
        if not issubclass(ingester_class, TableSourceIngester):
            message = f"Ingester '{key}' requires file input and does not support normalized tables"
            return ValidateResponse(is_valid=False, errors=[message])
        return ingester_class

    def _create_trusted_config(
        self,
        key: str,
        project: Project,
        core_project: Any,
        request: ProjectIngesterRequest,
    ) -> IngesterConfig:
        """Build the ingester config from backend settings and named request values."""
        required_connection_values = {
            "INGEST_TARGET_HOST": self.settings.INGEST_TARGET_HOST,
            "INGEST_TARGET_DBNAME": self.settings.INGEST_TARGET_DBNAME,
            "INGEST_TARGET_USER": self.settings.INGEST_TARGET_USER,
        }
        missing = [name for name, value in required_connection_values.items() if not isinstance(value, str) or not value.strip()]
        if missing:
            raise ProjectIngesterConfigurationError("Project ingester settings are missing: " + ", ".join(missing))
        if self.settings.INGEST_OUTPUT_DIR is None:
            raise ProjectIngesterConfigurationError("Project ingester setting INGEST_OUTPUT_DIR is required")

        target_model_data = core_project.cfg.get("metadata", {}).get("target_model")
        if target_model_data is None:
            raise ProjectIngesterConfigurationError("The saved project requires metadata.target_model")
        target_model = TargetModel.model_validate(target_model_data)

        foreign_key_value_sources: dict[str, dict[str, str]] = {}
        for entity_name in core_project.entities:
            entity_config = core_project.get_table(entity_name)
            if entity_config.foreign_key_value_sources:
                foreign_key_value_sources[entity_name] = dict(entity_config.foreign_key_value_sources)
        if key == "sead_change_request" and any(
            value_source == "public_id" for entity_sources in foreign_key_value_sources.values() for value_source in entity_sources.values()
        ):
            direct_issues = ForeignKeyValueSourceConformanceValidator().validate(target_model, core_project)
            if direct_issues:
                raise ProjectIngesterConfigurationError(self._format_direct_fk_issues(direct_issues))

        trusted_context = self.project_data_provider_service.build_trusted_context(project)

        submission_context = request.submission_context.model_dump(mode="python", exclude_none=True)
        submission_context["project_name"] = trusted_context.project_name
        extra: dict[str, Any] = {
            "target_model": target_model,
            TRUSTED_PROJECT_CONTEXT_KEY: trusted_context,
            "submission_context": submission_context,
        }
        if key == "sead_change_request" and foreign_key_value_sources:
            extra["foreign_key_value_sources"] = foreign_key_value_sources
        if request.deploy_strategy is not None:
            extra["deploy_strategy"] = request.deploy_strategy

        extra = inject_ingester_runtime_dependencies(key, extra, self.settings)
        extra = inject_ingester_database_dependencies(
            key,
            extra,
            {
                "host": self.settings.INGEST_TARGET_HOST,
                "port": self.settings.INGEST_TARGET_PORT,
                "dbname": self.settings.INGEST_TARGET_DBNAME,
                "user": self.settings.INGEST_TARGET_USER,
            },
        )
        return IngesterConfig(
            host=self.settings.INGEST_TARGET_HOST,
            port=self.settings.INGEST_TARGET_PORT,
            dbname=self.settings.INGEST_TARGET_DBNAME,
            user=self.settings.INGEST_TARGET_USER,
            submission_name=request.submission_context.submission_name,
            data_types=request.submission_context.datatype,
            output_folder=str(self.settings.INGEST_OUTPUT_DIR),
            extra=extra,
        )

    @staticmethod
    def _format_direct_fk_issues(issues: list[ConformanceIssue]) -> str:
        """Format direct foreign-key declaration errors for existing service responses."""
        formatted_issues: list[str] = []
        for issue in issues:
            context = [
                f"entity '{issue.entity}'" if issue.entity else None,
                f"field '{issue.field}'" if issue.field else None,
                f"column '{issue.column}'" if issue.column else None,
            ]
            issue_context = ", ".join(item for item in context if item)
            formatted_issues.append(f"{issue.code}: {issue.message}" + (f" ({issue_context})" if issue_context else ""))
        return "Invalid direct foreign-key declaration: " + "; ".join(formatted_issues)

    @staticmethod
    def _log_table_counts(project_name: str, tables: dict[str, Any]) -> None:
        """Log the entity and row counts passed to the ingester."""
        counts = {entity_name: len(table.index) for entity_name, table in tables.items()}
        logger.info(
            "Project '{}' produced {} table(s) and {} row(s) for ingester: {}",
            project_name,
            len(tables),
            sum(counts.values()),
            counts,
        )

    @staticmethod
    def _ingestion_failure(message: str, errors: list[str]) -> IngestResponse:
        """Build a failed response without a bundle or output path."""
        return IngestResponse(
            success=False,
            records_processed=0,
            message=message,
            output_path=None,
            error_details="\n".join(errors),
        )


class ProjectIngesterConfigurationError(ValueError):
    """Raised when required backend-owned project-ingester settings or data are missing."""
