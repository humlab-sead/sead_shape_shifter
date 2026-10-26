"""Resolve advisory column candidates for entity editor operations."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from src.model import ShapeShiftProject, TableConfig, UnnestConfig
from src.transforms.dsl import DSLException, extract_column_references
from src.transforms.extra_columns import ExtraColumnEvaluator
from src.transforms.filter import normalize_filter_stage


def resolve_column_availability(
    project: ShapeShiftProject,
    entity_name: str,
    *,
    source_columns: Sequence[str] | None = None,
    processed_parent_columns: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Return known column candidates for each operation on an entity draft.

    Source column names may be incomplete. This function does not read sources,
    execute loaders, or execute queries.
    """
    table_cfg: TableConfig = project.get_table(entity_name)
    source_candidates: list[str] = _get_source_candidates(project, table_cfg, source_columns, processed_parent_columns)
    extracted_columns, deferred_extra_columns = _apply_extra_columns(source_candidates, table_cfg.extra_columns)

    filters: dict[str, list[str]] = {"extract": _ordered(extracted_columns)}
    before_unnest, before_unnest_fks = _link_candidates(project, table_cfg, extracted_columns, processed_parent_columns)
    after_link, deferred_extra_columns = _apply_extra_columns(before_unnest, deferred_extra_columns)
    filters["after_link"] = _ordered(after_link)

    unnest_config: UnnestConfig | None = table_cfg.unnest
    before_unnest_candidates: list[str] = _ordered(after_link)
    if unnest_config and unnest_config.value_name not in after_link:
        after_unnest: list[str] = _ordered(
            [column for column in unnest_config.id_vars if column in after_link] + [unnest_config.var_name, unnest_config.value_name]
        )
    else:
        after_unnest = _ordered(after_link)

    after_second_link, after_unnest_fks = _link_candidates(project, table_cfg, after_unnest, processed_parent_columns)
    after_second_link, deferred_extra_columns = _apply_extra_columns(after_second_link, deferred_extra_columns)
    filters["after_unnest"] = _ordered(after_second_link)

    fk_candidates: list[dict[str, Any]] = []
    for index, fk in enumerate(table_cfg.foreign_keys):
        fk_candidates.append(
            {
                "index": index,
                "entity": fk.remote_entity,
                "local_keys_before_unnest": before_unnest_fks[index]["local_keys"],
                "local_keys_after_unnest": after_unnest_fks[index]["local_keys"],
                "remote_keys": before_unnest_fks[index]["remote_keys"],
                "extra_column_sources": before_unnest_fks[index]["remote_keys"],
            }
        )

    extra_column_sources: list[str] = _ordered(source_candidates + extracted_columns + after_link + after_second_link)
    drop_duplicates: list[str] = after_second_link if table_cfg.is_drop_duplicate_dependent_on_unnesting() else extracted_columns
    final_candidates: list[str] = _ordered(after_second_link)

    for configured_filter in table_cfg.filters:
        stage: str = normalize_filter_stage(configured_filter)
        filters.setdefault(stage, [])

    return {
        "columns": _ordered(source_candidates),
        "business_keys": _ordered(extracted_columns),
        "replacements": _ordered(extracted_columns),
        "drop_duplicates": _ordered(drop_duplicates),
        "drop_empty_rows": final_candidates,
        "extra_columns": {"sources": extra_column_sources},
        "filters": {stage: _ordered(columns) for stage, columns in filters.items()},
        "foreign_keys": fk_candidates,
        "unnest": {
            "id_vars": before_unnest_candidates,
            "value_vars": (
                [column for column in before_unnest_candidates if column not in set(unnest_config.id_vars)] if unnest_config else []
            ),
        },
    }


