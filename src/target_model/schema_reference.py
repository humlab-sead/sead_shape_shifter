from __future__ import annotations

import json

from pydantic import BaseModel
from pydantic.fields import PydanticUndefined

from src.target_model.models import ColumnSpec, EntitySpec, ForeignKeySpec, GlobalConstraint, ModelMetadata, NamingConventions, TargetModel

SCHEMA_REF_TEMPLATE = "#/$defs/{model}"
MODEL_ORDER: list[type[BaseModel]] = [
    TargetModel,
    ModelMetadata,
    EntitySpec,
    ColumnSpec,
    ForeignKeySpec,
    NamingConventions,
    GlobalConstraint,
]
MODEL_BY_NAME: dict[str, type[BaseModel]] = {model.__name__: model for model in MODEL_ORDER}
SECTION_INTROS: dict[str, str] = {
    "TargetModel": "Top-level target model file structure.",
    "ModelMetadata": "Values under the `model` section that identify the specification.",
    "EntitySpec": "Values under `entities.<entity_name>` for each target entity.",
    "ColumnSpec": "Values under `entities.<entity_name>.columns.<column_name>` for each declared column.",
    "ForeignKeySpec": "Values under `entities.<entity_name>.foreign_keys[]` for each foreign key requirement.",
    "NamingConventions": "Optional naming rules under the `naming` section.",
    "GlobalConstraint": "Entries under the optional `constraints[]` list.",
}


def generate_target_model_schema_reference() -> str:
    """Return a Markdown reference derived from the Pydantic target-model schema."""
    schema = TargetModel.model_json_schema(mode="serialization", by_alias=True, ref_template=SCHEMA_REF_TEMPLATE)
    defs: dict[str, dict[str, object]] = schema.get("$defs", {})

    lines: list[str] = [
        "# Target Model Schema Reference",
        "",
        "This file is generated from `src/target_model/models.py`. Do not edit it by hand.",
        "Run `python scripts/generate_target_model_schema_reference.py` to regenerate it.",
        "",
        "## What This Covers",
        "",
        "This reference lists the YAML sections and keys accepted by the strict Pydantic target-model schema.",
        "Unknown keys in these sections are rejected because each model uses `extra=\"forbid\"`.",
        "",
        "## YAML Paths",
        "",
    ]
    lines.extend(_render_yaml_paths(schema, defs))

    for model in MODEL_ORDER:
        lines.extend(["", f"## {model.__name__}", ""])
        intro = SECTION_INTROS.get(model.__name__)
        if intro:
            lines.extend([intro, ""])
        model_schema = schema if model is TargetModel else defs[model.__name__]
        lines.extend(_render_model_section(model, model_schema))

    return "\n".join(lines).rstrip() + "\n"


def _render_yaml_paths(root_schema: dict[str, object], defs: dict[str, dict[str, object]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    _collect_paths("", root_schema, defs, lines, seen)
    return lines


def _collect_paths(
    prefix: str,
    schema: dict[str, object],
    defs: dict[str, dict[str, object]],
    lines: list[str],
    seen: set[str],
) -> None:
    resolved = _resolve_schema(schema, defs)
    properties = resolved.get("properties")
    if not isinstance(properties, dict):
        return

    required_fields = set(_as_str_list(resolved.get("required")))
    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        path = f"{prefix}.{field_name}" if prefix else field_name
        marker = "required" if field_name in required_fields else "optional"
        rendered_type = _format_type(field_schema, defs)
        if path not in seen:
            lines.append(f"- `{path}`: {rendered_type} ({marker})")
            seen.add(path)
        _collect_child_paths(path, field_schema, defs, lines, seen)


def _collect_child_paths(
    path: str,
    field_schema: dict[str, object],
    defs: dict[str, dict[str, object]],
    lines: list[str],
    seen: set[str],
) -> None:
    resolved = _resolve_schema(field_schema, defs)

    additional = resolved.get("additionalProperties")
    if isinstance(additional, dict):
        key_name = _placeholder_key_name(path)
        child_path = f"{path}.{key_name}"
        rendered_type = _format_type(additional, defs)
        if child_path not in seen:
            lines.append(f"- `{child_path}`: {rendered_type} (map value)")
            seen.add(child_path)
        _collect_paths(child_path, additional, defs, lines, seen)

    items = resolved.get("items")
    if isinstance(items, dict):
        child_path = f"{path}[]"
        rendered_type = _format_type(items, defs)
        if child_path not in seen:
            lines.append(f"- `{child_path}`: {rendered_type} (list item)")
            seen.add(child_path)
        _collect_paths(child_path, items, defs, lines, seen)


def _render_model_section(model: type[BaseModel], schema: dict[str, object]) -> list[str]:
    lines = ["| Field | Type | Required | Default | Allowed |", "|---|---|---|---|---|"]
    properties = schema.get("properties", {})
    required_fields = set(_as_str_list(schema.get("required")))

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        lines.append(
            "| {field} | {type_} | {required} | {default} | {allowed} |".format(
                field=field_name,
                type_=_escape_table(_format_type(field_schema, schema.get("$defs", {}))),
                required="Yes" if field_name in required_fields else "No",
                default=_escape_table(_format_default(model, field_name, field_schema)),
                allowed=_escape_table(_format_allowed_values(field_schema)),
            )
        )

    lines.extend(["", f"Additional keys allowed: {_extra_keys_allowed(schema)}"])
    return lines


def _resolve_schema(schema: dict[str, object], defs: dict[str, dict[str, object]]) -> dict[str, object]:
    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            return defs[ref.split("/")[-1]]
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        non_null = [option for option in any_of if isinstance(option, dict) and option.get("type") != "null"]
        if len(non_null) == 1:
            return _resolve_schema(non_null[0], defs)
    return schema


def _format_type(schema: dict[str, object], defs: dict[str, dict[str, object]]) -> str:
    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(ref, str):
            return ref.split("/")[-1]

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        return " | ".join(_format_type(option, defs) for option in any_of if isinstance(option, dict))

    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        value_type = schema.get("type")
        prefix = f"enum[{value_type}]" if isinstance(value_type, str) else "enum"
        return f"{prefix}"

    schema_type = schema.get("type")
    if schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            return f"list[{_format_type(items, defs)}]"
        return "list"

    if schema_type == "object":
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"map[string, {_format_type(additional, defs)}]"
        return "object"

    if isinstance(schema_type, str):
        return schema_type

    resolved = _resolve_schema(schema, defs)
    if resolved is not schema:
        return _format_type(resolved, defs)

    return "unknown"


def _format_default(model: type[BaseModel], field_name: str, schema: dict[str, object]) -> str:
    model_field = model.model_fields.get(field_name)
    if model_field is not None:
        if model_field.default_factory is not None:
            return _json_literal(model_field.default_factory())
        if model_field.default is not PydanticUndefined:
            return _json_literal(model_field.default)
    if "default" not in schema:
        return "-"
    return _json_literal(schema["default"])


def _format_allowed_values(schema: dict[str, object]) -> str:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        return ", ".join(_json_literal(value) for value in enum_values)

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        enum_lists: list[str] = []
        include_null = False
        for option in any_of:
            if not isinstance(option, dict):
                continue
            option_enum = option.get("enum")
            if isinstance(option_enum, list):
                enum_lists.extend(_json_literal(value) for value in option_enum)
            if option.get("type") == "null":
                include_null = True
        if enum_lists or include_null:
            values = list(dict.fromkeys(enum_lists))
            if include_null:
                values.append("null")
            return ", ".join(values)

    return "-"


def _placeholder_key_name(path: str) -> str:
    if path.endswith("entities"):
        return "<entity_name>"
    if path.endswith("columns"):
        return "<column_name>"
    return "<key>"


def _extra_keys_allowed(schema: dict[str, object]) -> str:
    additional = schema.get("additionalProperties")
    if isinstance(additional, bool):
        return "Yes" if additional else "No"
    if additional is None:
        return "No"
    return "Map values only"


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _json_literal(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")