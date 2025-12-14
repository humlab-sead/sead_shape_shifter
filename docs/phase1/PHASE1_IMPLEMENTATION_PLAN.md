# Phase 1 Implementation Plan - Configuration Editor UI

**Project**: Shape Shifter Configuration Editor  
**Phase**: Phase 1 - Entity CRUD & Dependency Management  
**Technology Stack**: Vue 3 + TypeScript + Vuetify + FastAPI  
**Target Duration**: 9 weeks (1 developer, full-time)  
**Document Version**: 1.0  
**Date**: December 12, 2025

---

## 1. Executive Summary

This document provides a detailed, week-by-week implementation plan for Phase 1 of the Configuration Editor UI. The plan is organized into sprints with specific deliverables, acceptance criteria, and time estimates.

### Phase 1 Goals
- ✅ CRUD operations for entities
- ✅ Visual dependency graph with cycle detection
- ✅ Load/save YAML configurations with backups
- ✅ Full validation integration
- ✅ Professional, usable interface

### Success Criteria
- Domain specialist can create configuration in < 30 minutes
- Zero configuration file corruptions
- 90% reduction in syntax errors
- All existing validation specs integrated
- User acceptance rating ≥ 4/5

---

## 2. Project Phases Overview

```
Week 1-2: Foundation & Backend API
Week 3-4: Entity Management UI
Week 5-6: Dependency Management & Graph
Week 7-8: Configuration Operations & Validation
Week 9:   Testing, Polish & Documentation
```

---

## 3. Detailed Week-by-Week Plan

### **Week 1: Project Setup & Backend Foundation**

#### **Sprint 1.1: Project Scaffolding (2 days)**

**Backend Setup**
- [ ] Create `backend/` directory structure
  - `app/api/v1/endpoints/`
  - `app/core/`
  - `app/models/`
  - `app/services/`
  - `app/integrations/`
- [ ] Set up FastAPI application (`app/main.py`)
- [ ] Configure CORS middleware
- [ ] Create requirements.txt / pyproject.toml
- [ ] Set up uvicorn for development
- [ ] Create basic health check endpoint (`GET /api/v1/health`)

**Deliverable**: Backend server running on localhost:8000

**Acceptance Criteria**:
- `uvicorn app.main:app --reload` starts successfully
- Swagger docs accessible at http://localhost:8000/docs
- Health check returns 200 OK

**Time Estimate**: 2 days

---

#### **Sprint 1.2: Frontend Setup (2 days)**

**Frontend Setup**
- [ ] Create Vue 3 + TypeScript project with Vite
  ```bash
  npm create vite@latest frontend -- --template vue-ts
  ```
- [ ] Install dependencies:
  - Vuetify 3
  - Pinia
  - Vue Router 4
  - VeeValidate + Zod
  - Axios
- [ ] Configure Vuetify plugin
- [ ] Set up Vite proxy to backend (`/api` → `http://localhost:8000`)
- [ ] Create basic directory structure
- [ ] Set up ESLint + Prettier
- [ ] Configure TypeScript (`tsconfig.json`)

**Deliverable**: Frontend dev server running on localhost:5173

**Acceptance Criteria**:
- `pnpm dev` starts successfully
- Vuetify components render
- Proxy to backend works

**Time Estimate**: 2 days

---

#### **Sprint 1.3: Pydantic Models & Type Definitions (1 day)**

**Backend Models**
- [ ] Create `app/models/entity.py` with Pydantic models:
  - `Entity`
  - `ForeignKeyConfig`
  - `ForeignKeyConstraints`
  - `UnnestConfig`
  - `FilterConfig`
- [ ] Create `app/models/config.py`:
  - `Configuration`
  - `ConfigMetadata`
- [ ] Create `app/models/validation.py`:
  - `ValidationResult`
  - `ValidationError`
  - `ValidationWarning`
- [ ] Add validators for entity names, surrogate IDs, etc.

**Frontend Types**
- [ ] Create `src/types/entity.ts` (matching Pydantic models)
- [ ] Create `src/types/config.ts`
- [ ] Create `src/types/validation.ts`

**Deliverable**: Type-safe data models on both ends

**Acceptance Criteria**:
- Pydantic models validate correctly
- TypeScript types compile without errors
- Types match between frontend and backend

**Time Estimate**: 1 day

---

### **Week 2: Core Backend Services**

#### **Sprint 2.1: YAML Service (2 days)**

**Implementation**
- [ ] Create `app/services/yaml_service.py`
- [ ] Install and configure `ruamel.yaml`
- [ ] Implement `load(file_path)` method
  - Parse YAML preserving format
  - Handle special syntax (`@value:`, `@include:`, `@load:`)
  - Error handling for malformed YAML
