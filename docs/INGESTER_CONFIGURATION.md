# Ingester Configuration in Shape Shifter Projects

## Overview

The Shape Shifter project file now supports an `ingesters` section under `options`. This section defines ingester-specific configuration, policies, and default values that are used by the ingestion UI and CLI.

## Configuration Structure

```yaml
options:
  data_sources:
    # Define your data sources here
    target_database:
      driver: postgresql
      host: localhost
      port: 5432
      # ... other connection details
  
  ingesters:
    <ingester_name>:
      data_source: <data_source_reference>
      options:
        # Ingester-specific options
      policies:
        # Ingester-specific policies
```

## Fields

### `data_source` (required)
Reference to a data source defined in `options.data_sources`. This is the target database where data will be ingested.

**Example:**
```yaml
ingesters:
  sead:
    data_source: sead_staging  # References options.data_sources.sead_staging
```

### `options` (optional)
Ingester-specific configuration options. These serve as defaults in the ingestion UI.

**Common options:**
- `transfer_format`: Format for data transfer (`csv` or `excel`)
- `ignore_columns`: List of column patterns to exclude from ingestion
- `do_register`: Whether to register data in the database (boolean)
- `explode`: Whether to explode data to public tables (boolean)

**Example:**
```yaml
options:
  transfer_format: csv
  ignore_columns:
    - "date_updated"
    - "*_uuid"
    - "(*"
  do_register: true
  explode: false
```

### `policies` (optional)
Ingester-specific policies that control data transformation and validation behavior. These vary by ingester implementation.

## SEAD Ingester Configuration

The SEAD ingester supports the following policies:

### `if_foreign_key_value_is_missing_add_identity_mapping_to_foreign_key_table`
Add identity mapping when foreign key values are missing.

```yaml
if_foreign_key_value_is_missing_add_identity_mapping_to_foreign_key_table:
  priority: 1
```

### `set_public_id_to_negative_system_id_for_new_lookups`
Use negative system IDs as public IDs for new lookup values.

```yaml
set_public_id_to_negative_system_id_for_new_lookups:
  disabled: true  # Set to false to enable
```

### `update_missing_foreign_key_policy`
Specify default values for missing foreign keys in specific tables.

```yaml
update_missing_foreign_key_policy:
  tbl_dataset_contacts:
    contact_type_id: 2
    contact_id: 1
  tbl_another_table:
    field_id: 123
```

### `if_lookup_table_is_missing_add_table_using_system_id_as_public_id`
Add lookup tables if they're missing from the submission.

```yaml
if_lookup_table_is_missing_add_table_using_system_id_as_public_id:
  tables:
    - tbl_abundance_elements
    - tbl_contact_types
    - tbl_dataset_submission_types
  preallocated_tables: []
```

### `if_lookup_with_no_new_data_then_keep_only_system_id_public_id`
Keep only system_id and public_id columns for lookup tables with no new data.

```yaml
if_lookup_with_no_new_data_then_keep_only_system_id_public_id:
  priority: 9
```

### `drop_ignored_columns`
Drop columns matching specified patterns.

```yaml
drop_ignored_columns:
  priority: 3
  columns:
    - "date_updated"
    - "*_uuid"
    - "temp_*"
```

## Complete Example

See [`input/example-ingester-config.yml`](../input/example-ingester-config.yml) for a complete example.

## Usage in UI

When a project with ingester configuration is loaded:

1. The **Data Ingestion** view will automatically load defaults from the project configuration
2. The target database is determined by the `data_source` field
3. Default values for ignore columns, register, and explode flags are pre-populated
4. Users can override these defaults before running ingestion

## Usage in CLI

The CLI ingestion script will also read these defaults:

```bash
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "my-submission" \
  --data-types "dendro"
# Database and other options are loaded from project config
```

You can still override defaults via CLI flags:

```bash
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "my-submission" \
  --data-types "dendro" \
  --ignore-columns "custom_*" \
  --no-register
```

## Benefits

1. **Consistency**: Same configuration for UI and CLI
2. **Version Control**: Ingester settings tracked with project
3. **Reusability**: Share ingester configurations across team
4. **Flexibility**: Override defaults when needed
5. **Documentation**: Configuration serves as documentation

## Migration from Previous Version

Previously, users had to manually select a database and configure options each time. With the new system:

1. Add an `ingesters` section to your project file
2. Reference your target database via `data_source`
3. Configure default options and policies
4. Save the project file

The ingestion UI will now automatically use these settings.

## See Also

- [Ingester System Documentation](../backend/app/ingesters/README.md)
- [SEAD Ingester Implementation](../ingesters/sead/README.md)
- [Project Configuration Guide](./CONFIGURATION_GUIDE.md)
