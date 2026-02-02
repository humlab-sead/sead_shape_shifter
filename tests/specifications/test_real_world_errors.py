"""Integration test using real-world error scenarios from a.log."""

import pytest

from src.specifications.project import CompositeProjectSpecification


class TestRealWorldErrorScenarios:
    """Test that new validators catch the actual errors from production logs."""

    def test_abundance_property_unnest_error(self):
        """Test: abundance_property[unnesting]: Cannot unnest entity, missing `id_vars` columns: ['abundance_id']"""

        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "abundance_property": {
                    "type": "sql",
                    "columns": ["property_type", "value"],  # Missing abundance_id!
                    "keys": ["property_type"],
                    "data_source": "db1",
                    "query": "SELECT * FROM abundance_property",
                    "unnest": {
                        "id_vars": ["abundance_id"],  # ❌ Not in columns!
                        "value_vars": ["value"],
                        "var_name": "property",
                        "value_name": "property_value",
                    },
                }
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should fail validation
        assert result is False
        assert len(validator.errors) > 0

        # Check specific error
        unnest_errors = [e for e in validator.errors if e.entity_name == "abundance_property" and "id_vars" in e.message]
        assert len(unnest_errors) > 0
        assert "abundance_id" in unnest_errors[0].message
        assert "missing id_vars columns" in unnest_errors[0].message

    def test_dataset_contacts_foreign_key_error(self):
        """Test: dataset_contacts[linking]: local keys {'contact_name'} not found in local entity data"""

        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "dataset_contacts": {
                    "type": "sql",
                    "columns": ["dataset_id", "contact_id"],  # Missing contact_name!
                    "keys": ["dataset_id", "contact_id"],
                    "data_source": "db1",
                    "query": "SELECT * FROM dataset_contacts",
                    "foreign_keys": [
                        {
                            "entity": "contact",
                            "local_keys": ["contact_name"],  # ❌ Not in columns!
                            "remote_keys": ["contact_name"],
                        }
                    ],
                },
                "contact": {
                    "type": "sql",
                    "columns": ["contact_name", "email"],
                    "keys": ["contact_name"],
                    "data_source": "db1",
                    "query": "SELECT * FROM contact",
                },
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should fail validation
        assert result is False
        assert len(validator.errors) > 0

        # Check specific error
        fk_errors = [e for e in validator.errors if e.entity_name == "dataset_contacts" and "local_keys" in e.message]
        assert len(fk_errors) > 0
        assert "contact_name" in fk_errors[0].message
        assert "missing local_keys" in fk_errors[0].message

    def test_abundance_property_type_duplicate_keys_warning(self):
        """Test: abundance_property_type[keys]: DUPLICATE KEYS FOUND FOR KEYS {'abundance_property_type_id'}"""

        # Note: Actual duplicate detection requires data, but we can catch config issues
        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "abundance_property_type": {
                    "type": "sql",
                    "columns": ["name", "description"],
                    "keys": ["abundance_property_type_id"],  # Not in columns - warning!
                    "data_source": "db1",
                    "query": "SELECT * FROM abundance_property_type",
                }
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should pass (warnings don't fail validation)
        assert result is True

        # But should have warnings
        assert len(validator.warnings) > 0
        key_warnings = [w for w in validator.warnings if w.entity_name == "abundance_property_type"]
        assert len(key_warnings) > 0

    def test_location_unnest_error(self):
        """Test: location[unnesting]: Cannot unnest entity, missing `id_vars` columns: ['location_id']"""

        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "location": {
                    "type": "sql",
                    "columns": ["location_name", "country"],  # Missing location_id!
                    "keys": ["location_name"],
                    "data_source": "db1",
                    "query": "SELECT * FROM location",
                    "unnest": {
                        "id_vars": ["location_id"],  # ❌ Not in columns!
                        "value_vars": ["country"],
                        "var_name": "attribute",
                        "value_name": "value",
                    },
                }
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should fail validation
        assert result is False
        assert len(validator.errors) > 0

        # Check specific error
        unnest_errors = [e for e in validator.errors if e.entity_name == "location" and "id_vars" in e.message]
        assert len(unnest_errors) > 0
        assert "location_id" in unnest_errors[0].message

    def test_all_errors_combined(self):
        """Test multiple errors caught in single validation pass."""

        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "abundance_property": {
                    "type": "sql",
                    "columns": ["value"],
                    "data_source": "db1",
                    "query": "SELECT * FROM abundance_property",
                    "unnest": {
                        "id_vars": ["abundance_id"],  # ❌ Missing
                        "value_vars": ["value"],
                    },
                },
                "dataset_contacts": {
                    "type": "sql",
                    "columns": ["dataset_id"],
                    "data_source": "db1",
                    "query": "SELECT * FROM dataset_contacts",
                    "foreign_keys": [
                        {
                            "entity": "contact",
                            "local_keys": ["contact_name"],  # ❌ Missing
                            "remote_keys": ["contact_name"],
                        }
                    ],
                },
                "contact": {
                    "type": "sql",
                    "columns": ["contact_name"],
                    "data_source": "db1",
                    "query": "SELECT * FROM contact",
                },
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should fail validation
        assert result is False
        assert len(validator.errors) >= 2

        # Check we have both types of errors
        entity_names_with_errors = {e.entity_name for e in validator.errors}
        assert "abundance_property" in entity_names_with_errors
        assert "dataset_contacts" in entity_names_with_errors

    def test_fixed_after_correction(self):
        """Test that errors are fixed when configuration is corrected."""

        # Original broken config
        project_cfg = {
            "metadata": {"type": "shapeshifter-project"},
            "entities": {
                "abundance_property": {
                    "type": "sql",
                    "columns": ["abundance_id", "value"],  # ✅ Now includes abundance_id
                    "keys": ["abundance_id"],
                    "data_source": "db1",
                    "query": "SELECT * FROM abundance_property",
                    "unnest": {
                        "id_vars": ["abundance_id"],  # ✅ Now valid
                        "value_vars": ["value"],
                        "var_name": "property",
                        "value_name": "property_value",
                    },
                },
                "dataset_contacts": {
                    "type": "sql",
                    "columns": ["dataset_id", "contact_name"],  # ✅ Now includes contact_name
                    "keys": ["dataset_id", "contact_name"],
                    "data_source": "db1",
                    "query": "SELECT * FROM dataset_contacts",
                    "foreign_keys": [
                        {
                            "entity": "contact",
                            "local_keys": ["contact_name"],  # ✅ Now valid
                            "remote_keys": ["contact_name"],
                        }
                    ],
                },
                "contact": {
                    "type": "sql",
                    "columns": ["contact_name", "email"],
                    "keys": ["contact_name"],
                    "data_source": "db1",
                    "query": "SELECT * FROM contact",
                },
            },
            "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
        }

        validator = CompositeProjectSpecification(project_cfg)
        result = validator.is_satisfied_by()

        # Should pass validation now
        assert result is True

        # No errors for these specific issues
        unnest_errors = [e for e in validator.errors if "id_vars" in e.message]
        fk_errors = [e for e in validator.errors if "local_keys" in e.message and "missing" in e.message]

        assert len(unnest_errors) == 0
        assert len(fk_errors) == 0
