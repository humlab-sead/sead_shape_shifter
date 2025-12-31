# Driver Schema Registry Implementation

## Overview

This implementation provides a clean, extensible system for managing data source driver configurations through a **driver metadata registry pattern**. The system eliminates hardcoded field definitions and enables dynamic form generation in the UI.

## Architecture

FIXME: Describe new field attribute `aliases` that allows mapping multiple config names to the same field.
### 1. Core Components

#### `input/driver_schemas.yml`
YAML file defining all driver schemas. Each driver specifies:
- `display_name`: Human-readable name
- `description`: Driver description
- `category`: "database" or "file"
- `fields`: List of configuration fields with metadata

Field types: `string`, `integer`, `boolean`, `password`, `file_path`

Registered drivers:
- `postgresql` - PostgreSQL database (host, port, database, username, password)
- `access` / `ucanaccess` - MS Access database (filename, ucanaccess_dir)
- `sqlite` - SQLite database (filename)
- `csv` - CSV file (filename, encoding, delimiter)

#### `src/loaders/driver_metadata.py`
- **`FieldMetadata`**: Dataclass for field metadata (type, required, default, validation rules)
- **`DriverSchema`**: Dataclass for complete driver schema (fields, display info, category)
- **`DriverSchemaRegistry`**: Central registry that loads schemas from YAML on first access

The registry uses lazy loading - schemas are automatically loaded from `input/driver_schemas.yml` when first accessed.

### 2. Backend API

#### New Endpoint: `GET /api/v1/data-sources/drivers`
Returns JSON schema for all available drivers:

```json
{
  "postgresql": {
    "driver": "postgresql",
    "display_name": "PostgreSQL",
    "category": "database",
    "fields": [
      {
        "name": "host",
        "type": "string",
        "required": true,
        "default": "localhost",
        "description": "Database server hostname",
        "placeholder": "localhost"
      },
      ...
    ]
  }
}
```

#### Updated Mapper: `DataSourceMapper`
- Schema-aware mapping between API and core models
- Automatically validates required fields
- Handles password extraction from SecretStr
- Applies default values from schema
- Preserves additional options not in schema

### 3. Frontend Components

#### `frontend/src/types/driver-schema.ts`
TypeScript type definitions for driver schemas

#### `frontend/src/composables/useDriverSchema.ts`
Vue composable providing:
- `loadSchemas()` - Fetch schemas from API
- `getSchema(driver)` - Get schema for specific driver
- `getFieldsForDriver(driver)` - Get configuration fields
- `getDefaultFormValues(driver)` - Get defaults for new form
- `validateField(driver, fieldName, value)` - Validate field value
- `availableDrivers` - Computed list of drivers for dropdown

#### Updated `DataSourceFormDialog.vue`
- Dynamically renders form fields based on driver schema
- Shows only relevant fields for selected driver
- Applies validation rules from schema
- Uses field metadata for hints, placeholders, and labels

## Benefits

### 1. **Single Source of Truth**
Loaders define what configuration they need. No duplication across layers.

### 2. **Type Safety**
Strong typing from Python dataclasses to TypeScript interfaces.

### 3. **Dynamic UI**
Frontend adapts automatically when new drivers are added or schemas change.

### 4. **Better UX**
- Only relevant fields shown per driver
- Clear field descriptions and placeholders
- Consistent validation across stack

### 5. **Easy Extension**
Adding a new driver requires only:
1. Create `DriverSchema` in `driver_metadata.py`
2. Register it in the registry
3. No frontend changes needed!

## Usage Examples

### Adding a New Driver

Simply add a new entry to `input/driver_schemas.yml`:

```yaml
mysql:
  display_name: MySQL
  description: MySQL database connection
  category: database
  fields:
    - name: host
      type: string
      required: true
      default: localhost
      description: Database server hostname
      placeholder: localhost
    
    - name: port
      type: integer
      required: false
      default: 3306
      description: Database server port
      placeholder: "3306"
      min_value: 1
      max_value: 65535
    
    - name: database
      type: string
      required: true
      description: Database name
      placeholder: mydb
    
    - name: username
      type: string
      required: true
      description: Database user
      placeholder: root
    
    - name: password
      type: password
      required: false
      description: Database password
```

That's it! The schemas are loaded automatically. The API and frontend will immediately support MySQL connections without any code changes.

### Validation in Services

```python
from src.loaders.driver_metadata import DriverSchemaRegistry

schema = DriverSchemaRegistry.get(driver)
if not schema:
    raise ValueError(f"Unknown driver: {driver}")

# Check required fields
for field in schema.fields:
    if field.required and not config.get(field.name):
        raise ValueError(f"Missing required field: {field.name}")
```

## Testing

- `backend/tests/test_driver_schema.py` - API endpoint tests
- `backend/tests/test_data_source_mapper.py` - Mapper logic tests
- All existing data source tests still pass

## Migration Notes

### Breaking Changes
None - fully backward compatible.

### Project Files
Existing YAML configuration files work without changes. The mapper handles both old and new formats.

### Frontend
The updated `DataSourceFormDialog` uses the schema but still works with existing data sources.

## Future Enhancements

1. **Client-side validation** - Use schema for immediate field validation
2. **Conditional fields** - Show/hide fields based on other field values
3. **Field groups** - Group related fields (e.g., "Connection", "Advanced")
4. **Schema versioning** - Support schema evolution over time
5. **Auto-discovery** - Scan loaders for schema definitions automatically
