# Union/Concatenation Configuration Options

## Overview

This document proposes several options for adding union/concatenation features to the configuration system, allowing entities to be built from multiple sub-dataframes that are concatenated into a final result. All options maintain backward compatibility with existing configurations.

---

## Current State Analysis

The configuration already has an `append` feature (see `cultural_group` entity in arbodat.yml):

```yaml
cultural_group:
  keys: ["KultGr"]
  columns: ["KultGr", "Cult_EN"]
  surrogate_id: cultural_group_id
  append:
    - data_source: arbodat_lookup
      type: sql
      how: "append"
      values: |
        sql: 
        select KultGr, Cult_EN
        from Kulturgruppen;
    - type: fixed
      values:
        - ["unbekannt", "unknown"]
        - ["diverse", "various"]
  depends_on: []
```

This provides a foundation for union operations, but appears incomplete or not fully implemented in the current codebase.

---

## Design Requirements

1. **Backward Compatibility**: Existing configurations must continue to work without modification
2. **Optional Feature**: Union/concatenation should be opt-in
3. **Shared Properties**: Sub-configurations must inherit or share common properties (keys, columns, surrogate_id, depends_on)
4. **Clear Semantics**: Union behavior should be well-defined and predictable
5. **Validation**: Configuration errors should be caught early with clear error messages

---

## Option 1: Enhanced `append` List (Recommended)

**Description**: Formalize and enhance the existing `append` property as a list of sub-entity configurations. Each sub-config produces a dataframe that's concatenated with the main entity extraction.

### Configuration Structure

```yaml
entity_name:
  # Main entity configuration (produces base dataframe)
  surrogate_id: string
  keys: [string, ...]
  columns: [string, ...]
  source: string | null
  type: "data" | "fixed" | "sql"
  depends_on: [string, ...]
  
  # Union configuration (optional)
  append:
    - # Sub-config 1
      source: string | null      # Can override main source
      type: "data" | "fixed" | "sql"
      columns: [string, ...]     # Must be compatible with main columns
      data_source: string        # For SQL sources
      values: string | [...]     # For fixed/SQL sources
      extra_columns: {...}       # Optional additional columns
      drop_duplicates: bool | [string, ...]
      # Note: inherits keys, surrogate_id, depends_on from parent
      
    - # Sub-config 2
      type: fixed
      values: [[...], [...]]
      # ...
```

### Key Features

- **Main config produces base dataframe**: The primary entity configuration is processed first
- **Append items processed sequentially**: Each append item produces a dataframe using subset logic
- **Inheritance**: Sub-configs inherit `keys`, `surrogate_id`, and `depends_on` from parent unless overridden
- **Flexible sources**: Each sub-config can specify its own source, type, and data_source
- **Column alignment**: System validates that all sub-dataframes have compatible columns
- **Concatenation order**: Base dataframe first, then append items in order

### Example 1: Union of Multiple Fixed Tables

```yaml
sample_type:
  surrogate_id: sample_type_id
  keys: ["type_code"]
  columns: ["type_code", "type_name", "description"]
  type: fixed
  values:
    - ["SOIL", "Soil Sample", "Bulk soil sample"]
    - ["CHARCOAL", "Charcoal", "Charcoal remains"]
  append:
    - type: fixed
      values:
        - ["SEED", "Seed/Fruit", "Seed and fruit remains"]
        - ["POLLEN", "Pollen", "Pollen sample"]
    - type: fixed
      values:
        - ["WOOD", "Wood", "Wood remains"]
  depends_on: []
```

**Result**: 5 rows concatenated from 3 fixed value sets

### Example 2: Union of Spreadsheet + SQL + Fixed Data

