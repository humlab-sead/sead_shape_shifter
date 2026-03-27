from pathlib import Path

import yaml

from target_model_spec.conformance_validator import TargetModelConformanceValidator
from target_model_spec.models import TargetModel
from target_model_spec.project_models import ShapeShifterProject


ROOT_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT_DIR / "specs" / "sead_v2.yml"
EXAMPLES_DIR = ROOT_DIR / "examples"
REAL_PROJECTS_DIR = ROOT_DIR.parent / "tests" / "test_data" / "projects"


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")))


def load_project(name: str) -> ShapeShifterProject:
    project_path = EXAMPLES_DIR / name
    return ShapeShifterProject.model_validate(yaml.safe_load(project_path.read_text(encoding="utf-8")))


def load_real_project(project_name: str) -> ShapeShifterProject:
    project_path = REAL_PROJECTS_DIR / project_name / "shapeshifter.yml"
    return ShapeShifterProject.model_validate(yaml.safe_load(project_path.read_text(encoding="utf-8")))


def test_conformance_validator_accepts_minimal_conforming_project() -> None:
    target_model = load_target_model()
    project = ShapeShifterProject.model_validate(
        {
            "metadata": {
                "name": "sead:minimal-conforming",
                "type": "shapeshifter-project",
                "version": "1.0.0",
            },
            "entities": {
                "location": {
                    "public_id": "location_id",
                    "columns": ["location_name"],
                    "foreign_keys": [{"entity": "location_type"}],
                },
                "location_type": {
                    "public_id": "location_type_id",
                    "columns": ["location_type"],
                },
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name"],
                    "foreign_keys": [{"entity": "location"}],
                },
                "sample_group": {
                    "public_id": "sample_group_id",
                    "keys": ["site_id"],
                    "extra_columns": {"method_id": None, "sample_group_name": None},
                    "foreign_keys": [{"entity": "site"}, {"entity": "method"}],
                },
                "sample": {
                    "public_id": "physical_sample_id",
                    "extra_columns": {"sample_name": None},
                    "foreign_keys": [{"entity": "sample_group"}, {"entity": "sample_type"}],
                },
                "sample_type": {
                    "public_id": "sample_type_id",
                    "columns": ["type_name"],
                },
                "method": {
                    "public_id": "method_id",
                    "columns": ["method_name", "description", "method_group_id"],
                },
                "dataset": {
                    "public_id": "dataset_id",
                    "extra_columns": {"dataset_name": None, "data_type_id": None},
                    "foreign_keys": [{"entity": "method"}],
                },
                "analysis_entity": {
                    "public_id": "analysis_entity_id",
                    "foreign_keys": [{"entity": "sample"}, {"entity": "dataset"}],
                },
            },
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert issues == []


def test_conformance_validator_reports_known_gaps_for_real_fixture() -> None:
    target_model = load_target_model()
    project = load_project("sead_arbodat_core.yml")

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert sorted((issue.code, issue.entity) for issue in issues) == sorted([
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_COLUMN", "sample_type"),
    ])


def test_conformance_validator_reports_missing_entity_and_wrong_public_id() -> None:
    target_model = load_target_model()
    project = load_project("sead_missing_sample_group.yml")

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert ("MISSING_REQUIRED_ENTITY", "sample_group") in {(issue.code, issue.entity) for issue in issues}
    assert ("UNEXPECTED_PUBLIC_ID", "sample") in {(issue.code, issue.entity) for issue in issues}


def test_conformance_validator_keeps_alias_like_names_strict() -> None:
    target_model = load_target_model()
    project = ShapeShifterProject.model_validate(
        {
            "metadata": {
                "name": "sead:alias-like-columns",
                "type": "shapeshifter-project",
                "version": "1.0.0",
            },
            "entities": {
                "location": {
                    "public_id": "location_id",
                    "columns": ["location_name"],
                    "foreign_keys": [{"entity": "location_type"}],
                },
                "location_type": {
                    "public_id": "location_type_id",
                    "columns": ["location_type"],
                },
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name"],
                    "foreign_keys": [{"entity": "location"}],
                },
                "sample_group": {
                    "public_id": "sample_group_id",
                    "keys": ["site_id"],
                    "extra_columns": {"method_id": None, "sample_group_name": None},
                    "foreign_keys": [{"entity": "site"}, {"entity": "method"}],
                },
                "sample": {
                    "public_id": "physical_sample_id",
                    "extra_columns": {"sample_name": None},
                    "foreign_keys": [{"entity": "sample_group"}, {"entity": "sample_type"}],
                },
                "sample_type": {
                    "public_id": "sample_type_id",
                    "extra_columns": {"sample_type_name": None},
                },
                "method": {
                    "public_id": "method_id",
                    "columns": ["method_name", "description", "sead_method_group_id"],
                },
                "dataset": {
                    "public_id": "dataset_id",
                    "extra_columns": {"dataset_name": None, "data_type_id": None},
                    "foreign_keys": [{"entity": "method"}],
                },
                "analysis_entity": {
                    "public_id": "analysis_entity_id",
                    "foreign_keys": [{"entity": "sample"}, {"entity": "dataset"}],
                },
            },
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert ("MISSING_REQUIRED_COLUMN", "sample_type") in {(issue.code, issue.entity) for issue in issues}
    assert ("MISSING_REQUIRED_COLUMN", "method") in {(issue.code, issue.entity) for issue in issues}


def test_conformance_validator_reports_known_gaps_for_full_arbodat_project() -> None:
    target_model = load_target_model()
    project = load_real_project("arbodat")

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert sorted((issue.code, issue.entity) for issue in issues) == sorted([
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "site"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
        ("MISSING_REQUIRED_COLUMN", "sample_type"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
    ])