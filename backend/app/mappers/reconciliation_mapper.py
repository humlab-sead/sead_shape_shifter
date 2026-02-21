"""Mappers for converting between reconciliation DTOs and domain models.

This module handles the conversion between Pydantic models (API/persistence layer)
and domain models (business logic layer), following the same pattern as ProjectMapper.
"""

from backend.app import models as api
from src.reconciliation import model as core


class ReconciliationMapper:
    """Mapper for reconciliation models between API DTOs and domain models."""

    @staticmethod
    def source_to_domain(dto: api.ReconciliationSource) -> core.ResolutionSource:
        """Convert ReconciliationSource DTO to domain model."""
        return core.ResolutionSource(
            data_source=dto.data_source,
            type=dto.type,
            query=dto.query,
        )

    @staticmethod
    def source_to_dto(domain: core.ResolutionSource) -> api.ReconciliationSource:
        """Convert ReconciliationSource domain to DTO."""
        return api.ReconciliationSource(
            data_source=domain.data_source,
            type=domain.type,
            query=domain.query,
        )

    @staticmethod
    def remote_to_domain(dto: api.ReconciliationRemote) -> core.ResolutionTarget:
        """Convert ReconciliationRemote DTO to domain model."""
        return core.ResolutionTarget(
            service_type=dto.service_type,
            columns=dto.columns.copy() if dto.columns else [],
        )

    @staticmethod
    def remote_to_dto(domain: core.ResolutionTarget) -> api.ReconciliationRemote:
        """Convert ReconciliationRemote domain to DTO."""
        return api.ReconciliationRemote(
            service_type=domain.service_type,
            columns=domain.columns.copy() if domain.columns else [],
        )

    @staticmethod
    def mapping_item_to_domain(dto: api.ResolvedEntityPair) -> core.ResolvedEntityPair:
        """Convert EntityMappingItem DTO to domain model."""
        return core.ResolvedEntityPair(
            source_value=dto.source_value,
            target_id=dto.target_id,
            confidence=dto.confidence,
            notes=dto.notes,
            will_not_match=dto.will_not_match,
            created_at=dto.created_at,
            created_by=dto.created_by,
            last_modified=dto.last_modified,
        )

    @staticmethod
    def mapping_item_to_dto(domain: core.ResolvedEntityPair) -> api.ResolvedEntityPair:
        """Convert EntityMappingItem domain to DTO."""
        return api.ResolvedEntityPair(
            source_value=domain.source_value,
            target_id=domain.target_id,
            confidence=domain.confidence,
            notes=domain.notes,
            will_not_match=domain.will_not_match,
            created_at=domain.created_at,
            created_by=domain.created_by,
            last_modified=domain.last_modified,
        )

    @staticmethod
    def entity_mapping_to_domain(dto: api.EntityResolutionSet) -> core.EntityResolutionSet:
        """Convert EntityMapping DTO to domain model."""
        # Handle source which can be None, str, or ReconciliationSource
        source_domain: str | core.ResolutionSource | None = None
        if dto.source is not None:
            if isinstance(dto.source, str):
                source_domain = dto.source
            elif isinstance(dto.source, api.ReconciliationSource):
                source_domain = ReconciliationMapper.source_to_domain(dto.source)

        return core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=source_domain,
                property_mappings=dto.property_mappings.copy() if dto.property_mappings else {},
                remote=ReconciliationMapper.remote_to_domain(dto.remote),
                auto_accept_threshold=dto.auto_accept_threshold,
                review_threshold=dto.review_threshold,
            ),
            links=[ReconciliationMapper.mapping_item_to_domain(item) for item in dto.mapping],
        )

    @staticmethod
    def entity_mapping_to_dto(domain: core.EntityResolutionSet) -> api.EntityResolutionSet:
        """Convert EntityMapping domain to DTO."""
        # Handle source which can be None, str, or ReconciliationSourceDomain
        source_dto: str | api.ReconciliationSource | None = None
        metadata: core.EntityResolutionMetadata = domain.metadata
        if metadata.source is not None:
            if isinstance(metadata.source, str):
                source_dto = metadata.source
            elif isinstance(metadata.source, core.ResolutionSource):
                source_dto = ReconciliationMapper.source_to_dto(metadata.source)

        return api.EntityResolutionSet(
            source=source_dto,
            property_mappings=metadata.property_mappings.copy() if metadata.property_mappings else {},
            remote=ReconciliationMapper.remote_to_dto(metadata.remote),
            auto_accept_threshold=metadata.auto_accept_threshold,
            review_threshold=metadata.review_threshold,
            mapping=[ReconciliationMapper.mapping_item_to_dto(item) for item in domain.links],
        )

    @staticmethod
    def registry_to_domain(dto: api.EntityResolutionCatalog) -> core.EntityResolutionCatalog:
        """Convert EntityMappingRegistry DTO to domain model."""
        entities_domain: dict[str, dict[str, core.EntityResolutionSet]] = {}

        for entity_name, fields in dto.entities.items():
            entities_domain[entity_name] = {}
            for target_field, mapping_dto in fields.items():
                entities_domain[entity_name][target_field] = ReconciliationMapper.entity_mapping_to_domain(mapping_dto)

        return core.EntityResolutionCatalog(
            version=dto.version,
            service_url=dto.service_url,
            entities=entities_domain,
        )

    @staticmethod
    def registry_to_dto(domain: core.EntityResolutionCatalog) -> api.EntityResolutionCatalog:
        """Convert EntityMappingRegistry domain to DTO."""
        entities_dto: dict[str, dict[str, api.EntityResolutionSet]] = {}

        for entity_name, fields in domain.entities.items():
            entities_dto[entity_name] = {}
            for target_field, mapping_domain in fields.items():
                entities_dto[entity_name][target_field] = ReconciliationMapper.entity_mapping_to_dto(mapping_domain)

        return api.EntityResolutionCatalog(
            version=domain.version,
            service_url=domain.service_url,
            entities=entities_dto,
        )
