"""Tests for entity-level specifications."""

import pytest

from src.specifications.entity import (
    AppendSpecification,
    DependsOnSpecification,
    DropDuplicatesSpecification,
    EntityFieldsBaseSpecification,
    EntityFieldsSpecification,
    EntityReferencesExistSpecification,
    EntitySpecification,
    FixedEntityFieldsSpecification,
    FixedEntitySystemIdSpecification,
    ForeignKeySpecification,
    PublicIdSpecification,
    SqlEntityFieldsSpecification,
    UnnestSpecification,
)


class TestEntityFieldsBaseSpecification:
    """Tests for EntityFieldsBaseSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_entity": {"type": "entity", "columns": ["id", "col1", "col2"], "keys": ["id"]},  # id added to columns
                "missing_columns": {"keys": ["id"]},
                "non_list_columns": {"columns": "not_a_list", "keys": ["id"]},
            }
        }

    def test_valid_entity(self, project_cfg):
        """Test validation passes for valid entity."""
        spec = EntityFieldsBaseSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_columns_field(self, project_cfg):
        """Test validation fails when columns field missing."""
        spec = EntityFieldsBaseSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_columns")

        assert result is False
        assert len(spec.errors) > 0

    def test_non_list_columns(self, project_cfg):
        """Test validation fails when columns is not a list."""
        spec = EntityFieldsBaseSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="non_list_columns")

        assert result is False
        assert len(spec.errors) > 0


class TestFixedEntityFieldsSpecification:
    """Tests for FixedEntityFieldsSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_fixed": {
                    "type": "fixed",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                    "public_id": "entity_id",
                    "values": [["id1", "val1"]],
                },
                "missing_surrogate": {"type": "fixed", "columns": ["id", "col1"], "keys": ["id"], "values": [["id1", "val1"]]},
                "no_columns": {"type": "fixed", "columns": None, "keys": ["id"], "public_id": "entity_id", "values": [["val1"]]},
                "not_fixed": {
                    "type": "sql",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                    "public_id": "entity_id",
                    "values": [["id1", "val1"]],
                },
                # "valid_fixed": {"type": "fixed", "columns": ["col1", "col2"], "values": [["a", "b"], ["c", "d"]]},
                "mismatched_length": {
                    "type": "fixed",
                    "columns": ["col1", "col2"],
                    "keys": [],
                    "public_id": "entity_id",
                    "values": [["a"], ["c", "d", "e"]],
                },
                "missing_values": {"type": "fixed", "columns": ["id", "col1"], "keys": ["id"], "public_id": "entity_id"},
                "sql_entity": {
                    "type": "sql",
                    "query": "SELECT * FROM table",
                    "public_id": "entity_id",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                },
                "empty_fixed": {"type": "fixed", "columns": [], "keys": [], "public_id": "entity_id", "values": []},
                "empty_columns_with_values": {
                    "type": "fixed",
                    "columns": [],
                    "keys": [],
                    "public_id": "entity_id",
                    "values": [[1, None]],
                },
            }
        }

    def test_valid_fixed_entity(self, project_cfg):
        """Test validation passes for valid fixed entity."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_fixed")

        assert result is True, spec.get_report()
        assert len(spec.errors) == 0

    def test_missing_surrogate_id(self, project_cfg):
        """Test validation fails when public_id missing."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_surrogate")

        assert result is False
        assert len(spec.errors) > 0

    def test_columns_not_list(self, project_cfg):
        """Test validation fails when columns is not a list."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="no_columns")

        assert result is False
        assert len(spec.errors) > 0

    def test_non_fixed_entity_fails(self, project_cfg):
        """Test validation fails for non-fixed entities."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="not_fixed")

        assert result is False

    def test_mismatched_column_row_length(self, project_cfg):
        """Test validation fails when row length doesn't match columns."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="mismatched_length")

        assert result is False, spec.get_report()
        assert len(spec.errors) > 0, spec.get_report()
        assert any("mismatched" in str(e) for e in spec.errors), spec.get_report()

    def test_missing_values(self, project_cfg):
        """Test validation fails when values field missing."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_values")

        assert result is False, spec.get_report()
        assert len(spec.errors) > 0, spec.get_report()

    def test_empty_values_with_no_columns_or_keys_or_values(self, project_cfg):
        """Test validation passes when both columns and values are empty."""
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="empty_fixed")

        assert result is True, spec.get_report()
        assert len(spec.errors) == 0, spec.get_report()

    def test_empty_columns_with_values_fails(self, project_cfg):
        """Test validation fails when columns is empty but values are provided.

        This prevents the error: "0 columns passed, passed data had 2 columns"
        that occurs when trying to create a DataFrame with data but no column names.

        Regression test for issue #266.
        """
        spec = FixedEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="empty_columns_with_values")

        assert result is False, spec.get_report()
        assert len(spec.errors) > 0, spec.get_report()
        assert any("no columns defined" in str(e).lower() for e in spec.errors), spec.get_report()


