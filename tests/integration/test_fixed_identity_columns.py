"""A `fixed` entity keeps its stored `system_id` and public ID when `columns` does not list them.

The backend saves `fixed` entities with only the data columns in `columns`, while the stored rows still hold both ID columns.
The IDs used here are not 1, 2, 3, so that generated `system_id` values cannot pass for stored ones.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications import CompositeProjectSpecification

DATA_ONLY: list[str] = ["name"]
LISTED: list[str] = ["system_id", "location_id", "name"]
ID_TYPES: dict[str, str] = {"system_id": "int", "location_id": "int"}
ROWS: list[list[Any]] = [[143, 501, "x"], [7, 502, "y"]]


def location(columns: list[str], values: Any, **settings: Any) -> dict[str, Any]:
    return {"type": "fixed", "public_id": "location_id", "keys": [], "columns": list(columns), "values": values, **settings}


def project_of(**entities: dict[str, Any]) -> ShapeShiftProject:
    return ShapeShiftProject(cfg={"metadata": {"type": "shapeshifter-project", "name": "test"}, "entities": entities})


async def normalize(project: ShapeShiftProject) -> dict[str, pd.DataFrame]:
    return dict((await ShapeShifter(project=project).normalize()).table_store.items())


def column(table: pd.DataFrame, name: str) -> list[Any]:
    return [None if pd.isna(value) else value for value in table[name].tolist()]


def assert_stored_ids(table: pd.DataFrame) -> None:
    assert column(table, "system_id") == [143, 7]
    assert column(table, "location_id") == [501, 502]
    assert column(table, "name") == ["x", "y"]


def write_values_file(directory: Path, suffix: str, rows: pd.DataFrame, entity: dict[str, Any]) -> Path:
    """Writes the rows to a values file and a project that loads them with `@load:`."""
    values_file: Path = directory / f"location.{suffix}"
    if suffix == "parquet":
        rows.to_parquet(values_file, index=False)
    else:
        rows.to_csv(values_file, index=False)
    project_file: Path = directory / "shapeshifter.yml"
    project_file.write_text(
        yaml.safe_dump(
            {
                "metadata": {"type": "shapeshifter-project", "name": "test"},
                "entities": {"location": {**entity, "values": f"@load:location.{suffix}"}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return project_file


@pytest.mark.parametrize("column_types", [None, ID_TYPES], ids=["no-column-types", "id-column-types"])
@pytest.mark.parametrize("columns", [DATA_ONLY, LISTED], ids=["data-only", "listed"])
async def test_inline_rows_keep_stored_ids(columns: list[str], column_types: dict[str, str] | None) -> None:
    extra: dict[str, Any] = {"column_types": column_types} if column_types else {}

    tables = await normalize(project_of(location=location(columns, [list(row) for row in ROWS], **extra)))

    assert_stored_ids(tables["location"])


@pytest.mark.parametrize("column_types", [None, ID_TYPES], ids=["no-column-types", "id-column-types"])
@pytest.mark.parametrize("columns", [DATA_ONLY, LISTED], ids=["data-only", "listed"])
@pytest.mark.parametrize("suffix", ["parquet", "csv"])
async def test_file_rows_keep_stored_ids(tmp_path: Path, suffix: str, columns: list[str], column_types: dict[str, str] | None) -> None:
    rows = pd.DataFrame(ROWS, columns=LISTED)
    extra: dict[str, Any] = {"column_types": column_types} if column_types else {}
    project_file: Path = write_values_file(tmp_path, suffix, rows, location(columns, None, **extra))

    project = ShapeShiftProject.from_file(str(project_file))

    specification = CompositeProjectSpecification(project.cfg)
    assert specification.is_satisfied_by(), [issue.message for issue in specification.errors]
    assert_stored_ids((await normalize(project))["location"])


async def test_reference_to_a_stored_system_id_stays_valid() -> None:
    child: dict[str, Any] = {
        "type": "fixed",
        "public_id": "site_location_id",
        "keys": [],
        "columns": ["location_id"],
        "values": [[1, None, 7], [2, None, 143]],
        "foreign_keys": [{"entity": "location", "local_keys": ["location_id"], "remote_keys": ["system_id"]}],
    }

    tables = await normalize(project_of(location=location(DATA_ONLY, [list(row) for row in ROWS]), site_location=child))

    assert column(tables["site_location"], "location_id") == [7, 143]
    assert set(column(tables["site_location"], "location_id")) <= set(column(tables["location"], "system_id"))


async def test_partly_listed_ids_are_read_in_stored_order() -> None:
    tables = await normalize(project_of(location=location(["system_id", "name"], [list(row) for row in ROWS])))

    assert_stored_ids(tables["location"])


@pytest.mark.parametrize("column_types", [None, ID_TYPES], ids=["no-column-types", "id-column-types"])
async def test_rows_without_ids_still_get_generated_ids(column_types: dict[str, str] | None) -> None:
    extra: dict[str, Any] = {"column_types": column_types} if column_types else {}

    tables = await normalize(project_of(location=location(DATA_ONLY, [["x"], ["y"]], **extra)))

    assert column(tables["location"], "system_id") == [1, 2]
    assert column(tables["location"], "location_id") == [None, None]
    assert column(tables["location"], "name") == ["x", "y"]


async def test_file_rows_without_ids_still_get_generated_ids(tmp_path: Path) -> None:
    project_file: Path = write_values_file(tmp_path, "parquet", pd.DataFrame({"name": ["x", "y"]}), location(DATA_ONLY, None))

    tables = await normalize(ShapeShiftProject.from_file(str(project_file)))

    assert column(tables["location"], "system_id") == [1, 2]
    assert column(tables["location"], "location_id") == [None, None]


async def test_empty_values_file_with_id_column_types_loads(tmp_path: Path) -> None:
    empty = pd.DataFrame({name: pd.Series(dtype="string") for name in LISTED})
    entity: dict[str, Any] = location(DATA_ONLY, None, column_types={**ID_TYPES, "name": "string"})
    project_file: Path = write_values_file(tmp_path, "parquet", empty, entity)

    tables = await normalize(ShapeShiftProject.from_file(str(project_file)))

    assert len(tables["location"]) == 0
    assert {"system_id", "location_id", "name"} <= set(tables["location"].columns)


async def test_file_with_only_identity_columns_keeps_stored_ids(tmp_path: Path) -> None:
    rows = pd.DataFrame({"system_id": [143, 7], "location_id": [501, 502]})
    project_file: Path = write_values_file(tmp_path, "parquet", rows, location([], None))

    table = (await normalize(ShapeShiftProject.from_file(str(project_file))))["location"]

    assert column(table, "system_id") == [143, 7]
    assert column(table, "location_id") == [501, 502]


async def test_derived_entity_does_not_take_the_source_system_id() -> None:
    derived: dict[str, Any] = {"type": "entity", "source": "location", "public_id": "place_id", "keys": [], "columns": ["name"]}

    tables = await normalize(project_of(location=location(DATA_ONLY, [list(row) for row in ROWS]), place=derived))

    assert column(tables["place"], "system_id") == [1, 2]
    assert column(tables["place"], "place_id") == [None, None]


@pytest.mark.parametrize("appended_row", [["z"], [9, None, "z"]], ids=["data-only", "full"])
async def test_entity_with_append_is_not_changed(appended_row: list[Any]) -> None:
    entity: dict[str, Any] = location(DATA_ONLY, [[143, 501, "x"]], append=[{"type": "fixed", "values": [appended_row]}])

    tables = await normalize(project_of(location=entity))

    assert column(tables["location"], "system_id") == [1, 2]
    assert column(tables["location"], "location_id") == [None, None]
    assert column(tables["location"], "name") == ["x", "z"]


async def test_project_configuration_is_not_changed() -> None:
    project = project_of(location=location(DATA_ONLY, [list(row) for row in ROWS]))

    await normalize(project)

    assert project.cfg["entities"]["location"]["columns"] == DATA_ONLY
