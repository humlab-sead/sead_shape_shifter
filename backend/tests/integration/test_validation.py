import asyncio
import os
import shutil
from logging import warning
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jpype
import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.validation import ValidationError
from backend.app.services.dependency_service import DependencyGraph, DependencyService, get_dependency_service
from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    TableStoreDataFetchStrategy,
)
from backend.app.validators.target_model_validator import TargetModelValidator
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


@pytest.fixture(scope="function", name="project")
def _core_project() -> ShapeShiftProject:
    """Load the test project configuration for each test."""
    config_file: str = "./tests/test_data/projects/arbodat/shapeshifter.yml"
    return ShapeShiftProject.from_file(config_file, env_prefix="SHAPE_SHIFTER", env_file=".env")


#############################################################################################################
# Structural validation
#############################################################################################################


def test_composite_project_specification_is_satisfied_by(project: ShapeShiftProject):

    specification = CompositeProjectSpecification(project.cfg)
    is_valid: bool = specification.is_satisfied_by()

    print(specification.get_report())

    assert is_valid is True, specification.get_report()


#############################################################################################################
# Circular dependency validation
#############################################################################################################


def test_check_circular_dependencies(project: ShapeShiftProject):

    dependency_service: DependencyService = get_dependency_service()
    api_project: Project = ProjectMapper.to_api_config(project.cfg, name="arbodat")
    graph: DependencyGraph = dependency_service.analyze_dependencies(api_project)

    assert graph["has_cycles"] is False, f"Expected no circular dependencies, found cycles: {graph['cycles']}"


#############################################################################################################
# Data validation
#############################################################################################################


@pytest.mark.asyncio
async def test_data_validation_orchestrator(project: ShapeShiftProject):

    expected_issues: list[str] = [
        f"warning:dating:EMPTY_RESULT",
        f"warning:site_natural_region:EMPTY_RESULT"
    ]

    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    assert len(normalizer.table_store) > 0, "Table store should contain normalized entities"

    strategy = TableStoreDataFetchStrategy(table_store=normalizer.table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project, project_name="arbodat", entity_names=None
    )

    issues = [issue for issue in issues if f"{issue.severity}:{issue.entity}:{issue.code}" not in expected_issues]

    issue_report: str = "\n".join(f"{issue.severity} [{issue.code}] {issue.entity}: {issue.message}" for issue in issues)

    error_count: int = sum(1 for issue in issues if issue.severity == "error" and issue.code != 'EMPTY_RESULT')
    assert error_count == 0, f"Expected no validation errors, found {error_count}\n{issue_report}"

    warning_count: int = sum(1 for issue in issues if issue.severity == "warning")
    
    assert warning_count == 0, f"Expected no validation warnings, found {warning_count}\n{issue_report}"


#############################################################################################################
# Target model conformance validation
#############################################################################################################


def test_missing_required_column_returns_error(project: ShapeShiftProject):

    assert project.metadata.target_model, "Test project must have a target model defined for this test"

    target_model_data: dict[str, Any] = project.metadata.target_model

    errors: list[ValidationError] = TargetModelValidator().validate(target_model_data, project)

    assert not errors, f"Expected no validation errors, found {len(errors)}: {[error.message for error in errors]}"
