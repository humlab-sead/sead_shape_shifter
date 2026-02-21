# Shape Shifter Project Editor - System Capabilities

## 1. Executive Summary

This document describes the capabilities of the Shape Shifter Project Editor, a web-based application that enables users to create and manage data transformation configurations through an intuitive visual interface.

**Target Users**: Data managers, domain specialists, and developers working with data transformation pipelines  
**Purpose**: Enable users to configure complex data transformations without directly editing YAML files  
**Status**: Production-ready with comprehensive project lifecycle support

---

## 2. System Overview

### 2.1 Architecture

The Shape Shifter Project Editor is built on a modern web stack:

**Frontend**:
- Vue 3 with Composition API
- Vuetify 3 for Material Design components
- Pinia for state management
- Monaco Editor for YAML editing
- Cytoscape.js for dependency visualization

**Backend**:
- FastAPI (Python) REST API
- Pydantic v2 for data validation
- Async I/O for performance
- Ingester plugin system

### 2.2 Project Structure

Projects define data transformation pipelines with:

```yaml
entities:
  entity_name:
    source: null | entity_name      # Source entity
    type: entity | sql | fixed | csv | xlsx | openpyxl  # Entity type
    surrogate_id: column_name       # Generated ID column
    keys: [natural_key_columns]     # Natural key columns
    columns: [column_list]          # Columns to extract
    depends_on: [dependencies]      # Processing dependencies
    foreign_keys: [relationships]   # Relationship configs
    unnest: {...}                   # Wide-to-long transformations
    filters: [...]                  # Post-extraction filters
    append: [...]                   # Data augmentation
    reconciliation: [...]           # Reconciliation services

options:
  data_sources: {...}               # Database connections
  translations: {...}               # Column name mappings
  ingesters: {...}                  # Dispatch configuration

mappings:                            # Remote entity mappings
  entity_name: remote_entity
```

### 2.3 Core Capabilities

**Project Management**:
- Create, load, save, and manage YAML projects
- Automatic backups with restore capability
- Session management for concurrent editing
- Dual-mode editing (Form/YAML)

**Entity Management**:
- Visual dependency graph with Cytoscape
- Entity CRUD operations
- Foreign key relationship editing
- Column mapping and transformations

**Validation & Quality**:
- Multi-type validation (structural, data, entity-specific)
- Circular dependency detection
- Auto-fix suggestions with preview
- Real-time validation feedback

**Data Integration**:
- Database connections (PostgreSQL, SQLite, MS Access)
- Schema introspection and exploration
- Query testing and execution
- Data preview for entities

**Reconciliation**:
- Integration with reconciliation services
- Dual-mode editing (Form/YAML)
- Column mapping validation
- Service manifest discovery

**Dispatch**:
- Data dispatch to target systems
- Project-based configuration
- SEAD Clearinghouse integration
- Validation before dispatch

### 2.4 System Constraints

- **Dependency Order**: Entities must be processed in topological order
- **No Circular Dependencies**: System detects and prevents circular references
- **Entity References**: All referenced entities must exist in configuration
- **Naming Conventions**: Entity names use snake_case, surrogate IDs must end with `_id`
- **Data Integrity**: Foreign key relationships must be valid
- **YAML Validity**: Generated configurations must be valid YAML

---

## 3. Feature Catalog

### 3.1 Project Operations

**Project Lifecycle**:
- Load existing YAML configurations from file system
- Create new projects from scratch or templates
- Save projects with automatic backup creation
- Restore from previous versions (backup management)
- Session management with conflict detection

**Project Views**:
- Projects list with metadata (entity count, modified date, validation status)
- Project detail with tabbed interface
- Quick access to recent projects
- Search and filter projects

### 3.2 Entity Management

**Entity Operations**:
- Create entities with form-based wizard
- Edit entity properties in dedicated panel
- Delete entities with dependency checking
- Duplicate entities as templates
- Bulk operations support

**Entity Views**:
- List view with filtering and sorting
- Dependency graph visualization (hierarchical and force-directed layouts)
- Entity detail panel with all properties
- Quick navigation between related entities

**Entity Configuration**:
- Surrogate ID and natural keys
- Column selection and mapping
- Foreign key relationships
- Unnest/melt transformations
- Filters and append operations
- Extra columns with expressions

### 3.3 Dependency Management

**Visualization**:
- Interactive directed graph (Cytoscape.js)
- Hierarchical and force-directed layouts
- Node and edge labels toggle
- Zoom, pan, fit controls
- Legend with node type indicators

**Analysis**:
- Topological sorting
- Circular dependency detection
- Dependency chain tracing
- Deep linking to entities from graph

**Statistics**:
- Node and edge counts
- Processing order display
- Dependency depth analysis

### 3.4 Validation System

