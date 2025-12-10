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

# FIXED Improved deletion of empty row data

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

