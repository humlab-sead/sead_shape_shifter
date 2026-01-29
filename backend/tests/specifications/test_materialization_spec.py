"""Tests for MaterializationSpecification validator."""


from src.specifications.entity import MaterializationSpecification


class TestMaterializationSpecification:
    """Test MaterializationSpecification validator."""

    def test_non_materialized_entity_passes_validation(self):
        """Non-materialized entities should pass (specification is optional)."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM sites",
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert not spec.has_errors()

    def test_materialized_entity_disabled_passes_validation(self):
        """Entity with materialized.enabled=false should pass."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"]],
                    "materialized": {"enabled": False},
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert not spec.has_errors()

    def test_materialized_entity_must_be_fixed_type(self):
        """Materialized entity must have type='fixed'."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "sql",  # Wrong type!
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "data_source": "test_db",
                    "query": "SELECT * FROM sites",
                    "materialized": {"enabled": True, "source_state": {}},
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is False
        assert spec.has_errors()
        errors = [err.message for err in spec.errors]
        assert any("must have type='fixed'" in err for err in errors)

    def test_materialized_entity_must_have_values_or_data_file(self):
        """Materialized entity must have either values or data_file."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    # Missing values and data_file!
                    "materialized": {"enabled": True, "source_state": {}},
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is False
        assert spec.has_errors()
        errors = [err.message for err in spec.errors]
        assert any("must have either 'values' or 'materialized.data_file'" in err for err in errors)

    def test_materialized_entity_with_values_passes(self):
        """Materialized entity with inline values passes."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"], [2, "Site B"]],
                    "materialized": {"enabled": True, "source_state": {"type": "sql", "query": "SELECT * FROM sites"}},
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert not spec.has_errors()

    def test_materialized_entity_with_data_file_passes(self):
        """Materialized entity with data_file passes."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": "@file:materialized/site.parquet",
                    "materialized": {
                        "enabled": True,
                        "source_state": {"type": "sql", "query": "SELECT * FROM sites"},
                        "data_file": "materialized/site.parquet",
                    },
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert not spec.has_errors()

    def test_materialized_entity_must_have_source_state(self):
        """Materialized entity must have source_state for unmaterialization."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"]],
                    "materialized": {
                        "enabled": True,
                        # Missing source_state!
                    },
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is False
        assert spec.has_errors()
        errors = [err.message for err in spec.errors]
        assert any("must have 'materialized.source_state'" in err for err in errors)

    def test_materialized_entity_should_have_metadata_fields(self):
        """Materialized entity should have metadata fields (warning only)."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_id", "site_name"],
                    "values": [[1, "Site A"]],
                    "materialized": {
                        "enabled": True,
                        "source_state": {"type": "sql"},
                        # Missing materialized_at and materialized_by
                    },
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        # Should pass (warnings only)
        assert result is True
        assert not spec.has_errors()
        assert spec.has_warnings()
        warnings = [warn.message for warn in spec.warnings]
        assert any("should have 'materialized_at'" in warn for warn in warnings)
        assert any("should have 'materialized_by'" in warn for warn in warnings)

    def test_fully_configured_materialized_entity_passes(self):
        """Fully configured materialized entity passes without warnings."""
        project_cfg = {
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
                }
            }
        }
        spec = MaterializationSpecification(project_cfg)

        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert not spec.has_errors()
        assert not spec.has_warnings()
