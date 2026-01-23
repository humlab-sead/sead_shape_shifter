"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

Usage:
    python shaper_shifter.py input.csv output.xlsx

"""

import os
from pathlib import Path

from loguru import logger

from src.transforms.translate import extract_translation_map
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications import CompositeProjectSpecification
from src.utility import load_shape_file

# pylint: disable=no-value-for-parameter


def resolve_config(project: ShapeShiftProject | str, env_file: str | None = None) -> ShapeShiftProject:

    if isinstance(project, str):

        if not Path(project).exists():
            raise FileNotFoundError(f"Project file not found: {project}")

        if not env_file:
            raise FileNotFoundError("Environment file not specified")

        if not Path(env_file).exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")

        project = ShapeShiftProject.from_file(project, env_file=env_file, env_prefix="SEAD_NORMALIZER")

    if not isinstance(project, ShapeShiftProject):
        raise ValueError("Invalid project configuration")

    return project


async def workflow(
    project: str | ShapeShiftProject,
    target: str,
    translate: bool,
    target_type: str,
    drop_foreign_keys: bool,
    default_entity: str | None = None,
    env_file: str | None = None,
) -> None:

    project = resolve_config(project, env_file=env_file)

    shapeshifter: ShapeShifter = ShapeShifter(project=project, default_entity=default_entity)

    await shapeshifter.normalize()

    if drop_foreign_keys:
        shapeshifter.drop_foreign_key_columns()

    if translate:
        translations_map: dict[str, str] = extract_translation_map(fields_metadata=project.options.get("translation") or [])
        shapeshifter.translate(translations_map=translations_map)

    shapeshifter.add_system_id_columns()
    shapeshifter.move_keys_to_front()
    shapeshifter.map_to_remote(project.mappings)
    shapeshifter.store(target=target, mode=target_type)
    shapeshifter.log_shapes(target=target)

    # if verbose:
    #     click.echo("\nTable Summary:")
    #     for name, table in shapeshifter.table_store.items():
    #         click.echo(f"  - {name}: {len(table)} rows")


def validate_project(project: str | ShapeShiftProject) -> bool:
    if isinstance(project, str):
        if not Path(project).exists():
            raise FileNotFoundError(f"Project file not found: {project}")

        project = ShapeShiftProject.from_file(project, env_prefix="SEAD_NORMALIZER", env_file=".env")

    specification = CompositeProjectSpecification(project.cfg)
    is_satisfied: bool = specification.is_satisfied_by()
    if specification.has_errors():
        logger.error(f"Configuration validation failed with errors:\n{specification.get_report()}")
    elif specification.has_warnings():
        logger.warning(f"Configuration validation completed with warnings:\n{specification.get_report()}")
    else:
        logger.info("Configuration validation passed successfully.")
    return is_satisfied


def validate_entity_shapes(target: str, mode: str, regression_file: str | None):
    if mode != "csv" or not regression_file:
        return

    truth_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=regression_file)
    new_shapes: dict[str, tuple[int, int]] = load_shape_file(filename=os.path.join(target, "table_shapes.tsv"))

    entities_with_different_shapes = [
        (entity, truth_shapes.get(entity), new_shapes.get(entity))
        for entity in set(truth_shapes.keys()).union(set(new_shapes.keys()))
        if truth_shapes.get(entity) != new_shapes.get(entity)
    ]
    if len(entities_with_different_shapes) > 0:
        logger.warning("✗ Regression check failed: Entities with different shapes:")
        logger.warning("\n".join(f" {z[0]:>30}: expected {str(z[1]):<15} found {str(z[2]):<20}" for z in entities_with_different_shapes))
