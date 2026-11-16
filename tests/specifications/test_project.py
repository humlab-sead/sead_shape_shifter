"""Tests for project-level specifications."""

from datetime import date, datetime
from unittest.mock import Mock

import pytest

from src.specifications.base import ProjectSpecification, SpecificationIssue
from src.specifications.foreign_key import ForeignKeyRemotePublicIdSpecification
from src.specifications.output_expectations import OutputExpectationsSpecification
from src.specifications.project import (
    CircularDependencySpecification,
    CompositeProjectSpecification,
    DataSourceExistsSpecification,
    EntitiesSpecification,
    ForeignKeyValueSourceSpecification,
)


class TestOutputExpectationsSpecification:
    """Tests for output expectation declaration validation."""

    @staticmethod
    def make_spec(expectations, *, entities=None):
        project_cfg = {
            "entities": entities
            or {
                "site": {"type": "sql", "keys": ["site_key"], "columns": ["site_key", "Projekt"]},
                "no_keys": {"type": "fixed", "columns": ["name"], "values": [["one"]]},
                "wide": {
                    "type": "sql",
                    "keys": ["site_key"],
                    "columns": ["site_key", "amount"],
                    "unnest": {
                        "id_vars": ["site_key"],
                        "value_vars": ["amount"],
                        "var_name": "measure",
                        "value_name": "value",
                    },
                },
            },
            "options": {"output_expectations": expectations},
        }
        return OutputExpectationsSpecification(project_cfg)

    def test_accepts_all_metrics_and_comparison_modes(self):
        spec = self.make_spec(
            [
                {"name": "count-equals", "entity": "site", "metric": "row_count", "equals": 7},
                {"name": "count-min", "entity": "site", "metric": "row_count", "min": 1},
                {"name": "count-max", "entity": "site", "metric": "row_count", "max": 8},
                {"name": "count-range", "entity": "site", "metric": "row_count", "min": 1, "max": 8},
                {"name": "key-count", "entity": "site", "metric": "distinct_key_count", "equals": 7},
                {
                    "name": "sites-by-project",
                    "entity": "site",
                    "metric": "grouped_row_count",
                    "column": "Projekt",
                    "groups": {"north": {"equals": 1}, "south": {"min": 1, "max": 4}},
                },
                {
                    "name": "unnested-measures",
                    "entity": "wide",
                    "metric": "grouped_row_count",
                    "column": "measure",
                    "groups": {"amount": {"min": 1}},
                },
            ]
        )

        assert spec.is_satisfied_by() is True
        assert not spec.errors

    def test_accepts_null_group_value(self):
        spec = self.make_spec(
            [
                {
                    "name": "sites-without-project",
                    "entity": "site",
                    "metric": "grouped_row_count",
                    "column": "Projekt",
                    "groups": {None: {"equals": 0}},
                }
            ]
        )

        assert spec.is_satisfied_by() is True
        assert not spec.errors

    def test_accepts_json_scalar_group_values(self):
        spec = self.make_spec(
            [
                {
                    "name": "sites-by-json-value",
                    "entity": "site",
                    "metric": "grouped_row_count",
                    "column": "Projekt",
                    "groups": {
                        "north": {"equals": 0},
                        True: {"equals": 0},
                        42: {"equals": 0},
                        3.5: {"equals": 0},
                        None: {"equals": 0},
                    },
                }
            ]
        )

        assert spec.is_satisfied_by() is True
        assert not spec.errors

    @pytest.mark.parametrize(
        "group_value",
        [
            date(2026, 11, 13),
            datetime(2026, 11, 13, 12, 0),
            b"binary",
            float("nan"),
            float("inf"),
            float("-inf"),
        ],
    )
    def test_rejects_non_json_scalar_group_values(self, group_value):
        spec = self.make_spec(
            [
                {
                    "name": "sites-by-invalid-value",
                    "entity": "site",
                    "metric": "grouped_row_count",
                    "column": "Projekt",
                    "groups": {group_value: {"equals": 0}},
                }
            ]
        )

        assert spec.is_satisfied_by() is False
        issue = next(issue for issue in spec.errors if "JSON scalar" in issue.message)
        assert issue.entity == "site"
        assert issue.field == f"options.output_expectations[0].groups[{group_value!r}]"

    def test_absent_expectations_are_valid(self):
        spec = OutputExpectationsSpecification({"entities": {"site": {}}})

        assert spec.is_satisfied_by() is True
        assert not spec.errors

    @pytest.mark.parametrize(
        ("expectations", "expected_field"),
        [
            ({"name": "bad"}, "options.output_expectations"),
            ([None], "options.output_expectations[0]"),
            ([{"name": "bad", "entity": "missing", "metric": "row_count", "equals": 0}], ".entity"),
            ([{"name": "bad", "entity": "site", "metric": "unsupported", "equals": 0}], ".metric"),
            ([{"name": "bad", "entity": "no_keys", "metric": "distinct_key_count", "equals": 0}], ".metric"),
            (
                [{"name": "bad", "entity": "site", "metric": "grouped_row_count", "column": "unknown", "groups": {"x": {"min": 0}}}],
                ".column",
            ),
            (
                [{"name": "bad", "entity": "wide", "metric": "grouped_row_count", "column": "amount", "groups": {"x": {"min": 0}}}],
                ".column",
            ),
            ([{"name": "bad", "entity": "site", "metric": "row_count"}], "options.output_expectations[0]"),
            (
                [{"name": "bad", "entity": "site", "metric": "grouped_row_count", "column": "Projekt", "groups": {}}],
                ".groups",
            ),
            (
                [{"name": "bad", "entity": "site", "metric": "grouped_row_count", "column": "Projekt", "groups": {"x": {}}}],
                ".groups",
            ),
            (
                [{"name": "bad", "entity": "site", "metric": "row_count", "equals": 0, "column": "Projekt"}],
                ".column",
            ),
        ],
    )
    def test_rejects_invalid_declarations(self, expectations, expected_field):
        spec = self.make_spec(expectations)

        assert spec.is_satisfied_by() is False
        assert spec.errors
        assert any(expected_field in (issue.field or "") for issue in spec.errors)
        assert all(issue.code == "OUTPUT_EXPECTATION_INVALID" for issue in spec.errors)

    @pytest.mark.parametrize("limit", [True, -1, 1.5, None])
    def test_rejects_invalid_numeric_limits(self, limit):
        spec = self.make_spec([{"name": "bad", "entity": "site", "metric": "row_count", "equals": limit}])

        assert spec.is_satisfied_by() is False
        assert any(issue.field == "options.output_expectations[0].equals" for issue in spec.errors)

    def test_rejects_conflicting_bounds_and_reversed_ranges(self):
        for comparison in (
            {"equals": 1, "min": 1},
            {"min": 5, "max": 2},
            {"min": 0, "extra": 1},
        ):
            spec = self.make_spec([{"name": "bad", "entity": "site", "metric": "row_count", **comparison}])

            assert spec.is_satisfied_by() is False
            assert spec.errors

    def test_rejects_duplicate_names_and_invalid_metric_shape(self):
        spec = self.make_spec(
            [
                {"name": "same", "entity": "site", "metric": "row_count", "equals": 1},
                {"name": "same", "entity": "site", "metric": "row_count", "equals": 1},
                {"name": "bad-metric", "entity": "site", "metric": [], "equals": 1},
            ]
        )

        assert spec.is_satisfied_by() is False
        assert any(issue.field.endswith(".name") for issue in spec.errors if issue.field)
        assert any(issue.field.endswith(".metric") for issue in spec.errors if issue.field)


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


