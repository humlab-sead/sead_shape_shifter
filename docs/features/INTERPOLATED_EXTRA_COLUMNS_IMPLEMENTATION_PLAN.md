# Implementation Plan: Interpolated String Support in Extra Columns (Phase 1)

**Feature**: Add support for interpolated strings like `"{first_name} {last_name}"` in `extra_columns` configuration.

**Issue**: TODO #67 / Related to TODO #108  
**Priority**: High Value, Medium Complexity  
**Estimated Effort**: 4-6 days  

---

## 1. Overview

### Current Behavior
```yaml
extra_columns:
  new_col: existing_col  # Copy column
  constant: "literal"     # Constant value
```

### New Behavior (Phase 1)
```yaml
extra_columns:
  # Existing patterns (unchanged)
  parent_id: child_id           # Column copy
  record_type: "14"             # Constant
  
  # NEW: Interpolated strings
  fullname: "{first_name} {last_name}"
  location: "{city}, {country}"
  email: "{username}@example.com"
  
  # With FK columns from linked entities
  site_info: "{site_name} ({location_name})"  # location_name added by FK
```

### Key Architectural Requirement ⭐

**Multi-Stage Evaluation**: Extra columns must be evaluated **idempotently** at multiple stages:

1. **Extract Phase** (current): Evaluate constants, column copies, and interpolations using **source columns**
2. **Post-FK Link Phase** (new): Re-evaluate deferred interpolations using **FK-added columns**

**Why?**
- **Common case**: Constant FK columns must exist BEFORE linking (e.g., `description_type_id: 1` used as FK local_key)
- **Advanced case**: Interpolations can reference columns added by previous FKs (e.g., `"{site_name} ({location_name})"` where `location_name` is from FK)

---

## 2. Architecture Design

### 2.1 Processing Pipeline Integration

```
┌─────────────┐
│  Extract    │ → Evaluate extra_columns (Pass 1)
└─────────────┘    - Constants
                   - Column copies
                   - Interpolations with available columns
                   - Mark deferred: interpolations with missing columns
       ↓
┌─────────────┐
│  Filter     │
└─────────────┘
       ↓
┌─────────────┐
│  Link FK    │ → Adds columns from remote tables
└─────────────┘
       ↓
┌─────────────┐
│ Re-evaluate │ → Evaluate deferred extra_columns (Pass 2)
│ Extra Cols  │    - Interpolations now have FK columns available
└─────────────┘
       ↓
┌─────────────┐
│  Unnest     │
└─────────────┘
```

### 2.2 Component Architecture

```python
# New module: src/transforms/extra_columns.py

class ExtraColumnEvaluator:
    """Evaluates extra_columns with support for interpolated strings."""
    
    @staticmethod
    def is_interpolated_string(value: Any) -> bool:
        """Detect if value contains {column_name} patterns."""
    
    @staticmethod
    def extract_column_dependencies(value: str) -> list[str]:
        """Extract column names from "{col1} {col2}" pattern."""
    
    @staticmethod
    def evaluate_interpolation(df: pd.DataFrame, pattern: str) -> pd.Series:
        """Evaluate interpolated string, handling nulls gracefully."""
    
    def evaluate_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
        entity_name: str,
        defer_missing: bool = False
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Evaluate extra_columns, returning updated DataFrame and deferred items.
        
        Args:
            df: DataFrame to add columns to
            extra_columns: Configuration dict
            entity_name: For logging
            defer_missing: If True, defer interpolations with missing columns
        
        Returns:
            (updated_df, deferred_extra_columns)
        """
```

### 2.3 Evaluation Strategy

**Decision Tree**:
```
For each extra_column:
  ├─ Is constant? → Add immediately
  ├─ Is column copy? → Add if column exists, else defer
  └─ Is interpolated string?
      ├─ All dependencies available? → Evaluate and add
      └─ Missing dependencies? → Defer (if defer_missing=True) or error
```

---

## 3. Implementation Tasks

### 3.1 Core Implementation (Priority 1)

#### Task 1.1: Create ExtraColumnEvaluator Module
**File**: `src/transforms/extra_columns.py` (new)  
**Estimated**: 1 day

