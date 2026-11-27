"""API endpoint that tells the UI what the current user may do."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.authorization.dependencies import declare_authenticated_route, get_authorization_service, get_principal
from backend.app.authorization.models import Action, Principal
from backend.app.authorization.service import AuthorizationService
from backend.app.models.permissions import UserPermissions

router = APIRouter()


@router.get("/me/permissions", response_model=UserPermissions)
@declare_authenticated_route
async def get_my_permissions(
    principal: Annotated[Principal, Depends(get_principal())],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> UserPermissions:
    """Returns which deployment-wide features the current user may use.

    The UI uses this to hide features. It does not grant access: each protected route checks authorization itself.
    """
    return UserPermissions(can_read_logs=authorization_service.can_perform_application_action(principal, Action.READ_LOGS))
