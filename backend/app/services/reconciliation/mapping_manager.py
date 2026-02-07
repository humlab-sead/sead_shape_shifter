"""Entity mapping registry management."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from backend.app.core.config import settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models import EntityMappingRegistry, EntityMapping, ReconciliationRemote, EntityMappingListItem
from backend.app.models.project import Project
from backend.app.services import ProjectService
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.model import ShapeShiftProject

if TYPE_CHECKING:
    from backend.app.models import ReconciliationSource


class EntityMappingManager:
    """
    Manager for entity mapping registry and specification CRUD operations.
    
    Handles:
    - Loading and saving entity mapping configuration files (YAML)
    - CRUD operations for entity mapping specifications
    - Configuration file persistence and lifecycle management
    
    Query and introspection operations (like schema inspection) are handled by ReconciliationService.
    """

    def __init__(
        self,
        project_service: ProjectService,
        config_dir: Path,
    ):
        """
        Initialize entity mapping manager.

        Args:
            project_service: Project service instance
            config_dir: Directory containing project configuration files
        """
        self.project_service: ProjectService = project_service
        self.config_dir = Path(config_dir)

    def _get_default_registry_filename(self, project_name: str) -> Path:
        """Get path to reconciliation YAML file."""
        return self.config_dir / f"{project_name}-reconciliation.yml"

    def load_registry(self, project_name: str, filename: Path | None = None) -> EntityMappingRegistry:
        """
        Load entity mapping registry from YAML file.

        Args:
            project_name: Project name
            filename: Optional custom config file path

        Returns:
            Entity mapping registry
        """
        filename = filename or self._get_default_registry_filename(project_name)

        if not filename.exists():
            logger.info(f"No reconciliation config found for '{project_name}', creating empty config")
            return EntityMappingRegistry(service_url=settings.reconciliation_service_url, entities={}, version="2.0")

        logger.debug(f"Loading reconciliation config from {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return EntityMappingRegistry(**data)

    def save_registry(
        self, project_name: str, mapping_registry: EntityMappingRegistry, filename: Path | None = None
    ) -> None:
        """
        Save entity mapping registry to YAML file.

        Args:
            project_name: Project name
            mapping_registry: Entity mapping registry to save
            filename: Optional custom config file path
        """
        filename = filename or self._get_default_registry_filename(project_name)

        logger.info(f"Saving reconciliation config to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            yaml.dump(
                mapping_registry.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    def list_entity_mappings(self, project_name: str) -> list[EntityMappingListItem]:
        """
        List all entity mappings for a project (flattened view).

        Args:
            project_name: Project name

        Returns:
            List of flattened list of entity mapping items
        """
        mapping_registry: EntityMappingRegistry = self.load_registry(project_name)
        entity_mappings = []

        for entity_name, target_mappings in mapping_registry.entities.items():
            for target_field, mapping in target_mappings.items():
                entity_mappings.append(
                    EntityMappingListItem(
                        entity_name=entity_name,
                        target_field=target_field,
                        source=mapping.source,
                        property_mappings=mapping.property_mappings,
                        remote=mapping.remote,
                        auto_accept_threshold=mapping.auto_accept_threshold,
                        review_threshold=mapping.review_threshold,
                        mapping_count=len(mapping.mapping),
                        property_mapping_count=len(mapping.property_mappings),
                    )
                )

        return entity_mappings

    def create_registry(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        entity_mapping: EntityMapping,
    ) -> EntityMappingRegistry:
        """
        Create a new entity mapping registry.

        Args:
            project_name: Project name
            entity_name: Entity name (must exist in project)
            target_field: Target field name
            entity_mapping: Entity mapping specification

        Returns:
            Updated entity mapping registry

        Raises:
            BadRequestError: If entity mapping already exists or entity doesn't exist
        """
        # Verify entity exists in project
        project: Project = self.project_service.load_project(project_name)
        entity_exists: bool = entity_name in project.entities

        if not entity_exists:
            raise BadRequestError(f"Entity '{entity_name}' does not exist in project '{project_name}'")

        # Load registry
        mapping_registry: EntityMappingRegistry = self.load_registry(project_name)

        # Check if entity mapping already exists
        if entity_name in mapping_registry.entities and target_field in mapping_registry.entities[entity_name]:
            raise BadRequestError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' already exists")

        # Ensure mapping is empty for new entity mapping
        entity_mapping.mapping = []

        # Add entity mapping to registry
        if entity_name not in mapping_registry.entities:
            mapping_registry.entities[entity_name] = {}

        mapping_registry.entities[entity_name][target_field] = entity_mapping

        # Save and return
        self.save_registry(project_name, mapping_registry)
        logger.info(f"Created entity mapping for {entity_name}.{target_field}")
        return mapping_registry

    def update_registry(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source: "str | ReconciliationSource | None",
        property_mappings: dict[str, str],
        remote: ReconciliationRemote,
        auto_accept_threshold: float,
        review_threshold: float,
    ) -> EntityMappingRegistry:
        """
        Update an existing entity mapping registry.

        Note: Preserves existing mappings, entity name, and target field.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name
            source: Data source specification
            property_mappings: Property mappings
            remote: Remote entity configuration
            auto_accept_threshold: Auto-accept threshold
            review_threshold: Review threshold

        Returns:
            Updated entity mapping registry

        Raises:
            NotFoundError: If entity mapping doesn't exist
        """
        mapping_registry: EntityMappingRegistry = self.load_registry(project_name)

        # Check if entity mapping exists
        if entity_name not in mapping_registry.entities or target_field not in mapping_registry.entities[entity_name]:
            raise NotFoundError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' not found")

        # Get existing entity mapping to preserve mapping
        mapping: EntityMapping = mapping_registry.entities[entity_name][target_field]

        # Update fields (preserve mapping)
        mapping.source = source
        mapping.property_mappings = property_mappings
        mapping.remote = remote
        mapping.auto_accept_threshold = auto_accept_threshold
        mapping.review_threshold = review_threshold

        # Save and return
        self.save_registry(project_name, mapping_registry)
        logger.info(f"Updated entity mapping for {entity_name}.{target_field}")
        return mapping_registry

    def delete_registry(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        force: bool = False,
    ) -> EntityMappingRegistry:
        """
        Delete an entity mapping registry.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name
            force: If False, raises error if registry has mappings

        Returns:
            Updated entity mapping registry

        Raises:
            NotFoundError: If mapping registry doesn't exist
            BadRequestError: If mapping registry has mappings and force=False
        """
        mapping_registry: EntityMappingRegistry = self.load_registry(project_name)

        # Check if registry exists
        if entity_name not in mapping_registry.entities or target_field not in mapping_registry.entities[entity_name]:
            raise NotFoundError(f"Mapping registry for entity '{entity_name}' and target field '{target_field}' not found")

        # Check for existing mappings
        mapping: EntityMapping = mapping_registry.entities[entity_name][target_field]
        if mapping.mapping and not force:
            raise BadRequestError(
                f"Cannot delete existing mapping {len(mapping.mapping)} from registry. " "Use force=True to delete anyway."
            )

        # Delete registry
        del mapping_registry.entities[entity_name][target_field]

        # Clean up empty entity dict
        if not mapping_registry.entities[entity_name]:
            del mapping_registry.entities[entity_name]

        # Save and return
        self.save_registry(project_name, mapping_registry)
        logger.info(
            f"Deleted {entity_name}.{target_field} from registry "
            f"({len(mapping.mapping)} mappings {'forcefully removed' if force else 'removed'})"
        )
        return mapping_registry
