"""Tests for column introspection service."""

from unittest.mock import Mock

import pytest

from backend.app.models.project import Project
from backend.app.services.column_introspection_service import ColumnAvailability, ColumnIntrospectionService
from backend.app.services.project_service import ProjectService


class TestColumnIntrospectionService:
    """Tests for ColumnIntrospectionService."""

    @pytest.fixture
    def mock_project_service(self):
        """Mock ProjectService."""
        return Mock(spec=ProjectService)

    @pytest.fixture
    def service(self, mock_project_service):
        """Create ColumnIntrospectionService instance."""
        return ColumnIntrospectionService(mock_project_service)

    @pytest.fixture
    def sample_project(self):
        """Create a sample project for testing."""
        project = Project(
            entities={
                "location": {
                    "type": "fixed",
                    "public_id": "location_id",
                    "keys": ["location_name"],
                    "values": {"location.xlsx": {}},
                },
                "site": {
                    "type": "sql",
                    "public_id": "site_id",
                    "data_source": "test_db",
                    "table": "sites",
                    "columns": ["site_name", "latitude", "longitude"],
                    "keys": ["site_name"],
                    "extra_columns": {"full_name": "concat(site_name, ' - ', latitude)"},
                    "foreign_keys": [
                        {
                            "entity": "location",
                            "local_keys": ["location_name"],
                            "remote_keys": ["location_name"],
                        }
                    ],
                },
                "sample": {
                    "type": "sql",
                    "public_id": "sample_id",
                    "data_source": "test_db",
                    "table": "samples",
                    "columns": ["sample_name", "depth"],
                    "unnest": {
                        "value_column": "measurement",
                        "var_name": "measurement_type",
                        "id_vars": ["sample_name"],
                    },
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_name"],
                            "remote_keys": ["site_name"],
                        }
                    ],
                },
            },
        )
        return project

    def test_analyze_entity_explicit_columns(self, service, sample_project, mock_project_service):
        """Test extraction of explicit columns."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        assert "site_name" in result.explicit
        assert "latitude" in result.explicit
        assert "longitude" in result.explicit

    def test_analyze_entity_keys(self, service, sample_project, mock_project_service):
        """Test extraction of keys."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        assert "site_name" in result.keys

    def test_analyze_entity_extra_columns(self, service, sample_project, mock_project_service):
        """Test extraction of extra columns."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        assert "full_name" in result.extra

    def test_analyze_entity_unnested_columns(self, service, sample_project, mock_project_service):
        """Test extraction of unnested columns."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "sample")

        assert "value_id" in result.unnested
        assert "value_name" in result.unnested
        assert "measurement_type" in result.unnested
        assert "sample_name" in result.unnested

    def test_analyze_entity_fk_columns(self, service, sample_project, mock_project_service):
        """Test extraction of FK columns."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        # site has FK to location, so it inherits location_id column
        assert "location_id" in result.foreign_key

    def test_analyze_entity_system_columns(self, service, sample_project, mock_project_service):
        """Test extraction of system columns."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        assert "system_id" in result.system
        assert "site_id" in result.system  # public_id

    def test_analyze_entity_directives(self, service, sample_project, mock_project_service):
        """Test generation of @value directive suggestions."""
        mock_project_service.load_project.return_value = sample_project

        result = service._analyze_entity(sample_project, "site")

        assert "@value:entities.site.keys" in result.directives
        assert "@value:entities.site.columns" in result.directives

    def test_get_available_columns_local_only(self, service, sample_project, mock_project_service):
        """Test getting columns for local entity only."""
        mock_project_service.load_project.return_value = sample_project

        result = service.get_available_columns("test_project", "site")

        assert "local_columns" in result
        assert isinstance(result["local_columns"], ColumnAvailability)
        assert "remote_columns" not in result

    def test_get_available_columns_with_remote(self, service, sample_project, mock_project_service):
        """Test getting columns for both local and remote entities."""
        mock_project_service.load_project.return_value = sample_project

        result = service.get_available_columns("test_project", "site", "location")

        assert "local_columns" in result
        assert "remote_columns" in result
        assert isinstance(result["local_columns"], ColumnAvailability)
        assert isinstance(result["remote_columns"], ColumnAvailability)

    def test_analyze_nonexistent_entity(self, service, sample_project):
        """Test analyzing an entity that doesn't exist."""
        result = service._analyze_entity(sample_project, "nonexistent")

        # Should return empty ColumnAvailability
        assert result.explicit == []
        assert result.keys == []
        assert result.extra == []
    def test_analyze_entity_with_directive_columns(self, service, mock_project_service):
        """Test that string directives in columns field are not split into characters."""
        project = Project(
            entities={
                "abundance_property_type": {
                    "type": "fixed",
                    "public_id": "arbodat_code",
                    "keys": ["arbodat_code"],
                    "values": {"abundance_property_type.xlsx": {}},
                },
                "abundance_property": {
                    "type": "entity",
                    "source": "abundance",
                    "public_id": "abundance_property_id",
                    "keys": [],
                    "columns": "@value: entities.abundance_property_type.arbodat_codes + ['abundance_id']",
                    "foreign_keys": [
                        {
                            "entity": "abundance_property_type",
                            "local_keys": ["abundance_property_type"],
                            "remote_keys": ["arbodat_code"],
                        }
                    ],
                    "unnest": {
                        "id_vars": ["abundance_id"],
                        "value_vars": "@value: entities.abundance_property_type.arbodat_codes",
                        "var_name": "abundance_property_type",
                        "value_name": "abundance_property_value",
                    },
                },
            },
        )
        mock_project_service.load_project.return_value = project

        result = service._analyze_entity(project, "abundance_property")

        # String directive should be added to directives, not split into characters
        assert len(result.explicit) == 0  # No explicit columns
        assert "@value: entities.abundance_property_type.arbodat_codes + ['abundance_id']" in result.directives
        
        # Verify no individual characters from the directive string
        assert "@" not in result.explicit
        assert "v" not in result.explicit
        assert "a" not in result.explicit
        
        # unnest value_vars directive should not be split either
        assert "abundance_id" in result.unnested  # id_vars is still added
        assert "abundance_property_type" in result.unnested  # var_name is still added
        # But value_vars should not be split into characters

    def test_analyze_entity_with_directive_keys(self, service, mock_project_service):
        """Test that string directives in keys field are not split into characters."""
        project = Project(
            entities={
                "test_entity": {
                    "type": "entity",
                    "source": "test",
                    "public_id": "test_id",
                    "keys": "@value: entities.other.keys",
                    "columns": ["col1", "col2"],
                },
            },
        )
        mock_project_service.load_project.return_value = project

        result = service._analyze_entity(project, "test_entity")

        # String directive in keys should not be split into characters
        assert len(result.keys) == 0  # No actual keys
        # Verify no individual characters
        assert "@" not in result.keys
        assert "v" not in result.keys