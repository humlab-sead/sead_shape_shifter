"""Unit tests for arbodat utility configuration classes."""

from typing import Any

import pandas as pd
import pytest

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig, UnnestConfig


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
        config = {
            "site": {"surrogate_id": "site_id", "keys": ["site_name"]},
            "location": {"surrogate_id": "location_id", "keys": ["location_name"]},
        }
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.local_entity == "site"
        assert fk.remote_entity == "location"
        assert fk.local_keys == ["location_name"]
        assert fk.remote_keys == ["location_name"]
        assert fk.remote_surrogate_id == "location_id"

    def test_missing_remote_entity(self):
        """Test that missing remote entity raises ValueError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        fk_data: dict[str, Any] = {"local_keys": ["col1"], "remote_keys": ["col1"]}

        with pytest.raises(ValueError, match="missing remote entity"):
            ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

    def test_unknown_remote_entity(self):
        """Test that unknown remote entity raises ValueError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        fk_data: dict[str, Any] = {"entity": "unknown_entity", "local_keys": ["col1"], "remote_keys": ["col1"]}

        with pytest.raises(ValueError, match="references unknown entity"):
            ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

    def test_missing_remote_keys(self):
        """Test that missing remote_keys raises ValueError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data: dict[str, Any] = {"entity": "location", "local_keys": ["col1"]}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
            ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

    def test_empty_remote_keys(self):
        """Test that empty remote_keys raises ValueError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data: dict[str, Any] = {"entity": "location", "local_keys": ["col1"], "remote_keys": []}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
            ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

    def test_extra_columns_as_dict(self):
        """Test extra_columns as a dictionary mapping local to remote column names."""
        extra_columns_cfg: dict[str, str] = {"local_col1": "remote_col1", "local_col2": "remote_col2"}
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": extra_columns_cfg,
        }

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {v: k for k, v in extra_columns_cfg.items()}

    def test_extra_columns_as_list(self):
        """Test extra_columns as a list (maps column names to themselves)."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["col1", "col2", "col3"],
        }

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"col1": "col1", "col2": "col2", "col3": "col3"}

    def test_extra_columns_as_string(self):
        """Test extra_columns as a single string (converted to list, then dict)."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": "column1"}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"column1": "column1"}

    def test_extra_columns_empty_dict(self):
        """Test extra_columns with empty dict returns empty dict."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": {}}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {}

    def test_extra_columns_missing(self):
        """Test that missing extra_columns defaults to empty dict."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {}

    def test_extra_columns_invalid_type(self):
        """Test that invalid extra_columns type raises ValueError."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "extra_columns": 123}

        with pytest.raises(ValueError, match="Invalid extra_columns format"):
            ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

    def test_drop_remote_id_true(self):
        """Test drop_remote_id set to True."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "drop_remote_id": True}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is True

    def test_drop_remote_id_false(self):
        """Test drop_remote_id set to False."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"], "drop_remote_id": False}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is False

    def test_drop_remote_id_default(self):
        """Test that drop_remote_id defaults to False when not specified."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.drop_remote_id is False

    def test_combined_extra_columns_and_drop_remote_id(self):
        """Test using both extra_columns and drop_remote_id together."""
        config = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {
            "entity": "location",
            "local_keys": ["location_name"],
            "remote_keys": ["location_name"],
            "extra_columns": ["description", "code"],
            "drop_remote_id": True,
        }

        fk = ForeignKeyConfig(cfg=config, local_entity="site", data=fk_data)

        assert fk.remote_extra_columns == {"description": "description", "code": "code"}
        assert fk.drop_remote_id is True


