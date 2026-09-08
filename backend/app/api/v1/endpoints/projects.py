"""API endpoints for project management."""

from io import StringIO
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.authorization.dependencies import (
    authorize_shared_data_source_reference,
    get_authorization_service,
    get_principal,
    require_application_action,
    require_project,
    require_shared_data_source,
)
from backend.app.authorization.models import Action, AuthorizedResource, Principal
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import settings
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.models.project import Project, ProjectFileInfo, ProjectMetadata
from backend.app.models.validation import ValidationResult
from backend.app.services.documentation_service import DocumentationService, get_documentation_service
from backend.app.services.layout_sidecar_manager import LayoutSidecarManager, get_layout_sidecar_manager
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.validation_service import ValidationService, get_validation_service
from backend.app.services.yaml_service import YamlService, get_yaml_service
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, BaseAPIException, NotFoundError
from src.path_resolution import resolve_contained_path
from src.target_model import DocumentFormat

router = APIRouter()
shared_data_source_reader_dependency = require_shared_data_source(Action.READ)

# pylint: disable=no-member


def _project_directory(project_name: str) -> Path:
    """Resolve a project directory beneath the configured projects root."""
    try:
        return resolve_contained_path(ProjectNameMapper.to_path(project_name), settings.PROJECTS_DIR)
    except ValueError as exc:
        raise BadRequestError("Project path is outside the managed projects directory") from exc


def _authorize_referenced_shared_data_sources(
    data_sources: object,
    principal: Principal,
    authorization_service: AuthorizationService,
) -> None:
    """Require read access to every shared source included in project options."""
    if not isinstance(data_sources, dict):
        return

    for source_config in data_sources.values():
        if isinstance(source_config, str) and source_config.startswith("@include:"):
            source_filename = source_config.removeprefix("@include:").strip()
            authorize_shared_data_source_reference(principal, authorization_service, source_filename)


# Request/Response Models
class ProjectCreateRequest(BaseModel):
    """Request to create new project."""

    name: str = Field(..., description="Project name")
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Initial entities")
    task_list: dict[str, Any] | None = Field(default=None, description="Task list configuration")


class ProjectUpdateRequest(BaseModel):
    """Request to update project."""

    entities: dict[str, dict[str, Any]] = Field(..., description="Updated entities")
    options: dict[str, Any] = Field(default_factory=dict, description="Project options")


class BackupInfo(BaseModel):
    """Backup file information."""

    file_name: str = Field(..., description="Backup file name")
    created_at: float = Field(..., description="Creation timestamp")


class RawYamlUpdateRequest(BaseModel):
    """Request to update project with raw YAML."""

    yaml_content: str = Field(..., description="Raw YAML content")


class RestoreBackupRequest(BaseModel):
    """Request to restore from backup."""

    backup_name: str = Field(..., description="Server-issued backup file name")


class MetadataUpdateRequest(BaseModel):
    """Request to update project metadata."""

    name: str | None = Field(default=None, description="Project name")
    description: str | None = Field(default=None, description="Project description")
    version: str | None = Field(default=None, description="Project version (x.y.z format)")
    default_entity: str | None = Field(default=None, description="Default entity name")
    target_model: str | None = Field(
        default=None, description="Target model spec path (e.g. @load: target.yml); empty string clears the field"
    )


