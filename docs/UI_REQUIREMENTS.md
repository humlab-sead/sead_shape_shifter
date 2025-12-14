# Configuration Editor UI - Requirements Specification

## 1. Executive Summary

This document defines the functional and non-functional requirements for the Shape Shifter Configuration Editor, a web-based UI that enables users to create and manage data transformation configurations without directly editing YAML files.

**Target Users**: Data managers, domain specialists, and developers working with data transformation pipelines  
**Goal**: Enable users to configure complex data transformations through an intuitive visual interface  
**Scope**: Complete configuration lifecycle including creation, editing, validation, testing, and data-aware features

---

## 2. System Overview

### 2.1 Purpose

The Configuration Editor provides a user-friendly interface for managing entity configurations in the Shape Shifter data transformation framework. It bridges the gap between complex YAML configuration files and user needs, offering:

- Visual entity relationship management
- Real-time configuration validation
- Intelligent auto-fix suggestions
- Data-aware features (schema introspection, preview)
- Form-based editing to prevent syntax errors

### 2.2 Configuration Structure

Configurations define data transformation pipelines with:

```yaml
entities:
  entity_name:
    source: null | entity_name      # Data source entity
    type: data | sql | fixed        # Entity type
    surrogate_id: column_name       # Generated ID column
    keys: [natural_key_columns]     # Natural key columns
    columns: [column_list]          # Columns to extract
    depends_on: [dependencies]      # Processing dependencies
    foreign_keys: [relationships]   # Relationship configs
    unnest: {...}                   # Wide-to-long transformations
    filters: [...]                  # Post-extraction filters
    append: [...]                   # Data augmentation

options:
  data_sources: {...}               # Database connections
  translations: {...}               # Column name mappings

mappings:                            # Remote entity mappings
  entity_name: remote_entity
```

### 2.3 Key Constraints

- **Dependency Order**: Entities must be processed in topological order
- **No Circular Dependencies**: System must detect and prevent circular references
- **Entity References**: All referenced entities must exist in configuration
- **Naming Conventions**: Entity names use snake_case, surrogate IDs must end with `_id`
- **Data Integrity**: Foreign key relationships must be valid
- **YAML Validity**: Generated configurations must be valid YAML

---

## 3. User Personas

### 3.1 Domain Data Manager

**Background**: Subject matter expert with domain knowledge but limited programming experience

**Goals**:
- Configure data imports from domain-specific databases
- Define entity relationships matching domain understanding
- Validate configurations against actual data
- Preview transformations before full processing

**Pain Points**:
- YAML syntax is error-prone
- Difficult to visualize entity dependencies
- Hard to validate configuration correctness
- Time-consuming to test configurations

### 3.2 Data Engineer

**Background**: Technical user comfortable with code and SQL

**Goals**:
- Quickly create configurations for new data sources
- Leverage schema introspection to accelerate setup
- Test SQL queries and data transformations
- Debug configuration issues efficiently

**Pain Points**:
- Manual column listing is tedious
- Need to switch between tools for testing
- Configuration errors only discovered at runtime
- Difficult to maintain complex configurations

### 3.3 Developer/Integrator

**Background**: Software developer integrating Shape Shifter into data pipelines

**Goals**:
- Understand configuration structure and options
- Programmatically generate configurations
- Validate configurations before deployment
- Debug transformation issues

**Pain Points**:
- Need comprehensive documentation
- API endpoints for automation
- Clear error messages and validation
- Version control and change tracking

---

## 4. Functional Requirements

### 4.1 Configuration Management

#### FR-1: Load Configuration
**Priority**: Must Have  
**Description**: Load existing YAML configuration files for editing

**Acceptance Criteria**:
- Load configuration from file system
- Parse YAML and display in editor
- Handle malformed YAML with clear error messages
- Support large configurations (100+ entities)

#### FR-2: Save Configuration  
**Priority**: Must Have  
**Description**: Save modified configuration to YAML file

**Acceptance Criteria**:
- Validate configuration before saving
- Create backup of existing file
- Atomic write operations (no partial saves)
- Provide save confirmation feedback

#### FR-3: Create New Configuration
**Priority**: Must Have  
**Description**: Create new configuration from scratch or template

