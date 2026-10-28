"""Tests for @value: reference resolution (ReferenceResolver)."""

from src.configuration.resolve import ReferenceResolver, resolve_directives
from src.specifications.project import CompositeProjectSpecification


def _resolve(data: dict) -> dict:
    """Shorthand for resolving @value: references."""
    return ReferenceResolver().resolve_all(data)  # type: ignore[return-value]


def test_replace_references_simple_include() -> None:
    """@value directive should copy referenced data."""
    data: dict = {"base": {"letters": ["a", "b"]}, "copy": "@value: base.letters"}

    resolved: dict = _resolve(data)

    assert resolved["copy"] == ["a", "b"]


def test_replace_references_list_operations() -> None:
    """List operations should concatenate literal lists and referenced lists."""
    data: dict = {"base": ["a"], "combined": "@value: base + ['b', 'c']"}

    resolved: dict = _resolve(data)

    assert resolved["combined"] == ["a", "b", "c"]


def test_replace_references_ignores_nested_list_expression() -> None:
    """Invalid nested list expressions should be returned unchanged."""
    expr = "@value: base + [['nested']]"
    data: dict = {"base": ["x"], "bad": expr}

    resolved: dict = _resolve(data)

    assert resolved["bad"] == expr


def test_replace_references_directive_as_list_element() -> None:
    """@value: directive as a YAML list element should be flattened into the surrounding list."""
    data: dict = {
        "parent_keys": ["a", "b"],
        "child_keys": ["@value: parent_keys", "c"],
    }

    resolved: dict = _resolve(data)

    assert resolved["child_keys"] == ["a", "b", "c"]


def test_replace_references_multiple_directive_list_elements() -> None:
    """Multiple @value: directives as list elements should each be flattened."""
    data: dict = {
        "list_a": ["x"],
        "list_b": ["y", "z"],
        "combined": ["@value: list_a", "@value: list_b"],
    }

    resolved: dict = _resolve(data)

    assert resolved["combined"] == ["x", "y", "z"]


def test_replace_references_directive_list_element_scalar_result_not_flattened() -> None:
    """A @value: item in a list that resolves to a scalar should be appended (not extended)."""
    data: dict = {
        "single": "hello",
        "mixed": ["@value: single", "world"],
    }

    resolved: dict = _resolve(data)

    assert resolved["mixed"] == ["hello", "world"]


def test_replace_references_plain_list_unchanged() -> None:
    """A plain list with no directives should remain exactly as-is."""
    data: dict = {"plain": ["a", "b", "c"]}

    resolved: dict = _resolve(data)

    assert resolved["plain"] == ["a", "b", "c"]


def test_replace_references_with_space_after_directive() -> None:
    """@value: directive with space after colon should work identically to no space."""
    data: dict = {
        "base": {"letters": ["a", "b", "c"]},
        "no_space": "@value:base.letters",
        "with_space": "@value: base.letters",  # Space after colon
        "list_op": "@value: base.letters + ['d']",  # Space in list operation
    }

    resolved: dict = _resolve(data)

    # Both should resolve to the same value
    assert resolved["no_space"] == ["a", "b", "c"]
    assert resolved["with_space"] == ["a", "b", "c"]
    assert resolved["list_op"] == ["a", "b", "c", "d"]


def test_resolve_directives_flattens_list_references_and_preserves_other_forms() -> None:
    data: dict = {
        "base": ["id", "name"],
        "columns": ["local_id", "@value: base", "created_at"],
        "scalar": "label",
        "scalar_copy": "@value: scalar",
        "extended": "@value: base + ['created_at']",
    }

    resolved: dict = resolve_directives(data)

    assert resolved["columns"] == ["local_id", "id", "name", "created_at"]
    assert resolved["scalar_copy"] == "label"
    assert resolved["extended"] == ["id", "name", "created_at"]


def test_resolve_directives_list_reference_passes_project_validation() -> None:
    project_cfg: dict = {
        "metadata": {"type": "shapeshifter-project"},
        "entities": {
            "source": {
                "type": "sql",
                "columns": ["id", "name"],
                "keys": ["id"],
                "data_source": "db1",
                "query": "SELECT id, name FROM source",
            },
            "child": {
                "type": "sql",
                "columns": ["@value: entities.source.columns"],
                "keys": ["id"],
                "data_source": "db1",
                "query": "SELECT id FROM child",
            },
        },
        "options": {"data_sources": {"db1": {"driver": "postgresql"}}},
    }

    resolved: dict = resolve_directives(project_cfg)
    validator = CompositeProjectSpecification(resolved)

    assert validator.is_satisfied_by()
