
### Bugs

FIXME: Projects are sometimes stored with resolved values.
FIXME: #219 Inline data source configurations raised an error.

### Tech debts:


### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step that removes intermediate tables and columns.
 - [] TODO: #66 Introduce a "transformations" section with more advance columnar transforms (e.g. toWSG84).
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [] TODO: Improve multiuser support (working on same project)
 - [] TODO: Add more reconciliation entity types, and non-SEAD types (e.g. Geonames, RAÄ-lämningsnummer)
 - [] TODO: NOT WORTH THE EFFORT! Improve user experience (Add new edge/relationship in dependency graph)
 - [] TODO: Improve in-system help (full User Guide, more context sensitive help)
 - [] TODO: Improve UX suggestions when editing entity (awareness of availiable tables, columns etc)
 - [] TODO: Auto-save feature in YAML editing mode (trigger after 2 seconds of inactivity)
 - [] TODO: Consider limiting "@value:" directive usage to only refer to non-directive keys.
 - [] TODO: Consnider moving specifications/base/get_entity_columns it to TableConfig
            Note that columns avaliable at a specifik FK's linking includes result columns from previous linked FKs.

### TODO: #108 Tiny DSL Expression Support in extra_columns DETAILS

The "extra_colums" key in an entity's specification provides a way of adding new columns to the resulting DataFrame. The extra_columns value is a dict, where each key is the name of the new column, and the value is the initial value of the new column. The value can be a constant, or anoother column in the source or DataFrame.

It would be useful to support simple expressions in the key's value, e.g. create a fullname column for two first/last name columns. The expressions could translate to Pandas operations, or a python function that transforms the Pandas DataFrame.

Please suggest a YAML-notation for the expression in the extra-columns section for this feature, and how it could be implemented.. Try to make this feature simple but useful.


Feature Idea

Add expressions under extra_columns using a tiny DSL in YAML, e.g.
```yml
extra_columns:
  fullname: "{row.first_name} + ' ' + {row.last_name}"
  initials: "concat(initials, first_name[:1], last_name[:1])"
```
where {row.X} refers to source/df fields and helpers (like concat or slicing) map to Pandas-friendly Python.

Implementation path:
 - Interpret the string by formatting it inside a sandboxed helper that injects the current pandas.Series (row) or even the whole DataFrame.
 - For column-wise expressions, leverage df.eval/df.assign after prepping a safe namespace with allowed functions (concat, upper, etc.).
 - For more complex transformations, allow users to specify "lambda df: df['a'] + df['b']" (evaluated via eval with a restricted globals containing only helpers and pd).
- Keep simple by defaulting to expressions evaluated per-row via df.eval or df.assign, with ability to refer to any existing column.

Next steps:

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


### TODO: #124 Reconciliation editor extra_columns complaint - **Easy Fix**
- The reconciliation editor validation is likely too strict
- Simple fix: Update schema/validation to allow `extra_columns` property
- **Effort: 1-2 hours** | **Value: High** (removes user friction)
---

### TODO: Generate default reconciliation YAML from manifest - **Smart Feature**
- Calls `/reconcile` endpoint and scaffolds YAML
- **Effort: 6-8 hours** | **Value: High** (user productivity)
- Reconciliation system already exists with full implementation

### TODO: #68 Add "finally" cleanup step - **Pipeline Feature**
- Drops intermediate tables/columns after processing
- **Effort: 8-12 hours** | **Value: Medium** (clean output)
- Fits naturally after Store phase

### TODO: #108 Tiny DSL for extra_columns - **HIGH VALUE but Complex**
- Detailed spec already exists in TODO.md
- Two-tier approach is smart: `=concat(...)` for users, `expr:...` for power users
- **Effort: 2-3 weeks** | **Value: Very High** (major feature)
- **Recommendation: Phase 1 = Just `expr:` support (1 week), Phase 2 = DSL compiler (2 weeks)**

### TODO: #66 Transformations section (toWGS84, etc.) - **Data Quality Feature**
- Coordinate transformations, case normalization, etc.
- **Effort: 2-3 weeks** | **Value: High for geo data**
- Consider using existing libraries (pyproj for coords)

### TODO: #69 Add "parent" property to entities - **Hierarchical Data**
- Useful for nested structures (site → feature → sample)
- **Effort: 1-2 weeks** | **Value: Medium** (depends on use cases)

### TODO: #67 String concatenation in extra_columns - **Subset of #108**
- **Recommendation: Skip if doing #108 DSL, otherwise quick win**
- **Effort: 2-3 days** | **Value: Medium**

