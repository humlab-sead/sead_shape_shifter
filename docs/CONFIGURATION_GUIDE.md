# Project Guide - Shape Shifter

## Overview

This comprehensive guide describes the YAML configuration format used by the Shape Shifter data transformation framework. Shape Shifter is a general-purpose system for harmonizing input data from diverse sources (spreadsheets, databases, fixed values) into a target schema through declarative configuration.

This guide consolidates all configuration documentation including:
- **Entity Project**: Structure, properties, and relationship definitions
- **Foreign Key Constraints**: Comprehensive validation and data quality enforcement  
- **Append Project**: Union/concatenation of multiple data sources
- **Project Validation**: Specification-based validation system with 9 validators
- **Complete Examples**: Real-world configuration patterns and best practices

## Architecture

The normalization system follows a multi-phase pipeline:

1. **Extract**: Extract subsets from source data (spreadsheet, SQL, fixed values)
2. **Link**: Establish foreign key relationships between entities
3. **Unnest**: Transform wide-format data to long-format (melt operation)
4. **Translate**: Map column names to target schema
5. **Store**: Write to target format (Excel, CSV, database)

### Key Components

- **ProcessState**: Handles topological sorting and dependency resolution
- **ShapeShifter**: Orchestrates the normalization pipeline
- **ShapeShiftProject**: Project model for all entities and their relationships
- **SubsetService**: Extracts data subsets with column selection and transformations

---

## Project File Structure

A configuration file consists of three main sections:

```yaml
entities:          # Entity definitions (required)
  entity_name:
    # Entity configuration

options:           # Global options (optional)
  translations:    # Column name translations
  data_sources:    # Database connections

mappings:          # Remote entity mappings (optional)
```

---

## Entity Project

Each entity represents a table/dataset to be extracted and processed. Entities are processed in dependency order using topological sorting.

### Basic Entity Structure

```yaml
entities:
  entity_name:
    # Identity & Keys
    surrogate_id: string              # Primary key column name
    surrogate_name: string             # Alternative name for surrogate ID
    keys: [string, ...]               # Natural key columns
    
    # Data Selection
    source: string | null             # Source entity or null for root source
    type: "data" | "fixed" | "sql"    # Data source type
    columns: [string, ...]            # Columns to extract
    
    # Data Quality
    drop_duplicates: bool | [string, ...] # Duplicate handling
    drop_empty_rows: bool | [string, ...] | {string: [any, ...]}  # Empty row handling
    check_column_names: bool              # Validate column names match (SQL sources)
    
    # Filtering
    filters: [...]                        # Post-load data filters
    
    # Value Transformations
    replacements: {string: {any: any}}    # Value replacement mappings
    
    # Relationships
    foreign_keys: [...]               # Foreign key definitions
    depends_on: [string, ...]         # Dependency list
    
    # Transformations
    unnest: {...}                     # Unnesting configuration
    extra_columns: {...}              # Additional columns to add
    
    # Data Sources
    data_source: string               # Named data source (for SQL)
    values: string | [...]            # Fixed values or SQL query
```

---

## Property Reference

### Identity Properties

#### `surrogate_id`
- **Type**: `string`
- **Required**: No (but recommended)
- **Description**: Name of the surrogate primary key column to be generated. The system will create an integer ID starting from 1.
- **Example**:
  ```yaml
  surrogate_id: site_id
  ```

#### `surrogate_name`
- **Type**: `string`
- **Required**: No
- **Description**: Alternative name for the surrogate ID column. Used when the surrogate ID should be named differently than the generated ID.
- **Example**:
  ```yaml
  surrogate_name: contact_type
  ```

#### `keys`
- **Type**: `list[string]`
- **Required**: No
- **Description**: Natural key columns that uniquely identify rows in the source data. Used for duplicate detection and foreign key relationships.
- **Example**:
  ```yaml
  keys: ["ProjektNr", "Befu"]
  ```

---

### Data Source Properties

#### `source`
- **Type**: `string | null`
- **Required**: No (defaults to root survey data)
- **Description**: Specifies which entity's output should be used as input. `null` or omitted means use the root source data.
- **Example**:
  ```yaml
  # Use output from 'method' entity as source
  source: method
  
  # Use root survey data (default)
  source: null
  ```

#### `type`
- **Type**: `"data" | "fixed" | "sql"`
- **Required**: No (defaults to `"data"`)
- **Description**: 
  - `"data"`: Extract from source data (spreadsheet or another entity)
  - `"fixed"`: Use fixed/hardcoded values defined in `values`
  - `"sql"`: Execute SQL query against a database (requires `data_source` and `query`)
- **Requirements by Type**:
  - `type: fixed` → requires `values` (list of lists)
  - `type: sql` → requires `data_source` and `query`
  - `type: data` → uses `source` (defaults to root data if omitted)
- **Example**:
  ```yaml
  # Fixed lookup table
  type: fixed
  values:
    - ["value1", "desc1"]
    - ["value2", "desc2"]
  
  # SQL query
  type: sql
  data_source: sead
  query: |
    select id, name
    from tbl_dimensions
  ```

#### `data_source`
- **Type**: `string`
- **Required**: Yes when `type: sql`
- **Description**: Name of the data source connection defined in `options.data_sources`. The data source specifies database connection parameters (host, database, credentials, driver, etc.).
- **Validation**: The referenced data source must exist in `options.data_sources`
- **Example**:
  ```yaml
  data_source: sead  # Must be defined in options.data_sources
  ```

#### `query`
- **Type**: `string`
- **Required**: Yes when `type: sql`
- **Description**: SQL query string to execute against the data source. Typically uses multi-line format with `|` or `>` for readability.
- **Validation**: Must be non-empty when `type: sql`
- **Example**:
  ```yaml
  type: sql
  data_source: arbodat_data
  query: |
    select column1, column2
    from table_name
    where condition = true
  ```

#### `values`
- **Type**: `list[list[any]]`
- **Required**: Yes when `type: fixed`
- **Description**: 2D array of fixed values for lookup tables. Each inner list represents a row of data.
- **Validation**: 
  - Required when `type: fixed`
  - Each row must have the same number of columns as defined in `columns`
  - Number of values per row should match the number of columns
- **Example**:
  ```yaml
  type: fixed
  columns: ["code", "description"]
  values:
    - ["Type A", "Description A"]
    - ["Type B", "Description B"]
  ```

---

### Column Selection Properties

#### `columns`
- **Type**: `list[string] | string`
- **Required**: No (but typically needed)
- **Description**: List of columns to extract from the source. Can also reference other entity properties using `@value:` syntax.
- **Example**:
  ```yaml
  # Explicit list
  columns: ["ArchDat", "ArchDat_Beschreibung"]
  
  # Reference another entity's keys
  columns: "@value: entities.site.keys"
  ```

#### `extra_columns`
- **Type**: `dict[string, string | Any]`
- **Required**: No
- **Description**: Additional columns to add to the entity. Keys are new column names. Values can be:
  - A source column name (string) - copies that column
  - Any other value - creates a constant column with that value
- **Example**:
  ```yaml
  extra_columns:
    # Copy BefuTyp column to new column
    feature_type_name: "BefuTyp"
    # Create constant null column
    feature_type_description: null
    # Create constant value column
    default_status: "active"
  ```

---

### Data Quality Properties

#### `drop_duplicates`
- **Type**: `bool | list[string] | string`
- **Required**: No (defaults to `false`)
- **Description**: Controls duplicate row removal:
  - `true`: Drop all duplicate rows
  - `false`: Keep all rows
  - `list[string]`: Drop duplicates based on specified columns
  - `string` with `@value:`: Reference another entity's keys
- **Example**:
  ```yaml
  # Drop all duplicates
  drop_duplicates: true
  
  # Drop duplicates based on keys
  drop_duplicates: ["ProjektNr", "Befu"]
  
  # Reference another entity's keys
  drop_duplicates: "@value: entities.site.keys"
  ```

#### `drop_empty_rows`
- **Type**: `bool | list[string] | dict[string, list[any]]`
- **Required**: No (defaults to `false`)
- **Description**: Controls empty row removal. Empty values include `NaN`, `None`, and empty strings (`""`):
  - `true`: Drop rows where all columns are empty
  - `false`: Keep all rows
  - `list[string]`: Drop rows where all specified columns are empty
  - `dict[string, list[any]]`: Drop rows where specified columns contain the given values. Keys are column names, values are lists of values to treat as empty for that column (e.g., `[null, ""]`)
- **Note**: Empty strings are automatically treated as `pd.NA` before checking for empty rows (unless using dict format with custom empty values)
- **Example**:
  ```yaml
  # Drop completely empty rows (including rows with only empty strings)
  drop_empty_rows: true
  
  # Drop rows where specific columns are all empty or empty strings
  drop_empty_rows: ["name", "description"]
  
  # Drop rows where specific columns contain custom "empty" values
  drop_empty_rows:
    abundance_property_value: [null, ""]
    status: [null, "", "unknown", "N/A"]
  ```

