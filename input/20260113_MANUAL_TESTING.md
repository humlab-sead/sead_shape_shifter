# Frontend Manual Testing Guide - Shape Shifter Project Editor

## Overview

This guide provides comprehensive step-by-step manual testing procedures for the Shape Shifter Project Editor frontend application. Use this guide to ensure all UI features work correctly across different browsers and scenarios.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Core Application Testing](#core-application-testing)
- [Project Editor Testing](#project-editor-testing)
- [Entity Editor Testing](#entity-editor-testing)
- [Graph & Dependencies Testing](#graph--dependencies-testing)
- [Reconciliation Testing](#reconciliation-testing)
- [Validation Testing](#validation-testing)
- [Execute Workflow Testing](#execute-workflow-testing)
- [Ingester Testing](#ingester-testing)
- [Data Source Testing](#data-source-testing)
- [Cross-Browser Testing](#cross-browser-testing)
- [Feature-Specific Testing](#feature-specific-testing)
- [Error Scenario Testing](#error-scenario-testing)
- [Performance Testing](#performance-testing)
- [Accessibility Testing](#accessibility-testing)
- [Test Results Template](#test-results-template)

---

## Prerequisites

### Environment Setup

```bash
# Start backend server (Terminal 1)
cd /home/roger/source/sead_shape_shifter
make br
# Backend runs at: http://localhost:8012

# Start frontend server (Terminal 2)
make fr
# Frontend runs at: http://localhost:5173
```

### Verification Checklist

Before starting tests, verify:

- [x] Backend server running at http://localhost:8012
- [x] Frontend server running at http://localhost:5173
- [x] Backend health check passes: http://localhost:8012/api/v1/health
- [x] No console errors on initial page load
- [x] Browser DevTools open (F12)
- [x] Test project files available in `input/` directory

---

## Getting Started

### Initial Application Load

**Steps:**

1. Open browser
2. Navigate to http://localhost:5173
3. Wait for application to load

**Expected Results:**

- [x] Application loads within 2 seconds
- [x] No JavaScript errors in console
- [x] Navigation sidebar visible
- [x] Application title displayed
- [x] Theme toggle button visible
- [x] Current route highlighted in navigation

**Screenshot Checklist:**
- [x] Light mode renders correctly
- [x] Dark mode renders correctly (toggle theme)
- [x] Layout is responsive

---

## Core Application Testing

### Navigation Menu

**Test: Navigate Between Pages**

1. Click "Projects" in sidebar
2. Click "Data Sources" in sidebar
3. Click "Settings" in sidebar
4. Use browser back/forward buttons

**Expected Results:**

- [x] Each page loads without errors
- [x] Active route highlighted in navigation
- [x] Page content changes appropriately
- [x] Browser history works correctly
- [x] No console errors during navigation

### Theme Toggle

**Test: Light/Dark Mode Switch**

1. Note current theme (light or dark)
2. Click theme toggle button
3. Observe UI changes
4. Click toggle again
5. Refresh page

**Expected Results:**

- [x] Theme switches immediately
- [x] All UI elements adapt to new theme
- [x] Text remains readable (sufficient contrast)
- [x] Theme preference persists after refresh
- [x] No flickering during theme switch

### Responsive Layout

**Test: Different Screen Sizes**

1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M / Cmd+Shift+M)
3. Test viewports:
   - Mobile: 375x667 (iPhone SE)
   - Tablet: 768x1024 (iPad)
   - Desktop: 1920x1080

**Expected Results:**

- [x] Navigation collapses to hamburger menu on mobile
- [x] Content reflows appropriately
- [x] No horizontal scrolling
- [x] Touch targets ≥ 44x44px on mobile
- [x] Text remains readable at all sizes

---

## Project Editor Testing

### Project List View

**Test: Load Project List**

1. Navigate to "Projects"
2. Wait for list to load

**Expected Results:**

- [x] Project cards displayed
- [x] Each card shows: name, description, entity count
- [x] Cards are clickable
- [x] Loading skeleton appears before data loads
- [x] Empty state shown if no projects

**Test: Search Projects**

1. Enter search term in search box
2. Clear search
3. Search for non-existent project

**Expected Results:**

- [x] List filters as you type
- [x] Search is case-insensitive
- [x] Clearing search restores full list
- [x] "No results" message for no matches

### Create New Project

**Test: Project Creation**

1. Click "Create New Project" button
2. Enter project name: `test_project_manual`
3. Enter description (optional)
4. Click "Create"

**Expected Results:**

- [x] Dialog opens with form fields
- [x] Name field validates (required, unique)
- [x] Create button disabled until valid
- [x] Success notification appears
- [x] Redirected to project editor
- [x] New project appears in list

### Edit Project

**Test: Open Existing Project**

1. Click on project card
2. Wait for editor to load

**Expected Results:**

- [x] Editor view loads
- [x] YAML content displayed in Monaco editor
- [x] Syntax highlighting active
- [x] Line numbers visible
- [x] Entity list panel visible
- [x] Toolbar buttons enabled (Test Run, Validate, Execute, Backups, Save)

**Test: Edit YAML Content**

1. Make a simple edit (e.g., add comment)
2. Observe unsaved changes indicator
3. Make a syntax error
4. Fix the error

**Expected Results:**

- [ ] IGNORED: Unsaved changes indicator appears (*)
- [x] Syntax errors underlined in red
- [x] Error details shown on hover
- [x] Save button enabled when changes exist
- [x] Save button state reflects save status

**Note:** Auto-save is not currently implemented. Changes must be saved manually using the "Save" button.

### Save Project

**Test: Manual Save**

1. Edit project content
2. Click "Save" button
3. Observe notifications
4. Refresh page

**Expected Results:**

- [x] Save button shows loading state
- [x] Success notification appears
- [x] Unsaved indicator clears
- [x] Backup created (timestamp in `backups/`)
- [x] Changes persist after refresh

**Test: Save with Validation Errors**

1. Introduce validation error
2. Attempt to save

**Expected Results:**

- [ ] Save completes (saves invalid project)
- [ ] Warning notification about validation
- [ ] Validation panel shows errors
- [ ] User can fix and re-save

### Delete Project

**Test: Delete Project**

1. Open project
2. Click "Delete" button
3. Confirm deletion in dialog

**Expected Results:**

- [ ] Confirmation dialog appears
- [ ] Dialog explains consequences
- [ ] Cancel button works
- [ ] Confirm deletes project
- [ ] Redirected to project list
- [ ] Deleted project removed from list

---

## Entity Editor Testing

### Entity List Panel

**Test: Entity List Display**

1. Open project with multiple entities
2. Observe entity list panel

**Expected Results:**

- [ ] All entities listed
- [ ] Entity names displayed
- [ ] Entity types shown (icons/badges)
- [ ] Entities sorted alphabetically
- [ ] Search box functional
- [ ] Entity count accurate

**Test: Filter Entities**

1. Type in entity filter box
2. Clear filter

**Expected Results:**

- [ ] List filters instantly
- [ ] Matching entities highlighted
- [ ] Non-matches hidden
- [ ] Count updates
- [ ] Clear button appears when typing

### Create New Entity

**Test: Entity Creation Flow**

1. Click "Add Entity" button
2. Fill in Basic tab:
   - Name: `test_entity_manual`
   - Type: `sql`
   - Data Source: select from dropdown
   - Keys: add `test_id`
   - SQL Query: enter simple SELECT
3. Click "Create"

**Expected Results:**

- [ ] Dialog opens with tabbed interface
- [ ] Basic tab shows all required fields
- [ ] Field validation works (required fields)
- [ ] Create button disabled until valid
- [ ] Success notification on creation
- [ ] New entity appears in YAML
- [ ] New entity in entity list

### Edit Entity

**Test: Open Entity Editor**

1. Click entity in list
2. Observe editor dialog

**Expected Results:**

- [ ] Dialog opens in edit mode
- [ ] All entity data loaded
- [ ] Tabs available: Basic, Foreign Keys, Advanced, YAML, Preview
- [ ] Fields populated correctly
- [ ] Title shows "Edit [entity_name]"

### Entity Editor - Basic Tab

**Test: Edit Basic Fields**

1. Open entity editor
2. On Basic tab, modify:
   - Change type (if applicable)
   - Update keys
   - Modify columns
   - Change surrogate_id
3. Click "Save"

**Expected Results:**

- [ ] All fields editable
- [ ] Type change updates available fields
- [ ] Multi-select fields work (chips)
- [ ] Validation updates in real-time
- [ ] Save updates YAML immediately
- [ ] Changes reflect in entity list

**Test: Fixed Values Entity**

1. Create new entity, type: `fixed`
2. Add keys and columns
3. Observe Fixed Values Grid

**Expected Results:**

- [ ] Grid appears when type is `fixed`
- [ ] Columns from keys + columns shown
- [ ] Add Row button works
- [ ] Delete Selected button works
- [ ] Cells are editable
- [ ] Data saves to YAML as 2D array

### Entity Editor - Foreign Keys Tab

**Test: Add Foreign Key**

1. Switch to "Foreign Keys" tab
2. Click "Add" button
3. Fill in foreign key:
   - Target Entity: select entity
   - Local Keys: add column(s)
   - Remote Keys: add column(s)
   - Join Type: select `inner`
4. Expand "Constraints"
5. Set cardinality: `many_to_one`
6. Click "Save"

**Expected Results:**

- [ ] Tab disabled for new entities
- [ ] Add button creates new FK card
- [ ] All fields functional
- [ ] Join type dropdown works
- [ ] Constraints panel collapses/expands
- [ ] Delete button removes FK
- [ ] Test Join button appears (if entity saved)
- [ ] FK saves to YAML correctly

**Test: Test Foreign Key Join**

1. Add/select existing FK
2. Click "Test Join" button
3. Observe results

**Expected Results:**

- [ ] Button disabled for unsaved entities
- [ ] Loading indicator appears
- [ ] Results dialog opens
- [ ] Statistics shown (rows matched, etc.)
- [ ] Sample data preview displayed
- [ ] Errors clearly shown if join fails
- [ ] Dialog closable

### Entity Editor - Advanced Tab

**Test: Filters Project**

1. Switch to "Advanced" tab
2. Expand "Filters" panel
3. Click "Add Filter"
4. Configure `exists_in` filter:
   - Entity: select entity
   - Column: enter column
   - Remote Column: enter column
5. Click "Save"

**Expected Results:**

- [ ] Filter card appears
- [ ] Type selector shows filter types
- [ ] Entity autocomplete works
- [ ] All fields editable
- [ ] Remove button works
- [ ] Multiple filters supported
- [ ] Saves to YAML under `filters`

**Test: Unnest Project**

1. Toggle "Enable Unnest" switch
2. Fill in unnest fields:
   - ID Variables: add columns
   - Value Variables: add columns
   - Variable Name Column: enter name
   - Value Name Column: enter name
3. Toggle off "Enable Unnest"
4. Click "Save"

**Expected Results:**

- [ ] Switch toggles unnest panel visibility
- [ ] Fields appear immediately when enabled
- [ ] Multi-select comboboxes work
- [ ] Text fields editable
- [ ] Toggling off clears unnest from YAML
- [ ] Toggling on adds unnest to YAML
- [ ] Changes save correctly

**Test: Append Data**

1. Click "Add Append"
2. Select type: `fixed`
3. Enter values as JSON array
4. Change type to `sql`
5. Enter data source and query
6. Click "Save"

**Expected Results:**

- [ ] Append card created
- [ ] Type selector switches UI
- [ ] Fixed type shows textarea for JSON
- [ ] SQL type shows data source + query fields
- [ ] Validation occurs on JSON input
- [ ] Multiple appends supported
- [ ] Remove button works

**Test: Extra Columns**

1. Click "Add Extra Column"
2. Enter:
   - New Column Name: `extra_col`
   - Source Column: leave empty or select
3. Add another extra column
4. Remove one
5. Click "Save"

**Expected Results:**

- [ ] Extra column row added
- [ ] Column name field required
- [ ] Source column optional (null if empty)
- [ ] Multiple extra columns supported
- [ ] Delete button works
- [ ] Saves to YAML as object

### Entity Editor - YAML Tab

**Test: View Entity YAML**

1. Switch to "YAML" tab
2. Observe YAML content

**Expected Results:**

- [ ] YAML for current entity only shown
- [ ] Syntax highlighting active
- [ ] YAML read-only or editable
- [ ] Validation occurs on edits
- [ ] Info message about syncing displayed

**Test: Edit Entity YAML Directly**

1. Make change in YAML
2. Switch to Basic tab
3. Return to YAML tab

**Expected Results:**

- [ ] Changes sync to form fields
- [ ] Form fields update immediately
- [ ] Invalid YAML shows error
- [ ] Error message clear and actionable
- [ ] Can correct errors in YAML view

### Entity Editor - Preview Tab

**Test: Load Entity Preview**

1. Switch to "Preview" tab
2. Click "Refresh" button
3. Observe data preview

**Expected Results:**

- [ ] Tab disabled for unsaved entities
- [ ] Refresh button loads data
- [ ] Loading indicator appears
- [ ] ag-grid displays data
- [ ] Row count shown
- [ ] Execution time displayed
- [ ] Grid is scrollable
- [ ] Column headers clear

**Test: Preview with Errors**

1. Modify entity to cause error (e.g., invalid SQL)
2. Save entity
3. Try to load preview

**Expected Results:**

- [ ] Error message displayed
- [ ] Error details shown
- [ ] No app crash
- [ ] Can dismiss error
- [ ] Can fix entity and retry

### Entity Editor - Split View

**Test: Enable Split View**

1. In entity editor, click split view toggle (expand icon)
2. Observe layout change

**Expected Results:**

- [ ] Layout splits into left (form) and right (preview)
- [ ] Both panels visible
- [ ] Preview panel shows ag-grid
- [ ] Auto-refresh toggle available
- [ ] Refresh button works
- [ ] Form edits still functional

**Test: Auto-Refresh in Split View**

1. Enable split view
2. Enable "Auto-refresh" checkbox
3. Make change to entity (e.g., modify column)
4. Observe preview panel

**Expected Results:**

- [ ] Preview refreshes automatically after edits
- [ ] Debounced (not on every keystroke)
- [ ] Loading indicator during refresh
- [ ] Data updates in ag-grid
- [ ] No performance degradation

**Test: Collapse Split View**

1. Click split view toggle again

**Expected Results:**

- [ ] Layout returns to single panel
- [ ] Form expands to full width
- [ ] No data loss
- [ ] Smooth transition

### Entity Editor - Compact View

**Test: Field Sizing and Spacing**

1. Open entity editor
2. Observe field sizes, fonts, padding

**Expected Results:**

- [ ] Font sizes appropriate (11-12px)
- [ ] Field padding minimal but comfortable
- [ ] Labels clear and readable
- [ ] Chips (multi-select) compact
- [ ] Icons appropriately sized
- [ ] Delete buttons visible but not overwhelming
- [ ] Overall compact appearance

---

## Graph & Dependencies Testing

### Dependency Graph View

**Test: Open Graph View**

1. Open project with multiple entities
2. Click "Graph" tab in project detail view
3. Observe dependency graph

**Expected Results:**

- [ ] Graph renders with cytoscape.js
- [ ] Nodes displayed for all entities
- [ ] Edges show foreign key relationships
- [ ] Data source nodes distinguished (different style)
- [ ] Layout is readable and organized
- [ ] Zoom controls visible
- [ ] Fit-to-screen button available

### Graph Layout Options

**Test: Change Graph Layout**

1. Open graph view
2. Click layout dropdown
3. Select different layouts:
   - Breadthfirst
   - Circle
   - Concentric
   - Cose
   - Grid
   - Hierarchical

**Expected Results:**

- [ ] Layout dropdown accessible
- [ ] Each layout renders correctly
- [ ] Layout transitions smoothly
- [ ] Graph remains interactive
- [ ] Node positions update appropriately
- [ ] Performance acceptable (< 1s for layout change)

### Graph Display Options

**Test: Toggle Display Options**

1. Open graph view
2. Click display options dropdown
3. Toggle options:
   - Show labels
   - Show edge labels
   - Highlight paths
   - Compact view

**Expected Results:**

- [ ] Display options accessible
- [ ] Each option toggles immediately
- [ ] Labels appear/disappear correctly
- [ ] Edge labels readable
- [ ] Path highlighting works
- [ ] Options persist during session

### Graph Interaction

**Test: Node Selection**

1. Click on entity node in graph
2. Observe selection state
3. Click on data source node
4. Click on empty area to deselect

**Expected Results:**

- [ ] Node highlights on click
- [ ] Quick edit drawer opens for entities
- [ ] Data source nodes show info message
- [ ] Clicking empty area deselects
- [ ] Selection state visible

**Test: Graph Navigation**

1. Zoom in/out using mouse wheel
2. Pan by dragging background
3. Click "Fit to screen" button
4. Double-click node

**Expected Results:**

- [ ] Zoom works smoothly
- [ ] Pan works in all directions
- [ ] Fit-to-screen centers graph
- [ ] Double-click may trigger action
- [ ] Navigation controls responsive

### Quick Edit from Graph

**Test: Edit Entity from Graph**

1. Click entity node in graph
2. Observe quick edit drawer
3. Make changes to entity YAML
4. Save changes

**Expected Results:**

- [ ] Drawer opens on right side
- [ ] Entity YAML loaded in editor
- [ ] YAML editable
- [ ] Unsaved changes indicator works
- [ ] Save button functional
- [ ] Graph updates after save
- [ ] Can close drawer

**Test: Close Quick Edit**

1. Open quick edit drawer
2. Make unsaved changes
3. Click close or outside drawer

**Expected Results:**

- [ ] Confirmation dialog if unsaved changes
- [ ] Can cancel close action
- [ ] Changes discarded if confirmed
- [ ] Drawer closes smoothly

### Circular Dependency Detection

**Test: View Circular Dependencies**

1. Open project with circular dependencies
2. Observe circular dependency alert
3. Click on alert to view details

**Expected Results:**

- [ ] Alert appears if circular dependencies exist
- [ ] Alert shows number of cycles
- [ ] Can expand to see cycle details
- [ ] Affected entities listed
- [ ] Cycle path shown clearly
- [ ] Can navigate to entities from alert

### Task Status Filtering

**Test: Filter by Task Status**

1. Open graph view
2. Click task filter dropdown
3. Select filters:
   - All tasks
   - Pending
   - In progress
   - Completed
   - Not started

**Expected Results:**

- [ ] Filter dropdown accessible
- [ ] Graph nodes update based on filter
- [ ] Filtered nodes highlighted/dimmed
- [ ] Filter persists during session
- [ ] Count updates correctly

### Graph Context Menu

**Test: Right-Click Context Menu**

1. Right-click on entity node
2. Observe context menu
3. Select menu options

**Expected Results:**

- [ ] Context menu appears on right-click
- [ ] Options include: Edit, Validate, Preview, Delete
- [ ] Selecting option performs action
- [ ] Menu closes after selection
- [ ] Menu positioned near cursor

### Graph Performance

**Test: Large Graph Performance**

1. Open project with 20+ entities
2. Observe graph rendering
3. Interact with graph (zoom, pan, select)

**Expected Results:**

- [ ] Graph renders within 2 seconds
- [ ] Interactions remain smooth (60fps)
- [ ] No lag when zooming/panning
- [ ] Node selection immediate
- [ ] Layout changes performant

---

## Reconciliation Testing

### Reconciliation Overview

**Test: Access Reconciliation**

1. Open project
2. Click "Reconcile" tab
3. Observe reconciliation interface

**Expected Results:**

- [ ] Reconciliation tab accessible
- [ ] Three sub-tabs visible: Configuration, Reconcile, YAML
- [ ] Service health check displays
- [ ] Service name shown if connected
- [ ] Error message if service offline

### Service Health Check

**Test: Check Service Status**

1. Navigate to Reconciliation tab
2. Observe service status indicator
3. Click refresh if available

**Expected Results:**

- [ ] Service status shown (online/offline)
- [ ] Service name displayed when online
- [ ] Error message clear when offline
- [ ] Refresh button functional
- [ ] Status updates automatically

### Reconciliation Configuration

**Test: View Specifications List**

1. Click "Configuration" sub-tab
2. Observe specifications list
3. Search for specific specification

**Expected Results:**

- [ ] All specifications listed
- [ ] Each shows: entity name, target field, mapping count
- [ ] Search box functional
- [ ] Specifications filterable
- [ ] Empty state if no specifications
- [ ] Can click to view details

**Test: Create Reconciliation Specification**

1. Click "Add Specification" button
2. Fill in specification form:
   - Entity name: select from dropdown
   - Target field: select from dropdown
   - Source field: enter field name
   - Service type: select (e.g., "site")
   - Auto-accept threshold: set value (0-100)
   - Review threshold: set value (0-100)
3. Add property mappings (optional)
4. Click "Create"

**Expected Results:**

- [ ] Create dialog opens
- [ ] Entity dropdown populated
- [ ] Target field dropdown updates based on entity
- [ ] Service type dropdown shows available types
- [ ] Threshold sliders functional (0-100 range)
- [ ] Can add multiple property mappings
- [ ] Validation prevents invalid values
- [ ] Create button disabled until form valid
- [ ] Success message on creation
- [ ] New spec appears in list

**Test: Edit Reconciliation Specification**

1. Click edit icon on existing specification
2. Modify fields:
   - Change auto-accept threshold
   - Update property mappings
   - Add new property mapping
3. Click "Save"

**Expected Results:**

- [ ] Edit dialog opens with current values
- [ ] All fields editable
- [ ] Changes apply immediately
- [ ] Success message on save
- [ ] Specification list updates

**Test: Delete Reconciliation Specification**

1. Click delete icon on specification
2. Confirm deletion

**Expected Results:**

- [ ] Confirmation dialog appears
- [ ] Warning about data loss shown
- [ ] Can cancel deletion
- [ ] Specification removed from list
- [ ] Success message displayed

### Auto-Reconcile Workflow

**Test: Run Auto-Reconcile**

1. Click "Reconcile" sub-tab
2. Select entity from dropdown
3. Select target field from dropdown
4. Adjust auto-accept threshold slider (default 95%)
5. Click "Run Auto-Reconcile" button
6. Wait for completion

**Expected Results:**

- [ ] Entity dropdown populated with reconcilable entities
- [ ] Target field dropdown updates based on entity
- [ ] Threshold slider functional (0-100)
- [ ] Run button disabled until entity+field selected
- [ ] Loading indicator appears during reconciliation
- [ ] Progress updates shown (if available)
- [ ] Success message on completion
- [ ] Results displayed in grid

### Reconciliation Grid

**Test: View Reconciliation Results**

1. After auto-reconcile, observe grid
2. Scroll through results
3. Sort by columns

**Expected Results:**

- [ ] Grid displays all source records
- [ ] Columns include: source value, matched value, confidence, status
- [ ] Confidence shown as percentage
- [ ] Status indicators clear (matched/unmatched/review)
- [ ] Color coding for status (green/yellow/red)
- [ ] Grid scrollable
- [ ] Column sorting works
- [ ] Row count displayed

**Test: Review Reconciliation Matches**

1. Find row with "Review" status (confidence below auto-accept)
2. Click on row
3. Observe candidate suggestions
4. Select correct match from suggestions
5. Click "Accept" or "Reject"

**Expected Results:**

- [ ] Review rows highlighted
- [ ] Click expands row or opens dialog
- [ ] Candidate suggestions shown
- [ ] Each candidate shows name, ID, confidence
- [ ] Can select candidate
- [ ] Accept button applies mapping
- [ ] Reject button marks as unmatched
- [ ] Grid updates immediately

**Test: Manual Mapping**

1. Find unmatched row
2. Click "Add Mapping" or edit icon
3. Search for entity in autocomplete
4. Select correct entity
5. Add notes (optional)
6. Save mapping

**Expected Results:**

- [ ] Mapping dialog/form opens
- [ ] Autocomplete search functional
- [ ] Search queries reconciliation service
- [ ] Results show entity name and ID
- [ ] Can select from results
- [ ] Notes field optional
- [ ] Save updates mapping
- [ ] Grid row status changes to "Matched"
- [ ] Confidence shows 100% (manual)

**Test: Delete Mapping**

1. Find mapped row
2. Click delete/remove mapping button
3. Confirm deletion

**Expected Results:**

- [ ] Delete button visible for mapped rows
- [ ] Confirmation dialog appears
- [ ] Mapping removed from config
- [ ] Row status reverts to "Unmatched"
- [ ] Grid updates immediately

**Test: Mark as Unmatched**

1. Find row with low-confidence match
2. Click "Mark as Unmatched" button
3. Add notes explaining why (optional)
4. Confirm

**Expected Results:**

- [ ] Mark unmatched button available
- [ ] Notes field optional
- [ ] Action recorded in config
- [ ] Status changes to "Unmatched"
- [ ] Notes stored with record

### Reconciliation YAML Editor

**Test: Edit Reconciliation YAML**

1. Click "YAML" sub-tab
2. Observe YAML content
3. Make direct edit to YAML
4. Click "Save"

**Expected Results:**

- [ ] YAML tab shows reconciliation config
- [ ] Syntax highlighting active
- [ ] YAML structure clear
- [ ] Can edit directly
- [ ] Save button appears when modified
- [ ] Validation on save
- [ ] Error shown if invalid YAML
- [ ] Success message on save

**Test: Reload YAML**

1. Make changes to YAML
2. Click "Reload" button
3. Confirm discard changes

**Expected Results:**

- [ ] Reload button available
- [ ] Confirmation if unsaved changes
- [ ] YAML reverts to saved state
- [ ] Can cancel reload

### Reconciliation Preview

**Test: Preview Entity Data**

1. Select entity and target field
2. Observe preview data in grid
3. Check that mappings are applied

**Expected Results:**

- [ ] Preview loads automatically
- [ ] Shows source data with mappings
- [ ] Enriched columns visible (sead_id, confidence)
- [ ] Unmapped rows clearly indicated
- [ ] Preview updates after mappings change
- [ ] Row count accurate

### Save Reconciliation Changes

**Test: Save Reconciliation Config**

1. Make several mappings/changes
2. Observe unsaved changes indicator
3. Click "Save Changes" button
4. Confirm save

**Expected Results:**

- [ ] Unsaved indicator appears after changes
- [ ] Save button enabled when changes exist
- [ ] Save writes to reconciliation YAML file
- [ ] Success message displayed
- [ ] Changes persist after page refresh
- [ ] Backup created (optional)

### Reconciliation Error Handling

**Test: Service Connection Error**

1. Stop reconciliation service
2. Try to run auto-reconcile
3. Observe error handling

**Expected Results:**

- [ ] Error message clear and actionable
- [ ] Service status shows "Offline"
- [ ] Cannot run auto-reconcile when offline
- [ ] Can retry connection
- [ ] Manual mapping still works (cached data)

**Test: Invalid Entity Configuration**

1. Select entity without reconciliation spec
2. Attempt auto-reconcile

**Expected Results:**

- [ ] Error message explains missing spec
- [ ] Suggests creating specification
- [ ] Provides link to configuration tab

---

## Validation Testing

### Full Project Validation

**Test: Validate All**

1. Open project
2. Click "Validate All" button in toolbar
3. Wait for results

**Expected Results:**

- [ ] Button shows loading state
- [ ] Validation runs on all entities
- [ ] Results panel appears/updates
- [ ] Error count badge displayed
- [ ] Warning count badge displayed
- [ ] Execution time shown
- [ ] Results categorized by type

### Validation Result Categories

**Test: Navigate Validation Tabs**

1. After validation, click each tab:
   - Summary
   - Structural
   - Data
   - Entities
2. Observe content in each

**Expected Results:**

- [ ] Summary tab shows overview
- [ ] Structural tab shows project structure issues
- [ ] Data tab shows data quality issues
- [ ] Entities tab lists entity-specific validations
- [ ] Counts accurate in each tab
- [ ] Can expand/collapse validation items

### Entity-Specific Validation

**Test: Validate Single Entity**

1. Select entity in entity list
2. Click "Validate" icon/button for entity
3. Observe results

**Expected Results:**

- [ ] Only that entity validated
- [ ] Results filtered to entity
- [ ] Faster than full validation
- [ ] Error count specific to entity
- [ ] Can run on multiple entities sequentially

### Validation Caching

**Test: Cache Behavior**

1. Click "Validate All"
2. Note request time in Network tab (DevTools)
3. Immediately click "Validate All" again
4. Note request time

**Expected Results:**

- [ ] Second validation near-instant (cached)
- [ ] No new API request in Network tab
- [ ] Cache hit indicator shown (optional)
- [ ] Results identical

**Test: Cache Invalidation**

1. Run validation (cache results)
2. Edit project (modify entity)
3. Save project
4. Run validation again

**Expected Results:**

- [ ] Cache invalidated on edit
- [ ] New API request made
- [ ] New results reflect changes
- [ ] Execution time normal (not cached)

### Auto-Fix Suggestions

**Test: Apply Auto-Fix**

1. Run validation with fixable errors
2. Find validation with "Apply Fix" button
3. Click "Apply Fix"
4. Observe changes

**Expected Results:**

- [ ] Fix applied to YAML immediately
- [ ] YAML editor updates
- [ ] Success notification shown
- [ ] Re-validation shows error resolved
- [ ] Backup created before fix
- [ ] Can undo via backup

**Test: Multiple Auto-Fixes**

1. Apply one fix
2. Apply another fix
3. Run validation

**Expected Results:**

- [ ] Each fix applies independently
- [ ] No conflicts between fixes
- [ ] All fixes persist
- [ ] Validation shows improvements

### Validation Error Details

**Test: Expand Error Details**

1. Find validation error in results
2. Click to expand details

**Expected Results:**

- [ ] Details panel expands
- [ ] Error message clear and descriptive
- [ ] Location information shown (entity, field)
- [ ] Suggested fix shown (if available)
- [ ] Can click entity name to jump to it
- [ ] Can copy error message

---

## Execute Workflow Testing

### Execute Dialog

**Test: Open Execute Dialog**

1. Open a project
2. Click "Execute" button in toolbar
3. Observe dialog

**Expected Results:**

- [ ] Dialog opens with "Execute Workflow" title
- [ ] Dispatcher selection dropdown visible
- [ ] Form fields appropriate for selected dispatcher
- [ ] Cancel button available
- [ ] Execute button disabled until form valid

### Dispatcher Selection

**Test: Select Different Dispatchers**

1. Open Execute dialog
2. Click "Output Format" dropdown
3. Select each available dispatcher type:
   - Excel (xlsx) - file target
   - CSV - file target
   - CSV in ZIP - file target
   - Database - database target
   - Folder dispatchers (if available)

**Expected Results:**

- [ ] Dispatcher list loads from backend
- [ ] Each dispatcher shows: description, key, target_type
- [ ] Icons displayed for each target type (file/folder/database)
- [ ] Selecting dispatcher updates form fields
- [ ] File dispatchers show file path input
- [ ] Folder dispatchers show folder path input
- [ ] Database dispatchers show data source dropdown

### File Target Configuration

**Test: Configure File Output**

1. Select file dispatcher (e.g., "Excel Workbook (xlsx)")
2. Observe file path field
3. Leave empty to use default
4. Enter custom path: `./custom/output.xlsx`
5. Enter invalid path: `./custom/output.csv` (wrong extension)

**Expected Results:**

- [ ] File path field appears for file dispatchers
- [ ] Default hint shows: `./output/{project_name}.{extension}`
- [ ] File icon visible in field
- [ ] Validation requires correct file extension
- [ ] Error message shown for wrong extension
- [ ] Empty field uses default path

### Folder Target Configuration

**Test: Configure Folder Output**

1. Select folder dispatcher (e.g., "CSV Files (csv)")
2. Observe folder path field
3. Enter path: `./custom/output_folder`

**Expected Results:**

- [ ] Folder path field appears for folder dispatchers
- [ ] Default hint shows: `./output/{project_name}`
- [ ] Folder icon visible in field
- [ ] Path validation works
- [ ] Empty field uses default path

### Database Target Configuration

**Test: Configure Database Output**

1. Select database dispatcher (e.g., "PostgreSQL Database")
2. Observe data source dropdown
3. Select target database

**Expected Results:**

- [ ] Data source dropdown appears
- [ ] Lists all configured data sources
- [ ] Validation requires selection
- [ ] Database icon visible
- [ ] Hint text explains purpose

### Execution Options

**Test: Toggle Execution Options**

1. Observe execution options switches
2. Toggle "Run validation before execution"
3. Toggle "Apply translations"
4. Toggle "Drop foreign key columns"

**Expected Results:**

- [ ] Three toggle switches visible
- [ ] "Run validation" enabled by default
- [ ] "Apply translations" disabled by default
- [ ] "Drop foreign keys" disabled by default
- [ ] Each switch has descriptive hint text
- [ ] Switches toggle smoothly

### Execute Workflow

**Test: Execute to File (Success)**

1. Select "Excel Workbook (xlsx)" dispatcher
2. Leave file path empty (use default)
3. Ensure "Run validation" is enabled
4. Click "Execute" button
5. Wait for completion

**Expected Results:**

- [ ] Execute button shows loading state
- [ ] Loading indicator appears
- [ ] Success alert appears on completion
- [ ] Success message shows entity count
- [ ] Target path displayed
- [ ] "Download result file" button appears
- [ ] Download link functional
- [ ] Dialog auto-closes after 2 seconds (if download available)

**Test: Download Executed File**

1. After successful file execution
2. Observe download button in success alert
3. Click "Download result file" button

**Expected Results:**

- [ ] Download button visible for file targets only
- [ ] Button has download icon
- [ ] Clicking initiates file download
- [ ] File downloads with correct filename
- [ ] File contains expected data
- [ ] Can download multiple times

**Test: Execute to Database (Success)**

1. Select database dispatcher
2. Select target data source
3. Click "Execute" button
4. Wait for completion

**Expected Results:**

- [ ] Execute button shows loading state
- [ ] Success alert appears on completion
- [ ] Success message shows entity count
- [ ] No download button (database target)
- [ ] Dialog auto-closes immediately
- [ ] Data written to database successfully

**Test: Execute with Validation Errors**

1. Open project with validation errors
2. Open Execute dialog
3. Keep "Run validation" enabled
4. Click "Execute"

**Expected Results:**

- [ ] Execution stops if validation fails
- [ ] Error alert appears
- [ ] Error message explains validation failure
- [ ] Can cancel and fix errors
- [ ] Can disable "Run validation" to proceed anyway

**Test: Execute with Backend Error**

1. Select invalid project
2. Click "Execute"
3. Observe error handling

**Expected Results:**

- [ ] Error alert appears
- [ ] Error message from backend displayed
- [ ] Error details shown (if available)
- [ ] Loading state clears
- [ ] Can retry after fixing issue
- [ ] Dialog remains open

### Execute Dialog State Management

**Test: Form Validation**

1. Open Execute dialog
2. Leave dispatcher unselected
3. Select dispatcher but leave required fields empty

**Expected Results:**

- [ ] Execute button disabled when form invalid
- [ ] Field-level validation messages shown
- [ ] Form validates on change
- [ ] Execute button enables when valid
- [ ] All required fields marked

**Test: Reset Form State**

1. Fill in execute form
2. Click "Cancel"
3. Reopen Execute dialog

**Expected Results:**

- [ ] Form resets to defaults
- [ ] Dispatcher cleared
- [ ] File/folder paths reset
- [ ] Options reset to defaults
- [ ] No error messages shown
- [ ] Clean state on reopen

**Test: Auto-fill Default Paths**

1. Open Execute dialog
2. Select file dispatcher
3. Observe default file path hint
4. Select different dispatcher

**Expected Results:**

- [ ] Default paths include project name
- [ ] File extension matches dispatcher
- [ ] Paths update when switching dispatchers
- [ ] Hints show reasonable defaults

### Data Source List Loading

**Test: Data Sources Auto-Load**

1. Open Execute dialog (first time in session)
2. Select database dispatcher
3. Open data source dropdown

**Expected Results:**

- [ ] Data sources fetched automatically
- [ ] Loading indicator during fetch
- [ ] Data sources populate dropdown
- [ ] Cached for subsequent opens
- [ ] No duplicate fetches

### Execute Result Handling

**Test: Result Callback**

1. Execute workflow successfully
2. Observe parent component update

**Expected Results:**

- [ ] `executed` event emitted to parent
- [ ] Result object passed to parent
- [ ] Parent can react to execution
- [ ] UI updates appropriately

---

## Ingester Testing

### Ingester Overview

**Test: Access Ingester View**

1. Navigate to "Data Ingestion" in main navigation
2. Observe ingester interface

**Expected Results:**

- [ ] Ingester view loads
- [ ] Two-column layout (list + form)
- [ ] Info message when no ingester selected
- [ ] Title: "Data Ingestion"
- [ ] Description explaining purpose

### Ingester List

**Test: View Available Ingesters**

1. Observe left column (ingester list)
2. Review ingester cards

**Expected Results:**

- [ ] All registered ingesters displayed
- [ ] Each shows: name, description, version
- [ ] Icon or badge for each ingester
- [ ] Supported formats listed
- [ ] Clickable cards
- [ ] Active selection highlighted

**Test: Select Ingester**

1. Click on ingester card
2. Observe form update

**Expected Results:**

- [ ] Card highlights on selection
- [ ] Form appears in right column
- [ ] Form fields specific to selected ingester
- [ ] Info message replaced by form

### Ingester Form - Basic Fields

**Test: Fill in Common Fields**

1. Select ingester (e.g., "SEAD")
2. Fill in required fields:
   - Source file path
   - Submission name
   - Data types
   - Output folder
3. Observe validation

**Expected Results:**

- [ ] All required fields marked with asterisk
- [ ] File path field accepts path input
- [ ] Browse button opens file picker
- [ ] Submission name validates (no spaces/special chars)
- [ ] Data types dropdown/input functional
- [ ] Output folder has default value
- [ ] Validation messages clear
- [ ] Submit button disabled until valid

**Test: Database Connection Fields**

1. Observe database configuration section
2. Fill in database fields:
   - Host
   - Port
   - Database name
   - Username
   - Password (optional)

**Expected Results:**

- [ ] Database section collapsible/expandable
- [ ] Host field validates hostname/IP
- [ ] Port field accepts numbers only (default 5432)
- [ ] Database name required
- [ ] Username required
- [ ] Password field masked
- [ ] Test connection button available

### Ingester Form - Advanced Options

**Test: Configure Advanced Options**

1. Expand advanced options section
2. Configure options:
   - Ignore columns pattern
   - Batch size
   - Register data
   - Explode data
   - Verbose mode

**Expected Results:**

- [ ] Advanced section collapsible
- [ ] Ignore columns accepts patterns (comma-separated)
- [ ] Batch size accepts positive integers
- [ ] Register checkbox functional
- [ ] Explode checkbox functional
- [ ] Verbose checkbox functional
- [ ] Help text/tooltips available

### Validate Before Ingestion

**Test: Run Validation**

1. Fill in form completely
2. Click "Validate" button
3. Wait for validation results

**Expected Results:**

- [ ] Validate button visible
- [ ] Loading indicator during validation
- [ ] Progress messages shown
- [ ] Validation runs without modifying data
- [ ] Results displayed clearly
- [ ] Errors listed with details
- [ ] Warnings shown separately
- [ ] Success message if no issues
- [ ] Can proceed to ingest after validation

**Test: Validation Errors**

1. Enter invalid data (e.g., wrong file format)
2. Click "Validate"
3. Observe error handling

**Expected Results:**

- [ ] Validation catches errors
- [ ] Error messages specific and actionable
- [ ] Line numbers/locations provided (if applicable)
- [ ] Cannot proceed to ingest with errors
- [ ] Can fix errors and revalidate

### Run Ingestion

**Test: Execute Ingestion**

1. Complete valid form
2. Click "Ingest" or "Run" button
3. Monitor progress
4. Wait for completion

**Expected Results:**

- [ ] Ingest button enabled when form valid
- [ ] Confirmation dialog if validation not run
- [ ] Loading overlay appears
- [ ] Progress bar or spinner shown
- [ ] Progress messages update (if verbose)
- [ ] Execution time displayed
- [ ] Cannot close/navigate away during ingest
- [ ] Success message on completion
- [ ] Record count displayed

**Test: Ingestion Results**

1. After successful ingestion
2. Observe results panel/message

**Expected Results:**

- [ ] Success alert displayed
- [ ] Statistics shown (records processed, inserted, errors)
- [ ] Execution time shown
- [ ] Output file location displayed (if file-based)
- [ ] Database table name shown (if database)
- [ ] Can download results/logs
- [ ] Can run another ingestion

### Ingestion Error Handling

**Test: Database Connection Error**

1. Enter invalid database credentials
2. Attempt ingestion
3. Observe error handling

**Expected Results:**

- [ ] Connection error caught
- [ ] Error message explains issue
- [ ] Suggests checking credentials
- [ ] Ingestion stops gracefully
- [ ] Can correct and retry

**Test: File Not Found Error**

1. Enter non-existent file path
2. Attempt validation/ingestion
3. Observe error

**Expected Results:**

- [ ] File error caught early (validation)
- [ ] Error message clear
- [ ] Suggests checking path
- [ ] Browse button helps find correct file

**Test: Data Format Error**

1. Select Excel ingester
2. Provide CSV file
3. Attempt ingestion

**Expected Results:**

- [ ] Format mismatch detected
- [ ] Error message explains expected format
- [ ] Lists supported formats
- [ ] Suggests correct ingester

### Ingester Configuration Persistence

**Test: Save Configuration**

1. Fill in ingester form
2. Click "Save Configuration" (if available)
3. Reload page

**Expected Results:**

- [ ] Save config button available
- [ ] Configuration saved to file
- [ ] Can load saved config
- [ ] All fields populated from saved config
- [ ] Passwords not saved (security)

**Test: Load Configuration File**

1. Click "Load Configuration" button
2. Select previously saved config file
3. Observe form update

**Expected Results:**

- [ ] Load config button available
- [ ] File picker opens
- [ ] Accepts .json or .yaml files
- [ ] Form populates from config
- [ ] Validation runs on loaded config
- [ ] Can override loaded values

### Real-time Feedback

**Test: Progress Updates**

1. Enable verbose mode
2. Run ingestion on large dataset
3. Observe progress updates

**Expected Results:**

- [ ] Progress messages stream in real-time
- [ ] Percentage complete shown
- [ ] Current step/entity displayed
- [ ] Estimated time remaining (optional)
- [ ] Can view detailed logs
- [ ] Messages scrollable

### Cancel Ingestion

**Test: Cancel Running Ingestion**

1. Start long-running ingestion
2. Click "Cancel" button during execution
3. Confirm cancellation

**Expected Results:**

- [ ] Cancel button visible during execution
- [ ] Confirmation dialog appears
- [ ] Ingestion stops gracefully
- [ ] Partial results preserved (optional)
- [ ] Cleanup performed
- [ ] Can start new ingestion

### Ingester-Specific Features

**Test: SEAD Ingester Specifics**

1. Select SEAD ingester
2. Observe SEAD-specific options:
   - Submission type selection
   - Data type mapping
   - Column ignoring patterns
   - Auto-registration
   - Data explosion

**Expected Results:**

- [ ] SEAD options visible
- [ ] Submission types dropdown populated
- [ ] Data type mapping interface functional
- [ ] Ignore patterns accept wildcards
- [ ] Auto-register checkbox with explanation
- [ ] Explode option with warning

---

## Data Source Testing

### Data Sources List

**Test: View Data Sources**

1. Navigate to "Data Sources"
2. Observe list

**Expected Results:**

- [ ] All configured data sources shown
- [ ] Each shows: name, driver type, status
- [ ] Connection status indicators (green/red)
- [ ] Can search/filter data sources
- [ ] Empty state if no data sources

### Data Source Details

**Test: View Data Source Schema**

1. Click on data source
2. Observe details panel

**Expected Results:**

- [ ] Connection details displayed
- [ ] Tables list shown
- [ ] Can search tables
- [ ] Table count accurate
- [ ] Can refresh table list

**Test: Table Schema Viewer**

1. Click on table in data source
2. Observe schema information

**Expected Results:**

- [ ] Columns listed
- [ ] Data types shown
- [ ] Primary keys indicated
- [ ] Nullable columns marked
- [ ] Foreign keys shown (if available)

### Data Source Preview

**Test: Preview Table Data**

1. Select table
2. Click "Preview" button
3. Observe data preview

**Expected Results:**

- [ ] Sample data loads (10-50 rows)
- [ ] All columns displayed
- [ ] Data formatted correctly
- [ ] Can scroll horizontally/vertically
- [ ] Loading indicator during fetch
- [ ] Error handling for large tables

---

## Cross-Browser Testing

### Supported Browsers

Test in each of these browsers:

- **Chrome 120+** (primary)
- **Firefox 115+**
- **Edge 120+**
- **Safari 16+** (if on macOS)

### Core Functionality Checklist

For each browser, verify:

**Application Loading:**
- [ ] Application loads within 2 seconds
- [ ] No console errors
- [ ] Navigation works
- [ ] Theme toggle works

**Project Editor:**
- [ ] YAML editor displays correctly
- [ ] Syntax highlighting works
- [ ] Can edit and save
- [ ] Validation runs
- [ ] Execute dialog opens

**Entity Editor:**
- [ ] Dialog opens and closes
- [ ] All tabs functional
- [ ] Forms submit correctly
- [ ] Preview loads

**Execute Workflow:**
- [ ] Dialog opens correctly
- [ ] Dispatcher selection works
- [ ] Can execute workflow
- [ ] Download button functional
- [ ] Success/error messages display

**Visual Elements:**
- [ ] Fonts render correctly
- [ ] Icons display
- [ ] Colors appropriate (light/dark)
- [ ] Spacing consistent

### Browser-Specific Testing

#### Chrome DevTools

**Steps:**
1. Open DevTools (F12)
2. Check Console for errors
3. Monitor Network tab during operations
4. Use Performance tab for profiling

**Expected:**
- [ ] No errors or warnings
- [ ] API requests < 500ms
- [ ] UI interactions < 50ms
- [ ] 60 FPS animations

#### Firefox DevTools

**Steps:**
1. Open DevTools (F12)
2. Use CSS Grid Inspector on layout
3. Check Accessibility inspector
4. Monitor Storage tab for caching

**Expected:**
- [ ] CSS Grid layout correct
- [ ] Accessibility tree valid
- [ ] LocalStorage/SessionStorage working
- [ ] No CSS variable issues

#### Safari (macOS)

**Steps:**
1. Enable Develop menu: Safari → Settings → Advanced
2. Open Web Inspector (Cmd+Option+I)
3. Test touch gestures (if trackpad)
4. Check WebKit-specific rendering

**Expected:**
- [ ] Flexbox/Grid rendering correct
- [ ] Backdrop filters work (if used)
- [ ] Scrollbar styling acceptable
- [ ] Touch gestures responsive

### Performance Metrics

**Target Metrics (All Browsers):**

1. **Initial Page Load**: < 2 seconds
2. **Validation Response**: < 5 seconds
3. **UI Responsiveness**: 60 FPS
4. **Memory Usage**: < 100MB after 10 minutes

**Measuring Performance:**

```javascript
// In DevTools Console
performance.mark('validation-start');
// Click "Validate All"
performance.mark('validation-end');
performance.measure('validation', 'validation-start', 'validation-end');
console.table(performance.getEntriesByType('measure'));
```

---

## Feature-Specific Testing

### Validation Result Caching

**Test Steps:**

1. Open project
2. Click "Validate All"
3. Note request time in Network tab
4. Click "Validate All" again immediately
5. **Expected**: No new API request (cached)
6. Wait 5+ minutes
7. Click "Validate All" again
8. **Expected**: New API request (cache expired)

**Browser Notes:**
- Chrome: Check "Preserve log" in Network tab
- Firefox: Network tab auto-clears on reload
- Safari: Network tab under "Develop" menu

### Tooltips

**Test Steps:**

1. Hover over "Validate All" button
2. Hover over validation tabs
3. Hover over entity validation buttons
4. Hover over "Apply Fix" buttons

**Expected Results:**
- [ ] Tooltip appears within 500ms
- [ ] Text is readable
- [ ] Tooltip disappears on mouse-out
- [ ] No overlapping elements

**Safari Note**: Tooltips may appear slower

### Loading Indicators

**Test Steps:**

1. Click "Validate All"
2. Observe loading skeleton

**Expected Results:**
- [ ] Skeleton appears immediately
- [ ] Realistic multi-line structure
- [ ] Smooth pulsing animation
- [ ] Instant replacement when data loads
- [ ] No flash of empty content

**Performance Tip**: Throttle to "Slow 3G" in DevTools to see skeleton longer

### Success Animations

**Test Steps:**

1. Make YAML change
2. Save project
3. Observe success notification

**Expected Results:**
- [ ] Smooth scale-in transition (~300ms)
- [ ] No stuttering
- [ ] Auto-dismiss after 3 seconds
- [ ] GPU-accelerated (no jank)

### Debounced Validation

**Test Steps:**

1. Type rapidly in YAML editor
2. Monitor Network tab

**Expected Results:**
- [ ] Validation waits 500ms after last keystroke
- [ ] Only one request after typing stops
- [ ] No "validation storm"
- [ ] Typing remains responsive

### ag-Grid Data Preview

**Test Steps:**

1. Load entity preview (Preview tab or split view)
2. Observe ag-grid

**Expected Results:**
- [ ] Grid renders with proper styling
- [ ] Text color has good contrast
- [ ] Row height appropriate (compact)
- [ ] Header height appropriate
- [ ] Font size readable (10-11px)
- [ ] Scrolling smooth
- [ ] Columns resizable
- [ ] Sorting works (if enabled)

### Fixed Values Grid

**Test Steps:**

1. Create entity with type `fixed`
2. Add keys and columns
3. Interact with Fixed Values Grid:
   - Add row
   - Edit cells
   - Delete selected rows
   - Select multiple rows

**Expected Results:**
- [ ] Grid displays with columns from keys + columns
- [ ] Rows addable
- [ ] Cells editable (click to edit)
- [ ] Checkbox selection works
- [ ] Delete removes selected rows
- [ ] Data saves to YAML as 2D array
- [ ] Grid compact (small fonts, padding)

---

## Error Scenario Testing

### Syntax Errors

**Test: YAML Syntax Error**

1. Introduce YAML syntax error (e.g., invalid indentation)
2. Attempt to save
3. Run validation

**Expected Results:**
- [ ] Editor highlights error
- [ ] Hover shows error message
- [ ] Save completes (allows invalid YAML)
- [ ] Validation shows syntax error
- [ ] Error message indicates line number

### Missing References

**Test: Reference Non-Existent Entity**

1. In foreign key, reference entity that doesn't exist
2. Save entity
3. Run validation

**Expected Results:**
- [ ] Validation error appears
- [ ] Error message: "Entity 'xxx' not found"
- [ ] Location information provided
- [ ] Can fix by updating reference

### Circular Dependencies

**Test: Create Circular Dependency**

1. Entity A depends on Entity B
2. Entity B depends on Entity A
3. Run validation

**Expected Results:**
- [ ] Validation error about circular dependency
- [ ] Entities involved listed
- [ ] Can fix by removing one dependency

### Invalid SQL

**Test: Malformed SQL in Entity**

1. Create SQL entity
2. Enter invalid SQL (e.g., missing FROM clause)
3. Save entity
4. Try to preview

**Expected Results:**
- [ ] Preview fails gracefully
- [ ] Error message shows SQL error
- [ ] No app crash
- [ ] Can edit SQL and retry

### API Errors

**Test: Backend Unavailable**

1. Stop backend server (`Ctrl+C` in backend terminal)
2. Try to load project or validate

**Expected Results:**
- [ ] Error notification appears
- [ ] Error message: "Unable to connect to server"
- [ ] UI remains functional (no crash)
- [ ] Can retry after restarting backend

**Test: API Returns Error**

1. Trigger API error (e.g., invalid data source reference)
2. Observe error handling

**Expected Results:**
- [ ] Error notification with details
- [ ] Error logged to console
- [ ] User-friendly error message
- [ ] Can dismiss and continue

### Network Errors

**Test: Slow/Failed Network Requests**

1. Open DevTools Network tab
2. Throttle to "Slow 3G"
3. Perform actions (load project, validate, preview)

**Expected Results:**
- [ ] Loading indicators appear
- [ ] Requests eventually complete
- [ ] Timeout handled gracefully (if request fails)
- [ ] User notified of issues
- [ ] Can retry failed requests

---

## Performance Testing

### Frontend Performance Metrics

**Test: Initial Load Time**

1. Open DevTools Performance tab
2. Clear cache and hard reload (Ctrl+Shift+R)
3. Record load time

**Expected Results:**
- [ ] First Contentful Paint < 1 second
- [ ] Time to Interactive < 2 seconds
- [ ] Total load time < 2 seconds
- [ ] No render-blocking resources

**Test: Component Render Performance**

1. Open large project (10+ entities)
2. Open DevTools Performance tab
3. Start recording
4. Perform actions (open entity editor, switch tabs)
5. Stop recording
6. Analyze

**Expected Results:**
- [ ] Component render < 100ms
- [ ] 60 FPS during animations
- [ ] No long tasks (> 50ms)
- [ ] Smooth scrolling

**Test: Memory Usage**

1. Open DevTools Memory tab
2. Take heap snapshot (baseline)
3. Use app for 10 minutes (navigate, edit, validate)
4. Take another heap snapshot
5. Compare

**Expected Results:**
- [ ] Memory usage < 100MB
- [ ] No detached DOM nodes
- [ ] No memory leaks
- [ ] Memory released after closing dialogs

### API Response Times

**Test: Measure API Calls**

1. Open DevTools Network tab
2. Perform actions that trigger API calls:
   - Load project
   - Validate
   - Preview entity
   - Execute workflow
   - Load data source schema
   - Download execution result

**Expected Results:**
- [ ] Health check < 50ms
- [ ] Load project < 500ms
- [ ] Validate < 5 seconds
- [ ] Preview < 2 seconds
- [ ] Execute < 15 seconds (depends on data size)
- [ ] Schema < 500ms
- [ ] Download initiates immediately

---

## Accessibility Testing

### Keyboard Navigation

**Test: Tab Through Interface**

1. Tab through all interactive elements
2. Note tab order

**Expected Results:**
- [ ] All buttons/links reachable via Tab
- [ ] Tab order logical (top-to-bottom, left-to-right)
- [ ] Focus indicators clearly visible
- [ ] Can activate with Enter/Space
- [ ] Can close dialogs with Escape
- [ ] No keyboard traps

**Test: Form Navigation**

1. Open entity editor
2. Tab through all form fields
3. Use arrow keys in dropdowns

**Expected Results:**
- [ ] Tab moves between fields logically
- [ ] Arrow keys navigate dropdowns
- [ ] Can submit form with Enter
- [ ] Can cancel with Escape

### Screen Reader Testing

**Tools:**
- **Windows**: NVDA (free)
- **macOS**: VoiceOver (built-in)
- **Linux**: Orca

**Test: Screen Reader Compatibility**

1. Enable screen reader
2. Navigate application
3. Fill out forms
4. Trigger notifications

**Expected Results:**
- [ ] All buttons have accessible labels
- [ ] Form fields have labels
- [ ] Errors announced
- [ ] Notifications announced
- [ ] Landmarks defined (nav, main, etc.)
- [ ] ARIA attributes appropriate

### Color Contrast

**Test: Contrast Ratios**

1. Install WAVE or axe DevTools extension
2. Run accessibility audit
3. Check color contrast

**Expected Results:**
- [ ] Normal text: 4.5:1 minimum
- [ ] Large text: 3:1 minimum
- [ ] UI components: 3:1 minimum
- [ ] No contrast failures

**Test: Color Blindness**

1. Use browser extension (e.g., "Colorblinding")
2. Simulate different types of color blindness
3. Verify UI still usable

**Expected Results:**
- [ ] Information not conveyed by color alone
- [ ] Icons/text labels used with colors
- [ ] Error/success states distinguishable

### Focus Management

**Test: Focus Indicators**

1. Tab through interface
2. Observe focus rings/outlines

**Expected Results:**
- [ ] Focus indicator visible on all elements
- [ ] Focus indicator high contrast
- [ ] Custom focus styles maintain visibility
- [ ] Focus not hidden by CSS

**Test: Modal Focus Trap**

1. Open entity editor dialog
2. Tab through dialog
3. Try to tab outside dialog

**Expected Results:**
- [ ] Focus trapped within dialog
- [ ] Tab cycles through dialog elements
- [ ] Focus returns to trigger on close
- [ ] Can close with Escape

---

## Test Results Template

### Test Session Template

```markdown
## Frontend Manual Test Session - [Date]

**Tester**: [Your Name]
**Environment**: [OS, Browser versions]
**Backend Version**: [Backend version or commit]
**Frontend Version**: [Frontend version or commit]

### Test Summary

| Category | Tests Passed | Tests Failed | Notes |
|----------|--------------|--------------|-------|
| Core Application | 5/5 | 0 | All passed |
| Project Editor | 8/10 | 2 | Save occasionally slow |
| Entity Editor | 15/15 | 0 | All passed |
| Validation | 6/7 | 1 | Cache not invalidating |
| Execute Workflow | 9/9 | 0 | All passed |
| Cross-Browser | 4/4 | 0 | All browsers tested |
| Performance | 4/5 | 1 | Memory usage high |
| Accessibility | 6/6 | 0 | All passed |

### Detailed Results

#### Project Editor - Save Performance

**Issue**: Save button occasionally takes > 2 seconds

**Steps to Reproduce**:
1. Open large project (20+ entities)
2. Make small edit
3. Click Save

**Expected**: Save completes within 1 second
**Actual**: Save takes 2-3 seconds

**Severity**: Medium
**Browser**: Chrome 121, Firefox 115
**Priority**: P2

#### Validation - Cache Invalidation

**Issue**: Validation cache not invalidating after edit

**Steps to Reproduce**:
1. Run validation
2. Edit entity
3. Save
4. Run validation again

**Expected**: New validation request
**Actual**: Cached results returned

**Severity**: High
**Browser**: All
**Priority**: P1

### Browser Compatibility Matrix

| Feature | Chrome 121 | Firefox 115 | Edge 121 | Safari 16 |
|---------|-----------|-------------|----------|-----------|
| Project List | ✅ | ✅ | ✅ | ⚠️ Slow |
| YAML Editor | ✅ | ✅ | ✅ | ✅ |
| Entity Editor | ✅ | ✅ | ✅ | ✅ |
| Validation | ✅ | ✅ | ✅ | ❌ Cache |
| Execute Workflow | ✅ | ✅ | ✅ | ✅ |
| Download Results | ✅ | ✅ | ✅ | ✅ |
| Data Sources | ✅ | ✅ | ✅ | ✅ |
| Animations | ✅ | ✅ | ✅ | ⚠️ Jank |

**Legend:**
- ✅ Pass - Works as expected
- ⚠️ Minor Issue - Works with minor problems
- ❌ Fail - Does not work
- ⏸️ Blocked - Cannot test

### Performance Metrics

| Metric | Chrome | Firefox | Edge | Safari | Target |
|--------|--------|---------|------|--------|--------|
| Initial Load | 1.2s | 1.5s | 1.3s | 1.8s | < 2s |
| Project Load | 450ms | 500ms | 480ms | 600ms | < 500ms |
| Validation | 3.2s | 3.5s | 3.3s | 4.1s | < 5s |
| Execute Workflow | 8.5s | 9.1s | 8.7s | 10.2s | < 15s |
| Memory (10min) | 85MB | 92MB | 87MB | 105MB | < 100MB |

### Issues Found

1. **[P1] Validation cache not invalidating** - See details above
2. **[P2] Save performance degradation** - See details above
3. **[P3] Safari animation jank** - Minor stuttering in theme transitions

### Recommendations

1. Investigate validation cache invalidation logic
2. Profile save operation for large configurations
3. Optimize Safari-specific CSS animations
4. Add performance monitoring to catch regressions

### Notes

- All critical paths working correctly
- No blocking issues found
- Minor performance concerns in specific scenarios
- Overall stability good across browsers
```

---

## Quick Test Checklists

### 5-Minute Smoke Test

Minimal test to verify basic functionality:

- [ ] Application loads without errors
- [ ] Can navigate between pages
- [ ] Can open a project
- [ ] Can edit and save YAML
- [ ] Can run validation
- [ ] Can open entity editor
- [ ] Can execute workflow
- [ ] Theme toggle works

### 15-Minute Regression Test

After code changes, verify core features:

- [ ] Load project list
- [ ] Create new project
- [ ] Edit existing project
- [ ] Save changes
- [ ] Run full validation
- [ ] View validation results
- [ ] Create new entity
- [ ] Edit entity (all tabs)
- [ ] Add foreign key
- [ ] Test foreign key join
- [ ] Load entity preview
- [ ] Apply auto-fix
- [ ] Execute workflow (Excel output)
- [ ] Download execution result
- [ ] Switch themes
- [ ] Test in two browsers

### 1-Hour Full Test

Comprehensive test before release:

- [ ] Complete all sections in this guide
- [ ] Test in all supported browsers
- [ ] Run accessibility audit
- [ ] Measure performance metrics
- [ ] Test error scenarios
- [ ] Verify all features
- [ ] Document any issues
- [ ] Fill out test results template

---

## Appendix

### Useful Keyboard Shortcuts

**Application:**
- `Ctrl/Cmd + S` - Save project
- `Ctrl/Cmd + K` - Open command palette (if implemented)
- `Ctrl/Cmd + /` - Toggle comments in YAML editor

**DevTools:**
- `F12` - Open/close DevTools
- `Ctrl/Cmd + Shift + C` - Element picker
- `Ctrl/Cmd + Shift + M` - Responsive design mode
- `Ctrl/Cmd + Shift + P` - Command menu in DevTools

### Common Issues and Solutions

**Issue**: Application won't load
- **Solution**: Check backend is running, clear browser cache

**Issue**: YAML editor not highlighting syntax
- **Solution**: Refresh page, check console for Monaco errors

**Issue**: Validation not running
- **Solution**: Check Network tab for API errors, verify backend connection

**Issue**: Entity editor won't open
- **Solution**: Check console for errors, verify entity exists in project

**Issue**: Save not working
- **Solution**: Check for validation errors, verify backend writable permissions

### Test Data Locations

- **Projects**: `/home/roger/source/sead_shape_shifter/input/`
- **Test Database**: `/home/roger/source/sead_shape_shifter/input/test_query_tester.db`
- **Backups**: `/home/roger/source/sead_shape_shifter/backups/`

### Contact

For questions or issues with testing:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Include test results template
- Attach screenshots/videos if applicable
