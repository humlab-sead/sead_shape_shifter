"""Test runtime error prevention validators.

These validators catch configuration errors that would only manifest as
runtime errors during normalization, providing early feedback to users.
"""

from src.specifications.entity import (
    ForeignKeyColumnsSpecification,
    UnnestColumnsSpecification,
)


class TestUnnestColumnsSpecification:
    """Tests for UnnestColumnsSpecification - validates unnest column references."""

    def test_valid_unnest_configuration(self):
        """Test that valid unnest config passes."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id", "measure1", "measure2"],
                    "unnest": {
                        "id_vars": ["id"],
                        "value_vars": ["measure1", "measure2"],
                        "var_name": "measure_type",
                        "value_name": "value",
                    },
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_id_vars_error(self):
        """Test that missing id_vars produces error."""
        project_cfg = {
            "entities": {
                "abundance_property": {
                    "type": "sql",
                    "columns": ["property_type", "value"],
                    "unnest": {
                        "id_vars": ["abundance_id"],  # Missing from columns!
                        "value_vars": ["value"],
                        "var_name": "property",
                        "value_name": "property_value",
                    },
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="abundance_property")

        assert result is False
        assert len(spec.errors) > 0
        assert "abundance_id" in spec.errors[0].message
        assert "missing id_vars columns" in spec.errors[0].message

    def test_missing_value_vars_error(self):
        """Test that missing value_vars produces error."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id"],
                    "unnest": {
                        "id_vars": ["id"],
                        "value_vars": ["missing_col"],  # Missing from columns!
                        "var_name": "var",
                        "value_name": "value",
                    },
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is False
        assert len(spec.errors) > 0
        assert "missing_col" in spec.errors[0].message

    def test_id_vars_in_keys_passes(self):
        """Test that id_vars can be in keys instead of columns."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "keys": ["id"],
                    "columns": ["measure1"],
                    "unnest": {
                        "id_vars": ["id"],  # In keys, not columns
                        "value_vars": ["measure1"],
                        "var_name": "measure",
                        "value_name": "value",
                    },
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_no_unnest_passes(self):
        """Test that entities without unnest pass."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id", "name"],
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True

    def test_id_vars_from_extra_columns(self):
        """Test that id_vars can reference extra_columns."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["measure1"],
                    "extra_columns": {"id": 1},  # Computed column
                    "unnest": {
                        "id_vars": ["id"],  # References extra_column
                        "value_vars": ["measure1"],
                        "var_name": "measure",
                        "value_name": "value",
                    },
                }
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_id_vars_from_fk_added_public_id(self):
        """Test that id_vars can reference columns added by FK linking."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "sql",
                    "columns": ["site_name", "location_name", "area"],
                    "foreign_keys": [
                        {
                            "entity": "location",
                            "local_keys": ["location_name"],
                            "remote_keys": ["location_name"],
                        }
                    ],
                    "unnest": {
                        "id_vars": ["site_name", "location_id"],  # location_id added by FK
                        "value_vars": ["area"],
                        "var_name": "measure",
                        "value_name": "value",
                    },
                },
                "location": {
                    "type": "fixed",
                    "columns": ["location_name"],
                    "public_id": "location_id",  # This gets added to site during FK linking
                    "values": [["Sweden"], ["Norway"]],
                },
            }
        }

        spec = UnnestColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert len(spec.errors) == 0


class TestForeignKeyColumnsSpecification:
    """Tests for ForeignKeyColumnsSpecification - validates FK local_keys exist."""

    def test_valid_foreign_key(self):
        """Test that valid foreign key passes."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "sql",
                    "columns": ["site_name", "location_name"],
                    "keys": ["site_name"],
                    "foreign_keys": [
                        {
                            "entity": "location",
                            "local_keys": ["location_name"],
                            "remote_keys": ["location_name"],
                        }
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_local_keys_error(self):
        """Test that missing local_keys produces error."""
        project_cfg = {
            "entities": {
                "dataset_contacts": {
                    "type": "sql",
                    "columns": ["dataset_id", "contact_id"],
                    "foreign_keys": [
                        {
                            "entity": "contact",
                            "local_keys": ["contact_name"],  # Missing from columns!
                            "remote_keys": ["contact_name"],
                        }
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="dataset_contacts")

        assert result is False
        assert len(spec.errors) > 0
        assert "contact_name" in spec.errors[0].message
        assert "missing local_keys" in spec.errors[0].message

    def test_local_keys_in_keys_passes(self):
        """Test that local_keys can be in keys instead of columns."""
        project_cfg = {
            "entities": {
                "site": {
                    "type": "sql",
                    "keys": ["site_name", "location_name"],
                    "columns": ["description"],
                    "foreign_keys": [
                        {
                            "entity": "location",
                            "local_keys": ["location_name"],  # In keys
                            "remote_keys": ["location_name"],
                        }
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="site")

        assert result is True
        assert len(spec.errors) == 0

    def test_missing_local_keys_field_error(self):
        """Test that missing local_keys field produces error."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id"],
                    "foreign_keys": [
                        {
                            "entity": "other",
                            # Missing local_keys!
                            "remote_keys": ["id"],
                        }
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is False
        assert len(spec.errors) > 0
        assert "missing 'local_keys'" in spec.errors[0].message

    def test_no_foreign_keys_passes(self):
        """Test that entities without foreign keys pass."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id", "name"],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True

    def test_local_keys_from_extra_columns(self):
        """Test that local_keys can reference extra_columns."""
        project_cfg = {
            "entities": {
                "test_entity": {
                    "type": "sql",
                    "columns": ["id"],
                    "extra_columns": {"location_name": "Default Location"},  # Computed column
                    "foreign_keys": [
                        {
                            "entity": "location",
                            "local_keys": ["location_name"],  # References extra_column
                            "remote_keys": ["location_name"],
                        }
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="test_entity")

        assert result is True
        assert len(spec.errors) == 0

    def test_fk_references_unnest_result_columns(self):
        """Test that FK can reference unnest result columns (deferred linking)."""
        project_cfg = {
            "entities": {
                "site_location": {
                    "type": "sql",
                    "keys": ["site_id"],
                    "columns": ["Ort", "Kreis", "Land"],  # Will be unnested
                    "unnest": {
                        "id_vars": ["site_id"],
                        "value_vars": ["Ort", "Kreis", "Land"],
                        "var_name": "location_type",
                        "value_name": "location_name",
                    },
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_id"],  # Available at FK link time
                            "remote_keys": ["site_id"],
                        },
                        {
                            "entity": "location",
                            # These columns created by unnest - deferred linking handles this
                            "local_keys": ["location_type", "location_name"],
                            "remote_keys": ["location_type", "location_name"],
                        },
                    ],
                }
            }
        }

        spec = ForeignKeyColumnsSpecification(project_cfg)
        result = spec.is_satisfied_by(entity_name="site_location")

        # Should pass - unnest result columns are allowed (deferred linking)
        assert result is True
        assert len(spec.errors) == 0
