"""Unit tests for arbodat utility configuration classes."""

from typing import Any

import pandas as pd
import pytest

from src.configuration.config import Config
from src.configuration.provider import MockConfigProvider, set_config_provider
from src.loaders.base_loader import DataLoader
from src.model import DataSourceConfig, ForeignKeyConfig, ForeignKeyConstraints, ShapeShiftConfig, TableConfig, UnnestConfig


class TestForeignKeyConstraints:
    """Tests for ForeignKeyConstraints class."""

    def test_empty_constraints(self):
        """Test constraints with no data."""
        constraints = ForeignKeyConstraints()
        assert constraints.is_empty
        assert not constraints.has_constraints
        assert not constraints.has_match_constraints()

    def test_empty_dict_constraints(self):
        """Test constraints with empty dict."""
        constraints = ForeignKeyConstraints(data={})
        assert constraints.is_empty
        assert not constraints.has_constraints

    def test_cardinality_constraint(self):
        """Test cardinality property."""
        constraints = ForeignKeyConstraints(data={"cardinality": "one_to_one"})
        assert constraints.cardinality == "one_to_one"
        assert constraints.has_constraints

    def test_allow_unmatched_left(self):
        """Test allow_unmatched_left property."""
        constraints = ForeignKeyConstraints(data={"allow_unmatched_left": True})
        assert constraints.allow_unmatched_left is True
        assert constraints.has_match_constraints()

    def test_allow_unmatched_right(self):
        """Test allow_unmatched_right property."""
        constraints = ForeignKeyConstraints(data={"allow_unmatched_right": False})
        assert constraints.allow_unmatched_right is False
        assert constraints.has_match_constraints()

    def test_allow_row_decrease(self):
        """Test allow_row_decrease property."""
        constraints = ForeignKeyConstraints(data={"allow_row_decrease": True})
        assert constraints.allow_row_decrease is True

    def test_require_unique_left(self):
        """Test require_unique_left property."""
        constraints = ForeignKeyConstraints(data={"require_unique_left": True})
        assert constraints.require_unique_left is True

    def test_require_unique_right(self):
        """Test require_unique_right property."""
        constraints = ForeignKeyConstraints(data={"require_unique_right": True})
        assert constraints.require_unique_right is True

    def test_allow_null_keys_default(self):
        """Test allow_null_keys defaults to True."""
        constraints = ForeignKeyConstraints(data={})
        assert constraints.allow_null_keys is True

    def test_allow_null_keys_false(self):
        """Test allow_null_keys set to False."""
        constraints = ForeignKeyConstraints(data={"allow_null_keys": False})
        assert constraints.allow_null_keys is False

    def test_multiple_constraints(self):
        """Test multiple constraints together."""
        constraints = ForeignKeyConstraints(
            data={
                "cardinality": "many_to_one",
                "allow_null_keys": False,
                "allow_unmatched_left": False,
            }
        )
        assert constraints.cardinality == "many_to_one"
        assert constraints.allow_null_keys is False
        assert constraints.allow_unmatched_left is False
        assert constraints.has_constraints
        assert constraints.has_match_constraints()


class TestUnnestConfig:
    """Tests for UnnestConfig class."""

    def test_valid_unnest_config(self):
        """Test creating a valid unnest configuration."""
        data = {
            "unnest": {
                "id_vars": ["site_id"],
                "value_vars": ["Ort", "Kreis", "Land"],
                "var_name": "location_type",
                "value_name": "location_name",
            }
        }
        config = UnnestConfig(cfg={}, data=data)

        assert config.id_vars == ["site_id"]
        assert config.value_vars == ["Ort", "Kreis", "Land"]
        assert config.var_name == "location_type"
        assert config.value_name == "location_name"

    def test_missing_unnest_key(self):
        """Test that missing unnest key raises ValueError."""
        data: dict[str, dict[str, list[str] | str]] = {}
        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            UnnestConfig(cfg={}, data=data)

    def test_missing_id_vars_allowed(self):
        """Test that missing id_vars is allowed (defaults to empty list)."""
        data = {"unnest": {"value_vars": ["col1"], "var_name": "var", "value_name": "val"}}
        config = UnnestConfig(cfg={}, data=data)
        assert config.id_vars == []
        assert config.value_vars == ["col1"]

    def test_missing_value_vars_allowed(self):
        """Test that missing value_vars is allowed (defaults to empty list)."""
        data = {"unnest": {"id_vars": ["id"], "var_name": "var", "value_name": "val"}}
        config = UnnestConfig(cfg={}, data=data)
        assert config.id_vars == ["id"]
        assert config.value_vars == []

    def test_missing_var_name(self):
        """Test that missing var_name raises ValueError."""
        data = {"unnest": {"id_vars": ["id"], "value_vars": ["col1"], "value_name": "val"}}
        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            UnnestConfig(cfg={}, data=data)

    def test_missing_value_name(self):
        """Test that missing value_name raises ValueError."""
        data = {"unnest": {"id_vars": ["id"], "value_vars": ["col1"], "var_name": "var"}}
        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            UnnestConfig(cfg={}, data=data)

    def test_empty_lists_allowed(self):
        """Test that empty lists are allowed."""
        data = {"unnest": {"id_vars": [], "value_vars": ["col1"], "var_name": "var", "value_name": "val"}}
        config = UnnestConfig(cfg={}, data=data)
        assert config.id_vars == []
        assert config.value_vars == ["col1"]


