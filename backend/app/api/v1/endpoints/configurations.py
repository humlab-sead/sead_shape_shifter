"""API endpoints for configuration management."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from app.models.config import ConfigMetadata, Configuration
from app.models.validation import ValidationResult
from app.services.config_service import (
    ConfigurationNotFoundError,
    ConfigurationServiceError,
    get_config_service,
)
from app.services.validation_service import get_validation_service
from app.services.yaml_service import YamlServiceError, get_yaml_service

router = APIRouter()


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
    config_service = get_config_service()
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
    config_service = get_config_service()
    try:
        config = config_service.load_configuration(name)
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
    config_service = get_config_service()
    try:
        config = config_service.create_configuration(request.name, request.entities)
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

    Args:
        name: Configuration name
        request: Updated entities and options

    Returns:
        Updated configuration with new metadata
    """
    config_service = get_config_service()
    try:
        # Load existing config
        config = config_service.load_configuration(name)

        # Update entities and options
        config.entities = request.entities
        config.options = request.options

        # Save changes
        updated_config = config_service.save_configuration(config)
        logger.info(f"Updated configuration '{name}'")
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
    config_service = get_config_service()
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
    config_service = get_config_service()
    validation_service = get_validation_service()

    try:
        # Load configuration
        config = config_service.load_configuration(name)

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
    yaml_service = get_yaml_service()
    try:
        backups = yaml_service.list_backups(f"{name}.yml")
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
    config_service = get_config_service()
    yaml_service = get_yaml_service()

    try:
        from pathlib import Path

        from app.core.config import settings

        # Build target path in CONFIGURATIONS_DIR
        target_path = settings.CONFIGURATIONS_DIR / f"{name}.yml"

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
