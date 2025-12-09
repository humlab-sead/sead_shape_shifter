"""Unit tests for configuration validation specifications."""

from src.arbodat.specifications import (
    CircularDependencySpecification,
    CompositeConfigSpecification,
    EntityExistsSpecification,
    FixedDataSpecification,
    ForeignKeySpecification,
    RequiredFieldsSpecification,
    SurrogateIdSpecification,
    UnnestSpecification,
)


class TestEntityExistsSpecification:
    """Test suite for EntityExistsSpecification."""

    def test_valid_config_with_all_entities_exist(self):
        """Test that valid configuration passes."""
        config = {
            "entities": {
                "parent": {"columns": ["id", "name"]},
                "child": {
                    "columns": ["id", "parent_id"],
                    "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"]}],
                    "depends_on": ["parent"],
                },
            }
        }
        spec = EntityExistsSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_missing_entities_section(self):
        """Test that missing entities section is caught."""
        config = {}
        spec = EntityExistsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "must contain 'entities' section" in spec.errors[0]

    def test_foreign_key_references_nonexistent_entity(self):
        """Test that foreign key referencing non-existent entity is caught."""
        config = {
            "entities": {
                "child": {
                    "columns": ["id", "parent_id"],
                    "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"]}],
                }
            }
        }
        spec = EntityExistsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "non-existent entity 'parent'" in spec.errors[0]

    def test_depends_on_references_nonexistent_entity(self):
        """Test that depends_on referencing non-existent entity is caught."""
        config = {"entities": {"child": {"columns": ["id"], "depends_on": ["parent"]}}}
        spec = EntityExistsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "depends on non-existent entity 'parent'" in spec.errors[0]

    def test_source_references_nonexistent_entity(self):
        """Test that source referencing non-existent entity is caught."""
        config = {"entities": {"child": {"columns": ["id"], "source": "parent"}}}
        spec = EntityExistsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "non-existent source entity 'parent'" in spec.errors[0]


class TestCircularDependencySpecification:
    """Test suite for CircularDependencySpecification."""

    def test_no_circular_dependencies(self):
        """Test that valid dependency chain passes."""
        config = {
            "entities": {
                "a": {"columns": ["id"]},
                "b": {"columns": ["id"], "depends_on": ["a"]},
                "c": {"columns": ["id"], "depends_on": ["b"]},
            }
        }
        spec = CircularDependencySpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_direct_circular_dependency(self):
        """Test that direct circular dependency is caught."""
        config = {
            "entities": {
                "a": {"columns": ["id"], "depends_on": ["b"]},
                "b": {"columns": ["id"], "depends_on": ["a"]},
            }
        }
        spec = CircularDependencySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "Circular dependency detected" in spec.errors[0]

    def test_indirect_circular_dependency(self):
        """Test that indirect circular dependency is caught."""
        config = {
            "entities": {
                "a": {"columns": ["id"], "depends_on": ["c"]},
                "b": {"columns": ["id"], "depends_on": ["a"]},
                "c": {"columns": ["id"], "depends_on": ["b"]},
            }
        }
        spec = CircularDependencySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "Circular dependency detected" in spec.errors[0]

    def test_circular_dependency_via_source(self):
        """Test that circular dependency through source is caught."""
        config = {
            "entities": {
                "a": {"columns": ["id"], "source": "b"},
                "b": {"columns": ["id"], "source": "a"},
            }
        }
        spec = CircularDependencySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()


