"""Tests for resolving a linking warning to one saved foreign key."""

from typing import Any

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject
from src.table_store import TableStore
from src.transforms.link import ForeignKeyLinker
from src.transforms.link_resolution import SUPPORTED_JOIN_TYPES, resolve_integrity_issue, resolve_row_count_issue

DEFAULT_FK: dict[str, Any] = {
    "entity": "customers",
    "local_keys": ["customer_id"],
    "remote_keys": ["id"],
    "how": "inner",
    "constraints": {"allow_row_decrease": True},
}


def build_project(*, foreign_keys: list[dict[str, Any]] | None = None) -> ShapeShiftProject:
    """Build a project whose local entity holds the given foreign keys in list order."""
    keys: list[dict[str, Any]] = foreign_keys if foreign_keys is not None else [dict(DEFAULT_FK)]
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "public_id": "order_public_id",
                "columns": ["order_id", "order_public_id", "customer_id", "customer_code"],
                "foreign_keys": keys,
            },
            "customers": {
                "columns": ["id", "code"],
                "public_id": "customer_public_id",
            },
        }
    }
    return ShapeShiftProject(cfg=cfg)


def saved_fk(project: ShapeShiftProject, index: int = 0) -> ForeignKeyConfig:
    """Return one saved foreign key of the test project."""
    return project.get_table("orders").foreign_keys[index]


def metadata_for(project: ShapeShiftProject, index: int = 0, link_pass: str = "initial") -> dict[str, Any]:
    """Build warning metadata that matches the saved foreign key at the given index."""
    fk: ForeignKeyConfig = saved_fk(project, index)
    return {
        "row_count_before": 3,
        "row_count_after": 2,
        "join_type": fk.how,
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
        "link_pass": link_pass,
    }


def resolve(project: ShapeShiftProject, metadata: dict[str, Any], **kwargs: Any):
    """Resolve a row-count warning for the orders entity."""
    return resolve_row_count_issue(
        project,
        issue_type=kwargs.pop("issue_type", "row_count_mismatch"),
        local_entity=kwargs.pop("local_entity", "orders"),
        metadata=metadata,
    )


def test_inner_join_resolves_to_its_saved_foreign_key():
    """A supported inner link resolves to the saved entry and copies the linking pass."""
    project = build_project()

    resolution = resolve(project, metadata_for(project, link_pass="deferred_retry"))

    assert resolution.status == "resolved"
    assert resolution.is_eligible is True
    assert resolution.fk_index == 0
    assert resolution.fk is saved_fk(project, 0)
    assert resolution.link_pass == "deferred_retry"


def test_left_join_resolves_to_its_saved_foreign_key():
    """A supported left link resolves like an inner link."""
    project = build_project(foreign_keys=[{"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"], "how": "left"}])

    resolution = resolve(project, metadata_for(project))

    assert resolution.status == "resolved"
    assert resolution.fk is saved_fk(project, 0)