### TODO: Duplicate existing configuration - **User Convenience**
- Copy project with new name
- **Effort: 2-3 hours** | **Value: Medium**

### TODO: Add optional types for entity fields - **Type Safety**
- Schema validation + conversions in extra_columns
- **Effort: 1-2 weeks** | **Value: Medium** (better error messages)

### TODO: Improve multiuser support - **Complex Feature**
- Requires conflict resolution, locking, real-time sync
- **Effort: 4-6 weeks** | **Value: Low** (unless multiple concurrent users)
- **Recommendation: Defer unless actual need arises**

### TODO: Add more reconciliation entity types - **Domain-Specific**
- Geonames, RAÄ, etc.
- **Effort: Varies** | **Value: Depends on user base**
- **Recommendation: Add on demand, not preemptively**

### TODO: Improve UX suggestions when editing entity - **Context-Aware Editor**
- Show available tables/columns from data source
- **Effort: 2-3 weeks** | **Value: High for new users**
- Could integrate with existing YAML intelligence


**Bottom line:** Focus on Phase 1 (bugs), then tackle #108 DSL in two phases. The extra_columns DSL is your highest-value unimplemented feature based on the detailed spec you've already written.

Add capability to upload Excel files (.xls, .xlsx) to the data source files directory defined by SHAPE_SHIFTER_DATA_SOURCE_FILES_DIR in the .env file. The uploaded Excel files should be accessible for use in entity configurations within the Shape Shifter application.

### TODO: #181 Drop duplicates of "site" entity fails FD validation

### TODO: Introduce entity type "file" for entities based on files,
Type of files could be csv, excel, json, xml etc, and specified in e.g a "file_type" field.
This would give a more plugin friendly way of adding file based entities.

### TODO: #202 Improve FK editing user experience

We can improve the user experience when editing FKs. Currently, thw system offers no assistance when entering local and remote FK. 