Implementation:
```python
import re
from typing import Any

import pandas as pd
from loguru import logger


class ExtraColumnEvaluator:
    """Evaluates extra_columns with support for constants, copies, and interpolated strings."""
    
    # Regex pattern: match {column_name} but not {{escaped}}
    INTERPOLATION_PATTERN = re.compile(r'(?<!\{)\{([a-zA-Z_][\w]*)\}(?!\})')
    ESCAPED_BRACE_PATTERN = re.compile(r'\{\{|\}\}')
    
    @staticmethod
    def is_interpolated_string(value: Any) -> bool:
        """
        Detect if value is an interpolated string pattern.
        
        Examples:
            - "{first_name} {last_name}" → True
            - "{{literal}}" → False (escaped)
            - "constant" → False
            - 123 → False
        """
        if not isinstance(value, str):
            return False
        
        # Check for unescaped {column} patterns
        return bool(ExtraColumnEvaluator.INTERPOLATION_PATTERN.search(value))
    
    @staticmethod
    def extract_column_dependencies(pattern: str) -> list[str]:
        """
        Extract column names from interpolated string.
        
        Example:
            "{first_name} {last_name}" → ["first_name", "last_name"]
        """
        matches = ExtraColumnEvaluator.INTERPOLATION_PATTERN.findall(pattern)
        return list(dict.fromkeys(matches))  # Preserve order, remove duplicates
    
    @staticmethod
    def unescape_braces(text: str) -> str:
        """Convert {{literal}} to {literal}."""
        return text.replace('{{', '{').replace('}}', '}')
    
    @staticmethod
    def evaluate_interpolation(df: pd.DataFrame, pattern: str, entity_name: str = "") -> pd.Series:
        """
        Evaluate interpolated string pattern against DataFrame.
        
        Handles:
            - Null values (converted to empty strings)
            - Type coercion (all values converted to strings)
            - Escaped braces ({{}} → {})
        
        Args:
            df: DataFrame with columns to interpolate
            pattern: String like "{col1} {col2}"
            entity_name: For error messages
        
        Returns:
            pd.Series with interpolated values
        
        Raises:
            ValueError: If required columns are missing
        """
        columns = ExtraColumnEvaluator.extract_column_dependencies(pattern)
        
        # Check all columns exist
        missing = set(columns) - set(df.columns)
        if missing:
            raise ValueError(
                f"Cannot interpolate '{pattern}' for entity '{entity_name}': "
                f"columns not found: {sorted(missing)}"
            )
        
        # Create a row-wise function that handles nulls and types
        def interpolate_row(row: pd.Series) -> str:
            # Build dictionary with null-safe string conversion
            values = {
                col: '' if pd.isna(row[col]) else str(row[col])
                for col in columns
            }
            # Use format_map for safer interpolation
            result = pattern
            for col in columns:
                result = result.replace(f'{{{col}}}', values[col])
            
            # Unescape any {{}} to {}
            return ExtraColumnEvaluator.unescape_braces(result)
        
        return df[columns].apply(interpolate_row, axis=1)
    
    def evaluate_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
        entity_name: str,
        defer_missing: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Evaluate extra_columns configuration, adding columns to DataFrame.
        
        Processing order:
        1. Constants (non-string values)
        2. Column copies (string value matching existing column)
        3. Interpolated strings (string with {column} patterns)
        
        Args:
            df: DataFrame to add columns to
            extra_columns: Dict of {new_column: value/pattern}
            entity_name: For logging and error messages
            defer_missing: If True, defer interpolations with missing columns
        
        Returns:
            (updated_df, deferred_extra_columns)
            - updated_df: DataFrame with new columns added
            - deferred_extra_columns: Dict of items that were deferred
        """
        if not extra_columns:
            return df, {}
        
        result = df.copy()
        deferred: dict[str, Any] = {}
        added_count = 0
        
        for new_col, value in extra_columns.items():
            
            # Case 1: Non-string constant
            if not isinstance(value, str):
                result[new_col] = value
                added_count += 1
                logger.debug(f"{entity_name}[extra_columns]: Added constant '{new_col}' = {value}")
                continue
            
            # Case 2: Interpolated string
            if self.is_interpolated_string(value):
                columns = self.extract_column_dependencies(value)
                missing = set(columns) - set(result.columns)
                
                if missing:
                    if defer_missing:
                        deferred[new_col] = value
                        logger.debug(
                            f"{entity_name}[extra_columns]: Deferred interpolation '{new_col}' "
                            f"(missing columns: {sorted(missing)})"
                        )
                    else:
                        raise ValueError(
                            f"{entity_name}[extra_columns]: Cannot evaluate '{new_col}' = '{value}': "
                            f"columns not found: {sorted(missing)}"
                        )
                    continue
                
                # All columns available - evaluate
                result[new_col] = self.evaluate_interpolation(result, value, entity_name)
                added_count += 1
                logger.debug(f"{entity_name}[extra_columns]: Added interpolation '{new_col}' = '{value}'")
                continue
            
            # Case 3: Column copy (string matching existing column, case-insensitive)
            col_lower = value.lower()
            col_map = {str(c).lower(): c for c in result.columns if isinstance(c, str)}
            
            if col_lower in col_map:
                result[new_col] = result[col_map[col_lower]]
                added_count += 1
                logger.debug(f"{entity_name}[extra_columns]: Copied column '{new_col}' from '{value}'")
                continue
            
            # Case 4: String constant (doesn't match any column)
            result[new_col] = value
            added_count += 1
            logger.debug(f"{entity_name}[extra_columns]: Added constant '{new_col}' = '{value}'")
        
        if added_count > 0 or deferred:
            logger.info(
                f"{entity_name}[extra_columns]: Added {added_count} columns"
                + (f", deferred {len(deferred)}" if deferred else "")
            )
        
        return result, deferred
```

