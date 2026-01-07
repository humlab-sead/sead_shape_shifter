import asyncio
import os
from pathlib import Path
import shutil

import pytest

from src.model import ShapeShiftProject
from src.specifications.project import CompositeProjectSpecification
from src.utility import load_shape_file
from src.workflow import validate_entity_shapes, workflow


def test_validate_project_file():

    config_file: str = "./input/arbodat-test.yml"
    project: ShapeShiftProject = ShapeShiftProject.from_file(
        config_file,
        env_prefix="SEAD_NORMALIZER",
        env_file=".env",
    )

    specification = CompositeProjectSpecification(project.cfg)
    is_valid: bool = specification.is_satisfied_by()

    print(specification.get_report())

    assert is_valid is True


def test_access_database_csv_workflow():

    config_file: str = "./input/arbodat-test.yml"
    config: ShapeShiftProject = ShapeShiftProject.from_file(
        config_file,
        env_prefix="SEAD_NORMALIZER",
        env_file=".env",
    )

    translate: bool = False

    output_path: Path = Path("tmp/arbodat-test.xlsx")
    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    remove_path(output_path)

    assert not os.path.exists(output_path)

    _ = asyncio.run(
        workflow(
            project=config,
            target=str(output_path),
            translate=translate,
            target_type="xlsx",
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)

    shape_filename: Path = (output_path if output_path.is_dir() else output_path.parent) / "table_shapes.tsv"

    assert os.path.exists(shape_filename)


def check_regression_of_shapes(output_path: Path, shape_filename: Path):
    # Load and verify table shapes
    # Truth is stored in ./input/table_shapes.tsv
    # We need to compare this against the generated tsv-files in output_path
    truth_filename: Path = Path("./input/table_shapes.tsv")
    if truth_filename.exists():
        truth_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=str(truth_filename))
        new_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=str(shape_filename))

        entities_with_different_shapes = [  # noqa: F841 ;pylint: disable=unused-variable
            (entity, truth_shapes.get(entity), new_shapes.get(entity))
            for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
            if truth_shapes.get(entity) != new_shapes.get(entity)
        ]
        validate_entity_shapes(str(output_path), "csv", str(shape_filename))


def remove_path(output_path):
    if os.path.exists(output_path):
        if os.path.isdir(output_path):
            shutil.rmtree(output_path)
        else:
            os.remove(output_path)

    # assert len(entities_with_different_shapes) == 0, f"Entities with different shapes: {entities_with_different_shapes}"
