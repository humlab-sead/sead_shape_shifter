# Configuration Editor UI - Phase 2 Requirements

## 1. Executive Summary

This document defines requirements for Phase 2 of the Shape Shifter Configuration Editor, building on the Phase 1 foundation. Phase 2 focuses on **data-aware features** that leverage actual data sources to provide intelligent suggestions, validation, and preview capabilities.

**Target Users**: Data managers and domain specialists who need to validate configurations against real data  
**Goal**: Enable data-driven configuration with preview, testing, and intelligent suggestions  
**Scope**: Data source integration, schema introspection, data preview, and enhanced validation

### Phase 2 Goals
- Connect to actual data sources (databases, CSV files)
- Introspect schemas to suggest column names and relationships
- Preview data transformations before processing
- Test queries and validate foreign key relationships with real data
- Provide intelligent suggestions based on actual data structure
- Enhanced validation with data-aware checks

---

## 2. Background & Context

### 2.1 Phase 1 Recap
Phase 1 delivered:
- ✅ Entity CRUD operations
- ✅ Dependency graph visualization
- ✅ Configuration validation (structural)
- ✅ Load/save YAML with backups
- ✅ Foreign key configuration

### 2.2 Phase 2 Focus: Data-Aware Features

Phase 1 validated **configuration structure** but didn't verify against actual data. Phase 2 adds:
- **Data Source Connections**: Test database credentials, browse schemas
- **Schema Introspection**: Discover tables, columns, data types automatically
- **Data Preview**: See actual data samples before processing
- **Query Testing**: Validate SQL queries return expected results
- **Foreign Key Validation**: Verify relationships exist in actual data
- **Smart Suggestions**: Recommend entity configurations based on data patterns

### 2.3 Key Benefits
- **Catch errors earlier**: Detect data issues before running full transformation
- **Reduce manual work**: Auto-discover schemas instead of typing column names
- **Increase confidence**: Preview results before committing to configuration
- **Faster development**: Intelligent suggestions accelerate configuration creation

---

## 3. User Personas

### 3.1 Primary Persona: Domain Data Manager (Enhanced)
- **Name**: Dr. Elena Researcher
- **Phase 2 Needs**:
  - Preview how SQL query transforms source data
  - Verify foreign key relationships actually exist
  - Discover available columns without memorizing schema
  - Test configuration on sample data before full run
  - Get suggestions for common patterns (e.g., date columns)

### 3.2 New Persona: Data Integration Specialist
- **Name**: Maria Integration Engineer
- **Background**: Experienced with databases and ETL processes
- **Goals**:
  - Quickly map multiple database tables to entities
  - Validate join keys before processing
  - Optimize queries for performance
  - Document data lineage
- **Pain Points**:
  - Typos in column names cause silent failures
  - Invalid joins discovered only after hours of processing
  - No way to test transformations incrementally

---

## 4. Functional Requirements

### 4.1 Data Source Management

#### FR-1.1: Configure Data Sources
- **Priority**: MUST HAVE
- **Description**: Manage database connections and file paths
- **Acceptance Criteria**:
  - Add data source with connection details (driver, host, port, database, credentials)
  - Edit existing data source configurations
  - Delete data source (with warning if used by entities)
  - Store credentials securely (environment variables or encrypted storage)
  - Support drivers: PostgreSQL, Access (via UCanAccess), SQLite, CSV files
  - Test connection button shows success/failure
  - List all configured data sources

**UI Details**:
- Data source form fields:
  - Name (unique identifier)
  - Driver (dropdown: postgresql, access, sqlite, csv)
  - Host, Port, Database (for database drivers)
  - Username, Password (optional, with "Use environment variable" checkbox)
  - File path (for CSV/Access/SQLite)
  - Connection string (advanced option)
- "Test Connection" button with loading state
- Success: Show green checkmark + "Connected successfully"
- Failure: Show error message (e.g., "Authentication failed")

---

#### FR-1.2: Browse Data Source Schema
- **Priority**: MUST HAVE
- **Description**: Explore database structure without writing queries
- **Acceptance Criteria**:
  - List all tables/views in selected database
  - Show table row counts
  - For each table, list columns with data types
  - Show primary keys and indexes
  - Show foreign key relationships (if available)
  - Search/filter tables by name
  - Preview first 10 rows of any table

**UI Details**:
- Tree view or expandable list:
  ```
  📁 arbodat_data (PostgreSQL)
    📊 tblSample (1,245 rows)
      🔑 SampleID (integer, primary key)
      📝 SampleName (varchar)
      📅 CollectionDate (date)
    📊 tblDating (832 rows)
      ...
  ```
