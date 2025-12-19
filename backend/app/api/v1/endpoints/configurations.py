"""API endpoints for configuration management."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.models.config import ConfigMetadata, Configuration
from backend.app.models.validation import ValidationResult
from backend.app.services.config_service import (
    ConfigurationNotFoundError,
    ConfigurationService,
    ConfigurationServiceError,
    get_config_service,
)
from backend.app.services.validation_service import ValidationService, get_validation_service
from backend.app.services.yaml_service import YamlService, YamlServiceError, get_yaml_service

router = APIRouter()

# pylint: disable=no-member

# Request/Response Models
class ConfigurationCreateRequest(BaseModel):
    """Request to create new configuration."""

    name: str = Field(..., description="Configuration name")
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Initial entities")


class ConfigurationUpdateRequest(BaseModel):
    """Request to update configuration."""

    entities: dict[str, dict[str, Any]] = Field(..., description="Updated entities")
    options: dict[str, Any] = Field(default_factory=dict, description="Configuration options")


class BackupInfo(BaseModel):
    """Backup file information."""

    file_name: str = Field(..., description="Backup file name")
    file_path: str = Field(..., description="Full backup file path")
    created_at: float = Field(..., description="Creation timestamp")


class RestoreBackupRequest(BaseModel):
    """Request to restore from backup."""

    backup_path: str = Field(..., description="Path to backup file to restore")


# Endpoints
@router.get("/configurations", response_model=list[ConfigMetadata])
async def list_configurations() -> list[ConfigMetadata]:
    """
    List all available configuration files.

    Returns metadata for each configuration including:
    - Name and file path
    - Entity count
    - Creation and modification timestamps
    - Validation status
    """
    config_service: ConfigurationService = get_config_service()
    try:
        configs = config_service.list_configurations()
        logger.debug(f"Listed {len(configs)} configuration(s)")
        return configs
    except Exception as e:
        logger.error(f"Failed to list configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list configurations: {str(e)}",
        ) from e


@router.get("/configurations/{name}", response_model=Configuration)
async def get_configuration(name: str) -> Configuration:
    """
    Get specific configuration by name.

    Args:
        name: Configuration name (without .yml extension)

    Returns:
        Complete configuration with entities, options, and metadata
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config: Configuration = config_service.load_configuration(name)
        logger.info(f"Retrieved configuration '{name}'")
        return config
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}",
        ) from e


@router.post("/configurations", response_model=Configuration, status_code=status.HTTP_201_CREATED)
async def create_configuration(request: ConfigurationCreateRequest) -> Configuration:
    """
    Create new configuration.

    Args:
        request: Configuration creation request with name and optional entities

    Returns:
        Created configuration with metadata
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config: Configuration = config_service.create_configuration(request.name, request.entities)
        logger.info(f"Created configuration '{request.name}'")
        return config
    except ConfigurationServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration: {str(e)}",
        ) from e


@router.put("/configurations/{name}", response_model=Configuration)
async def update_configuration(name: str, request: ConfigurationUpdateRequest) -> Configuration:
    """
    Update existing configuration.

    IMPORTANT: This endpoint does NOT update entities - use the /entities endpoints for that.
    This only updates the configuration options.

    Args:
        name: Configuration name
        request: Configuration options (entities field is ignored)

    Returns:
        Updated configuration with new metadata
    """
    config_service: ConfigurationService = get_config_service()
    try:
        # Load existing config from disk to preserve entities
        config: Configuration = config_service.load_configuration(name)

        # Only update options - entities are managed via /entities endpoints
        # This prevents the frontend from overwriting entities with stale data
        config.options = request.options
        # Explicitly preserve entities from disk
        logger.debug(f"Updating config '{name}': preserving {len(config.entities)} entities from disk, " f"updating options only")

        updated_config: Configuration = config_service.save_configuration(config)
        logger.info(
            f"Updated configuration '{name}' options (entities preserved: " f"{list(updated_config.entities.keys())})",
        )
        return updated_config
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to update configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}",
        ) from e


@router.delete("/configurations/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(name: str) -> None:
    """
    Delete configuration file.

    Creates a backup before deletion.

    Args:
        name: Configuration name to delete
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config_service.delete_configuration(name)
        logger.info(f"Deleted configuration '{name}'")
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to delete configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}",
        ) from e


@router.post("/configurations/{name}/validate", response_model=ValidationResult)
async def validate_configuration(name: str) -> ValidationResult:
    """
    Validate configuration against specifications.

    Checks for:
    - Required fields
    - Entity references
    - Circular dependencies
    - Foreign key configurations
    - Data source availability

    Args:
        name: Configuration name to validate

    Returns:
        Validation result with errors and warnings
    """
    config_service: ConfigurationService = get_config_service()
    validation_service: ValidationService = get_validation_service()

    try:
        # Load configuration
        config: Configuration = config_service.load_configuration(name)

        # Build config dict for validation
        config_data = {"entities": config.entities, "options": config.options}

        # Validate
        result = validation_service.validate_configuration(config_data)
        logger.info(f"Validated configuration '{name}': {'valid' if result.is_valid else 'invalid'}")
        return result
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to validate configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}",
        ) from e


@router.get("/configurations/{name}/backups", response_model=list[BackupInfo])
async def list_backups(name: str) -> list[BackupInfo]:
    """
    List all backup files for a configuration.

    Returns backups sorted by creation time (newest first).

    Args:
        name: Configuration name

    Returns:
        List of backup file information
    """
    yaml_service: YamlService = get_yaml_service()
    try:
        backups: list[Path] = yaml_service.list_backups(f"{name}.yml")
        backup_infos = [
            BackupInfo(
                file_name=backup.name,
                file_path=str(backup),
                created_at=backup.stat().st_mtime,
            )
            for backup in backups
        ]
        logger.debug(f"Listed {len(backup_infos)} backup(s) for '{name}'")
        return backup_infos
    except Exception as e:
        logger.error(f"Failed to list backups for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backups: {str(e)}",
        ) from e


