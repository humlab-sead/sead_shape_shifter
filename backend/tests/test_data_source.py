"""Tests for data source models and service."""

import pytest
from pydantic import ValidationError

from app.models.data_source import (
    DataSourceConfig,
    DataSourceTestResult,
    DataSourceType,
    TableMetadata,
    ColumnMetadata,
)


class TestDataSourceType:
    """Tests for DataSourceType enum."""
    
    def test_normalize_postgres(self):
        """Test normalization of postgres driver names."""
        assert DataSourceType.normalize("postgres") == DataSourceType.POSTGRESQL
        assert DataSourceType.normalize("postgresql") == DataSourceType.POSTGRESQL
        assert DataSourceType.normalize("POSTGRES") == DataSourceType.POSTGRESQL
    
    def test_normalize_access(self):
        """Test normalization of access driver names."""
        assert DataSourceType.normalize("access") == DataSourceType.ACCESS
        assert DataSourceType.normalize("ucanaccess") == DataSourceType.ACCESS
        assert DataSourceType.normalize("UCANACCESS") == DataSourceType.ACCESS
    
    def test_normalize_invalid(self):
        """Test normalization with invalid driver."""
        with pytest.raises(ValueError, match="Unsupported data source type"):
            DataSourceType.normalize("invalid")


class TestDataSourceConfig:
    """Tests for DataSourceConfig model."""
    
    def test_postgresql_config(self):
        """Test PostgreSQL data source configuration."""
        config = DataSourceConfig(
            name="test_db",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
        )
        
        assert config.name == "test_db"
        assert config.driver == DataSourceType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.effective_database == "testdb"
        assert config.is_database_source()
        assert not config.is_file_source()
    
    def test_postgres_alias(self):
        """Test postgres alias normalization."""
        config = DataSourceConfig(
            name="test_db",
            driver="postgres",
            host="localhost",
            database="testdb",
        )
        
        assert config.driver == DataSourceType.POSTGRESQL
        assert config.get_loader_driver() == "postgres"
    
    def test_access_config(self):
        """Test Access database configuration."""
        config = DataSourceConfig(
            name="access_db",
            driver="ucanaccess",
            filename="./data/test.mdb",
            options={"ucanaccess_dir": "lib/ucanaccess"},
        )
        
        assert config.name == "access_db"
        assert config.driver == DataSourceType.ACCESS
        assert config.effective_file_path == "./data/test.mdb"
        assert config.options["ucanaccess_dir"] == "lib/ucanaccess"
        assert config.is_database_source()
        assert config.get_loader_driver() == "ucanaccess"
    
    def test_csv_config(self):
        """Test CSV file configuration."""
        config = DataSourceConfig(
            name="csv_data",
            driver="csv",
            filename="./data/test.csv",
            options={
                "sep": ";",
                "encoding": "utf-8",
            },
        )
        
        assert config.name == "csv_data"
        assert config.driver == DataSourceType.CSV
        assert config.effective_file_path == "./data/test.csv"
        assert config.is_file_source()
        assert not config.is_database_source()
    
    def test_dbname_alias(self):
        """Test dbname as alias for database."""
        config = DataSourceConfig(
            name="test_db",
            driver="postgresql",
            host="localhost",
            dbname="testdb",
        )
        
        assert config.effective_database == "testdb"
    
    def test_file_path_alias(self):
        """Test file_path as alias for filename."""
        config = DataSourceConfig(
            name="csv_data",
            driver="csv",
            file_path="./data/test.csv",
        )
        
        assert config.effective_file_path == "./data/test.csv"
    
    def test_invalid_port(self):
        """Test validation of port number."""
        with pytest.raises(ValidationError):
            DataSourceConfig(
                name="test_db",
                driver="postgresql",
                host="localhost",
                port=99999,  # Invalid port
            )
    
    def test_password_is_secret(self):
        """Test that password is stored as SecretStr."""
        from pydantic import SecretStr
        
        config = DataSourceConfig(
            name="test_db",
            driver="postgresql",
            host="localhost",
            password=SecretStr("secret123"),
        )
        
        assert isinstance(config.password, SecretStr)
        assert config.password.get_secret_value() == "secret123"
        
        # Password should not appear in string representation
        config_str = str(config)
        assert "secret123" not in config_str


class TestDataSourceTestResult:
    """Tests for DataSourceTestResult model."""
    
    def test_successful_connection(self):
        """Test successful connection result."""
        result = DataSourceTestResult(
            success=True,
            message="Connected successfully",
            connection_time_ms=150,
            metadata={"table_count": 42},
        )
        
        assert result.success
        assert result.connection_time_ms == 150
        assert result.connection_time_seconds == 0.15
        assert result.metadata["table_count"] == 42
    
    def test_failed_connection(self):
        """Test failed connection result."""
        result = DataSourceTestResult(
            success=False,
            message="Connection timeout",
            connection_time_ms=30000,
        )
        
        assert not result.success
        assert "timeout" in result.message.lower()
        assert result.connection_time_seconds == 30.0


class TestTableMetadata:
    """Tests for TableMetadata model."""
    
    def test_table_metadata(self):
        """Test table metadata."""
        metadata = TableMetadata(
            name="users",
            schema="public",
            row_count=1000,
            comment="User accounts table",
        )
        
        assert metadata.name == "users"
        assert metadata.schema == "public"
        assert metadata.row_count == 1000
        assert metadata.comment == "User accounts table"


class TestColumnMetadata:
    """Tests for ColumnMetadata model."""
    
    def test_column_metadata(self):
        """Test column metadata."""
        column = ColumnMetadata(
            name="user_id",
            data_type="integer",
            nullable=False,
            is_primary_key=True,
        )
        
        assert column.name == "user_id"
        assert column.data_type == "integer"
        assert not column.nullable
        assert column.is_primary_key
    
    def test_column_with_defaults(self):
        """Test column metadata with default values."""
        column = ColumnMetadata(
            name="created_at",
            data_type="timestamp",
            nullable=True,
            default="CURRENT_TIMESTAMP",
        )
        
        assert column.name == "created_at"
        assert column.default == "CURRENT_TIMESTAMP"
        assert not column.is_primary_key  # Default value