**Validation Types**:
- Structural validation (YAML syntax, required fields)
- Data validation (column existence, data types)
- Entity-specific validation (foreign keys, references)
- Circular dependency detection
- Naming convention checks

**Validation Features**:
- Real-time validation as you edit
- Comprehensive validation reports
- Error categorization (error, warning, info)
- Entity-level error summaries
- Quick navigation to errors

**Auto-Fix System**:
- Intelligent fix suggestions
- Fix preview with before/after comparison
- One-click fix application
- Automatic backups before fixes
- Rollback capability

### 3.5 Data Source Integration

**Supported Drivers**:
- PostgreSQL
- SQLite  
- MS Access (via UCanAccess)
- CSV files
- Excel files

**Connection Management**:
- Global data source configuration
- Connection testing
- Credential management
- Connection status monitoring

**Schema Operations**:
- Database schema introspection
- Table and column discovery
- Data type mapping
- Index and constraint information

**Query Capabilities**:
- SQL query testing
- Query execution with result display
- Performance metrics
- Export results to CSV

### 3.6 Schema Explorer

**Features**:
- Browse database schemas
- View table structure (columns, types, keys)
- Data preview with pagination
- Column filtering and sorting
- Export capabilities

**Navigation**:
- Tree view of tables
- Schema selection (PostgreSQL)
- Search and filter
- Quick table selection

### 3.7 Reconciliation Integration

**Service Integration**:
- Connect to reconciliation services
- Service manifest discovery
- Entity reconciliation configuration
- Column mapping editor

**Dual-Mode Editing**:
- Form-based editor with validation
- YAML editor with syntax highlighting
- Seamless switching between modes
- Real-time synchronization

**Validation**:
- Column type validation
- Required field checking
- Service endpoint testing
- Status indicators

### 3.8 Dispatch System

**Configuration**:
- Project-based dispatch settings
- Data source references
- Ingester-specific policies
- Default value management

**Dispatchers**:
- SEAD Clearinghouse integration
- Extensible ingester plugin system
- Validation before dispatch
- Status reporting

**Operations**:
- Validate data before dispatch
- Dispatch to target systems
- Track dispatch history
- Error handling and reporting

### 3.9 YAML Editor

**Editing Features**:
- Monaco Editor integration
- Syntax highlighting
- Auto-formatting
- Validation feedback
- Search and replace

**Editor Capabilities**:
- Direct YAML editing
- Real-time validation
- Error highlighting
- Auto-save support
- Keyboard shortcuts

### 3.10 User Experience

**Interface Design**:
- Material Design (Vuetify 3)
- Dark and light themes
- Responsive layout
- Accessible navigation

**Feedback Systems**:
- Success/error snackbars
- Loading states and progress indicators
- Tooltips and inline help
- Validation status indicators

**Navigation**:
- Sidebar menu
- Breadcrumb trails
- Quick access shortcuts
- Deep linking support

---

## 4. Technical Specifications

### 4.1 Performance

**Response Times**:
- Configuration load: < 2s for 100+ entities
- Entity operations: < 200ms
- Validation: < 3s for 100+ entities  
- Graph rendering: < 1s for 100+ nodes

**Caching**:
- Validation results cached with 5-minute TTL
- Schema introspection cached for 10 minutes
- Smart cache invalidation on configuration changes
- Debounced validation (500ms) prevents excessive re-validation

**Optimization**:
- Lazy-load entity details on demand
- Virtual scrolling for large entity lists
- Code splitting for faster initial load
- Efficient dependency graph algorithms

**Scalability**:
- Supports configurations with 500+ entities
- Handles large dependency graphs smoothly
- Efficient memory usage for large projects

### 4.2 Reliability

**Data Safety**:
- Atomic save operations prevent partial writes
- Automatic timestamped backups on every save
- Backup restoration for version recovery
- Validation before save prevents corrupt configs

**Error Handling**:
- Comprehensive error messages with context
- Graceful degradation on service failures
- Connection retry logic for databases
- Detailed error logging for debugging
- User-friendly error display with recovery suggestions

**Testing**:
- 90%+ test coverage (unit + integration)
- E2E tests for critical user paths
- Continuous integration validation
- Backend and frontend test suites

### 4.3 Usability

**Learning Curve**:
- Form-based editors reduce YAML knowledge requirement
- Inline help and tooltips throughout
- Validation feedback guides corrections
- Intuitive navigation and workflows

**Accessibility**:
- Keyboard shortcuts for common operations (Save: Ctrl/Cmd+S, Find: Ctrl/Cmd+F)
- Responsive design for different screen sizes (desktop 1920x1080+, laptop 1366x768+)
- Material Design with dark/light themes
- Focus indicators and keyboard navigation

**Browser Support**:
- Chrome/Edge 120+
- Firefox 115+
- Safari 16+
- Latest 2 versions of all major browsers

**User Guidance**:
- Comprehensive inline help and tooltips
- Example configurations included
- Documentation for all features
- Success/error feedback with snackbars