def _get_source_candidates(
    project: ShapeShiftProject,
    table_cfg: TableConfig,
    source_columns: Sequence[str] | None,
    processed_parent_columns: Mapping[str, Sequence[str]] | None,
) -> list[str]:
    candidates: list[str] = list(source_columns or [])
    candidates.extend(table_cfg.safe_columns)

    if table_cfg.type == "fixed":
        candidates.extend(column for column in table_cfg.values_column_order if column != table_cfg.system_id)

    if table_cfg.source and project.has_table(table_cfg.source):
        candidates.extend(_processed_entity_columns(project, table_cfg.source, processed_parent_columns))

    for branch in table_cfg.branches:
        branch_source = branch.get("source")
        if isinstance(branch_source, str) and project.has_table(branch_source):
            branch_cfg: TableConfig = project.get_table(branch_source)
            candidates.extend(
                column
                for column in _processed_entity_columns(project, branch_source, processed_parent_columns)
                if column != branch_cfg.system_id
            )
            candidates.append(f"{table_cfg.entity_name}_branch")
            candidates.append(branch_cfg.public_id or f"{branch_source}_id")

    for append in table_cfg.append_configs:
        append_source = append.get("source")
        if isinstance(append_source, str) and project.has_table(append_source):
            candidates.extend(_processed_entity_columns(project, append_source, processed_parent_columns))

    generated_columns: set[str] = set(table_cfg.extra_column_names)
    generated_columns.update(column for fk in table_cfg.foreign_keys for column in fk.extra_columns)
    generated_columns.update(
        project.get_table(fk.remote_entity).public_id for fk in table_cfg.foreign_keys if project.has_table(fk.remote_entity)
    )
    if table_cfg.unnest:
        generated_columns.update({table_cfg.unnest.var_name, table_cfg.unnest.value_name})
    generated_columns.add(table_cfg.system_id)

    return _ordered(column for column in candidates if column not in generated_columns)


def _processed_entity_columns(
    project: ShapeShiftProject,
    entity_name: str,
    processed_parent_columns: Mapping[str, Sequence[str]] | None,
) -> list[str]:
    table_cfg: TableConfig = project.get_table(entity_name)
    if processed_parent_columns is not None and entity_name in processed_parent_columns:
        columns: list[str] = list(processed_parent_columns[entity_name])
    else:
        columns = table_cfg.get_target_facing_columns()
    columns.append(table_cfg.system_id)
    return _ordered(columns)


def _link_candidates(
    project: ShapeShiftProject,
    table_cfg: TableConfig,
    columns: Sequence[str],
    processed_parent_columns: Mapping[str, Sequence[str]] | None,
) -> tuple[list[str], list[dict[str, list[str]]]]:
    available: list[str] = _ordered(columns)
    fk_candidates: list[dict[str, list[str]]] = []

    for fk in table_cfg.foreign_keys:
        remote_columns: list[str] = (
            _processed_entity_columns(project, fk.remote_entity, processed_parent_columns) if project.has_table(fk.remote_entity) else []
        )
        fk_candidates.append({"local_keys": _ordered(available), "remote_keys": remote_columns})

        if not project.has_table(fk.remote_entity):
            continue
        if table_cfg.unnest and not table_cfg.unnest_columns.issubset(available):
            continue
        if fk.local_keys and not set(fk.local_keys).issubset(available):
            continue
        if not fk.local_keys and fk.how != "cross":
            continue

        remote_cfg: TableConfig = project.get_table(fk.remote_entity)
        if remote_cfg.public_id and not (fk.extra_columns and fk.drop_remote_id):
            available.append(remote_cfg.public_id)
        remote_set: set[str] = set(remote_columns)
        available.extend(local_column for remote_column, local_column in fk.resolved_extra_columns().items() if remote_column in remote_set)
        available = _ordered(available)

    return available, fk_candidates


def _apply_extra_columns(columns: Sequence[str], extra_columns: Mapping[str, Any]) -> tuple[list[str], dict[str, Any]]:
    available: list[str] = _ordered(columns)
    deferred: dict[str, Any] = {}
    evaluator = ExtraColumnEvaluator()

    for output_column, expression in extra_columns.items():
        if output_column in available:
            continue

        dependencies: set[str] | None = _extra_column_dependencies(evaluator, expression, available)
        if dependencies is None or not dependencies.issubset(available):
            deferred[output_column] = expression
            continue

        available.append(output_column)

    return _ordered(available), deferred


def _extra_column_dependencies(evaluator: ExtraColumnEvaluator, expression: Any, available: Sequence[str]) -> set[str] | None:
    if not isinstance(expression, str) or evaluator.is_escaped_equals_literal(expression):
        return set()

    if evaluator.is_dsl_formula(expression):
        try:
            return extract_column_references(evaluator.formula_engine.parse(expression))
        except DSLException:  # Formula errors are reported by normal validation and execution.
            return None

    if evaluator.is_interpolated_string(expression):
        return set(evaluator.extract_column_dependencies(expression))

    return {expression} if expression in available else set()


def _ordered(columns: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for column in columns:
        if isinstance(column, str) and column and column not in seen:
            result.append(column)
            seen.add(column)
    return result
