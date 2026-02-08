#!/usr/bin/env python3
"""Standalone script to debug the duplicate column bug.

This reproduces the exact scenario from the arbodat-copy project where:
- master_dataset has public_id="master_dataset_id" 
- master_dataset also has "master_dataset_id" as a column in values
- Linking to master_dataset creates duplicate columns

Run this to see the bug and the fix in action.
"""

import pandas as pd
from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig

print("=" * 80)
print("DUPLICATE COLUMN BUG DEMONSTRATION")
print("=" * 80)

# Create the project config matching arbodat-copy
project_cfg = {
    "entities": {
        "dataset": {
            "public_id": "dataset_id",
            "columns": ["Projekt", "Fraktion"],
            "foreign_keys": [
                {
                    "entity": "master_dataset",
                    "local_keys": ["master_set_id"],
                    "remote_keys": ["master_dataset_id"],
                }
            ],
            "extra_columns": {"master_set_id": 1},
        },
        "master_dataset": {
            "type": "fixed",
            "public_id": "master_dataset_id",
            "columns": ["master_dataset_id", "master_name"],
            "values": [[1, "ArboDat Pilot"]],
        },
    }
}

project = ShapeShiftProject(cfg=project_cfg)

# Create the dataframes
local_df = pd.DataFrame(
    {
        "system_id": [1, 2],
        "Projekt": ["18_0025", "18_0025"],
        "Fraktion": ["ORG 0,5", "Trocken"],
        "master_set_id": [1, 1],  # Already set via extra_columns
    }
)

remote_df = pd.DataFrame(
    {
        "system_id": [1],
        "master_dataset_id": [1],  # This is the problem!
        "master_name": ["ArboDat Pilot"],
    }
)

print("\n1. LOCAL DATAFRAME (dataset):")
print(local_df)
print(f"\nColumns: {local_df.columns.tolist()}")

print("\n2. REMOTE DATAFRAME (master_dataset):")
print(remote_df)
print(f"\nColumns: {remote_df.columns.tolist()}")

# Get the FK config
dataset_cfg = project.get_table("dataset")
fk = dataset_cfg.foreign_keys[0]
remote_cfg: TableConfig = project.get_table("master_dataset")

print(f"\n3. FK CONFIGURATION:")
print(f"   Foreign Key: {fk.local_entity} -> {fk.remote_entity}")
print(f"   Local keys: {fk.local_keys}")
print(f"   Remote keys: {fk.remote_keys}")
print(f"   Remote public_id: {remote_cfg.public_id}")
print(f"   Remote system_id: {remote_cfg.system_id}")

# Demonstrate the bug
print("\n" + "=" * 80)
print("OLD APPROACH (CAUSES BUG):")
print("=" * 80)

try:
    renames = {remote_cfg.system_id: remote_cfg.public_id}
    print(f"\nRenames: {renames}")
    
    # Old code: select ALL columns including ones that will be renamed
    remote_extra_cols = fk.get_valid_remote_columns(remote_df.columns.tolist())
    print(f"Remote extra columns: {remote_extra_cols}")
    
    cols_to_select = [remote_cfg.system_id] + remote_extra_cols
    print(f"Columns to select: {cols_to_select}")
    
    # This creates duplicate columns!
    bad_remote_df = remote_df[cols_to_select].rename(columns=renames)
    print(f"\nAfter rename, columns: {bad_remote_df.columns.tolist()}")
    print(bad_remote_df)
    
    # Now try to merge - this will fail
    result = local_df.merge(
        bad_remote_df,
        left_on=["master_set_id"],
        right_on=["master_dataset_id"],
        how="inner",
    )
    print("\nMerge succeeded (unexpected!)")
    
except ValueError as e:
    print(f"\n❌ MERGE FAILED: {e}")
    print("   This is the bug from the log file!")

# Demonstrate the fix
print("\n" + "=" * 80)
print("NEW APPROACH (FIX):")
print("=" * 80)

try:
    renames = {remote_cfg.system_id: remote_cfg.public_id}
    print(f"\nRenames: {renames}")
    
    remote_extra_cols = fk.get_valid_remote_columns(remote_df.columns.tolist())
    print(f"Remote extra columns: {remote_extra_cols}")
    
    # NEW: Filter out columns that would be created by rename
    cols_to_select = [col for col in remote_extra_cols if col not in renames.values()]
    print(f"Columns to select (filtered): {cols_to_select}")
    print(f"⚠️  This is WRONG - filters all rename targets, even identity renames!")
    
    final_cols = [remote_cfg.system_id] + cols_to_select
    print(f"Final columns to select: {final_cols}")
    
    # This works!
    good_remote_df = remote_df[final_cols].rename(columns=renames)
    print(f"\nAfter rename, columns: {good_remote_df.columns.tolist()}")
    print(good_remote_df)
    
    # Now merge works
    result = local_df.merge(
        good_remote_df,
        left_on=["master_set_id"],
        right_on=["master_dataset_id"],
        how="inner",
    )
    print("\n✅ MERGE SUCCEEDED!")
    print("\nResult:")
    print(result)
    print(f"\nFinal columns: {result.columns.tolist()}")

