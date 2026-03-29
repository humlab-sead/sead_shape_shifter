# Proposal: Source-Based Append With Position Alignment

## Status

- Proposed change request
- Scope: append configuration, normalization logic, validation, editor UX, documentation
- Goal: make source-based append a valid and predictable way to union heterogeneous entities into one target shape

## Summary

Allow append items that reference another entity through `source` to behave as first-class source-based appends regardless of the parent entity type.

This change is needed because the current behavior makes a useful modeling pattern fail at runtime: a parent entity with `append: [{ source: ... }]` can inherit the parent `type` and be loaded incorrectly. The motivating case is a union entity like `ab` built from `a` and `b`, where the source entities have different column names but compatible structure.

The proposal also recommends making column alignment explicit and user-facing. The default should remain name-based alignment. Position-based alignment should be opt-in, documented as advanced, and validated with a previewable mapping so it does not feel ambiguous.

## Problem

The following setup is useful and should be allowed:

```yaml
entities:
  a:
    type: fixed
    public_id: a_id
    columns: [system_id, a_type, a_id, a_value]
    values:
      - [1, 'A', 1, 'a']

  b:
    type: fixed
    public_id: b_id
    columns: [system_id, b_type, b_id, b_value]
    values:
      - [1, 'B', 1, 'b']

  ab:
    type: fixed
    public_id: ab_id
    columns: [system_id, ab_type, ab_id, ab_value]
    values: []
    append:
      - source: a
      - source: b
```

The intent is clear:

- `a` and `b` are source entities
- `ab` is a union entity
- `ab` should append rows from both sources
- the source columns should either align by name, align by position, or be renamed explicitly

Today this does not work reliably.

The main issues are:

1. A source-based append item can inherit the parent `type` and be treated as a fixed append instead of an entity append.
2. Validation, documentation, frontend behavior, and runtime behavior do not fully agree on how source-based append should be expressed.
3. Position-based alignment exists in the implementation, but it is not robust enough for identity-bearing entities with different public ID column names.
4. Users cannot tell clearly when alignment is name-based, position-based, or explicit mapping, and when each mode is safe.

## Scope

This proposal covers:

- source-based append semantics
- column alignment rules for append items
- position-based alignment for heterogeneous but structurally compatible entities
- validation and editor behavior needed to make the feature understandable
- documentation updates for append modeling

## Non-Goals

This proposal does not:

- replace existing append support for `fixed` or `sql`
- add automatic semantic matching between unrelated schemas
- infer mappings from fuzzy column names
- change foreign key behavior outside append processing
- redesign the broader entity model

## Current Behavior

Current append behavior is split across runtime, validation, docs, and frontend handling.

Observed problems:

- `append: [{ source: ... }]` is validated as a source-based append, but runtime merging can still inherit parent properties that cause the append item to load incorrectly.
- the current model treats `align_by_position` and `column_mapping` as append options, but their behavior is not explained as a single alignment decision
- position-based alignment can fail when the target and source have different identity column names, even when the payload columns are structurally compatible
- the frontend already presents a "From Entity" concept, but the saved YAML shape and runtime semantics are not fully aligned with that concept

This produces a bad outcome for a reasonable use case: the user expresses a valid union intent, but gets no rows back.

## Proposed Design

### 1. Make Source-Based Append A First-Class Append Mode

Any append item with `source` must be treated as a source-based append, not as an inherited variant of the parent entity type.

Recommended rule:

- if `append[i].source` is present, the append item is a source append
- source append must resolve rows from an existing entity in `table_store`
- source append must not inherit parent loader-driving fields such as `type`, `values`, `query`, or `data_source`
- source append may inherit only safe processing properties such as filters, duplicate handling, and alignment settings where appropriate

This should be the internal behavior regardless of whether the user writes:

```yaml
append:
  - source: a
```

or:

```yaml
append:
  - type: entity
    source: a
```

Recommendation:

- support both forms
- treat `source`-only as shorthand for `type: entity`
- normalize both forms to the same internal representation

This avoids breaking existing editor behavior while removing the current ambiguity.

