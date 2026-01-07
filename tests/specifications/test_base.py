"""Tests for base specification classes and utilities."""

import pytest

# Import to register validators
from src.specifications.base import (
    FIELD_VALIDATORS,
    FieldValidator,
    FieldValidatorRegistry,
    ProjectSpecification,
    SpecificationIssue,
)
from src.utility import dotget


class TestSpecificationIssue:
    """Tests for SpecificationIssue class."""

    def test_create_error(self):
        """Test creating an error issue."""
        issue = SpecificationIssue(severity="error", message="Test error", entity="test_entity")

        assert issue.severity == "error"
        assert issue.message == "Test error"
        assert issue.entity_name == "test_entity"
        assert issue.entity_field is None
        assert issue.column_name is None

    def test_create_warning_with_field(self):
        """Test creating a warning with field context."""
        issue = SpecificationIssue(
            severity="warning", message="Test warning", entity="test_entity", field="test_field", column="test_column"
        )

        assert issue.severity == "warning"
        assert issue.entity_field == "test_field"
        assert issue.column_name == "test_column"

    def test_string_representation_minimal(self):
        """Test string representation with minimal info."""
        issue = SpecificationIssue(severity="error", message="Test error")
        result = str(issue)

        assert "[ERROR]" in result
        assert "Test error" in result
        assert "Entity" not in result

    def test_string_representation_full(self):
        """Test string representation with all context."""
        issue = SpecificationIssue(severity="warning", message="Test warning", entity="sample", field="columns", column="site_id")
        result = str(issue)

        assert "[WARNING]" in result
        assert "Entity 'sample':" in result
        assert "Test warning" in result
        assert "(field: columns)" in result
        assert "(column: site_id)" in result

    def test_repr_equals_str(self):
        """Test that __repr__ equals __str__."""
        issue = SpecificationIssue(severity="error", message="Test", entity="test")
        assert repr(issue) == str(issue)

    def test_kwargs_storage(self):
        """Test that additional kwargs are stored."""
        issue = SpecificationIssue(severity="error", message="Test", extra_data="value", custom_field=123)

        assert issue.kwargs["extra_data"] == "value"
        assert issue.kwargs["custom_field"] == 123


class ConcreteSpecification(ProjectSpecification):
    """Concrete implementation for testing abstract base class."""

    def is_satisfied_by(self, **kwargs) -> bool:
        """Simple implementation that always returns True."""
        return True


