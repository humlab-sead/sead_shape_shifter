from pathlib import Path
from collections import Counter

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


def issue_pairs(target_model: TargetModel, project: ShapeShifterProject) -> list[tuple[str, str | None]]:
    issues = TargetModelConformanceValidator().validate(target_model, project)
    return [(issue.code, issue.entity) for issue in issues]


def test_conformance_validator_accepts_minimal_conforming_project() -> None:
    target_model = load_target_model()
    project = load_project("sead_canonical_minimal.yml")

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert issues == []


def test_conformance_validator_reports_known_gaps_for_real_fixture() -> None:
    target_model = load_target_model()
    project = load_project("sead_arbodat_core.yml")

    assert sorted(issue_pairs(target_model, project)) == sorted([
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_COLUMN", "sample_type"),
    ])


def test_conformance_validator_reports_missing_entity_and_wrong_public_id() -> None:
    target_model = load_target_model()
    project = load_project("sead_missing_sample_group.yml")

    issues = issue_pairs(target_model, project)

    assert ("MISSING_REQUIRED_ENTITY", "sample_group") in set(issues)
    assert ("UNEXPECTED_PUBLIC_ID", "sample") in set(issues)


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

    issues = issue_pairs(target_model, project)

    assert ("MISSING_REQUIRED_COLUMN", "sample_type") in set(issues)
    assert ("MISSING_REQUIRED_COLUMN", "method") in set(issues)


def test_conformance_validator_reports_known_gaps_for_full_arbodat_project() -> None:
    target_model = load_target_model()
    project = load_real_project("arbodat")

    assert sorted(issue_pairs(target_model, project)) == sorted([
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "site"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
        ("MISSING_REQUIRED_COLUMN", "sample_type"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
        ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
    ])


def test_conformance_validator_current_corpus_issue_families_are_stable() -> None:
    target_model = load_target_model()
    corpus = {
        "sead_canonical_minimal": load_project("sead_canonical_minimal.yml"),
        "sead_arbodat_core": load_project("sead_arbodat_core.yml"),
        "sead_missing_sample_group": load_project("sead_missing_sample_group.yml"),
        "arbodat_full": load_real_project("arbodat"),
    }

    issue_summary = {
        name: Counter(code for code, _entity in issue_pairs(target_model, project))
        for name, project in corpus.items()
    }

    assert issue_summary == {
        "sead_canonical_minimal": Counter(),
        "sead_arbodat_core": Counter({"MISSING_REQUIRED_COLUMN": 3, "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 1}),
        "sead_missing_sample_group": Counter(
            {
                "MISSING_REQUIRED_COLUMN": 4,
                "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 3,
                "MISSING_REQUIRED_ENTITY": 1,
                "UNEXPECTED_PUBLIC_ID": 1,
            }
        ),
        "arbodat_full": Counter({"MISSING_REQUIRED_FOREIGN_KEY_TARGET": 4, "MISSING_REQUIRED_COLUMN": 3}),
    }