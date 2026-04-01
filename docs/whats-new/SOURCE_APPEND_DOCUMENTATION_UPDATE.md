# Source-Based Append Documentation Update

**Date**: 2025-01-21  
**Related Proposal**: [SOURCE_BASED_APPEND_WITH_POSITION_ALIGNMENT.md](../proposals/SOURCE_BASED_APPEND_WITH_POSITION_ALIGNMENT.md)  
**Implementation**: Step 1 (Fix internal source-append normalization)

## Overview

Updated user-facing documentation to clarify **source-based append** behavior and property inheritance rules following the implementation of loader field blocking in `src/model.py`.

## Problem

The previous documentation did not adequately explain:
1. **Source shorthand form**: Users could use `source: entity` but docs didn't explain this was shorthand for `type: entity, source: entity`
2. **Loader field blocking**: Docs didn't explain that source-based append blocks inheritance of `type`, `values`, `query`, `data_source`, `sql`
3. **Union pattern**: Common pattern of fixed parent with `values: []` + source append was not documented

This led to confusion about why certain properties weren't inherited and how source-based append differs from loader-based append.

## Changes

### 1. CONFIGURATION_GUIDE.md - Data Source Append Section

**Location**: Line ~2185

**Added**:
- Explanation of source shorthand form with example
- Union pattern documentation (fixed parent + source append)
- Important note about loader property non-inheritance

**Example** (new):
```yaml
analysis_entity:
  source: method  # Shorthand for type: entity, source: method
  append:
    - source: sample_type  # Shorthand form
```

### 2. CONFIGURATION_GUIDE.md - Property Inheritance Section

**Location**: Line ~2230

**Added**:
- New subsection "Source-Based Append Loader Blocking"
- Explicit list of blocked properties: `type`, `values`, `query`, `data_source`, `sql`
- Explanation of why blocking is necessary (prevents conflicts)
- Note that safe properties continue to inherit

### 3. AppendEditor.vue - Info Notice

**Location**: Lines 138-153

**Updated**:
- Changed "From Entity" to "From Entity (source)" to emphasize source-based nature
- Added nested bullet list explaining:
  - Shorthand form usage
  - Table_store fetching behavior
  - Non-inheritance of loader properties
- Added note about safe property inheritance

## Benefits

1. **Clearer User Understanding**: Users now understand the difference between source-based and loader-based append
2. **Documented Patterns**: Common union pattern (fixed parent + source append) is now explicitly documented
3. **Shorthand Awareness**: Users can use terser `source: entity` form confidently
4. **Expectation Management**: Clear explanation of what does/doesn't inherit prevents confusion

## Testing

The documentation changes align with the implemented behavior:
- `tests/model/test_append.py`: 5 tests verify loader field blocking
- `tests/integration/test_append_integration.py`: Integration test validates full pipeline
- All 49 tests passing

## Migration Impact

**No breaking changes**. This is documentation-only update clarifying existing behavior after the Step 1 implementation.

## Related Documentation

- [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) - Updated sections: "Data Source Append", "Property Inheritance"
- [SOURCE_BASED_APPEND_WITH_POSITION_ALIGNMENT.md](../proposals/SOURCE_BASED_APPEND_WITH_POSITION_ALIGNMENT.md) - Technical proposal
- [USER_GUIDE.md](../USER_GUIDE.md) - No changes needed (high-level overview only)

## Next Steps

From the proposal:
- ✅ **Step 1**: Fix internal source-append normalization (COMPLETE with docs)
- ⏳ **Step 2**: Align validator behavior with fixed behavior
- ⏳ **Step 3**: Tighten position-based alignment rules in validators
- ⏳ **Step 4**: Add integration tests with filter interactions
- ⏳ **Step 5**: Update editor wording and examples (PARTIAL - info notice updated)

## Summary

This documentation update ensures that users understand the source-based append semantics introduced in Step 1 of the proposal. The union pattern (fixed parent with source append) is now clearly documented as an intentional and supported approach for combining entity data.
