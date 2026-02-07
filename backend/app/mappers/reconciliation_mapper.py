"""Mappers for converting between reconciliation DTOs and domain models.

This module handles the conversion between Pydantic models (API/persistence layer)
and domain models (business logic layer), following the same pattern as ProjectMapper.
"""

from backend.app.models.reconciliation import (
    EntityMapping,
    EntityMappingItem,
    EntityMappingRegistry,
    ReconciliationRemote,
    ReconciliationSource,
)
from src.reconciliation.model import (
    EntityMappingDomain,
    EntityMappingItemDomain,
    EntityMappingRegistryDomain,
    ReconciliationRemoteDomain,
    ReconciliationSourceDomain,
)


class ReconciliationMapper:
    """Mapper for reconciliation models between API DTOs and domain models."""

    @staticmethod
    def source_to_domain(dto: ReconciliationSource) -> ReconciliationSourceDomain:
        """Convert ReconciliationSource DTO to domain model."""
        return ReconciliationSourceDomain(
            data_source=dto.data_source,
            type=dto.type,
            query=dto.query,
        )

    @staticmethod
    def source_to_dto(domain: ReconciliationSourceDomain) -> ReconciliationSource:
        """Convert ReconciliationSource domain to DTO."""
        return ReconciliationSource(
            data_source=domain.data_source,
            type=domain.type,
            query=domain.query,
        )

    @staticmethod
    def remote_to_domain(dto: ReconciliationRemote) -> ReconciliationRemoteDomain:
        """Convert ReconciliationRemote DTO to domain model."""
        return ReconciliationRemoteDomain(
            service_type=dto.service_type,
            columns=dto.columns.copy() if dto.columns else [],
        )

    @staticmethod
    def remote_to_dto(domain: ReconciliationRemoteDomain) -> ReconciliationRemote:
        """Convert ReconciliationRemote domain to DTO."""
        return ReconciliationRemote(
            service_type=domain.service_type,
            columns=domain.columns.copy() if domain.columns else [],
        )

    @staticmethod
    def mapping_item_to_domain(dto: EntityMappingItem) -> EntityMappingItemDomain:
        """Convert EntityMappingItem DTO to domain model."""
        return EntityMappingItemDomain(
            source_value=dto.source_value,
            sead_id=dto.sead_id,
            confidence=dto.confidence,
            notes=dto.notes,
            will_not_match=dto.will_not_match,
            created_at=dto.created_at,
            created_by=dto.created_by,
            last_modified=dto.last_modified,
        )

    @staticmethod
    def mapping_item_to_dto(domain: EntityMappingItemDomain) -> EntityMappingItem:
        """Convert EntityMappingItem domain to DTO."""
        return EntityMappingItem(
            source_value=domain.source_value,
            sead_id=domain.sead_id,
            confidence=domain.confidence,
            notes=domain.notes,
            will_not_match=domain.will_not_match,
            created_at=domain.created_at,
            created_by=domain.created_by,
            last_modified=domain.last_modified,
        )

    @staticmethod
    def entity_mapping_to_domain(dto: EntityMapping) -> EntityMappingDomain:
        """Convert EntityMapping DTO to domain model."""
        # Handle source which can be None, str, or ReconciliationSource
        source_domain: str | ReconciliationSourceDomain | None = None
        if dto.source is not None:
            if isinstance(dto.source, str):
                source_domain = dto.source
            elif isinstance(dto.source, ReconciliationSource):
                source_domain = ReconciliationMapper.source_to_domain(dto.source)

        return EntityMappingDomain(
            source=source_domain,
            property_mappings=dto.property_mappings.copy() if dto.property_mappings else {},
            remote=ReconciliationMapper.remote_to_domain(dto.remote),
            auto_accept_threshold=dto.auto_accept_threshold,
            review_threshold=dto.review_threshold,
            mapping=[ReconciliationMapper.mapping_item_to_domain(item) for item in dto.mapping],
        )

    @staticmethod
    def entity_mapping_to_dto(domain: EntityMappingDomain) -> EntityMapping:
        """Convert EntityMapping domain to DTO."""
        # Handle source which can be None, str, or ReconciliationSourceDomain
        source_dto: str | ReconciliationSource | None = None
        if domain.source is not None:
            if isinstance(domain.source, str):
                source_dto = domain.source
            elif isinstance(domain.source, ReconciliationSourceDomain):
                source_dto = ReconciliationMapper.source_to_dto(domain.source)

        return EntityMapping(
            source=source_dto,
            property_mappings=domain.property_mappings.copy() if domain.property_mappings else {},
            remote=ReconciliationMapper.remote_to_dto(domain.remote),
            auto_accept_threshold=domain.auto_accept_threshold,
            review_threshold=domain.review_threshold,
            mapping=[ReconciliationMapper.mapping_item_to_dto(item) for item in domain.mapping],
        )

    @staticmethod
    def registry_to_domain(dto: EntityMappingRegistry) -> EntityMappingRegistryDomain:
        """Convert EntityMappingRegistry DTO to domain model."""
        entities_domain: dict[str, dict[str, EntityMappingDomain]] = {}
        
        for entity_name, fields in dto.entities.items():
            entities_domain[entity_name] = {}
            for target_field, mapping_dto in fields.items():
                entities_domain[entity_name][target_field] = ReconciliationMapper.entity_mapping_to_domain(mapping_dto)

        return EntityMappingRegistryDomain(
            version=dto.version,
            service_url=dto.service_url,
            entities=entities_domain,
        )

    @staticmethod
    def registry_to_dto(domain: EntityMappingRegistryDomain) -> EntityMappingRegistry:
        """Convert EntityMappingRegistry domain to DTO."""
        entities_dto: dict[str, dict[str, EntityMapping]] = {}
        
        for entity_name, fields in domain.entities.items():
            entities_dto[entity_name] = {}
            for target_field, mapping_domain in fields.items():
                entities_dto[entity_name][target_field] = ReconciliationMapper.entity_mapping_to_dto(mapping_domain)

        return EntityMappingRegistry(
            version=domain.version,
            service_url=domain.service_url,
            entities=entities_dto,
        )
