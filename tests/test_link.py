"""Tests for link helpers."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.link import link_entity, link_foreign_key
from src.model import ForeignKeyConfig, ShapeShiftConfig


@pytest.fixture
def fk_config() -> ForeignKeyConfig:
    """Create a foreign key config linking local.remote_ref -> remote.remote_id."""
    cfg = {
        "local": {
            "columns": ["remote_code", "value"],
            "keys": ["remote_code"],
            "foreign_keys": [
                {
                    "entity": "remote",
                    "local_keys": ["remote_code"],
                    "remote_keys": ["remote_code"],
                    "extra_columns": {"remote_name": "name"},
                    "drop_remote_id": True,
                }
            ],
        },
        "remote": {
            "columns": ["remote_pk", "remote_code", "name"],
            "keys": ["remote_code"],
            "surrogate_id": "remote_pk",
        },
    }
    fk_data = cfg["local"]["foreign_keys"][0]
    return ForeignKeyConfig(cfg=cfg, local_entity="local", data=fk_data)


def test_link_foreign_key_renames_and_drops_remote_id(fk_config: ForeignKeyConfig, monkeypatch: pytest.MonkeyPatch):
    """Link foreign key adds renamed extra columns and drops remote id when requested."""
    local_df = pd.DataFrame({"remote_code": [1, 2], "value": ["a", "b"]})
    remote_df = pd.DataFrame({"remote_pk": [10, 20], "remote_code": [1, 2], "name": ["alpha", "beta"]})

    captured: dict[str, object] = {}

    class DummyValidator:
        def __init__(self, entity_name, fk):
            captured["init_entity"] = entity_name
            captured["fk"] = fk

        def validate_before_merge(self, local_df_arg, remote_df_arg):
            captured["before_merge"] = (local_df_arg.copy(), remote_df_arg.copy())
            return self

        def validate_merge_opts(self):
            captured["merge_opts_called"] = True
            return {}

        def validate_after_merge(self, *_):
            captured["after_merge_called"] = True

    monkeypatch.setattr("src.link.ForeignKeyConstraintValidator", DummyValidator)

    linked = link_foreign_key("local", local_df, fk_config, "remote_pk", remote_df)

    assert "remote_pk" not in linked.columns  # dropped after merge
    assert "remote_name" in linked.columns
    assert linked["remote_name"].tolist() == ["alpha", "beta"]
    assert captured["init_entity"] == "local"
    assert captured["merge_opts_called"] is True
    assert captured["after_merge_called"] is True


def test_link_entity_returns_deferred_when_specification_defers(monkeypatch: pytest.MonkeyPatch):
    """link_entity should return True and skip linking when specification marks deferred."""
    config = ShapeShiftConfig(
        cfg={
            "entities": {
                "local": {
                    "columns": ["remote_ref"],
                    "keys": ["remote_ref"],
                    "foreign_keys": [
                        {"entity": "remote", "local_keys": ["remote_ref"], "remote_keys": ["remote_id"]},
                    ],
                },
                "remote": {
                    "columns": ["remote_id"],
                    "keys": ["remote_id"],
                    "surrogate_id": "remote_id",
                },
            }
        }
    )

    table_store = {
        "local": pd.DataFrame({"remote_ref": [1]}),
        "remote": pd.DataFrame({"remote_id": [1]}),
    }

    class DummySpecification:
        def __init__(self, cfg=None, table_store=None, **_):
            self.cfg = cfg
            self.table_store = table_store
            self.deferred = False
            self.error = ""

        def is_satisfied_by(self, fk_cfg):
            self.deferred = True
            return True

    monkeypatch.setattr("src.link.ForeignKeyDataSpecification", DummySpecification)
    with patch("src.link.link_foreign_key") as mock_link:
        deferred = link_entity(entity_name="local", config=config, table_store=table_store)

    assert deferred is True
    mock_link.assert_not_called()
    pd.testing.assert_frame_equal(table_store["local"], pd.DataFrame({"remote_ref": [1]}))
