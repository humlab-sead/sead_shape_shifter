# Phase 2 Implementation Plan - Configuration Editor UI

**Project**: Shape Shifter Configuration Editor  
**Phase**: Phase 2 - Data-Aware Features & Schema Introspection  
**Technology Stack**: Vue 3 + TypeScript + Vuetify + FastAPI  
**Target Duration**: 8 weeks (1 developer, full-time)  
**Document Version**: 1.0  
**Date**: December 13, 2025

---

## 1. Executive Summary

This document provides a detailed, week-by-week implementation plan for Phase 2 of the Configuration Editor UI. Phase 2 builds on the Phase 1 foundation to add data-aware features that leverage actual data sources for intelligent suggestions, validation, and preview capabilities.

### Phase 2 Goals
- ✅ Connect to data sources (PostgreSQL, Access, CSV)
- ✅ Introspect database schemas automatically
- ✅ Preview data transformations before processing
- ✅ Test SQL queries and foreign key relationships with real data
- ✅ Intelligent suggestions based on data patterns
- ✅ Enhanced validation with data-aware checks

### Success Criteria
- 80%+ of entities created using schema introspection
- 95%+ of foreign key errors caught before full processing
- Data preview loads in < 5 seconds
- 67% reduction in entity creation time (15 min → 5 min)
- User satisfaction ≥ 4.5/5 stars

### Prerequisites
- Phase 1 must be complete and stable
- All Phase 1 features tested and documented
- Backend API extensible for new endpoints
- Frontend state management ready for data source state

---

## 2. Project Phases Overview

```
Week 1-2: Data Source Management & Connection
Week 3-4: Schema Introspection & Discovery
Week 5-6: Data Preview & Query Testing
Week 7-8: Smart Suggestions & Enhanced Validation
```

---

## 3. Detailed Week-by-Week Plan

### **Week 1: Data Source Management Backend**

#### **Sprint 1.1: Data Source Models & Service (2 days)**

**Backend Models**
- [ ] Create `app/models/data_source.py`:
  - `DataSourceType` enum (postgresql, access, sqlite, csv)
  - `DataSourceConfig` Pydantic model:
    - name: str
    - driver: DataSourceType
    - host: Optional[str]
    - port: Optional[int]
    - database: Optional[str]
    - username: Optional[str]
    - password: Optional[str] (marked as SecretStr)
    - file_path: Optional[str]
    - connection_string: Optional[str]
  - `DataSourceTestResult` model:
    - success: bool
    - message: str
    - connection_time_ms: int
    - metadata: Optional[Dict]

**Backend Service**
- [ ] Create `app/services/data_source_service.py`:
  - `test_connection(config)` → DataSourceTestResult
  - `get_connection(name)` → database connection
  - `list_data_sources()` → List[DataSourceConfig]
  - `create_data_source(config)` → DataSourceConfig
  - `update_data_source(name, config)` → DataSourceConfig
  - `delete_data_source(name)` → None
- [ ] Implement connection pooling for performance
- [ ] Add connection timeout handling (max 10 seconds)
- [ ] Support environment variable substitution for credentials

**Security**
- [ ] Never log passwords or connection strings
- [ ] Encrypt passwords in storage (optional: use keyring)
- [ ] Support `${ENV_VAR}` syntax for credentials

**Tests**
- [ ] Unit tests for each operation
- [ ] Test connection with mock database
- [ ] Test environment variable substitution
- [ ] Test connection pooling
- [ ] Test timeout handling

**Deliverable**: DataSourceService with connection management

**Acceptance Criteria**:
- Can connect to PostgreSQL test database
- Connection test completes in < 10 seconds
- Credentials never appear in logs
- 80%+ test coverage

**Time Estimate**: 2 days

---

#### **Sprint 1.2: Data Source API Endpoints (2 days)**

**API Endpoints**
- [ ] `GET /api/v1/data-sources` - List all data sources
- [ ] `GET /api/v1/data-sources/{name}` - Get data source details
- [ ] `POST /api/v1/data-sources` - Create new data source
- [ ] `PUT /api/v1/data-sources/{name}` - Update data source
- [ ] `DELETE /api/v1/data-sources/{name}` - Delete data source
- [ ] `POST /api/v1/data-sources/{name}/test` - Test connection
- [ ] `GET /api/v1/data-sources/{name}/status` - Get connection status

**Implementation**
- [ ] Create `app/api/v1/endpoints/data_sources.py`
- [ ] Add request/response models
- [ ] Add error handling (connection failures, timeouts)
- [ ] Add OpenAPI documentation
- [ ] Wire up to DataSourceService