**Tests**:
- `tests/transforms/test_extra_columns.py` (new)
  - Test interpolation detection
  - Test dependency extraction
  - Test null handling
  - Test escaping (`{{}}` → `{}`)
  - Test deferred evaluation
  - Test error cases (missing columns)

---

#### Task 1.2: Refactor SubsetService to Use Evaluator
**File**: `src/extract.py`  
**Estimated**: 0.5 days

Changes:
```python
from src.transforms.extra_columns import ExtraColumnEvaluator

class SubsetService:
    
    def __init__(self):
        self.extra_col_evaluator = ExtraColumnEvaluator()
    
    def get_subset2(self, ...) -> pd.DataFrame:
        # ... existing code ...
        
        # OLD: Manual split and apply
        # extra_source_columns, extra_constant_columns = self._split_extra_columns(...)
        
        # NEW: Use evaluator (Pass 1 - no deferral in extract phase)
        if extra_columns:
            result, deferred = self.extra_col_evaluator.evaluate_extra_columns(
                df=result,
                extra_columns=extra_columns,
                entity_name=entity_name,
                defer_missing=False  # Extract phase: fail if columns missing
            )
            # Deferred should be empty here
        
        # ... rest of existing code ...
```

**Note**: Keep `_split_extra_columns` for backward compatibility in tests, or update all tests.

---

#### Task 1.3: Add Post-FK Link Evaluation Hook
**File**: `src/normalizer.py`  
**Estimated**: 0.5 days

Add method to ShapeShifter:
```python
from src.transforms.extra_columns import ExtraColumnEvaluator

class ShapeShifter:
    
    def __init__(self, ...):
        # ... existing code ...
        self.extra_col_evaluator = ExtraColumnEvaluator()
        # Track deferred extra_columns per entity
        self.deferred_extra_columns: dict[str, dict[str, Any]] = {}
    
    async def normalize(self) -> Self:
        # ... existing code in main loop ...
        
        # After: self.table_store[entity] = data
        # NEW: Evaluate extra_columns (Pass 1)
        if table_cfg.extra_columns:
            data, deferred = self.extra_col_evaluator.evaluate_extra_columns(
                df=data,
                extra_columns=table_cfg.extra_columns,
                entity_name=entity,
                defer_missing=True  # Defer if columns not available yet
            )
            self.table_store[entity] = data
            if deferred:
                self.deferred_extra_columns[entity] = deferred
        
        self.linker.link_entity(entity_name=entity)
        
        # NEW: Re-evaluate deferred extra_columns (Pass 2)
        if entity in self.deferred_extra_columns:
            self._evaluate_deferred_extra_columns(entity)
        
        # ... rest of existing code ...
    
    def _evaluate_deferred_extra_columns(self, entity_name: str) -> None:
        """Evaluate deferred extra_columns after FK linking adds columns."""
        if entity_name not in self.deferred_extra_columns:
            return
        
        deferred = self.deferred_extra_columns[entity_name]
        df = self.table_store[entity_name]
        
        # Attempt to evaluate deferred items
        updated_df, still_deferred = self.extra_col_evaluator.evaluate_extra_columns(
            df=df,
            extra_columns=deferred,
            entity_name=entity_name,
            defer_missing=False  # Fail if still missing after FK link
        )
        
        self.table_store[entity_name] = updated_df
        
        if still_deferred:
            # This shouldn't happen if defer_missing=False, but handle gracefully
            logger.error(
                f"{entity_name}[extra_columns]: Still deferred after FK linking: "
                f"{list(still_deferred.keys())}"
            )
        else:
            # Success - clear deferred
            del self.deferred_extra_columns[entity_name]
```

