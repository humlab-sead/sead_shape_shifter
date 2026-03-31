"""Tests for merged entity validation."""

from src.specifications.entity import MergedEntityFieldsSpecification


class TestMergedEntityFieldsSpecification:
    """Test merged entity validation."""

    def test_valid_merged_entity(self):
        """Test valid merged entity passes validation."""
        config = {
            "entities": {
                "abundance": {"type": "entity", "data_source": "clearinghouse", "columns": ["sample_id", "taxon_id"]},
                "_analysis_entity_relative_dating": {
                    "type": "entity",
                    "data_source": "clearinghouse",
                    "columns": ["dating_id"],
                },
                "analysis_entity": {
                    "type": "merged",
                    "public_id": "analysis_entity_id",
                    "columns": ["sample_id", "taxon_id", "dating_id"],
                    "branches": [
                        {"name": "abundance", "source": "abundance", "keys": ["sample_id"]},
                        {"name": "relative_dating", "source": "_analysis_entity_relative_dating", "keys": []},
                    ],
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="analysis_entity")

        # Debug: print errors if any
        if spec.has_errors():
            print("\nErrors:")
            for err in spec.errors:
                print(f"  - {err}")
        if spec.has_warnings():
            print("\nWarnings:")
            for warn in spec.warnings:
                print(f"  - {warn}")

        assert result is True
        assert not spec.has_errors()
        assert not spec.has_warnings()

    def test_merged_entity_missing_public_id(self):
        """Test error when public_id is missing."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "merged": {"type": "merged", "columns": ["id"], "branches": [{"name": "branch1", "source": "source1"}]},
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("public_id" in str(err).lower() for err in spec.errors)

    def test_merged_entity_missing_branches(self):
        """Test error when branches field is missing."""
        config = {
            "entities": {
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    # No branches field
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("branches" in str(err).lower() for err in spec.errors)

    def test_merged_entity_empty_branches(self):
        """Test error when branches is empty list."""
        config = {
            "entities": {
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [],  # Empty
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("at least one branch" in str(err).lower() for err in spec.errors)

    def test_branch_missing_name(self):
        """Test error when branch is missing name field."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [{"source": "source1"}],  # Missing 'name'
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("'name' field is required" in str(err) for err in spec.errors)

    def test_branch_missing_source(self):
        """Test error when branch is missing source field."""
        config = {
            "entities": {
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [{"name": "branch1"}],  # Missing 'source'
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("'source' field is required" in str(err) for err in spec.errors)

    def test_branch_source_not_exists(self):
        """Test error when branch source entity doesn't exist."""
        config = {
            "entities": {
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [{"name": "branch1", "source": "nonexistent_entity"}],  # Source doesn't exist
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("does not exist" in str(err) for err in spec.errors)

    def test_duplicate_branch_names(self):
        """Test error when branch names are duplicated."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "source2": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [
                        {"name": "same_name", "source": "source1"},
                        {"name": "same_name", "source": "source2"},  # Duplicate name
                    ],
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()
        assert any("duplicate branch name" in str(err).lower() for err in spec.errors)

    def test_branch_keys_validation(self):
        """Test validation of keys field in branches."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id", "name"]},
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id", "name"],
                    "branches": [{"name": "branch1", "source": "source1", "keys": ["name"]}],  # Valid keys list
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is True
        assert not spec.has_errors()

    def test_branch_keys_invalid_type(self):
        """Test error when keys field is not a list."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [{"name": "branch1", "source": "source1", "keys": "not_a_list"}],  # Invalid type
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        assert result is False
        assert spec.has_errors()

    def test_merged_entity_with_source_fields_warning(self):
        """Test warning when merged entity has incompatible source/data_source/query fields."""
        config = {
            "entities": {
                "source1": {"type": "entity", "data_source": "db", "columns": ["id"]},
                "merged": {
                    "type": "merged",
                    "public_id": "merged_id",
                    "columns": ["id"],
                    "branches": [{"name": "branch1", "source": "source1"}],
                    "data_source": "should_not_have_this",  # Incompatible field
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="merged")

        # Debug: print errors and warnings
        if spec.has_errors():
            print("\nErrors:")
            for err in spec.errors:
                print(f"  - {err}")
        if spec.has_warnings():
            print("\nWarnings:")
            for warn in spec.warnings:
                print(f"  - {warn}")

        # Should pass (warning only), but should have warnings
        assert result is True
        assert not spec.has_errors()
        assert spec.has_warnings()

    def test_complex_merged_entity(self):
        """Test complex merged entity with multiple branches and FKs."""
        config = {
            "entities": {
                "location": {"type": "fixed", "public_id": "location_id", "values": [["Norway"]]},
                "abundance": {"type": "entity", "data_source": "db", "columns": ["sample_id", "taxon_id", "abundance_value"]},
                "_analysis_entity_relative_dating": {
                    "type": "entity",
                    "data_source": "db",
                    "columns": ["dating_id", "dating_value"],
                },
                "_analysis_entity_isotope": {"type": "entity", "data_source": "db", "columns": ["isotope_id", "c14_value"]},
                "analysis_entity": {
                    "type": "merged",
                    "public_id": "analysis_entity_id",
                    "columns": ["sample_id", "taxon_id", "dating_id", "isotope_id", "location_name"],
                    "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
                    "branches": [
                        {"name": "abundance", "source": "abundance", "keys": ["sample_id", "taxon_id"]},
                        {"name": "relative_dating", "source": "_analysis_entity_relative_dating", "keys": ["dating_id"]},
                        {"name": "isotope", "source": "_analysis_entity_isotope", "keys": []},
                    ],
                },
            }
        }

        spec = MergedEntityFieldsSpecification(config)
        result = spec.is_satisfied_by(entity_name="analysis_entity")

        assert result is True
        assert not spec.has_errors()
        assert not spec.has_warnings()
