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
