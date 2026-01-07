"""Specifications for validating fields in entity configurations."""

from types import NoneType
from typing import Any

from src.utility import dotexists, dotget

from .base import FIELD_VALIDATORS, FieldValidator

# pylint: disable=line-too-long, unused-argument


@FIELD_VALIDATORS.register(key="is_empty")
class IsEmptyFieldValidator(FieldValidator):
    """Validator to check if a field is empty (None, empty string, empty list, or empty dict).

    Fails if the field has a non-empty value.
    """

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        return dotget(target_cfg, field) in (None, "", [], {})

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must be empty. {kwargs.get('message', '')}", entity=entity_name, column=field
        )


@FIELD_VALIDATORS.register(key="exists")
class FieldExistsValidator(FieldValidator):
    """Validator to check if a field exists in the configuration.

    Fails if the field path is not present in the target config.
    """

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        return dotexists(target_cfg, field)

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' is required but missing. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="is_string_list")
class FieldIsStringListValidator(FieldValidator):
    """Validator to check if a field's value is a list of strings."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: str | list[str] | None = dotget(target_cfg, field)
        if isinstance(value, str) and value.startswith("@value"):
            # Special case for value references if project_cfg is unresolved
            return True
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must be a list of strings. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="not_empty_string")
class FieldIsNotEmptyStringValidator(FieldValidator):
    """Validator to check if a field is a non-empty string."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: Any = dotget(target_cfg, field)
        return isinstance(value, str) and bool(value.strip())

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must be a non-empty string. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="not_empty")
class FieldIsNonEmptyValidator(FieldValidator):
    """Validator to check that a field has a truthy value.

    Fails if the field is empty, None, False, 0, or any falsy value.
    Note: Despite the class name, this validates non-emptiness.
    """

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: Any = dotget(target_cfg, field)
        return value

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' is empty or falsy. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="of_type")
class FieldTypeValidator(FieldValidator):
    """Validator to check that a field is of a specific type.

    Requires 'expected_types' kwarg as a tuple of acceptable types.
    Fails if the field value doesn't match any of the expected types.
    """

    def rule_predicate(
        self, target_cfg: dict[str, Any], entity_name: str, field: str, *, expected_types: tuple[type, ...] = (), **kwargs
    ) -> bool:
        value: Any = dotget(target_cfg, field)
        expected_types = tuple(NoneType if t is None else t for t in expected_types)
        return isinstance(value, expected_types)

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        message: str = kwargs.get("message", "")
        expected_types: tuple[type, ...] = kwargs.get("expected_types", ())
        expected_type_names: str = ", ".join([t.__name__ for t in expected_types])
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must be of type(s) '{expected_type_names}'. {message}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="is_existing_entity")
class IsExistingEntityValidator(FieldValidator):
    """Validator to check that a field is an existing entity."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value = dotget(target_cfg, field) or ""
        return value in self.project_cfg.get("entities", {})

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must be an existing entity. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="ends_with_id")
class EndsWithIdValidator(FieldValidator):
    """Validator to check that a field ends with '_id'."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: str = dotget(target_cfg, field)
        return isinstance(value, str) and value.endswith("_id")

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' should end with '_id'. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="is_of_categorical_values")
class IsOfCategoricalValuesValidator(FieldValidator):
    """Validator to check that a field's value is one of the specified categorical values."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: str = dotget(target_cfg, field)
        categories: list[str] = kwargs.get("categories", [])
        if not isinstance(value, str):
            return True
        return value in categories

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' should have a value in the specified categories. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="is_in_columns")
class IsInColumnsValidator(FieldValidator):
    """Validator to check that a field's value is defined in the `columns` field."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        value: str = dotget(target_cfg, field)
        columns: list[str] = kwargs.get("columns", [])
        if not isinstance(columns, list) or not isinstance(value, str):
            return True
        return value in columns

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' not specified in `columns`. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )


@FIELD_VALIDATORS.register(key="has_value")
class HasValueValidator(FieldValidator):
    """Validator to check that a field's value is equal to the expected value."""

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, *, expected_value: Any = None, **kwargs) -> bool:
        value: str = dotget(target_cfg, field)
        return value == expected_value

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' does not have the expected value. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )
