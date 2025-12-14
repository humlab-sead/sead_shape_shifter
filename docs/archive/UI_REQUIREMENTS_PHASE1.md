# Configuration Editor UI - Phase 1 Requirements

## 1. Executive Summary

This document defines requirements for Phase 1 of a configuration editor UI that enables domain specialists to manage entity configurations for the Shape Shifter data transformation framework without directly editing YAML files.

**Target Users**: Data managers, archaeologists, and domain specialists with limited technical expertise  
**Goal**: Enable non-technical users to create and maintain data transformation configurations  
**Scope**: Phase 1 focuses on entity CRUD operations and dependency management

---

## 2. Background & Context

### 2.1 Current State
- Configuration files (e.g., `arbodat-database.yml`) are manually edited YAML documents
- Entities define data extraction, transformation, and relationship rules
- The system uses topological sorting based on entity dependencies
- Configuration validation is performed by specification classes in `src/specifications.py`

### 2.2 Configuration Structure Overview
```yaml
entities:
  entity_name:
    source: null | entity_name
    type: data | sql | fixed
    surrogate_id: column_name
    keys: [natural_key_columns]
    columns: [column_list]
    depends_on: [entity_dependencies]
    foreign_keys: [relationship_configs]
    # ... additional properties
```

### 2.3 Key Constraints
- **Dependency Order**: Entities must be processed in topological order
- **Circular Dependencies**: Not allowed - must be detected and prevented
- **Entity References**: All referenced entities (in dependencies, foreign keys, source) must exist
- **Naming Conventions**: Entity names use snake_case, surrogate IDs must end with `_id`

---

## 3. User Personas

### 3.1 Primary Persona: Domain Data Manager
- **Name**: Dr. Elena Researcher
- **Background**: Archaeobotanist with domain expertise but limited programming knowledge
- **Goals**: 
  - Configure data imports from archaeological databases
  - Define entity relationships matching domain understanding
  - Validate configurations before processing
- **Pain Points**:
  - YAML syntax errors break configurations
  - Difficult to visualize entity dependencies
  - Unclear what order to define entities

### 3.2 Secondary Persona: Technical Data Engineer
- **Name**: System Administrator
- **Background**: Developer maintaining the Shape Shifter system
- **Goals**:
  - Quickly scaffold new configurations
  - Review and debug configurations created by domain specialists
  - Ensure configuration quality and consistency
- **Pain Points**:
  - Manual review of large YAML files is time-consuming
  - Inconsistent naming conventions across projects

---

## 4. Functional Requirements

### 4.1 Entity Management (CRUD)

#### FR-1.1: List Entities
- **Priority**: MUST HAVE
- **Description**: Display all entities in the current configuration with key metadata
- **Acceptance Criteria**:
  - Show entity name, type, source, and dependency count
  - Support filtering by entity type (data, sql, fixed)
  - Support sorting by name or dependency order
  - Display dependency order sequence number (topological sort result)
  - Indicate entities with validation errors with visual cues

#### FR-1.2: View Entity Details
- **Priority**: MUST HAVE
- **Description**: Display complete configuration for a selected entity
- **Acceptance Criteria**:
  - Show all configured properties in organized sections
  - Display entity type and source configuration
  - List keys, columns, and extra_columns
  - Show dependencies (entities this depends on)
  - Show dependents (entities that depend on this)
  - Display foreign key relationships
  - Show validation status and errors

#### FR-1.3: Create New Entity
- **Priority**: MUST HAVE
- **Description**: Create a new entity with guided form input
- **Acceptance Criteria**:
  - Unique entity name (snake_case validation)
  - Select entity type: data, sql, or fixed
  - Choose source entity from dropdown (or null for root)
  - Define surrogate_id with automatic `_id` suffix suggestion
  - Define natural keys (multiple input)
  - Specify dependencies from available entities
  - Form validation before creation
  - Automatic topological sort validation

#### FR-1.4: Edit Existing Entity
- **Priority**: MUST HAVE
- **Description**: Modify entity configuration properties
- **Acceptance Criteria**:
  - Edit all basic properties (type, source, keys, columns)
  - Modify dependency list
  - Update foreign key relationships
  - Validate changes before saving
  - Prevent changes that would create circular dependencies
  - Show impact analysis (which entities will be affected)

#### FR-1.5: Delete Entity
- **Priority**: MUST HAVE
- **Description**: Remove an entity from configuration
- **Acceptance Criteria**:
  - Show warning if other entities depend on this entity
  - Require confirmation with list of affected entities
  - Option to cascade delete dependent entities
  - Validate configuration after deletion
  - Support undo operation

#### FR-1.6: Duplicate Entity
- **Priority**: SHOULD HAVE
- **Description**: Clone an existing entity as starting point for new entity
- **Acceptance Criteria**:
  - Copy all properties except entity name
  - Auto-generate unique name (e.g., `entity_name_copy`)
  - Allow immediate editing before saving
  - Validate uniqueness of new entity name

### 4.2 Dependency Management

#### FR-2.1: Visualize Dependency Graph
- **Priority**: MUST HAVE
- **Description**: Interactive graph showing entity dependencies
- **Acceptance Criteria**:
  - Nodes represent entities (colored by type)
  - Edges represent dependencies
  - Support zoom and pan
  - Click node to view/edit entity
  - Highlight path to/from selected entity
  - Detect and highlight circular dependencies in red
  - Show topological sort order as node labels

#### FR-2.2: Edit Dependencies
- **Priority**: MUST HAVE
- **Description**: Add or remove dependencies for an entity
- **Acceptance Criteria**:
  - Multi-select dropdown of available entities
  - Prevent self-dependency
  - Real-time circular dependency detection
  - Visual feedback on dependency changes
  - Show entities that will be affected by change

#### FR-2.3: Automatic Dependency Suggestion
- **Priority**: SHOULD HAVE
- **Description**: Suggest dependencies based on foreign keys and source references
- **Acceptance Criteria**:
  - If entity has foreign key to entity X, suggest X as dependency
  - If entity sources from entity Y, suggest Y and its dependencies
  - Allow user to accept or reject suggestions
  - Explain why each dependency is suggested

#### FR-2.4: Dependency Order Validation
- **Priority**: MUST HAVE
- **Description**: Validate topological order is possible
- **Acceptance Criteria**:
  - Run validation on every dependency change
  - Show clear error message for circular dependencies
  - Highlight entities involved in cycle
  - Suggest how to break the cycle

### 4.3 Configuration File Operations

#### FR-3.1: Load Configuration
- **Priority**: MUST HAVE
- **Description**: Import existing YAML configuration file
- **Acceptance Criteria**:
  - Support file upload or file path input
  - Parse YAML and validate structure
  - Show parsing errors with line numbers
  - Display summary of loaded entities
  - Preserve all entity properties (including unknown/custom fields)
  - Support special syntax: `@value:`, `@include:`, `@load:`

#### FR-3.2: Save Configuration
- **Priority**: MUST HAVE
- **Description**: Export configuration to YAML file
- **Acceptance Criteria**:
  - Write valid YAML with proper indentation
  - Preserve entity order (topological or user-defined)
  - Maintain comments if possible
  - Preserve special syntax (`@value:`, etc.)
  - Validate before saving
  - Show diff of changes before writing

#### FR-3.3: Configuration Validation
- **Priority**: MUST HAVE
- **Description**: Run validation specs before saving
- **Acceptance Criteria**:
  - Integrate with existing `specifications.py` validators
  - Display all errors and warnings grouped by entity
  - Link errors to entities for easy navigation
  - Prevent save if critical errors exist
  - Allow save with warnings (with confirmation)

#### FR-3.4: Configuration Backup
- **Priority**: SHOULD HAVE
- **Description**: Automatic backup before overwriting file
- **Acceptance Criteria**:
  - Create timestamped backup before each save
  - Store backups in configurable location
  - Allow restoration from backup
  - Show list of available backups

### 4.4 Entity Property Editors

#### FR-4.1: Basic Properties Editor
- **Priority**: MUST HAVE
- **Description**: Form for editing entity identity and source properties
- **Fields**:
  - Entity name (read-only after creation)
  - Type (data | sql | fixed)
  - Source entity (dropdown or null)
  - Surrogate ID name
  - Surrogate name (optional)
  - Keys (multi-value input)
  - Columns (multi-value input with `@value:` support)

#### FR-4.2: Type-Specific Property Editors
- **Priority**: MUST HAVE
- **Description**: Context-sensitive fields based on entity type
- **For SQL Type**:
  - Data source dropdown (from `options.data_sources`)
  - SQL query editor with syntax highlighting
  - Query validation button
- **For Fixed Type**:
  - Values grid editor (2D table)
  - Add/remove rows and columns
  - Import from CSV option
- **For Data Type**:
  - Filters editor (add/remove/configure filters)
  - Unnest configuration (if applicable)

#### FR-4.3: Foreign Key Editor
- **Priority**: MUST HAVE
- **Description**: Manage foreign key relationships
- **Acceptance Criteria**:
  - Add multiple foreign keys
  - Select remote entity from dropdown
  - Specify local and remote keys (with `@value:` support)
  - Choose join type (inner, left, right, outer, cross)
  - Configure constraints (cardinality, uniqueness, match rules)
  - Preview join result (if data available)

#### FR-4.4: Extra Columns Editor
- **Priority**: SHOULD HAVE
- **Description**: Define additional columns
- **Acceptance Criteria**:
  - Add column name and source/value pairs
  - Support column reference or constant value
  - Drag to reorder columns
  - Delete columns

---

## 5. Non-Functional Requirements

### 5.1 Usability

#### NFR-1.1: Accessibility
- **Priority**: MUST HAVE
- Meet WCAG 2.1 Level AA standards
- Keyboard navigation support for all features
- Screen reader compatible
- High contrast mode support

#### NFR-1.2: User Guidance
- **Priority**: SHOULD HAVE
- Inline help tooltips for all fields
- Link to configuration reference documentation
- Contextual examples for common patterns
- Validation error messages with suggested fixes

#### NFR-1.3: Learning Curve
- **Priority**: SHOULD HAVE
- New users should create basic entity in < 5 minutes
- Provide interactive tutorial/walkthrough
- Example configurations to learn from

### 5.2 Performance

#### NFR-2.1: Responsiveness
- **Priority**: MUST HAVE
- UI operations complete in < 200ms for configurations with < 100 entities
- Dependency graph renders in < 1 second
- File load/save operations in < 2 seconds for typical files (< 5000 lines)

#### NFR-2.2: Large Configuration Support
- **Priority**: SHOULD HAVE
- Support configurations with up to 200 entities
- Virtual scrolling for large entity lists
- Incremental validation for large files

### 5.3 Reliability

#### NFR-3.1: Data Integrity
- **Priority**: MUST HAVE
- Never corrupt existing configuration files
- Atomic file writes (write to temp, then rename)
- Validate after every modification
- Auto-save draft to browser storage

#### NFR-3.2: Error Recovery
- **Priority**: MUST HAVE
- Graceful handling of malformed YAML
- Recovery from validation errors
- Ability to export current state even if invalid

### 5.4 Compatibility

#### NFR-4.1: File Format Compatibility
- **Priority**: MUST HAVE
- Fully compatible with existing YAML configurations
- Preserve all properties, including unknown/custom fields
- Maintain special syntax (`@value:`, `@include:`, `@load:`)
- Round-trip fidelity (load → save → load produces identical config)

#### NFR-4.2: Browser Support
- **Priority**: SHOULD HAVE
- Modern browsers: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- Responsive design for tablets (1024px+)

---

## 6. User Interface Requirements

### 6.1 Layout Structure

#### UI-1.1: Three-Panel Layout
- **Left Panel**: Entity list with search/filter
- **Center Panel**: Dependency graph or entity editor
- **Right Panel**: Entity details and validation messages

#### UI-1.2: Navigation
- Primary navigation tabs:
  - **Entities**: List view with CRUD operations
  - **Graph**: Dependency visualization
  - **Validation**: Configuration validation report
  - **Settings**: Application settings

### 6.2 Entity List View

#### UI-2.1: Entity List
- Sortable table with columns:
  - Entity name
  - Type (icon + label)
  - Source
  - Dependencies count
  - Status (icon: valid/invalid/warning)
- Actions per row: View, Edit, Duplicate, Delete
- Bulk actions: Select multiple, Delete selected
- Search/filter bar at top

#### UI-2.2: Entity Card View (Alternative)
- Card-based layout showing entity summary
- Visual indicators for type and status
- Quick actions on hover
- Drag-and-drop to reorder

### 6.3 Entity Editor

#### UI-3.1: Tabbed Editor
- Tabs for entity sections:
  - **Basic**: Name, type, source, keys
  - **Columns**: Column selection and extra columns
  - **Dependencies**: Dependency management
  - **Foreign Keys**: Relationship configuration
  - **Advanced**: Type-specific properties (SQL query, fixed values, filters, unnest)

#### UI-3.2: Form Validation
- Inline validation errors (red border + message)
- Field-level warnings (yellow border + message)
- Success indicators (green checkmark)
- Required field indicators (asterisk)

### 6.4 Dependency Graph

#### UI-4.1: Graph Visualization
- Node style:
  - Color by type (data: blue, sql: green, fixed: orange)
  - Size by dependency count
  - Label shows entity name
  - Badge shows topological order number
- Edge style:
  - Solid line for dependencies
  - Dashed line for foreign keys (optional toggle)
  - Arrow direction shows dependency flow
- Interaction:
  - Click node → open entity editor
  - Hover node → highlight connected nodes
  - Right-click → context menu (edit, delete, etc.)
- Controls:
  - Zoom in/out buttons
  - Fit to view button
  - Layout algorithm selector (hierarchical, force-directed, circular)
  - Toggle foreign key edges
  - Filter by entity type

### 6.5 Validation Report

#### UI-5.1: Validation Results
- Grouped by severity: Errors, Warnings, Info
- Expandable sections per entity
- Each issue shows:
  - Severity icon
  - Error message
  - Affected entity/property (clickable link)
  - Suggested fix (if available)
- Summary counts at top
- "Fix All" button for auto-fixable issues

---

## 7. Use Cases

### UC-1: Create Simple Entity from CSV
**Actor**: Domain Data Manager  
**Precondition**: CSV file available  
**Flow**:
1. User clicks "New Entity" button
2. System shows entity creation form
3. User enters entity name: "survey"
4. User selects type: "csv"
5. User sets source: null (root entity)
6. User defines surrogate_id: "survey_id"
7. User specifies keys: ["survey_name"]
8. User leaves depends_on empty
9. User clicks "Create"
10. System validates entity
11. System adds entity to configuration
12. System shows success message

**Postcondition**: New entity created and visible in entity list  
**Alternative Flow**: Validation fails at step 10 → show errors, allow correction

---

### UC-2: Create SQL Entity with Dependencies
**Actor**: Domain Data Manager  
**Precondition**: Database connection configured, sample entity exists  
**Flow**:
1. User clicks "New Entity"
2. User enters name: "dating"
3. User selects type: "sql"
4. User selects data_source: "arbodat_data"
5. User enters SQL query in editor
6. User clicks "Validate Query" → system confirms valid SQL
7. User defines keys: ["Projekt", "Befu", "ProbNr"]
8. User adds dependency: "sample"
9. System automatically suggests "sample" (since keys match)
10. User adds foreign key:
    - entity: "sample"
    - local_keys: same as entity keys
    - how: "inner"
