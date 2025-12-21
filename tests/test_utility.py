"""Unit tests for arbodat utility configuration classes."""

from typing import Any

import pytest

from src.model import ForeignKeyConfig, ShapeShiftConfig, TableConfig, UnnestConfig


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
        data = {}
        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            UnnestConfig(cfg={}, data=data)

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
        fk_data: dict[str, list[str]] = {"local_keys": ["col1"], "remote_keys": ["col1"]}

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
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["col1"]}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
            ForeignKeyConfig(cfg=entities, local_entity="site", data=fk_data)

    def test_empty_remote_keys(self):
        """Test that empty remote_keys raises ValueError."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}
        fk_data = {"entity": "location", "local_keys": ["col1"], "remote_keys": []}

        with pytest.raises(ValueError, match="missing local and/or remote keys"):
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
        entities = {
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

    def test_table_drop_duplicates_bool(self):
        """Test drop_duplicates as boolean."""
        entities = {"site": {"surrogate_id": "site_id", "drop_duplicates": True}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates is True

    def test_table_drop_duplicates_list(self):
        """Test drop_duplicates as list of columns."""
        entities = {"site": {"surrogate_id": "site_id", "drop_duplicates": ["col1", "col2"]}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates == ["col1", "col2"]

    def test_table_drop_duplicates_default(self):
        """Test drop_duplicates defaults to False."""
        entities = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.drop_duplicates is False

    def test_table_with_unnest(self):
        """Test table configuration with unnest."""
        entities = {
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
        entities = {"site": {"surrogate_id": "site_id"}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert table.unnest is None

    def test_missing_entity_raises_error(self):
        """Test that missing entity raises KeyError."""
        entities = {"site": {"surrogate_id": "site_id"}}

        with pytest.raises(KeyError):
            TableConfig(cfg=entities, entity_name="nonexistent")

    def test_empty_lists_default_correctly(self):
        """Test that empty lists in config return as empty lists."""
        entities = {"site": {"surrogate_id": "site_id", "keys": [], "columns": [], "depends_on": []}}

        table = TableConfig(cfg=entities, entity_name="site")
        assert not table.keys
        assert table.columns == []
        assert table.depends_on == set()

    def test_fk_column_set(self):
        """Test fk_column_set returns all foreign key columns."""
        entities = {
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
        fk_cols = table.fk_columns

        assert len(fk_cols) == 3
        assert "location_id" in fk_cols
        assert "location_type" in fk_cols
        assert "region_id" in fk_cols

    def test_extra_fk_columns(self):
        """Test extra_fk_columns returns FK columns not in keys or columns."""
        entities = {
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
        entities = {
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


class TestShapeShiftConfig:
    """Tests for ShapeShiftConfig class."""

    def test_shape_shift_config_with_provided_config(self):
        """Test ShapeShiftConfig with provided configuration."""
        entities = {
            "site": {"surrogate_id": "site_id", "columns": ["site_name"]},
            "location": {"surrogate_id": "location_id", "columns": ["location_name"]},
        }

        config = ShapeShiftConfig(cfg={"entities": entities})

        assert len(config.tables) == 2
        assert "site" in config.tables
        assert "location" in config.tables
        assert config.get_table("site").surrogate_id == "site_id"

    def test_get_table(self):
        """Test getting a specific table configuration."""
        entities = {"site": {"surrogate_id": "site_id", "columns": ["site_name"]}}

        config = ShapeShiftConfig(cfg={"entities": entities})
        site_table: TableConfig = config.get_table("site")

        assert site_table.entity_name == "site"
        assert site_table.surrogate_id == "site_id"

    def test_get_nonexistent_table_raises_error(self):
        """Test that getting nonexistent table raises KeyError."""
        entities = {"site": {"surrogate_id": "site_id"}}

        config = ShapeShiftConfig(cfg={"entities": entities})

        with pytest.raises(KeyError):
            config.get_table("nonexistent")

    def test_empty_config(self):
        """Test ShapeShiftConfig with empty configuration."""
        # Note: ShapeShiftConfig uses 'or' logic, so empty dict will try to load from ConfigValue
        # We need to provide a dict with at least one entity or use None to avoid the config loader
        entities = {"dummy": {"surrogate_id": "id"}}
        config = ShapeShiftConfig(cfg={"entities": entities})

        assert len(config.tables) == 1
        assert "dummy" in config.tables

    def test_has_table(self):
        """Test has_table method."""
        entities = {"site": {"surrogate_id": "site_id"}, "location": {"surrogate_id": "location_id"}}

        config = ShapeShiftConfig(cfg={"entities": entities})

        assert config.has_table("site") is True
        assert config.has_table("location") is True
        assert config.has_table("nonexistent") is False

    def test_table_names(self):
        """Test table_names property."""
        entities = {
            "site": {"surrogate_id": "site_id"},
            "location": {"surrogate_id": "location_id"},
            "region": {"surrogate_id": "region_id"},
        }

        config = ShapeShiftConfig(cfg={"entities": entities})
        names: list[str] = config.table_names

        assert len(names) == 3
        assert "site" in names
        assert "location" in names
        assert "region" in names

    def test_complex_configuration(self):
        """Test with complex nested configuration."""
        entities = {
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

        config = ShapeShiftConfig(cfg={"entities": entities})

        site_table: TableConfig = config.get_table("site")
        assert site_table.keys == {"ProjektNr", "Fustel"}
        assert site_table.drop_duplicates == ["ProjektNr", "Fustel"]
        assert len(site_table.foreign_keys) == 1
        assert site_table.foreign_keys[0].remote_entity == "natural_region"
        assert site_table.depends_on == {"natural_region"}

        nat_region_table: TableConfig = config.get_table("natural_region")
        assert nat_region_table.drop_duplicates is True


class TestIntegration:
    """Integration tests for all classes working together."""

    def test_full_configuration_workflow(self):
        """Test a full configuration workflow with all features."""
        entities = {
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
