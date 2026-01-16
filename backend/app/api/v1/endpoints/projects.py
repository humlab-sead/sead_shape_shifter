"""API endpoints for project management."""

from datetime import datetime, timezone
from io import StringIO
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
    task_list: dict[str, Any] | None = Field(default=None, description="Task list configuration")


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
    project: Project = project_service.create_project(request.name, entities=request.entities, task_list=request.task_list)
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
    config_data: dict[str, Any] = {
        "metadata": project.metadata.model_dump() if project.metadata else {},
        "entities": project.entities,
        "options": project.options,
    }
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
    project_service: ProjectService = get_project_service()

    project_service.load_project(name)

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
async def get_custom_layout(name: str) -> CustomLayoutResponse:
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
    project: Project = project_service.load_project(name)

    # Get layout from project options
    layout_data = project.options.get("layout", {}).get("custom", {})

    # Convert to response model
    layout_positions = {
        entity_name: LayoutPositionResponse(x=pos["x"], y=pos["y"])
        for entity_name, pos in layout_data.items()
        if not entity_name.startswith("_")  # Skip metadata
    }

    logger.info(f"Retrieved custom layout for project '{name}': {len(layout_positions)} entities")

    return CustomLayoutResponse(
        project_name=name,
        layout=layout_positions,
        has_custom_layout=bool(layout_data),
    )


@router.put("/projects/{name}/layout", response_model=SaveLayoutResponse)
@handle_endpoint_errors
async def save_custom_layout(name: str, request: SaveLayoutRequest) -> SaveLayoutResponse:
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
    project: Project = project_service.load_project(name)

    # Validate layout structure
    for entity_name, pos in request.layout.items():
        if "x" not in pos or "y" not in pos:
            raise BadRequestError(f"Invalid position for entity '{entity_name}': must have x and y")
        # Note: We don't require entities to exist in project - allows saving layout before entity creation
        if entity_name not in project.entities:
            logger.warning(f"Entity '{entity_name}' not found in project '{name}', keeping position anyway")

    # Update project options
    if "layout" not in project.options:
        project.options["layout"] = {}
    project.options["layout"]["custom"] = request.layout
    project.options["layout"]["_metadata"] = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "layout_version": 1,
    }

    # Save project (backup is created automatically by save_project)
    project_service.save_project(project)

    logger.info(f"Saved custom layout for project '{name}': {len(request.layout)} entities positioned")

    return SaveLayoutResponse(
        project_name=name,
        entities_positioned=len(request.layout),
        message="Custom layout saved successfully",
    )


@router.delete("/projects/{name}/layout", response_model=dict[str, str])
@handle_endpoint_errors
async def clear_custom_layout(name: str) -> dict[str, str]:
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
    project: Project = project_service.load_project(name)

    # Check if custom layout exists
    had_layout = bool(project.options.get("layout", {}).get("custom"))

    # Remove custom layout
    if "layout" in project.options and "custom" in project.options["layout"]:
        del project.options["layout"]["custom"]
        # Clean up metadata
        if "_metadata" in project.options["layout"]:
            del project.options["layout"]["_metadata"]
        # Clean up empty layout dict
        if not project.options["layout"]:
            del project.options["layout"]

    if had_layout:
        # Save project (backup is created automatically by save_project)
        project_service.save_project(project)

        logger.info(f"Cleared custom layout for project '{name}'")
        return {"project_name": name, "message": "Custom layout cleared successfully"}

    logger.info(f"No custom layout found for project '{name}'")
    return {"project_name": name, "message": "No custom layout to clear"}
