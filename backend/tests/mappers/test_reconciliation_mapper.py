"""Tests for reconciliation mappers."""

import pytest

from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
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


class TestReconciliationSourceMapper:
    """Test ReconciliationSource DTO <-> Domain mapping."""

    def test_source_to_domain(self):
        """Test converting source DTO to domain."""
        dto = ReconciliationSource(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        domain = ReconciliationMapper.source_to_domain(dto)

        assert isinstance(domain, ReconciliationSourceDomain)
        assert domain.data_source == "test_db"
        assert domain.type == "sql"
        assert domain.query == "SELECT * FROM test"

    def test_source_to_dto(self):
        """Test converting source domain to DTO."""
        domain = ReconciliationSourceDomain(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        dto = ReconciliationMapper.source_to_dto(domain)

        assert isinstance(dto, ReconciliationSource)
        assert dto.data_source == "test_db"
        assert dto.type == "sql"
        assert dto.query == "SELECT * FROM test"

    def test_source_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = ReconciliationSource(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        domain = ReconciliationMapper.source_to_domain(original)
        result = ReconciliationMapper.source_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestReconciliationRemoteMapper:
    """Test ReconciliationRemote DTO <-> Domain mapping."""

    def test_remote_to_domain(self):
        """Test converting remote DTO to domain."""
        dto = ReconciliationRemote(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        domain = ReconciliationMapper.remote_to_domain(dto)

        assert isinstance(domain, ReconciliationRemoteDomain)
        assert domain.service_type == "site"
        assert domain.columns == ["latitude", "longitude"]

    def test_remote_to_dto(self):
        """Test converting remote domain to DTO."""
        domain = ReconciliationRemoteDomain(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        dto = ReconciliationMapper.remote_to_dto(domain)

        assert isinstance(dto, ReconciliationRemote)
        assert dto.service_type == "site"
        assert dto.columns == ["latitude", "longitude"]

    def test_remote_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = ReconciliationRemote(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        domain = ReconciliationMapper.remote_to_domain(original)
        result = ReconciliationMapper.remote_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestEntityMappingItemMapper:
    """Test EntityMappingItem DTO <-> Domain mapping."""

    def test_mapping_item_to_domain(self):
        """Test converting mapping item DTO to domain."""
        dto = EntityMappingItem(
            source_value="Test Site",
            sead_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        domain = ReconciliationMapper.mapping_item_to_domain(dto)

        assert isinstance(domain, EntityMappingItemDomain)
        assert domain.source_value == "Test Site"
        assert domain.sead_id == 123
        assert domain.confidence == 0.95
        assert domain.notes == "Auto-matched"
        assert domain.will_not_match is False

    def test_mapping_item_to_dto(self):
        """Test converting mapping item domain to DTO."""
        domain = EntityMappingItemDomain(
            source_value="Test Site",
            sead_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        dto = ReconciliationMapper.mapping_item_to_dto(domain)

        assert isinstance(dto, EntityMappingItem)
        assert dto.source_value == "Test Site"
        assert dto.sead_id == 123
        assert dto.confidence == 0.95
        assert dto.notes == "Auto-matched"

    def test_mapping_item_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = EntityMappingItem(
            source_value="Test Site",
            sead_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        domain = ReconciliationMapper.mapping_item_to_domain(original)
        result = ReconciliationMapper.mapping_item_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestEntityMappingMapper:
    """Test EntityMapping DTO <-> Domain mapping."""

    def test_entity_mapping_to_domain_simple(self):
        """Test converting entity mapping DTO to domain with string source."""
        dto = EntityMapping(
            source="another_entity",
            property_mappings={"lat": "latitude", "lon": "longitude"},
            remote=ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[
                EntityMappingItem(
                    source_value="Test",
                    sead_id=123,
                    confidence=0.98,
                    notes="Auto-matched",
                    will_not_match=False,
                    created_at="2024-01-01T00:00:00Z",
                    created_by="system",
                    last_modified="2024-01-01T00:00:00Z",
                )
            ],
        )

        domain = ReconciliationMapper.entity_mapping_to_domain(dto)

        assert isinstance(domain, EntityMappingDomain)
        assert domain.source == "another_entity"
        assert domain.property_mappings == {"lat": "latitude", "lon": "longitude"}
        assert domain.auto_accept_threshold == 0.95
        assert len(domain.mapping) == 1

    def test_entity_mapping_to_domain_with_custom_source(self):
        """Test converting entity mapping with custom ReconciliationSource."""
        dto = EntityMapping(
            source=ReconciliationSource(
                data_source="test_db",
                type="sql",
                query="SELECT * FROM test",
            ),
            property_mappings={},
            remote=ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        domain = ReconciliationMapper.entity_mapping_to_domain(dto)

        assert isinstance(domain, EntityMappingDomain)
        assert isinstance(domain.source, ReconciliationSourceDomain)
        assert domain.source.data_source == "test_db"

    def test_entity_mapping_to_dto(self):
        """Test converting entity mapping domain to DTO."""
        domain = EntityMappingDomain(
            source="another_entity",
            property_mappings={"lat": "latitude"},
            remote=ReconciliationRemoteDomain(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[EntityMappingItemDomain(source_value="Test", sead_id=123, confidence=0.98)],
        )

        dto = ReconciliationMapper.entity_mapping_to_dto(domain)

        assert isinstance(dto, EntityMapping)
        assert dto.source == "another_entity"
        assert dto.property_mappings == {"lat": "latitude"}
        assert len(dto.mapping) == 1

    def test_entity_mapping_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = EntityMapping(
            source=None,
            property_mappings={"lat": "latitude"},
            remote=ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[
                EntityMappingItem(
                    source_value="Test",
                    sead_id=123,
                    confidence=0.98,
                    notes="Auto-matched",
                    will_not_match=False,
                    created_at="2024-01-01T00:00:00Z",
                    created_by="system",
                    last_modified="2024-01-01T00:00:00Z",
                )
            ],
        )

        domain = ReconciliationMapper.entity_mapping_to_domain(original)
        result = ReconciliationMapper.entity_mapping_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestEntityMappingRegistryMapper:
    """Test EntityMappingRegistry DTO <-> Domain mapping."""

    def test_registry_to_domain(self):
        """Test converting registry DTO to domain."""
        dto = EntityMappingRegistry(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": EntityMapping(
                        remote=ReconciliationRemote(service_type="site", columns=["latitude", "longitude"]),
                        mapping=[
                            EntityMappingItem(
                                source_value="Test",
                                sead_id=123,
                                confidence=0.98,
                                notes="Auto-matched",
                                will_not_match=False,
                                created_at="2024-01-01T00:00:00Z",
                                created_by="system",
                                last_modified="2024-01-01T00:00:00Z",
                            )
                        ],
                        source=ReconciliationSource(
                            data_source="test_db",
                            type="sql",
                            query="SELECT * FROM test",
                        ),
                        property_mappings={"lat": "latitude", "lon": "longitude"},
                        auto_accept_threshold=0.95,
                        review_threshold=0.70,
                    )
                }
            },
        )

        domain = ReconciliationMapper.registry_to_domain(dto)

        assert isinstance(domain, EntityMappingRegistryDomain)
        assert domain.version == "2.0"
        assert domain.service_url == "http://localhost:8000"
        assert "site" in domain.entities
        assert "site_name" in domain.entities["site"]
        assert len(domain.entities["site"]["site_name"].mapping) == 1

    def test_registry_to_dto(self):
        """Test converting registry domain to DTO."""
        domain = EntityMappingRegistryDomain(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": EntityMappingDomain(
                        remote=ReconciliationRemoteDomain(service_type="site"),
                        mapping=[EntityMappingItemDomain(source_value="Test", sead_id=123)],
                    )
                }
            },
        )

        dto = ReconciliationMapper.registry_to_dto(domain)

        assert isinstance(dto, EntityMappingRegistry)
        assert dto.version == "2.0"
        assert dto.service_url == "http://localhost:8000"
        assert "site" in dto.entities
        assert "site_name" in dto.entities["site"]
        assert len(dto.entities["site"]["site_name"].mapping) == 1

    def test_registry_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = EntityMappingRegistry(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": EntityMapping(
                        remote=ReconciliationRemote(service_type="site"),
                        mapping=[
                            EntityMappingItem(
                                source_value="Test",
                                sead_id=123,
                                confidence=0.98,
                                notes="Auto-matched",
                                will_not_match=False,
                                created_at="2024-01-01T00:00:00Z",
                                created_by="system",
                                last_modified="2024-01-01T00:00:00Z",
                            )
                        ],
                        source=ReconciliationSource(
                            data_source="test_db",
                            type="sql",
                            query="SELECT * FROM test",
                        ),
                        property_mappings={"lat": "latitude", "lon": "longitude"},
                        auto_accept_threshold=0.95,
                        review_threshold=0.70,
                    )
                }
            },
        )

        domain = ReconciliationMapper.registry_to_domain(original)
        result = ReconciliationMapper.registry_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestDomainModelMethods:
    """Test business logic methods on domain models."""

    def test_entity_mapping_add_item(self):
        """Test adding mapping item to entity mapping."""
        mapping = EntityMappingDomain(
            remote=ReconciliationRemoteDomain(service_type="site"),
        )

        item = EntityMappingItemDomain(source_value="Test", sead_id=123)
        mapping.add_mapping_item(item)

        assert len(mapping.mapping) == 1
        assert mapping.mapping[0].source_value == "Test"

        # Adding another item with same source_value should replace
        item2 = EntityMappingItemDomain(source_value="Test", sead_id=456)
        mapping.add_mapping_item(item2)

        assert len(mapping.mapping) == 1
        assert mapping.mapping[0].sead_id == 456

    def test_entity_mapping_remove_item(self):
        """Test removing mapping item from entity mapping."""
        mapping = EntityMappingDomain(
            remote=ReconciliationRemoteDomain(service_type="site"),
            mapping=[
                EntityMappingItemDomain(source_value="Test1", sead_id=123),
                EntityMappingItemDomain(source_value="Test2", sead_id=456),
            ],
        )

        result = mapping.remove_mapping_item("Test1")

        assert result is True
        assert len(mapping.mapping) == 1
        assert mapping.mapping[0].source_value == "Test2"

        # Removing non-existent item
        result = mapping.remove_mapping_item("NonExistent")
        assert result is False

    def test_entity_mapping_get_item(self):
        """Test getting mapping item by source value."""
        mapping = EntityMappingDomain(
            remote=ReconciliationRemoteDomain(service_type="site"),
            mapping=[
                EntityMappingItemDomain(source_value="Test1", sead_id=123),
            ],
        )

        item = mapping.get_mapping_item("Test1")
        assert item is not None
        assert item.sead_id == 123

        item = mapping.get_mapping_item("NonExistent")
        assert item is None

    def test_registry_add_mapping(self):
        """Test adding mapping to registry."""
        registry = EntityMappingRegistryDomain(
            version="2.0",
            service_url="http://localhost:8000",
        )

        mapping = EntityMappingDomain(
            remote=ReconciliationRemoteDomain(service_type="site"),
        )

        registry.add_mapping("site", "site_name", mapping)

        assert registry.has_mapping("site", "site_name")
        retrieved = registry.get_mapping("site", "site_name")
        assert retrieved is mapping

    def test_registry_remove_mapping(self):
        """Test removing mapping from registry."""
        mapping = EntityMappingDomain(
            remote=ReconciliationRemoteDomain(service_type="site"),
        )

        registry = EntityMappingRegistryDomain(
            version="2.0",
            service_url="http://localhost:8000",
            entities={"site": {"site_name": mapping}},
        )

        result = registry.remove_mapping("site", "site_name")
        assert result is True
        assert not registry.has_mapping("site", "site_name")
        assert "site" not in registry.entities  # Empty entity dict removed

        # Remove non-existent
        result = registry.remove_mapping("site", "nonexistent")
        assert result is False