#### `check_column_names`
- **Type**: `bool`
- **Required**: No (defaults to `true`)
- **Description**: For SQL data sources, controls whether to validate column names match the configuration:
  - `true`: Validates that SQL result columns exactly match the configured `keys` and `columns`. Raises error on mismatch.
  - `false`: Only validates that the number of columns matches. Automatically renames SQL columns to match configuration.
- **Use Case**: Set to `false` when SQL column names don't match target schema but have the same structure (e.g., in `append` configurations)
- **Example**:
  ```yaml
  contact:
    type: sql
    columns: ["contact_name", "contact_type"]
    check_column_names: false  # SQL returns different column names
    values: |\n      sql: \n      select [BotBest], \"BotBest\" from [Befunde]
  ```

#### `filters`
- **Type**: `list[dict]`
- **Required**: No
- **Description**: List of post-load filters to apply after data extraction. Filters run sequentially and can reference other entities in the data store.
- **Available Filters**:
  - `exists_in`: Keep only rows where a column value exists in another entity's column
- **Example**:
  ```yaml
  filters:
    - type: exists_in
      column: "PCODE"              # Local column to filter
      other_entity: "_pcodes"      # Entity to check against
      other_column: "PCODE"        # Column in other entity (optional, defaults to same name)
      drop_duplicates: ["PCODE"]  # Optional: drop duplicates after filtering
  ```

#### `replacements`
- **Type**: `dict[string, dict[any, any]]`
- **Required**: No
- **Description**: Defines value replacement mappings for specified columns. Each key is a column name, and each value is a dictionary mapping old values to new values. This is useful for normalizing data values, converting codes to standardized formats, or correcting inconsistent data.
- **Use Cases**:
  - Converting coordinate system names to EPSG codes
  - Standardizing status codes or category names
  - Mapping legacy identifiers to new ones
  - Correcting typos or inconsistent values in source data
- **Note**: Replacements are applied after column extraction but before other operations. Values not in the mapping remain unchanged.
- **Example**:
  ```yaml
  site:
    columns: ["site_name", "coordinate_system"]
    replacements:
      coordinate_system:
        "DHDN Gauss-Krüger Zone 3": "EPSG:31467"
        "RGF93 Lambert 93": "EPSG:2154"
        "CH1903/Swiss grid": "EPSG:21781"
  
  # Multiple columns can be replaced
  sample:
    columns: ["status", "type"]
    replacements:
      status:
        "old": "legacy"
        "new": "current"
      type:
        "A": "Type_A"
        "B": "Type_B"
  
  # Replacements can reference external project files
  site:
    replacements:
      coordinate_system: "@value: replacements.site.KoordSys"
  ```
- **See**: Filters section below for detailed filter documentation

---

### Relationship Properties

#### `depends_on`
- **Type**: `list[string]`
- **Required**: Yes (can be empty list)
- **Description**: List of entity names that must be processed before this entity. Used for topological sorting to ensure correct processing order.
- **Example**:
  ```yaml
  # Process site and feature_type before this entity
  depends_on: ["site", "feature_type"]
  
  # No dependencies (root entity)
  depends_on: []
  ```

#### `foreign_keys`
- **Type**: `list[ForeignKeyConfig]`
- **Required**: No
- **Description**: List of foreign key relationships to establish. Each foreign key links this entity to another entity.
- **See**: Foreign Key Project section below

---

### Foreign Key Project

Foreign keys establish relationships between entities by linking local keys to remote keys.

#### Basic Foreign Key Structure

```yaml
foreign_keys:
  - entity: string                  # Remote entity name (required)
    local_keys: [string, ...]       # Local columns to match (required)
    remote_keys: [string, ...]      # Remote columns to match (required)
    how: "inner" | "left" | ...     # Join type (optional)
    extra_columns: {...}            # Extra columns to bring (optional)
    drop_remote_id: bool            # Drop remote ID after linking (optional)
    constraints: {...}              # Validation constraints (optional)
```

#### Foreign Key Properties

##### `entity`
- **Type**: `string`
- **Required**: Yes
- **Description**: Name of the remote entity to link to
- **Example**:
  ```yaml
  entity: site
  ```

##### `local_keys`
- **Type**: `list[string] | string`
- **Required**: Yes (except for cross joins)
- **Description**: Column names in the local entity to match against remote keys. Can use `@value:` to reference another entity's keys.
- **Example**:
  ```yaml
  local_keys: ["ProjektNr"]
  # Or reference another entity
  local_keys: "@value: entities.site.keys"
  ```

##### `remote_keys`
- **Type**: `list[string] | string`
- **Required**: Yes (except for cross joins)
- **Description**: Column names in the remote entity to match against local keys. Must have same length as `local_keys`.
- **Example**:
  ```yaml
  remote_keys: ["ProjektNr"]
  ```

##### `how`
- **Type**: `"inner" | "left" | "right" | "outer" | "cross"`
- **Required**: No (defaults to `"inner"`)
- **Description**: Type of join operation (follows pandas merge semantics):
  - `inner`: Keep only matching rows (default)
  - `left`: Keep all left rows, add nulls for non-matches
  - `right`: Keep all right rows
  - `outer`: Keep all rows from both
  - `cross`: Cartesian product (no keys needed)
- **Example**:
  ```yaml
  how: left
  ```

##### `extra_columns`
- **Type**: `dict[string, string]`
- **Required**: No
- **Description**: Additional columns to bring from the remote entity. Format is `{"local_name": "remote_column_name"}`.
- **Example**:
  ```yaml
  extra_columns:
    taxa_name: "Taxon"
    taxa_author: "Autor"
  ```

##### `drop_remote_id`
- **Type**: `bool`
- **Required**: No (defaults to `false`)
- **Description**: If `true`, drops the remote surrogate ID column after linking (useful when only extra columns are needed).
- **Example**:
  ```yaml
  drop_remote_id: true
  ```

##### `constraints`
- **Type**: `ForeignKeyConstraints`
- **Required**: No
- **Description**: Validation constraints for the foreign key relationship. See Foreign Key Constraints section below.

---

### Foreign Key Constraints

Constraints validate foreign key relationships during the linking phase. They help ensure data integrity and catch configuration errors.

#### Constraint Structure

```yaml
foreign_keys:
  - entity: remote_entity
    # ... other FK config ...
    constraints:
      # Cardinality
      cardinality: "one_to_one" | "many_to_one" | "one_to_many" | "many_to_many"
      
      # Match Requirements
      allow_unmatched_left: bool
      allow_unmatched_right: bool
      
      # Key Uniqueness
      require_unique_left: bool
      require_unique_right: bool
      allow_null_keys: bool
      
      # Row Count
      allow_row_decrease: bool
```

#### Cardinality Constraints

##### `cardinality`
- **Type**: `"one_to_one" | "many_to_one" | "one_to_many" | "many_to_many"`
- **Description**: Defines the expected relationship type
- **Validation**:
  - `one_to_one`: Both sides must have unique keys
  - `many_to_one`: Right side must have unique keys
  - `one_to_many`: Left side must have unique keys
  - `many_to_many`: No uniqueness requirements
- **Example**:
  ```yaml
  constraints:
    cardinality: many_to_one
  ```

#### Match Constraints

##### `allow_unmatched_left`
- **Type**: `bool`
- **Description**: Whether to allow rows in the left (local) table with no match in the right (remote) table
- **Example**:
  ```yaml
  constraints:
    allow_unmatched_left: true
  ```

##### `allow_unmatched_right`
- **Type**: `bool`
- **Description**: Whether to allow rows in the right (remote) table with no match in the left (local) table
- **Example**:
  ```yaml
  constraints:
    allow_unmatched_right: false
  ```

#### Uniqueness Constraints

##### `require_unique_left`
- **Type**: `bool`
- **Description**: If `true`, the local key columns must be unique (no duplicates)
- **Example**:
  ```yaml
  constraints:
    require_unique_left: true
  ```

##### `require_unique_right`
- **Type**: `bool`
- **Description**: If `true`, the remote key columns must be unique (no duplicates)
- **Example**:
  ```yaml
  constraints:
    require_unique_right: true
  ```

##### `allow_null_keys`
- **Type**: `bool`
- **Default**: `true`
- **Description**: Whether to allow null values in key columns
- **Example**:
  ```yaml
  constraints:
    allow_null_keys: false
  ```

#### Row Count Constraints

##### `allow_row_decrease`
- **Type**: `bool`
- **Description**: Whether to allow the row count to decrease after merge
- **Example**:
  ```yaml
  constraints:
    allow_row_decrease: false
  ```

---

### Foreign Key Constraints

Foreign key constraints provide robust validation and data quality enforcement during relationship linking. Constraints ensure that foreign key relationships meet specified requirements and help catch data quality issues early.

#### Overview

Constraints are optional but highly recommended for production configurations. They provide:
- **Data validation**: Enforce cardinality, uniqueness, and match requirements
- **Quality monitoring**: Detect and report data quality issues
- **Documentation**: Make relationship expectations explicit
- **Safe changes**: Enable gradual constraint adoption without breaking existing configs

