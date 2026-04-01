"""Tests for merged entity configuration parsing."""

from src.model import TableConfig


class TestMergedEntityConfig:
    """Test merged entity configuration support."""

    def test_merged_entity_type_recognized(self):
        """Test that type='merged' is recognized."""
        config = {
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "system_id": "system_id",
                "branches": [
                    {"name": "abundance", "source": "abundance"},
                    {"name": "relative_dating", "source": "_analysis_entity_relative_dating"},
                ],
            }
        }

        table_cfg = TableConfig(entities_cfg=config, entity_name="analysis_entity")

        assert table_cfg.type == "merged"
        assert table_cfg.public_id == "analysis_entity_id"

    def test_branches_property_returns_list(self):
        """Test that branches property returns list of branch configs."""
        config = {
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "branches": [
                    {"name": "abundance", "source": "abundance", "keys": ["sample_id"]},
                    {"name": "relative_dating", "source": "_analysis_entity_relative_dating", "keys": []},
                ],
            }
        }

        table_cfg = TableConfig(entities_cfg=config, entity_name="analysis_entity")

        assert len(table_cfg.branches) == 2
        assert table_cfg.branches[0]["name"] == "abundance"
        assert table_cfg.branches[0]["source"] == "abundance"
        assert table_cfg.branches[0]["keys"] == ["sample_id"]
        assert table_cfg.branches[1]["name"] == "relative_dating"

    def test_branches_empty_for_non_merged_entity(self):
        """Test that branches is empty for non-merged entities."""
        config = {
            "sample_type": {
                "type": "fixed",
                "values": [["Soil"], ["Core"]],
            }
        }

        table_cfg = TableConfig(entities_cfg=config, entity_name="sample_type")

        assert table_cfg.type == "fixed"
        assert table_cfg.branches == []

    def test_depends_on_includes_branch_sources(self):
        """Test that depends_on includes branch source entities."""
        config = {
            "abundance": {"type": "entity", "data_source": "clearinghouse"},
            "_analysis_entity_relative_dating": {"type": "entity", "data_source": "clearinghouse"},
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "branches": [
                    {"name": "abundance", "source": "abundance"},
                    {"name": "relative_dating", "source": "_analysis_entity_relative_dating"},
                ],
            },
        }

        table_cfg = TableConfig(entities_cfg=config, entity_name="analysis_entity")

        depends_on = table_cfg.depends_on

        assert "abundance" in depends_on
        assert "_analysis_entity_relative_dating" in depends_on
        assert len(depends_on) == 2  # Only branch sources, no other dependencies

    def test_merged_entity_with_foreign_keys_and_branches(self):
        """Test that merged entity can have both foreign keys and branches."""
        config = {
            "location": {"type": "fixed", "values": [["Norway"]], "public_id": "location_id"},
            "abundance": {"type": "entity", "data_source": "clearinghouse"},
            "_analysis_entity_relative_dating": {"type": "entity", "data_source": "clearinghouse"},
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "branches": [
                    {"name": "abundance", "source": "abundance"},
                    {"name": "relative_dating", "source": "_analysis_entity_relative_dating"},
                ],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
            },
        }

        table_cfg = TableConfig(entities_cfg=config, entity_name="analysis_entity")

        depends_on = table_cfg.depends_on

        # Should include both branch sources and FK dependencies
        assert "abundance" in depends_on
        assert "_analysis_entity_relative_dating" in depends_on
        assert "location" in depends_on
        assert len(depends_on) == 3