**Alternative**: Instead of modifying normalize() extensively, we could:
1. Keep extra_columns evaluation in SubsetService (Pass 1)
2. Add a new explicit step `self.evaluate_deferred_extra_columns()` after FK linking
3. Store deferred items in TableConfig or pass via table_store metadata

---

### 3.2 Backend Integration (Priority 2)

#### Task 2.1: Update Frontend ExtraColumnsEditor
**File**: `frontend/src/components/entities/ExtraColumnsEditor.vue`  
**Estimated**: 0.5 days

Changes:
- Add help text explaining interpolation syntax
- Add syntax highlighting for `{column}` patterns
- Add validation hints when typing interpolations
- Show warning if column doesn't exist (async validation)

```vue
<v-text-field
  v-model="item.source"
  placeholder="e.g., constant, column_name, or {first} {last}"
  hint="Use {column_name} for interpolation"
  persistent-hint
>
  <template #append-inner>
    <v-tooltip location="top">
      <template #activator="{ props }">
        <v-icon v-bind="props" size="small">mdi-help-circle-outline</v-icon>
      </template>
      <div class="text-caption">
        <strong>Syntax:</strong><br>
        • Constant: <code>literal_value</code><br>
        • Copy column: <code>existing_column</code><br>
        • Interpolate: <code>{first_name} {last_name}</code><br>
        • Escape: <code>{{literal_braces}}</code>
      </div>
    </v-tooltip>
  </template>
</v-text-field>
```

#### Task 2.2: Add Backend Validation
**File**: `backend/app/validators/entity_validators.py` (if exists) or create new  
**Estimated**: 0.5 days

Add validator to check interpolation syntax:
```python
class ExtraColumnsValidator:
    """Validate extra_columns configuration."""
    
    @staticmethod
    def validate_interpolation_syntax(extra_columns: dict[str, Any]) -> list[ValidationIssue]:
        """Check interpolation syntax is valid."""
        issues = []
        
        for key, value in extra_columns.items():
            if not isinstance(value, str):
                continue
            
            # Check for malformed interpolations
            if '{' in value or '}' in value:
                # Extract and validate
                try:
                    columns = ExtraColumnEvaluator.extract_column_dependencies(value)
                    # Could check if columns exist in entity config
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity="error",
                        entity=None,
                        field=f"extra_columns.{key}",
                        message=f"Malformed interpolation syntax: {e}",
                        code="INVALID_INTERPOLATION",
                    ))
        
        return issues
```

---

### 3.3 Testing (Priority 1)

#### Task 3.1: Unit Tests
**Files**:
- `tests/transforms/test_extra_columns.py` (new)
- `tests/process/test_subset_service.py` (update)

Test cases:
```python
def test_interpolation_detection():
    """Test is_interpolated_string() detection."""
    assert ExtraColumnEvaluator.is_interpolated_string("{col}")
    assert ExtraColumnEvaluator.is_interpolated_string("{first} {last}")
    assert not ExtraColumnEvaluator.is_interpolated_string("{{escaped}}")
    assert not ExtraColumnEvaluator.is_interpolated_string("constant")

def test_dependency_extraction():
    """Test extract_column_dependencies()."""
    assert extract_column_dependencies("{a} {b}") == ["a", "b"]
    assert extract_column_dependencies("{a} {a}") == ["a"]  # Dedup
    assert extract_column_dependencies("{{a}}") == []  # Escaped

def test_interpolation_with_nulls():
    """Test evaluate_interpolation() handles nulls."""
    df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
    result = evaluate_interpolation(df, "{a}-{b}", "test")
    assert result.tolist() == ["1-x", "-y", "3-"]

def test_interpolation_with_fk_columns():
    """Test deferred evaluation after FK link."""
    # Initial DF (no FK columns yet)
    df = pd.DataFrame({"site_name": ["Site A"]})
    
    # Attempt interpolation - should defer
    result, deferred = evaluator.evaluate_extra_columns(
        df, {"info": "{site_name} ({location_name})"}, "site", defer_missing=True
    )
    assert "info" in deferred  # Missing location_name
    
    # Simulate FK link adding column
    result["location_name"] = "Norway"
    
    # Re-evaluate deferred
    result, still_deferred = evaluator.evaluate_extra_columns(
        result, deferred, "site", defer_missing=False
    )
    assert len(still_deferred) == 0
    assert result["info"].iloc[0] == "Site A (Norway)"

def test_escaping_braces():
    """Test {{}} → {} escaping."""
    df = pd.DataFrame({"name": ["John"]})
    result = evaluate_interpolation(df, "{{name}}: {name}", "test")
    assert result.iloc[0] == "{name}: John"
```

