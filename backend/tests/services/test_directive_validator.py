"""Tests for @value directive validator."""

from unittest.mock import Mock

import pytest

from backend.app.models.project import Project
from backend.app.services.directive_validator import DirectiveValidationResult, DirectiveValidator


class TestDirectiveValidator:
    """Tests for DirectiveValidator."""

    @pytest.fixture
    def sample_project(self):
        """Create a sample project for testing."""
        return Project(
            entities={
                "location": {
                    "type": "fixed",
                    "public_id": "location_id",
                    "keys": ["location_name"],
                    "columns": ["location_name", "country"],
                },
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude"],
                    "extra_columns": {"full_name": "concat(...)"},
                },
            },
        )

    @pytest.fixture
    def validator(self, sample_project):
        """Create DirectiveValidator instance."""
        return DirectiveValidator(sample_project)

    def test_validate_valid_directive(self, validator):
        """Test validation of a valid @value directive."""
        result = validator.validate_directive("@value:entities.site.keys")
        
        assert result.is_valid
        assert result.path == "entities.site.keys"
        assert result.resolved_value == ["site_name"]
        assert result.error is None

    def test_validate_directive_without_prefix(self, validator):
        """Test validation fails without @value: prefix."""
        result = validator.validate_directive("entities.site.keys")
        
        assert not result.is_valid
        assert "must start with '@value:'" in result.error

    def test_validate_directive_too_short(self, validator):
        """Test validation fails with too short path."""
        result = validator.validate_directive("@value:entities")
        
        assert not result.is_valid
        assert "at least 2 parts" in result.error
        assert len(result.suggestions) > 0

    def test_validate_invalid_entity(self, validator):
        """Test validation fails with nonexistent entity."""
        result = validator.validate_directive("@value:entities.nonexistent.keys")
        
        assert not result.is_valid
        assert "nonexistent" in result.error
        assert len(result.suggestions) > 0

    def test_validate_invalid_field(self, validator):
        """Test validation fails with nonexistent field."""
        result = validator.validate_directive("@value:entities.site.invalid_field")
        
        assert not result.is_valid
        assert "invalid_field" in result.error

    def test_validate_columns_field(self, validator):
        """Test validation of columns field."""
        result = validator.validate_directive("@value:entities.site.columns")
        
        assert result.is_valid
        assert result.resolved_value == ["site_name", "latitude", "longitude"]

    def test_validate_extra_columns_field(self, validator):
        """Test validation of extra_columns field."""
        result = validator.validate_directive("@value:entities.site.extra_columns")
        
        assert result.is_valid
        assert result.resolved_value == {"full_name": "concat(...)"}

    def test_validate_fk_directive_valid_list(self, validator):
        """Test FK-specific validation with valid list."""
        result = validator.validate_foreign_key_directive(
            "site", "location", "@value:entities.location.keys", is_local=False
        )
        
        assert result.is_valid
        assert isinstance(result.resolved_value, list)

    def test_validate_fk_directive_invalid_type(self, validator):
        """Test FK-specific validation fails with non-list value."""
        result = validator.validate_foreign_key_directive(
            "site", "location", "@value:entities.location.public_id", is_local=False
        )
        
        assert not result.is_valid
        assert "must resolve to a list" in result.error

    def test_validate_fk_directive_suggestions(self, validator):
        """Test FK validation provides entity-specific suggestions."""
        result = validator.validate_foreign_key_directive(
            "site", "location", "@value:invalid.path", is_local=False
        )
        
        assert not result.is_valid
        assert any("location.keys" in s for s in result.suggestions)
        assert any("location.columns" in s for s in result.suggestions)

    def test_get_all_valid_paths(self, validator):
        """Test getting all valid directive paths."""
        paths = validator.get_all_valid_paths()
        
        assert "@value:entities.location.keys" in paths
        assert "@value:entities.location.columns" in paths
        assert "@value:entities.site.keys" in paths
        assert "@value:entities.site.columns" in paths
        assert "@value:entities.site.extra_columns" in paths

    def test_suggestions_for_partial_path(self, validator):
        """Test suggestions are provided for invalid paths."""
        result = validator.validate_directive("@value:entities.site.xyz")
        
        assert not result.is_valid
        assert len(result.suggestions) > 0

    def test_resolve_nested_path(self, sample_project):
        """Test resolving deeply nested paths."""
        # Add nested structure
        sample_project.options = {
            "ingesters": {
                "sead": {
                    "host": "localhost",
                }
            }
        }
        validator = DirectiveValidator(sample_project)
        
        result = validator.validate_directive("@value:options.ingesters.sead.host")
        
        assert result.is_valid
        assert result.resolved_value == "localhost"

    def test_empty_project(self):
        """Test validator with empty project."""
        empty_project = Project(entities={})
        validator = DirectiveValidator(empty_project)
        
        result = validator.validate_directive("@value:entities.site.keys")
        
        assert not result.is_valid
        assert len(result.suggestions) >= 1  # Should suggest root paths
