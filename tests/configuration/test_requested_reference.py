"""Tests for scoped resolution of one requested configuration reference."""

import copy
from pathlib import Path

import pytest

from src.configuration.resolve import (
    RequestedReferenceResolutionError,
    resolve_requested_reference,
    resolve_requested_references,
    split_reference_expression,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("@value: entities.source.keys + ['last']", ["@value: entities.source.keys", "['last']"]),
        ("['first'] + @value: entities.source.keys", ["['first']", "@value: entities.source.keys"]),
        (
            "@value: entities.first.keys + ['middle'] + @value: entities.last.keys",
            ["@value: entities.first.keys", "['middle']", "@value: entities.last.keys"],
        ),
    ],
)
def test_split_reference_expression_keeps_supported_operands_in_order(expression: str, expected: list[str]) -> None:
    """Expose supported value paths and list literals without changing their order."""
    assert split_reference_expression(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "@value: entities.source.keys +",
        "@value: entities.source.keys + + ['last']",
        "@value: entities.source.keys + ['last'",
        "['first'] + @value: entities.source.keys]",
        "@value: entities.source.keys + unsupported",
        "@value: entities.source.keys + {'key': 'value'}",
    ],
)
def test_split_reference_expression_rejects_malformed_or_unsupported_operands(expression: str) -> None:
    """Reject incomplete expressions and tokens the scoped resolver cannot evaluate."""
    assert split_reference_expression(expression) is None


def test_resolves_nested_and_list_item_references_in_order() -> None:
    """Resolve nested references and flatten list-item references without changing order."""
    config = {
        "entities": {
            "source": {"keys": ["first", "second"]},
            "middle": {"keys": "@value: entities.source.keys"},
            "child": {"keys": ["before", "@value: entities.middle.keys", "after"]},
        },
    }

    result = resolve_requested_reference(config, "entities.child.keys")

    assert result == ["before", "first", "second", "after"]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("@value: entities.source.keys + ['last']", ["first", "second", "last"]),
        ("['first'] + @value: entities.source.keys", ["first", "first", "second"]),
    ],
)
def test_resolves_supported_expression_operands_in_order(expression: str, expected: list[str]) -> None:
    """Keep source columns and literal columns in their expression order."""
    config = {"entities": {"source": {"keys": ["first", "second"]}, "child": {"keys": expression}}}

    assert resolve_requested_reference(config, "entities.child.keys") == expected


def test_unrelated_missing_cycle_and_file_directives_do_not_block_requested_path() -> None:
    """Do not resolve invalid directives outside the requested dependency chain."""
    config = {
        "entities": {
            "source": {"keys": ["first", "second"]},
            "child": {"keys": "@value: entities.source.keys"},
            "missing": {"keys": "@value: entities.unknown.keys"},
            "cycle_a": {"keys": "@value: entities.cycle_b.keys"},
            "cycle_b": {"keys": "@value: entities.cycle_a.keys"},
            "file": {"keys": "@include: missing.yml"},
        },
    }

    assert resolve_requested_reference(config, "entities.child.keys") == ["first", "second"]


def test_reports_missing_and_circular_requested_dependencies() -> None:
    """Classify missing paths and cycles in the requested dependency chain."""
    missing_config = {"entities": {"child": {"keys": "@value: entities.unknown.keys"}}}
    cycle_config = {
        "entities": {
            "first": {"keys": "@value: entities.second.keys"},
            "second": {"keys": "@value: entities.first.keys"},
        }
    }

    with pytest.raises(RequestedReferenceResolutionError) as missing_error:
        resolve_requested_reference(missing_config, "entities.child.keys")
    with pytest.raises(RequestedReferenceResolutionError) as cycle_error:
        resolve_requested_reference(cycle_config, "entities.first.keys")

    assert missing_error.value.reason_code == "missing_path"
    assert cycle_error.value.reason_code == "circular_reference"


def test_resolves_several_paths_and_reports_each_failure() -> None:
    """Return one result per path and keep a broken path from hiding the others."""
    config = {
        "entities": {
            "source": {"keys": ["first", "second"]},
            "child": {"keys": "@value: entities.source.keys", "columns": "@value: entities.unknown.columns"},
        },
    }

    results = resolve_requested_references(
        config,
        ["entities.source.keys", "entities.child.keys", "entities.child.columns"],
    )

    assert results["entities.source.keys"] == ["first", "second"]
    assert results["entities.child.keys"] == ["first", "second"]
    failure = results["entities.child.columns"]
    assert isinstance(failure, RequestedReferenceResolutionError)
    assert failure.reason_code == "missing_path"


def test_expression_with_only_empty_operands_resolves_to_no_columns() -> None:
    """Accept an empty result the same way a simple reference to an empty list is accepted."""
    config = {
        "entities": {
            "empty": {"keys": []},
            "child": {"keys": "@value: entities.empty.keys + []"},
        },
    }

    assert resolve_requested_reference(config, "entities.child.keys") == []


def test_does_not_return_expression_values_when_an_operand_is_missing() -> None:
    """Reject a missing operand instead of returning a shortened expression result."""
    config = {"entities": {"child": {"keys": "@value: entities.missing.keys + ['literal']"}}}

    with pytest.raises(RequestedReferenceResolutionError) as error:
        resolve_requested_reference(config, "entities.child.keys")

    assert error.value.reason_code == "missing_path"


def test_resolves_allowed_environment_values_only_in_the_requested_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve approved environment variables in reached values and ignore unrelated values."""
    monkeypatch.setenv("SS_ALLOWED_COLUMN", "approved")
    monkeypatch.setenv("SS_UNRELATED_COLUMN", "unrelated")
    config = {
        "entities": {
            "source": {"keys": ["${SS_ALLOWED_COLUMN}"]},
            "child": {"keys": "@value: entities.source.keys"},
            "unrelated": {"keys": ["${SS_UNRELATED_COLUMN}"]},
        },
    }

    result = resolve_requested_reference(
        config,
        "entities.child.keys",
        allowed_vars=frozenset({"SS_ALLOWED_COLUMN"}),
    )

    assert result == ["approved"]


def test_resolves_only_requested_include_and_keeps_input_unchanged(tmp_path: Path) -> None:
    """Load a reached include under an allowed root and leave the source mapping unchanged."""
    project_file = tmp_path / "shapeshifter.yml"
    project_file.write_text("entities: {}", encoding="utf-8")
    included_file = tmp_path / "included.yml"
    included_file.write_text("keys: [one, two]", encoding="utf-8")
    config = {
        "entities": {
            "child": "@include: included.yml",
            "unrelated": {"keys": "@include: absent.yml"},
        },
    }
    original = copy.deepcopy(config)

    result = resolve_requested_reference(
        config,
        "entities.child.keys",
        source_path=str(project_file),
        allowed_roots=(tmp_path,),
    )

    assert result == ["one", "two"]
    assert config == original


def test_requested_file_failure_is_classified_and_confined(tmp_path: Path) -> None:
    """Return a local dependency failure for a requested file outside allowed roots."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_file = project_root / "shapeshifter.yml"
    project_file.write_text("entities: {}", encoding="utf-8")
    outside_file = tmp_path / "outside.yml"
    outside_file.write_text("keys: [hidden]", encoding="utf-8")
    config = {"entities": {"child": {"keys": f"@include: {outside_file}"}}}

    with pytest.raises(RequestedReferenceResolutionError) as error:
        resolve_requested_reference(
            config,
            "entities.child.keys",
            source_path=str(project_file),
            allowed_roots=(project_root,),
        )

    assert error.value.reason_code == "dependency_failure"
