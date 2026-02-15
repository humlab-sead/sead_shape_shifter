"""Entity mapping registry management."""

from __future__ import annotations

from pathlib import Path

import yaml
from loguru import logger

from backend.app.core.config import settings
from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models import reconciliation as dto
from backend.app.models.project import Project
from backend.app.services import ProjectService
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.reconciliation import model as core


class EntityMappingManager:
    """
    Manager for entity resolution catalog and specification CRUD operations.

    Handles:
    - Loading and saving entity resolution catalog configuration files (YAML)
    - CRUD operations for entity resolution catalog specifications
    - Configuration file persistence and lifecycle management

    Query and introspection operations (like schema inspection) are handled by ReconciliationService.
    """

    def __init__(self, project_service: ProjectService, config_dir: Path):
        """
        Initialize entity resolution catalog manager.

        Args:
            project_service: Project service instance
            config_dir: Directory containing project configuration files
        """
        self.project_service: ProjectService = project_service
        self.config_dir = Path(config_dir)

    def _get_default_catalog_filename(self, project_name: str) -> Path:
        """Get path to reconciliation YAML file."""
        return self.config_dir / project_name / f"{project_name}-reconciliation.yml"

    def load_catalog(self, project_name: str, filename: Path | None = None) -> core.EntityResolutionCatalog:
        """
        Load entity resolution catalog from YAML file.

        Maps from YAML → DTO → Domain at the persistence boundary.

        Args:
            project_name: Project name
            filename: Optional custom config file path

        Returns:
            Entity resolution catalog domain model
        """
        filename = filename or self._get_default_catalog_filename(project_name)

        if not filename.exists():
            logger.info(f"No reconciliation config found for '{project_name}', creating empty config")
            dto_catalog = dto.EntityResolutionCatalog(service_url=settings.reconciliation_service_url, entities={}, version="2.0")
            return ReconciliationMapper.registry_to_domain(dto_catalog)

        logger.debug(f"Loading reconciliation config from {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Map: YAML dict → DTO (Pydantic validation) → Domain
        dto_catalog = dto.EntityResolutionCatalog(**data)
        return ReconciliationMapper.registry_to_domain(dto_catalog)

    def save_catalog(self, project_name: str, catalog: core.EntityResolutionCatalog, filename: Path | None = None) -> None:
        """
        Save entity resolution catalog to YAML file.

        Maps from Domain → DTO → YAML at the persistence boundary.

        Args:
            project_name: Project name
            catalog: Entity resolution catalog domain model to save
            filename: Optional custom config file path
        """
        filename = filename or self._get_default_catalog_filename(project_name)

        # Map: Domain → DTO → YAML dict
        dto_catalog: dto.EntityResolutionCatalog = ReconciliationMapper.registry_to_dto(catalog)

        logger.info(f"Saving reconciliation config to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            yaml.dump(dto_catalog.model_dump(exclude_none=True), f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def list_entity_mappings(self, project_name: str) -> list[dto.EntityResolutionListItem]:
        """
        List all entity mappings for a project (flattened view).

        Works with domain models internally, returns DTOs for API contract.

        Args:
            project_name: Project name

        Returns:
            List of flattened entity mapping items (DTOs)
        """
        catalog: core.EntityResolutionCatalog = self.load_catalog(project_name)
        entity_mappings = []

        for entity_name, target_mappings in catalog.entities.items():
            for target_field, mapping_domain in target_mappings.items():
                # Map domain model to DTO for list item
                mapping_dto: dto.EntityResolutionSet = ReconciliationMapper.entity_mapping_to_dto(mapping_domain)

                entity_mappings.append(
                    dto.EntityResolutionListItem(
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

    def create_entity_mapping(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        entity_mapping: core.EntityResolutionSet,
    ) -> core.EntityResolutionCatalog:
        """
        Create a new entity resolution mapping.

        Works with domain models throughout.

        Args:
            project_name: Project name
            entity_name: Entity name (must exist in project)
            target_field: Target field name
            entity_mapping: Entity resolution set domain model

        Returns:
            Updated entity resolution catalog (domain model)

        Raises:
            BadRequestError: If entity mapping already exists or entity doesn't exist
        """
        # Verify entity exists in project
        project: Project = self.project_service.load_project(project_name)
        entity_exists: bool = entity_name in project.entities

        if not entity_exists:
            raise BadRequestError(f"Entity '{entity_name}' does not exist in project '{project_name}'")

        # Load registry (now returns domain model)
        catalog: core.EntityResolutionCatalog = self.load_catalog(project_name)

        # Check if entity mapping already exists using domain model method
        if catalog.exists(entity_name, target_field):
            raise BadRequestError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' already exists")

        # Ensure mapping is empty for new entity mapping
        entity_mapping.links = []

        # Add entity mapping to registry using domain model method
        catalog.add(entity_name, target_field, entity_mapping)

        # Save and return
        self.save_catalog(project_name, catalog)
        logger.info(f"Created entity mapping for {entity_name}.{target_field}")
        return catalog

    def update_entity_mapping(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source: "str | core.ResolutionSource | None",
        property_mappings: dict[str, str],
        remote: core.ResolutionTarget,
        auto_accept_threshold: float,
        review_threshold: float,
    ) -> core.EntityResolutionCatalog:
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
        catalog: core.EntityResolutionCatalog = self.load_catalog(project_name)
        if not catalog.exists(entity_name, target_field):
            raise NotFoundError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' not found")

        mapping: core.EntityResolutionSet | None = catalog.get(entity_name, target_field)

        assert mapping is not None  # Should never be None here since we checked existence

        mapping.metadata = core.EntityResolutionMetadata(
            source=source,
            property_mappings=property_mappings,
            remote=remote,
            auto_accept_threshold=auto_accept_threshold,
            review_threshold=review_threshold,
        )

        # Save and return
        self.save_catalog(project_name, catalog)
        logger.info(f"Updated metadata for entity mapping {entity_name}.{target_field}")
        return catalog

    def delete(self, project_name: str, entity_name: str, target_field: str, force: bool = False) -> core.EntityResolutionCatalog:
        """
        Delete an entity-field resolution set from resolution catalog.

        Works with domain models throughout.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name
            force: If False, raises error if catalog has mappings

        Returns:
            Updated entity mapping catalog (domain model)

        Raises:
            NotFoundError: If mapping catalog doesn't exist
            BadRequestError: If mapping catalog has mappings and force=False
        """
        catalog: core.EntityResolutionCatalog = self.load_catalog(project_name)

        # Check if catalog exists using domain model method
        mapping: core.EntityResolutionSet | None = catalog.get(entity_name, target_field)
        if mapping is None:
            raise NotFoundError(f"Mapping catalog for entity '{entity_name}' and target field '{target_field}' not found")

        # Check for existing mappings using domain model method
        if not mapping.is_empty() and not force:
            raise BadRequestError(f"Cannot delete existing mapping {mapping.count()} from catalog. " "Use force=True to delete anyway.")

        # Delete catalog using domain model method
        mapping_count: int = mapping.count()
        catalog.remove(entity_name, target_field)

        # Save and return
        self.save_catalog(project_name, catalog)
        logger.info(
            f"Deleted {entity_name}.{target_field} from catalog "
            f"({mapping_count} mappings {'forcefully removed' if force else 'removed'})"
        )
        return catalog