except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")

# Demonstrate the even better fix
print("\n" + "=" * 80)
print("IMPROVED FIX (ALLOW IDENTITY RENAMES):")
print("=" * 80)

try:
    renames = {remote_cfg.system_id: remote_cfg.public_id}
    print(f"\nRenames: {renames}")
    
    remote_extra_cols = fk.get_valid_remote_columns(remote_df.columns.tolist())
    print(f"Remote extra columns: {remote_extra_cols}")
    
    # IMPROVED: Only filter non-identity renames
    rename_targets = {target for source, target in renames.items() if source != target}
    print(f"Non-identity rename targets: {rename_targets}")
    
    cols_to_select = [col for col in remote_extra_cols if col not in rename_targets]
    print(f"Columns to select (filtered): {cols_to_select}")
    
    final_cols = [remote_cfg.system_id] + cols_to_select
    print(f"Final columns to select: {final_cols}")
    
    # This works!
    best_remote_df = remote_df[final_cols].rename(columns=renames)
    print(f"\nAfter rename, columns: {best_remote_df.columns.tolist()}")
    print(best_remote_df)
    
    # Now merge works
    result = local_df.merge(
        best_remote_df,
        left_on=["master_set_id"],
        right_on=["master_dataset_id"],
        how="inner",
    )
    print("\n✅ MERGE SUCCEEDED!")
    print("\nResult:")
    print(result)
    
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")

# Demonstrate identity rename case
print("\n" + "=" * 80)
print("IDENTITY RENAME TEST:")
print("=" * 80)
print("""
What if we have extra_columns with identity renames like {'name': 'name'}?
The improved fix should allow these through!
""")

test_remote = pd.DataFrame({
    "system_id": [1, 2],
    "remote_id": [10, 20],
    "name": ["A", "B"],
    "value": [100, 200],
})

test_renames = {"system_id": "remote_id", "name": "name"}  # Mix of real + identity
test_extra = ["remote_id", "name", "value"]

print("Renames:", test_renames)
print("Extra columns:", test_extra)

# Old approach (bad)
old_targets = test_renames.values()
old_filtered = [col for col in test_extra if col not in old_targets]
print(f"\nOld filter (wrong): {old_filtered}")
print(f"  → Removes 'name' even though it's identity rename!")

# New approach (good)
new_targets = {target for source, target in test_renames.items() if source != target}
new_filtered = [col for col in test_extra if col not in new_targets]
print(f"\nNew filter (correct): {new_filtered}")
print(f"  → Keeps 'name' because it's identity rename ✓")
print(f"  → Only removes 'remote_id' because system_id->remote_id creates it ✓")

# Demonstrate alternative approach
print("\n" + "=" * 80)
print("ALTERNATIVE APPROACH (SKIP IF COLUMNS EXIST):")
print("=" * 80)

# Add master_dataset_id to local df (simulating it already exists)
local_with_fk = local_df.copy()
local_with_fk["master_dataset_id"] = 1

print("\nLocal dataframe WITH master_dataset_id already present:")
print(local_with_fk)

# Check if all columns to be added already exist
columns_to_add = [remote_cfg.public_id] + list(fk.resolved_extra_columns().values())
print(f"\nColumns that would be added: {columns_to_add}")

if all(col in local_with_fk.columns for col in columns_to_add):
    print("\n✅ All FK columns already exist - SKIP MERGE")
    result = local_with_fk
    print("\nResult (unchanged local df):")
    print(result)
else:
    print("\n⚠️  Some columns missing - PERFORM MERGE")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
The bug occurs when:
  1. Remote entity has public_id as a column name (master_dataset_id)
  2. Code tries to select [system_id, master_dataset_id] from remote
  3. Then renames system_id → master_dataset_id
  4. This creates TWO columns named "master_dataset_id"
  5. pandas.merge() fails with "column label is not unique"

Current fix (IMPROVED):
  - Build set of non-identity rename targets: {target for src, tgt in renames if src != tgt}
  - Filter out columns from selection if they're non-identity rename targets
  - This allows identity renames like {'name': 'name'} to pass through
  - Example: For {'system_id': 'master_dataset_id', 'name': 'name'}
    → Only filter 'master_dataset_id', keep 'name'
  
Alternative approach:
  - Check if FK columns already exist in local df
  - If yes, skip the entire merge operation
  - More efficient and explicit for the "FK for graph visibility only" use case
""")
