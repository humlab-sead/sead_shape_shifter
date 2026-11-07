"""API endpoint for read-only foreign-key link diagnostics."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.link_troubleshooter import (
    LinkExperimentContextRequest,
    LinkExperimentContextResponse,
    LinkExperimentTrialRequest,
    LinkExperimentTrialResponse,
)
from backend.app.services.link_troubleshooter_service import (
    LinkExperimentContextResult,
    LinkExperimentTrialResult,
    LinkTroubleshooterService,
)
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()

_NOT_FOUND_DETAIL = "Resource not found"


def get_link_troubleshooter_service() -> LinkTroubleshooterService:
    """Create the link troubleshooter service for one request."""
    return LinkTroubleshooterService()


@router.post("/projects/{project_name}/link-experiment-contexts", response_model=LinkExperimentContextResponse)
@handle_endpoint_errors
async def open_link_experiment_context(
    project_name: str,  # pylint: disable=unused-argument
    request: LinkExperimentContextRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[LinkTroubleshooterService, Depends(get_link_troubleshooter_service)],
) -> LinkExperimentContextResponse:
    """Retain one reproduced link snapshot for later trials."""
    return await service.open_context(
        project_name=authorized_project.resource.locator,
        issue_type=request.issue_type,
        local_entity=request.local_entity,
        metadata=request.metadata,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
    )


@router.get("/projects/{project_name}/link-experiment-contexts/{context_id}", response_model=LinkExperimentContextResponse)
@handle_endpoint_errors
async def read_link_experiment_context(
    project_name: str,  # pylint: disable=unused-argument
    context_id: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[LinkTroubleshooterService, Depends(get_link_troubleshooter_service)],
) -> LinkExperimentContextResponse:
    """Return the retained baseline state of one owned context."""
    result: LinkExperimentContextResult = await service.read_context(
        context_id=context_id,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
    )
    return _context_response_or_error(result)


@router.post(
    "/projects/{project_name}/link-experiment-contexts/{context_id}/trials",
    response_model=LinkExperimentTrialResponse,
)
@handle_endpoint_errors
async def run_link_experiment_trial(
    project_name: str,  # pylint: disable=unused-argument
    context_id: str,
    request: LinkExperimentTrialRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[LinkTroubleshooterService, Depends(get_link_troubleshooter_service)],
) -> LinkExperimentTrialResponse:
    """Run one trial on an owned snapshot and return the bounded comparison."""
    result: LinkExperimentTrialResult = await service.run_context_trial(
        context_id=context_id,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
        local_keys=request.local_keys,
        remote_keys=request.remote_keys,
        how=request.how,
        allow_null_keys=request.allow_null_keys,
        null_keys_equal=request.null_keys_equal,
    )
    return _trial_response_or_error(result)


@router.delete("/projects/{project_name}/link-experiment-contexts/{context_id}", status_code=204)
@handle_endpoint_errors
async def close_link_experiment_context(
    project_name: str,  # pylint: disable=unused-argument
    context_id: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[LinkTroubleshooterService, Depends(get_link_troubleshooter_service)],
) -> None:
    """Release one owned context and its retained inputs."""
    closed: bool = await service.close_context(
        context_id=context_id,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
    )
    if not closed:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)


def _raise_context_expired() -> NoReturn:
    """Raise the explicit expiry outcome shared by context routes."""
    raise HTTPException(
        status_code=410,
        detail={
            "error_type": "LinkExperimentContextExpired",
            "message": "The retained link inputs expired. Reopen the troubleshooter to reproduce the warning again.",
            "reason": "context_expired",
            "recoverable": True,
        },
    )


def _context_response_or_error(result: LinkExperimentContextResult) -> LinkExperimentContextResponse:
    """Return the context response or the matching non-success outcome."""
    if result.state == "expired":
        _raise_context_expired()
    if result.response is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
    return result.response


def _trial_response_or_error(result: LinkExperimentTrialResult) -> LinkExperimentTrialResponse:
    """Return the context trial response or the matching non-success outcome."""
    if result.state == "expired":
        _raise_context_expired()
    if result.response is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
    return result.response