class TestRequiredFieldsSpecification:
    """Test suite for RequiredFieldsSpecification."""

    def test_valid_data_table(self):
        """Test that valid data table passes."""
        config = {"entities": {"table": {"columns": ["id", "name"]}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_valid_data_table_with_keys_only(self):
        """Test that data table with only keys passes."""
        config = {"entities": {"table": {"keys": ["id"]}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_data_table_without_columns_or_keys(self):
        """Test that data table without columns or keys is caught."""
        config = {"entities": {"table": {}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "must have 'columns' or 'keys'" in spec.errors[0]

    def test_valid_fixed_data_table(self):
        """Test that valid fixed data table passes."""
        config = {
            "entities": {
                "fixed_table": {
                    "type": "fixed",
                    "surrogate_id": "id",
                    "columns": ["name"],
                    "values": [["value1"], ["value2"]],
                }
            }
        }
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_fixed_data_table_missing_surrogate_id(self):
        """Test that fixed data table without surrogate_id is caught."""
        config = {"entities": {"fixed_table": {"type": "fixed", "columns": ["name"], "values": [["value1"]]}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'surrogate_id'" in spec.errors[0]

    def test_fixed_data_table_missing_columns(self):
        """Test that fixed data table without columns is caught."""
        config = {"entities": {"fixed_table": {"type": "fixed", "surrogate_id": "id", "values": [["value1"]]}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'columns'" in spec.errors[0]

    def test_fixed_data_table_missing_values(self):
        """Test that fixed data table without values is caught."""
        config = {"entities": {"fixed_table": {"type": "fixed", "surrogate_id": "id", "columns": ["name"]}}}
        spec = RequiredFieldsSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'values'" in spec.errors[0]


class TestForeignKeySpecification:
    """Test suite for ForeignKeySpecification."""

    def test_valid_foreign_key(self):
        """Test that valid foreign key configuration passes."""
        config = {
            "entities": {
                "table": {
                    "columns": ["id"],
                    "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"]}],
                }
            }
        }
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_foreign_key_missing_entity(self):
        """Test that foreign key without entity is caught."""
        config = {"entities": {"table": {"columns": ["id"], "foreign_keys": [{"local_keys": ["parent_id"], "remote_keys": ["id"]}]}}}
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required field 'entity'" in spec.errors[0]

    def test_foreign_key_missing_local_keys(self):
        """Test that foreign key without local_keys is caught."""
        config = {"entities": {"table": {"columns": ["id"], "foreign_keys": [{"entity": "parent", "remote_keys": ["id"]}]}}}
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required field 'local_keys'" in spec.errors[0]

    def test_foreign_key_missing_remote_keys(self):
        """Test that foreign key without remote_keys is caught."""
        config = {"entities": {"table": {"columns": ["id"], "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"]}]}}}
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required field 'remote_keys'" in spec.errors[0]

    def test_foreign_key_mismatched_lengths(self):
        """Test that foreign key with mismatched key lengths is caught."""
        config = {
            "entities": {
                "table": {
                    "columns": ["id"],
                    "foreign_keys": [{"entity": "parent", "local_keys": ["a", "b"], "remote_keys": ["id"]}],
                }
            }
        }
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "does not match" in spec.errors[0]

    def test_foreign_key_invalid_extra_columns(self):
        """Test that foreign key with invalid extra_columns is caught."""
        config = {
            "entities": {
                "table": {
                    "columns": ["id"],
                    "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"], "extra_columns": 123}],
                }
            }
        }
        spec = ForeignKeySpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "must be string, list, or dict" in spec.errors[0]


class TestUnnestSpecification:
    """Test suite for UnnestSpecification."""

    def test_valid_unnest_config(self):
        """Test that valid unnest configuration passes."""
        config = {
            "entities": {
                "table": {
                    "columns": ["id", "col1", "col2"],
                    "unnest": {"id_vars": ["id"], "value_vars": ["col1", "col2"], "var_name": "var", "value_name": "val"},
                }
            }
        }
        spec = UnnestSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_unnest_missing_value_vars(self):
        """Test that unnest without value_vars is caught."""
        config = {"entities": {"table": {"columns": ["id"], "unnest": {"id_vars": ["id"], "var_name": "var", "value_name": "val"}}}}
        spec = UnnestSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'value_vars'" in spec.errors[0]

    def test_unnest_missing_var_name(self):
        """Test that unnest without var_name is caught."""
        config = {"entities": {"table": {"columns": ["id"], "unnest": {"id_vars": ["id"], "value_vars": ["col1"], "value_name": "val"}}}}
        spec = UnnestSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'var_name'" in spec.errors[0]

    def test_unnest_missing_value_name(self):
        """Test that unnest without value_name is caught."""
        config = {"entities": {"table": {"columns": ["id"], "unnest": {"id_vars": ["id"], "value_vars": ["col1"], "var_name": "var"}}}}
        spec = UnnestSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "missing required 'value_name'" in spec.errors[0]

    def test_unnest_missing_id_vars_warning(self):
        """Test that unnest without id_vars generates warning."""
        config = {"entities": {"table": {"columns": ["id"], "unnest": {"value_vars": ["col1"], "var_name": "var", "value_name": "val"}}}}
        spec = UnnestSpecification()
        assert spec.is_satisfied_by(config) is True
        assert spec.has_warnings()
        assert "missing 'id_vars'" in spec.warnings[0]


class TestSurrogateIdSpecification:
    """Test suite for SurrogateIdSpecification."""

    def test_valid_surrogate_ids(self):
        """Test that valid surrogate IDs pass."""
        config = {
            "entities": {
                "table1": {"columns": ["name"], "surrogate_id": "table1_id"},
                "table2": {"columns": ["name"], "surrogate_id": "table2_id"},
            }
        }
        spec = SurrogateIdSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_surrogate_id_without_suffix_warning(self):
        """Test that surrogate ID without _id suffix generates warning."""
        config = {"entities": {"table": {"columns": ["name"], "surrogate_id": "pk"}}}
        spec = SurrogateIdSpecification()
        assert spec.is_satisfied_by(config) is True
        assert spec.has_warnings()
        assert "does not follow convention" in spec.warnings[0]

    def test_duplicate_surrogate_ids(self):
        """Test that duplicate surrogate IDs are caught."""
        config = {
            "entities": {
                "table1": {"columns": ["name"], "surrogate_id": "id"},
                "table2": {"columns": ["name"], "surrogate_id": "id"},
            }
        }
        spec = SurrogateIdSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "used by multiple entities" in spec.errors[0]


class TestFixedDataSpecification:
    """Test suite for FixedDataSpecification."""

    def test_valid_fixed_data_with_list(self):
        """Test that valid fixed data with list passes."""
        config = {
            "entities": {
                "table": {
                    "type": "fixed",
                    "surrogate_id": "id",
                    "columns": ["name", "code"],
                    "values": [["value1", "A"], ["value2", "B"]],
                }
            }
        }
        spec = FixedDataSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_valid_fixed_data_with_sql(self):
        """Test that valid fixed data with SQL passes."""
        config = {
            "entities": {"table": {"type": "fixed", "surrogate_id": "id", "columns": ["name"], "values": "sql: SELECT name FROM table"}}
        }
        spec = FixedDataSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()

    def test_fixed_data_with_empty_sql(self):
        """Test that fixed data with empty SQL is caught."""
        config = {"entities": {"table": {"type": "fixed", "surrogate_id": "id", "columns": ["name"], "values": "sql:   "}}}
        spec = FixedDataSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "empty SQL query" in spec.errors[0]

    def test_fixed_data_value_row_mismatch(self):
        """Test that fixed data with mismatched row length is caught."""
        config = {
            "entities": {
                "table": {
                    "type": "fixed",
                    "surrogate_id": "id",
                    "columns": ["name", "code"],
                    "values": [["value1"], ["value2", "B"]],  # First row has wrong length
                }
            }
        }
        spec = FixedDataSpecification()
        assert spec.is_satisfied_by(config) is False
        assert spec.has_errors()
        assert "has 1 items but 2 columns" in spec.errors[0]

    def test_fixed_data_with_source_warning(self):
        """Test that fixed data with source field generates warning."""
        config = {
            "entities": {
                "table": {
                    "type": "fixed",
                    "surrogate_id": "id",
                    "columns": ["name"],
                    "values": [["value1"]],
                    "source": "survey",
                }
            }
        }
        spec = FixedDataSpecification()
        assert spec.is_satisfied_by(config) is True
        assert spec.has_warnings()
        assert "has 'source' field" in spec.warnings[0]


class TestCompositeConfigSpecification:
    """Test suite for CompositeConfigSpecification."""

    def test_valid_complete_config(self):
        """Test that valid complete configuration passes all specs."""
        config = {
            "entities": {
                "parent": {"columns": ["id", "name"], "surrogate_id": "parent_id"},
                "child": {
                    "columns": ["id", "name"],
                    "surrogate_id": "child_id",
                    "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"]}],
                    "depends_on": ["parent"],
                },
            }
        }
        spec = CompositeConfigSpecification()
        assert spec.is_satisfied_by(config) is True
        assert not spec.has_errors()
        assert not spec.has_warnings()

    def test_config_with_multiple_errors(self):
        """Test that configuration with multiple issues is caught."""
        config = {
            "entities": {
                "table": {
                    "foreign_keys": [{"entity": "nonexistent", "local_keys": ["a", "b"], "remote_keys": ["c"]}],  # Multiple errors
                    "depends_on": ["nonexistent2"],
                }
            }
        }
        spec = CompositeConfigSpecification()
        assert spec.is_satisfied_by(config) is False
        assert len(spec.errors) > 1

    def test_get_report_valid_config(self):
        """Test report generation for valid config."""
        config = {"entities": {"table": {"columns": ["id"]}}}
        spec = CompositeConfigSpecification()
        spec.is_satisfied_by(config)
        report = spec.get_report()
        assert "✓ Configuration is valid" in report

    def test_get_report_with_errors(self):
        """Test report generation with errors."""
        config = {"entities": {"table": {}}}  # Missing columns/keys
        spec = CompositeConfigSpecification()
        spec.is_satisfied_by(config)
        report = spec.get_report()
        assert "✗ Configuration has" in report
        assert "error(s):" in report

    def test_get_report_with_warnings(self):
        """Test report generation with warnings."""
        config = {"entities": {"table": {"columns": ["id"], "surrogate_id": "pk"}}}  # Warning: no _id suffix
        spec = CompositeConfigSpecification()
        spec.is_satisfied_by(config)
        report = spec.get_report()
        assert "⚠ Configuration has" in report
        assert "warning(s):" in report