def test_same_entity_pair_with_different_keys_resolves_to_its_own_index():
    """Two links between the same entities resolve by their own index."""
    project = build_project(
        foreign_keys=[
            {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"]},
            {"entity": "customers", "local_keys": ["customer_code"], "remote_keys": ["code"]},
        ]
    )

    first = resolve(project, metadata_for(project, 0))
    second = resolve(project, metadata_for(project, 1))

    assert (first.status, first.fk_index) == ("resolved", 0)
    assert (second.status, second.fk_index) == ("resolved", 1)
    assert first.fk is saved_fk(project, 0)
    assert second.fk is saved_fk(project, 1)


def test_identical_saved_entries_each_resolve_to_their_own_index():
    """Two identical saved entries are interchangeable for counts, so neither is rejected."""
    duplicate: dict[str, Any] = {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"]}
    project = build_project(foreign_keys=[dict(duplicate), dict(duplicate)])

    first = resolve(project, metadata_for(project, 0))
    second = resolve(project, metadata_for(project, 1))

    assert (first.status, first.fk_index) == ("resolved", 0)
    assert (second.status, second.fk_index) == ("resolved", 1)


@pytest.mark.parametrize(
    "metadata",
    [
        pytest.param({"fk_signature": "abc"}, id="missing-index"),
        pytest.param({"fk_index": None, "fk_signature": "abc"}, id="none-index"),
        pytest.param({"fk_index": True, "fk_signature": "abc"}, id="bool-index"),
        pytest.param({"fk_index": "0", "fk_signature": "abc"}, id="string-index"),
        pytest.param({"fk_index": 0}, id="missing-signature"),
        pytest.param({"fk_index": 0, "fk_signature": None}, id="none-signature"),
    ],
)
def test_unusable_identity_metadata_reports_missing_metadata(metadata: dict[str, Any]):
    """Metadata without a usable index and signature offers no action."""
    project = build_project()

    resolution = resolve(project, metadata)

    assert resolution.status == "missing_metadata"
    assert resolution.is_eligible is False
    assert resolution.fk is None


@pytest.mark.parametrize("fk_index", [1, 5, -1])
def test_index_outside_the_saved_list_reports_out_of_range(fk_index: int):
    """An index that names no saved entry offers no action."""
    project = build_project()
    metadata: dict[str, Any] = {"fk_index": fk_index, "fk_signature": saved_fk(project).identity_signature}

    resolution = resolve(project, metadata)

    assert resolution.status == "index_out_of_range"
    assert resolution.fk_index == fk_index


@pytest.mark.parametrize(
    "edited",
    [
        pytest.param({"remote_keys": ["code"]}, id="changed-remote-key"),
        pytest.param({"how": "left"}, id="changed-join-type"),
        pytest.param({"constraints": {"allow_row_decrease": False}}, id="changed-constraint"),
        pytest.param({"defer_dependency": True}, id="changed-defer-flag"),
    ],
)
def test_edited_saved_entry_reports_signature_mismatch(edited: dict[str, Any]):
    """A saved entry edited after the warning was recorded no longer matches."""
    metadata: dict[str, Any] = metadata_for(build_project())
    project = build_project(foreign_keys=[{**DEFAULT_FK, **edited}])

    resolution = resolve(project, metadata)

    assert resolution.status == "signature_mismatch"
    assert resolution.fk_index == 0


def test_inserted_saved_entry_shifts_the_index_to_a_signature_mismatch():
    """A new entry before the target shifts positions instead of matching the wrong link."""
    target_fk: dict[str, Any] = {**DEFAULT_FK, "local_keys": ["customer_code"], "remote_keys": ["code"]}
    metadata: dict[str, Any] = metadata_for(build_project(foreign_keys=[dict(DEFAULT_FK), target_fk]), 1)
    project = build_project(
        foreign_keys=[
            {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["code"]},
            dict(DEFAULT_FK),
            target_fk,
        ]
    )

    resolution = resolve(project, metadata)

    assert resolution.status == "signature_mismatch"
    assert resolution.fk_index == 1


@pytest.mark.parametrize("join_type", ["right", "outer", "cross"])
def test_unsupported_join_types_offer_no_action(join_type: str):
    """Right, outer, and cross joins have no troubleshooting action."""
    project = build_project(foreign_keys=[{"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"], "how": join_type}])

    resolution = resolve(project, metadata_for(project))

    assert resolution.status == "unsupported_join"
    assert resolution.is_eligible is False


def test_supported_join_types_are_inner_and_left():
    """Only inner and left joins are supported."""
    assert SUPPORTED_JOIN_TYPES == ("inner", "left")


def test_other_issue_types_are_not_row_count_issues():
    """Column-count warnings are outside the troubleshooting scope."""
    project = build_project()

    resolution = resolve(project, metadata_for(project), issue_type="column_count_mismatch")

    assert resolution.status == "not_row_count_issue"


def test_unknown_entity_reports_entity_not_found():
    """An entity missing from the project offers no action."""
    project = build_project()

    resolution = resolve(project, metadata_for(project), local_entity="missing_entity")

    assert resolution.status == "entity_not_found"
    assert resolution.entity_name == "missing_entity"


def test_linker_warnings_resolve_to_the_foreign_key_that_raised_them():
    """Warnings raised by a real linker resolve to their own saved entry."""
    project = ShapeShiftProject(
        cfg={
            "entities": {
                "local": {
                    "columns": ["remote_code", "other_code"],
                    "keys": ["remote_code"],
                    "foreign_keys": [
                        {
                            "entity": "remote",
                            "local_keys": ["remote_code"],
                            "remote_keys": ["remote_code"],
                            "how": "inner",
                            "constraints": {"allow_row_decrease": True},
                        },
                        {
                            "entity": "remote",
                            "local_keys": ["other_code"],
                            "remote_keys": ["remote_code"],
                            "how": "inner",
                            "constraints": {"allow_row_decrease": True},
                        },
                    ],
                },
                "remote": {
                    "columns": ["remote_code"],
                    "keys": ["remote_code"],
                    "public_id": "remote_id",
                },
            }
        }
    )
    local_df = pd.DataFrame({"system_id": [100, 101, 102], "remote_code": ["A", "A", "missing"], "other_code": ["A", "missing", "A"]})
    remote_df = pd.DataFrame({"system_id": [7, 8], "remote_code": ["A", "B"]})
    linker = ForeignKeyLinker(project=project, table_store=TableStore({"local": local_df, "remote": remote_df}))

    for fk_cfg in project.get_table("local").foreign_keys:
        linker.link_foreign_key(local_df, fk_cfg, remote_df)

    issues = [issue for validator in linker.validators for issue in validator.issues if issue.issue_type == "row_count_mismatch"]
    assert len(issues) == 2

    resolutions = [
        resolve_row_count_issue(project, issue_type=issue.issue_type, local_entity=issue.local_entity, metadata=issue.metadata)
        for issue in issues
    ]

    assert [resolution.status for resolution in resolutions] == ["resolved", "resolved"]
    assert [resolution.fk_index for resolution in resolutions] == [0, 1]
    assert [resolution.fk for resolution in resolutions] == [
        project.get_table("local").foreign_keys[0],
        project.get_table("local").foreign_keys[1],
    ]


def integrity_metadata_for(project: ShapeShiftProject, index: int = 0) -> dict[str, Any]:
    """Build integrity-warning metadata for the saved foreign key at the given index."""
    fk: ForeignKeyConfig = saved_fk(project, index)
    return {
        "orphan_count": 2,
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
    }


def resolve_integrity(project: ShapeShiftProject, metadata: dict[str, Any], **kwargs: Any):
    """Resolve an integrity warning for the orders entity."""
    return resolve_integrity_issue(
        project,
        issue_type=kwargs.pop("issue_type", "FK_DATA_INTEGRITY"),
        local_entity=kwargs.pop("local_entity", "orders"),
        metadata=metadata,
    )


def test_integrity_issue_resolves_to_its_saved_foreign_key():
    """An integrity warning resolves to the saved entry that produced it."""
    project = build_project()

    resolution = resolve_integrity(project, integrity_metadata_for(project))

    assert resolution.status == "resolved"
    assert resolution.is_eligible is True
    assert resolution.fk_index == 0
    assert resolution.fk is saved_fk(project, 0)


@pytest.mark.parametrize("join_type", ["right", "outer", "cross"])
def test_integrity_issues_resolve_with_any_join_type(join_type: str):
    """Integrity warnings have no join-type restriction."""
    project = build_project(foreign_keys=[{"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"], "how": join_type}])

    resolution = resolve_integrity(project, integrity_metadata_for(project))

    assert resolution.status == "resolved"
    assert resolution.is_eligible is True
    assert resolution.fk is saved_fk(project, 0)


