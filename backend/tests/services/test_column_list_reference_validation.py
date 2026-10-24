"""Tests for raw saved-project column-list reference checks."""

from copy import deepcopy

import pytest

from backend.app.services.column_list_reference_validation import ColumnListReferenceValidationService


@pytest.fixture(name="validator")
def _validator() -> ColumnListReferenceValidationService:
    """Create a reference validator for one test."""
    return ColumnListReferenceValidationService()


def make_project(entities: dict, options: dict | None = None) -> dict:
    """Build a raw project configuration for reference checks."""
    return {
        "metadata": {"name": "reference_test"},
        "entities": entities,
        "options": options or {},
    }


def test_scans_each_supported_field_and_keeps_list_indexes(validator: ColumnListReferenceValidationService) -> None:
    """Report references from scalar/list fields and both foreign-key storage forms."""
    project_cfg = make_project(
        {
            "source": {"keys": ["id"], "columns": ["id"]},
            "child": {
                "keys": "@value: entities.missing.keys",
                "columns": ["name", "@value: entities.missing.columns"],
                "foreign_keys": [
                    {
                        "local_keys": ["local", "@value: entities.missing.local"],
                        "remote_keys": "@value: entities.missing.remote",
                    }
                ],
                "unnest": {
                    "id_vars": "@value: entities.missing.ids",
                    "value_vars": ["value", "@value: entities.missing.values"],
                },
                "drop_duplicates": {"columns": ["@value: entities.missing.duplicates"]},
                "drop_empty_rows": "@value: entities.missing.empty_rows",
            },
            "legacy_fk": {
                "foreign_keys": {
                    "site": {
                        "local_keys": "@value: entities.missing.legacy_local",
                        "remote_keys": ["@value: entities.missing.legacy_remote"],
                    }
                }
            },
        }
    )

    errors = validator.validate(project_cfg)

    assert [error.field for error in errors] == [
        "keys",
        "columns[1]",
        "foreign_keys[0].local_keys[1]",
        "foreign_keys[0].remote_keys",
        "unnest.id_vars",
        "unnest.value_vars[1]",
        "drop_duplicates.columns[0]",
        "drop_empty_rows",
        "foreign_keys.site.local_keys",
        "foreign_keys.site.remote_keys[0]",
    ]
    assert all(error.entity in {"child", "legacy_fk"} for error in errors)
    assert all(error.code == "COLUMN_REFERENCE_MISSING_PATH" for error in errors)
    assert all(error.category.value == "structural" for error in errors)
    assert "@value: entities.missing.keys" in errors[0].message


def test_ignores_booleans_literals_and_fixed_entity_columns(validator: ColumnListReferenceValidationService) -> None:
    """Skip boolean row options and Fixed Entity Columns while checking other fields."""
    project_cfg = make_project(
        {
            "fixed": {
                "type": "fixed",
                "keys": ["@value: entities.missing.fixed_key"],
                "columns": ["@value: entities.missing.fixed_column"],
                "drop_duplicates": True,
                "drop_empty_rows": False,
            },
            "ordinary": {
                "type": "entity",
                "keys": ["literal", True],
                "columns": ["@value: entities.missing.column"],
                "drop_duplicates": False,
                "drop_empty_rows": True,
            },
        }
    )

    errors = validator.validate(project_cfg)

    assert [(error.entity, error.field) for error in errors] == [
        ("fixed", "keys[0]"),
        ("ordinary", "columns[0]"),
    ]
    assert all("fixed_column" not in error.message for error in errors)


def test_requires_string_lists_for_simple_references_and_accepts_empty_lists(
    validator: ColumnListReferenceValidationService,
) -> None:
    """Accept ordered string lists and empty lists, and reject scalar or mixed values."""
    project_cfg = make_project(
        {
            "source": {
                "keys": ["one", "two", "one"],
                "empty": [],
                "scalar": "one",
                "number": 12,
                "mixed": ["one", 12],
            },
            "child": {
                "keys": "@value: entities.source.keys",
                "columns": [
                    "@value: entities.source.empty",
                    "@value: entities.source.scalar",
                    "@value: entities.source.number",
                    "@value: entities.source.mixed",
                    "before",
                    "@value: entities.source.keys",
                    "@value: entities.source.scalar",
                ],
            },
        }
    )

    errors = validator.validate(project_cfg)

    assert [(error.field, error.code) for error in errors] == [
        ("columns[1]", "COLUMN_REFERENCE_WRONG_TYPE"),
        ("columns[2]", "COLUMN_REFERENCE_WRONG_TYPE"),
        ("columns[3]", "COLUMN_REFERENCE_WRONG_TYPE"),
        ("columns[6]", "COLUMN_REFERENCE_WRONG_TYPE"),
    ]


