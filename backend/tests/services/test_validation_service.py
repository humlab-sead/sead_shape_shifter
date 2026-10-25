"""Tests for validation service."""

from unittest.mock import Mock, patch

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata
from backend.app.models.validation import (
    DataValidationStatus,
    EntityDataValidationResult,
    EntityDataValidationStatus,
    ValidationCategory,
    ValidationError,
    ValidationPriority,
    ValidationResult,
)
from backend.app.services import validation_service as validation_service_module
from backend.app.services.validation_service import ValidationService, get_validation_service
from src.model import ShapeShiftProject
from src.validators.data_validators import ValidationIssue

# pylint: disable=redefined-outer-name, unused-argument

FIXED_PROVIDER_ENTITY = {
    "type": "fixed",
    "public_id": "data_provider_id",
    "keys": ["data_provider_code"],
    "columns": ["data_provider_id", "data_provider_code"],
    "values": [[51, "test-provider"]],
}
"""Fixed data provider row required of every project bound to a provider-schema pair."""


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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "data_provider": FIXED_PROVIDER_ENTITY,
                "sample": {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id", "name", "value"]},
            },
        }
        result = validation_service.validate_project(config)

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_project_with_foreign_key(self, validation_service):
        """Test validating configuration with foreign keys."""
        config = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "data_provider": FIXED_PROVIDER_ENTITY,
                "site": {"type": "entity", "keys": ["site_id"], "columns": ["site_id", "name"]},
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["sample_id", "name", "site_id"],
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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

    def test_invalid_filter_stage_is_reported(self, validation_service):
        """Stage-aware filter validation should surface invalid stage values."""
        config = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["value"],
                    "filters": [{"type": "query", "stage": "postprocess", "query": "value > 0"}],
                }
            },
        }

        result = validation_service.validate_project(config)

        assert result.is_valid is False
        assert any("invalid filter stage" in e.message.lower() for e in result.errors)


class TestValidationServiceEntity:
    """Tests for entity-specific validation."""

    def test_validate_single_entity(self, validation_service):
        """Test validating single entity."""
        entity_data = {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id", "name", "value"]}
        project = Project(
            metadata=ProjectMetadata(
                type="shapeshifter-project",
                name="test",
                entity_count=1,
                data_provider_code="test-provider",
                provider_schema="schema-one",
            ),
            entities={"sample": entity_data},
            options={},
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
            metadata=ProjectMetadata(
                type="shapeshifter-project",
                name="test",
                entity_count=1,
                data_provider_code="test-provider",
                provider_schema="schema-one",
            ),
            entities={"sample": entity_data},
            options={},
        )

        result = validation_service.validate_entity(project, "sample")

        assert result.is_valid is False
        assert result.error_count > 0

    def test_validate_entity_filters_errors(self, validation_service):
        """Test that entity validation only returns errors for that entity."""
        project_cfg = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
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

    def test_extra_columns_errors_include_entity_field_and_expression_context(self, validation_service):
        """Derived-value validation messages should include entity, field, and expression context."""
        config = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["sample_name"],
                    "extra_columns": {
                        "sample_label": "=unknown_func(sample_name)",
                    },
                }
            },
        }

        result = validation_service.validate_project(config)

        matching_errors = [error for error in result.errors if error.field == "extra_columns.sample_label"]
        assert len(matching_errors) == 1
        assert "Entity 'sample', field 'extra_columns.sample_label':" in matching_errors[0].message
        assert "=unknown_func(sample_name)" in matching_errors[0].message

    def test_merged_entity_branch_errors_include_branch_metadata(self, validation_service):
        """Merged entity branch-scoped validation should expose branch metadata for UI grouping."""
        config = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "source": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["sample_id"],
                    "public_id": "source_id",
                },
                "analysis_entity": {
                    "type": "merged",
                    "public_id": "analysis_entity_id",
                    "branches": [
                        {"name": "abundance", "source": "missing_entity", "keys": ["sample_id"]},
                    ],
                },
            },
        }

        result = validation_service.validate_project(config)

        matching_errors = [error for error in result.errors if error.entity == "analysis_entity" and error.branch_name == "abundance"]
        assert len(matching_errors) == 1
        assert matching_errors[0].branch_source == "missing_entity"
        assert "missing_entity" in matching_errors[0].message


