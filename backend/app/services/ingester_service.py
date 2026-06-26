"""Service layer for ingester operations."""

from typing import Any

from loguru import logger

from backend.app.core.config import get_settings
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


class IngesterService:
    """Service for managing data ingesters."""

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
            )
            for metadata in metadata_list
        ]

    async def validate(self, key: str, request: ValidateRequest) -> ValidateResponse:
        """Validate data using specified ingester.

        Args:
            key: Ingester key/identifier
            request: Validation request with source and config

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

    async def ingest(self, key: str, request: IngestRequest) -> IngestResponse:
        """Ingest data using specified ingester.

        Args:
            key: Ingester key/identifier
            request: Ingestion request with source, config, and submission details

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
