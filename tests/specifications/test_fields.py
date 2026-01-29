"""Tests for field-level validators."""

import pytest

from src.specifications.fields import (
    EndsWithIdValidator,
    FieldExistsValidator,
    FieldIsNonEmptyValidator,
    FieldIsNotEmptyStringValidator,
    FieldIsStringListValidator,
    FieldTypeValidator,
    IsEmptyFieldValidator,
    IsExistingEntityValidator,
    IsOfCategoricalValuesValidator,
)


class TestFieldExistsValidator:
    """Tests for FieldExistsValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"sample": {"columns": ["site_id"], "keys": ["sample_id"], "nested": {"deep": {"value": "exists"}}}}}

    def test_field_exists(self, project_cfg):
        """Test validation passes when field exists."""
        validator = FieldExistsValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "columns")

        assert len(validator.errors) == 0

    def test_field_missing(self, project_cfg):
        """Test validation fails when field missing."""
        validator = FieldExistsValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "nonexistent")

        assert len(validator.errors) == 1
        assert "Field 'nonexistent' is required but missing" in validator.errors[0].message

    def test_nested_field_exists(self, project_cfg):
        """Test validation with nested field path."""
        validator = FieldExistsValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "nested.deep.value")

        assert len(validator.errors) == 0

    def test_warning_severity(self, project_cfg):
        """Test validation with warning severity."""
        validator = FieldExistsValidator(project_cfg, severity="W")

        validator.is_satisfied_by_field("sample", "missing_field")

        assert len(validator.errors) == 0
        assert len(validator.warnings) == 1


class TestIsEmptyFieldValidator:
    """Tests for IsEmptyFieldValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "sample": {
                    "empty_string": "",
                    "empty_list": [],
                    "empty_dict": {},
                    "none_value": None,
                    "non_empty_string": "entity",
                    "non_empty_list": ["item"],
                }
            }
        }

    def test_empty_string_passes(self, project_cfg):
        """Test that empty string passes validation."""
        validator = IsEmptyFieldValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "empty_string")

        assert len(validator.errors) == 0

    def test_empty_list_passes(self, project_cfg):
        """Test that empty list passes validation."""
        validator = IsEmptyFieldValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "empty_list")

        assert len(validator.errors) == 0

    def test_none_passes(self, project_cfg):
        """Test that None passes validation."""
        validator = IsEmptyFieldValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "none_value")

        assert len(validator.errors) == 0

    def test_non_empty_string_fails(self, project_cfg):
        """Test that non-empty string fails validation."""
        validator = IsEmptyFieldValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "non_empty_string")

        assert len(validator.errors) == 1
        assert "must be empty" in validator.errors[0].message

    def test_non_empty_list_fails(self, project_cfg):
        """Test that non-empty list fails validation."""
        validator = IsEmptyFieldValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "non_empty_list")

        assert len(validator.errors) == 1


class TestFieldIsStringListValidator:
    """Tests for FieldIsStringListValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "sample": {
                    "valid_list": ["a", "b", "c"],
                    "mixed_list": ["a", 1, "c"],
                    "not_a_list": "string",
                    "empty_list": [],
                    "list_with_none": ["a", None, "c"],
                }
            }
        }

    def test_valid_string_list(self, project_cfg):
        """Test that valid string list passes."""
        validator = FieldIsStringListValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "valid_list")

        assert len(validator.errors) == 0

    def test_empty_list_passes(self, project_cfg):
        """Test that empty list passes."""
        validator = FieldIsStringListValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "empty_list")

        assert len(validator.errors) == 0

    def test_mixed_list_fails(self, project_cfg):
        """Test that mixed type list fails."""
        validator = FieldIsStringListValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "mixed_list")

        assert len(validator.errors) == 1
        assert "must be a list of strings" in validator.errors[0].message

    def test_non_list_fails(self, project_cfg):
        """Test that non-list value fails."""
        validator = FieldIsStringListValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "not_a_list")

        assert len(validator.errors) == 1

    def test_list_with_none_fails(self, project_cfg):
        """Test that list with None fails."""
        validator = FieldIsStringListValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "list_with_none")

        assert len(validator.errors) == 1


class TestFieldIsNotEmptyStringValidator:
    """Tests for FieldIsNotEmptyStringValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "sample": {
                    "valid_string": "data",
                    "empty_string": "",
                    "whitespace_only": "   ",
                    "not_a_string": 123,
                }
            }
        }

    def test_valid_string(self, project_cfg):
        """Test that non-empty string passes."""
        validator = FieldIsNotEmptyStringValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "valid_string")

        assert len(validator.errors) == 0

    def test_empty_string_fails(self, project_cfg):
        """Test that empty string fails."""
        validator = FieldIsNotEmptyStringValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "empty_string")

        assert len(validator.errors) == 1
        assert "must be a non-empty string" in validator.errors[0].message

    def test_whitespace_only_fails(self, project_cfg):
        """Test that whitespace-only string fails."""
        validator = FieldIsNotEmptyStringValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "whitespace_only")

        assert len(validator.errors) == 1

    def test_non_string_fails(self, project_cfg):
        """Test that non-string value fails."""
        validator = FieldIsNotEmptyStringValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "not_a_string")

        assert len(validator.errors) == 1


