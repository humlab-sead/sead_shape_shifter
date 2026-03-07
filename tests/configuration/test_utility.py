"""Tests for src.configuration.utility helpers."""

from src.configuration.utility import replace_references


def test_replace_references_simple_include() -> None:
    """@value directive should copy referenced data."""
    data: dict = {"base": {"letters": ["a", "b"]}, "copy": "@value: base.letters"}

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["copy"] == ["a", "b"]


def test_replace_references_list_operations() -> None:
    """List operations should concatenate literal lists and referenced lists."""
    data: dict = {"base": ["a"], "combined": "@value: base + ['b', 'c']"}

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["combined"] == ["a", "b", "c"]


def test_replace_references_ignores_nested_list_expression() -> None:
    """Invalid nested list expressions should be returned unchanged."""
    expr = "@value: base + [['nested']]"
    data: dict = {"base": ["x"], "bad": expr}

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["bad"] == expr


def test_replace_references_directive_as_list_element() -> None:
    """@value: directive as a YAML list element should be flattened into the surrounding list."""
    data: dict = {
        "parent_keys": ["a", "b"],
        "child_keys": ["@value: parent_keys", "c"],
    }

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["child_keys"] == ["a", "b", "c"]


def test_replace_references_multiple_directive_list_elements() -> None:
    """Multiple @value: directives as list elements should each be flattened."""
    data: dict = {
        "list_a": ["x"],
        "list_b": ["y", "z"],
        "combined": ["@value: list_a", "@value: list_b"],
    }

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["combined"] == ["x", "y", "z"]


def test_replace_references_directive_list_element_scalar_result_not_flattened() -> None:
    """A @value: item in a list that resolves to a scalar should be appended (not extended)."""
    data: dict = {
        "single": "hello",
        "mixed": ["@value: single", "world"],
    }

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["mixed"] == ["hello", "world"]


def test_replace_references_plain_list_unchanged() -> None:
    """A plain list with no directives should remain exactly as-is."""
    data: dict = {"plain": ["a", "b", "c"]}

    resolved: dict = replace_references(data)  # type: ignore

    assert resolved["plain"] == ["a", "b", "c"]
