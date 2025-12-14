"""
Query execution models for the Shape Shifter Configuration Editor.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result of a query execution."""

    rows: List[Dict[str, Any]] = Field(..., description="Query result rows as list of dictionaries")
    columns: List[str] = Field(..., description="Column names in the result set")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    is_truncated: bool = Field(default=False, description="Whether the result was truncated due to size limits")
    total_rows: Optional[int] = Field(default=None, description="Total number of rows in result (if known, before truncation)")


class QueryValidation(BaseModel):
    """Result of query validation."""

    is_valid: bool = Field(..., description="Whether the query is valid and safe to execute")
    errors: List[str] = Field(default_factory=list, description="Validation errors (syntax, security, etc.)")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings about the query")
    statement_type: Optional[str] = Field(default=None, description="Type of SQL statement (SELECT, INSERT, etc.)")
    tables: List[str] = Field(default_factory=list, description="Tables referenced in the query")


class QueryPlan(BaseModel):
    """Query execution plan."""

    plan_text: str = Field(..., description="Formatted query execution plan")
    estimated_cost: Optional[float] = Field(default=None, description="Estimated query cost (if available)")
    estimated_rows: Optional[int] = Field(default=None, description="Estimated number of rows to be processed")


class QueryExecution(BaseModel):
    """Request to execute a query."""

    query: str = Field(..., description="SQL query to execute", min_length=1)
    limit: int = Field(default=100, description="Maximum number of rows to return", ge=1, le=10000)
    timeout: int = Field(default=30, description="Query timeout in seconds", ge=1, le=300)