11. User clicks "Create"
12. System validates no circular dependency
13. System adds entity

**Postcondition**: dating entity created with foreign key to sample

---

### UC-3: Visualize and Fix Circular Dependency
**Actor**: Domain Data Manager  
**Precondition**: Configuration with circular dependency  
**Flow**:
1. User opens Graph view
2. System renders dependency graph
3. System detects circular dependency: A → B → C → A
4. System highlights A, B, C nodes in red
5. System highlights edges in cycle with red dashed line
6. User hovers over error indicator
7. System shows tooltip: "Circular dependency detected: A → B → C → A"
8. User right-clicks on entity B
9. User selects "Edit Dependencies"
10. User removes dependency on C
11. System re-validates, cycle broken
12. System updates graph, nodes return to normal color

**Postcondition**: Circular dependency resolved

---

### UC-4: Delete Entity with Cascade Warning
**Actor**: Technical Data Engineer  
**Precondition**: Entity "feature" exists, "sample" depends on "feature"  
**Flow**:
1. User selects "feature" entity in list
2. User clicks "Delete" button
3. System shows modal:
   - "Warning: 3 entities depend on 'feature'"
   - Lists: "sample", "sample_group", "feature_property"
   - "Do you want to continue? These entities will have invalid dependencies."
4. User sees options:
   - "Cancel"
   - "Delete anyway" (mark dependents invalid)
   - "Cascade delete" (delete all dependents)
5. User clicks "Cancel"
6. System closes modal, no changes made

**Alternative Flow**: User clicks "Delete anyway" → feature deleted, dependents marked invalid

---

### UC-5: Load Existing Configuration and Validate
**Actor**: Domain Data Manager  
**Precondition**: YAML file exists on disk  
**Flow**:
1. User clicks "Load Configuration"
2. System shows file picker
3. User selects "arbodat-database.yml"
4. System parses YAML
5. System loads 67 entities
6. System runs validation specs
7. System finds 2 errors, 5 warnings
8. System shows summary: "Loaded 67 entities. 2 errors, 5 warnings."
9. User clicks "View Validation Report"
10. System shows Validation tab with details
11. User clicks on first error
12. System navigates to entity with error and highlights field

**Postcondition**: Configuration loaded, user aware of validation issues

---

### UC-6: Export Configuration with Changes
**Actor**: Domain Data Manager  
**Precondition**: Configuration loaded, changes made  
**Flow**:
1. User makes changes to multiple entities
2. User clicks "Save Configuration"
3. System validates configuration
4. System shows diff view:
   - Entities added (green)
   - Entities modified (yellow)
   - Entities deleted (red)
5. User reviews changes
6. User confirms save
7. System creates backup: "arbodat-database.yml.backup.20251212_143022"
8. System writes updated YAML
9. System shows success: "Configuration saved"

**Postcondition**: YAML file updated with changes, backup created

---

## 8. Validation Requirements

### 8.1 Client-Side Validation
- Immediate feedback on form fields
- Entity name format (snake_case)
- Surrogate ID suffix (_id)
- Unique entity names
- Non-empty required fields
- Circular dependency detection

### 8.2 Server-Side Validation
- Integrate existing `specifications.py` validators:
  - RequiredFieldsSpecification
  - EntityExistsSpecification
  - CircularDependencySpecification
  - DataSourceExistsSpecification
  - SqlDataSpecification
  - FixedDataSpecification
  - ForeignKeySpecification
  - UnnestSpecification
  - SurrogateIdSpecification
- Return structured validation results (errors, warnings, entity references)

---