class TestValidationServiceIntegration:
    """Integration tests with complex configurations."""

    def test_complex_valid_configuration(self, validation_service):
        """Test complex but valid configuration."""
        config = {
            "metadata": {
                "type": "shapeshifter-project",
                "name": "test",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
            },
            "entities": {
                "data_provider": FIXED_PROVIDER_ENTITY,
                "natural_region": {
                    "type": "entity",
                    "keys": ["region_id"],
                    "columns": ["region_id", "name"],
                },
                "site": {
                    "type": "entity",
                    "keys": ["site_id"],
                    "columns": ["site_id", "name", "location"],
                },
                "sample": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": ["sample_id", "name", "site_id"],
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
    async def test_structural_errors_skip_data_validation_before_core_mapping(self):
        """Structural errors are returned without mapping, fetching, or normalizing project data."""
        project = Project(entities={"broken": {"type": "entity"}})
        project_service = Mock()
        project_service.load_project.return_value = project
        orchestrator_factory = Mock()
        service = ValidationService(data_orchestrator_factory=orchestrator_factory)

        with (
            patch("backend.app.services.validation_service.get_project_service", return_value=project_service),
            patch("backend.app.services.validation_service.ProjectMapper.to_core") as mapper,
        ):
            result = await service.validate_project_data("broken-project")

        assert result.status == DataValidationStatus.SKIPPED
        assert result.validation_mode is not None
        assert result.errors
        assert result.errors[0].category == ValidationCategory.STRUCTURAL
        assert result.entity_statuses["broken"].status == EntityDataValidationStatus.SKIPPED
        mapper.assert_not_called()
        orchestrator_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_project_data_groups_by_severity(self, reset_validation_singleton):
        """Test data validation groups issues by severity using dependency injection."""
        captured: dict[str, object] = {}

        class DummyDataValidationOrchestrator:
            status = DataValidationStatus.COMPLETED
            status_reason = None
            entity_statuses = {
                "entity1": EntityDataValidationResult(status=EntityDataValidationStatus.COMPLETED),
            }

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
        mock_api_project.model_dump.return_value = {}
        mock_api_project.filename = None
        mock_api_project.entities = {}
        mock_core_project = Mock()
        mock_core_project.cfg = {"entities": {}}

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with (
                patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project),
                patch.object(
                    validation_service_module.ValidationService,
                    "validate_project",
                    return_value=ValidationResult(
                        is_valid=True,
                        warnings=[ValidationError(severity="warning", message="Structural warning")],
                    ),
                ),
            ):
                # Inject the factory via constructor
                service = ValidationService(data_orchestrator_factory=mock_orchestrator_factory)  # type: ignore
                result = await service.validate_project_data("cfg-name", ["entity1"])

        assert result.is_valid is False
        assert result.error_count == 1
        assert result.warning_count == 2
        assert len(result.info) == 1
        assert result.status == DataValidationStatus.COMPLETED
        assert result.entity_statuses["entity1"].status == EntityDataValidationStatus.COMPLETED
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


class TestValidateTargetModel:
    """Tests for validate_target_model error-handling path."""

    def test_projects_without_target_model_return_empty_valid_result(self, validation_service: ValidationService):
        """Projects without a target model should skip conformance cleanly."""
        mock_api_project = Mock(spec=Project)
        mock_core_project = Mock()
        mock_core_project.metadata.target_model = None

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is True
        assert result.errors == []

    def test_direct_fk_declaration_without_target_model_returns_specific_error(self, validation_service: ValidationService):
        mock_api_project = Mock(spec=Project)
        mock_api_project.entities = {"location": {"foreign_key_value_sources": {"location_type": "public_id"}}}
        mock_core_project = Mock()
        mock_core_project.metadata.target_model = None

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is False
        assert [(issue.code, issue.entity, issue.field) for issue in result.errors] == [
            ("DIRECT_FK_TARGET_MODEL_UNAVAILABLE", "location", "metadata.target_model")
        ]

    def test_direct_fk_declaration_with_missing_target_model_file_returns_specific_error(self, validation_service: ValidationService):
        mock_api_project = Mock(spec=Project)
        mock_api_project.entities = {"location": {"foreign_key_value_sources": {"location_type": "public_id"}}}

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch(
                "backend.app.services.validation_service.ProjectMapper.to_core",
                side_effect=FileNotFoundError("missing_target_model.yml"),
            ):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is False
        assert result.errors[0].code == "DIRECT_FK_TARGET_MODEL_UNAVAILABLE"
        assert result.errors[0].entity == "location"

    def test_target_model_null_is_treated_as_missing(self, validation_service: ValidationService):
        """A resolved null target_model should behave the same as an absent target model."""
        mock_api_project = Mock(spec=Project)
        mock_core_project = Mock()
        mock_core_project.metadata.target_model = None

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is True
        assert result.errors == []

    def test_missing_target_model_file_is_silently_ignored(self, validation_service: ValidationService):
        """FileNotFoundError from @load resolution must be silently ignored (valid=True, no errors)."""
        mock_api_project = Mock(spec=Project)

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch(
                "backend.app.services.validation_service.ProjectMapper.to_core",
                side_effect=FileNotFoundError("No such file or directory: 'missing_target_model.yml'"),
            ):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.parametrize("include_static_error", [False, True])
    def test_conditional_foreign_key_is_returned_as_info(self, validation_service: ValidationService, include_static_error: bool):
        target_model_data = {
            "model": {"name": "Test Model", "version": "1.0.0"},
            "entities": {
                "location": {
                    "public_id": "location_id",
                    "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
                },
                "location_type": {"public_id": "location_type_id"},
            },
        }
        if include_static_error:
            target_model_data["entities"]["site"] = {"required": True, "public_id": "site_id"}

        mock_api_project = Mock(spec=Project)
        mock_core_project = ShapeShiftProject(
            cfg={
                "metadata": {
                    "name": "test-project",
                    "type": "shapeshifter-project",
                    "target_model": target_model_data,
                },
                "entities": {
                    "location": {
                        "system_id": "system_id",
                        "data": {"type": "fixed", "values": []},
                        "public_id": "location_id",
                        "columns": ["location_name"],
                    }
                },
                "options": {"validation": {"severity_overrides": {"conditional_foreign_key": "error"}}},
            },
            filename="test.yml",
        )

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                result = validation_service.validate_target_model("test-project")

        assert result.is_valid is (not include_static_error)
        assert [issue.code for issue in result.errors] == (["MISSING_REQUIRED_ENTITY"] if include_static_error else [])
        assert result.warnings == []
        assert [issue.code for issue in result.info] == ["CONDITIONAL_FK_AWAITING_RECONCILIATION"]

    def test_target_model_validation_groups_warnings_by_severity(self, validation_service: ValidationService):
        """Target-model validation should keep conformance warnings out of the error bucket."""
        mock_api_project = Mock(spec=Project)
        mock_core_project = Mock()
        mock_core_project.metadata.target_model = {"model": {"name": "Test Model", "version": "1.0.0"}, "entities": {}}

        with patch("backend.app.services.validation_service.get_project_service") as mock_get_service:
            mock_project_service = Mock()
            mock_project_service.load_project.return_value = mock_api_project
            mock_get_service.return_value = mock_project_service

            with patch("backend.app.services.validation_service.ProjectMapper.to_core", return_value=mock_core_project):
                with patch("backend.app.validators.target_model_validator.TargetModelValidator") as mock_validator_cls:
                    mock_validator = Mock()
                    mock_validator.validate.return_value = [
                        validation_service_module.ValidationError(
                            severity="warning",
                            entity="analysis_entity",
                            field=None,
                            message="Warning",
                            code="ORPHAN_FACT_ENTITY",
                            category=ValidationCategory.CONFORMANCE,
                            priority=ValidationPriority.HIGH,
                            auto_fixable=False,
                        )
                    ]
                    mock_validator_cls.return_value = mock_validator

                    result = validation_service.validate_target_model("test-project")

        assert result.is_valid is True
        assert result.errors == []
        assert [warning.code for warning in result.warnings] == ["ORPHAN_FACT_ENTITY"]
