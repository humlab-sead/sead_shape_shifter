
# Finally cleanup step

### Bugs

 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: Active route only highlighted in navigation breadcrumbs for "Projects"
 - [] FIXME: #114 Database and port number fields in data source view are empty
 - [] FIXME: #115 Titles in data source view are displayed inconsistently
 - [] FIXME: #116 Intermittent navigation error when opening project
 - [] FIXME: #117 pening a project always creates a new session
 - [] FIXME: #118 Legend in dependency graph has transparent background.
 - [] FIXME: #119 Entity Editor layout needs improvements
 - [x] FIXME: #120 [Reconciliation] Wrong number of published entities. (Fixed: Added service manifest endpoint and real-time entity count)
 - [x] FIXME: #122 No API call made when doing alternative search in entity reconciliation editor (Fixed: Added targetField parameter)
 - [ ] FIXME: #124 Reconciliation editor complains when "extra_columns" entered in property field
 - [ ] FIXME: #126 Preview fails due to duplicate column names.
 - [ ] FIXME: #138 Wrong VITE_API_BASE_URL when front end served via backend

### Tech debts:

 - [ ] FIXME: #89 Test Faker or mimesis for data generation in normalization tests
 - [ ] FIXME: #143 Update Docker configuration and related documentation

### New features

 - [x] TODO: #121 Add dual-mode editing of entity reconciliation specifications (Completed: YAML/Form tabs with Monaco editor)
 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step.
 - [] TODO: #66 Introduce a "transformations" section.
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #98 Enable entity to have multiple reconciliation specifications.
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [] TODO: #125 Add capability to edit full reconciliation YAML
 - [] TODO: #127 Add three-state toggling of L/R panes in entity ediitor.
 - [] TODO: #137 Rename "ingest" in UX to "dispatch" since it better conveys UX perspective. Move feature inside project editor.

 qbj 

# Tiny DSL Expression Support in extra_columns

The "extra_colums" key in an entity's specification provides a way of adding new columns to the resulting DataFrame. The extra_columns value is a dict, where each key is the name of the new column, and the value is the initial value of the new column. The value can be a constant, or anoother column in the source or DataFrame.

It would be useful to support simple expressions in the key's value, e.g. create a fullname column for two first/last name columns. The expressions could translate to Pandas operations, or a python function that transforms the Pandas DataFrame.

Please suggest a YAML-notation for the expression in the extra-columns section for this feature, and how it could be implemented.. Try to make this feature simple but useful.


## Feature Idea

Add expressions under extra_columns using a tiny DSL in YAML, e.g.
```yml
extra_columns:
  fullname: "{row.first_name} + ' ' + {row.last_name}"
  initials: "concat(initials, first_name[:1], last_name[:1])"
```
where {row.X} refers to source/df fields and helpers (like concat or slicing) map to Pandas-friendly Python.

## Implementation path:
 - Interpret the string by formatting it inside a sandboxed helper that injects the current pandas.Series (row) or even the whole DataFrame.
 - For column-wise expressions, leverage df.eval/df.assign after prepping a safe namespace with allowed functions (concat, upper, etc.).
 - For more complex transformations, allow users to specify "lambda df: df['a'] + df['b']" (evaluated via eval with a restricted globals containing only helpers and pd).
- Keep simple by defaulting to expressions evaluated per-row via df.eval or df.assign, with ability to refer to any existing column.

## Next steps:

1. Decide whether expressions should be evaluated row-by-row (via df.assign(extra=...)) or on the whole DataFrame.
2. Implement parsing/evaluation in the pipeline step where extra_columns currently get applied (likely near the Filter/Link stage).
3. Add tests covering constant, direct column reference, and expression cases.
Expression Detection

Treat every extra_columns value as a string; interpret it as an expression only if it uses a special marker (e.g., starts with expr: or contains {/} tokens). Anything else stays literal.
Recommended rule: if the string matches expr:<python> (e.g., fullname: "expr:df['first_name'] + ' ' + df['last_name']"), run it through the expression evaluator; otherwise just assign the string directly.
This keeps defaults simple (constants work out of the box) while giving a clear hint when evaluation is intended.

Using "expr: python-pandas-row-expression" sounds great. It might be a bit complicated for non-technical users, thoght. Can you suggest a layer/notation above these expressions that exposes the most common e.g. string expressions,a nd that "ompiles" into these pandas expressions? E.g. "= <user-friendly-expression>" by the backend compiles to "expr:<corresponding-python-expression>". In such a case, non-tech user can add simple expressions, but we still have a super-user option.