@router.post("/configurations/{name}/restore", response_model=Configuration)
async def restore_backup(name: str, request: RestoreBackupRequest) -> Configuration:
    """
    Restore configuration from backup file.

    Creates a backup of current file before restoring.

    Args:
        name: Configuration name
        request: Backup file path to restore from

    Returns:
        Restored configuration
    """
    # config_service = get_config_service()
    yaml_service: YamlService = get_yaml_service()

    try:

        # Build target path in CONFIGURATIONS_DIR
        target_path: Path = settings.CONFIGURATIONS_DIR / f"{name}.yml"

        # Restore backup - this writes to target_path
        yaml_service.restore_backup(request.backup_path, str(target_path), create_backup=True)

        # Load configuration directly from the target path to avoid cache issues
        restored_data = yaml_service.load(target_path)

        # Build Configuration with proper metadata
        stat = target_path.stat()
        config = Configuration(
            metadata=ConfigMetadata(
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

        logger.info(f"Restored configuration '{name}' from backup")
        return config
    except YamlServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to restore configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore configuration: {str(e)}",
        ) from e


@router.get("/configurations/active/name", response_model=dict[str, str | None])
async def get_active_configuration() -> dict[str, str | None]:
    """
    Get the currently active configuration name.

    The active configuration determines which data sources are available
    in the Data Sources view.

    Returns:
        Dictionary with 'name' key containing the active configuration filename
        (without .yml extension), or null if no configuration is loaded.
    """
    config_service: ConfigurationService = get_config_service()
    try:
        active_name: str | None = config_service.get_active_configuration_name()
        return {"name": active_name}
    except Exception as e:
        logger.error(f"Failed to get active configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active configuration: {str(e)}",
        ) from e


@router.post("/configurations/{name}/activate", response_model=Configuration)
async def activate_configuration(name: str) -> Configuration:
    """
    Activate (load) a configuration into the backend context.

    This makes the configuration's data sources available in the Data Sources view
    and sets it as the active configuration for all data source operations.

    Args:
        name: Configuration name to activate

    Returns:
        The activated configuration
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config: Configuration = config_service.activate_configuration(name)
        logger.info(f"Activated configuration '{name}'")
        return config
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to activate configuration '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate configuration: {str(e)}",
        ) from e


# Data Source Connection Endpoints


class DataSourceConnectionRequest(BaseModel):
    """Request to connect a data source to a configuration."""

    source_name: str = Field(..., description="Name to assign to the data source in this configuration")
    source_filename: str = Field(..., description="Filename of the data source file (e.g., 'sead-options.yml')")


@router.get("/configurations/{name}/data-sources", response_model=dict[str, str])
async def get_configuration_data_sources(name: str) -> dict[str, str]:
    """
    Get all data sources connected to a configuration.

    Returns a dict mapping data source names to their filenames (or inline config).

    Args:
        name: Configuration name

    Returns:
        Dict of source_name -> "@include: filename.yml" or inline config
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config: Configuration = config_service.load_configuration(name)
        data_sources = config.options.get("data_sources", {})
        return data_sources
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get data sources for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data sources: {str(e)}",
        ) from e


@router.post("/configurations/{name}/data-sources", response_model=Configuration)
async def connect_data_source_to_configuration(name: str, request: DataSourceConnectionRequest) -> Configuration:
    """
    Connect a data source to a configuration.

    Adds an @include reference in the configuration's options.data_sources section.

    Args:
        name: Configuration name
        request: Data source connection details (name and filename)

    Returns:
        Updated configuration
    """
    config_service: ConfigurationService = get_config_service()

    try:
        # Load configuration
        config: Configuration = config_service.load_configuration(name)

        # Check if source name already exists
        data_sources = config.options.get("data_sources", {})
        if request.source_name in data_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data source '{request.source_name}' already connected to this configuration",
            )

        # Add @include reference
        data_sources[request.source_name] = f"@include: {request.source_filename}"
        config.options["data_sources"] = data_sources

        # Save configuration
        updated_config: Configuration = config_service.save_configuration(config)

        logger.info(f"Connected data source '{request.source_name}' (@include: {request.source_filename}) " f"to configuration '{name}'")

        return updated_config

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect data source to '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect data source: {str(e)}",
        ) from e


@router.delete("/configurations/{name}/data-sources/{source_name}", response_model=Configuration)
async def disconnect_data_source_from_configuration(name: str, source_name: str) -> Configuration:
    """
    Disconnect a data source from a configuration.

    Removes the data source reference from options.data_sources section.

    Args:
        name: Configuration name
        source_name: Data source name to disconnect

    Returns:
        Updated configuration
    """
    config_service: ConfigurationService = get_config_service()

    try:
        # Load configuration
        config: Configuration = config_service.load_configuration(name)

        # Check if source exists
        data_sources = config.options.get("data_sources", {})
        if source_name not in data_sources:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source '{source_name}' not found in configuration '{name}'"
            )

        # Remove data source
        del data_sources[source_name]
        config.options["data_sources"] = data_sources

        # Save configuration
        updated_config: Configuration = config_service.save_configuration(config)

        logger.info(f"Disconnected data source '{source_name}' from configuration '{name}'")

        return updated_config

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect data source from '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect data source: {str(e)}",
        ) from e
