"""`fixed` entities keep their `system_id` and public ID after backend saves and materialization.

The saved project is reloaded with Core. The IDs used here are not 1, 2, 3, so that generated values cannot pass for stored ones.
"""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest
import yaml

from backend.app.core.config import settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.services.materialization_service import MaterializationService
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter

# pylint: disable=redefined-outer-name

ID_TYPES: dict[str, str] = {"system_id": "int", "location_id": "int"}
FULL_COLUMNS: list[str] = ["system_id", "location_id", "name"]


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    # The project service caches projects by name, so each test needs its own name.
    directory: Path = tmp_path / f"identity_{uuid4().hex}"
    directory.mkdir()
    return directory


def write_project(project_dir: Path, entities: dict[str, Any]) -> None:
    cfg: dict[str, Any] = {"metadata": {"type": "shapeshifter-project", "name": project_dir.name, "version": "1.0.0"}, "entities": entities}
    (project_dir / "shapeshifter.yml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def saved_entity(project_dir: Path, name: str) -> dict[str, Any]:
    return yaml.safe_load((project_dir / "shapeshifter.yml").read_text(encoding="utf-8"))["entities"][name]


async def reload_ids(project: ShapeShiftProject, name: str) -> tuple[list[Any], list[Any]]:
    table: pd.DataFrame = (await ShapeShifter(project=project).normalize()).table_store[name]
    public_ids: list[Any] = [None if pd.isna(value) else value for value in table["location_id"].tolist()]
    return table["system_id"].tolist(), public_ids


def save_entity_unchanged(service: ProjectService, project_name: str) -> None:
    entity: dict[str, Any] = dict(service.load_project(project_name, force_reload=True).entities["location"])
    service.update_entity_by_name(project_name, "location", entity)


def location_entity(project_dir: Path, storage: str, with_types: bool) -> dict[str, Any]:
    rows: list[list[Any]] = [[143, 501, "x"], [7, 502, "y"]]
    values: Any = rows
    if storage == "parquet":
        (project_dir / "materialized").mkdir()
        pd.DataFrame(rows, columns=FULL_COLUMNS).to_parquet(project_dir / "materialized" / "location.parquet", index=False)
        values = "@load:materialized/location.parquet"
    entity: dict[str, Any] = {"type": "fixed", "public_id": "location_id", "keys": [], "columns": list(FULL_COLUMNS), "values": values}
    if with_types:
        entity["column_types"] = dict(ID_TYPES)
    return entity


@pytest.mark.parametrize("with_types", [False, True], ids=["no-column-types", "id-column-types"])
@pytest.mark.parametrize("storage", ["inline", "parquet"])
async def test_ids_survive_repeated_entity_saves(project_dir: Path, storage: str, with_types: bool) -> None:
    write_project(project_dir, {"location": location_entity(project_dir, storage, with_types)})
    service = ProjectService(projects_dir=project_dir.parent)
    project_file: str = str(project_dir / "shapeshifter.yml")

    # The second save starts from the form that the first save wrote.
    for _ in range(2):
        save_entity_unchanged(service, project_dir.name)

        assert saved_entity(project_dir, "location")["columns"] == ["name"]
        assert await reload_ids(ShapeShiftProject.from_file(project_file), "location") == ([143, 7], [501, 502])

    core_project = ProjectMapper.to_core(service.load_project(project_dir.name, force_reload=True), validate_mapping_sidecar=False)
    assert await reload_ids(core_project, "location") == ([143, 7], [501, 502])


@pytest.mark.parametrize("storage_format", ["inline", "parquet"])
async def test_materialized_entity_keeps_its_ids(project_dir: Path, monkeypatch, storage_format: str) -> None:
    monkeypatch.setenv("SHAPE_SHIFTER_MATERIALIZATION_INLINE_THRESHOLD", "0")
    write_project(
        project_dir,
        {
            "raw": {
                "type": "fixed",
                "public_id": "raw_id",
                "keys": [],
                "columns": ["system_id", "raw_id", "location_id", "name"],
                "values": [[1, None, 501, "x"], [2, None, 502, "y"]],
            },
            # `location` takes its public ID values from its source.
            "location": {"type": "entity", "source": "raw", "public_id": "location_id", "keys": [], "columns": ["location_id", "name"]},
        },
    )

    result = await MaterializationService(ProjectService(projects_dir=project_dir.parent)).materialize_entity(
        project_dir.name, "location", storage_format=storage_format
    )

    assert result.success, result.errors
    assert saved_entity(project_dir, "location")["columns"] == ["name"]
    project = ShapeShiftProject.from_file(str(project_dir / "shapeshifter.yml"))
    assert await reload_ids(project, "location") == ([1, 2], [501, 502])