# Endpoints
@router.get("/projects", response_model=list[ProjectMetadata])
@handle_endpoint_errors
async def list_projects(
    principal: Annotated[Principal, Depends(get_principal())],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> list[ProjectMetadata]:
    """
    List all available project files.

    Returns metadata for each project including:
    - Name and file path
    - Entity count
    - Creation and modification timestamps
    - Validation status
    """
    project_service: ProjectService = get_project_service()
    configs: list[ProjectMetadata] = project_service.list_authorized_projects(principal, authorization_service)
    logger.debug(f"Listed {len(configs)} project(s)")
    return configs


@router.get("/projects/{name}", response_model=Project)
@handle_endpoint_errors
async def get_project(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> Project:
    """
    Get specific project by name.
    Args:
        name: Project name (without .yml extension)

    Returns:
        Complete project with entities, options, and metadata
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    logger.info(f"Retrieved project '{name}'")
    return project


@router.post("/projects/{name}/refresh", response_model=Project)
@handle_endpoint_errors
async def refresh_project(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> Project:
    """
    Force reload a project from disk, invalidating the server-side cache.

    Useful when the YAML file has been modified externally (manual edit, git pull, etc.)
    and you need to reload the changes without restarting the server.

    Args:
        name: Project name (without .yml extension)

    Returns:
        Reloaded project with fresh data from disk
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator, force_reload=True)
    logger.info(f"Force reloaded project '{name}' from disk")
    return project


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
@handle_endpoint_errors
async def create_project(
    request: ProjectCreateRequest,
    principal: Annotated[Principal, Depends(require_application_action(Action.CREATE_PROJECT))],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> Project:
    """
    Create new project.

    Args:
        request: Project creation request with name and optional entities

    Returns:
        Created project with metadata
    """
    project_service: ProjectService = get_project_service()
    project: Project | None = None
    try:
        project = project_service.create_project(request.name, entities=request.entities, task_list=request.task_list)
        project_service.assign_project_owner(request.name, principal, authorization_service)
    except Exception:
        if project is not None:
            project_service.delete_project(request.name)
        raise
    logger.info(f"Created project '{request.name}'")
    assert project is not None
    return project


@router.put("/projects/{name}", response_model=Project)
@handle_endpoint_errors
async def update_project(
    name: str,
    request: ProjectUpdateRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
    principal: Annotated[Principal, Depends(get_principal())],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> Project:
    """
    Update existing project.

    IMPORTANT: This endpoint does NOT update entities - use the /entities endpoints for that.
    This only updates the project options.

    Args:
        name: Project name
        request: Project options (entities field is ignored)

    Returns:
        Updated project with new metadata
    """
    project_service: ProjectService = get_project_service()
    _authorize_referenced_shared_data_sources(request.options.get("data_sources"), principal, authorization_service)
    # Boundary save: replaces only the options section on disk, leaving entities
    # and metadata (and all YAML comments) untouched.  No full-file reload needed.
    project_service.save_options_boundary(authorized_project.resource.locator, request.options or {})
    updated_project: Project = project_service.load_project(authorized_project.resource.locator, force_reload=True)
    logger.info(f"Updated project '{name}' options via boundary save")
    return updated_project


@router.patch("/projects/{name}/metadata", response_model=Project)
@handle_endpoint_errors
async def update_project_metadata(
    name: str,
    request: MetadataUpdateRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> Project:
    """
    Update project metadata.

    Updates the metadata section of a project including name, description,
    version, and default_entity. Only provided fields are updated.

    Args:
        name: Current project name
        request: Metadata fields to update

    Returns:
        Updated project with new metadata
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.update_metadata(
        name=authorized_project.resource.locator,
        new_name=request.name,
        description=request.description,
        version=request.version,
        default_entity=request.default_entity,
        target_model=request.target_model if "target_model" in request.model_fields_set else None,
        target_model_provided="target_model" in request.model_fields_set,
    )
    logger.info(f"Updated metadata for project '{name}'")
    return project


@router.delete("/projects/{name}", status_code=status.HTTP_204_NO_CONTENT)
@handle_endpoint_errors
async def delete_project(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.DELETE))],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> None:
    """
    Delete project file.

    Creates a backup before deletion.

    Args:
        name: Project name to delete
    """
    project_service: ProjectService = get_project_service()
    resource = authorized_project.resource
    authorization_service.transition_resource(resource, "deleting")
    try:
        project_service.delete_project(resource.locator)
    except Exception:
        authorization_service.transition_resource(resource, "active")
        raise
    authorization_service.transition_resource(resource, "deleted")
    logger.info(f"Deleted project '{name}'")


@router.post("/projects/{name}/copy", response_model=Project, status_code=status.HTTP_201_CREATED)
@handle_endpoint_errors
async def copy_project(
    name: str,
    source_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    principal: Annotated[Principal, Depends(require_application_action(Action.CREATE_PROJECT))],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    target_name: str = Body(..., embed=True),
) -> Project:
    """
    Copy project and its associated files to a new name.

    Copies:
    - Project YAML file with updated metadata
    - Materialized files directory (if exists)
    - Reconciliation file (if exists)

    Args:
        name: Source project name
        target_name: Target project name (with or without .yml extension)

    Returns:
        Newly created project

    Raises:
        HTTPException: If source not found or target already exists
    """
    project_service: ProjectService = get_project_service()
    new_project: Project | None = None
    try:
        new_project = project_service.copy_project(source_project.resource.locator, target_name)
        project_service.assign_project_owner(target_name, principal, authorization_service)
    except Exception:
        if new_project is not None:
            project_service.delete_project(target_name)
        raise
    logger.info(f"Copied project '{name}' to '{target_name}'")
    assert new_project is not None
    return new_project


@router.post("/projects/{name}/validate", response_model=ValidationResult)
@handle_endpoint_errors
async def validate_project(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> ValidationResult:
    """
    Validate project against specifications.

    Checks for:
    - Required fields
    - Entity references
    - Circular dependencies
    - Foreign key configurations
    - Data source availability

    Args:
        name: Project name to validate

    Returns:
        Validation result with errors and warnings
    """
    project_service: ProjectService = get_project_service()
    validation_service: ValidationService = get_validation_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    config_data: dict[str, Any] = {
        "metadata": project.metadata.model_dump() if project.metadata else {},
        "entities": project.entities,
        "options": project.options,
    }
    source_path: str = (
        project.metadata.file_path
        if project.metadata and project.metadata.file_path
        else str(settings.PROJECTS_DIR / f"{authorized_project.resource.locator}.yml")
    )
    result: ValidationResult = validation_service.validate_project(config_data, source_path=source_path)
    logger.info(f"Validated project '{name}': {'valid' if result.is_valid else 'invalid'}")
    return result


@router.get("/projects/{name}/backups", response_model=list[BackupInfo])
@handle_endpoint_errors
async def list_backups(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> list[BackupInfo]:
    """
    List all backup files for a project.

    Returns backups sorted by creation time (newest first).

    Args:
        name: Project name

    Returns:
        List of backup file information
    """
    yaml_service: YamlService = get_yaml_service()
    project_dir = _project_directory(authorized_project.resource.locator)
    backups: list[Path] = yaml_service.list_backups(project_dir=project_dir)
    backup_infos: list[BackupInfo] = [
        BackupInfo(
            file_name=backup.name,
            created_at=backup.stat().st_mtime,
        )
        for backup in backups
    ]
    logger.debug(f"Listed {len(backup_infos)} backup(s) for '{name}'")
    return backup_infos


@router.post("/projects/{name}/restore", response_model=Project)
@handle_endpoint_errors
async def restore_backup(
    name: str,
    request: RestoreBackupRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> Project:
    """
    Restore project from backup file.

    Creates a backup of current file before restoring.

    Args:
        name: Project name
        request: Server-issued backup file name to restore from

    Returns:
        Restored project
    """
    yaml_service: YamlService = get_yaml_service()
    project_dir: Path = _project_directory(authorized_project.resource.locator)
    backups: list[Path] = yaml_service.list_backups(project_dir=project_dir)
    backup_path: Path | None = next((backup for backup in backups if backup.name == request.backup_name), None)
    if backup_path is None:
        raise NotFoundError(f"Backup '{request.backup_name}' not found for project '{name}'")

    target_path: Path = resolve_contained_path("shapeshifter.yml", project_dir)
    yaml_service.restore_backup(backup_path, str(target_path), create_backup=True)
    restored_data: dict[str, Any] = yaml_service.load(target_path)
    stat = target_path.stat()
    project = Project(
        metadata=ProjectMetadata(
            name=name,
            file_path=str(target_path),
            entity_count=len(restored_data.get("entities", {})),
            created_at=stat.st_ctime,
            modified_at=stat.st_mtime,
            is_valid=True,  # Will be validated separately if needed
        ),
        entities=restored_data.get("entities", {}),
        options=restored_data.get("options", {}),
    )

    logger.info(f"Restored project '{name}' from backup")
    return project


@router.get("/projects/active/name", response_model=dict[str, str | None])
@handle_endpoint_errors
async def get_active_project_name() -> dict[str, str | None]:
    """
    Get the currently active project name.

    The active project determines which data sources are available
    in the Data Sources view.

    Returns:
        Dictionary with 'name' key containing the active project filename
        (without .yml extension), or null if no project is loaded.
    """
    active_name: str = get_project_service().get_active_project_metadata().name
    return {"name": active_name}


@router.post("/projects/{name}/activate", response_model=Project)
@handle_endpoint_errors
async def activate_project(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> Project:
    """
    Activate (load) a project into the backend context.

    This makes the project's data sources available in the Data Sources view
    and sets it as the active project for all data source operations.

    Args:
        name: Project name to activate

    Returns:
        The activated project
    """
    project: Project = get_project_service().activate_project(authorized_project.resource.locator)
    logger.info(f"Activated project '{name}'")
    return project


# Data Source Connection Endpoints


class DataSourceConnectionRequest(BaseModel):
    """Request to connect a data source to a project."""

    source_name: str = Field(..., description="Name to assign to the data source in this project")
    source_filename: str = Field(..., description="Filename of the data source file (e.g., 'sead-options.yml')")


@router.get("/projects/{name}/data-sources", response_model=dict[str, str | dict[str, Any]])
@handle_endpoint_errors
async def get_project_data_sources(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> dict[str, str | dict[str, Any]]:
    """
    Get all data sources connected to a project.

    Returns a dict mapping data source names to their configurations.
    Configurations can be either:
    - String references: "@include: filename.yml"
    - Inline objects: {"driver": "postgresql", "options": {...}}

    Args:
        name: Project name

    Returns:
        Dict of source_name -> "@include: filename.yml" or inline configuration object
    """
    project: Project = get_project_service().load_project(authorized_project.resource.locator)
    data_sources = project.options.get("data_sources", {})
    return data_sources


@router.post("/projects/{name}/data-sources", response_model=Project)
@handle_endpoint_errors
async def connect_data_source_to_project(
    name: str,
    request: DataSourceConnectionRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
    authorized_data_source: Annotated[AuthorizedResource, Depends(shared_data_source_reader_dependency)],
) -> Project:
    """
    Connect a data source to a project.

    Adds an @include reference in the project's options.data_sources section.

    Args:
        name: Project name
        request: Data source connection details (name and filename)

    Returns:
        Updated project
    """

    # Load project
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)

    # Check if source name already exists
    data_sources = project.options.get("data_sources", {})
    if request.source_name in data_sources:
        raise BadRequestError(f"Data source '{request.source_name}' already connected to this project")

    # Add @include reference
    data_sources[request.source_name] = f"@include: {request.source_filename}"
    project.options["data_sources"] = data_sources

    # Boundary save: replaces only the options section, leaving entities and YAML comments untouched.
    project_service.save_options_boundary(authorized_project.resource.locator, project.options)
    updated_config: Project = project_service.load_project(authorized_project.resource.locator, force_reload=True)

    logger.info(
        f"Connected data source '{request.source_name}' (@include: {authorized_data_source.resource.locator}.yml) " f"to project '{name}'"
    )

    return updated_config


@router.delete("/projects/{name}/data-sources/{source_name}", response_model=Project)
@handle_endpoint_errors
async def disconnect_data_source_from_project(
    name: str,
    source_name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> Project:
    """
    Disconnect a data source from a project.

    Removes the data source reference from options.data_sources section.

    Args:
        name: Project name
        source_name: Data source name to disconnect

    Returns:
        Updated project
    """

    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)

    data_sources: dict[str, str] = project.options.get("data_sources", {})
    if source_name not in data_sources:
        raise NotFoundError(f"Data source '{source_name}' not found in project '{name}'")

    del data_sources[source_name]
    project.options["data_sources"] = data_sources

    # Boundary save: replaces only the options section, leaving entities and YAML comments untouched.
    project_service.save_options_boundary(authorized_project.resource.locator, project.options)
    updated_config: Project = project_service.load_project(authorized_project.resource.locator, force_reload=True)

    logger.info(f"Disconnected data source '{source_name}' from project '{name}'")

    return updated_config


@router.get("/projects/{name}/raw-yaml", response_model=dict[str, str])
@handle_endpoint_errors
async def get_project_raw_yaml(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> dict[str, str]:
    """
    Get project as raw YAML string.

    Args:
        name: Project name

    Returns:
        Dictionary containing yaml_content
    """

    project_service: ProjectService = get_project_service()

    project_service.load_project(authorized_project.resource.locator)

    # Convert API name to filesystem path (: -> /)
    project_dir = _project_directory(authorized_project.resource.locator)
    project_path = resolve_contained_path("shapeshifter.yml", project_dir, allow_absolute=False)
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {project_path}")

    yaml_content = project_path.read_text(encoding="utf-8")

    logger.info(f"Retrieved raw YAML for project '{name}'")

    return {"yaml_content": yaml_content}


@router.put("/projects/{name}/raw-yaml", response_model=Project)
@handle_endpoint_errors
async def update_project_raw_yaml(
    name: str,
    request: RawYamlUpdateRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
    principal: Annotated[Principal, Depends(get_principal())],
    authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> Project:
    """
    Update project with raw YAML content.

    This endpoint accepts raw YAML and saves it directly to the project file.
    It performs validation after save.

    Args:
        name: Project name
        request: Raw YAML content

    Returns:
        Updated project
    """
    yaml_service: YamlService = get_yaml_service()
    project_service: ProjectService = get_project_service()

    # Validate YAML syntax
    is_valid, error_msg = yaml_service.validate_yaml(request.yaml_content)
    if not is_valid:
        raise BadRequestError(f"Invalid YAML syntax: {error_msg}")

    # Parse and validate structure
    try:
        parsed_yaml = yaml_service.yaml.load(StringIO(request.yaml_content))
    except Exception as e:
        raise BadRequestError(f"Failed to parse YAML: {str(e)}") from e

    # Ensure it's a valid project structure
    if not isinstance(parsed_yaml, dict):
        raise BadRequestError("YAML must be a dictionary")

    options = parsed_yaml.get("options")
    if isinstance(options, dict):
        _authorize_referenced_shared_data_sources(options.get("data_sources"), principal, authorization_service)

    # Write to file (convert API name to filesystem path: : -> /)
    project_dir = _project_directory(authorized_project.resource.locator)
    project_path = resolve_contained_path("shapeshifter.yml", project_dir, allow_absolute=False)
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {project_path}")

    # Create backup before update
    yaml_service.create_backup(project_path)

    # Write new content
    project_path.write_text(request.yaml_content, encoding="utf-8")

    # Load and return updated project.
    # IMPORTANT: Force reload so ApplicationState cache cannot return stale data.
    updated_project = project_service.load_project(authorized_project.resource.locator, force_reload=True)

    logger.info(f"Updated project '{name}' from raw YAML")

    return updated_project


# ---------------------------------------------------------------------------
# Target Model YAML Endpoints
# ---------------------------------------------------------------------------


def _resolve_target_model_path(project: Project, project_name: str) -> Path:
    """Return the absolute path to the project-local target model file.

    Raises:
        NotFoundError: if project has no target_model or the file is missing.
        BadRequestError: if target_model is an inline dict (no backing file).
        BaseAPIException (403): if the resolved path escapes the project directory.
    """
    target_model: str | dict[str, Any] | None = project.metadata.target_model if project.metadata else None
    if target_model is None:
        raise NotFoundError(f"Project '{project_name}' has no target_model configured")
    if isinstance(target_model, dict):
        raise BadRequestError("Target model is defined inline and has no backing file to edit")

    raw: str = str(target_model).strip()
    rel_path: str = raw
    if raw.startswith("@"):
        for prefix in ("@load", "@include"):
            if raw.startswith(prefix):
                rel_path: str = raw[len(prefix) :].lstrip(":").strip()
                break

    # Security: must stay inside the project directory
    path_name: str = ProjectNameMapper.to_path(project_name)
    project_dir: Path = _project_directory(project_name)

    # Resolve the file path: simple filenames are project-local, paths with directories use APPLICATION_ROOT
    if "/" not in rel_path and "\\" not in rel_path:
        # Simple filename - resolve relative to project directory
        target_path = resolve_contained_path(rel_path, project_dir)
    else:
        # Path with directories - resolve relative to APPLICATION_ROOT (for shared specs)
        target_path = resolve_contained_path(rel_path, settings.application_root, allow_absolute=False)

    if not target_path.is_relative_to(project_dir.resolve()):
        raise BaseAPIException(
            f"Target model file '{rel_path}' is outside the project directory and cannot be edited here",
            403,
        )

    if not target_path.exists():
        raise NotFoundError(f"Target model file not found: {target_path}")

    return target_path


@router.get("/projects/{name}/target-model-yaml", response_model=dict[str, str])
@handle_endpoint_errors
async def get_project_target_model_yaml(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> dict[str, str]:
    """
    Get the project-local target model file as a raw YAML string.

    Only project-local files (inside the project directory) are served.
    Shared/global spec files return 403.

    Args:
        name: Project name

    Returns:
        Dictionary containing yaml_content
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    target_path: Path = _resolve_target_model_path(project, authorized_project.resource.locator)
    yaml_content: str = target_path.read_text(encoding="utf-8")
    logger.info(f"Retrieved target model YAML for project '{name}'")
    return {"yaml_content": yaml_content}


@router.put("/projects/{name}/target-model-yaml", response_model=Project)
@handle_endpoint_errors
async def update_project_target_model_yaml(
    name: str,
    request: RawYamlUpdateRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> Project:
    """
    Update the project-local target model file with raw YAML content.

    Content is written verbatim to preserve comments. Syntax is validated
    but the file is never re-serialised through PyYAML.

    Only project-local files can be updated; shared files return 403.

    Args:
        name: Project name
        request: Raw YAML content

    Returns:
        Updated project
    """
    yaml_service: YamlService = get_yaml_service()
    project_service: ProjectService = get_project_service()

    project: Project = project_service.load_project(authorized_project.resource.locator)
    target_path: Path = _resolve_target_model_path(project, authorized_project.resource.locator)

    # Validate YAML syntax only — never re-serialise; write verbatim to preserve comments
    is_valid, error_msg = yaml_service.validate_yaml(request.yaml_content)
    if not is_valid:
        raise BadRequestError(f"Invalid YAML syntax: {error_msg}")

    yaml_service.create_backup(target_path)
    target_path.write_text(request.yaml_content, encoding="utf-8")

    updated_project: Project = project_service.load_project(authorized_project.resource.locator, force_reload=True)
    logger.info(f"Updated target model YAML for project '{name}'")
    return updated_project


@router.get("/projects/{name}/target-model-docs")
@handle_endpoint_errors
async def download_target_model_docs(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    format: str = Query(  # pylint: disable=redefined-builtin
        "html", description="Documentation format: html, markdown, excel, sims, or schema-reference"
    ),
) -> Response:
    """
    Generate and download target model documentation for a project.

    Generates human-readable documentation from the project's target_model specification
    with project context (which entities are actually used).

    Supported formats:
    - html: Interactive web page with entity cards, search, and visual indicators
    - markdown: Static documentation for GitHub/wikis
    - excel: Spreadsheet with 3 sheets (Entities, Columns, Relationships)
    - sims: SIMS identity register grouped by identity behavior
    - schema-reference: Markdown reference generated from the Pydantic target-model schema

    Args:
        name: Project name
        format: Output format (default: html)

    Returns:
        Documentation file as downloadable response

    Raises:
        NotFoundError: If project has no target_model configured
        BadRequestError: If format is invalid or target_model is malformed
    """
    documentation_service: DocumentationService = get_documentation_service()

    # Validate and normalize format
    format_lower: str = format.lower()
    try:
        doc_format = DocumentFormat(format_lower)
    except ValueError as e:
        raise BadRequestError(f"Invalid format '{format}'. Supported: html, markdown, excel, sims, schema-reference") from e

    # Generate documentation
    content: bytes = documentation_service.generate_target_model_docs(authorized_project.resource.locator, doc_format)

    # Determine content type and file extension
    content_types: dict[DocumentFormat, str] = {
        DocumentFormat.HTML: "text/html",
        DocumentFormat.MARKDOWN: "text/markdown",
        DocumentFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        DocumentFormat.SIMS: "text/markdown",
        DocumentFormat.SCHEMA_REFERENCE: "text/markdown",
    }
    extensions: dict[DocumentFormat, str] = {
        DocumentFormat.HTML: "html",
        DocumentFormat.MARKDOWN: "md",
        DocumentFormat.EXCEL: "xlsx",
        DocumentFormat.SIMS: "sims.md",
        DocumentFormat.SCHEMA_REFERENCE: "schema-reference.md",
    }

    media_type: str = content_types[doc_format]
    if doc_format is DocumentFormat.SCHEMA_REFERENCE:
        filename = f"{name}_target_model_schema_reference.md"
    else:
        filename = f"{name}_target_model.{extensions[doc_format]}"

    logger.info(f"Serving {doc_format.value} target model documentation for project '{name}' ({len(content)} bytes)")

    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# Layout Management Models
class LayoutPositionResponse(BaseModel):
    """Node position in graph layout."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class CustomLayoutResponse(BaseModel):
    """Custom graph layout response."""

    project_name: str = Field(..., description="Project name")
    layout: dict[str, LayoutPositionResponse] = Field(..., description="Entity positions")
    has_custom_layout: bool = Field(..., description="Whether custom layout exists")


class SaveLayoutRequest(BaseModel):
    """Request to save custom graph layout."""

    layout: dict[str, dict[str, float]] = Field(..., description="Entity name to position mapping")


class SaveLayoutResponse(BaseModel):
    """Response after saving custom layout."""

    project_name: str = Field(..., description="Project name")
    entities_positioned: int = Field(..., description="Number of entities positioned")
    message: str = Field(..., description="Success message")


# Layout Management Endpoints
@router.get("/projects/{name}/layout", response_model=CustomLayoutResponse)
@handle_endpoint_errors
async def get_custom_layout(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> CustomLayoutResponse:
    """
    Get custom graph layout for project.

    Returns the saved custom node positions for the dependency graph.
    If no custom layout exists, returns an empty layout.

    Args:
        name: Project name

    Returns:
        Custom layout with entity positions
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    layout_sidecar_manager: LayoutSidecarManager = get_layout_sidecar_manager()
    project_file = project_service.projects_dir / ProjectNameMapper.to_path(authorized_project.resource.locator) / "shapeshifter.yml"

    # Primary source: sidecar file
    layout_data = layout_sidecar_manager.load_layout(project_file)

    # Backward compatibility: migrate legacy in-file layout if sidecar missing
    if not layout_data:
        layout_data = layout_sidecar_manager.migrate_from_project_options(project_file, project.options)

    # Convert to response model (skip only the _metadata key, not entities starting with _)
    layout_positions = {
        entity_name: LayoutPositionResponse(x=pos["x"], y=pos["y"])
        for entity_name, pos in layout_data.items()
        if entity_name != "_metadata"  # Skip only the metadata key
    }

    logger.info(f"Retrieved custom layout for project '{name}': {len(layout_positions)} entities")

    return CustomLayoutResponse(
        project_name=name,
        layout=layout_positions,
        has_custom_layout=bool(layout_data),
    )


@router.put("/projects/{name}/layout", response_model=SaveLayoutResponse)
@handle_endpoint_errors
async def save_custom_layout(
    name: str,
    request: SaveLayoutRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> SaveLayoutResponse:
    """
    Save custom graph layout for project.

    Saves the current positions of nodes in the dependency graph.
    Creates a backup before modifying the project file.

    Args:
        name: Project name
        request: Layout data with entity positions

    Returns:
        Success response with number of entities positioned
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    layout_sidecar_manager: LayoutSidecarManager = get_layout_sidecar_manager()
    project_file = project_service.projects_dir / ProjectNameMapper.to_path(authorized_project.resource.locator) / "shapeshifter.yml"

    # Validate layout structure
    for entity_name, pos in request.layout.items():
        if "x" not in pos or "y" not in pos:
            raise BadRequestError(f"Invalid position for entity '{entity_name}': must have x and y")
        # Note: We don't require entities to exist in project - allows saving layout before entity creation
        if entity_name not in project.entities:
            logger.warning(f"Entity '{entity_name}' not found in project '{name}', keeping position anyway")

    # Save layout in sidecar file
    layout_sidecar_manager.save_layout(project_file, request.layout)

    # Keep project file clean: remove legacy in-file layout if present
    had_legacy_layout = bool(project.options.get("layout", {}).get("custom"))
    if "layout" in project.options and "custom" in project.options["layout"]:
        del project.options["layout"]["custom"]
    if "layout" in project.options and "_metadata" in project.options["layout"]:
        del project.options["layout"]["_metadata"]
    if "layout" in project.options and not project.options["layout"]:
        del project.options["layout"]

    if had_legacy_layout:
        # Save project only when legacy keys were removed
        project_service.save_project(project)

    logger.info(f"Saved custom layout for project '{name}': {len(request.layout)} entities positioned")

    return SaveLayoutResponse(
        project_name=name,
        entities_positioned=len(request.layout),
        message="Custom layout saved successfully",
    )


@router.delete("/projects/{name}/layout", response_model=dict[str, str])
@handle_endpoint_errors
async def clear_custom_layout(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
) -> dict[str, str]:
    """
    Clear custom graph layout for project.

    Removes saved custom node positions from the project.
    Creates a backup before modifying the project file.

    Args:
        name: Project name

    Returns:
        Success message
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(authorized_project.resource.locator)
    layout_sidecar_manager: LayoutSidecarManager = get_layout_sidecar_manager()
    project_file = project_service.projects_dir / ProjectNameMapper.to_path(authorized_project.resource.locator) / "shapeshifter.yml"

    deleted_sidecar = layout_sidecar_manager.delete_sidecar(project_file)

    # Also remove legacy in-file layout if still present
    had_legacy_layout = bool(project.options.get("layout", {}).get("custom"))
    if "layout" in project.options and "custom" in project.options["layout"]:
        del project.options["layout"]["custom"]
    if "layout" in project.options and "_metadata" in project.options["layout"]:
        del project.options["layout"]["_metadata"]
    if "layout" in project.options and not project.options["layout"]:
        del project.options["layout"]

    if had_legacy_layout:
        project_service.save_project(project)

    if deleted_sidecar or had_legacy_layout:
        logger.info(f"Cleared custom layout for project '{name}'")
        return {"project_name": name, "message": "Custom layout cleared successfully"}

    logger.info(f"No custom layout found for project '{name}'")
    return {"project_name": name, "message": "No custom layout to clear"}


# File Management Endpoints


@router.post(
    "/projects/{name}/files",
    response_model=ProjectFileInfo,
    summary="Upload a file to project directory",
)
@handle_endpoint_errors
async def upload_project_file(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.EDIT))],
    file: UploadFile = File(...),
) -> ProjectFileInfo:
    """Upload data file (Excel, CSV) to project's directory.

    Files are stored directly in the project folder alongside shapeshifter.yml,
    making them immediately available for entity configuration with location='local'.
    """
    project_service: ProjectService = get_project_service()
    return project_service.save_project_file(
        project_name=authorized_project.resource.locator,
        upload=file,
        allowed_extensions={".xlsx", ".xls", ".csv"},
    )


@router.get(
    "/projects/{name}/files",
    response_model=list[ProjectFileInfo],
    summary="List project's data files",
)
@handle_endpoint_errors
async def list_project_files(
    name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    ext: list[str] | None = Query(default=None, description="Filter by extension(s), e.g. ext=yml&ext=yaml"),
) -> list[ProjectFileInfo]:
    """List files in project directory.

    By default returns Excel and CSV data files.  Pass one or more ``ext``
    query parameters (without the leading dot) to filter by extension instead,
    e.g. ``?ext=yml&ext=yaml`` for YAML files only.
    """
    project_service: ProjectService = get_project_service()
    if ext:
        extensions = [f".{e.lstrip('.')}" for e in ext]
    else:
        extensions = [".xlsx", ".xls", ".csv"]
    return project_service.list_project_files(
        project_name=authorized_project.resource.locator,
        extensions=extensions,
    )