class TestTableConfig:
    """Tests for TableConfig class."""

    def test_basic_table_config(self):
        """Test creating a basic table configuration."""
        config = {
            "site": {"surrogate_id": "site_id", "keys": ["site_name"], "columns": ["site_name", "description"], "depends_on": ["location"]}
        }

        table = TableConfig(cfg=config, entity_name="site")

        assert table.entity_name == "site"
        assert table.surrogate_id == "site_id"
        assert table.keys == {"site_name"}
        assert table.columns == ["site_name", "description"]
        assert table.depends_on == {"location"}
        assert table.foreign_keys == []

    def test_table_with_foreign_keys(self):
        """Test table configuration with foreign keys."""
        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
            },
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
        }

        table = TableConfig(cfg=config, entity_name="site")

        assert len(table.foreign_keys) == 1
        assert table.foreign_keys[0].remote_entity == "location"
        assert table.foreign_keys[0].local_keys == ["location_id"]

    def test_table_with_foreign_keys_extra_columns(self):
        """Test table configuration with foreign keys including extra_columns."""
        config: dict[str, dict[str, Any]] = {
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

        table = TableConfig(cfg=config, entity_name="site")

        assert len(table.foreign_keys) == 1
        fk = table.foreign_keys[0]
        assert fk.remote_entity == "location"
        assert fk.remote_extra_columns == {"latitude": "latitude", "longitude": "longitude"}
        assert fk.drop_remote_id is True

    def test_table_drop_duplicates_bool(self):
        """Test drop_duplicates as boolean."""
        config: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "drop_duplicates": True}}

        table = TableConfig(cfg=config, entity_name="site")
        assert table.drop_duplicates is True

    def test_table_drop_duplicates_list(self):
        """Test drop_duplicates as list of columns."""
        config: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "drop_duplicates": ["col1", "col2"]}}

        table = TableConfig(cfg=config, entity_name="site")
        assert table.drop_duplicates == ["col1", "col2"]

    def test_table_drop_duplicates_default(self):
        """Test drop_duplicates defaults to False."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=config, entity_name="site")
        assert table.drop_duplicates is False

    def test_table_with_unnest(self):
        """Test table configuration with unnest."""
        config: dict[str, dict[str, Any]] = {
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

        table = TableConfig(cfg=config, entity_name="location")

        assert table.unnest is not None
        assert table.unnest.id_vars == ["site_id"]
        assert table.unnest.var_name == "location_type"

    def test_table_without_unnest(self):
        """Test table configuration without unnest."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=config, entity_name="site")
        assert table.unnest is None

    def test_missing_entity_raises_error(self):
        """Test that missing entity raises KeyError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        with pytest.raises(KeyError):
            TableConfig(cfg=config, entity_name="nonexistent")

    def test_empty_lists_default_correctly(self):
        """Test that empty lists in config return as empty lists."""
        config: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "keys": [], "columns": [], "depends_on": []}}

        table = TableConfig(cfg=config, entity_name="site")
        assert not table.keys
        assert table.columns == []
        assert table.depends_on == set()

    def test_fk_column_set(self):
        """Test fk_column_set returns all foreign key columns."""
        config: dict[str, dict[str, Any]] = {
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

        table = TableConfig(cfg=config, entity_name="site")
        fk_cols: set[str] = table.fk_columns

        assert len(fk_cols) == 3
        assert "location_id" in fk_cols
        assert "location_type" in fk_cols
        assert "region_id" in fk_cols

    def test_extra_fk_columns(self):
        """Test extra_fk_columns returns FK columns not in keys or columns."""
        config: dict[str, dict[str, Any]] = {
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

        table = TableConfig(cfg=config, entity_name="site")
        extra_cols = table.extra_fk_columns

        # location_id is in columns, location_type is not
        assert "location_type" in extra_cols
        assert "location_id" not in extra_cols

    def test_usage_columns(self):
        """Test usage_columns returns union of columns2 and fk_column_set."""
        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "description"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["location_id"]}],
            },
            "location": {"surrogate_id": "location_id"},
        }

        table = TableConfig(cfg=config, entity_name="site")
        usage_cols: list[str] = table.keys_columns_and_fks

        assert "site_name" in usage_cols
        assert "description" in usage_cols
        assert "location_id" in usage_cols
        assert len(usage_cols) == 3


class TestTablesConfig:
    """Tests for TablesConfig class."""

    def test_tables_config_with_provided_config(self):
        """Test TablesConfig with provided configuration."""
        config: dict[str, Any] = {
            "site": {"surrogate_id": "site_id", "columns": ["site_name"]},
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
        }

        tables = TablesConfig(entities_cfg=config, options={})

        assert len(tables.tables) == 2
        assert "site" in tables.tables
        assert "location" in tables.tables
        assert tables.get_table("site").surrogate_id == "site_id"

    def test_get_table(self):
        """Test getting a specific table configuration."""
        config: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "columns": ["site_name"]}}

        tables = TablesConfig(entities_cfg=config, options={})
        site_table: TableConfig = tables.get_table("site")

        assert site_table.entity_name == "site"
        assert site_table.surrogate_id == "site_id"

    def test_get_nonexistent_table_raises_error(self):
        """Test that getting nonexistent table raises KeyError."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}

        tables = TablesConfig(entities_cfg=config, options={})

        with pytest.raises(KeyError):
            tables.get_table("nonexistent")

    def test_empty_config(self):
        """Test TablesConfig with empty configuration."""
        # Note: TablesConfig uses 'or' logic, so empty dict will try to load from ConfigValue
        # We need to provide a dict with at least one entity or use None to avoid the config loader
        config: dict[str, dict[str, str]] = {"dummy": {"surrogate_id": "id"}}
        tables = TablesConfig(entities_cfg=config, options={})

        assert len(tables.tables) == 1
        assert "dummy" in tables.tables

    def test_has_table(self):
        """Test has_table method."""
        config: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}

        tables = TablesConfig(entities_cfg=config, options={})

        assert tables.has_table("site") is True
        assert tables.has_table("location") is True
        assert tables.has_table("nonexistent") is False

    def test_table_names(self):
        """Test table_names property."""
        config: dict[str, dict[str, str]] = {
            "site": {"surrogate_id": "site_id"},
            "location": {"surrogate_id": "location_id"},
            "region": {"surrogate_id": "region_id"},
        }

        tables = TablesConfig(entities_cfg=config, options={})
        names: list[str] = tables.table_names

        assert len(names) == 3
        assert "site" in names
        assert "location" in names
        assert "region" in names

    def test_complex_configuration(self):
        """Test with complex nested configuration."""
        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})

        site_table = tables.get_table("site")
        assert site_table.keys == {"ProjektNr", "Fustel"}
        assert site_table.drop_duplicates == ["ProjektNr", "Fustel"]
        assert len(site_table.foreign_keys) == 1
        assert site_table.foreign_keys[0].remote_entity == "natural_region"
        assert site_table.depends_on == {"natural_region"}

        nat_region_table: TableConfig = tables.get_table("natural_region")
        assert nat_region_table.drop_duplicates is True

    def test_get_sorted_columns_basic(self):
        """Test get_sorted_columns with basic configuration."""
        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_id", "name", "description", "location"],
            }
        }

        tables = TablesConfig(entities_cfg=config, options={})
        sorted_cols = tables.get_sorted_columns("site")

        # Surrogate ID should be first, then other columns
        assert sorted_cols[0] == "site_id"
        assert set(sorted_cols[1:]) == {"name", "description", "location"}

    def test_get_sorted_columns_with_foreign_keys(self):
        """Test get_sorted_columns places foreign key surrogate IDs after primary surrogate ID."""
        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})
        sorted_cols = tables.get_sorted_columns("site")

        # Order: site_id, location_id (FK), then other columns
        assert sorted_cols[0] == "site_id"
        assert sorted_cols[1] == "location_id"
        assert set(sorted_cols[2:]) == {"site_name", "location_name", "description"}

    def test_get_sorted_columns_multiple_foreign_keys(self):
        """Test get_sorted_columns with multiple foreign keys."""
        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})
        sorted_cols = tables.get_sorted_columns("site")

        # Order: site_id, location_id, region_id, then other columns
        assert sorted_cols[0] == "site_id"
        assert sorted_cols[1] == "location_id"
        assert sorted_cols[2] == "region_id"
        assert set(sorted_cols[3:]) == {"site_name", "location_name", "region_name", "description"}

    def test_reorder_columns_basic(self):
        """Test reorder_columns with basic DataFrame."""

        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "description"],
            }
        }

        tables = TablesConfig(entities_cfg=config, options={})
        df = pd.DataFrame({"name": ["Site A", "Site B"], "description": ["Desc A", "Desc B"], "site_id": [1, 2]})

        reordered = tables.reorder_columns("site", df)

        # site_id should be first
        assert list(reordered.columns) == ["site_id", "name", "description"]

    def test_reorder_columns_with_foreign_keys(self):
        """Test reorder_columns places foreign key IDs after primary ID."""

        config: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name", "location_name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        tables = TablesConfig(entities_cfg=config, options={})
        df = pd.DataFrame(
            {"site_name": ["Site A", "Site B"], "location_name": ["Loc A", "Loc B"], "location_id": [10, 20], "site_id": [1, 2]}
        )

        reordered = tables.reorder_columns("site", df)

        # Order: site_id, location_id, then other columns
        assert list(reordered.columns) == ["site_id", "location_id", "site_name", "location_name"]

    def test_reorder_columns_with_extra_columns(self):
        """Test reorder_columns places extra_columns after foreign keys."""

        config: dict[str, dict[str, Any]] = {
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
            "site": {
                "surrogate_id": "site_id",
                "columns": ["site_name", "location_name"],
                "extra_columns": {"default_lat": 0.0, "default_lon": 0.0},
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        tables = TablesConfig(entities_cfg=config, options={})
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

        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "description"],
            }
        }

        tables = TablesConfig(entities_cfg=config, options={})
        df = pd.DataFrame({"name": ["Site A", "Site B"], "description": ["Desc A", "Desc B"]})

        reordered = tables.reorder_columns("site", df)

        # Should still work, just without site_id in front
        assert list(reordered.columns) == ["name", "description"]

    def test_reorder_columns_with_table_config_object(self):
        """Test reorder_columns accepts TableConfig object instead of string."""

        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name"],
            }
        }

        tables = TablesConfig(entities_cfg=config, options={})
        table_cfg = tables.get_table("site")
        df = pd.DataFrame({"name": ["Site A", "Site B"], "site_id": [1, 2]})

        reordered = tables.reorder_columns(table_cfg, df)

        assert list(reordered.columns) == ["site_id", "name"]

    def test_reorder_columns_complex_scenario(self):
        """Test reorder_columns with multiple foreign keys and extra columns."""

        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})
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

        config: dict[str, dict[str, Any]] = {
            "site": {
                "surrogate_id": "site_id",
                "columns": ["name", "value"],
            }
        }

        tables = TablesConfig(entities_cfg=config, options={})
        df = pd.DataFrame({"name": ["A", "B", "C"], "value": [1, 2, 3], "site_id": [10, 20, 30]})

        reordered = tables.reorder_columns("site", df)

        # Check data is preserved
        assert len(reordered) == 3
        assert reordered["site_id"].tolist() == [10, 20, 30]
        assert reordered["name"].tolist() == ["A", "B", "C"]
        assert reordered["value"].tolist() == [1, 2, 3]