Expression DSL

Introduce a mini DSL for extra_columns like:

extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=upper(substr(first_name, 0, 1)) + upper(substr(last_name, 0, 1))"
  source_note: "expr:df['city'] + ' (' + df['code'] + ')'"
Strings starting with = are treated as friendly expressions; strings starting with expr: are raw pandas expressions for power users. Anything else stays constant.

Backend implementation: parse the string when it’s added to the DataFrame. If the value starts with expr:, strip the prefix and run it through df.assign(**{name: eval(expr, safe_globals, {"df": df})}). If it starts with =, feed it to a small compiler that replaces helper names with pandas operations (e.g., concat(a, b) → df['a'].astype(str) + df['b'].astype(str), upper(x) → df['x'].str.upper(), substr(x, start, length) → df['x'].str[start:start+length], ifnull(x, default) etc.), then evaluate the resulting pandas expression in the same safe context. Constants remain untouched.

Keep helper mappings simple so non-technical users can combine columns with string functions; expose more via extending the compiler (e.g., additional helpers for dates or math).

- TODO: #129 Add "ingestion" capability to Shape Shifter workflow (e.g sead_clearinghouse_import) 
  
The Shape Shifter application is designed to facilitate the ingestion and processing of data submissions through a structured workflow. The end result of the workflow is the generation of CSV files or Excel files that represent the data in a format suitable for database ingestion. Currently, this system targets the SEAD relational database schema. The system that imports the data produced by Shape Shifter is the SEAD Clearinghouse Import system (sead_clearinghouse_import) which is added as a project to this workspace.

I want you to analyse the sead_clearinghouse_import system, and suggest a detailed implementation plan how the sead_clearinghouse_import can be added as a final step in the Shape Shifter workflow, so that when the user clicks "Run Workflow", the data is not only processed and output as CSV/Excel files, but also automatically ingested into a SEAD database via the sead_clearinghouse_import system. It can also be an additional button "Ingest to SEAD" if that makes more sense. For simplicity, I would like to add sead_clearinghouse_import as module within the Shape Shifter backend codebase, so that the entire workflow from data ingestion to SEAD database population is handled within a single application in a mono-repo. I still want the Shape Shifter to be moduler, so I would prefer to place sead_clearinghouse_import separately e.g. in an "ingesters" subfolder with a clear interface towards the rest of the system. The functionality needed corresponds to the importer/scripts/import_excel.py script. I can imagine creating a workflow interface for ingesters that can be implemented by sead_clearinghouse_import and any future ingesters that may be added later. I also want to keep the possibility to call the workflow via a CLI script.

I want you to suggest a detailed implementation plan how to achieve this, including any necessary changes to the Shape Shifter backend codebase, any new configuration options that need to be added, and any changes to the frontend that may be required. Please provide a step-by-step plan with clear tasks and milestones.

Please takes this into account:

Ignore any code found in "deprecated" folder
Ignore "importer/configuration" since this is an exact copy of configuration module in Shape Shifter.
Avoid sharing domain model between the ingesters and the Shape Shifters. The main part of the API is the Excel file produced by Shape Shifter. You can ignore CSV output format for now. The API should have a "is_satisfied/validate" method (or endpoint) that the user via UX can call to check if the ingester accepts the Excel file.
The API could be an endpoint exposed by the backend e.g. /ingest/ingester-name" etc with a set of well defined methods. In such a case the backend need to be able to scan the system (e.g. via a Registry) for avaliable ingesters.


TODO: #131 Relocate the ingester implementations

Move ingesters (e.g. "sead" folder) to a folder outside of backend to this structure:

```
backend/
   app/
      ...
      ingeters/
         __init__.py
         protocol.py
         registry.py
         README.md
ingesters/
  sead/
      /dispatchers
      /importer
      __init__.py
      ingester.py
      registry.py
      README.md
  ...
```

The IngesterRegistry would be responsible for scanning/loading for registering avaliable ingesters. A config option in the backend would point to the ingesters folder. This would make it easier to add new ingesters in the future without changing the backend codebase. The ingesters would implement a common interface defined in backend/app/ingesters/protocol.py.

TODO: #134 Add ingestion options to Shape Shifter project file. 
We need to introduce an "ingesters" section in the project file under "options". The values in this section would be default values for ingester UX, and values specific for a certain ingester module. 

