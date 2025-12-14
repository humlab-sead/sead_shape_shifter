"""Pydantic models for validation results."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ValidationCategory(str, Enum):
    """Category of validation check."""

    STRUCTURAL = "structural"  # Configuration structure issues
    DATA = "data"  # Issues found in actual data
    PERFORMANCE = "performance"  # Performance-related warnings


class ValidationPriority(str, Enum):
    """Priority level for validation checks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationError(BaseModel):
    """A validation error or warning."""

    severity: Literal["error", "warning", "info"] = Field(..., description="Severity level")
    entity: str | None = Field(default=None, description="Entity name where error occurred")
    field: str | None = Field(default=None, description="Field name where error occurred")
    message: str = Field(..., description="Error message")
    code: str | None = Field(default=None, description="Error code for programmatic handling")
    suggestion: str | None = Field(default=None, description="Suggested fix")
    category: ValidationCategory = Field(default=ValidationCategory.STRUCTURAL, description="Validation category")
    priority: ValidationPriority = Field(default=ValidationPriority.MEDIUM, description="Validation priority")
    auto_fixable: bool = Field(default=False, description="Whether this issue can be auto-fixed")


class ValidationResult(BaseModel):
    """Result of configuration validation."""

    is_valid: bool = Field(..., description="Whether configuration is valid")
    errors: list[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: list[ValidationError] = Field(default_factory=list, description="Validation warnings")
    info: list[ValidationError] = Field(default_factory=list, description="Informational messages")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")

    @model_validator(mode="after")
    def calculate_counts(self) -> "ValidationResult":
        """Calculate error and warning counts from lists."""
        self.error_count = len(self.errors)
        self.warning_count = len(self.warnings)
        return self

    @property
    def total_issues(self) -> int:
        """Total number of issues (errors + warnings + info)."""
        return self.error_count + self.warning_count + len(self.info)

    def get_errors_for_entity(self, entity_name: str) -> list[ValidationError]:
        """Get all errors for a specific entity."""
        return [e for e in self.errors if e.entity == entity_name]

    def get_warnings_for_entity(self, entity_name: str) -> list[ValidationError]:
        """Get all warnings for a specific entity."""
        return [e for e in self.warnings if e.entity == entity_name]