class TestSqlEntityFieldsSpecification:
    """Tests for SqlEntityFieldsSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_sql": {
                    "type": "sql",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                    "data_source": "db1",
                    "query": "SELECT * FROM table",
                },
                "missing_query": {"type": "sql", "columns": ["id", "col1"], "keys": ["id"], "data_source": "db1"},
            }
        }

    def test_valid_sql_entity(self, project_cfg):
        """Test validation passes for valid SQL entity."""
        spec = SqlEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_sql")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_query(self, project_cfg):
        """Test validation fails when query missing."""
        spec = SqlEntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_query")

        assert result is False
        assert len(spec.errors) > 0


class TestFixedEntitySystemIdSpecification:
    """Tests for FixedEntitySystemIdSpecification."""

    def test_valid_system_id_values(self):
        """Test validation passes for valid system_id values."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, 1, "Soil"],
                        [2, 2, "Wood"],
                        [3, 3, "Sediment"],
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is True
        assert len(spec.errors) == 0

    def test_non_sequential_system_id_is_valid(self):
        """Test that non-sequential system_id values are valid."""
        project_cfg = {
            "entities": {
                "location": {
                    "type": "fixed",
                    "columns": ["system_id", "location_id", "name"],
                    "public_id": "location_id",
                    "values": [
                        [1, 162, "Norway"],
                        [5, 205, "Sweden"],  # Gap in system_id is OK
                        [8, 207, "Finland"],
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="location")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_system_id_column_is_valid(self):
        """Test that missing system_id column doesn't cause errors (will be auto-generated)."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, "Soil"],
                        [2, "Wood"],
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is True
        assert len(spec.errors) == 0

    def test_null_system_id_values_fail(self):
        """Test that null system_id values cause validation error."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, 1, "Soil"],
                        [None, 2, "Wood"],  # Null system_id
                        [3, 3, "Sediment"],
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is False
        assert len(spec.errors) == 1
        assert "null" in spec.errors[0].message.lower()
        assert spec.errors[0].kwargs.get("code") == "SYSTEM_ID_NULL_VALUES"

    def test_duplicate_system_id_values_fail(self):
        """Test that duplicate system_id values cause validation error."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, 1, "Soil"],
                        [2, 2, "Wood"],
                        [1, 3, "Sediment"],  # Duplicate system_id=1
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is False
        assert len(spec.errors) == 1
        assert "duplicate" in spec.errors[0].message.lower()
        assert spec.errors[0].kwargs.get("code") == "SYSTEM_ID_DUPLICATE_VALUES"

    def test_invalid_system_id_type_fails(self):
        """Test that non-integer system_id values cause validation error."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, 1, "Soil"],
                        ["not_an_int", 2, "Wood"],  # Invalid type
                        [3, 3, "Sediment"],
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is False
        assert len(spec.errors) >= 1
        assert any("not a valid integer" in err.message.lower() for err in spec.errors)
        assert any(err.kwargs.get("code") == "SYSTEM_ID_INVALID_TYPE" for err in spec.errors)

    def test_negative_system_id_fails(self):
        """Test that negative or zero system_id values cause validation error."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [1, 1, "Soil"],
                        [0, 2, "Wood"],  # Zero is invalid
                        [-1, 3, "Sediment"],  # Negative is invalid
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is False
        assert len(spec.errors) >= 2
        assert any("positive integer" in err.message.lower() for err in spec.errors)
        assert any(err.kwargs.get("code") == "SYSTEM_ID_INVALID_VALUE" for err in spec.errors)

    def test_multiple_errors_reported(self):
        """Test that multiple system_id errors are reported."""
        project_cfg = {
            "entities": {
                "sample_type": {
                    "type": "fixed",
                    "columns": ["system_id", "sample_type_id", "type_name"],
                    "public_id": "sample_type_id",
                    "values": [
                        [None, 1, "Soil"],  # Null
                        [2, 2, "Wood"],
                        [2, 3, "Sediment"],  # Duplicate
                    ],
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sample_type")

        assert result is False
        assert len(spec.errors) == 2  # Null error + duplicate error

    def test_non_fixed_entity_skips_validation(self):
        """Test that non-fixed entities are not validated."""
        project_cfg = {
            "entities": {
                "sql_entity": {
                    "type": "sql",
                    "columns": ["system_id", "col1"],
                    "query": "SELECT *",
                    "data_source": "db1",
                }
            }
        }
        spec = FixedEntitySystemIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sql_entity")

        # Should pass - SQL entities are not validated by this spec
        assert result is True
        assert len(spec.errors) == 0


class TestEntityFieldsSpecification:
    """Tests for EntityFieldsSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "fixed_entity": {
                    "type": "fixed",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                    "public_id": "entity_id",
                    "values": [["id1", "val"]],
                },
                "sql_entity": {"type": "sql", "columns": ["id", "col1"], "keys": ["id"], "data_source": "db1", "query": "SELECT *"},
                "data_entity": {"type": "entity", "columns": ["id", "col1"], "keys": ["id"]},
            }
        }

    def test_fixed_entity(self, project_cfg):
        """Test validation uses FixedEntityFieldsSpecification for fixed type."""
        spec = EntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="fixed_entity")

        assert result is True

    def test_sql_entity(self, project_cfg):
        """Test validation uses SqlEntityFieldsSpecification for sql type."""
        spec = EntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="sql_entity")

        assert result is True

    def test_data_entity(self, project_cfg):
        """Test validation uses base specification for data type."""
        spec = EntityFieldsSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="data_entity")

        assert result is True