class TestFieldIsNonEmptyValidator:
    """Tests for FieldIsNonEmptyValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "sample": {
                    "truthy_string": "data",
                    "truthy_list": [1, 2],
                    "truthy_number": 42,
                    "false_bool": False,
                    "zero": 0,
                    "empty_string": "",
                    "none_value": None,
                }
            }
        }

    def test_truthy_string(self, project_cfg):
        """Test that truthy string passes."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "truthy_string")

        assert len(validator.errors) == 0

    def test_truthy_list(self, project_cfg):
        """Test that non-empty list passes."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "truthy_list")

        assert len(validator.errors) == 0

    def test_truthy_number(self, project_cfg):
        """Test that non-zero number passes."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "truthy_number")

        assert len(validator.errors) == 0

    def test_false_fails(self, project_cfg):
        """Test that False fails."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "false_bool")

        assert len(validator.errors) == 1

    def test_zero_fails(self, project_cfg):
        """Test that 0 fails."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "zero")

        assert len(validator.errors) == 1

    def test_empty_string_fails(self, project_cfg):
        """Test that empty string fails."""
        validator = FieldIsNonEmptyValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "empty_string")

        assert len(validator.errors) == 1


class TestFieldTypeValidator:
    """Tests for FieldTypeValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"sample": {"string_field": "text", "int_field": 42, "list_field": [1, 2], "dict_field": {"key": "value"}}}}

    def test_string_type_match(self, project_cfg):
        """Test that string type matches."""
        validator = FieldTypeValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "string_field", expected_types=(str,))

        assert len(validator.errors) == 0

    def test_int_type_match(self, project_cfg):
        """Test that int type matches."""
        validator = FieldTypeValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "int_field", expected_types=(int,))

        assert len(validator.errors) == 0

    def test_multiple_types_match(self, project_cfg):
        """Test matching against multiple allowed types."""
        validator = FieldTypeValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "int_field", expected_types=(str, int, bool))

        assert len(validator.errors) == 0

    def test_type_mismatch(self, project_cfg):
        """Test that type mismatch fails."""
        validator = FieldTypeValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "string_field", expected_types=(int, list))

        assert len(validator.errors) == 1
        assert "must be of type(s)" in validator.errors[0].message

    def test_error_message_shows_types(self, project_cfg):
        """Test that error message shows expected types."""
        validator = FieldTypeValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "string_field", expected_types=(int, bool))

        assert len(validator.errors) == 1
        assert "int" in validator.errors[0].message
        assert "bool" in validator.errors[0].message


class TestIsExistingEntityValidator:
    """Tests for IsExistingEntityValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"sample": {"type": "sql", "source": "site"}, "site": {"type": "fixed", "source": "does_not_exist"}}}

    def test_existing_entity(self, project_cfg):
        """Test that existing entity passes."""
        validator = IsExistingEntityValidator(project_cfg, severity="E")

        # When the field name is an entity name
        validator.is_satisfied_by_field(entity_name="sample", field="source")

        assert len(validator.errors) == 0

    def test_non_existing_entity(self, project_cfg):
        """Test that non-existing entity fails."""
        validator = IsExistingEntityValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field(entity_name="site", field="source")

        assert len(validator.errors) == 1
        assert "must be an existing entity" in validator.errors[0].message


class TestEndsWithIdValidator:
    """Tests for EndsWithIdValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"sample": {"sample_id": "sample_id", "sample_name": "sample_name", "number_field": 123}}}

    def test_ends_with_id(self, project_cfg):
        """Test that field ending with _id passes."""
        validator = EndsWithIdValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "sample_id")

        assert len(validator.errors) == 0

    def test_does_not_end_with_id(self, project_cfg):
        """Test that field not ending with _id fails."""
        validator = EndsWithIdValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "sample_name")

        assert len(validator.errors) == 1
        assert "should end with '_id'" in validator.errors[0].message

    def test_non_string_value(self, project_cfg):
        """Test that non-string value fails."""
        validator = EndsWithIdValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "number_field")

        assert len(validator.errors) == 1


class TestIsOfCategoricalValuesValidator:
    """Tests for IsOfCategoricalValuesValidator."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {"entities": {"sample": {"type": "sql", "mode": "all", "status": "active", "count": 123}}}

    def test_value_in_categories(self, project_cfg):
        """Test that value in categories passes."""
        validator = IsOfCategoricalValuesValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "type", categories=["sql", "fixed", "entity"])

        assert len(validator.errors) == 0

    def test_value_not_in_categories(self, project_cfg):
        """Test that value not in categories fails."""
        validator = IsOfCategoricalValuesValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "mode", categories=["distinct", "unique"])

        assert len(validator.errors) == 1
        assert "should have a value in the specified categories" in validator.errors[0].message

    def test_non_string_value_passes(self, project_cfg):
        """Test that non-string value passes (doesn't validate)."""
        validator = IsOfCategoricalValuesValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "count", categories=["one", "two"])

        assert len(validator.errors) == 0  # Non-string values are not validated

    def test_empty_categories_list(self, project_cfg):
        """Test with empty categories list."""
        validator = IsOfCategoricalValuesValidator(project_cfg, severity="E")

        validator.is_satisfied_by_field("sample", "status", categories=[])

        assert len(validator.errors) == 1  # Any value should fail with empty categories