class TestForeignKeyValueSourceSpecification:
    """Tests for direct target-model FK value-source declarations."""

    def test_rejects_non_map_and_unsupported_value_sources_with_codes(self):
        for declaration in ([], {"location_type": "external_id"}, {"location_type": {"source": "public_id"}}):
            specification = ForeignKeyValueSourceSpecification(
                {
                    "metadata": {"type": "shapeshifter-project", "target_model": {"entities": {}}},
                    "entities": {"location": {"foreign_key_value_sources": declaration}},
                }
            )

            assert specification.is_satisfied_by() is False
            assert specification.errors[0].code == "DIRECT_FK_VALUE_SOURCE_INVALID"
            assert specification.errors[0].entity == "location"
            assert specification.errors[0].field is not None
            assert specification.errors[0].field.startswith("foreign_key_value_sources")

    def test_nonempty_map_requires_target_model(self):
        specification = ForeignKeyValueSourceSpecification(
            {
                "metadata": {"type": "shapeshifter-project"},
                "entities": {"location": {"foreign_key_value_sources": {"location_type": "public_id"}}},
            }
        )

        assert specification.is_satisfied_by() is False
        assert [(issue.code, issue.entity, issue.field) for issue in specification.errors] == [
            ("DIRECT_FK_TARGET_MODEL_REQUIRED", "location", "metadata.target_model")
        ]

    def test_empty_or_absent_map_keeps_target_model_optional(self):
        for entity_cfg in ({}, {"foreign_key_value_sources": {}}):
            specification = ForeignKeyValueSourceSpecification(
                {"metadata": {"type": "shapeshifter-project"}, "entities": {"location": entity_cfg}}
            )

            assert specification.is_satisfied_by() is True
            assert not specification.errors

    def test_composite_project_specification_runs_value_source_check(self):
        project = CompositeProjectSpecification(
            {
                "metadata": {"type": "shapeshifter-project"},
                "entities": {"location": {"foreign_key_value_sources": {"location_type": "public_id"}}},
            }
        )

        assert project.is_satisfied_by() is False
        assert any(issue.code == "DIRECT_FK_TARGET_MODEL_REQUIRED" for issue in project.errors)


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
                    "columns": ["id", "col1"],
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

    def test_composite_validation_reports_misspelled_fk_key(self):
        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "parent": {
                    "type": "entity",
                    "columns": ["ref_id"],
                    "keys": ["ref_id"],
                    "public_id": "parent_id",
                },
                "child": {
                    "type": "entity",
                    "columns": ["parent_ref"],
                    "keys": ["parent_ref"],
                    "public_id": "child_id",
                    "foreign_keys": [
                        {
                            "entity": "parent",
                            "local_keys": ["parent_ref"],
                            "remote_keys": ["ref_id"],
                            "contraints": {"cardinality": "many_to_one"},
                        }
                    ],
                },
            },
        }
        spec = CompositeProjectSpecification(project_cfg)

        assert spec.is_satisfied_by() is False
        issue = next(issue for issue in spec.errors if issue.field == "foreign_keys[0].contraints")
        assert issue.entity == "child"
        assert "foreign key #1" in issue.message

    def test_composite_validation_reports_invalid_output_expectations(self, valid_project_cfg):
        project_cfg = {
            **valid_project_cfg,
            "options": {
                **valid_project_cfg["options"],
                "output_expectations": [{"name": "missing-site", "entity": "missing", "metric": "row_count", "equals": 0}],
            },
        }
        spec = CompositeProjectSpecification(project_cfg)

        assert spec.is_satisfied_by() is False
        assert any(issue.code == "OUTPUT_EXPECTATION_INVALID" for issue in spec.errors)

    def test_default_specifications_used(self, valid_project_cfg):
        """Test that default specifications are used."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        assert len(spec.specifications) > 0
        assert any(isinstance(s, EntitiesSpecification) for s in spec.specifications)
        assert any(isinstance(s, OutputExpectationsSpecification) for s in spec.specifications)
        assert any(isinstance(s, CircularDependencySpecification) for s in spec.specifications)
        assert any(isinstance(s, DataSourceExistsSpecification) for s in spec.specifications)

    def test_get_default_specifications(self, valid_project_cfg):
        """Test get_default_specifications returns proper list."""
        spec = CompositeProjectSpecification(valid_project_cfg)

        specs: list[ProjectSpecification] = spec.get_default_specifications()

        assert isinstance(specs, list)
        assert len(specs) == 7
        assert any(isinstance(s, OutputExpectationsSpecification) for s in specs)
        assert any(isinstance(s, ForeignKeyValueSourceSpecification) for s in specs)
        assert any(isinstance(s, ForeignKeyRemotePublicIdSpecification) for s in specs)

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
