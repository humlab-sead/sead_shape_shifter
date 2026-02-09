"""Tests for pure domain data validators."""

import pandas as pd

from src.validators.data_validators import (
    ColumnExistsValidator,
    DataTypeCompatibilityValidator,
    DuplicateKeysValidator,
    ForeignKeyDataValidator,
    ForeignKeyIntegrityValidator,
    NaturalKeyUniquenessValidator,
    NonEmptyResultValidator,
    ValidationIssue,
)


class TestColumnExistsValidator:
    """Tests for ColumnExistsValidator."""

    def test_validates_all_columns_exist(self):
        """Test passes when all configured columns exist."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
        issues = ColumnExistsValidator.validate(df, ["a", "b"], "test_entity")
        assert not issues

    def test_reports_missing_columns(self):
        """Test reports errors for missing columns."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        issues = ColumnExistsValidator.validate(df, ["a", "b", "c", "d"], "test_entity")

        assert len(issues) == 2
        assert all(issue.code == "COLUMN_NOT_FOUND" for issue in issues)
        assert all(issue.severity == "error" for issue in issues)
        assert {issue.message for issue in issues} == {
            "Column 'c' is configured but does not exist in data",
            "Column 'd' is configured but does not exist in data",
        }

    def test_empty_dataframe_no_errors(self):
        """Test empty DataFrame doesn't raise errors."""
        df = pd.DataFrame()
        issues = ColumnExistsValidator.validate(df, ["a", "b"], "test_entity")
        assert not issues

    def test_no_configured_columns_no_errors(self):
        """Test no configured columns doesn't raise errors."""
        df = pd.DataFrame({"a": [1, 2]})
        issues = ColumnExistsValidator.validate(df, [], "test_entity")
        assert not issues

    def test_unnest_value_vars_excluded_from_validation(self):
        """Test that columns in unnest.value_vars are not validated (they get melted)."""
        # After unnest operation, value_vars columns are melted away
        # DataFrame only has id_vars + var_name + value_name columns
        df = pd.DataFrame(
            {
                "site_id": [1, 2],
                "location_type": ["Ort", "Land"],
                "location_value": ["Berlin", "Germany"],
            }
        )

        # Entity config shows that Ort, Land, Staat are value_vars that got melted
        entity_config = {
            "columns": ["site_id", "Ort", "Land", "Staat"],  # Configured columns include value_vars
            "unnest": {
                "id_vars": ["site_id"],
                "value_vars": ["Ort", "Land", "Staat"],  # These got melted
                "var_name": "location_type",
                "value_name": "location_value",
            },
        }

        # Validation should ONLY check id_vars + var_name + value_name, not value_vars
        issues = ColumnExistsValidator.validate(
            df,
            entity_config["columns"],
            "location",
            entity_config,
        )

        # No errors because value_vars (Ort, Land, Staat) are excluded from validation
        assert not issues

    def test_unnest_reports_missing_non_value_vars(self):
        """Test that missing columns not in value_vars are still reported."""
        df = pd.DataFrame(
            {
                "location_type": ["Ort", "Land"],
                "location_value": ["Berlin", "Germany"],
            }
        )

        entity_config = {
            "columns": ["site_id", "Ort", "Land", "Staat"],
            "unnest": {
                "id_vars": ["site_id"],
                "value_vars": ["Ort", "Land", "Staat"],
                "var_name": "location_type",
                "value_name": "location_value",
            },
        }

        # site_id is NOT in value_vars, so it should be validated and reported missing
        issues = ColumnExistsValidator.validate(
            df,
            entity_config["columns"],
            "location",
            entity_config,
        )

        assert len(issues) == 1
        assert issues[0].code == "COLUMN_NOT_FOUND"
        assert "site_id" in issues[0].message

    def test_no_unnest_config_validates_all_columns(self):
        """Test that without unnest config, all columns are validated normally."""
        df = pd.DataFrame({"a": [1, 2]})
        entity_config = {"columns": ["a", "b", "c"]}

        issues = ColumnExistsValidator.validate(
            df,
            entity_config["columns"],
            "test_entity",
            entity_config,
        )

        assert len(issues) == 2
        assert {issue.message for issue in issues} == {
            "Column 'b' is configured but does not exist in data",
            "Column 'c' is configured but does not exist in data",
        }

    def test_unnest_validates_id_vars_but_not_value_vars(self):
        """Test that id_vars are validated while value_vars are excluded."""
        # DataFrame with only some id_vars and the melt output columns
        df = pd.DataFrame(
            {
                "Befu": [1, 2],
                # "Projekt": MISSING - this is an id_var and SHOULD be reported
                # "arbodat_code": MISSING - this is an id_var and SHOULD be reported
                "feature_property_type": ["FlSchn", "okBefu"],
                "feature_property_value": ["Yes", "Good"],
            }
        )

        entity_config = {
            "columns": ["Befu", "Projekt", "arbodat_code", "FlSchn", "okBefu", "BestJa"],
            "unnest": {
                "id_vars": ["Befu", "Projekt", "arbodat_code"],  # These MUST exist
                "value_vars": ["FlSchn", "okBefu", "BestJa"],  # These should NOT be validated
                "var_name": "feature_property_type",
                "value_name": "feature_property_value",
            },
        }

        issues = ColumnExistsValidator.validate(
            df,
            entity_config["columns"],
            "feature_property",
            entity_config,
        )

        # Should report ONLY missing id_vars (Projekt, arbodat_code)
        # Should NOT report missing value_vars (FlSchn, okBefu, BestJa are excluded)
        assert len(issues) == 2
        assert all(issue.code == "COLUMN_NOT_FOUND" for issue in issues)
        
        missing_column_names = {issue.message.split("'")[1] for issue in issues}
        assert missing_column_names == {"Projekt", "arbodat_code"}
        
        # Verify value_vars are NOT in the error messages
        all_messages = " ".join(issue.message for issue in issues)
        assert "FlSchn" not in all_messages
        assert "okBefu" not in all_messages
        assert "BestJa" not in all_messages