#### Constraint Project Structure

```yaml
foreign_keys:
  - entity: remote_entity
    local_keys: [key1]
    remote_keys: [key1]
    how: left
    constraints:
      # Cardinality constraints
      cardinality: one_to_one | many_to_one | one_to_many | many_to_many
      
      # Match requirements
      allow_unmatched_left: false    # Require all local rows to match
      allow_unmatched_right: true    # Allow unmatched remote rows
      
      # Data quality constraints  
      require_unique_left: false     # Require unique local keys
      require_unique_right: true     # Require unique remote keys
      allow_null_keys: false         # Allow null foreign keys
      
      # Row validation
      allow_row_decrease: false      # Check for row count changes
```

#### Constraint Types

##### Cardinality Constraints

Specifies the expected relationship cardinality between entities:

**`one_to_one`**
- Each local row matches exactly one remote row
- Each remote row matched by at most one local row
- Implies: `require_unique_left: true`, `require_unique_right: true`
- Use case: Employee to employee details, site to location

```yaml
# Example: Employee has one set of details
foreign_keys:
  - entity: employee_details
    local_keys: [employee_id]
    remote_keys: [employee_id]
    how: inner
    constraints:
      cardinality: one_to_one
      allow_unmatched_left: false  # Every employee must have details
```

**`many_to_one`** (Most common)
- Multiple local rows can reference the same remote row
- Each local row matches exactly one remote row
- Implies: `require_unique_right: true`, `require_unique_left: false`
- Use case: Samples to sample types, features to sites

```yaml
# Example: Many samples reference one sample type
foreign_keys:
  - entity: sample_type
    local_keys: [sample_type_id]
    remote_keys: [sample_type_id]
    how: inner
    constraints:
      cardinality: many_to_one
      allow_unmatched_left: false  # Every sample must have a type
```

**`one_to_many`**
- Each local row can be matched by multiple remote rows (row expansion)
- Each remote row matches at most one local row
- Implies: `require_unique_left: true`, `require_unique_right: false`
- Use case: Orders to order items, sites to site observations

```yaml
# Example: One order has many items (expansion OK)
foreign_keys:
  - entity: order_items  
    local_keys: [order_id]
    remote_keys: [order_id]
    how: left
    constraints:
      cardinality: one_to_many
      allow_row_decrease: false  # Don't allow losing orders
```

**`many_to_many`**
- Multiple local rows can match multiple remote rows
- No uniqueness constraints
- Implies: `require_unique_left: false`, `require_unique_right: false`
- Use case: Students to courses (junction tables)

```yaml
# Example: Many students in many courses
foreign_keys:
  - entity: courses
    local_keys: [course_id]
    remote_keys: [course_id]
    how: inner
    constraints:
      cardinality: many_to_many
```

##### Match Requirements

Control whether unmatched rows are allowed after the join:

**`allow_unmatched_left`**
- **Type**: `bool`
- **Default**: Inferred from `how` and `cardinality`
- **Description**: Allow local rows with no match in remote entity
  - `false`: All local rows must match remote rows (enforces referential integrity)
  - `true`: Local rows can have unmatched foreign keys (warning only)
- **Use with**: `how: inner` or `how: left`
- **Common patterns**:
  - `false` for required relationships (every sample must have a type)
  - `true` for optional relationships (site may have optional location)

```yaml
# Strict: Every sample MUST reference a valid sample type
foreign_keys:
  - entity: sample_type
    local_keys: [type_code]
    remote_keys: [type_code]
    how: inner  # Use inner join
    constraints:
      allow_unmatched_left: false  # Enforce match requirement
      
# Lenient: Samples can have unknown types (with warning)
foreign_keys:
  - entity: sample_type
    local_keys: [type_code]
    remote_keys: [type_code]
    how: left  # Use left join to keep unmatched
    constraints:
      allow_unmatched_left: true  # Allow but warn about unmatched
```

**`allow_unmatched_right`**
- **Type**: `bool`
- **Default**: `true`
- **Description**: Allow remote rows that aren't referenced by any local row
  - `false`: All remote rows must be used by at least one local row
  - `true`: Remote lookup tables can have unused entries
- **Common pattern**: Usually `true` for lookup tables

**Error Example**:
```
ForeignKeyConstraintViolation: Feature linking violation:
- Entity 'feature' linking to 'feature_type'
- 5 local rows have no match in remote entity
- Unmatched values in 'type_code': ['Unknown', 'Legacy', ...]
- Set allow_unmatched_left: true to allow this
```

##### Data Quality Constraints

Enforce uniqueness and null-handling requirements:

**`require_unique_left`**
- **Type**: `bool`
- **Default**: Inferred from `cardinality`
- **Description**: Require local foreign key values to be unique
  - `false`: Multiple local rows can have the same foreign key (many-to-one OK)
  - `true`: Each local row must have a unique foreign key (one-to-one required)
- **Use case**: Enforce one-to-one relationships, detect duplicate keys

```yaml
# Each employee should have unique ID
foreign_keys:
  - entity: employee_details
    local_keys: [employee_id]
    remote_keys: [employee_id]
    how: inner
    constraints:
      require_unique_left: true  # Catch duplicate employees
```

**`require_unique_right`**
- **Type**: `bool`
- **Default**: Inferred from `cardinality`
- **Description**: Require remote entity keys to be unique
  - `false`: Remote entity can have duplicate keys (unusual)
  - `true`: Remote entity must have unique keys (standard for lookup tables)
- **Use case**: Validate integrity of lookup tables and reference data

```yaml
# Sample types should have unique codes
foreign_keys:
  - entity: sample_type
    local_keys: [type_code]
    remote_keys: [type_code]
    how: left
    constraints:
      require_unique_right: true  # Detect duplicate type codes
```

**`allow_null_keys`**
- **Type**: `bool`
- **Default**: `true`
- **Description**: Allow NULL/NaN values in foreign key columns
  - `false`: Raise error if local foreign key contains nulls
  - `true`: Allow null foreign keys (treated as unmatched)
- **Interaction**: When `false` + `allow_unmatched_left: false`, ensures all rows have valid non-null foreign keys
- **Use case**: Enforce mandatory relationships, detect missing reference data

```yaml
# Every sample MUST have a non-null type
foreign_keys:
  - entity: sample_type
    local_keys: [type_id]
    remote_keys: [type_id]
    how: inner
    constraints:
      allow_null_keys: false          # No null types allowed
      allow_unmatched_left: false     # And type must exist
```

##### Row Validation Constraints

**`allow_row_decrease`**
- **Type**: `bool`
- **Default**: `true`
- **Description**: Allow the entity's row count to decrease after this foreign key link
  - `false`: Raise error if join reduces row count (data loss detection)
  - `true`: Allow row decrease (normal for inner joins)
- **Use case**: Catch accidental filtering from inner joins, validate one-to-many expansions
- **Common pattern**: Set to `false` for left joins to detect unexpected data loss

```yaml
# Linking site to location should not lose sites
foreign_keys:
  - entity: location
    local_keys: [location_id]
    remote_keys: [location_id]
    how: left  # Keep all sites
    constraints:
      allow_row_decrease: false  # Error if we lose sites
      
# Inner join is expected to filter rows
foreign_keys:
  - entity: valid_types
    local_keys: [type_code]
    remote_keys: [type_code]
    how: inner  # Intentionally filter to valid types
    constraints:
      allow_row_decrease: true  # This is expected
```

#### Constraint Combinations and Patterns

##### Strict Many-to-One (Most Common)

Every local row must reference exactly one remote row from a lookup table:

```yaml
sample:
  depends_on: [sample_type]
  foreign_keys:
    - entity: sample_type
      local_keys: [type_code]
      remote_keys: [type_code]
      how: inner
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false  # Every sample must have type
        allow_null_keys: false       # Type cannot be null
        require_unique_right: true   # Types must be unique (implied by cardinality)
```

##### Optional Reference with Quality Monitoring

Allow unmatched foreign keys but warn about them:

```yaml
site:
  depends_on: [location]
  foreign_keys:
    - entity: location
      local_keys: [location_id]
      remote_keys: [location_id]
      how: left
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: true   # Sites can lack location
        allow_null_keys: true        # NULL location_id is OK
        require_unique_right: true   # But valid locations must be unique
```

**Result**: Sites without matching locations are kept with a warning showing which location_ids were not found.

##### Strict One-to-One Relationship

Each local row must match exactly one remote row, and vice versa:

```yaml
employee:
  depends_on: [employee_details]
  foreign_keys:
    - entity: employee_details
      local_keys: [employee_id]
      remote_keys: [employee_id]
      how: inner
      constraints:
        cardinality: one_to_one
        allow_unmatched_left: false   # Every employee must have details
        require_unique_left: true     # Each employee appears once (implied)
        require_unique_right: true    # Each detail set appears once (implied)
```

##### Controlled One-to-Many Expansion

Allow row expansion but ensure we don't lose base records:

