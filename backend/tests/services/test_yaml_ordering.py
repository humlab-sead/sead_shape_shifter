"""Tests for YAML entity key ordering in YamlService."""

import tempfile
from pathlib import Path

import pytest

from backend.app.services.yaml_service import YamlService


class TestYamlEntityKeyOrdering:
    """Test entity key ordering in YAML output."""

    @pytest.fixture
    def yaml_service(self):
        """Create YamlService instance."""
        return YamlService()

    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yield Path(f.name)
            Path(f.name).unlink(missing_ok=True)

    def test_entity_keys_ordered_correctly(self, yaml_service, temp_file):
        """Test that entity keys are ordered according to canonical schema."""
        # Data with scrambled key order
        data = {
            "metadata": {"name": "test", "type": "shapeshifter-project", "version": "1.0.0"},
            "entities": {
                "test_entity": {
                    # Keys intentionally in random order
                    "columns": ["col1", "col2"],
                    "foreign_keys": [],
                    "source": "some_source",
                    "type": "sql",
                    "public_id": "test_id",
                    "keys": ["key1"],
                    "system_id": "system_id",
                    "drop_duplicates": True,
                }
            },
        }

        # Save and reload
        yaml_service.save(data, temp_file, create_backup=False)
        result = yaml_service.load(temp_file)

        # Extract ordered keys
        entity_keys = list(result["entities"]["test_entity"].keys())

        # Expected order from canonical schema
        expected_order = [
            "type",  # Core identity first
            "source",
            "system_id",
            "public_id",
            "keys",  # Business keys
            "columns",  # Schema
            # values would be here if present
            "foreign_keys",  # Relationships
            "drop_duplicates",  # Operations
            # filters would be here if present
        ]

        assert entity_keys == expected_order, f"Expected {expected_order}, got {entity_keys}"

    def test_multiple_entities_all_ordered(self, yaml_service, temp_file):
        """Test that all entities in config are ordered."""
        data = {
            "metadata": {"name": "test", "type": "shapeshifter-project", "version": "1.0.0"},
            "entities": {
                "entity1": {"type": "fixed", "values": [[1]], "keys": ["id"]},
                "entity2": {"columns": ["a"], "type": "sql", "source": "db", "keys": ["b"]},
            },
        }

        yaml_service.save(data, temp_file, create_backup=False)
        result = yaml_service.load(temp_file)

        # Entity1 keys
        entity1_keys = list(result["entities"]["entity1"].keys())
        assert entity1_keys[0] == "type", "type should be first"
        assert entity1_keys[1] == "keys", "keys should be second (after type)"
        assert entity1_keys[2] == "values", "values should be third"

        # Entity2 keys
        entity2_keys = list(result["entities"]["entity2"].keys())
        assert entity2_keys[0] == "type", "type should be first"
        assert entity2_keys[1] == "source", "source should be second"
        assert entity2_keys[2] == "keys", "keys should come before columns"
        assert entity2_keys[3] == "columns", "columns should be fourth"

    def test_non_canonical_keys_alphabetically_at_end(self, yaml_service, temp_file):
        """Test that keys not in canonical order are sorted alphabetically at end."""
        data = {
            "metadata": {"name": "test", "type": "shapeshifter-project", "version": "1.0.0"},
            "entities": {
                "test": {
                    "type": "fixed",
                    "keys": ["id"],
                    # Custom keys not in canonical order
                    "zebra_custom": "value",
                    "alpha_custom": "value",
                    "beta_custom": "value",
                }
            },
        }

        yaml_service.save(data, temp_file, create_backup=False)
        result = yaml_service.load(temp_file)

        entity_keys = list(result["entities"]["test"].keys())

        # Canonical keys should come first
        assert entity_keys[0] == "type"
        assert entity_keys[1] == "keys"

        # Custom keys should be alphabetically sorted at end
        custom_keys = entity_keys[2:]
        assert custom_keys == ["alpha_custom", "beta_custom", "zebra_custom"]

    def test_ordering_preserves_values_formatting(self, yaml_service, temp_file):
        """Test that key ordering doesn't break special 'values' formatting."""
        data = {
            "metadata": {"name": "test", "type": "shapeshifter-project", "version": "1.0.0"},
            "entities": {
                "test": {
                    "keys": ["id"],
                    "type": "fixed",
                    "values": [
                        [1, "row1", "data"],
                        [2, "row2", "data"],
                    ],
                }
            },
        }

        yaml_service.save(data, temp_file, create_backup=False)
        result = yaml_service.load(temp_file)

        # Verify values are preserved
        assert result["entities"]["test"]["values"] == [[1, "row1", "data"], [2, "row2", "data"]]

        # Verify key order (type, keys, values)
        entity_keys = list(result["entities"]["test"].keys())
        assert entity_keys == ["type", "keys", "values"]

    def test_no_entities_key_does_not_error(self, yaml_service, temp_file):
        """Test that configs without 'entities' key don't error."""
        data = {
            "metadata": {"name": "test", "type": "shapeshifter-project", "version": "1.0.0"},
            "options": {"some_option": "value"},
        }

        # Should not raise
        yaml_service.save(data, temp_file, create_backup=False)
        result = yaml_service.load(temp_file)

        assert "metadata" in result
        assert "options" in result
