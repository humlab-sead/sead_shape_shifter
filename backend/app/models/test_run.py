"""Models for configuration test runs."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestRunStatus(str, Enum):
    """Test run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(str, Enum):
    """Output format for test run results."""

    PREVIEW = "preview"
    CSV = "csv"
    JSON = "json"


class TestRunOptions(BaseModel):
    """Options for running a configuration test."""

    entities: Optional[List[str]] = Field(None, description="List of entity names to test. If None, tests all entities")
    max_rows_per_entity: int = Field(100, description="Maximum number of rows to process per entity", ge=10, le=10000)
    output_format: OutputFormat = Field(OutputFormat.PREVIEW, description="Output format for results")
    validate_foreign_keys: bool = Field(True, description="Validate foreign key relationships")
    validate_constraints: bool = Field(True, description="Validate constraints")
    stop_on_error: bool = Field(False, description="Stop processing on first error")


class ValidationIssue(BaseModel):
    """A validation issue found during test run."""

    entity_name: str = Field(..., description="Entity where issue was found")
    severity: str = Field(..., description="Issue severity: error, warning, info")
    message: str = Field(..., description="Issue description")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    location: Optional[str] = Field(None, description="Where the issue occurred")


class EntityTestResult(BaseModel):
    """Test result for a single entity."""

    # See https://github.com/pylint-dev/pylint/issues/10087 for why pylint reports no-member for container fields
    entity_name: str = Field(..., description="Entity name")
    status: str = Field(..., description="Processing status: success, failed, skipped")
    rows_in: int = Field(..., description="Number of input rows")
    rows_out: int = Field(..., description="Number of output rows")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    validation_issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues found")
    preview_rows: Optional[List[Dict[str, Any]]] = Field(None, description="Preview of output rows (first 10)")


class TestProgress(BaseModel):
    """Progress information for a running test."""

    run_id: str = Field(..., description="Test run ID")
    status: TestRunStatus = Field(..., description="Current status")
    current_entity: Optional[str] = Field(None, description="Entity currently being processed")
    entities_completed: int = Field(..., description="Number of entities completed")
    entities_total: int = Field(..., description="Total number of entities to process")
    progress_percentage: float = Field(..., description="Progress percentage (0-100)")
    elapsed_time_ms: int = Field(..., description="Elapsed time in milliseconds")
    estimated_time_remaining_ms: Optional[int] = Field(None, description="Estimated time remaining in milliseconds")


class TestRunResult(BaseModel):
    """Complete test run result."""

    run_id: str = Field(..., description="Unique test run ID")
    config_name: str = Field(..., description="Configuration name")
    status: TestRunStatus = Field(..., description="Overall status")
    started_at: datetime = Field(..., description="Test run start time")
    completed_at: Optional[datetime] = Field(None, description="Test run completion time")
    total_time_ms: int = Field(..., description="Total execution time in milliseconds")
    entities_processed: List[EntityTestResult] = Field(default_factory=list, description="Results for each entity")
    entities_total: int = Field(0, description="Total number of entities to process")
    entities_succeeded: int = Field(0, description="Number of entities that succeeded")
    entities_failed: int = Field(0, description="Number of entities that failed")
    entities_skipped: int = Field(0, description="Number of entities that were skipped")
    validation_issues: List[ValidationIssue] = Field(default_factory=list, description="All validation issues found")
    error_message: Optional[str] = Field(None, description="Overall error message if failed")
    options: TestRunOptions = Field(..., description="Test run options used")
    current_entity: Optional[str] = Field(None, description="Entity currently being processed")
    entities_completed: int = Field(0, description="Number of entities completed")


class TestRunRequest(BaseModel):
    """Request to start a test run."""

    config_name: str = Field(..., description="Configuration name to test")
    options: TestRunOptions = Field(default_factory=TestRunOptions, description="Test run options")
