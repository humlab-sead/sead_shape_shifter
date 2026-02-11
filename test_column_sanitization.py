#!/usr/bin/env python3
"""Test column name sanitization with real-world Excel column names."""

from src.loaders.excel_loaders import sanitize_columns

# Example columns from user's Excel file
test_columns = [
    "Map Fig. 1",
    "Element",
    "Biological Age",
    "Site",
    "Lab nr",
    "BP",
    "±",
    "δ13C",
    "R(t)",
    "±",  # Duplicate
    "from 1σ",
    "to 1σ",
    "from 2σ",
    "to 2σ",
    "Source",
    "Column1",
]

print("Testing column name sanitization:")
print("=" * 80)

result = sanitize_columns(test_columns)

for original, sanitized in zip(test_columns, result):
    print(f"{original:20} → {sanitized}")

print("\n" + "=" * 80)
print(f"All names unique: {len(result) == len(set(result))}")
print(f"All names YAML-friendly: {all(name.replace('_', '').isalnum() for name in result)}")
print(f"No consecutive underscores: {all('__' not in name for name in result)}")
print(f"No leading/trailing underscores: {all(not name.startswith('_') and not name.endswith('_') for name in result)}")