def test_classifies_nested_and_circular_reference_failures(validator: ColumnListReferenceValidationService) -> None:
    """Classify a failed dependency separately from a reference cycle."""
    project_cfg = make_project(
        {
            "nested": {"keys": "@include: missing.yml"},
            "child": {"keys": "@value: entities.nested.keys"},
            "cycle_a": {"keys": "@value: entities.cycle_b.keys"},
            "cycle_b": {"keys": "@value: entities.cycle_a.keys"},
        }
    )

    errors = validator.validate(project_cfg)

    assert any(error.entity == "child" and error.code == "COLUMN_REFERENCE_DEPENDENCY_FAILURE" for error in errors)
    assert any(error.code == "COLUMN_REFERENCE_CIRCULAR_REFERENCE" for error in errors)


def test_checks_each_expression_operand_and_validates_scalar_and_list_item_results(
    validator: ColumnListReferenceValidationService,
) -> None:
    """Keep both legacy operand orders and apply existing list-item flattening rules."""
    project_cfg = make_project(
        {
            "source": {"keys": ["first", "second"], "scalar": "one"},
            "child": {
                "keys": "@value: entities.source.keys + ['last']",
                "columns": [
                    "@value: entities.source.scalar + ['tail']",
                    "@value: entities.source.keys + ['flattened']",
                    "['not flattened'] + @value: entities.source.keys",
                ],
                "drop_duplicates": "['before'] + @value: entities.source.keys",
            },
        }
    )

    errors = validator.validate(project_cfg)

    assert [(error.field, error.code) for error in errors] == [("columns[2]", "COLUMN_REFERENCE_WRONG_TYPE")]
    assert "['not flattened'] + @value: entities.source.keys" in errors[0].message


def test_reports_every_missing_expression_operand_without_repeating_expression_error(
    validator: ColumnListReferenceValidationService,
) -> None:
    """Report multiple missing paths independently with the full saved expression."""
    expression = "@value: entities.missing.first + @value: entities.missing.second + ['literal']"
    project_cfg = make_project({"child": {"keys": expression}})

    errors = validator.validate(project_cfg)

    assert len(errors) == 2
    assert [error.code for error in errors] == ["COLUMN_REFERENCE_MISSING_PATH"] * 2
    assert all(error.field == "keys" for error in errors)
    assert all(expression in error.message for error in errors)
    assert "entities.missing.first" in errors[0].message
    assert "entities.missing.second" in errors[1].message


@pytest.mark.parametrize(
    "expression",
    [
        "@value: entities.source.keys +",
        "['first'] + @value: entities.source.keys]",
        "@value: entities.source.keys + unsupported",
    ],
)
def test_reports_malformed_legacy_expressions(validator: ColumnListReferenceValidationService, expression: str) -> None:
    """Report malformed or unsupported expression syntax at its saved field."""
    errors = validator.validate(make_project({"child": {"keys": expression}}))

    assert len(errors) == 1
    assert errors[0].code == "COLUMN_REFERENCE_EXPRESSION_INVALID"
    assert errors[0].field == "keys"
    assert expression in errors[0].message


def test_keeps_valid_reference_results_when_an_unrelated_path_is_broken(
    validator: ColumnListReferenceValidationService,
) -> None:
    """Resolve a valid path independently of a separate missing path and preserve source data."""
    project_cfg = make_project(
        {
            "source": {"keys": ["first", "second"]},
            "valid_child": {"keys": "@value: entities.source.keys"},
            "broken_child": {"keys": "@value: entities.missing.keys"},
        }
    )
    original = deepcopy(project_cfg)

    errors = validator.validate(project_cfg)

    assert [(error.entity, error.field, error.code) for error in errors] == [("broken_child", "keys", "COLUMN_REFERENCE_MISSING_PATH")]
    assert project_cfg == original


def test_malformed_foreign_key_does_not_block_checks_in_other_entities(
    validator: ColumnListReferenceValidationService,
) -> None:
    """Keep a malformed FK dictionary from stopping checks for other saved paths."""
    project_cfg = make_project(
        {
            "source": {"keys": ["first", "second"]},
            "valid_child": {"keys": "@value: entities.source.keys"},
            "malformed_fk": {
                "foreign_keys": {
                    "missing_entity_field": {"local_keys": "@value: entities.missing.keys"},
                }
            },
        }
    )

    errors = validator.validate(project_cfg)

    assert [(error.entity, error.field, error.code) for error in errors] == [
        ("malformed_fk", "foreign_keys.missing_entity_field.local_keys", "COLUMN_REFERENCE_MISSING_PATH")
    ]


def test_expression_check_uses_a_collision_free_options_key(validator: ColumnListReferenceValidationService) -> None:
    """Keep existing options and the source project unchanged while checking an expression."""
    project_cfg = make_project(
        {
            "source": {"keys": ["first"]},
            "child": {"keys": "@value: entities.source.keys + ['last']"},
        },
        options={"__column_reference_expression_check__": "existing"},
    )
    original = deepcopy(project_cfg)

    assert validator.validate(project_cfg) == []
    assert project_cfg == original