- [ ] Implement `save(data, file_path)` method
  - Atomic write (temp file → rename)
  - Preserve comments and formatting
  - Preserve entity order
- [ ] Implement `validate_yaml(content)` method
- [ ] Implement `create_backup(file_path)` method
  - Timestamped backups (`.backup.YYYYMMDD_HHMMSS`)
  - Store in configurable backup directory

**Tests**
- [ ] Unit tests for load/save round-trip
- [ ] Test special syntax parsing
- [ ] Test backup creation
- [ ] Test atomic write safety

**Deliverable**: YamlService with round-trip fidelity

**Acceptance Criteria**:
- Load → Save → Load produces identical structure
- Comments preserved
- Special syntax (`@value:`) preserved
- Backups created successfully
- 80%+ test coverage

**Time Estimate**: 2 days

---

#### **Sprint 2.2: Configuration Service (2 days)**

**Implementation**
- [ ] Create `app/services/config_service.py`
- [ ] Implement CRUD operations:
  - `load_configuration(file_path)` → Configuration
  - `save_configuration(config, file_path)`
  - `add_entity(config, entity)` → Configuration
  - `update_entity(config, entity_id, updates)` → Configuration
  - `delete_entity(config, entity_id)` → Configuration
  - `get_entity(config, entity_id)` → Entity
- [ ] Add validation:
  - Unique entity names
  - Entity existence checks
- [ ] Add helper methods:
  - `list_configurations(directory)` → List[str]
  - `get_metadata(config)` → ConfigMetadata

**Tests**
- [ ] Unit tests for each CRUD operation
- [ ] Test entity name uniqueness
- [ ] Test deletion with dependents (should raise error)
- [ ] Test with existing `arbodat-database.yml`

**Deliverable**: ConfigurationService ready for API integration

**Acceptance Criteria**:
- All CRUD operations work correctly
- Validation catches duplicate names
- Works with real arbodat-database.yml file
- 80%+ test coverage

**Time Estimate**: 2 days

---

#### **Sprint 2.3: Validation Service Integration (1 day)**

**Implementation**
- [ ] Create `app/services/validation_service.py`
- [ ] Create `app/integrations/specifications.py` wrapper
- [ ] Implement `validate(config)` method:
  - Convert Configuration to TablesConfig
  - Call existing `CompositeConfigSpecification`
  - Convert errors/warnings to API format
- [ ] Implement `validate_entity(entity)` for quick checks
- [ ] Map validation errors to entities and fields

**Tests**
- [ ] Test with valid configuration
- [ ] Test with invalid configuration (known errors)
- [ ] Test error format conversion
- [ ] Verify all specs run

**Deliverable**: Validation service using existing specs

**Acceptance Criteria**:
- Existing validation specs work unchanged
- Errors include entity and field references
- Validation runs in < 2 seconds for typical configs

**Time Estimate**: 1 day

---

### **Week 3: Backend API Endpoints**

#### **Sprint 3.1: Configuration Endpoints (2 days)**

**API Endpoints**
- [ ] `GET /api/v1/configurations` - List available configs
- [ ] `GET /api/v1/configurations/{name}` - Get full configuration
- [ ] `POST /api/v1/configurations` - Create new configuration
- [ ] `PUT /api/v1/configurations/{name}` - Update configuration
- [ ] `DELETE /api/v1/configurations/{name}` - Delete configuration
- [ ] `POST /api/v1/configurations/{name}/load` - Load from file
- [ ] `POST /api/v1/configurations/{name}/save` - Save to file
- [ ] `GET /api/v1/configurations/{name}/backups` - List backups
- [ ] `POST /api/v1/configurations/{name}/backups/{timestamp}/restore` - Restore backup

**Implementation**
- [ ] Create `app/api/v1/endpoints/configuration.py`
- [ ] Add request/response models
- [ ] Add error handling
- [ ] Add OpenAPI documentation
- [ ] Wire up to services

**Tests**
- [ ] Integration tests for each endpoint
- [ ] Test error cases (file not found, etc.)
- [ ] Test with real YAML files

**Deliverable**: Working configuration API

**Acceptance Criteria**:
- All endpoints work via Swagger UI
- Error responses are clear and structured
- Load/save preserves YAML format
- OpenAPI docs are complete

**Time Estimate**: 2 days

---

#### **Sprint 3.2: Entity Endpoints (2 days)**

