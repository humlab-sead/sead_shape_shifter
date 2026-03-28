from src.target_model.models import TargetModel


def test_target_model_parses_minimal_payload() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {},
            "constraints": [],
        }
    )

    assert target_model.model.name == "SEAD Clearinghouse"
    assert target_model.entities == {}
    assert target_model.constraints == []


def test_target_model_parses_richer_entity_payload() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "location": {
                    "role": "lookup",
                    "required": True,
                    "domains": ["core", "spatial"],
                    "target_table": "tbl_locations",
                    "public_id": "location_id",
                    "identity_columns": ["location_type_id", "location_name"],
                    "columns": {
                        "location_name": {"required": True, "type": "string", "nullable": False},
                        "location_type_id": {"required": True, "type": "integer", "nullable": False},
                    },
                    "unique_sets": [["location_type_id", "location_name"]],
                    "foreign_keys": [{"entity": "location_type", "required": True}],
                },
                "location_type": {
                    "role": "classifier",
                    "columns": {"location_type": {"required": True}},
                },
            },
            "naming": {"public_id_suffix": "_id"},
            "constraints": [{"type": "no_circular_dependencies"}],
        }
    )

    location = target_model.entities["location"]
    assert location.domains == ["core", "spatial"]
    assert location.identity_columns == ["location_type_id", "location_name"]
    assert list(location.columns) == ["location_name", "location_type_id"]
    assert location.columns["location_name"].required is True
    assert location.unique_sets == [["location_type_id", "location_name"]]