**Security**
- [ ] Sanitize connection errors (don't expose internal details)
- [ ] Validate data source names (no path traversal)
- [ ] Check if data source in use before deletion

**Tests**
- [ ] Integration tests for each endpoint
- [ ] Test error cases (invalid credentials, timeout)
- [ ] Test deletion protection (data source in use)

**Deliverable**: Working data source management API

**Acceptance Criteria**:
- All endpoints work via Swagger UI
- Connection test returns clear success/failure
- Error messages are user-friendly
- Can't delete data source used by entities

**Time Estimate**: 2 days

---

#### **Sprint 1.3: Frontend Data Source State & UI (1 day)**

**Frontend Types**
- [ ] Create `src/types/data-source.ts`:
  - `DataSourceType` enum
  - `DataSource` interface
  - `ConnectionTestResult` interface

**Frontend Store**
- [ ] Create `src/stores/data-source.ts`:
  - State: dataSources, testResults, isLoading
  - Getters: getDataSourceByName, availableDataSources
  - Actions: fetchDataSources, createDataSource, updateDataSource, deleteDataSource, testConnection

**API Client**
- [ ] Create `src/api/data-source-api.ts`:
  - `listDataSources()`
  - `getDataSource(name)`
  - `createDataSource(config)`
  - `updateDataSource(name, config)`
  - `deleteDataSource(name)`
  - `testConnection(name)`

**Deliverable**: Frontend data source management foundation

**Acceptance Criteria**:
- Store integrates with API
- Type-safe data source operations
- Loading states handled

**Time Estimate**: 1 day

---

### **Week 2: Data Source UI & Schema Browser**

#### **Sprint 2.1: Data Source Management View (2 days)**

**UI Components**
- [ ] Create `src/views/DataSourcesView.vue`:
  - List of configured data sources
  - Add/Edit/Delete buttons
  - Connection status indicators
- [ ] Create `src/components/data-source/DataSourceList.vue`:
  - Table with columns: Name, Type, Status, Actions
  - Status indicator (connected/disconnected/testing)
- [ ] Create `src/components/data-source/DataSourceFormDialog.vue`:
  - Type selector (PostgreSQL, Access, SQLite, CSV)
  - Context-sensitive fields based on type
  - "Use environment variable" checkbox for credentials
  - "Test Connection" button
  - Save/Cancel buttons
- [ ] Create `src/components/data-source/ConnectionTestResult.vue`:
  - Success/failure icon
  - Connection time display
  - Error message display (if failed)

**Form Validation**
- [ ] Required fields based on driver type
- [ ] Port number validation (1-65535)
- [ ] File path validation for CSV/Access/SQLite
- [ ] Connection string validation (if provided)

**UI/UX**
- [ ] Color-coded status (green=connected, red=error, yellow=testing)
- [ ] Inline test results
- [ ] Confirmation dialog for deletion
- [ ] Warning if data source in use by entities

**Deliverable**: Complete data source management UI

**Acceptance Criteria**:
- Can create/edit/delete data sources
- Connection test shows clear results
- Form validates inputs
- Professional appearance

**Time Estimate**: 2 days

---

#### **Sprint 2.2: Schema Browser Backend (2 days)**

**Backend Service**
- [ ] Create `app/services/schema_service.py`:
  - `get_tables(data_source_name)` → List[TableMetadata]
  - `get_table_schema(data_source_name, table_name)` → TableSchema
  - `get_table_preview(data_source_name, table_name, limit=10)` → DataFrame
  - `get_primary_keys(data_source_name, table_name)` → List[str]
  - `get_foreign_keys(data_source_name, table_name)` → List[ForeignKeyMetadata]

**Models**
- [ ] Create `app/models/schema.py`:
  - `TableMetadata` (name, row_count, comment)
  - `ColumnMetadata` (name, data_type, nullable, default)
  - `TableSchema` (table_name, columns, primary_keys, indexes)
  - `ForeignKeyMetadata` (column, referenced_table, referenced_column)

**Driver-Specific Implementation**
- [ ] PostgreSQL: Use information_schema queries
- [ ] SQLite: Use sqlite_master and PRAGMA statements
- [ ] Access: Use UCanAccess JDBC metadata
- [ ] CSV: Read header row and infer types from first 100 rows

**Caching**
- [ ] Cache schema metadata (invalidate on demand)
- [ ] Cache preview data (session-based, 5-minute TTL)

**Tests**
- [ ] Unit tests with mock databases
- [ ] Test each driver type
- [ ] Test caching behavior
- [ ] Test with large tables (row count query optimization)

**Deliverable**: Schema introspection service

**Acceptance Criteria**:
- Can list tables from PostgreSQL database
- Can get column metadata with types
- Preview queries complete in < 5 seconds
- Handles tables with millions of rows gracefully

**Time Estimate**: 2 days

---

#### **Sprint 2.3: Schema Browser API & Frontend (1 day)**

**API Endpoints**
- [ ] `GET /api/v1/data-sources/{name}/tables` - List tables
- [ ] `GET /api/v1/data-sources/{name}/tables/{table}/schema` - Get table schema
- [ ] `GET /api/v1/data-sources/{name}/tables/{table}/preview` - Preview data
- [ ] `GET /api/v1/data-sources/{name}/tables/{table}/metadata` - Get table metadata

**Frontend Components**
- [ ] Create `src/components/data-source/SchemaBrowser.vue`:
  - Tree view of tables
  - Expandable table nodes showing columns
  - Search/filter tables
- [ ] Create `src/components/data-source/TablePreview.vue`:
  - Data table with pagination
  - Column headers with types
  - Row count display

**Deliverable**: Schema browser UI

**Acceptance Criteria**:
- Can browse database tables
- Can expand table to see columns
- Preview shows sample data
- Search filters table list

**Time Estimate**: 1 day

---

### **Week 3: SQL Query Testing & Builder**

#### **Sprint 3.1: Query Execution Backend (2 days)**

**Backend Service**
- [ ] Create `app/services/query_service.py`:
  - `execute_query(data_source_name, query, limit=100)` → QueryResult
  - `validate_query(data_source_name, query)` → ValidationResult
  - `explain_query(data_source_name, query)` → QueryPlan
  - `get_query_metadata(data_source_name, query)` → ColumnMetadata[]

**Models**
- [ ] Create `app/models/query.py`:
  - `QueryResult` (rows, columns, execution_time_ms, row_count)
  - `QueryValidation` (is_valid, errors, warnings)
  - `QueryPlan` (plan_text, estimated_cost)

**Security & Safety**
- [ ] Block destructive SQL (INSERT, UPDATE, DELETE, DROP, ALTER)
- [ ] Use read-only connections where possible
- [ ] Timeout protection (max 30 seconds)
- [ ] Result size limit (max 100MB)
- [ ] Query complexity analysis (prevent cartesian products)

**SQL Parsing**
- [ ] Install `sqlparse` library
- [ ] Detect statement type (SELECT, INSERT, etc.)
- [ ] Extract table names from query
- [ ] Basic syntax validation

**Tests**
- [ ] Test query execution
- [ ] Test destructive SQL blocking
- [ ] Test timeout handling
- [ ] Test result size limiting
- [ ] Test with various SQL dialects

**Deliverable**: Query execution service

**Acceptance Criteria**:
- Can execute SELECT queries
- Blocks destructive operations
- Returns results in < 30 seconds or times out
- Clear error messages for syntax errors

**Time Estimate**: 2 days

---

#### **Sprint 3.2: Query Testing API & UI (2 days)**

**API Endpoints**
- [ ] `POST /api/v1/data-sources/{name}/query/execute` - Execute query
- [ ] `POST /api/v1/data-sources/{name}/query/validate` - Validate query
- [ ] `POST /api/v1/data-sources/{name}/query/explain` - Get query plan

**Frontend Components**
- [ ] Create `src/components/query/QueryEditor.vue`:
  - Monaco editor with SQL syntax highlighting
  - "Run Query" button with loading state
  - Query execution stats (time, row count)
  - Error display panel
- [ ] Create `src/components/query/QueryResults.vue`:
  - Data table with pagination
  - Column headers with types
  - Export to CSV button
  - "Use this query" button (populate entity form)

**Editor Features**
- [ ] SQL syntax highlighting
- [ ] Line numbers
- [ ] Keyboard shortcuts (Ctrl+Enter to run)
- [ ] Error line highlighting

**Deliverable**: Query testing UI

**Acceptance Criteria**:
- Can write and execute SQL queries
- Results display in table
- Syntax errors highlighted
- Execution stats shown

**Time Estimate**: 2 days

---

#### **Sprint 3.3: Visual Query Builder (1 day)**

**Frontend Component**
- [ ] Create `src/components/query/QueryBuilder.vue`:
  - Table selector dropdown
  - Column multi-select with search
  - WHERE clause builder (add condition)
  - ORDER BY builder
  - "Generate SQL" button
- [ ] Create `src/components/query/QueryCondition.vue`:
  - Column dropdown
  - Operator dropdown (=, !=, <, >, LIKE, IN, etc.)
  - Value input
  - Delete button

**Query Generation**
- [ ] Generate valid SQL from visual components
- [ ] Support multiple WHERE conditions (AND/OR)
- [ ] Support ORDER BY multiple columns
- [ ] Escape identifiers properly

**Deliverable**: Visual query builder

**Acceptance Criteria**:
- Can build queries visually
- Generated SQL is valid
- Can switch between visual and SQL views
- Changes sync between views

**Time Estimate**: 1 day

---

### **Week 4: Schema Introspection & Auto-Discovery**

#### **Sprint 4.1: Column Discovery Backend (2 days)**

**Backend Service**
- [ ] Enhance `app/services/schema_service.py`:
  - `discover_columns(query, data_source_name)` → List[ColumnMetadata]
  - `suggest_surrogate_id(columns)` → Optional[str]
  - `suggest_natural_keys(columns)` → List[str]
  - `infer_entity_type(table_metadata)` → EntityTypeHint

**Pattern Detection**
- [ ] ID columns: name ends with "ID" or "Id", integer type
- [ ] Natural keys: name ends with "Name", "Code", "Number"
- [ ] Date columns: name contains "Date", "Time", date/timestamp type
- [ ] Lookup tables: small row count (<1000), has ID + Name
- [ ] Fact tables: large row count, multiple foreign keys

**Tests**
- [ ] Test column discovery from SQL query
- [ ] Test surrogate ID suggestions
- [ ] Test natural key suggestions
- [ ] Test entity type inference

**Deliverable**: Column discovery service

**Acceptance Criteria**:
- Correctly identifies column types from query
- Suggests appropriate surrogate IDs
- Pattern detection works on real database schemas

**Time Estimate**: 2 days

---

#### **Sprint 4.2: Import Entity from Table (2 days)**

**Backend Endpoint**
- [ ] `POST /api/v1/data-sources/{name}/tables/{table}/import` - Generate entity from table

**Entity Generation**
- [ ] Generate entity name from table name (convert to snake_case)
- [ ] Generate SQL query: `SELECT * FROM {table}`
- [ ] Auto-populate columns from table schema
- [ ] Suggest surrogate_id from primary key
- [ ] Suggest natural keys from unique constraints
- [ ] Include column types as comments

**Frontend Component**
- [ ] Create `src/components/entity/ImportEntityDialog.vue`:
  - Data source selector
  - Table browser
  - Preview generated entity
  - Customize fields before creating
  - "Import" button

**Workflow**
- [ ] User clicks "Import from Database"
- [ ] Select data source and table
- [ ] System generates entity configuration
- [ ] User reviews and adjusts
- [ ] User clicks "Create Entity"

**Deliverable**: Import entity from database table

**Acceptance Criteria**:
- Can import entity from database table
- Generated entity is valid
- Surrogate ID and keys suggested correctly
- User can customize before creating

**Time Estimate**: 2 days

---

#### **Sprint 4.3: Smart Suggestions (1 day)**

**Backend Service**
- [ ] Create `app/services/suggestion_service.py`:
  - `suggest_foreign_keys(entity, all_entities)` → List[ForeignKeySuggestion]
  - `suggest_dependencies(entity, all_entities)` → List[str]
  - `calculate_suggestion_confidence(suggestion)` → float

**Suggestion Models**
- [ ] Create `app/models/suggestion.py`:
  - `ForeignKeySuggestion` (entity, local_keys, remote_keys, confidence, reason)
  - `DependencySuggestion` (entity, reason)

**Algorithm**
- [ ] Find matching column names across entities
- [ ] Check data integrity (sample foreign key values)
- [ ] Infer cardinality from uniqueness
- [ ] Score suggestions (0.0-1.0):
  - Exact name match: +0.5
  - Data integrity 100%: +0.3
  - Type compatibility: +0.2

**Frontend Component**
- [ ] Create `src/components/entity/SuggestionsPanel.vue`:
  - List of suggestions with confidence scores
  - Accept/Reject buttons
  - Explanation of why suggested

**Deliverable**: Smart suggestions feature

**Acceptance Criteria**:
- Suggests foreign keys based on column names
- Confidence scores are reasonable
- Explanations are clear
- Can accept/reject suggestions

**Time Estimate**: 1 day

---

### **Week 5: Data Preview & Transformation Testing**

#### **Sprint 5.1: Entity Data Preview Backend (2 days)**

**Backend Service**
- [ ] Create `app/services/preview_service.py`:
  - `preview_entity(config_name, entity_name, limit=50)` → DataFrame
  - `preview_with_transformations(entity, limit=50)` → DataFrame
  - `get_entity_sample(entity, limit=100)` → DataFrame

**Integration with Core**
- [ ] Use existing normalizer code to load entity data
- [ ] Apply filters, unnest, etc. to preview
- [ ] Handle entities with dependencies (load dependencies first)
- [ ] Cache preview results (session-based)

**Performance**
- [ ] Limit to 50 rows for preview
- [ ] Use LIMIT clause in SQL queries
- [ ] Avoid loading full datasets
- [ ] Show progress for slow previews

**Tests**
- [ ] Test preview for each entity type (data, sql, fixed)
- [ ] Test with transformations (unnest, filters)
- [ ] Test with dependencies
- [ ] Test caching behavior

**Deliverable**: Entity preview service

**Acceptance Criteria**:
- Can preview entity data (first 50 rows)
- Transformations applied correctly
- Preview loads in < 5 seconds
- Handles dependencies correctly

**Time Estimate**: 2 days

---

#### **Sprint 5.2: Data Preview UI (2 days)**

**Frontend Components**
- [ ] Create `src/components/entity/DataPreview.vue`:
  - Data table with pagination
  - Key columns highlighted
  - Null values styled distinctly
  - Row count display ("Showing 1-50 of ~1,245")
- [ ] Create `src/components/entity/PreviewPanel.vue`:
  - Dockable panel (bottom or right)
  - "Preview Data" button
  - Loading skeleton
  - Error display

**UI Features**
- [ ] Column sorting
- [ ] Column filtering (basic text search)
- [ ] Column width adjustment
- [ ] Export preview to CSV
- [ ] Refresh preview button

**Integration**
- [ ] Add "Preview Data" button to entity editor
- [ ] Open preview panel automatically when clicked
- [ ] Keep preview visible while editing entity
- [ ] Update preview when entity changes (debounced)

**Deliverable**: Data preview UI

**Acceptance Criteria**:
- Can preview entity data
- Preview panel is dockable
- Key columns are highlighted
- Professional table appearance

**Time Estimate**: 2 days

---

#### **Sprint 5.3: Foreign Key Join Testing (1 day)**

**Backend Service**
- [ ] Enhance `app/services/preview_service.py`:
  - `test_foreign_key(entity, foreign_key_config)` → JoinTestResult
  - `get_unmatched_rows(entity, foreign_key_config)` → DataFrame

**Join Test Result**
- [ ] Create `app/models/join_test.py`:
  - `JoinTestResult`:
    - matched_rows: int
    - total_rows: int
    - match_percentage: float
    - unmatched_sample: List[Dict]
    - cardinality_actual: str
    - cardinality_expected: str
    - cardinality_match: bool

**Frontend Component**
- [ ] Create `src/components/entity/ForeignKeyTester.vue`:
  - "Test Join" button in foreign key editor
  - Split view: before/after join
  - Statistics panel (match percentage, cardinality)
  - "View Unmatched Rows" button

**Deliverable**: Foreign key join testing

**Acceptance Criteria**:
- Can test foreign key joins
- Shows match statistics
- Displays unmatched rows
- Detects cardinality mismatches

**Time Estimate**: 1 day

---

### **Week 6: Test Run & Enhanced Validation**

#### **Sprint 6.1: Configuration Test Run Backend (3 days)**

**Backend Service**
- [ ] Create `app/services/test_run_service.py`:
  - `run_test(config_name, options)` → TestRunResult
  - `get_test_progress(run_id)` → TestProgress
  - `cancel_test(run_id)` → None

**Test Run Options**
- [ ] Create `app/models/test_run.py`:
  - `TestRunOptions`:
    - entities: Optional[List[str]] (null = all)
    - max_rows_per_entity: int (default 100)
    - output_format: str ('preview' | 'csv')
    - validate_foreign_keys: bool
- [ ] `TestRunResult`:
  - run_id: str
  - status: str ('running' | 'completed' | 'failed')
  - entities_processed: List[EntityTestResult]
  - total_time_ms: int
  - validation_results: List[ValidationIssue]

**Implementation**
- [ ] Run normalizer on subset of data
- [ ] Process entities in topological order
- [ ] Collect output for each entity
- [ ] Run validation on results
- [ ] Support cancellation
- [ ] Async execution with progress tracking

**Tests**
- [ ] Test with sample configuration
- [ ] Test entity selection
- [ ] Test row limiting
- [ ] Test cancellation
- [ ] Test error handling

**Deliverable**: Configuration test run service

**Acceptance Criteria**:
- Can run transformation on sample data
- Processing order is correct
- Results include all entities
- Can cancel long-running tests
- Completes in reasonable time (<2 min for 100 rows/entity)

**Time Estimate**: 3 days

---

#### **Sprint 6.2: Test Run UI (2 days)**

**Frontend Components**
- [ ] Create `src/views/TestRunView.vue`:
  - Configuration dialog (entity selection, row limit)
  - "Run Test" button
  - Progress indicator
  - Results panel
- [ ] Create `src/components/test-run/TestRunConfig.vue`:
  - Entity multi-select with "Select All"
  - Row limit slider (10-1000)
  - Validation options checkboxes
- [ ] Create `src/components/test-run/TestRunProgress.vue`:
  - Progress bar
  - Current entity being processed
  - Entity processing order list
  - Cancel button
- [ ] Create `src/components/test-run/TestRunResults.vue`:
  - Success/failure summary
  - Per-entity results (rows in/out, time)
  - Validation issues
  - Preview output data
  - Export results

**Deliverable**: Test run UI

**Acceptance Criteria**:
- Can configure and run test
- Progress updates in real-time
- Results are clear and actionable
- Can cancel running tests

**Time Estimate**: 2 days

---

### **Week 7: Data-Aware Validation**

#### **Sprint 7.1: Data Validation Backend (3 days)**

**New Validators**
- [ ] Create `app/validators/data_validators.py`:
  - `ColumnExistsValidator`: Check configured columns exist in data
  - `ForeignKeyDataValidator`: Verify foreign key values exist
  - `NaturalKeyUniquenessValidator`: Check keys are unique
  - `DataTypeCompatibilityValidator`: Check join column types match
  - `NonEmptyResultValidator`: Query returns at least one row

**Validator Framework Enhancement**
- [ ] Add validator priority (structural → data → performance)
- [ ] Add validator category for UI grouping
- [ ] Add suggestion generation for validators
- [ ] Add auto-fix capability where possible

**Data Sampling**
- [ ] Sample 1000 rows for validation (not full dataset)
- [ ] Cache samples per validation run
- [ ] Configurable sample size

**Tests**
- [ ] Unit tests for each validator
- [ ] Test with real database data
- [ ] Test with various edge cases (nulls, duplicates)
- [ ] Test performance with large datasets

**Deliverable**: Data-aware validation framework

**Acceptance Criteria**:
- All new validators work correctly
- Validation runs on sample data (not full dataset)
- Clear error messages with suggestions
- Performance acceptable (<30 seconds for typical config)

**Time Estimate**: 3 days

---

#### **Sprint 7.2: Enhanced Validation UI (2 days)**

**Frontend Components**
- [ ] Enhance `src/components/validation/ValidationReport.vue`:
  - Add "Data Validation" tab
  - Group by category (Structural | Data | Performance)
  - Show validation progress
  - "Run Data Validation" button (separate from structural)
- [ ] Create `src/components/validation/ValidationSuggestion.vue`:
  - Display suggested fixes
  - "Apply Suggestion" button
  - "Apply All" for multiple issues
- [ ] Create `src/components/validation/DataValidationConfig.vue`:
  - Enable/disable specific validators
  - Configure sample size
  - Select entities to validate

**Features**
- [ ] Separate data validation from structural validation
- [ ] Data validation runs on demand (not automatically)
- [ ] Progress indicator for slow validations
- [ ] Group similar issues
- [ ] Auto-fix button where applicable

**Deliverable**: Enhanced validation UI

**Acceptance Criteria**:
- Data validation runs separately
- Clear categorization of issues
- Suggestions are actionable
- Can apply fixes automatically

**Time Estimate**: 2 days

---

### **Week 8: Polish, Integration & Documentation**

#### **Sprint 8.1: Integration & Workflows (2 days)**

**Workflow Integration**
- [ ] Entity creation workflow with data source:
  1. Select data source
  2. Browse tables or write query
  3. Discover columns
  4. Auto-suggest foreign keys
  5. Preview data
  6. Create entity
- [ ] Configuration test workflow:
  1. Configure test options
  2. Run test
  3. Review results
  4. Fix validation issues
  5. Re-test

**UI Improvements**
- [ ] Add quick actions (e.g., "Import from DB" button)
- [ ] Add keyboard shortcuts for common actions
- [ ] Add tooltips explaining features
- [ ] Add onboarding tutorial for new features
- [ ] Add context-sensitive help

**Performance Optimization**
- [ ] Optimize preview queries
- [ ] Implement request debouncing
- [ ] Add loading skeletons
- [ ] Lazy load heavy components
- [ ] Cache API responses

**Deliverable**: Integrated workflows

**Acceptance Criteria**:
- Complete workflows are smooth
- Performance is acceptable (no lag)
- Help is accessible
- Professional polish

**Time Estimate**: 2 days

---

#### **Sprint 8.2: Testing & Bug Fixes (2 days)**

**Testing**
- [ ] End-to-end testing of all Phase 2 features
- [ ] Test with real arbodat database
- [ ] Test error scenarios (connection failures, timeouts)
- [ ] Cross-browser testing
- [ ] Performance testing (large datasets, slow networks)
- [ ] Accessibility testing
- [ ] Security testing (SQL injection, credential exposure)

**Bug Fixes**
- [ ] Fix issues found in testing
- [ ] Address edge cases
- [ ] Improve error messages
- [ ] Fix UI inconsistencies

**Deliverable**: Stable, tested application

**Acceptance Criteria**:
- All critical bugs fixed
- Performance targets met
- Cross-browser compatible
- Accessible (WCAG 2.1 AA)

**Time Estimate**: 2 days

---

#### **Sprint 8.3: Documentation (1 day)**

**User Documentation**
- [ ] Update User Guide with Phase 2 features:
  - Managing data sources
  - Browsing schemas
  - Testing queries
  - Importing entities from database
  - Using smart suggestions
  - Previewing data
  - Running test configurations
  - Data-aware validation
- [ ] Add screenshots/videos
- [ ] Add FAQ section
- [ ] Add troubleshooting guide

**Developer Documentation**
- [ ] Update Developer Guide:
  - Data source architecture
  - Schema introspection design
  - Query execution safety
  - Validation framework extensions
  - Adding new data source drivers
- [ ] Update API documentation
- [ ] Add code comments

**Deployment Documentation**
- [ ] Update deployment guide for database drivers
- [ ] Document environment variable requirements
- [ ] Add configuration examples

**Deliverable**: Complete documentation

**Acceptance Criteria**:
- All Phase 2 features documented
- Clear step-by-step guides
- Updated for both users and developers

**Time Estimate**: 1 day

---

## 4. Risk Management

### 4.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Database driver compatibility issues | Medium | High | Test with all target databases early, have fallback options |
| Query execution timeout/performance | High | Medium | Implement strict timeouts, row limits, query complexity checks |
| Large result sets causing memory issues | Medium | High | Strict result size limits, pagination, streaming where possible |
| SQL injection vulnerabilities | Low | Critical | Use parameterized queries, query validation, read-only connections |
| Schema introspection fails on complex databases | Medium | Medium | Graceful degradation, manual column entry fallback |

### 4.2 Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Database access issues (credentials, permissions) | Medium | Medium | Set up test databases early, document requirements clearly |
| Underestimated complexity of query builder | Low | Medium | Keep MVP simple, visual builder is "could have" feature |
| Integration issues with Phase 1 | Low | High | Maintain clear API contracts, integration tests |

### 4.3 User Acceptance Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Users don't trust automated suggestions | Medium | Medium | Show confidence scores, allow manual override, explain reasoning |
| Preview feature too slow for large databases | Medium | High | Optimize queries, use indexes, strict row limits |
| Confusion about when to use data validation | Low | Low | Clear UI separation, good documentation, tooltips |

---

## 5. Dependencies

### 5.1 External Dependencies

**Python Libraries**:
- `psycopg2-binary` - PostgreSQL driver
- `sqlparse` - SQL parsing and validation
- `pandas` - Data manipulation for previews
- `networkx` - Graph analysis (already used)
- `jpype1` - Java bridge for UCanAccess (Access databases)

**Frontend Libraries**:
- `monaco-editor-vue3` - SQL editor component
- `@vue-flow/core` - Already used, no new dependency

### 5.2 Infrastructure Dependencies

- PostgreSQL test database (for development/testing)
- Access database files (for testing UCanAccess)
- Sample CSV files (for testing)

### 5.3 Phase 1 Dependencies

- All Phase 1 features must be complete and stable
- Entity CRUD API must support extensions
- Validation framework must be extensible
- Configuration store must support data source state

---

## 6. Success Metrics

### 6.1 Feature Adoption

- [ ] 80%+ of users use schema browser
- [ ] 60%+ of entities created via import from database
- [ ] 50%+ of users run test configurations before full processing
- [ ] 70%+ of foreign keys tested with data

### 6.2 Error Reduction

- [ ] 90% reduction in foreign key errors
- [ ] 95% reduction in column name typos
- [ ] 75% reduction in failed transformation runs
- [ ] 80% reduction in data type mismatches

### 6.3 Efficiency Gains

- [ ] Entity creation time: 15 min → 5 min (67% reduction)
- [ ] Configuration debugging time: 80% reduction
- [ ] Time to find data issues: 90% reduction

### 6.4 Performance

- [ ] Schema introspection: < 10 seconds
- [ ] Data preview: < 5 seconds
- [ ] Query execution: < 5 seconds (or timeout)
- [ ] Test run (100 rows/entity): < 2 minutes

### 6.5 Quality

- [ ] User satisfaction: ≥ 4.5/5 stars
- [ ] Bug reports: < 10 critical bugs in first month
- [ ] Data validation accuracy: > 95%

---

## 7. Deliverables Summary

### Week 1-2: Data Source Management
- ✅ Data source CRUD API
- ✅ Connection testing
- ✅ Data source management UI
- ✅ Schema browser (backend)

### Week 3-4: Query & Discovery
- ✅ Query execution API
- ✅ Query testing UI
- ✅ Visual query builder
- ✅ Column discovery
- ✅ Import entity from table
- ✅ Smart suggestions

### Week 5-6: Preview & Testing
- ✅ Entity data preview
- ✅ Foreign key join testing
- ✅ Configuration test runs
- ✅ Test run UI

### Week 7-8: Validation & Polish
- ✅ Data-aware validators
- ✅ Enhanced validation UI
- ✅ Workflow integration
- ✅ Testing & bug fixes
- ✅ Complete documentation

---

## 8. Post-Phase 2 Roadmap

### Potential Phase 3 Features

**Advanced Features** (4-6 weeks):
- Data quality profiling (nulls, duplicates, outliers)
- Performance optimization suggestions
- Data lineage visualization
- Automated testing suite generation
- ML-powered column mapping
- Advanced query optimization

**Collaboration Features** (3-4 weeks):
- Multi-user editing (real-time collaboration)
- Version control integration (Git)
- Comments and annotations
- Change approval workflows

**Enterprise Features** (4-6 weeks):
- Role-based access control
- Audit logging
- SSO integration
- Scheduled jobs
- Email notifications
- API for external tools

---

## 9. Acceptance Criteria Checklist

Phase 2 is complete when:

- [ ] **Data Source Management**
  - [ ] Can configure PostgreSQL, Access, and CSV data sources
  - [ ] Connection testing works reliably
  - [ ] Credentials handled securely
  - [ ] Data sources can be edited and deleted

- [ ] **Schema Introspection**
  - [ ] Can browse database tables
  - [ ] Can view table columns with types
  - [ ] Can preview table data (first 50 rows)
  - [ ] Works with PostgreSQL and Access databases

- [ ] **Query Testing**
  - [ ] Can write and execute SQL queries
  - [ ] Query results display correctly
  - [ ] Destructive SQL is blocked
  - [ ] Query timeout protection works

- [ ] **Smart Features**
  - [ ] Can import entity from database table
  - [ ] Column discovery suggests appropriate columns
  - [ ] Foreign key suggestions are reasonable
  - [ ] Confidence scores are accurate

- [ ] **Data Preview**
  - [ ] Can preview entity data
  - [ ] Transformations applied correctly in preview
  - [ ] Foreign key joins can be tested
  - [ ] Unmatched rows are identified

- [ ] **Test Runs**
  - [ ] Can run test on subset of data
  - [ ] Progress indicator works
  - [ ] Results are clear and actionable
  - [ ] Can cancel running tests

- [ ] **Enhanced Validation**
  - [ ] Data-aware validators detect real issues
  - [ ] Validation runs on sample data (not full dataset)
  - [ ] Suggestions are helpful
  - [ ] Can apply auto-fixes

- [ ] **Quality**
  - [ ] All features documented
  - [ ] Performance targets met
  - [ ] No critical bugs
  - [ ] User acceptance testing passed

---

**Document Version**: 1.0  
**Status**: Ready for Implementation  
**Next Review**: After Week 4 (mid-phase checkpoint)