class TestUnnestSpecification:
    """Tests for UnnestSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_unnest": {
                    "unnest": {"value_vars": ["col1", "col2"], "var_name": "variable", "value_name": "value", "id_vars": ["id"]}
                },
                "missing_var_name": {"unnest": {"value_vars": ["col1"], "value_name": "value"}},
                "non_list_value_vars": {"unnest": {"value_vars": "not_a_list", "var_name": "var", "value_name": "val"}},
            }
        }

    def test_valid_unnest(self, project_cfg):
        """Test validation passes for valid unnest config."""
        spec = UnnestSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_unnest")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_required_field(self, project_cfg):
        """Test validation fails when required field missing."""
        spec = UnnestSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_var_name")

        assert result is False
        assert len(spec.errors) > 0

    def test_non_list_value_vars(self, project_cfg):
        """Test validation fails when value_vars not a list."""
        spec = UnnestSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="non_list_value_vars")

        assert result is False
        assert len(spec.errors) > 0


class TestDropDuplicatesSpecification:
    """Tests for DropDuplicatesSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "bool_drop": {"drop_duplicates": True},
                "string_drop": {"drop_duplicates": "include:all"},
                "list_drop": {"drop_duplicates": ["col1", "col2"]},
                "invalid_type": {"drop_duplicates": 123},
                "mixed_list": {"drop_duplicates": ["col1", 123]},
                "dict_drop": {"drop_duplicates": {"columns": ["col1", "col2"]}},
                "dict_drop_with_fd": {
                    "drop_duplicates": {
                        "columns": ["col1"],
                        "check_functional_dependency": True,
                        "strict_functional_dependency": False,
                    }
                },
                "dict_drop_bool_columns": {"drop_duplicates": {"columns": True}},
                "dict_drop_string_columns": {"drop_duplicates": {"columns": "col1"}},
                "dict_drop_missing_columns": {"drop_duplicates": {"check_functional_dependency": True}},
                "dict_drop_invalid_fd": {"drop_duplicates": {"columns": ["col1"], "check_functional_dependency": "yes"}},
                "dict_drop_invalid_strict_fd": {"drop_duplicates": {"columns": ["col1"], "strict_functional_dependency": "no"}},
            }
        }

    def test_bool_drop_duplicates(self, project_cfg):
        """Test validation passes for boolean drop_duplicates."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="bool_drop")

        assert result is True

    def test_string_drop_duplicates(self, project_cfg):
        """Test validation passes for string drop_duplicates."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="string_drop")

        assert result is True

    def test_list_drop_duplicates(self, project_cfg):
        """Test validation passes for list drop_duplicates."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="list_drop")

        assert result is True

    def test_invalid_type(self, project_cfg):
        """Test validation fails for invalid type."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_type")

        assert result is False

    def test_mixed_list(self, project_cfg):
        """Test validation fails for non-string list items."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="mixed_list")

        assert result is False

    def test_dict_drop_duplicates(self, project_cfg):
        """Test validation passes for dict drop_duplicates with columns."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop")

        assert result is True

    def test_dict_drop_duplicates_with_fd_settings(self, project_cfg):
        """Test validation passes for dict with functional dependency settings."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_with_fd")

        assert result is True

    def test_dict_drop_duplicates_bool_columns(self, project_cfg):
        """Test validation passes for dict with bool columns."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_bool_columns")

        assert result is True

    def test_dict_drop_duplicates_string_columns(self, project_cfg):
        """Test validation passes for dict with string columns."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_string_columns")

        assert result is True

    def test_dict_drop_duplicates_missing_columns(self, project_cfg):
        """Test validation fails when dict missing columns key."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_missing_columns")

        assert result is False
        assert len(spec.errors) > 0

    def test_dict_drop_duplicates_invalid_fd_check(self, project_cfg):
        """Test validation fails when check_functional_dependency is not bool."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_invalid_fd")

        assert result is False
        assert len(spec.errors) > 0

    def test_dict_drop_duplicates_invalid_strict_fd(self, project_cfg):
        """Test validation fails when strict_functional_dependency is not bool."""
        spec = DropDuplicatesSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="dict_drop_invalid_strict_fd")

        assert result is False
        assert len(spec.errors) > 0


class TestForeignKeySpecification:
    """Tests for ForeignKeySpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_fk": {"foreign_keys": [{"entity": "target", "local_keys": ["id"], "remote_keys": ["ref_id"]}]},
                "missing_entity": {"foreign_keys": [{"local_keys": ["id"], "remote_keys": ["ref_id"]}]},
                "mismatched_keys": {"foreign_keys": [{"entity": "target", "local_keys": ["id"], "remote_keys": ["ref1", "ref2"]}]},
                "invalid_extra": {"foreign_keys": [{"entity": "t", "local_keys": ["id"], "remote_keys": ["id"], "extra_columns": 123}]},
            }
        }

    def test_valid_foreign_key(self, project_cfg):
        """Test validation passes for valid foreign key."""
        spec = ForeignKeySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_fk")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_entity_field(self, project_cfg):
        """Test validation fails when entity field missing."""
        spec = ForeignKeySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="missing_entity")

        assert result is False
        assert len(spec.errors) > 0

    def test_mismatched_key_lengths(self, project_cfg):
        """Test validation fails when key lengths don't match."""
        spec = ForeignKeySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="mismatched_keys")

        assert result is False
        assert any("length" in str(e) for e in spec.errors)

    def test_invalid_extra_columns_type(self, project_cfg):
        """Test validation fails for invalid extra_columns type."""
        spec = ForeignKeySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_extra")

        assert result is False


