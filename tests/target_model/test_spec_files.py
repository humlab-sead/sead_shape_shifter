from pathlib import Path

import yaml

from src.target_model.models import TargetModel
from src.target_model.spec_validator import TargetModelSpecValidator

EXAMPLES_DIR = Path("tests/test_data/examples")
SPECS_DIR = Path("tests/test_data/specs")


def test_sead_v2_spec_loads_and_validates() -> None:
    spec_path: Path = SPECS_DIR / "sead_standard_model.yml"
    target_model = TargetModel.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))

    issues = TargetModelSpecValidator().validate(target_model)

    assert target_model.model.name == "SEAD Clearinghouse Extended"
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


def test_sead_superset_spec_loads_and_validates() -> None:
    spec_path = Path("resources/target_models/sead_superset_model.yml")
    target_model = TargetModel.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))

    issues = TargetModelSpecValidator().validate(target_model)
    analysis_categorical_value = target_model.entities["analysis_categorical_value"]
    analysis_value = target_model.entities["analysis_value"]
    analysis_boolean_value = target_model.entities["analysis_boolean_value"]
    analysis_note = target_model.entities["analysis_note"]
    analysis_identifier = target_model.entities["analysis_identifier"]
    analysis_integer_range = target_model.entities["analysis_integer_range"]
    analysis_integer_value = target_model.entities["analysis_integer_value"]
    analysis_numerical_range = target_model.entities["analysis_numerical_range"]
    analysis_numerical_value = target_model.entities["analysis_numerical_value"]
    analysis_dating_range = target_model.entities["analysis_dating_range"]
    analysis_taxon_count = target_model.entities["analysis_taxon_count"]
    analysis_value_dimension = target_model.entities["analysis_value_dimension"]
    horizon = target_model.entities["horizon"]
    value_class = target_model.entities["value_class"]
    value_qualifier = target_model.entities["value_qualifier"]
    value_qualifier_symbol = target_model.entities["value_qualifier_symbol"]
    value_type = target_model.entities["value_type"]
    value_type_item = target_model.entities["value_type_item"]
    sample_group = target_model.entities["sample_group"]
    sample_group_coordinate = target_model.entities["sample_group_coordinate"]
    sample_group_dimension = target_model.entities["sample_group_dimension"]
    sample_group_note = target_model.entities["sample_group_note"]
    sample_group_reference = target_model.entities["sample_group_reference"]
    sample_group_sampling_context = target_model.entities["sample_group_sampling_context"]
    sample_dimension = target_model.entities["sample_dimension"]
    sample_location_type = target_model.entities["sample_location_type"]
    sample_location = target_model.entities["sample_location"]
    sample_note = target_model.entities["sample_note"]
    sample_horizon = target_model.entities["sample_horizon"]

    assert target_model.model.name == "SEAD Clearinghouse Extended"
    assert len(target_model.entities) == 78
    assert {
        "analysis_value",
        "analysis_boolean_value",
        "analysis_categorical_value",
        "analysis_note",
        "analysis_identifier",
        "analysis_integer_range",
        "analysis_integer_value",
        "analysis_numerical_range",
        "analysis_numerical_value",
        "analysis_dating_range",
        "analysis_taxon_count",
        "analysis_value_dimension",
        "value_class",
        "value_type",
        "value_type_item",
    }.issubset(target_model.entities)
    assert {"sample_horizon", "sample_location", "sample_location_type", "sample_note", "horizon"}.issubset(target_model.entities)
    assert {"value_qualifier", "value_qualifier_symbol"}.issubset(target_model.entities)
    assert {"sample_group_coordinate", "sample_group_dimension", "sample_group_note", "sample_group_reference", "sample_group_sampling_context"}.issubset(
        target_model.entities
    )
    assert analysis_value.target_table == "tbl_analysis_values"
    assert analysis_value.aggregate_parent == "analysis_entity"
    assert analysis_value.columns["value_class_id"].nullable is False
    assert any(foreign_key.entity == "value_class" for foreign_key in analysis_value.foreign_keys)
    assert analysis_boolean_value.target_table == "tbl_analysis_boolean_values"
    assert analysis_boolean_value.aggregate_parent == "analysis_value"
    assert analysis_categorical_value.target_table == "tbl_analysis_categorical_values"
    assert any(foreign_key.entity == "value_type_item" for foreign_key in analysis_categorical_value.foreign_keys)
    assert analysis_note.target_table == "tbl_analysis_notes"
    assert analysis_note.aggregate_parent == "analysis_value"
    assert analysis_identifier.target_table == "tbl_analysis_identifiers"
    assert analysis_identifier.aggregate_parent == "analysis_value"
    assert analysis_integer_range.target_table == "tbl_analysis_integer_ranges"
    assert any(foreign_key.entity == "value_qualifier_symbol" for foreign_key in analysis_integer_range.foreign_keys)
    assert analysis_integer_value.target_table == "tbl_analysis_integer_values"
    assert any(foreign_key.entity == "value_qualifier_symbol" for foreign_key in analysis_integer_value.foreign_keys)
    assert analysis_numerical_range.target_table == "tbl_analysis_numerical_ranges"
    assert analysis_numerical_range.columns["value"].type == "numrange"
    assert any(foreign_key.entity == "value_qualifier_symbol" for foreign_key in analysis_numerical_range.foreign_keys)
    assert analysis_numerical_value.target_table == "tbl_analysis_numerical_values"
    assert any(foreign_key.entity == "value_qualifier_symbol" for foreign_key in analysis_numerical_value.foreign_keys)
    assert analysis_dating_range.target_table == "tbl_analysis_dating_ranges"
    assert any(foreign_key.entity == "value_qualifier_symbol" for foreign_key in analysis_dating_range.foreign_keys)
    assert analysis_taxon_count.target_table == "tbl_analysis_taxon_counts"
    assert any(foreign_key.entity == "taxa_tree_master" for foreign_key in analysis_taxon_count.foreign_keys)
    assert analysis_value_dimension.target_table == "tbl_analysis_value_dimensions"
    assert any(foreign_key.entity == "dimension" for foreign_key in analysis_value_dimension.foreign_keys)
    assert value_class.target_table == "tbl_value_classes"
    assert any(foreign_key.entity == "value_type" for foreign_key in value_class.foreign_keys)
    assert any(foreign_key.entity == "method" for foreign_key in value_class.foreign_keys)
    assert value_qualifier.target_table == "tbl_value_qualifiers"
    assert value_qualifier_symbol.target_table == "tbl_value_qualifier_symbols"
    assert any(foreign_key.entity == "value_qualifier" for foreign_key in value_qualifier_symbol.foreign_keys)
    assert value_type.target_table == "tbl_value_types"
    assert any(foreign_key.entity == "unit" for foreign_key in value_type.foreign_keys)
    assert value_type_item.target_table == "tbl_value_type_items"
    assert any(foreign_key.entity == "value_type" for foreign_key in value_type_item.foreign_keys)
    assert sample_group.target_table == "tbl_sample_groups"
    assert any(foreign_key.entity == "sample_group_sampling_context" for foreign_key in sample_group.foreign_keys)
    assert sample_group_coordinate.target_table == "tbl_sample_group_coordinates"
    assert sample_group_coordinate.public_id == "sample_group_position_id"
    assert sample_group_coordinate.aggregate_parent == "sample_group"
    assert sample_group_dimension.target_table == "tbl_sample_group_dimensions"
    assert sample_group_dimension.aggregate_parent == "sample_group"
    assert any(foreign_key.entity == "value_qualifier" for foreign_key in sample_group_dimension.foreign_keys)
    assert sample_group_note.target_table == "tbl_sample_group_notes"
    assert sample_group_note.aggregate_parent == "sample_group"
    assert sample_group_reference.target_table == "tbl_sample_group_references"
    assert sample_group_reference.aggregate_parent == "sample_group"
    assert sample_group_sampling_context.target_table == "tbl_sample_group_sampling_contexts"
    assert any(foreign_key.entity == "value_qualifier" for foreign_key in sample_dimension.foreign_keys)
    assert sample_location_type.target_table == "tbl_sample_location_types"
    assert sample_location.target_table == "tbl_sample_locations"
    assert sample_location.aggregate_parent == "sample"
    assert sample_note.target_table == "tbl_sample_notes"
    assert sample_note.aggregate_parent == "sample"
    assert horizon.target_table == "tbl_horizons"
    assert any(foreign_key.entity == "method" for foreign_key in horizon.foreign_keys)
    assert sample_horizon.target_table == "tbl_sample_horizons"
    assert sample_horizon.aggregate_parent == "sample"
    assert any(foreign_key.entity == "horizon" for foreign_key in sample_horizon.foreign_keys)
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