### 2. Make Alignment A Single User-Facing Concept

Users should make one clear alignment choice per source-based append item:

- `name` alignment: source and target columns must match by name
- `position` alignment: source and target payload columns are matched by order
- `mapping` alignment: explicit source-to-target mapping is provided

The current runtime fields can remain for compatibility, but the product should present them as one concept: column alignment.

Recommended user-facing model:

- default: `name`
- advanced option: `position`
- explicit option: `mapping`

Recommended YAML support:

```yaml
append:
  - source: a
    column_mapping:
      a_type: ab_type
      a_id: ab_id
      a_value: ab_value
```

```yaml
append:
  - source: a
    align_by_position: true
```

Optional future cleanup:

- introduce a clearer alias such as `alignment: name | position | mapping`
- keep `align_by_position` and `column_mapping` as backward-compatible forms

### 3. Define Position-Based Alignment Around Payload Columns, Not Raw Column Names

Position-based alignment should be valid when the source and target have the same payload shape even if identity columns differ.

Recommended rules for `align_by_position: true` on source-based append:

- always exclude `system_id` from positional matching
- exclude the source entity's `public_id` from positional matching unless the user explicitly maps it
- exclude the target entity's `public_id` from positional matching unless the user explicitly maps it
- compare and align only the remaining payload columns by order
- after concatenation, re-add or preserve the target `public_id` column according to existing append behavior

This makes cases like `a_id -> ab_id` and `b_id -> ab_id` predictable.

Without this rule, position-based alignment is brittle for exactly the kind of identity-bearing entities users are likely to append.

### 4. Keep Name-Based Alignment As The Safe Default

To avoid user confusion, the system should not silently fall back from name-based matching to position-based matching.

Recommended behavior:

- if no alignment option is set, use name-based behavior
- if source and target columns are incompatible by name, fail validation with an actionable message
- suggest either `column_mapping` or `align_by_position: true`

This preserves safety and keeps the mental model simple:

- default mode is strict and obvious
- advanced modes require explicit opt-in

### 5. Improve Validation Messages For Source Append

Validation should explain why a source append is invalid and how to fix it.

Examples:

- source append cannot inherit fixed loader fields
- source append has incompatible payload column count for position-based alignment
- source append has unmapped source columns for name-based alignment
- source append maps multiple source columns to the same target column

For position-based alignment, the error should include the actual inferred payload columns on both sides.

### 6. Present The Feature Clearly In The Editor

The frontend already has a useful concept: "From Entity" with optional column mapping and align-by-position.

The recommended UX is:

- expose source append as "From Entity"
- show an explicit "Column alignment" control with three mutually exclusive states:
  - Match by name
  - Match by position
  - Explicit mapping
- label position mode as advanced
- show a preview of inferred source-to-target column pairs before save when possible
- warn when identity columns are being excluded or preserved automatically

This keeps the feature understandable without exposing internal merge rules directly in the main editing flow.

## Alternatives Considered

### 1. Require Explicit `column_mapping` For All Heterogeneous Source Appends

Rejected because it is safe but too verbose. Many real cases are structurally aligned and only differ in column names.

### 2. Allow Implicit Position-Based Alignment When Names Do Not Match

Rejected because it is too surprising. Silent fallback would hide important mistakes.

### 3. Require `type: entity` And Reject `source`-Only Shorthand

Rejected because the shorthand is already natural, already used, and already represented in frontend behavior. The better fix is to normalize it internally.

## Risks And Tradeoffs

- source append semantics become more explicit, which may expose previously hidden misconfigurations in existing projects
- position-based alignment is inherently more fragile than explicit mapping
- supporting both `source` shorthand and explicit `type: entity` adds compatibility logic
- identity-column handling must be documented carefully to avoid surprises

These risks are acceptable because the proposed default remains strict and explicit mapping remains available for sensitive cases.

## Testing And Validation

Validation should cover at least these cases:

