"""Tests for validation models."""

from app.models.validation import ValidationError, ValidationResult


class TestValidationError:
    """Tests for ValidationError model."""

    def test_valid_error(self):
        """Test valid validation error."""
        error = ValidationError(
            severity="error",
            entity="sample",
            field="surrogate_id",
            message="Surrogate ID must end with _id",
            code="INVALID_SURROGATE_ID",
            suggestion="Rename to 'sample_id'",
        )
        assert error.severity == "error"
        assert error.entity == "sample"
        assert error.message == "Surrogate ID must end with _id"

    def test_warning(self):
        """Test warning validation error."""
        warning = ValidationError(
            severity="warning",
            message="This entity has no keys defined",
        )
        assert warning.severity == "warning"


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_configuration(self):
        """Test validation result for valid configuration."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_with_errors(self):
        """Test validation result with errors."""
        errors = [
            ValidationError(severity="error", message="Error 1"),
            ValidationError(severity="error", message="Error 2"),
        ]
        result = ValidationResult(is_valid=False, errors=errors)
        assert result.is_valid is False
        assert result.error_count == 2

    def test_with_warnings(self):
        """Test validation result with warnings."""
        warnings = [
            ValidationError(severity="warning", message="Warning 1"),
        ]
        result = ValidationResult(is_valid=True, warnings=warnings)
        assert result.warning_count == 1
        assert result.total_issues == 1

    def test_get_errors_for_entity(self):
        """Test filtering errors by entity."""
        errors = [
            ValidationError(severity="error", entity="sample", message="Error 1"),
            ValidationError(severity="error", entity="site", message="Error 2"),
            ValidationError(severity="error", entity="sample", message="Error 3"),
        ]
        result = ValidationResult(is_valid=False, errors=errors)

        sample_errors = result.get_errors_for_entity("sample")
        assert len(sample_errors) == 2
        assert all(e.entity == "sample" for e in sample_errors)

    def test_total_issues(self):
        """Test total_issues property."""
        result = ValidationResult(
            is_valid=False,
            errors=[ValidationError(severity="error", message="Error")],
            warnings=[
                ValidationError(severity="warning", message="Warning 1"),
                ValidationError(severity="warning", message="Warning 2"),
            ],
        )
        assert result.total_issues == 3
