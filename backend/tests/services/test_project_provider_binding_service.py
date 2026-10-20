"""Tests for project provider-schema validation and save rules."""

# pylint: disable=redefined-outer-name

import pytest

from backend.app.services.data_provider_service import DataProviderService
from backend.app.services.project_provider_binding_service import (
    ProjectProviderBindingError,
    ProjectProviderBindingService,
    ProjectProviderRegistryUnavailable,
)


@pytest.fixture
def binding_service(tmp_path):
    registry_dir = tmp_path / "providers"
    registry_dir.mkdir()
    (registry_dir / "provider.yml").write_text(
        """
code: test-provider
name: Test Provider
schemas:
  - provider_schema: schema-one
    scope_name: provider://test-provider/schema-one
  - provider_schema: schema-two
    scope_name: provider://test-provider/schema-two
""".lstrip(),
        encoding="utf-8",
    )
    return ProjectProviderBindingService(DataProviderService(registry_dir))


def test_validation_errors_are_field_specific_for_missing_partial_and_blank_values(binding_service):
    assert {error.field for error in binding_service.validation_errors({})} == {
        "metadata.data_provider_code",
        "metadata.provider_schema",
    }
    assert [error.field for error in binding_service.validation_errors({"data_provider_code": "test-provider"})] == [
        "metadata.provider_schema"
    ]
    assert [error.field for error in binding_service.validation_errors({"data_provider_code": " ", "provider_schema": "schema-one"})] == [
        "metadata.data_provider_code"
    ]


def test_registered_schemas_pass_and_unregistered_pair_fails_both_fields(binding_service):
    assert binding_service.validation_errors({"data_provider_code": "test-provider", "provider_schema": "schema-one"}) == []
    errors = binding_service.validation_errors({"data_provider_code": "test-provider", "provider_schema": "unknown"})
    assert {error.field for error in errors} == {"metadata.data_provider_code", "metadata.provider_schema"}


def test_existing_unbound_project_can_receive_one_registered_pair(binding_service):
    binding_service.validate_write({}, {})
    binding_service.validate_write(
        {},
        {"data_provider_code": "test-provider", "provider_schema": "schema-one"},
    )

    with pytest.raises(ProjectProviderBindingError):
        binding_service.validate_write({}, {"data_provider_code": "test-provider"})


@pytest.mark.parametrize(
    ("candidate", "changed_field"),
    [
        ({"data_provider_code": "other-provider", "provider_schema": "schema-one"}, "metadata.data_provider_code"),
        ({"data_provider_code": "test-provider", "provider_schema": "schema-two"}, "metadata.provider_schema"),
        ({"data_provider_code": None, "provider_schema": "schema-one"}, "metadata.data_provider_code"),
        ({"data_provider_code": "test-provider", "provider_schema": None}, "metadata.provider_schema"),
    ],
)
def test_assigned_pair_cannot_be_changed_or_removed(binding_service, candidate, changed_field):
    current = {"data_provider_code": "test-provider", "provider_schema": "schema-one"}
    with pytest.raises(ProjectProviderBindingError) as error:
        binding_service.validate_write(current, candidate)
    assert changed_field in {issue.field for issue in error.value.errors}


def test_malformed_registry_is_not_reported_as_an_unregistered_pair(tmp_path):
    registry_dir = tmp_path / "providers"
    registry_dir.mkdir()
    (registry_dir / "provider.yml").write_text("code: [", encoding="utf-8")
    service = ProjectProviderBindingService(DataProviderService(registry_dir))

    with pytest.raises(ProjectProviderRegistryUnavailable, match="Data provider registry is unavailable"):
        service.validation_errors({"data_provider_code": "test-provider", "provider_schema": "schema-one"})
