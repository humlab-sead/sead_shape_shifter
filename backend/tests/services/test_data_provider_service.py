"""Tests for the curated data provider registry service."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.services.data_provider_service import DataProviderRegistryError, DataProviderService


def _write_provider(directory: Path, filename: str, content: str) -> Path:
    """Write one provider file and return its path."""
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def _mal_provider_yaml() -> str:
    """Return a provider record with two slash-containing schema codes."""
    return (
        "code: synthetic\n"
        "name: Synthetic Provider\n"
        "schemas:\n"
        "  - provider_schema: archeobotany/arbodat-pilot\n"
        "    scope_name: provider://synthetic/archeobotany/arbodat-pilot\n"
        "  - provider_schema: radiocarbon/strucke-pilot\n"
        "    scope_name: provider://synthetic/radiocarbon/strucke-pilot\n"
    )


def test_lists_one_provider_with_two_distinct_scopes(tmp_path: Path) -> None:
    """One provider file returns two distinct provider-schema scopes."""
    _write_provider(tmp_path, "synthetic.yml", _mal_provider_yaml())

    providers = DataProviderService(tmp_path).list_providers()

    assert len(providers) == 1
    assert providers[0].code == "synthetic"
    assert [schema.provider_schema for schema in providers[0].schemas] == [
        "archeobotany/arbodat-pilot",
        "radiocarbon/strucke-pilot",
    ]
    assert [schema.scope_name for schema in providers[0].schemas] == [
        "provider://synthetic/archeobotany/arbodat-pilot",
        "provider://synthetic/radiocarbon/strucke-pilot",
    ]


def test_pair_lookup_selects_each_registered_scope(tmp_path: Path) -> None:
    """Pair lookup returns the scope for its own provider schema."""
    _write_provider(tmp_path, "synthetic.yml", _mal_provider_yaml())
    service = DataProviderService(tmp_path)

    archeobotany = service.get_scope("synthetic", "archeobotany/arbodat-pilot")
    radiocarbon = service.get_scope("synthetic", "radiocarbon/strucke-pilot")

    assert archeobotany is not None
    assert archeobotany.scope_name == "provider://synthetic/archeobotany/arbodat-pilot"
    assert radiocarbon is not None
    assert radiocarbon.scope_name == "provider://synthetic/radiocarbon/strucke-pilot"
    assert service.get_scope("synthetic", "missing-schema") is None
    assert service.get_scope("missing-provider", "archeobotany/arbodat-pilot") is None


def test_two_providers_with_independent_schemas_are_sorted(tmp_path: Path) -> None:
    """Several provider files are returned in provider-code order with sorted schemas."""
    _write_provider(
        tmp_path, "zulu.yml", "code: zulu\nname: Zulu\nschemas:\n  - provider_schema: beta\n    scope_name: provider://zulu/beta\n"
    )
    _write_provider(
        tmp_path,
        "alpha.yml",
        "code: alpha\nname: Alpha\nschemas:\n  - provider_schema: gamma\n    scope_name: provider://alpha/gamma\n"
        "  - provider_schema: beta\n    scope_name: provider://alpha/beta\n",
    )

    providers = DataProviderService(tmp_path).list_providers()

    assert [provider.code for provider in providers] == ["alpha", "zulu"]
    assert [schema.provider_schema for schema in providers[0].schemas] == ["beta", "gamma"]


def test_empty_registry_returns_no_providers(tmp_path: Path) -> None:
    """An existing but empty directory is a valid empty registry."""
    assert DataProviderService(tmp_path).list_providers() == []


def test_missing_directory_is_an_error(tmp_path: Path) -> None:
    """A missing configured directory is an error, not an empty registry."""
    missing = tmp_path / "missing"

    with pytest.raises(DataProviderRegistryError):
        DataProviderService(missing).list_providers()
    with pytest.raises(DataProviderRegistryError):
        DataProviderService(missing).get_scope("synthetic", "archeobotany/arbodat-pilot")


def test_duplicate_provider_code_is_rejected(tmp_path: Path) -> None:
    """Two files declaring the same provider code fail the complete read."""
    _write_provider(tmp_path, "synthetic.yml", _mal_provider_yaml())
    _write_provider(
        tmp_path,
        "duplicate.yml",
        "code: synthetic\nname: Other\nschemas:\n  - provider_schema: other\n    scope_name: provider://synthetic/other\n",
    )

    with pytest.raises(DataProviderRegistryError, match="Duplicate data provider code"):
        DataProviderService(tmp_path).list_providers()


def test_duplicate_schema_code_within_provider_is_rejected(tmp_path: Path) -> None:
    """Repeating a provider schema inside one provider fails the complete read."""
    _write_provider(
        tmp_path,
        "synthetic.yml",
        "code: synthetic\nname: Synthetic\nschemas:\n"
        "  - provider_schema: archeobotany/arbodat-pilot\n"
        "    scope_name: provider://synthetic/archeobotany/arbodat-pilot\n"
        "  - provider_schema: archeobotany/arbodat-pilot\n"
        "    scope_name: provider://synthetic/archeobotany/arbodat-pilot\n",
    )

    with pytest.raises(DataProviderRegistryError, match="duplicate provider_schema"):
        DataProviderService(tmp_path).list_providers()


def test_duplicate_scope_name_across_providers_is_rejected(tmp_path: Path) -> None:
    """Two distinct providers cannot register the same scope name."""
    _write_provider(
        tmp_path,
        "parent.yml",
        "code: parent\nname: Parent\nschemas:\n  - provider_schema: child/pilot\n    scope_name: provider://parent/child/pilot\n",
    )
    _write_provider(
        tmp_path,
        "nested.yml",
        "code: parent/child\nname: Nested\nschemas:\n  - provider_schema: pilot\n    scope_name: provider://parent/child/pilot\n",
    )

    with pytest.raises(DataProviderRegistryError, match="Duplicate scope name"):
        DataProviderService(tmp_path).list_providers()


def test_mismatched_scope_name_is_rejected(tmp_path: Path) -> None:
    """A scope name that does not match its provider-schema pair fails the read."""
    _write_provider(
        tmp_path,
        "synthetic.yml",
        "code: synthetic\nname: Synthetic\nschemas:\n"
        "  - provider_schema: archeobotany/arbodat-pilot\n"
        "    scope_name: provider://other/archeobotany/arbodat-pilot\n",
    )

    with pytest.raises(DataProviderRegistryError, match="must equal"):
        DataProviderService(tmp_path).list_providers()


def test_blank_field_is_rejected(tmp_path: Path) -> None:
    """A blank provider field fails the read."""
    _write_provider(
        tmp_path,
        "synthetic.yml",
        "code: '   '\nname: Synthetic\nschemas:\n  - provider_schema: beta\n    scope_name: provider://synthetic/beta\n",
    )

    with pytest.raises(DataProviderRegistryError, match="must not be blank"):
        DataProviderService(tmp_path).list_providers()


@pytest.mark.parametrize(
    "extra_field",
    [
        "data_provider_id: 42",
        "scope_uuid: 7f0f5b1e-0000-0000-0000-000000000000",
    ],
)
def test_extra_fields_are_rejected(tmp_path: Path, extra_field: str) -> None:
    """Target IDs and other unregistered fields fail the read."""
    _write_provider(
        tmp_path,
        "synthetic.yml",
        f"code: synthetic\nname: Synthetic\n{extra_field}\nschemas:\n"
        "  - provider_schema: beta\n    scope_name: provider://synthetic/beta\n",
    )

    with pytest.raises(DataProviderRegistryError):
        DataProviderService(tmp_path).list_providers()


def test_provider_without_schemas_is_rejected(tmp_path: Path) -> None:
    """A provider must declare at least one schema."""
    _write_provider(tmp_path, "synthetic.yml", "code: synthetic\nname: Synthetic\nschemas: []\n")

    with pytest.raises(DataProviderRegistryError):
        DataProviderService(tmp_path).list_providers()


def test_malformed_yaml_is_rejected(tmp_path: Path) -> None:
    """Unparsable YAML fails the read instead of being skipped."""
    _write_provider(tmp_path, "broken.yml", "code: [unclosed\n")

    with pytest.raises(DataProviderRegistryError, match="not valid YAML"):
        DataProviderService(tmp_path).list_providers()


def test_non_mapping_document_is_rejected(tmp_path: Path) -> None:
    """A provider file that is not a mapping fails the read."""
    _write_provider(tmp_path, "list.yml", "- code: synthetic\n")

    with pytest.raises(DataProviderRegistryError, match="must contain a mapping"):
        DataProviderService(tmp_path).list_providers()


def test_invalid_file_rejects_the_valid_files_too(tmp_path: Path) -> None:
    """A valid provider is not returned when another file in the registry is invalid."""
    _write_provider(tmp_path, "synthetic.yml", _mal_provider_yaml())
    _write_provider(tmp_path, "broken.yml", "code: [unclosed\n")

    with pytest.raises(DataProviderRegistryError):
        DataProviderService(tmp_path).list_providers()


def test_non_yaml_files_are_ignored(tmp_path: Path) -> None:
    """Only .yml provider files are read from the directory."""
    _write_provider(tmp_path, "synthetic.yml", _mal_provider_yaml())
    _write_provider(tmp_path, "README.txt", "not a provider record")

    providers = DataProviderService(tmp_path).list_providers()

    assert [provider.code for provider in providers] == ["synthetic"]


def test_directive_text_is_stored_literally(tmp_path: Path) -> None:
    """Provider values are not expanded through directives or environment variables."""
    _write_provider(
        tmp_path,
        "synthetic.yml",
        "code: synthetic\nname: '${SHAPE_SHIFTER_ENVIRONMENT}'\nschemas:\n"
        "  - provider_schema: beta\n    scope_name: provider://synthetic/beta\n",
    )

    providers = DataProviderService(tmp_path).list_providers()

    assert providers[0].name == "${SHAPE_SHIFTER_ENVIRONMENT}"