- Click table → show column list in side panel
- "Preview Data" button → shows data table modal

---

#### FR-1.3: Test SQL Queries
- **Priority**: MUST HAVE
- **Description**: Execute SQL queries to validate syntax and preview results
- **Acceptance Criteria**:
  - Execute SELECT queries against configured data source
  - Show result set with pagination (max 100 rows)
  - Show query execution time
  - Syntax highlighting in SQL editor
  - Show error messages for invalid SQL
  - Prevent destructive queries (INSERT/UPDATE/DELETE)
  - Show column names and data types in result

**UI Details**:
- SQL editor with syntax highlighting (Monaco or CodeMirror)
- "Run Query" button
- Results shown in data table below editor
- Execution stats: "Returned 45 rows in 0.12 seconds"
- Error display: "Syntax error at line 3: unexpected token 'FORM'"

---

### 4.2 Schema Introspection & Smart Suggestions

#### FR-2.1: Auto-Discover Columns
- **Priority**: MUST HAVE
- **Description**: Automatically populate column list from data source
- **Acceptance Criteria**:
  - For SQL entities: Extract column names from query result
  - For CSV entities: Read header row
  - Show detected columns with data types
  - Allow user to select which columns to include
  - Suggest surrogate_id column if numeric ID column exists
  - Suggest natural keys based on column names (e.g., columns ending in "Name", "Code")

**UI Details**:
- "Discover Columns" button in entity editor
- Shows modal with checkboxes:
  ```
  ☑️ SampleID (integer) → Suggested as surrogate_id
  ☑️ SampleName (varchar)
  ☑️ CollectionDate (date)
  ☐ InternalNotes (text) → Unchecked by default
  ```
- "Select All" / "Deselect All" buttons
- Apply → populates columns field in entity editor

---

#### FR-2.2: Suggest Foreign Keys
- **Priority**: SHOULD HAVE
- **Description**: Recommend foreign key relationships based on data
- **Acceptance Criteria**:
  - Detect columns with similar names across entities (e.g., "SampleID")
  - Check if values in potential foreign key column exist in target entity
  - Suggest cardinality (one-to-one, many-to-one) based on uniqueness
  - Show confidence score for suggestions
  - Allow user to accept or reject suggestions

**Algorithm**:
1. Find columns with matching names in different entities
2. Query data to check referential integrity (do all values exist in target?)
3. Calculate cardinality (check uniqueness in both entities)
4. Score suggestions based on:
   - Name similarity (100% match = high score)
   - Data integrity (100% matching values = high score)
   - Column types match = bonus points

**UI Details**:
- "Suggest Foreign Keys" button
- Shows list of suggestions:
  ```
  💡 dating.SampleID → sample.SampleID (95% confidence)
    - All 832 values found in sample table
    - Many-to-one relationship (multiple dating rows per sample)
    [Accept] [Reject]
  ```

---

#### FR-2.3: Intelligent Entity Templates
- **Priority**: SHOULD HAVE
- **Description**: Offer pre-configured entity templates based on data patterns
- **Acceptance Criteria**:
  - Detect common patterns (lookup table, fact table, date dimension)
  - Suggest entity configuration based on pattern
  - Templates include sensible defaults (keys, columns, unnest config)

**Pattern Detection**:
- **Lookup Table**: Small table (<1000 rows), has ID + Name columns, no foreign keys
- **Fact Table**: Large table, multiple foreign keys, has date/measure columns
- **Bridge Table**: Only foreign key columns, no descriptive attributes
- **Date Dimension**: Columns with date-related names (Year, Month, Day, etc.)

**UI Details**:
- When creating entity from database table, show suggested template:
  ```
  📋 Template Suggestion: Lookup Table
  - Set sample_type_id as surrogate_id
  - Set sample_type_name as natural key
  - No foreign keys detected
  [Use Template] [Customize]
  ```

---

### 4.3 Data Preview & Transformation Testing

#### FR-3.1: Preview Entity Data
- **Priority**: MUST HAVE
- **Description**: Show sample data for an entity before processing
- **Acceptance Criteria**:
  - Load first 50 rows of entity data
  - Show data in table with column headers
  - Highlight columns configured as keys
  - Show surrogate_id values (if generated)
  - Filter and sort preview data
  - Show data types for each column
  - Indicate null values clearly

**UI Details**:
- "Preview Data" button in entity details
- Opens modal with data table
- Key columns have bold headers or colored background
- Null values shown as `<null>` in gray
- Pagination controls (showing rows 1-50 of ~1,245)

---

