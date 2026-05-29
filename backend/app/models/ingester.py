"""Pydantic models for ingester API requests and responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IngesterMetadataResponse(BaseModel):
    """Response model for ingester metadata."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "sead",
                "name": "SEAD Clearinghouse",
                "description": "Import SEAD Clearinghouse Excel submissions",
                "version": "1.0.0",
                "supported_formats": ["xlsx"],
            }
        }
    )

    key: str = Field(..., description="Unique identifier for the ingester")
    name: str = Field(..., description="Display name of the ingester")
    description: str = Field(..., description="Description of what the ingester does")
    version: str = Field(..., description="Version of the ingester")
    supported_formats: list[str] = Field(..., description="List of supported file formats")


class ValidateRequest(BaseModel):
    """Request model for validation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "/path/to/data.xlsx",
                "config": {"ignore_columns": ["date_updated", "*_uuid"]},
            }
        }
    )

    source: str = Field(..., description="Path to source file or data to validate")
    config: dict[str, Any] = Field(default_factory=dict, description="Optional configuration parameters for validation")
    submission_context: dict[str, Any] | None = Field(
        default=None, description="Optional submission context for ingesters that need operator metadata"
    )
    deploy_strategy: str | None = Field(
        default=None, description="Optional deploy artifact strategy for ingesters that support multiple outputs"
    )


class ValidateResponse(BaseModel):
    """Response model for validation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "errors": [],
                "warnings": ["Column 'date_updated' will be ignored"],
            }
        }
    )

    is_valid: bool = Field(..., description="Whether the data is valid")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings")
    infos: list[str] = Field(default_factory=list, description="List of informational messages")
    pending_confirmation_report: dict[str, Any] | None = Field(
        default=None,
        description="Pending confirmation report when Binding Set confirmation blocks progress",
    )


class IngestRequest(BaseModel):
    """Request model for ingestion endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "/path/to/data.xlsx",
                "config": {
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "dbname": "sead_staging",
                        "user": "sead_user",
                    },
                    "ignore_columns": ["date_updated", "*_uuid"],
                },
                "submission_name": "dendro_2026_01",
                "data_types": "dendro",
                "output_folder": "output/dendro",
                "do_register": True,
                "explode": True,
            }
        }
    )

    source: str = Field(..., description="Path to source file or data to ingest")
    config: dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for ingestion")
    submission_name: str = Field(..., description="Name for this submission")
    data_types: str = Field(..., description="Type of data being ingested (e.g., 'dendro', 'ceramics')")
    output_folder: str = Field(default="output", description="Folder for output files")
    do_register: bool = Field(default=False, description="Register submission in database")
    explode: bool = Field(default=False, description="Explode submission into public tables")
    submission_context: dict[str, Any] | None = Field(
        default=None, description="Optional submission context for ingesters that need operator metadata"
    )
    deploy_strategy: str | None = Field(
        default=None, description="Optional deploy artifact strategy for ingesters that support multiple outputs"
    )


class IngestResponse(BaseModel):
    """Response model for ingestion endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "records_processed": 1250,
                "message": "Successfully ingested dendro_2026_01",
                "submission_id": 42,
                "output_path": "output/dendro/dendro_2026_01_20260111_143022",
            }
        }
    )

    success: bool = Field(..., description="Whether ingestion was successful")
    records_processed: int = Field(default=0, description="Number of records processed")
    message: str = Field(..., description="Status message")
    submission_id: int | None = Field(None, description="Database submission ID if registered")
    output_path: str | None = Field(None, description="Path to output files")
    error_details: str | None = Field(None, description="Detailed error information when ingestion is incomplete or failed")
    deploy_artifact: dict[str, Any] | None = Field(
        default=None,
        description="In-memory deploy artifact containing SQL statements and package metadata",
    )
    pending_confirmation_report: dict[str, Any] | None = Field(
        default=None,
        description="Pending confirmation report when Binding Set confirmation blocks progress",
    )