```yaml
taxa:
  surrogate_id: taxon_id
  keys: ["taxon_code"]
  columns: ["taxon_code", "scientific_name", "common_name"]
  source: null  # From main survey spreadsheet
  drop_duplicates: true
  
  append:
    # Add reference taxa from database
    - type: sql
      data_source: sead
      values: |
        sql:
        select taxon_code, scientific_name, common_name
        from reference.tbl_taxa
        where is_active = true
      drop_duplicates: ["taxon_code"]
    
    # Add manually curated taxa
    - type: fixed
      values:
        - ["UNKNOWN", "Unknown", "Unidentified"]
        - ["INDET", "Indeterminate", "Cannot be determined"]
  
  depends_on: []
```

**Result**: Rows from survey + database query + fixed values, all concatenated

### Example 3: Union from Multiple Spreadsheet Sources

```yaml
sample:
  surrogate_id: sample_id
  keys: ["project_id", "sample_id"]
  columns: ["project_id", "sample_id", "sample_name", "date_collected"]
  source: null  # Main survey data
  
  append:
    # Include samples from historical dataset
    - source: historical_samples
      columns: ["project_id", "sample_id", "sample_name", "date_collected"]
      extra_columns:
        data_quality: "historical"
    
    # Include samples from partner institution
    - source: partner_samples
      columns: ["project_id", "sample_id", "sample_name", "date_collected"]
      extra_columns:
        data_quality: "partner"
  
  depends_on: ["historical_samples", "partner_samples"]
```

### Implementation Notes

**Processing Logic**:
```python
async def process_entity_with_append(entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
    # 1. Process main entity configuration
    main_df = await extract_main_entity(entity_name, table_cfg)
    
    if not table_cfg.has_append:
        return main_df
    
    # 2. Process each append configuration
    dfs = [main_df]
    for append_cfg in table_cfg.append_configs:
        # Create sub-config inheriting parent properties
        sub_cfg = create_sub_config(table_cfg, append_cfg)
        sub_df = await extract_sub_entity(entity_name, sub_cfg)
        dfs.append(sub_df)
    
    # 3. Concatenate all dataframes
    result_df = pd.concat(dfs, ignore_index=True)
    
    # 4. Apply post-concatenation operations
    if table_cfg.drop_duplicates:
        result_df = drop_duplicate_rows(result_df, table_cfg.drop_duplicates)
    
    return result_df
```

**Validation Requirements**:
- All sub-configs must produce dataframes with compatible columns
- Column data types should be compatible across sub-dataframes
- Keys must be consistent across all sub-dataframes
- Dependencies must be satisfied for all sources

### Advantages

✅ Builds on existing `append` pattern  
✅ Simple and intuitive configuration  
✅ Clear inheritance model  
✅ Flexible - supports all source types  
✅ Maintains processing order guarantees  

### Disadvantages

❌ Limited control over concatenation behavior (always vertical concat)  
❌ No support for complex union operations (UNION ALL vs UNION)  

---

## Option 2: Explicit `union` Configuration

**Description**: Introduce a new `union` property that explicitly defines multiple sub-entity configurations with full control over each.

### Configuration Structure

```yaml
entity_name:
  # Union configuration
  union:
    mode: "all" | "distinct"  # UNION ALL vs UNION (drop duplicates)
    
    sources:
      - name: "main_source"
        source: null
        type: data
        columns: [...]
        keys: [...]
        # Full entity config
      
      - name: "additional_source"
        source: other_entity
        type: data
        columns: [...]
        # Full entity config
      
      - name: "fixed_values"
        type: fixed
        columns: [...]
        values: [...]
  
  # Shared properties (inherited by all sources if not overridden)
  surrogate_id: string
  keys: [string, ...]
  depends_on: [string, ...]
```

### Example

```yaml
site_location:
  surrogate_id: site_location_id
  keys: ["site_id", "location_name"]
  
  union:
    mode: distinct  # Drop duplicates after concatenation
    
    sources:
      - name: survey_locations
        source: null  # Main survey
        columns: ["site_id", "location_name", "location_type"]
        drop_duplicates: true
      
      - name: database_locations
        type: sql
        data_source: sead
        columns: ["site_id", "location_name", "location_type"]
        values: |
          sql:
          select site_id, location_name, location_type
          from public.tbl_site_locations
      
      - name: default_locations
        type: fixed
        columns: ["site_id", "location_name", "location_type"]
        values:
          - [null, "Unknown", "unknown"]
  
  depends_on: []
```