class TestNaturalKeyUniquenessValidator:
    """Tests for NaturalKeyUniquenessValidator."""

    def test_validates_unique_keys(self):
        """Test passes when keys are unique."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        issues = NaturalKeyUniquenessValidator.validate(df, ["a"], "test_entity")
        assert not issues

    def test_reports_duplicate_keys(self):
        """Test reports errors for duplicate keys."""
        df = pd.DataFrame(
            {
                "a": [1, 1, 2],
                "b": ["x", "x", "y"],
            }
        )
        issues = NaturalKeyUniquenessValidator.validate(df, ["a"], "test_entity")

        assert len(issues) == 1
        assert issues[0].code == "NON_UNIQUE_KEYS"
        assert issues[0].severity == "error"
        assert "not unique" in issues[0].message.lower()

    def test_composite_keys(self):
        """Test composite key uniqueness."""
        df = pd.DataFrame(
            {
                "a": [1, 1, 2, 2],
                "b": ["x", "y", "x", "x"],  # Composite (a,b) has duplicate (2, x)
            }
        )
        issues = NaturalKeyUniquenessValidator.validate(df, ["a", "b"], "test_entity")

        assert len(issues) == 1
        assert issues[0].code == "NON_UNIQUE_KEYS"

    def test_missing_key_columns_no_error(self):
        """Test missing key columns don't cause errors (ColumnExistsValidator handles this)."""
        df = pd.DataFrame({"a": [1, 2]})
        issues = NaturalKeyUniquenessValidator.validate(df, ["a", "missing"], "test_entity")
        assert not issues

    def test_single_row_no_error(self):
        """Test single row can't have duplicates."""
        df = pd.DataFrame({"a": [1]})
        issues = NaturalKeyUniquenessValidator.validate(df, ["a"], "test_entity")
        assert not issues


class TestNonEmptyResultValidator:
    """Tests for NonEmptyResultValidator."""

    def test_validates_non_empty_dataframe(self):
        """Test passes with data."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        issues = NonEmptyResultValidator.validate(df, "test_entity")
        assert not issues

    def test_reports_empty_dataframe(self):
        """Test reports warning for empty DataFrame."""
        df = pd.DataFrame()
        issues = NonEmptyResultValidator.validate(df, "test_entity")

        assert len(issues) == 1
        assert issues[0].code == "EMPTY_RESULT"
        assert issues[0].severity == "warning"
        assert "no data" in issues[0].message.lower()


class TestDuplicateKeysValidator:
    """Tests for DuplicateKeysValidator (alias for NaturalKeyUniquenessValidator)."""

    def test_is_alias_for_uniqueness_validator(self):
        """Test DuplicateKeysValidator is equivalent to NaturalKeyUniquenessValidator."""
        df = pd.DataFrame({"a": [1, 1, 2]})

        issues_dup = DuplicateKeysValidator.validate(df, ["a"], "test")
        issues_unique = NaturalKeyUniquenessValidator.validate(df, ["a"], "test")

        assert len(issues_dup) == len(issues_unique)
        if issues_dup:
            assert issues_dup[0].code == issues_unique[0].code


class TestForeignKeyDataValidator:
    """Tests for ForeignKeyDataValidator."""

    def test_validates_fk_columns_exist(self):
        """Test passes when FK columns exist."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        fk_config = {"local_keys": ["a", "b"], "remote_keys": ["x", "y"]}
        issues = ForeignKeyDataValidator.validate(df, fk_config, "test_entity")
        assert not issues

    def test_reports_missing_fk_columns(self):
        """Test reports errors for missing FK columns."""
        df = pd.DataFrame({"a": [1, 2]})
        fk_config = {"local_keys": ["a", "missing"], "remote_keys": ["x", "y"]}
        issues = ForeignKeyDataValidator.validate(df, fk_config, "test_entity")

        assert len(issues) == 1
        assert issues[0].code == "FK_LOCAL_COLUMN_MISSING"
        assert issues[0].severity == "error"
        assert "missing" in issues[0].message.lower()

    def test_no_local_keys_no_error(self):
        """Test no local_keys doesn't cause errors."""
        df = pd.DataFrame({"a": [1, 2]})
        fk_config = {"remote_keys": ["x"]}
        issues = ForeignKeyDataValidator.validate(df, fk_config, "test_entity")
        assert not issues


