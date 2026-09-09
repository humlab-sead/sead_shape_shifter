"""Backend service for mapping sidecar CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.exceptions import ResourceNotFoundError, ValidationError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject, TableConfig
from src.reconciliation.mapping_manager import MappingManager
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource, MappingCatalog


class MappingService:
    """Read and write project mapping sidecar entries."""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service
        self.manager = MappingManager()

    @staticmethod
    def _default_local_key(table: TableConfig) -> str | list[str]:
        """Return the default local key for a project entity."""
        keys = table.safe_keys
        if not keys:
            raise ValidationError(
                message=f"Entity '{table.entity_name}' has no entity.keys configuration for mapping operations.",
                context={"entity": table.entity_name},
            )
        if len(keys) == 1:
            return keys[0]
        return keys

    @staticmethod
    def _project_path(api_project: Project, project_name: str) -> str:
        """Return the project path used for sidecar load and save operations."""
        return api_project.filename or project_name

    def _build_default_entity_mapping(self, table: TableConfig) -> EntityMapping:
        """Build default sidecar metadata from entity configuration."""
        if not table.public_id:
            raise ValidationError(
                message=f"Entity '{table.entity_name}' has no public_id configuration for mapping operations.",
                context={"entity": table.entity_name},
            )
        return EntityMapping(
            local_key=self._default_local_key(table),
            public_id=table.public_id,
            entity_type=EntityType.PRIMARY,
        )

    def _load_project_table_and_catalog(self, project_name: str, entity_name: str) -> tuple[Project, TableConfig, MappingCatalog]:
        """Load project state and mapping catalog for one entity."""
        api_project = self.project_service.load_project(project_name)
        core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        try:
            table = core_project.get_table(entity_name)
        except KeyError as exc:
            raise ResourceNotFoundError(
                message=f"Entity '{entity_name}' not found",
                resource_type="entity",
                resource_id=entity_name,
            ) from exc

        catalog = self.manager.load(self._project_path(api_project, project_name))
        return api_project, table, catalog

    def get_entity_mapping(self, project_name: str, entity_name: str) -> EntityMapping:
        """Return sidecar mapping metadata and links for one entity."""
        _api_project, table, catalog = self._load_project_table_and_catalog(project_name, entity_name)
        return self.manager.get_entity(catalog, entity_name) or self._build_default_entity_mapping(table)

    def get_link(self, project_name: str, entity_name: str, local_key_value: str) -> tuple[EntityMapping, Link]:
        """Return one link for an entity and local-key pair."""
        _api_project, table, catalog = self._load_project_table_and_catalog(project_name, entity_name)
        entity_mapping = self.manager.get_entity(catalog, entity_name) or self._build_default_entity_mapping(table)
        link = self.manager.get_link(catalog, entity_name, local_key_value)
        if link is None:
            raise ResourceNotFoundError(
                message=f"Mapping link '{local_key_value}' not found for entity '{entity_name}'",
                resource_type="mapping-link",
                resource_id=f"{entity_name}:{local_key_value}",
            )
        return entity_mapping, link

    def put_link(
        self,
        project_name: str,
        entity_name: str,
        local_key_value: str,
        *,
        target_id: int,
        confidence: float | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> tuple[EntityMapping, Link]:
        """Create or update one manual mapping link."""
        api_project, table, catalog = self._load_project_table_and_catalog(project_name, entity_name)
        entity_mapping = self.manager.get_entity(catalog, entity_name)
        if entity_mapping is None:
            entity_mapping = self._build_default_entity_mapping(table)
            catalog.entities[entity_name] = entity_mapping

        link = Link(
            target_id=target_id,
            source=LinkSource.MANUAL,
            confidence=confidence,
            committed_at=datetime.now(timezone.utc),
            notes=notes,
            created_by=created_by or get_correlation_id(),
        )
        self.manager.set_link(catalog, entity_name, local_key_value, link)
        self.manager.save(catalog, self._project_path(api_project, project_name))
        return entity_mapping, link

    def delete_link(self, project_name: str, entity_name: str, local_key_value: str) -> None:
        """Delete one mapping link for an entity and local-key pair."""
        api_project, _table, catalog = self._load_project_table_and_catalog(project_name, entity_name)
        deleted = self.manager.delete_link(catalog, entity_name, local_key_value)
        if not deleted:
            raise ResourceNotFoundError(
                message=f"Mapping link '{local_key_value}' not found for entity '{entity_name}'",
                resource_type="mapping-link",
                resource_id=f"{entity_name}:{local_key_value}",
            )
        self.manager.save(catalog, self._project_path(api_project, project_name))
