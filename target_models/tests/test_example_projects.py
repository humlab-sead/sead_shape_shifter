from pathlib import Path

import yaml


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def load_example_project(name: str) -> dict:
    example_path = EXAMPLES_DIR / name
    return yaml.safe_load(example_path.read_text(encoding="utf-8"))


def test_all_example_projects_load_as_shapeshifter_projects() -> None:
    for example_path in sorted(EXAMPLES_DIR.glob("*.yml")):
        project = yaml.safe_load(example_path.read_text(encoding="utf-8"))

        assert project["metadata"]["type"] == "shapeshifter-project"
        assert isinstance(project["entities"], dict)
        assert project["entities"]


def test_real_example_contains_iteration_one_sead_core_entities() -> None:
    project = load_example_project("sead_arbodat_core.yml")

    assert project["metadata"]["name"] == "arbodat:sead-core"
    assert set(project["entities"]) == {
        "analysis_entity",
        "dataset",
        "location",
        "location_type",
        "method",
        "sample",
        "sample_group",
        "sample_type",
        "site",
    }
    assert project["entities"]["sample"]["public_id"] == "physical_sample_id"


def test_canonical_example_is_non_arbodat_positive_control() -> None:
    project = load_example_project("sead_canonical_minimal.yml")

    assert project["metadata"]["name"] == "example:sead-canonical-minimal"
    assert set(project["entities"]) == {
        "analysis_entity",
        "dataset",
        "location",
        "location_type",
        "method",
        "sample",
        "sample_group",
        "sample_type",
        "site",
    }
    assert project["entities"]["method"]["columns"] == ["method_name", "description", "method_group_id"]


def test_broken_example_preserves_intended_conformance_gaps() -> None:
    project = load_example_project("sead_missing_sample_group.yml")

    assert project["metadata"]["name"] == "arbodat:sead-core-missing-sample-group"
    assert "sample_group" not in project["entities"]
    assert project["entities"]["sample"]["public_id"] == "sample_id"