class TestPublicIdSpecification:
    """Tests for PublicIdSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_id": {"public_id": "entity_id"},
                "no_id_suffix": {"public_id": "entity"},
                "non_string_id": {"public_id": 123},
                "no_public_id": {},
            }
        }

    def test_valid_public_id(self, project_cfg):
        """Test validation passes for valid public_id."""
        spec = PublicIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_id")

        assert result is True
        assert len(spec.warnings) == 0

    def test_no_id_suffix_error(self, project_cfg):
        """Test error when public_id doesn't end with _id."""
        spec = PublicIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="no_id_suffix")

        assert result is False
        assert len(spec.errors) > 0

    def test_non_string_public_id(self, project_cfg):
        """Test validation fails for non-string public_id."""
        spec = PublicIdSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="non_string_id")

        assert result is False


class TestAppendSpecification:
    """Tests for AppendSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_fixed_append": {"append": [{"type": "fixed", "values": [["a"], ["b"]]}], "append_mode": "all"},
                "valid_sql_append": {"append": [{"type": "sql", "query": "SELECT * FROM table"}]},
                "valid_source_append": {"append": [{"source": "other_entity"}]},
                "both_type_and_source": {"append": [{"type": "fixed", "source": "other", "values": []}]},
                "neither_type_nor_source": {"append": [{}]},
                "invalid_mode": {"append": [{"type": "fixed", "values": []}], "append_mode": "invalid"},
            }
        }

    def test_valid_fixed_append(self, project_cfg):
        """Test validation passes for valid fixed append."""
        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_fixed_append")

        assert result is True

    def test_valid_sql_append(self, project_cfg):
        """Test validation passes for valid SQL append."""
        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_sql_append")

        assert result is True

    def test_valid_source_append(self, project_cfg):
        """Test validation passes for valid source append."""
        # Need to add the referenced entity
        project_cfg["entities"]["other_entity"] = {"columns": ["col1"]}

        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_source_append")

        assert result is True

    def test_both_type_and_source(self, project_cfg):
        """Test validation fails when both type and source specified."""
        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="both_type_and_source")

        assert result is False
        assert any("cannot specify both" in str(e) for e in spec.errors)

    def test_neither_type_nor_source(self, project_cfg):
        """Test validation fails when neither type nor source specified."""
        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="neither_type_nor_source")

        assert result is False
        assert any("must specify either" in str(e) for e in spec.errors)

    def test_invalid_append_mode(self, project_cfg):
        """Test validation fails for invalid append_mode."""
        spec = AppendSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_mode")

        assert result is False


class TestDependsOnSpecification:
    """Tests for DependsOnSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "entity1": {"depends_on": ["entity2"]},
                "entity2": {},
                "invalid_dep": {"depends_on": ["nonexistent"]},
            }
        }

    def test_valid_dependency(self, project_cfg):
        """Test validation passes for valid dependency."""
        spec = DependsOnSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="entity1")

        assert result is True

    def test_nonexistent_dependency(self, project_cfg):
        """Test validation fails for nonexistent dependency."""
        spec = DependsOnSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_dep")

        assert result is False
        assert any("non-existent entity" in str(e) for e in spec.errors)


