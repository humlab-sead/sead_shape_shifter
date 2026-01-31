# Keys and Columns Configuration Review

## Executive Summary

**Finding**: The current `keys` and `columns` configuration has significant **redundancy and confusion** that creates unnecessary verbosity and user friction.

**Recommendation**: Simplify to a single `columns` property with automatic key inference or explicit key subset designation.

---

## 1. Current Usage in arbodat-test.yml

### Statistics (60 entities analyzed):
- **100% have both keys and columns** fields
- **37 entities (62%)**: keys ⊆ columns (redundancy!)
- **14 entities (23%)**: empty keys `[]`
- **4 entities (7%)**: empty columns `[]` (SQL entities - columns from query)
- **5 entities (8%)**: @value references

### Key Patterns Observed:

**Pattern 1: Complete Redundancy** (Most Common - 37 entities)
```yaml
abundance_element:
  keys: ["RTyp"]
  columns: ["Resttyp", "RTypGrup", "RTypNr", "RTyp"]  # RTyp appears in both!
```

**Pattern 2: Empty Columns (SQL Query)** (4 entities)
```yaml
analysis_entity:
  keys: ["Projekt", "Befu", "ProbNr", "PCODE", ...]
  columns: []  # Columns come from SQL query - keys listed anyway!
  query: select [Projekt], [Befu], [ProbNr], [PCODE], ...
```

**Pattern 3: Empty Keys** (14 entities - fixed/lookup tables)
```yaml
contact_type:
  keys: []
  columns: ["contact_type_code"]
```

**Pattern 4: Reference-Based** (5 entities)
```yaml
abundance:
  keys: '@value: entities.analysis_entity.keys'
  columns: [...]
```

---

## 2. Code Usage Analysis

### Where `keys` is used:

1. **Deduplication** (`src/transforms/drop.py`)
   - `drop_duplicate_rows(data, columns=keys)` - Could use column subset instead
   
2. **Foreign Key Matching** (`src/transforms/link.py`)
   - Matches FK `local_keys` → `remote_keys` via business keys
   - **Critical**: FK logic doesn't require separate `keys` field
   
3. **Validation** (`backend/app/validators/data_validators.py`)
   - `DuplicateKeysValidator`: Checks keys are unique
   - `NaturalKeyUniquenessValidator`: Validates key uniqueness
   - **Could validate**: "primary key columns should be unique"
   
4. **Data Quality** (`src/specifications/fd.py`)
   - Functional dependency validation
   - Checks if non-key columns depend on keys

5. **UI/Display** (`src/model.py`)
   - `keys_and_columns` property: Orders keys first
   - Used for display ordering

### Where `columns` is used:

1. **Data Extraction** (all loaders)
   - SQL: `SELECT {columns} FROM ...` or empty for `SELECT *`
   - CSV/Excel: Which columns to read
   - Fixed: Column definitions for value matrix

2. **Schema Definition**
   - Defines what data exists after extraction
   - Used for validation, FK matching, transforms

---

## 3. Consistency Issues

### Issue 1: Duplicate Information (62% of entities)
```yaml
# User must maintain keys in TWO places:
sample:
  keys: ["sample_code"]
  columns: ["sample_code", "sample_name", "depth"]  # sample_code AGAIN!
```

**Problem**: Keys that identify the entity must be listed in both `keys` AND `columns`. This is error-prone and verbose.

### Issue 2: Semantic Confusion
**Q**: What's the difference between `keys` and `columns`?
**A** (current): 
- `keys` = business identifiers for deduplication/FK matching
- `columns` = what to extract from source

**But**: Users expect:
- `columns` = "all columns in my data"
- `keys` = "subset of columns that uniquely identify rows"

**Reality**: They have to list key columns twice.

### Issue 3: Empty Columns Pattern
```yaml
# SQL entity - columns inferred from query
analysis_entity:
  keys: ["Projekt", "Befu", ...]  # Listed explicitly
  columns: []                      # But columns are implicit!
  query: select [Projekt], [Befu], ...  # Keys are in the query!
```