#### FR-3.2: Test Foreign Key Joins
- **Priority**: MUST HAVE
- **Description**: Preview joined data before running full transformation
- **Acceptance Criteria**:
  - Show sample of join result (first 50 rows)
  - Highlight unmatched rows (if left/outer join)
  - Show match statistics (e.g., "832 rows joined, 3 unmatched")
  - Compare before/after column counts
  - Validate cardinality matches constraints

**UI Details**:
- "Test Join" button in foreign key editor
- Shows split view:
  - Left: Source entity sample
  - Right: Joined result
- Statistics panel:
  ```
  Join Results:
  ✓ 829 rows matched (99.6%)
  ⚠️ 3 rows unmatched (0.4%)
  ✗ Cardinality mismatch: Expected many-to-one, found one-to-many
  ```

---

#### FR-3.3: Preview Unnest Operations
- **Priority**: SHOULD HAVE
- **Description**: Show how wide-to-long transformations will look
- **Acceptance Criteria**:
  - Show original wide format (first 5 rows)
  - Show transformed long format (first 20 rows)
  - Highlight id_vars and value_vars columns
  - Show before/after row counts

**UI Details**:
- "Preview Unnest" button in unnest configuration
- Side-by-side comparison:
  ```
  Before (Wide):
  | SampleID | Taxon1 | Taxon2 | Taxon3 |
  |----------|--------|--------|--------|
  | 1        | Oak    | Pine   | Birch  |
  
  After (Long):
  | SampleID | TaxonType | TaxonName |
  |----------|-----------|-----------|
  | 1        | Taxon1    | Oak       |
  | 1        | Taxon2    | Pine      |
  | 1        | Taxon3    | Birch     |
  
  Row count: 1 → 3 (3x expansion)
  ```

---

#### FR-3.4: Test Full Configuration
- **Priority**: SHOULD HAVE
- **Description**: Run transformation on subset of data to validate configuration
- **Acceptance Criteria**:
  - Select entities to test (or all)
  - Limit to first N rows per entity (configurable, default 100)
  - Run full transformation pipeline
  - Show output for each entity
  - Display validation results
  - Show processing time and row counts
  - Compare output to expected schema

**UI Details**:
- "Test Run" button in main toolbar
- Configuration dialog:
  - Select entities to include
  - Max rows per entity (slider: 10-1000)
  - Output format (in-memory preview, CSV export)
- Progress indicator showing entity processing order
- Results panel showing success/failure per entity

---

### 4.4 Enhanced Validation

#### FR-4.1: Data-Aware Validation
- **Priority**: MUST HAVE
- **Description**: Validate configuration against actual data
- **Acceptance Criteria**:
  - Check if configured columns exist in data source
  - Validate foreign key columns exist in both entities
  - Check if natural keys are actually unique in data
  - Validate data types are compatible for joins
  - Check for null values in required columns
  - Warn if query returns no rows

**New Validation Rules**:
- **ColumnExistsValidator**: Configured columns exist in query result
- **ForeignKeyDataValidator**: Foreign key values exist in target entity
- **NaturalKeyUniquenessValidator**: Natural keys are unique in data
- **DataTypeCompatibilityValidator**: Join columns have compatible types
- **NonEmptyResultValidator**: Query returns at least one row

---

#### FR-4.2: Foreign Key Data Validation
- **Priority**: MUST HAVE
- **Description**: Verify foreign key relationships exist in actual data
- **Acceptance Criteria**:
  - Check if all foreign key values exist in target entity
  - Report orphaned rows (foreign key value not found)
  - Suggest how to fix orphaned rows (add missing data, change join type)
  - Show percentage of successful matches

**UI Details**:
- Validation report shows:
  ```
  ⚠️ Foreign Key Validation: dating → sample
    - 829/832 rows matched (99.6%)
    - 3 orphaned rows with SampleID not in sample table
    - Suggested fix: Change join type to 'left' to keep orphaned rows
    [View Orphaned Rows] [Apply Suggestion]
  ```

---

### 4.5 Query Builder & SQL Assistance

#### FR-5.1: Visual Query Builder
- **Priority**: COULD HAVE
- **Description**: Build SQL queries visually for non-SQL users
- **Acceptance Criteria**:
  - Select table from dropdown
  - Select columns to include (multi-select with search)
  - Add WHERE clause conditions (column, operator, value)
  - Add JOIN clauses (select table, join type, conditions)
  - Add ORDER BY clauses
  - Generate SQL from visual components
  - Edit generated SQL manually if needed
  - Validate query before saving

**UI Details**:
- Tabbed interface:
  - **Visual** tab: Form-based query builder
  - **SQL** tab: Text editor with syntax highlighting
