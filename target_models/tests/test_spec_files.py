from pathlib import Path

import yaml

from src.target_model.models import TargetModel
from src.target_model.spec_validator import TargetModelSpecValidator


def test_sead_v2_spec_loads_and_validates() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "specs" / "sead_v2.yml"
    target_model = TargetModel.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))

    issues = TargetModelSpecValidator().validate(target_model)

    assert target_model.model.name == "SEAD Clearinghouse"
    assert "sample_group" in target_model.entities
    assert {"abundance", "abundance_element", "abundance_element_group", "abundance_modification", "abundance_property"}.issubset(
        target_model.entities
    )
    assert {"taxa_tree_master", "taxa_common_names"}.issubset(target_model.entities)
    assert {"relative_ages", "relative_dating", "geochronology", "dating_lab"}.issubset(target_model.entities)
    assert {"method_group", "contact", "contact_type"}.issubset(target_model.entities)
    assert {"project", "feature_type", "feature", "sample_description_type", "sample_description"}.issubset(
        target_model.entities
    )
    assert {"site_type_group", "site_type", "modification_type"}.issubset(target_model.entities)
    assert {"citation", "master_dataset", "dataset_contact", "sample_feature"}.issubset(target_model.entities)
    assert issues == []