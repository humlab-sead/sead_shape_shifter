"""A materialized fixed entity keeps its stored IDs when some rows have none."""

from pathlib import Path

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.types.fixed_entity_types import FixedEntityTypeValidationError


def _project(tmp_path: Path, ids: list[float | None]) -> ShapeShiftProject:
    """Writes the parquet file as materialization does and loads it with ``@load:``."""
    path = tmp_path / "feature_type.parquet"
    frame = pd.DataFrame(
        {
            "system_id": range(1, len(ids) + 1),
            "feature_type_id": pd.Series(ids, dtype="float64"),
            "feature_type_name": [f"name-{index}" for index in range(len(ids))],
        }
    )
    frame.to_parquet(path)
    entity = {
        "type": "fixed",
        "keys": ["feature_type_name"],
        "columns": ["feature_type_name"],
        "public_id": "feature_type_id",
        "values": f"@load:{path}",
    }
    return ShapeShiftProject(cfg={"metadata": {"name": "p"}, "entities": {"feature_type": entity}}).resolve()


@pytest.mark.asyncio
async def test_stored_ids_are_kept_when_other_rows_have_no_id(tmp_path: Path) -> None:
    shifter = ShapeShifter(_project(tmp_path, [27.0, None, 12.0]))

    await shifter.normalize()

    ids = shifter.table_store["feature_type"]["feature_type_id"]
    assert [None if pd.isna(value) else value for value in ids] == [27, None, 12]


@pytest.mark.asyncio
async def test_a_stored_id_that_is_not_a_whole_number_is_refused(tmp_path: Path) -> None:
    shifter = ShapeShifter(_project(tmp_path, [27.5, None]))

    with pytest.raises(FixedEntityTypeValidationError, match="1 invalid typed value"):
        await shifter.normalize()