**API Endpoints**
- [ ] `GET /api/v1/configurations/{name}/entities` - List entities
- [ ] `GET /api/v1/configurations/{name}/entities/{entity_id}` - Get entity
- [ ] `POST /api/v1/configurations/{name}/entities` - Create entity
- [ ] `PUT /api/v1/configurations/{name}/entities/{entity_id}` - Update entity
- [ ] `DELETE /api/v1/configurations/{name}/entities/{entity_id}` - Delete entity

**Implementation**
- [ ] Create `app/api/v1/endpoints/entities.py`
- [ ] Add request/response models
- [ ] Add validation before entity operations
- [ ] Add error handling
- [ ] Add OpenAPI documentation

**Tests**
- [ ] Integration tests for CRUD operations
- [ ] Test validation errors
- [ ] Test duplicate name prevention
- [ ] Test delete with dependents

**Deliverable**: Working entity CRUD API

**Acceptance Criteria**:
- All CRUD operations work via Swagger UI
- Validation errors are clear
- Can't create duplicate entity names
- Can't delete entity with dependents (without flag)

**Time Estimate**: 2 days

---

#### **Sprint 3.3: Validation & Dependency Endpoints (1 day)**

**API Endpoints**
- [ ] `POST /api/v1/configurations/{name}/validate` - Validate configuration
- [ ] `GET /api/v1/configurations/{name}/dependencies` - Get dependency graph
- [ ] `POST /api/v1/configurations/{name}/dependencies/check` - Check for circular deps

**Implementation**
- [ ] Create `app/api/v1/endpoints/validation.py`
- [ ] Create `app/api/v1/endpoints/dependencies.py`
- [ ] Create `app/services/dependency_service.py`:
  - `get_dependency_graph()` using NetworkX
  - `get_topological_order()`
  - `find_circular_dependencies()`
  - `get_dependents(entity_id)`
- [ ] Add response models for graph data

**Tests**
- [ ] Test validation with errors/warnings
- [ ] Test dependency graph generation
- [ ] Test circular dependency detection
- [ ] Test topological sort

**Deliverable**: Validation and dependency analysis API

**Acceptance Criteria**:
- Validation returns structured errors
- Dependency graph includes nodes and edges
- Circular dependencies detected correctly
- Topological order is valid

**Time Estimate**: 1 day

---

### **Week 4: Frontend State & API Layer**

#### **Sprint 4.1: API Client (2 days)**

**Implementation**
- [ ] Create `src/api/client.ts` - Axios wrapper with:
  - Base URL configuration
  - Error handling
  - Request/response interceptors
  - TypeScript typing
- [ ] Create `src/api/config-api.ts`:
  - `listConfigurations()`
  - `loadConfiguration(name)`
  - `saveConfiguration(name, config)`
  - `createConfiguration(name)`
  - `deleteConfiguration(name)`
- [ ] Create `src/api/entity-api.ts`:
  - `listEntities(configName)`
  - `getEntity(configName, entityId)`
  - `createEntity(configName, entity)`
  - `updateEntity(configName, entityId, updates)`
  - `deleteEntity(configName, entityId)`
- [ ] Create `src/api/validation-api.ts`:
  - `validate(configName)`
- [ ] Create `src/api/dependency-api.ts`:
  - `getDependencyGraph(configName)`

**Tests**
- [ ] Mock API responses for testing
- [ ] Test error handling
- [ ] Test request formatting

**Deliverable**: Complete TypeScript API client

**Acceptance Criteria**:
- All API methods work with backend
- Type-safe requests and responses
- Clear error messages
- Works in dev (proxied) and production

**Time Estimate**: 2 days

---

#### **Sprint 4.2: Pinia Stores (2 days)**

**Implementation**
- [ ] Create `src/stores/config.ts` - Configuration store:
  - State: entities, metadata, isDirty, isLoading, currentFile
  - Getters: entityList, getEntityById, getEntityDependencies, etc.
  - Actions: loadConfiguration, saveConfiguration, CRUD operations
- [ ] Create `src/stores/validation.ts` - Validation store:
  - State: results, isValidating, lastValidation
  - Getters: hasErrors, errorCount, getEntityErrors
  - Actions: validate, clearValidation
- [ ] Create `src/stores/ui.ts` - UI state store:
  - State: selectedEntity, showEditor, sidebarOpen, etc.
  - Actions: selectEntity, openEditor, closeEditor

**Tests**
- [ ] Test store actions
- [ ] Test computed getters
- [ ] Test state updates trigger reactivity

**Deliverable**: Reactive state management with Pinia

**Acceptance Criteria**:
- Stores integrate with API client
- State updates trigger component re-renders
- Computed values update correctly
- Store actions are async-safe

**Time Estimate**: 2 days

---

#### **Sprint 4.3: Composables (1 day)**

