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

A configuration file consists of three main sections. The existence of value 'shapeshifter-project' in `metadata.type` identifies the file as a Shapeshifter project file.

```yaml
metadata:          # metadata definitions (required)
  type: 'shapeshifter-project'  #         (required)
  ...

entities:          # Entity definitions   (required)
  entity_name:
    # Entity configuration

options:           # Global options (optional)
  translations:    # Column name translations
  data_sources:    # named data sources associated to this project
  mappings:        # Remote entity mappings (optional)

```

---

## Metadata Section

The metadata section identifies the file as a Shape Shifter project and provides descriptive information about the configuration.

### Structure

```yaml
metadata:                             # Metadata definitions (required)
  type: 'shapeshifter-project'        # Project file tag (required)
  name: string                        # Human-readable project name (optional)
  description: string                 # Detailed project description (optional)
  version: string                     # Semantic version (e.g., "1.0.0") (optional)
  default_entity: string              # Default entity for `data` entities (optional)
```

### Fields

#### Required
- **type**: Must be `"shapeshifter-project"` to identify the file as a Shape Shifter configuration

#### Optional
- **name**: A human-readable name for the project (if omitted, derived from filename)
- **description**: Detailed description of what this configuration does (supports multi-line strings using `|`)
- **version**: Semantic version string (e.g., "1.0.0", "2.1.3") for tracking configuration changes
- **default_entity**: Reference to an existing entity used as the default source for `data` type entities

### Examples

**Minimal Metadata:**
```yaml
metadata:
  type: 'shapeshifter-project'
```

**Full Metadata:**
```yaml
metadata:
  type: 'shapeshifter-project'
  name: "Archaeological Site Data Import"
  description: |
    Imports archaeological site data from multiple sources including
    field surveys, laboratory analyses, and historical records.
    Transforms data to match SEAD Clearinghouse schema.
  version: "2.1.0"
  default_entity: sample_data
```

### Validation Rules

- **metadata section**: Required (error if missing)
- **metadata.type**: Required, must be `"shapeshifter-project"` (error if missing or incorrect)
- **metadata.name**: Optional string
- **metadata.description**: Optional string  
- **metadata.version**: Optional string (recommended to follow semantic versioning)
- **metadata.default_entity**: Optional, must reference existing entity if provided

### API Integration

When loaded via the API, metadata is accessible through the `Project.metadata` property:

```python
from backend.app.mappers.project_mapper import ProjectMapper

# Load configuration
cfg_dict = load_yaml("my_config.yml")
api_config = ProjectMapper.to_api_config(cfg_dict, "my-config")

# Access metadata
print(api_config.metadata.name)         # "Archaeological Site Data Import"
print(api_config.metadata.description)  # "Imports archaeological site data..."
print(api_config.metadata.version)      # "2.1.0"
```

### Core Model Integration

In the core `ShapeShiftProject`, metadata is accessible via the `metadata` property:

```python
from src.model import ShapeShiftProject

project = ShapeShiftProject.from_file("my_config.yml")

# Access metadata
print(project.metadata.name)         # "Archaeological Site Data Import"
print(project.metadata.description)  # "Imports archaeological site data..."
print(project.metadata.version)      # "2.1.0"
```

### Backward Compatibility

The metadata section's optional fields maintain backward compatibility. Projects with minimal metadata (only `type` specified) continue to work, with the project name derived from the filename.

## Entity Section

Each entity represents a table/dataset to be extracted and processed. Entities are processed in dependency order using topological sorting.

### Basic Entity Structure

```yml
entities:
  entity_name:
    # Identity & Keys
    public_id: string                       # Target system primary key name
    surrogate_name: string                  # Alternative name for public ID
    keys: [string, ...]                     # Natural (business) key columns
    
    # Data Selection
    source: string | null                   # Data: source entity or null for default source
    type: \"data\" | \"fixed\" | \"sql\"    # Data source type  (required)
    columns: [string, ...]                  # Columns to extract
    
    # Data quality
    drop_empty_rows: bool | [string, ...] | {string: [any, ...]}  # Empty row handling
    functional_dependency_check: bool       # Check functional dependency when dropping columns
    check_column_names: bool                # Validate column names match (SQL sources)
    
    # Filtering
    filters: [...]                          # Post-load data filters
    
    # Value Transformations
    replacements: {string: any}             # Value replacement rules (mapping/legacy/rule-list)
    
    # Relationships
    foreign_keys: [...]                     # Foreign key definitions
      ....
    depends_on: [string, ...]               # Dependency list
  
    # Transformations
    unnest: {...}                           # Unnesting configuration
    extra_columns: {...}                    # Additional columns to add
    drop_duplicates: bool | [string, ...]   # Duplicate handling
    
    # Data Sources
    data_source: string               # Named data source (for SQL)
    values: string | [...]            # Fixed values or SQL query
```

---

## Property Reference

### Identity Properties

Shape Shifter implements a three-tier identity system to support flexible data transformation and integration:

1. **system_id**: Standardized local auto-incrementing ID (always "system_id")
2. **keys**: Business/natural keys from source data
3. **public_id**: Target system primary key name (defines FK column names)

This architecture separates concerns between:
- **Local scope**: `system_id` for internal processing (1, 2, 3...)  
- **Business logic**: `keys` for entity identification in source data
- **Global scope**: `public_id` for target system integration and FK relationships

**Critical Principle**: All relationships in ShapeShifter use local `system_id` values. FK columns always contain parent's `system_id` (sequential integers), never external IDs. External IDs (e.g., SEAD IDs) are applied as a decoration step via `mappings.yml` → `map_to_remote()`.

#### `system_id` (Auto-Managed)
- **Type**: `string` (always "system_id")
- **Required**: Automatically managed by system
- **Description**: Standardized name for auto-incrementing integer IDs (1, 2, 3...). This column is always added automatically during data loading and is used for internal processing. When data is exported, this column is renamed based on the entity's `public_id` setting.
- **Behavior**:
  - Added automatically by all loaders (SQL, fixed, file)
  - Always numbered sequentially starting from 1
  - Column name is always "system_id" during processing
  - Renamed to `public_id` value during export/dispatch
  - Read-only in UI (cannot be edited)
- **Example**: Not configured directly - automatically managed

#### `public_id`
- **Type**: `string`
- **Required**: **Yes** (error if missing for fixed entities, warning for others)
- **Description**: Serves dual purpose in the identity system:
  1. **Column Name**: Specifies the target system's PK column name (e.g., "location_id" in SEAD schema)
  2. **Column Values**: Holds mapped external IDs from `mappings.yml` (local business key → SEAD ID)
  
  Additionally, `public_id` determines FK column names in child entities to avoid `system_id` collision.
  
- **FK Linking Process**:
  ```
  Parent (location):
    system_id: [1, 2, 3]           ← Local sequential
    location_name: ["Norway", ...]  ← Business key
    location_id: [162, 205, ...]    ← SEAD IDs from mappings.yml
                 ↑ public_id column
  
  Child (site) after FK link:
    system_id: [1, 2, 3]           ← Local sequential
    location_name: ["Norway", ...]  ← Join key
    location_id: [1, 2, ...]        ← FK = parent's system_id values!
                 ↑ FK column name from parent's public_id
  ```
  