**Acceptance Criteria**:
- Provide blank configuration option
- Offer templates for common scenarios
- Pre-populate with sensible defaults
- Validate new configuration structure

#### FR-4: Configuration Versioning
**Priority**: Should Have  
**Description**: Track configuration changes over time

**Acceptance Criteria**:
- Create timestamped backups on save
- Display backup history
- Restore from previous version
- Compare versions (diff view)

### 4.2 Entity Management

#### FR-5: Create Entity
**Priority**: Must Have  
**Description**: Add new entity to configuration

**Acceptance Criteria**:
- Form-based entity creation
- Validate entity name uniqueness
- Set required properties (name, type, source)
- Add to configuration in correct dependency order

#### FR-6: Edit Entity
**Priority**: Must Have  
**Description**: Modify existing entity properties

**Acceptance Criteria**:
- Update all entity properties
- Validate changes before applying
- Update dependencies automatically
- Provide undo capability

#### FR-7: Delete Entity
**Priority**: Must Have  
**Description**: Remove entity from configuration

**Acceptance Criteria**:
- Confirm deletion with user
- Check for dependent entities
- Cascade delete option or prevention
- Update configuration structure

#### FR-8: Duplicate Entity
**Priority**: Should Have  
**Description**: Copy entity as template for new entity

**Acceptance Criteria**:
- Copy all properties except name
- Generate unique name automatically
- Clear entity-specific values (surrogate_id)
- Validate duplicated entity

### 4.3 Entity Visualization

#### FR-9: Dependency Graph
**Priority**: Must Have  
**Description**: Visualize entity relationships and dependencies

**Acceptance Criteria**:
- Display directed graph of entities
- Show foreign key relationships
- Highlight circular dependencies
- Interactive navigation (zoom, pan, click)

#### FR-10: Entity Tree View
**Priority**: Must Have  
**Description**: Hierarchical tree view of entities

**Acceptance Criteria**:
- Display entities in dependency order
- Expand/collapse entity groups
- Search and filter entities
- Quick navigation to entity details

#### FR-11: Entity Properties Panel
**Priority**: Must Have  
**Description**: Side panel showing entity details

**Acceptance Criteria**:
- Display all entity properties
- Inline editing of simple properties
- Jump to related entities (foreign keys, source)
- Show entity statistics (columns, dependencies)

### 4.4 Validation

#### FR-12: Structural Validation
**Priority**: Must Have  
**Description**: Validate configuration structure and syntax

**Acceptance Criteria**:
- Check YAML syntax validity
- Verify required properties present
- Validate entity references exist
- Detect circular dependencies
- Check naming conventions

#### FR-13: Data Validation
**Priority**: Must Have  
**Description**: Validate configuration against actual data sources

**Acceptance Criteria**:
- Verify columns exist in data sources
- Check data types compatibility
- Validate foreign key relationships
- Test SQL queries execute successfully
- Report data quality issues

#### FR-14: Validation Reporting
**Priority**: Must Have  
**Description**: Display validation results with clear messages

**Acceptance Criteria**:
- Categorize errors by severity (error, warning, info)
- Show error location (entity, property, line)
- Provide actionable error messages
- Filter and search validation results
- Export validation report

#### FR-15: Real-Time Validation
**Priority**: Should Have  
**Description**: Validate configuration as user makes changes

**Acceptance Criteria**:
- Debounced validation (avoid constant re-validation)
- Display validation status indicator
- Highlight errors inline in editor
- Cache validation results (5-minute TTL)

### 4.5 Auto-Fix

#### FR-16: Fix Suggestions
**Priority**: Must Have  
**Description**: Provide intelligent fix suggestions for validation errors

**Acceptance Criteria**:
- Analyze validation errors
- Generate applicable fix suggestions
- Categorize by fix type (automatic, manual, complex)
- Display fix description and impact

#### FR-17: Preview Fix
**Priority**: Must Have  
**Description**: Show changes before applying fix

**Acceptance Criteria**:
- Display before/after comparison
- Show all affected configuration parts
- Highlight changes clearly
- Allow fix cancellation

#### FR-18: Apply Fix
**Priority**: Must Have  
**Description**: Apply suggested fix to configuration

