# Enhancement Suggestions

# Entity Inheritance

- Add "parent" property to entity definitions to enable inheritence
  of properties, eliminating redundancy and improving maintainability.
  If a parent entity is specified, the child entity should inherit all
  properties from the parent unless explicitly overridden.

# Simple String Concatenation in Extra Columns

- Introduce support for string concatenation in "extra_columns" in entity definitions. As a starting point,
  support string concatenation using a syntax like:
  
  ```yaml
  extra_columns:
    full_name: ["first_name", " ", "last_name"]
  ```

# **FIXED** Improved deletion of empty row data

- Add support for specifying which values except np.na that should be considered as empty for row deletion.

  ```
  drop_empty_rows:
      column_name_1:
        - ""
        - "N/A"
        - "null"
      column_name_2:
        - "unknown"
      etc.
  ```

# STARTED Add value transformations

- Introduce a "transformations" section within entity definitions to allow for common data transformations
  such as trimming whitespace, changing case, or applying custom functions to column values.

  Example:
  ```yaml
  entities:
    sample:
      surrogate_id: sample_id
      keys: [sample_name]
      columns: [sample_name, ...]
      transformations:
        sample_name:
          - trim_whitespace
          - to_uppercase
      depends_on: [site]
  ```

# Finally cleanup step
- Add a "finally" step after all entities have been processed to allow for final adjustments
  or validations on the entire dataset.
  e.g.,
  
  ```yaml
  finally:
    drop:
      tables:
        - _pcodes
      columns:
          - site: [temp_column1, temp_column2]
          - sample: [temp_column3]
  """

# **FIXED** Use "query" prefix for SQL data source values instead of "values: sql: ..."
- Standardize SQL data source queries by using a "query" prefix instead of embedding SQL directly in "values".
  This improves clarity and consistency in configuration files.

  Example:
  ```yaml
  append:
    - type: sql
      data_source: test_sql_source
      query: SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude
  ```

# **FIXED** Validation Improvements

Improve validations for configuration files to catch the most common errors and give better feedback. Add an option to run validations without executing the full normalization workflow. 


### Bugs

 - [] FIXME: #12 [Frontend]: Nothing happens when "Entities" is clicked.
 - [] FIXME: #14 [Frontend]: Nothing happens when clicking "FORCE DIRECTED" in dependency view 
 - [] FIXME: #15 [Frontend/Backend]: Testing data sources fails.
 - [] FIXME: #16 [Crosscutting] Add data source driver specific properties using schema registry.
 - [] FIXME: #17 [Frontend] Sidebar "Entities" unaware of loaded configuration
 - [] FIXME: #23 Preview of data fails with strange error message
 - [x] FIXME: #28 When saving a configuration all "macros" are resolved/lost.
 - [x] FIXME: #29 Data source editor has strange labels
 - [] FIXME: File modification date is always 1970-01-21 when listing configurations
 - [x] FIXME: [Backend] Postgres Edit doesn't display values fomr data source configuration
 - [] FIXME: src/model.py:161:9: W0511: This smells like a fix for a bug elsewhere, why should we check extra columns here? (fixme)
 - [] FIXME: Query Tester has no data sources
 - [] FIXME: Schema Explorer has no data sources
 - [x] FIXME: #39 Nothing happens when clicking "Add" in FK Editor


### Tech debts:

 - [x] FIXME: #26 [Backend] Move database vendor specific logic to Loaders
 - [x] FIXME: [Backend] Test for MS Access returns 0 tables
 - [x] INSTALL: Codex AGENTS.md
 - [x] FIXME: #33 Remove hardcoded settings in backend/app/core/config.py

### New features

 - [x] TODO: #18 [Frontend/Backend] Add ability to edit entity configuration in a dual-mode editor (Form/YAML). 
 - [] TODO: [Frontend/Backend] Add ability to edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: #31 [Frontend/Backend] Simplify data source management.
 - [] TODO: #21 Add UX for mapping/reconciling remote/target entities to local entities.
 - [] TODO: #30 Add logic to identify a YAML file as a shape shifter config file
 - [] TODO: dispatch.py: Add support for colors, formats, etc. using openpyxl
 - [] TODO: #32 backend/app/services/data_source_service.py:43:9: Consider making patterns configurable, or to probe content for "driver" key (fixme)
 - [x] TODO: #34 Improve server side state management for configuration editing, what should be per app (lifespan) vs per request? **COMPLETED** - See docs/STATE_MANAGEMENT_IMPLEMENTATION.md
 - [x] TODO: #37 Add session management to frontend configuration editors. **COMPLETED** - See frontend/FRONTEND_SESSION_QUICKSTART.md
 - [] TODO: Add ability to test entity configurations without executing full normalization workflow.
 - [] TODO: Add setting view to frontend to configure frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: #41 Add grid editor for editing fixed entity
 - [] TODO: #44 Use grid editor in preview
 - [] TODO: #45 Improve REPL experience
 - [] TODO: #43 Move configuration tools inside editor