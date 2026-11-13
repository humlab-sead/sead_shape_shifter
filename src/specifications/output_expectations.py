"""Validate project declarations for full-run output expectations."""

import math
from typing import Any

from src.model import TableConfig
from src.specifications.base import ProjectSpecification


class OutputExpectationsSpecification(ProjectSpecification):
    """Validate expectation declarations without loading entity data."""

    _SCALAR_METRICS = {"row_count", "distinct_key_count"}
    _GROUPED_METRIC = "grouped_row_count"
    _SUPPORTED_METRICS = _SCALAR_METRICS | {_GROUPED_METRIC}
    _COMPARISONS = {"equals", "min", "max"}
    _COMMON_FIELDS = {"name", "entity", "metric"}

    def is_satisfied_by(self, **kwargs: Any) -> bool:
        """Check declaration shapes, entity references, metrics, columns, and limits."""
        self.clear()
        options = self.project_cfg.get("options", {})
        if not isinstance(options, dict) or "output_expectations" not in options:
            return True

        expectations = options["output_expectations"]
        if not isinstance(expectations, list):
            self._add_error(
                "Output expectations must be a list.",
                field="options.output_expectations",
            )
            return False

        entities = self.project_cfg.get("entities", {})
        seen_names: set[str] = set()
        for index, expectation in enumerate(expectations):
            field = f"options.output_expectations[{index}]"
            if not isinstance(expectation, dict):
                self._add_error("Each output expectation must be a mapping.", field=field)
                continue

            name = expectation.get("name")
            if not isinstance(name, str) or not name.strip():
                self._add_error("Each output expectation must have a non-empty name.", field=f"{field}.name")
            elif name in seen_names:
                self._add_error(f"Output expectation name '{name}' is not unique.", field=f"{field}.name")
            else:
                seen_names.add(name)

            entity_name = expectation.get("entity")
            entity_cfg: dict[str, Any] | None = None
            if (
                not isinstance(entity_name, str)
                or not entity_name.strip()
                or not isinstance(entities, dict)
                or entity_name not in entities
                or not isinstance(entities.get(entity_name), dict)
            ):
                self._add_error(
                    f"Output expectation references an unknown or invalid entity '{entity_name}'.",
                    entity=entity_name if isinstance(entity_name, str) else None,
                    field=f"{field}.entity",
                )
            else:
                entity_cfg = entities[entity_name]

            metric = expectation.get("metric")
            if not isinstance(metric, str) or metric not in self._SUPPORTED_METRICS:
                self._add_error(
                    f"Unsupported output expectation metric '{metric}'.",
                    entity=entity_name if isinstance(entity_name, str) else None,
                    field=f"{field}.metric",
                )
                continue

            entity_context = entity_name if isinstance(entity_name, str) else None
            if metric in self._SCALAR_METRICS:
                allowed_fields = self._COMMON_FIELDS | self._COMPARISONS
                self._check_supported_fields(expectation, allowed_fields, field, entity_context)
                self._validate_comparison(expectation, field, entity_context)
                if metric == "distinct_key_count" and entity_cfg is not None and not self._has_business_keys(entity_cfg):
                    self._add_error(
                        "The distinct_key_count metric requires at least one configured business key.",
                        entity=entity_context,
                        field=f"{field}.metric",
                    )
                continue

            allowed_fields = self._COMMON_FIELDS | {"column", "groups"}
            self._check_supported_fields(expectation, allowed_fields, field, entity_context)
            column = expectation.get("column")
            if not isinstance(column, str) or not column.strip():
                self._add_error(
                    "The grouped_row_count metric requires a non-empty output column.",
                    entity=entity_context,
                    field=f"{field}.column",
                    column=column if isinstance(column, str) else None,
                )
            elif entity_cfg is not None and isinstance(entity_name, str):
                self._validate_grouping_column(entity_name, column, entities, options, field)

            groups = expectation.get("groups")
            if not isinstance(groups, dict) or not groups:
                self._add_error(
                    "The grouped_row_count metric requires a non-empty groups mapping.",
                    entity=entity_context,
                    field=f"{field}.groups",
                )
                continue

            for group_value, limits in groups.items():
                group_field = f"{field}.groups[{group_value!r}]"
                if not self._is_json_scalar(group_value):
                    self._add_error(
                        "A configured group value must be a JSON scalar: a string, boolean, finite number, or null.",
                        entity=entity_context,
                        field=group_field,
                    )
                if not isinstance(limits, dict):
                    self._add_error(
                        "Each configured group must have a comparison mapping.",
                        entity=entity_context,
                        field=group_field,
                    )
                    continue
                self._check_supported_fields(limits, self._COMPARISONS, group_field, entity_context)
                self._validate_comparison(limits, group_field, entity_context)

        return not self.has_errors()

    def _validate_grouping_column(
        self,
        entity_name: str,
        column: str,
        entities: dict[str, Any],
        options: dict[str, Any],
        field: str,
    ) -> None:
        """Check that a grouping column is part of the configured output schema."""
        try:
            table_config = TableConfig(
                entities_cfg=entities,
                entity_name=entity_name,
                project_options=options,
            )
            output_columns = table_config.get_target_facing_columns()
        except (AssertionError, AttributeError, KeyError, TypeError, ValueError):
            self._add_error(
                f"Could not determine the configured output columns for entity '{entity_name}'.",
                entity=entity_name,
                field=f"{field}.column",
                column=column,
            )
            return

        if column not in output_columns:
            self._add_error(
                f"Column '{column}' is not a configured pre-translation output column for entity '{entity_name}'.",
                entity=entity_name,
                field=f"{field}.column",
                column=column,
            )

    def _validate_comparison(self, comparison: dict[str, Any], field: str, entity: str | None) -> None:
        """Check one exact limit or inclusive numeric range."""
        has_equals = "equals" in comparison
        has_min = "min" in comparison
        has_max = "max" in comparison

        if has_equals and (has_min or has_max):
            self._add_error(
                "Use either equals or min/max bounds, not both.",
                entity=entity,
                field=field,
            )
        elif not has_equals and not has_min and not has_max:
            self._add_error(
                "A comparison must define equals, min, max, or both min and max.",
                entity=entity,
                field=field,
            )

        valid_limits: dict[str, int] = {}
        for key in ("equals", "min", "max"):
            if key not in comparison:
                continue
            value = comparison[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                self._add_error(
                    f"The '{key}' limit must be a non-negative integer.",
                    entity=entity,
                    field=f"{field}.{key}",
                )
            else:
                valid_limits[key] = value

        if has_min and has_max and "min" in valid_limits and "max" in valid_limits and valid_limits["min"] > valid_limits["max"]:
            self._add_error(
                "The min limit must not be greater than the max limit.",
                entity=entity,
                field=field,
            )

    def _check_supported_fields(
        self,
        declaration: dict[str, Any],
        allowed_fields: set[str],
        field: str,
        entity: str | None,
    ) -> None:
        """Report fields that are not supported for this metric or comparison."""
        for key in declaration:
            if key not in allowed_fields:
                self._add_error(
                    f"Unsupported field '{key}' in output expectation declaration.",
                    entity=entity,
                    field=f"{field}.{key}",
                )

    @staticmethod
    def _has_business_keys(entity_cfg: dict[str, Any]) -> bool:
        """Return whether the entity declares at least one non-empty business key."""
        keys = entity_cfg.get("keys")
        if isinstance(keys, str):
            return bool(keys.strip())
        return isinstance(keys, list) and any(isinstance(key, str) and key.strip() for key in keys)

    @staticmethod
    def _is_json_scalar(value: Any) -> bool:
        """Return whether a group value is a JSON scalar without coercion."""
        if value is None or isinstance(value, (str, bool, int)):
            return True
        return isinstance(value, float) and math.isfinite(value)

    def _add_error(
        self,
        message: str,
        *,
        field: str,
        entity: str | None = None,
        column: str | None = None,
    ) -> None:
        """Add a structural issue tied to the output expectation declaration."""
        self.add_error(
            message,
            entity=entity,
            field=field,
            column=column,
            code="OUTPUT_EXPECTATION_INVALID",
        )
