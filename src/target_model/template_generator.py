from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import yaml

from src.target_model.models import EntitySpec, TargetModel


PLACEHOLDER_ENTITY_TYPE = "TODO"


def generate_project_template(
    target_model: TargetModel,
    *,
    domains: list[str] | None = None,
    entity_names: list[str] | None = None,
    project_name: str | None = None,
) -> dict[str, object]:

    selected_entities: list[str] = _resolve_entity_selection(target_model, domains=domains or [], entity_names=entity_names or [])

    metadata: dict[str, str] = {
        "name": project_name or _default_project_name(target_model, domains or [], entity_names or []),
        "type": "shapeshifter-project",
        "version": "0.1.0",
        "description": f"Starter scaffold generated from target model '{target_model.model.name}'",
    }

    entities: dict[str, dict[str, object]] = {}
    for entity_name in selected_entities:
        entity_spec: EntitySpec = target_model.entities[entity_name]
        entities[entity_name] = _generate_entity_stub(entity_spec)

    return {
        "metadata": metadata,
        "entities": entities,
    }


def render_project_template_yaml(
    target_model: TargetModel,
    *,
    domains: list[str] | None = None,
    entity_names: list[str] | None = None,
    project_name: str | None = None,
) -> str:
    template: dict[str, object] = generate_project_template(
        target_model,
        domains=domains,
        entity_names=entity_names,
        project_name=project_name,
    )
    return yaml.safe_dump(template, sort_keys=False, allow_unicode=False)


def main() -> int:
    parser = ArgumentParser(description="Generate a starter Shape Shifter scaffold from a target model")
    parser.add_argument("--spec", type=Path, required=True, help="Path to the target model YAML file")
    parser.add_argument("--domain", action="append", default=[], help="Domain filter to apply (repeatable)")
    parser.add_argument("--entity", action="append", default=[], help="Explicit entity name to include (repeatable)")
    parser.add_argument("--project-name", help="Override generated project metadata name")
    parser.add_argument("--output", type=Path, help="Optional output path; writes to stdout when omitted")
    args = parser.parse_args()

    target_model: TargetModel = TargetModel.model_validate(yaml.safe_load(args.spec.read_text(encoding="utf-8")))
    rendered: str = render_project_template_yaml(
        target_model,
        domains=args.domain,
        entity_names=args.entity,
        project_name=args.project_name,
    )

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0


def _default_project_name(target_model: TargetModel, domains: list[str], entity_names: list[str]) -> str:
    suffix_parts: list[str] = list(domains) + list(entity_names)
    suffix: str = "-".join(suffix_parts) if suffix_parts else "full"
    model_name: str = target_model.model.name.lower().replace(" ", "-")
    return f"generated:{model_name}:{suffix}"


def _generate_entity_stub(entity_spec: EntitySpec) -> dict[str, object]:
    entity_stub: dict[str, object] = {
        "type": PLACEHOLDER_ENTITY_TYPE,
    }

    if entity_spec.public_id:
        entity_stub["public_id"] = entity_spec.public_id

    required_columns: list[str] = [column_name for column_name, column_spec in entity_spec.columns.items() if column_spec.required]
    if required_columns:
        entity_stub["columns"] = required_columns

    required_foreign_keys: list[dict[str, str]] = [{"entity": foreign_key.entity} for foreign_key in entity_spec.foreign_keys if foreign_key.required]
    if required_foreign_keys:
        entity_stub["foreign_keys"] = required_foreign_keys

    return entity_stub


def _resolve_entity_selection(target_model: TargetModel, *, domains: list[str], entity_names: list[str]) -> list[str]:
    explicit_entities: list[str] = list(dict.fromkeys(entity_names))
    unknown_entities: list[str] = [entity_name for entity_name in explicit_entities if entity_name not in target_model.entities]
    if unknown_entities:
        unknown_list: str = ", ".join(sorted(unknown_entities))
        raise ValueError(f"Unknown entities requested: {unknown_list}")

    selected_names: set[str]
    if not domains and not explicit_entities:
        selected_names = set(target_model.entities)
    else:
        selected_names = set(explicit_entities)
        for entity_name, entity_spec in target_model.entities.items():
            if domains and set(domains).intersection(entity_spec.domains):
                selected_names.add(entity_name)

    queue: list[str] = list(selected_names)
    while queue:
        entity_name: str = queue.pop(0)
        entity_spec: EntitySpec = target_model.entities[entity_name]
        for foreign_key in entity_spec.foreign_keys:
            if foreign_key.required and foreign_key.entity not in selected_names:
                selected_names.add(foreign_key.entity)
                queue.append(foreign_key.entity)

    return [entity_name for entity_name in target_model.entities if entity_name in selected_names]


if __name__ == "__main__":
    raise SystemExit(main())