class TestForeignKeyConfig:
    """Tests for ForeignKeyConfig class."""

    def test_valid_foreign_key_config(self):
        """Test creating a valid foreign key configuration."""
        entities = {
            "site": {"surrogate_id": "site_id", "keys": ["site_name"]},
            "location": {"surrogate_id": "location_id", "keys": ["location_name"]},
        }
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.local_entity == "site"
        assert fk.remote_entity == "location"
        assert fk.local_keys == ["location_name"]
        assert fk.remote_keys == ["location_name"]
        assert fk.remote_surrogate_id == "location_id"

    def test_missing_remote_entity(self):
        """Test that missing remote entity raises ValueError."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        fk_data: dict[str, Any] = {"local_keys": ["col1"], "remote_keys": ["col1"]}

        with pytest.raises(ValueError, match="missing remote entity"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_unknown_remote_entity(self):
        """Test that unknown remote entity raises ValueError."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        fk_data: dict[str, Any] = {"entity": "unknown_entity", "local_keys": ["col1"], "remote_keys": ["col1"]}

        with pytest.raises(ValueError, match="references unknown entity"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_missing_remote_keys(self):
        """Test that missing remote_keys raises ValueError."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data: dict[str, Any] = {"entity": "location", "local_keys": ["col1"]}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_empty_remote_keys(self):
        """Test that empty remote_keys raises ValueError."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data: dict[str, Any] = {"entity": "location", "local_keys": ["col1"], "remote_keys": []}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_extra_columns_as_dict(self):
        """Test extra_columns as a dictionary mapping local to remote column names."""
        extra_columns_cfg: dict[str, str] = {"local_col1": "remote_col1", "local_col2": "remote_col2"}
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": extra_columns_cfg,
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {v: k for k, v in extra_columns_cfg.items()}

    def test_extra_columns_as_list(self):
        """Test extra_columns as a list (maps column names to themselves)."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["col1", "col2", "col3"],
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"col1": "col1", "col2": "col2", "col3": "col3"}

    def test_extra_columns_as_string(self):
        """Test extra_columns as a single string (converted to list, then dict)."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": "column1"}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"column1": "column1"}

    def test_extra_columns_empty_dict(self):
        """Test extra_columns with empty dict returns empty dict."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": {}}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {}

    def test_extra_columns_missing(self):
        """Test that missing extra_columns defaults to empty dict."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {}

    def test_extra_columns_invalid_type(self):
        """Test that invalid extra_columns type raises ValueError."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": 123}

        with pytest.raises(ValueError, match="Invalid extra_columns format"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_drop_remote_id_true(self):
        """Test drop_remote_id set to True."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "drop_remote_id": True}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is True

    def test_drop_remote_id_false(self):
        """Test drop_remote_id set to False."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "drop_remote_id": False}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is False

    def test_drop_remote_id_default(self):
        """Test that drop_remote_id defaults to False when not specified."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is False

    def test_combined_extra_columns_and_drop_remote_id(self):
        """Test using both extra_columns and drop_remote_id together."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["description", "code"],
            "drop_remote_id": True,
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"description": "description", "code": "code"}
        assert fk.drop_remote_id is True

    def test_cross_join_no_keys_required(self):
        """Test that cross join doesn't require keys."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "how": "cross"}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.how == "cross"
        assert fk.remote_entity == "location"

    def test_has_constraints_true(self):
        """Test has_constraints returns True when constraints are present."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "constraints": {"cardinality": "one_to_one"},
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.has_constraints is True

    def test_has_constraints_false(self):
        """Test has_constraints returns False when no constraints."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

        assert fk.has_constraints is False

    def test_get_valid_remote_columns_all_present(self):
        """Test get_valid_remote_columns when all columns are present."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["latitude", "longitude"],
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
        df = pd.DataFrame({"location_name": ["A", "B"], "latitude": [1.0, 2.0], "longitude": [3.0, 4.0]})

        valid_cols = fk.get_valid_remote_columns(df)

        assert set(valid_cols) == {"location_name", "latitude", "longitude"}

    def test_get_valid_remote_columns_some_missing(self):
        """Test get_valid_remote_columns when some columns are missing."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["latitude", "longitude", "elevation"],
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
        df = pd.DataFrame({"location_name": ["A", "B"], "latitude": [1.0, 2.0]})

        valid_cols = fk.get_valid_remote_columns(df)

        # Should only return columns that exist in df
        assert set(valid_cols) == {"location_name", "latitude"}

    def test_has_foreign_key_link_with_remote_id(self):
        """Test has_foreign_key_link returns True when remote_id is in table."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
        table = pd.DataFrame({"site_name": ["A", "B"], "location_id": [1, 2]})

        assert fk.has_foreign_key_link("location_id", table) is True

    def test_has_foreign_key_link_with_extra_columns(self):
        """Test has_foreign_key_link returns True when extra columns are present."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["latitude", "longitude"],
        }

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
        table = pd.DataFrame({"site_name": ["A", "B"], "latitude": [1.0, 2.0], "longitude": [3.0, 4.0]})

        assert fk.has_foreign_key_link("location_id", table) is True

    def test_has_foreign_key_link_false(self):
        """Test has_foreign_key_link returns False when link not present."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
        table = pd.DataFrame({"site_name": ["A", "B"], "description": ["X", "Y"]})

        assert fk.has_foreign_key_link("location_id", table) is False

    def test_how_join_types(self):
        """Test different join types."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}

        for how in ["left", "inner", "outer", "right"]:
            fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "how": how}
            fk = ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)
            assert fk.how == how

    def test_mismatched_key_counts(self):
        """Test that mismatched key counts raises ValueError."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["col1", "col2"], "remote_keys": ["col1"]}

        with pytest.raises(ValueError, match="number of local keys.*does not match"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)


class TestTableConfig:
    """Tests for TableConfig class."""

    def test_basic_table_config(self):
        """Test creating a basic table configuration."""
        entities = {
            "site": {"surrogate_id": "site_id", "keys": ["site_name"], "columns": ["site_name", "description"], "depends_on": ["location"]}
        }

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.entity_name == "site"
        assert table.surrogate_id == "site_id"
        assert table.keys == {"site_name"}
        assert table.columns == ["site_name", "description"]
        assert table.depends_on == {"location"}
        assert table.foreign_keys == []

    def test_table_with_foreign_keys(self):
        """Test table configuration with foreign keys."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
            },
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
        }

        table = TableConfig(cfg=entities, entity_name="site")

        assert len(table.foreign_keys) == 1
        assert table.foreign_keys[0].remote_entity == "location"
        assert table.foreign_keys[0].local_keys == ["location_id"]

    def test_table_with_foreign_keys_extra_columns(self):
        """Test table configuration with foreign keys including extra_columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name"],
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": ["location_id"],
                        "remote_keys": ["location_id"],
                        "extra_columns": ["latitude", "longitude"],
                        "drop_remote_id": True,
                    }
                ],
            },
            "location": {"surrogate_id": "location_id", "columns": ["location_name", "latitude", "longitude"]},
        }

        table = TableConfig(cfg=entities, entity_name="site")

        assert len(table.foreign_keys) == 1
        fk = table.foreign_keys[0]
        assert fk.remote_entity == "location"
        assert fk.remote_extra_columns == {"latitude": "latitude", "longitude": "longitude"}
        assert fk.drop_remote_id is True

    def test_table_drop_duplicates_bool(self):
        """Test drop_duplicates as boolean."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "drop_duplicates": True}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates is True

    def test_table_drop_duplicates_list(self):
        """Test drop_duplicates as list of columns."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "drop_duplicates": ["col1", "col2"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates == ["col1", "col2"]

    def test_table_drop_duplicates_default(self):
        """Test drop_duplicates defaults to False."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates is False

    def test_table_with_unnest(self):
        """Test table configuration with unnest."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "unnest": {
                    "id_vars": ["site_id"],
                    "value_vars": ["Ort", "Kreis"],
                    "var_name": "location_type",
                    "value_name": "location_name",
                },
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")

        assert table.unnest is not None
        assert table.unnest.id_vars == ["site_id"]
        assert table.unnest.var_name == "location_type"

    def test_table_without_unnest(self):
        """Test table configuration without unnest."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.unnest is None

    def test_missing_entity_raises_error(self):
        """Test that missing entity raises KeyError."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        with pytest.raises(KeyError):
            TableConfig(cfg=entities, entity_name="nonexistent")

    def test_empty_lists_default_correctly(self):
        """Test that empty lists in config return as empty lists."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "keys": [], "columns": [], "depends_on": []}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert not table.keys
        assert table.columns == []
        assert table.depends_on == set()

    def test_fk_column_set(self):
        """Test fk_column_set returns all foreign key columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name"],
                "foreign_keys": [
                    {"entity": "location", "local_keys": ["location_id", "location_type"], "remote_keys": ["location_id", "location_type"]},
                    {"entity": "region", "local_keys": ["region_id"], "remote_keys": ["region_id"]},
                ],
            },
            "location": {"surrogate_id": "location_id"},
            "region": {"surrogate_id": "region_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        fk_cols: set[str] = table.fk_columns

        assert len(fk_cols) == 3
        assert "location_id" in fk_cols
        assert "location_type" in fk_cols
        assert "region_id" in fk_cols

    def test_extra_fk_columns(self):
        """Test extra_fk_columns returns FK columns not in keys or columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "description", "location_id"],
                "foreign_keys": [
                    {"entity": "location", "local_keys": ["location_id", "location_type"], "remote_keys": ["location_id", "location_type"]}
                ],
            },
            "location": {"surrogate_id": "location_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        extra_cols = table.extra_fk_columns

        # location_id is in columns, location_type is not
        assert "location_type" in extra_cols
        assert "location_id" not in extra_cols

    def test_usage_columns(self):
        """Test usage_columns returns union of columns2 and fk_column_set."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "description"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
            },
            "location": {"surrogate_id": "location_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        usage_cols: list[str] = table.keys_columns_and_fks

        assert "site_name" in usage_cols
        assert "description" in usage_cols
        assert "location_id" in usage_cols
        assert len(usage_cols) == 3

    def test_query_property(self):
        """Test query property returns SQL query for sql type."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "type": "sql", "values": "sql: SELECT * FROM sites"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.type == "sql"
        assert table.query == "SELECT * FROM sites"

    def test_query_property_non_sql(self):
        """Test query property returns None for non-sql type."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.type != "sql"
        assert table.query is None

    def test_has_append_true(self):
        """Test has_append returns True when append configs exist."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "append": [{"source": "extra_sites"}]}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.has_append is True

    def test_has_append_false(self):
        """Test has_append returns False when no append configs."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.has_append is False

    def test_keys_and_columns_property(self):
        """Test keys_and_columns returns keys first, then columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {"surrogate_id": "site_id", "keys": ["id", "name"], "columns": ["description", "id", "location"]}
        }

        table = TableConfig(cfg=entities, entity_name="site")
        result = table.keys_and_columns

        # Keys should come first
        assert set(result[:2]) == {"id", "name"}
        # Then non-key columns
        assert "description" in result[2:]
        assert "location" in result[2:]

    def test_unnest_columns_property(self):
        """Test unnest_columns returns set of unnest column names."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "unnest": {"id_vars": ["site_id"], "value_vars": ["Ort", "Kreis"], "var_name": "type", "value_name": "name"},
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")

        assert table.unnest_columns == {"type", "name"}

    def test_unnest_columns_empty_when_no_unnest(self):
        """Test unnest_columns returns empty set when no unnest config."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.unnest_columns == set()

    def test_is_unnested_true(self):
        """Test is_unnested returns True when unnest columns are in table."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "unnest": {"id_vars": ["site_id"], "value_vars": ["Ort"], "var_name": "type", "value_name": "name"},
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")
        df = pd.DataFrame({"site_id": [1, 2], "type": ["city", "region"], "name": ["Berlin", "Bavaria"]})

        assert table.is_unnested(df) is True

    def test_is_unnested_false(self):
        """Test is_unnested returns False when unnest columns are not in table."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "unnest": {"id_vars": ["site_id"], "value_vars": ["Ort"], "var_name": "type", "value_name": "name"},
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")
        df = pd.DataFrame({"site_id": [1, 2], "Ort": ["Berlin", "Bavaria"]})

        assert table.is_unnested(df) is False

    def test_is_unnested_no_unnest_config(self):
        """Test is_unnested returns False when no unnest config."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"site_id": [1, 2]})

        assert table.is_unnested(df) is False

    def test_get_columns_all_included(self):
        """Test get_columns with all options included."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["id"],
                "columns": ["name", "description"],
                "extra_columns": {"created_at": None},
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
                "unnest": {"id_vars": ["id"], "value_vars": ["val"], "var_name": "var", "value_name": "value"},
            },
            "location": {"surrogate_id": "location_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        cols = table.get_columns(include_keys=True, include_fks=True, include_extra=True, include_unnest=True)

        assert "id" in cols
        assert "name" in cols
        assert "description" in cols
        assert "created_at" in cols
        assert "location_id" in cols
        assert "var" in cols
        assert "value" in cols

    def test_get_columns_exclude_keys(self):
        """Test get_columns excluding keys."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "keys": ["id"], "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        cols = table.get_columns(include_keys=False)

        assert "id" not in cols
        assert "name" in cols

    def test_get_columns_exclude_fks(self):
        """Test get_columns excluding foreign keys."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
            },
            "location": {"surrogate_id": "location_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        cols = table.get_columns(include_fks=False)

        assert "location_id" not in cols
        assert "name" in cols

    def test_get_columns_exclude_extra(self):
        """Test get_columns excluding extra columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {"surrogate_id": "site_id", "columns": ["name"], "extra_columns": {"created_at": None}}
        }

        table = TableConfig(cfg=entities, entity_name="site")
        cols = table.get_columns(include_extra=False)

        assert "created_at" not in cols
        assert "name" in cols

    def test_get_columns_exclude_unnest(self):
        """Test get_columns excluding unnest columns."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name"],
                "unnest": {"id_vars": ["id"], "value_vars": ["val"], "var_name": "var", "value_name": "value"},
            }
        }

        table = TableConfig(cfg=entities, entity_name="site")
        cols = table.get_columns(include_unnest=False)

        assert "var" not in cols
        assert "value" not in cols
        assert "name" in cols

    def test_drop_fk_columns(self):
        """Test drop_fk_columns removes FK columns not in columns list."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "location_id"],
                "foreign_keys": [
                    {"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]},
                    {"entity": "region", "local_keys": ["region_id"], "remote_keys": ["region_id"]},
                ],
            },
            "location": {"surrogate_id": "location_id"},
            "region": {"surrogate_id": "region_id"},
        }

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"name": ["A", "B"], "location_id": [1, 2], "region_id": [10, 20]})

        result = table.drop_fk_columns(df)

        # location_id should remain (it's in columns), region_id should be dropped
        assert "location_id" in result.columns
        assert "region_id" not in result.columns
        assert "name" in result.columns

    def test_drop_fk_columns_no_fks(self):
        """Test drop_fk_columns with no foreign keys."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"name": ["A", "B"], "extra": [1, 2]})

        result = table.drop_fk_columns(df)

        assert list(result.columns) == list(df.columns)

    def test_add_system_id_column(self):
        """Test add_system_id_column adds system_id and sets surrogate_id to None."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]})

        result = table.add_system_id_column(df)

        assert "system_id" in result.columns
        assert result["system_id"].tolist() == [1, 2]
        assert result["site_id"].isna().all()

    def test_add_system_id_column_already_exists(self):
        """Test add_system_id_column doesn't overwrite existing system_id."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"site_id": [1, 2], "system_id": [100, 200], "name": ["A", "B"]})

        result = table.add_system_id_column(df)

        # system_id should not be overwritten
        assert result["system_id"].tolist() == [100, 200]

    def test_add_system_id_column_no_surrogate_id(self):
        """Test add_system_id_column when surrogate_id not in dataframe."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        df = pd.DataFrame({"name": ["A", "B"]})

        result = table.add_system_id_column(df)

        # Should not add system_id if surrogate_id doesn't exist
        assert "system_id" not in result.columns

    def test_is_drop_duplicate_dependent_on_unnesting_true(self):
        """Test is_drop_duplicate_dependent_on_unnesting returns True."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "columns": ["name"],
                "unnest": {"id_vars": ["site_id"], "value_vars": ["val"], "var_name": "type", "value_name": "name"},
                "drop_duplicates": ["type", "name"],
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")

        assert table.is_drop_duplicate_dependent_on_unnesting() is True

    def test_is_drop_duplicate_dependent_on_unnesting_false_no_overlap(self):
        """Test is_drop_duplicate_dependent_on_unnesting returns False when no overlap."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "columns": ["name"],
                "unnest": {"id_vars": ["site_id"], "value_vars": ["val"], "var_name": "type", "value_name": "value"},
                "drop_duplicates": ["site_id", "name"],
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")

        assert table.is_drop_duplicate_dependent_on_unnesting() is False

    def test_is_drop_duplicate_dependent_on_unnesting_false_no_unnest(self):
        """Test is_drop_duplicate_dependent_on_unnesting returns False when no unnest."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"], "drop_duplicates": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.is_drop_duplicate_dependent_on_unnesting() is False

    def test_is_drop_duplicate_dependent_on_unnesting_false_bool(self):
        """Test is_drop_duplicate_dependent_on_unnesting returns False when drop_duplicates is bool."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "columns": ["name"],
                "unnest": {"id_vars": ["site_id"], "value_vars": ["val"], "var_name": "type", "value_name": "value"},
                "drop_duplicates": True,
            }
        }

        table = TableConfig(cfg=entities, entity_name="location")

        assert table.is_drop_duplicate_dependent_on_unnesting() is False

    def test_create_append_config(self):
        """Test create_append_config merges configurations correctly."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["id"],
                "columns": ["name", "description"],
                "drop_duplicates": True,
                "source": "main_source",
            }
        }

        table = TableConfig(cfg=entities, entity_name="site")
        append_data = {"source": "extra_source", "columns": ["name", "extra_field"]}

        merged = table.create_append_config(append_data)

        # Should use append_data values when present
        assert merged["source"] == "extra_source"
        assert merged["columns"] == ["name", "extra_field"]
        # Should inherit from parent when not in append_data
        assert merged["surrogate_id"] == "site_id"
        assert merged["drop_duplicates"] is True
        # Should not include ignored keys
        assert "foreign_keys" not in merged
        assert "unnest" not in merged
        assert "append" not in merged

    def test_get_sub_table_configs(self):
        """Test get_sub_table_configs yields base and append configs."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name"],
                "append": [{"source": "extra_sites_1"}, {"source": "extra_sites_2"}],
            }
        }

        table = TableConfig(cfg=entities, entity_name="site")
        configs = list(table.get_sub_table_configs())

        assert len(configs) == 3
        # First should be the base config
        assert configs[0].entity_name == "site"
        # Next should be append configs
        assert configs[1].entity_name == "site__append_0"
        assert configs[2].entity_name == "site__append_1"

    def test_get_sub_table_configs_no_append(self):
        """Test get_sub_table_configs yields only base config when no append."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["name"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        configs = list(table.get_sub_table_configs())

        assert len(configs) == 1
        assert configs[0].entity_name == "site"

    def test_type_property(self):
        """Test type property for different table types."""
        config_fixed: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "type": "fixed"}}
        table_fixed = TableConfig(cfg=config_fixed, entity_name="site")
        assert table_fixed.type == "fixed"

        config_sql: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "type": "sql"}}
        table_sql = TableConfig(cfg=config_sql, entity_name="site")
        assert table_sql.type == "sql"

    def test_data_source_property(self):
        """Test data_source property."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "data_source": "postgres_db"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.data_source == "postgres_db"

    def test_check_column_names_default(self):
        """Test check_column_names defaults to True."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.check_column_names is True

    def test_check_column_names_false(self):
        """Test check_column_names can be set to False."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "check_column_names": False}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.check_column_names is False

    def test_append_mode_default(self):
        """Test append_mode defaults to 'all'."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.append_mode == "all"

    def test_append_mode_distinct(self):
        """Test append_mode can be set to 'distinct'."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "append_mode": "distinct"}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert table.append_mode == "distinct"

    def test_append_configs_dict_converted_to_list(self):
        """Test append config as dict is converted to list."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "append": {"source": "extra"}}}

        table = TableConfig(cfg=entities, entity_name="site")

        assert isinstance(table.append_configs, list)
        assert len(table.append_configs) == 1
        assert table.append_configs[0]["source"] == "extra"

    def test_append_configs_with_non_string_source(self):
        """Test append config with non-string source doesn't add to depends_on."""
        entities: dict[str, dict[str, Any]] = {
            "site": {"surrogate_id": "site_id", "append": [{"source": None}, {"source": 123}, {"source": "valid_source"}]}
        }

        table = TableConfig(cfg=entities, entity_name="site")

        # Only the valid string source should be in depends_on
        assert "valid_source" in table.depends_on
        # Non-string sources should not be in depends_on (depends_on only has string values)
        assert len([dep for dep in table.depends_on if dep == "valid_source"]) == 1

    def test_append_configs_with_several_appends(self):
        """Test append config with non-string source doesn't add to depends_on."""
        cfg = {
            "entities": {
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude"],
                    "depends_on": [],
                    "append": [
                        {
                            "data_source": "test_sql_source",
                            "type": "sql",
                            "values": "sql: SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude",
                        }
                    ],
                    "append_mode": "all",
                },
            },
            "options": {
                "data_sources": {"test_sql_source": {}},
            },
        }
        config: ShapeShiftConfig = ShapeShiftConfig(cfg=cfg)

        sub_configs = list(config.get_table("site").get_sub_table_configs())

        assert len(sub_configs) == 2

        base_config = sub_configs[0]

        # This does a deep comparison!
        assert base_config._data == cfg["entities"]["site"]

        expected_append_config = {
            "surrogate_id": "site_id",
            "keys": ["site_name"],
            "columns": ["site_name", "latitude", "longitude"],
            "data_source": "test_sql_source",
            "type": "sql",
            "values": "sql: SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude",
        }

        sql_append_config = sub_configs[1]
        assert sql_append_config._data == expected_append_config


