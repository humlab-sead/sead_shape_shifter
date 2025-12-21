import asyncio
import os
import shutil

import pytest

from src.model import ShapeShiftConfig
from src.survey2excel import validate_entity_shapes, workflow
from src.utility import load_shape_file

# def test_workflow():

#     config_file: str = "./input/arbodat.yml"
#     translate: bool = False

#     output_filename: str = f"output{'' if not translate else '_translated'}.xlsx"
#     asyncio.run(
#         setup_config_store(
#             config_file,
#             env_prefix="SEAD_NORMALIZER",
#             env_filename="./input/.env",
#             db_opts_path=None,
#         )
#     )
#     asyncio.sleep(0.1)  # type: ignore ; ensure config is fully loaded;
#     if os.path.exists(output_filename):
#         os.remove(output_filename)

#     assert not os.path.exists(output_filename)
#     asyncio.run(
#         workflow(
#             input_csv="./input/arbodat_mal_elena_input.csv",
#             target=output_filename,
#             sep=";",
#             verbose=False,
#             translate=translate,
#             mode="xlsx",
#             drop_foreign_keys=False,
#         )
#     )

#     assert os.path.exists(output_filename)


@pytest.mark.skip(reason="Pending deprecation, will be replaced with database tests")
def test_workflow_using_survey_report_to_csv():

    config_file: str = "./input/arbodat-test.yml"
    translate: bool = False

    output_path: str = "tmp/arbodat/"
    config: ShapeShiftConfig = ShapeShiftConfig.from_file(
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
            config=config,
            target=output_path,
            translate=translate,
            mode="csv",
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


def test_access_database_csv_workflow():

    config_file: str = "./input/arbodat-database.yml"
    config: ShapeShiftConfig = ShapeShiftConfig.from_file(
        config_file,
        env_prefix="SEAD_NORMALIZER",
        env_file=".env",
    )

    translate: bool = False

    output_path: str = "tmp/arbodat-database/"
    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)

    assert not os.path.exists(output_path)

    _ = asyncio.run(
        workflow(
            config=config,
            target=output_path,
            translate=translate,
            mode="csv",
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

    entities_with_different_shapes = [  # pylint: disable=unused-variable
        (entity, truth_shapes.get(entity), new_shapes.get(entity))
        for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
        if truth_shapes.get(entity) != new_shapes.get(entity)
    ]
    validate_entity_shapes(output_path, "csv", "./input/table_shapes.tsv")

    # assert len(entities_with_different_shapes) == 0, f"Entities with different shapes: {entities_with_different_shapes}"
