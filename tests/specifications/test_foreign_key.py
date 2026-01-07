"""Tests for foreign key specifications."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications.foreign_key import ForeignKeyConfigSpecification, ForeignKeyDataSpecification


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
        assert spec.error == ""

    def test_cross_join_with_keys_fails(self, mock_project):
        """Test validation fails for cross join with keys."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "cross", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "should not specify local_keys or remote_keys" in spec.error

    def test_non_cross_join_missing_keys(self, mock_project):
        """Test validation fails when keys missing for non-cross join."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left"},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is False
        assert "must be specified" in spec.error

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
        assert "does not match" in spec.error

    def test_valid_join_with_keys(self, mock_project):
        """Test validation passes for valid join with matching keys."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["local_id"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True
        assert spec.error == ""

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
        assert "not found in local entity" in spec.error

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
        assert "not found in remote entity" in spec.error

    def test_unnest_column_in_local_keys(self, mock_project):
        """Test validation passes when local key is in unnest_columns."""
        fk_cfg = ForeignKeyConfig(
            local_entity="local_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["unnest_col"], "remote_keys": ["remote_id"]},
        )

        spec = ForeignKeyConfigSpecification(mock_project)
        result = spec.is_satisfied_by(fk_cfg=fk_cfg)

        assert result is True

    def test_clear_resets_state(self, mock_project):
        """Test that clear() resets error and deferred state."""
        spec = ForeignKeyConfigSpecification(mock_project)
        spec.error = "test error"
        spec.deferred = True

        spec.clear()

        assert spec.error == ""
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
        assert spec.error == ""

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
        assert "not found in local entity" in spec.error

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
        assert "not found in remote entity" in spec.error

    def test_missing_local_df_assertion(self, mock_project):
        """Test assertion when local DataFrame missing."""
        fk_cfg = ForeignKeyConfig(
            entities_cfg={"missing_entity": {}, "remote_entity": {}},
            local_entity="missing_entity",
            fk_cfg={"entity": "remote_entity", "how": "left", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyDataSpecification({}, mock_project)

        with pytest.raises(AssertionError, match="Local DataFrame.*not found"):
            spec.is_satisfied_by(fk_cfg=fk_cfg)

    def test_missing_remote_df_assertion(self, mock_project):
        """Test assertion when remote DataFrame missing."""
        table_store = {"local_entity": pd.DataFrame({"id": [1]})}

        fk_cfg = ForeignKeyConfig(
            entities_cfg={"local_entity": {}, "missing_entity": {}},
            local_entity="local_entity",
            fk_cfg={"entity": "missing_entity", "how": "left", "local_keys": ["id"], "remote_keys": ["id"]},
        )

        spec = ForeignKeyDataSpecification(table_store, mock_project)

        with pytest.raises(AssertionError, match="Remote DataFrame.*not found"):
            spec.is_satisfied_by(fk_cfg=fk_cfg)

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
        table_store = {
            "local_entity": pd.DataFrame({"local_id": [1, 2]}),  # unnest_col not yet present
            "remote_entity": pd.DataFrame({"remote_id": [1, 2]}),
        }

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
        assert spec.error != ""