class TestEntityReferencesExistSpecification:
    """Tests for EntityReferencesExistSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "entity1": {
                    "source": "entity2",
                    "depends_on": ["entity2"],
                    "foreign_keys": [{"entity": "entity2", "local_keys": ["id"], "remote_keys": ["id"]}],
                },
                "entity2": {},
                "invalid_refs": {
                    "source": "missing",
                    "depends_on": ["missing2"],
                    "foreign_keys": [{"entity": "missing3", "local_keys": ["id"], "remote_keys": ["id"]}],
                },
            }
        }

    def test_valid_references(self, project_cfg):
        """Test validation passes when all references exist."""
        spec = EntityReferencesExistSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="entity1")

        assert result is True

    def test_missing_source_reference(self, project_cfg):
        """Test validation fails for missing source reference."""
        spec = EntityReferencesExistSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_refs")

        assert result is False
        assert any("source" in str(e).lower() for e in spec.errors)

    def test_missing_dependency_reference(self, project_cfg):
        """Test validation fails for missing dependency reference."""
        spec = EntityReferencesExistSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_refs")

        assert result is False
        assert any("depends on non-existent" in str(e) for e in spec.errors)

    def test_missing_foreign_key_reference(self, project_cfg):
        """Test validation fails for missing foreign key reference."""
        spec = EntityReferencesExistSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid_refs")

        assert result is False
        assert any("foreign key" in str(e).lower() for e in spec.errors)


class TestEntitySpecification:
    """Tests for EntitySpecification composite."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_entity": {
                    "type": "sql",
                    "columns": ["id", "col1"],
                    "keys": ["id"],
                    "data_source": "db1",
                    "query": "SELECT *",
                    "public_id": "entity_id",
                }
            }
        }

    def test_valid_entity_passes_all_specs(self, project_cfg):
        """Test that valid entity passes all specifications."""
        spec = EntitySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="valid_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_get_specifications_returns_list(self, project_cfg):
        """Test get_specifications returns proper list."""
        spec = EntitySpecification(project_cfg)

        specs = spec.get_specifications()

        assert isinstance(specs, list)
        assert len(specs) > 0
        assert all(hasattr(s, "is_satisfied_by") for s in specs)

    def test_aggregates_errors_from_subspecs(self, project_cfg):
        """Test that errors from sub-specifications are aggregated."""
        # Create invalid entity
        project_cfg["entities"]["invalid"] = {"type": "sql"}  # Missing required fields

        spec = EntitySpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="invalid")

        assert result is False
        assert len(spec.errors) > 0
