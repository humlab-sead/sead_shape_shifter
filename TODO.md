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

 - [] FIXME: File modification date is always 1970-01-21 when listing configurations
 - [x] FIXME: #48 [Frontend] Unnest tool doesn't work, nothing happens 
 - [x] FIXME: #49 [Frontend] Text color in preview grid is the same as background color in dark mode
 - [] FIXME: When opening YAML view in entity editor, an empty entity is displayed
 - [] FIXME: Saving a configuration stores the YAML in a file with a new filename
 - [x] FIXME: #54 The ag-grid in tab "PREVIEW" needs styling
 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: Keys is a mandatory field, but many entities has no value in Keys
 - [x] FIXME: #61 Information missing in Global Data Sources view
 - [] FIXME: #63 Wrong modified data in Configurations view 
 - [] FIXME: #62 Testing a UCanAccess data source returns success, but no tables are found.
 - [] FIXME:
 - [] FIXME:
 - [] FIXME:


### Tech debts:

 - [x] FIXME: Improve test coverage (+85%)
 - [ ] FIXME: #59 [Frontend] Create frontend (manual) testing guide 

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: #21 Add UX for mapping/reconciling remote/target entities to local entities.
 - [x] TODO: #52 dispatch.py: Add support for colors, formats, etc. using openpyxl
 - [x] TODO: #51 Add ability to test entity configurations without executing full normalization workflow.
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: Change so that only entities avaliable for service reconciliation are displayed  
 - [] TODO: #53 Fixed value grid must be more compact
 - [] TODO: #55 Not all transformations are shown in Preview mode 
 - [] TODO: #56 Add capability to export preview
 - [] TODO: #57 Add capability to set number of rows (including all) from preview
 - [] TODO: #58 FK editor needs styling