def test_integrity_issues_use_their_own_saved_entry_for_the_same_remote_entity():
    """Two links to the same remote entity resolve by their own index."""
    project = build_project(
        foreign_keys=[
            {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"]},
            {"entity": "customers", "local_keys": ["customer_code"], "remote_keys": ["code"]},
        ]
    )

    first = resolve_integrity(project, integrity_metadata_for(project, 0))
    second = resolve_integrity(project, integrity_metadata_for(project, 1))

    assert [(first.status, first.fk_index), (second.status, second.fk_index)] == [("resolved", 0), ("resolved", 1)]
    assert first.fk is saved_fk(project, 0)
    assert second.fk is saved_fk(project, 1)


def test_identical_integrity_entries_each_resolve_to_their_own_index():
    """Identical saved entries stay distinguishable by index."""
    duplicate: dict[str, Any] = {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["id"]}
    project = build_project(foreign_keys=[dict(duplicate), dict(duplicate)])

    first = resolve_integrity(project, integrity_metadata_for(project, 0))
    second = resolve_integrity(project, integrity_metadata_for(project, 1))

    assert [(first.status, first.fk_index), (second.status, second.fk_index)] == [("resolved", 0), ("resolved", 1)]


@pytest.mark.parametrize(
    "metadata",
    [
        pytest.param({"fk_signature": "abc"}, id="missing-index"),
        pytest.param({"fk_index": None, "fk_signature": "abc"}, id="none-index"),
        pytest.param({"fk_index": True, "fk_signature": "abc"}, id="bool-index"),
        pytest.param({"fk_index": "0", "fk_signature": "abc"}, id="string-index"),
        pytest.param({"fk_index": 0}, id="missing-signature"),
        pytest.param({}, id="no-identity"),
    ],
)
def test_integrity_warnings_without_usable_identity_are_refused(metadata: dict[str, Any]):
    """Older or malformed integrity warnings offer no action."""
    project = build_project()

    resolution = resolve_integrity(project, metadata)

    assert resolution.status == "missing_metadata"
    assert resolution.is_eligible is False
    assert resolution.fk is None


def test_integrity_warning_for_unknown_entity_is_refused():
    """An entity missing from the project offers no action."""
    project = build_project()

    resolution = resolve_integrity(project, integrity_metadata_for(project), local_entity="missing_entity")

    assert resolution.status == "entity_not_found"
    assert resolution.entity_name == "missing_entity"


def test_integrity_warning_with_out_of_range_index_is_refused():
    """An index that names no saved entry offers no action."""
    project = build_project()
    metadata: dict[str, Any] = {"fk_index": 5, "fk_signature": saved_fk(project).identity_signature}

    resolution = resolve_integrity(project, metadata)

    assert resolution.status == "index_out_of_range"
    assert resolution.fk_index == 5


def test_integrity_warning_with_edited_entry_is_refused():
    """A saved entry edited after the warning was recorded no longer matches."""
    metadata: dict[str, Any] = integrity_metadata_for(build_project())
    project = build_project(foreign_keys=[{**DEFAULT_FK, "how": "left"}])

    resolution = resolve_integrity(project, metadata)

    assert resolution.status == "signature_mismatch"
    assert resolution.fk_index == 0


def test_integrity_warning_with_shifted_index_is_refused():
    """A new entry before the target shifts positions instead of matching the wrong link."""
    target_fk: dict[str, Any] = {**DEFAULT_FK, "local_keys": ["customer_code"], "remote_keys": ["code"]}
    metadata: dict[str, Any] = integrity_metadata_for(build_project(foreign_keys=[dict(DEFAULT_FK), target_fk]), 1)
    project = build_project(
        foreign_keys=[
            {"entity": "customers", "local_keys": ["customer_id"], "remote_keys": ["code"]},
            dict(DEFAULT_FK),
            target_fk,
        ]
    )

    resolution = resolve_integrity(project, metadata)

    assert resolution.status == "signature_mismatch"
    assert resolution.fk_index == 1


def test_row_count_warnings_are_not_integrity_issues():
    """Row-count warnings use their own resolver."""
    project = build_project()

    resolution = resolve_integrity(project, metadata_for(project), issue_type="row_count_mismatch")

    assert resolution.status == "not_integrity_issue"
    assert resolution.is_eligible is False