- Visual builder components:
  - Table selector dropdown
  - Columns multi-select (with "Select All")
  - WHERE conditions list (+ Add Condition button)
  - JOIN configurator
- "Generate SQL" button to see text query
- Switch between tabs preserves changes

---

#### FR-5.2: SQL Syntax Assistance
- **Priority**: SHOULD HAVE
- **Description**: Help users write correct SQL
- **Acceptance Criteria**:
  - Autocomplete for table names
  - Autocomplete for column names
  - Keyword highlighting (SELECT, FROM, WHERE, etc.)
  - Syntax error highlighting
  - Common SQL snippets (JOIN template, GROUP BY example)

**UI Details**:
- SQL editor features:
  - Ctrl+Space for autocomplete
  - Red underline for syntax errors
  - Tooltip on hover showing error details
  - Snippet library sidebar (optional)

---

### 4.6 Import/Export Enhancements

#### FR-6.1: Import Entity from Database Table
- **Priority**: SHOULD HAVE
- **Description**: Create entity directly from database table
- **Acceptance Criteria**:
  - Select data source and table
  - Auto-populate entity properties:
    - Name from table name (converted to snake_case)
    - Columns from table columns
    - Surrogate_id from primary key
    - Keys from unique constraints
  - Generate SQL query automatically
  - Allow customization before creating entity

**Workflow**:
1. Click "Import from Database"
2. Select data source
3. Select table from list
4. System populates entity form
5. User reviews and adjusts
6. Click "Create Entity"

---

#### FR-6.2: Export Entity Definitions
- **Priority**: COULD HAVE
- **Description**: Export entity configurations for reuse
- **Acceptance Criteria**:
  - Export single entity as YAML snippet
  - Export multiple entities (preserving dependencies)
  - Import entity from YAML snippet
  - Validate imported entities

---

#### FR-6.3: Clone Configuration
- **Priority**: SHOULD HAVE
- **Description**: Create new configuration based on existing one
- **Acceptance Criteria**:
  - Select source configuration
  - Specify new configuration name
  - Optionally select which entities to copy
  - Update references if entities renamed

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### NFR-1.1: Query Execution
- **Priority**: MUST HAVE
- Preview queries must complete in < 5 seconds
- Schema introspection in < 10 seconds
- Test runs (100 rows) in < 30 seconds

#### NFR-1.2: Data Caching
- **Priority**: SHOULD HAVE
- Cache schema metadata (refresh on demand)
- Cache preview data (invalidate on query change)
- Session-based caching for repeated previews

### 5.2 Security

#### NFR-2.1: Credential Management
- **Priority**: MUST HAVE
- Never store plain-text passwords in configuration files
- Support environment variable references
- Optional: Encrypt credentials at rest
- Credentials not included in exported configurations

#### NFR-2.2: Query Safety
- **Priority**: MUST HAVE
- Block destructive SQL (INSERT, UPDATE, DELETE, DROP, ALTER)
- Read-only database connections where possible
- Timeout protection (max 30 seconds)
- Resource limits (max 100MB result set for preview)

### 5.3 Usability

#### NFR-3.1: Progressive Disclosure
- **Priority**: SHOULD HAVE
- Basic entity creation doesn't require data source connection
- Advanced features (preview, test) available when data source configured
- Clear indicators when features require data source

#### NFR-3.2: Error Recovery
- **Priority**: MUST HAVE
- Connection failures don't lose work
- Validation continues if preview unavailable
- Graceful degradation (suggest columns even if preview fails)

---

## 6. User Interface Requirements

### 6.1 New Views

#### UI-1.1: Data Sources View
- List all configured data sources
- Add/Edit/Delete data source buttons
- Test connection status indicators
- Schema browser panel

#### UI-1.2: Data Preview Panel
- Dockable panel (bottom or right side)
- Shows preview for selected entity
- Can pin preview while editing
- Collapsible to save space

#### UI-1.3: Query Builder View
- Split view: Visual builder | SQL editor
- Table browser sidebar
- Preview results panel

### 6.2 Enhanced Entity Editor

#### UI-2.1: Data Source Integration
- "Connect Data Source" section at top
- "Discover Columns" button near columns field
- "Test Query" button for SQL entities
- "Preview Data" button in all entity types

#### UI-2.2: Foreign Key Testing
- "Test Join" button in each foreign key row
- Inline match statistics
- Expandable details showing unmatched rows

### 6.3 Validation Enhancements

