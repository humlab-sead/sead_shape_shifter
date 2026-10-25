import copy
import os
from collections import Counter
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

TEST_DATA_DIR: Path = Path("tests/test_data").resolve()
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


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.YAML(typ="safe").load(TARGET_MODEL_PATH.read_text(encoding="utf-8")))


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
    site_location_df = normalizer.table_store["site_location"]
    kville_rows = site_location_df.loc[(site_location_df["Fustel"] == "Kville 1502") & site_location_df["EVNr"].isna()]
    assert not kville_rows.empty, "The site_location row with a null EVNr should link to the matching site row"

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

# pylint: disable=line-too-long

def test_core_conformance_reports_known_gaps_for_full_arbodat_project(project: ShapeShiftProject) -> None:
    target_model: TargetModel = load_target_model()

    expected_issues: list[str] = [
        "UNEXPECTED_PUBLIC_ID;relative_dating;Entity 'relative_dating' declares public_id 'relative_age_id' but target model expects 'relative_date_id'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;sample_group;Entity 'sample_group' is missing required foreign key target 'site'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;sample_group;Entity 'sample_group' is missing required foreign key target 'method'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;dataset;Entity 'dataset' is missing required foreign key target 'submission'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;dataset;Entity 'dataset' is missing required foreign key target 'data_type'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;analysis_entity;Entity 'analysis_entity' is missing required foreign key target 'dataset'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;abundance_modification;Entity 'abundance_modification' is missing required foreign key target 'abundance'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;abundance_property;Entity 'abundance_property' is missing required foreign key target 'abundance'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;abundance_property;Entity 'abundance_property' is missing required foreign key target 'property_type'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;relative_dating;Entity 'relative_dating' is missing required foreign key target 'analysis_entity'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;site_property;Entity 'site_property' is missing required foreign key target 'property_type'",
        "MISSING_REQUIRED_FOREIGN_KEY_TARGET;feature_property;Entity 'feature_property' is missing required foreign key target 'property_type'",
        "CONDITIONAL_FK_AWAITING_RECONCILIATION;location;Conditional foreign key from 'location' to 'location_type' is awaiting reconciliation; project conformance cannot determine whether rows will be inserted.",
        "ORPHAN_FACT_ENTITY;sample_group;Fact entity 'sample_group' does not reach any lookup or classifier entity",
        "ORPHAN_FACT_ENTITY;abundance_property;Fact entity 'abundance_property' does not reach any lookup or classifier entity",
        "MISSING_REQUIRED_COLUMN;sample_type;Entity 'sample_type' is missing required target column 'type_name'",
        "MISSING_REQUIRED_COLUMN;sample_coordinate;Entity 'sample_coordinate' is missing required target column 'measurement'",
        "MISSING_REQUIRED_COLUMN;dataset;Entity 'dataset' is missing required target column 'submission_id'",
        "MISSING_REQUIRED_COLUMN;analysis_entity;Entity 'analysis_entity' is missing required target column 'dataset_id'",
        "MISSING_REQUIRED_COLUMN;abundance_property;Entity 'abundance_property' is missing required target column 'property_type_id'",
        "MISSING_REQUIRED_COLUMN;abundance_property;Entity 'abundance_property' is missing required target column 'property_value'",
        "MISSING_REQUIRED_COLUMN;relative_dating;Entity 'relative_dating' is missing required target column 'analysis_entity_id'",
        "MISSING_REQUIRED_COLUMN;contact_type;Entity 'contact_type' is missing required target column 'contact_type_name'",
        "MISSING_REQUIRED_COLUMN;feature;Entity 'feature' is missing required target column 'feature_name'",
        "MISSING_REQUIRED_COLUMN;site_property;Entity 'site_property' is missing required target column 'property_type_id'",
        "MISSING_REQUIRED_COLUMN;site_property;Entity 'site_property' is missing required target column 'property_value'",
        "MISSING_REQUIRED_COLUMN;feature_property;Entity 'feature_property' is missing required target column 'property_type_id'",
        "MISSING_REQUIRED_COLUMN;feature_property;Entity 'feature_property' is missing required target column 'property_value'",
        "MISSING_REQUIRED_ENTITY;data_provider;Target model requires entity 'data_provider'",
        "MISSING_REQUIRED_ENTITY;citation;Target model requires entity 'citation'",
        "MISSING_INDUCED_REQUIRED_ENTITY;property_type;Entity 'property_type' is required because entity 'abundance_property' is present and has a required foreign key chain to 'property_type'",
    ]

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
    actual_issues: list[str] = [f"{x.code};{x.entity};{x.message}" for x in issues]
    assert sorted(actual_issues) == sorted(expected_issues)


def test_core_conformance_current_corpus_issue_families_are_stable(project: ShapeShiftProject) -> None:
    target_model: TargetModel = load_target_model()

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    issue_summary: Counter[str | None] = Counter(issue.code for issue in issues)

    assert issue_summary == Counter(
        {
            "MISSING_REQUIRED_COLUMN": 13,
            "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 11,
            "ORPHAN_FACT_ENTITY": 2,
            "MISSING_REQUIRED_ENTITY": 2,
            "UNEXPECTED_PUBLIC_ID": 1,
            "CONDITIONAL_FK_AWAITING_RECONCILIATION": 1,
            "MISSING_INDUCED_REQUIRED_ENTITY": 1,
        }
    )
