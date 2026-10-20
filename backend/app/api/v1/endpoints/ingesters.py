"""API endpoints for data ingester operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from backend.app.authorization.dependencies import (
    require_application_action,
    require_ingester_project,
    require_project,
)
from backend.app.authorization.models import Action, AuthorizedResource, Principal
from backend.app.models.ingester import (
    IngesterMetadataResponse,
    IngestRequest,
    IngestResponse,
    ProjectIngesterRequest,
    ValidateRequest,
    ValidateResponse,
)
from backend.app.services.ingester_service import CHANGE_REQUEST_INGESTER_KEY, get_ingester_service
from backend.app.services.project_ingester_service import ProjectIngesterService
from ingesters.sead_change_request.contracts import CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE

# pylint: disable=raise-missing-from

router = APIRouter()
ingester_operator_dependency = require_application_action(Action.RUN_INGESTERS)
ingester_project_dependency = require_ingester_project(Action.EXECUTE)
project_ingester_project_dependency = require_project(Action.EXECUTE, body_locator=True)


def get_project_ingester_service() -> ProjectIngesterService:
    """Build the project-only ingester service for the dedicated routes."""
    return ProjectIngesterService()


@router.get("", response_model=list[IngesterMetadataResponse])
async def list_ingesters() -> list[IngesterMetadataResponse]:
    """List all available data ingesters.

    Returns:
        List of ingester metadata including key, name, description, version, and supported formats
    """
    return get_ingester_service().list_ingesters()


@router.post("/sead_change_request/from-project/validate", response_model=ValidateResponse)
async def validate_project_ingester(
    request: ProjectIngesterRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(project_ingester_project_dependency)],
    project_ingester_service: Annotated[ProjectIngesterService, Depends(get_project_ingester_service)],
) -> ValidateResponse:
    """Validate the authorized project's normalized tables for a Change Request."""
    try:
        return await project_ingester_service.validate_project_tables(
            CHANGE_REQUEST_INGESTER_KEY,
            authorized_project,
            request,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception:
        logger.exception("Project ingester validation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Validation failed")


@router.post("/sead_change_request/from-project/ingest", response_model=IngestResponse)
async def ingest_project_ingester(
    request: ProjectIngesterRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(project_ingester_project_dependency)],
    project_ingester_service: Annotated[ProjectIngesterService, Depends(get_project_ingester_service)],
) -> IngestResponse:
    """Ingest the authorized project's normalized tables as a Change Request."""
    try:
        return await project_ingester_service.ingest_project_tables(
            CHANGE_REQUEST_INGESTER_KEY,
            authorized_project,
            request,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception:
        logger.exception("Project ingester ingestion failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed")


@router.post("/{key}/validate", response_model=ValidateResponse)
async def validate_data(
    key: str,
    request: ValidateRequest,
    _: Annotated[Principal, Depends(ingester_operator_dependency)],
    authorized_project: Annotated[AuthorizedResource | None, Depends(ingester_project_dependency)],
) -> ValidateResponse:
    """Validate data using the specified ingester.

    Args:
        key: Ingester identifier (e.g., 'sead')
        request: Validation request with source path and optional config
        authorized_project: Saved project authorized for the SEAD Change Request ingester

    Returns:
        Validation result with is_valid flag, errors, and warnings

    Raises:
        HTTPException: 403 if the principal lacks run_ingesters, 404 if the ingester or
        project is not found, 400 for the retired Change Request file input,
        500 if validation fails critically
    """
    if key == CHANGE_REQUEST_INGESTER_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE)

    try:
        result = await get_ingester_service().validate(
            key,
            request,
            project_name=authorized_project.resource.locator if authorized_project is not None else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}") from e


@router.post("/{key}/ingest", response_model=IngestResponse)
async def ingest_data(
    key: str,
    request: IngestRequest,
    _: Annotated[Principal, Depends(ingester_operator_dependency)],
    authorized_project: Annotated[AuthorizedResource | None, Depends(ingester_project_dependency)],
) -> IngestResponse:
    """Ingest data using the specified ingester.

    Args:
        key: Ingester identifier (e.g., 'sead')
        request: Ingestion request with source path, config, submission details
        authorized_project: Saved project authorized for the SEAD Change Request ingester

    Returns:
        Ingestion result with success status, records processed, submission ID, and output path

    Raises:
        HTTPException: 403 if the principal lacks run_ingesters, 404 if the ingester or
        project is not found, 400 for the retired Change Request file input,
        500 if ingestion fails
    """
    if key == CHANGE_REQUEST_INGESTER_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE)

    try:
        return await get_ingester_service().ingest(
            key,
            request,
            project_name=authorized_project.resource.locator if authorized_project is not None else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}") from e
