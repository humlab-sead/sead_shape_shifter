"""Tests for entity materialization functionality."""


from src.model import ShapeShiftProject


class TestCanMaterialize:
    """Test TableConfig.can_materialize() validation logic."""

    def test_fixed_entity_cannot_be_materialized(self):
        """Fixed entities cannot be materialized (already frozen)."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "country": {
                    "type": "fixed",
                    "public_id": "country_id",
                    "keys": ["country_name"],
                    "columns": ["country_id", "country_name"],
                    "values": [[1, "Sweden"], [2, "Norway"]],
                }
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        country = project.get_table("country")

        can_mat, errors = country.can_materialize(project)

        assert can_mat is False
        assert "already type 'fixed'" in errors[0]

    def test_already_materialized_entity_cannot_be_rematerialized(self):
        """Materialized entities cannot be materialized again (caught by fixed type check)."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"], [2, "Site B"]],
                    "materialized": {
                        "enabled": True,
                        "source_state": {"type": "sql", "query": "SELECT * FROM sites"},
                        "materialized_at": "2026-01-29T12:00:00Z",
                    },
                }
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        site = project.get_table("site")

        can_mat, errors = site.can_materialize(project)

        assert can_mat is False
        # Materialized entities are type 'fixed', so fixed check catches them first
        assert "already type 'fixed'" in errors[0]

    def test_sql_entity_with_fixed_dependencies_can_be_materialized(self):
        """SQL entity depending on fixed entities can be materialized."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "country": {
                    "type": "fixed",
                    "public_id": "country_id",
                    "keys": ["country_name"],
                    "columns": ["country_id", "country_name"],
                    "values": [[1, "Sweden"]],
                },
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM sites",
                    "foreign_keys": [{"entity": "country", "local_keys": ["country_name"], "remote_keys": ["country_name"]}],
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        site = project.get_table("site")

        can_mat, errors = site.can_materialize(project)

        assert can_mat is True
        assert errors == []

    def test_entity_with_non_materialized_dependencies_cannot_be_materialized(self):
        """Entity depending on non-materialized dynamic entities cannot be materialized."""
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
                "sample": {
                    "type": "sql",
                    "public_id": "sample_id",
                    "keys": ["sample_code"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM samples",
                    "foreign_keys": [{"entity": "site", "local_keys": ["site_name"], "remote_keys": ["site_name"]}],
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        sample = project.get_table("sample")

        can_mat, errors = sample.can_materialize(project)

        assert can_mat is False
        assert any("non-materialized entity 'site'" in err for err in errors)

    def test_entity_with_materialized_dependencies_can_be_materialized(self):
        """Entity depending on materialized entities can be materialized."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "country": {
                    "type": "fixed",
                    "public_id": "country_id",
                    "keys": ["country_name"],
                    "columns": ["country_id", "country_name"],
                    "values": [[1, "Sweden"]],
                    "materialized": {
                        "enabled": True,
                        "source_state": {"type": "sql", "query": "SELECT * FROM countries"},
                    },
                },
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM sites",
                    "foreign_keys": [{"entity": "country", "local_keys": ["country_name"], "remote_keys": ["country_name"]}],
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        site = project.get_table("site")

        can_mat, errors = site.can_materialize(project)

        assert can_mat is True
        assert errors == []

    def test_non_existent_fk_dependency_prevents_materialization(self):
        """Entity with foreign key to non-existent entity cannot be materialized."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "sample": {
                    "type": "sql",
                    "public_id": "sample_id",
                    "keys": ["sample_code"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM samples",
                    "foreign_keys": [{"entity": "site", "local_keys": ["site_name"], "remote_keys": ["site_name"]}],  # site doesn't exist
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        sample = project.get_table("sample")

        can_mat, errors = sample.can_materialize(project)

        assert can_mat is False
        assert any("non-existent entity 'site'" in err for err in errors)

    def test_entity_without_dependencies_can_be_materialized(self):
        """SQL entity without dependencies can be materialized."""
        project_cfg = {
            "project_name": "test",
            "entities": {
                "standalone": {
                    "type": "sql",
                    "public_id": "standalone_id",
                    "keys": ["code"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM standalone_table",
                },
            },
        }
        project = ShapeShiftProject(cfg=project_cfg)
        standalone = project.get_table("standalone")

        can_mat, errors = standalone.can_materialize(project)

        assert can_mat is True
        assert errors == []


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
        site = project.get_table("site")
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
        site_mat = project_mat.get_table("site")
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
        site = project.get_table("site")

        mat_config = site.materialized
        assert mat_config.enabled is True
        assert mat_config.source_state == {"type": "sql", "query": "SELECT * FROM sites"}
        assert mat_config.materialized_at == "2026-01-29T12:00:00Z"
        assert mat_config.materialized_by == "test@example.com"
        assert mat_config.data_file == "materialized/site.parquet"
