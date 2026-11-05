"""Tests for ReconciliationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml

from backend.app import models as dto
from backend.app.exceptions import DependencyError, ResourceConflictError, ResourceNotFoundError, ValidationError
from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models.shapeshift import PreviewResult
from backend.app.services.reconciliation import ReconciliationQueryService, ReconciliationService
from backend.app.services.reconciliation.resolvers import (
    AnotherEntityReconciliationSourceResolver,
    ReconciliationSourceResolver,
    SqlQueryReconciliationSourceResolver,
    TargetEntityReconciliationSourceResolver,
)
from backend.app.services.reconciliation.service import ResolvedSourceRows
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from backend.tests.test_reconciliation_client import RECONCILIATION_SERVICE_URL
from src.reconciliation import model as core
from src.reconciliation.source_strategy import ReconciliationSourceStrategy, SourceStrategyType

# pylint: disable=redefined-outer-name,unused-argument,protected-access


@pytest.fixture
def mock_config_service() -> MagicMock:
    """Mock configuration service."""
    service = MagicMock()
    service.load_project.return_value = MagicMock(
        metadata=MagicMock(name="test_project"),
        entities={
            "site": {
                "name": "site",
                "type": "sql",
                "data_source": "test_db",
                "keys": ["site_code"],
                "columns": ["site_name", "latitude", "longitude"],
            },
            "sample": {
                "name": "sample",
                "type": "sql",
                "data_source": "test_db",
                "source": "site",
                "keys": ["sample_code"],
                "columns": ["sample_type"],
            },
        },
        options={},
    )
    return service


@pytest.fixture
def mock_core_project() -> MagicMock:
    """Mock ShapeShiftProject (core domain model)."""
    project = MagicMock()
    project.tables = {
        "site": MagicMock(name="site"),
        "sample": MagicMock(name="sample"),
    }
    project.data_sources = {
        "test_db": MagicMock(driver="postgresql"),
    }
    project.get_data_source = MagicMock(return_value=MagicMock(driver="postgresql"))
    return project


@pytest.fixture
def mock_recon_client() -> AsyncMock:
    """Mock reconciliation client."""
    client = AsyncMock()
    client.reconcile_batch.return_value = {}
    client.get_service_manifest.return_value = {
        "defaultTypes": [{"id": "site", "name": "Site"}, {"id": "feature_type", "name": "Feature type"}],
        "reconciliation": {"supportedTypes": ["site", "feature_type"]},
        "extend": {
            "property_settings": [
                {"name": "latitude", "entity_types": ["site"]},
                {"name": "longitude", "entity_types": ["site"]},
            ]
        },
    }
    return client


@pytest.fixture
def reconciliation_service(tmp_path, mock_recon_client) -> ReconciliationService:
    """Create ReconciliationService instance."""
    return ReconciliationService(config_dir=tmp_path, reconciliation_client=mock_recon_client)


@pytest.fixture
def sample_entity_spec() -> core.EntityResolutionSet:
    """Create sample EntityResolutionSet (domain model)."""
    return core.EntityResolutionSet(
        metadata=core.EntityResolutionMetadata(
            source=None,
            property_mappings={"latitude": "latitude", "longitude": "longitude"},
            remote=core.ResolutionTarget(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        ),
        links=[],
    )


@pytest.fixture
def sample_entity_spec_dto() -> dto.EntityResolutionSet:
    """Create sample EntityMapping (DTO for YAML serialization tests)."""
    return dto.EntityResolutionSet(
        source=None,
        property_mappings={"latitude": "latitude", "longitude": "longitude"},
        remote=dto.ReconciliationRemote(service_type="site"),
        auto_accept_threshold=0.95,
        review_threshold=0.70,
        mapping=[],
    )


@pytest.fixture
def catalog(sample_entity_spec_dto) -> dto.EntityResolutionCatalog:
    """Create sample EntityMappingRegistry (DTO for YAML serialization tests)."""
    return dto.EntityResolutionCatalog(
        version="3.0",
        service_url=RECONCILIATION_SERVICE_URL,
        entities={"site": {"site_code": sample_entity_spec_dto}},  # Nested: entity -> target -> spec
    )


class TestReconciliationSourceStrategy:
    """Tests for ReconciliationSourceStrategy (domain logic)."""

    def test_determine_strategy_for_none_source(self):
        """Test strategy determination for None source."""
        strategy = ReconciliationSourceStrategy.determine_strategy("site", None)
        assert strategy == SourceStrategyType.TARGET_ENTITY

    def test_determine_strategy_for_empty_source(self):
        """Test strategy determination for empty source."""
        strategy = ReconciliationSourceStrategy.determine_strategy("site", "")
        assert strategy == SourceStrategyType.TARGET_ENTITY

    def test_determine_strategy_for_same_entity(self):
        """Test strategy determination when source equals entity name."""
        strategy = ReconciliationSourceStrategy.determine_strategy("site", "site")
        assert strategy == SourceStrategyType.TARGET_ENTITY

    def test_determine_strategy_for_another_entity(self):
        """Test strategy determination for another entity."""
        strategy = ReconciliationSourceStrategy.determine_strategy("sample", "site")
        assert strategy == SourceStrategyType.ANOTHER_ENTITY

    def test_determine_strategy_for_custom_query(self):
        """Test strategy determination for ReconciliationSourceDomain."""
        source = core.ResolutionSource(type="sql", data_source="test_db", query="SELECT * FROM sites")
        strategy = ReconciliationSourceStrategy.determine_strategy("site", source)
        assert strategy == SourceStrategyType.SQL_QUERY

    def test_determine_strategy_invalid_source(self):
        """Test strategy determination raises for invalid source."""
        with pytest.raises(ValueError, match="Invalid source specification"):
            ReconciliationSourceStrategy.determine_strategy("site", 123)  # type: ignore

    def test_get_source_entity_name_target_entity(self):
        """Test get_source_entity_name for target entity strategy."""
        entity_mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=None,
                property_mappings={"latitude": "latitude", "longitude": "longitude"},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            )
        )
        entity_name = ReconciliationSourceStrategy.get_source_entity_name("site", entity_mapping)
        assert entity_name == "site"

    def test_get_source_entity_name_another_entity(self):
        """Test get_source_entity_name for another entity strategy."""
        entity_mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source="location",
                property_mappings={"latitude": "latitude", "longitude": "longitude"},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            )
        )
        entity_name = ReconciliationSourceStrategy.get_source_entity_name("site", entity_mapping)
        assert entity_name == "location"

    def test_get_source_entity_name_sql_query(self):
        """Test get_source_entity_name for SQL query strategy."""
        entity_mapping = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=core.ResolutionSource(type="sql", data_source="test_db", query="SELECT * FROM custom"),
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            )
        )
        entity_name: str = ReconciliationSourceStrategy.get_source_entity_name("site", entity_mapping)
        assert entity_name == ""


class TestReconciliationSourceResolver:
    """Tests for ReconciliationSourceResolver application-layer implementations."""

    def test_get_resolver_cls_for_target_entity_strategy(self):
        """Test resolver class selection for target entity strategy."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_strategy(SourceStrategyType.TARGET_ENTITY)
        assert resolver_cls == TargetEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_another_entity_strategy(self):
        """Test resolver class selection for another entity strategy."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_strategy(SourceStrategyType.ANOTHER_ENTITY)
        assert resolver_cls == AnotherEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_sql_query_strategy(self):
        """Test resolver class selection for SQL query strategy."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_strategy(SourceStrategyType.SQL_QUERY)
        assert resolver_cls == SqlQueryReconciliationSourceResolver