### Advantages

✅ Explicit and clear union semantics  
✅ Named sources for better debugging  
✅ Full control over each source configuration  
✅ Supports UNION vs UNION ALL semantics  

### Disadvantages

❌ More verbose configuration  
❌ Doesn't leverage existing `append` pattern  
❌ Requires more significant code changes  

---

## Option 3: Multi-Section Entity with `sections`

**Description**: Define entities with multiple named sections, each producing a dataframe, with explicit concatenation control.

### Configuration Structure

```yaml
entity_name:
  # Shared configuration (applies to all sections)
  surrogate_id: string
  keys: [string, ...]
  columns: [string, ...]  # Required columns for all sections
  depends_on: [string, ...]
  
  # Multi-section definition
  sections:
    base:  # Required base section
      source: null
      type: data
      # Section-specific config
    
    additional:
      source: other_entity
      type: data
      columns: [...]  # Can extend base columns
    
    fallback:
      type: fixed
      values: [...]
  
  # Concatenation behavior
  concat:
    ignore_index: true
    verify_integrity: false
    drop_duplicates: true | [string, ...]
```

### Example

```yaml
taxa:
  surrogate_id: taxon_id
  keys: ["taxon_code"]
  columns: ["taxon_code", "scientific_name"]
  depends_on: []
  
  sections:
    survey:
      source: null
      columns: ["taxon_code", "scientific_name", "family", "author"]
      drop_empty_rows: true
    
    reference:
      type: sql
      data_source: sead
      columns: ["taxon_code", "scientific_name", "family", "author"]
      values: |
        sql:
        select taxon_code, scientific_name, family, author
        from tbl_taxa_reference
        where verified = true
    
    manual:
      type: fixed
      columns: ["taxon_code", "scientific_name", "family", "author"]
      values:
        - ["UNK", "Unknown", null, null]
  
  concat:
    ignore_index: true
    drop_duplicates: ["taxon_code"]
```

### Advantages

✅ Very explicit about multi-section nature  
✅ Named sections improve clarity and debugging  
✅ Fine-grained control over concatenation  
✅ Clear separation of shared vs section-specific config  

### Disadvantages

❌ More complex configuration structure  
❌ Potential confusion between sections and sources  
❌ Requires significant implementation work  

---

## Option 4: Source Array with Implicit Union

**Description**: Allow `source` to be an array, implicitly creating a union of all sources.

### Configuration Structure

```yaml
entity_name:
  surrogate_id: string
  keys: [string, ...]
  columns: [string, ...]
  
  # Source can be string or array
  source: [null, "other_entity", "third_entity"]
  # OR specify detailed configs
  sources:
    - source: null
      filter: {"column": "value"}  # Optional filtering
    - source: other_entity
      columns: [...]  # Optional column selection
    - type: fixed
      values: [...]
  
  drop_duplicates: true | [string, ...]
  depends_on: [string, ...]
```

### Example

```yaml
sample:
  surrogate_id: sample_id
  keys: ["sample_code"]
  columns: ["sample_code", "sample_name", "sample_type"]
  
  # Simple array syntax
  source: [null, "historical_samples", "partner_samples"]
  
  drop_duplicates: ["sample_code"]
  depends_on: ["historical_samples", "partner_samples"]
```

### Advantages

✅ Minimal syntax for simple cases  
✅ Intuitive for common use cases  
✅ Easy migration from single source  

### Disadvantages

❌ Limited control over individual sources  
❌ Less clear for complex scenarios  
❌ Hard to specify different column sets per source  

---

## Comparison Matrix

