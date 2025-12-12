"""Tests for append configuration parsing and validation."""

from src.config_model import TableConfig


class TestAppendConfigurationParsing:
    """Test parsing of append configurations from YAML-like dictionaries."""

    def test_no_append_configuration(self):
        """Test entity without append configuration."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "keys": ["key1"],
                "columns": ["key1", "col1"],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert table_cfg.has_append is False
        assert table_cfg.append_configs == []
        assert table_cfg.append_mode == "all"

    def test_single_append_configuration(self):
        """Test entity with single append item."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "keys": ["key1"],
                "columns": ["key1", "col1"],
                "depends_on": [],
                "append": [
                    {
                        "type": "fixed",
                        "values": [["val1"], ["val2"]],
                    }
                ],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert table_cfg.has_append is True
        assert len(table_cfg.append_configs) == 1
        assert table_cfg.append_configs[0]["type"] == "fixed"

    def test_multiple_append_configurations(self):
        """Test entity with multiple append items."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "keys": ["key1"],
                "columns": ["key1", "col1"],
                "depends_on": [],
                "append": [
                    {"type": "fixed", "values": [["val1"]]},
                    {"type": "fixed", "values": [["val2"]]},
                    {"type": "data", "source": "other_entity"},
                ],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert table_cfg.has_append is True
        assert len(table_cfg.append_configs) == 3

    def test_append_mode_default(self):
        """Test default append_mode is 'all'."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": [{"type": "fixed", "values": []}],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        assert table_cfg.append_mode == "all"

    def test_append_mode_distinct(self):
        """Test explicit append_mode setting."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": [{"type": "fixed", "values": []}],
                "append_mode": "distinct",
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        assert table_cfg.append_mode == "distinct"


class TestAppendDependencyResolution:
    """Test dependency resolution for append configurations."""

    def test_append_adds_source_to_dependencies(self):
        """Test that append source is added to depends_on."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": [
                    {"type": "data", "source": "source_entity"},
                ],
            },
            "source_entity": {
                "surrogate_id": "source_id",
                "columns": [],
                "depends_on": [],
            },
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert "source_entity" in table_cfg.depends_on

    def test_append_multiple_sources_in_dependencies(self):
        """Test multiple append sources are added to depends_on."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": ["manual_dep"],
                "append": [
                    {"type": "data", "source": "source1"},
                    {"type": "data", "source": "source2"},
                ],
            },
            "source1": {"columns": [], "depends_on": []},
            "source2": {"columns": [], "depends_on": []},
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert "source1" in table_cfg.depends_on
        assert "source2" in table_cfg.depends_on
        assert "manual_dep" in table_cfg.depends_on

    def test_append_fixed_no_dependency(self):
        """Test that fixed append doesn't add dependencies."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": [
                    {"type": "fixed", "values": [["val"]]},
                ],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        # Should only have explicit dependencies, no append-related ones
        assert len(table_cfg.depends_on) == 0


class TestAppendPropertyInheritance:
    """Test property inheritance from parent to append items."""

    def test_create_append_config_inherits_keys(self):
        """Test that append config inherits keys from parent."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "keys": ["key1", "key2"],
                "columns": ["key1", "key2", "col1"],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"type": "fixed", "values": []}

        merged = table_cfg.create_append_config(append_data)

        # Keys come from a set, so order may vary
        assert set(merged["keys"]) == {"key1", "key2"}

    def test_create_append_config_inherits_surrogate_id(self):
        """Test that append config inherits surrogate_id."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "keys": [],
                "columns": [],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"type": "fixed", "values": []}

        merged = table_cfg.create_append_config(append_data)

        assert merged["surrogate_id"] == "test_id"

    def test_create_append_config_can_override_source(self):
        """Test that append config can override source."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "source": "parent_source",
                "columns": [],
                "depends_on": [],
            },
            "parent_source": {"columns": [], "depends_on": []},
            "append_source": {"columns": [], "depends_on": []},
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"source": "append_source"}

        merged = table_cfg.create_append_config(append_data)

        assert merged["source"] == "append_source"

    def test_create_append_config_inherits_columns(self):
        """Test that append config inherits columns by default."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["col1", "col2"],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"type": "fixed"}

        merged = table_cfg.create_append_config(append_data)

        assert merged["columns"] == ["col1", "col2"]

    def test_create_append_config_can_override_columns(self):
        """Test that append config can specify different columns."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["col1", "col2"],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"columns": ["col3", "col4"]}

        merged = table_cfg.create_append_config(append_data)

        assert merged["columns"] == ["col3", "col4"]

    def test_create_append_config_with_values(self):
        """Test that append config includes values property."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        values_data = [["val1"], ["val2"]]
        append_data = {"type": "fixed", "values": values_data}

        merged = table_cfg.create_append_config(append_data)

        assert merged["values"] == values_data

    def test_create_append_config_inherits_type(self):
        """Test that append config inherits type from parent."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "type": "data",
                "columns": [],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {}

        merged = table_cfg.create_append_config(append_data)

        assert merged["type"] == "data"

    def test_create_append_config_can_override_type(self):
        """Test that append config can override type."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "type": "data",
                "columns": [],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")
        append_data = {"type": "fixed"}

        merged = table_cfg.create_append_config(append_data)

        assert merged["type"] == "fixed"


class TestAppendEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_append_list(self):
        """Test entity with empty append list."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert table_cfg.has_append is False
        assert table_cfg.append_configs == []

    def test_append_none_treated_as_empty(self):
        """Test that append: null is treated as no append."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": [],
                "depends_on": [],
                "append": None,
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        assert table_cfg.has_append is False
        assert table_cfg.append_configs == []


class TestGetSubTablesConfigs:
    """Test get_configured_tables() method."""

    def test_base_only_no_append(self):
        """Test entity without append returns only base config."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["id", "name"],
                "depends_on": [],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        assert len(tables) == 1
        assert tables[0]._data == table_cfg._data
        assert tables[0] is table_cfg

    def test_base_plus_one_append(self):
        """Test entity with one append returns base + append config."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["id", "name"],
                "depends_on": [],
                "append": [{"type": "fixed", "values": ["A", "B"]}],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        assert len(tables) == 2
        assert tables[0].entity_name == "test_entity"
        assert tables[0]._data == table_cfg._data

        assert tables[1].entity_name == "test_entity__append_0"
        assert tables[1]._data == {
            "surrogate_id": "test_id",
            "values": ["A", "B"],
            "type": "fixed",
            "columns": ["id", "name"],
        }

    def test_base_plus_multiple_append(self):
        """Test entity with multiple append items."""
        cfg = {
            "source_entity": {
                "surrogate_id": "src_id",
                "columns": ["id", "name"],
                "depends_on": [],
            },
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["id", "name"],
                "depends_on": [],
                "append": [
                    {"type": "fixed", "values": ["A", "B"]},
                    {"type": "data", "source": "source_entity"},
                    {"type": "sql", "data_source": "db", "values": "SELECT * FROM table"},
                ],
            },
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        assert len(tables) == 4
        assert tables[0].entity_name == "test_entity"
        assert tables[1].entity_name == "test_entity__append_0"
        assert tables[2].entity_name == "test_entity__append_1"
        assert tables[3].entity_name == "test_entity__append_2"

    def test_append_config_inherits_keys(self):
        """Test that append configs inherit keys from parent."""
        cfg = {
            "test_entity": {
                "keys": ["parent_key1", "parent_key2"],
                "surrogate_id": "test_id",
                "columns": ["col1", "col2"],
                "depends_on": [],
                "append": [{"type": "fixed", "values": ["A"]}],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        append_cfg = tables[1]

        assert set(append_cfg.keys) == {"parent_key1", "parent_key2"}

    def test_append_config_inherits_surrogate_id(self):
        """Test that append configs inherit surrogate_id from parent."""
        cfg = {
            "test_entity": {
                "surrogate_id": "parent_surrogate",
                "columns": ["id", "name"],
                "depends_on": [],
                "append": [{"type": "fixed", "values": ["A"]}],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        append_cfg = tables[1]

        assert append_cfg.surrogate_id == "parent_surrogate"

    def test_append_config_can_override_columns(self):
        """Test that append configs can override columns."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["a", "b", "c"],
                "depends_on": [],
                "append": [{"type": "fixed", "values": [1,2,3], "columns": ["a", "x", "y"]}],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())
        append_cfg = tables[1]

        assert append_cfg.columns == ["a", "x", "y"]

    def test_append_config_type_inheritance(self):
        """Test that append configs inherit type correctly."""
        cfg = {
            "test_entity": {
                "surrogate_id": "test_id",
                "columns": ["id", "name"],
                "type": "data",  # Parent type
                "depends_on": [],
                "append": [
                    {"values": [1, 2]},  # Should default to parent type
                    {"type": "fixed", "values": [3, 5]},  # Should use explicit type
                ],
            }
        }

        table_cfg = TableConfig(cfg=cfg, entity_name="test_entity")

        tables = list(table_cfg.get_sub_table_configs())

        assert tables[0].type != "fixed"  # Parent
        assert tables[1].type != "fixed"  # Inherits "data" from parent
        assert tables[2].type == "fixed"  # Explicit "fixed"