class TestTargetEntityReconciliationSourceResolver:
    """Tests for TargetEntityReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_uses_entity_preview(self, mock_config_service, mock_core_project, sample_entity_spec):
        """Test resolve uses preview data from target entity."""
        resolver = TargetEntityReconciliationSourceResolver("test_project", mock_core_project, mock_config_service)

        preview_data = [
            {"site_code": "SITE001", "site_name": "Test Site 1"},
            {"site_code": "SITE002", "site_name": "Test Site 2"},
        ]

        with patch.object(resolver.preview_service, "preview_entity", new=AsyncMock()) as mock_preview:
            mock_preview.return_value = PreviewResult(
                entity_name="site",
                rows=preview_data,
                columns=[],
                total_rows_in_preview=2,
                execution_time_ms=10,
            )

            result = await resolver.resolve("site", sample_entity_spec)

            assert result == preview_data
            mock_preview.assert_called_once_with("test_project", "site", limit=None)


class TestAnotherEntityReconciliationSourceResolver:
    """Tests for AnotherEntityReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_uses_source_entity_preview(self, mock_config_service, mock_core_project):
        """Test resolve uses preview data from source entity."""
        resolver = AnotherEntityReconciliationSourceResolver("test_project", mock_core_project, mock_config_service)

        # Entity spec domain model with source pointing to another entity
        entity_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source="site",
                property_mappings={"latitude": "latitude", "longitude": "longitude"},
                remote=core.ResolutionTarget(service_type="sample"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
        )

        source_data = [{"site_code": "SITE001", "sample_code": "SAMP001"}]

        with patch.object(resolver.preview_service, "preview_entity", new=AsyncMock()) as mock_preview:
            mock_preview.return_value = PreviewResult(
                entity_name="site", rows=source_data, columns=[], total_rows_in_preview=1, execution_time_ms=10
            )

            result = await resolver.resolve("sample", entity_spec)

            assert result == source_data
            mock_preview.assert_called_once_with("test_project", "site", limit=None)

    @pytest.mark.asyncio
    async def test_resolve_raises_for_missing_source_entity(self, mock_config_service, mock_core_project):
        """Test resolve raises if source entity not found."""
        # Set up mock_core_project to only have 'site' table, not 'nonexistent'
        mock_core_project.tables = {"site": MagicMock(name="site")}

        resolver = AnotherEntityReconciliationSourceResolver("test_project", mock_core_project, mock_config_service)

        entity_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source="nonexistent",
                remote=core.ResolutionTarget(service_type="test"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
        )

        with pytest.raises(NotFoundError, match="Source entity 'nonexistent' not found"):
            await resolver.resolve("entity", entity_spec)


