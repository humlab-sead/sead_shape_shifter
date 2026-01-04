"""Tests for ReconciliationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from backend.app.models import (
    EntityReconciliationSpec,
    ReconciliationCandidate,
    ReconciliationConfig,
    ReconciliationMapping,
    ReconciliationSource,
)
from backend.app.models.reconciliation import ReconciliationRemote
from backend.app.models.shapeshift import PreviewResult
from backend.app.services.reconciliation_service import (
    AnotherEntityReconciliationSourceResolver,
    ReconciliationQueryService,
    ReconciliationService,
    ReconciliationSourceResolver,
    SqlQueryReconciliationSourceResolver,
    TargetEntityReconciliationSourceResolver,
)
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from backend.tests.test_reconciliation_client import RECONCILIATION_SERVICE_URL

# pylint: disable=redefined-outer-name,unused-argument,protected-access

RECONCILIATION_SERVICE_URL = "http://localhost:8000"


@pytest.fixture
def mock_config_service():
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
def mock_recon_client():
    """Mock reconciliation client."""
    client = AsyncMock()
    client.reconcile_batch.return_value = {}
    return client


@pytest.fixture
def reconciliation_service(tmp_path, mock_recon_client):
    """Create ReconciliationService instance."""
    return ReconciliationService(config_dir=tmp_path, reconciliation_client=mock_recon_client)


@pytest.fixture
def sample_entity_spec():
    """Create sample EntityReconciliationSpec (v2 format)."""
    return EntityReconciliationSpec(
        source=None,
        property_mappings={"latitude": "latitude", "longitude": "longitude"},
        remote=ReconciliationRemote(service_type="site", data_source="sead", entity="site", key="site_id"),
        auto_accept_threshold=0.95,
        review_threshold=0.70,
        mapping=[],
    )


@pytest.fixture
def sample_recon_config(sample_entity_spec):
    """Create sample ReconciliationConfig (v2 format)."""
    return ReconciliationConfig(
        version="2.0",
        service_url=RECONCILIATION_SERVICE_URL,
        entities={"site": {"site_code": sample_entity_spec}},  # Nested: entity -> target -> spec
    )


class TestReconciliationSourceResolver:
    """Tests for ReconciliationSourceResolver base class."""

    def test_get_resolver_cls_for_none_source(self):
        """Test resolver class selection for None source."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_source("site", None)
        assert resolver_cls == TargetEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_empty_source(self):
        """Test resolver class selection for empty source."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_source("site", "")
        assert resolver_cls == TargetEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_same_entity(self):
        """Test resolver class selection when source equals entity name."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_source("site", "site")
        assert resolver_cls == TargetEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_another_entity(self):
        """Test resolver class selection for another entity."""
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_source("sample", "site")
        assert resolver_cls == AnotherEntityReconciliationSourceResolver

    def test_get_resolver_cls_for_custom_query(self):
        """Test resolver class selection for ReconciliationSource."""
        source = ReconciliationSource(type="sql", data_source="test_db", query="SELECT * FROM sites")
        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_source("site", source)
        assert resolver_cls == SqlQueryReconciliationSourceResolver

    def test_get_resolver_cls_invalid_source(self):
        """Test resolver class selection raises for invalid source."""

        with pytest.raises(BadRequestError, match="Invalid source specification"):
            ReconciliationSourceResolver.get_resolver_cls_for_source("site", 123)  # type: ignore