#### Task 3.2: Integration Tests
**File**: `tests/integration/test_extra_columns_with_fk.py` (new)  
**Estimated**: 1 day

Full E2E test:
```python
@pytest.mark.asyncio
async def test_extra_columns_interpolation_with_fk():
    """Test interpolation can reference FK-added columns."""
    
    config = {
        "entities": {
            "location": {
                "type": "fixed",
                "data": [
                    {"location_name": "Norway", "country": "NO"},
                    {"location_name": "Sweden", "country": "SE"},
                ],
                "columns": ["location_name", "country"],
                "keys": ["location_name"],
            },
            "site": {
                "type": "fixed",
                "data": [
                    {"site_name": "Site A", "location_name": "Norway"},
                    {"site_name": "Site B", "location_name": "Sweden"},
                ],
                "columns": ["site_name", "location_name"],
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": ["location_name"],
                        "remote_keys": ["location_name"],
                        "extra_columns": {"country": "country"},  # Pull country from location
                    }
                ],
                "extra_columns": {
                    # This interpolation references FK-added 'country' column
                    "full_info": "{site_name}, {location_name} ({country})"
                },
            },
        }
    }
    
    normalizer = ShapeShifter(project=config)
    await normalizer.normalize()
    
    site_df = normalizer.table_store["site"]
    assert "full_info" in site_df.columns
    assert site_df["full_info"].iloc[0] == "Site A, Norway (NO)"
    assert site_df["full_info"].iloc[1] == "Site B, Sweden (SE)"
```

---

### 3.4 Documentation (Priority 3)

#### Task 4.1: Update Configuration Guide
**File**: `docs/CONFIGURATION_GUIDE.md`  
**Estimated**: 0.5 days

Add section:
```markdown
### Extra Columns - Interpolated Strings

Create new columns from existing ones using interpolated string syntax:

**Syntax**: `"{column_name}"` - Reference column values in curly braces

**Examples**:
```yaml
entities:
  person:
    extra_columns:
      # String interpolation
      fullname: "{first_name} {last_name}"
      email: "{username}@example.com"
      
      # With FK columns (added during link phase)
      site_info: "{site_name} ({location_name})"
      
      # Escaping (use {{ and }})
      json_field: '{{"key": "{value}"}}'  # → {"key": "actual_value"}
      
      # Still supported: constants and column copies
      record_type: "14"
      parent_id: child_id
```

**Features**:
- Null-safe: null values become empty strings
- Type coercion: all values converted to strings
- Multi-stage evaluation: can reference FK columns
- Case-insensitive column matching

**Limitations**:
- No transformations (use TODO #108 DSL for `upper()`, `substr()`, etc.)
- No arithmetic expressions
- No conditionals
```

#### Task 4.2: Update AI Validation Guide
**File**: `docs/AI_VALIDATION_GUIDE.md`  
**Estimated**: 0.25 days

Update extra_columns section with interpolation examples.

---

## 4. Testing Strategy

### 4.1 Test Coverage Requirements

| Component | Test Type | Coverage Target |
|-----------|-----------|----------------|
| ExtraColumnEvaluator | Unit | 100% |
| SubsetService integration | Unit | 90% |
| Normalizer deferred eval | Integration | 100% |
| E2E with FK interpolation | Integration | 100% |
| Frontend validation | E2E | 80% |

### 4.2 Edge Cases to Test

1. **Null handling**: `{null_col}` → empty string
2. **Escaping**: `{{literal}}` → `{literal}`
3. **Missing columns**: Proper error messages
4. **Deferred evaluation**: Works after FK link
5. **Multiple FKs**: Can reference columns from different FKs
6. **Circular dependencies**: Detect and error
7. **Type coercion**: Numbers, dates, booleans → strings
8. **Empty DataFrames**: No errors on empty data
9. **Unicode**: Handle international characters
10. **Column name conflicts**: New column same as existing

---

## 5. Rollout Plan

### Phase 1a: Core Implementation (Week 1)
- ✅ Task 1.1: ExtraColumnEvaluator module
- ✅ Task 1.2: Refactor SubsetService
- ✅ Task 3.1: Unit tests

