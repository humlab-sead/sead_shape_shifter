from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.validation import ValidationCategory, ValidationPriority
from src.specifications.constraints import ValidationIssue as LinkerValidationIssue
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
        metadata={"expected_column": "sample_name"},
    )

    result = ValidationMapper.from_core_issue(issue, default_category=ValidationCategory.DATA)

    assert result.severity == "warning"
    assert result.entity == "sample"
    assert result.field == "columns"
    assert result.code == "COLUMN_NOT_FOUND"
    assert result.suggestion == "Fix the source schema"
    assert result.category == ValidationCategory.DATA
    assert result.priority == ValidationPriority.HIGH
    assert result.metadata == {"expected_column": "sample_name"}


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


def test_from_linker_issue_preserves_fk_identity_metadata() -> None:
    """Linker issue metadata keeps the foreign-key identity and the added context keys."""
    issue = LinkerValidationIssue(
        issue_type="row_count_mismatch",
        severity="warning",
        local_entity="users",
        remote_entity="accounts",
        message="users -> accounts: join changed the row count",
        metadata={
            "row_count_before": 3,
            "row_count_after": 2,
            "join_type": "inner",
            "fk_index": 2,
            "fk_signature": "abc123",
            "link_pass": "after_unnest",
        },
    )

    result = ValidationMapper.from_linker_issue(issue)

    assert result.metadata["fk_index"] == 2
    assert result.metadata["fk_signature"] == "abc123"
    assert result.metadata["link_pass"] == "after_unnest"
    assert result.metadata["issue_type"] == "row_count_mismatch"
    assert result.metadata["remote_entity"] == "accounts"


def test_to_api_error_preserves_integrity_identity_metadata() -> None:
    """Integrity identity and count reach the API error unchanged."""
    issue = ValidationIssue(
        severity="warning",
        entity="orders",
        field="foreign_keys[].entity",
        message="2 foreign key value(s) not found in 'customers'",
        code="FK_DATA_INTEGRITY",
        suggestion="Ensure all foreign key values exist in referenced entity.",
        category="data",
        priority="medium",
        auto_fixable=False,
        metadata={"orphan_count": 2, "fk_index": 1, "fk_signature": "abc123"},
    )

    result = ValidationMapper.to_api_error(issue)

    assert result.metadata == {"orphan_count": 2, "fk_index": 1, "fk_signature": "abc123"}
