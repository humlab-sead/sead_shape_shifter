from pathlib import Path

import yaml

from src.target_model.models import TargetModel
from src.target_model.template_generator import generate_project_template, render_project_template_yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT_DIR / "specs" / "sead_v2.yml"


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")))


def test_generate_project_template_for_dating_domain_includes_required_dependency_closure() -> None:
    target_model = load_target_model()

    template = generate_project_template(target_model, domains=["dating"])

    generated_entities = template["entities"]
    assert {"relative_ages", "relative_dating", "geochronology", "dating_lab"}.issubset(generated_entities)
    assert {"analysis_entity", "sample", "sample_group", "sample_type", "site", "location", "location_type", "dataset", "method"}.issubset(
        generated_entities
    )
    assert "abundance" not in generated_entities


def test_generate_project_template_renders_valid_yaml_for_explicit_entity_selection() -> None:
    target_model = load_target_model()

    rendered = render_project_template_yaml(target_model, entity_names=["contact_type"], project_name="generated:test-contact-type")
    parsed = yaml.safe_load(rendered)

    assert parsed["metadata"]["name"] == "generated:test-contact-type"
    assert set(parsed["entities"]) == {"contact_type"}
    assert parsed["entities"]["contact_type"]["public_id"] == "contact_type_id"
    assert parsed["entities"]["contact_type"]["type"] == "TODO"


def test_generate_project_template_raises_for_unknown_entity() -> None:
    target_model = load_target_model()

    try:
        generate_project_template(target_model, entity_names=["does_not_exist"])
    except ValueError as exc:
        assert "Unknown entities requested" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown entity selection")