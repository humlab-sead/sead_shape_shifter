# Configuration Validation Improvements

## Overview

This document describes the new validation specifications added to the configuration system to ensure data integrity and catch configuration errors early.

## New Validation Specifications

### 1. SqlDataSpecification

**Purpose**: Validates that SQL-type entities have all required fields.

**Checks**:
- Entities with `type: sql` must have a `data_source` field
- Entities with `type: sql` must have a `query` field
- The `query` field must not be empty
- Warns if SQL entities have a `source` field (should be null for direct queries)

**Example Error**:
```
Entity 'my_table': type 'sql' requires 'data_source' field
Entity 'my_table': type 'sql' requires 'query' field
Entity 'my_table': 'query' field is empty
```

**Example Valid Configuration**:
```yaml
my_table:
  type: sql
  data_source: sead
  query: |
    select id, name from tbl_data
```

### 2. DataSourceExistsSpecification

**Purpose**: Validates that all referenced data sources exist in `options.data_sources`.

**Checks**:
- Entity `data_source` references must exist in configuration
- Append configuration `data_source` references must exist
- Catches typos and missing data source definitions

**Example Error**:
```
Entity 'my_table': references non-existent data source 'sead_db'
Entity 'my_table', append item #1: references non-existent data source 'lookup_db'
```

**Example Valid Configuration**:
```yaml
entities:
  my_table:
    type: sql
    data_source: sead  # Must exist in options.data_sources
    query: select * from tbl_data

options:
  data_sources:
    sead:
      driver: postgresql
      host: localhost
      database: sead_db
```

### 3. Enhanced FixedDataSpecification

**Improvements**:
- Now explicitly requires `values` field for fixed-type entities
- Now explicitly requires `columns` field for fixed-type entities
- Validates that each value row is a list
- Better error messages for mismatched column counts

**Example Error**:
```
Entity 'lookup_table': type 'fixed' requires 'values' field
Entity 'lookup_table': type 'fixed' requires 'columns' field
Entity 'lookup_table': value row 1 has 3 items but 2 columns defined
```

### 4. Enhanced AppendConfigurationSpecification

**Improvements**:
- Validates `append_mode` is either 'all' or 'distinct'
- Type-specific validation:
  - `type: fixed` requires `values`
  - `type: sql` requires `query` and `data_source`
- Validates source entity references exist
- Provides detailed error messages with append item index

**Example Error**:
```
Entity 'my_table': invalid append_mode 'some_mode' (must be 'all' or 'distinct')
Entity 'my_table', append item #1: type 'fixed' requires 'values' field
Entity 'my_table', append item #2: type 'sql' requires 'query' field
Entity 'my_table', append item #3: references non-existent source entity 'missing_entity'
```

## Updated Validation Order

The `CompositeConfigSpecification` now runs validators in this order:

1. **RequiredFieldsSpecification** - Check basic required fields
2. **EntityExistsSpecification** - Validate entity references
3. **CircularDependencySpecification** - Detect circular dependencies
4. **DataSourceExistsSpecification** - Validate data source references (NEW)
5. **SqlDataSpecification** - Validate SQL entity configurations (NEW)
6. **FixedDataSpecification** - Validate fixed entity configurations (ENHANCED)
7. **ForeignKeySpecification** - Validate foreign key configurations
8. **UnnestSpecification** - Validate unnest configurations
9. **DropDuplicatesSpecification** - Validate drop_duplicates configurations
10. **SurrogateIdSpecification** - Validate surrogate ID conventions
11. **AppendConfigurationSpecification** - Validate append configurations (ENHANCED)

## Additional Suggested Validations

Here are additional validation checks that could be implemented:

### 5. ColumnConsistencySpecification

**Purpose**: Validate that columns referenced in various configurations actually exist.

**Checks**:
- Foreign key `local_keys` exist in entity's keys + columns
- Foreign key `remote_keys` exist in remote entity's keys + columns
- Unnest `id_vars` exist in entity's columns
- Unnest `value_vars` exist in entity's columns
- Filter column references are valid

### 6. DependencyConsistencySpecification

**Purpose**: Ensure `depends_on` matches actual data dependencies.

**Checks**:
- If entity references another in `source`, that entity should be in `depends_on`
- If entity has foreign keys to another entity, that entity should be in `depends_on`
- Warn about missing dependencies that could cause runtime errors

### 7. QuerySyntaxSpecification

**Purpose**: Basic SQL query syntax validation.

**Checks**:
- Query is not empty
- Query doesn't contain obvious syntax errors
- Query mentions columns that are in the `columns` configuration
- Warn about SELECT * queries (prefer explicit columns)

### 8. ReplacementSpecification

**Purpose**: Validate replacement configurations.

**Checks**:
- Replacement column names exist in entity's columns
- Replacement values are properly formatted dictionaries
- Warn about replacements that might not match any data

### 9. FilterSpecification

**Purpose**: Validate filter configurations.

**Checks**:
- Filter type is valid ('exists_in', etc.)
- Required filter parameters are present
- Referenced entities in filters exist
- Column names in filters are valid

### 10. NamingConventionSpecification

**Purpose**: Enforce naming conventions across the configuration.

**Checks**:
- Entity names use snake_case
- Column names use snake_case
- Foreign key columns follow naming pattern (e.g., entity_id)
- Surrogate IDs end with '_id'
- Warn about extremely long names

### 11. DataTypeConsistencySpecification

**Purpose**: Validate data type consistency in fixed data.

**Checks**:
- Fixed data values match expected types for columns
- Date formats are consistent
- Numeric values are properly formatted
- Warn about mixed types in the same column

### 12. AppendColumnMatchSpecification

**Purpose**: Validate that append data matches entity columns.

**Checks**:
- Append fixed data has same columns as entity
- Append SQL query returns expected columns
- Source entity used in append has compatible columns
- Warn about column mismatches that will cause runtime errors

## Usage

All validations are automatically run when a configuration is loaded:

```python
from src.config_model import TablesConfig
from src.specifications import CompositeConfigSpecification

# Load configuration
config = TablesConfig(entities_cfg=config_dict, options=options)

# Validate configuration
validator = CompositeConfigSpecification()
is_valid = validator.is_satisfied_by(config_dict)

if not is_valid:
    print(validator.get_report())
```

## Benefits

1. **Early Error Detection**: Catch configuration errors before runtime
2. **Better Error Messages**: Clear, actionable error messages with context
3. **Type Safety**: Ensure type-specific requirements are met
4. **Consistency**: Enforce consistent configuration patterns
5. **Documentation**: Validation rules serve as implicit documentation
6. **Maintainability**: Easier to refactor knowing validations will catch issues

## Testing

Run validation tests:

```bash
# Run all specification tests
uv run pytest tests/test_specifications.py -v

# Run specific test
uv run pytest tests/test_specifications.py::TestSqlDataSpecification -v
```

## Configuration Reference

See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for complete configuration documentation with validation requirements.