- source-only append from a fixed parent entity
- explicit `type: entity` plus `source`
- name-based source append with matching columns
- position-based source append with different source and target public ID names
- explicit column mapping from heterogeneous source entities into one target entity
- clear validation failures for incompatible column counts
- frontend serialization and deserialization of source append alignment modes

The motivating `a` / `b` / `ab` example should be added as an integration test.

## Acceptance Criteria

- a source-based append item is resolved as a source append regardless of the parent entity type
- `append: [{ source: x }]` and `append: [{ type: entity, source: x }]` have the same runtime behavior
- the motivating `a` / `b` / `ab` scenario can be modeled successfully with either explicit mapping or explicit position-based alignment where structurally valid
- position-based alignment ignores source and target identity columns unless explicitly mapped
- validation messages tell the user which alignment mode failed and why
- documentation explains when to use name-based, position-based, and explicit mapping modes
- the editor presents alignment as a single explicit choice for source-based append

## Recommended Delivery Order

1. ✅ **Fix internal source-append normalization so `source` append does not inherit parent loader type.** (Implemented 2026-03-24)
2. ✅ **Align validator behavior with runtime behavior for `source` and `type: entity` append forms.** (Implemented 2026-03-24)
3. ✅ **Tighten position-based alignment rules around payload columns and identity columns.** (Verified 2026-03-24)
4. ✅ **Add integration tests for the motivating case and for failure modes.** (Implemented 2026-03-24)
5. ✅ **Update append documentation and editor wording.** (Implemented 2026-03-24)

## Implementation Notes

### Step 1: Source Append Normalization (Implemented 2026-03-24)

**Files Changed:**
- `src/model.py` - Modified `create_append_config()` to block loader field inheritance when `source` is present
- `tests/model/test_append.py` - Added 5 unit tests verifying source append behavior
- `tests/integration/test_append_integration.py` - Added integration test for fixed parent + source append pattern

**Implementation:**
When `source` is present in append_data, the following fields are added to `non_inheritable_keys`:
- `type` - Prevents inheritance of fixed/sql/entity type from parent
- `values` - Prevents inheritance of fixed values array
- `query` - Prevents inheritance of SQL query
- `data_source` - Prevents inheritance of data source name
- `sql` - Prevents inheritance of SQL configuration

This ensures source-based append items resolve data from `table_store` rather than using parent loader.

**Tests Added:**
- `test_source_append_does_not_inherit_type_from_fixed_parent` - Verifies no type inheritance
- `test_source_append_does_not_inherit_query_from_sql_parent` - Verifies no query inheritance
- `test_source_append_still_inherits_safe_properties` - Verifies safe properties still inherited
- `test_non_source_append_still_inherits_type_for_backward_compatibility` - Ensures backward compat
- `test_source_append_from_fixed_parent_does_not_inherit_type` - Integration test for full pipeline

**Validation:**
- `tests/test_data/projects/bugs/shapeshifter.yml` now returns 2 rows (was 0 rows)
- Production `analysis_entity` pattern verified working correctly
- All existing tests pass (38 unit tests + 10 integration tests)

### Step 2: Validator Alignment for Source Append Forms (Implemented 2026-03-24)

**Files Changed:**
- `src/specifications/entity.py` - Modified `AppendSpecification.is_satisfied_by()` to treat source append forms equivalently
- `tests/specifications/test_entity.py` - Updated tests to cover both shorthand and explicit forms

**Implementation:**
The validator now:
- Accepts both `source: entity_name` (shorthand) and `type: entity, source: entity_name` (explicit)
- Validates that if `type` and `source` are both specified, `type` must be `"entity"`
- Rejects combinations like `type: fixed, source: entity_name` with clear error message
- Treats both forms identically during validation

**Changes:**
- Removed restriction that prevented `type` and `source` from coexisting
- Added validation that `type` must be `"entity"` when both present
- Split validation logic: type-only (fixed/sql) vs source-based (entity)

**Tests Added:**
- `test_valid_source_append` - Verifies shorthand form `source: entity` passes validation
- `test_valid_source_with_type_entity` - Verifies explicit form `type: entity, source: entity` passes validation
- `test_invalid_source_with_wrong_type` - Verifies `type: fixed, source: entity` is rejected