**Problem**: When `columns: []`, the keys are still extracted (they're in the SQL). Why list them separately?

### Issue 4: Validation Ambiguity

Current validation: `keys ⊆ columns` (when columns non-empty)

**Edge Cases**:
- Empty columns (SQL): Keys NOT validated against columns
- Unnest operations: Keys created by transforms (e.g., `feature_property_type`)
- @value references: Validation skipped until resolution

**Problem**: The validation rules have many exceptions, suggesting the model is wrong.

---

## 4. User Perspective Analysis

### Current User Mental Model (Confusing):
1. "I need to list the columns to extract" → `columns`
2. "I need to specify business keys separately" → `keys`
3. "Do I list business keys in columns too?" → **YES** (?!)
4. "Why am I duplicating information?"

### Desired User Mental Model (Simple):
1. "I need to list the columns to extract" → `columns`
2. "Some columns are primary keys" → Mark them somehow
3. Done!

### Current Verbosity Examples:

**Example 1**: Simple entity with single key
```yaml
# Current: 2 lines, 2 mentions of "site_code"
site:
  keys: ["site_code"]
  columns: ["site_code", "site_name", "location"]
  
# Could be: 1 line, columns only
site:
  columns: 
    - site_code: {primary_key: true}
    - site_name
    - location
```

**Example 2**: Composite key
```yaml
# Current: 10 lines, keys repeated
analysis_entity:
  keys: ["Projekt", "Befu", "ProbNr", "PCODE", "Fraktion", "cf", "RTyp", "Zust"]
  columns:
    - Projekt
    - Befu
    - ProbNr
    - PCODE
    - Fraktion
    - cf
    - RTyp
    - Zust
    
# Could be: Mark keys inline or use simplified notation
analysis_entity:
  columns: ["Projekt*", "Befu*", "ProbNr*", "PCODE*", "Fraktion*", "cf*", "RTyp*", "Zust*"]
  # Or
  primary_key: ["Projekt", "Befu", "ProbNr", "PCODE", "Fraktion", "cf", "RTyp", "Zust"]
  columns: [...]  # All columns including keys
```

---

## 5. Recommendations

### Option A: Single `columns` Property with Metadata (Best UX)

```yaml
# Simple list - no keys needed for lookup tables
contact_type:
  columns: ["contact_type_code", "description"]

# Mark primary key columns inline
site:
  columns:
    - site_code: {key: true}  # or {pk: true}
    - site_name
    - location
    
# Or use simpler notation
site:
  primary_key: ["site_code"]
  columns: ["site_code", "site_name", "location"]  # Include ALL columns
```

**Pros**:
- Eliminates redundancy
- Single source of truth
- Clear semantic meaning
- Backward compatible (migrate `keys` → `primary_key`)

**Cons**:
- Requires migration of existing configs
- Need to support both styles during transition

### Option B: Keep Both, But Make `keys` Optional Subset (Current + Enhancement)

```yaml
# Keys inferred from context when omitted
site:
  columns: ["site_code", "site_name", "location"]
  # keys automatically: first column OR all columns OR validation warning

# Explicit keys when needed for deduplication/FKs
site:
  columns: ["site_code", "site_name", "location"]
  keys: ["site_code"]  # Explicit subset for FK matching
```

**Pros**:
- Less breaking change
- Maintains current semantics
- Allows gradual migration

**Cons**:
- Still has redundancy
- Ambiguity when keys omitted

### Option C: Separate Concerns - Extract vs. Schema (Most Precise)

```yaml
site:
  # What to extract from source
  select: ["site_code", "site_name", "location"]
  
  # Schema metadata
  schema:
    primary_key: ["site_code"]
    unique_constraints: [["site_name"]]
    
# OR for SQL entities:
analysis_entity:
  query: SELECT * FROM analysis  # Columns implicit
  schema:
    primary_key: ["Projekt", "Befu", ...]
```

**Pros**:
- Clear separation of extraction vs. schema
- Supports rich schema metadata
- Professional data modeling approach

**Cons**:
- More complex
- Bigger breaking change
- May be over-engineering

---

## 6. Proposed Changes (Recommendation: Option A)

### Phase 1: Add `primary_key` Alias (No Breaking Changes)

```python
# src/model.py - TableConfig
@cached_property
def keys(self) -> list[str]:
    """Business keys - supports both 'keys' and 'primary_key' names."""
    return self.entity_cfg.get("primary_key") or self.entity_cfg.get("keys") or []
```

**Benefits**:
- Clearer semantic name
- Backward compatible
- Allows gradual migration

### Phase 2: Relax Validation (Remove Keys ⊆ Columns Requirement)

**Current Problem**: We just added validation that `keys ⊆ columns`, but this creates issues:
- SQL entities with `columns: []` → keys not validated
- Transform-created columns → false positives
- Redundancy encouragement

**Proposed**: 
- Remove the `KeysSubsetOfColumnsValidator` we just added
- Instead: Validate at runtime when keys are actually needed
- Warning (not error) if keys not in extracted data

### Phase 3: Documentation Updates

1. Clarify `keys` vs `columns` purpose
2. Show best practices:
   - List keys in both places (current requirement)
   - Or use `primary_key` + `columns` separately
3. Explain empty `columns` pattern for SQL

### Phase 4: Optional - Support Column Metadata

```yaml
# Future enhancement
site:
  columns:
    - site_code: {primary_key: true, type: string}
    - site_name: {nullable: false}
    - location
```

---

## 7. Conclusion

### Current State: 
- **62% redundancy** (keys listed in both places)
- **Confusing semantics** (keys vs columns)
- **Verbose configuration** (duplicate maintenance)

### Root Cause:
The system conflates two concerns:
1. **What to extract** (`columns`)
2. **What identifies uniqueness** (`keys`)

These SHOULD be related (keys are usually a subset of columns), but the current model makes users maintain them independently.

### Recommended Path Forward:

**Short Term** (Low Risk):
1. ✅ Add `primary_key` as alias for `keys`
2. ✅ Update documentation to clarify relationship
3. ✅ Add examples showing both patterns

**Medium Term** (After feedback):
1. ⚠️ **Reconsider** the `keys ⊆ columns` validation we just added
   - It may be too strict given edge cases (empty columns, transforms, @value refs)
   - Better: runtime validation when keys are actually used
2. Support omitting `columns` more broadly (infer from query/file)
3. Support omitting `keys` when not needed (lookup tables)

**Long Term** (Future Enhancement):
1. Rich column metadata (types, constraints, PK marking)
2. Schema-first design (DDL-like syntax)
3. Automatic key inference from data patterns

---

## Appendix: Breaking Down the 62% Redundancy

Out of 60 entities:
- **37 have keys ⊆ columns** (must list keys twice)
- **14 have empty keys** (no redundancy, but could auto-infer)
- **5 use @value references** (indirection, still potential redundancy)
- **4 have empty columns** (SQL query defines schema, keys separate)

**Only 4 entities** truly benefit from separate keys/columns (SQL with empty columns).

**56 entities** (93%) would be clearer with a unified or inferred approach.