**Acceptance Criteria**:
- Create automatic backup before fix
- Apply fix atomically
- Revalidate after fix
- Provide success/failure feedback

#### FR-19: Rollback Fix
**Priority**: Must Have  
**Description**: Undo applied fix if result is unsatisfactory

**Acceptance Criteria**:
- Restore from automatic backup
- Maintain rollback history
- Allow selective rollback
- Confirm before rollback

### 4.6 Data-Aware Features

#### FR-20: Data Source Connection
**Priority**: Should Have  
**Description**: Connect to databases and test credentials

**Acceptance Criteria**:
- Configure database connections
- Test connection before saving
- Display connection status
- Securely store credentials

#### FR-21: Schema Introspection
**Priority**: Should Have  
**Description**: Discover tables and columns from data sources

**Acceptance Criteria**:
- List available tables in database
- Display column names and types
- Suggest entity configurations based on schema
- Auto-populate column lists

#### FR-22: Data Preview
**Priority**: Should Have  
**Description**: Show sample data from entities

**Acceptance Criteria**:
- Display first N rows of entity data
- Show column names and types
- Filter and sort preview data
- Export preview to CSV

#### FR-23: Query Testing
**Priority**: Should Have  
**Description**: Test SQL queries before adding to configuration

**Acceptance Criteria**:
- Execute SQL queries on demand
- Display query results
- Show execution time and row count
- Validate query syntax

#### FR-24: Foreign Key Validation
**Priority**: Should Have  
**Description**: Verify foreign key relationships in actual data

**Acceptance Criteria**:
- Check referenced keys exist
- Identify orphaned records
- Validate cardinality constraints
- Report match percentages

### 4.7 YAML Editor

#### FR-25: Syntax Highlighting
**Priority**: Must Have  
**Description**: Visual syntax highlighting for YAML

**Acceptance Criteria**:
- Color-code YAML elements
- Highlight keywords and values
- Show indentation guides
- Support dark/light themes

#### FR-26: Code Completion
**Priority**: Should Have  
**Description**: Auto-complete entity and property names

**Acceptance Criteria**:
- Suggest entity names
- Complete property names
- Show available values for enums
- Context-aware suggestions

#### FR-27: Error Highlighting
**Priority**: Must Have  
**Description**: Highlight validation errors in editor

**Acceptance Criteria**:
- Underline error locations
- Show error on hover
- Jump to error location
- Clear errors on fix

#### FR-28: Search and Replace
**Priority**: Should Have  
**Description**: Find and replace text in YAML

**Acceptance Criteria**:
- Search with regex support
- Replace all or selective
- Case-sensitive option
- Search history

### 4.8 User Experience

#### FR-29: Responsive Design
**Priority**: Must Have  
**Description**: Work on different screen sizes

**Acceptance Criteria**:
- Support desktop (1920x1080+)
- Usable on laptop (1366x768+)
- Adapt layout to screen size
- Maintain functionality on all sizes

#### FR-30: Keyboard Shortcuts
**Priority**: Should Have  
**Description**: Common operations accessible via keyboard

**Acceptance Criteria**:
- Save (Ctrl/Cmd+S)
- Validate (Ctrl/Cmd+V)
- Find (Ctrl/Cmd+F)
- Undo/Redo (Ctrl/Cmd+Z/Y)
- Display shortcut help

#### FR-31: Tooltips and Help
**Priority**: Must Have  
**Description**: Contextual help throughout interface

**Acceptance Criteria**:
- Tooltips on hover (500ms delay)
- Help icon with descriptions
- Link to documentation
- Inline hints for complex features

#### FR-32: Loading States
**Priority**: Must Have  
**Description**: Visual feedback during operations

**Acceptance Criteria**:
- Skeleton loaders for data fetching
- Progress bars for long operations
- Disable controls during processing
- Timeout handling

#### FR-33: Success/Error Feedback
**Priority**: Must Have  
**Description**: Clear confirmation of operations

**Acceptance Criteria**:
- Success snackbar with animation
- Error messages with details
- Auto-dismiss after timeout
- Manual dismiss option

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### NFR-1: Response Time
- Page load: < 2 seconds
- Validation: < 500ms for typical config
- Auto-save: < 200ms
- Data preview: < 1 second