### 4.4 Security

**Input Validation**:
- All user inputs sanitized and validated
- YAML structure validation before parsing
- Prevention of code injection attacks
- File size limits to prevent DoS

**Data Security**:
- Secure credential storage for data sources
- HTTPS for all API communications
- Sensitive data excluded from logs
- No credentials in configuration files (environment variables)

**Future Security Features**:
- User authentication and session management
- Role-based access control
- Audit logging for all operations
- Backup encryption

### 4.5 Maintainability

**Code Quality**:
- TypeScript strict mode enforcement
- Pydantic v2 for runtime type safety
- Comprehensive test coverage
- Linting with zero errors (ESLint + Prettier)
- Clear separation of concerns (components, stores, services)

**Documentation**:
- User guides for all major features
- API documentation (OpenAPI/Swagger)
- Code comments for complex logic
- Architecture and system documentation
- Development guides for contributors

**Extensibility**:
- Plugin architecture for validators
- Registry pattern for loaders and dispatchers
- Configurable data source drivers
- Theme support (dark/light modes)
- Modular component architecture

---

## 5. Technology Stack

### 5.1 Frontend

- **Framework**: Vue 3 with Composition API (`<script setup>` syntax)
- **UI Library**: Vuetify 3 (Material Design components)
- **State Management**: Pinia stores
- **Language**: TypeScript with strict mode
- **Code Editor**: Monaco Editor for YAML
- **Visualization**: Cytoscape.js for dependency graphs
- **Build Tool**: Vite
- **Testing**: Vitest (unit), Playwright (E2E)

### 5.2 Backend

- **Framework**: FastAPI (Python)
- **Validation**: Pydantic v2 models
- **Database**: SQLAlchemy ORM
- **Logging**: Loguru
- **Database Drivers**: PostgreSQL, SQLite, MS Access (UCanAccess), CSV, Excel

### 5.3 Infrastructure

- **Browser Support**: Chrome/Edge, Firefox, Safari (latest 2 versions)
- **Configuration**: YAML with `@include` directive support
- **Storage**: Local file system with automatic backup rotation
- **Deployment**: Docker support, standalone application

---

## 6. System Capabilities Summary

Shape Shifter provides a comprehensive web-based interface for managing declarative data transformations:

**Core Strengths**:
- Declarative approach reduces ETL complexity
- Visual tools make complex relationships understandable
- Validation prevents errors before execution
- Auto-fix accelerates problem resolution
- Modular configuration supports maintainability

**Target Users**:
- Domain data managers (minimal programming required)
- Data engineers (accelerated configuration with schema introspection)
- Developers/integrators (API-driven automation support)

**Typical Workflows**:
1. **New Project**: Create configuration → Add data sources → Define entities → Validate → Dispatch
2. **Extend Project**: Load existing → Add entities → Auto-fix validation errors → Save
3. **Debug Issues**: Validate → Review errors → Preview fixes → Apply → Re-validate
4. **Data Integration**: Connect sources → Explore schema → Test queries → Configure reconciliation
5. **Production Deploy**: Validate data → Configure dispatch → Execute transformations

---

## 7. Future Enhancements

**Planned Features**:
- Multi-user collaboration with real-time editing
- Git integration for version control
- Configuration templates library
- Advanced graph analytics (impact analysis, bottleneck detection)
- Configuration diff and merge tools
- Scheduled automated validation
- Entity-level performance profiling
- User-defined custom validators
- Workflow automation and scheduling
- Mobile-responsive interface improvements

**Known Limitations**:
- Single-user editing (no concurrent edit protection)
- Local file system storage only
- Limited audit trail beyond backups
- No auto-reload on external file changes
- Manual refresh required for external updates

---

## 8. Glossary

**Entity**: A data table/view configuration with source, columns, relationships, and transformations

**Surrogate ID**: Auto-generated unique identifier column (must end with `_id`)

**Natural Key**: Business key columns that uniquely identify records

**Foreign Key**: Column(s) referencing another entity's primary/natural key

**Unnest/Melt**: Transformation from wide format to long format (pivot inverse)

**Dependency Graph**: Visual representation of entity relationships and processing order

**Topological Sort**: Ordering entities by dependencies (prerequisites before dependents)

**Reconciliation**: Matching and enriching data against external reference services

**Dispatch**: Sending transformed data to target systems (e.g., databases, APIs)

**Auto-Fix**: Automated correction suggestions for validation errors

**@include**: YAML directive for modular configuration composition

**Data Source**: Connection configuration for databases or file sources

**Schema Introspection**: Automatic discovery of database table and column structure

**Validation**: Multi-level checking (structural, data, entity-specific) of configuration correctness

---

**Document Status**: Production System Documentation  
**Last Updated**: January 12, 2026  
**Version**: 2.0
