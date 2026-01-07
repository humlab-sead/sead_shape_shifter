"""Models for executing full workflow."""

from pydantic import BaseModel, Field


class DispatcherMetadata(BaseModel):
    """Metadata about a dispatcher."""

    key: str = Field(..., description="Dispatcher key (registered name)")
    target_type: str = Field(..., description="Target type: 'file', 'folder', or 'database'")
    description: str = Field(..., description="Human-readable description of the dispatcher")
    extension: str | None = Field(None, description="File extension for the dispatcher target, if applicable")


class ExecuteRequest(BaseModel):
    """Request to execute full workflow."""

    dispatcher_key: str = Field(..., description="Key of the dispatcher to use")
    target: str = Field(..., description="Target location (file path, folder path, or data source name)")
    run_validation: bool = Field(True, description="Run validation before execution")
    translate: bool = Field(False, description="Apply translations to output")
    drop_foreign_keys: bool = Field(False, description="Drop foreign key columns from output")
    default_entity: str | None = Field(None, description="Default entity to use if not specified")


class ExecuteResult(BaseModel):
    """Result of workflow execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    message: str = Field(..., description="Success or error message")
    target: str = Field(..., description="Output target location")
    dispatcher_key: str = Field(..., description="Dispatcher that was used")
    target_type: str = Field(
        ...,
        description="Target type for the dispatcher (file, folder, database, or unknown)",
    )
    entity_count: int = Field(..., description="Number of entities processed")
    validation_passed: bool | None = Field(None, description="Whether validation passed (if run)")
    error_details: str | None = Field(None, description="Detailed error information if failed")
    download_path: str | None = Field(
        None,
        description="Relative API path that can be used to download the generated file (file targets only)",
    )
