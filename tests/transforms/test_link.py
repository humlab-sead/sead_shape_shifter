"""Tests for link helpers."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject
from src.transforms.link import ForeignKeyLinker

# pylint: disable=redefined-outer-name


@pytest.fixture
def fk_config() -> ForeignKeyConfig:
    """Create a foreign key config linking local.remote_ref -> remote.remote_id."""
    entities_cfg = {
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
            "public_id": "remote_pk",
        },
    }
    fk_cfg = entities_cfg["local"]["foreign_keys"][0]
    return ForeignKeyConfig(local_entity="local", fk_cfg=fk_cfg)


def test_link_foreign_key_renames_and_drops_remote_id(fk_config: ForeignKeyConfig, monkeypatch: pytest.MonkeyPatch):
    """Link foreign key adds renamed extra columns and drops remote id when requested."""
    project = ShapeShiftProject(
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
                    "public_id": "remote_id",
                },
            }
        }
    )
    local_df = pd.DataFrame({"remote_code": [1, 2], "value": ["a", "b"], "system_id": [100, 101]})
    remote_df = pd.DataFrame({"remote_pk": [10, 20], "remote_code": [1, 2], "name": ["alpha", "beta"], "system_id": [1, 2]})

    captured: dict[str, object] = {}

    class DummyValidator:
        def __init__(self, entity_name, fk):
            captured["init_entity"] = entity_name
            captured["fk"] = fk
            self.merge_indicator_col = "_merge_indicator_"

        def validate_before_merge(self, local_df_arg, remote_df_arg):
            captured["before_merge"] = (local_df_arg.copy(), remote_df_arg.copy())
            return self

        def validate_merge_opts(self):
            captured["merge_opts_called"] = True
            return {}

        def validate_after_merge(
            self, local_df_arg, remote_df_arg, linked_df_arg, merge_indicator_col=None  # pylint: disable=unused-argument
        ):
            captured["after_merge_called"] = True
            captured["merge_indicator"] = merge_indicator_col

    monkeypatch.setattr("src.transforms.link.ForeignKeyConstraintValidator", DummyValidator)
    table_store = {
        "local": pd.DataFrame({"remote_ref": [1]}),
        "remote": pd.DataFrame({"remote_id": [1]}),
    }
    linker: ForeignKeyLinker = ForeignKeyLinker(project=project, table_store=table_store)

    linked = linker.link_foreign_key(local_df, fk_config, remote_df)

    assert "remote_pk" not in linked.columns  # dropped after merge
    assert "remote_name" in linked.columns
    assert linked["remote_name"].tolist() == ["alpha", "beta"]
    assert captured["init_entity"] == "local"
    assert captured["merge_opts_called"] is True
    assert captured["after_merge_called"] is True


def test_link_entity_returns_deferred_when_specification_defers(monkeypatch: pytest.MonkeyPatch):
    """link_entity should return True and skip linking when specification marks deferred."""
    project = ShapeShiftProject(
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
                    "public_id": "remote_id",
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

        def is_satisfied_by(self, fk_cfg):  # pylint: disable=unused-argument
            self.deferred = True
            return True

        def is_already_linked(self, fk_cfg):
            return False

    linker = ForeignKeyLinker(project=project, table_store=table_store)

    monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

    # Patch linker.link_foreign_key
    with patch.object(linker, "link_foreign_key") as mock_link:
        deferred = linker.link_entity(entity_name="local")

    assert deferred is True
    mock_link.assert_not_called()
    pd.testing.assert_frame_equal(table_store["local"], pd.DataFrame({"remote_ref": [1]}))


class TestDeferredLinkingTrackerIntegration:
    """Tests for DeferredLinkingTracker integration with ForeignKeyLinker."""

    def test_linker_initializes_deferred_tracker(self):
        """ForeignKeyLinker should initialize DeferredLinkingTracker on creation."""
        table_store: dict[str, pd.DataFrame] = {}
        project = ShapeShiftProject(cfg={"entities": {}})
        linker: ForeignKeyLinker = ForeignKeyLinker(project=project, table_store=table_store)

        assert linker.deferred_tracker is not None
        assert linker.deferred_tracker.deferred == set()

    def test_link_entity_tracks_deferred_status_when_not_deferred(self, monkeypatch: pytest.MonkeyPatch):
        """link_entity should track entity as not deferred when linking completes successfully."""
        config = ShapeShiftProject(
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
                        "public_id": "remote_id",
                    },
                }
            }
        )

        table_store = {
            "local": pd.DataFrame({"remote_ref": [1]}),
            "remote": pd.DataFrame({"remote_id": [1]}),
        }

        class DummyValidator:
            def __init__(self, entity_name, fk):
                self.merge_indicator_col = "_merge_indicator_"

            def validate_before_merge(self, local_df_arg, remote_df_arg):
                return self

            def validate_merge_opts(self):
                return {}

            def validate_after_merge(self, local_df_arg, remote_df_arg, linked_df_arg, merge_indicator_col=None):
                pass

        class DummySpecification:
            def __init__(self, cfg=None, table_store=None, **_):
                self.deferred = False
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                return True

            def is_already_linked(self, fk_cfg):
                return False

        linker = ForeignKeyLinker(project=config, table_store=table_store)

        monkeypatch.setattr("src.transforms.link.ForeignKeyConstraintValidator", DummyValidator)
        monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

        with patch.object(linker, "link_foreign_key", return_value=table_store["local"]):
            deferred = linker.link_entity(entity_name="local")

        assert deferred is False
        assert "local" not in linker.deferred_tracker.deferred

    def test_link_entity_tracks_deferred_status_when_deferred(self, monkeypatch: pytest.MonkeyPatch):
        """link_entity should track entity as deferred in tracker when linking is deferred."""
        project = ShapeShiftProject(
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
                        "public_id": "remote_id",
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
                self.deferred = False
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                self.deferred = True
                return True

            def is_already_linked(self, fk_cfg):
                return False

        linker = ForeignKeyLinker(project=project, table_store=table_store)

        monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

        deferred = linker.link_entity(entity_name="local")

        assert deferred is True
        assert "local" in linker.deferred_tracker.deferred

    def test_link_entity_multiple_entities_tracking(self, monkeypatch: pytest.MonkeyPatch):
        """DeferredLinkingTracker should track deferred status of multiple entities."""
        project = ShapeShiftProject(
            cfg={
                "entities": {
                    "local": {
                        "columns": ["remote_ref"],
                        "keys": ["remote_ref"],
                        "foreign_keys": [
                            {"entity": "remote", "local_keys": ["remote_ref"], "remote_keys": ["remote_id"]},
                        ],
                    },
                    "middle": {
                        "columns": ["local_ref"],
                        "keys": ["local_ref"],
                        "depends_on": ["local"],
                        "foreign_keys": [
                            {"entity": "local", "local_keys": ["local_ref"], "remote_keys": ["local_ref"]},
                        ],
                    },
                    "remote": {
                        "columns": ["remote_id"],
                        "keys": ["remote_id"],
                        "public_id": "remote_id",
                    },
                }
            }
        )

        table_store = {
            "local": pd.DataFrame({"remote_ref": [1]}),
            "middle": pd.DataFrame({"local_ref": [1]}),
            "remote": pd.DataFrame({"remote_id": [1]}),
        }

        class DummyValidator:
            def __init__(self, entity_name, fk):
                self.merge_indicator_col = "_merge_indicator_"

            def validate_before_merge(self, local_df_arg, remote_df_arg):
                return self

            def validate_merge_opts(self):
                return {}

            def validate_after_merge(self, local_df_arg, remote_df_arg, linked_df_arg, merge_indicator_col=None):
                pass

        class DummySpecification:
            def __init__(self, cfg=None, table_store=None, **_):
                self.deferred = False
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                return True

            def is_already_linked(self, fk_cfg):
                return False

        linker = ForeignKeyLinker(project=project, table_store=table_store)

        monkeypatch.setattr("src.transforms.link.ForeignKeyConstraintValidator", DummyValidator)
        monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

        with patch.object(linker, "link_foreign_key", return_value=table_store["local"]):
            deferred_local = linker.link_entity(entity_name="local")
            deferred_middle = linker.link_entity(entity_name="middle")

        assert deferred_local is False
        assert deferred_middle is False
        assert linker.deferred_tracker.deferred == set()

    def test_deferred_tracker_removes_entity_when_no_longer_deferred(self, monkeypatch: pytest.MonkeyPatch):
        """DeferredLinkingTracker should remove entity when it transitions from deferred to not deferred."""
        project = ShapeShiftProject(
            cfg={
                "entities": {
                    "entity": {
                        "columns": ["ref"],
                        "keys": ["ref"],
                        "foreign_keys": [
                            {"entity": "remote", "local_keys": ["ref"], "remote_keys": ["id"]},
                        ],
                    },
                    "remote": {
                        "columns": ["id"],
                        "keys": ["id"],
                        "public_id": "id",
                    },
                }
            }
        )

        table_store = {
            "entity": pd.DataFrame({"ref": [1]}),
            "remote": pd.DataFrame({"id": [1]}),
        }

        class DummyValidator:
            def __init__(self, entity_name, fk):
                self.merge_indicator_col = "_merge_indicator_"

            def validate_before_merge(self, local_df_arg, remote_df_arg):
                return self

            def validate_merge_opts(self):
                return {}

            def validate_after_merge(self, local_df_arg, remote_df_arg, linked_df_arg, merge_indicator_col=None):
                pass

        # Use a shared state object to track calls across multiple instantiations
        shared_state = {"call_count": 0}

        class DummySpecification:
            def __init__(self, cfg=None, table_store=None, **_):
                self.deferred = False
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                # First call: deferred, second call: not deferred
                shared_state["call_count"] += 1
                if shared_state["call_count"] == 1:
                    self.deferred = True
                    return True
                self.deferred = False
                return True

            def is_already_linked(self, fk_cfg):
                return False

        linker = ForeignKeyLinker(project=project, table_store=table_store)

        monkeypatch.setattr("src.transforms.link.ForeignKeyConstraintValidator", DummyValidator)
        monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

        with patch.object(linker, "link_foreign_key", return_value=table_store["entity"]):
            # First call: entity should be tracked as deferred
            deferred1 = linker.link_entity(entity_name="entity")
            assert deferred1 is True
            assert "entity" in linker.deferred_tracker.deferred

            # Second call: entity should be removed from deferred set
            deferred2 = linker.link_entity(entity_name="entity")
            assert deferred2 is False
            assert "entity" not in linker.deferred_tracker.deferred

    def test_deferred_tracker_state_independence(self, monkeypatch: pytest.MonkeyPatch):
        """Each ForeignKeyLinker instance should have independent DeferredLinkingTracker state."""
        project = ShapeShiftProject(
            cfg={
                "entities": {
                    "entity": {
                        "columns": ["ref"],
                        "keys": ["ref"],
                        "foreign_keys": [
                            {"entity": "remote", "local_keys": ["ref"], "remote_keys": ["id"]},
                        ],
                    },
                    "remote": {
                        "columns": ["id"],
                        "keys": ["id"],
                        "public_id": "id",
                    },
                }
            }
        )

        table_store1 = {
            "entity": pd.DataFrame({"ref": [1]}),
            "remote": pd.DataFrame({"id": [1]}),
        }

        table_store2 = {
            "entity": pd.DataFrame({"ref": [2]}),
            "remote": pd.DataFrame({"id": [2]}),
        }

        class DummySpecification:
            def __init__(self, cfg=None, table_store=None, **_):
                self.deferred = True
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                return True

            def is_already_linked(self, fk_cfg):
                return False

        linker1 = ForeignKeyLinker(project=project, table_store=table_store1)
        linker2 = ForeignKeyLinker(project=project, table_store=table_store2)

        monkeypatch.setattr("src.transforms.link.ForeignKeyDataSpecification", DummySpecification)

        linker1.link_entity(entity_name="entity")
        linker2.link_entity(entity_name="entity")

        # Both should have tracked the entity as deferred
        assert "entity" in linker1.deferred_tracker.deferred
        assert "entity" in linker2.deferred_tracker.deferred
        # But they should be independent instances
        assert linker1.deferred_tracker is not linker2.deferred_tracker