```yaml
order:
  depends_on: [order_items]
  foreign_keys:
    - entity: order_items
      local_keys: [order_id]
      remote_keys: [order_id]
      how: left
      constraints:
        cardinality: one_to_many
        allow_row_decrease: false     # Don't lose any orders
        allow_unmatched_left: true    # Orders without items OK
```

##### Complex Multi-Constraint Validation

Combine multiple constraints for robust validation:

```yaml
sample_analysis:
  depends_on: [sample, analysis_method, lab]
  foreign_keys:
    # Required: sample must exist
    - entity: sample
      local_keys: [sample_id]
      remote_keys: [sample_id]
      how: inner
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false
        allow_null_keys: false
        
    # Required: method must exist  
    - entity: analysis_method
      local_keys: [method_code]
      remote_keys: [method_code]
      how: inner
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false
        require_unique_right: true
        
    # Optional: lab reference (with monitoring)
    - entity: lab
      local_keys: [lab_id]
      remote_keys: [lab_id]
      how: left
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: true  # Warn if lab unknown
        allow_null_keys: true       # NULL lab is OK
```

#### Gradual Constraint Adoption

Start without constraints, then add them incrementally:

**Phase 1: No Constraints (Initial Setup)**
```yaml
sample:
  foreign_keys:
    - entity: sample_type
      local_keys: [type_code]
      remote_keys: [type_code]
      how: left  # Permissive join
```

**Phase 2: Add Quality Monitoring**
```yaml
sample:
  foreign_keys:
    - entity: sample_type
      local_keys: [type_code]
      remote_keys: [type_code]
      how: left
      constraints:
        require_unique_right: true  # Detect duplicate types
        allow_unmatched_left: true  # Warn about unmatched
```

**Phase 3: Enforce Data Quality**
```yaml
sample:
  foreign_keys:
    - entity: sample_type
      local_keys: [type_code]
      remote_keys: [type_code]
      how: inner  # Stricter join
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false  # Now require matches
        allow_null_keys: false       # And no nulls
```

#### Error Messages and Debugging

Constraint violations provide detailed diagnostic information:

**Cardinality Violation:**
```
ForeignKeyConstraintViolation: Employee-to-details cardinality violation:
- Expected: one_to_one
- Found: 3 employees with multiple detail records
- Duplicate employee_ids: [101, 205, 387]
- This violates the unique left key requirement
```

**Match Requirement Violation:**
```
ForeignKeyConstraintViolation: Sample linking violation:
- Entity 'sample' linking to 'sample_type'
- 12 local rows have no match in remote entity
- Unmatched type_codes: ['UNKN', 'OLD_TYPE', 'TEMP']
- Set allow_unmatched_left: true to allow (with warning)
```

**Null Key Violation:**
```
ForeignKeyConstraintViolation: Sample foreign key validation failed:
- 5 rows have NULL values in foreign key column 'type_id'
- Set allow_null_keys: true to permit null foreign keys
```

**Row Decrease Violation:**
```
ForeignKeyConstraintViolation: Row count decreased unexpectedly:
- Entity: site  
- Before: 150 rows
- After: 142 rows
- Lost: 8 rows during foreign key link to 'location'
- Set allow_row_decrease: true if this is intended
```

#### Best Practices

1. **Start with cardinality**: Define expected relationship type first
2. **Use strict constraints in production**: Catch data issues early
3. **Allow flexibility during development**: Use permissive settings initially
4. **Monitor warnings**: Review unmatched row warnings even with permissive settings
5. **Document expectations**: Constraints serve as inline documentation
6. **Test incrementally**: Add one constraint at a time to isolate issues
7. **Validate lookup tables**: Always set `require_unique_right: true` for reference data

#### Performance Considerations

Constraints add minimal overhead:
- **Validation timing**: After merge, before next processing stage
- **Memory impact**: Negligible (uses merge indicator columns)
- **Processing time**: ~1-5% increase for most datasets
- **Trade-off**: Small performance cost for significant data quality benefit

---

### Unnest Project

Unnesting transforms wide-format data to long-format using pandas' `melt` operation. This is useful for normalizing attribute-value pairs.

#### Unnest Structure

```yaml
unnest:
  id_vars: [string, ...]        # Columns to keep as identifiers
  value_vars: [string, ...]     # Columns to melt into rows
  var_name: string              # Name for variable column
  value_name: string            # Name for value column
```

#### Unnest Properties

##### `id_vars`
- **Type**: `list[string]`
- **Required**: No (defaults to empty list)
- **Description**: Columns to use as identifier variables (kept unchanged)
- **Example**:
  ```yaml
  id_vars: ["ProjektNr", "Befu"]
  ```

##### `value_vars`
- **Type**: `list[string]`
- **Required**: No (defaults to all non-id columns)
- **Description**: Columns to unpivot/melt into rows
- **Example**:
  ```yaml
  value_vars: ["ArchAusg", "ArchBear", "BotBear", "Aut", "BotBest"]
  ```

##### `var_name`
- **Type**: `string`
- **Required**: Yes
- **Description**: Name of the new column that will contain the original column names
- **Example**:
  ```yaml
  var_name: contact_type
  ```

##### `value_name`
- **Type**: `string`
- **Required**: Yes
- **Description**: Name of the new column that will contain the values
- **Example**:
  ```yaml
  value_name: contact_name
  ```

#### Unnest Example

**Before unnesting:**
```
| site_id | KoordX | KoordY | KoordZ |
|---------|--------|--------|--------|
| 1       | 100    | 200    | 50     |
| 2       | 150    | 250    | 75     |
```

**Project:**
```yaml
unnest:
  id_vars: ["site_id"]
  value_vars: ["KoordX", "KoordY", "KoordZ"]
  var_name: coordinate_type
  value_name: coordinate_value
```

**After unnesting:**
```
| site_id | coordinate_type | coordinate_value |
|---------|----------------|------------------|
| 1       | KoordX         | 100              |
| 1       | KoordY         | 200              |
| 1       | KoordZ         | 50               |
| 2       | KoordX         | 150              |
| 2       | KoordY         | 250              |
| 2       | KoordZ         | 75               |
```

---

## Options Section

The `options` section contains global configuration for translations and data sources.

### Translation Project

```yaml
options:
  translations:
    filename: string      # Path to translation file
    delimiter: string     # Delimiter character (default: "\t")
```

Translation files map source column names to target schema column names. Format is typically TSV with columns:
- `arbodat_field`: Source column name
- `english_column_name`: Target column name

**Example:**
```yaml
options:
  translations:
    filename: translations.tsv
    delimiter: "\t"
```

### Data Sources Project

```yaml
options:
  data_sources:
    source_name:
      driver: "postgres" | "ucanaccess"
      options:
        host: string
        port: int
        dbname: string
        username: string
        # ... driver-specific options
```

Data sources define database connections for SQL-type entities.

#### PostgreSQL Data Source

```yaml
options:
  data_sources:
    sead:
      driver: postgres
      options:
        host: ${SEAD_HOST}
        port: ${SEAD_PORT}
        dbname: ${SEAD_DBNAME}
        username: ${SEAD_USER}
```

Environment variables are supported using `${VAR_NAME}` syntax.

#### MS Access Data Source

```yaml
options:
  data_sources:
    arbodat_lookup:
      driver: ucanaccess
      options:
        path: /path/to/database.accdb
```

---

## Special Syntax

### `@value:` Reference Syntax

The `@value:` syntax allows referencing other configuration values dynamically.

**Format:**
```yaml
@value: entities.entity_name.property
```

**Examples:**
```yaml
# Reference another entity's keys
keys: "@value: entities.site.keys"

# Reference another entity's columns
columns: "@value: entities.contact_type.contact_types"

# Use in foreign key configuration
local_keys: "@value: entities.feature.keys"
remote_keys: "@value: entities.feature.keys"
```