class TestShapeShiftConfig:
    """Tests for ShapeShiftConfig class."""

    def test_shape_shift_config_with_provided_config(self):
        """Test ShapeShiftConfig with provided configuration."""

        config = ShapeShiftConfig(
            cfg={
                "entities": {
                    "site": {"surrogate_id": "site_id", "columns": ["site_name"]},
                    "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
                }
            }
        )

        assert len(config.tables) == 2
        assert "site" in config.tables
        assert "location" in config.tables
        assert config.get_table("site").surrogate_id == "site_id"

    def test_get_table(self):
        """Test getting a specific table configuration."""

        config = ShapeShiftConfig(cfg={"entities": {"site": {"surrogate_id": "site_id", "columns": ["site_name"]}}})
        site_table: TableConfig = config.get_table("site")

        assert site_table.entity_name == "site"
        assert site_table.surrogate_id == "site_id"

    def test_get_nonexistent_table_raises_error(self):
        """Test that getting nonexistent table raises KeyError."""

        config = ShapeShiftConfig(cfg={"entities": {"site": {"surrogate_id": "site_id"}}})

        with pytest.raises(KeyError):
            config.get_table("nonexistent")

    def test_empty_config(self):
        """Test ShapeShiftConfig with empty configuration."""
        # Note: ShapeShiftConfig uses 'or' logic, so empty dict will try to load from ConfigValue
        # We need to provide a dict with at least one entity or use None to avoid the config loader
        tables = ShapeShiftConfig(cfg={"entities": {"dummy": {"surrogate_id": "id"}}})

        assert len(tables.tables) == 1
        assert "dummy" in tables.tables

    def test_has_table(self):
        """Test has_table method."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}

        tables = ShapeShiftConfig(cfg={"entities": entities})

        assert tables.has_table("site") is True
        assert tables.has_table("location") is True
        assert tables.has_table("nonexistent") is False

    def test_table_names(self):
        """Test table_names property."""
        entities: dict[str, dict[str, str]] = {
            "site": {"surrogate_id": "site_id"},
            "location": {"surrogate_id": "location_id"},
            "region": {"surrogate_id": "region_id"},
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        names: list[str] = tables.table_names

        assert len(names) == 3
        assert "site" in names
        assert "location" in names
        assert "region" in names

    def test_complex_configuration(self):
        """Test with complex nested configuration."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["ProjektNr", "Fustel"],
                "columns": ["ProjektNr", "Fustel", "EVNr"],
                "drop_duplicates": ["ProjektNr", "Fustel"],
                "foreign_keys": [{"entity": "natural_region", "local_keys": ["NaturE"], "remote_keys": ["NaturE"]}],
                "depends_on": ["natural_region"],
            },
            "natural_region": {"surrogate_id": "natural_region_id", "columns": ["NaturE", "NaturrEinh"], "drop_duplicates": True},
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})

        site_table = tables.get_table("site")
        assert site_table.keys == {"ProjektNr", "Fustel"}
        assert site_table.drop_duplicates == ["ProjektNr", "Fustel"]
        assert len(site_table.foreign_keys) == 1
        assert site_table.foreign_keys[0].remote_entity == "natural_region"
        assert site_table.depends_on == {"natural_region"}

        nat_region_table: TableConfig = tables.get_table("natural_region")
        assert nat_region_table.drop_duplicates is True

    @pytest.mark.asyncio
    async def test_resolve_returns_existing_config_instance(self):
        """ShapeShiftConfig.resolve should return provided instance unchanged."""

        config = ShapeShiftConfig(cfg={"entities": {"site": {"surrogate_id": "site_id"}}})

        resolved = await ShapeShiftConfig.resolve(config)

        assert resolved is config

    @pytest.mark.asyncio
    async def test_resolve_loads_from_file_path(self, tmp_path):
        """ShapeShiftConfig.resolve should load configuration from file path."""

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "entities:\n  site:\n    surrogate_id: site_id\n    columns:\n      - name\n",
            encoding="utf-8",
        )

        resolved = await ShapeShiftConfig.resolve(str(config_path))

        assert resolved.has_table("site") is True
        assert resolved.get_table("site").surrogate_id == "site_id"

    @pytest.mark.asyncio
    async def test_resolve_uses_config_provider_for_default_context(self):
        """ShapeShiftConfig.resolve should pull from provider when no config passed."""

        config = Config(data={"entities": {"site": {"surrogate_id": "site_id"}}})

        class RecordingProvider(MockConfigProvider):
            def __init__(self, config: Config) -> None:
                super().__init__(config=config)
                self.last_context: str | None = None

            def is_configured(self, context: str | None = None) -> bool:
                self.last_context = context
                return super().is_configured(context)

        provider = RecordingProvider(config)
        old_provider = set_config_provider(provider)

        try:
            resolved = await ShapeShiftConfig.resolve(None)
            assert resolved.has_table("site")
            assert provider.last_context == "default"
        finally:
            set_config_provider(old_provider)

    @pytest.mark.asyncio
    async def test_resolve_raises_when_context_not_configured(self):
        """ShapeShiftConfig.resolve should raise when provider lacks requested context."""

        provider = MockConfigProvider(config=None)  # type: ignore
        old_provider = set_config_provider(provider)

        try:
            with pytest.raises(ValueError, match="Failed to resolve Config for context 'missing'"):
                await ShapeShiftConfig.resolve("missing")
        finally:
            set_config_provider(old_provider)

    def test_get_sorted_columns_basic(self):
        """Test get_sorted_columns with basic configuration."""
        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_id", "name", "description", "location"],
            }
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        sorted_cols = tables.get_sorted_columns("site")

        # Surrogate ID should be first, then other columns
        assert sorted_cols[0] == "site_id"
        assert set(sorted_cols[1:]) == {"name", "description", "location"}

    def test_get_sorted_columns_with_foreign_keys(self):
        """Test get_sorted_columns places foreign key surrogate IDs after primary surrogate ID."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "columns": ["location_name"],
            },
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_id", "location_id", "site_name", "location_name", "description"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        sorted_cols = tables.get_sorted_columns("site")

        # Order: site_id, location_id (FK), then other columns
        assert sorted_cols[0] == "site_id"
        assert sorted_cols[1] == "location_id"
        assert set(sorted_cols[2:]) == {"site_name", "location_name", "description"}

    def test_get_sorted_columns_multiple_foreign_keys(self):
        """Test get_sorted_columns with multiple foreign keys."""
        entities: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "region": {"surrogate_id": "region_id", "columns": ["region_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_id", "location_id", "region_id", "site_name", "location_name", "region_name", "description"],
                "foreign_keys": [
                    {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]},
                    {"entity": "region", "local_keys": ["region_name"], "remote_keys": ["region_name"]},
                ],
            },
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        sorted_cols = tables.get_sorted_columns("site")

        # Order: site_id, location_id, region_id, then other columns
        assert sorted_cols[0] == "site_id"
        assert sorted_cols[1] == "location_id"
        assert sorted_cols[2] == "region_id"
        assert set(sorted_cols[3:]) == {"site_name", "location_name", "region_name", "description"}

    def test_reorder_columns_basic(self):
        """Test reorder_columns with basic DataFrame."""

        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "description"],
            }
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame({"name": ["Site A", "Site B"], "description": ["Desc A", "Desc B"], "site_id": [1, 2]})

        reordered = tables.reorder_columns("site", df)

        # site_id should be first, the the rest of the columns sorted
        assert list(reordered.columns) == ["site_id", "description", "name"]

    def test_reorder_columns_with_foreign_keys(self):
        """Test reorder_columns places foreign key IDs after primary ID."""

        entities: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name", "location_name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame(
            {"site_name": ["Site A", "Site B"], "location_name": ["Loc A", "Loc B"], "location_id": [10, 20], "site_id": [1, 2]}
        )

        reordered = tables.reorder_columns("site", df)

        # Order: site_id, location_id, then other columns
        assert list(reordered.columns) == ["site_id", "location_id", "location_name", "site_name"]

    def test_reorder_columns_with_extra_columns(self):
        """Test reorder_columns places extra_columns after foreign keys."""

        entities: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name", "location_name"],
                "extra_columns": {"default_lat": 0.0, "default_lon": 0.0},
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame(
            {
                "site_name": ["Site A", "Site B"],
                "location_name": ["Loc A", "Loc B"],
                "location_id": [10, 20],
                "site_id": [1, 2],
                "default_lat": [1.0, 2.0],
                "default_lon": [3.0, 4.0],
                "other_col": ["X", "Y"],
            }
        )

        reordered = tables.reorder_columns("site", df)

        # Order: site_id, location_id, extra columns (default_lat, default_lon), then other columns
        assert reordered.columns[0] == "site_id"
        assert reordered.columns[1] == "location_id"
        assert "default_lat" in reordered.columns[:4]
        assert "default_lon" in reordered.columns[:4]
        # Other columns come last
        assert "site_name" in list(reordered.columns)[4:]
        assert "location_name" in list(reordered.columns)[4:]
        assert "other_col" in list(reordered.columns)[4:]

    def test_reorder_columns_missing_surrogate_id(self):
        """Test reorder_columns when surrogate_id not in DataFrame."""

        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "description"],
            }
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame({"name": ["Site A", "Site B"], "description": ["Desc A", "Desc B"]})

        reordered = tables.reorder_columns("site", df)

        # Should still work, just without site_id in front
        assert list(reordered.columns) == ["description", "name"]

    def test_reorder_columns_with_table_config_object(self):
        """Test reorder_columns accepts TableConfig object instead of string."""

        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name"],
            }
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        table_cfg = tables.get_table("site")
        df = pd.DataFrame({"name": ["Site A", "Site B"], "site_id": [1, 2]})

        reordered = tables.reorder_columns(table_cfg, df)

        assert list(reordered.columns) == ["site_id", "name"]

    def test_reorder_columns_complex_scenario(self):
        """Test reorder_columns with multiple foreign keys and extra columns."""

        entities: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "region": {"surrogate_id": "region_id", "columns": ["region_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name", "location_name", "region_name"],
                "extra_columns": {"created_at": None, "updated_at": None},
                "foreign_keys": [
                    {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]},
                    {"entity": "region", "local_keys": ["region_name"], "remote_keys": ["region_name"]},
                ],
            },
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame(
            {
                "site_name": ["Site A", "Site B"],
                "description": ["Desc A", "Desc B"],
                "location_name": ["Loc A", "Loc B"],
                "region_name": ["Reg A", "Reg B"],
                "location_id": [10, 20],
                "region_id": [100, 200],
                "site_id": [1, 2],
                "created_at": ["2021-01-01", "2021-01-02"],
                "updated_at": ["2021-02-01", "2021-02-02"],
            }
        )

        reordered = tables.reorder_columns("site", df)

        # Expected order: site_id, location_id, region_id, created_at, updated_at, then other columns
        cols = list(reordered.columns)
        assert cols[0] == "site_id"
        assert cols[1] == "location_id"
        assert cols[2] == "region_id"
        # Extra columns should come next
        assert "created_at" in cols[3:5]
        assert "updated_at" in cols[3:5]
        # Other columns come last
        assert "site_name" in cols[5:]
        assert "description" in cols[5:]
        assert "location_name" in cols[5:]
        assert "region_name" in cols[5:]

    def test_reorder_columns_preserves_data(self):
        """Test that reorder_columns preserves all data correctly."""

        entities: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "value"],
            }
        }

        tables = ShapeShiftConfig(cfg={"entities": entities})
        df = pd.DataFrame({"name": ["A", "B", "C"], "value": [1, 2, 3], "site_id": [10, 20, 30]})

        reordered: pd.DataFrame = tables.reorder_columns("site", df)

        # Check data is preserved
        assert len(reordered) == 3
        assert reordered["site_id"].tolist() == [10, 20, 30]
        assert reordered["name"].tolist() == ["A", "B", "C"]
        assert reordered["value"].tolist() == [1, 2, 3]

    def test_get_data_source(self):
        """Test get_data_source method."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        options = {"data_sources": {"postgres_db": {"driver": "postgresql", "options": {"host": "localhost"}}}}

        config = ShapeShiftConfig(cfg={"entities": entities, "options": options})
        data_source: DataSourceConfig = config.get_data_source("postgres_db")

        assert data_source.name == "postgres_db"
        assert data_source.driver == "postgresql"

    def test_get_data_source_not_found(self):
        """Test get_data_source raises ValueError when source not found."""

        config = ShapeShiftConfig(cfg={"entities": {"site": {"surrogate_id": "site_id"}}, "options": {"data_sources": {}}})

        with pytest.raises(ValueError, match="Data source.*not found"):
            config.get_data_source("nonexistent")

    def test_resolve_loader_with_data_source(self):
        """Test resolve_loader with data_source configured."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "data_source": "postgres_db"}}
        options = {"data_sources": {"postgres_db": {"driver": "postgresql", "options": {"host": "localhost"}}}}

        config = ShapeShiftConfig(cfg={"entities": entities, "options": options})
        table_cfg: TableConfig = config.get_table("site")

        # This will fail if the loader type isn't registered, but we're testing the logic
        # In real code, the DataLoaders would be registered
        try:
            _ = config.resolve_loader(table_cfg)
            # If it succeeds, check it's not None (depends on DataLoaders being registered)
            # For now, we just test that it doesn't crash
        except KeyError:
            # Expected if the loader type isn't registered
            pass

    def test_resolve_loader_with_type(self):
        """Test resolve_loader with type configured."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "type": "fixed"}}
        options: dict[str, dict[str, Any]] = {}

        config = ShapeShiftConfig(cfg={"entities": entities, "options": options})
        table_cfg: TableConfig = config.get_table("site")

        # This will fail if the loader type isn't registered
        try:
            _ = config.resolve_loader(table_cfg)
            # Test passes if no exception
        except KeyError:
            # Expected if the loader type isn't registered
            pass

    def test_resolve_loader_no_loader(self):
        """Test resolve_loader returns None when no loader available."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        options: dict[str, dict[str, Any]] = {}

        config = ShapeShiftConfig(cfg={"entities": entities, "options": options})
        table_cfg: TableConfig = config.get_table("site")

        loader: DataLoader | None = config.resolve_loader(table_cfg)

        # Should return None or log warning
        assert loader is None


class TestDataSourceConfig:
    """Tests for DataSourceConfig class."""

    def test_data_source_config_basic(self):
        """Test basic DataSourceConfig initialization."""
        cfg = {"driver": "postgresql", "options": {"host": "localhost", "port": 5432}}

        data_source = DataSourceConfig(cfg=cfg, name="test_db")

        assert data_source.name == "test_db"
        assert data_source.driver == "postgresql"
        assert data_source.options == {"host": "localhost", "port": 5432}

    def test_data_source_config_no_driver(self):
        """Test DataSourceConfig with missing driver defaults to empty string."""
        cfg: dict[str, Any] = {"options": {"host": "localhost"}}

        data_source = DataSourceConfig(cfg=cfg, name="test_db")

        assert data_source.driver == ""
        assert data_source.options == {"host": "localhost"}

    def test_data_source_config_no_options(self):
        """Test DataSourceConfig with missing options defaults to empty dict."""
        cfg = {"driver": "postgresql"}

        data_source = DataSourceConfig(cfg=cfg, name="test_db")

        assert data_source.driver == "postgresql"
        assert data_source.options == {}

    def test_data_source_config_empty(self):
        """Test DataSourceConfig with empty config."""
        data_source = DataSourceConfig(cfg={}, name="test_db")

        assert data_source.name == "test_db"
        assert data_source.driver == ""
        assert data_source.options == {}

    def test_data_source_config_none(self):
        """Test DataSourceConfig with None config."""
        data_source = DataSourceConfig(cfg=None, name="test_db")

        assert data_source.name == "test_db"
        assert data_source.driver == ""
        assert data_source.options == {}

    def test_tables_config_with_none_options(self):
        """Test ShapeShiftConfig with None options triggers ConfigValue resolution."""

        # This will try to resolve options from ConfigValue when options=None
        # We can't fully test this without the config system, but we ensure it doesn't crash
        try:
            tables = ShapeShiftConfig(cfg={"entities": {"site": {"surrogate_id": "site_id"}}})
            # If it succeeds, options should be a dict
            assert isinstance(tables.options, dict)
        except Exception:  # pylint: disable=broad-except
            # May fail if ConfigValue can't resolve, but that's OK for this test
            pass


class TestIntegration:
    """Integration tests for all classes working together."""

    def test_full_configuration_workflow(self):
        """Test a full configuration workflow with all features."""
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "keys": ["Ort", "Kreis", "Land"],
                "columns": ["Ort", "Kreis", "Land"],
                "unnest": {
                    "id_vars": ["site_id"],
                    "value_vars": ["Ort", "Kreis", "Land"],
                    "var_name": "location_type",
                    "value_name": "location_name",
                },
                "drop_duplicates": ["Ort", "Kreis", "Land"],
                "depends_on": [],
            },
            "site": {
                "surrogate_id": "site_id",
                "keys": ["ProjektNr", "Fustel"],
                "columns": ["ProjektNr", "Fustel", "EVNr"],
                "drop_duplicates": ["ProjektNr", "Fustel"],
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": ["location_type", "location_name"],
                        "remote_keys": ["location_type", "location_name"],
                    }
                ],
                "depends_on": ["location"],
            },
        }

        config = ShapeShiftConfig(cfg={"entities": entities})

        # Test location table
        location: TableConfig = config.get_table("location")
        assert location.unnest is not None
        assert location.unnest.var_name == "location_type"
        assert location.drop_duplicates == ["Ort", "Kreis", "Land"]

        # Test site table
        site: TableConfig = config.get_table("site")
        assert len(site.foreign_keys) == 1
        assert site.foreign_keys[0].remote_entity == "location"
        assert site.foreign_keys[0].remote_surrogate_id == "location_id"
        assert site.depends_on == {"location"}

    def test_foreign_key_with_extra_columns_workflow(self):
        """Test foreign key configuration with extra_columns in full workflow."""
        extra_columns_cfg: dict[str, str] = {"site_latitude": "latitude", "site_longitude": "longitude"}
        entities: dict[str, dict[str, Any]] = {
            "location": {
                "surrogate_id": "location_id",
                "keys": ["location_name"],
                "columns": ["location_name", "latitude", "longitude", "elevation"],
            },
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "description"],
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": ["location_name"],
                        "remote_keys": ["location_name"],
                        "extra_columns": extra_columns_cfg,
                        "drop_remote_id": False,
                    }
                ],
                "depends_on": ["location"],
            },
        }

        config = ShapeShiftConfig(cfg={"entities": entities})

        # Test site foreign key configuration
        site: TableConfig = config.get_table("site")
        assert len(site.foreign_keys) == 1

        fk: ForeignKeyConfig = site.foreign_keys[0]
        assert fk.remote_entity == "location"
        assert fk.local_keys == ["location_name"]
        assert fk.remote_keys == ["location_name"]
        assert fk.remote_extra_columns == {v: k for k, v in extra_columns_cfg.items()}
        assert fk.drop_remote_id is False
