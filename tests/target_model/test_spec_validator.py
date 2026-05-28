import pytest
from pydantic import ValidationError

from src.target_model.models import TargetModel
from src.target_model.spec_validator import TargetModelSpecValidator


@pytest.mark.parametrize(
    ("raw", "loc"),
    [
        (
            {
                "model": {
                    "name": "SEAD Clearinghouse",
                    "version": "2.0.0",
                    "unexpected": True,
                },
                "entities": {},
            },
            ("model", "unexpected"),
        ),
        (
            {
                "model": {
                    "name": "SEAD Clearinghouse",
                    "version": "2.0.0",
                },
                "entities": {
                    "site": {
                        "public_id": "site_id",
                        "unexpected": True,
                    }
                },
            },
            ("entities", "site", "unexpected"),
        ),
        (
            {
                "model": {
                    "name": "SEAD Clearinghouse",
                    "version": "2.0.0",
                },
                "entities": {
                    "location": {
                        "public_id": "location_id",
                    },
                    "site": {
                        "public_id": "site_id",
                        "foreign_keys": [
                            {
                                "entity": "location",
                                "unexpected": True,
                            }
                        ],
                    },
                },
            },
            ("entities", "site", "foreign_keys", 0, "unexpected"),
        ),
        (
            {
                "model": {
                    "name": "SEAD Clearinghouse",
                    "version": "2.0.0",
                },
                "entities": {
                    "site": {
                        "public_id": "site_id",
                        "columns": {
                            "site_name": {
                                "required": True,
                                "unexpected": True,
                            }
                        },
                    }
                },
            },
            ("entities", "site", "columns", "site_name", "unexpected"),
        ),
    ],
)
def test_target_model_rejects_unknown_keys(raw: dict, loc: tuple[object, ...]) -> None:
    with pytest.raises(ValidationError) as exc_info:
        TargetModel.model_validate(raw)

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"
    assert exc_info.value.errors()[0]["loc"] == loc


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
                    "columns": {"site_name": {"required": True}},
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


def test_validator_reports_aggregate_parent_semantic_issues() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "sample": {
                    "role": "fact",
                    "public_id": "sample_id",
                },
                "sample_description": {
                    "role": "fact",
                    "public_id": "sample_description_id",
                    "aggregate_parent": "sample",
                    "identity_tracking": "tracked",
                    "foreign_keys": [],
                },
                "sample_note": {
                    "role": "fact",
                    "public_id": "sample_note_id",
                    "identity_tracking": "child",
                },
                "orphan_child": {
                    "role": "fact",
                    "public_id": "orphan_child_id",
                    "aggregate_parent": "missing_parent",
                },
                "recursive_child": {
                    "role": "fact",
                    "public_id": "recursive_child_id",
                    "aggregate_parent": "recursive_child",
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("AGGREGATE_PARENT_CONFLICTS_WITH_IDENTITY_TRACKING", "sample_description"),
        ("MISSING_AGGREGATE_PARENT_FOREIGN_KEY", "sample_description"),
        ("CHILD_IDENTITY_MISSING_AGGREGATE_PARENT", "sample_note"),
        ("UNKNOWN_AGGREGATE_PARENT", "orphan_child"),
        ("SELF_REFERENTIAL_AGGREGATE_PARENT", "recursive_child"),
    ]


def test_validator_reports_invalid_identity_reconciliation_combinations() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "tracked_entity": {
                    "role": "fact",
                    "public_id": "tracked_entity_id",
                    "reconciliation": "lookup-only",
                },
                "derived_entity": {
                    "role": "bridge",
                    "public_id": "derived_entity_id",
                    "reconciliation": "allocate",
                },
                "ambiguous_lookup": {
                    "role": "fact",
                    "public_id": "ambiguous_lookup_id",
                    "identity_tracking": "reconciled",
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("INVALID_IDENTITY_RECONCILIATION_COMBINATION", "tracked_entity"),
        ("INVALID_IDENTITY_RECONCILIATION_COMBINATION", "derived_entity"),
        ("INVALID_IDENTITY_RECONCILIATION_COMBINATION", "ambiguous_lookup"),
    ]


def test_validator_reports_invalid_allowed_values_usage() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {
                "name": "SEAD Clearinghouse",
                "version": "2.0.0",
            },
            "entities": {
                "sample": {
                    "public_id": "sample_id",
                    "columns": {
                        "sample_kind": {"type": "string", "allowed_values": ["core", "control"]},
                        "sample_status": {"type": "enum"},
                    },
                }
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.field) for issue in issues] == [
        ("ALLOWED_VALUES_REQUIRE_ENUM_TYPE", "sample_kind"),
        ("ENUM_MISSING_ALLOWED_VALUES", "sample_status"),
    ]
