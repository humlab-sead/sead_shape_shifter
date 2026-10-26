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


@pytest.mark.parametrize(
    ("entities", "expected_code"),
    [
        (
            {
                "location": {"foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "missing"}}]},
                "location_type": {"public_id": "location_type_id"},
            },
            "UNKNOWN_CONDITIONAL_FOREIGN_KEY_SOURCE",
        ),
        (
            {
                "location": {"foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "site"}}]},
                "site": {},
                "location_type": {"public_id": "location_type_id"},
            },
            "CONDITIONAL_FOREIGN_KEY_SOURCE_MISMATCH",
        ),
    ],
)
def test_validator_rejects_unknown_or_non_owning_conditional_source(entities: dict, expected_code: str) -> None:
    target_model = TargetModel.model_validate({"model": {"name": "SEAD Clearinghouse", "version": "2.0.0"}, "entities": entities})

    issues = TargetModelSpecValidator().validate(target_model)

    assert expected_code in {issue.code for issue in issues}


def test_validator_rejects_conditional_fk_without_target_public_id() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "location": {"foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}]},
                "location_type": {},
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [issue.code for issue in issues] == ["CONDITIONAL_FOREIGN_KEY_TARGET_MISSING_PUBLIC_ID"]


@pytest.mark.parametrize("required", [True, False])
def test_validator_rejects_explicit_required_with_required_when(required: bool) -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "location": {
                    "foreign_keys": [{"entity": "location_type", "required": required, "required_when": {"has_new_rows": "location"}}]
                },
                "location_type": {"public_id": "location_type_id"},
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)
    round_tripped = TargetModel.model_validate(target_model.model_dump(mode="json"))
    round_trip_issues = TargetModelSpecValidator().validate(round_tripped)

    assert [issue.code for issue in issues] == ["CONFLICTING_FOREIGN_KEY_REQUIREMENTS"]
    assert [issue.code for issue in round_trip_issues] == ["CONFLICTING_FOREIGN_KEY_REQUIREMENTS"]


def test_validator_accepts_conditional_fk_after_json_round_trip() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "location": {"foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}]},
                "location_type": {"public_id": "location_type_id"},
            },
        }
    )

    round_tripped = TargetModel.model_validate(target_model.model_dump(mode="json"))
    issues = TargetModelSpecValidator().validate(round_tripped)

    assert issues == []


def test_validator_rejects_conditional_bridge_foreign_key() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "location": {
                    "foreign_keys": [
                        {"entity": "location_type", "via": "location_type_bridge", "required_when": {"has_new_rows": "location"}}
                    ]
                },
                "location_type": {"public_id": "location_type_id"},
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [issue.code for issue in issues] == ["CONDITIONAL_FOREIGN_KEY_VIA_UNSUPPORTED"]


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


def test_validator_reports_unknown_unique_set_columns() -> None:
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
                    "unique_sets": [["site_name", "missing_unique"]],
                }
            },
            "naming": {"public_id_suffix": "_id"},
            "constraints": [],
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [issue.code for issue in issues] == ["UNKNOWN_UNIQUE_SET_COLUMN"]


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


def test_validator_requires_database_sequences_to_use_explicit_non_tracked_identity() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "implicitly_tracked": {
                    "role": "fact",
                    "public_id": "implicitly_tracked_id",
                    "public_id_generation": "database_sequence",
                },
                "tracked_entity": {
                    "role": "fact",
                    "public_id": "tracked_entity_id",
                    "public_id_generation": "database_sequence",
                    "identity_tracking": "tracked",
                    "reconciliation": "allocate",
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("DATABASE_SEQUENCE_REQUIRES_EXPLICIT_NON_TRACKED_IDENTITY", "implicitly_tracked"),
        ("DATABASE_SEQUENCE_REQUIRES_EXPLICIT_NON_TRACKED_IDENTITY", "tracked_entity"),
    ]


