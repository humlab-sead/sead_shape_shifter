"""Service layer for ingester operations."""

from typing import Any

from loguru import logger
from networkx import out_degree_centrality

from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    IngestionResult,
    ValidationResult,
)
from backend.app.ingesters.registry import Ingesters
from backend.app.models.ingester import (
    IngesterMetadataResponse,
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
)


class IngesterService:
    """Service for managing data ingesters."""

    @staticmethod
    def list_ingesters() -> list[IngesterMetadataResponse]:
        """List all registered ingesters with their metadata.

        Returns:
            List of ingester metadata responses
        """
        metadata_list: list[IngesterMetadata] = Ingesters.get_metadata_list()
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

    @staticmethod
    async def validate(key: str, request: ValidateRequest) -> ValidateResponse:
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
        ingester_cls = Ingesters.get(key)
        if ingester_cls is None:
            raise ValueError(f"Ingester '{key}' not found")

        # Create configuration
        config = IngesterService._create_config(request.config)

        # Instantiate and validate
        try:
            ingester: Ingester = ingester_cls(config)
            result: ValidationResult = await ingester.validate(request.source)

            return ValidateResponse(
                is_valid=result.is_valid,
                errors=result.errors,
                warnings=result.warnings,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Validation failed for ingester '{key}'")
            return ValidateResponse(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
            )

    @staticmethod
    async def ingest(key: str, request: IngestRequest) -> IngestResponse:
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
        ingester_cls = Ingesters.get(key)
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
        config = IngesterService._create_config(config_dict)

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
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Ingestion failed for ingester '{key}'")
            return IngestResponse(
                success=False,
                records_processed=0,
                message=f"Ingestion error: {str(e)}",
                submission_id=None,
                output_path=None,
            )

    @staticmethod
    def _create_config(config_dict: dict[str, Any]) -> IngesterConfig:
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

        return IngesterConfig(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            dbname=db_config.get("dbname", ""),
            user=db_config.get("user", ""),
            submission_name=config_dict.get("submission_name", ""),
            data_types=config_dict.get("data_types", ""),
            extra=extra,
        )