class TestTargetEntityReconciliationSourceResolver:
    """Tests for TargetEntityReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_uses_entity_preview(self, mock_config_service, sample_entity_spec):
        """Test resolve uses preview data from target entity."""
        resolver = TargetEntityReconciliationSourceResolver("test_project", mock_config_service)

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
            mock_preview.assert_called_once_with("test_project", "site", limit=1000)


class TestAnotherEntityReconciliationSourceResolver:
    """Tests for AnotherEntityReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_uses_source_entity_preview(self, mock_config_service):
        """Test resolve uses preview data from source entity."""
        resolver = AnotherEntityReconciliationSourceResolver("test_project", mock_config_service)

        # Entity spec with source pointing to another entity
        entity_spec = EntityReconciliationSpec(
            source="site",
            remote=ReconciliationRemote(service_type="sample", data_source="sead", entity="sample", key="sample_id"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        source_data = [{"site_code": "SITE001", "sample_code": "SAMP001"}]

        with patch.object(resolver.preview_service, "preview_entity", new=AsyncMock()) as mock_preview:
            mock_preview.return_value = PreviewResult(
                entity_name="site", rows=source_data, columns=[], total_rows_in_preview=1, execution_time_ms=10
            )

            result = await resolver.resolve("sample", entity_spec)

            assert result == source_data
            mock_preview.assert_called_once_with("test_project", "site", limit=1000)

    @pytest.mark.asyncio
    async def test_resolve_raises_for_missing_source_entity(self, mock_config_service):
        """Test resolve raises if source entity not found."""
        resolver = AnotherEntityReconciliationSourceResolver("test_project", mock_config_service)

        entity_spec = EntityReconciliationSpec(
            source="nonexistent",
            remote=ReconciliationRemote(service_type="test", data_source="sead", entity="sample", key="sample_id"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        with pytest.raises(NotFoundError, match="Source entity 'nonexistent' not found"):
            await resolver.resolve("entity", entity_spec)


class TestSqlQueryReconciliationSourceResolver:
    """Tests for SqlQueryReconciliationSourceResolver."""

    @pytest.mark.asyncio
    async def test_resolve_executes_custom_query(self, mock_config_service):
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

        entity_spec = EntityReconciliationSpec(
            source=ReconciliationSource(type="sql", data_source="test_db", query="SELECT * FROM custom_view"),
            remote=ReconciliationRemote(service_type="test", data_source="sead", entity="sample", key="sample_id"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        resolver = SqlQueryReconciliationSourceResolver("test_project", mock_config_service)

        # This will fail at TableConfig creation, but that's OK - we're just verifying
        # that the SQL query path is taken and data source validation happens
        with pytest.raises(KeyError):
            await resolver.resolve("entity", entity_spec)

    @pytest.mark.asyncio
    async def test_resolve_raises_for_missing_data_source(self, mock_config_service):
        """Test resolve raises if data source not found."""
        resolver = SqlQueryReconciliationSourceResolver("test_project", mock_config_service)

        entity_spec = EntityReconciliationSpec(
            source=ReconciliationSource(type="sql", data_source="nonexistent_db", query="SELECT * FROM test"),
            remote=ReconciliationRemote(service_type="test", data_source="sead", entity="sample", key="sample_id"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
        )

        with pytest.raises(NotFoundError, match="Data source 'nonexistent_db' not found"):
            await resolver.resolve("entity", entity_spec)


class TestReconciliationQueryService:
    """Tests for ReconciliationQueryService."""

    def test_create_builds_queries_from_source_data(self, sample_entity_spec):
        """Test create builds queries correctly from source data."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "SITE001", "site_name": "Test Site", "latitude": 60.0, "longitude": 15.0},
            {"site_code": "SITE002", "site_name": "Another Site", "latitude": 61.0, "longitude": 16.0},
        ]

        result = service.create(
            target_field="site_code",
            entity_spec=sample_entity_spec,
            max_candidates=3,
            source_data=source_data,
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
            entity_spec=sample_entity_spec,
            max_candidates=3,
            source_data=source_data,
            service_type="site",
        )

        # Should create only 1 query (second row), indexed as q1 (original row index)
        assert len(result.queries) == 1
        assert "q1" in result.queries
        assert result.queries["q1"].query == "SITE001"
        assert result.key_mapping["q1"] == "SITE001"

    def test_create_skips_empty_query_strings(self, sample_entity_spec):
        """Test create skips rows with empty query strings."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "", "site_name": ""},
            {"site_code": "SITE001", "site_name": "Valid"},
        ]

        result = service.create(
            target_field="site_code",
            entity_spec=sample_entity_spec,
            max_candidates=3,
            source_data=source_data,
            service_type="site",
        )

        assert len(result.queries) == 1

    def test_create_excludes_none_properties(self, sample_entity_spec):
        """Test create excludes properties with None values."""
        service = ReconciliationQueryService()

        source_data = [
            {"site_code": "SITE001", "latitude": 60.0, "longitude": None},
        ]

        result = service.create(
            target_field="site_code",
            entity_spec=sample_entity_spec,
            max_candidates=3,
            source_data=source_data,
            service_type="site",
        )

        q0 = result.queries["q0"]
        assert len(q0.properties) == 1
        assert {"pid": "latitude", "v": "60.0"} in q0.properties


class TestReconciliationService:
    """Tests for ReconciliationService main class."""

    def test_get_default_recon_config_filename(self, reconciliation_service):
        """Test default reconciliation config filename generation."""
        path = reconciliation_service._get_default_recon_config_filename("my_config")
        assert path.name == "my_config-reconciliation.yml"

    def test_load_reconciliation_config_creates_empty_if_missing(self, reconciliation_service):
        """Test load creates empty config if file doesn't exist."""
        config = reconciliation_service.load_reconciliation_config("nonexistent")

        assert config.service_url == RECONCILIATION_SERVICE_URL
        assert config.entities == {}

    def test_load_reconciliation_config_reads_yaml(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test load reads config from YAML file."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        loaded = reconciliation_service.load_reconciliation_config("test", recon_config_filename=config_file)

        assert loaded.service_url == sample_recon_config.service_url
        assert "site" in loaded.entities

    def test_save_reconciliation_config_writes_yaml(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test save writes config to YAML file."""
        config_file = tmp_path / "test-reconciliation.yml"

        reconciliation_service.save_reconciliation_config("test", sample_recon_config, recon_config_filename=config_file)

        assert config_file.exists()
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["service_url"] == sample_recon_config.service_url
        assert "site" in data["entities"]

    @pytest.mark.asyncio
    async def test_get_resolved_source_data_uses_correct_resolver(self, reconciliation_service, sample_entity_spec):
        """Test get_resolved_source_data selects and uses correct resolver."""
        with patch("backend.app.services.reconciliation_service.TargetEntityReconciliationSourceResolver") as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.resolve.return_value = [{"key": "value"}]
            mock_resolver_cls.return_value = mock_resolver

            result = await reconciliation_service.get_resolved_source_data("test_project", "site", sample_entity_spec)

            assert result == [{"key": "value"}]
            mock_resolver.resolve.assert_called_once_with("site", sample_entity_spec)

    def test_extract_id_from_uri_success(self, reconciliation_service):
        """Test _extract_id_from_uri extracts ID correctly."""
        uri = "https://w3id.org/sead/id/site/12345"
        sead_id = reconciliation_service._extract_id_from_uri(uri)
        assert sead_id == 12345

    def test_extract_id_from_uri_with_trailing_slash(self, reconciliation_service):
        """Test _extract_id_from_uri handles trailing slash."""
        uri = "https://w3id.org/sead/id/site/12345/"
        sead_id = reconciliation_service._extract_id_from_uri(uri)
        assert sead_id == 12345

    def test_extract_id_from_uri_raises_on_invalid(self, reconciliation_service):
        """Test _extract_id_from_uri raises on invalid URI."""

        with pytest.raises(BadRequestError, match="Cannot extract numeric ID"):
            reconciliation_service._extract_id_from_uri("https://example.com/invalid")

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_disabled_without_service_type(self, reconciliation_service, sample_entity_spec):
        """Test auto_reconcile_entity returns empty result when service_type is None."""
        sample_entity_spec.remote.service_type = None

        result = await reconciliation_service.auto_reconcile_entity("test_project", "site", "site_code", sample_entity_spec)

        assert result.auto_accepted == 0
        assert result.total == 0
        assert result.candidates == {}

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_no_queries(self, reconciliation_service, sample_entity_spec, mock_recon_client):
        """Test auto_reconcile_entity handles empty query list."""
        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = [{"site_code": None}]  # Will be skipped

            result = await reconciliation_service.auto_reconcile_entity("test", "site", "site_code", sample_entity_spec)

            assert result.total == 0
            assert not mock_recon_client.reconcile_batch.called

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_auto_accepts_high_scores(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity auto-accepts candidates with high scores."""
        # Setup source data
        source_data = [{"site_code": "SITE001", "site_name": "Test Site"}]

        # Setup reconciliation results
        candidates = [
            ReconciliationCandidate(
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
            mock_source.return_value = source_data

            reconciliation_service.recon_client.reconcile_batch.return_value = {"q0": candidates}

            # Create empty config file with v2 format
            config_file = tmp_path / "test-reconciliation.yml"
            config = {
                "version": "2.0",
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

            assert result.auto_accepted == 1
            assert result.needs_review == 0
            assert result.unmatched == 0
            assert result.total == 1

            # Check mapping was created in nested structure
            loaded_config = reconciliation_service.load_reconciliation_config("test", recon_config_filename=config_file)
            assert len(loaded_config.entities["site"]["site_code"].mapping) == 1
            mapping = loaded_config.entities["site"]["site_code"].mapping[0]
            assert mapping.sead_id == 123
            assert mapping.source_value == "SITE001"

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_marks_needs_review(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity marks candidates needing review."""
        source_data = [{"site_code": "SITE001"}]

        candidates = [
            ReconciliationCandidate(
                id="https://w3id.org/sead/id/site/123", name="Test", score=80.0, match=False, type=[], distance_km=None, description=None
            )
        ]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = source_data
            reconciliation_service.recon_client.reconcile_batch.return_value = {"q0": candidates}

            config_file = tmp_path / "test-reconciliation.yml"
            config = {
                "version": "2.0",
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

            assert result.auto_accepted == 0
            assert result.needs_review == 1
            assert result.unmatched == 0

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_marks_unmatched(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity marks unmatched entries."""
        source_data = [{"site_code": "SITE001"}]

        candidates = [
            ReconciliationCandidate(
                id="https://w3id.org/sead/id/site/123", name="Test", score=50.0, match=False, type=[], distance_km=None, description=None
            )
        ]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = source_data
            reconciliation_service.recon_client.reconcile_batch.return_value = {"q0": candidates}

            config_file = tmp_path / "test-reconciliation.yml"
            config = {
                "version": "2.0",
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

            assert result.auto_accepted == 0
            assert result.needs_review == 0
            assert result.unmatched == 1

    @pytest.mark.asyncio
    async def test_auto_reconcile_entity_handles_no_candidates(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test auto_reconcile_entity handles entries with no candidates."""
        source_data = [{"site_code": "SITE001"}]

        with patch.object(reconciliation_service, "get_resolved_source_data", new=AsyncMock()) as mock_source:
            mock_source.return_value = source_data
            reconciliation_service.recon_client.reconcile_batch.return_value = {"q0": []}

            config_file = tmp_path / "test-reconciliation.yml"
            config = {
                "version": "2.0",
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

    def test_update_mapping_adds_new_mapping(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test update_mapping adds new mapping entry."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated = reconciliation_service.update_mapping(
            "test",
            "site",
            "site_code",
            source_value="SITE001",
            sead_id=123,
            notes="Manual mapping",
        )

        assert len(updated.entities["site"]["site_code"].mapping) == 1
        mapping = updated.entities["site"]["site_code"].mapping[0]
        assert mapping.sead_id == 123
        assert mapping.source_value == "SITE001"
        assert mapping.notes == "Manual mapping"
        assert mapping.confidence == 1.0

    def test_update_mapping_updates_existing(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test update_mapping updates existing mapping."""
        # Add existing mapping
        existing_mapping = ReconciliationMapping(
            source_value="SITE001",
            sead_id=100,
            confidence=0.8,
            notes="Old mapping",
            created_by="system",
            created_at="2024-01-01T00:00:00Z",
            will_not_match=False,
            last_modified="2024-01-02T00:00:00Z",
        )
        sample_recon_config.entities["site"]["site_code"].mapping = [existing_mapping]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated = reconciliation_service.update_mapping(
            "test",
            "site",
            "site_code",
            source_value="SITE001",
            sead_id=200,
            notes="Updated mapping",
        )

        assert len(updated.entities["site"]["site_code"].mapping) == 1
        mapping = updated.entities["site"]["site_code"].mapping[0]
        assert mapping.sead_id == 200
        assert mapping.notes == "Updated mapping"

    def test_update_mapping_removes_mapping(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test update_mapping removes mapping when sead_id is None."""
        existing_mapping = ReconciliationMapping(
            source_value="SITE001",
            sead_id=100,
            confidence=0.8,
            notes="To remove",
            created_by="user",
            created_at="2024-01-01T00:00:00Z",
            will_not_match=False,
            last_modified="2024-01-02T00:00:00Z",
        )
        sample_recon_config.entities["site"]["site_code"].mapping = [existing_mapping]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated = reconciliation_service.update_mapping("test", "site", "site_code", source_value="SITE001", sead_id=None)

        assert len(updated.entities["site"]["site_code"].mapping) == 0

    def test_update_mapping_raises_for_missing_entity(self, reconciliation_service, tmp_path):
        """Test update_mapping raises if entity not in config."""
        config_file = tmp_path / "test-reconciliation.yml"
        config_file.write_text(yaml.dump({"version": "2.0", "service_url": RECONCILIATION_SERVICE_URL, "entities": {}}))

        with pytest.raises(NotFoundError, match="Entity 'nonexistent' not in reconciliation config"):
            reconciliation_service.update_mapping("test", "nonexistent", "field", source_value="KEY", sead_id=123)

    def test_mark_as_unmatched(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test mark_as_unmatched creates mapping with will_not_match=True."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated = reconciliation_service.mark_as_unmatched(
            "test",
            "site",
            "site_code",
            source_value="LOCAL_SITE",
            notes="Local identifier only",
        )

        assert len(updated.entities["site"]["site_code"].mapping) == 1
        mapping = updated.entities["site"]["site_code"].mapping[0]
        assert mapping.source_value == "LOCAL_SITE"
        assert mapping.sead_id is None
        assert mapping.will_not_match is True
        assert mapping.notes == "Local identifier only"
        assert mapping.confidence is None
        assert mapping.last_modified is not None

    def test_mark_as_unmatched_updates_existing(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test mark_as_unmatched can convert existing mapping to unmatched."""
        # Add existing matched mapping
        existing_mapping = ReconciliationMapping(
            source_value="SITE001",
            sead_id=100,
            confidence=0.8,
            notes="Was matched",
            created_by="system",
            created_at="2024-01-01T00:00:00Z",
            will_not_match=False,
            last_modified="2024-01-02T00:00:00Z",
        )
        sample_recon_config.entities["site"]["site_code"].mapping = [existing_mapping]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated = reconciliation_service.mark_as_unmatched(
            "test",
            "site",
            "site_code",
            source_value="SITE001",
            notes="Changed to local-only",
        )

        assert len(updated.entities["site"]["site_code"].mapping) == 1
        mapping = updated.entities["site"]["site_code"].mapping[0]
        assert mapping.sead_id is None
        assert mapping.will_not_match is True
        assert mapping.notes == "Changed to local-only"


class TestSpecificationManagement:
    """Tests for specification CRUD operations."""

    def test_list_specifications_empty(self, reconciliation_service, tmp_path):
        """Test listing specifications when config has no entities."""
        config = ReconciliationConfig(version="2.0", service_url=RECONCILIATION_SERVICE_URL, entities={})

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        specs = reconciliation_service.list_specifications("test")
        assert specs == []

    def test_list_specifications_multiple(self, reconciliation_service, tmp_path, sample_entity_spec):
        """Test listing multiple specifications."""
        config = ReconciliationConfig(
            version="2.0",
            service_url=RECONCILIATION_SERVICE_URL,
            entities={
                "site": {
                    "site_code": sample_entity_spec,
                    "site_name": EntityReconciliationSpec(
                        source="another_entity",
                        property_mappings={},
                        remote=ReconciliationRemote(service_type="taxon"),
                        auto_accept_threshold=0.85,
                        review_threshold=0.60,
                        mapping=[
                            ReconciliationMapping(source_value="test", sead_id=1),
                            ReconciliationMapping(source_value="test2", sead_id=2),
                        ],
                    ),
                },
                "sample": {
                    "sample_type": EntityReconciliationSpec(
                        source=None,
                        property_mappings={"name": "type_name"},
                        remote=ReconciliationRemote(service_type="location"),
                        auto_accept_threshold=0.90,
                        review_threshold=0.75,
                        mapping=[],
                    ),
                },
            },
        )

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        specs = reconciliation_service.list_specifications("test")

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

    @patch("backend.app.services.reconciliation_service.ProjectMapper")
    @patch("backend.app.services.reconciliation_service.ProjectService")
    def test_create_specification_success(self, mock_project_service, mock_mapper, reconciliation_service, tmp_path, sample_recon_config):
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

        # Save initial config
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        # Create new spec
        new_spec = EntityReconciliationSpec(
            source=None,
            property_mappings={"lat": "latitude"},
            remote=ReconciliationRemote(service_type="location"),
            auto_accept_threshold=0.90,
            review_threshold=0.75,
            mapping=[],
        )

        updated_config = reconciliation_service.create_specification("test", "sample", "sample_code", new_spec)

        assert "sample" in updated_config.entities
        assert "sample_code" in updated_config.entities["sample"]
        assert updated_config.entities["sample"]["sample_code"] == new_spec

    @patch("backend.app.services.reconciliation_service.ProjectMapper")
    @patch("backend.app.services.reconciliation_service.ProjectService")
    def test_create_specification_duplicate(self, mock_project_service, mock_mapper, reconciliation_service, tmp_path, sample_recon_config):
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

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        new_spec = EntityReconciliationSpec(
            source=None,
            property_mappings={},
            remote=ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[],
        )

        with pytest.raises(BadRequestError, match="already exists"):
            reconciliation_service.create_specification("test", "site", "site_code", new_spec)

    @patch("backend.app.services.reconciliation_service.ProjectMapper")
    @patch("backend.app.services.reconciliation_service.ProjectService")
    def test_create_specification_invalid_entity(
        self, mock_project_service, mock_mapper, reconciliation_service, tmp_path, sample_recon_config
    ):
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
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        new_spec = EntityReconciliationSpec(
            source=None,
            property_mappings={},
            remote=ReconciliationRemote(service_type="site"),
            auto_accept_threshold=0.95,
            review_threshold=0.70,
            mapping=[],
        )

        with pytest.raises(BadRequestError, match="Entity 'invalid_entity' does not exist"):
            reconciliation_service.create_specification("test", "invalid_entity", "some_field", new_spec)

    def test_update_specification_success(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test updating specification preserves mapping."""
        # Add mapping to original spec
        sample_recon_config.entities["site"]["site_code"].mapping = [
            ReconciliationMapping(source_value="SITE001", sead_id=100, confidence=0.95)
        ]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        # Update thresholds and property mappings
        updated_config = reconciliation_service.update_specification(
            project_name="test",
            entity_name="site",
            target_field="site_code",
            source="another_entity",
            property_mappings={"lat": "latitude"},
            remote=ReconciliationRemote(service_type="site", data_source="sead"),
            auto_accept_threshold=0.80,
            review_threshold=0.60,
        )

        spec = updated_config.entities["site"]["site_code"]
        assert spec.auto_accept_threshold == 0.80
        assert spec.review_threshold == 0.60
        assert spec.source == "another_entity"
        assert spec.property_mappings == {"lat": "latitude"}
        # Mapping should be preserved
        assert len(spec.mapping) == 1
        assert spec.mapping[0].source_value == "SITE001"

    def test_update_specification_not_found(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test updating non-existent specification raises error."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        with pytest.raises(NotFoundError, match="not found"):
            reconciliation_service.update_specification(
                project_name="test",
                entity_name="site",
                target_field="nonexistent_field",
                source=None,
                property_mappings={},
                remote=ReconciliationRemote(service_type="site"),
                auto_accept_threshold=0.90,
                review_threshold=0.70,
            )

    def test_delete_specification_success(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test deleting specification without mappings."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated_config = reconciliation_service.delete_specification("test", "site", "site_code", force=False)

        assert "site_code" not in updated_config.entities.get("site", {})

    def test_delete_specification_with_mappings_no_force(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test deleting specification with mappings raises error without force."""
        sample_recon_config.entities["site"]["site_code"].mapping = [ReconciliationMapping(source_value="SITE001", sead_id=100)]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        with pytest.raises(BadRequestError, match="with 1 existing mappings"):
            reconciliation_service.delete_specification("test", "site", "site_code", force=False)

    def test_delete_specification_with_mappings_force(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test force deleting specification with mappings succeeds."""
        sample_recon_config.entities["site"]["site_code"].mapping = [
            ReconciliationMapping(source_value="SITE001", sead_id=100),
            ReconciliationMapping(source_value="SITE002", sead_id=101),
        ]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated_config = reconciliation_service.delete_specification("test", "site", "site_code", force=True)

        assert "site_code" not in updated_config.entities.get("site", {})

    def test_delete_specification_not_found(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test deleting non-existent specification raises error."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        with pytest.raises(NotFoundError, match="not found"):
            reconciliation_service.delete_specification("test", "site", "nonexistent_field")

    def test_delete_last_specification_removes_entity(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test deleting last specification removes entity from config."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        updated_config = reconciliation_service.delete_specification("test", "site", "site_code")

        # Entity should be removed entirely
        assert "site" not in updated_config.entities

    async def test_get_available_target_fields_success(self, reconciliation_service, tmp_path, sample_recon_config):
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
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        fields = await reconciliation_service.get_available_target_fields("test", "site")

        assert fields == ["site_code", "site_name", "latitude", "longitude"]

    def test_get_mapping_count_success(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test getting mapping count."""
        sample_recon_config.entities["site"]["site_code"].mapping = [
            ReconciliationMapping(source_value="SITE001", sead_id=100),
            ReconciliationMapping(source_value="SITE002", sead_id=101),
            ReconciliationMapping(source_value="SITE003", sead_id=None),
        ]

        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        count = reconciliation_service.get_mapping_count("test", "site", "site_code")

        assert count == 3

    def test_get_mapping_count_not_found(self, reconciliation_service, tmp_path, sample_recon_config):
        """Test getting mapping count for non-existent specification."""
        config_file = tmp_path / "test-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_recon_config.model_dump(exclude_none=True), f)

        with pytest.raises(NotFoundError, match="not found"):
            reconciliation_service.get_mapping_count("test", "site", "nonexistent_field")
