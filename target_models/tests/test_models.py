from target_model_spec.models import TargetModel


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