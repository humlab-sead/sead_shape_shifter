"""API endpoints for data ingester operations."""

from fastapi import APIRouter, HTTPException, status

from backend.app.models.ingester import (
    IngesterMetadataResponse,
    IngestRequest,
    IngestResponse,
    ValidateRequest,
    ValidateResponse,
)
from backend.app.services.ingester_service import IngesterService

router = APIRouter()


@router.get("", response_model=list[IngesterMetadataResponse])
async def list_ingesters() -> list[IngesterMetadataResponse]:
    """List all available data ingesters.

    Returns:
        List of ingester metadata including key, name, description, version, and supported formats
    """
    return IngesterService.list_ingesters()


@router.post("/{key}/validate", response_model=ValidateResponse)
async def validate_data(key: str, request: ValidateRequest) -> ValidateResponse:
    """Validate data using the specified ingester.

    Args:
        key: Ingester identifier (e.g., 'sead')
        request: Validation request with source path and optional config

    Returns:
        Validation result with is_valid flag, errors, and warnings

    Raises:
        HTTPException: 404 if ingester not found, 500 if validation fails critically
    """
    try:
        result = await IngesterService.validate(key, request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}") from e


@router.post("/{key}/ingest", response_model=IngestResponse)
async def ingest_data(key: str, request: IngestRequest) -> IngestResponse:
    """Ingest data using the specified ingester.

    Args:
        key: Ingester identifier (e.g., 'sead')
        request: Ingestion request with source path, config, submission details

    Returns:
        Ingestion result with success status, records processed, submission ID, and output path

    Raises:
        HTTPException: 404 if ingester not found, 500 if ingestion fails
    """
    try:
        result = await IngesterService.ingest(key, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.message)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}") from e