#### UI-3.1: Data Validation Tab
- Separate tab for data-aware validation results
- Group by: Structural | Data Integrity | Performance
- "Run Data Validation" button (doesn't run automatically)
- Progress indicator for slow validations

---

## 7. Use Cases

### UC-1: Create SQL Entity with Data Preview

**Actor**: Domain Data Manager  
**Precondition**: Database connection configured  
**Flow**:
1. User clicks "New Entity"
2. User enters name: "sample"
3. User selects type: "sql"
4. User selects data_source: "arbodat_data"
5. User clicks "Browse Tables"
6. System shows list of tables
7. User selects "tblSample"
8. User clicks "Import Table Structure"
9. System generates SQL query: `SELECT * FROM tblSample`
10. System populates columns from table schema
11. User clicks "Preview Data"
12. System shows first 50 rows
13. User reviews data and adjusts columns
14. User clicks "Create"
15. Entity created successfully

**Postcondition**: Entity created with validated query

---

### UC-2: Test Foreign Key Relationship

**Actor**: Domain Data Manager  
**Precondition**: Two entities exist (sample, dating)  
**Flow**:
1. User opens "dating" entity editor
2. User adds foreign key:
   - entity: sample
   - local_keys: [SampleID]
   - remote_keys: [SampleID]
3. User clicks "Test Join"
4. System queries both entities
5. System performs join on SampleID
6. System shows results:
   - 829/832 rows matched
   - 3 orphaned rows
7. System suggests: "Change to left join to keep all dating rows"
8. User reviews orphaned rows
9. User decides to change to left join
10. User saves entity

**Postcondition**: Foreign key validated with data

---

### UC-3: Use Query Builder

**Actor**: Non-technical user  
**Precondition**: Database connection configured  
**Flow**:
1. User creates new SQL entity
2. User clicks "Visual Query Builder"
3. System shows query builder interface
4. User selects table: "tblDating"
5. User selects columns:
   - Projekt
   - Befu
   - ProbNr
   - DatMethod
6. User adds WHERE condition:
   - Column: DatMethod
   - Operator: "="
   - Value: "C14"
7. User clicks "Generate SQL"
8. System generates:
   ```sql
   SELECT Projekt, Befu, ProbNr, DatMethod
   FROM tblDating
   WHERE DatMethod = 'C14'
   ```
9. User clicks "Test Query"
10. System shows 45 rows returned
11. User saves entity

**Postcondition**: SQL query created without manual SQL writing

---

## 8. Success Metrics

### 8.1 Efficiency Metrics
- **Time to create entity**: Reduce from 15 min → 5 min (67% improvement)
- **Data errors caught**: Increase from 60% → 95% (before full processing)
- **Configuration debugging time**: Reduce by 80%

### 8.2 Quality Metrics
- **Foreign key errors**: Reduce by 90%
- **Column name typos**: Reduce to near-zero
- **Failed transformation runs**: Reduce by 75%

### 8.3 Adoption Metrics
- **Users using data preview**: >80% of active users
- **Entities created via introspection**: >60%
- **User satisfaction**: ≥4.5/5 stars

---

## 9. Dependencies

### 9.1 Technical Dependencies
- Database drivers (psycopg2, sqlite3, etc.)
- Query parsing library (sqlparse)
- Data sampling utilities
- Schema introspection utilities

### 9.2 Phase 1 Requirements
- All Phase 1 features must be complete
- Entity CRUD API stable
- Validation framework extensible

---

## 10. Out of Scope (Future Phases)

The following are explicitly NOT in Phase 2:
- Real-time collaboration (multi-user editing)
- Version control integration (Git)
- ML-powered suggestions
- Performance optimization recommendations
- Automated testing suite generation
- Data quality profiling
- Full ETL pipeline monitoring
- Data lineage tracking
- Custom validation rule builder
- Scheduling and automation

These may be considered for Phase 3 and beyond.

---

## 11. Acceptance Criteria Summary

Phase 2 is complete when:
- [ ] Users can configure and test database connections
- [ ] Schema introspection works for PostgreSQL and Access databases
- [ ] Users can preview entity data (first 50 rows)
- [ ] SQL query testing shows results and errors
- [ ] Foreign key relationships can be tested with actual data
- [ ] Column names auto-discovered from data sources
- [ ] Data-aware validation catches column/join errors
- [ ] Visual query builder creates valid SQL
- [ ] Test runs validate configuration on sample data
- [ ] All Phase 2 features documented in user guide
- [ ] Performance targets met (queries < 5s, previews < 10s)
- [ ] Security requirements met (no plain-text passwords)

---

**Document Version**: 1.0  
**Date**: December 13, 2025  
**Status**: Draft for Review
