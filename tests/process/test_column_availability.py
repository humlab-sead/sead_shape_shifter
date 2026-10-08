from typing import Any

import pandas as pd
import pytest

from src.column_availability import resolve_column_availability
from src.extract import SubsetService
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.table_store import TableStore


def test_candidates_follow_operation_stages_and_current_unnest_shape() -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_code"],
                    "columns": ["site_name"],
                },
                "sample": {
                    "type": "entity",
                    "keys": ["site_code"],
                    "columns": ["site_code", "measure_a", "measure_b", "filter_value"],
                    "extra_columns": {
                        "early_copy": "filter_value",
                        "linked_copy": "{site_id}",
                        "melted_copy": "{reading}",
                    },
                    "foreign_keys": [
                        {
                            "entity": "site",
                            "local_keys": ["site_code"],
                            "remote_keys": ["site_code"],
                            "extra_columns": {"remote_site_name": "site_name"},
                        }
                    ],
                    "unnest": {
                        "id_vars": ["site_code", "early_copy"],
                        "value_vars": ["measure_a", "measure_b"],
                        "var_name": "measure",
                        "value_name": "reading",
                    },
                    "filters": [
                        {"type": "query", "query": "filter_value != ''"},
                        {"type": "query", "stage": "after_link", "query": "site_id > 0"},
                        {"type": "query", "stage": "after_unnest", "query": "reading > 0"},
                    ],
                    "drop_duplicates": ["reading"],
                    "drop_empty_rows": ["reading"],
                },
            }
        }
    )

    result = resolve_column_availability(
        project,
        "sample",
        source_columns=["metadata_only", "system_id", "site_code", "measure_a", "measure_b", "filter_value"],
    )

    assert "system_id" not in result["columns"]
    assert "early_copy" not in result["columns"]
    assert "early_copy" in result["filters"]["extract"]
    assert "site_id" not in result["filters"]["extract"]
    assert "site_id" not in result["filters"]["after_link"]
    assert "linked_copy" not in result["filters"]["after_link"]
    assert "reading" not in result["filters"]["after_link"]
    assert {"reading", "melted_copy"}.issubset(result["filters"]["after_unnest"])
    assert {"site_id", "linked_copy"}.issubset(result["filters"]["after_unnest"])
    assert "site_id" in result["filters"]["after_unnest"]
    assert "measure_a" in result["unnest"]["value_vars"]
    assert "site_id" not in result["foreign_keys"][0]["local_keys_after_unnest"]
    assert "system_id" in result["foreign_keys"][0]["remote_keys"]
    assert "reading" in result["drop_duplicates"]
    assert "system_id" not in result["drop_empty_rows"]
    assert "filter_value" in result["filters"]["extract"]


def test_unknown_source_fields_remain_advisory_and_partial_metadata_is_used() -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "sample": {
                    "type": "entity",
                    "columns": ["configured_field"],
                    "extra_columns": {"unknown_copy": "{not_known}"},
                }
            }
        }
    )

    result = resolve_column_availability(project, "sample", source_columns=["known_source_field"])

    assert {"configured_field", "known_source_field"}.issubset(result["columns"])
    assert "unknown_copy" not in result["filters"]["extract"]
    assert "not_known" not in result["extra_columns"]["sources"]


def test_derived_entity_uses_supplied_processed_source_columns() -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_code"],
                    "columns": ["site_name"],
                },
                "site_property": {"type": "entity", "source": "site", "columns": ["site_id"]},
            }
        }
    )

    result = resolve_column_availability(
        project,
        "site_property",
        processed_parent_columns={"site": ["system_id", "site_id", "site_name", "processed_extra"]},
    )

    assert {"site_id", "site_name", "processed_extra"}.issubset(result["columns"])
    assert "system_id" not in result["columns"]


def test_merged_candidates_include_branch_outputs_without_branch_system_id() -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_code"],
                    "columns": ["site_name"],
                },
                "all_sites": {"type": "merged", "branches": [{"source": "site"}]},
            }
        }
    )

    result = resolve_column_availability(project, "all_sites")

    assert {"site_code", "site_name", "all_sites_branch", "site_id"}.issubset(result["columns"])
    assert "system_id" not in result["columns"]


def test_ordinary_deduplication_candidates_use_extracted_columns() -> None:
    project = ShapeShiftProject(
        cfg={"entities": {"sample": {"type": "entity", "columns": ["site_code", "value"], "drop_duplicates": ["site_code"]}}}
    )

    result = resolve_column_availability(project, "sample", source_columns=["site_code", "value"])

    assert result["drop_duplicates"] == result["business_keys"]
    assert "value" in result["drop_duplicates"]


