"""SEAD Clearinghouse ingester implementation.

This module provides the SeadIngester class which implements the Ingester protocol
for ingesting data into SEAD Clearinghouse PostgreSQL databases.
"""

from pathlib import Path

from loguru import logger

from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    IngestionResult,
    ValidationResult,
)
from backend.app.ingesters.registry import Ingesters
from backend.app.ingesters.sead.metadata import SchemaService, SeadSchema
from backend.app.ingesters.sead.process import ImportService, Options
from backend.app.ingesters.sead.specification import SpecificationError, SubmissionSpecification
from backend.app.ingesters.sead.submission import Submission


@Ingesters.register(key="sead")
class SeadIngester:
    """Ingester for SEAD Clearinghouse database.

    This ingester handles the complete workflow of validating and ingesting
    Excel data files into a SEAD Clearinghouse PostgreSQL database, including:

    1. Loading and validating Excel data against SEAD schema
    2. Applying transformation policies
    3. Generating CSV files for database upload
    4. Registering submissions in the clearinghouse
    5. Uploading data to staging tables
    6. Exploding data into public schema tables

    The ingester uses the established SEAD clearinghouse import workflow
    that has been battle-tested with real archaeological data submissions.
    """

    def __init__(self, config: IngesterConfig) -> None:
        """Initialize SEAD ingester with configuration.

        Args:
            config: Ingester configuration including database connection details
        """
        self.config = config

        # Build database URI
        password_part = f":{self.config.password}" if self.config.password else ""
        self.db_uri = (
            f"postgresql+psycopg://{self.config.user}{password_part}" f"@{self.config.host}:{self.config.port}/{self.config.dbname}"
        )

        # Initialize schema service (schema loaded lazily on first use)
        self.schema_service = SchemaService(
            db_uri=self.db_uri,
            ignore_columns=self.config.extra.get("ignore_columns") if self.config.extra else None,
        )
        self.schema: SeadSchema | None = None

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        """Get metadata about this ingester.

        Returns:
            IngesterMetadata with ingester details
        """
        return IngesterMetadata(
            key="sead",
            name="SEAD Clearinghouse",
            description="Ingest data into SEAD Clearinghouse PostgreSQL database with validation and transformation",
            version="1.0.0",
            supported_formats=["xlsx"],
            requires_config=True,
        )

    async def _load_schema(self) -> SeadSchema:
        """Load SEAD schema from database if not already loaded.

        Returns:
            SeadSchema instance with database metadata
        """
        if self.schema is None:
            logger.debug("Loading SEAD schema from database...")
            self.schema = self.schema_service.load()
            logger.debug(f"Loaded schema with {len(self.schema.keys())} tables")
        return self.schema

    async def validate(self, excel_file: Path | str) -> ValidationResult:
        """Validate Excel file against SEAD schema.

        This performs comprehensive validation including:
        - Schema compliance (correct tables and columns)
        - Data type checking
        - Foreign key validation
        - Required field validation
        - Data integrity checks

        Args:
            excel_file: Path to Excel file to validate

        Returns:
            ValidationResult with validation status and messages
        """
        try:
            logger.info(f"Validating Excel file: {excel_file}")

            # Load schema
            schema = await self._load_schema()

            # Load submission with transformation policies
            logger.debug("Loading submission and applying policies...")
            submission = Submission.load(
                schema=schema,
                source=str(excel_file),
                service=self.schema_service,
                apply_policies=True,
            )

            # Run validation specifications
            logger.debug("Running validation specifications...")
            specification = SubmissionSpecification(
                schema=schema,
                ignore_columns=self.config.extra.get("ignore_columns") if self.config.extra else None,
                raise_errors=False,
            )

            is_valid = specification.is_satisfied_by(submission)

            # Log summary
            if is_valid:
                logger.info(f"Validation passed with {len(specification.warnings)} warnings")
            else:
                logger.warning(f"Validation failed with {len(specification.errors)} errors, " f"{len(specification.warnings)} warnings")

            return ValidationResult(
                is_valid=is_valid,
                errors=specification.errors,
                warnings=specification.warnings,
                infos=specification.infos,
            )

        except SpecificationError as e:
            logger.error(f"Specification error during validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=e.messages.errors if hasattr(e, "messages") else [str(e)],
                warnings=e.messages.warnings if hasattr(e, "messages") else [],
                infos=e.messages.infos if hasattr(e, "messages") else [],
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Validation failed with exception: {e}")
            return ValidationResult(is_valid=False, errors=[f"Validation error: {str(e)}"], warnings=[], infos=[])

    async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
        """Ingest Excel file into SEAD database.

        This performs the complete ingestion workflow:
        1. Optional validation
        2. CSV generation from Excel data
        3. Database registration
        4. Upload to staging tables
        5. Explode to public schema

        Args:
            excel_file: Path to Excel file to ingest
            validate_first: Run validation before ingesting (recommended)

        Returns:
            IngestionResult with success status and details
        """
        try:
            logger.info(f"Ingesting Excel file: {excel_file}")

            # Validate first if requested
            if validate_first:
                validation = await self.validate(excel_file)
                if not validation.is_valid:
                    logger.error("Validation failed, aborting ingestion")
                    return IngestionResult(
                        success=False,
                        message="Validation failed",
                        submission_id=None,
                        tables_processed=0,
                        records_inserted=0,
                        error_details="\n".join(validation.errors),
                    )
                logger.info("Validation passed, proceeding with ingestion")

            # Build import options
            opts = Options(
                filename=str(excel_file),
                skip=False,
                submission_id=None,
                submission_name=self.config.submission_name,
                data_types=self.config.data_types,
                table_names=[],
                check_only=self.config.check_only,
                register=self.config.register,
                explode=self.config.explode,
                timestamp=True,
                ignore_columns=self.config.extra.get("ignore_columns") if self.config.extra else None,
                output_folder=self.config.output_folder,
                database={
                    "host": self.config.host,
                    "port": self.config.port,
                    "dbname": self.config.dbname,
                    "user": self.config.user,
                },
                transfer_format="csv",
                dump_to_csv=False,
            )

            # Load schema
            schema = await self._load_schema()

            # Create import service and process submission
            logger.debug("Creating import service and processing submission...")
            import_service = ImportService(opts=opts, schema=schema, service=self.schema_service)

            # Process the submission
            import_service.process(process_target=str(excel_file))

            # Get results
            submission_id = opts.submission_id
            tables_processed = len([t for t in schema.keys() if not schema[t].is_lookup])

            logger.info(f"Ingestion completed successfully: submission_id={submission_id}, " f"tables_processed={tables_processed}")

            return IngestionResult(
                success=True,
                message=f"Successfully ingested submission '{self.config.submission_name}'",
                submission_id=submission_id,
                tables_processed=tables_processed,
                records_inserted=0,  # TODO: Track this in ImportService
                error_details=None,
            )

        except SpecificationError as e:
            error_msg = f"Specification error: {str(e)}"
            logger.error(error_msg)
            return IngestionResult(
                success=False,
                message="Ingestion failed due to specification error",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=error_msg,
            )
        except Exception as e:  # pylint: disable=broad-except
            error_msg = f"Ingestion error: {str(e)}"
            logger.exception(error_msg)
            return IngestionResult(
                success=False,
                message="Ingestion failed",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=error_msg,
            )
