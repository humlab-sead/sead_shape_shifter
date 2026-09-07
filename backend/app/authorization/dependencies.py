"""FastAPI dependencies for centralized authorization checks."""

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from backend.app.api.dependencies import require_session
from backend.app.authorization.authentication import AuthenticationAdapter
from backend.app.authorization.models import Action, AuthorizedResource, Principal, ResourceType
from backend.app.authorization.repository import AuthorizationRepository, SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import settings
from backend.app.core.operation_manager import OperationProgress, operation_manager
from backend.app.core.state_manager import ProjectSession


def get_authorization_repository() -> Generator[AuthorizationRepository, None, None]:
    """Open the configured authorization repository for one request."""
    repository = SQLiteAuthorizationRepository(settings.AUTHORIZATION_DATABASE_PATH)
    try:
        yield repository
    finally:
        repository.close()


def get_principal() -> Callable:
    """Build the dependency that converts request authentication into a principal."""
    adapter = AuthenticationAdapter(
        enabled=settings.TRUSTED_PROXY_AUTH_ENABLED,
        environment=settings.ENVIRONMENT,
        development_principal_id=settings.DEVELOPMENT_PRINCIPAL_ID,
    )

    async def dependency(request: Request) -> Principal:
        return adapter.principal_from_request(request)

    return dependency


async def get_authorization_service(
    repository: Annotated[AuthorizationRepository, Depends(get_authorization_repository)],
) -> AuthorizationService:
    """Build the central authorization service for one request."""
    return AuthorizationService(repository)


def require_project(action: Action) -> Callable:
    """Create a dependency that authorizes a project locator for an action."""

    async def dependency(
        principal: Annotated[Principal, Depends(get_principal())],
        service: Annotated[AuthorizationService, Depends(get_authorization_service)],
        project_name: str | None = None,
        name: str | None = None,
    ) -> AuthorizedResource:
        locator = project_name or name
        resource = service.repository.get_resource_by_locator(ResourceType.PROJECT, locator) if locator is not None else None
        authorized = service.authorize(principal, action, resource) if resource is not None else None
        if authorized is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        return authorized

    dependency.authorization_requirement = {"resource_type": ResourceType.PROJECT.value, "action": action.value}
    return dependency


def require_shared_data_source(action: Action) -> Callable:
    """Create a dependency that authorizes a shared data source locator for an action."""

    async def dependency(
        principal: Annotated[Principal, Depends(get_principal())],
        service: Annotated[AuthorizationService, Depends(get_authorization_service)],
        filename: str | None = None,
        name: str | None = None,
        data_source_name: str | None = None,
    ) -> AuthorizedResource:
        locator = _data_source_locator(filename or name or data_source_name)
        resource = service.repository.get_resource_by_locator(ResourceType.SHARED_DATA_SOURCE, locator) if locator is not None else None
        authorized = service.authorize(principal, action, resource) if resource is not None else None
        if authorized is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        return authorized

    dependency.authorization_requirement = {"resource_type": ResourceType.SHARED_DATA_SOURCE.value, "action": action.value}
    return dependency


def _data_source_locator(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    return path.with_suffix(".yml").stem if path.suffix == ".yml" else path.stem


def require_application_action(action: Action) -> Callable:
    """Create a dependency that authorizes an application-scoped action."""

    async def dependency(
        principal: Annotated[Principal, Depends(get_principal())],
        service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> Principal:
        if not any(
            service.policy.allows_application_role(role, action)
            for role in service.repository.list_application_roles(principal.principal_id)
        ):
            raise HTTPException(status_code=403, detail="Insufficient authorization")
        return principal

    dependency.authorization_requirement = {"resource_type": "application", "action": action.value}
    return dependency


def require_authorized_session(action: Action) -> Callable:
    """Create a dependency that checks session ownership and current project access."""

    async def dependency(
        session: Annotated[ProjectSession, Depends(require_session)],
        principal: Annotated[Principal, Depends(get_principal())],
        service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> ProjectSession:
        if session.user_id != principal.principal_id:
            raise HTTPException(status_code=403, detail="Session does not belong to the authenticated user")
        resource = service.repository.get_resource_by_locator(ResourceType.PROJECT, session.project_name)
        authorized = service.authorize(principal, action, resource) if resource is not None else None
        if authorized is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        return session

    dependency.authorization_requirement = {"resource_type": ResourceType.PROJECT.value, "action": action.value}
    return dependency


def require_operation(action: Action = Action.READ) -> Callable:
    """Authorize access to an operation owned by the current principal and project."""

    async def dependency(
        operation_id: str,
        principal: Annotated[Principal, Depends(get_principal())],
        service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> OperationProgress:
        progress = operation_manager.get_progress(operation_id)
        if progress is None or progress.owner_principal_id != principal.principal_id:
            raise HTTPException(status_code=404, detail="Operation not found")

        try:
            resource = service.repository.get_resource(UUID(progress.project_resource_id))
        except ValueError:
            resource = None
        if service.authorize(principal, action, resource) is None:
            raise HTTPException(status_code=404, detail="Operation not found")
        return progress

    dependency.authorization_requirement = {"resource_type": ResourceType.PROJECT.value, "action": action.value}
    return dependency
