"""Service layer for ingester operations."""

from typing import Any

from loguru import logger

from backend.app.core.config import get_settings
from backend.app.exceptions import ConfigurationError, ResourceNotFoundError
from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    IngestionResult,
    ValidationResult,
)
from backend.app.ingesters.registry import get_ingester_registry
from backend.app.models.ingester import (
    IngesterMetadataResponse,
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
)
from backend.app.services.ingester_runtime import inject_ingester_database_dependencies, inject_ingester_runtime_dependencies
from backend.app.services.project_data_provider_service import ProjectDataProviderError, ProjectDataProviderService
from ingesters.sead_change_request.contracts import TrustedProjectContext

CHANGE_REQUEST_INGESTER_KEY = "sead_change_request"


class IngesterService:
    """Service for managing data ingesters."""

    def __init__(self, project_data_provider_service: ProjectDataProviderService | None = None) -> None:
        self.project_data_provider_service = project_data_provider_service or ProjectDataProviderService()

    def list_ingesters(self) -> list[IngesterMetadataResponse]:
        """List all registered ingesters with their metadata.

        Returns:
            List of ingester metadata responses
        """
        metadata_list: list[IngesterMetadata] = get_ingester_registry().get_metadata_list()
        return [
            IngesterMetadataResponse(
                key=metadata.key,
                name=metadata.name,
                description=metadata.description,
                version=metadata.version,
                supported_formats=metadata.supported_formats,
                deprecated=metadata.deprecated,
                deprecation_message=metadata.deprecation_message,
            )
            for metadata in metadata_list
        ]

    async def validate(self, key: str, request: ValidateRequest, *, project_name: str | None = None) -> ValidateResponse:
        """Validate data using specified ingester.

        Args:
            key: Ingester key/identifier
            request: Validation request with source and config
            project_name: Authorized saved project locator for project-scoped ingesters

        Returns:
            Validation response with errors/warnings

        Raises:
            ValueError: If ingester not found or validation fails critically
        """
        # Get ingester class
        ingester_cls: None | type[Ingester] = get_ingester_registry().get(key)
        if ingester_cls is None:
            raise ValueError(f"Ingester '{key}' not found")

        # Create configuration
        config_dict = request.config.copy()
        try:
            trusted_project_context = self._trusted_project_context(key, project_name)
        except (ConfigurationError, ProjectDataProviderError, ResourceNotFoundError) as exc:
            logger.warning(f"Ingester '{key}' rejected the saved project binding: {exc}")
            return ValidateResponse(is_valid=False, errors=[str(exc)], warnings=[], infos=[], pending_confirmation_report=None)

        if trusted_project_context is not None:
            config_dict["trusted_project_context"] = trusted_project_context

        if request.submission_context is not None:
            config_dict["submission_context"] = request.submission_context
        if request.deploy_strategy is not None:
            config_dict["deploy_strategy"] = request.deploy_strategy

        config: IngesterConfig = self._create_config(config_dict, key=key)

        # Instantiate and validate
        try:
            ingester: Ingester = ingester_cls(config)
            result: ValidationResult = await ingester.validate(request.source)

            return ValidateResponse(
                is_valid=result.is_valid,
                errors=result.errors,
                warnings=result.warnings,
                infos=result.infos,
                pending_confirmation_report=result.pending_confirmation_report,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Validation failed for ingester '{key}'")
            return ValidateResponse(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                infos=[],
                pending_confirmation_report=None,
            )

    async def ingest(self, key: str, request: IngestRequest, *, project_name: str | None = None) -> IngestResponse:
        """Ingest data using specified ingester.

        Args:
            key: Ingester key/identifier
            request: Ingestion request with source, config, and submission details
            project_name: Authorized saved project locator for project-scoped ingesters

        Returns:
            Ingestion response with success status and details

        Raises:
            ValueError: If ingester not found or ingestion fails
        """
        # Get ingester class
        ingester_cls: None | type[Ingester] = get_ingester_registry().get(key)
        if ingester_cls is None:
            raise ValueError(f"Ingester '{key}' not found")

        # Create configuration with submission details
        config_dict = request.config.copy()
        try:
            trusted_project_context = self._trusted_project_context(key, project_name)
        except (ConfigurationError, ProjectDataProviderError, ResourceNotFoundError) as exc:
            logger.warning(f"Ingester '{key}' rejected the saved project binding: {exc}")
            return IngestResponse(
                success=False,
                records_processed=0,
                message="Ingestion failed",
                submission_id=None,
                output_path=None,
                error_details=str(exc),
            )

        if trusted_project_context is not None:
            config_dict["trusted_project_context"] = trusted_project_context

        config_dict.update(
            {
                "submission_name": request.submission_name,
                "data_types": request.data_types,
                "output_folder": request.output_folder,
                "register": request.do_register,
                "explode": request.explode,
            }
        )
        if request.submission_context is not None:
            config_dict["submission_context"] = request.submission_context
        if request.deploy_strategy is not None:
            config_dict["deploy_strategy"] = request.deploy_strategy

        config: IngesterConfig = self._create_config(config_dict, key=key)

        # Instantiate and ingest
        try:
            ingester: Ingester = ingester_cls(config)
            result: IngestionResult = await ingester.ingest(request.source)

            return IngestResponse(
                success=result.success,
                records_processed=result.records_inserted,
                message=result.message,
                submission_id=result.submission_id,
                output_path=request.output_folder,
                error_details=result.error_details,
                deploy_artifact=result.deploy_artifact,
                pending_confirmation_report=result.pending_confirmation_report,
                scope_name=result.scope_name,
                run_id=result.run_id,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Ingestion failed for ingester '{key}'")
            return IngestResponse(
                success=False,
                records_processed=0,
                message=f"Ingestion error: {str(e)}",
                submission_id=None,
                output_path=None,
                error_details=str(e),
                deploy_artifact=None,
                pending_confirmation_report=None,
            )

    def _trusted_project_context(self, key: str, project_name: str | None) -> TrustedProjectContext | None:
        """Return the backend-owned project facts for a project-scoped ingester.

        Only the SEAD Change Request ingester acts on one saved project. For that ingester
        the authorized project supplies the registered provider-schema scope, the fixed
        provider row, and the ordered business keys. Every other ingester returns ``None``
        and keeps its existing configuration contract.

        ``project_name`` must come from an authorization check. A project name in the request
        body is caller data, so it is not accepted here.
        """
        if key != CHANGE_REQUEST_INGESTER_KEY:
            return None
        if not isinstance(project_name, str) or not project_name.strip():
            raise ProjectDataProviderError("SEAD Change Request runs require an authorized saved project")

        from backend.app.services.project_service import get_project_service  # pylint: disable=import-outside-toplevel

        project = get_project_service().load_project(project_name.strip())
        return self.project_data_provider_service.build_trusted_context(project)

    def _create_config(self, config_dict: dict[str, Any], key: str | None = None) -> IngesterConfig:
        """Create IngesterConfig from dict, extracting standard fields.

        Args:
            config_dict: Configuration dictionary

        Returns:
            IngesterConfig instance
        """
        # Extract database config if present
        db_config = config_dict.get("database", {})

        # Build extra dict with all non-standard fields
        standard_fields = {"host", "port", "dbname", "user", "submission_name", "data_types", "database"}
        extra = {k: v for k, v in config_dict.items() if k not in standard_fields}
        extra = inject_ingester_runtime_dependencies(key, extra, get_settings())
        extra = inject_ingester_database_dependencies(key, extra, db_config)

        return IngesterConfig(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            dbname=db_config.get("dbname", ""),
            user=db_config.get("user", ""),
            submission_name=config_dict.get("submission_name", ""),
            data_types=config_dict.get("data_types", ""),
            extra=extra,
        )


__DEFAULT_INGESTER_SERVICE: IngesterService | None = None


def get_ingester_service() -> IngesterService:
    """Factory function to get an instance of IngesterService.

    Returns:
        IngesterService instance
    """
    global __DEFAULT_INGESTER_SERVICE  # pylint: disable=global-statement
    __DEFAULT_INGESTER_SERVICE = __DEFAULT_INGESTER_SERVICE or IngesterService()
    return __DEFAULT_INGESTER_SERVICE
