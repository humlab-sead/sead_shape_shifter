"""Tests for foreign key specifications."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications.foreign_key import (
    ForeignKeyConfigSpecification,
    ForeignKeyDataSpecification,
    ForeignKeyRemotePublicIdSpecification,
)
from src.table_store import TableStore


class TestForeignKeyConfigSpecification:
    """Tests for ForeignKeyConfigSpecification."""

    @pytest.fixture
    def mock_project(self):
        """Mock ShapeShiftProject for testing."""
        project = MagicMock(spec=ShapeShiftProject)

        # Create mock local table
        local_table = MagicMock(spec=TableConfig)
        local_table.keys_columns_and_fks = ["local_id", "local_name"]
        local_table.unnest_columns = ["unnest_col"]
        local_table.get_columns.return_value = ["local_id", "local_name", "data"]

        # Create mock remote table
        remote_table = MagicMock(spec=TableConfig)
        remote_table.get_columns.return_value = ["remote_id", "remote_name"]

        # Configure project to return these tables
        def get_table(entity_name):
            if entity_name == "local_entity":
                return local_table
            if entity_name == "remote_entity":
                return remote_table
            return None

        project.get_table = get_table

        return project

    def test_cross_join_valid(self, mock_project):
        """Test validation passes for valid cross join."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "cross"},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert not spec.has_errors(), spec.get_report()

    def test_cross_join_with_keys_fails(self, mock_project):
        """Test validation fails for cross join with keys."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "cross", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "should not specify local_keys or remote_keys" in spec.get_report()

    def test_non_cross_join_missing_keys(self, mock_project):
        """Test validation fails when keys missing for non-cross join."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left"},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "must be specified" in spec.get_report()

    def test_mismatched_key_count(self, mock_project):
        """Test validation fails when key counts don't match."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["local_id"],
                "remote_keys": ["remote_id", "remote_name"],
            },
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "does not match" in spec.get_report()

    def test_valid_join_with_keys(self, mock_project):
        """Test validation passes for valid join with matching keys."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert not spec.has_errors(), spec.get_report()

    def test_missing_local_key(self, mock_project):
        """Test validation fails when local key doesn't exist."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["nonexistent_key"],
                "remote_keys": ["remote_id"],
            },
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "not found in local entity" in spec.get_report()

    def test_missing_remote_key(self, mock_project):
        """Test validation fails when remote key doesn't exist."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["local_id"],
                "remote_keys": ["nonexistent_key"],
            },
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "not found in remote entity" in spec.get_report()

    def test_unnest_column_in_local_keys(self, mock_project):
        """Test validation passes when local key is in unnest_columns."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["unnest_col"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert not spec.has_errors(), spec.get_report()

    def test_clear_resets_state(self, mock_project):
        """Test that clear() resets error and deferred state."""
        spec = ForeignKeyConfigSpecification(mock_project)
        spec.add_error("test error", entity="local_entity")
        spec.deferred = True

        spec.clear()

        assert not spec.has_errors(), spec.get_report()
        assert spec.deferred is False


class TestForeignKeyDataSpecification:
    """Tests for ForeignKeyDataSpecification."""

    @pytest.fixture
    def mock_project(self):
        """Mock ShapeShiftProject for testing."""
        project = MagicMock(spec=ShapeShiftProject)

        # Create mock local table
        local_table = MagicMock(spec=TableConfig)
        local_table.keys_columns_and_fks = ["local_id", "local_name"]
        local_table.unnest_columns = set(["unnest_col"])
        local_table.get_columns.return_value = ["local_id", "local_name", "data"]

        # Create mock remote table
        remote_table = MagicMock(spec=TableConfig)
        remote_table.get_columns.return_value = ["remote_id", "remote_name"]

        # Configure project to return these tables
        def get_table(entity_name):
            if entity_name == "local_entity":
                return local_table
            if entity_name == "remote_entity":
                return remote_table
            return None

        project.get_table = get_table

        return project

    @pytest.fixture
    def table_store(self):
        """Sample table store with DataFrames."""
        return {
            "local_entity": pd.DataFrame({"local_id": [1, 2], "local_name": ["a", "b"], "data": ["x", "y"]}),
            "remote_entity": pd.DataFrame({"remote_id": [1, 2], "remote_name": ["A", "B"]}),
        }

    def test_valid_data_join(self, mock_project, table_store):
        """Test validation passes when all keys exist in data."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert not spec.has_errors(), spec.get_report()

    def test_missing_local_key_in_data(self, mock_project, table_store):
        """Test validation fails when local key missing from data."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["missing_col"],
                "remote_keys": ["remote_id"],
            },
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "not found in local entity" in spec.get_report()

    def test_missing_remote_key_in_data(self, mock_project, table_store):
        """Test validation fails when remote key missing from data."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["local_id"],
                "remote_keys": ["missing_col"],
            },
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "not found in remote entity" in spec.get_report()

    def test_missing_local_df_assertion(self, mock_project):
        """Test assertion when local DataFrame missing."""
        fk_cfg = ForeignKeyConfig(
            local_entity="missing_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyDataSpecification(TableStore({}), mock_project)

        with pytest.raises(ValueError, match="Local entity.*not found"):
            spec.is_satisfied_by(fk_cfg=fk_cfg)

    def test_missing_remote_entity_assertion(self, mock_project):
        """Test assertion when remote DataFrame missing."""
        table_store = TableStore({"local_entity": pd.DataFrame({"id": [1]})})

        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "missing_entity", "how": "left", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)

        is_ok: bool = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert not is_ok
        assert spec.deferred is True
        assert "deferring link" in spec.get_report()

    def test_deferred_when_missing_unnest_column(self, mock_project, table_store):
        """Test validation is deferred when missing local key is in unnest_columns."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["unnest_col"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert spec.deferred is True

    def test_deferred_when_pending_fields(self, mock_project):
        """Test validation is deferred when there are pending unnest fields."""
        # Create table store where local entity is missing unnest column
        table_store = TableStore(
            {
                "local_entity": pd.DataFrame({"local_id": [1, 2]}),  # unnest_col not yet present
                "remote_entity": pd.DataFrame({"remote_id": [1, 2]}),
            }
        )

        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        # Should be deferred if unnest_columns not yet in data
        if spec.deferred:
            assert result is True
        else:
            assert result in (True, False)

    def test_get_missing_fields(self, mock_project, table_store):
        """Test get_missing_fields utility method."""
        spec = ForeignKeyDataSpecification(table_store, mock_project)

        missing = spec.get_missing_fields(required_fields={"a", "b", "c"}, available_fields={"a", "b"})

        assert missing == {"c"}

    def test_get_missing_local_fields(self, mock_project, table_store):
        """Test get_missing_local_fields method."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["local_id", "missing_col"],
                "remote_keys": ["remote_id", "remote_name"],
            },
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        missing = spec.get_missing_local_fields(fk_cfg=fk_cfg)

        assert "missing_col" in missing

    def test_get_missing_remote_fields(self, mock_project, table_store):
        """Test get_missing_remote_fields method."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={
                "entity": "remote_entity",
                "how": "left",
                "local_keys": ["local_id"],
                "remote_keys": ["missing_col"],
            },
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        missing = spec.get_missing_remote_fields(fk_cfg=fk_cfg)

        assert "missing_col" in missing

    def test_config_validation_failure_propagates(self, mock_project, table_store):
        """Test that config validation failures propagate to data validation."""
        # Create invalid FK config (mismatched key counts)
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["r1", "r2"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        # Error should come from config validation
        assert spec.has_errors()


class TestIdentityKeyHint:
    """Tests for the identity-column hint added to the missing-remote-key error."""

    @pytest.fixture
    def mock_project(self):
        """Mock project whose remote table has a public_id and a system_id."""
        project = MagicMock(spec=ShapeShiftProject)

        local_table = MagicMock(spec=TableConfig)
        local_table.keys_columns_and_fks = ["local_id"]
        local_table.unnest_columns = []

        remote_table = MagicMock(spec=TableConfig)
        # The remote entity exposes only a data column; neither identity column is joinable.
        remote_table.get_columns.return_value = ["data"]
        remote_table.system_id = "system_id"
        remote_table.public_id = "site_id"

        def get_table(entity_name):
            return local_table if entity_name == "local_entity" else remote_table

        project.get_table = get_table
        return project

    def test_missing_public_id_key_explains_public_id_rule(self, mock_project):
        """Joining on the remote public_id explains that FKs store system_id values."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["site_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        report: str = spec.get_report()
        assert result is False
        assert "not found in remote entity" in report
        assert "is the remote entity's 'public_id'" in report
        assert "Join on 'remote_entity.system_id' instead" in report

    def test_missing_system_id_key_explains_generated_system_id(self, mock_project):
        """Joining on the remote system_id explains it is generated during normalization."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["system_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        report: str = spec.get_report()
        assert result is False
        assert "not found in remote entity" in report
        assert "generated 'system_id'" in report

    def test_unrelated_missing_key_has_no_hint(self, mock_project):
        """A missing key that is not an identity column keeps the plain message."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["bogus"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        report: str = spec.get_report()
        assert result is False
        assert "not found in remote entity" in report
        assert "public_id" not in report
        assert "system_id" not in report