- **Example**:
  ```yaml
  public_id: site_id
  ```
- **Foreign Key Naming Convention**:
  When establishing foreign key relationships, the FK column in the child table is named after the parent entity's `public_id`:
  ```yaml
  # Parent entity
  site:
    public_id: site_id
    keys: ["site_code"]
  
  # Child entity - FK column will be named "site_id" (from parent's public_id)
  sample:
    public_id: sample_id
    keys: ["sample_code"]
    foreign_keys:
      - entity: site
        remote_keys: ["site_code"]
        local_keys: ["sample_site_code"]
        # Result: FK column named "site_id" containing parent's system_id values
  ```
- **Validation Rules**:
  - **Existence**: Error if missing (required for proper integration)
  - **Type**: Must be `string` (error if not)
  - **Naming Convention**: Error if doesn't end with `_id` suffix
  - **Uniqueness**: Each entity should have unique public_id (suggested validation)
- **Common Issues**:
  - Missing `public_id` prevents proper export and FK relationships
  - Not following `_id` naming convention violates schema expectations
  - Duplicate `public_id` names across entities causes confusion
- **Backward Compatibility**:
  Configurations using the deprecated `surrogate_id` field will automatically migrate to `public_id`:
  ```yaml
  # Old format (deprecated but still works)
  surrogate_id: site_id
  
  # Automatically migrated to:
  public_id: site_id
  ```

#### `surrogate_id` (Deprecated - Use `public_id`)
- **Status**: **DEPRECATED** - Use `public_id` instead
- **Type**: `string`
- **Required**: No (automatically migrates to `public_id`)
- **Description**: Legacy field name for primary key configuration. When present, values are automatically migrated to `public_id` during project loading.
- **Migration**: 
  ```yaml
  # Before (old config)
  entities:
    my_entity:
      surrogate_id: entity_id
  
  # After (recommended)
  entities:
    my_entity:
      public_id: entity_id
  ```
- **Note**: Both fields are accepted for backward compatibility, but `public_id` takes precedence if both are present.

#### `surrogate_name`
- **Type**: `string`
- **Required**: No
- **Description**: Name of a text column associated with the `public_id`. This column can be used when reconciling entities by name in the UI editor.
- **Example**:
  ```yaml
  public_id: contact_type_id
  surrogate_name: contact_type
  ```
- **Validation Rules**:
  - **Type**: Must be `string` if provided
  - **Usage**: Currently not validated but should be documented
- **Suggested Additional Validation**:
  - Should not conflict with existing column names
  - Should not be the same as `public_id`
  - Must exist in `columns` if provided


#### `keys`
- **Type**: `list[string]`
- **Required**: Yes (field must exist, but can be empty list)
- **Description**: Natural/business key columns that uniquely identify rows in the source data. Used for duplicate detection and foreign key relationships. These are the "real world" identifiers from your source system (e.g., sample codes, site names).
- **Example**:
  ```yaml
  keys: ["ProjektNr", "Befu"]
  ```
- **Validation Rules**:
  - **Existence**: Error if field is missing
  - **Type**: Must be `list[string]` (error if not)
  - **Empty Keys**: Warning if empty list `[]`
  - **String Items**: Each item must be a string (error if not)
  - **Column Existence**: Keys should exist in `columns` or be generated fields (suggested validation)
- **Common Issues**:
  - Empty keys prevent proper duplicate detection
  - Keys not matching actual columns cause linking failures
- **Suggested Additional Validation**:
  - Warn if keys are not unique in source data
  - Validate that all key columns are present after data extraction

---

#### Three-Tier Identity System: Complete Example

```yaml
entities:
  # Parent entity with natural key
  site:
    type: sql
    data_source: my_database
    query: SELECT * FROM sites
    public_id: site_id           # Target PK name
    keys: ["site_code"]          # Business key from source
    columns:
      - site_code
      - site_name
      - location
  
  # Child entity referencing parent
  sample:
    type: sql
    data_source: my_database
    query: SELECT * FROM samples
    public_id: sample_id          # Target PK name
    keys: ["sample_code"]         # Business key from source
    columns:
      - sample_code
      - sample_name
      - parent_site_code
    foreign_keys:
      - entity: site
        remote_keys: ["site_code"]     # Match parent's business key
        local_keys: ["parent_site_code"] # Local column with parent's business key
        # Result: Creates FK column "site_id" (from parent's public_id)
        #         containing parent's system_id values (1, 2, 3...)
```