We should (at least for the time being) remove the target database from the ingestion UX, and instead rely on what's defined in the datasource.
```yml
metadata:
  name: arbodat-test
  type: shapeshifter-project
  description: ...
  ...
entities:
  abundance:
    ...
  ...
options:
  data_sources:
    sead: "@include: sead-options.yml"
    ....
  ...
  ingesters:
    sead: # could be "@include: sead-ingester.yml"
      data_source: sead # UX default. or "@include: sead-options.yml"
      options:
        database: # resolved value of data_source
        transfer_format: csv
        ignore_columns:  # UX default. 
          - "date_updated"
          - "*_uuid"
          - "(*"
      policies:
        if_foreign_key_value_is_missing_add_identity_mapping_to_foreign_key_table:
          priority: 1
        set_public_id_to_negative_system_id_for_new_lookups:
          disabled: true
        update_missing_foreign_key_policy:
          tbl_dataset_contacts:
            contact_type_id: 2
            contact_id: 1
        if_lookup_table_is_missing_add_table_using_system_id_as_public_id:
          tables:
            - tbl_abundance_elements
            - tbl_contact_types
            - tbl_dataset_submission_types
            - tbl_location_types
            - tbl_project_types
            - tbl_project_stages
            - tbl_relative_ages
            - tbl_sample_group_sampling_contexts
            - tbl_sample_types
          preallocated_tables:
        if_lookup_with_no_new_data_then_keep_only_system_id_public_id:
          priority: 9
        drop_ignored_columns:
          priority: 3
          columns:
            - "date_updated"
            - "*_uuid"
```

TODO: #140 Improve user experience

The user experience of this system can be improved.  Currently the "default" workflow is to edit entities via the project's entity list, which can be somewhat cumbersome when there are a lot of entities.  Some of the existing functions in the system can be improved tp user experience.

1. Use the dependency graph view as an alternative view point of the project, i.e. instead of using the "entity list" view. These would mean adding "Open entity" (e.g. double click) and "Add entity". It would be best if the entity editor overlayed the dependency graph instead of the system bouncing to the entity view

TODO: #141 Improve user experience (right click context menu)

Add a context menu on right mouse click show "duplicate", "delete" and "preview" options.


TODO: Improve user experience ()

Emphasing the end result. When a project is started the user (most often) knows what entities to create. How can this information be utilized so that the user get a feel of having a task log? Some entities are mandatory, and the "depend_on" and foreign keys gives a possibly logical "work order". or "action item list".
   
3. Perhaps intriducing "project templates", which would basically be project YAML files where mandatory entities exists. That can form the starting point for templates.


---------------------------------------------------------------------------------------------------------------------------------------------------------------

These are excellent UX improvement ideas that align well with how users naturally think about data transformation workflows. Here are my thoughts:

## On Your Proposed Improvements

### 1. Dependency Graph as Primary Navigation ✓ Strong idea

**Benefits:**
- **Visual workflow understanding**: Users can see the entire transformation pipeline at a glance
- **Context preservation**: Editing in overlay keeps the big picture visible
- **Natural navigation**: Graph structure mirrors actual work dependencies
- **Reduced cognitive load**: No context switching between views

**Implementation considerations:**
- **Overlay pattern**: Use a slide-out panel or modal that doesn't hide the graph
- **Visual feedback**: Highlight entity in graph when editing, show validation states as node colors
- **Quick actions**: Right-click context menu for common operations (duplicate, delete, preview)
- **Mini-map**: For large projects, add a zoom-able overview

### 2. Task-Oriented Templates & Progress Tracking ✓ Very strong idea

**Benefits:**
- **Guided workflow**: Especially valuable for new users or complex domains
- **Progress visibility**: Clear completion tracking motivates users
- **Consistency**: Templates ensure best practices
- **Onboarding**: New team members can start faster

**Implementation suggestions:**
- **Template structure**: Include mandatory entities, optional entities, and suggested work order
- **Smart completion tracking**: Mark entities as "complete" when they pass validation and have preview data
- **Dependency-aware ordering**: Auto-suggest next entity based on what's complete
- **Template marketplace**: Start with SEAD template, allow users to export their own as templates

## Additional UX Improvements

### 3. **Entity Quick-Add Wizard**
Since you already know target entities, streamline creation:
```
"Add Entity" → Wizard shows:
- Required fields only (name, source_data, depend_on)
- Smart defaults from similar entities
- Preview column mapping immediately
- Validate & create in one flow
```

