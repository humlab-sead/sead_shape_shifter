import asyncio
import os
import shutil

import pytest

from src.model import ShapeShiftProject
from src.specifications.project import CompositeProjectSpecification
from src.utility import load_shape_file
from src.workflow import validate_entity_shapes, workflow


@pytest.mark.skip(reason="Pending deprecation, will be replaced with database tests")
def test_workflow_using_survey_report_to_csv():

    config_file: str = "./input/arbodat-test.yml"
    translate: bool = False

    output_path: str = "tmp/arbodat/"
    config: ShapeShiftProject = ShapeShiftProject.from_file(
        config_file,
        env_prefix="SEAD_NORMALIZER",
        env_file=".env",
    )
    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    assert not os.path.exists(output_path)

    _ = asyncio.run(
        workflow(
            project=config,
            target=output_path,
            translate=translate,
            target_type="csv",
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)
    assert os.path.exists(os.path.join(output_path, "table_shapes.tsv"))

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output path not found: {output_path}")

    # Load and verify table shapes
    # Truth is stored in ./input/table_shapes.tsv
    # We need to compare this against the generated tsv-files in output_path
    truth_shapes: dict[str, tuple[int, int]] = load_shape_file(filename="./input/table_shapes.tsv")
    new_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=os.path.join(output_path, "table_shapes.tsv"))

    entities_with_different_shapes = [
        (entity, truth_shapes.get(entity), new_shapes.get(entity))
        for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
        if truth_shapes.get(entity) != new_shapes.get(entity)
    ]
    validate_entity_shapes(output_path, "csv", "./input/table_shapes.tsv")

    assert len(entities_with_different_shapes) == 0, f"Entities with different shapes: {entities_with_different_shapes}"


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

    output_path: str = "tmp/arbodat-test.xlsx"
    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    assert not os.path.exists(output_path)

    _ = asyncio.run(
        workflow(
            project=config,
            target=output_path,
            translate=translate,
            target_type="xlsx",
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)
    assert os.path.exists(os.path.join(output_path, "table_shapes.tsv"))

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output path not found: {output_path}")

    # Load and verify table shapes
    # Truth is stored in ./input/table_shapes.tsv
    # We need to compare this against the generated tsv-files in output_path
    truth_shapes: dict[str, tuple[int, int]] = load_shape_file(filename="./input/table_shapes.tsv")
    new_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=os.path.join(output_path, "table_shapes.tsv"))

    entities_with_different_shapes = [  # noqa: F841 ;pylint: disable=unused-variable
        (entity, truth_shapes.get(entity), new_shapes.get(entity))
        for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
        if truth_shapes.get(entity) != new_shapes.get(entity)
    ]
    validate_entity_shapes(output_path, "csv", "./input/table_shapes.tsv")

    # assert len(entities_with_different_shapes) == 0, f"Entities with different shapes: {entities_with_different_shapes}"