**Implementation**
- [ ] Create `src/composables/useConfiguration.ts`:
  - Wraps config store with business logic
  - Handles validation before save
  - Error handling
- [ ] Create `src/composables/useEntityEditor.ts`:
  - Entity editing logic
  - Available sources/dependencies
  - Circular dependency validation
- [ ] Create `src/composables/useValidation.ts`:
  - Validation helpers
  - Error filtering and grouping
- [ ] Create `src/composables/useDependencyGraph.ts`:
  - Graph layout computation
  - Node/edge formatting

**Tests**
- [ ] Test composable logic
- [ ] Test with mock stores

**Deliverable**: Reusable business logic composables

**Acceptance Criteria**:
- Composables are reusable across components
- Logic is testable in isolation
- Type-safe composition

**Time Estimate**: 1 day

---

### **Week 5: Entity List & Editor UI**

#### **Sprint 5.1: Layout & Navigation (2 days)**

**Implementation**
- [ ] Create `src/layouts/DefaultLayout.vue`:
  - Vuetify app bar with title and actions
  - Navigation drawer with menu
  - Main content area
  - Footer
- [ ] Create `src/router/index.ts`:
  - Routes: /entities, /graph, /validation, /settings
  - Navigation guards
- [ ] Create `src/views/EntitiesView.vue` (placeholder)
- [ ] Create `src/views/GraphView.vue` (placeholder)
- [ ] Create `src/views/ValidationView.vue` (placeholder)
- [ ] Create `src/views/SettingsView.vue` (placeholder)
- [ ] Add navigation menu with icons
- [ ] Add "Load Configuration" and "Save Configuration" buttons in app bar

**Deliverable**: Basic app shell with navigation

**Acceptance Criteria**:
- Navigation works between views
- Responsive layout
- Professional appearance
- Vuetify theme applied

**Time Estimate**: 2 days

---

#### **Sprint 5.2: Entity List Component (2 days)**

**Implementation**
- [ ] Create `src/components/entity/EntityList.vue`:
  - Vuetify data table with entities
  - Search/filter functionality
  - Sort by name, type, status
  - Action buttons (edit, duplicate, delete)
  - Status icons (valid/warning/error)
- [ ] Create `src/components/entity/EntityCard.vue` (alternative view):
  - Card-based layout
  - Shows entity summary
- [ ] Add entity type filter dropdown
- [ ] Add "New Entity" button
- [ ] Integrate with config store
- [ ] Show loading state
- [ ] Show empty state ("No entities yet")

**Deliverable**: Working entity list with real data

**Acceptance Criteria**:
- Displays entities from loaded config
- Search filters entities in real-time
- Status icons reflect validation state
- Actions open appropriate dialogs

**Time Estimate**: 2 days

---

#### **Sprint 5.3: Entity Detail View (1 day)**

**Implementation**
- [ ] Create `src/components/entity/EntityDetail.vue`:
  - Tabbed view of entity properties
  - Read-only display
  - Shows all fields organized logically
  - Links to dependencies/dependents
- [ ] Add "Edit" button to open editor
- [ ] Add "Delete" button with confirmation
- [ ] Add "Duplicate" button

**Deliverable**: Entity detail view

**Acceptance Criteria**:
- Shows complete entity configuration
- Organized and readable
- Actions work correctly

**Time Estimate**: 1 day

---

### **Week 6: Entity Editor Forms**

#### **Sprint 6.1: Basic Properties Form (2 days)**

**Implementation**
- [ ] Create `src/components/entity/EntityEditor.vue`:
  - Modal dialog or side panel
  - Tabbed interface
  - VeeValidate form setup
  - Save/Cancel buttons
- [ ] Create `src/components/entity/BasicPropertiesForm.vue`:
  - Entity name field (with validation: snake_case)
  - Entity type selector (data/sql/fixed)
  - Source entity dropdown (nullable)
  - Surrogate ID field (with validation: ends with _id)
  - Keys array input (chips/tags)
- [ ] Add Zod schema for validation
- [ ] Show validation errors inline
- [ ] Disable save if form invalid

**Deliverable**: Basic entity property editor

**Acceptance Criteria**:
- Form validates input in real-time
- Can create new entity with basic properties
- Can edit existing entity
- Validation prevents invalid data

**Time Estimate**: 2 days

---

#### **Sprint 6.2: Columns & Dependencies Forms (2 days)**

**Implementation**
- [ ] Create `src/components/entity/ColumnsForm.vue`:
  - Columns list (add/remove)
  - Extra columns key-value editor
  - Support `@value:` syntax helper
