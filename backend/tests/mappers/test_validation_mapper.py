from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.validation import ValidationCategory, ValidationPriority
from src.target_model.conformance import ConformanceIssue
from src.validators.data_validators import ValidationIssue


def test_from_core_issue_maps_validation_issue() -> None:
    issue = ValidationIssue(
        severity="warning",
        entity="sample",
        field="columns",
        message="Configured column is missing",
        code="COLUMN_NOT_FOUND",
        suggestion="Fix the source schema",
        category="data",
        priority="high",
        auto_fixable=False,
    )

    result = ValidationMapper.from_core_issue(issue, default_category=ValidationCategory.DATA)

    assert result.severity == "warning"
    assert result.entity == "sample"
    assert result.field == "columns"
    assert result.code == "COLUMN_NOT_FOUND"
    assert result.suggestion == "Fix the source schema"
    assert result.category == ValidationCategory.DATA
    assert result.priority == ValidationPriority.HIGH


def test_from_core_issue_maps_conformance_defaults() -> None:
    issue = ConformanceIssue(code="MISSING_REQUIRED_ENTITY", message="Target model requires entity 'site'", entity="site")

    result = ValidationMapper.from_core_issue(
        issue,
        default_category=ValidationCategory.CONFORMANCE,
        default_priority=ValidationPriority.HIGH,
    )

    assert result.severity == "error"
    assert result.entity == "site"
    assert result.field is None
    assert result.category == ValidationCategory.CONFORMANCE
    assert result.priority == ValidationPriority.HIGH


def test_from_core_issue_uses_column_as_field_fallback() -> None:
    issue = ConformanceIssue(code="MISSING_REQUIRED_COLUMN", message="Missing target column", entity="sample", column="site_id")

    result = ValidationMapper.from_core_issue(
        issue,
        default_category=ValidationCategory.CONFORMANCE,
        default_priority=ValidationPriority.HIGH,
    )

    assert result.field == "site_id"