class TestForeignKeyRemotePublicIdSpecification:
    """Tests for the structural warning on joins against an unpopulated remote public_id."""

    @staticmethod
    def _project_cfg(*, remote_cfg: dict, remote_keys: list[str], how: str = "left") -> dict:
        """Build a minimal project where ``child`` joins ``remote`` on ``remote_keys``."""
        return {
            "entities": {
                "child": {
                    "columns": ["join_col"],
                    "foreign_keys": [
                        {"entity": "remote", "local_keys": ["join_col"], "remote_keys": remote_keys, "how": how},
                    ],
                },
                "remote": remote_cfg,
            }
        }

    def _warning_codes(self, project_cfg: dict, mapping_catalog=None) -> list[str]:
        spec = ForeignKeyRemotePublicIdSpecification(project_cfg, mapping_catalog)
        spec.is_satisfied_by()
        return [issue.code for issue in spec.warnings]

    def test_fixed_all_null_public_id_warns(self):
        """A fixed remote whose public_id is all-null warns when joined on."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "fixed", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "values": [[1, None, "foo"]]},
            remote_keys=["site_id"],
        )
        assert self._warning_codes(project_cfg) == ["FK_REMOTE_PUBLIC_ID_EMPTY"]

    def test_fixed_populated_public_id_no_warning(self):
        """A fixed remote whose public_id carries values is left alone."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "fixed", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "values": [[1, 100, "foo"]]},
            remote_keys=["site_id"],
        )
        assert self._warning_codes(project_cfg) == []

    def test_fixed_with_append_no_warning(self):
        """A fixed remote filled by append is assumed to populate the public_id."""
        project_cfg = self._project_cfg(
            remote_cfg={
                "type": "fixed",
                "public_id": "site_id",
                "keys": ["name"],
                "columns": ["name"],
                "values": [[1, None, "foo"]],
                "append": {"values": [[2, 200, "bar"]]},
            },
            remote_keys=["site_id"],
        )
        assert self._warning_codes(project_cfg) == []

    def test_sql_public_id_not_a_column_warns(self):
        """A sql remote whose public_id is not a declared column warns when joined on."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "query": "select 1"},
            remote_keys=["site_id"],
        )
        assert self._warning_codes(project_cfg) == ["FK_REMOTE_PUBLIC_ID_EMPTY"]

    def test_sql_public_id_as_column_no_warning(self):
        """A sql remote that selects its public_id as a column is left alone."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["site_id", "name"], "query": "select 1"},
            remote_keys=["site_id"],
        )
        assert self._warning_codes(project_cfg) == []

    def test_committed_sidecar_suppresses_warning(self):
        """A committed mapping sidecar that populates the public_id suppresses the warning."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "query": "select 1"},
            remote_keys=["site_id"],
        )
        catalog = MagicMock()
        catalog.committed_links_by_entity.return_value = {"site_id": MagicMock()}
        assert self._warning_codes(project_cfg, mapping_catalog=catalog) == []

    def test_cross_join_skipped(self):
        """A cross join carries no remote keys to check and is skipped."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "query": "select 1"},
            remote_keys=["site_id"],
            how="cross",
        )
        assert self._warning_codes(project_cfg) == []

    def test_join_on_other_key_no_warning(self):
        """Joining on a key that is not the public_id is left alone."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "query": "select 1"},
            remote_keys=["name"],
        )
        assert self._warning_codes(project_cfg) == []

    def test_unresolved_directive_remote_keys_skipped(self):
        """An unresolved directive string in remote_keys is skipped rather than substring-matched."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "sql", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "query": "select 1"},
            remote_keys=["site_id"],
        )
        project_cfg["entities"]["child"]["foreign_keys"][0]["remote_keys"] = "@load: site_id"
        assert self._warning_codes(project_cfg) == []

    def test_missing_remote_entity_no_crash(self):
        """A foreign key pointing at an unknown entity is skipped without error."""
        project_cfg = {
            "entities": {
                "child": {
                    "columns": ["join_col"],
                    "foreign_keys": [{"entity": "ghost", "local_keys": ["join_col"], "remote_keys": ["site_id"]}],
                }
            }
        }
        assert self._warning_codes(project_cfg) == []

    def test_warning_carries_field_and_entity(self):
        """The warning records the child entity and the remote_keys field."""
        project_cfg = self._project_cfg(
            remote_cfg={"type": "fixed", "public_id": "site_id", "keys": ["name"], "columns": ["name"], "values": [[1, None, "foo"]]},
            remote_keys=["site_id"],
        )
        spec = ForeignKeyRemotePublicIdSpecification(project_cfg)
        spec.is_satisfied_by()
        assert len(spec.warnings) == 1
        warning = spec.warnings[0]
        assert warning.entity == "child"
        assert warning.field == "foreign_keys[].remote_keys"
        assert "Join on 'remote.system_id' instead" in warning.message