### Phase 1b: Integration (Week 2)
- ✅ Task 1.3: Normalizer deferred evaluation
- ✅ Task 3.2: Integration tests
- ✅ Task 2.2: Backend validation

### Phase 1c: Frontend & Docs (Week 3)
- ✅ Task 2.1: Frontend editor updates
- ✅ Task 4.1: Configuration guide
- ✅ Task 4.2: AI validation guide

### Final: Testing & Refinement (Week 3-4)
- ✅ Edge case testing
- ✅ Performance testing (large DataFrames)
- ✅ User acceptance testing

---

## 6. Success Criteria

### Functional Requirements
- ✅ Users can use `"{col1} {col2}"` syntax in extra_columns
- ✅ Nulls handled gracefully (empty strings)
- ✅ Escaping works (`{{}}` → `{}`)
- ✅ Can reference FK-added columns
- ✅ Clear error messages for missing columns
- ✅ Backward compatible (constants/copies still work)

### Non-Functional Requirements
- ✅ Performance: <10% overhead on typical projects
- ✅ Test coverage: >90% for new code
- ✅ Documentation: Complete with examples
- ✅ No breaking changes to existing projects

---

## 7. Future Enhancements (Phase 2)

After Phase 1 is stable, consider:

### TODO #108: DSL Functions
```yaml
extra_columns:
  # Phase 2: Function-based DSL
  initials: "=upper(substr(first_name, 0, 1)) + upper(substr(last_name, 0, 1))"
  age: "=2026 - birth_year"
  
  # Phase 2: Power user mode
  computed: "expr:df['price'] * df['quantity'] * (1 + df['tax_rate'])"
```

**Detection precedence**:
1. `expr:...` → Pandas eval (power users)
2. `=function(...)` → DSL compiler (advanced users)
3. `{col}` → Interpolation (Phase 1 - common case)
4. Constant or column copy (existing)

---

## 8. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance degradation on large DFs | Medium | Medium | Benchmark, optimize with vectorization |
| Breaking existing projects | Low | High | Extensive backward compat tests |
| Security (code injection via `expr:`) | Low | High | Phase 1: no eval; Phase 2: sandboxed namespace |
| Complex deferred evaluation bugs | Medium | Medium | Comprehensive integration tests |
| User confusion (when to use) | Medium | Low | Clear docs with decision tree |

---

## 9. Open Questions

1. **Should we allow nested interpolations?** `{outer_{inner}}`
   - **Decision**: No, too complex for Phase 1
   
2. **Should we cache evaluated interpolations?**
   - **Decision**: Not needed unless performance issues

3. **Should deferred evaluation be per-entity or per-column?**
   - **Decision**: Per-column (more granular, better errors)

4. **How to handle column name conflicts?** New extra column overwrites existing?
   - **Decision**: Error if new column already exists (safer)

---

## 10. Acceptance Criteria

### Demo Scenario
```yaml
# Configuration
entities:
  location:
    type: fixed
    data:
      - {location_name: "Norway", country_code: "NO"}
      - {location_name: "Sweden", country_code: "SE"}
    columns: [location_name, country_code]
    keys: [location_name]
  
  site:
    type: fixed
    data:
      - {site_name: "Site A", location_name: "Norway"}
      - {site_name: "Site B", location_name: "Sweden"}
    columns: [site_name, location_name]
    foreign_keys:
      - entity: location
        local_keys: [location_name]
        remote_keys: [location_name]
        extra_columns: {country_code: country_code}
    extra_columns:
      full_info: "{site_name}, {location_name} ({country_code})"  # Uses FK column!
      record_type: "site_record"  # Constant still works

# Expected Output
site:
  | site_name | location_name | country_code | full_info              | record_type  |
  |-----------|---------------|--------------|------------------------|--------------|
  | Site A    | Norway        | NO           | Site A, Norway (NO)    | site_record  |
  | Site B    | Sweden        | SE           | Site B, Sweden (SE)    | site_record  |
```

**Success**: All columns created correctly, no errors, clear logs.

---

## Conclusion

This implementation plan provides a robust, idempotent solution for interpolated strings in extra_columns that:

1. ✅ Maintains backward compatibility
2. ✅ Supports the critical use case (constant FK columns)
3. ✅ Enables the advanced use case (interpolating FK columns)
4. ✅ Sets foundation for Phase 2 (DSL functions)
5. ✅ Includes comprehensive testing and documentation

**Recommended approach**: Implement Phase 1a first, validate with users, then proceed to 1b/1c based on feedback.
