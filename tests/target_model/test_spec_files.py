from pathlib import Path

import yaml

from src.target_model.models import TargetModel
from src.target_model.spec_validator import TargetModelSpecValidator

EXAMPLES_DIR = Path("tests/test_data/examples")
SPECS_DIR = Path("tests/test_data/specs")


def test_sead_v2_spec_loads_and_validates() -> None:
    spec_path: Path = SPECS_DIR / "sead_v2.yml"
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
    assert {"project", "feature_type", "feature", "sample_description_type", "sample_description"}.issubset(target_model.entities)
    assert {"site_type_group", "site_type", "modification_type"}.issubset(target_model.entities)
    assert {"citation", "master_dataset", "dataset_contact", "sample_feature"}.issubset(target_model.entities)
    assert issues == []


def test_non_sead_target_model_expresses_cleanly() -> None:
    """Acceptance criterion #5: at least one non-SEAD model can be expressed without schema changes.

    Uses a minimal fictional museum specimen database to confirm the format is system-agnostic.
    """
    raw = {
        "model": {
            "name": "Museum Specimen Database",
            "version": "1.0.0",
            "description": "Fictional specimen catalogue for format generality test",
        },
        "entities": {
            "collection": {
                "role": "lookup",
                "required": True,
                "description": "Top-level collection.",
                "domains": ["core"],
                "target_table": "tbl_collections",
                "public_id": "collection_id",
                "identity_columns": ["collection_name"],
                "columns": {
                    "collection_name": {"required": True, "type": "string", "nullable": False},
                    "institution_code": {"required": True, "type": "string", "nullable": False},
                },
                "unique_sets": [["collection_name"]],
            },
            "specimen": {
                "role": "fact",
                "required": True,
                "description": "A catalogued specimen.",
                "domains": ["core"],
                "target_table": "tbl_specimens",
                "public_id": "specimen_id",
                "identity_columns": ["catalogue_number"],
                "columns": {
                    "catalogue_number": {"required": True, "type": "string", "nullable": False},
                    "taxon_id": {"required": True, "type": "integer", "nullable": False},
                    "collected_date": {"type": "date", "nullable": True},
                },
                "unique_sets": [["catalogue_number"]],
                "foreign_keys": [{"entity": "collection", "required": True}],
            },
            "taxon": {
                "role": "classifier",
                "required": False,
                "description": "Taxonomic classification.",
                "domains": ["taxonomy"],
                "target_table": "tbl_taxa",
                "public_id": "taxon_id",
                "identity_columns": ["scientific_name"],
                "columns": {
                    "scientific_name": {"required": True, "type": "string", "nullable": False},
                    "common_name": {"type": "string", "nullable": True},
                },
                "unique_sets": [["scientific_name"]],
            },
        },
        "naming": {"public_id_suffix": "_id"},
        "constraints": [{"type": "no_circular_dependencies"}],
    }

    target_model = TargetModel.model_validate(raw)
    issues = TargetModelSpecValidator().validate(target_model)

    assert target_model.model.name == "Museum Specimen Database"
    assert set(target_model.entities) == {"collection", "specimen", "taxon"}
    assert target_model.entities["specimen"].role == "fact"
    assert target_model.entities["collection"].public_id == "collection_id"
    assert target_model.naming is not None and target_model.naming.public_id_suffix == "_id"
    assert issues == [], f"Unexpected spec issues: {issues}"
