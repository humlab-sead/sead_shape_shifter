"""Protocol definitions for data ingesters.

This module defines the standard interface that all ingesters must implement,
along with configuration and result data classes.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class IngesterMetadata:
    """Metadata about an ingester.
    
    Attributes:
        key: Unique identifier for the ingester (e.g., 'sead')
        name: Human-readable name (e.g., 'SEAD Clearinghouse')
        description: Description of what the ingester does
        version: Ingester version string
        supported_formats: List of supported file formats (e.g., ['xlsx', 'xls'])
        requires_config: Whether ingester requires configuration
    """

    key: str
    name: str
    description: str
    version: str
    supported_formats: list[str]
    requires_config: bool


@dataclass
class ValidationResult:
    """Result of ingester validation.
    
    Attributes:
        is_valid: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages
        infos: List of informational messages
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0


@dataclass
class IngestionResult:
    """Result of ingestion operation.
    
    Attributes:
        success: Whether ingestion succeeded
        message: Success or error message
        submission_id: ID of created submission (if applicable)
        tables_processed: Number of tables processed
        records_inserted: Number of records inserted
        error_details: Detailed error information if failed
    """

    success: bool
    message: str
    submission_id: int | None = None
    tables_processed: int = 0
    records_inserted: int = 0
    error_details: str | None = None


@dataclass
class IngesterConfig:
    """Configuration for an ingester instance.
    
    This is the base configuration class. Specific ingesters may require
    additional configuration fields passed via the 'extra' dictionary.
    
    Attributes:
        host: Database host
        port: Database port
        dbname: Database name
        user: Database user
        password: Database password (optional)
        submission_name: Name for the submission
        data_types: Description of data types being ingested
        output_folder: Folder for intermediate output files
        check_only: Only validate, don't ingest
        register: Register submission in database
        explode: Explode data to public tables
        extra: Additional ingester-specific options
    """

    host: str
    port: int
    dbname: str
    user: str
    password: str | None = None
    submission_name: str = ""
    data_types: str = ""
    output_folder: str = "output"
    check_only: bool = False
    register: bool = True
    explode: bool = True
    extra: dict[str, Any] | None = None


@runtime_checkable
class Ingester(Protocol):
    """Protocol defining the standard ingester interface.
    
    All ingesters must implement this protocol to be compatible with
    the Shape Shifter ingestion system.
    """

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        """Get metadata about this ingester.
        
        Returns:
            IngesterMetadata with ingester details
        """
        ...

    def __init__(self, config: IngesterConfig) -> None:
        """Initialize ingester with configuration.
        
        Args:
            config: Ingester configuration
        """
        ...

    async def validate(self, excel_file: Path | str) -> ValidationResult:
        """Validate Excel file without ingesting.
        
        This method should check that the Excel file conforms to the
        expected schema and contains valid data. It should not make
        any changes to the database.
        
        Args:
            excel_file: Path to Excel file to validate
            
        Returns:
            ValidationResult with errors, warnings, and info messages
        """
        ...

    async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
        """Ingest Excel file into target system.
        
        This method performs the actual data ingestion. If validate_first
        is True, it should run validation before ingesting and abort if
        validation fails.
        
        Args:
            excel_file: Path to Excel file to ingest
            validate_first: Run validation before ingesting
            
        Returns:
            IngestionResult with success status and details
        """
        ...