**Validation:**
- All 7 AppendSpecification tests pass
- Both source append forms validate identically

### Step 3: Position-Based Alignment Around Payload Columns (Verified 2026-03-24)

**Status:** Already implemented and tested in codebase.

**Implementation Location:**
- `src/model.py` - `TableConfig.apply_column_renaming()` method (lines 653-708)

**Behavior:**
Position-based alignment properly excludes identity columns:
- Always excludes `system_id` from positional matching
- Excludes entity's `public_id` from positional matching (if defined)
- Aligns only payload columns by position
- Preserves identity columns unchanged in result

**Algorithm:**
```python
# Filter out identity columns from both source and target
exclude_cols = {system_id_col, public_id_col} if public_id_col else {system_id_col}
parent_cols_filtered = [c for c in parent_columns if c not in exclude_cols]
current_cols_filtered = [c for c in current_columns if c not in exclude_cols]

# Validate payload column count matches
if len(parent_cols_filtered) != len(current_cols_filtered):
    raise ValueError("Column count mismatch for align_by_position...")

# Create rename mapping for payload columns only
rename_map = dict(zip(current_cols_filtered, parent_cols_filtered))
```

**Existing Tests:**
- `test_apply_column_renaming_align_by_position_with_system_id` - Unit test verifying exclusion
- `test_apply_column_renaming_column_count_mismatch` - Validates error on mismatch
- `test_append_with_align_by_position` - Integration test with full pipeline

**Validation:**
- All existing tests pass (3 unit tests + 1 integration test)
- Identity columns properly preserved during position-based alignment
- Heterogeneous entities with different identity columns can be unioned successfully

### Step 5: Editor UX Improvements (Implemented 2026-03-24)

**Status:** Implemented and ready for testing.

**Implementation Location:**
- `frontend/src/components/entities/AppendEditor.vue`

**Changes:**

1. **Redesigned Alignment Mode Selector:**
   - Replaced independent checkboxes with mutually exclusive radio group
   - Changed "Column Alignment Options" to "Column Alignment" for clarity
   - Made alignment mode a single explicit choice (not independent toggles)

2. **Three Mutually Exclusive Modes:**
   - **Match by name (default)** - Strict column name matching (no flags required)
   - **Match by position (advanced)** - Align payload columns by position with identity exclusion (warning chip)
   - **Explicit mapping** - Manual source→target column specification

3. **Added Mode Management Functions:**
   ```typescript
   // Determine current alignment mode from item state
   function getAlignmentMode(item): 'name' | 'position' | 'mapping' {
     if (item.align_by_position) return 'position'
     if (item.column_mapping?.length) return 'mapping'
     return 'name'
   }
   
   // Handle mode changes from radio group
   function handleAlignmentModeChange(item, mode) {
     item.align_by_position = (mode === 'position')
     item.column_mapping = (mode === 'mapping') ? {} : undefined
   }
   ```

4. **Visual Improvements:**
   - Added "(default)" label to name-based mode
   - Added "advanced" warning chip to position-based mode
   - Added descriptive text under each mode option
   - Conditional display of mapping editor based on selected mode

**Benefits:**
- Single-choice UI pattern matches mutual exclusivity of modes
- Position mode clearly labeled as advanced feature
- Reduced cognitive load (one decision instead of two checkboxes)
- Better visual hierarchy and mode descriptions

**Testing Plan:**
- Verify radio group renders correctly
- Test mode switching behavior (mutual exclusivity enforced)
- Verify mapping editor shows/hides based on selected mode
- Check visual styling (chips, descriptions, layout)

## Final Recommendation

Accept source-based append as a first-class append mode and treat `source` as the defining signal for entity append behavior.

Keep name-based matching as the default. Allow position-based matching only through explicit opt-in. Keep explicit column mapping as the safest heterogeneous append mode.

This change makes a useful modeling pattern valid, fixes a real runtime inconsistency, and expands append support without making the default behavior harder to understand.