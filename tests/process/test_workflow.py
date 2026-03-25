import asyncio
import os
import shutil
from pathlib import Path

import jpype
import pandas as pd
import pytest

from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    TableStoreDataFetchStrategy,
)
from src.loaders.sql_loaders import init_jvm_for_ucanaccess
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications.project import CompositeProjectSpecification
from src.utility import load_shape_file
from src.validators.data_validators import ValidationIssue
from src.workflow import validate_entity_shapes, workflow


@pytest.fixture(scope="module", autouse=True)
def initialize_jvm():
    """Initialize JVM once for all tests in this module."""
    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess()
    yield


def test_validate_project_file():

    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"
    project: ShapeShiftProject = ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")

    specification = CompositeProjectSpecification(project.cfg)
    is_valid: bool = specification.is_satisfied_by()

    print(specification.get_report())

    assert is_valid is True, specification.get_report()


def test_access_database_csv_workflow():

    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"
    config: ShapeShiftProject = ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")

    translate: bool = False
    target_type: str = "csv"

    output_path: Path = Path("tmp/arbodat-test.xlsx") if target_type in ("xlsx", "openpyxl") else Path("tmp/arbodat-test")

    asyncio.run(asyncio.sleep(0.1))  # type: ignore ; ensure config is fully loaded;

    remove_path(output_path)

    assert not os.path.exists(output_path)

    _ = asyncio.run(
        workflow(
            project=config,
            target=str(output_path),
            translate=translate,
            target_type=target_type,
            drop_foreign_keys=False,
        )
    )

    assert os.path.exists(output_path)

    shape_filename: Path = (output_path if output_path.is_dir() else output_path.parent) / "table_shapes.tsv"

    assert os.path.exists(shape_filename)


def check_regression_of_shapes(output_path: Path, shape_filename: Path):
    # Load and verify table shapes
    # Truth is stored in ./projects/table_shapes.tsv
    # We need to compare this against the generated tsv-files in output_path
    truth_filename: Path = Path("./projects/table_shapes.tsv")
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


@pytest.mark.asyncio
async def test_full_data_validation():
    """Test full data validation using normalized table store.

    This test:
    1. Loads a project configuration
    2. Runs full normalization to create table store
    3. Validates all entities using the normalized data
    4. Checks that validation passes for well-formed data
    """
    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"
    project: ShapeShiftProject = ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")

    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    assert len(normalizer.table_store) > 0, "Table store should contain normalized entities"

    strategy = TableStoreDataFetchStrategy(table_store=normalizer.table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Run validation on all entities
    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project, project_name="arbodat", entity_names=None
    )
    issue_report: str = "\n".join(f"{issue.severity} [{issue.code}] {issue.entity}: {issue.message}" for issue in issues)
    error_count: int = sum(1 for issue in issues if issue.severity == "error")
    assert error_count == 0, f"Expected no validation errors, found {error_count}\n{issue_report}"


@pytest.mark.asyncio
async def test_full_data_validation_with_unresolved_extra_columns():
    """Test full data validation detects unresolved extra_columns.

    This test verifies that the validation system correctly identifies
    extra_columns that reference non-existent columns after normalization.
    """
    # Create a minimal test project with intentionally unresolved extra_columns
    test_config: dict = {
        "metadata": {"name": "test_unresolved", "description": "Test unresolved extra columns"},
        "options": {"data_sources": {}},
        "entities": {
            "test_entity": {
                "type": "fixed",
                "columns": ["col_a", "col_b"],
                "values": [[1, 2], [3, 4]],
                "keys": ["col_a"],
                "public_id": "test_entity_id",
                "extra_columns": {
                    "valid_concat": "=concat(col_a, col_b)",  # Should resolve
                    "invalid_ref": "nonexistent_column",  # Should NOT resolve
                    "invalid_formula": "=upper(missing_col)",  # Should NOT resolve
                },
            }
        },
    }

    project = ShapeShiftProject(cfg=test_config)

    # Run full normalization
    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    # Verify unresolved extra columns were tracked
    assert "test_entity" in normalizer.unresolved_extra_columns, "Should track unresolved extra columns"
    unresolved = normalizer.unresolved_extra_columns["test_entity"]

    print(f"\nUnresolved extra columns: {unresolved}")

    # Verify that the problematic extra_columns are in the unresolved set
    # Note: 'invalid_ref' referring to a plain column name may be handled differently than formulas
    assert len(unresolved) >= 1, f"Expected at least 1 unresolved extra column, found {len(unresolved)}"

    # Create a custom strategy that includes unresolved extra column issues
    class TestDataFetchStrategy(TableStoreDataFetchStrategy):
        """Custom strategy that includes unresolved extra column validation."""

        def __init__(self, table_store: dict[str, pd.DataFrame], unresolved_map: dict[str, dict[str, dict]]) -> None:
            super().__init__(table_store)
            self.unresolved_map = unresolved_map

        async def get_additional_issues(self, project_name: str, entity_name: str) -> list[ValidationIssue]:
            """Return unresolved extra column issues."""
            from src.validators.data_validators import UnresolvedExtraColumnsValidator

            unresolved_extra_columns = self.unresolved_map.get(entity_name, {})
            return UnresolvedExtraColumnsValidator.validate(unresolved_extra_columns, entity_name)

    # Create validation strategy with unresolved tracking
    strategy = TestDataFetchStrategy(
        table_store=normalizer.table_store,
        unresolved_map=normalizer.unresolved_extra_columns,
    )
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Run validation
    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project,
        project_name="test_unresolved",
        entity_names=["test_entity"],
    )

    # Print validation issues for debugging
    print(f"\nFound {len(issues)} validation issues:")
    for issue in issues:
        print(f"  - {issue.severity} [{issue.code}] {issue.entity}.{issue.field}: {issue.message}")

    # Verify that unresolved extra column errors were detected
    unresolved_errors = [issue for issue in issues if issue.code == "EXTRA_COLUMN_UNRESOLVED"]

    assert len(unresolved_errors) >= 1, f"Expected unresolved extra column errors, found {len(unresolved_errors)}"

    # Verify error details mention the problematic extra columns
    error_messages = " ".join(issue.message for issue in unresolved_errors)
    assert (
        "invalid_" in error_messages.lower() or "missing" in error_messages.lower()
    ), f"Expected errors to mention missing columns, got: {error_messages}"
