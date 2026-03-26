from target_model_spec.models import TargetModel
from target_model_spec.validator import TargetModelSpecValidator


def test_validator_reports_unknown_foreign_key_entity() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "site": {
                    "public_id": "site_id",
                    "foreign_keys": [{"entity": "location", "required": True}],
                }
            },
            "naming": {"public_id_suffix": "_id"},
            "constraints": [],
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert len(issues) == 1
    assert issues[0].code == "UNKNOWN_FOREIGN_KEY_ENTITY"


def test_validator_reports_invalid_public_id_suffix() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "site": {
                    "public_id": "site_identifier",
                }
            },
            "naming": {"public_id_suffix": "_id"},
            "constraints": [],
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert len(issues) == 1
    assert issues[0].code == "INVALID_PUBLIC_ID_SUFFIX"


def test_validator_reports_unknown_identity_and_unique_set_columns() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "site": {
                    "public_id": "site_id",
                    "columns": [{"name": "site_name", "required": True}],
                    "identity_columns": ["missing_identity"],
                    "unique_sets": [["site_name", "missing_unique"]],
                }
            },
            "naming": {"public_id_suffix": "_id"},
            "constraints": [],
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [issue.code for issue in issues] == ["UNKNOWN_IDENTITY_COLUMN", "UNKNOWN_UNIQUE_SET_COLUMN"]