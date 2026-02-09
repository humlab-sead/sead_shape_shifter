"""Tests for validation service."""

from unittest.mock import Mock, patch

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services import validation_service as validation_service_module
from backend.app.services.validation_service import ValidationService, get_validation_service
from src.validators.data_validators import ValidationIssue

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def validation_service():
    """Create ValidationService instance."""
    return ValidationService()


@pytest.fixture
def reset_validation_singleton():
    """Reset validation service singleton between tests."""
    original = validation_service_module._validation_service
    validation_service_module._validation_service = None
    yield
    validation_service_module._validation_service = original


class TestValidationServiceBasic:
    """Tests for basic validation functionality."""

    def test_validate_empty_configuration(self, validation_service: ValidationService):
        """Test validating empty configuration."""
        config = {}
        result: validation_service_module.ValidationResult = validation_service.validate_project(config)

        assert result.is_valid is False
        assert result.error_count > 0
        assert any("metadata" in e.message.lower() or "entities" in e.message.lower() for e in result.errors)

    def test_validate_valid_configuration(self, validation_service):
        """Test validating valid configuration."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {"sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value"]}},
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_project_with_foreign_key(self, validation_service):
        """Test validating configuration with foreign keys."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "site": {"type": "entity", "keys": ["site_id"], "columns": ["name"]},
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["name", "site_id"],
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_id"],
                            "remote_keys": ["site_id"],
                            "how": "left",
                        }
                    ],
                },
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is True
        assert result.error_count == 0


class TestValidationServiceErrors:
    """Tests for error detection."""

    def test_missing_entity_reference(self, validation_service):
        """Test detecting missing entity reference in foreign key."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": [],
                    "foreign_keys": [
                        {
                            "entity": "nonexistent",
                            "local_keys": ["site_id"],
                            "remote_keys": ["site_id"],
                            "how": "left",
                        }
                    ],
                }
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is False
        assert result.error_count > 0
        # Check that error was parsed correctly
        errors_for_sample = result.get_errors_for_entity("sample")
        assert len(errors_for_sample) > 0
        assert any("nonexistent" in e.message for e in errors_for_sample)

    def test_circular_dependency(self, validation_service):
        """Test detecting circular dependencies."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "entity_a": {"type": "entity", "columns": [], "keys": ["id"], "depends_on": ["entity_b"]},
                "entity_b": {"type": "entity", "columns": [], "keys": ["id"], "depends_on": ["entity_a"]},
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is False
        assert result.error_count > 0
        assert any("circular" in e.message.lower() for e in result.errors)

    def test_missing_required_fields(self, validation_service):
        """Test detecting missing required fields."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "sample": {
                    "type": "entity"
                    # Missing 'keys' field
                }
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is False
        assert result.error_count > 0

    def test_invalid_foreign_key_mismatched_keys(self, validation_service):
        """Test detecting foreign key with mismatched number of keys."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "site": {"type": "entity", "keys": ["site_id"], "columns": ["name"]},
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["name", "site_id"],
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_id", "extra_key"],  # Mismatched count
                            "remote_keys": ["site_id"],
                            "how": "left",
                        }
                    ],
                },
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is False
        assert result.error_count > 0
        assert any("does not match" in e.message.lower() for e in result.errors)


class TestValidationServiceEntity:
    """Tests for entity-specific validation."""

    def test_validate_single_entity(self, validation_service):
        """Test validating single entity."""
        entity_data = {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value"]}
        project = Project(
            metadata=ProjectMetadata(type="shapeshifter-project", name="test", entity_count=1), entities={"sample": entity_data}, options={}
        )

        result = validation_service.validate_entity(project, "sample")

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_entity_with_errors(self, validation_service: ValidationService):
        """Test validating entity with errors."""
        entity_data = {
            "type": "entity"
            # Missing required 'keys' field
        }
        project: Project = Project(
            metadata=ProjectMetadata(type="shapeshifter-project", name="test", entity_count=1), entities={"sample": entity_data}, options={}
        )

        result = validation_service.validate_entity(project, "sample")

        assert result.is_valid is False
        assert result.error_count > 0

    def test_validate_entity_filters_errors(self, validation_service):
        """Test that entity validation only returns errors for that entity."""
        project_cfg = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "natural_region": {"type": "entity", "keys": ["region_id"], "columns": ["name"]},
                "site": {
                    "type": "entity",
                    "keys": ["site_id"],
                    "columns": ["name", "location"],
                },
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "foreign_keys": [
                        {
                            "entity": "nonexistent",
                            "local_keys": ["site_id"],
                            "remote_keys": ["site_id"],
                            "how": "left",
                        }
                    ],
                },
            },
            "options": {"verbose": True},
        }
        project: Project = ProjectMapper.to_api_config(project_cfg, "test")

        result = validation_service.validate_entity(project, "sample")

        # Should only contain errors related to 'sample' entity
        assert result.is_valid is False
        for error in result.errors:
            assert error.entity is None or error.entity == "sample"