## 9. Future Phase Considerations

### 9.1 Phase 2 Preview
Phase 2 will build on this foundation by adding:
- **Data Source Analysis**: Connect to databases/files and list available tables/columns
- **Smart Pick Lists**: Populate dropdowns with actual database tables, columns, relationships
- **Sample Data Preview**: Show sample rows from sources during configuration
- **Column Mapping Assistant**: Suggest column mappings based on names/types
- **Auto-detection**: Detect keys, types, relationships from source schema

**Architecture Impact**:
- Need data source connectors (database drivers, file parsers)
- Schema introspection API endpoints
- Caching layer for schema metadata

### 9.2 Phase 3 Preview
Phase 3 will add schema-aware guidance:
- **Target Schema Knowledge**: Load SEAD or other target schemas
- **Guided Entity Creation**: Suggest entities needed to populate target schema
- **Relationship Recommendations**: Suggest foreign keys based on target schema
- **Completeness Checker**: Identify missing entities or mappings
- **Template Library**: Pre-built configurations for common sources

**Architecture Impact**:
- Target schema metadata store
- Rule engine for recommendations
- Template management system

---

## 10. Success Metrics

### 10.1 Phase 1 Success Criteria
- Domain specialist can create basic configuration in < 30 minutes (vs 2+ hours manually)
- Reduction in configuration syntax errors by 90%
- Zero configuration file corruptions
- 100% validation coverage (all specs integrated)

### 10.2 User Acceptance Tests
- 5 domain specialists successfully create configurations without developer assistance
- Technical review confirms configurations meet quality standards
- Users rate ease of use ≥ 4/5
- Users report increased confidence in configuration correctness

---

## 11. Out of Scope (Phase 1)

The following are explicitly **NOT** included in Phase 1:
- Data source connectivity and schema introspection
- Sample data preview from sources
- Column mapping between source and target
- SQL query builder/assistant
- Automated entity generation from source schema
- Target schema guidance and recommendations
- Multi-user collaboration features
- Version control integration
- Configuration templates library
- Unnest configuration wizard
- Filter configuration UI (beyond basic add/remove)
- Advanced constraint editors
- Export to formats other than YAML
- Configuration comparison/merge tools
- Undo/redo beyond single operation

---

## 12. Dependencies & Assumptions

### 12.1 Technical Dependencies
- Python backend with existing Shape Shifter codebase
- YAML parsing library (PyYAML or ruamel.yaml)
- Web framework (to be determined in architecture document)
- Graph visualization library (to be determined)

### 12.2 Assumptions
- Users have basic understanding of data concepts (entities, relationships, keys)
- Configuration files are stored on server-accessible filesystem
- Single-user editing (no concurrent modifications in Phase 1)
- Network connectivity for web-based UI
- YAML format remains stable

---

## 13. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Loss of YAML formatting/comments | Medium | High | Use ruamel.yaml to preserve formatting |
| Complex configurations exceed UI capabilities | High | Medium | Support manual YAML edit mode as fallback |
| Validation performance on large configs | Medium | Medium | Incremental/background validation |
| Users create invalid configs that break processing | High | Medium | Block save on critical errors, require confirmation on warnings |
| Circular dependencies difficult to visualize | Medium | Low | Clear graph highlights, interactive cycle breaking |

---

## 14. Appendices

### Appendix A: Entity Property Quick Reference
See [CONFIGURATION_REFERENCE.md](./CONFIGURATION_REFERENCE.md) for complete details.

### Appendix B: Validation Specifications
See `src/specifications.py` for implementation details.

### Appendix C: Example Configurations
- Simple lookup: `archaeological_period`
- Complex entity with FK: `sample`
- Fixed values: `contact_type`
- Unnested data: `sample_coordinate`

---

**Document Version**: 1.0  
**Date**: December 12, 2025  
**Author**: System Architect  
**Status**: Draft for Review