I think the system could offer picklists of available local and remote columns. This picklist should include all columns from each entity that is a candidate for the FK relationship, i.e. all columns in columns, keys nd extra_columns, any columns that are generated during normalization (e.g. result of unnesting unnested columns (value id, value vars, id_vars), FK-columns and FK's extra columns etc), system_id, public_id.
The candidate columns can be computed without doing the full normalization, by analyzing the entity definitions and their relationships.

A special case is if the user wants to use a "@value"-directive to point to e.g. another YAML-key in the project. To keep it aimple "@value: entities.**local/remote-entity-name**.keys" could be added to the picklist.
One could also for flexibility allow the user to enter arbitrary YAML-path i.e. a åath that doesn't exist in the picklist.
If a "@value" is used, that can be the only value, and should be a string (not a list). This will be resolved at runtime to the actual column(s).

The "auto_detect_columns", i believe, is the only attibute in the entity workflow that is changed during the normalization. 

### FIXME: Data Source in Schema Explorer is empty
Data Source in Schema Explorer is empty unless Data Sources tab is visited first. This is because the data sources are only loaded into the store when visiting the Data Sources tab. We should consider loading data sources on app startup to avoid this issue.

### TODO: #213 Copy SQL feature from Schema Explorer.
Add a convenience function for copying an SQL select statement to the clipboard for selected entity in schema explorer. This is useful when a user want to create an SQL select in the entity editor based on a table in the specified data source. This could also possibly be extended to a "picker" in the entity editor that allows users to select a table from the data source and automatically generate a select statement for that table.

### TODO: Add a "Test Query" button in the entity editor.
Should open a modal with a Monaco Editor for SQL editing, allowing users to test SQL queries against the data source directly from the entity editor. This would provide a more integrated experience for users working with SQL entities.

### TODO: Do not close Entity Editor on Save

Consider not closing the entity editor modal when clicking "Save" to allow users to make multiple edits without having to reopen the editor each time. This could be implemented as a user preference or a toggle in the UI.

### TODO: #217 Allow a user to create an entity of type "sql" by specifying a data source, a table in that data source, and an entity name. The new entity would be initialized with:
- type: sql
- data_source: data-source
- query: select * from table-name
- keys: tables PKs in data source (as is seen in schema explorer)
- public_id: table-name + "_id"

I guess one option is to add the feature to Schema Explorer, where we have all the information when data source, a table and a columns are displayed. But this feature is outside of a project. We could allow for opening be opening schema explorer from within the project (e.g. from the "data sources" tab), or ask for which project to put it in (and add data source to project if missing). Another option whould be a button next to each data source in the "data source" tab, thet would show a create dialog with asking for name and a table picker.

What do you think, would this feature be worthwhile?

Auto-Detection Logic:

Table name → entity name (with sanitization: my_table ✓, my-table → my_table)
Primary keys → keys field
If no PKs → empty keys: [] (user can add manually)
public_id = {table_name}_id (follows convention)
Smart Defaults:

Query: SELECT * FROM {table_name} (user can customize later)
If table has composite PK → all PK columns in keys
Preserve schema prefix if present: public.sites → SELECT * FROM public.sites
Validation:

Entity name uniqueness in project
Data source connectivity (test before showing tables)
Table existence (cached from schema service)
Error Handling:

Data source not connected → "Please test connection first"
No tables found → "No tables available in this data source"
Entity name conflict → "Entity 'X' already exists. Choose different name."

### TODO: Save custom graph layout in separate file


### TODO: #221 System fails to find ingesters folder
The system currently fails to find the ingesters folder when running in Docker. Cause: the ingesters folder is not copied to the Docker image, we need to copy the ingesters folder to the Docker image in the Dockerfile, and set environment variables accordingly.

### TODO: #222 Using columns added by a FK as local keys in a subsequent FK does not work

When trying to link the dataset_contacts entity to the contact entity using the contact_name as the linking key this error is logged. The .
The `_project_contact` is correctly normalized and contains the contact_name column, but the dataset_contacts entity cannot find the contact_name column in its local data when trying to link to the contact entity.

The `contact_name` is added as an extra column in the foreign key from dataset_contacts to _project_contact, but it seems that this extra column is not being included in the local data of dataset_contacts when performing the link to contact.


```
2026-02-08 16:15:24.962 | ERROR    | src.transforms.link:link_entity:84 - dataset_contacts[linking]: ✗ Configuration has 1 error(s):
  1. [ERROR] Entity 'dataset_contacts': dataset_contacts -> contact: local keys {'contact_name'} not found in local entity data 'dataset_contacts'
```

```yml
dataset_contacts:
  type: entity
  source: dataset
  public_id: dataset_contact_id
  keys: [Projekt, Fraktion, contact_id]
  columns: []
  foreign_keys:
  - entity: _project_contact
    local_keys: [Projekt]
    remote_keys: [Projekt]
    extra_columns:
      contact_name: contact_name
  - entity: contact
    local_keys: [contact_name]
    remote_keys: [contact_name]
  depends_on: [_project_contact, contact, dataset, project]
  drop_duplicates: [Projekt, Fraktion, contact_id]

_project_contact:
  type: sql
  source:
  public_id: project_contact_id
  keys: [Projekt, contact_type, contact_name]
  columns: [Projekt, ArchAusg, ArchBear, BotBear]
  drop_duplicates: [Projekt, contact_type, contact_name]
  unnest:
    id_vars: [Projekt]
    value_vars: [ArchAusg, ArchBear, BotBear]
    var_name: contact_type
    value_name: contact_name
  data_source: arbodat_data
  query: "select distinct [Projekt], [ArchAusg], [ArchBear], [BotBear] from [Projekte] ;\n"

### FIXME: #228 Silent failures occurs when fetching Excel file metadata

### TODO: #229 Add project refresh feature for reloading project from disk

### TODO: #231 Pressing "CREATE" when adding a new entity doesn't save the entity. It only adds the entity to the project in memory, but does not save the project to disk. This can lead to confusion for users who expect their changes to be saved immediately. We should have the same buttons when creating a new entity as for editing an existing entity .

### FIXED: #234 Sync issue after new entity creation ✅
~~The following steps can be taken to reproduce the issue:
  1. (Refresh project)
  2. Click "Add entity"
  3. Click enter entity name, select XLSX, sheet name, public id, click "Create"
  4. Click "Save" in entity editor
  5. Entity editor mode changes to "Edit".
     Project "SAVE CHANGES" becomes enabled. (This should not happen since entity was saved)
     New entity is visible in project view's entity list.
  6. Close entity editor.
     Open file on disk (outside of application) shows that new entity has been written to disk.
     Open YAML in project's view shows that the new entity is NOT present, i.e. project in memory is NOT updated with the new entity, so the project in memory is out of sync with the project on disk.~~

**Fixed in commit 3c3ca82**: Entity store now refreshes project from disk after create/update/delete operations, ensuring in-memory state matches saved state. 

