# Spreadsheet Normalization Configuration Reference

## Overview

This document describes the YAML configuration format used by the spreadsheet normalization subsystem. This system is a general-purpose framework for **denormalizing** input data from various sources (spreadsheets, databases, fixed values) and harmonizing the output into a target schema. While the examples use Arbodat data for proof-of-concept, the system is designed to be adaptable to any domain.

## Architecture

The normalization system follows a multi-phase pipeline:

1. **Extract**: Extract subsets from source data (spreadsheet, SQL, fixed values)
2. **Link**: Establish foreign key relationships between entities
3. **Unnest**: Transform wide-format data to long-format (melt operation)
4. **Translate**: Map column names to target schema
5. **Store**: Write to target format (Excel, CSV, database)

### Key Components

- **ProcessState**: Handles topological sorting and dependency resolution
- **ArbodatSurveyNormalizer**: Orchestrates the normalization pipeline
- **TablesConfig**: Configuration model for all entities and their relationships
- **SubsetService**: Extracts data subsets with column selection and transformations

---

## Configuration File Structure

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

## Entity Configuration

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
    drop_empty_rows: bool | [string, ...]  # Empty row handling
    check_column_names: bool              # Validate column names match (SQL sources)
    
    # Filtering
    filters: [...]                        # Post-load data filters
    
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
  - `"sql"`: Execute SQL query against a database
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
  values: |
    sql:
    select id, name
    from tbl_dimensions
  ```

#### `data_source`
- **Type**: `string`
- **Required**: Only for `type: sql`
- **Description**: Name of the data source connection defined in `options.data_sources`. The data source specifies database connection parameters.
- **Example**:
  ```yaml
  data_source: sead
  ```

#### `values`
- **Type**: `string | list[list]`
- **Required**: Only for `type: fixed` or `type: sql`
- **Description**: 
  - For `type: fixed`: 2D array of values
  - For `type: sql`: SQL query string (typically multi-line with `|`)
- **Example**:
  ```yaml
  # Fixed values
  type: fixed
  values:
    - ["Type A", "Description A"]
    - ["Type B", "Description B"]
  
  # SQL query
  type: sql
  values: |
    sql:
    select column1, column2
    from table_name
    where condition = true
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
- **Type**: `bool | list[string]`
- **Required**: No (defaults to `false`)
- **Description**: Controls empty row removal. Empty values include `NaN`, `None`, and empty strings (`""`):
  - `true`: Drop rows where all columns are empty
  - `false`: Keep all rows
  - `list[string]`: Drop rows where all specified columns are empty
- **Note**: Empty strings are automatically treated as `pd.NA` before checking for empty rows
- **Example**:
  ```yaml
  # Drop completely empty rows (including rows with only empty strings)
  drop_empty_rows: true
  
  # Drop rows where specific columns are all empty or empty strings
  drop_empty_rows: ["name", "description"]
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
- **See**: Foreign Key Configuration section below

---

### Foreign Key Configuration

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
      require_all_left_matched: bool
      require_all_right_matched: bool
      min_match_rate: float
      
      # Key Uniqueness
      require_unique_left: bool
      require_unique_right: bool
      allow_null_keys: bool
      
      # Row Count
      max_row_increase_pct: float
      max_row_increase_abs: int
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

##### `require_all_left_matched`
- **Type**: `bool`
- **Description**: If `true`, all left rows must find a match in the right table
- **Example**:
  ```yaml
  constraints:
    require_all_left_matched: true
  ```

##### `require_all_right_matched`
- **Type**: `bool`
- **Description**: If `true`, all right rows must find a match in the left table
- **Example**:
  ```yaml
  constraints:
    require_all_right_matched: true
  ```

##### `min_match_rate`
- **Type**: `float` (0.0 to 1.0)
- **Description**: Minimum fraction of left rows that must match (e.g., 0.95 = 95% match rate)
- **Example**:
  ```yaml
  constraints:
    min_match_rate: 0.95
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

##### `max_row_increase_pct`
- **Type**: `float`
- **Description**: Maximum allowed percentage increase in row count after merge (e.g., 0.05 = 5% increase)
- **Example**:
  ```yaml
  constraints:
    max_row_increase_pct: 0.05
  ```

##### `max_row_increase_abs`
- **Type**: `int`
- **Description**: Maximum allowed absolute increase in row count after merge
- **Example**:
  ```yaml
  constraints:
    max_row_increase_abs: 10
  ```

##### `allow_row_decrease`
- **Type**: `bool`
- **Description**: Whether to allow the row count to decrease after merge
- **Example**:
  ```yaml
  constraints:
    allow_row_decrease: false
  ```

---

### Unnest Configuration

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

**Configuration:**
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

### Translation Configuration

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

### Data Sources Configuration

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
        require_all_left_matched: true
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
        require_all_left_matched: true
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

## Validation

The configuration system includes comprehensive validation through specifications:

- **EntityExistsSpecification**: Ensures all referenced entities exist
- **CircularDependencySpecification**: Detects circular dependencies
- **ForeignKeySpecification**: Validates foreign key configurations
- **ColumnExistsSpecification**: Checks that referenced columns exist
- **UnnestSpecification**: Validates unnest configurations
- **DataSourceSpecification**: Validates data source configurations

See `docs/config_validation.md` for detailed validation documentation.

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

### 6. Configuration Maintainability

- **Use `@value:` references** to avoid duplication
- **Split large configs** using `@include:`
- **Keep data sources** in separate files
- **Version control** your configuration files

### 7. Performance

- **Limit column selection** to only needed columns
- **Drop unnecessary foreign key columns** with `drop_remote_id`
- **Process large entities early** to catch errors faster

---

## Data Filters

Filters provide post-load data filtering capabilities. They are applied after data extraction but before foreign key linking and other transformations.

### Filter Configuration

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

- **CONFIG-README.md**: User guide for configuration files
- **config_validation.md**: Validation system documentation
- **FOREIGN_KEY_CONSTRAINTS.md**: Detailed constraint documentation
- **constraint_examples.py**: Constraint usage examples

---

## Appendix: Configuration Schema Summary

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
  drop_empty_rows?: bool | list[string]
  check_column_names?: bool
  
  # Filtering
  filters?: list[FilterConfig]
  
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
  require_all_left_matched?: bool
  require_all_right_matched?: bool
  min_match_rate?: float
  require_unique_left?: bool
  require_unique_right?: bool
  allow_null_keys?: bool
  max_row_increase_pct?: float
  max_row_increase_abs?: int
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