#### NFR-2: Caching
- Cache validation results (5-minute TTL)
- Cache schema introspection (10-minute TTL)
- Invalidate on configuration change

#### NFR-3: Optimization
- Debounce validation (500ms)
- Lazy-load entity details
- Virtual scrolling for large lists
- Code splitting for faster initial load

### 5.2 Reliability

#### NFR-4: Data Integrity
- Atomic save operations
- Automatic backups before changes
- Rollback capability
- Data validation before write

#### NFR-5: Error Handling
- Graceful degradation on failures
- Clear error messages
- Log errors for debugging
- Retry transient failures

#### NFR-6: Testing
- 90%+ test coverage
- Unit tests for business logic
- Integration tests for API
- E2E tests for critical paths

### 5.3 Usability

#### NFR-7: Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Focus indicators

#### NFR-8: Browser Support
- Chrome 120+
- Firefox 115+
- Safari 16+
- Edge 120+

#### NFR-9: User Guidance
- Inline help and tooltips
- Comprehensive documentation
- Example configurations
- Video tutorials (future)

### 5.4 Security

#### NFR-10: Input Validation
- Sanitize all user inputs
- Validate YAML structure
- Prevent code injection
- Limit file sizes

#### NFR-11: Authentication (Future)
- User login/logout
- Session management
- Role-based access control
- Audit logging

#### NFR-12: Data Security
- Secure credential storage
- HTTPS for API calls
- No sensitive data in logs
- Backup encryption (future)

### 5.5 Maintainability

#### NFR-13: Code Quality
- Type safety (TypeScript, Pydantic)
- Consistent code style
- Comprehensive comments
- Design patterns

#### NFR-14: Documentation
- API documentation (OpenAPI)
- User guides
- Developer guides
- Architecture diagrams

#### NFR-15: Extensibility
- Plugin architecture for validators
- Configurable data loaders
- Theme support
- Extensible UI components

---

## 6. Success Criteria

### 6.1 Phase 1 Success Criteria

- ✅ Users can create and edit entities without touching YAML
- ✅ Dependency visualization prevents circular dependencies
- ✅ Validation catches configuration errors before processing
- ✅ Form-based editing reduces syntax errors by 90%+
- ✅ 90%+ test coverage

### 6.2 Phase 2 Success Criteria

- ✅ Schema introspection saves 50%+ time on column listing
- ✅ Data preview catches data issues before full processing
- ✅ Auto-fix resolves 70%+ of common errors automatically
- ✅ Query testing validates SQL before adding to config
- ✅ Foreign key validation catches relationship errors

### 6.3 Overall Success Criteria

- ✅ Non-technical users can create configurations independently
- ✅ Configuration errors reduced by 80%+
- ✅ Time to create new configuration reduced by 60%+
- ✅ User satisfaction score > 4/5
- ✅ Zero data loss incidents

---

## 7. Constraints and Assumptions

### 7.1 Constraints

- Must work with existing Shape Shifter Python codebase
- Cannot modify core transformation engine
- Must maintain YAML configuration format
- Limited to single-user initially (no concurrent editing)

### 7.2 Assumptions

- Users have basic understanding of data transformation concepts
- Data sources are accessible from server
- Configurations fit in browser memory (< 10MB)
- Network connectivity for API calls

### 7.3 Out of Scope

- Multi-user real-time collaboration (Phase 3)
- Visual data transformation pipeline builder (Phase 3)
- Advanced data quality checks (Phase 3)
- Mobile app (Phase 4)
- AI-powered configuration generation (Phase 4)

---

## 8. Glossary

- **Entity**: A table or dataset in the transformation pipeline
- **Surrogate ID**: Auto-generated integer identifier for entity records
- **Natural Key**: Business key columns that uniquely identify records
- **Foreign Key**: Relationship between entities referencing surrogate IDs
- **Dependency**: Entity that must be processed before another
- **Unnest**: Transform wide data to long format (melt operation)
- **Topological Sort**: Ordering entities by dependencies for processing
- **Schema Introspection**: Automatic discovery of database structure
- **Validation**: Checking configuration correctness (structural or data)
- **Auto-Fix**: Automated correction of configuration errors

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**Status**: Complete (Phases 1 & 2 Implemented)
