"""Test FK linking when local entity already has FK column via extra_columns.

This test reproduces the bug where:
1. Local entity has a column added via extra_columns (e.g., description_type_id: 1)
2. That column is used as a FK local_key to join with remote entity's system_id
3. The remote entity is a fixed entity with system_id in its columns
4. The join fails with KeyError: 'system_id' because system_id was renamed to public_id before merge
"""

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject
from src.transforms.link import ForeignKeyLinker


@pytest.fixture
def sample_project_config():
    """Minimal project config matching the roger-copy pattern."""
    return {
        "metadata": {"name": "test_project", "version": "1.0.0"},
        "entities": {
            "sample_description_type": {
                "type": "fixed",
                "public_id": "sample_description_type_id",
                "keys": [],
                "columns": ["system_id", "sample_description_type_id", "type_name", "type_description"],
                "values": [
                    [1, None, "Biological Age", "The (infered) age or development stage"]
                ]
            },
            "sample_description": {
                "type": "entity",
                "source": "datasheet",
                "public_id": "sample_description_id",
                "keys": [],
                "columns": ["biological_age"],
                "foreign_keys": [
                    {
                        "entity": "sample_description_type",
                        "local_keys": ["description_type_id"],
                        "remote_keys": ["system_id"]
                    }
                ],
                "extra_columns": {
                    "description_type_id": 1
                }
            }
        }
    }


@pytest.fixture
def table_store():
    """Mock table store with sample data."""
    return {
        "sample_description_type": pd.DataFrame({
            "system_id": [1],
            "sample_description_type_id": [None],
            "type_name": ["Biological Age"],
            "type_description": ["The (infered) age or development stage"]
        }),
        "sample_description": pd.DataFrame({
            "system_id": [1, 2, 3],
            "biological_age": ["juvenile", "adult", "elderly"],
            "description_type_id": [1, 1, 1]  # Added via extra_columns
        })
    }


def test_fk_linking_with_extra_columns_constant(sample_project_config, table_store):
    """Test FK linking when local entity has FK column via extra_columns with constant value.
    
    This reproduces the bug: KeyError: 'system_id' during merge because system_id
    was renamed to public_id before the merge, but merge still uses original remote_keys.
    """
    project = ShapeShiftProject(cfg=sample_project_config)
    linker = ForeignKeyLinker(project=project, table_store=table_store)
    
    # This should not raise KeyError: 'system_id'
    deferred = linker.link_entity("sample_description")
    
    assert not deferred, "FK linking should not be deferred"
    
    # Verify the link was successful
    result_df = table_store["sample_description"]
    
    # Should have the FK column (remote public_id)
    assert "sample_description_type_id" in result_df.columns
    
    # All rows should link to type_id = 1 (since description_type_id = 1 for all)
    assert result_df["sample_description_type_id"].notna().all()
    assert (result_df["sample_description_type_id"] == 1).all()


def test_fk_merge_keys_after_rename():
    """Test that merge keys are correctly mapped after column renaming.
    
    When remote_df has system_id renamed to public_id, the merge should use
    the new column name, not the original remote_keys.
    """
    project_config = {
        "metadata": {"name": "test", "version": "1.0"},
        "entities": {
            "parent": {
                "type": "fixed",
                "public_id": "parent_id",
                "keys": [],
                "columns": ["system_id", "parent_id", "name"],
                "values": [[1, None, "Parent A"], [2, None, "Parent B"]]
            },
            "child": {
                "type": "entity",
                "source": "data",
                "public_id": "child_id",
                "columns": ["child_name"],
                "foreign_keys": [{
                    "entity": "parent",
                    "local_keys": ["parent_ref"],
                    "remote_keys": ["system_id"]
                }],
                "extra_columns": {"parent_ref": 1}
            }
        }
    }
    
    table_store = {
        "parent": pd.DataFrame({
            "system_id": [1, 2],
            "parent_id": [None, None],
            "name": ["Parent A", "Parent B"]
        }),
        "child": pd.DataFrame({
            "system_id": [1, 2],
            "child_name": ["Child 1", "Child 2"],
            "parent_ref": [1, 1]
        })
    }
    
    project = ShapeShiftProject(cfg=project_config)
    linker = ForeignKeyLinker(project=project, table_store=table_store)
    
    # Should successfully link without KeyError
    deferred = linker.link_entity("child")
    
    assert not deferred
    result_df = table_store["child"]
    assert "parent_id" in result_df.columns
    assert (result_df["parent_id"] == 1).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
