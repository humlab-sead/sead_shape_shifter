import asyncio
import os
import shutil
from pathlib import Path

import jpype
import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.dependency_service import DependencyGraph, DependencyService, get_dependency_service
from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    TableStoreDataFetchStrategy,
)
from src.loaders.sql_loaders import init_jvm_for_ucanaccess
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications.project import CompositeProjectSpecification
from src.table_store import TableStore
from src.utility import load_shape_file
from src.validators.data_validators import UnresolvedExtraColumnsValidator, ValidationIssue
from src.workflow import validate_entity_shapes, workflow


@pytest.fixture(scope="module", autouse=True)
def initialize_jvm():
    """Initialize JVM once for all tests in this module."""
    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess()
    yield


def test_composite_project_specification_is_satisfied_by():

    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"
    project: ShapeShiftProject = ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")

    specification = CompositeProjectSpecification(project.cfg)
    is_valid: bool = specification.is_satisfied_by()

    print(specification.get_report())

    assert is_valid is True, specification.get_report()


def test_check_circular_dependencies():

    dependency_service: DependencyService = get_dependency_service()
    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"

    core_project: ShapeShiftProject = ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")
    project: Project = ProjectMapper.to_api_config(core_project.cfg, name="arbodat")
    graph: DependencyGraph = dependency_service.analyze_dependencies(project)

    assert graph["has_cycles"] is False, f"Expected no circular dependencies, found cycles: {graph['cycles']}"



@pytest.mark.asyncio
async def test_data_validation_orchestrator():

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

