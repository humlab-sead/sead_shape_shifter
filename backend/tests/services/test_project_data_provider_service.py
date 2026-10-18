"""Tests for the fixed SEAD data provider row and the trusted Change Request context."""

from typing import Any

import pytest

from backend.app.core.config import settings
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.data_provider_service import DataProviderService
from backend.app.services.project_data_provider_service import (
    FixedProviderRow,
    ProjectDataProviderError,
    ProjectDataProviderService,
)
from backend.app.services.project_provider_binding_service import ProjectProviderBindingError, ProjectProviderBindingService

# pylint: disable=redefined-outer-name


@pytest.fixture
def service() -> ProjectDataProviderService:
    """Build the service against the isolated test provider registry."""
    provider_service = DataProviderService(settings.global_data_provider_dir)
    return ProjectDataProviderService(provider_service, ProjectProviderBindingService(provider_service))


def _entities(provider_id: Any = 51, provider_code: Any = "test-provider", extra_keys: list[str] | None = None) -> dict[str, Any]:
    """Build fixed entities for a synthetic project."""
    return {
        "data_provider": {
            "type": "fixed",
            "public_id": "data_provider_id",
            "keys": ["data_provider_code"],
            "columns": ["data_provider_id", "data_provider_code"],
            "values": [[provider_id, provider_code]],
        },
        "site": {
            "type": "fixed",
            "public_id": "site_id",
            "keys": extra_keys if extra_keys is not None else ["site_code", "site_name"],
            "columns": ["site_id", "site_code", "site_name"],
            "values": [[1, "S1", "Site one"]],
        },
    }


def _project_config(entities: dict[str, Any] | None = None, *, provider_code: str = "test-provider") -> dict[str, Any]:
    """Build a resolved project configuration dictionary."""
    return {
        "metadata": {"data_provider_code": provider_code, "provider_schema": "schema-one"},
        "entities": _entities() if entities is None else entities,
    }


def _api_project(entities: dict[str, Any] | None = None) -> Project:
    """Build an API project model for mapping tests."""
    resolved_entities = _entities() if entities is None else entities
    return Project(
        metadata=ProjectMetadata(
            name="pilot",
            data_provider_code="test-provider",
            provider_schema="schema-one",
            entity_count=len(resolved_entities),
        ),
        entities=resolved_entities,
        options={},
    )


class TestFixedRowErrors:
    """Structural checks that never read the target database."""

    def test_accepts_one_matching_fixed_row(self, service: ProjectDataProviderService):
        assert service.fixed_row_errors(_project_config()) == []

    def test_requires_the_data_provider_entity(self, service: ProjectDataProviderService):
        errors = service.fixed_row_errors({"metadata": {"data_provider_code": "test-provider"}, "entities": {}})

        assert [error.field for error in errors] == ["entities.data_provider"]
        assert "fixed 'data_provider' entity" in errors[0].message

    def test_requires_fixed_type(self, service: ProjectDataProviderService):
        entities = _entities()
        entities["data_provider"]["type"] = "entity"

        errors = service.fixed_row_errors(_project_config(entities))

        assert [error.field for error in errors] == ["entities.data_provider.type"]

    def test_requires_provider_public_id(self, service: ProjectDataProviderService):
        entities = _entities()
        entities["data_provider"]["public_id"] = "provider_id"

        errors = service.fixed_row_errors(_project_config(entities))

        assert "entities.data_provider.public_id" in [error.field for error in errors]

    def test_requires_provider_code_as_the_only_key(self, service: ProjectDataProviderService):
        entities = _entities()
        entities["data_provider"]["keys"] = ["data_provider_code", "data_provider_name"]

        errors = service.fixed_row_errors(_project_config(entities))

        assert [error.field for error in errors] == ["entities.data_provider.keys"]

    @pytest.mark.parametrize("values", [[], [[51, "test-provider"], [52, "test-provider"]]])
    def test_requires_exactly_one_row(self, service: ProjectDataProviderService, values: list[list[Any]]):
        entities = _entities()
        entities["data_provider"]["values"] = values

        errors = service.fixed_row_errors(_project_config(entities))

        assert any("exactly one row" in error.message for error in errors)

    @pytest.mark.parametrize("provider_id", [None, "abc", -1, 0, True])
    def test_requires_a_positive_integer_id(self, service: ProjectDataProviderService, provider_id: Any):
        errors = service.fixed_row_errors(_project_config(_entities(provider_id=provider_id)))

        assert any(error.field == "entities.data_provider.data_provider_id" for error in errors)

    def test_requires_a_nonblank_code(self, service: ProjectDataProviderService):
        errors = service.fixed_row_errors(_project_config(_entities(provider_code="   ")))

        assert any(error.field == "entities.data_provider.data_provider_code" for error in errors)

    def test_requires_code_to_match_metadata(self, service: ProjectDataProviderService):
        errors = service.fixed_row_errors(_project_config(_entities(provider_code="other-provider")))

        assert [error.field for error in errors] == ["metadata.data_provider_code"]
        assert "must match the project data provider code" in errors[0].message


class TestRequireFixedRow:
    """Reads from a mapped project instead of a raw dictionary."""

    def test_returns_the_fixed_row(self, service: ProjectDataProviderService):
        from backend.app.mappers.project_mapper import ProjectMapper  # pylint: disable=import-outside-toplevel

        core_project = ProjectMapper.to_core(_api_project())

        row = service.require_fixed_row(core_project, "test-provider")

        assert row == FixedProviderRow(data_provider_id=51, data_provider_code="test-provider")

    def test_rejects_a_different_saved_code(self, service: ProjectDataProviderService):
        from backend.app.mappers.project_mapper import ProjectMapper  # pylint: disable=import-outside-toplevel

        core_project = ProjectMapper.to_core(_api_project())

        with pytest.raises(ProjectDataProviderError, match="must match the project data provider code"):
            service.require_fixed_row(core_project, "other-provider")


class TestBuildTrustedContext:
    """Backend-owned scope, provider row, and ordered keys for one project."""

    def test_builds_scope_provider_and_ordered_keys(self, service: ProjectDataProviderService):
        context = service.build_trusted_context(_api_project())

        assert context.project_name == "pilot"
        assert context.provider_code == "test-provider"
        assert context.provider_schema == "schema-one"
        assert context.scope_name == "provider://test-provider/schema-one"
        assert context.data_provider_id == 51
        assert context.business_keys["site"] == ("site_code", "site_name")
        assert context.business_keys["data_provider"] == ("data_provider_code",)

    def test_preserves_declared_key_order(self, service: ProjectDataProviderService):
        context = service.build_trusted_context(_api_project(_entities(extra_keys=["site_name", "site_code"])))

        assert context.business_keys["site"] == ("site_name", "site_code")

    def test_uses_the_saved_schema_scope(self, service: ProjectDataProviderService):
        project = _api_project()
        assert project.metadata is not None
        project.metadata.provider_schema = "schema-two"

        assert service.build_trusted_context(project).scope_name == "provider://test-provider/schema-two"

    def test_rejects_an_unregistered_pair(self, service: ProjectDataProviderService):
        project = _api_project()
        assert project.metadata is not None
        project.metadata.provider_schema = "unknown-schema"

        with pytest.raises(ProjectProviderBindingError, match="not registered"):
            service.build_trusted_context(project)
