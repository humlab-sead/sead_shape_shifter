"""Tests for saved foreign-key identity: list position and identity signature."""

from typing import Any

import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig

BASE_FK: dict[str, Any] = {
    "entity": "customers",
    "local_keys": ["customer_id"],
    "remote_keys": ["id"],
    "how": "inner",
    "constraints": {"allow_row_decrease": True},
}


def build_project(*, foreign_keys: list[dict[str, Any]] | None = None) -> ShapeShiftProject:
    """Build a project whose local entity holds the given foreign keys in list order."""
    keys: list[dict[str, Any]] = foreign_keys if foreign_keys is not None else [dict(BASE_FK)]
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


def orders_table(project: ShapeShiftProject) -> TableConfig:
    """Return the local table of the test project."""
    return project.get_table("orders")


def signature_of(fk_cfg: dict[str, Any]) -> str:
    """Return the identity signature of a foreign key built from raw configuration."""
    return ForeignKeyConfig(local_entity="orders", fk_cfg=fk_cfg).identity_signature


def test_saved_foreign_keys_carry_their_list_position():
    """Each saved entry knows its position in the entity's foreign_keys list."""
    project = build_project(
        foreign_keys=[
            dict(BASE_FK),
            {**BASE_FK, "local_keys": ["customer_code"], "remote_keys": ["code"]},
            dict(BASE_FK),
        ]
    )

    assert [fk.fk_index for fk in orders_table(project).foreign_keys] == [0, 1, 2]


def test_directly_built_foreign_key_has_no_index():
    """A foreign key not built from a saved list has no index."""
    fk = ForeignKeyConfig(local_entity="orders", fk_cfg=dict(BASE_FK))

    assert fk.fk_index is None


def test_duplicate_entries_share_signature_but_not_index():
    """Two identical saved entries differ by position and agree on the signature."""
    project = build_project(foreign_keys=[dict(BASE_FK), dict(BASE_FK)])
    first, second = orders_table(project).foreign_keys

    assert first.identity_signature == second.identity_signature
    assert (first.fk_index, second.fk_index) == (0, 1)


def test_signature_is_stable_for_equal_configuration():
    """Equal configuration gives an equal signature."""
    assert signature_of(dict(BASE_FK)) == signature_of(dict(BASE_FK))


@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"entity": "suppliers"}, id="remote-entity"),
        pytest.param({"local_keys": ["customer_code"]}, id="local-keys"),
        pytest.param({"remote_keys": ["code"]}, id="remote-keys"),
        pytest.param({"how": "left"}, id="join-type"),
        pytest.param({"defer_dependency": True}, id="defer-dependency"),
        pytest.param({"constraints": {"allow_row_decrease": False}}, id="constraints"),
        pytest.param({"constraints": {"allow_row_decrease": True, "allow_unmatched_left": True}}, id="added-constraint-key"),
    ],
)
def test_signature_changes_when_a_listed_field_changes(change: dict[str, Any]):
    """Every field in the fixed signature list changes the digest when edited."""
    assert signature_of(dict(BASE_FK)) != signature_of({**BASE_FK, **change})


@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"extra_columns": {"customer_name": "name"}}, id="extra-columns"),
        pytest.param({"drop_remote_id": True}, id="drop-remote-id"),
    ],
)
def test_signature_ignores_fields_that_do_not_change_matching(change: dict[str, Any]):
    """extra_columns and drop_remote_id are outside the fixed signature list."""
    assert signature_of(dict(BASE_FK)) == signature_of({**BASE_FK, **change})


def test_missing_join_type_matches_inner_join_signature():
    """A missing how value is treated as an inner join, as the linker does."""
    without_how: dict[str, Any] = {key: value for key, value in BASE_FK.items() if key != "how"}

    assert signature_of(without_how) == signature_of(dict(BASE_FK))
