"""Pydantic models for validation results."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ValidationError(BaseModel):
    """A validation error or warning."""

    severity: Literal["error", "warning", "info"] = Field(..., description="Severity level")
    entity: str | None = Field(default=None, description="Entity name where error occurred")
    field: str | None = Field(default=None, description="Field name where error occurred")
    message: str = Field(..., description="Error message")
    code: str | None = Field(default=None, description="Error code for programmatic handling")
    suggestion: str | None = Field(default=None, description="Suggested fix")


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