- [ ] Create `src/components/entity/DependenciesForm.vue`:
  - Multi-select dropdown for dependencies
  - Shows available entities
  - Validates against circular dependencies
  - Shows warning if cycle would be created
  - Shows current dependents (entities depending on this)
- [ ] Add real-time circular dependency checking

**Deliverable**: Column and dependency editors

**Acceptance Criteria**:
- Can add/remove columns
- Can add/remove dependencies
- Circular dependencies prevented
- `@value:` syntax supported

**Time Estimate**: 2 days

---

#### **Sprint 6.3: Type-Specific Forms (1 day)**

**Implementation**
- [ ] Create `src/components/entity/SqlPropertiesForm.vue`:
  - Data source dropdown
  - SQL query editor (Monaco Editor)
  - "Validate Query" button (future)
- [ ] Create `src/components/entity/FixedPropertiesForm.vue`:
  - Values grid editor (2D table)
  - Add/remove rows and columns
- [ ] Show appropriate form based on entity type
- [ ] Add validation for required fields per type

**Deliverable**: Type-specific property editors

**Acceptance Criteria**:
- SQL entities show query editor
- Fixed entities show values grid
- Type-specific validation works

**Time Estimate**: 1 day

---

### **Week 7: Dependency Graph & Foreign Keys**

#### **Sprint 7.1: Dependency Graph Visualization (3 days)**

**Implementation**
- [ ] Install Vue Flow and dagre
- [ ] Create `src/components/graph/DependencyGraph.vue`:
  - Vue Flow container
  - Compute graph layout with dagre
  - Node styling by entity type
  - Edge styling for dependencies
  - Zoom and pan controls
- [ ] Create `src/components/graph/EntityNode.vue`:
  - Custom node component
  - Shows entity name and type icon
  - Shows status indicator
  - Topological order badge
- [ ] Create `src/components/graph/GraphControls.vue`:
  - Fit view button
  - Zoom in/out
  - Layout algorithm selector
  - Toggle foreign key edges
- [ ] Add node click → open entity editor
- [ ] Add node hover → highlight connected nodes
- [ ] Highlight circular dependencies in red

**Deliverable**: Interactive dependency graph

**Acceptance Criteria**:
- Graph renders with correct layout
- Nodes colored by type
- Circular dependencies highlighted
- Interactive (click, hover, zoom)
- Performance good for 100+ entities

**Time Estimate**: 3 days

---

#### **Sprint 7.2: Foreign Key Editor (2 days)**

**Implementation**
- [ ] Create `src/components/entity/ForeignKeysForm.vue`:
  - List of foreign keys
  - Add/remove foreign keys
  - Per-FK editor:
    - Remote entity dropdown
    - Local keys selector
    - Remote keys selector
    - Join type dropdown (inner/left/right/outer/cross)
    - Extra columns editor
    - Constraints editor (expandable)
- [ ] Create `src/components/entity/ForeignKeyConstraintsForm.vue`:
  - Cardinality selector
  - Match checkboxes (allow unmatched left/right)
  - Uniqueness checkboxes
  - Allow null keys checkbox
- [ ] Add validation for FK configuration

**Deliverable**: Foreign key relationship editor

**Acceptance Criteria**:
- Can add/remove foreign keys
- All FK properties configurable
- Constraints editor works
- Validation prevents invalid FKs

**Time Estimate**: 2 days

---

### **Week 8: Configuration Operations & Validation UI**

#### **Sprint 8.1: Load/Save Configuration (2 days)**

**Implementation**
- [ ] Create `src/components/config/LoadConfigDialog.vue`:
  - File picker (or path input)
  - Show loading indicator
  - Show parse errors if any
  - Summary of loaded entities
- [ ] Create `src/components/config/SaveConfigDialog.vue`:
  - Show validation results before save
  - Show diff of changes (optional)
  - Confirm button
  - Show backup confirmation
- [ ] Add "Load Configuration" action to app bar
- [ ] Add "Save Configuration" action to app bar
- [ ] Add dirty state indicator (unsaved changes)
- [ ] Add confirmation before closing with unsaved changes
- [ ] Add auto-save to browser local storage

**Deliverable**: Configuration file operations

**Acceptance Criteria**:
- Can load existing YAML files
- Can save changes to file
- Backup created before save
- Dirty state tracked correctly
- Parse errors shown clearly

**Time Estimate**: 2 days

---

#### **Sprint 8.2: Validation Report UI (2 days)**

**Implementation**
- [ ] Create `src/views/ValidationView.vue`:
  - Validation summary (error/warning counts)
  - Grouped by severity
  - Expandable sections per entity
  - Filter by severity
  - "Validate Now" button