class TestIntegration:
    """Integration tests for all classes working together."""

    def test_full_configuration_workflow(self):
        """Test a full configuration workflow with all features."""
        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})

        # Test location table
        location: TableConfig = tables.get_table("location")
        assert location.unnest is not None
        assert location.unnest.var_name == "location_type"
        assert location.drop_duplicates == ["Ort", "Kreis", "Land"]

        # Test site table
        site: TableConfig = tables.get_table("site")
        assert len(site.foreign_keys) == 1
        assert site.foreign_keys[0].remote_entity == "location"
        assert site.foreign_keys[0].remote_surrogate_id == "location_id"
        assert site.depends_on == {"location"}

    def test_foreign_key_with_extra_columns_workflow(self):
        """Test foreign key configuration with extra_columns in full workflow."""
        extra_columns_cfg: dict[str, str] = {"site_latitude": "latitude", "site_longitude": "longitude"}
        config: dict[str, dict[str, Any]] = {
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

        tables = TablesConfig(entities_cfg=config, options={})

        # Test site foreign key configuration
        site: TableConfig = tables.get_table("site")
        assert len(site.foreign_keys) == 1

        fk = site.foreign_keys[0]
        assert fk.remote_entity == "location"
        assert fk.local_keys == ["location_name"]
        assert fk.remote_keys == ["location_name"]
        assert fk.remote_extra_columns == {v: k for k, v in extra_columns_cfg.items()}
        assert fk.drop_remote_id is False
