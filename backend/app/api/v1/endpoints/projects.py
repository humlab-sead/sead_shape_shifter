"""API endpoints for project management."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.models.project import Project, ProjectMetadata
from backend.app.models.validation import ValidationResult
from backend.app.services.project_service import (
    ProjectService,
    get_project_service,
)
from backend.app.services.validation_service import ValidationService, get_validation_service
from backend.app.services.yaml_service import YamlService, get_yaml_service
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError

router = APIRouter()

# pylint: disable=no-member


# Request/Response Models
class ProjectCreateRequest(BaseModel):
    """Request to create new project."""

    name: str = Field(..., description="Project name")
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Initial entities")


class ProjectUpdateRequest(BaseModel):
    """Request to update project."""

    entities: dict[str, dict[str, Any]] = Field(..., description="Updated entities")
    options: dict[str, Any] = Field(default_factory=dict, description="Project options")


class BackupInfo(BaseModel):
    """Backup file information."""

    file_name: str = Field(..., description="Backup file name")
    file_path: str = Field(..., description="Full backup file path")
    created_at: float = Field(..., description="Creation timestamp")


class RawYamlUpdateRequest(BaseModel):
    """Request to update project with raw YAML."""

    yaml_content: str = Field(..., description="Raw YAML content")


class RestoreBackupRequest(BaseModel):
    """Request to restore from backup."""

    backup_path: str = Field(..., description="Path to backup file to restore")


class MetadataUpdateRequest(BaseModel):
    """Request to update project metadata."""

    name: str | None = Field(default=None, description="Project name")
    description: str | None = Field(default=None, description="Project description")
    version: str | None = Field(default=None, description="Project version (x.y.z format)")
    default_entity: str | None = Field(default=None, description="Default entity name")


# Endpoints
@router.get("/projects", response_model=list[ProjectMetadata])
@handle_endpoint_errors
async def list_projects() -> list[ProjectMetadata]:
    """
    List all available project files.

    Returns metadata for each project including:
    - Name and file path
    - Entity count
    - Creation and modification timestamps
    - Validation status
    """
    project_service: ProjectService = get_project_service()
    configs: list[ProjectMetadata] = project_service.list_projects()
    logger.debug(f"Listed {len(configs)} project(s)")
    return configs


@router.get("/projects/{name}", response_model=Project)
@handle_endpoint_errors
async def get_project(name: str) -> Project:
    """
    Get specific project by name.
    Args:
        name: Project name (without .yml extension)

    Returns:
        Complete project with entities, options, and metadata
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.load_project(name)
    logger.info(f"Retrieved project '{name}'")
    return project


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
@handle_endpoint_errors
async def create_project(request: ProjectCreateRequest) -> Project:
    """
    Create new project.

    Args:
        request: Project creation request with name and optional entities

    Returns:
        Created project with metadata
    """
    project_service: ProjectService = get_project_service()
    project: Project = project_service.create_project(request.name, request.entities)
    logger.info(f"Created project '{request.name}'")
    return project


@router.put("/projects/{name}", response_model=Project)
@handle_endpoint_errors
async def update_project(name: str, request: ProjectUpdateRequest) -> Project:
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
    project: Project = project_service.load_project(name)
    project.options = request.options

    logger.debug(f"Updating project '{name}': preserving {len(project.entities)} entities from disk, " f"updating options only")

    updated_project: Project = project_service.save_project(project)
    logger.info(
        f"Updated project '{name}' options (entities preserved: " f"{list(updated_project.entities.keys())})",
    )
    return updated_project


@router.patch("/projects/{name}/metadata", response_model=Project)
@handle_endpoint_errors
async def update_project_metadata(name: str, request: MetadataUpdateRequest) -> Project:
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
        name=name,
        new_name=request.name,
        description=request.description,
        version=request.version,
        default_entity=request.default_entity,
    )
    logger.info(f"Updated metadata for project '{name}'")
    return project


@router.delete("/projects/{name}", status_code=status.HTTP_204_NO_CONTENT)
@handle_endpoint_errors
async def delete_project(name: str) -> None:
    """
    Delete project file.

    Creates a backup before deletion.

    Args:
        name: Project name to delete
    """
    project_service: ProjectService = get_project_service()
    project_service.delete_project(name)
    logger.info(f"Deleted project '{name}'")


@router.post("/projects/{name}/validate", response_model=ValidationResult)
@handle_endpoint_errors
async def validate_project(name: str) -> ValidationResult:
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
    project: Project = project_service.load_project(name)
    config_data: dict[str, Any] = {"entities": project.entities, "options": project.options}
    result: ValidationResult = validation_service.validate_project(config_data)
    logger.info(f"Validated project '{name}': {'valid' if result.is_valid else 'invalid'}")
    return result


@router.get("/projects/{name}/backups", response_model=list[BackupInfo])
@handle_endpoint_errors
async def list_backups(name: str) -> list[BackupInfo]:
    """
    List all backup files for a project.

    Returns backups sorted by creation time (newest first).

    Args:
        name: Project name

    Returns:
        List of backup file information
    """
    yaml_service: YamlService = get_yaml_service()
    backups: list[Path] = yaml_service.list_backups(f"{name}.yml")
    backup_infos: list[BackupInfo] = [
        BackupInfo(
            file_name=backup.name,
            file_path=str(backup),
            created_at=backup.stat().st_mtime,
        )
        for backup in backups
    ]
    logger.debug(f"Listed {len(backup_infos)} backup(s) for '{name}'")
    return backup_infos


