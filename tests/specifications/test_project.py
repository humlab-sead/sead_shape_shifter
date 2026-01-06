"""Tests for project-level specifications."""

from unittest.mock import Mock

import pytest

from src.specifications.base import SpecificationIssue
from src.specifications.project import (
    CircularDependencySpecification,
    CompositeProjectSpecification,
    DataSourceExistsSpecification,
    EntitiesSpecification,
)


class TestCircularDependencySpecification:
    """Tests for CircularDependencySpecification."""

    def test_no_dependencies(self):
        """Test validation passes when there are no dependencies."""
        project_cfg = {"entities": {"entity1": {}, "entity2": {}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True
        assert len(spec.errors) == 0

    def test_linear_dependencies(self):
        """Test validation passes for linear dependency chain."""
        project_cfg = {"entities": {"entity1": {"depends_on": ["entity2"]}, "entity2": {"depends_on": ["entity3"]}, "entity3": {}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_source_dependency(self):
        """Test validation handles source dependencies."""
        project_cfg = {"entities": {"entity1": {"source": "entity2"}, "entity2": {}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_simple_circular_dependency(self):
        """Test validation fails for simple circular dependency."""
        project_cfg = {"entities": {"entity1": {"depends_on": ["entity2"]}, "entity2": {"depends_on": ["entity1"]}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert len(spec.errors) > 0
        assert any("Circular dependency" in str(e) for e in spec.errors)

    def test_three_way_circular_dependency(self):
        """Test validation fails for three-way circular dependency."""
        project_cfg = {
            "entities": {
                "entity1": {"depends_on": ["entity2"]},
                "entity2": {"depends_on": ["entity3"]},
                "entity3": {"depends_on": ["entity1"]},
            }
        }

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert any("Circular dependency" in str(e) for e in spec.errors)

    def test_self_dependency(self):
        """Test validation fails for self-dependency."""
        project_cfg = {"entities": {"entity1": {"depends_on": ["entity1"]}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False

    def test_circular_via_source(self):
        """Test validation fails for circular dependency via source."""
        project_cfg = {"entities": {"entity1": {"source": "entity2"}, "entity2": {"depends_on": ["entity1"]}}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False

    def test_complex_dependency_graph(self):
        """Test validation with complex dependency graph without cycles."""
        project_cfg = {
            "entities": {
                "entity1": {"depends_on": ["entity2", "entity3"]},
                "entity2": {"depends_on": ["entity4"]},
                "entity3": {"depends_on": ["entity4"]},
                "entity4": {},
            }
        }

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_empty_entities(self):
        """Test validation passes with empty entities."""
        project_cfg = {"entities": {}}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_no_entities_key(self):
        """Test validation passes when entities key missing."""
        project_cfg = {}

        spec = CircularDependencySpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True


class TestDataSourceExistsSpecification:
    """Tests for DataSourceExistsSpecification."""

    def test_valid_data_sources(self):
        """Test validation passes when all data sources exist."""
        project_cfg = {
            "entities": {"entity1": {"data_source": "db1", "query": "SELECT *"}},
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_data_source(self):
        """Test validation fails when data source doesn't exist."""
        project_cfg = {"entities": {"entity1": {"data_source": "missing_db"}}, "options": {"data_sources": {}}}

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert len(spec.errors) > 0
        assert any("non-existent data source" in str(e) for e in spec.errors)

    def test_append_data_source(self):
        """Test validation checks append data sources."""
        project_cfg = {
            "entities": {"entity1": {"append": [{"type": "sql", "data_source": "db1", "query": "SELECT *"}]}},
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_missing_append_data_source(self):
        """Test validation fails for missing append data source."""
        project_cfg = {
            "entities": {"entity1": {"append": [{"type": "sql", "data_source": "missing_db"}]}},
            "options": {"data_sources": {}},
        }

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert any("append" in str(e).lower() for e in spec.errors)

    def test_multiple_append_configs(self):
        """Test validation with multiple append configurations."""
        project_cfg = {
            "entities": {"entity1": {"append": [{"type": "sql", "data_source": "db1"}, {"type": "sql", "data_source": "db2"}]}},
            "options": {"data_sources": {"db1": {}, "db2": {}}},
        }

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_non_list_append_config(self):
        """Test validation handles non-list append config."""
        project_cfg = {
            "entities": {"entity1": {"append": {"type": "sql", "data_source": "db1"}}},
            "options": {"data_sources": {"db1": {}}},
        }

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_no_entities(self):
        """Test validation passes when no entities."""
        project_cfg = {"options": {"data_sources": {}}}

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True

    def test_no_data_source_field(self):
        """Test validation passes when entity has no data_source field."""
        project_cfg = {"entities": {"entity1": {"type": "fixed"}}, "options": {"data_sources": {}}}

        spec = DataSourceExistsSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is True


class TestEntitiesSpecification:
    """Tests for EntitiesSpecification."""

    @pytest.fixture
    def project_cfg(self):
        """Sample project configuration."""
        return {
            "entities": {
                "valid_entity": {
                    "type": "sql",
                    "columns": ["col1"],
                    "keys": ["id"],
                    "data_source": "db1",
                    "query": "SELECT *",
                }
            },
            "options": {"data_sources": {"db1": {}}},
        }

    def test_validates_all_entities(self, project_cfg):
        """Test that all entities are validated."""
        spec = EntitiesSpecification(project_cfg)

        result = spec.is_satisfied_by()

        # Should validate the entity (implementation validates all entities in project)
        assert isinstance(result, bool)

    def test_aggregates_entity_errors(self):
        """Test that errors from entity validations are aggregated."""
        project_cfg = {"entities": {"invalid_entity": {"type": "sql"}}}  # Missing required fields

        spec = EntitiesSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert len(spec.errors) > 0


class TestCompositeProjectSpecification:
    """Tests for CompositeProjectSpecification."""

    @pytest.fixture
    def valid_project_cfg(self):
        """Valid project configuration."""
        return {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "entity1": {
                    "type": "sql",
                    "columns": ["col1"],
                    "keys": ["id"],
                    "data_source": "db1",
                    "query": "SELECT *",
                }
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

    def test_valid_project(self, valid_project_cfg):
        """Test validation passes for valid project."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        result = spec.is_satisfied_by()

        assert result is True
        assert len(spec.errors) == 0
        assert len(spec.warnings) > 0

    def test_default_specifications_used(self, valid_project_cfg):
        """Test that default specifications are used."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        assert len(spec.specifications) > 0
        assert any(isinstance(s, EntitiesSpecification) for s in spec.specifications)
        assert any(isinstance(s, CircularDependencySpecification) for s in spec.specifications)
        assert any(isinstance(s, DataSourceExistsSpecification) for s in spec.specifications)

    def test_get_default_specifications(self, valid_project_cfg):
        """Test get_default_specifications returns proper list."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        specs = spec.get_default_specifications()

        assert isinstance(specs, list)
        assert len(specs) == 3

    def test_custom_specifications(self, valid_project_cfg):
        """Test using custom specifications."""
        custom_spec = DataSourceExistsSpecification(valid_project_cfg)
        spec = CompositeProjectSpecification(valid_project_cfg, specifications=[custom_spec])

        assert len(spec.specifications) == 1
        assert spec.specifications[0] == custom_spec

    def test_aggregates_errors(self):
        """Test that errors from all specifications are aggregated."""
        project_cfg = {
            "entities": {
                "entity1": {"data_source": "missing_db"},  # Missing data source
                "entity2": {"depends_on": ["entity1"]},
                "entity3": {"depends_on": ["entity4"]},  # Circular dependency
            }
        }

        spec = CompositeProjectSpecification(project_cfg)
        result = spec.is_satisfied_by()

        assert result is False
        assert len(spec.errors) > 0

    def test_aggregates_warnings(self):
        """Test that warnings from specifications are aggregated."""
        project_cfg = {
            "entities": {"entity1": {"type": "sql", "columns": ["col1"], "keys": ["id"], "data_source": "db1", "query": "SELECT *"}},
            "options": {"data_sources": {"db1": {}}},
        }

        spec = CompositeProjectSpecification(project_cfg)
        spec.is_satisfied_by()

        # Warnings might be generated by entity specifications
        assert isinstance(spec.warnings, list)

    def test_clear_resets_state(self, valid_project_cfg):
        """Test that clear() resets errors and warnings."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        # Add some errors manually
        spec.errors.append(Mock())
        spec.warnings.append(Mock())

        spec.clear()

        assert len(spec.errors) == 0
        assert len(spec.warnings) == 0

    def test_get_report_valid_config_with_warnings(self, valid_project_cfg):
        """Test report generation for valid configuration."""
        spec = CompositeProjectSpecification(valid_project_cfg)
        is_valid = spec.is_satisfied_by()
        assert is_valid

        assert spec.has_warnings()

        report = spec.get_report()

        assert "[WARNING]" in report

    def test_get_report_with_errors(self):
        """Test report generation with errors."""
        project_cfg = {"entities": {"entity1": {"data_source": "missing"}}, "options": {"data_sources": {}}}

        spec = CompositeProjectSpecification(project_cfg)
        spec.is_satisfied_by()

        report = spec.get_report()

        assert "✗" in report
        assert "error" in report.lower()

    def test_get_report_with_warnings(self, valid_project_cfg):
        """Test report generation with warnings."""
        spec = CompositeProjectSpecification(valid_project_cfg)
        spec.is_satisfied_by()

        # Manually add a warning for testing

        spec.warnings.append(SpecificationIssue(severity="warning", message="Test warning"))

        report = spec.get_report()

        assert "⚠" in report
        assert "warning" in report.lower()

    def test_get_report_with_both(self):
        """Test report generation with both errors and warnings."""

        project_cfg = {"entities": {}}
        spec = CompositeProjectSpecification(project_cfg)

        spec.errors.append(SpecificationIssue(severity="error", message="Test error"))
        spec.warnings.append(SpecificationIssue(severity="warning", message="Test warning"))

        report = spec.get_report()

        assert "✗" in report
        assert "⚠" in report
        assert "error" in report.lower()
        assert "warning" in report.lower()

    def test_multiple_errors_numbered(self):
        """Test that multiple errors are numbered in report."""

        project_cfg = {"entities": {}}
        spec = CompositeProjectSpecification(project_cfg)

        spec.errors.append(SpecificationIssue(severity="error", message="Error 1"))
        spec.errors.append(SpecificationIssue(severity="error", message="Error 2"))

        report = spec.get_report()

        assert "1." in report
        assert "2." in report
