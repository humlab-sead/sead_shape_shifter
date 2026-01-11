"""Unit tests for ingester protocol and registry."""


from backend.app.ingesters import IngesterConfig, IngesterMetadata, Ingesters, SeadIngester
from backend.app.ingesters.protocol import IngestionResult, ValidationResult


class TestIngesterRegistry:
    """Tests for the IngesterRegistry."""

    def test_registry_imports_successfully(self):
        """Test that the registry can be imported."""
        assert Ingesters is not None
        assert hasattr(Ingesters, "items")
        assert hasattr(Ingesters, "get_metadata_list")

    def test_sead_ingester_registered(self):
        """Test that SeadIngester is automatically registered."""
        assert "sead" in Ingesters.items
        assert Ingesters.items["sead"] == SeadIngester

    def test_get_metadata_list(self):
        """Test getting list of all ingester metadata."""
        metadata_list = Ingesters.get_metadata_list()
        assert len(metadata_list) >= 1
        assert any(m.key == "sead" for m in metadata_list)

    def test_get_ingester_by_key(self):
        """Test getting an ingester class by key."""
        ingester_cls = Ingesters.get("sead")
        assert ingester_cls is not None
        assert ingester_cls == SeadIngester


class TestSeadIngester:
    """Tests for the SeadIngester class."""

    def test_get_metadata(self):
        """Test getting SeadIngester metadata."""
        metadata = SeadIngester.get_metadata()

        assert isinstance(metadata, IngesterMetadata)
        assert metadata.key == "sead"
        assert metadata.name == "SEAD Clearinghouse"
        assert metadata.version == "1.0.0"
        assert "xlsx" in metadata.supported_formats
        assert metadata.requires_config is True

    def test_ingester_creation(self):
        """Test creating a SeadIngester instance."""
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            submission_name="test_submission",
            data_types="test",
            extra={"ignore_columns": []},  # Provide explicit ignore_columns to avoid ConfigValue lookup
        )

        ingester = SeadIngester(config)
        assert ingester is not None
        assert ingester.config == config
        assert ingester.schema_service is not None

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
