# Shape Shifter Project Editor - User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Glossary](#2-glossary)
3. [Interface Overview](#3-interface-overview)
4. [Core Workflow](#4-core-workflow)
5. [Working with Entities](#5-working-with-entities)
6. [Validation](#6-validation)
7. [Execute](#7-execute)

---

## 1. Introduction

### What is Shape Shifter?

Shape Shifter is a declarative data transformation framework that transforms diverse data sources into standardized target schemas using YAML configurations. The Project Editor provides a visual interface for creating and managing these transformations.

### Core Workflow

The typical workflow has four main steps:

1. **Create/Open Project** - Start with a project configuration
2. **Configure Entities** - Define your data entities and relationships
3. **Validate** - Check configuration and data integrity
4. **Execute** - Run transformations and export results

### Who Uses Shape Shifter?

- **Data Managers** - Configure data entity mappings
- **Data Engineers** - Build complex transformation pipelines
- **Developers** - Integrate transformations into data workflows

### Key Features

- **Visual Editor** - Monaco-based YAML editing with syntax highlighting
- **Entity Tree** - Visual navigation of entity dependencies
- **Real-Time Validation** - Immediate feedback on configuration errors
- **Data Validation** - Validate against actual data sources (Sample or Complete mode)
- **Execution Pipeline** - Export to multiple formats (Excel, CSV, databases)

---

## 2. Glossary

### Core Concepts

**Project**
: A YAML configuration file defining all entities, data sources, and transformations for a data harmonization workflow.

**Entity**
: A logical data table in your transformation pipeline. Can be derived from SQL queries, CSV files, Excel sheets, or other entities.

**Data Source**
: A connection configuration to a database (PostgreSQL, SQLite, MS Access) or file that provides source data.

**Dependency**
: Relationship between entities where one entity (child) relies on another (parent) for data or foreign key relationships.

### Identity System

Shape Shifter uses a three-tier identity system to separate concerns:

**System ID** (`system_id`)
: Auto-managed local sequential identifier (1, 2, 3...). Always named `system_id`. Used internally by Shape Shifter for tracking and FK relationships. Read-only.

**Business Keys** (`keys`)
: Natural identifiers from your source data (e.g., `[site_code, year]`, `[sample_name]`). Used for deduplication and matching records across data sources.

**Public ID** (`public_id`)
: Target system primary key column name (e.g., `site_id`, `sample_type_id`). Must end with `_id`. Defines the FK column names in child entities. Required for entities with children or used in mappings.

### Relationships

**Foreign Key**
: Relationship between two entities where one entity references another. Defined using `foreign_keys` section with join columns and constraints.

**Cardinality**
: The relationship multiplicity between entities:
- `one_to_one`: Each record matches exactly one record
- `many_to_one`: Multiple child records reference one parent record  
- `one_to_many`: One parent record has multiple child records

**Join Type**
: How entities are merged:
- `inner`: Keep only matching records  
- `left`: Keep all child records, match parent where available
- `outer`: Keep all records from both entities
- `cross`: Cartesian product

### Transformations

**Unnest (Melt)**
: Transform data from wide format (many columns) to long format (rows). Uses pandas `melt()` operation.

**ID Variables** (`id_vars`)
: Columns that stay unchanged during unnest. These become identifier columns in the long format.

**Value Variables** (`value_vars`)
: Columns that get "melted" into rows during unnest. Each value_var becomes a row in the output.

**Variable Name** (`var_name`)
: Column name for the attribute column in unnested output (e.g., "measurement_type").

**Value Name** (`value_name`)
: Column name for the value column in unnested output (e.g., "measurement_value").

**Example:**
```yaml
# Wide format (before unnest):
id | name  | height | weight | age
1  | John  | 180    | 75     | 30

# Unnest configuration:
unnest:
  id_vars: [id, name]
  value_vars: [height, weight, age]
  var_name: measurement_type
  value_name: measurement_value

# Long format (after unnest):
id | name  | measurement_type | measurement_value
1  | John  | height          | 180
1  | John  | weight          | 75
1  | John  | age             | 30
```

### Validation

**Structural Validation**
: Checks YAML syntax, entity definitions, references, and dependency structure. Does not access data sources.

**Data Validation**
: Validates against actual data from sources. Two modes:
- **Sample Mode**: Fast validation using preview data (first 1000 rows)
- **Complete Mode**: Comprehensive validation using full normalization pipeline

**Validation Issue**
: A problem found during validation, categorized by severity:
- **Error** (🔴): Must fix before execution
- **Warning** (⚠️): Should review, may cause issues
- **Info** (ℹ️): Optional improvements or suggestions

---

## 3. Interface Overview

```
┌──────────────────────────────────────────────────────────┐
│  Shape Shifter                   [Save] [Validate] [▶]   │
├─────────────┬────────────────────────┬────────────────────┤
│             │                        │                    │
│  Entity     │   Monaco Editor        │  Validation        │
│  Tree       │   (YAML)               │  Results           │
│             │                        │                    │
│  • entity_1 │  entities:             │  ✓ No errors       │
│  • entity_2 │    entity_1:           │                    │
│   - entity_3│      type: entity      │  Structural ✓      │
│             │      columns: [...]    │  Data ✓            │
│             │                        │                    │
└─────────────┴────────────────────────┴────────────────────┘
```

### Three Main Panels

**Left: Entity Tree**
- Navigate entity hierarchy
- View dependencies (children indented under parents)
- Click entity to jump to YAML definition
- Expand/collapse dependency trees

**Center: Monaco Editor**
- Edit YAML configuration
- Syntax highlighting and validation
- Auto-completion (`Ctrl+Space`)
- Find/Replace (`Ctrl+F` / `Ctrl+H`)

**Right: Validation Panel**
- View validation results
- Filter by severity or entity
- Click errors for details
- Monitor validation status

---

## 4. Core Workflow

---

## 4. Core Workflow

### Step 1: Open or Create Project

**Open Existing Project:**
1. Click project dropdown in toolbar
2. Select configuration name
3. Project loads into editor
4. Entity tree populates with entities

**Create New Project:**
1. Click "New Project" button
2. Enter project name
3. Click "Create"
4. Empty project opens in editor

**Project File Location:**
- Projects stored in configured directory (typically `projects/`)
- Format: `project_name.yml`
- YAML syntax with specific structure
- Automatic backups created on save

### Step 2: Configure Entities

#### Understanding Entity Structure

Every entity has these key properties:

```yaml
entity_name:
  # Identity (three-tier system)
  system_id: system_id           # Auto-managed (always system_id)
  keys: [business_key1, key2]    # Source identifiers
  public_id: entity_name_id      # Target PK name (required)
  
  # Data source
  type: entity | sql | csv | xlsx | fixed
  source: parent_entity          # For derived entities
  columns: [col1, col2, col3]    # Columns to extract
  
  # Relationships (optional)
  foreign_keys: [...]            # FK to other entities
  depends_on: [other_entity]     # Processing dependencies
  
  # Transformations (optional)
  unnest: {...}                  # Wide-to-long transformation
  filters: [...]                 # Post-load data filters
```

#### Entity Types

**Derived Entity** (from another entity):
```yaml
sample:
  type: entity
  source: raw_sample_data
  columns: [sample_id, site_id, depth]
  public_id: sample_id
  keys: [sample_id]
```

**SQL Entity** (from database):
```yaml
species:
  type: sql
  data_source: postgres_db
  query: "SELECT species_id, name FROM species"
  public_id: species_id
  keys: [name]
```

**CSV Entity**:
```yaml
measurements:
  type: csv
  options:
    filename: projects/measurements.csv
    sep: ","
    encoding: utf-8
  columns: [id, value, unit]
  public_id: measurement_id
  keys: [id]
```

**Excel Entity**:
```yaml
locations:
  type: xlsx
  options:
    filename: projects/locations.xlsx
    sheet_name: Sheet1
  columns: [loc_id, name, latitude, longitude]
  public_id: location_id
  keys: [name]
```

**Fixed Entity** (static data):
```yaml
sample_types:
  type: fixed
  values:
    - [1, "Soil"]
    - [2, "Water"]
    - [3, "Sediment"]
  columns: [id, type_name]
  public_id: sample_type_id
  keys: [type_name]
```

#### Adding Entities with the Form Editor

The form editor provides a visual interface for adding/editing entities:

1. **Select entity in tree** (or position cursor in YAML)
2. **Click "Form" tab** in right panel
3. **Fill in fields:**
   - **Entity Name**: Unique identifier (snake_case)
   - **Type**: Choose entity type (entity, sql, csv, xlsx, fixed)
   - **System ID**: Auto-managed (read-only: `system_id`)
   - **Business Keys**: Multi-select columns for deduplication
   - **Public ID**: Target PK column name (must end with `_id`)
   - **Columns**: Comma-separated list of columns to extract
   - **Source Entity**: Parent entity (for derived entities)
   - **Additional Dependencies**: Other required entities

4. **Click "Save"** to add to configuration

**Form vs YAML Editing:**
- **Form Editor**: Guided field-by-field editing, prevents syntax errors
- **YAML Editor**: Direct YAML editing, for advanced users and bulk changes
- **Auto-sync**: Changes sync automatically when switching tabs

#### Defining Foreign Keys

Foreign keys create relationships between entities:

```yaml
sample:
  public_id: sample_id
  foreign_keys:
    - entity: site                 # Parent entity
      local_keys: [site_name]      # Join column in this entity
      remote_keys: [site_name]     # Join column in parent
      how: inner                   # Join type (inner/left/outer)
      constraints:
        cardinality: many_to_one   # Relationship type
        require_unique_left: false # Allow duplicate local values
        allow_null_keys: false     # Reject null join keys
```

**Key Points:**
- `entity`: Must reference existing entity with `public_id` defined
- `local_keys` / `remote_keys`: Join columns (usually business keys)
- `how`: Join strategy (inner=strict matching, left=keep all children)
- `cardinality`: Enforces relationship rules
- FK column name in output: Uses parent's `public_id` as column name
- FK column values: References parent's `system_id` (local sequential IDs)

**Common Cardinalities:**
- `many_to_one`: Multiple children → one parent (e.g., samples → site)
- `one_to_one`: Strict 1:1 relationship
- `one_to_many`: One parent → many children (rare in child entity config)

#### Defining Unnest Operations

Unnest transforms wide data (many columns) to long format (rows):

```yaml
measurements:
  unnest:
    id_vars: [sample_id, date]         # Columns to preserve
    value_vars: [pH, temp, depth]      # Columns to melt into rows
    var_name: measurement_type         # Column name for attribute
    value_name: measurement_value      # Column name for value
```

**Before unnest (wide):**
```
sample_id | date       | pH  | temp | depth
S001      | 2024-01-01 | 7.2 | 15   | 10
```

**After unnest (long):**
```
sample_id | date       | measurement_type | measurement_value
S001      | 2024-01-01 | pH              | 7.2
S001      | 2024-01-01 | temp            | 15
S001      | 2024-01-01 | depth           | 10
```

**Important:** Data validation knows about unnest and only validates `id_vars` columns (not `value_vars`, which get melted away).

### Step 3: Validate Configuration

Validation ensures your configuration is correct before execution.

#### Validation Types

**Structural Validation** (Fast):
- YAML syntax correctness
- Required fields present
- Entity references valid
- No circular dependencies
- No data source access needed

**Data Validation** (Requires data sources):
- Columns exist in data
- Foreign keys joinable
- Business keys unique
- Data types compatible

**Two Modes:**
- **Sample Mode** (Fast): Validates using preview data (first 1000 rows)
- **Complete Mode** (Comprehensive): Runs full normalization, validates all data

#### Running Validation

**Validate All Entities:**
1. Click "Validate All" button
2. Choose mode:
   - **Sample Data (Fast)**: Quick validation using preview
   - **Complete Data (Comprehensive)**: Full normalization and validation
3. Wait for results (seconds for sample, minutes for complete)
4. Review results in validation panel

**Validate Single Entity:**
1. Select entity in tree
2. Click "Validate Entity"
3. Choose validation mode
4. Faster than full validation for iterative editing

**Validate Structural Only:**
1. Click "Structural" tab in validation panel
2. Click "Validate" button
3. Instant results (no data access)
4. Use for quick syntax checks

**Validate Data Only:**
1. Click "Data" tab in validation panel
2. Click "Validate" button
3. Choose Sample or Complete mode
4. Checks against actual data sources

#### Understanding Results

**Severity Levels:**
- 🔴 **Error**: Must fix before execution
- ⚠️ **Warning**: Should review, may cause issues
- ℹ️ **Info**: Optional improvements

**Each issue shows:**
- **Message**: Description of problem
- **Entity**: Which entity has the issue
- **Field**: Which configuration field
- **Code**: Error code for reference

**Example Issues:**

*Error - Column Not Found:*
```
Column 'old_column' not found in data source
Entity: sample
Field: columns
Code: COLUMN_NOT_FOUND
```

*Warning - Duplicate Keys:*
```
Found 5 duplicate business keys
Entity: site
Field: keys
Code: DUPLICATE_BUSINESS_KEYS
```

*Info - Missing Public ID:*
```
Entity is missing public_id field
Entity: measurement
Code: MISSING_PUBLIC_ID
```

#### Filtering Results

**By Severity:**
- Click severity badge (Error/Warning/Info)
- Filter to specific severity
- Multiple selections allowed

**By Entity:**
- Select entity in tree
- Shows only issues for that entity
- Click "All" to show all entities

**Search:**
- Type in search box
- Filters by message text
- Real-time filtering as you type

#### Validation Cache

Results are cached for 5 minutes for performance:

**Cache Benefits:**
- Repeat validations are instant (5ms vs 200ms)
- Reduces server load during editing
- Enables rapid iteration

**Cache Invalidation:**
- Automatic when project modified
- Automatic after 5 minutes
- Manual via browser refresh

See [Appendix: Validation Caching](USER_GUIDE_APPENDIX.md#validation-caching) for technical details.

### Step 4: Execute Workflow

Once validation passes, execute the transformation pipeline.

#### Opening Execute Dialog

1. Ensure validation passes (no errors)
2. Click "Execute" button (green play icon)
3. Execute dialog opens with configuration options

#### Selecting Output Format

**File Formats:**
- **Excel (xlsx)**: Single workbook with entity sheets
- **CSV**: Single combined CSV file  
- **CSV  ZIP**: Multiple CSV files in compressed archive

**Database Formats:**
- **PostgreSQL**: Write to PostgreSQL database
- **SQLite**: Write to SQLite file

**Folder Formats:**
- **CSV Folder**: Directory with separate CSV files per entity

**Selection:**
1. Click "Output Format" dropdown
2. Select desired format
3. Form updates with format-specific options

#### Configuring Output

**For File Outputs (Excel, CSV):**
```
Output Path: ./output/my_project.xlsx
```
- Optional (defaults to `./output/{project_name}.{ext}`)
- Must match file extension
- File will be created/overwritten

**For Folder Outputs:**
```
Folder Path: ./output/my_project/
```
- Directory path (created if needed)
- Each entity becomes separate file
- Example: `./output/my_project/entity_1.csv`

**For Database Outputs:**
- Select pre-configured data source from dropdown
- Data source must exist in configuration
- Entities written as database tables
- Requires write permissions

#### Execution Options

**Run Validation Before Execution:**
- **Default**: Enabled
- **Purpose**: Ensure configuration valid
- **Behavior**: Stops execution if validation fails
- **Recommendation**: Always enabled

**Apply Translations:**
- **Default**: Disabled  
- **Purpose**: Translate column names using mappings
- **Use When**: Target schema differs from source
- **Example**: `sample_id` → `sampleId`

**Drop Foreign Key Columns:**
- **Default**: Disabled
- **Purpose**: Remove FK columns from output
- **Use When**: Want only natural keys
- **Effect**: Cleaner output, fewer columns

#### Running Execution

1. Configure format and options
2. Click "Execute" button
3. Progress indicator shows status
4. Wait for completion (may take minutes for large datasets)
5. Success/error message displayed

**What Happens:**
1. Optional validation runs
2. Entities loaded in dependency order
3. Foreign keys linked (using parent `system_id`)
4. Unnest operations applied
5. Transformations executed
6. Data exported to target format

#### Download Results

**For File Outputs:**
1. Execution completes successfully
2. Success message shows: "Successfully executed workflow. Processed 12 entities."
3. "Download result file" button appears
4. Click to download to browser's download folder

**Not Available For:**
- Database outputs (data already in database)
- Folder outputs (access folder directly on filesystem)

#### Handling Errors

**Validation Errors:**
- Execution stops before processing
- Validation errors displayed

- Fix errors and retry
- Or disable "Run validation" (not recommended)

**Execution Errors:**
- Error message with details
- Check backend logs for full trace
- Common causes:
  - Data source unavailable
  - Disk space full
  - Permission denied
  - Invalid SQL in entity

**Recovery:**
1. Read error message carefully
2. Fix underlying issue (data source, permissions, SQL)
3. Close and reopen dialog
4. Retry execution

---

## 5. Working with Entities

### Entity Tree Navigation

The entity tree shows your project's structure:

**Root Entities** (no dependencies):
```
• species
• sample_type
• location
```

**Dependent Entities** (indented under parent):
```
• site
  - sample
    - measurement
    - analysis
```

**Navigation:**
- **Click entity** → Jump to YAML definition
- **Double-click** → Expand/collapse children
- **View hierarchy** → Understand processing order

**Processing Order:**
Shape Shifter automatically processes entities in dependency order:
1. Root entities first (no dependencies)
2. First-level dependents
3. Second-level dependents
4. Continues until all processed

### Editing Entities: Form vs YAML

Shape Shifter provides two editing modes:

**Form Editor** (Visual):
- Structured input fields
- Guided configuration
- Prevents syntax errors
- Best for: Learning, specific field edits

**YAML Editor** (Code):
- Direct YAML editing
- Monaco editor with syntax highlighting
- Full control over configuration
- Best for: Advanced users, bulk edits, copy/paste

**Switching Modes:**
- Click **Form** tab for visual editing
- Click **YAML** tab for code editing  
- Changes auto-sync when switching
- Must save to persist changes

### Form Editor Fields

**Identity Section:**
- **System ID**: Auto-managed (read-only: `system_id`)
- **Business Keys**: Multi-select columns for deduplication
- **Public ID**: Target PK name (must end with `_id`)

**Data Section:**
- **Type**: Entity type (entity, sql, csv, xlsx, fixed)
- **Columns**: Comma-separated list to extract
- **Source Entity**: Parent entity name (for derived entities)
- **Data Source**: Database connection (for SQL entities)

**Dependencies Section:**
- **Additional Dependencies**: Other required entities
- **Foreign Keys**: Configured separately (see below)

**Transformations:**
- **Unnest**: Configure via form or YAML

### YAML Editor Features

**Syntax Highlighting:**
- Keywords (blue), strings (green), numbers (orange)
- Clear visual structure
- Easy to spot errors

**Auto-Completion:**
- Press `Ctrl+Space` for suggestions
- Entity name completion
- Column name hints (when available)

**Real-Time Validation:**
- Red underlines for syntax errors
- Hover for error details
- Immediate feedback

**Validation Errors:**
- Invalid YAML shows red error banner
- Error message with line number
- Cannot switch to Form tab until valid
- Auto-validates as you type

### Deleting Entities

**Method 1: YAML Deletion**
1. Select entity definition in YAML
2. Delete all lines for that entity
3. Save configuration
4. Validation checks for orphaned references

**Method 2: Form Editor** (Future)
- Right-click entity in tree → Delete
- Confirmation dialog
- Automatic reference cleanup

**⚠️ Important**: Check dependent entities before deleting!
- Deleting a parent breaks child FK references
- Validation will show errors after deletion
- Fix child entities or delete them too

### Managing Dependencies

**Viewing Dependencies:**
- Entity tree shows parent-child relationships
- Indentation indicates dependency depth
- Hover shows dependency count

**Adding Dependencies:**
```yaml
entity_name:
  source: parent_entity          # Derives from parent
  depends_on: [other_entity]     # Also requires other_entity
```

**Circular Dependencies:**
- Not allowed (validation error)
- Example: A → B → C → A (circular!)
- Fix: Break the cycle by removing one dependency

---

## 6. Validation

### Quick Start

1. Click "Validate All" button
2. Choose validation mode:
   - **Sample Data (Fast)**: Preview-based (recommended for development)
   - **Complete Data (Comprehensive)**: Full normalization (recommended before production)
3. Review results in right panel
4. Fix errors (red) first, then warnings (yellow)
5. Revalidate after changes

### Validation Modes

**Sample Mode** (Default):
- ✅ Fast (seconds)
- ✅ Uses preview data (first 1000 rows)
- ✅ Good for iterative development
- ❌ May miss issues in later data
- **Use when**: Developing configuration, quick checks

**Complete Mode**:
- ✅ Comprehensive (validates all data)
- ✅ Runs full normalization pipeline
- ✅ Catches all data issues
- ❌ Slower (minutes for large datasets)
- **Use when**: Pre-production validation, final check

### Understanding Results

**Result Summary:**
- Total issues count
- Breakdown by severity (Error/Warning/Info)
- Entity-level grouping
- Validation mode indicator

**Issue Details:**
Each issue shows:
```
🔴 Column 'old_column' not found in data source
  Entity: sample
  Field: columns
  Code: COLUMN_NOT_FOUND
```

**Severity Guidelines:**
- **Errors** 🔴: Fix before execution (will fail)
- **Warnings** ⚠️: Review carefully (may cause issues)
- **Info** ℹ️: Optional improvements (won't affect execution)

### Common Validation Issues

**Structural Errors:**
- Missing required fields (public_id, type, columns)
- Invalid entity references
- Circular dependencies
- YAML syntax errors

**Data Errors:**
- Column not found in data source
- Duplicate business keys
- Foreign key columns missing
- Type mismatches
- Constraint violations

**Resolution:**
1. Read error message carefully
2. Navigate to entity (click entity name)
3. Fix issue in Form or YAML editor
4. Save changes
5. Revalidate

### Filtering and Search

**Filter by Severity:**
- Click severity badge (Error/Warning/Info)
- Shows only selected severity
- Multi-selection allowed

**Filter by Entity:**
- Select entity in tree
- Shows only that entity's issues
- Click "All" to clear filter

**Search Issues:**
- Type in search box
- Filters by message text
- Real-time filtering

### Validation Best Practices

✅ **Do:**
- Validate frequently during development
- Use Sample mode for quick iteration
- Run Complete mode before production
- Fix errors immediately
- Review warnings carefully
- Revalidate after all changes

❌ **Don't:**
- Skip validation before execution
- Ignore warnings
- Apply multiple untested changes
- Assume Sample catches everything

---

## 7. Execute

### Quick Start

1. Ensure validation passes (no errors)
2. Click "Execute" button (green play icon ▶)
3. Select output format
4. Configure output path/destination
5. Click "Execute"
6. Wait for completion
7. Download result file (if applicable)

### Output Formats

**Excel Workbook (xlsx)**:
- Single `.xlsx` file
- Each entity as separate sheet
- Best for: Manual review, sharing, small-medium datasets
- Path example: `./output/project.xlsx`

**CSV Files**:
- **Single CSV**: Combined data in one file
- **CSV in ZIP**: Multiple CSVs compressed
- Best for: Universal compatibility, scripting
- Path example: `./output/project.csv` or `./output/project.zip`

**CSV Folder**:
- Directory with separate CSV per entity
- Best for: Programmatic access, large datasets
- Path example: `./output/project/`

**PostgreSQL Database**:
- Write directly to PostgreSQL
- Each entity as database table
- Requires pre-configured data source
- Best for: Integration, large datasets, SQL queries

**SQLite Database**:
- Single `.db` file with all entities as tables
- Best for: Portable database, local analysis
- Path example: `./output/project.db`

### Configuration Options

**Run Validation Before Execution**:
- **Default**: ✅ Enabled
- **Recommendation**: Always enabled
- **Purpose**: Catch errors before processing
- **Disable only if**: Re-running after successful validation

**Apply Translations**:
- **Default**: ❌ Disabled
- **Purpose**: Rename columns using mapping config
- **Use when**: Target schema requires different column names
- **Example**: `sample_id` → `sampleId`

**Drop Foreign Key Columns**:
- **Default**: ❌ Disabled
- **Purpose**: Remove FK columns from output
- **Use when**: Want only natural keys
- **Effect**: Cleaner output, fewer columns
- **Note**: Drops system_id columns used for FK linking

### Execution Process

**What Happens:**
1. **Validation** (if enabled): Checks configuration
2. **Load Entities**: Processes in dependency order (roots first)
3. **Link Foreign Keys**: Joins entities using parent `system_id`
4. **Apply Unnest**: Transforms wide → long data
5. **Filter Data**: Applies post-load filters
6. **Export**: Writes to selected format

**Processing Order:**
```
Root entities (no dependencies)
  ↓
First-level children (depend on roots)
  ↓
Second-level children
  ↓
Continue until all processed
```

**Timing:**
- Small projects (< 10 entities, < 10K rows): Seconds
- Medium projects (10-50 entities, 10K-100K rows): Minutes
- Large projects (> 50 entities, > 100K rows): 10+ minutes

### Downloading Results

**For File Outputs** (Excel, CSV, SQLite):
1. Execution completes successfully  
2. Success message: "Successfully executed workflow. Processed X entities."
3. "Download result file" button appears
4. Click to download to browser's download folder

**For Database Outputs** (PostgreSQL):
- Data written directly to database
- No download (access via database client)
- Tables named by entity names

**For Folder Outputs** (CSV Folder):
- No download button
- Access folder directly on filesystem
- Each entity is `entity_name.csv`

### Error Handling

**Validation Errors**:
```
✗ Validation failed, cannot execute
  - Column 'old_col' not found in sample
  - Missing public_id in measurement
```
**Resolution**: Fix errors in configuration, revalidate, retry

**Data Source Errors**:
```
✗ Cannot connect to data source 'postgres_db'
```
**Resolution**: Check data source configuration, verify network/credentials

**Permission Errors**:
```
✗ Permission denied writing to ./output/project.xlsx
```
**Resolution**: Check file/folder permissions, verify path writable

**SQL Errors**:
```
✗ SQL query failed in entity 'measurements'
  Syntax error near 'FROM'
```
**Resolution**: Check SQL syntax in entity configuration

### Best Practices

✅ **Before Execute:**
- Run Complete data validation
- Fix all errors
- Review warnings
- Verify data sources connected
- Check output path writable
- Backup existing output files

✅ **Choosing Format:**
- **Excel**: Best for manual review, sharing
- **CSV**: Universal compatibility, simple
- **Database**: Best for large data, integration, queries
- **Folder**: Best for programmatic access

✅ **After Execute:**
- Verify entity count matches expected
- Spot-check output data
- Confirm FK relationships correct
- Validate against target system (if applicable)

---

## Additional Resources

### Documentation

- **[User Guide Appendix](other/USER_GUIDE_APPENDIX.md)** - System requirements, installation, performance, troubleshooting
- **[Configuration Guide](CONFIGURATION_GUIDE.md)** - Complete YAML configuration reference
- **[Architecture](ARCHITECTURE.md)** - System architecture and components
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development setup and contribution
- **[Testing Guide](TESTING_GUIDE.md)** - Testing procedures

### Getting Help

**Tooltips:**
- Hover over buttons for contextual help
- Wait 500ms for tooltip to appear

**Error Messages:**
- Click errors for detailed information
- Error codes help identify issue type

**Validation Results:**
- Read messages carefully for resolution guidance
- Check field and entity for context

**Backend Logs:**
- Check backend console for detailed errors
- Useful for debugging execution failures

**Support:**
- Check GitHub issues for known problems
- Submit bug reports with reproducible steps
- Contact administrator for help

### Quick Reference

**Keyboard Shortcuts:**
- `Ctrl/Cmd + S` - Save project
- `Ctrl/Cmd + V` - Validate
- `Ctrl/Cmd + E` - Execute
- `Ctrl/Cmd + F` - Find in editor
- See [Appendix: Keyboard Shortcuts](USER_GUIDE_APPENDIX.md#keyboard-shortcuts) for full list

**Identity System:**
- **system_id**: Auto-managed local ID (always `system_id`)
- **keys**: Business identifiers for deduplication
- **public_id**: Target PK name (defines FK columns, must end with `_id`)

**Common Entity Types:**
- `entity`: Derived from another entity
- `sql`: From database query
- `csv`: From CSV file
- `xlsx`: From Excel file
- `fixed`: Static values

**Join Types:**
- `inner`: Strict matching only
- `left`: Keep all children
- `outer`: Keep all records
- `cross`: Cartesian product

**Cardinality:**
- `many_to_one`: Multiple children → one parent
- `one_to_one`: Strict 1:1
- `one_to_many`: One parent → many children

---

**Document Version**: 2.0 (Streamlined)  
**Last Updated**: January 29, 2026  
**For**: Shape Shifter Project Editor v0.1.0
