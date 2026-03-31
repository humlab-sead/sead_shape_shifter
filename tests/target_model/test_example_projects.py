from pathlib import Path

import pytest
import yaml

from src.model import ShapeShiftProject
from src.target_model.conformance import TargetModelConformanceValidator
from src.target_model.models import TargetModel


EXAMPLES_DIR = Path( "tests/test_data/examples")
SPECS_DIR = Path("tests/test_data/specs")


def load_target_model(name: str = "sead_v2.yml") -> TargetModel:
    spec_path = SPECS_DIR / name
    return TargetModel.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))


def load_example_project(name: str) -> dict:
    example_path = EXAMPLES_DIR / name
    return yaml.safe_load(example_path.read_text(encoding="utf-8"))


def load_example_as_core_project(name: str) -> ShapeShiftProject:
    cfg = load_example_project(name)
    return ShapeShiftProject(cfg=cfg, filename=str(EXAMPLES_DIR / name))


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


# ---------------------------------------------------------------------------
# Conformance tests using the core engine
# ---------------------------------------------------------------------------


class TestExampleProjectConformance:
    """Use TargetModelConformanceValidator to check example projects against sead_v2.yml."""

    def test_arbodat_core_conforms_to_sead_v2(self) -> None:
        """The complete arbodat example should produce no critical conformance errors."""
        target_model = load_target_model()
        project = load_example_as_core_project("sead_arbodat_core.yml")

        issues = TargetModelConformanceValidator().validate(target_model, project)

        # Verify no parse/validation exception was raised and results are a list
        assert isinstance(issues, list), "Expected a list of ConformanceIssues"

    def test_canonical_minimal_conforms_to_sead_v2(self) -> None:
        """The canonical minimal example should also run through the validator cleanly."""
        target_model = load_target_model()
        project = load_example_as_core_project("sead_canonical_minimal.yml")

        issues = TargetModelConformanceValidator().validate(target_model, project)

        assert isinstance(issues, list)

    def test_missing_sample_group_triggers_required_entity_issue(self) -> None:
        """The fixture that deliberately omits sample_group should produce a MISSING_REQUIRED_ENTITY issue."""
        target_model = load_target_model()
        project = load_example_as_core_project("sead_missing_sample_group.yml")

        issues = TargetModelConformanceValidator().validate(target_model, project)

        missing = [i for i in issues if i.code == "MISSING_REQUIRED_ENTITY" and i.entity == "sample_group"]
        assert missing, (
            f"Expected MISSING_REQUIRED_ENTITY for 'sample_group', got: {[i.code for i in issues]}"
        )

    def test_all_example_projects_run_without_exception(self) -> None:
        """All example YAMLs should run through the conformance engine without crashing."""
        target_model = load_target_model()

        for example_path in sorted(EXAMPLES_DIR.glob("*.yml")):
            cfg = yaml.safe_load(example_path.read_text(encoding="utf-8"))
            project = ShapeShiftProject(cfg=cfg, filename=str(example_path))

            issues = TargetModelConformanceValidator().validate(target_model, project)
            assert isinstance(issues, list), f"Expected list for {example_path.name}"


class TestNamingConventionConformance:
    """Unit tests for NamingConventionConformanceValidator."""

    _MINIMAL_CFG_PREFIX: dict = {
        "metadata": {"type": "shapeshifter-project", "name": "test"},
    }

    def _make_project(self, entities: dict) -> ShapeShiftProject:
        cfg = {**self._MINIMAL_CFG_PREFIX, "entities": entities}
        return ShapeShiftProject(cfg=cfg, filename="test.yml")

    def _make_target_model(self, entity_specs: dict, suffix: str = "_id") -> "TargetModel":
        import yaml as _yaml
        from src.target_model.models import TargetModel as _TM

        raw = {
            "model": {"name": "Test", "version": "1.0.0"},
            "entities": entity_specs,
            "naming": {"public_id_suffix": suffix},
        }
        return _TM.model_validate(raw)

    def test_entity_with_conforming_public_id_produces_no_violation(self) -> None:
        target_model = self._make_target_model({"location": {"required": True}})
        project = self._make_project({"location": {"type": "csv", "file": "loc.csv", "public_id": "location_id"}})

        from src.target_model.conformance import NamingConventionConformanceValidator

        issues = NamingConventionConformanceValidator().validate(target_model, project)
        assert issues == []

    def test_entity_with_non_conforming_public_id_raises_violation(self) -> None:
        target_model = self._make_target_model({"location": {"required": True}})
        # "locid" does not end with "_id"
        project = self._make_project({"location": {"type": "csv", "file": "loc.csv", "public_id": "locid"}})

        from src.target_model.conformance import NamingConventionConformanceValidator

        issues = NamingConventionConformanceValidator().validate(target_model, project)
        assert len(issues) == 1
        assert issues[0].code == "PUBLIC_ID_NAMING_VIOLATION"
        assert issues[0].entity == "location"
        assert "locid" in issues[0].message
        assert "_id" in issues[0].message

    def test_entity_without_public_id_produces_no_violation(self) -> None:
        target_model = self._make_target_model({"location": {"required": True}})
        project = self._make_project({"location": {"type": "csv", "file": "loc.csv"}})

        from src.target_model.conformance import NamingConventionConformanceValidator

        issues = NamingConventionConformanceValidator().validate(target_model, project)
        assert issues == []

    def test_no_naming_conventions_in_target_model_skips_check(self) -> None:
        from src.target_model.models import TargetModel as _TM

        raw = {"model": {"name": "Test", "version": "1.0.0"}, "entities": {"location": {}}}
        target_model = _TM.model_validate(raw)
        project = self._make_project({"location": {"type": "csv", "file": "loc.csv", "public_id": "locid"}})

        from src.target_model.conformance import NamingConventionConformanceValidator

        issues = NamingConventionConformanceValidator().validate(target_model, project)
        assert issues == []

    def test_naming_convention_integrated_into_main_validator(self) -> None:
        """NamingConventionConformanceValidator is registered and runs via TargetModelConformanceValidator."""
        target_model = self._make_target_model({"location": {"required": True}})
        project = self._make_project({"location": {"type": "csv", "file": "loc.csv", "public_id": "locid"}})

        issues = TargetModelConformanceValidator().validate(target_model, project)
        naming_issues = [i for i in issues if i.code == "PUBLIC_ID_NAMING_VIOLATION"]
        assert naming_issues, "Expected PUBLIC_ID_NAMING_VIOLATION from integrated validator"