@router.post("/projects/{name}/restore", response_model=Project)
@handle_endpoint_errors
async def restore_backup(name: str, request: RestoreBackupRequest) -> Project:
    """
    Restore project from backup file.

    Creates a backup of current file before restoring.

    Args:
        name: Project name
        request: Backup file path to restore from

    Returns:
        Restored project
    """
    yaml_service: YamlService = get_yaml_service()
    target_path: Path = settings.PROJECTS_DIR / f"{name}.yml"
    yaml_service.restore_backup(request.backup_path, str(target_path), create_backup=True)
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
async def activate_project(name: str) -> Project:
    """
    Activate (load) a project into the backend context.

    This makes the project's data sources available in the Data Sources view
    and sets it as the active project for all data source operations.

    Args:
        name: Project name to activate

    Returns:
        The activated project
    """
    project: Project = get_project_service().activate_project(name)
    logger.info(f"Activated project '{name}'")
    return project


# Data Source Connection Endpoints


class DataSourceConnectionRequest(BaseModel):
    """Request to connect a data source to a project."""

    source_name: str = Field(..., description="Name to assign to the data source in this project")
    source_filename: str = Field(..., description="Filename of the data source file (e.g., 'sead-options.yml')")


@router.get("/projects/{name}/data-sources", response_model=dict[str, str])
@handle_endpoint_errors
async def get_project_data_sources(name: str) -> dict[str, str]:
    """
    Get all data sources connected to a project.

    Returns a dict mapping data source names to their filenames (or inline project).

    Args:
        name: Project name

    Returns:
        Dict of source_name -> "@include: filename.yml" or inline project
    """
    project: Project = get_project_service().load_project(name)
    data_sources = project.options.get("data_sources", {})
    return data_sources


@router.post("/projects/{name}/data-sources", response_model=Project)
@handle_endpoint_errors
async def connect_data_source_to_project(name: str, request: DataSourceConnectionRequest) -> Project:
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
    project: Project = get_project_service().load_project(name)

    # Check if source name already exists
    data_sources = project.options.get("data_sources", {})
    if request.source_name in data_sources:
        raise BadRequestError(f"Data source '{request.source_name}' already connected to this project")

    # Add @include reference
    data_sources[request.source_name] = f"@include: {request.source_filename}"
    project.options["data_sources"] = data_sources

    # Save project
    updated_config: Project = get_project_service().save_project(project)

    logger.info(f"Connected data source '{request.source_name}' (@include: {request.source_filename}) " f"to project '{name}'")

    return updated_config


@router.delete("/projects/{name}/data-sources/{source_name}", response_model=Project)
@handle_endpoint_errors
async def disconnect_data_source_from_project(name: str, source_name: str) -> Project:
    """
    Disconnect a data source from a project.

    Removes the data source reference from options.data_sources section.

    Args:
        name: Project name
        source_name: Data source name to disconnect

    Returns:
        Updated project
    """

    project: Project = get_project_service().load_project(name)

    data_sources: dict[str, str] = project.options.get("data_sources", {})
    if source_name not in data_sources:
        raise NotFoundError(f"Data source '{source_name}' not found in project '{name}'")

    del data_sources[source_name]
    project.options["data_sources"] = data_sources

    updated_config: Project = get_project_service().save_project(project)

    logger.info(f"Disconnected data source '{source_name}' from project '{name}'")

    return updated_config


@router.get("/projects/{name}/raw-yaml", response_model=dict[str, str])
@handle_endpoint_errors
async def get_project_raw_yaml(name: str) -> dict[str, str]:
    """
    Get project as raw YAML string.

    Args:
        name: Project name

    Returns:
        Dictionary containing yaml_content
    """
    yaml_service: YamlService = get_yaml_service()
    project_service: ProjectService = get_project_service()

    # Get project to verify it exists
    project_service.load_project(name)

    # Read raw YAML file
    project_path = settings.PROJECTS_DIR / f"{name}.yml"
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {name}.yml")

    yaml_content = project_path.read_text(encoding="utf-8")

    logger.info(f"Retrieved raw YAML for project '{name}'")

    return {"yaml_content": yaml_content}


@router.put("/projects/{name}/raw-yaml", response_model=Project)
@handle_endpoint_errors
async def update_project_raw_yaml(name: str, request: RawYamlUpdateRequest) -> Project:
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
        from io import StringIO
        parsed_yaml = yaml_service.yaml.load(StringIO(request.yaml_content))
    except Exception as e:
        raise BadRequestError(f"Failed to parse YAML: {str(e)}") from e

    # Ensure it's a valid project structure
    if not isinstance(parsed_yaml, dict):
        raise BadRequestError("YAML must be a dictionary")

    # Write to file
    project_path = settings.PROJECTS_DIR / f"{name}.yml"
    if not project_path.exists():
        raise NotFoundError(f"Project file not found: {name}.yml")

    # Create backup before update
    yaml_service.create_backup(project_path)

    # Write new content
    project_path.write_text(request.yaml_content, encoding="utf-8")

    # Load and return updated project
    updated_project = project_service.load_project(name)

    logger.info(f"Updated project '{name}' from raw YAML")

    return updated_project