- [ ] Create `src/components/validation/ValidationReport.vue`:
  - List of validation issues
  - Each issue shows:
    - Severity icon and color
    - Entity name (clickable link)
    - Field name (clickable link)
    - Error message
    - Suggested fix (if available)
- [ ] Create `src/components/validation/ValidationSummary.vue`:
  - Card showing counts
  - Status indicator (all clear / warnings / errors)
- [ ] Add "Fix All" button for auto-fixable issues (future)
- [ ] Clicking issue navigates to entity editor and highlights field

**Deliverable**: Validation report UI

**Acceptance Criteria**:
- Shows all validation errors and warnings
- Grouped logically
- Clickable links to entities
- Updates when configuration changes
- Clear and actionable messages

**Time Estimate**: 2 days

---

#### **Sprint 8.3: Backup Management (1 day)**

**Implementation**
- [ ] Create `src/components/config/BackupManager.vue`:
  - List of available backups
  - Show timestamp and size
  - "Restore" button per backup
  - "Delete" button per backup
  - Confirmation dialogs
- [ ] Add "Manage Backups" to settings or menu
- [ ] Implement restore functionality
- [ ] Show diff before restore (optional)

**Deliverable**: Backup management UI

**Acceptance Criteria**:
- Lists all backups
- Can restore from backup
- Confirmation before restore
- Backup deleted on restore (optional)

**Time Estimate**: 1 day

---

### **Week 9: Testing, Polish & Documentation**

#### **Sprint 9.1: Integration Testing (2 days)**

**Testing Activities**
- [ ] End-to-end tests with Playwright:
  - Load configuration
  - Create new entity
  - Edit entity
  - Delete entity (with dependencies)
  - Save configuration
  - Validation flow
  - Graph interaction
- [ ] Test with real `arbodat-database.yml`
- [ ] Test error scenarios:
  - Invalid YAML
  - Circular dependencies
  - Duplicate entity names
  - Missing dependencies
- [ ] Test edge cases:
  - Large configurations (100+ entities)
  - Empty configuration
  - Configuration with errors
- [ ] Performance testing:
  - Load time
  - Graph rendering
  - Validation speed

**Deliverable**: Comprehensive test suite

**Acceptance Criteria**:
- All critical user flows have E2E tests
- Tests pass consistently
- Edge cases covered
- Performance acceptable

**Time Estimate**: 2 days

---

#### **Sprint 9.2: UI Polish & UX Improvements (2 days)**

**Polish Activities**
- [ ] Review and improve loading states
- [ ] Add skeleton loaders where appropriate
- [ ] Improve error messages (user-friendly)
- [ ] Add success notifications (toasts)
- [ ] Add keyboard shortcuts:
  - Ctrl+S: Save
  - Ctrl+N: New entity
  - Ctrl+F: Focus search
  - Escape: Close dialogs
- [ ] Add tooltips to all buttons and fields
- [ ] Add inline help text
- [ ] Review and fix responsive layout issues
- [ ] Add animations (subtle, professional)
- [ ] Test accessibility:
  - Keyboard navigation
  - Screen reader compatibility
  - Color contrast
- [ ] Add dark mode support (optional)

**Deliverable**: Polished, professional UI

**Acceptance Criteria**:
- Consistent visual design
- Clear feedback for all actions
- Keyboard shortcuts work
- Accessible (WCAG 2.1 AA)
- Responsive on tablets

**Time Estimate**: 2 days

---

#### **Sprint 9.3: Documentation & Deployment (1 day)**

**Documentation**
- [ ] User guide:
  - Getting started
  - Creating entities
  - Using the graph
  - Understanding validation
  - Tips and tricks
- [ ] Developer guide:
  - Project structure
  - Adding new entity types
  - Extending validation
  - Deployment instructions
- [ ] API documentation (review and enhance)
- [ ] README.md updates
- [ ] CHANGELOG.md

**Deployment**
- [ ] Create Dockerfile for production
- [ ] Create docker-compose.yml (optional)
- [ ] Test production build
- [ ] Create deployment instructions
- [ ] Set up basic CI/CD (optional)

**Deliverable**: Complete documentation and deployment artifacts

**Acceptance Criteria**:
- User can follow guide to use the app
- Developer can set up project from docs
- Production deployment works
- All docs up to date

**Time Estimate**: 1 day

---

## 4. Effort Estimation Summary

### **By Sprint**