| Feature | Option 1: Enhanced `append` | Option 2: Explicit `union` | Option 3: `sections` | Option 4: Source Array |
|---------|---------------------------|--------------------------|-------------------|---------------------|
| Backward Compatible | ✅ Perfect | ✅ Yes | ⚠️ Partial | ⚠️ Partial |
| Leverages Existing Pattern | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial |
| Configuration Simplicity | ✅ Simple | ⚠️ Moderate | ❌ Complex | ✅ Very Simple |
| Flexibility | ✅ High | ✅ High | ✅ Very High | ⚠️ Moderate |
| Clear Semantics | ✅ Clear | ✅ Very Clear | ✅ Very Clear | ⚠️ Can be unclear |
| Implementation Effort | ✅ Low | ⚠️ Moderate | ❌ High | ✅ Low |
| Debugging Support | ⚠️ Moderate | ✅ Good | ✅ Excellent | ⚠️ Moderate |
| Named Sub-Configs | ❌ No | ✅ Yes | ✅ Yes | ❌ No |

---

## Recommended Approach: Enhanced `append` (Option 1)

**Rationale**:
1. **Builds on existing pattern**: The `cultural_group` entity already uses `append`
2. **Minimal breaking changes**: Existing configs work as-is
3. **Simple to understand**: Clear master + append model
4. **Flexible enough**: Supports all required use cases
5. **Low implementation effort**: Extends existing infrastructure

### Implementation Roadmap

#### Phase 1: Core Union Support

1. **Update `TableConfig`**:
   - Add `append_configs` property to parse `append` list
   - Add `has_append` property
   - Ensure inheritance of keys, surrogate_id, depends_on

2. **Update `ArbodatSurveyNormalizer.normalize()`**:
   - Extract main entity dataframe
   - If `has_append`, process each append config
   - Concatenate dataframes using `pd.concat()`
   - Apply post-concatenation deduplication

3. **Add validation**:
   - Verify column compatibility across all sub-configs
   - Validate that all sources are available
   - Check for circular dependencies

#### Phase 2: Enhanced Features

4. **Add concatenation options**:
   ```yaml
   append_mode: "all" | "distinct"  # UNION ALL vs UNION
   ```

5. **Add column alignment options**:
   ```yaml
   append_align_columns: true | false  # Align columns across sources
   append_fill_missing: null | value   # Fill missing columns
   ```

6. **Add debugging support**:
   - Log source for each row (optional `_source` column)
   - Track row counts from each source

#### Phase 3: Advanced Features

7. **Add filtering per append item**:
   ```yaml
   append:
     - source: other_entity
       filter:
         column_name: value
   ```

8. **Add column transformations**:
   ```yaml
   append:
     - source: other_entity
       transform:
         column_name: "new_value"
   ```

### Configuration Specification

```yaml
entity_name:
  # Standard properties (required)
  surrogate_id: string
  keys: [string, ...]
  columns: [string, ...]
  source: string | null
  type: "data" | "fixed" | "sql"
  depends_on: [string, ...]
  
  # Union properties (optional)
  append:  # List of sub-entity configurations
    - # Sub-config inherits parent's keys, surrogate_id, depends_on
      source?: string | null      # Override parent source
      type?: "data" | "fixed" | "sql"
      data_source?: string        # For SQL type
      values?: string | [[...]]   # For fixed/SQL type
      columns?: [string, ...]     # Must be compatible with parent
      extra_columns?: {...}
      drop_duplicates?: bool | [string, ...]
      drop_empty_rows?: bool | [string, ...]
      # Cannot override: keys, surrogate_id, depends_on
  
  # Concatenation control (optional)
  append_mode?: "all" | "distinct"  # Default: "all"
  append_align_columns?: bool       # Default: true
  append_fill_missing?: any         # Default: null
  
  # Standard post-processing (applied after concatenation)
  drop_duplicates: bool | [string, ...]
  drop_empty_rows: bool | [string, ...]
```

### Property Inheritance Rules

**Inherited Properties** (from parent to all append items):
- `keys`: Natural key columns
- `surrogate_id`: Primary key column name
- `depends_on`: Entity dependencies