**Benefits:**
- DRY (Don't Repeat Yourself) principle
- Single source of truth
- Automatic updates when referenced values change

### `@include:` Include Syntax

The `@include:` syntax allows splitting configuration across multiple files.

**Format:**
```yaml
@include: filename.yml
```

**Example:**
```yaml
options:
  data_sources:
    sead: "@include: sead-options.yml"
    arbodat_lookup: "@include: arbodat-lookup-options.yml"

mappings: "@include: mappings.yml"
```

### `@load:` Load Syntax

The `@load:` syntax loads external files (typically for translations).

**Format:**
```yaml
@load: path.to.property
```

**Example:**
```yaml
translation: "@load: options.translations"
```

---

## Append Project (Union/Concatenation)

The `append` feature allows combining data from multiple sources (fixed tables, SQL queries, other entities) into a single entity through row concatenation. This is useful for:
- Augmenting data tables with additional rows from different sources
- Unioning multiple spreadsheets or database tables
- Combining fixed lookup values with dynamic database content
- Building comprehensive datasets from heterogeneous sources

### Overview

The `append` property is added to entitys and specifies a list of additional data sources to concatenate with the primary entity data. Each append source can have its own configuration for data extraction, column selection, and data quality operations.

### Basic Append Structure

```yaml
entity_name:
  # Primary entity
  type: data | sql | fixed
  columns: [...]
  # ... other properties ...
  
  # Append additional sources
  append:
    - type: fixed | sql | data
      # Source-specific configuration
      # Inherits selected properties from parent entity
```

### Append Source Types

#### Fixed Value Append

Add fixed/hardcoded rows to the entity:

```yaml
sample_type:
  type: sql
  data_source: sead
  query: |
    SELECT type_id, type_name, description
    FROM sample_types
  columns: [type_id, type_name, description]
  
  append:
    - type: fixed
      values:
        - [999, "Unknown", "Unknown sample type"]
        - [1000, "Not Specified", "Type not specified"]
```

**Properties for `type: fixed`:**
- `type`: Must be `"fixed"`
- `values`: 2D array of values (list of lists)
- `columns`: Optional, inherits from parent if not specified
- Inherits: `drop_duplicates`, `drop_empty_rows`, `replacements`, `filters`

#### SQL Query Append

Append rows from a SQL query:

```yaml
contact:
  type: sql
  data_source: main_db
  query: |
    SELECT contact_id, name, email
    FROM active_contacts
  columns: [contact_id, name, email]
  
  append:
    - type: sql
      data_source: archive_db
      query: |
        SELECT contact_id, name, email  
        FROM archived_contacts
```

**Properties for `type: sql`:**
- `type`: Must be `"sql"`
- `data_source`: Required, data source name (can differ from parent)
- `query`: Required, SQL query string
- `columns`: Optional, inherits from parent if not specified
- `check_column_names`: Optional, defaults to parent's value
- Inherits: `drop_duplicates`, `drop_empty_rows`, `replacements`, `filters`

#### Data Source Append

Append rows extracted from another entity or data source:

```yaml
measurement:
  type: data
  source: survey_2023
  columns: [measurement_id, value, unit]
  
  append:
    - type: data
      source: survey_2024  # Different source entity
      columns: [measurement_id, value, unit]
```

**Properties for `type: data`:**
- `type`: Must be `"data"`
- `source`: Required, entity name to extract from
- `columns`: Optional, inherits from parent if not specified
- Inherits: `drop_duplicates`, `drop_empty_rows`, `replacements`, `filters`

### Property Inheritance

Append sources inherit certain properties from their parent entity to ensure consistent processing:

#### Inherited Properties
These properties are automatically inherited unless explicitly overridden:

- `columns`: Column names (if not specified in append source)
- `drop_duplicates`: Duplicate removal settings
- `drop_empty_rows`: Empty row removal settings
- `replacements`: Value replacement mappings
- `filters`: Post-load data filters
- `check_column_names`: Column name validation (for SQL sources)

**Example - Inherited columns:**
```yaml
sample_type:
  columns: [type_code, type_name]
  drop_duplicates: true
  
  append:
    - type: fixed
      # Inherits columns: [type_code, type_name]
      # Inherits drop_duplicates: true
      values:
        - ["UNKN", "Unknown"]
```

#### Non-Inherited Properties
These properties are specific to the parent entity and are NOT inherited:

- `surrogate_id`: Surrogate key generation (applied after concatenation)
- `keys`: Natural keys (validated after concatenation)
- `foreign_keys`: Foreign key relationships (established after concatenation)
- `unnest`: Unnesting/melting operations (applied after concatenation)
- `depends_on`: Processing dependencies
- `source`: Data source (append sources specify their own)
- `type`: Entity type (append sources must specify their own)

### Column Name Handling

#### Exact Column Match (Default)

By default, `check_column_names: true` enforces that SQL query results have columns matching the configuration exactly:

```yaml
contact:
  type: sql
  columns: [contact_name, contact_type]
  check_column_names: true  # Default
  query: |
    SELECT contact_name, contact_type
    FROM contacts
```

**Requirement**: SQL must return columns named exactly `contact_name` and `contact_type`.

#### Flexible Column Names

Set `check_column_names: false` to allow SQL queries with different column names. The system will:
1. Validate the number of columns matches
2. Automatically rename SQL columns to match the configuration

```yaml
contact:
  type: sql
  columns: [contact_name, contact_type]
  check_column_names: false  # Allow different SQL column names
  
  append:
    - type: sql
      data_source: external_db
      check_column_names: false  # Inherited from parent
      query: |
        SELECT name, type  # Different column names OK
        FROM external_contacts
```

**Result**: SQL columns `[name, type]` are automatically renamed to `[contact_name, contact_type]`.

**Use Cases**:
- Unioning tables with different column names but same structure
- Extracting from legacy databases with non-standard naming
- Combining data from multiple sources with varying schemas

### Complete Append Examples

#### Example 1: Union of Multiple Fixed Tables

Combine several fixed lookup tables into one entity:

```yaml
cultural_group:
  type: fixed
  columns: [cultural_group_id, cultural_group]
  keys: [cultural_group]
  surrogate_id: cultural_group_id
  drop_duplicates: true
  
  values:
    - [null, "Neolithic"]
    - [null, "Bronze Age"]
  
  append:
    - type: fixed
      values:
        - [null, "Iron Age"]
        - [null, "Roman"]
        
    - type: fixed
      values:
        - [null, "Medieval"]
        - [null, "Modern"]
```

**Processing**:
1. Load primary values (2 rows)
2. Append first fixed source (2 rows)
3. Append second fixed source (2 rows)
4. Remove duplicates if configured
5. Generate surrogate IDs (all 6 rows)

**Result**: 6 cultural groups with generated IDs 1-6.

#### Example 2: Spreadsheet + SQL + Fixed Data

Combine data from survey spreadsheet, database, and fixed values:

```yaml
sample:
  type: data
  source: survey_data
  columns: [sample_id, sample_name, type_code, depth]
  drop_duplicates: [sample_id]
  
  append:
    # Add samples from previous survey in database
    - type: sql
      data_source: archive_db
      query: |
        SELECT sample_id, sample_name, type_code, depth
        FROM historical_samples
        WHERE survey_year = 2022
    
    # Add control samples
    - type: fixed
      values:
        - ["CTRL001", "Control Sample 1", "CONTROL", null]
        - ["CTRL002", "Control Sample 2", "CONTROL", null]
```

**Result**: Combined dataset with samples from:
- Current survey spreadsheet
- 2022 archived samples (from database)
- 2 fixed control samples

#### Example 3: Multiple Spreadsheet Sources

Union data from several Excel/CSV files:

```yaml
observation:
  type: data
  source: site_a_observations
  columns: [obs_id, site_id, date, value]
  
  append:
    - type: data
      source: site_b_observations
      # Inherits columns from parent
      
    - type: data
      source: site_c_observations
```

**Requirements**:
- `site_a_observations`, `site_b_observations`, `site_c_observations` must be defined as separate entities
- All must provide columns: `[obs_id, site_id, date, value]`

#### Example 4: SQL Append with Column Name Mismatch

Union tables with different column names:

```yaml
contact:
  type: sql
  data_source: main_db
  columns: [contact_name, contact_type]
  check_column_names: false  # Allow column name flexibility
  query: |
    SELECT [Name] as contact_name, 
           [Type] as contact_type
    FROM MainContacts
  
  append:
    - type: sql
      data_source: main_db
      check_column_names: false  # Inherited  
      query: |
        SELECT [BotBest], [BotBest]  # Column names don't match
        FROM FieldSurvey              # But structure is compatible
        
    - type: sql
      data_source: archive_db
      query: |
        SELECT name_field, type_field  # Different names again
        FROM LegacyContacts
```

**Behavior**:
- Each SQL query can have different column names
- System validates column COUNT matches (2 columns expected)
- Automatically renames all to `[contact_name, contact_type]`
- All rows concatenated with consistent column names

### Validation Requirements

The system validates append configurations to ensure data compatibility:

#### Column Compatibility

1. **Column Count**: All append sources must have the same number of columns as the parent entity
2. **Column Names**: 
   - With `check_column_names: true`: SQL column names must match exactly
   - With `check_column_names: false`: Only count is validated, names are auto-renamed

```yaml
# VALID: Same column count
parent:
  columns: [a, b, c]
  append:
    - type: fixed
      values: [[1, 2, 3]]  # 3 values = 3 columns ✓

# INVALID: Column count mismatch  
parent:
  columns: [a, b, c]
  append:
    - type: fixed
      values: [[1, 2]]  # 2 values ≠ 3 columns ✗
```

#### Type Compatibility

Data types should be compatible across sources to avoid pandas concatenation errors:

```yaml
# VALID: Compatible types
sample_type:
  type: sql
  columns: [type_id, type_name]
  query: "SELECT type_id::int, type_name::text FROM types"
  
  append:
    - type: fixed
      values:
        - [999, "Unknown"]  # int, string - compatible

# RISKY: Type mismatch may cause issues
sample_type:
  columns: [type_id, type_name]
  append:
    - type: fixed
      values:
        - ["ABC", 123]  # string, int - swapped types!
```

#### Dependency Satisfaction

If append sources reference other entities via `source`, those entities must:
1. Exist in the configuration
2. Be included in `depends_on` list

```yaml
measurement:
  depends_on: [survey_2023, survey_2024]  # Required!
  type: data
  source: survey_2023
  
  append:
    - type: data
      source: survey_2024  # Must be in depends_on
```

### Processing Logic

Append sources are processed in the following order:

1. **Extract Primary**: Load data for the primary entity
2. **Extract Append Sources**: Load each append source sequentially
3. **Apply Inherited Properties**: Apply inherited `replacements`, `filters` to each source
4. **Concatenate**: Combine all dataframes using pandas concat (vertical stack)
5. **Apply Post-Concat Properties**: Apply `drop_duplicates`, `drop_empty_rows` to combined data
6. **Generate Surrogate IDs**: If configured, generate IDs across all rows
7. **Establish Foreign Keys**: Link to other entities using combined data
8. **Apply Unnest**: If configured, transform wide to long format

**Important**: Append happens early in the pipeline, before foreign key establishment and unnest operations.

### Advanced Patterns

#### Conditional Appending

While the configuration doesn't support conditional logic directly, you can achieve similar results using SQL filters:

```yaml
sample:
  type: sql
  query: |
    SELECT * FROM samples
    WHERE status = 'active'
  
  append:
    - type: sql
      query: |
        SELECT * FROM samples  
        WHERE status = 'archived'
        AND archive_year >= 2020  # Conditional filter
```

#### Incremental Data Loading

Append allows building datasets incrementally:

```yaml
observation:
  type: data
  source: base_observations
  
  append:
    - type: sql
      data_source: updates_db
      query: |
        SELECT * FROM new_observations
        WHERE created_date > '2024-01-01'
```

#### Multi-Source Lookups

Build comprehensive lookup tables from multiple authoritative sources:

```yaml
location:
  type: sql
  data_source: gis_db
  query: "SELECT location_id, name, coords FROM gis_locations"
  
  append:
    - type: sql
      data_source: field_db
      query: "SELECT location_id, name, coords FROM field_locations"
      
    - type: fixed
      values:
        - [99999, "Unknown Location", null]
```

### Comparison with Alternatives

The `append` approach was chosen over other design alternatives:

| Feature | Append (Selected) | Separate Parent Entity | Union SQL | Multiple Root Sources |
|---------|------------------|---------------------|-----------|---------------------|
| Backward Compatible | ✓ | ✗ | ✗ | ✗ |
| Simple Syntax | ✓ | ✗ | ~ | ~ |
| Property Inheritance | ✓ | ✗ | ✗ | ~ |
| Multiple Source Types | ✓ | ✓ | ✗ | ✓ |
| SQL + Fixed Mix | ✓ | ✓ | ✗ | ✓ |
| Intuitive Semantics | ✓ | ~ | ✓ | ~ |

**Key Advantages**:
- **Backward Compatible**: Existing configs work without changes
- **Property Inheritance**: Automatic inheritance of data quality settings
- **Mixed Sources**: Combine SQL, fixed values, and data entities seamlessly
- **Clear Semantics**: "Append" clearly indicates vertical concatenation

### Best Practices

1. **Use Consistent Schemas**: Ensure all append sources have compatible column types
2. **Set** `drop_duplicates`: Recommended when appending from multiple sources
3. **Validate Dependencies**: Include all referenced entities in `depends_on`
4. **Use** `check_column_names: false` **Carefully**: Only when column name mismatch is intentional
5. **Document Sources**: Add comments explaining what each append source provides
6. **Test Incrementally**: Add append sources one at a time to isolate issues
7. **Consider Performance**: Many append sources can impact processing time

### Troubleshooting

**Column Count Mismatch**:
```
Error: Append source has 3 columns but parent entity expects 2
```
**Solution**: Ensure all append sources have matching column counts.

**Column Name Validation Error** (when `check_column_names: true`):
```
Error: SQL columns [name, type] don't match expected [contact_name, contact_type]
```
**Solution**: Either rename SQL columns or set `check_column_names: false`.

**Type Incompatibility**:
```
Error: Cannot concatenate dataframes - incompatible types in column 'id'
```
**Solution**: Ensure compatible data types across all sources (e.g., all integers or all strings).

**Circular Dependency**:
```
Error: Circular dependency detected involving entities: [A, B, C]
```
**Solution**: Review `depends_on` declarations. Append sources that reference other entities via `source` create dependencies.

---

## Complete Entity Examples

### Simple Lookup Table

```yaml
archaeological_period:
  surrogate_id: archaeological_period_id
  keys: ["ArchDat", "ArchDat_Beschreibung"]
  columns: ["ArchDat", "ArchDat_Beschreibung"]
  drop_duplicates: "@value: entities.archaeological_period.keys"
  depends_on: []
```

### Fixed Lookup Table

```yaml
contact_type:
  source: null
  type: fixed
  surrogate_id: contact_type_id
  surrogate_name: contact_type
  columns: ["contact_type_name", "description", "arbodat_code"]
  values:
    - ["Archaeologist", "Name of scientist responsible", "ArchBear"]
    - ["Botanist", "Name of botanist responsible", "BotBear"]
    - ["Author(s)", "Publication authors", "Aut"]
```

### SQL-Based Entity

```yaml
identification_level:
  data_source: sead
  surrogate_id: identification_level_id
  type: sql
  columns: ["identification_level_id", "identification_level_abbrev", "identification_level_name"]
  drop_duplicates: false
  values: |
    sql: 
    select identification_level_id, identification_level_abbrev, identification_level_name
    from public.tbl_identification_levels
  depends_on: []
```

### Entity with Foreign Keys

```yaml
feature:
  surrogate_id: feature_id
  keys: ["ProjektNr", "Befu"]
  columns: ["ProjektNr", "Fustel", "Befu", "BefuTyp"]
  drop_duplicates: true
  foreign_keys:
    - entity: site
      local_keys: "@value: entities.site.keys"
      remote_keys: "@value: entities.site.keys"
      how: inner
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false
    - entity: feature_type
      local_keys: "@value: entities.feature_type.keys"
      remote_keys: "@value: entities.feature_type.keys"
  depends_on: ["site", "feature_type"]
```

### Entity with Unnesting

```yaml
contact:
  surrogate_id: contact_id
  keys: []
  columns: "@value: entities.contact_type.contact_types"
  unnest:
    id_vars: []
    value_vars: "@value: entities.contact_type.contact_types"
    var_name: contact_type
    value_name: contact_name
  foreign_keys:
    - entity: contact_type
      local_keys: ["contact_type"]
      remote_keys: ["arbodat_code"]
  drop_duplicates: ["contact_type", "contact_name"]
  depends_on: ["contact_type"]
```

### Complex Entity with Multiple Features

```yaml
sample:
  surrogate_id: sample_id
  keys: ["ProjektNr", "Befu", "ProbNr"]
  columns: ["ProjektNr", "Befu", "ProbNr", "Probeart", "SampleType"]
  extra_columns:
    sample_name: "ProbNr"
    alt_ref_num: null
    sample_group_id: null
  drop_duplicates: true
  drop_empty_rows: ["ProbNr"]
  foreign_keys:
    - entity: feature
      local_keys: ["ProjektNr", "Befu"]
      remote_keys: ["ProjektNr", "Befu"]
      how: inner
      constraints:
        cardinality: many_to_one
        allow_unmatched_left: false
        allow_null_keys: false
    - entity: sample_group
      local_keys: ["ProjektNr", "Befu"]
      remote_keys: ["ProjektNr", "Befu"]
    - entity: sample_type
      local_keys: ["Probeart"]
      remote_keys: ["sample_type_code"]
      extra_columns:
        sample_type_description: "description"
  depends_on: ["feature", "sample_group", "sample_type"]
```

---

## Processing Order

The system processes entities in dependency order using topological sorting:

1. **Identify Root Entities**: Entities with `depends_on: []`
2. **Topological Sort**: Process entities only after their dependencies
3. **Circular Dependency Detection**: Errors if circular dependencies exist
4. **Deferred Linking**: If dependencies aren't ready, linking is deferred

**Example Processing Order:**
```
1. site_type_group (no dependencies)
2. site_type (depends_on: [site_type_group])
3. site (depends_on: [site_type])
4. feature (depends_on: [site])
5. sample (depends_on: [feature])
```

---

## Project Validation

The Shape Shifter configuration system includes comprehensive validation using the **Specification Pattern**. Validation catches configuration errors early, before processing begins, providing clear error messages and warnings to help troubleshoot issues.

### Validation Usage

#### Command-Line Validation

Validate a configuration file before running normalization:

```bash
python validate_config.py path/to/config.yml
```

**Output Example:**
```
Project Validation Results:
=================================

✓ EntityExistsSpecification: All referenced entities exist
✓ CircularDependencySpecification: No circular dependencies detected  
✗ SqlDataSpecification: SQL entities missing required fields
  ERROR: Entity 'location' (type: sql) missing required field 'data_source'
  ERROR: Entity 'site' (type: sql) missing required field 'query'
⚠ SurrogateIdSpecification: Surrogate ID naming issues  
  WARNING: Entity 'sample': Surrogate ID 'sample_identifier' should end with '_id'

Validation failed with 2 errors and 1 warnings.
```

#### Programmatic Validation

Validate configurations in code:

```python
from src.model import ShapeShiftProject
from src.specifications import CompositeConfigSpecification

# Load configuration
config = ShapeShiftProject.from_file("config.yml")

# Validate
validator = CompositeConfigSpecification()
is_valid = validator.is_satisfied_by(config)

# Check results
if is_valid:
    print("Project is valid")
else:
    for error in validator.errors:
        print(f"ERROR: {error}")
    for warning in validator.warnings:
        print(f"WARNING: {warning}")
```

#### Integration with Normalizer

Validation is automatically run when initializing the normalizer:

```python
from src.normalizer import ShapeShifter

# Validation happens during initialization
normalizer = ShapeShifter("config.yml")
# If validation fails, initialization raises an exception
```

### Validation Specifications

The system includes 9 validation specifications that check different aspects of the configuration:

#### 1. EntityExistsSpecification

**Purpose**: Ensures all entity references point to existing entities.

**Validates**:
- Entity names in `foreign_keys.entity`
- Entity names in `depends_on` lists
- Entity names in `source` properties
- Entity names in `append[].source` properties
- Entity names in filters (e.g., `exists_in.other_entity`)

**Error Examples**:
```
ERROR: Entity 'sample' references non-existent entity 'sample_type' in foreign_keys
ERROR: Entity 'feature' lists non-existent dependency 'location'
ERROR: Entity 'measurement' uses non-existent source 'sensor_data'
ERROR: Filter in entity 'sample' references non-existent entity 'valid_samples'
```

**Why It Matters**: Missing entity references cause runtime failures. Catching them during validation prevents pipeline crashes.

#### 2. CircularDependencySpecification

**Purpose**: Detects circular dependencies in entity processing order.

**Validates**:
- Direct dependencies declared in `depends_on`
- Implicit dependencies from `source` properties
- Implicit dependencies from `foreign_keys`
- Implicit dependencies from `append[].source`

**Detection**: Uses topological sorting to identify cycles.

**Error Examples**:
```
ERROR: Circular dependency detected: sample → sample_type → lookup → sample
ERROR: Circular dependency in dependency chain: A → B → C → A
```

**Why It Matters**: Circular dependencies make topological sorting impossible, preventing the pipeline from determining processing order.

**Resolution**: Review `depends_on` and `source` references to break the cycle. Consider:
- Using a different entity as the data source
- Restructuring entities to remove cyclic relationships
- Using append sources instead of direct dependencies

#### 3. RequiredFieldsSpecification

**Purpose**: Validates that entities have required fields based on their configuration.

**Validates**:
- Entities with `source` have `depends_on` including that source
- Foreign key configs have `entity`, `local_keys`, `remote_keys`
- Unnest configs have `var_name` and `value_name`
- Append configs have `type` and type-specific required fields

**Error Examples**:
```
ERROR: Entity 'sample' uses source 'survey' but 'survey' not in depends_on
ERROR: Foreign key in entity 'feature' missing required field 'entity'
ERROR: Foreign key in entity 'feature' missing required field 'local_keys'
ERROR: Unnest config in entity 'contact' missing required field 'var_name'
ERROR: Append source in entity 'sample' missing required field 'type'
```

**Why It Matters**: Missing required fields cause runtime errors. Early detection saves debugging time.

#### 4. SqlDataSpecification

**Purpose**: Validates SQL-type entities have required database query configuration.

**Validates**:
- Entities with `type: sql` have `data_source` field
- Entities with `type: sql` have `query` field
- Append sources with `type: sql` have these fields

**Error Examples**:
```
ERROR: Entity 'location' (type: sql) missing required field 'data_source'
ERROR: Entity 'site' (type: sql) missing required field 'query'
ERROR: Append source in entity 'sample' (type: sql) missing 'query'
```

**Why It Matters**: SQL entities cannot execute without a data source connection and query. Validation ensures these are specified before attempting database connections.

#### 5. DataSourceExistsSpecification

**Purpose**: Validates that all referenced data sources are defined in `options.data_sources`.

**Validates**:
- `data_source` references in SQL-type entities
- `data_source` references in SQL-type append sources

**Error Examples**:
```
ERROR: Entity 'location' references non-existent data source 'gis_db'
ERROR: Available data sources: ['sead', 'arbodat']
ERROR: Append source in entity 'sample' references non-existent data source 'external_db'
```

**Why It Matters**: Referencing non-existent data sources causes connection failures. Validation helps catch typos and configuration errors.

#### 6. ForeignKeySpecification

**Purpose**: Validates foreign key configurations are well-formed.

**Validates**:
- Required fields: `entity`, `local_keys`, `remote_keys`
- `local_keys` and `remote_keys` have matching lengths
- `local_keys` and `remote_keys` are non-empty lists
- Referenced entity exists (delegates to EntityExistsSpecification)
- Constraint configurations if present

**Error Examples**:
```
ERROR: Foreign key in entity 'sample' missing required field 'entity'
ERROR: Foreign key in entity 'feature' has mismatched key lengths:
       local_keys (2): ['feature_id', 'site_id']
       remote_keys (1): ['feature_id']
ERROR: Foreign key in entity 'sample' has empty local_keys list
ERROR: Foreign key constraint in entity 'sample' has invalid cardinality 'one_to_few'
       Valid values: one_to_one, many_to_one, one_to_many, many_to_many
```

**Why It Matters**: Malformed foreign key configs cause merge failures. Validation ensures relationship definitions are correct before attempting joins.

#### 7. UnnestSpecification

**Purpose**: Validates unnest (melt) configurations are well-formed.

**Validates**:
- Required fields: `var_name`, `value_name`
- Optional fields have correct types if present: `id_vars`, `value_vars`

**Error Examples**:
```
ERROR: Unnest config in entity 'contact' missing required field 'var_name'
ERROR: Unnest config in entity 'coordinate' missing required field 'value_name'
ERROR: Unnest config in entity 'measurement' has invalid type for 'id_vars' (expected list)
```

**Why It Matters**: Unnest operations require specific field names for the transformation. Missing these causes pandas melt failures.

#### 8. SurrogateIdSpecification

**Purpose**: Validates surrogate ID naming conventions and uniqueness.

**Validates**:
- Surrogate IDs end with `_id` suffix (convention)
- No duplicate surrogate IDs across entities
- Surrogate ID doesn't conflict with column names (optional check)

**Error Examples**:
```
WARNING: Entity 'sample': Surrogate ID 'sample_identifier' should end with '_id'
WARNING: Recommended: 'sample_id'

ERROR: Duplicate surrogate ID 'entity_id' used by entities: ['sample', 'feature']

WARNING: Entity 'sample': Surrogate ID 'sample_id' conflicts with column name 'sample_id'
```

**Why It Matters**: 
- **Convention**: `_id` suffix makes IDs easily identifiable
- **Uniqueness**: Duplicate IDs can cause ambiguous references
- **Conflicts**: Column name conflicts can cause overwriting issues

**Note**: Naming warnings are non-fatal but indicate potential issues.

#### 9. AppendProjectSpecification

**Purpose**: Validates append/union configurations are well-formed.

**Validates**:
- Each append source has `type` field
- Type-specific required fields:
  - `type: fixed` requires `values`
  - `type: sql` requires `data_source` and `query`
  - `type: data` requires `source`
- `values` for fixed sources is a list of lists (2D array)
- Referenced entities in `source` exist
- Referenced data sources exist

**Error Examples**:
```
ERROR: Append source in entity 'sample_type' missing required field 'type'
ERROR: Append source in entity 'contact' (type: fixed) missing 'values'
ERROR: Append source in entity 'measurement' (type: sql) missing 'data_source'
ERROR: Append source in entity 'observation' (type: data) missing 'source'
ERROR: Append source in entity 'lookup' has invalid values format (expected list of lists)
ERROR: Append source in entity 'sample' (type: data) references non-existent entity 'calibration'
```

**Why It Matters**: Append operations fail if sources are misconfigured. Validation ensures all append sources have proper type-specific configuration before attempting concatenation.

### Error vs. Warning

**Errors**: Project issues that will cause processing to fail
- **Action**: Must be fixed before running normalization
- **Examples**: Missing required fields, non-existent references, circular dependencies

**Warnings**: Issues that may indicate problems but won't cause immediate failure
- **Action**: Review and address if appropriate
- **Examples**: Naming convention violations, potential ambiguities

### Validation Output Format

Validation results include:
- **Specification name**: Which validation rule was checked
- **Status**: Pass (✓), Warning (⚠), or Error (✗)
- **Messages**: Detailed error/warning messages with context
- **Entity names**: Which entities have issues
- **Suggested fixes**: When possible, hints for resolution

### Custom Specifications

You can add custom validation specifications by:

1. **Create a new specification class** inheriting from `ConfigSpecification`:

```python
from src.specifications import ConfigSpecification

class MyCustomSpecification(ConfigSpecification):
    def is_satisfied_by(self, config: ShapeShiftProject) -> bool:
        # Your validation logic
        for entity_name, entity in config.entities.items():
            if self._has_issue(entity):
                self.add_error(f"Entity '{entity_name}' has issue: ...")
        
        return len(self.errors) == 0
```

2. **Register it with CompositeConfigSpecification**:

```python
class CompositeConfigSpecification(ConfigSpecification):
    def __init__(self):
        self.specs = [
            # ... existing specs ...
            MyCustomSpecification(),
        ]
```

3. **Run validation**:

The new specification will automatically run with all other validations.

### Validation Best Practices

1. **Validate Early**: Run validation before starting normalization
2. **Fix Errors First**: Address errors before warnings
3. **Review Warnings**: Warnings often indicate real issues
4. **Incremental Fixes**: Fix one issue at a time and re-validate
5. **Use Descriptive Names**: Follow naming conventions to avoid warnings
6. **Document Complex Configs**: Add comments explaining unusual configurations
7. **Test After Changes**: Re-run validation after modifying configs

### Integration Points

Validation is integrated at several points:

1. **CLI Validation Tool** (`validate_config.py`): Standalone validation before processing
2. **Normalizer Initialization**: Automatic validation when creating normalizer instance
3. **Project Loading**: Optional validation during `ShapeShiftProject.from_yaml()`
4. **Test Suite**: Validation tests ensure specifications work correctly

This comprehensive validation system helps catch configuration errors early, provides clear diagnostics, and makes the configuration format more robust and user-friendly.

---

## Best Practices

### 1. Entity Organization

- **Group related entities** together in the YAML file
- **Use comments** to separate logical sections
- **Document complex logic** with inline comments

### 2. Dependency Management

- **Minimize dependencies** to simplify processing
- **Declare all dependencies explicitly** in `depends_on`
- **Avoid circular dependencies** - they will cause errors

### 3. Key Design

- **Use natural keys** where possible for better readability
- **Always define surrogate_id** for join operations
- **Keep key columns consistent** across related entities

### 4. Foreign Key Design

- **Use constraints** to validate data quality
- **Prefer inner joins** unless outer joins are explicitly needed
- **Document relationship cardinality** in comments or constraints

### 5. Data Quality

- **Enable drop_duplicates** for lookup tables
- **Use drop_empty_rows** to clean sparse data
- **Add validation constraints** to foreign keys

### 6. Project Maintainability

- **Use `@value:` references** to avoid duplication
- **Split large configs** using `@include:`
- **Keep data sources** in separate files
- **Version control** your project files

### 7. Performance

- **Limit column selection** to only needed columns
- **Drop unnecessary foreign key columns** with `drop_remote_id`
- **Process large entities early** to catch errors faster

---

## Data Filters

Filters provide post-load data filtering capabilities. They are applied after data extraction but before foreign key linking and other transformations.

### Filter Project

Filters are configured in the `filters` property of an entity as a list of filter definitions:

```yaml
entity_name:
  filters:
    - type: filter_type
      # filter-specific parameters
```

### Available Filter Types

#### `exists_in` Filter

Keeps only rows where a column's value exists in another entity's column. This is useful for filtering data based on values in a reference table.

**Parameters**:
- `type`: `"exists_in"` (required)
- `column`: Local column name to filter (required)
- `other_entity`: Name of entity to check values against (required)
- `other_column`: Column name in other entity (optional, defaults to same as `column`)
- `drop_duplicates`: Optional list of columns to drop duplicates after filtering

**Example 1: Basic filtering**
```yaml
taxa:
  columns: ["PCODE", "BNam", "Name_E"]
  filters:
    - type: exists_in
      column: "PCODE"
      other_entity: "_pcodes"  # Reference entity with valid codes
      other_column: "PCODE"
```

**Example 2: With deduplication**
```yaml
taxa:
  columns: ["PCODE", "BNam", "Name_E"]
  filters:
    - type: exists_in
      column: "PCODE"
      other_entity: "abundance"
      drop_duplicates: ["PCODE"]  # Drop duplicate taxa after filtering
```

**Use Cases**:
- Filter lookup tables to only include values actually used in the data
- Remove orphaned records before establishing foreign keys
- Reduce data size by filtering based on dependent entities

**Execution Order**:
1. Filter is applied after data extraction
2. Filter can reference entities that appear earlier in dependency order
3. Filter is applied before foreign key linking for the entity

**Error Handling**:
- Raises error if `other_entity` does not exist in data store
- Raises error if `column` or `other_column` is missing
- Logs warning if no rows match filter criteria

### Custom Filter Development

To add new filter types:

1. Create a filter class in `src/arbodat/filter.py`
2. Register with `@Filters.register(key="filter_type")`
3. Implement `apply(df, filter_cfg, data_store)` method

Example:
```python
@Filters.register(key="my_filter")
class MyFilter:
    def apply(self, df: pd.DataFrame, filter_cfg: dict, data_store: dict) -> pd.DataFrame:
        # Filter logic here
        return filtered_df
```

---

## Troubleshooting

### Common Issues

#### Circular Dependencies
**Error**: `Circular dependencies detected`
**Solution**: Review `depends_on` declarations and break the cycle

#### Missing Columns
**Error**: `Column 'X' not found in DataFrame`
**Solution**: Verify column names match source data exactly (case-sensitive)

#### Unmet Dependencies
**Error**: `Entity has unmet dependencies: ['entity_name']`
**Solution**: Add missing entity to `depends_on` list

#### Foreign Key Constraint Violations
**Error**: `ForeignKeyConstraintViolation: cardinality mismatch`
**Solution**: Review constraint settings and verify data matches expectations

#### Unnesting Issues
**Error**: `Invalid unnest configuration`
**Solution**: Ensure `var_name` and `value_name` are both specified

### Debugging Tips

1. **Enable detailed logging**: Set log level to DEBUG
2. **Process entities incrementally**: Comment out entities to isolate issues
3. **Validate configuration**: Run `validate_config.py` before processing
4. **Check data shapes**: Use log_shapes to inspect row counts
5. **Review processing order**: Check log for entity processing sequence

---

## Related Documentation

This guide consolidates the following previously separate documents:
- **constraint_examples.py**: Constraint usage examples (now in Foreign Key Constraints section)
- **FOREIGN_KEY_CONSTRAINTS.md**: Constraint documentation (now in Foreign Key Constraints section)
- **UNION_CONFIGURATION_OPTIONS.md**: Append/union configuration (now in Append Project section)
- **config_validation.md**: Validation specifications (now in Project Validation section)

**Additional Resources:**
- **[USER_GUIDE.md](USER_GUIDE.md)**: Complete user guide for Shape Shifter
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**: Development and architecture documentation
- **[VALIDATION_IMPROVEMENTS.md](VALIDATION_IMPROVEMENTS.md)**: Validation system design and improvements
- **[README.md](README.md)**: Documentation index and navigation

---

## Appendix: Project Schema Summary

```yaml
# Root Structure
entities: dict[string, EntityConfig]
options:
  translations: TranslationConfig
  data_sources: dict[string, DataSourceConfig]
mappings: dict[string, any]

# EntityConfig
EntityConfig:
  # Identity
  surrogate_id?: string
  surrogate_name?: string
  keys?: list[string]
  
  # Source
  source?: string | null
  type?: "data" | "fixed" | "sql"
  data_source?: string
  values?: string | list[list]
  
  # Columns
  columns?: list[string] | string
  extra_columns?: dict[string, string | any]
  
  # Quality
  drop_duplicates?: bool | list[string] | string
  drop_empty_rows?: bool | list[string] | dict[string, list[any]]
  check_column_names?: bool
  
  # Filtering
  filters?: list[FilterConfig]
  
  # Value Transformations
  replacements?: dict[string, dict[any, any]]
  
  # Relationships
  depends_on: list[string]
  foreign_keys?: list[ForeignKeyConfig]
  
  # Transformations
  unnest?: UnnestConfig

# FilterConfig
FilterConfig:
  type: string
  # ... filter-specific parameters

# ForeignKeyConfig
ForeignKeyConfig:
  entity: string
  local_keys: list[string] | string
  remote_keys: list[string] | string
  how?: "inner" | "left" | "right" | "outer" | "cross"
  extra_columns?: dict[string, string]
  drop_remote_id?: bool
  constraints?: ForeignKeyConstraints

# ForeignKeyConstraints
ForeignKeyConstraints:
  cardinality?: "one_to_one" | "many_to_one" | "one_to_many" | "many_to_many"
  allow_unmatched_left?: bool
  allow_unmatched_right?: bool
  require_unique_left?: bool
  require_unique_right?: bool
  allow_null_keys?: bool
  allow_row_decrease?: bool

# UnnestConfig
UnnestConfig:
  id_vars?: list[string]
  value_vars?: list[string]
  var_name: string
  value_name: string

# DataSourceConfig
DataSourceConfig:
  driver: "postgres" | "ucanaccess"
  options: dict[string, any]

# TranslationConfig
TranslationConfig:
  filename: string
  delimiter?: string
```