| Week | Sprint | Description | Days | Hours (8h/day) |
|------|--------|-------------|------|----------------|
| 1 | 1.1 | Project Scaffolding | 2 | 16 |
| 1 | 1.2 | Frontend Setup | 2 | 16 |
| 1 | 1.3 | Models & Types | 1 | 8 |
| 2 | 2.1 | YAML Service | 2 | 16 |
| 2 | 2.2 | Configuration Service | 2 | 16 |
| 2 | 2.3 | Validation Service | 1 | 8 |
| 3 | 3.1 | Configuration API | 2 | 16 |
| 3 | 3.2 | Entity API | 2 | 16 |
| 3 | 3.3 | Validation & Dependency API | 1 | 8 |
| 4 | 4.1 | API Client | 2 | 16 |
| 4 | 4.2 | Pinia Stores | 2 | 16 |
| 4 | 4.3 | Composables | 1 | 8 |
| 5 | 5.1 | Layout & Navigation | 2 | 16 |
| 5 | 5.2 | Entity List | 2 | 16 |
| 5 | 5.3 | Entity Detail | 1 | 8 |
| 6 | 6.1 | Basic Properties Form | 2 | 16 |
| 6 | 6.2 | Columns & Dependencies | 2 | 16 |
| 6 | 6.3 | Type-Specific Forms | 1 | 8 |
| 7 | 7.1 | Dependency Graph | 3 | 24 |
| 7 | 7.2 | Foreign Key Editor | 2 | 16 |
| 8 | 8.1 | Load/Save Config | 2 | 16 |
| 8 | 8.2 | Validation Report | 2 | 16 |
| 8 | 8.3 | Backup Management | 1 | 8 |
| 9 | 9.1 | Integration Testing | 2 | 16 |
| 9 | 9.2 | UI Polish | 2 | 16 |
| 9 | 9.3 | Documentation | 1 | 8 |
| **Total** | | | **45 days** | **360 hours** |

### **By Category**

| Category | Days | Percentage |
|----------|------|------------|
| Backend (API, Services) | 12 | 27% |
| Frontend (UI Components) | 20 | 44% |
| Integration & State Management | 5 | 11% |
| Testing & QA | 4 | 9% |
| Polish & Documentation | 4 | 9% |
| **Total** | **45** | **100%** |

### **Timeline Estimates**

#### **Ideal Conditions** (1 developer, full-time, no interruptions)
- **Best Case**: 8 weeks (working days)
- **Expected**: 9 weeks (accounting for minor issues)
- **With Buffer**: 10-11 weeks (20% buffer)

#### **Real-World Conditions** (1 developer, with typical interruptions)
- **With 30% overhead**: 12 weeks
- **Part-time (50%)**: 18-20 weeks

#### **Team of 2 Developers**
- **Parallel work**: 5-6 weeks (with good coordination)
- **With integration overhead**: 6-7 weeks

---

## 5. Risk Assessment & Mitigation

### **High Risk Items**

| Risk | Impact | Probability | Mitigation | Time Impact |
|------|--------|-------------|------------|-------------|
| ruamel.yaml doesn't preserve formatting | High | Medium | Fallback to manual edit mode, extensive testing | +3 days |
| Circular dependency detection edge cases | Medium | Medium | Comprehensive test cases, NetworkX testing | +2 days |
| Large configuration performance | Medium | Medium | Virtual scrolling, progressive rendering | +2 days |
| Graph layout complexity | Medium | Low | Use dagre library, multiple layout options | +1 day |
| Integration issues with existing code | High | Low | Early integration testing, wrapper classes | +3 days |
| VeeValidate + Zod learning curve | Low | Medium | Good documentation available | +1 day |
| Vue Flow performance issues | Medium | Low | Evaluate alternatives, canvas rendering | +2 days |

### **Medium Risk Items**

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| TypeScript type mismatches | Low | High | Shared type generation, strict typing |
| UI/UX refinement takes longer | Low | High | Iterative reviews, user feedback early |
| Validation error message quality | Medium | Medium | Review with domain experts |
| Browser compatibility issues | Low | Low | Modern browser focus, testing |

### **Total Risk Buffer**: +14 days worst case (covered in 20% buffer)

---

## 6. Success Metrics

### **Phase 1 Completion Criteria**

#### **Functional Requirements** (Must Have)
- ✅ Can load existing YAML configuration
- ✅ Can create new entity with all basic properties
- ✅ Can edit existing entity
- ✅ Can delete entity (with dependency check)
- ✅ Can view dependency graph
- ✅ Can detect circular dependencies
- ✅ Can save configuration with backup
- ✅ Validation runs and shows results
- ✅ All existing validation specs integrated

