#!/usr/bin/env python3
"""Quick test to verify unnest value_vars are excluded from validation.

This simulates the scenario from a.tsv where entities like feature_property
have unnest configurations, and columns in value_vars should NOT trigger
COLUMN_NOT_FOUND errors because they're melted during unnest processing.
"""

import pandas as pd
from src.validators.data_validators import ColumnExistsValidator

# Simulate feature_property after unnest (melt already applied)
# Original columns (value_vars): FlSchn, okBefu, BestJa, Anmerkung, gebäud
# After melt: these columns are gone, replaced by var_name/value_name
df_melted = pd.DataFrame({
    "Befu": [1, 1, 1, 1, 1, 2, 2],
    "Projekt": ["P1", "P1", "P1", "P1", "P1", "P2", "P2"],
    "arbodat_code": ["A1", "A1", "A1", "A1", "A1", "A2", "A2"],
    "feature_property_type": ["FlSchn", "okBefu", "BestJa", "Anmerkung", "gebäud", "FlSchn", "okBefu"],
    "feature_property_value": ["Yes", "Good", "2024", "Note", "Building", "No", "Fair"],
})

# Entity configuration (what's in YAML)
entity_config = {
    "columns": [
        "Befu", "Projekt", "arbodat_code",
        # These columns are in value_vars and get melted away:
        "FlSchn", "okBefu", "BestJa", "Anmerkung", "gebäud"
    ],
    "unnest": {
        "id_vars": ["Befu", "Projekt", "arbodat_code"],
        "value_vars": ["FlSchn", "okBefu", "BestJa", "Anmerkung", "gebäud"],
        "var_name": "feature_property_type",
        "value_name": "feature_property_value",
    }
}

print("Testing ColumnExistsValidator with unnest configuration...")
print("\nDataFrame columns (after melt):", list(df_melted.columns))
print("\nConfigured columns:", entity_config["columns"])
print("\nColumns in value_vars (should be excluded):", entity_config["unnest"]["value_vars"])

# OLD BEHAVIOR (without unnest awareness):
# This would create 5 errors for FlSchn, okBefu, BestJa, Anmerkung, gebäud
# Because they're configured but missing from the melted DataFrame

# NEW BEHAVIOR (with unnest awareness):
# Should return NO errors because value_vars columns are excluded from validation
issues = ColumnExistsValidator.validate(
    df_melted,
    entity_config["columns"],
    "feature_property",
    entity_config,
)

print("\n" + "="*80)
if len(issues) == 0:
    print("✅ SUCCESS: No validation errors (value_vars correctly excluded)")
    print("   - id_vars (Befu, Projekt, arbodat_code) are present ✓")
    print("   - value_vars (FlSchn, okBefu, BestJa, Anmerkung, gebäud) excluded from validation ✓")
else:
    print(f"❌ FAILED: {len(issues)} validation errors:")
    for issue in issues:
        print(f"  - {issue.message}")
print("="*80)

# Test missing non-value_vars column
print("\n\nTesting with missing id_var column...")
df_missing_id_var = pd.DataFrame({
    "Projekt": ["P1", "P1"],
    "arbodat_code": ["A1", "A1"],
    "feature_property_type": ["FlSchn", "okBefu"],
    "feature_property_value": ["Yes", "Good"],
})

issues_missing = ColumnExistsValidator.validate(
    df_missing_id_var,
    entity_config["columns"],
    "feature_property",
    entity_config,
)

print("\n" + "="*80)
if len(issues_missing) == 1 and "Befu" in issues_missing[0].message:
    print("✅ SUCCESS: Correctly detects missing id_var 'Befu'")
    print("   - id_var 'Befu' is required and validated ✓")
    print("   - Other id_vars (Projekt, arbodat_code) are present ✓")
    print("   - value_vars are still excluded from validation ✓")
else:
    print(f"❌ FAILED: Expected 1 error for 'Befu', got {len(issues_missing)} errors:")
    for issue in issues_missing:
        print(f"  - {issue.message}")
print("="*80)

# Test with multiple missing id_vars
print("\n\nTesting with multiple missing id_vars...")
df_multiple_missing = pd.DataFrame({
    # All id_vars missing!
    "feature_property_type": ["FlSchn", "okBefu"],
    "feature_property_value": ["Yes", "Good"],
})

issues_multiple = ColumnExistsValidator.validate(
    df_multiple_missing,
    entity_config["columns"],
    "feature_property",
    entity_config,
)

print("\n" + "="*80)
if len(issues_multiple) == 3:
    missing_cols = {issue.message.split("'")[1] for issue in issues_multiple}
    if missing_cols == {"Befu", "Projekt", "arbodat_code"}:
        print("✅ SUCCESS: Correctly detects all missing id_vars")
        print("   - All 3 id_vars (Befu, Projekt, arbodat_code) reported as missing ✓")
        print("   - value_vars (FlSchn, okBefu, BestJa, Anmerkung, gebäud) still excluded ✓")
    else:
        print(f"❌ FAILED: Wrong columns reported: {missing_cols}")
else:
    print(f"❌ FAILED: Expected 3 errors, got {len(issues_multiple)} errors:")
    for issue in issues_multiple:
        print(f"  - {issue.message}")
print("="*80)
