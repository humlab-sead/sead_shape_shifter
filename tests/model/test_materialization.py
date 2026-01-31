"""Tests for entity materialization functionality."""

from src.model import TableConfig
from src.model import ShapeShiftProject


class TestMaterializationConfig:
    """Test MaterializationConfig model."""

    def test_is_materialized_property(self):
        """Test is_materialized property."""
        # Non-materialized entity
        project_cfg = {
            "project_name": "test",
            "entities": {
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM sites",
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        site: TableConfig = project.get_table("site")
        assert site.is_materialized is False

        # Materialized entity
        project_cfg_mat = {
            "project_name": "test",
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"]],
                    "materialized": {"enabled": True, "source_state": {}},
                },
            },
        }
        project_mat = ShapeShiftProject(cfg=project_cfg_mat)
        site_mat: TableConfig = project_mat.get_table("site")
        assert site_mat.is_materialized is True

    def test_materialized_property_returns_config(self):
        """Test materialized property returns MaterializationConfig."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"]],
                    "materialized": {
                        "enabled": True,
                        "source_state": {"type": "sql", "query": "SELECT * FROM sites"},
                        "materialized_at": "2026-01-29T12:00:00Z",
                        "materialized_by": "test@example.com",
                        "data_file": "materialized/site.parquet",
                    },
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        site: TableConfig = project.get_table("site")

        mat_config = site.materialized
        assert mat_config.enabled is True
        assert mat_config.source_state == {"type": "sql", "query": "SELECT * FROM sites"}
        assert mat_config.materialized_at == "2026-01-29T12:00:00Z"
        assert mat_config.materialized_by == "test@example.com"
        assert mat_config.data_file == "materialized/site.parquet"