**Inheritable Properties** (can be overridden in append items):
- `source`: Data source entity
- `type`: Source type (data/fixed/sql)
- `data_source`: Database connection name
- `columns`: Column selection
- `extra_columns`: Additional columns
- `drop_duplicates`: Duplicate handling per source
- `drop_empty_rows`: Empty row handling per source

**Non-inheritable Properties** (parent level only):
- `foreign_keys`: Applied after concatenation
- `unnest`: Applied after concatenation
- Global `drop_duplicates`: Applied after concatenation
- Global `drop_empty_rows`: Applied after concatenation

### Validation Rules

1. **Column Compatibility**: All sources must produce compatible column sets
2. **Key Consistency**: Keys must be present in all sources
3. **Type Compatibility**: Column types should be compatible for concatenation
4. **Source Availability**: All referenced sources must exist or be processable
5. **Dependency Satisfaction**: All dependencies must be met before processing
6. **No Circular Append**: Entities cannot append themselves (directly or indirectly)

### Error Messages

```
ConfigurationError: Entity 'taxa' append[1] missing required inherited columns: ['taxon_code']
ConfigurationError: Entity 'sample' append[0] references unknown source: 'missing_entity'
ConfigurationError: Entity 'site' append[2] has incompatible column types for 'elevation' (int vs str)
ValidationError: Entity 'location' has circular append dependency: location -> extra_locations -> location
```

---

## Alternative: Hybrid Approach

For maximum flexibility, implement **Option 1 (Enhanced `append`)** as the primary mechanism, with an **optional migration path to Option 2 (Explicit `union`)** for advanced cases.

### Configuration

```yaml
# Simple case: use append
entity_simple:
  columns: [...]
  append:
    - type: fixed
      values: [...]

# Advanced case: use union with named sources
entity_advanced:
  union:
    mode: distinct
    sources:
      - name: survey
        source: null
        columns: [...]
      - name: reference
        type: sql
        data_source: sead
        values: |
          sql: ...
```

This provides simplicity for common cases while allowing explicit control when needed.

---

## Testing Strategy

1. **Backward Compatibility Tests**: Ensure existing configs work unchanged
2. **Simple Append Tests**: Single append item from each source type
3. **Multiple Append Tests**: Multiple append items, mixed source types
4. **Column Compatibility Tests**: Verify column alignment and type checking
5. **Deduplication Tests**: Test drop_duplicates at source and global level
6. **Dependency Tests**: Verify correct dependency resolution
7. **Error Handling Tests**: Test validation and error messages
8. **Performance Tests**: Benchmark concatenation of large datasets

---

## Migration Guide

### For Existing `append` Usage

If your config already uses `append` (like `cultural_group`):

```yaml
# Current (if implemented)
cultural_group:
  append:
    - data_source: arbodat_lookup
      how: "append"  # This property may be removed
      # ...
```

**No changes required** - the enhanced implementation will be backward compatible.

### For New Union Configurations

```yaml
# Before: single source
taxa:
  source: null
  columns: ["taxon_code", "name"]

# After: multiple sources
taxa:
  source: null
  columns: ["taxon_code", "name"]
  append:
    - type: sql
      data_source: sead
      values: |
        sql:
        select taxon_code, name from tbl_taxa
```

---

## Future Enhancements

1. **Append Transformations**: Apply transformations to specific append items
2. **Conditional Append**: Include append items based on runtime conditions
3. **Append Ordering**: Control the order of concatenation explicitly
4. **Source Metadata**: Track which source each row came from
5. **Incremental Append**: Support incremental updates from different sources
6. **Cross-Source Validation**: Validate relationships across append sources

---

## Conclusion

**Recommended Implementation**: **Option 1 - Enhanced `append`**

This approach provides:
- ✅ Backward compatibility with existing configurations
- ✅ Builds on the existing `append` pattern
- ✅ Simple configuration for common cases
- ✅ Sufficient flexibility for complex scenarios
- ✅ Low implementation complexity
- ✅ Clear upgrade path for future enhancements

The enhanced `append` feature will enable union/concatenation of multiple data sources while maintaining the clarity and simplicity that makes the current configuration system effective.
