# Foreign Key Constraints

This document describes the constraint system for foreign key linking in the Arbodat normalization process.

## Overview

Foreign key constraints allow you to enforce data integrity rules when linking tables. Constraints are specified in the `constraints` section of each foreign key configuration.

## Configuration Format

```yaml
tables:
  entity_name:
    foreign_keys:
      - entity: remote_entity_name
        local_keys: ["key1"]
        remote_keys: ["key1"]
        constraints:
          # Add constraint specifications here
```

## Constraint Types

### 1. Cardinality Constraints

Enforce relationship multiplicity between tables.

**`cardinality`**: `one_to_one | many_to_one | one_to_many | many_to_many`

```yaml
constraints:
  cardinality: many_to_one  # Multiple left rows can match one right row
```

- **`one_to_one`**: Each left row matches exactly one right row (row count stays same)
- **`many_to_one`**: Multiple left rows match one right row (row count cannot increase)
- **`one_to_many`**: One left row matches multiple right rows (row count can increase)
- **`many_to_many`**: No restrictions on multiplicity

**Example Use Cases:**
- `one_to_one`: Employee → Employee_Details (each employee has one detail record)
- `many_to_one`: Sample → Site (many samples from one site)
- `one_to_many`: Order → OrderItems (one order has many items)

### 2. Match Requirements

Control how unmatched rows are handled.

**`allow_unmatched_left`**: `bool` (default: depends on join type)

```yaml
constraints:
  allow_unmatched_left: false  # All left rows must find a match
```

Determines whether left rows without matches are kept in the result. When `false`, raises an error if any left rows don't match.

**`allow_unmatched_right`**: `bool` (default: false)

```yaml
constraints:
  allow_unmatched_right: false  # Right table fully consumed
```

Determines whether right rows without matches are kept. Usually `false` since foreign keys reference existing data.

**`require_all_left_matched`**: `bool` (default: false)

```yaml
constraints:
  require_all_left_matched: true  # Strict validation
```

Stricter than `allow_unmatched_left: false`. Raises an error if ANY left rows don't match, regardless of join type.

**`require_all_right_matched`**: `bool` (default: false)

```yaml
constraints:
  require_all_right_matched: true  # All reference data must be used
```

Ensures all right rows are matched. Useful for validating that reference tables are complete.

**`min_match_rate`**: `float` (0.0 to 1.0)

```yaml
constraints:
  min_match_rate: 0.95  # At least 95% of left rows must match
```

Specifies minimum percentage of left rows that must find a match. Useful for data quality checks.

### 3. Validation Constraints

Control row count changes during merge.

**`max_row_increase_pct`**: `float` (percentage)

```yaml
constraints:
  max_row_increase_pct: 10  # Allow up to 10% row increase
```

Maximum allowed percentage increase in row count. Useful for detecting unexpected one-to-many relationships.

**`max_row_increase_abs`**: `int` (absolute count)

```yaml
constraints:
  max_row_increase_abs: 100  # Allow up to 100 additional rows
```

Maximum allowed absolute increase in row count.

**`allow_row_decrease`**: `bool` (default: depends on join type)

```yaml
constraints:
  allow_row_decrease: false  # Row count cannot decrease
```

Whether the merge can result in fewer rows. Useful for detecting data loss in joins.

### 4. Data Quality Constraints

Ensure key uniqueness and null handling.

**`require_unique_left`**: `bool` (default: false)

```yaml
constraints:
  require_unique_left: true  # Left keys must be unique
```

Requires that left key columns contain unique values. Useful for enforcing one-to-one or many-to-one relationships.

**`require_unique_right`**: `bool` (default: false)

```yaml
constraints:
  require_unique_right: true  # Right keys must be unique
```

Requires that right key columns contain unique values. Ensures reference table has no duplicates.

**`allow_null_keys`**: `bool` (default: true)

```yaml
constraints:
  allow_null_keys: false  # No null values in keys
```

Whether null values are allowed in key columns. When `false`, raises an error if any keys are null.

## Complete Examples

### Example 1: Strict One-to-Many

Sample → Dataset (each sample belongs to exactly one dataset, datasets can have multiple samples)

```yaml
sample:
  foreign_keys:
    - entity: dataset
      local_keys: ["dataset_name"]
      remote_keys: ["dataset_name"]
      constraints:
        cardinality: many_to_one
        require_all_left_matched: true
        require_unique_right: true
        allow_null_keys: false
```

### Example 2: Optional Reference with Quality Check

Site → Location (site may have a location, but if it does, it must be valid)

```yaml
site:
  foreign_keys:
    - entity: location
      local_keys: ["location_name"]
      remote_keys: ["location_name"]
      how: left
      constraints:
        cardinality: many_to_one
        min_match_rate: 0.8  # At least 80% should match
        max_row_increase_pct: 0  # Never multiply rows
        allow_null_keys: true  # Location can be null
```

### Example 3: Strict One-to-One

Employee → EmployeeDetails (each employee has exactly one detail record)

```yaml
employee:
  foreign_keys:
    - entity: employee_details
      local_keys: ["employee_id"]
      remote_keys: ["employee_id"]
      constraints:
        cardinality: one_to_one
        require_all_left_matched: true
        require_all_right_matched: true
        require_unique_left: true
        require_unique_right: true
        allow_null_keys: false
```

### Example 4: Controlled Expansion

Order → OrderItems (one order has items, but limit growth)

```yaml
order:
  foreign_keys:
    - entity: order_items
      local_keys: ["order_id"]
      remote_keys: ["order_id"]
      constraints:
        cardinality: one_to_many
        max_row_increase_pct: 500  # Up to 5x expansion (avg 5 items per order)
        require_all_left_matched: true  # All orders must have items
```

## Error Messages

When constraints are violated, you'll see descriptive error messages:

```
ForeignKeyConstraintViolation: sample -> dataset: many_to_one cardinality violated 
(rows increased: 1000 -> 1050)
```

```
ForeignKeyConstraintViolation: site -> location: 250 unmatched left rows 
(require_all_left_matched=True)
```

```
ForeignKeyConstraintViolation: employee -> employee_details: Match rate 87.50% below 
minimum 95.00%
```

## Best Practices

1. **Start with basic constraints**: Begin with `cardinality` and `require_all_left_matched`
2. **Use match rates for monitoring**: Set `min_match_rate` to detect data quality issues early
3. **Protect against unexpected expansion**: Use `max_row_increase_pct` to catch one-to-many issues
4. **Document your assumptions**: Use constraints to make data relationships explicit
5. **Test with real data**: Run with constraints to discover hidden data issues

## Performance Considerations

- Pre-merge validation (unique checks, null checks) adds minimal overhead
- Post-merge validation requires a merge indicator (`indicator=True` in pandas merge)
- Match requirement validation is only performed when relevant constraints are specified
- Most constraint checks are O(1) or O(n) operations on pandas DataFrames

## Migration Guide

Existing configurations without constraints will continue to work unchanged. To add constraints:

1. Identify the relationship type (one-to-one, many-to-one, etc.)
2. Add `constraints:` section with `cardinality`
3. Add additional constraints based on data requirements
4. Test with your data and adjust as needed

```yaml
# Before
foreign_keys:
  - entity: site
    local_keys: ["site_name"]
    remote_keys: ["site_name"]

# After
foreign_keys:
  - entity: site
    local_keys: ["site_name"]
    remote_keys: ["site_name"]
    constraints:
      cardinality: many_to_one
      require_all_left_matched: true
```