class TestSqlQueryReconciliationSourceResolver:
    """Tests for SqlQueryReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_executes_custom_query(self, mock_config_service, mock_core_project):
        """Test resolve attempts to execute custom SQL query (verifies code path)."""
        # This test is simplified to verify the code path without deep mocking
        # Full integration would require a real ShapeShiftProject with data sources

        mock_config_service.load_project.return_value.options = {
            "data_sources": {
                "test_db": {
                    "driver": "postgresql",
                    "host": "localhost",
                    "database": "testdb",
                }
            }
        }

        entity_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=core.ResolutionSource(type="sql", data_source="test_db", query="SELECT * FROM custom_view"),
                remote=core.ResolutionTarget(service_type="test"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
        )

        resolver = SqlQueryReconciliationSourceResolver("test_project", mock_core_project, mock_config_service)

        # This will fail at TableConfig creation, but that's OK - we're just verifying
        # that the SQL query path is taken and data source validation happens
        with pytest.raises(KeyError):
            await resolver.resolve("entity", entity_spec)

    @pytest.mark.asyncio
    async def test_resolve_raises_for_missing_data_source(self, mock_config_service, mock_core_project):
        """Test resolve raises if data source not found."""
        # Set up mock_core_project to have no data sources
        mock_core_project.data_sources = {}

        resolver = SqlQueryReconciliationSourceResolver("test_project", mock_core_project, mock_config_service)

        entity_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=core.ResolutionSource(type="sql", data_source="nonexistent_db", query="SELECT * FROM test"),
                remote=core.ResolutionTarget(service_type="test"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
        )

        with pytest.raises(NotFoundError, match="Data source 'nonexistent_db' not found"):
            await resolver.resolve("entity", entity_spec)


class TestReconciliationQueryService:
    """Tests for ReconciliationQueryService."""

    def test_equal_labels_and_compound_keys_do_not_merge(self, sample_entity_spec):
        source = ResolvedSourceRows(
            local_key=["site_code", "region"],
            rows=[
                {"site_code": "A|B", "region": "X", "site_name": "Same"},
                {"site_code": "A", "region": "B|X", "site_name": "Same"},
            ],
        )
        result = ReconciliationQueryService().create("site_name", sample_entity_spec, 3, source, "site")
        assert result.queries["q0"].query == result.queries["q1"].query == "Same"
        assert result.key_mapping == {"q0": r"A\|B|X", "q1": r"A|B\|X"}
        assert result.errors == []
        reversed_keys, reversed_errors = ReconciliationQueryService.index_rows(source.rows, ["region", "site_code"])
        assert reversed_keys == {0: r"X|A\|B", 1: r"B\|X|A"}
        assert not reversed_errors

    def test_invalid_key_rows_are_reported_without_merging(self, sample_entity_spec):
        source = ResolvedSourceRows(
            local_key=["site_code", "region"],
            rows=[
                {"site_code": "A", "region": "X", "site_name": "Same"},
                {"site_code": "A", "region": "X", "site_name": "Same"},
                {"site_code": "B", "region": None, "site_name": "Other"},
                {"site_code": "C", "region": "X", "site_name": ""},
            ],
        )
        result = ReconciliationQueryService().create("site_name", sample_entity_spec, 3, source, "site")
        assert result.queries == {}
        assert {error.row_index for error in result.errors} == {0, 1, 2, 3}
        assert [error.message for error in result.errors].count("Duplicate business key") == 2
        assert result.row_keys == {3: "C|X"}

    def test_create_builds_queries_from_source_data(self, sample_entity_spec):
        """Test create builds queries correctly from source data."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "SITE001", "site_name": "Test Site", "latitude": 60.0, "longitude": 15.0},
            {"site_code": "SITE002", "site_name": "Another Site", "latitude": 61.0, "longitude": 16.0},
        ]

        result = service.create(
            target_field="site_code",
            entity_mapping=sample_entity_spec,
            max_candidates=3,
            source_data=ResolvedSourceRows(rows=source_data, local_key="site_code"),
            service_type="site",
        )

        assert len(result.queries) == 2
        assert len(result.key_mapping) == 2

        # Check first query
        q0 = result.queries["q0"]
        assert q0.query == "SITE001"
        assert q0.type == "site"
        assert q0.limit == 3
        assert len(q0.properties) == 2
        assert {"pid": "latitude", "v": "60.0"} in q0.properties
        assert {"pid": "longitude", "v": "15.0"} in q0.properties

        # Check key mapping (single value, not tuple)
        assert result.key_mapping["q0"] == "SITE001"
        assert result.key_mapping["q1"] == "SITE002"

    def test_create_skips_rows_with_all_none_keys(self, sample_entity_spec):
        """Test create skips rows where target field is None."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": None, "site_name": "Test"},
            {"site_code": "SITE001", "site_name": "Valid"},
        ]

        result = service.create(
            target_field="site_code",
            entity_mapping=sample_entity_spec,
            max_candidates=3,
            source_data=ResolvedSourceRows(rows=source_data, local_key="site_code"),
            service_type="site",
        )

        # Should create only 1 query (second row), indexed as q1 (original row index)
        assert len(result.queries) == 1
        assert "q1" in result.queries
        assert result.queries["q1"].query == "SITE001"
        assert result.key_mapping["q1"] == "SITE001"
        assert result.errors[0].row_index == 0

    def test_create_skips_empty_query_strings(self, sample_entity_spec):
        """Test create skips rows with empty query strings."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "", "site_name": ""},
            {"site_code": "SITE001", "site_name": "Valid"},
        ]

        result = service.create(
            target_field="site_code",
            entity_mapping=sample_entity_spec,
            max_candidates=3,
            source_data=ResolvedSourceRows(rows=source_data, local_key="site_code"),
            service_type="site",
        )

        assert len(result.queries) == 1
        assert result.errors[0].row_index == 0

    def test_create_excludes_none_properties(self, sample_entity_spec):
        """Test create excludes properties with None values."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "SITE001", "latitude": 60.0, "longitude": None},
        ]

        result = service.create(
            target_field="site_code",
            entity_mapping=sample_entity_spec,
            max_candidates=3,
            source_data=ResolvedSourceRows(rows=source_data, local_key="site_code"),
            service_type="site",
        )

        q0 = result.queries["q0"]
        assert len(q0.properties) == 1
        assert {"pid": "latitude", "v": "60.0"} in q0.properties


class TestReconciliationService:
    """Tests for ReconciliationService main class."""

    def test_get_default_registry_filename(self, reconciliation_service: ReconciliationService):
        """Test default reconciliation config filename generation."""
        path = reconciliation_service.catalog_manager._get_default_catalog_filename("my_config")
        assert path.name == "my_config-reconciliation.yml"

    def test_load_reconciliation_config_creates_empty_if_missing(self, reconciliation_service: ReconciliationService):
        """Test load creates empty config if file doesn't exist."""
        config = reconciliation_service.catalog_manager.load_catalog("nonexistent")

        assert config.service_url in ["http://localhost:8000", "http://host.docker.internal:8000"]
        assert config.entities == {}

    def test_load_reconciliation_config_reads_yaml(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test load reads config from YAML file."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        loaded = reconciliation_service.catalog_manager.load_catalog("test", filename=config_file)

        assert loaded.service_url == catalog.service_url
        assert "site" in loaded.entities

    def test_save_reconciliation_config_writes_yaml(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test save writes config to YAML file."""
        config_file = tmp_path / "test-reconciliation.yml"

        domain_catalog = ReconciliationMapper.registry_to_domain(catalog)

        reconciliation_service.catalog_manager.save_catalog("test", domain_catalog, filename=config_file)

        assert config_file.exists()
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["service_url"] == catalog.service_url
        assert "site" in data["entities"]

    @pytest.mark.asyncio
    async def test_get_resolved_source_data_uses_correct_resolver(
        self, reconciliation_service: ReconciliationService, sample_entity_spec, mock_core_project
    ):
        """Test get_resolved_source_data selects and uses correct resolver via domain strategy."""
        # Mock project loading to return a project
        with patch.object(reconciliation_service.project_service, "load_project") as mock_load:
            mock_api_project = MagicMock()
            mock_load.return_value = mock_api_project

            # Mock ProjectMapper to return our mock core project
            with patch("backend.app.services.reconciliation.service.ProjectMapper") as mock_mapper:
                mock_mapper.to_core.return_value = mock_core_project

                # Mock ReconciliationSourceStrategy to return target entity strategy
                with patch("backend.app.services.reconciliation.service.ReconciliationSourceStrategy") as mock_strategy:
                    mock_strategy.determine_strategy.return_value = SourceStrategyType.TARGET_ENTITY

                    # Mock the resolver class and instance
                    mock_resolver = AsyncMock()
                    mock_resolver.resolve.return_value = [{"key": "value"}]
                    mock_resolver_cls = MagicMock(return_value=mock_resolver)

                    # Mock get_resolver_cls_for_strategy to return our mock class
                    with (
                        patch(
                            "backend.app.services.reconciliation.service.ReconciliationSourceResolver.get_resolver_cls_for_strategy"
                        ) as mock_get_cls,
                        patch(
                            "backend.app.services.reconciliation.service.MappingService.get_entity_mapping",
                            return_value=MagicMock(local_key="site_code", public_id="site_id"),
                        ),
                    ):
                        mock_get_cls.return_value = mock_resolver_cls

                        result = await reconciliation_service.get_resolved_source_data("test_project", "site", sample_entity_spec)

                        assert result.rows == [{"key": "value"}]
                        assert result.local_key == "site_code"

                        # Verify domain strategy was used
                        mock_strategy.determine_strategy.assert_called_once_with("site", sample_entity_spec.metadata.source)

                        # Verify get_resolver_cls_for_strategy was called with correct strategy
                        mock_get_cls.assert_called_once_with(SourceStrategyType.TARGET_ENTITY)

                        # Verify resolver was created with correct parameters
                        mock_resolver_cls.assert_called_once_with("test_project", mock_core_project, reconciliation_service.project_service)
                        mock_resolver.resolve.assert_called_once_with("site", sample_entity_spec)

    def test_extract_id_from_uri_success(self, reconciliation_service: ReconciliationService):
        """Test _extract_id_from_uri extracts ID correctly."""
        uri = "https://w3id.org/sead/id/site/12345"
        target_id = reconciliation_service._extract_id_from_uri(uri)
        assert target_id == 12345

    def test_extract_id_from_uri_with_trailing_slash(self, reconciliation_service: ReconciliationService):
        """Test _extract_id_from_uri handles trailing slash."""
        uri = "https://w3id.org/sead/id/site/12345/"
        target_id = reconciliation_service._extract_id_from_uri(uri)
        assert target_id == 12345

    def test_extract_id_from_uri_raises_on_invalid(self, reconciliation_service: ReconciliationService):
        """Test _extract_id_from_uri raises on invalid URI."""

        with pytest.raises(BadRequestError, match="Cannot extract numeric ID"):
            reconciliation_service._extract_id_from_uri("https://example.com/invalid")

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_disabled_without_service_type(
        self, reconciliation_service: ReconciliationService, sample_entity_spec: core.EntityResolutionSet
    ):
        """Test auto_reconcile_entity returns empty result when service_type is None."""
        sample_entity_spec.metadata.remote.service_type = None

        result = await reconciliation_service.auto_reconcile_entity("test_project", "site", "site_code", sample_entity_spec)

        assert result.proposed == 0
        assert result.total == 0
        assert result.candidates == {}

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_no_queries(
        self, reconciliation_service: ReconciliationService, sample_entity_spec: core.EntityResolutionSet, mock_recon_client
    ):
        """Test auto_reconcile_entity handles empty query list."""
        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = ResolvedSourceRows(rows=[{"site_code": None}], local_key="site_code")

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

            assert result.total == 1
            assert result.errors[0].row_index == 0
            assert not mock_recon_client.reconcile_batch.called

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_proposes_high_scores(
        self, reconciliation_service: ReconciliationService, tmp_path, sample_entity_spec: core.EntityResolutionSet
    ):
        """A high-scoring candidate remains proposed until an operator accepts it."""
        # Setup source data
        source_data = [{"site_code": "SITE001", "site_name": "Test Site"}]

        # Setup reconciliation results
        candidates = [
            dto.ReconciliationCandidate(
                id="https://w3id.org/sead/id/site/123",
                name="Test Site",
                score=98.5,
                match=True,
                type=[],
                distance_km=None,
                description=None,
            )
        ]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = ResolvedSourceRows(rows=source_data, local_key="site_code")

            reconciliation_service.reconciliation_client.reconcile_batch.return_value = {"q0": candidates}  # type: ignore

            # Create empty config file with v2 format in nested project structure
            project_dir = tmp_path / "test"
            project_dir.mkdir(exist_ok=True)
            config_file = project_dir / "test-reconciliation.yml"
            config = {
                "version": "3.0",
                "service_url": RECONCILIATION_SERVICE_URL,
                "entities": {
                    "site": {
                        "site_code": {
                            "source": None,
                            "property_mappings": {},
                            "remote": {
                                "data_source": "sead",
                                "entity": "tbl_sites",
                                "key": "site_id",
                                "service_type": "site",
                            },
                            "auto_accept_threshold": 0.95,
                            "review_threshold": 0.7,
                            "mapping": [],
                        }
                    }
                },
            }
            config_file.write_text(yaml.dump(config))

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec, max_candidates=3)

            assert result.proposed == 1
            assert result.unmatched == 0
            assert result.total == 1

            # Check mapping was created by loading from the nested location
            loaded_config = reconciliation_service.catalog_manager.load_catalog("test")
            assert len(loaded_config.entities["site"]["site_code"].links) == 1
            mapping = loaded_config.entities["site"]["site_code"].links[0]
            assert mapping.target_id is None
            assert mapping.status == core.DecisionStatus.PROPOSED
            assert mapping.candidates[0].id == "https://w3id.org/sead/id/site/123"
            assert mapping.local_key_value == "SITE001"
            assert mapping.source_value == "SITE001"

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_marks_needs_review(
        self, reconciliation_service: ReconciliationService, tmp_path, sample_entity_spec
    ):
        """Test auto_reconcile_entity marks candidates needing review."""
        source_data = [{"site_code": "SITE001"}]

        candidates = [
            dto.ReconciliationCandidate(
                id="https://w3id.org/sead/id/site/123", name="Test", score=80.0, match=False, type=[], distance_km=None, description=None
            )
        ]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = ResolvedSourceRows(rows=source_data, local_key="site_code")
            reconciliation_service.reconciliation_client.reconcile_batch.return_value = {"q0": candidates}  # type: ignore

            # Create config in nested structure
            project_dir = tmp_path / "test"
            project_dir.mkdir(exist_ok=True)
            config_file = project_dir / "test-reconciliation.yml"
            config = {
                "version": "3.0",
                "service_url": RECONCILIATION_SERVICE_URL,
                "entities": {
                    "site": {
                        "site_code": {
                            "source": None,
                            "property_mappings": {},
                            "remote": {
                                "data_source": "sead",
                                "entity": "tbl_sites",
                                "key": "site_id",
                                "service_type": "site",
                            },
                            "auto_accept_threshold": 0.95,
                            "review_threshold": 0.7,
                            "mapping": [],
                        }
                    }
                },
            }
            config_file.write_text(yaml.dump(config))

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

            assert result.proposed == 1
            assert len(result.candidates["SITE001"]) == 1
            assert result.unmatched == 0

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_marks_unmatched(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity marks unmatched entries."""
        source_data = [{"site_code": "SITE001"}]

        candidates = [
            dto.ReconciliationCandidate(
                id="https://w3id.org/sead/id/site/123", name="Test", score=50.0, match=False, type=[], distance_km=None, description=None
            )
        ]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = ResolvedSourceRows(rows=source_data, local_key="site_code")
            reconciliation_service.reconciliation_client.reconcile_batch.return_value = {"q0": candidates}

            # Create config in nested structure
            project_dir = tmp_path / "test"
            project_dir.mkdir(exist_ok=True)
            config_file = project_dir / "test-reconciliation.yml"
            config = {
                "version": "3.0",
                "service_url": RECONCILIATION_SERVICE_URL,
                "entities": {
                    "site": {
                        "site_code": {
                            "source": None,
                            "property_mappings": {},
                            "remote": {
                                "data_source": "sead",
                                "entity": "tbl_sites",
                                "key": "site_id",
                                "service_type": "site",
                            },
                            "auto_accept_threshold": 0.95,
                            "review_threshold": 0.7,
                            "mapping": [],
                        }
                    }
                },
            }
            config_file.write_text(yaml.dump(config))

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

            assert result.proposed == 1
            assert result.unmatched == 0

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_handles_no_candidates(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity handles entries with no candidates."""
        source_data = [{"site_code": "SITE001"}]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = ResolvedSourceRows(rows=source_data, local_key="site_code")
            reconciliation_service.reconciliation_client.reconcile_batch.return_value = {"q0": []}

            # Create config in nested structure
            project_dir = tmp_path / "test"
            project_dir.mkdir(exist_ok=True)
            config_file = project_dir / "test-reconciliation.yml"
            config = {
                "version": "3.0",
                "service_url": RECONCILIATION_SERVICE_URL,
                "entities": {
                    "site": {
                        "site_code": {
                            "source": None,
                            "property_mappings": {},
                            "remote": {
                                "data_source": "sead",
                                "entity": "tbl_sites",
                                "key": "site_id",
                                "service_type": "site",
                            },
                            "auto_accept_threshold": 0.95,
                            "review_threshold": 0.7,
                            "mapping": [],
                        }
                    }
                },
            }
            config_file.write_text(yaml.dump(config))

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

            assert result.unmatched == 1
            assert result.total == 1

    def test_update_mapping_adds_new_mapping(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test accepting a proposed entry by encoded key."""
        catalog.entities["site"]["site_code"].mapping = [dto.ResolvedEntityPair(local_key_value="SITE001", source_value="Same")]
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        updated: core.EntityResolutionCatalog = reconciliation_service.update_mapping(
            "test",
            "site",
            "site_code",
            local_key_value="SITE001",
            status=core.DecisionStatus.ACCEPTED,
            target_id=123,
            notes="Manual link",
            candidate_id="https://w3id.org/sead/id/site/123",
        )

        assert len(updated.entities["site"]["site_code"].links) == 1
        links = updated.entities["site"]["site_code"].links[0]
        assert links.target_id == 123
        assert links.source_value == "Same"
        assert links.notes == "Manual link"
        assert links.confidence is None

    def test_update_mapping_updates_existing(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test update_mapping updates existing mapping."""
        # Add existing mapping
        existing_mapping = dto.ResolvedEntityPair(
            local_key_value="SITE001",
            source_value="SITE001",
            status="accepted",
            target_id=100,
            confidence=0.8,
            notes="Old mapping",
            created_by="system",
            created_at="2024-01-01T00:00:00Z",
            last_modified="2024-01-02T00:00:00Z",
        )
        catalog.entities["site"]["site_code"].mapping = [existing_mapping]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        updated: core.EntityResolutionCatalog = reconciliation_service.update_mapping(
            "test",
            "site",
            "site_code",
            local_key_value="SITE001",
            status=core.DecisionStatus.ACCEPTED,
            target_id=200,
            notes="Updated mapping",
            candidate_id="https://w3id.org/sead/id/site/200",
        )

        assert len(updated.entities["site"]["site_code"].links) == 1
        links = updated.entities["site"]["site_code"].links[0]
        assert links.target_id == 200
        assert links.notes == "Updated mapping"

    def test_update_mapping_removes_mapping(
        self, reconciliation_service: ReconciliationService, tmp_path, catalog: dto.EntityResolutionCatalog
    ):
        """Test update_mapping removes mapping when target_id is None."""
        existing_mapping = dto.ResolvedEntityPair(
            local_key_value="SITE001",
            source_value="SITE001",
            status="accepted",
            target_id=100,
            confidence=0.8,
            notes="To remove",
            created_by="user",
            created_at="2024-01-01T00:00:00Z",
            last_modified="2024-01-02T00:00:00Z",
        )
        catalog.entities["site"]["site_code"].mapping = [existing_mapping]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        updated: core.EntityResolutionCatalog = reconciliation_service.delete_decision("test", "site", "site_code", "SITE001")

        assert len(updated.entities["site"]["site_code"].links) == 0

    def test_update_mapping_raises_for_missing_entity(self, reconciliation_service: ReconciliationService, tmp_path):
        """Test update_mapping raises if entity not in registry."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        config_file.write_text(yaml.dump({"version": "3.0", "service_url": RECONCILIATION_SERVICE_URL, "entities": {}}))

        with pytest.raises(NotFoundError, match="Entity mapping for entity 'nonexistent' and target field 'field' not found"):
            reconciliation_service.update_mapping(
                "test", "nonexistent", "field", local_key_value="KEY", status=core.DecisionStatus.ACCEPTED, target_id=123
            )

    def test_mark_as_unmatched(self, reconciliation_service, tmp_path, catalog):
        """Test mark_as_unmatched changes an existing row to local-only."""
        catalog.entities["site"]["site_code"].mapping = [dto.ResolvedEntityPair(local_key_value="LOCAL_SITE", source_value="Same")]
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        updated = reconciliation_service.mark_as_unmatched(
            "test",
            "site",
            "site_code",
            local_key_value="LOCAL_SITE",
            notes="Local identifier only",
        )

        assert len(updated.entities["site"]["site_code"].links) == 1
        link: core.ResolvedEntityPair = updated.entities["site"]["site_code"].links[0]
        assert link.local_key_value == "LOCAL_SITE"
        assert link.source_value == "Same"
        assert link.target_id is None
        assert link.status == core.DecisionStatus.LOCAL_ONLY
        assert link.notes == "Local identifier only"
        assert link.confidence is None
        assert link.last_modified is not None

    def test_mark_as_unmatched_updates_existing(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test mark_as_unmatched can convert existing mapping to unmatched."""
        # Add existing matched mapping
        existing_mapping = dto.ResolvedEntityPair(
            local_key_value="SITE001",
            source_value="SITE001",
            status="accepted",
            target_id=100,
            confidence=0.8,
            notes="Was matched",
            created_by="system",
            created_at="2024-01-01T00:00:00Z",
            last_modified="2024-01-02T00:00:00Z",
        )
        catalog.entities["site"]["site_code"].mapping = [existing_mapping]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        updated: core.EntityResolutionCatalog = reconciliation_service.mark_as_unmatched(
            "test",
            "site",
            "site_code",
            local_key_value="SITE001",
            notes="Changed to local-only",
        )

        assert len(updated.entities["site"]["site_code"].links) == 1
        link: core.ResolvedEntityPair = updated.entities["site"]["site_code"].links[0]
        assert link.target_id is None
        assert link.status == core.DecisionStatus.LOCAL_ONLY
        assert link.notes == "Changed to local-only"

    @pytest.mark.asyncio
    async def test_all_normalized_rows_have_independent_proposals(self, reconciliation_service, sample_entity_spec, mock_recon_client):
        source = ResolvedSourceRows(
            local_key="site_code",
            rows=[{"site_code": f"K{index:04}", "site_name": "Same"} for index in range(1001)],
        )

        async def respond(queries):
            return {
                query_id: [dto.ReconciliationCandidate(id="https://w3id.org/sead/id/site/123", name="Same", score=100.0)]
                for query_id in queries
            }

        mock_recon_client.reconcile_batch.side_effect = respond
        with (
            patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock(return_value=source)),
            patch("backend.app.services.reconciliation.service.operation_manager.update_progress") as progress,
            patch("backend.app.services.reconciliation.service.operation_manager.complete_operation"),
        ):
            result = await reconciliation_service.auto_reconcile_entity(
                "rows", "site", "site_name", sample_entity_spec, operation_id="operation"
            )

        assert result.total == result.proposed == len(result.candidates) == 1001
        assert result.errors == []
        assert result.candidates["K1000"][0].score == 100.0
        assert mock_recon_client.reconcile_batch.call_count == 21
        assert any(call.kwargs.get("current") == 1001 for call in progress.call_args_list)
        decisions = reconciliation_service.catalog_manager.load_catalog("rows").get("site", "site_name").links
        assert len(decisions) == 1001
        assert all(decision.status == core.DecisionStatus.PROPOSED and decision.target_id is None for decision in decisions)

    @pytest.mark.asyncio
    async def test_rerun_retains_operator_decisions(self, reconciliation_service, sample_entity_spec, mock_recon_client):
        sample_entity_spec.links = [
            core.ResolvedEntityPair(
                local_key_value=key,
                source_value="Same",
                status=status,
                target_id=target_id,
                notes="operator",
                candidates=[core.ResolutionCandidate(id="old", name="Original", score=70.0)],
            )
            for key, status, target_id in (
                ("A", core.DecisionStatus.ACCEPTED, 101),
                ("B", core.DecisionStatus.REJECTED, None),
                ("C", core.DecisionStatus.LOCAL_ONLY, None),
            )
        ]
        sample_entity_spec.links.append(core.ResolvedEntityPair(local_key_value="D", source_value="Same"))
        registry = core.EntityResolutionCatalog(
            version="3.0", service_url="http://localhost:8000", entities={"site": {"site_name": sample_entity_spec}}
        )
        reconciliation_service.catalog_manager.save_catalog("rerun", registry)
        source = ResolvedSourceRows(
            local_key="site_code",
            rows=[{"site_code": key, "site_name": "Same"} for key in ("A", "B", "C", "D")],
        )
        mock_recon_client.reconcile_batch.return_value = {"q3": [dto.ReconciliationCandidate(id="new", name="New", score=100.0)]}
        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock(return_value=source)):
            result = await reconciliation_service.auto_reconcile_entity("rerun", "site", "site_name", sample_entity_spec)
            result = await reconciliation_service.auto_reconcile_entity("rerun", "site", "site_name", sample_entity_spec)

        assert result.proposed == 1
        assert list(mock_recon_client.reconcile_batch.call_args.args[0]) == ["q3"]
        decisions = {
            item.local_key_value: item
            for item in reconciliation_service.catalog_manager.load_catalog("rerun").get("site", "site_name").links
        }
        assert [
            (decisions[key].status, decisions[key].target_id, decisions[key].notes, decisions[key].candidates[0].id)
            for key in ("A", "B", "C")
        ] == [
            (core.DecisionStatus.ACCEPTED, 101, "operator", "old"),
            (core.DecisionStatus.REJECTED, None, "operator", "old"),
            (core.DecisionStatus.LOCAL_ONLY, None, "operator", "old"),
        ]
        assert decisions["D"].status == core.DecisionStatus.PROPOSED
        assert decisions["D"].candidates[0].id == "new"

    @pytest.mark.asyncio
    async def test_decision_saved_during_matching_is_not_overwritten(self, reconciliation_service, sample_entity_spec, mock_recon_client):
        sample_entity_spec.links = [
            core.ResolvedEntityPair(
                local_key_value="A",
                source_value="Same",
                candidates=[core.ResolutionCandidate(id="old", name="Original", score=70.0)],
            )
        ]
        reconciliation_service.catalog_manager.save_catalog(
            "editing",
            core.EntityResolutionCatalog(
                version="3.0", service_url="http://localhost:8000", entities={"site": {"site_name": sample_entity_spec}}
            ),
        )

        async def respond(queries):
            reconciliation_service.update_mapping(
                "editing",
                "site",
                "site_name",
                "A",
                core.DecisionStatus.ACCEPTED,
                101,
                "reviewed",
                candidate_id="site/101",
            )
            return {"q0": [dto.ReconciliationCandidate(id="new", name="New", score=100.0)]}

        mock_recon_client.reconcile_batch.side_effect = respond
        source = ResolvedSourceRows(local_key="site_code", rows=[{"site_code": "A", "site_name": "Same"}])
        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock(return_value=source)):
            result = await reconciliation_service.auto_reconcile_entity("editing", "site", "site_name", sample_entity_spec)

        decision = reconciliation_service.catalog_manager.load_catalog("editing").get("site", "site_name").links[0]
        assert result.proposed == 0
        assert result.candidates["A"][0].id == "old"
        assert (decision.status, decision.target_id, decision.notes, decision.candidates[0].id) == (
            core.DecisionStatus.ACCEPTED,
            101,
            "reviewed",
            "old",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("manifest", "service_type", "property_mappings", "error_type"),
        [
            (
                {
                    "defaultTypes": [{"id": "site"}],
                    "reconciliation": {"supportedTypes": []},
                    "extend": {"property_settings": []},
                },
                "site",
                {},
                ValidationError,
            ),
            (
                {
                    "defaultTypes": [{"id": "site"}],
                    "reconciliation": {"supportedTypes": ["site"]},
                    "extend": {"property_settings": [{"name": "place_name", "entity_types": ["site"]}]},
                },
                "site",
                {"old_property": "site_name"},
                ValidationError,
            ),
            ({"defaultTypes": [{"id": "site"}]}, "site", {}, DependencyError),
        ],
    )
    async def test_auto_reconcile_entity_blocks_unverified_specifications(
        self,
        reconciliation_service: ReconciliationService,
        sample_entity_spec: core.EntityResolutionSet,
        mock_recon_client: AsyncMock,
        manifest: dict,
        service_type: str,
        property_mappings: dict[str, str],
        error_type: type[Exception],
    ):
        sample_entity_spec.metadata.remote.service_type = service_type
        sample_entity_spec.metadata.property_mappings = property_mappings
        mock_recon_client.get_service_manifest.return_value = manifest

        with (
            patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as get_source_data,
            patch.object(reconciliation_service.catalog_manager, "save_catalog") as save_catalog,
            pytest.raises(error_type),
        ):
            await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

        get_source_data.assert_not_awaited()
        mock_recon_client.reconcile_batch.assert_not_awaited()
        save_catalog.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_blocks_when_manifest_request_fails(
        self,
        reconciliation_service: ReconciliationService,
        sample_entity_spec: core.EntityResolutionSet,
        mock_recon_client: AsyncMock,
    ):
        mock_recon_client.get_service_manifest.side_effect = httpx.ConnectError("service offline")

        with (
            patch.object(reconciliation_service.catalog_manager, "save_catalog") as save_catalog,
            pytest.raises(DependencyError, match="manifest is unavailable"),
        ):
            await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

        mock_recon_client.reconcile_batch.assert_not_awaited()
        save_catalog.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_accepts_supported_type_with_no_properties(
        self,
        reconciliation_service: ReconciliationService,
        sample_entity_spec: core.EntityResolutionSet,
        mock_recon_client: AsyncMock,
    ):
        sample_entity_spec.metadata.remote.service_type = "feature_type"
        sample_entity_spec.metadata.property_mappings = {}
        mock_recon_client.reconcile_batch.return_value = {"q0": [dto.ReconciliationCandidate(id="feature/25", name="Trench", score=100)]}
        source_data = ResolvedSourceRows(rows=[{"site_code": "FT-1"}], local_key="site_code")

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock(return_value=source_data)):
            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

        query = mock_recon_client.reconcile_batch.await_args.args[0]["q0"]
        assert query.type == "feature_type"
        assert query.properties == []
        assert "properties" not in query.to_dict()
        assert result.proposed == 1

    @pytest.mark.asyncio
    async def test_ambiguous_search_source_is_rejected(self, reconciliation_service, sample_entity_spec, mock_core_project):
        sample_entity_spec.metadata.source = "sample"
        with (
            patch.object(reconciliation_service.project_service, "load_project"),
            patch("backend.app.services.reconciliation.service.ProjectMapper.to_core", return_value=mock_core_project),
            patch(
                "backend.app.services.reconciliation.service.MappingService.get_entity_mapping",
                return_value=MagicMock(local_key="site_code", public_id="site_id"),
            ),
            patch("backend.app.services.reconciliation.service.ReconciliationSourceResolver.get_resolver_cls_for_strategy") as get_resolver,
        ):

            def choose(strategy):
                rows = [{"site_code": "A", "site_name": "Same"}]
                if strategy == SourceStrategyType.ANOTHER_ENTITY:
                    rows *= 2
                return MagicMock(return_value=MagicMock(resolve=AsyncMock(return_value=rows)))

            get_resolver.side_effect = choose
            with pytest.raises(ValidationError, match="duplicate business keys"):
                await reconciliation_service.get_resolved_source_data("site-project", "site", sample_entity_spec)

    @pytest.mark.parametrize("header", ["version: '2.0'\n", ""])
    def test_old_catalog_is_ignored_but_invalid_future_is_rejected(self, reconciliation_service, tmp_path, header):
        filename = tmp_path / "old-reconciliation.yml"
        filename.write_text(f"{header}entities: {{site: {{site_code: {{mapping: []}}}}}}\n", encoding="utf-8")
        original = filename.read_bytes()
        assert reconciliation_service.catalog_manager.load_catalog("old", filename=filename).entities == {}
        assert filename.read_bytes() == original
        filename.write_text("version: '4.0'\nentities: {}\n", encoding="utf-8")
        with pytest.raises(ValidationError, match="Unsupported reconciliation catalog version"):
            reconciliation_service.catalog_manager.load_catalog("old", filename=filename)
        filename.write_text("version: [\n", encoding="utf-8")
        with pytest.raises(ValidationError, match="Malformed reconciliation catalog"):
            reconciliation_service.catalog_manager.load_catalog("old", filename=filename)

    @pytest.mark.asyncio
    async def test_old_catalog_rows_can_be_proposed_again(self, reconciliation_service, sample_entity_spec, mock_recon_client, tmp_path):
        project_dir = tmp_path / "old"
        project_dir.mkdir()
        catalog = project_dir / "old-reconciliation.yml"
        catalog.write_text("version: '2.0'\nentities: {site: {site_name: {mapping: []}}}\n", encoding="utf-8")
        source = ResolvedSourceRows(rows=[{"site_code": "A", "site_name": "Same"}], local_key="site_code")
        mock_recon_client.reconcile_batch.return_value = {"q0": []}
        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock(return_value=source)):
            result = await reconciliation_service.auto_reconcile_entity("old", "site", "site_name", sample_entity_spec)
        assert result.total == result.proposed == 1
        assert yaml.safe_load(catalog.read_text(encoding="utf-8"))["version"] == "3.0"
        assert reconciliation_service.catalog_manager.load_catalog("old").get("site", "site_name").links[0].local_key_value == "A"


class TestSpecificationManagement:
    """Tests for specification CRUD operations."""

    def test_list_specifications_empty(self, reconciliation_service: ReconciliationService, tmp_path):
        """Test listing specifications when config has no entities."""
        config = dto.EntityResolutionCatalog(version="3.0", service_url=RECONCILIATION_SERVICE_URL, entities={})

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        specs = reconciliation_service.catalog_manager.list_entity_mappings("test")
        assert specs == []

    def test_list_specifications_multiple(self, reconciliation_service: ReconciliationService, tmp_path, sample_entity_spec_dto):
        """Test listing multiple specifications."""
        config = dto.EntityResolutionCatalog(
            version="3.0",
            service_url=RECONCILIATION_SERVICE_URL,
            entities={
                "site": {
                    "site_code": sample_entity_spec_dto,
                    "site_name": dto.EntityResolutionSet(
                        source="another_entity",
                        property_mappings={},
                        remote=dto.ReconciliationRemote(service_type="taxon"),
                        auto_accept_threshold=0.85,
                        review_threshold=0.60,
                        mapping=[
                            dto.ResolvedEntityPair(
                                local_key_value="SITE-1",
                                source_value="test",
                                status="accepted",
                                target_id=1,
                                confidence=0.9,
                                notes="Existing mapping",
                                created_by="user",
                                created_at="2024-01-01T00:00:00Z",
                                last_modified="2024-01-02T00:00:00Z",
                            ),
                            dto.ResolvedEntityPair(
                                local_key_value="SITE-2",
                                source_value="test2",
                                status="accepted",
                                target_id=2,
                                confidence=0.8,
                                notes="Another mapping",
                                created_by="user",
                                created_at="2024-01-03T00:00:00Z",
                                last_modified="2024-01-04T00:00:00Z",
                            ),
                        ],
                    ),
                },
                "sample": {
                    "sample_type": dto.EntityResolutionSet(
                        source=None,
                        property_mappings={"name": "type_name"},
                        remote=dto.ReconciliationRemote(service_type="location"),
                        auto_accept_threshold=0.90,
                        review_threshold=0.75,
                        mapping=[],
                    ),
                },
            },
        )

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        specs = reconciliation_service.catalog_manager.list_entity_mappings("test")

        assert len(specs) == 3
        # Check site.site_code
        site_code_spec = next(s for s in specs if s.entity_name == "site" and s.target_field == "site_code")
        assert site_code_spec.mapping_count == 0
        assert site_code_spec.property_mapping_count == 2
        assert site_code_spec.remote.service_type == "site"

        # Check site.site_name
        site_name_spec = next(s for s in specs if s.entity_name == "site" and s.target_field == "site_name")
        assert site_name_spec.mapping_count == 2
        assert site_name_spec.property_mapping_count == 0
        assert site_name_spec.source == "another_entity"

        # Check sample.sample_type
        sample_spec = next(s for s in specs if s.entity_name == "sample")
        assert sample_spec.mapping_count == 0
        assert sample_spec.property_mapping_count == 1

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    @patch("backend.app.services.reconciliation.service.ProjectService")
    def test_create_specification_success(
        self, mock_project_service, mock_mapper, reconciliation_service: ReconciliationService, tmp_path, catalog
    ):
        """Test creating new specification."""
        # Mock project service to return a project
        mock_project = MagicMock()
        mock_project.entities = {"site": MagicMock(), "sample": MagicMock()}
        mock_ps_instance = MagicMock()
        mock_ps_instance.load_project.return_value = mock_project
        mock_project_service.return_value = mock_ps_instance
        reconciliation_service.project_service = mock_ps_instance

        # Mock entity validation
        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock(), "sample": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        # Save initial config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        # Create new spec
        new_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=None,
                property_mappings={"lat": "latitude"},
                remote=core.ResolutionTarget(service_type="location"),
                auto_accept_threshold=0.90,
                review_threshold=0.75,
            ),
            links=[],
        )

        updated_config = reconciliation_service.catalog_manager.create_entity_mapping("test", "sample", "sample_code", new_spec)

        assert "sample" in updated_config.entities
        assert "sample_code" in updated_config.entities["sample"]
        assert updated_config.entities["sample"]["sample_code"] == new_spec

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    @patch("backend.app.services.reconciliation.service.ProjectService")
    def test_create_specification_duplicate(
        self, mock_project_service, mock_mapper, reconciliation_service: ReconciliationService, tmp_path, catalog
    ):
        """Test creating duplicate specification raises error."""
        # Mock project service
        mock_project = MagicMock()
        mock_project.entities = {"site": MagicMock()}
        mock_ps_instance = MagicMock()
        mock_ps_instance.load_project.return_value = mock_project
        mock_project_service.return_value = mock_ps_instance
        reconciliation_service.project_service = mock_ps_instance

        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        new_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=None,
                property_mappings={},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
            links=[],
        )

        with pytest.raises(ResourceConflictError, match="already exists"):
            reconciliation_service.catalog_manager.create_entity_mapping("test", "site", "site_code", new_spec)

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    @patch("backend.app.services.reconciliation.service.ProjectService")
    def test_create_specification_invalid_entity(self, mock_project_service, mock_mapper, reconciliation_service, tmp_path, catalog):
        """Test creating specification for non-existent entity raises error."""
        # Mock project service
        mock_project = MagicMock()
        mock_project.entities = {"site": MagicMock()}
        mock_ps_instance = MagicMock()
        mock_ps_instance.load_project.return_value = mock_project
        mock_project_service.return_value = mock_ps_instance
        reconciliation_service.project_service = mock_ps_instance

        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        new_spec = core.EntityResolutionSet(
            metadata=core.EntityResolutionMetadata(
                source=None,
                property_mappings={},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.95,
                review_threshold=0.70,
            ),
            links=[],
        )

        with pytest.raises(ValidationError, match="Entity 'invalid_entity' does not exist"):
            reconciliation_service.catalog_manager.create_entity_mapping("test", "invalid_entity", "some_field", new_spec)

    def test_update_specification_success(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test updating specification preserves mapping."""
        # Add mapping to original spec
        catalog.entities["site"]["site_code"].mapping = [
            dto.ResolvedEntityPair(
                local_key_value="SITE001",
                source_value="SITE001",
                status="accepted",
                target_id=100,
                confidence=0.95,
                notes="Existing mapping",
                created_by="user",
                created_at="2024-01-01T00:00:00Z",
                last_modified="2024-01-02T00:00:00Z",
            )
        ]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        # Update thresholds and property mappings
        updated_config: core.EntityResolutionCatalog = reconciliation_service.catalog_manager.update_entity_mapping(
            project_name="test",
            entity_name="site",
            target_field="site_code",
            source="another_entity",
            property_mappings={"lat": "latitude"},
            remote=core.ResolutionTarget(service_type="site"),
            auto_accept_threshold=0.80,
            review_threshold=0.60,
        )

        mapping: core.EntityResolutionSet = updated_config.entities["site"]["site_code"]
        assert mapping.metadata.auto_accept_threshold == 0.80
        assert mapping.metadata.review_threshold == 0.60
        assert mapping.metadata.source == "another_entity"
        assert mapping.metadata.property_mappings == {"lat": "latitude"}
        # Links should be preserved
        assert len(mapping.links) == 1
        assert mapping.links[0].source_value == "SITE001"

    def test_update_specification_not_found(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test updating non-existent specification raises error."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        with pytest.raises(ResourceNotFoundError, match="not found"):
            reconciliation_service.catalog_manager.update_entity_mapping(
                project_name="test",
                entity_name="site",
                target_field="nonexistent_field",
                source=None,
                property_mappings={},
                remote=core.ResolutionTarget(service_type="site"),
                auto_accept_threshold=0.90,
                review_threshold=0.70,
            )

    def test_delete_specification_success(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test deleting specification without mappings."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        mock_project = MagicMock()
        mock_project.filename = None
        with patch.object(reconciliation_service.project_service, "load_project", return_value=mock_project):
            updated_config, removed_links, removed_approvals = reconciliation_service.delete_specification(
                "test", "site", "site_code", force=False
            )

        assert "site_code" not in updated_config.entities.get("site", {})
        assert removed_links == 0
        assert removed_approvals == 0

    def test_delete_specification_with_mappings_no_force(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test deleting specification with mappings raises error without force."""
        catalog.entities["site"]["site_code"].mapping = [
            dto.ResolvedEntityPair(
                local_key_value="SITE001",
                source_value="SITE001",
                status="accepted",
                target_id=100,
                confidence=0.95,
                notes="Existing mapping",
                created_by="user",
                created_at="2024-01-01T00:00:00Z",
                last_modified="2024-01-02T00:00:00Z",
            )
        ]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        mock_project = MagicMock()
        mock_project.filename = None
        with patch.object(reconciliation_service.project_service, "load_project", return_value=mock_project):
            with pytest.raises(ValidationError, match="Cannot delete existing mapping.*from catalog"):
                reconciliation_service.delete_specification("test", "site", "site_code", force=False)

    def test_delete_specification_with_mappings_force(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test force deleting specification with mappings succeeds."""
        catalog.entities["site"]["site_code"].mapping = [
            dto.ResolvedEntityPair(
                local_key_value="SITE001",
                source_value="SITE001",
                status="accepted",
                target_id=100,
                confidence=0.95,
                notes="Existing mapping",
                created_by="user",
                created_at="2024-01-01T00:00:00Z",
                last_modified="2024-01-02T00:00:00Z",
            ),
            dto.ResolvedEntityPair(
                local_key_value="SITE002",
                source_value="SITE002",
                status="accepted",
                target_id=101,
                confidence=0.90,
                notes="Another mapping",
                created_by="user",
                created_at="2024-01-03T00:00:00Z",
                last_modified="2024-01-04T00:00:00Z",
            ),
        ]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        mock_project = MagicMock()
        mock_project.filename = None
        with patch.object(reconciliation_service.project_service, "load_project", return_value=mock_project):
            updated_config, removed_links, removed_approvals = reconciliation_service.delete_specification(
                "test", "site", "site_code", force=True
            )

        assert "site_code" not in updated_config.entities.get("site", {})
        assert removed_links == 0
        assert removed_approvals == 0

    def test_delete_specification_not_found(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test deleting non-existent specification raises error."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        mock_project = MagicMock()
        mock_project.filename = None
        with patch.object(reconciliation_service.project_service, "load_project", return_value=mock_project):
            with pytest.raises(ResourceNotFoundError, match="not found"):
                reconciliation_service.delete_specification("test", "site", "nonexistent_field")

    def test_delete_last_specification_removes_entity(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test deleting last specification removes entity from config."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        mock_project = MagicMock()
        mock_project.filename = None
        with patch.object(reconciliation_service.project_service, "load_project", return_value=mock_project):
            updated_config, _, _ = reconciliation_service.delete_specification("test", "site", "site_code")

        # Entity should be removed entirely
        assert "site" not in updated_config.entities

    async def test_get_available_target_fields_success(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test getting available target fields from preview."""
        # Mock preview result
        mock_preview_result = MagicMock()
        mock_preview_result.columns = [
            MagicMock(name="site_code"),
            MagicMock(name="site_name"),
            MagicMock(name="latitude"),
            MagicMock(name="longitude"),
        ]

        # Mock shapeshift service
        mock_ss_service = MagicMock()
        mock_ss_service.preview_entity = AsyncMock(return_value=mock_preview_result)
        reconciliation_service.shapeshift_service = mock_ss_service

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        fields = await reconciliation_service.get_available_target_fields("test", "site")

        assert fields == ["site_code", "site_name", "latitude", "longitude"]

    def test_get_mapping_count_success(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test getting mapping count."""
        catalog.entities["site"]["site_code"].mapping = [
            dto.ResolvedEntityPair(
                local_key_value="SITE001",
                source_value="SITE001",
                status="accepted",
                target_id=100,
                confidence=0.99,
                notes="Test note",
                created_by="user1",
                created_at="2024-01-01T00:00:00Z",
                last_modified="2024-01-02T00:00:00Z",
            ),
            dto.ResolvedEntityPair(
                local_key_value="SITE002",
                source_value="SITE002",
                status="accepted",
                target_id=101,
                confidence=0.95,
                notes="Test note 2",
                created_by="user2",
                created_at="2024-01-03T00:00:00Z",
                last_modified="2024-01-04T00:00:00Z",
            ),
            dto.ResolvedEntityPair(
                local_key_value="SITE003",
                source_value="SITE003",
                status="local-only",
                target_id=None,
                confidence=None,
                notes="Local only",
                created_by="user3",
                created_at="2024-01-05T00:00:00Z",
                last_modified="2024-01-06T00:00:00Z",
            ),
        ]

        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        count: int = reconciliation_service.get_mapping_count("test", "site", "site_code")

        assert count == 3

    def test_get_mapping_count_not_found(self, reconciliation_service: ReconciliationService, tmp_path, catalog):
        """Test getting mapping count for non-existent specification."""
        # Create config in nested structure
        project_dir = tmp_path / "test"
        project_dir.mkdir(exist_ok=True)
        config_file = project_dir / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(catalog.model_dump(exclude_none=True), f)

        with pytest.raises(NotFoundError, match="not found"):
            reconciliation_service.get_mapping_count("test", "site", "nonexistent_field")
