"""Tests for entity materialization functionality."""

from src.model import ShapeShiftProject, TableConfig
from src.specifications.materialize import CanMaterializeSpecification


class TestCanMaterializeSpecification:
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
        country: TableConfig = project.get_table("country")
        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=country)

        assert is_satisfied is False
        assert any("already type 'fixed'" in error.message for error in specification.errors)

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
        site: TableConfig = project.get_table("site")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=site)

        assert is_satisfied is False
        # Materialized entities are type 'fixed', so fixed check catches them first
        assert any("already type 'fixed'" in error.message for error in specification.errors)

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
        site: TableConfig = project.get_table("site")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=site)

        assert is_satisfied is True
        assert not specification.has_errors()

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
        sample: TableConfig = project.get_table("sample")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=sample)

        assert is_satisfied is False
        assert any("non-materialized entity 'site'" in error.message for error in specification.errors)

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
        site: TableConfig = project.get_table("site")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=site)

        assert is_satisfied is True
        assert not specification.has_errors()

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
        sample: TableConfig = project.get_table("sample")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=sample)

        assert is_satisfied is False
        assert any("non-existent entity 'site'" in error.message for error in specification.errors)

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
        standalone: TableConfig = project.get_table("standalone")

        specification: CanMaterializeSpecification = CanMaterializeSpecification(project)
        is_satisfied: bool = specification.is_satisfied_by(entity=standalone)

        assert is_satisfied is True
        assert not specification.has_errors()
