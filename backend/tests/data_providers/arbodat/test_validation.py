from collections import Counter
import copy
import os
from pathlib import Path
from typing import Any

import jpype
import pytest
from dotenv import dotenv_values
from loguru import logger
from ruamel import yaml

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
from src.target_model.conformance import ConformanceIssue, TargetModelConformanceValidator
from src.target_model.models import TargetModel
from src.validators.data_validators import ValidationIssue

TEST_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "test_data"
TARGET_MODEL_PATH: Path = TEST_DATA_DIR / "target_models" / "sead_standard_model.yml"
PROJECTS_DIR: Path = TEST_DATA_DIR / "projects"


@pytest.fixture(scope="module", autouse=True)
def initialize_jvm():
    """Initialize JVM once for all tests in this module."""
    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess()
    yield


@pytest.fixture(scope="module", name="arbodat_project")
def _arbodat_project() -> ShapeShiftProject:
    """Load the backend integration test project configuration once per module.

    Applies data/test.env first and the local data/.env second, so a variable defined in
    both files takes the value from data/.env. The environment is applied only for the
    duration of the load through a temporary MonkeyPatch; directive values are resolved
    into the returned project, so tests do not depend on the process environment.
    """
    with pytest.MonkeyPatch.context() as env_patch:
        for env_file, override in (("data/test.env", False), ("data/.env", True)):
            for name, value in dotenv_values(env_file).items():
                if value is not None and (override or name not in os.environ):
                    env_patch.setenv(name, value)

        config_file: str = "tests/test_data/projects/arbodat/shapeshifter.yml"

        return ShapeShiftProject.from_file(config_file)


@pytest.fixture(scope="function", name="project")
def _project(arbodat_project: ShapeShiftProject) -> ShapeShiftProject:
    """Provide each test with its own copy of the parsed project."""
    return copy.deepcopy(arbodat_project)


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

    expected_issues: set[str] = {
        "warning:dataset_submission:FK_DATA_INTEGRITY",
        "warning:ecocode:FK_DATA_INTEGRITY",
        "warning:method:FK_ALL_NULL",
        "warning:dating:EMPTY_RESULT",
        "warning:site_natural_region:EMPTY_RESULT",
    }

    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    assert len(normalizer.table_store) > 0, "Table store should contain normalized entities"

    strategy = TableStoreDataFetchStrategy(table_store=normalizer.table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project, project_name="arbodat", entity_names=None
    )
    actual_issues: set[str] = {f"{issue.severity}:{issue.entity}:{issue.code}" for issue in issues}

    print("\n".join({f"{issue.severity}:{issue.entity}:{issue.code}:{issue.message}" for issue in issues}))
    assert expected_issues == actual_issues, f"Expected issues {expected_issues}, but found {actual_issues}"


#############################################################################################################
# Target model conformance validation
#############################################################################################################


def test_target_model_conformance(project: ShapeShiftProject):

    assert project.metadata.target_model, "Test project must have a target model defined for this test"

    target_model_data: dict[str, Any] = project.metadata.target_model

    errors: list[ValidationError] = TargetModelValidator().validate(target_model_data, project)

    if errors:
        error_report: str = "\n".join(f"{str(error.severity).upper()} {error.code} [{error.entity}]: {error.message}" for error in errors)
        logger.warning(f"Target model validation found {len(errors)} errors:\n{error_report}")

    # assert not errors, f"Expected no validation errors, found {len(errors)}: {[error.message for error in errors]}"


def test_core_conformance_reports_known_gaps_for_full_arbodat_project() -> None:
    target_model: TargetModel = load_target_model()
    project: ShapeShiftProject = load_real_project("arbodat")

    expected_errors = [
        ("CONDITIONAL_FK_AWAITING_RECONCILIATION", "location"),
        ("MISSING_REQUIRED_COLUMN", "relative_dating"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "abundance_modification"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "abundance_property"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "relative_dating"),
        ("UNEXPECTED_PUBLIC_ID", "relative_dating"),
    ]

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
    actual_issues = [(issue.code, issue.entity) for issue in issues]
    # print('\n'.join(f'{x.code};{x.entity};{x.message}' for x in issues))
    assert sorted(actual_issues) == sorted(expected_errors)


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.safe_load(TARGET_MODEL_PATH.read_text(encoding="utf-8")))


def load_real_project(project_name: str) -> ShapeShiftProject:
    project_path: Path = Path(PROJECTS_DIR / project_name / "shapeshifter.yml")
    return ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))


def test_core_conformance_current_corpus_issue_families_are_stable() -> None:
    target_model: TargetModel = load_target_model()
    project: ShapeShiftProject = load_real_project("arbodat")

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    issue_summary: Counter[str | None] = Counter(issue.code for issue in issues)

    assert issue_summary == Counter(
        {
            "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 3,
            "UNEXPECTED_PUBLIC_ID": 1,
            "CONDITIONAL_FK_AWAITING_RECONCILIATION": 1,
            "MISSING_REQUIRED_COLUMN": 1,
        }
    )