### 4. **Inline Validation Feedback**
Currently validation may feel separate from editing:
- **Real-time validation badges** on graph nodes (✓ valid, ⚠ warnings, ✗ errors)
- **Hover tooltips** on graph showing validation messages
- **One-click fixes** for auto-fixable issues directly from graph
- **Diff preview** before applying auto-fixes

### 5. **Entity Cloning/Duplication**
For similar entities (common in multi-table workflows):
- **"Duplicate entity" action** preserving structure
- **Bulk edit mode** for changing multiple entities at once
- **Pattern detection**: Suggest duplication when adding similar entity names

### 6. **Work Session Management**
Track user progress across sessions:
- **Auto-save drafts** (you already have backups/)
- **Session resume**: "Continue where you left off" with highlighted incomplete entities
- **Change history**: Show recent edits in sidebar
- **Collaboration markers**: If multi-user, show who's editing what

### 7. **Smart Search & Filtering**
For projects with many entities:
- **Quick filter** in graph: by status (incomplete/complete), by data source, by dependencies
- **Search highlights** matching entities in graph
- **Bookmark frequently edited** entities

### 8. **Preview-Driven Development**
Make preview more central:
- **Split-screen mode**: Edit YAML on left, live preview on right
- **Preview caching** (you already have this in backend)
- **Sample data explorer**: Show sample rows for any entity from graph
- **Preview comparison**: Side-by-side before/after when editing

### 9. **Keyboard Navigation**
Power users will appreciate:
- **Arrow keys** to navigate graph nodes
- **Enter** to open entity editor
- **Ctrl+S** to save, **Ctrl+P** to preview
- **Tab** to cycle through incomplete entities
- **Command palette** (Cmd+K) for all actions

### 10. **Contextual Help**
Reduce learning curve:
- **Inline documentation** for each YAML field (tooltips or ? icons)
- **Example snippets** for common patterns (reconciliation, unnest, filters)
- **Guided tours** for first-time users
- **Validation error explanations** with links to docs

## Recommended Implementation Priority

**Phase 1 (High Impact, Lower Effort):**
1. Graph overlay entity editor
2. Inline validation badges on graph
3. Entity quick-add with smart defaults
4. Keyboard navigation basics

**Phase 2 (Template System):**
1. Template YAML schema extension
2. Template loader/manager
3. Progress tracker UI component
4. SEAD starter template

**Phase 3 (Polish):**
1. Session management & auto-save improvements
2. Split-screen preview mode
3. Entity cloning
4. Advanced search/filtering

**Phase 4 (Power Features):**
1. Command palette
2. Bulk editing
3. Collaborative features
4. Advanced keyboard shortcuts

## Technical Approach

### Frontend Changes Needed:
```typescript
// New composables
useGraphNavigation() - handle node selection, double-click, overlay
useTemplates() - load/apply templates, track completion
useTaskProgress() - calculate completion % based on validation
useKeyboardShortcuts() - global keyboard event handling

// Store enhancements
graphStore - selection state, filter state, view mode
templateStore - available templates, active template, completion tracking
sessionStore - draft state, recent changes, bookmarks

// New components
EntityEditorOverlay.vue - slide-out panel over graph
TemplateSelector.vue - template chooser on project creation
ProgressTracker.vue - task completion widget
GraphContextMenu.vue - right-click actions on nodes
```

### Backend Changes Needed:
```python
# New endpoints
GET /api/v1/templates - list available templates
GET /api/v1/templates/{name} - get template YAML
POST /api/v1/projects/from-template - create project from template
GET /api/v1/projects/{name}/progress - calculate completion metrics

# Template schema
metadata.template = True
metadata.mandatory_entities = ["entity1", "entity2"]
metadata.suggested_order = ["entity1", "entity2", "entity3"]
```

## Quick Win: Graph Overlay Editor

This could be implemented relatively quickly with high impact:

1. Add `showEntityEditor` ref to graph component store
2. Create `EntityEditorOverlay.vue` that takes entity name as prop
3. Emit `edit-entity` event from graph on double-click
4. Render overlay with backdrop, slide animation from right
5. Reuse existing entity editor form inside overlay
6. Add close button and Escape key handler

Would you like me to start implementing any of these improvements? I'd recommend starting with the **graph overlay editor** as it provides immediate value and sets up the foundation for the template system.