**Processing Flow**:
1. **Load**: `site` loaded with `system_id=1,2,3...` and `site_code` from source
2. **Link**: `sample` FK created:
   - Column name: `site_id` (from parent's `public_id`)
   - Column values: Parent's `system_id` (matched via `keys`)
3. **Export**: 
   - `site`: `system_id` column renamed to `site_id`
   - `sample`: `system_id` renamed to `sample_id`, FK `site_id` preserved

**Critical Architectural Principle**: 
- **All relationships use local `system_id` values** - FK columns contain parent's `system_id` (1, 2, 3...), never external IDs
- **FK column naming**: Child FK column = parent's `public_id` (avoids `system_id` collision)
- **SEAD ID mapping**: Applied separately via `mappings.yml` → `map_to_remote()` (decoration step)
- **Local domain integrity**: All processing happens with sequential integer references
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
- **Validation Rules**:
  - **Type**: Must be `string` or `null`
  - **Context-Dependent**:
    - **When `type: fixed`**: Should be empty/null (warning if set, value ignored)
    - **When `type: sql`**: Should be empty/null (warning if set, value ignored)
    - **When `type: entity`**: Can reference another entity name
  - **Entity Existence**: If string, must reference an existing entity in the project (error if not)
  - **Circular Dependencies**: Source entity must not create circular dependency chain (error)
- **Common Issues**:
  - Referencing non-existent entities
  - Creating circular dependencies through source chains
- **Suggested Additional Validation**:
  - Warn if source entity is processed after current entity in dependency order
  - Validate that source entity produces compatible output columns
#### `type`
- **Type**: `"entity" | "fixed" | "sql"`
- **Required**: No (defaults to `"entity"`)
- **Description**: 
  - `"entity"`: Extract from source data (spreadsheet or another entity)
  - `"fixed"`: Use fixed/hardcoded values defined in `values`
  - `"sql"`: Execute SQL query against a database (requires `data_source` and `query`)
- **Requirements by Type**:
  - `type: fixed` → requires `values` (list of lists)
  - `type: sql` → requires `data_source` and `query`
  - `type: entity` → uses `source` (defaults to root data if omitted)
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
- **Validation Rules**:
  - **Type**: Must be one of `"entity"`, `"fixed"`, or `"sql"` if provided
  - **Default**: Defaults to `"entity"` if omitted
  - **Context-Dependent Requirements**:
    - **When `type: fixed`**:
      - `values` field is required (error if missing)
      - `values` must be non-empty (error if empty)
      - `columns` field is required (error if missing)
      - `source` should be empty (warning if set)
      - `data_source` should be empty (warning if set)
      - `query` should be empty (warning if set)
    - **When `type: sql`**:
      - `data_source` is required (error if missing)
      - `query` is required (error if missing)
      - `data_source` must exist in `options.data_sources` (error if not)
      - `source` should be empty (warning if set)
      - `values` should be empty (warning if set)
    - **When `type: entity`**:
      - Can use `source` field to reference another entity
      - Should not have `values`, `data_source`, or `query` (warning if present)
- **Common Issues**:
  - Missing required fields for entity type
  - Conflicting fields (e.g., both `values` and `query`)
- **Suggested Additional Validation**:
  - Validate SQL query syntax for `type: sql` entities
  - Check that fixed values structure matches columns count

#### `data_source`
- **Type**: `string`
- **Required**: Yes when `type: sql`; No for other types
- **Description**: Name of the data source connection defined in `options.data_sources`. The data source specifies database connection parameters (host, database, credentials, driver, etc.).
- **Example**:
  ```yaml
  data_source: sead  # Must be defined in options.data_sources
  ```
- **Validation Rules**:
  - **Existence in Options**: Must exist in `options.data_sources` configuration (error if not)
  - **Type**: Must be a non-empty `string`
  - **Context-Dependent**:
    - **When `type: sql`**: Required (error if missing)
    - **When `type: fixed`**: Should be empty (warning if set)
    - **When `type: entity`**: Should be empty (warning if set)
  - **Append Configurations**: Also validated for each append item with `type: sql`
- **Common Issues**:
  - Typos in data source name
  - Referencing data source before it's defined in options
  - Missing data source configuration in `options.data_sources`
- **Suggested Additional Validation**:
  - Test database connection during validation
  - Warn if data source credentials are missing environment variables
  ```

#### `query`
- **Type**: `string`
- **Required**: Yes when `type: sql`; No for other types
- **Description**: SQL query string to execute against the data source. Typically uses multi-line format with `|` or `>` for readability.
- **Example**:
  ```yaml
  type: sql
  data_source: arbodat_data
  query: |
    select column1, column2
    from table_name
    where condition = true
  ```
- **Validation Rules**:
  - **Type**: Must be a non-empty `string`
  - **Context-Dependent**:
    - **When `type: sql`**: Required (error if missing)
    - **When `type: fixed`**: Should be empty (warning if set)
    - **When `type: entity`**: Should be empty (warning if set)
  - **Non-Empty**: Must contain actual SQL text (error if empty)
  - **Append Configurations**: Also validated for append items with `type: sql`
- **Common Issues**:
  - Empty query string
  - SQL syntax errors (not detected until execution)
  - Query column count/names not matching entity configuration
- **Suggested Additional Validation**:
  - Basic SQL syntax validation
  - Dry-run query to verify column names and count
  - Validate query doesn't contain dangerous operations (DROP, DELETE without WHERE, etc.)

#### `values`
- **Type**: `list[list[any]]` or `list[any]` (for single-column tables)
- **Required**: Yes when `type: fixed`; No for other types
- **Description**: 2D array of fixed values for lookup tables. Each inner list represents a row of data.
- **Example**:
  ```yaml
  # Multi-column fixed values
  values:
    - ["value1", "desc1", 1]
    - ["value2", "desc2", 2]
  
  # Single-column fixed values (automatically wrapped)
  values: ["value1", "value2", "value3"]
  ```
- **Validation Rules**:
  - **Context-Dependent**:
    - **When `type: fixed`**: Required (error if missing), must be non-empty (error if empty)
    - **When `type: sql`**: Should be empty (warning if set)
    - **When `type: entity`**: Should be empty (warning if set)
  - **Type**: Must be a `list` (error if not)
  - **Non-Empty**: Must contain at least one value/row (error if empty)
  - **Structure Validation**:
    - **Multi-column**: Each row must be a list with length matching `columns` count (error if mismatch)
    - **Single-column**: If values are primitives (not lists), `columns` must have exactly 1 item (error if not)
  - **Consistency**: All rows should have the same number of columns (error if inconsistent)
  - **Append Configurations**: Also validated for append items with `type: fixed`
- **Common Issues**:
  - Column/row count mismatch
  - Empty values list
  - Mixed row structures (some lists, some primitives)
  - Missing `columns` configuration
- **Suggested Additional Validation**:
  - Warn if values contain duplicate rows (when keys are defined)
  - Validate data types match expected column types
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
- **Required**: Recommended (error if missing for most entity types)
- **Description**: List of columns to extract from the source. Can also reference other entity properties using `@value:` syntax.
- **Example**:
  ```yaml
  # Explicit list
  columns: ["ArchDat", "ArchDat_Beschreibung"]
  
  # Reference another entity's keys
  columns: "@value: entities.site.keys"
  ```
- **Validation Rules**:
  - **Existence**: Error if field is missing (for most entities)
  - **Type**: Must be `list[string]` or a `string` (for `@value:` references) (error if not)
  - **String Items**: Each item in list must be a string (error if not)
  - **Context-Dependent**:
    - **When `type: fixed`**: Required (error if missing)
    - **When `type: sql`**: Recommended (warning if missing)
    - **When `type: entity`**: Recommended (warning if missing)
  - **Reference Resolution**: If using `@value:` syntax, the referenced path must exist (error if not)
  - **Fixed Values**: For `type: fixed`, column count must match values row width (error if mismatch)
- **Common Issues**:
  - Missing columns configuration
  - Column names not matching source data
  - Incorrect `@value:` reference paths
  - Mismatch between columns and values for fixed entities
- **Suggested Additional Validation**:
  - Warn if columns reference non-existent source columns (for data/SQL types)
  - Validate column name uniqueness
  - Check for reserved column names (surrogate_id, etc.)

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
    dataset_type_id: 4
  ```
- **Validation Rules**:
  - **Type**: Must be `dict` if provided (error if not)
  - **Keys**: Must be valid Python identifiers / column names (suggested validation)
  - **Values**: Can be any type (string for column reference, or literal value)
- **Common Issues**:
  - Duplicate column names (conflicts with existing columns)
  - Referenced source columns don't exist
  - Invalid column name characters
- **Suggested Additional Validation**:
  - Error if extra_column name conflicts with existing columns or keys
  - Warn if referenced source column doesn't exist
  - Validate column names follow naming conventions
    # Create constant value column
    default_status: "active"
  ```

---

### Data Quality Properties

#### `drop_duplicates`
- **Type**: `bool | list[string] | string | dict`
- **Required**: No (defaults to `false`)
- **Description**: Controls duplicate row removal. Can be specified as:
  - `true`: Drop all duplicate rows
  - `false`: Keep all rows
  - `list[string]`: Drop duplicates based on specified columns
  - `string` with `@value:`: Reference another entity's keys
  - `dict`: Complex configuration with columns and optional functional dependency settings
- **Dict Format**: The dict format allows grouping duplicate removal with functional dependency validation settings:
  ```yaml
  drop_duplicates:
    columns: [col1, col2]                          # Columns to check for duplicates
    check_functional_dependency: true              # (Optional, defaults to true)
    strict_functional_dependency: false            # (Optional, defaults to true)
  ```
- **Example**:
  ```yaml
  # Drop all duplicates
  drop_duplicates: true
  
  # Drop duplicates based on keys
  drop_duplicates: ["ProjektNr", "Befu"]
  
  # Reference another entity's keys
  drop_duplicates: "@value: entities.site.keys"
  
  # Dict format with functional dependency settings
  drop_duplicates:
    columns: ["id"]
    check_functional_dependency: true
    strict_functional_dependency: false
  ```
- **Functional Dependency Settings** (when using dict format):
  - `check_functional_dependency`: Whether to validate functional dependencies during duplicate removal
  - `strict_functional_dependency`: Whether to raise error (true) or warning (false) if FD validation fails
- **Precedence**: Top-level `check_functional_dependency` and `strict_functional_dependency` properties take precedence over those specified in the `drop_duplicates` dict
- **Validation Rules**:
  - **Type**: Must be `bool`, `str`, `list[string]`, or `dict` (error if not)
  - **List Items**: If list, all items must be strings (error if not)
  - **Dict Columns**: If dict, `columns` key is required and must be `bool`, `string`, or `list[string]`
  - **Column Existence**: If list or dict columns, should exist in entity's columns/keys (suggested validation)
  - **Reference Resolution**: If `@value:` string, referenced path must exist
- **Common Issues**:
  - Columns in list don't exist in entity
  - Invalid `@value:` reference
  - Dict missing required `columns` key
- **Suggested Additional Validation**:
  - Warn if drop_duplicates columns don't include all key columns
  - Validate referenced columns exist before runtime

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
- **Validation Rules**:
  - **Type**: Must be `bool`, `list[string]`, or `dict` (error if not)
  - **List Items**: If list, all items must be strings
  - **Dict Structure**: If dict, keys must be column names, values must be lists
  - **Column Existence**: Columns should exist in entity's data (suggested validation)
- **Common Issues**:
  - Specified columns don't exist in entity
  - Dictionary format with non-list values
- **Suggested Additional Validation**:
  - Warn if specified columns don't exist
  - Validate empty value types match column data types

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
    query: |
      select [BotBest], "BotBest" from [Befunde]
  ```
- **Validation Rules**:
  - **Type**: Must be `bool` if provided
  - **Context**: Only applies to `type: sql` entities (ignored for other types)
  - **Default Behavior**: Defaults to `true` (strict column name matching)
- **Common Issues**:
  - SQL query returns different column names than configured
  - Column order mismatch when `check_column_names: false`
- **Suggested Additional Validation**:
  - Warn if set to `false` for non-SQL entities
  - Validate column count matches even when names don't

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
- **Validation Rules**:
  - **Type**: Must be `list` if provided
  - **Filter Items**: Each item must be a `dict` with required fields
  - **Filter Type**: Each filter must specify a valid `type` field
  - **exists_in Filter Requirements**:
    - `column`: Required, must be string referencing local column
    - `other_entity`: Required, must reference existing entity
    - `other_column`: Optional string (defaults to same as `column`)
- **Common Issues**:
  - Referenced entity doesn't exist
  - Column doesn't exist in current or other entity
  - Filter type not supported
- **Suggested Additional Validation**:
  - Validate filter type is supported
  - Check that referenced entities exist
  - Warn if filtering removes all rows
  - Validate column existence before runtime

#### `replacements`
- **Type**: `dict[string, any]`
- **Required**: No
- **Description**: Defines value replacement mappings for specified columns. Each key is a column name, and each value is a dictionary mapping old values to new values. This is useful for normalizing data values, converting codes to standardized formats, or correcting inconsistent data.
- **Use Cases**:
  - Converting coordinate system names to EPSG codes
  - Standardizing status codes or category names
  - Mapping legacy identifiers to new ones
  - Correcting typos or inconsistent values in source data
- **Application Order**: Replacements are applied after column extraction and after duplicate/empty-row handling in the subsetting step.
- **Supported Forms**:
  - **Mapping**: `{old: new, ...}` (fast exact match)
  - **Legacy blank-out + forward fill**: scalar/list/set/tuple → treat as values to blank out, then forward-fill
  - **Advanced ordered rules**: `list[dict]` (regex, normalization, explicit fill policies)
- **Advanced rule operators** (via `match:`):
  - Positive: `equals`, `contains`, `startswith`, `endswith`, `in`, `regex`, `regex_sub`
  - Negated (optional): `not_equals`, `not_contains`, `not_startswith`, `not_endswith`, `not_in`, `not_regex`
- **Type coercion** (optional): `coerce: string|int|float`
  - Most useful for `equals`, `in`, and `map` when source columns are strings like `"1"` but config uses numeric keys.
  - If `normalize:` is provided, matching is performed in normalized string space (numeric `coerce` is ignored).
- **Note**: Values not matched by any replacement remain unchanged.
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

  # Legacy blank-out + forward-fill (useful for "pad"-style inputs)
  sample:
    replacements:
      status: ["drop", "deleted"]

  # Advanced ordered rules
  site:
    replacements:
      coordinate_system:
        - match: regex
          from: "^dhdn\\s+zone\\s+3$"
          to: "EPSG:31467"
          flags: [ignorecase]
          normalize: [collapse_ws, lower]
          report_replaced: true
          report_unmatched: true
          report_top: 10
        - map:
            "RGF93 Lambert 93": "EPSG:2154"
          normalize: [strip]
        - match: regex_sub
          from: "\\bZone\\s+(\\d+)\\b"
          to: "Z\\1"
        # If `to` is null, matching cells are set to NA
        - match: regex_sub
          from: "^N/A$"
          to: null
      status:
        - blank_out: ["drop"]
          fill: none          # forward | backward | none | {constant: "UNKNOWN"}
          report_replaced: true

  # Replace whole cell if it contains a substring
  sample:
    replacements:
      note:
        - match: contains
          from: "foo"
          to: "HAS_FOO"
          flags: [ignorecase]

  # Starts/ends-with operators
  sample:
    replacements:
      filename:
        - match: endswith
          from: ".txt"
          to: "TEXT_FILE"
          flags: [ignorecase]

  # Set-membership ("in") with optional coercion
  sample:
    replacements:
      status_code:
        - match: in
          from: [1, 2, 3]
          to: "KNOWN"
          coerce: int
  
  # Replacements can reference external project files
  site:
    replacements:
      coordinate_system: "@value: replacements.site.KoordSys"
  ```
- **Validation Rules**:
  - **Type**: Must be `dict` if provided
  - **Structure**: Keys must be column names (strings)
  - **Mapping form**: column value must be a dict mapping old values to new values
  - **Legacy blank-out form**: column value can be a scalar or sequence of values to blank out (then forward-fill)
  - **Rule list form**: column value can be a list of dict rules (ordered)
  - **Column Existence**: Column names should exist in entity (suggested validation)
- **Common Issues**:
  - Replacement column doesn't exist in entity
  - Invalid dict structure
  - Circular replacements
- **Suggested Additional Validation**:
  - Warn if replacement column doesn't exist
  - Validate replacement values match column data types
  - Check for unmapped values (suggested warning)
  - Use `report_unmatched: true` for rule-list replacements to log common unmatched values
- **See**: Filters section below for detailed filter documentation

---

### Relationship Properties

#### `depends_on`
- **Type**: `list[string]`
- **Required**: Yes (field must exist, but can be empty list)
- **Description**: List of entity names that must be processed before this entity. Used for topological sorting to ensure correct processing order.
- **Example**:
  ```yaml
  # Process site and feature_type before this entity
  depends_on: ["site", "feature_type"]
  
  # No dependencies (root entity)
  depends_on: []
  ```
- **Validation Rules**:
  - **Existence**: Field must exist (error if missing)
  - **Type**: Must be `list[string]` (warning if not)
  - **Entity Existence**: Each referenced entity must exist in project (error if not)
  - **Circular Dependencies**: Must not create circular dependency chains (error if detected)
  - **Source Entity**: If `source` field is set, that entity is implicitly a dependency
  - **Foreign Key Entities**: Entities referenced in foreign_keys are implicit dependencies
- **Common Issues**:
  - Referencing non-existent entities
  - Creating circular dependencies
  - Missing implicit dependencies (source, foreign keys)
  - Incomplete dependency list
- **Suggested Additional Validation**:
  - Warn if explicit dependencies don't match implicit ones
  - Validate dependency order resolves correctly
  - Check for redundant dependencies

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
- **Validation Rules**:
  - **Existence**: Required field (error if missing)
  - **Type**: Must be a non-empty `string`
  - **Entity Exists**: Must reference an existing entity in project (error if not)
  - **Dependency**: Remote entity should be in `depends_on` list (suggested validation)
- **Common Issues**:
  - Typo in entity name
  - Referencing entity not yet defined
  - Missing from depends_on list
- **Suggested Additional Validation**:
  - Error if entity creates circular dependency
  - Warn if remote entity doesn't have surrogate_id

##### `local_keys`
- **Type**: `list[string] | string`
- **Required**: Yes (except for cross joins where it should be empty)
- **Description**: Column names in the local entity to match against remote keys. Can use `@value:` to reference another entity's keys.
- **Example**:
  ```yaml
  local_keys: ["ProjektNr"]
  # Or reference another entity
  local_keys: "@value: entities.site.keys"
  ```
- **Validation Rules**:
  - **Existence**: Required for non-cross joins (error if missing)
  - **Type**: Must be `list[string]` or `string` (for `@value:` reference) (error if not)
  - **Context-Dependent**:
    - **When `how: cross`**: Should be empty/null (error if provided)
    - **When `how` is not cross**: Required and must be non-empty (error if missing)
  - **Key Count**: Must have same length as `remote_keys` (error if mismatch)
  - **Column Existence**: Each key must exist in local entity's columns, keys, or unnest_columns (error if not)
  - **Reference Resolution**: If `@value:` string, referenced path must exist
- **Common Issues**:
  - Missing keys for non-cross joins
  - Providing keys for cross joins
  - Key count mismatch with remote_keys
  - Referencing non-existent columns
- **Suggested Additional Validation**:
  - Warn if keys are not in entity's key list
  - Validate keys exist before runtime

##### `remote_keys`
- **Type**: `list[string] | string`
- **Required**: Yes (except for cross joins where it should be empty)
- **Description**: Column names in the remote entity to match against local keys. Must have same length as `local_keys`.
- **Example**:
  ```yaml
  remote_keys: ["ProjektNr"]
  ```
- **Validation Rules**:
  - **Existence**: Required for non-cross joins (error if missing)
  - **Type**: Must be `list[string]` or `string` (for `@value:` reference) (error if not)
  - **Context-Dependent**:
    - **When `how: cross`**: Should be empty/null (error if provided)
    - **When `how` is not cross**: Required and must be non-empty (error if missing)
  - **Key Count**: Must have same length as `local_keys` (error if mismatch)
  - **Column Existence**: Each key must exist in remote entity's columns (error if not)
- **Common Issues**:
  - Missing keys for non-cross joins
  - Providing keys for cross joins
  - Key count mismatch with local_keys
  - Referencing non-existent remote columns
- **Suggested Additional Validation**:
  - Warn if keys are not in remote entity's key list
  - Validate keys exist in remote entity before runtime

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
- **Validation Rules**:
  - **Type**: Must be one of `"inner"`, `"left"`, `"right"`, `"outer"`, `"cross"`
  - **Default**: Defaults to `"inner"` if not specified
  - **Cross Join Logic**: When `how: cross`, local_keys and remote_keys must be empty/null
- **Common Issues**:
  - Invalid join type string
  - Using keys with cross joins
  - Not using keys with non-cross joins
- **Suggested Additional Validation**:
  - Warn about data loss with inner joins
  - Suggest constraints based on join type

##### `extra_columns`
- **Type**: `dict[string, string]` | `list[string]` | `string`
- **Required**: No
- **Description**: Additional columns to bring from the remote entity. Format is `{"local_name": "remote_column_name"}`.
- **Example**:
  ```yaml
  extra_columns:
    taxa_name: "Taxon"
    taxa_author: "Autor"
  ```
- **Validation Rules**:
  - **Type**: Must be `dict`, `list`, or `string` if provided (error if not)
  - **Column Existence**: Referenced remote columns must exist in remote entity (suggested validation)
  - **Name Conflicts**: Local column names should not conflict with existing columns (suggested validation)
- **Common Issues**:
  - Referenced remote columns don't exist
  - Local names conflict with existing columns
  - Invalid data structure
- **Suggested Additional Validation**:
  - Validate remote columns exist
  - Warn about column name conflicts
  - Check for duplicate column mappings

##### `drop_remote_id`
- **Type**: `bool`
- **Required**: No (defaults to `false`)
- **Description**: If `true`, drops the remote surrogate ID column after linking (useful when only extra columns are needed).
- **Example**:
  ```yaml
  drop_remote_id: true
  ```
- **Validation Rules**:
  - **Type**: Must be `bool` if provided
  - **Default**: Defaults to `false`
- **Common Issues**:
  - Dropping ID when it's needed later
  - Not dropping ID when only using extra_columns
- **Suggested Additional Validation**:
  - Warn if dropping ID that's referenced elsewhere
  - Suggest dropping when only extra_columns are used

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
- **Type**: `list[string]` | `string` (for `@value:` reference)
- **Required**: No (defaults to empty list, but recommended)
- **Description**: Columns to use as identifier variables (kept unchanged)
- **Example**:
  ```yaml
  id_vars: ["ProjektNr", "Befu"]
  
  # Reference another entity's keys
  id_vars: "@value: entities.sample.keys"
  ```
- **Validation Rules**:
  - **Type**: Must be `list[string]` or `string` (for `@value:`) (warning if not)
  - **Column Existence**: Columns should exist in entity (suggested validation)
  - **Reference Resolution**: If `@value:` string, referenced path must exist
- **Common Issues**:
  - ID columns don't exist in source data
  - Empty id_vars causes all rows to have same identifier
- **Suggested Additional Validation**:
  - Warn if id_vars is empty
  - Validate columns exist before unnesting

##### `value_vars`
- **Type**: `list[string]` | `string` (for `@value:` reference)
- **Required**: Yes (error if missing when unnest is configured)
- **Description**: Columns to unpivot/melt into rows
- **Example**:
  ```yaml
  value_vars: ["ArchAusg", "ArchBear", "BotBear", "Aut", "BotBest"]
  
  # Reference from another config
  value_vars: "@value: entities.contact_type.contact_types"
  ```
- **Validation Rules**:
  - **Existence**: Required when unnest is configured (error if missing)
  - **Type**: Must be `list[string]` or `string` (for `@value:`) (error if not)
  - **Non-Empty**: Must contain at least one column (error if empty)
  - **String Items**: Each item must be a string (error if not)
  - **Column Existence**: Columns should exist in entity (suggested validation)
  - **No Overlap**: Should not overlap with id_vars (suggested validation)
- **Common Issues**:
  - Missing value_vars
  - Value columns don't exist in source
  - Overlap with id_vars
- **Suggested Additional Validation**:
  - Validate columns exist before unnesting
  - Warn if value_vars includes id_vars columns

##### `var_name`
- **Type**: `string`
- **Required**: Yes (error if missing when unnest is configured)
- **Description**: Name of the new column that will contain the original column names
- **Example**:
  ```yaml
  var_name: contact_type
  ```
- **Validation Rules**:
  - **Existence**: Required when unnest is configured (error if missing)
  - **Type**: Must be a non-empty `string` (error if not)
  - **Name Conflict**: Should not conflict with existing column names (suggested validation)
- **Common Issues**:
  - Missing var_name
  - Empty string
  - Conflicts with existing columns
- **Suggested Additional Validation**:
  - Validate unique column name
  - Follow naming conventions

##### `value_name`
- **Type**: `string`
- **Required**: Yes (error if missing when unnest is configured)
- **Description**: Name of the new column that will contain the values
- **Example**:
  ```yaml
  value_name: contact_name
  ```
- **Validation Rules**:
  - **Existence**: Required when unnest is configured (error if missing)
  - **Type**: Must be a non-empty `string` (error if not)
  - **Name Conflict**: Should not conflict with existing column names including var_name (suggested validation)
- **Common Issues**:
  - Missing value_name
  - Empty string
  - Same name as var_name
  - Conflicts with existing columns
- **Suggested Additional Validation**:
  - Validate unique column name
  - Error if same as var_name
  - Follow naming conventions

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
  type: entity | sql | fixed | csv | xlsx | openpyxl
  columns: [...]
  # ... other properties ...
  
  # Append additional sources
  append:
    - type: fixed | sql | entity | csv | xlsx | openpyxl
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
  type: entity
  source: survey_2023
  columns: [measurement_id, value, unit]
  
  append:
    - type: entity
      source: survey_2024  # Different source entity
      columns: [measurement_id, value, unit]
```

**Properties for `type: entity`:**
- `type`: Must be `"entity"`
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
  type: entity
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
  type: entity
  source: site_a_observations
  columns: [obs_id, site_id, date, value]
  
  append:
    - type: entity
      source: site_b_observations
      # Inherits columns from parent
      
    - type: entity
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
  type: entity
  source: survey_2023
  
  append:
    - type: entity
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
  type: entity
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
  - `type: entity` requires `source`
- `values` for fixed sources is a list of lists (2D array)
- Referenced entities in `source` exist
- Referenced data sources exist

**Error Examples**:
```
ERROR: Append source in entity 'sample_type' missing required field 'type'
ERROR: Append source in entity 'contact' (type: fixed) missing 'values'
ERROR: Append source in entity 'measurement' (type: sql) missing 'data_source'
ERROR: Append source in entity 'observation' (type: entity) missing 'source'
ERROR: Append source in entity 'lookup' has invalid values format (expected list of lists)
ERROR: Append source in entity 'sample' (type: entity) references non-existent entity 'calibration'
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
  type?: "entity" | "fixed" | "sql"
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
  unnest?: UnnestConfig---

## Validation Rules Summary

This section provides a comprehensive overview of all validation rules implemented in the `src.specifications` module. These rules serve as requirements for the implementation.

### Project-Level Validations

#### IsProjectSpecification
- **Purpose**: Validates project metadata section
- **Rules**:
  - Metadata section must exist (error)
  - `metadata.type` must equal `"shapeshifter-project"` (error)

#### CircularDependencySpecification  
- **Purpose**: Detects circular dependencies in entity graph
- **Rules**:
  - No circular dependency chains allowed (error)
  - Builds dependency graph from `depends_on` and `source` fields
  - Uses DFS to detect cycles

#### DataSourceExistsSpecification
- **Purpose**: Validates data source references
- **Rules**:
  - Entity `data_source` must exist in `options.data_sources` (error)
  - Append item `data_source` must exist in `options.data_sources` (error)

### Entity-Level Validations

#### EntityFieldsSpecification
- **Purpose**: Validates required fields based on entity type
- **Context-Dependent Rules**:
  - **All entity types**:
    - `keys` field must exist (error), must be list[string] (error)
    - `columns` field must exist (error), must be list[string] (error)
  - **When `type: fixed`**:
    - `surrogate_id` must exist (error)
    - `values` must exist (error) and be non-empty (error)
  - **When `type: sql`**:
    - `data_source` must exist and be non-empty string (error)
    - `query` must exist and be non-empty string (error)

#### FixedDataSpecification
- **Purpose**: Validates fixed entity data structure
- **Rules**:
  - `values` must be non-empty list (error)
  - `columns` must be non-empty list of strings (error)
  - **Structure validation**:
    - If single-column: `columns` length must be 1 (error)
    - If multi-column: each row length must match `columns` length (error)
    - All rows must be lists or all primitives (error for mixed)
  - **Conflicting fields**:
    - `source`, `data_source`, `query` should be empty (warning)

#### UnnestSpecification
- **Purpose**: Validates unnest configuration
- **Rules**:
  - `value_vars` must exist (error) and be list[string] (error)
  - `var_name` must exist (error) and be non-empty string (error)
  - `value_name` must exist (error) and be non-empty string (error)
  - `id_vars` should exist (warning) and be list[string] if provided

#### DropDuplicatesSpecification
- **Purpose**: Validates drop_duplicates configuration
- **Rules**:
  - Must be type bool, str, or list if provided (error)
  - If list, all items must be strings (error via is_string_list validator)

#### ForeignKeySpecification
- **Purpose**: Validates foreign key configuration
- **Rules**:
  - Each FK must have `entity` field (error)
  - Each FK must have `local_keys` and `remote_keys` (error)  
  - `local_keys` and `remote_keys` must be list[string] (error)
  - `local_keys` and `remote_keys` must have same length (error)
  - If `extra_columns` provided, must be str, list, or dict (error)

#### SurrogateIdSpecification
- **Purpose**: Validates surrogate ID configuration
- **Rules**:
  - `surrogate_id` should exist (warning)
  - If exists, must be string type (error)
  - Should end with `_id` (warning)

#### AppendSpecification  
- **Purpose**: Validates append configuration
- **Rules**:
  - `append_mode` must be 'all' or 'distinct' if provided (error)
  - Each append item must specify either `type` OR `source` (error), not both (error)
  - **When append `type: fixed`**:
    - `values` must exist (error) and be list type (error)
    - Empty values triggers warning
  - **When append `type: sql`**:
    - `query` must exist (error) and be string type (error)
  - **When append `source` provided**:
    - Must be string type (error)
    - Must reference existing entity (error)
    - `columns` should exist (warning)

#### DependsOnSpecification
- **Purpose**: Validates dependency declarations
- **Rules**:
  - `depends_on` should be list[string] (warning)
  - Each dependency must reference existing entity (error)

#### EntityReferencesExistSpecification
- **Purpose**: Validates all entity references exist
- **Rules**:
  - `source` entity must exist if provided (error)
  - Each `depends_on` entity must exist (error)
  - Each foreign key `entity` must exist (error)

### Foreign Key Runtime Validations

#### ForeignKeyConfigSpecification
- **Purpose**: Validates FK configuration is resolvable
- **Rules**:
  - **Cross joins**:
    - `local_keys` and `remote_keys` must be empty (error)
  - **Non-cross joins**:
    - `local_keys` and `remote_keys` must be non-empty (error)
    - Key counts must match (error)
  - **Key existence**:
    - Local keys must exist in local entity's columns/keys/unnest_columns (error)
    - Remote keys must exist in remote entity's columns (error)

#### ForeignKeyDataSpecification
- **Purpose**: Validates FK keys exist in actual data
- **Rules**:
  - Local DataFrame must exist (assertion error)
  - Remote DataFrame must exist (assertion error)
  - Config validation must pass first
  - **Missing local keys**:
    - If all missing keys are in unnest_columns: defer validation
    - Otherwise: error
  - **Pending unnest fields**:
    - If unnest_columns not yet in data: defer validation
  - **Missing remote keys**: error

### Field-Level Validators

#### exists
- **Purpose**: Field path must exist in configuration
- **Implementation**: Uses `dotexists()` to check path
- **Fails with**: Error if path not found

#### is_empty
- **Purpose**: Field must be empty (None, "", [], {})
- **Implementation**: Checks value in (None, "", [], {})
- **Fails with**: Error if non-empty value

#### is_string_list
- **Purpose**: Field must be list of strings
- **Implementation**: isinstance(value, list) and all isinstance(item, str)
- **Special case**: Returns True for "@value:" references
- **Fails with**: Error if not list or contains non-string items

#### not_empty_string
- **Purpose**: Field must be non-empty string with content
- **Implementation**: isinstance(value, str) and bool(value.strip())
- **Fails with**: Error if not string or empty/whitespace-only

#### not_empty
- **Purpose**: Field must have truthy value
- **Implementation**: bool(value)
- **Fails with**: Error if falsy (None, False, 0, "", [], {})

#### of_type
- **Purpose**: Field must match one of expected types
- **Requires**: `expected_types` kwarg as tuple
- **Implementation**: isinstance(value, expected_types)
- **Fails with**: Error listing expected type names

#### is_existing_entity
- **Purpose**: Field value must be existing entity name
- **Implementation**: value in project_cfg["entities"]
- **Fails with**: Error if entity doesn't exist

#### ends_with_id
- **Purpose**: Field must end with "_id" suffix
- **Implementation**: isinstance(value, str) and value.endswith("_id")
- **Fails with**: Warning if doesn't end with "_id"

#### is_of_categorical_values
- **Purpose**: Field must be one of allowed categorical values
- **Requires**: `categories` kwarg as list
- **Implementation**: value in categories
- **Fails with**: Error if value not in categories

### Suggested Additional Validations

The following validations are recommended but not yet implemented:

1. **Column Existence Validation**:
   - Validate that columns in `keys`, `columns`, `extra_columns` exist in source data
   - Check before runtime to catch misconfigurations early

2. **Surrogate ID Uniqueness**:
   - Ensure each entity has unique `surrogate_id` across project
   - Prevent ID collisions in final output

3. **Naming Convention Validation**:
   - Enforce snake_case for entity names
   - Validate column names don't contain spaces or special characters
   - Check for SQL reserved words in column names

4. **Dependency Completeness**:
   - Warn if `depends_on` doesn't include implicit dependencies (from `source`, `foreign_keys`)
   - Validate dependency order resolves correctly

5. **Foreign Key Column Types**:
   - Warn if local/remote key column types don't match
   - Suggest type conversions when needed

6. **Unused Entity Detection**:
   - Warn about entities not used in dependencies or foreign keys
   - Help identify orphaned configurations

7. **SQL Query Validation**:
   - Basic SQL syntax checking for `type: sql` entities
   - Validate query doesn't contain dangerous operations (DROP, DELETE without WHERE)
   - Dry-run query to verify column count and names

8. **Circular Reference in @value**:
   - Detect circular references in `@value:` directives
   - Prevent infinite loops during config resolution

9. **Replacement Coverage**:
   - Warn if replacement column doesn't exist in entity
   - Report unmapped values after replacements applied

10. **Filter Validation**:
    - Validate filter type is supported
    - Check referenced entities and columns exist
    - Warn if filter removes all rows

11. **Append Compatibility**:
    - Validate appended data has compatible column structure
    - Warn about column type mismatches between primary and append sources

12. **Unnest Column Overlap**:
    - Error if `value_vars` contains columns from `id_vars`
    - Prevent ambiguous unnest configurations

---

## Type Schema Definitions

````
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
# Environment Variable Resolution in Data Sources

## Overview

The Shape Shifter data source system now supports automatic resolution of environment variables when testing connections. This allows you to store sensitive configuration (like database credentials) in environment variables rather than hardcoding them.

## How It Works

### In Project Files (Core System)

When loading configurations through the core system (e.g., `arbodat-database.yml`), environment variables are automatically resolved by the `src.configuration` framework.

Example from `sead-options.yml`:
```yaml
driver: postgres
options:
  host: ${SEAD_HOST}
  port: ${SEAD_PORT}
  dbname: ${SEAD_DBNAME}
  username: ${SEAD_USER}
```

### In API/Backend (Data Source Testing)

When testing data source connections via the API, the `DataSourceService` now automatically resolves environment variables before attempting the connection.

**Before Resolution:**
```json
{
  "name": "sead",
  "driver": "postgresql",
  "options": {
    "host": "${SEAD_HOST}",
    "port": "${SEAD_PORT}",
    "database": "${SEAD_DBNAME}",
    "username": "${SEAD_USER}"
  }
}
```

**After Resolution (automatic):**
```json
{
  "name": "sead",
  "driver": "postgresql",
  "options": {
    "host": "localhost",
    "port": "5432",
    "database": "sead_production",
    "username": "sead_user"
  }
}
```

## Password Management with .pgpass

For PostgreSQL connections, the recommended approach is to use `.pgpass` file for password management rather than storing passwords in configuration or environment variables.

### Setting up .pgpass

1. Create `~/.pgpass` file:
   ```bash
   touch ~/.pgpass
   chmod 600 ~/.pgpass
   ```

2. Add connection credentials (one per line):
   ```
   hostname:port:database:username:password
   ```

   Example:
   ```
   localhost:5432:sead_production:sead_user:mypassword123
   localhost:5432:*:postgres:adminpassword
   ```

3. PostgreSQL will automatically use `.pgpass` when no password is provided in the connection

### Benefits

- **Security**: Passwords never appear in project files or environment variables
- **Convenience**: No need to pass passwords in connection strings
- **Standard**: `.pgpass` is the PostgreSQL-recommended approach
- **Multi-environment**: Different passwords for different databases in one file

## API Usage

### Testing Connection with Environment Variables

When creating or testing a data source via the API, you can use environment variable references:

```typescript
// Frontend API call
const dataSource = {
  name: 'production_db',
  driver: 'postgresql',
  options: {
    host: '${DB_HOST}',
    port: '${DB_PORT}',
    database: '${DB_NAME}',
    username: '${DB_USER}'
    // No password - will use .pgpass
  }
};

// Test connection
const result = await api.testConnection(dataSource);
// Environment variables are resolved automatically before testing
```

### Setting Environment Variables

**In shell:**
```bash
export SEAD_HOST=localhost
export SEAD_PORT=5432
export SEAD_DBNAME=sead_production
export SEAD_USER=sead_user
```

**In .env file (development):**
```env
SEAD_HOST=localhost
SEAD_PORT=5432
SEAD_DBNAME=sead_production
SEAD_USER=sead_user
```

**In systemd service (production):**
```ini
[Service]
Environment="SEAD_HOST=prod-db.example.com"
Environment="SEAD_PORT=5432"
Environment="SEAD_DBNAME=sead_production"
Environment="SEAD_USER=sead_user"
```

## Implementation Details

### Architecture: Layer-Based Resolution

The system follows a **clean separation of concerns** where environment variable resolution happens **exclusively in the mapper layer** when converting between API and Core entities.

#### Layer Responsibilities

| Layer | Responsibility | Environment Variables |
|-------|---------------|----------------------|
| **API Models** (`backend/app/models/`) | Data transfer, validation | Raw, unresolved (`${VAR}`) |
| **Services** (`backend/app/services/`) | Business logic | Works with raw API entities |
| **Mapper** (`backend/app/mappers/`) | Translation + **Resolution** | **Resolves here** |
| **Core** (`src/`) | Processing, execution | Always resolved |

#### Why This Approach?

1. **Single Responsibility**: The `DataSourceMapper.to_core_config()` method is the **only** place that resolves environment variables
2. **Clear Boundaries**: API layer = raw config, Core layer = resolved config
3. **No Redundancy**: Services never need to remember to call `resolve_config_env_vars()`
4. **Type Safety**: Core entities are guaranteed to be fully resolved
5. **Easier Testing**: Mock the mapper for tests that need unresolved configs

### Mapper Layer

The `DataSourceMapper` class handles the boundary between API and Core layers:

```python
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig as ApiConfig
from src.model import DataSourceConfig as CoreConfig

class DataSourceMapper:
    @staticmethod
    def to_core_config(api_config: ApiConfig) -> CoreConfig:
        """Map API config to Core config.
        
        IMPORTANT: This method resolves environment variables during mapping.
        API entities remain "raw" with ${ENV_VAR} syntax, but core entities
        are always fully resolved and ready for use.
        """
        # Resolution happens here at the API/Core boundary
        api_config = api_config.resolve_config_env_vars()
        
        # Map to core format with resolved values
        return CoreConfig(
            name=api_config.name,
            cfg={
                "driver": api_config.driver,
                "options": {...}  # Fully resolved
            }
        )
```

### Service Layer

Services work with **raw API entities** and rely on the mapper for resolution:

```python
# SchemaIntrospectionService example
class SchemaIntrospectionService:
    async def get_tables(self, data_source_name: str) -> list[TableMetadata]:
        # Get raw API config (with ${ENV_VARS})
        api_config = self.data_source_service.get_data_source(data_source_name)
        
        # Mapper handles resolution when creating core config
        core_config = DataSourceMapper.to_core_config(api_config)
        
        # Core loader receives fully resolved config
        loader = DataLoaders.get(core_config.driver)(core_config)
        return await loader.get_tables()
```

**Important:** Environment variables are **preserved in API entities** and only resolved when mapping to Core:

- `list_data_sources()` - Returns API configs **with unresolved env vars** (e.g., `${SEAD_HOST}`) for UI display/editing
- `get_data_source(name)` - Returns API config **with unresolved env vars** for editing
- `test_connection(config)` - Mapper resolves env vars **when creating core config** for testing
- `get_tables(name)` - Mapper resolves env vars **when creating loader** for introspection

This approach allows users to:
1. **See and edit** the environment variable references in the UI (e.g., `${SEAD_HOST}`)
2. **Test connections** with actual resolved values from the environment
3. **Keep configuration portable** across environments

### Resolution Rules

1. Environment variable syntax: `${VAR_NAME}`
2. If variable exists: Replaces with actual value
3. If variable doesn't exist: Replaces with empty string
4. Nested dictionaries: Resolved recursively (e.g., in `options`)
5. Non-string values: Passed through unchanged

### Example Code

```python
from backend.app.services.data_source_service import DataSourceService
from backend.app.models.data_source import DataSourceConfig
from backend.app.mappers.data_source_mapper import DataSourceMapper

# Create API config with env var references (stays raw)
api_config = DataSourceConfig(
    name="my_db",
    driver="postgresql",
    options={
        "host": "${DB_HOST}",
        "port": "${DB_PORT}",
        "database": "${DB_NAME}",
        "username": "${DB_USER}",
    }
)

# API config remains raw throughout the service layer
service = DataSourceService(config_store)

# Mapper resolves env vars when converting to core config
core_config = DataSourceMapper.to_core_config(api_config)
# Now core_config has resolved values: host="localhost", etc.

# Test connection using core config
result = await service.test_connection(api_config)
# Internally, test_connection uses mapper to get resolved core config
```

