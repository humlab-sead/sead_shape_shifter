"""Tests for reconciliation mappers."""

from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models import reconciliation as api
from src.reconciliation import model as core


class TestReconciliationSourceMapper:
    """Test ReconciliationSource DTO <-> Domain mapping."""

    def test_source_to_domain(self):
        """Test converting source DTO to domain."""
        dto = api.ReconciliationSource(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        domain: core.ResolutionSource = ReconciliationMapper.source_to_domain(dto)

        assert isinstance(domain, core.ResolutionSource)
        assert domain.data_source == "test_db"
        assert domain.type == "sql"
        assert domain.query == "SELECT * FROM test"

    def test_source_to_dto(self):
        """Test converting source domain to DTO."""
        domain = core.ResolutionSource(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        dto = ReconciliationMapper.source_to_dto(domain)

        assert isinstance(dto, api.ReconciliationSource)
        assert dto.data_source == "test_db"
        assert dto.type == "sql"
        assert dto.query == "SELECT * FROM test"

    def test_source_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = api.ReconciliationSource(
            data_source="test_db",
            type="sql",
            query="SELECT * FROM test",
        )

        domain: core.ResolutionSource = ReconciliationMapper.source_to_domain(original)
        result: api.ReconciliationSource = ReconciliationMapper.source_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestReconciliationRemoteMapper:
    """Test ReconciliationRemote DTO <-> Domain mapping."""

    def test_remote_to_domain(self):
        """Test converting remote DTO to domain."""
        dto = api.ReconciliationRemote(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        domain: core.ResolutionTarget = ReconciliationMapper.remote_to_domain(dto)

        assert isinstance(domain, core.ResolutionTarget)
        assert domain.service_type == "site"
        assert domain.columns == ["latitude", "longitude"]

    def test_remote_to_dto(self):
        """Test converting remote domain to DTO."""
        domain = core.ResolutionTarget(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        dto: api.ReconciliationRemote = ReconciliationMapper.remote_to_dto(domain)

        assert isinstance(dto, api.ReconciliationRemote)
        assert dto.service_type == "site"
        assert dto.columns == ["latitude", "longitude"]

    def test_remote_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = api.ReconciliationRemote(
            service_type="site",
            columns=["latitude", "longitude"],
        )

        domain: core.ResolutionTarget = ReconciliationMapper.remote_to_domain(original)
        result: api.ReconciliationRemote = ReconciliationMapper.remote_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestEntityResolutionItemMapper:
    """Test EntityResolutionItem DTO <-> Domain mapping."""

    def test_mapping_item_to_domain(self):
        """Test converting mapping item DTO to domain."""
        dto = api.ResolvedEntityPair(
            source_value="Test Site",
            target_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        domain: core.ResolvedEntityPair = ReconciliationMapper.mapping_item_to_domain(dto)

        assert isinstance(domain, core.ResolvedEntityPair)
        assert domain.source_value == "Test Site"
        assert domain.target_id == 123
        assert domain.confidence == 0.95
        assert domain.notes == "Auto-matched"
        assert domain.will_not_match is False

    def test_mapping_item_to_dto(self):
        """Test converting mapping item domain to DTO."""
        domain = core.ResolvedEntityPair(
            source_value="Test Site",
            target_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        dto: api.ResolvedEntityPair = ReconciliationMapper.mapping_item_to_dto(domain)

        assert isinstance(dto, api.ResolvedEntityPair)
        assert dto.source_value == "Test Site"
        assert dto.target_id == 123
        assert dto.confidence == 0.95
        assert dto.notes == "Auto-matched"

    def test_mapping_item_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = api.ResolvedEntityPair(
            source_value="Test Site",
            target_id=123,
            confidence=0.95,
            notes="Auto-matched",
            will_not_match=False,
            created_at="2024-01-01T00:00:00Z",
            created_by="system",
            last_modified="2024-01-01T00:00:00Z",
        )

        domain: core.ResolvedEntityPair = ReconciliationMapper.mapping_item_to_domain(original)
        result = ReconciliationMapper.mapping_item_to_dto(domain)

        assert result.model_dump() == original.model_dump()


class TestEntityResolutionMapper:
    """Test EntityResolution DTO <-> Domain mapping."""

    def test_entity_mapping_to_domain_simple(self):
        """Test converting entity mapping DTO to domain with string source."""
        dto = api.EntityResolutionSet(
            source="another_entity",
            property_mappings={"lat": "latitude", "lon": "longitude"},
            remote=api.ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[
                api.ResolvedEntityPair(
                    source_value="Test",
                    target_id=123,
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

        assert isinstance(domain, core.EntityResolutionSet)
        assert domain.metadata is not None
        assert domain.metadata.source == "another_entity"
        assert domain.metadata.property_mappings == {"lat": "latitude", "lon": "longitude"}
        assert domain.metadata.auto_accept_threshold == 0.95
        assert len(domain.links) == 1

    def test_entity_mapping_to_domain_with_custom_source(self):
        """Test converting entity mapping with custom ReconciliationSource."""
        dto = api.EntityResolutionSet(
            source=api.ReconciliationSource(
                data_source="test_db",
                type="sql",
                query="SELECT * FROM test",
            ),
            property_mappings={},
            remote=api.ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        domain = ReconciliationMapper.entity_mapping_to_domain(dto)

        assert isinstance(domain, core.EntityResolutionSet)
        assert isinstance(domain.metadata.source, core.ResolutionSource)
        assert domain.metadata.source.data_source == "test_db"

    def test_entity_mapping_to_dto(self):
        """Test converting entity mapping domain to DTO."""
        domain = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source="another_entity",
                property_mappings={"lat": "latitude"},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
            links=[core.ResolvedEntityPair(source_value="Test", target_id=123, confidence=0.98)],
        )

        dto = ReconciliationMapper.entity_mapping_to_dto(domain)

        assert isinstance(dto, api.EntityResolutionSet)
        assert dto.source == "another_entity"
        assert dto.property_mappings == {"lat": "latitude"}
        assert len(dto.mapping) == 1

    def test_entity_mapping_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = api.EntityResolutionSet(
            source=None,
            property_mappings={"lat": "latitude"},
            remote=api.ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[
                api.ResolvedEntityPair(
                    source_value="Test",
                    target_id=123,
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


class TestEntityResolutionRegistryMapper:
    """Test EntityResolutionRegistry DTO <-> Domain mapping."""

    def test_registry_to_domain(self):
        """Test converting registry DTO to domain."""
        dto = api.EntityResolutionCatalog(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": api.EntityResolutionSet(
                        remote=api.ReconciliationRemote(service_type="site", columns=["latitude", "longitude"]),
                        mapping=[
                            api.ResolvedEntityPair(
                                source_value="Test",
                                target_id=123,
                                confidence=0.98,
                                notes="Auto-matched",
                                will_not_match=False,
                                created_at="2024-01-01T00:00:00Z",
                                created_by="system",
                                last_modified="2024-01-01T00:00:00Z",
                            )
                        ],
                        source=api.ReconciliationSource(
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

        assert isinstance(domain, core.EntityResolutionCatalog)
        assert domain.version == "2.0"
        assert domain.service_url == "http://localhost:8000"
        assert "site" in domain.entities
        assert "site_name" in domain.entities["site"]
        assert len(domain.entities["site"]["site_name"].links) == 1

    def test_registry_to_dto(self):
        """Test converting registry domain to DTO."""
        domain = core.EntityResolutionCatalog(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": core.EntityResolutionSet(
                        metadata=core.EntityResolutionMetadata(remote=core.ResolutionTarget(service_type="site")),
                        links=[core.ResolvedEntityPair(source_value="Test", target_id=123)],
                    )
                }
            },
        )

        dto = ReconciliationMapper.registry_to_dto(domain)

        assert isinstance(dto, api.EntityResolutionCatalog)
        assert dto.version == "2.0"
        assert dto.service_url == "http://localhost:8000"
        assert "site" in dto.entities
        assert "site_name" in dto.entities["site"]
        assert len(dto.entities["site"]["site_name"].mapping) == 1

    def test_registry_roundtrip(self):
        """Test DTO -> Domain -> DTO roundtrip."""
        original = api.EntityResolutionCatalog(
            version="2.0",
            service_url="http://localhost:8000",
            entities={
                "site": {
                    "site_name": api.EntityResolutionSet(
                        remote=api.ReconciliationRemote(service_type="site"),
                        mapping=[
                            api.ResolvedEntityPair(
                                source_value="Test",
                                target_id=123,
                                confidence=0.98,
                                notes="Auto-matched",
                                will_not_match=False,
                                created_at="2024-01-01T00:00:00Z",
                                created_by="system",
                                last_modified="2024-01-01T00:00:00Z",
                            )
                        ],
                        source=api.ReconciliationSource(
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
        mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                remote=core.ResolutionTarget(service_type="site"),
            ),
        )

        item = core.ResolvedEntityPair(source_value="Test", target_id=123)
        mapping.add(item)

        assert len(mapping.links) == 1
        assert mapping.links[0].source_value == "Test"

        # Adding another item with same source_value should replace
        item2 = core.ResolvedEntityPair(source_value="Test", target_id=456)
        mapping.add(item2)

        assert len(mapping.links) == 1
        assert mapping.links[0].target_id == 456

    def test_entity_mapping_remove_item(self):
        """Test removing mapping item from entity mapping."""
        mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                remote=core.ResolutionTarget(service_type="site"),
            ),
            links=[
                core.ResolvedEntityPair(source_value="Test1", target_id=123),
                core.ResolvedEntityPair(source_value="Test2", target_id=456),
            ],
        )

        result = mapping.remove("Test1")

        assert result is True
        assert len(mapping.links) == 1
        assert mapping.links[0].source_value == "Test2"

        # Removing non-existent item
        result = mapping.remove("NonExistent")
        assert result is False

    def test_entity_mapping_get_item(self):
        """Test getting mapping item by source value."""
        mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                remote=core.ResolutionTarget(service_type="site"),
            ),
            links=[
                core.ResolvedEntityPair(source_value="Test1", target_id=123),
            ],
        )

        item = mapping.get("Test1")
        assert item is not None
        assert item.target_id == 123

        item = mapping.get("NonExistent")
        assert item is None

    def test_registry_add_mapping(self):
        """Test adding mapping to registry."""
        registry = core.EntityResolutionCatalog(
            version="2.0",
            service_url="http://localhost:8000",
        )

        mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                remote=core.ResolutionTarget(service_type="site"),
            ),
        )

        registry.add("site", "site_name", mapping)

        assert registry.exists("site", "site_name")
        retrieved = registry.get("site", "site_name")
        assert retrieved is mapping

    def test_registry_remove_mapping(self):
        """Test removing mapping from registry."""
        mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                remote=core.ResolutionTarget(service_type="site"),
            ),
        )

        registry = core.EntityResolutionCatalog(
            version="2.0",
            service_url="http://localhost:8000",
            entities={"site": {"site_name": mapping}},
        )

        result = registry.remove("site", "site_name")
        assert result is True
        assert not registry.exists("site", "site_name")
        assert "site" not in registry.entities  # Empty entity dict removed

        # Remove non-existent
        result = registry.remove("site", "nonexistent")
        assert result is False