#### **Quality Metrics**
- ⚡ Load configuration < 2 seconds
- ⚡ Validation completes < 3 seconds (typical config)
- ⚡ Graph renders < 1 second (100 entities)
- ⚡ UI operations < 200ms response time
- 🧪 80%+ backend test coverage
- 🧪 70%+ frontend test coverage
- 🧪 All critical paths have E2E tests
- 🎨 Passes accessibility audit (WCAG 2.1 AA)

#### **User Acceptance Criteria**
- 👤 Domain specialist creates config in < 30 minutes
- 👤 Zero file corruptions in testing
- 👤 90% reduction in syntax errors vs manual editing
- 👤 User satisfaction rating ≥ 4/5
- 👤 5 successful user acceptance tests

---

## 7. Dependencies & Prerequisites

### **Technical Prerequisites**
- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed
- ✅ pnpm installed (or npm)
- ✅ Git repository set up
- ✅ Access to existing Shape Shifter codebase
- ✅ Sample YAML configurations for testing

### **Knowledge Prerequisites**
- 👨‍💻 Vue 3 Composition API experience
- 👨‍💻 TypeScript fundamentals
- 👨‍💻 FastAPI basics
- 👨‍💻 REST API design
- 👨‍💻 Graph algorithms (basic)

### **External Dependencies**
- 📦 All npm packages available
- 📦 All Python packages available (pip/uv)
- 📦 No external services required (Phase 1)

---

## 8. Handoff & Transition to Phase 2

### **Phase 1 Deliverables**
- ✅ Working application (frontend + backend)
- ✅ Source code in Git repository
- ✅ Test suite (unit, integration, E2E)
- ✅ User documentation
- ✅ Developer documentation
- ✅ Deployment instructions
- ✅ Known issues list
- ✅ Phase 2 recommendations

### **Phase 2 Planning Inputs**
- 📊 User feedback from Phase 1
- 📊 Performance metrics
- 📊 Usage patterns
- 📊 Feature requests
- 📊 Technical debt items

### **Transition Timeline**
- **Week 10**: Phase 1 user acceptance testing
- **Week 11**: Bug fixes and refinements
- **Week 12**: Phase 2 planning and design
- **Week 13+**: Phase 2 development begins

---

## 9. Resource Allocation

### **Developer Time Allocation**

```
Backend:          27% (12 days)
Frontend:         44% (20 days)
Integration:      11% (5 days)
Testing:          9%  (4 days)
Polish/Docs:      9%  (4 days)
```

### **Ideal Team Composition**

**Single Developer** (MVP approach):
- Full-stack developer with Vue + Python experience
- 9 weeks full-time

**Two Developers** (Recommended):
- **Frontend Developer**: Vue 3, TypeScript, Vuetify
  - Weeks 1-2: Setup + API client
  - Weeks 3-6: UI components
  - Weeks 7-9: Testing + polish
- **Backend Developer**: Python, FastAPI
  - Weeks 1-3: API + services
  - Weeks 4-5: Integration support
  - Weeks 6-9: Advanced features + testing

**Timeline with 2 developers**: 6-7 weeks

---

## 10. Next Steps

### **Immediate Actions** (Week 1, Days 1-2)
1. Review and approve this plan
2. Set up development environment
3. Create project repositories (monorepo or separate)
4. Initialize backend (FastAPI) project
5. Initialize frontend (Vue 3) project
6. Set up project management tool (Jira, Linear, GitHub Projects)
7. Schedule weekly demos/reviews

### **Week 1 Goals**
- Backend server running with health check
- Frontend dev server running with Vuetify
- Basic project structure in place
- CI/CD pipeline started (optional)

### **Communication Plan**
- **Daily**: Standup (if team > 1)
- **Weekly**: Demo to stakeholders
- **Bi-weekly**: Retrospective and plan adjustment

---

## 11. Appendix: Technology Checklist

### **Backend Stack**
- [x] Python 3.11+
- [x] FastAPI
- [x] Pydantic v2
- [x] ruamel.yaml
- [x] NetworkX (dependency graphs)
- [x] pytest
- [x] uvicorn

### **Frontend Stack**
- [x] Vue 3 (Composition API)
- [x] TypeScript
- [x] Vite
- [x] Vuetify 3
- [x] Pinia
- [x] Vue Router 4
- [x] VeeValidate + Zod
- [x] Vue Flow
- [x] Monaco Editor
- [x] Axios
- [x] Vitest
- [x] Playwright

### **Development Tools**
- [x] ESLint + Prettier
- [x] Vue Language Features (Volar)
- [x] Python Black + Pylint
- [x] Git
- [x] Docker (optional)

---

**End of Implementation Plan**

**Approval Signatures**:
- Project Manager: _________________ Date: _______
- Technical Lead: __________________ Date: _______
- Stakeholder: _____________________ Date: _______
