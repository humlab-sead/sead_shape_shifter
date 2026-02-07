"""Entity mapping registry management."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from backend.app.core.config import settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models import EntityMappingRegistry, EntityMapping, ReconciliationRemote, EntityMappingListItem
from backend.app.models.project import Project
from backend.app.services import ProjectService
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.model import ShapeShiftProject
from src.reconciliation.model import (
    EntityMappingRegistryDomain,
    EntityMappingDomain,
    ReconciliationRemoteDomain,
    ReconciliationSourceDomain,
)

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

    def load_registry(self, project_name: str, filename: Path | None = None) -> EntityMappingRegistryDomain:
        """
        Load entity mapping registry from YAML file.

        Maps from YAML → DTO → Domain at the persistence boundary.

        Args:
            project_name: Project name
            filename: Optional custom config file path

        Returns:
            Entity mapping registry domain model
        """
        filename = filename or self._get_default_registry_filename(project_name)

        if not filename.exists():
            logger.info(f"No reconciliation config found for '{project_name}', creating empty config")
            dto = EntityMappingRegistry(service_url=settings.reconciliation_service_url, entities={}, version="2.0")
            return ReconciliationMapper.registry_to_domain(dto)

        logger.debug(f"Loading reconciliation config from {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Map: YAML dict → DTO (Pydantic validation) → Domain
        dto = EntityMappingRegistry(**data)
        return ReconciliationMapper.registry_to_domain(dto)

    def save_registry(
        self, project_name: str, mapping_registry: EntityMappingRegistryDomain, filename: Path | None = None
    ) -> None:
        """
        Save entity mapping registry to YAML file.

        Maps from Domain → DTO → YAML at the persistence boundary.

        Args:
            project_name: Project name
            mapping_registry: Entity mapping registry domain model to save
            filename: Optional custom config file path
        """
        filename = filename or self._get_default_registry_filename(project_name)

        # Map: Domain → DTO → YAML dict
        dto = ReconciliationMapper.registry_to_dto(mapping_registry)

        logger.info(f"Saving reconciliation config to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            yaml.dump(
                dto.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    def list_entity_mappings(self, project_name: str) -> list[EntityMappingListItem]:
        """
        List all entity mappings for a project (flattened view).

        Works with domain models internally, returns DTOs for API contract.

        Args:
            project_name: Project name

        Returns:
            List of flattened entity mapping items (DTOs)
        """
        mapping_registry_domain: EntityMappingRegistryDomain = self.load_registry(project_name)
        entity_mappings = []

        for entity_name, target_mappings in mapping_registry_domain.entities.items():
            for target_field, mapping_domain in target_mappings.items():
                # Map domain model to DTO for list item
                mapping_dto = ReconciliationMapper.entity_mapping_to_dto(mapping_domain)
                
                entity_mappings.append(
                    EntityMappingListItem(
                        entity_name=entity_name,
                        target_field=target_field,
                        source=mapping_dto.source,
                        property_mappings=mapping_dto.property_mappings,
                        remote=mapping_dto.remote,
                        auto_accept_threshold=mapping_dto.auto_accept_threshold,
                        review_threshold=mapping_dto.review_threshold,
                        mapping_count=len(mapping_dto.mapping),
                        property_mapping_count=len(mapping_dto.property_mappings),
                    )
                )

        return entity_mappings

    def create_registry(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        entity_mapping: EntityMappingDomain,
    ) -> EntityMappingRegistryDomain:
        """
        Create a new entity mapping registry.

        Works with domain models throughout.

        Args:
            project_name: Project name
            entity_name: Entity name (must exist in project)
            target_field: Target field name
            entity_mapping: Entity mapping domain model

        Returns:
            Updated entity mapping registry (domain model)

        Raises:
            BadRequestError: If entity mapping already exists or entity doesn't exist
        """
        # Verify entity exists in project
        project: Project = self.project_service.load_project(project_name)
        entity_exists: bool = entity_name in project.entities

        if not entity_exists:
            raise BadRequestError(f"Entity '{entity_name}' does not exist in project '{project_name}'")

        # Load registry (now returns domain model)
        mapping_registry: EntityMappingRegistryDomain = self.load_registry(project_name)

        # Check if entity mapping already exists using domain model method
        if mapping_registry.has_mapping(entity_name, target_field):
            raise BadRequestError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' already exists")

        # Ensure mapping is empty for new entity mapping
        entity_mapping.mapping = []

        # Add entity mapping to registry using domain model method
        mapping_registry.add_mapping(entity_name, target_field, entity_mapping)

        # Save and return
        self.save_registry(project_name, mapping_registry)
        logger.info(f"Created entity mapping for {entity_name}.{target_field}")
        return mapping_registry

    def update_registry(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source: "str | ReconciliationSourceDomain | None",
        property_mappings: dict[str, str],
        remote: ReconciliationRemoteDomain,
        auto_accept_threshold: float,
        review_threshold: float,
    ) -> EntityMappingRegistryDomain:
        """
        Update an existing entity mapping registry.

        Works with domain models throughout. Preserves existing mappings, entity name, and target field.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name
            source: Data source specification (domain model)
            property_mappings: Property mappings
            remote: Remote entity configuration (domain model)
            auto_accept_threshold: Auto-accept threshold
            review_threshold: Review threshold

        Returns:
            Updated entity mapping registry (domain model)

        Raises:
            NotFoundError: If entity mapping doesn't exist
        """
        mapping_registry: EntityMappingRegistryDomain = self.load_registry(project_name)

        # Check if entity mapping exists using domain model method
        existing_mapping = mapping_registry.get_mapping(entity_name, target_field)
        if existing_mapping is None:
            raise NotFoundError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' not found")

        # Update fields (preserve mapping)
        existing_mapping.source = source
        existing_mapping.property_mappings = property_mappings
        existing_mapping.remote = remote
        existing_mapping.auto_accept_threshold = auto_accept_threshold
        existing_mapping.review_threshold = review_threshold

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
    ) -> EntityMappingRegistryDomain:
        """
        Delete an entity mapping registry.

        Works with domain models throughout.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name
            force: If False, raises error if registry has mappings

        Returns:
            Updated entity mapping registry (domain model)

        Raises:
            NotFoundError: If mapping registry doesn't exist
            BadRequestError: If mapping registry has mappings and force=False
        """
        mapping_registry: EntityMappingRegistryDomain = self.load_registry(project_name)

        # Check if registry exists using domain model method
        existing_mapping = mapping_registry.get_mapping(entity_name, target_field)
        if existing_mapping is None:
            raise NotFoundError(f"Mapping registry for entity '{entity_name}' and target field '{target_field}' not found")

        # Check for existing mappings using domain model method
        if existing_mapping.has_mappings() and not force:
            raise BadRequestError(
                f"Cannot delete existing mapping {existing_mapping.mapping_count()} from registry. "
                "Use force=True to delete anyway."
            )

        # Delete registry using domain model method
        mapping_count = existing_mapping.mapping_count()
        mapping_registry.remove_mapping(entity_name, target_field)

        # Save and return
        self.save_registry(project_name, mapping_registry)
        logger.info(
            f"Deleted {entity_name}.{target_field} from registry "
            f"({mapping_count} mappings {'forcefully removed' if force else 'removed'})"
        )
        return mapping_registry
