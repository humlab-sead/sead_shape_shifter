"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

Usage:
    python shaper_shifter.py input.csv output.xlsx

"""

import os
from collections.abc import Mapping
from pathlib import Path

from loguru import logger

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.output_expectations import OutputExpectationEvaluation, evaluate_output_expectations
from src.specifications import CompositeProjectSpecification
from src.specifications.output_expectations import OutputExpectationsSpecification
from src.transforms.translate import extract_translation_map
from src.utility import load_shape_file

# pylint: disable=no-value-for-parameter


def resolve_config(project: ShapeShiftProject | str, env_file: str | None = None) -> ShapeShiftProject:
    """Resolve the project configuration from a file or object."""
    if isinstance(project, str):
        if not Path(project).exists():
            raise FileNotFoundError(f"Project file not found: {project}")

        if not env_file:
            raise FileNotFoundError("Environment file not specified")

        if not Path(env_file).exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")

        project = ShapeShiftProject.from_file(project, env_file=env_file, env_prefix="SHAPE_SHIFTER")

    if not isinstance(project, ShapeShiftProject):
        raise ValueError("Invalid project configuration")

    return project


async def normalize_project(
    project: str | ShapeShiftProject,
    translate: bool,
    drop_foreign_keys: bool,
    default_entity: str | None = None,
    env_file: str | None = None,
    check_output_expectations: bool = False,
) -> ShapeShifter:
    """Normalize a project's tables and return the completed ShapeShifter without writing output.

    Applies the same post-normalization options as ``workflow()`` in the same order:
    foreign key column dropping, then column translation. No dispatcher is invoked
    and no output target is required.
    """
    resolved_project: ShapeShiftProject = resolve_config(project, env_file=env_file)

    shapeshifter: ShapeShifter = ShapeShifter(project=resolved_project, default_entity=default_entity)

    should_evaluate_expectations = check_output_expectations and bool(resolved_project.options.get("output_expectations"))
    if should_evaluate_expectations:
        await shapeshifter.normalize(continue_on_error=True)
        shapeshifter.output_expectation_evaluation = evaluate_output_expectations(
            project=resolved_project,
            tables=shapeshifter.table_store,
            incomplete_entities=shapeshifter.incomplete_entities,
        )
    else:
        await shapeshifter.normalize()

    if drop_foreign_keys:
        shapeshifter.drop_foreign_key_columns()

    if translate:
        translations_map: dict[str, str] = extract_translation_map(fields_metadata=resolved_project.options.get("translation") or [])
        shapeshifter.translate(translations_map=translations_map)

    # Note: add_system_id_columns, add_public_id_columns, and move_keys_to_front
    # are now called within normalize() to ensure materialized entities get identity columns
    return shapeshifter


async def workflow(
    project: str | ShapeShiftProject,
    target: str,
    translate: bool,
    target_type: str,
    drop_foreign_keys: bool,
    default_entity: str | None = None,
    env_file: str | None = None,
) -> OutputExpectationEvaluation | None:
    """Normalize and store tables, then return any output expectation results."""
    resolved_project = resolve_config(project, env_file=env_file)
    expectation_specification = OutputExpectationsSpecification(resolved_project.cfg)
    if not expectation_specification.is_satisfied_by():
        error_details = "\n".join(str(error) for error in expectation_specification.errors)
        raise ValueError(f"Invalid output expectation declarations:\n{error_details}")

    shapeshifter: ShapeShifter = await normalize_project(
        resolved_project,
        translate=translate,
        drop_foreign_keys=drop_foreign_keys,
        default_entity=default_entity,
        env_file=None,
        check_output_expectations=True,
    )

    evaluation: OutputExpectationEvaluation | None = shapeshifter.output_expectation_evaluation
    if evaluation is not None and not evaluation.passed:
        return evaluation

    if shapeshifter.incomplete_entities:
        raise ValueError(_incomplete_output_message(shapeshifter.incomplete_entities))

    shapeshifter.store(target=target, mode=target_type)
    shapeshifter.log_shapes(target=target)
    return evaluation

    # if verbose:
    #     click.echo("\nTable Summary:")
    #     for name, table in shapeshifter.table_store.items():
    #         click.echo(f"  - {name}: {len(table)} rows")


def _incomplete_output_message(incomplete_entities: Mapping[str, str]) -> str:
    """Describe why a full run cannot write output with an incomplete entity."""
    details = "; ".join(f"entity '{entity}': {reason}" for entity, reason in incomplete_entities.items())
    return f"Full-run output is incomplete and was not written: {details}"


def validate_project(project: str | ShapeShiftProject) -> bool:
    """Validate the project configuration against specifications."""
    if isinstance(project, str):
        if not Path(project).exists():
            raise FileNotFoundError(f"Project file not found: {project}")

        project = ShapeShiftProject.from_file(project, env_prefix="SHAPE_SHIFTER", env_file=".env")

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
    """Validate entity shapes against a regression file if provided."""
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