def test_foreign_key_candidates_follow_link_order_and_processed_parent_columns() -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "first_parent": {"type": "fixed", "public_id": "first_id", "keys": ["lookup"]},
                "second_parent": {"type": "fixed", "public_id": "second_id", "keys": ["lookup"]},
                "child": {
                    "type": "entity",
                    "columns": ["code"],
                    "foreign_keys": [
                        {
                            "entity": "first_parent",
                            "local_keys": ["code"],
                            "remote_keys": ["lookup"],
                            "extra_columns": {"next_code": "runtime_extra"},
                        },
                        {
                            "entity": "second_parent",
                            "local_keys": ["next_code"],
                            "remote_keys": ["runtime_lookup"],
                        },
                    ],
                },
            }
        }
    )

    result = resolve_column_availability(
        project,
        "child",
        processed_parent_columns={
            "first_parent": ["lookup", "runtime_extra"],
            "second_parent": ["runtime_lookup"],
        },
    )

    fk_candidates = result["foreign_keys"]
    first_fk = fk_candidates[0]
    second_fk = fk_candidates[1]
    assert "next_code" not in first_fk["local_keys_before_unnest"]
    assert "next_code" in second_fk["local_keys_before_unnest"]
    assert "runtime_extra" in first_fk["remote_keys"]
    assert "system_id" in first_fk["remote_keys"]
    assert "system_id" in second_fk["remote_keys"]


@pytest.mark.asyncio
async def test_candidates_match_deterministic_normalizer_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "site": {"type": "fixed", "public_id": "site_id", "keys": ["site_code"], "columns": ["site_name"]},
                "measurement": {
                    "type": "entity",
                    "keys": ["site_code"],
                    "columns": ["site_code", "measure_a", "measure_b"],
                    "foreign_keys": [{"entity": "site", "local_keys": ["site_code"], "remote_keys": ["site_code"], "how": "left"}],
                    "unnest": {
                        "id_vars": ["site_code"],
                        "value_vars": ["measure_a", "measure_b"],
                        "var_name": "variable",
                        "value_name": "value",
                    },
                    "drop_duplicates": ["value"],
                    "drop_empty_rows": ["value"],
                    "check_functional_dependency": False,
                },
            }
        }
    )
    source = pd.DataFrame({"site_code": ["a", "b"], "measure_a": [1, 1], "measure_b": [2, 2]})
    parent = pd.DataFrame({"system_id": [1, 2], "site_code": ["a", "b"], "site_name": ["North", "South"]})
    normalizer = ShapeShifter(project=project, table_store=TableStore({"site": parent}))
    observed: dict[str, Any] = {"link_inputs": [], "link_outputs": []}

    async def get_source_subset(*_args: Any, **_kwargs: Any) -> pd.DataFrame:
        return source.copy()

    original_link = normalizer.linker.link_entity

    def record_link(entity_name: str) -> bool:
        if entity_name == "measurement":
            observed["link_inputs"].append(list(normalizer.table_store[entity_name].columns))
        result = original_link(entity_name)
        if entity_name == "measurement":
            observed["link_outputs"].append(list(normalizer.table_store[entity_name].columns))
        return result

    original_unnest = normalizer.unnest_entity

    def record_unnest(*, entity: str) -> pd.DataFrame:
        result = original_unnest(entity=entity)
        observed["after_unnest"] = list(result.columns)
        return result

    original_drop_duplicates = normalizer.drop_duplicates

    def record_drop_duplicates(entity_name: str, table_cfg: TableConfig, data: pd.DataFrame) -> pd.DataFrame:
        observed["drop_duplicates"] = list(data.columns)
        return original_drop_duplicates(entity_name, table_cfg, data)

    original_check_duplicate_keys = normalizer._check_duplicate_keys

    def record_pre_cleanup_columns(entity: str, table_cfg: TableConfig) -> None:
        observed["before_drop_empty"] = list(normalizer.table_store[entity].columns)
        original_check_duplicate_keys(entity, table_cfg)

    monkeypatch.setattr(normalizer, "get_subset", get_source_subset)
    monkeypatch.setattr(normalizer.linker, "link_entity", record_link)
    monkeypatch.setattr(normalizer, "unnest_entity", record_unnest)
    monkeypatch.setattr(normalizer, "drop_duplicates", record_drop_duplicates)
    monkeypatch.setattr(normalizer, "_check_duplicate_keys", record_pre_cleanup_columns)

    try:
        await normalizer._process_entity("measurement", SubsetService())
    finally:
        normalizer.duckdb_workspace.close()
        normalizer.loaders.close_all()

    candidates = resolve_column_availability(project, "measurement", source_columns=source.columns.tolist())

    assert set(candidates["filters"]["extract"]) == set(observed["link_inputs"][0])
    assert "site_id" not in observed["link_outputs"][0]
    assert set(observed["after_unnest"]) == {"site_code", "variable", "value"}
    assert set(candidates["foreign_keys"][0]["local_keys_after_unnest"]) == set(observed["link_inputs"][1])
    assert set(candidates["filters"]["after_unnest"]) == set(observed["link_outputs"][1])
    assert set(candidates["drop_duplicates"]) == set(observed["drop_duplicates"])
    assert set(candidates["drop_empty_rows"]) == set(observed["before_drop_empty"])
    assert "system_id" not in candidates["drop_empty_rows"]
    assert "system_id" in normalizer.table_store["measurement"].columns
