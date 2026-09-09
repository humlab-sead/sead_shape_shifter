"""API endpoints for mapping sidecar CRUD operations."""

from fastapi import APIRouter, Depends

from backend.app.models import mapping as api
from backend.app.services.mapping_service import MappingService
from backend.app.services.project_service import get_project_service
from backend.app.utils.error_handlers import handle_endpoint_errors
from src.reconciliation.mapping_model import EntityMapping, Link

router = APIRouter()


def get_mapping_service() -> MappingService:
    """Create a mapping service bound to the current project service."""
    return MappingService(get_project_service())


def _to_link_response(link: Link) -> api.MappingLinkResponse:
    """Convert a domain mapping link to API response shape."""
    return api.MappingLinkResponse(
        target_id=link.target_id,
        source=link.source.value,
        confidence=link.confidence,
        created_at=link.created_at,
        committed_at=link.committed_at,
        notes=link.notes,
        created_by=link.created_by,
        reviewed_by=link.reviewed_by,
    )


def _to_entity_response(entity_name: str, entity_mapping: EntityMapping) -> api.MappingEntityResponse:
    """Convert a domain entity mapping to API response shape."""
    return api.MappingEntityResponse(
        entity_name=entity_name,
        local_key=entity_mapping.local_key,
        public_id=entity_mapping.public_id,
        entity_type=entity_mapping.entity_type.value,
        description=entity_mapping.description,
        links={key: _to_link_response(link) for key, link in entity_mapping.links.items()},
    )


@router.get("/projects/{project_name}/mapping/{entity_name}", response_model=api.MappingEntityResponse)
@handle_endpoint_errors
async def get_entity_mapping(
    project_name: str,
    entity_name: str,
    service: MappingService = Depends(get_mapping_service),
) -> api.MappingEntityResponse:
    """Return all mapping links and sidecar metadata for one entity."""
    entity_mapping = service.get_entity_mapping(project_name, entity_name)
    return _to_entity_response(entity_name, entity_mapping)


@router.get("/projects/{project_name}/mapping/{entity_name}/{local_key_value}", response_model=api.MappingLinkRecordResponse)
@handle_endpoint_errors
async def get_mapping_link(
    project_name: str,
    entity_name: str,
    local_key_value: str,
    service: MappingService = Depends(get_mapping_service),
) -> api.MappingLinkRecordResponse:
    """Return one mapping link for an entity and local-key pair."""
    entity_mapping, link = service.get_link(project_name, entity_name, local_key_value)
    return api.MappingLinkRecordResponse(
        entity_name=entity_name,
        local_key_value=local_key_value,
        local_key=entity_mapping.local_key,
        public_id=entity_mapping.public_id,
        link=_to_link_response(link),
    )


@router.put("/projects/{project_name}/mapping/{entity_name}/{local_key_value}", response_model=api.MappingLinkRecordResponse)
@handle_endpoint_errors
async def put_mapping_link(
    project_name: str,
    entity_name: str,
    local_key_value: str,
    request: api.MappingLinkUpsertRequest,
    service: MappingService = Depends(get_mapping_service),
) -> api.MappingLinkRecordResponse:
    """Create or update one manual mapping link."""
    entity_mapping, link = service.put_link(
        project_name,
        entity_name,
        local_key_value,
        target_id=request.target_id,
        confidence=request.confidence,
        notes=request.notes,
    )
    return api.MappingLinkRecordResponse(
        entity_name=entity_name,
        local_key_value=local_key_value,
        local_key=entity_mapping.local_key,
        public_id=entity_mapping.public_id,
        link=_to_link_response(link),
    )


@router.delete("/projects/{project_name}/mapping/{entity_name}/{local_key_value}", response_model=api.MappingDeleteResponse)
@handle_endpoint_errors
async def delete_mapping_link(
    project_name: str,
    entity_name: str,
    local_key_value: str,
    service: MappingService = Depends(get_mapping_service),
) -> api.MappingDeleteResponse:
    """Delete one mapping link for an entity and local-key pair."""
    service.delete_link(project_name, entity_name, local_key_value)
    return api.MappingDeleteResponse(entity_name=entity_name, local_key_value=local_key_value, deleted=True)
