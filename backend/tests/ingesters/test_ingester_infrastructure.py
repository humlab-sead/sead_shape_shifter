"""Unit tests for ingester protocol and registry."""

import pytest

from backend.app.ingesters import IngesterConfig, IngesterMetadata, get_ingester_registry
from backend.app.ingesters.protocol import Ingester, IngestionResult, TableSourceIngester, ValidationResult
from backend.app.ingesters.registry import IngesterRegistry
from ingesters.sead_change_request import SeadChangeRequestIngester


@pytest.fixture(name="registry")
def get_ingesters() -> IngesterRegistry:
    """Ensure ingester registry is initialized for tests."""
    registry: IngesterRegistry = get_ingester_registry()
    return registry


class FileOnlyIngester:
    """Minimal file-only ingester used to check the optional table capability."""

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="file_only",
            name="File Only",
            description="Test ingester with file input only",
            version="0.0.0",
            supported_formats=["xlsx"],
            requires_config=False,
        )

    def __init__(self, config: IngesterConfig) -> None:
        self.config = config

    async def validate(self, _source: str) -> ValidationResult:
        return ValidationResult(is_valid=True)

    async def ingest(self, _source: str) -> IngestionResult:
        return IngestionResult(success=True, message="ok")


class TestIngesterRegistry:
    """Tests for the IngesterRegistry."""

    def test_registry_imports_successfully(self, registry: IngesterRegistry):
        """Test that the registry can be imported."""
        assert registry is not None
        assert hasattr(registry, "items")
        assert hasattr(registry, "get_metadata_list")

    def test_get_metadata_list(self, registry: IngesterRegistry):
        """Test getting list of all ingester metadata."""
        metadata_list: list[IngesterMetadata] = registry.get_metadata_list()
        assert len(metadata_list) >= 1
        assert any(m.key == "sead_change_request" for m in metadata_list)

    def test_get_ingester_by_key(self, registry: IngesterRegistry):
        """Test getting an ingester class by key."""
        ingester_cls: None | type[Ingester] = registry.get("sead_change_request")
        assert ingester_cls is not None
        assert ingester_cls == SeadChangeRequestIngester

    def test_sead_change_request_ingester_registered(self, registry: IngesterRegistry):
        """Test that SeadChangeRequestIngester is automatically registered."""
        assert "sead_change_request" in registry.items
        assert registry.items["sead_change_request"] == SeadChangeRequestIngester

    def test_get_sead_change_request_ingester_by_key(self, registry: IngesterRegistry):
        """Test getting the new scaffold ingester by key."""
        ingester_cls: None | type[Ingester] = registry.get("sead_change_request")
        assert ingester_cls is not None
        assert ingester_cls == SeadChangeRequestIngester


class TestTableSourceCapability:
    """Table input is an optional capability beside the shared file protocol."""

    @staticmethod
    def _change_request_ingester() -> SeadChangeRequestIngester:
        return SeadChangeRequestIngester(IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user"))

    def test_change_request_ingester_supports_table_sources(self):
        """The Change Request ingester should satisfy both the file and table protocols."""
        ingester = self._change_request_ingester()

        assert isinstance(ingester, Ingester)
        assert isinstance(ingester, TableSourceIngester)
        assert isinstance(SeadChangeRequestIngester, TableSourceIngester)

    def test_file_only_ingester_does_not_satisfy_table_protocol(self):
        """An ingester without table methods should not satisfy the table protocol."""
        ingester = FileOnlyIngester(IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user"))

        assert isinstance(ingester, Ingester)
        assert not isinstance(ingester, TableSourceIngester)

    def test_validation_result_structure(self):
        """Test ValidationResult dataclass."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning 1"],
            infos=["Info 1"],
        )

        assert result.is_valid is True
        assert result.has_errors is False
        assert result.has_warnings is True
        assert len(result.warnings) == 1
        assert len(result.infos) == 1

    def test_ingestion_result_structure(self):
        """Test IngestionResult dataclass."""
        result = IngestionResult(
            success=True,
            message="Success",
            submission_id=123,
            tables_processed=5,
            records_inserted=100,
            error_details=None,
        )

        assert result.success is True
        assert result.submission_id == 123
        assert result.tables_processed == 5
        assert result.records_inserted == 100
        assert result.error_details is None
        assert result.output_path is None


class TestSeadChangeRequestIngester:
    """Tests for the SeadChangeRequestIngester scaffold."""

    def test_get_metadata(self):
        """Test getting scaffold ingester metadata."""
        metadata = SeadChangeRequestIngester.get_metadata()

        assert isinstance(metadata, IngesterMetadata)
        assert metadata.key == "sead_change_request"
        assert metadata.name == "SEAD Change Request"
        assert metadata.version == "0.1.0"
        assert metadata.requires_config is True
        assert not metadata.supported_formats

    def test_ingester_creation(self):
        """Test creating the scaffold ingester instance."""
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
        )

        ingester = SeadChangeRequestIngester(config)
        assert ingester is not None
        assert ingester.config == config


class TestIngesterConfig:
    """Tests for IngesterConfig dataclass."""

    def test_config_defaults(self):
        """Test IngesterConfig default values."""
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
        )

        assert config.password is None
        assert config.submission_name == ""
        assert config.data_types == ""
        assert config.output_folder == "output"
        assert config.check_only is False
        assert config.register is True
        assert config.explode is True
        assert config.extra is None

    def test_config_with_all_fields(self):
        """Test IngesterConfig with all fields specified."""
        config = IngesterConfig(
            host="db.example.com",
            port=5433,
            dbname="production_db",
            user="admin",
            password="secret",
            submission_name="2026-01-11_MySubmission",
            data_types="dendro",
            output_folder="/tmp/output",
            check_only=True,
            register=False,
            explode=False,
            extra={"ignore_columns": ["date_updated"]},
        )

        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.dbname == "production_db"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.submission_name == "2026-01-11_MySubmission"
        assert config.data_types == "dendro"
        assert config.output_folder == "/tmp/output"
        assert config.check_only is True
        assert config.register is False
        assert config.explode is False
        assert config.extra == {"ignore_columns": ["date_updated"]}
