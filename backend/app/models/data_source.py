"""Data source models for Phase 2 data-aware features."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class DataSourceType(str, Enum):
    """Supported data source types."""

    POSTGRESQL = "postgresql"
    POSTGRES = "postgres"  # Alias for postgresql
    ACCESS = "access"
    UCANACCESS = "ucanaccess"  # Alias for access
    SQLITE = "sqlite"
    CSV = "csv"

    @classmethod
    def normalize(cls, value: str) -> "DataSourceType":
        """Normalize driver names to canonical form."""
        mapping = {
            "postgres": cls.POSTGRESQL,
            "postgresql": cls.POSTGRESQL,
            "access": cls.ACCESS,
            "ucanaccess": cls.ACCESS,
            "sqlite": cls.SQLITE,
            "csv": cls.CSV,
        }
        normalized = mapping.get(value.lower())
        if not normalized:
            raise ValueError(f"Unsupported data source type: {value}")
        return normalized


class DataSourceConfig(BaseModel):
    """Configuration for a data source connection.

    This model represents both database connections (PostgreSQL, Access, SQLite)
    and file-based sources (CSV).

    For database connections:
        - driver: postgresql, access, or sqlite
        - Connection details (host, port, database, username, password)
        - Or connection_string for custom connections

    For CSV sources:
        - driver: csv
        - options: dict with pandas.read_csv parameters

    Environment variable substitution is supported using ${VAR_NAME} syntax.
    """

    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., description="Unique identifier for this data source")
    driver: DataSourceType = Field(..., description="Data source driver type")

    # Database connection fields (optional, used for PostgreSQL, SQLite)
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port", ge=1, le=65535)
    database: Optional[str] = Field(None, description="Database name")
    dbname: Optional[str] = Field(None, description="Database name (alias for database)")
    username: Optional[str] = Field(None, description="Database username")
    password: Optional[SecretStr] = Field(None, description="Database password (sensitive)")

    # File path (for Access, SQLite, CSV)
    filename: Optional[str] = Field(None, description="File path for file-based sources")
    file_path: Optional[str] = Field(None, description="File path (alias for filename)")

    # Custom connection string (advanced)
    connection_string: Optional[str] = Field(None, description="Custom connection string")

    # Additional options (driver-specific)
    options: Optional[dict[str, Any]] = Field(
        None, description="Driver-specific options (e.g., ucanaccess_dir for Access, pandas options for CSV)"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Human-readable description")

    @field_validator("driver", mode="before")
    @classmethod
    def normalize_driver(cls, v: str) -> DataSourceType:
        """Normalize driver name to canonical form."""
        return DataSourceType.normalize(v)

    @property
    def effective_database(self) -> Optional[str]:
        """Get database name, checking both 'database' and 'dbname' fields."""
        return self.database or self.dbname

    @property
    def effective_file_path(self) -> Optional[str]:
        """Get file path, checking both 'filename' and 'file_path' fields."""
        return self.filename or self.file_path

    def is_database_source(self) -> bool:
        """Check if this is a database connection (vs file-based)."""
        return self.driver in (
            DataSourceType.POSTGRESQL,
            DataSourceType.POSTGRES,
            DataSourceType.ACCESS,
            DataSourceType.UCANACCESS,
            DataSourceType.SQLITE,
        )

    def is_file_source(self) -> bool:
        """Check if this is a file-based source."""
        return self.driver == DataSourceType.CSV

    def get_loader_driver(self) -> str:
        """Get the driver name for the existing loader system."""
        mapping = {
            DataSourceType.POSTGRESQL: "postgres",
            DataSourceType.POSTGRES: "postgres",
            DataSourceType.ACCESS: "ucanaccess",
            DataSourceType.UCANACCESS: "ucanaccess",
            DataSourceType.SQLITE: "sqlite",
            DataSourceType.CSV: "csv",
        }
        return mapping[self.driver]


class DataSourceTestResult(BaseModel):
    """Result of testing a data source connection."""

    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Success or error message")
    connection_time_ms: int = Field(..., description="Time taken to connect in milliseconds", ge=0)
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata (e.g., database version, table count)")

    @property
    def connection_time_seconds(self) -> float:
        """Get connection time in seconds."""
        return self.connection_time_ms / 1000.0


class DataSourceStatus(BaseModel):
    """Current status of a data source."""

    name: str = Field(..., description="Data source name")
    is_connected: bool = Field(..., description="Whether currently connected")
    last_test_result: Optional[DataSourceTestResult] = Field(None, description="Result of last connection test")
    in_use_by_entities: list[str] = Field(default_factory=list, description="Entity names using this data source")


class TableMetadata(BaseModel):
    """Metadata about a database table."""

    name: str = Field(..., description="Table name")
    schema: Optional[str] = Field(None, description="Schema name (for databases that support schemas)")  # type: ignore
    row_count: Optional[int] = Field(None, description="Approximate row count", ge=0)
    comment: Optional[str] = Field(None, description="Table comment/description")


class ColumnMetadata(BaseModel):
    """Metadata about a table column."""

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type (database-specific)")
    nullable: bool = Field(..., description="Whether column allows NULL values")
    default: Optional[str] = Field(None, description="Default value")
    is_primary_key: bool = Field(False, description="Whether this is a primary key column")
    max_length: Optional[int] = Field(None, description="Max length for string columns")


class TableSchema(BaseModel):
    """Complete schema information for a table."""

    table_name: str = Field(..., description="Table name")
    columns: list[ColumnMetadata] = Field(..., description="Column definitions")
    primary_keys: list[str] = Field(default_factory=list, description="Primary key column names")
    indexes: list[str] = Field(default_factory=list, description="Index names")
    row_count: Optional[int] = Field(None, description="Approximate row count")
    foreign_keys: list["ForeignKeyMetadata"] = Field(default_factory=list, description="Foreign key relationships")

class ForeignKeyMetadata(BaseModel):
    """Metadata about a foreign key relationship."""

    column: str = Field(..., description="Local column name")
    referenced_table: str = Field(..., description="Referenced table name")
    referenced_column: str = Field(..., description="Referenced column name")
    constraint_name: Optional[str] = Field(None, description="Foreign key constraint name")
