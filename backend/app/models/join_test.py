"""Models for foreign key join testing."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class JoinTestRequest(BaseModel):
    """Request model for testing a foreign key join."""

    entity_name: str = Field(..., description="Name of the entity to test")
    foreign_key_index: int = Field(..., description="Index of the foreign key in the entity's foreign_keys list")
    sample_size: int = Field(default=100, ge=10, le=1000, description="Number of rows to test")


class UnmatchedRow(BaseModel):
    """A row that failed to match during the join."""

    row_data: dict[str, Any] = Field(..., description="The actual row data")
    local_key_values: list[Any] = Field(..., description="Values of the local join keys")
    reason: str = Field(..., description="Reason for the mismatch")


class CardinalityInfo(BaseModel):
    """Information about join cardinality."""

    expected: str = Field(..., description="Expected cardinality (e.g., 'one_to_one', 'many_to_one')")
    actual: str = Field(..., description="Detected actual cardinality")
    matches: bool = Field(..., description="Whether actual matches expected")
    explanation: str = Field(..., description="Explanation of the cardinality result")


class JoinStatistics(BaseModel):
    """Statistics about the join operation."""

    total_rows: int = Field(..., description="Total number of rows in the source entity")
    matched_rows: int = Field(..., description="Number of rows that matched successfully")
    unmatched_rows: int = Field(..., description="Number of rows that failed to match")
    match_percentage: float = Field(..., description="Percentage of rows that matched (0-100)")
    null_key_rows: int = Field(default=0, description="Number of rows with null in join keys")
    duplicate_matches: int = Field(default=0, description="Number of rows that matched multiple times")


class JoinTestResult(BaseModel):
    """Result of testing a foreign key join."""

    entity_name: str = Field(..., description="Name of the entity tested")
    remote_entity: str = Field(..., description="Name of the remote entity")
    local_keys: list[str] = Field(..., description="Local join key columns")
    remote_keys: list[str] = Field(..., description="Remote join key columns")
    join_type: str = Field(..., description="Type of join (inner, left, etc.)")

    statistics: JoinStatistics = Field(..., description="Join statistics")
    cardinality: CardinalityInfo = Field(..., description="Cardinality information")

    unmatched_sample: list[UnmatchedRow] = Field(default_factory=list, description="Sample of unmatched rows (max 10)")

    execution_time_ms: int = Field(..., description="Time taken to perform the test")
    success: bool = Field(..., description="Whether the join test passed validation")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations for improvement")


class JoinTestError(BaseModel):
    """Error details when a join test fails."""

    entity_name: str
    remote_entity: str
    error_type: str
    message: str
    details: Optional[dict[str, Any]] = None
