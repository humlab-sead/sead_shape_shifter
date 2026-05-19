"""Regression tests for fixed-entity FK linking with coerced _id values."""

import pandas as pd
import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from src.normalizer import ShapeShifter


@pytest.mark.asyncio
async def test_fixed_entity_string_fk_value_is_coerced_before_normalization() -> None:
    """A string FK value in fixed YAML should still match the parent integer during linking."""
    cfg_dict = {
        "metadata": {
            "type": "shapeshifter-project",
            "version": "1.0.0",
        },
        "entities": {
            "method_group": {
                "type": "fixed",
                "public_id": "method_group_id",
                "keys": ["label"],
                "columns": ["system_id", "method_group_id", "label"],
                "values": [[1, 53, "Group A"]],
            },
            "method": {
                "type": "fixed",
                "public_id": "method_id",
                "keys": ["label"],
                "depends_on": ["method_group"],
                "columns": ["system_id", "method_id", "method_group_id", "label"],
                "foreign_keys": [
                    {
                        "entity": "method_group",
                        "local_keys": ["method_group_id"],
                        "remote_keys": ["method_group_id"],
                    }
                ],
                "values": [[1, 100, "53", "Method A"]],
            },
        },
    }

    api_project = ProjectMapper.to_api_config(cfg_dict, "fixed-fk-regression")
    core_project = ProjectMapper.to_core(api_project)

    # The mapper boundary should normalize the YAML string before execution.
    assert core_project.cfg["entities"]["method"]["values"][0][2] == 53
    assert type(core_project.cfg["entities"]["method"]["values"][0][2]) is int  # pylint: disable=unidiomatic-typecheck

    normalizer = ShapeShifter(project=core_project)
    await normalizer.normalize()

    result = normalizer.table_store["method"]

    # Regression guard: the FK match succeeds and the row survives the inner merge.
    assert len(result) == 1
    assert result["method_group_id"].tolist() == [53]
    assert pd.api.types.is_integer_dtype(result["method_group_id"])