class TestForeignKeyIntegrityValidator:
    """Tests for ForeignKeyIntegrityValidator."""

    def test_validates_fk_integrity(self):
        """Test passes when all FK values exist in remote."""
        local_df = pd.DataFrame({"fk": [1, 2, 3]})
        remote_df = pd.DataFrame({"pk": [1, 2, 3, 4]})
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk_config, "local")
        assert not issues

    def test_reports_orphaned_fk_values(self):
        """Test reports warnings for orphaned FK values."""
        local_df = pd.DataFrame({"fk": [1, 2, 99]})
        remote_df = pd.DataFrame({"pk": [1, 2]})
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk_config, "local")

        assert len(issues) == 1
        assert issues[0].code == "FK_DATA_INTEGRITY"
        assert issues[0].severity == "warning"
        assert "not found" in issues[0].message.lower()

    def test_composite_foreign_keys(self):
        """Test composite FK validation."""
        local_df = pd.DataFrame({"fk1": [1, 2], "fk2": ["a", "z"]})  # (2, z) missing
        remote_df = pd.DataFrame({"pk1": [1, 2], "pk2": ["a", "b"]})
        fk_config = {
            "local_keys": ["fk1", "fk2"],
            "remote_keys": ["pk1", "pk2"],
            "entity": "remote",
        }

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk_config, "local")

        assert len(issues) == 1
        assert issues[0].code == "FK_DATA_INTEGRITY"

    def test_empty_remote_warning(self):
        """Test warning when remote entity is empty."""
        local_df = pd.DataFrame({"fk": [1, 2]})
        remote_df = pd.DataFrame({"pk": []})
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk_config, "local")

        assert len(issues) == 1
        assert issues[0].code == "FK_REMOTE_EMPTY"

    def test_null_values_ignored(self):
        """Test null FK values are ignored."""
        local_df = pd.DataFrame({"fk": [1, None, 2]})
        remote_df = pd.DataFrame({"pk": [1, 2]})
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk_config, "local")
        assert not issues


class TestDataTypeCompatibilityValidator:
    """Tests for DataTypeCompatibilityValidator."""

    def test_validates_compatible_types(self):
        """Test passes for compatible types."""
        local_df = pd.DataFrame({"fk": [1, 2, 3]})
        remote_df = pd.DataFrame({"pk": [1, 2, 3]})
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = DataTypeCompatibilityValidator.validate(local_df, remote_df, fk_config, "local")
        assert not issues

    def test_warns_on_type_mismatch(self):
        """Test warns when types don't match."""
        local_df = pd.DataFrame({"fk": [1, 2, 3]})  # int
        remote_df = pd.DataFrame({"pk": ["a", "b", "c"]})  # object
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = DataTypeCompatibilityValidator.validate(local_df, remote_df, fk_config, "local")

        assert len(issues) == 1
        assert issues[0].code == "FK_TYPE_MISMATCH"
        assert issues[0].severity == "warning"

    def test_numeric_types_compatible(self):
        """Test numeric types are considered compatible."""
        local_df = pd.DataFrame({"fk": [1, 2, 3]})  # int64
        remote_df = pd.DataFrame({"pk": [1.0, 2.0, 3.0]})  # float64
        fk_config = {"local_keys": ["fk"], "remote_keys": ["pk"], "entity": "remote"}

        issues = DataTypeCompatibilityValidator.validate(local_df, remote_df, fk_config, "local")
        assert not issues

    def test_missing_columns_no_error(self):
        """Test missing columns don't cause errors (other validators handle this)."""
        local_df = pd.DataFrame({"a": [1]})
        remote_df = pd.DataFrame({"b": [2]})
        fk_config = {"local_keys": ["missing"], "remote_keys": ["b"], "entity": "remote"}

        issues = DataTypeCompatibilityValidator.validate(local_df, remote_df, fk_config, "local")
        assert not issues


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_creates_issue_with_defaults(self):
        """Test creating ValidationIssue with default values."""
        issue = ValidationIssue(
            severity="error",
            entity="test",
            field="col",
            message="test message",
            code="TEST_CODE",
        )

        assert issue.severity == "error"
        assert issue.entity == "test"
        assert issue.field == "col"
        assert issue.message == "test message"
        assert issue.code == "TEST_CODE"
        assert issue.suggestion is None
        assert issue.category == "data"
        assert issue.priority == "medium"
        assert issue.auto_fixable is False

    def test_creates_issue_with_all_fields(self):
        """Test creating ValidationIssue with all fields specified."""
        issue = ValidationIssue(
            severity="warning",
            entity="entity1",
            field="field1",
            message="Custom message",
            code="CUSTOM_CODE",
            suggestion="Fix it like this",
            category="config",
            priority="high",
            auto_fixable=True,
        )

        assert issue.severity == "warning"
        assert issue.suggestion == "Fix it like this"
        assert issue.category == "config"
        assert issue.priority == "high"
        assert issue.auto_fixable is True