def test_validator_requires_sims_sequence_sync_to_have_a_tracked_target_id() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "valid": {
                    "role": "fact",
                    "identity_tracking": "tracked",
                    "reconciliation": "allocate",
                    "target_table": "tbl_valid",
                    "public_id": "valid_id",
                    "synchronize_sequence_after_insert": True,
                },
                "missing_target": {
                    "role": "fact",
                    "identity_tracking": "tracked",
                    "reconciliation": "allocate",
                    "public_id": "missing_target_id",
                    "synchronize_sequence_after_insert": True,
                },
                "untracked": {
                    "role": "lookup",
                    "identity_tracking": "reconciled",
                    "reconciliation": "reconcile-exact",
                    "target_table": "tbl_untracked",
                    "public_id": "untracked_id",
                    "synchronize_sequence_after_insert": True,
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("SEQUENCE_SYNC_REQUIRES_TARGET_ID", "missing_target"),
        ("SEQUENCE_SYNC_REQUIRES_TRACKED_IDENTITY", "untracked"),
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


def test_validator_reports_each_aggregate_cycle_once() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "alpha": {
                    "role": "fact",
                    "public_id": "alpha_id",
                    "aggregate_parent": "beta",
                    "foreign_keys": [{"entity": "beta", "required": True}],
                },
                "beta": {
                    "role": "fact",
                    "public_id": "beta_id",
                    "aggregate_parent": "alpha",
                    "foreign_keys": [{"entity": "alpha", "required": True}],
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [("AGGREGATE_PARENT_CYCLE", "alpha")]
    assert issues[0].message == "Aggregate parents form a cycle: alpha -> beta -> alpha"


def test_validator_reports_three_entity_aggregate_cycle_once() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "alpha": {
                    "role": "fact",
                    "public_id": "alpha_id",
                    "aggregate_parent": "beta",
                    "foreign_keys": [{"entity": "beta", "required": True}],
                },
                "beta": {
                    "role": "fact",
                    "public_id": "beta_id",
                    "aggregate_parent": "gamma",
                    "foreign_keys": [{"entity": "gamma", "required": True}],
                },
                "gamma": {
                    "role": "fact",
                    "public_id": "gamma_id",
                    "aggregate_parent": "alpha",
                    "foreign_keys": [{"entity": "alpha", "required": True}],
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [("AGGREGATE_PARENT_CYCLE", "alpha")]
    assert issues[0].message == "Aggregate parents form a cycle: alpha -> beta -> gamma -> alpha"


def test_validator_reports_derived_aggregate_root_for_each_child() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "derived_root": {
                    "role": "bridge",
                    "public_id": "derived_root_id",
                },
                "child": {
                    "role": "fact",
                    "public_id": "child_id",
                    "aggregate_parent": "derived_root",
                    "foreign_keys": [{"entity": "derived_root", "required": True}],
                },
                "grandchild": {
                    "role": "fact",
                    "public_id": "grandchild_id",
                    "aggregate_parent": "child",
                    "foreign_keys": [{"entity": "child", "required": True}],
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("INVALID_AGGREGATE_ROOT_IDENTITY", "child"),
        ("INVALID_AGGREGATE_ROOT_IDENTITY", "grandchild"),
    ]


def test_validator_reports_missing_aggregate_root_public_id() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "root": {"role": "fact"},
                "child": {
                    "role": "fact",
                    "public_id": "child_id",
                    "aggregate_parent": "root",
                    "foreign_keys": [{"entity": "root", "required": True}],
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("AGGREGATE_ROOT_MISSING_PUBLIC_ID", "child"),
    ]


def test_validator_does_not_duplicate_broken_aggregate_links() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "child": {
                    "role": "fact",
                    "public_id": "child_id",
                    "aggregate_parent": "missing_parent",
                },
                "grandchild": {
                    "role": "fact",
                    "public_id": "grandchild_id",
                    "aggregate_parent": "child",
                    "foreign_keys": [{"entity": "child", "required": True}],
                },
            },
        }
    )

    issues = TargetModelSpecValidator().validate(target_model)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("UNKNOWN_AGGREGATE_PARENT", "child"),
    ]