class TestValidationServiceErrorParsing:
    """Tests for error message parsing."""

    def test_parse_entity_from_error(self, validation_service):
        """Test parsing entity name from error message."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "foreign_keys": [{"entity": "missing", "local_keys": ["x"], "remote_keys": ["y"]}],
                }
            },
        }

        result = validation_service.validate_project(config)

        # Check that entity was extracted correctly
        assert any(e.entity == "sample" for e in result.errors)

    def test_error_codes_assigned(self, validation_service):
        """Test that error codes are assigned."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "foreign_keys": [{"entity": "missing", "local_keys": ["x"], "remote_keys": ["y"]}],
                }
            },
        }

        result = validation_service.validate_project(config)

        # All errors should have codes
        assert all(e.code is not None for e in result.errors)


class TestValidationServiceIntegration:
    """Integration tests with complex configurations."""

    def test_complex_valid_configuration(self, validation_service):
        """Test complex but valid configuration."""
        config = {
            "metadata": {"type": "shapeshifter-project", "name": "test"},
            "entities": {
                "natural_region": {
                    "type": "entity",
                    "keys": ["region_id"],
                    "columns": ["name"],
                },
                "site": {
                    "type": "entity",
                    "keys": ["site_id"],
                    "columns": ["name", "location"],
                },
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["name", "site_id"],
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_id"],
                            "remote_keys": ["site_id"],
                            "how": "left",
                        }
                    ],
                },
            },
            "options": {"verbose": True},
        }

        result = validation_service.validate_project(config)

        assert result.is_valid is True
        assert result.error_count == 0


class TestDataValidation:
    """Tests for data-aware validation that depends on preview and data validators."""

    @pytest.mark.asyncio
    async def test_validate_project_data_groups_by_severity(self, reset_validation_singleton):
        """Test data validation groups issues by severity using dependency injection."""
        captured: dict[str, object] = {}

        class DummyDataValidationOrchestrator:
            async def validate_all_entities(
                self,
                core_project,
                project_name: str,
                entity_names: list[str] | None = None,
            ):

                captured["args"] = (core_project, project_name, entity_names)
                # Return domain ValidationIssues (not API models)
                return [
                    ValidationIssue(severity="error", entity="a", field=None, message="err", code="E1", category="data", priority="high"),
                    ValidationIssue(
                        severity="warning", entity="b", field=None, message="warn", code="W1", category="data", priority="medium"
                    ),
                    ValidationIssue(severity="info", entity="c", field=None, message="info", code="I1", category="data", priority="low"),
                ]

        # Create factory that returns our mock orchestrator
        def mock_orchestrator_factory():
            orchestrator = DummyDataValidationOrchestrator()
            captured["orchestrator"] = orchestrator
            return orchestrator

        # Mock project loading and resolution
        mock_api_project = Mock(spec=Project)
        mock_core_project = Mock()
        mock_core_project.cfg = {"entities": {}}

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                # Inject the factory via constructor
                service = ValidationService(data_orchestrator_factory=mock_orchestrator_factory)  # type: ignore
                result = await service.validate_project_data("cfg-name", ["entity1"])

        assert result.is_valid is False
        assert result.error_count == 1
        assert result.warning_count == 1
        assert len(result.info) == 1
        # Verify captured arguments (core_project is Mock object, project_name, entity_names)
        assert captured["args"][1] == "cfg-name"  # project_name # type: ignore
        assert captured["args"][2] == ["entity1"]  # entity_names # type: ignore
        assert isinstance(captured["orchestrator"], DummyDataValidationOrchestrator)

    def test_get_validation_service_singleton(self, reset_validation_singleton):
        """Test get_validation_service returns a singleton instance."""
        first = get_validation_service()
        second = get_validation_service()

        assert isinstance(first, ValidationService)
        assert first is second
