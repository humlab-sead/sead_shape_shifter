# Shape Shifter Configuration Rules

These statements summarize the validation requirements implemented by `src/specifications.py`. Follow them when authoring or reviewing project configuration files to ensure every specification passes.

## Foreign key rules
- A non-`cross` join must explicitly list matching numbers of `local_keys` and `remote_keys` that exist as columns (or unnest columns for the local table) before data linkage is considered valid.
- `cross` joins must not specify `local_keys` or `remote_keys`.
- In data-aware checks, every referenced entity must have a loaded DataFrame and the required keys must exist in the actual data; missing local keys that appear only after unnesting defer validation, but missing remote key values or local key values (that are not unnest columns) fail validation.

## Entity structure requirements
- Every configuration must provide an `entities` section; each entity name must be unique, and every declared dependency (`depends_on`, `source`, and foreign key `entity`) must reference an entity that exists in the same configuration.
- Entities may not form circular dependencies across `depends_on` and `source` relationships.
- Each entity must declare both `columns` and `keys` as lists of strings (`EntityFieldsSpecification`), and any missing required fields should be reported explicitly.
- Fixed-type entities must supply `surrogate_id` (ending with `_id` is preferred), `columns`, and `values` (or a resolved `source`) with matching lengths; every `values` row should match the column count.
- Regular data tables must include either `columns` or `keys`; `columns`, when present, must be a string list.

## Foreign key configuration rules
- Each foreign key entry must include `entity`, `local_keys`, and `remote_keys`.
- `local_keys` and `remote_keys` must be lists of equal length.
- `extra_columns` (if provided) must be a string, list, or dictionary.

## Special entity features
- The optional `unnest` block requires `value_vars`, `var_name`, and `value_name`; omitting `id_vars` is allowed but should emit a warning.
- `drop_duplicates` can be a boolean, string, or list; other types are invalid.
- Surrogate IDs should be unique across entities and preferably end with `_id`; duplicates or deviations emit warnings.

## Source and append constraints
- SQL-type entities must declare `data_source` and a non-empty `query`, and they should not specify a `source`.
- Fixed-type entities should not specify a `source`, but must define `columns` and `values`.
- Every referenced `data_source` (entity-level or in `append`) must exist inside `options.data_sources`.
- `append` configurations must be lists of append blocks; each block must specify exactly one of `type` or `source`.
  - A `type` of `fixed` requires a non-empty `values` list; `sql` requires a `query`.
  - A `source` reference must point to an existing entity and should ideally include explicit `columns` mapping.
- `append_mode`, when used alongside `append`, must be either `all` or `distinct`.

## Composite validation
- The `CompositeProjectSpecification` runs all individual specifications (`RequiredFieldsSpecification`, `EntityExistsSpecification`, `CircularDependencySpecification`, `DataSourceExistsSpecification`, `SqlDataSpecification`, `FixedDataSpecification`, `ForeignKeySpecification`, `UnnestSpecification`, `DropDuplicatesSpecification`, `SurrogateIdSpecification`, and `AppendConfigurationSpecification`) and reports every accumulated error or warning.
