"""Test for the duplicate column bug when FK column already exists in local entity.

This reproduces the scenario from arbodat-copy project where:
- dataset entity has master_set_id set via extra_columns
- master_dataset is a fixed entity with public_id="master_dataset_id"
- master_dataset also has "master_dataset_id" in its columns list
- The FK linking should not create duplicate columns
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.transforms.link import ForeignKeyLinker


class TestDuplicateColumnBug:
    """Tests for the duplicate column bug scenario."""

    @pytest.fixture
    def project_config(self):
        """Project config matching the arbodat-copy scenario."""
        return {
            "entities": {
                "dataset": {
                    "type": "entity",
                    "source": "analysis_entity",
                    "public_id": "dataset_id",
                    "keys": ["Projekt", "Fraktion"],
                    "columns": ["Projekt", "Fraktion"],
                    "foreign_keys": [
                        {
                            "entity": "project",
                            "local_keys": ["Projekt"],
                            "remote_keys": ["Projekt"],
                        },
                        {
                            "entity": "method",
                            "local_keys": ["Fraktion"],
                            "remote_keys": ["arbodat_code"],
                        },
                        {
                            "entity": "master_dataset",
                            "local_keys": ["master_set_id"],
                            "remote_keys": ["master_dataset_id"],
                        },
                    ],
                    "extra_columns": {
                        "dataset_type_id": None,
                        "dataset_name": "method_name",
                        "master_set_id": 1,
                        "data_type_id": None,
                        "biblio_id": None,
                    },
                },
                "master_dataset": {
                    "type": "fixed",
                    "public_id": "master_dataset_id",
                    "keys": [],
                    "columns": [
                        "master_dataset_id",
                        "contact_id",
                        "biblio_id",
                        "master_name",
                        "master_notes",
                        "url",
                    ],
                    "values": [[1, None, None, "ArboDat Pilot", None, None]],
                },
                "method": {
                    "type": "entity",
                    "public_id": "method_id",
                    "keys": ["arbodat_code"],
                    "columns": ["arbodat_code", "method_name"],
                },
                "project": {
                    "type": "entity",
                    "public_id": "project_id",
                    "keys": ["Projekt"],
                    "columns": ["Projekt", "project_name"],
                },
            }
        }

    @pytest.fixture
    def table_store(self):
        """Table store with data simulating the bug scenario."""
        return {
            "dataset": pd.DataFrame(
                {
                    "system_id": [1, 2],
                    "Fraktion": ["ORG 0,5", "Trocken"],
                    "Projekt": ["18_0025", "18_0025"],
                    "master_set_id": [1, 1],  # Already set via extra_columns
                    "method_id": [1, 2],  # Already linked
                    "project_id": [1, 1],  # Already linked
                    "arbodat_code": ["ORG", "TRO"],
                    "method_name": ["Organic", "Dry"],
                }
            ),
            "master_dataset": pd.DataFrame(
                {
                    "system_id": [1],
                    "master_dataset_id": [1],  # This creates the duplicate!
                    "contact_id": [None],
                    "biblio_id": [None],
                    "master_name": ["ArboDat Pilot"],
                    "master_notes": [None],
                    "url": [None],
                }
            ),
            "method": pd.DataFrame(
                {
                    "system_id": [1, 2],
                    "arbodat_code": ["ORG", "TRO"],
                    "method_name": ["Organic", "Dry"],
                }
            ),
            "project": pd.DataFrame({"system_id": [1], "Projekt": ["18_0025"], "project_name": ["Project 18_0025"]}),
        }

    def test_bug_scenario_no_duplicate_columns(self, project_config, table_store):
        """Test that the bug scenario doesn't create duplicate columns."""
        project = ShapeShiftProject(cfg=project_config)

        # Mock the validator
        mock_validator = MagicMock()
        mock_validator.merge_indicator_col = "_merge"
        mock_validator.validate_before_merge.return_value = mock_validator
        mock_validator.validate_merge_opts.return_value = {}

        with patch("src.transforms.link.ForeignKeyConstraintValidator", return_value=mock_validator):
            linker = ForeignKeyLinker(project=project, table_store=table_store)

            # Get the FK config for master_dataset
            dataset_cfg = project.get_table("dataset")
            master_dataset_fk = [fk for fk in dataset_cfg.foreign_keys if fk.remote_entity == "master_dataset"][0]

            local_df = table_store["dataset"]
            remote_df = table_store["master_dataset"]

            # This should NOT raise "ValueError: The column label 'master_dataset_id' is not unique"
            result_df = linker.link_foreign_key(local_df, master_dataset_fk, remote_df)

            # Verify no duplicate columns
            column_counts = result_df.columns.value_counts()
            duplicates = column_counts[column_counts > 1]
            assert len(duplicates) == 0, f"Found duplicate columns: {duplicates.index.tolist()}"

            # Verify master_dataset_id exists
            assert "master_dataset_id" in result_df.columns

    def test_bug_scenario_full_link_entity(self, project_config, table_store):
        """Test the full link_entity workflow with the bug scenario."""
        project = ShapeShiftProject(cfg=project_config)

        # Mock the specification to avoid external dependencies
        class MockSpecification:
            def __init__(self, cfg=None, table_store=None):
                self.deferred = False
                self.error = ""

            def is_satisfied_by(self, fk_cfg):
                return True

            def is_already_linked(self, fk_cfg):
                # Simulate that project and method are already linked
                return fk_cfg.remote_entity in ["project", "method"]

            def get_report(self):
                return self.error

        mock_validator = MagicMock()
        mock_validator.merge_indicator_col = "_merge"
        mock_validator.validate_before_merge.return_value = mock_validator
        mock_validator.validate_merge_opts.return_value = {}

        with patch("src.transforms.link.ForeignKeyDataSpecification", MockSpecification):
            with patch("src.transforms.link.ForeignKeyConstraintValidator", return_value=mock_validator):
                linker = ForeignKeyLinker(project=project, table_store=table_store)

                # Link the dataset entity
                linker.link_entity(entity_name="dataset")

                # Verify the result
                result_df = table_store["dataset"]

                # Should have master_dataset_id
                assert "master_dataset_id" in result_df.columns

                # Should not have duplicate columns
                column_counts = result_df.columns.value_counts()
                duplicates = column_counts[column_counts > 1]
                assert len(duplicates) == 0, f"Found duplicate columns: {duplicates.index.tolist()}"

    def test_alternative_approach_already_exists(self, project_config, table_store):
        """Test the alternative approach: skip merge if FK column already exists."""
        project = ShapeShiftProject(cfg=project_config)

        # Add master_dataset_id to the dataset table (simulating it already exists)
        table_store["dataset"]["master_dataset_id"] = 1

        mock_validator = MagicMock()
        mock_validator.merge_indicator_col = "_merge"
        mock_validator.validate_before_merge.return_value = mock_validator
        mock_validator.validate_merge_opts.return_value = {}

        with patch("src.transforms.link.ForeignKeyConstraintValidator", return_value=mock_validator):
            linker = ForeignKeyLinker(project=project, table_store=table_store)

            dataset_cfg = project.get_table("dataset")
            master_dataset_fk = [fk for fk in dataset_cfg.foreign_keys if fk.remote_entity == "master_dataset"][0]

            local_df = table_store["dataset"].copy()
            remote_df = table_store["master_dataset"]

            # If we implement the alternative approach, this should detect the column exists
            # and return local_df unchanged
            result_df = linker.link_foreign_key(local_df, master_dataset_fk, remote_df)

            # The result should have master_dataset_id
            assert "master_dataset_id" in result_df.columns

            # Original values should be preserved (all 1s)
            assert result_df["master_dataset_id"].tolist() == [1, 1]

    def test_remote_df_has_duplicate_columns_in_source(self):
        """Test the exact error case: remote_df has duplicate column after rename."""
        # This is the minimal reproduction of the pandas error
        remote_df = pd.DataFrame(
            {
                "system_id": [1],
                "master_dataset_id": [1],  # This causes duplicate after rename
            }
        )

        # This demonstrates the bug: selecting both columns then renaming creates duplicate
        with pytest.raises(ValueError, match="column label.*is not unique"):
            # This is what the old code did:
            renames = {"system_id": "master_dataset_id"}
            # Select both columns, then rename system_id -> master_dataset_id
            # This creates TWO columns named "master_dataset_id"
            bad_result = remote_df[["system_id", "master_dataset_id"]].rename(columns=renames)
            # Trying to use this in a merge causes the error
            pd.merge(
                pd.DataFrame({"key": [1]}),
                bad_result,
                left_on=["key"],
                right_on=["master_dataset_id"],
            )

    def test_fixed_approach_filters_duplicate_targets(self):
        """Test the fix: filter out columns that would be created by rename."""
        remote_df = pd.DataFrame(
            {
                "system_id": [1],
                "master_dataset_id": [1],
                "master_name": ["Test"],
            }
        )

        renames = {"system_id": "master_dataset_id"}

        # The fix: filter out columns that are in rename targets (non-identity only)
        extra_cols = ["master_dataset_id", "master_name"]
        rename_targets = {target for source, target in renames.items() if source != target}
        cols_to_select = [col for col in extra_cols if col not in rename_targets]

        # Should only select master_name, not master_dataset_id (since it's being created by rename)
        assert cols_to_select == ["master_name"]

        # This works without error
        result = remote_df[["system_id"] + cols_to_select].rename(columns=renames)

        # Verify we have the right columns
        assert "master_dataset_id" in result.columns
        assert "master_name" in result.columns
        assert len([c for c in result.columns if c == "master_dataset_id"]) == 1

    def test_identity_renames_are_allowed(self):
        """Test that identity renames like {'name': 'name'} are preserved."""
        remote_df = pd.DataFrame(
            {
                "system_id": [1, 2],
                "remote_id": [10, 20],
                "name": ["A", "B"],
                "value": [100, 200],
            }
        )

        # Mix of real rename and identity rename
        renames = {"system_id": "remote_id", "name": "name"}

        extra_cols = ["remote_id", "name", "value"]

        # Filter should only exclude true renames (not identity renames)
        rename_targets = {target for source, target in renames.items() if source != target}
        cols_to_select = [col for col in extra_cols if col not in rename_targets]

        # Should filter remote_id (created by system_id->remote_id) but keep name and value
        assert rename_targets == {"remote_id"}
        assert set(cols_to_select) == {"name", "value"}

        # Apply the logic
        result = remote_df[["system_id"] + cols_to_select].rename(columns=renames)

        # Verify: should have remote_id (from rename), name, and value
        assert set(result.columns) == {"remote_id", "name", "value"}
        assert result["name"].tolist() == ["A", "B"]
        assert result["value"].tolist() == [100, 200]
        assert result["remote_id"].tolist() == [1, 2]  # From system_id