class TestProjectSpecification:
    """Tests for ProjectSpecification base class."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "sample": {"type": "sql", "columns": ["site_id", "sample_name"], "keys": ["sample_id"]},
                "site": {"type": "fixed", "columns": ["site_name"], "values": [["Site A"], ["Site B"]]},
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql", "host": "localhost"}}},
        }

    def test_initialization(self, project_cfg):
        """Test specification initialization."""
        spec = ConcreteSpecification(project_cfg)

        assert spec.project_cfg == project_cfg
        assert not spec.errors
        assert not spec.warnings

    def test_clear(self, project_cfg):
        """Test clearing errors and warnings."""
        spec = ConcreteSpecification(project_cfg)
        spec.add_error("Test error", entity="sample")
        spec.add_warning("Test warning", entity="site")

        assert len(spec.errors) == 1
        assert len(spec.warnings) == 1

        spec.clear()

        assert len(spec.errors) == 0
        assert len(spec.warnings) == 0

    def test_add_error(self, project_cfg):
        """Test adding error."""
        spec = ConcreteSpecification(project_cfg)
        spec.add_error("Critical error", entity="sample", field="columns")

        assert len(spec.errors) == 1
        assert spec.errors[0].severity == "error"
        assert spec.errors[0].message == "Critical error"
        assert spec.errors[0].entity_name == "sample"
        assert spec.errors[0].entity_field == "columns"

    def test_add_warning(self, project_cfg):
        """Test adding warning."""
        spec = ConcreteSpecification(project_cfg)
        spec.add_warning("Minor issue", entity="site")

        assert len(spec.warnings) == 1
        assert spec.warnings[0].severity == "warning"
        assert spec.warnings[0].message == "Minor issue"

    def test_has_errors(self, project_cfg):
        """Test has_errors method."""
        spec = ConcreteSpecification(project_cfg)
        assert not spec.has_errors()

        spec.add_error("Error", entity="test")
        assert spec.has_errors()

    def test_has_warnings(self, project_cfg):
        """Test has_warnings method."""
        spec = ConcreteSpecification(project_cfg)
        assert not spec.has_warnings()

        spec.add_warning("Warning", entity="test")
        assert spec.has_warnings()

    def test_merge(self, project_cfg):
        """Test merging specifications."""
        spec1 = ConcreteSpecification(project_cfg)
        spec1.add_error("Error 1", entity="test1")
        spec1.add_warning("Warning 1", entity="test1")

        spec2 = ConcreteSpecification(project_cfg)
        spec2.add_error("Error 2", entity="test2")
        spec2.add_warning("Warning 2", entity="test2")

        result = spec1.merge(spec2)

        assert result == spec1  # Should return self
        assert len(spec1.errors) == 2
        assert len(spec1.warnings) == 2
        assert spec1.errors[0].message == "Error 1"
        assert spec1.errors[1].message == "Error 2"

    def test_get_entity_cfg(self, project_cfg):
        """Test getting entity configuration."""
        spec = ConcreteSpecification(project_cfg)

        sample_cfg = spec.get_entity_cfg("sample")
        assert sample_cfg["type"] == "sql"
        assert "site_id" in sample_cfg["columns"]

    def test_get_entity_cfg_missing(self, project_cfg):
        """Test getting non-existent entity configuration."""
        spec = ConcreteSpecification(project_cfg)

        missing_cfg = spec.get_entity_cfg("nonexistent")
        assert missing_cfg == {}

    def test_exists(self, project_cfg):
        """Test entity existence check."""
        spec = ConcreteSpecification(project_cfg)

        assert spec.entity_exists("sample")
        assert spec.entity_exists("site")
        assert not spec.entity_exists("nonexistent")

    def test_check_fields_with_valid_validator(self, project_cfg):
        """Test check_fields with registered validator."""
        spec = ConcreteSpecification(project_cfg)

        # Should not raise any errors
        spec.check_fields("sample", ["columns"], "exists/E")
        # Validator will add errors if field doesn't exist

    def test_check_fields_with_severity_parsing(self, project_cfg):
        """Test check_fields severity level parsing."""
        spec = ConcreteSpecification(project_cfg)

        # Test error severity
        spec.check_fields("sample", ["nonexistent_field"], "exists/E")
        assert len(spec.errors) > 0

        spec.clear()

        # Test warning severity
        spec.check_fields("sample", ["nonexistent_field"], "exists/W")
        assert len(spec.warnings) > 0

    def test_check_fields_multiple_validators(self, project_cfg):
        """Test check_fields with multiple validators."""
        spec = ConcreteSpecification(project_cfg)

        spec.check_fields("sample", ["columns", "keys"], "exists/E,is_string_list/E")
        # Should run both validators

    def test_check_fields_with_custom_message(self, project_cfg):
        """Test check_fields with custom message."""
        spec = ConcreteSpecification(project_cfg)

        spec.check_fields("sample", ["missing"], "exists/E", message="Custom error message")


class ConcreteFieldValidator(FieldValidator):
    """Concrete field validator for testing."""

    def rule_predicate(self, target_cfg: dict, entity_name: str, field: str, **kwargs) -> bool:
        """Check if field value equals 'valid'. Returns True if valid (no error), False if invalid."""

        value = dotget(target_cfg, field)
        # Return False when value != 'valid' (which means rule failed, so rule_fail will be called)
        return value == "valid"

    def rule_fail(self, target_cfg: dict, entity_name: str, field: str, **kwargs) -> None:
        """Log failure."""
        self.rule_handler(f"Field {field} is not 'valid'", entity=entity_name, column=field)


class TestFieldValidator:
    """Tests for FieldValidator base class."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"test_entity": {"field1": "valid", "field2": "invalid"}}}

    def test_initialization(self, project_cfg):
        """Test field validator initialization."""
        validator = ConcreteFieldValidator(project_cfg, severity="E")

        assert validator.severity == "E"
        assert validator.project_cfg == project_cfg

    def test_default_severity(self, project_cfg):
        """Test default severity is error."""
        validator = ConcreteFieldValidator(project_cfg)

        assert validator.severity == "E"

    def test_is_satisfied_by_multiple_fields(self, project_cfg):
        """Test validating multiple fields."""
        validator = ConcreteFieldValidator(project_cfg)

        result = validator.is_satisfied_by(entity_name="test_entity", fields=["field1", "field2"])

        assert result is True  # Always returns True
        assert len(validator.errors) == 1  # field2 should fail

    def test_is_satisfied_by_field_with_target_cfg(self, project_cfg):
        """Test validating field with custom target_cfg."""
        validator = ConcreteFieldValidator(project_cfg)

        custom_cfg = {"custom_field": "invalid"}
        validator.is_satisfied_by_field("test", "custom_field", target_cfg=custom_cfg)

        # Field is not 'valid', so validation should fail
        assert len(validator.errors) == 1

    def test_is_satisfied_by_field_uses_entity_cfg(self, project_cfg):
        """Test that is_satisfied_by_field uses entity config by default."""
        validator = ConcreteFieldValidator(project_cfg)

        validator.is_satisfied_by_field("test_entity", "field1")
        # rule_predicate returns True when field == 'valid', which means no error
        assert len(validator.errors) == 0  # field1 is 'valid'

        validator.is_satisfied_by_field("test_entity", "field2")
        # rule_predicate returns False when field != 'valid', so rule_fail is called
        assert len(validator.errors) == 1  # field2 is 'invalid'

    def test_rule_handler_error(self, project_cfg):
        """Test rule_handler returns add_error for error severity."""
        validator = ConcreteFieldValidator(project_cfg, severity="E")

        assert validator.rule_handler == validator.add_error

    def test_rule_handler_warning(self, project_cfg):
        """Test rule_handler returns add_warning for warning severity."""
        validator = ConcreteFieldValidator(project_cfg, severity="W")

        assert validator.rule_handler == validator.add_warning


class TestFieldValidatorRegistry:
    """Tests for FieldValidatorRegistry."""

    def test_registry_is_instance(self):
        """Test that FIELD_VALIDATORS is a registry instance."""
        assert isinstance(FIELD_VALIDATORS, FieldValidatorRegistry)

    def test_registry_has_validators(self):
        """Test that validators are registered."""
        # Check for some known validators
        assert "exists" in FIELD_VALIDATORS.items
        assert "is_string_list" in FIELD_VALIDATORS.items
        assert "not_empty_string" in FIELD_VALIDATORS.items

    def test_registry_get_validator(self):
        """Test getting a validator from registry."""
        validator_class = FIELD_VALIDATORS.get("exists")

        assert validator_class is not None
        assert issubclass(validator_class, FieldValidator)

    def test_can_instantiate_registered_validator(self):
        """Test that registered validators can be instantiated."""
        validator_class = FIELD_VALIDATORS.get("exists")
        project_cfg = {"entities": {}}

        validator = validator_class(project_cfg, severity="W")

        assert isinstance(validator, FieldValidator)
        assert validator.severity == "W"
